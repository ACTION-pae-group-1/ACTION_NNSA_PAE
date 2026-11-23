"""Offline-only tests of the explicitly invoked monthly BLS source helper."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError

import pytest

from bls_mcp.tests.unit.manual_monthly_import import load

monthly = load("manual_bls_monthly")

AGENT = "manual-BLS-tests/1.0 (tests@example.org)"


class FakeResponse:
    def __init__(self, url: str, body: bytes, *, headers: dict[str, str] | None = None):
        self.url = url
        self.stream = io.BytesIO(body)
        self.headers = headers or {"Content-Type": "text/plain"}

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)

    def geturl(self) -> str:
        return self.url

    def close(self) -> None:
        self.stream.close()

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def fixture_listing(program: str) -> str:
    names = (
        [
            "pc.industry",
            "pc.product",
            "pc.series",
            "pc.data.0.Current",
            "pc.data.20.ComputerProduct",
        ]
        if program == "pc"
        else [
            "cu.area",
            "cu.item",
            "cu.series",
            "cu.data.0.Current",
            "cu.data.1.AllItems",
        ]
    )
    return (
        "<html>"
        + "".join(
            f'<a href="/pub/time.series/{program}/{name}">{name}</a>' for name in names
        )
        + "</html>"
    )


def inventory(root: Path, program: str, month: str) -> Path:
    folder = root / month / program
    folder.mkdir(parents=True)
    path = folder / "discovery.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "month": month,
                "program": program,
                "directory_url": monthly.directory_url(program),
                "files": monthly.parse_listing(fixture_listing(program), program),
            }
        ),
        encoding="utf-8",
    )
    return folder


def test_discovery_only_accepts_official_direct_file_links():
    html = """<a href='/pub/time.series/pc/pc.series'>ok</a>
    <a href='https://evil.invalid/pub/time.series/pc/pc.data.0.Current'>bad</a>
    <a href='/pub/time.series/cu/cu.area'>wrong</a>
    <a href='pc.data.0.Current'>ok2</a>
    <a href='../pc/pc.data.20.ComputerProduct'>not direct</a>
    <a href='/pub/time.series/pc/../../pc.data.50.Oops'>traversal</a>"""
    result = monthly.parse_listing(html, "pc")
    assert [x["path"] for x in result] == ["pc.data.0.Current", "pc.series"]
    with pytest.raises(monthly.AcquisitionError, match="No recognized"):
        monthly.parse_listing("<html><title>Access denied</title></html>", "cu")


def test_discovery_one_request_per_program_and_month(tmp_path, monkeypatch):
    month = datetime.now(UTC).strftime("%Y-%m")
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    urls: list[str] = []

    def respond(url: str, agent: str, timeout: float):
        urls.append(url)
        assert agent == AGENT and timeout == 40.0
        return FakeResponse(url, fixture_listing("pc").encode())

    monkeypatch.setattr(monthly, "_request", respond)
    result = monthly.discover(tmp_path, month, "pc")
    assert result.is_file()
    assert len(json.loads(result.read_text())["files"]) == 5
    with pytest.raises(monthly.AcquisitionError, match="Already discovered"):
        monthly.discover(tmp_path, month, "pc")
    assert urls == [monthly.directory_url("pc")]


def test_historical_download_requires_explicit_partition(tmp_path):
    month = datetime.now(UTC).strftime("%Y-%m")
    folder = inventory(tmp_path, "cu", month)
    items = monthly._inventory(folder, "cu", month)
    with pytest.raises(monthly.AcquisitionError, match="require --partition"):
        monthly.select_sources(items, "cu", "historical", [], False)
    with pytest.raises(monthly.AcquisitionError, match="Not a discovered"):
        monthly.select_sources(
            items, "cu", "historical", ["cu.data.666.Invented"], False
        )
    chosen = monthly.select_sources(
        items, "cu", "historical", ["cu.data.1.AllItems"], False
    )
    assert [x["path"] for x in chosen] == [
        "cu.area",
        "cu.item",
        "cu.series",
        "cu.data.1.AllItems",
    ]
    both = monthly.select_sources(items, "cu", "both", [], True)
    assert len(both) == 5


@pytest.mark.parametrize("program", ["pc", "cu"])
def test_download_creates_pinned_manifest_and_never_refetches(
    tmp_path, monkeypatch, program
):
    month = datetime.now(UTC).strftime("%Y-%m")
    inventory(tmp_path, program, month)
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    delays: list[float] = []
    urls: list[str] = []
    monkeypatch.setattr(monthly.time, "sleep", lambda value: delays.append(value))

    def respond(url: str, agent: str, timeout: float):
        urls.append(url)
        assert agent == AGENT and timeout == 90.0
        name = url.rsplit("/", 1)[-1]
        role = monthly._role(program, name)
        if program == "pc":
            from bls_mcp.ingestion.manifest import _HEADERS
        else:
            from bls_mcp.ingestion.cu_manifest import _HEADERS

        body = ("\t".join(_HEADERS[role]) + "\n").encode()
        return FakeResponse(
            url,
            body,
            headers={
                "Content-Type": "text/plain",
                "Content-Length": str(len(body)),
                "ETag": '"test"',
            },
        )

    monkeypatch.setattr(monthly, "_request", respond)
    result = monthly.download(tmp_path, month, program, "current", [], False)
    doc = json.loads(result.read_text())
    assert doc["schema_version"] == 1 and doc["program"] == program
    if program == "pc":
        from bls_mcp.ingestion.manifest import load_pc_manifest

        manifest = load_pc_manifest(result)
        from bls_mcp.ingestion.manifest import verify_pc_source

        assert len(manifest.selected()) == 4
        for source in manifest.selected():
            assert verify_pc_source(manifest.resolve(source), source) > 0
    else:
        from bls_mcp.ingestion.cu_manifest import load_cu_manifest

        manifest = load_cu_manifest(result)
        from bls_mcp.ingestion.cu_manifest import verify_cu_source

        assert len(manifest.selected()) == 4
        for source in manifest.selected():
            assert verify_cu_source(manifest.resolve(source), source) > 0
    assert len(doc["files"]) == 4
    assert len(urls) == len(delays) == 4
    assert all(30.0 <= pause <= 90.0 for pause in delays)
    assert len(set(delays)) > 1
    audit = [
        json.loads(line)
        for line in (result.parent / "requests.jsonl").read_text().splitlines()
    ]
    assert len(audit) == 4
    assert all(entry["http_status"] == 200 for entry in audit)
    assert all(entry["result"] == "ok" for entry in audit)
    assert all(entry["bytes_received"] > 0 for entry in audit)
    for entry in doc["files"]:
        name = entry["path"]
        raw = (result.parent / name).read_bytes()
        assert raw and raw.endswith(b"\n")
        assert entry["sha256"] == monthly._hash_file(result.parent / name)[0]
        assert entry["source_url"] == monthly.file_url(program, name)
        assert entry["etag"] == '"test"'
    assert monthly.download(tmp_path, month, program, "current", [], False) == result
    assert len(urls) == 4


def test_resume_verifies_receipts_before_further_requests(tmp_path, monkeypatch):
    month = datetime.now(UTC).strftime("%Y-%m")
    folder = inventory(tmp_path, "pc", month)
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    monkeypatch.setattr(monthly.time, "sleep", lambda _: None)
    requested: list[str] = []

    def flaky(url: str, _agent: str, _timeout: float):
        requested.append(url)
        if len(requested) == 2:
            raise monthly.AcquisitionError("simulated outage")
        return FakeResponse(url, b"mock-data\n")

    monkeypatch.setattr(monthly, "_request", flaky)
    with pytest.raises(monthly.AcquisitionError, match="simulated outage"):
        monthly.download(tmp_path, month, "pc", "current", [], False)
    receipts = json.loads((folder / "download-receipts.json").read_text())
    assert len(receipts["files"]) == 1
    monkeypatch.setattr(
        monthly, "_request", lambda url, *_: FakeResponse(url, b"mock-data\n")
    )
    finished = monthly.download(tmp_path, month, "pc", "current", [], False)
    assert len(json.loads(finished.read_text())["files"]) == 4
    (folder / "pc.series").write_text("tampered", encoding="utf-8")
    (folder / "pc-input.json").unlink()
    with pytest.raises(monthly.AcquisitionError, match="hash/size mismatch"):
        monthly.download(tmp_path, month, "pc", "current", [], False)


def test_html_block_page_rejected_without_manifest(tmp_path, monkeypatch):
    month = datetime.now(UTC).strftime("%Y-%m")
    folder = inventory(tmp_path, "pc", month)
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    monkeypatch.setattr(monthly.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        monthly,
        "_request",
        lambda url, *_: FakeResponse(
            url,
            b"<!doctype html><html>blocked</html>",
            headers={"Content-Type": "text/plain"},
        ),
    )
    with pytest.raises(monthly.AcquisitionError, match="HTML block page"):
        monthly.download(tmp_path, month, "pc", "current", [], False)
    assert not list(folder.glob("*.part"))
    assert not (folder / "pc-input.json").exists()


def test_bad_user_agent_and_invalid_file_names(monkeypatch):
    monkeypatch.delenv("BLS_USER_AGENT", raising=False)
    with pytest.raises(monthly.AcquisitionError, match="BLS_USER_AGENT"):
        monthly._agent()
    for name in (
        "../pc.series",
        "pc.data.0.Current/../x",
        "..\\pc.series",
        "pc.data.0.Current?x=1",
    ):
        with pytest.raises(monthly.AcquisitionError):
            monthly.file_url("pc", name)


def test_network_failure_does_not_disable_tls_validation(monkeypatch):
    def fail(*_args: object, **_kwargs: object):
        raise URLError("CERTIFICATE_VERIFY_FAILED")

    monkeypatch.setattr(monthly, "urlopen", fail)
    with pytest.raises(monthly.AcquisitionError, match="CERTIFICATE_VERIFY_FAILED"):
        monthly._request(monthly.directory_url("cu"), AGENT, 10.0)


def test_month_must_be_current_and_redirects_remain_on_requested_file(
    tmp_path, monkeypatch
):
    with pytest.raises(monthly.AcquisitionError, match="current UTC"):
        monthly.discover(tmp_path, "2020-01", "pc")

    different = monthly.directory_url("pc") + "pc.series"
    other = monthly.directory_url("pc") + "pc.product"
    monkeypatch.setattr(
        monthly,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(other, b"misdirected"),
    )
    with pytest.raises(monthly.AcquisitionError, match="redirected away"):
        monthly._request(different, AGENT, 10.0)


def test_plan_lists_cached_inputs_without_http_or_agent(tmp_path, monkeypatch, capsys):
    month = datetime.now(UTC).strftime("%Y-%m")
    inventory(tmp_path, "pc", month)
    monkeypatch.delenv("BLS_USER_AGENT", raising=False)
    monkeypatch.setattr(
        monthly,
        "_request",
        lambda *_args: pytest.fail("plan must not contact BLS"),
    )
    assert (
        monthly.main(
            [
                "--root",
                str(tmp_path),
                "--month",
                month,
                "plan",
                "--program",
                "pc",
                "--selection",
                "both",
                "--partition",
                "pc.data.20.ComputerProduct",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "pc.industry" in output
    assert "pc.data.20.ComputerProduct" in output
    assert "No files downloaded" in output
    assert not (tmp_path / month / "pc" / "requests.jsonl").exists()


def test_explicit_pacing_is_configurable_and_rejects_unsafe_values(
    tmp_path, monkeypatch
):
    month = datetime.now(UTC).strftime("%Y-%m")
    inventory(tmp_path, "cu", month)
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    pauses: list[float] = []
    choices: list[tuple[float, float]] = []
    monkeypatch.setattr(monthly.time, "sleep", lambda delay: pauses.append(delay))

    def choose(low: float, high: float) -> float:
        choices.append((low, high))
        return low if len(choices) % 2 else high

    monkeypatch.setattr(monthly.random, "uniform", choose)
    monkeypatch.setattr(
        monthly, "_request", lambda url, *_: FakeResponse(url, b"data\n")
    )
    manifest = monthly.download(
        tmp_path,
        month,
        "cu",
        "current",
        [],
        False,
        min_delay=45.0,
        max_delay=75.0,
    )
    assert manifest.exists()
    assert choices == [(45.0, 75.0)] * 4
    assert pauses == [45.0, 75.0, 45.0, 75.0]

    for low, high in ((3, 90), (45, 30), (float("nan"), 90), (30, float("inf"))):
        with pytest.raises(monthly.AcquisitionError, match="finite delays"):
            monthly._validate_delays(low, high)


def test_single_process_lock_blocks_parallel_sessions(tmp_path, monkeypatch):
    month = datetime.now(UTC).strftime("%Y-%m")
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    requested: list[str] = []

    def respond(url: str, *_args):
        requested.append(url)
        with pytest.raises(monthly.AcquisitionError, match="Another manual"):
            monthly.discover(tmp_path, month, "cu")
        return FakeResponse(url, fixture_listing("pc").encode())

    monkeypatch.setattr(monthly, "_request", respond)
    result = monthly.discover(tmp_path, month, "pc")
    assert result.exists()
    assert requested == [monthly.directory_url("pc")]
    assert not (tmp_path / ".monthly-acquisition.lock").exists()
    audit = [
        json.loads(line)
        for line in (result.parent / "requests.jsonl").read_text().splitlines()
    ]
    assert len(audit) == 1
    assert audit[0]["action"] == "discover"
    assert audit[0]["bytes_received"] > 0


def test_rate_limit_stops_without_retry_and_is_logged(tmp_path, monkeypatch):
    from urllib.error import HTTPError

    month = datetime.now(UTC).strftime("%Y-%m")
    folder = inventory(tmp_path, "cu", month)
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    monkeypatch.setattr(monthly.time, "sleep", lambda _: None)
    requested: list[str] = []

    def blocked(url: str, _agent: str, _timeout: float):
        requested.append(url)
        raise monthly.AcquisitionError("BLS request failed: HTTP 429") from HTTPError(
            url, 429, "Too Many Requests", {}, None
        )

    monkeypatch.setattr(monthly, "_request", blocked)
    with pytest.raises(monthly.AcquisitionError, match="429"):
        monthly.download(tmp_path, month, "cu", "current", [], False)
    assert len(requested) == 1
    assert not (folder / "cu-input.json").exists()
    marker = tmp_path / ".bls-access-paused.json"
    assert json.loads(marker.read_text())["http_status"] == 429
    with pytest.raises(monthly.AcquisitionError, match="earlier request"):
        monthly.download(tmp_path, month, "cu", "current", [], False)
    with pytest.raises(monthly.AcquisitionError, match="earlier request"):
        monthly.discover(tmp_path, month, "pc")
    assert len(requested) == 1
    audit = [
        json.loads(line)
        for line in (folder / "requests.jsonl").read_text().splitlines()
    ]
    assert len(audit) == 1
    assert audit[0]["result"] == "failed"
    assert audit[0]["http_status"] == 429
    assert not (tmp_path / ".monthly-acquisition.lock").exists()


def test_stale_manual_lock_fails_closed(tmp_path, monkeypatch):
    month = datetime.now(UTC).strftime("%Y-%m")
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    (tmp_path / ".monthly-acquisition.lock").write_text("stale")
    monkeypatch.setattr(
        monthly,
        "_request",
        lambda *_args: pytest.fail("must not request with a lock"),
    )
    with pytest.raises(monthly.AcquisitionError, match="left a lock"):
        monthly.discover(tmp_path, month, "pc")
    assert (tmp_path / ".monthly-acquisition.lock").exists()


@pytest.mark.parametrize("program", ["pc", "cu"])
def test_completed_current_selection_can_expand_into_historical_without_refetch(
    tmp_path, monkeypatch, program, capsys
):
    """The first manifest remains immutable when the monthly selection grows."""
    month = datetime.now(UTC).strftime("%Y-%m")
    folder = inventory(tmp_path, program, month)
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    monkeypatch.setattr(monthly.time, "sleep", lambda _: None)
    requests: list[str] = []

    def respond(url: str, *_args):
        requests.append(url)
        name = url.rsplit("/", 1)[-1]
        role = monthly._role(program, name)
        if program == "pc":
            from bls_mcp.ingestion.manifest import _HEADERS
        else:
            from bls_mcp.ingestion.cu_manifest import _HEADERS

        return FakeResponse(url, ("\t".join(_HEADERS[role]) + "\n").encode())

    monkeypatch.setattr(monthly, "_request", respond)
    current = monthly.download(tmp_path, month, program, "current", [], False)
    current_bytes = current.read_bytes()
    first_count = len(requests)
    assert first_count == 4
    historical_name = (
        "pc.data.20.ComputerProduct" if program == "pc" else "cu.data.1.AllItems"
    )
    chosen = monthly.download(
        tmp_path, month, program, "historical", [historical_name], False
    )
    assert chosen != current and chosen.is_file()
    assert len(requests) == 5  # Only the new historical file.
    assert current.read_bytes() == current_bytes
    both = monthly.download(tmp_path, month, program, "both", [historical_name], False)
    assert both != chosen and both != current
    assert len(requests) == 5  # Every source was already present.
    assert len(json.loads(both.read_text())["files"]) == 5
    assert len(json.loads(chosen.read_text())["files"]) == 4
    assert len(json.loads(current.read_text())["files"]) == 4

    monkeypatch.delenv("BLS_USER_AGENT", raising=False)
    again = monthly.download(tmp_path, month, program, "both", [historical_name], False)
    assert again == both and len(requests) == 5
    assert "verified/reused" in capsys.readouterr().out
    assert (
        len(json.loads((folder / "download-receipts.json").read_text())["files"]) == 5
    )


def test_plan_discloses_reuse_and_identical_partition_arguments(
    tmp_path, monkeypatch, capsys
):
    month = datetime.now(UTC).strftime("%Y-%m")
    inventory(tmp_path, "cu", month)
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    monkeypatch.setattr(monthly.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        monthly, "_request", lambda url, *_: FakeResponse(url, b"source\n")
    )
    monthly.download(tmp_path, month, "cu", "current", [], False)
    monkeypatch.setattr(
        monthly, "_request", lambda *_: pytest.fail("plan is strictly offline")
    )
    assert (
        monthly.main(
            [
                "--root",
                str(tmp_path),
                "--month",
                month,
                "plan",
                "--program",
                "cu",
                "--selection",
                "both",
                "--partition",
                "cu.data.1.AllItems",
                "--partition",
                "cu.data.1.AllItems",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "4 reused, 1 network requests" in output
    assert "Duplicate --partition ignored" in output
    assert "may repeat series/year/period" in output
    assert "REUSE (checksum verified)" in output


def test_all_historical_excludes_named_partition_with_explicit_feedback(tmp_path):
    month = datetime.now(UTC).strftime("%Y-%m")
    folder = inventory(tmp_path, "cu", month)
    entries = monthly._inventory(folder, "cu", month)
    entries.append({"path": "cu.data.2.Additional", "role": "historical"})
    notes: list[str] = []
    files = monthly.select_sources(
        entries,
        "cu",
        "historical",
        [],
        True,
        excluded=["cu.data.1.AllItems"],
        notes=notes,
    )
    assert "cu.data.2.Additional" in [f["path"] for f in files]
    assert "cu.data.1.AllItems" not in [f["path"] for f in files]
    assert any("Excluded historical partition" in note for note in notes)
    with pytest.raises(monthly.AcquisitionError, match="Not a discovered"):
        monthly.select_sources(
            entries,
            "cu",
            "historical",
            [],
            True,
            excluded=["cu.data.99.Invented"],
        )
    with pytest.raises(monthly.AcquisitionError, match="requires --all-historical"):
        monthly.select_sources(
            entries,
            "cu",
            "historical",
            ["cu.data.2.Additional"],
            False,
            excluded=["cu.data.1.AllItems"],
        )


def test_pc_all_data_is_separate_from_historical_partitions():
    entries = monthly.parse_listing(
        fixture_listing("pc") + '<a href="pc.data.1.AllData">all data</a>', "pc"
    )
    assert (
        next(e for e in entries if e["path"] == "pc.data.1.AllData")["role"]
        == "all_data"
    )
    notes: list[str] = []
    historical = monthly.select_sources(
        entries, "pc", "historical", [], True, notes=notes
    )
    assert "pc.data.1.AllData" not in [e["path"] for e in historical]
    assert any("AllData intentionally excluded" in note for note in notes)
    all_data = monthly.select_sources(entries, "pc", "all-data", [], False)
    assert [e["path"] for e in all_data][-1] == "pc.data.1.AllData"
    with pytest.raises(monthly.AcquisitionError, match="only for PC"):
        monthly.select_sources(entries, "cu", "all-data", [], False)


def test_preexisting_file_without_receipt_blocks_new_requests(tmp_path, monkeypatch):
    month = datetime.now(UTC).strftime("%Y-%m")
    folder = inventory(tmp_path, "pc", month)
    (folder / "pc.series").write_text("some old file")
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    monkeypatch.setattr(
        monthly, "_request", lambda *_: pytest.fail("must not overwrite old file")
    )
    with pytest.raises(monthly.AcquisitionError, match="Unreceipted"):
        monthly.download(tmp_path, month, "pc", "current", [], False)


def test_corrupt_cached_file_blocks_expanding_download(tmp_path, monkeypatch):
    month = datetime.now(UTC).strftime("%Y-%m")
    folder = inventory(tmp_path, "pc", month)
    monkeypatch.setenv("BLS_USER_AGENT", AGENT)
    monkeypatch.setattr(monthly.time, "sleep", lambda _: None)
    monkeypatch.setattr(monthly, "_request", lambda url, *_: FakeResponse(url, b"ok\n"))
    monthly.download(tmp_path, month, "pc", "current", [], False)
    (folder / "pc.product").write_bytes(b"corrupt\n")
    monkeypatch.setattr(
        monthly, "_request", lambda *_: pytest.fail("must verify before requests")
    )
    with pytest.raises(monthly.AcquisitionError, match="hash/size mismatch"):
        monthly.download(
            tmp_path, month, "pc", "historical", ["pc.data.20.ComputerProduct"], False
        )


@pytest.mark.parametrize(
    "program,metadata,data",
    [
        ("wp", ["wp.group", "wp.item", "wp.series"], "wp.data.80.Construction"),
        (
            "ci",
            [
                "ci.owner",
                "ci.industry",
                "ci.occupation",
                "ci.subcell",
                "ci.area",
                "ci.estimate",
                "ci.series",
            ],
            "ci.data.1.AllData",
        ),
    ],
)
def test_additional_program_discovery_and_selection(program, metadata, data):
    names = [
        *metadata,
        "ci.data.0.Current" if program == "ci" else "wp.data.0.Current",
        data,
    ]
    html = "".join(f'<a href="{name}">{name}</a>' for name in names)
    files = monthly.parse_listing(html, program)
    assert len(files) == len(names)
    selection = "all-data" if program == "ci" else "historical"
    partitions = [] if program == "ci" else [data]
    selected = monthly.select_sources(files, program, selection, partitions, False)
    assert {item["path"] for item in selected} == set(metadata) | {data}


def test_ci_rejects_historical_partition_selection():
    with pytest.raises(monthly.AcquisitionError, match="all-data"):
        monthly.select_sources([], "ci", "historical", [], False)
