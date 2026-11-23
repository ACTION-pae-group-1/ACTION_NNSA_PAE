"""Offline-only, disk-bounded PC/CU data overlap diagnostics."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from bls_mcp.tests.unit.manual_monthly_import import load

monthly = load("manual_bls_monthly")
_overlap_audit = load("overlap_audit")
OverlapAuditError = _overlap_audit.OverlapAuditError
audit_manifest = _overlap_audit.audit_manifest

_HEADER = "series_id\tyear\tperiod\tvalue\tfootnote_codes\n"


def fixture_manifest(
    folder: Path,
    program: str,
    data: dict[str, str],
) -> Path:
    if program == "pc":
        metadata = {
            "pc.industry": "industry_mapping",
            "pc.product": "product_mapping",
            "pc.series": "series_metadata",
        }
        from bls_mcp.ingestion.manifest import _HEADERS
    else:
        metadata = {
            "cu.area": "area_mapping",
            "cu.item": "item_mapping",
            "cu.series": "series_metadata",
        }
        from bls_mcp.ingestion.cu_manifest import _HEADERS
    files = []
    files_with_roles = [
        *metadata.items(),
        *((name, monthly._role(program, name)) for name in data),
    ]
    for name, role in files_with_roles:
        content = (
            ("\t".join(_HEADERS[role]) + "\n")
            if name in metadata
            else _HEADER + data[name]
        )
        source = folder / name
        source.write_bytes(content.encode("utf-8"))
        raw = source.read_bytes()
        files.append(
            {
                "path": name,
                "role": role,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    manifest = folder / f"{program}-input.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "program": program,
                "files": files,
            }
        ),
        encoding="utf-8",
    )
    return manifest


@pytest.mark.parametrize(
    "program,current,historical",
    [
        ("pc", "pc.data.0.Current", "pc.data.20.ComputerProduct"),
        ("cu", "cu.data.0.Current", "cu.data.1.AllItems"),
    ],
)
def test_identical_overlap_produces_nonblocking_report(
    tmp_path, program, current, historical
):
    manifest = fixture_manifest(
        tmp_path,
        program,
        {
            historical: "SERIES\t2020\tM01\t100.000\tP\nSERIES\t2020\tM02\t101\t\n",
            current: "SERIES\t2020\tM01\t100\tP\nSERIES\t2020\tM02\t-\t\n",
        },
    )
    path, report = audit_manifest(manifest, chunk_size=1, max_open=2)
    assert report["result"] == "PASS_IDENTICAL_OVERLAP"
    assert report["overlapping_keys"] == 1
    assert report["identical_duplicate_rows"] == 1
    assert report["conflicting_keys"] == 0
    assert report["missing_rows"] == 1
    assert report["unique_keys"] == 2
    assert path.parent.name == "reports"
    assert json.loads(path.read_text())["result"] == "PASS_IDENTICAL_OVERLAP"
    assert len(report["examples"][0]["sources"]) == 2
    assert manifest.read_bytes().startswith(b"{")
    assert all(f.is_file() for f in (tmp_path / historical, tmp_path / current))


@pytest.mark.parametrize(
    "variation",
    [
        "SERIES\t2020\tM01\t102\tP\n",
        "SERIES\t2020\tM01\t100\tR\n",
    ],
)
def test_conflicting_overlap_is_explicit_and_does_not_change_manifest(
    tmp_path, variation
):
    manifest = fixture_manifest(
        tmp_path,
        "pc",
        {
            "pc.data.20.ComputerProduct": "SERIES\t2020\tM01\t100\tP\n",
            "pc.data.0.Current": variation,
        },
    )
    old_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    path, report = audit_manifest(manifest, chunk_size=1, max_open=2)
    assert report["result"] == "FAIL_CONFLICTS"
    assert report["conflicting_keys"] == 1
    assert report["overlapping_keys"] == 1
    assert report["examples"][0]["conflict"] is True
    assert report["examples"][0]["first"] != report["examples"][0]["other"]
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == old_hash
    assert json.loads(path.read_text())["result"] == "FAIL_CONFLICTS"
    with pytest.raises(SystemExit) as exc:
        monthly.main(["audit", "--manifest", str(manifest)])
    assert exc.value.code == 2


def test_audit_no_overlap_and_tampered_source_writes_failure_report(tmp_path):
    manifest = fixture_manifest(
        tmp_path,
        "cu",
        {
            "cu.data.1.AllItems": "SERIES\t2020\tM01\t10\t\n",
            "cu.data.0.Current": "SERIES\t2021\tM01\t11\t\n",
        },
    )
    report_path, report = audit_manifest(manifest, chunk_size=1, max_open=2)
    assert report["result"] == "PASS_NO_OVERLAP"
    assert report["overlapping_keys"] == 0
    report_path.unlink()
    (tmp_path / "cu.data.1.AllItems").write_text(_HEADER + "tampered")
    with pytest.raises(OverlapAuditError, match="Cannot verify"):
        audit_manifest(manifest, chunk_size=1, max_open=2)
    failure = json.loads(report_path.read_text(encoding="utf-8"))
    assert failure["result"] == "FAIL_AUDIT_ERROR"
    assert failure["phase"] == "verify_sources"
    assert "SHA-256 mismatch" in failure["error"]
    assert failure["rows_read"] == 0


def test_audit_safely_rejects_malformed_data(tmp_path):
    manifest = fixture_manifest(
        tmp_path,
        "pc",
        {
            "pc.data.0.Current": "SERIES\t2020\tM14\t22\t\n",
        },
    )
    with pytest.raises(OverlapAuditError, match="Invalid BLS observation"):
        audit_manifest(manifest)
    path = tmp_path / "reports" / "pc-input.json.overlaps.json"
    failure = json.loads(path.read_text(encoding="utf-8"))
    assert failure["result"] == "FAIL_AUDIT_ERROR"
    assert failure["phase"] == "scan_observations"
    assert failure["rows_read"] == 1


def test_audit_uses_semiannual_periods_for_cu(tmp_path):
    manifest = fixture_manifest(
        tmp_path,
        "cu",
        {
            "cu.data.0.Current": "SERIES\t2020\tS01\t22\t\n",
        },
    )
    _path, report = audit_manifest(manifest)
    assert report["unique_keys"] == 1
    assert report["result"] == "PASS_NO_OVERLAP"


def test_cu_published_five_column_area_header_passes_audit(tmp_path):
    """The previously omitted BLS area selectable column must be accepted."""
    manifest = fixture_manifest(
        tmp_path,
        "cu",
        {"cu.data.1.AllItems": "CUUR0000SA0\t2020\tM01\t250.0\t\n"},
    )
    source = tmp_path / "cu.area"
    source.write_bytes(
        b"area_code\tarea_name\tdisplay_level\tselectable\tsort_sequence\r\n"
        b"0000\tU.S. city average\t0\tT\t1\r\n"
    )
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    for item in entries["files"]:
        if item["path"] == "cu.area":
            raw = source.read_bytes()
            item["sha256"] = hashlib.sha256(raw).hexdigest()
            item["size_bytes"] = len(raw)
    manifest.write_text(json.dumps(entries), encoding="utf-8")
    path, report = audit_manifest(manifest)
    assert report["result"] == "PASS_NO_OVERLAP"
    assert json.loads(path.read_text(encoding="utf-8"))["program"] == "cu"


def test_cu_old_four_column_area_header_is_rejected_with_report(tmp_path):
    manifest = fixture_manifest(
        tmp_path,
        "cu",
        {"cu.data.1.AllItems": "CUUR0000SA0\t2020\tM01\t250.0\t\n"},
    )
    source = tmp_path / "cu.area"
    raw = b"area_code\tarea_name\tdisplay_level\tsort_sequence\n"
    source.write_bytes(raw)
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    for item in entries["files"]:
        if item["path"] == "cu.area":
            item["sha256"] = hashlib.sha256(raw).hexdigest()
            item["size_bytes"] = len(raw)
    manifest.write_text(json.dumps(entries), encoding="utf-8")
    with pytest.raises(OverlapAuditError, match="Unexpected CU area_mapping header"):
        audit_manifest(manifest)
    path = tmp_path / "reports" / "cu-input.json.overlaps.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["result"] == "FAIL_AUDIT_ERROR"
    assert report["phase"] == "verify_sources"
    assert "area_mapping header" in report["error"]


def test_audit_cli_imports_from_script_and_module(tmp_path):
    """Both documented CLI launch styles must find the sibling audit module."""
    manifest = fixture_manifest(
        tmp_path,
        "pc",
        {
            "pc.data.20.ComputerProduct": "SERIES\t2020\tM01\t100\t\n",
        },
    )
    repo_root = Path(__file__).resolve().parents[4]
    script = repo_root / "data/manual_monthly/manual_bls_monthly.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(repo_root / "src"), env.get("PYTHONPATH", "")))
    )
    invocations = (
        (str(script),),
        ("-m", "data.manual_monthly.manual_bls_monthly"),
    )
    for invocation in invocations:
        result = subprocess.run(
            [sys.executable, *invocation, "audit", "--manifest", str(manifest)],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "PASS_NO_OVERLAP" in result.stdout
