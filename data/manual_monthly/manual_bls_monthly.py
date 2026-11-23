#!/usr/bin/env python3
"""MANUAL, AT MOST MONTHLY: discover and retrieve BLS PC/WP/CU/CI flat-file inputs.

Run explicitly; never import into the application, scheduler, or MCP server.
Discovery contacts one BLS directory per program. Download uses that pinned
listing, fetches selected files serially, and emits a checksum-pinned input
manifest for the offline DuckDB snapshot builder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import ssl
import tempfile
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

BASE = "https://download.bls.gov/pub/time.series/"
DEFAULT_ROOT = Path("data/local/bls")
MIN_REQUEST_DELAY_SECONDS = 30.0
DEFAULT_MAX_DELAY_SECONDS = 31.0
MAX_INDEX_BYTES = 2_000_000
MAX_SOURCE_BYTES = 256 * 1024 * 1024
CHUNK = 1024 * 1024
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}\Z")
_MONTH = re.compile(r"\d{4}-(0[1-9]|1[0-2])\Z")
_REQUIRED = {
    "pc": ("industry_mapping", "product_mapping", "series_metadata"),
    "cu": ("area_mapping", "item_mapping", "series_metadata"),
    "wp": ("group_mapping", "item_mapping", "series_metadata"),
    "ci": (
        "owner_mapping",
        "industry_mapping",
        "occupation_mapping",
        "subcell_mapping",
        "area_mapping",
        "estimate_mapping",
        "series_metadata",
    ),
}
_ORDER = {
    "pc": (
        "industry_mapping",
        "product_mapping",
        "series_metadata",
        "historical",
        "current",
        "all_data",
    ),
    "cu": ("area_mapping", "item_mapping", "series_metadata", "historical", "current"),
    "wp": ("group_mapping", "item_mapping", "series_metadata", "historical", "current"),
    "ci": (
        "owner_mapping",
        "industry_mapping",
        "occupation_mapping",
        "subcell_mapping",
        "area_mapping",
        "estimate_mapping",
        "series_metadata",
        "all_data",
        "current",
    ),
}


class AcquisitionError(ValueError):
    """A discovery or download cannot safely proceed."""


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self.hrefs.extend(
                value for name, value in attrs if name == "href" and value
            )


def _role(program: str, name: str) -> str | None:
    if not _NAME.fullmatch(name) or ".." in name:
        return None
    if program == "pc":
        if name in {"pc.industry", "pc.industry.txt"}:
            return "industry_mapping"
        if name in {"pc.product", "pc.product.txt"}:
            return "product_mapping"
        if name == "pc.series":
            return "series_metadata"
        if name == "pc.data.0.Current":
            return "current"
        if name.startswith("pc.data.") and name.endswith(".AllData"):
            return "all_data"
        if name.startswith("pc.data."):
            return "historical"
    elif program == "cu":
        if name == "cu.area":
            return "area_mapping"
        if name == "cu.item":
            return "item_mapping"
        if name == "cu.series":
            return "series_metadata"
        if name == "cu.data.0.Current":
            return "current"
        if name.startswith("cu.data."):
            return "historical"
    elif program == "wp":
        if name == "wp.group":
            return "group_mapping"
        if name == "wp.item":
            return "item_mapping"
        if name == "wp.series":
            return "series_metadata"
        if name == "wp.data.0.Current":
            return "current"
        if name.startswith("wp.data."):
            return "historical"
    elif program == "ci":
        mapping = {
            "ci.owner": "owner_mapping",
            "ci.industry": "industry_mapping",
            "ci.occupation": "occupation_mapping",
            "ci.subcell": "subcell_mapping",
            "ci.area": "area_mapping",
            "ci.estimate": "estimate_mapping",
            "ci.series": "series_metadata",
            "ci.data.0.Current": "current",
            "ci.data.1.AllData": "all_data",
        }
        return mapping.get(name)
    return None


def directory_url(program: str) -> str:
    if program not in _REQUIRED:
        raise AcquisitionError(f"Unsupported BLS program: {program!r}")
    return BASE + program + "/"


def file_url(program: str, name: str) -> str:
    if _role(program, name) is None:
        raise AcquisitionError(f"Unsafe or unsupported {program} filename: {name!r}")
    return directory_url(program) + name


def parse_listing(html: str, program: str) -> list[dict[str, str]]:
    """Accept only direct file links within the expected official directory."""
    page = directory_url(program)
    parser = _Links()
    parser.feed(html)
    found: dict[str, str] = {}
    for href in parser.hrefs:
        raw_path = unquote(urlsplit(href).path)
        if "\\" in raw_path or any(part in {".", ".."} for part in raw_path.split("/")):
            continue
        absolute = urlsplit(urljoin(page, href))
        if (
            absolute.scheme != "https"
            or absolute.netloc != "download.bls.gov"
            or absolute.query
            or absolute.fragment
        ):
            continue
        path = unquote(absolute.path)
        if not path.startswith(f"/pub/time.series/{program}/"):
            continue
        name = path.removeprefix(f"/pub/time.series/{program}/")
        role = _role(program, name)
        if role is not None:
            found[name] = role
    if not found or not any(role == "series_metadata" for role in found.values()):
        raise AcquisitionError(
            f"No recognized {program.upper()} file listing found. "
            "BLS may have blocked the request; check the response and usage policy."
        )
    return [
        {"path": name, "role": role}
        for name, role in sorted(found.items(), key=lambda pair: pair[0])
    ]


def _folder(root: Path, month: str, program: str) -> Path:
    if not _MONTH.fullmatch(month):
        raise AcquisitionError("Month must have YYYY-MM format")
    if month != datetime.now(UTC).strftime("%Y-%m"):
        raise AcquisitionError(
            "Manual BLS acquisition is limited to the current UTC calendar month"
        )
    directory_url(program)
    return root / month / program


def _json_atomic(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".bls-", suffix=".json.tmp", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


@contextmanager
def _manual_lock(root: Path):
    """Permit at most one manual acquisition process across both programs."""
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".monthly-acquisition.lock"
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise AcquisitionError(
            f"Another manual acquisition is active (or left a lock): {lock}. "
            "Check that no other run is active before removing a stale lock."
        ) from exc
    except OSError as exc:
        raise AcquisitionError(f"Cannot create acquisition lock: {lock}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(f"pid={os.getpid()} started={datetime.now(UTC).isoformat()}\n")
        yield
    finally:
        lock.unlink(missing_ok=True)


def _request_event(
    folder: Path,
    *,
    action: str,
    url: str,
    result: str,
    http_status: int | None = None,
    bytes_received: int | None = None,
    error: str | None = None,
) -> None:
    """Keep a local, append-only request log separate from input manifests."""
    folder.mkdir(parents=True, exist_ok=True)
    record = {
        "at": datetime.now(UTC).isoformat(),
        "action": action,
        "url": url,
        "result": result,
        "http_status": http_status,
        "bytes_received": bytes_received,
        "error": error,
    }
    with (folder / "requests.jsonl").open("a", encoding="utf-8", newline="\n") as out:
        out.write(json.dumps(record, sort_keys=True) + "\n")
        out.flush()
        os.fsync(out.fileno())


def _http_status_from_error(exc: BaseException) -> int | None:
    cause = exc.__cause__
    if isinstance(cause, HTTPError):
        return cause.code
    return None


def _ensure_access_allowed(root: Path) -> None:
    marker = root / ".bls-access-paused.json"
    if marker.exists():
        raise AcquisitionError(
            f"BLS returned 403/429 during an earlier request: {marker}. "
            "Stop automated attempts and review BLS access guidance before resuming."
        )


def _pause_on_denial(root: Path, exc: BaseException) -> None:
    status = _http_status_from_error(exc)
    if status in {403, 429}:
        _json_atomic(
            root / ".bls-access-paused.json",
            {
                "at": datetime.now(UTC).isoformat(),
                "http_status": status,
                "reason": (
                    "Review BLS access guidance; never retry a block automatically"
                ),
            },
        )


def _json_read(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AcquisitionError(f"Missing or invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise AcquisitionError(f"Expected JSON object: {path}")
    return data


def _agent() -> str:
    agent = os.getenv("BLS_USER_AGENT", "").strip()
    if "@" not in agent or "\n" in agent or "\r" in agent:
        raise AcquisitionError(
            "Set BLS_USER_AGENT to a descriptive value with a contact address, "
            "for example: 'BLS-manual/1.0 (contact@example.org)'"
        )
    return agent


def _tls_context() -> ssl.SSLContext:
    # SSL_CERT_FILE allows users behind corporate HTTPS inspection to install
    # the organization CA correctly. Never disable verification.
    return ssl.create_default_context()


def _request(url: str, agent: str, timeout: float):
    request = Request(url, headers={"User-Agent": agent, "Accept": "*/*"})
    try:
        response = urlopen(request, timeout=timeout, context=_tls_context())
    except (HTTPError, URLError, OSError) as exc:
        raise AcquisitionError(f"BLS request failed ({url}): {exc}") from exc
    # Don't follow untrusted redirects to another host, even if HTTPS succeeds.
    final = urlsplit(response.geturl())
    original = urlsplit(url)
    if (
        final.scheme != "https"
        or final.netloc != "download.bls.gov"
        or final.path != original.path
        or final.query
        or final.fragment
    ):
        response.close()
        raise AcquisitionError("BLS redirected away from requested source; refusing")
    return response


def discover(root: Path, month: str, program: str, timeout: float = 40.0) -> Path:
    """Make one listing request per program per month; cache the inventory."""
    folder = _folder(root, month, program)
    destination = folder / "discovery.json"
    with _manual_lock(root):
        _ensure_access_allowed(root)
        if destination.exists():
            raise AcquisitionError(
                f"Already discovered {program} for {month}: {destination}. "
                "Use the saved inventory; do not scrape repeatedly."
            )
        url = directory_url(program)
        try:
            with _request(url, _agent(), timeout) as response:
                status = getattr(response, "status", 200)
                body = response.read(MAX_INDEX_BYTES + 1)
            if len(body) > MAX_INDEX_BYTES:
                raise AcquisitionError("BLS directory listing exceeded size limit")
            files = parse_listing(body.decode("utf-8-sig", errors="replace"), program)
        except AcquisitionError as exc:
            _pause_on_denial(root, exc)
            _request_event(
                folder,
                action="discover",
                url=url,
                result="failed",
                http_status=_http_status_from_error(exc),
                error=str(exc),
            )
            raise
        _json_atomic(
            destination,
            {
                "schema_version": 1,
                "program": program,
                "month": month,
                "discovered_at": datetime.now(UTC).isoformat(),
                "directory_url": url,
                "files": files,
            },
        )
        _request_event(
            folder,
            action="discover",
            url=url,
            result="ok",
            http_status=status,
            bytes_received=len(body),
        )
        return destination


def _inventory(folder: Path, program: str, month: str) -> list[dict[str, str]]:
    doc = _json_read(folder / "discovery.json")
    if (
        doc.get("schema_version") != 1
        or doc.get("program") != program
        or doc.get("month") != month
        or doc.get("directory_url") != directory_url(program)
    ):
        raise AcquisitionError(
            "Discovery metadata does not match requested program/month"
        )
    entries = doc.get("files")
    if not isinstance(entries, list) or not entries:
        raise AcquisitionError("Empty or malformed discovery inventory")
    seen: set[str] = set()
    validated: list[dict[str, str]] = []
    for item in entries:
        if not isinstance(item, dict):
            raise AcquisitionError("Malformed discovery entry")
        name, role = item.get("path"), item.get("role")
        if (
            not isinstance(name, str)
            or not isinstance(role, str)
            or _role(program, name) != role
        ):
            raise AcquisitionError("Tampered or invalid discovered BLS filename/role")
        if name.casefold() in seen:
            raise AcquisitionError("Duplicate filename in discovery inventory")
        seen.add(name.casefold())
        validated.append({"path": name, "role": role})
    return validated


def select_sources(
    files: list[dict[str, str]],
    program: str,
    selection: str,
    partitions: list[str],
    all_historical: bool,
    excluded: list[str] | None = None,
    notes: list[str] | None = None,
) -> list[dict[str, str]]:
    """Choose an explicit, non-overlapping set of *files*, not observation keys.

    Repeated CLI partition names are collapsed with feedback. The separate
    offline audit checks whether selected files contain overlapping observations.
    """
    excluded = excluded or []
    notes = notes if notes is not None else []
    if selection not in {"current", "historical", "both", "all-data"}:
        raise AcquisitionError(f"Invalid selection: {selection}")
    if selection == "all-data" and program not in {"pc", "ci"}:
        raise AcquisitionError("AllData is supported only for PC and CI")
    if program == "ci" and selection == "historical":
        raise AcquisitionError("CI historical coverage uses --selection all-data")
    by_name = {item["path"]: item for item in files}
    selected: list[dict[str, str]] = []
    for role in _REQUIRED[program]:
        matches = [f for f in files if f["role"] == role]
        if not matches:
            raise AcquisitionError(f"BLS directory lacks required {role}")
        exact_name = {
            "industry_mapping": "pc.industry",
            "product_mapping": "pc.product",
        }.get(role)
        selected.append(
            next((f for f in matches if f["path"] == exact_name), matches[0])
        )

    if selection == "all-data":
        if partitions or excluded or all_historical:
            raise AcquisitionError("AllData cannot be combined with other partitions")
        all_data = [f for f in files if f["role"] == "all_data"]
        if len(all_data) != 1:
            raise AcquisitionError("BLS directory lacks a unique PC AllData file")
        selected.extend(all_data)
    else:
        if selection in {"current", "both"}:
            current = [f for f in files if f["role"] == "current"]
            if len(current) != 1:
                raise AcquisitionError("BLS directory lacks a unique current partition")
            selected.extend(current)
        if selection == "current" and (partitions or all_historical or excluded):
            raise AcquisitionError(
                "Historical partitions require historical or both selection"
            )
        if all_historical and partitions:
            raise AcquisitionError(
                "Choose --all-historical OR explicit --partition arguments"
            )
        if excluded and not all_historical:
            raise AcquisitionError("--exclude-partition requires --all-historical")
        for name in excluded:
            entry = by_name.get(name)
            if entry is None or entry["role"] != "historical":
                raise AcquisitionError(f"Not a discovered historical partition: {name}")
        if selection in {"historical", "both"} and program == "ci":
            raise AcquisitionError("CI has no historical partitions; use all-data")
        if selection in {"historical", "both"}:
            if all_historical:
                excluded_names = set(excluded)
                history = [
                    f
                    for f in files
                    if f["role"] == "historical" and f["path"] not in excluded_names
                ]
                if not history:
                    raise AcquisitionError("No historical partitions remain selected")
                selected.extend(history)
                for name in sorted(excluded_names):
                    notes.append(f"Excluded historical partition: {name}")
            else:
                if not partitions:
                    raise AcquisitionError(
                        "Historical downloads require --partition NAME (repeatable) "
                        "or --all-historical."
                    )
                chosen: set[str] = set()
                for name in partitions:
                    entry = by_name.get(name)
                    if entry is None or entry["role"] != "historical":
                        raise AcquisitionError(
                            f"Not a discovered historical partition: {name}"
                        )
                    if name in chosen:
                        notes.append(f"Duplicate --partition ignored: {name}")
                        continue
                    chosen.add(name)
                    selected.append(entry)

    paths = [f["path"] for f in selected]
    if len(paths) != len(set(paths)):
        raise AcquisitionError("Duplicate filename across selected source roles")
    if any(f["role"] == "all_data" for f in files) and selection != "all-data":
        notes.append(
            "AllData intentionally excluded; it cannot be mixed with "
            "current or historical partitions"
        )
    data_count = sum(
        item["role"] in {"historical", "current", "all_data"} for item in selected
    )
    if data_count > 1:
        notes.append(
            "Selected data partitions may repeat series/year/period observations. "
            "After downloading, run the offline 'audit' command; identical "
            "duplicates can be deduplicated, but conflicts block ingestion."
        )
    roles = _ORDER[program]
    return sorted(selected, key=lambda f: (roles.index(f["role"]), f["path"]))


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
            count += len(chunk)
    return digest.hexdigest(), count


def _fetch_one(
    folder: Path, program: str, source: dict[str, str], agent: str, timeout: float
) -> tuple[dict[str, object], int]:
    name = source["path"]
    dest = folder / name
    if dest.exists():
        raise AcquisitionError(
            f"Unreceipted local file exists; will not overwrite: {dest}"
        )
    url = file_url(program, name)
    temp: Path | None = None
    try:
        with _request(url, agent, timeout) as response:
            http_status = getattr(response, "status", 200)
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" in content_type:
                raise AcquisitionError(f"BLS returned HTML, not data: {name}")
            fd, filename = tempfile.mkstemp(
                prefix=f".{name}.", suffix=".part", dir=folder
            )
            temp = Path(filename)
            digest = hashlib.sha256()
            size = 0
            with os.fdopen(fd, "wb") as stream:
                first = True
                while chunk := response.read(CHUNK):
                    if first and chunk.lstrip().lower().startswith(
                        (b"<html", b"<!doctype html")
                    ):
                        raise AcquisitionError(
                            f"BLS returned an HTML block page: {name}"
                        )
                    first = False
                    size += len(chunk)
                    if size > MAX_SOURCE_BYTES:
                        raise AcquisitionError(
                            f"Source exceeds {MAX_SOURCE_BYTES} bytes: {name}"
                        )
                    stream.write(chunk)
                    digest.update(chunk)
                stream.flush()
                os.fsync(stream.fileno())
            if size == 0:
                raise AcquisitionError(f"Empty BLS response: {name}")
            content_length = response.headers.get("Content-Length")
            if (
                content_length
                and content_length.isdecimal()
                and int(content_length) != size
            ):
                raise AcquisitionError(f"Incomplete BLS download: {name}")
            receipt: dict[str, object] = {
                **source,
                "sha256": digest.hexdigest(),
                "size_bytes": size,
                "source_url": url,
            }
            if program != "wp":
                for header, field in (
                    ("ETag", "etag"),
                    ("Last-Modified", "last_modified"),
                ):
                    value = response.headers.get(header)
                    if value:
                        receipt[field] = value
        os.replace(temp, dest)
        temp = None
        return receipt, http_status
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def _load_receipts(
    folder: Path, program: str, month: str, discovered: list[dict[str, str]]
) -> dict[str, dict[str, object]]:
    receipts_file = folder / "download-receipts.json"
    if not receipts_file.exists():
        return {}
    old = _json_read(receipts_file)
    if (
        old.get("program") != program
        or old.get("month") != month
        or not isinstance(old.get("files"), list)
    ):
        raise AcquisitionError("Invalid or mismatched download receipts")
    known = {item["path"]: item["role"] for item in discovered}
    receipts: dict[str, dict[str, object]] = {}
    for item in old["files"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise AcquisitionError("Malformed download receipt")
        name = item["path"]
        if (
            name in receipts
            or known.get(name) != item.get("role")
            or not isinstance(item.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is None
            or type(item.get("size_bytes")) is not int
            or item["size_bytes"] < 0
            or item.get("source_url") != file_url(program, name)
        ):
            raise AcquisitionError(
                f"Invalid, duplicate, or unrecognized receipt: {name}"
            )
        receipts[name] = item
    return receipts


def _verify_cached(folder: Path, name: str, receipt: dict[str, object]) -> None:
    local = folder / name
    if not local.is_file():
        raise AcquisitionError(f"Previously downloaded source is missing: {name}")
    try:
        digest, size = _hash_file(local)
    except OSError as exc:
        raise AcquisitionError(f"Cannot read cached source: {name}") from exc
    if digest != receipt["sha256"] or size != receipt["size_bytes"]:
        raise AcquisitionError(f"Cached source hash/size mismatch: {name}")


def _manifest_for_selection(
    folder: Path,
    program: str,
    sources: list[dict[str, str]],
    receipts: dict[str, dict[str, object]],
) -> tuple[Path, bool]:
    """Reuse an immutable matching manifest or choose a distinct new filename."""
    expected = [receipts[source["path"]] for source in sources]
    original = folder / f"{program}-input.json"
    canonical_paths = [entry["path"] for entry in expected]
    manifests = [original, *sorted(folder.glob(f"{program}-input-*.json"))]
    for path in manifests:
        if not path.exists():
            continue
        doc = _json_read(path)
        if (
            doc.get("schema_version") != 1
            or doc.get("program") != program
            or not isinstance(doc.get("files"), list)
        ):
            raise AcquisitionError(f"Invalid existing input manifest: {path}")
        entries = doc["files"]
        if any(
            not isinstance(row, dict) or not isinstance(row.get("path"), str)
            for row in entries
        ):
            raise AcquisitionError(
                f"Invalid entries in existing input manifest: {path}"
            )
        names = [row["path"] for row in entries]
        if len(names) != len(set(names)):
            raise AcquisitionError(
                f"Invalid entries in existing input manifest: {path}"
            )
        for item in entries:
            if item.get("path") not in receipts or item != receipts[item["path"]]:
                raise AcquisitionError(
                    "Existing input manifest differs from recorded source receipts: "
                    f"{path}"
                )
        if names == canonical_paths:
            return path, True

    if not original.exists():
        return original, False
    fingerprint = hashlib.sha256(
        json.dumps(canonical_paths, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    result = folder / f"{program}-input-{fingerprint}.json"
    if result.exists():
        raise AcquisitionError(f"Input manifest name collision: {result}")
    return result, False


def plan(
    root: Path,
    month: str,
    program: str,
    selection: str,
    partitions: list[str],
    all_historical: bool,
    min_delay: float = MIN_REQUEST_DELAY_SECONDS,
    max_delay: float = DEFAULT_MAX_DELAY_SECONDS,
    excluded: list[str] | None = None,
    notes: list[str] | None = None,
) -> list[dict[str, str]]:
    """Inspect the cached selection and reusable files without network requests."""
    _validate_delays(min_delay, max_delay)
    folder = _folder(root, month, program)
    discovered = _inventory(folder, program, month)
    files = select_sources(
        discovered, program, selection, partitions, all_historical, excluded, notes
    )
    receipts = _load_receipts(folder, program, month, discovered)
    # Detect corrupt files *before* a long download is planned.
    for source in files:
        name = source["path"]
        if name in receipts:
            _verify_cached(folder, name, receipts[name])
        elif (folder / name).exists():
            raise AcquisitionError(
                f"Unreceipted source already exists: {name}. "
                "Use the local-only manifest tool; refusing to overwrite it."
            )
    return files


def _validate_delays(min_delay: float, max_delay: float) -> None:
    if (
        not math.isfinite(min_delay)
        or not math.isfinite(max_delay)
        or min_delay < MIN_REQUEST_DELAY_SECONDS
        or max_delay < min_delay
    ):
        raise AcquisitionError(
            f"Use finite delays with {MIN_REQUEST_DELAY_SECONDS:g} <= "
            "--min-delay <= --max-delay (seconds)"
        )


def download(
    root: Path,
    month: str,
    program: str,
    selection: str,
    partitions: list[str],
    all_historical: bool,
    timeout: float = 45.0,
    min_delay: float = MIN_REQUEST_DELAY_SECONDS,
    max_delay: float = DEFAULT_MAX_DELAY_SECONDS,
    excluded: list[str] | None = None,
    notes: list[str] | None = None,
) -> Path:
    """Safely extend a monthly cache, without re-fetching or replacing files."""
    _validate_delays(min_delay, max_delay)
    folder = _folder(root, month, program)
    with _manual_lock(root):
        _ensure_access_allowed(root)
        return _download_locked(
            folder,
            program,
            month,
            selection,
            partitions,
            all_historical,
            timeout,
            min_delay,
            max_delay,
            excluded,
            notes,
        )


def _download_locked(
    folder: Path,
    program: str,
    month: str,
    selection: str,
    partitions: list[str],
    all_historical: bool,
    timeout: float,
    min_delay: float,
    max_delay: float,
    excluded: list[str] | None,
    notes: list[str] | None,
) -> Path:
    discovered = _inventory(folder, program, month)
    files = select_sources(
        discovered, program, selection, partitions, all_historical, excluded, notes
    )
    existing = _load_receipts(folder, program, month, discovered)
    receipts_file = folder / "download-receipts.json"
    folder.mkdir(parents=True, exist_ok=True)

    # Check every selected reusable file before any new network requests.
    for source in files:
        name = source["path"]
        if name in existing:
            _verify_cached(folder, name, existing[name])
        elif (folder / name).exists():
            raise AcquisitionError(
                f"Unreceipted local file exists; will not overwrite: {folder / name}"
            )

    if notes:
        for note in notes:
            print(f"NOTE: {note}", flush=True)
    to_download = [source for source in files if source["path"] not in existing]
    reused = len(files) - len(to_download)
    print(
        f"{program.upper()} selection: {len(files)} files, "
        f"{reused} verified/reused, {len(to_download)} new download(s)",
        flush=True,
    )
    # Loading .env is only necessary if new requests will be made.
    agent = _agent() if to_download else None
    for source in files:
        name = source["path"]
        if name in existing:
            print(f"Reusing verified file: {name}", flush=True)
            continue
        pause = random.uniform(min_delay, max_delay)
        print(f"Waiting {pause:.1f}s before {name}", flush=True)
        time.sleep(pause)
        url = file_url(program, name)
        assert agent is not None
        try:
            receipt, http_status = _fetch_one(folder, program, source, agent, timeout)
        except AcquisitionError as exc:
            _pause_on_denial(folder.parent.parent, exc)
            _request_event(
                folder,
                action="download",
                url=url,
                result="failed",
                http_status=_http_status_from_error(exc),
                error=str(exc),
            )
            raise
        existing[name] = receipt
        _json_atomic(
            receipts_file,
            {
                "program": program,
                "month": month,
                "files": [existing[key] for key in sorted(existing)],
            },
        )
        _request_event(
            folder,
            action="download",
            url=url,
            result="ok",
            http_status=http_status,
            bytes_received=receipt["size_bytes"],
        )
        print(f"Downloaded: {name} ({receipt['size_bytes']} bytes)", flush=True)

    # A source set that grows later in the month gets a NEW immutable manifest.
    # The earlier manifest remains pinned for any build that already used it.
    manifest_path, already_exists = _manifest_for_selection(
        folder, program, files, existing
    )
    for source in files:
        _verify_cached(folder, source["path"], existing[source["path"]])
    if already_exists:
        print(f"Existing matching manifest reused: {manifest_path}", flush=True)
    else:
        _json_atomic(
            manifest_path,
            {
                "schema_version": 1,
                "program": program,
                "files": [existing[source["path"]] for source in files],
            },
        )
        print(f"New immutable input manifest: {manifest_path}", flush=True)
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--month", default=datetime.now(UTC).strftime("%Y-%m"))
    actions = parser.add_subparsers(dest="action", required=True)
    discover_cmd = actions.add_parser(
        "discover", help="One BLS directory listing per program/month"
    )
    discover_cmd.add_argument(
        "--program", required=True, choices=("pc", "wp", "cu", "ci")
    )

    def selection_args(command: argparse.ArgumentParser) -> None:
        command.add_argument(
            "--program", required=True, choices=("pc", "wp", "cu", "ci")
        )
        command.add_argument(
            "--selection",
            choices=("current", "historical", "both", "all-data"),
            default="current",
        )
        command.add_argument("--partition", action="append", default=[], metavar="NAME")
        command.add_argument(
            "--partition-file",
            type=Path,
            default=None,
            help="Offline JSON list of exact historical filenames; "
            "no wildcard expansion",
        )
        command.add_argument("--all-historical", action="store_true")
        command.add_argument(
            "--exclude-partition",
            action="append",
            default=[],
            metavar="NAME",
            help="With --all-historical, omit explicitly named historical partitions",
        )

    plan_cmd = actions.add_parser(
        "plan", help="Print cached selection, reuse and overlaps; no network"
    )
    selection_args(plan_cmd)
    download_cmd = actions.add_parser(
        "download", help="Serially download only missing files from saved listing"
    )
    selection_args(download_cmd)
    download_cmd.add_argument(
        "--min-delay",
        type=float,
        default=MIN_REQUEST_DELAY_SECONDS,
        help="Minimum seconds before every request (at least 30)",
    )
    download_cmd.add_argument(
        "--max-delay",
        type=float,
        default=DEFAULT_MAX_DELAY_SECONDS,
        help="Maximum seconds before every request (default 31)",
    )
    download_cmd.add_argument("--timeout", type=float, default=31.0)

    audit_cmd = actions.add_parser(
        "audit", help="Offline audit of overlapping observations in a pinned manifest"
    )
    audit_cmd.add_argument("--manifest", type=Path, required=True)
    audit_cmd.add_argument(
        "--scratch-dir",
        type=Path,
        default=None,
        help="Directory for temporary external-sort files (must have free disk space)",
    )
    args = parser.parse_args(argv)
    try:
        if args.action == "discover":
            path = discover(args.root, args.month, args.program)
            print(f"Discovered official {args.program.upper()} filenames: {path}")
        elif args.action in {"plan", "download"}:
            notes: list[str] = []
            if args.partition_file is not None:
                raw = json.loads(args.partition_file.read_text(encoding="utf-8"))
                if (
                    not isinstance(raw, dict)
                    or raw.get("program") != args.program
                    or not isinstance(raw.get("partitions"), list)
                    or not all(isinstance(n, str) for n in raw["partitions"])
                ):
                    raise AcquisitionError(
                        "Partition file must contain program and a list of exact "
                        "partition filenames"
                    )
                args.partition.extend(raw["partitions"])
            if args.program == "ci" and args.selection == "historical":
                raise AcquisitionError("CI history is --selection all-data")
            if args.action == "plan":
                files = plan(
                    args.root,
                    args.month,
                    args.program,
                    args.selection,
                    args.partition,
                    args.all_historical,
                    excluded=args.exclude_partition,
                    notes=notes,
                )
                folder = _folder(args.root, args.month, args.program)
                inventory_files = _inventory(folder, args.program, args.month)
                existing = _load_receipts(
                    folder, args.program, args.month, inventory_files
                )
                count_new = 0
                for file in files:
                    reused = file["path"] in existing
                    count_new += not reused
                    label = "REUSE (checksum verified)" if reused else "DOWNLOAD"
                    print(f"{file['role']:18s} {file['path']} [{label}]")
                print(
                    f"{len(files)} files: {len(files) - count_new} reused, "
                    f"{count_new} network requests. Default pause budget "
                    f"{count_new * MIN_REQUEST_DELAY_SECONDS / 60:.1f}-"
                    f"{count_new * DEFAULT_MAX_DELAY_SECONDS / 60:.1f} minutes "
                    "plus transfer time. No files downloaded."
                )
            else:
                path = download(
                    args.root,
                    args.month,
                    args.program,
                    args.selection,
                    args.partition,
                    args.all_historical,
                    timeout=args.timeout,
                    min_delay=args.min_delay,
                    max_delay=args.max_delay,
                    excluded=args.exclude_partition,
                    notes=notes,
                )
                print(f"Snapshot input manifest: {path}")
                print(
                    "Run offline overlap audit before building: "
                    f"uv run --locked python {__file__} audit --manifest {path}"
                )
            if args.action == "plan":
                for note in notes:
                    print(f"NOTE: {note}")
        elif args.action == "audit":
            # Direct-file invocation adds this script's folder to sys.path;
            # package invocation (-m) uses the repository root instead.
            if __package__:
                from .overlap_audit import audit_manifest
            else:
                from overlap_audit import audit_manifest

            try:
                report_path, report = audit_manifest(
                    args.manifest, scratch_dir=args.scratch_dir
                )
            except ValueError as exc:
                report_path = (
                    Path(args.manifest).parent
                    / "reports"
                    / f"{Path(args.manifest).name}.overlaps.json"
                )
                details = (
                    f"; diagnostic report: {report_path}"
                    if report_path.is_file()
                    else ""
                )
                raise AcquisitionError(f"{exc}{details}") from exc
            print(
                f"Overlap audit: {report['result']}; "
                f"{report['overlapping_keys']} repeated observation keys, "
                f"{report['identical_duplicate_rows']} identical repeated rows, "
                f"{report['conflicting_keys']} conflicting keys; "
                f"{report['missing_rows']} missing-value rows ignored."
            )
            print(f"Report: {report_path}")
            for example in report["examples"]:
                print(
                    f"  {'CONFLICT' if example['conflict'] else 'IDENTICAL'}: "
                    f"{example['series_id']} {example['year']} "
                    f"{example['period']} in {', '.join(example['sources'])}"
                )
                if example["conflict"]:
                    print(f"    {example['first']} versus {example['other']}")
            if report["result"] == "EMPTY_DATA":
                raise AcquisitionError(
                    "No BLS observation rows available in this selection"
                )
            if report["conflicting_keys"]:
                raise AcquisitionError(
                    "Conflicting observations detected. DuckDB ingestion will reject "
                    "this selection. Review the report and select different "
                    "partitions; raw files and manifests were not modified."
                )
        else:
            raise AssertionError("Unknown CLI action")
    except AcquisitionError as exc:
        parser.exit(2, f"BLS manual acquisition: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
