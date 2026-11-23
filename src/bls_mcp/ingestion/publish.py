"""Versioned DuckDB publication and atomic active-snapshot registry.

Publication copies an independently validated READY candidate into a new
staging file, marks only that copy PUBLISHED, checkpoints and closes DuckDB,
then renames it into the immutable snapshot directory. No existing snapshot
is rewritten or deleted. Activation and rollback change only the registry.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb

from bls_mcp.ingestion.lifecycle import (
    SnapshotLifecycleError,
    _integrity,
    _sync_directory,
    _transition,
    sha256_file,
    validation_report_path,
    write_json_atomic,
)
from bls_mcp.storage.connection import snapshot_reader
from bls_mcp.storage.models import SnapshotState, ValidationStatus
from bls_mcp.storage.schema import SCHEMA_VERSION
from bls_mcp.storage.snapshots import read_snapshot_info

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection

REGISTRY_SCHEMA_VERSION = 1
_REGISTRY_NAME = "active-snapshot.json"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
_HASH = re.compile(r"[a-f0-9]{64}\Z")


class PublicationError(SnapshotLifecycleError):
    """Publication or registry transition was refused without changing active data."""


@dataclass(frozen=True, slots=True)
class PublishedSnapshot:
    snapshot_id: str
    filename: str
    validation_filename: str
    published_at: str
    sha256: str


@dataclass(frozen=True, slots=True)
class ActivationEvent:
    from_snapshot_id: str | None
    to_snapshot_id: str
    activated_at: str
    operation: str


@dataclass(frozen=True, slots=True)
class SnapshotRegistry:
    schema_version: int
    active_snapshot_id: str | None
    snapshots: tuple[PublishedSnapshot, ...]
    history: tuple[ActivationEvent, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _name(snapshot_id: str) -> str:
    if not isinstance(snapshot_id, str) or not _ID.fullmatch(snapshot_id):
        raise PublicationError("Invalid or unsafe snapshot identifier")
    return f"bls-{snapshot_id}.duckdb"


def _load_registry(root: Path) -> SnapshotRegistry:
    path = root / _REGISTRY_NAME
    if not path.exists():
        return SnapshotRegistry(REGISTRY_SCHEMA_VERSION, None, (), ())
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or set(document) != {
            "schema_version",
            "active_snapshot_id",
            "snapshots",
            "history",
        }:
            raise ValueError("unexpected registry fields")
        if document["schema_version"] != REGISTRY_SCHEMA_VERSION:
            raise ValueError("unsupported registry format")
        entries = tuple(PublishedSnapshot(**value) for value in document["snapshots"])
        events = tuple(ActivationEvent(**value) for value in document["history"])
        active = document["active_snapshot_id"]
        seen: set[str] = set()
        for entry in entries:
            if (
                entry.snapshot_id in seen
                or entry.filename != _name(entry.snapshot_id)
                or entry.validation_filename != entry.filename + ".validation.json"
                or not isinstance(entry.sha256, str)
                or not _HASH.fullmatch(entry.sha256)
                or not isinstance(entry.published_at, str)
            ):
                raise ValueError("unsafe or duplicate registry entry")
            seen.add(entry.snapshot_id)
        if active is not None and active not in seen:
            raise ValueError("active snapshot is not registered")
        for event in events:
            if (
                event.to_snapshot_id not in seen
                or (
                    event.from_snapshot_id is not None
                    and event.from_snapshot_id not in seen
                )
                or event.operation not in ("activate", "rollback")
                or not isinstance(event.activated_at, str)
            ):
                raise ValueError("invalid registry activation history")
        return SnapshotRegistry(REGISTRY_SCHEMA_VERSION, active, entries, events)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise PublicationError(f"Invalid snapshot registry: {path}") from exc


def read_registry(registry_dir: str | Path) -> SnapshotRegistry:
    """List registered immutable snapshots, without altering any files."""
    return _load_registry(Path(registry_dir).resolve())


@contextmanager
def _registry_lock(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".publication.lock"
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise PublicationError(
            f"Publication lock exists: {lock}. Inspect the owning process; "
            "do not remove an active lock"
        ) from exc
    try:
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(str(os.getpid()) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        yield
    finally:
        lock.unlink(missing_ok=True)


def _write_registry(root: Path, registry: SnapshotRegistry) -> None:
    write_json_atomic(root / _REGISTRY_NAME, registry.as_dict())


def _verify_registered(root: Path, entry: PublishedSnapshot) -> Path:
    path = root / entry.filename
    if not path.is_file():
        raise PublicationError(f"Registered snapshot is missing: {path}")
    if sha256_file(path) != entry.sha256:
        raise PublicationError(
            f"Published snapshot checksum changed: {entry.snapshot_id}"
        )
    with snapshot_reader(path) as conn:
        info = read_snapshot_info(conn)
        if (
            info.snapshot_id != entry.snapshot_id
            or info.validation_status is not ValidationStatus.PASSED
        ):
            raise PublicationError(
                "Published snapshot metadata does not match registry"
            )
    return path


def current_snapshot_path(registry_dir: str | Path) -> Path:
    """Resolve the active immutable file for a new BLSStore at startup.

    Registry reads do not automatically reload an existing store. For routine
    startup this checks metadata/state, not the potentially huge full-file hash;
    activation and rollback verify the registered hash before pointer updates.
    """
    root = Path(registry_dir).resolve()
    registry = _load_registry(root)
    active = registry.active_snapshot_id
    if active is None:
        raise PublicationError("No active BLS snapshot; activate one first")
    entry = next(item for item in registry.snapshots if item.snapshot_id == active)
    path = root / entry.filename
    if not path.is_file():
        raise PublicationError(f"Active snapshot missing: {path}")
    with snapshot_reader(path) as conn:
        info = read_snapshot_info(conn)
        if (
            info.snapshot_id != active
            or info.validation_status is not ValidationStatus.PASSED
        ):
            raise PublicationError("Active snapshot metadata does not match registry")
    return path


def _read_ready(
    conn: DuckDBPyConnection, snapshot_id: str, expected_counts: dict[str, int]
) -> None:
    info = read_snapshot_info(conn)
    if (
        info.snapshot_id != snapshot_id
        or info.lifecycle_state is not SnapshotState.READY
        or info.validation_status is not ValidationStatus.PASSED
    ):
        raise PublicationError("Candidate must be READY, PASSED, and match the report")
    if _integrity(conn, info.programs) != expected_counts:
        raise PublicationError("Candidate contents differ from the validation report")


def _read_report(path: Path) -> tuple[str, dict[str, int], str]:
    report_path = validation_report_path(path)
    try:
        doc = json.loads(report_path.read_text(encoding="utf-8"))
        digest = doc["candidate_sha256"]
        counts = doc["counts"]
        snapshot_id = doc["snapshot_id"]
        if (
            doc["passed"] is not True
            or doc.get("schema_version") != SCHEMA_VERSION
            or not isinstance(snapshot_id, str)
            or not isinstance(digest, str)
            or not _HASH.fullmatch(digest)
            or not isinstance(counts, dict)
            or not counts
            or any(
                not isinstance(k, str) or type(v) is not int for k, v in counts.items()
            )
        ):
            raise ValueError("incomplete or failed validation report")
        return snapshot_id, counts, digest
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise PublicationError(
            f"Missing or invalid READY validation report: {report_path}"
        ) from exc


def _copy_checked(source: Path, stage: Path, expected_hash: str) -> None:
    digest = hashlib.sha256()
    with source.open("rb") as reader, stage.open("xb") as writer:
        for block in iter(lambda: reader.read(1024 * 1024), b""):
            digest.update(block)
            writer.write(block)
        writer.flush()
        os.fsync(writer.fileno())
    if digest.hexdigest() != expected_hash:
        raise PublicationError("Candidate changed after validation")


def publish_candidate(
    candidate_path: str | Path, registry_dir: str | Path
) -> PublishedSnapshot:
    """Publish without activation; the active pointer is never changed here.

    The copy is checkpointed and closed before being renamed into its final
    versioned filename. Registry changes are a separate atomic operation.
    Any unexpected failure leaves the previous active snapshot untouched.
    """
    candidate = Path(candidate_path)
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    snapshot_id, counts, ready_hash = _read_report(candidate)
    filename = _name(snapshot_id)
    root = Path(registry_dir).resolve()
    with _registry_lock(root):
        registry = _load_registry(root)
        if any(item.snapshot_id == snapshot_id for item in registry.snapshots):
            raise PublicationError(f"Snapshot already registered: {snapshot_id}")
        destination = root / filename
        report_dest = root / (filename + ".validation.json")
        if destination.exists() or report_dest.exists():
            raise PublicationError(
                f"Snapshot publication files already exist: {filename}"
            )
        with snapshot_reader(candidate, require_published=False) as conn:
            _read_ready(conn, snapshot_id, counts)
        if Path(str(candidate) + ".wal").exists():
            raise PublicationError("Candidate still has an uncheckpointed DuckDB WAL")
        stage = root / f".stage-{uuid.uuid4().hex}.duckdb"
        try:
            _copy_checked(candidate, stage, ready_hash)
            with closing(duckdb.connect(str(stage), read_only=False)) as conn:
                _read_ready(conn, snapshot_id, counts)
                _transition(conn, SnapshotState.PUBLISHED, ValidationStatus.PASSED)
                conn.execute("CHECKPOINT")
            with snapshot_reader(stage) as conn:
                info = read_snapshot_info(conn)
                if (
                    info.snapshot_id != snapshot_id
                    or _integrity(conn, info.programs) != counts
                ):
                    raise PublicationError(
                        "Published copy failed read-only verification"
                    )
            if Path(str(stage) + ".wal").exists():
                raise PublicationError("Staging copy still has an uncheckpointed WAL")
            digest = sha256_file(stage)
            published_at = datetime.now(UTC).isoformat()
            entry = PublishedSnapshot(
                snapshot_id, filename, report_dest.name, published_at, digest
            )
            # The report remains immutable beside the published database.
            report = json.loads(
                validation_report_path(candidate).read_text(encoding="utf-8")
            )
            if (
                report.get("snapshot_id") != snapshot_id
                or report.get("candidate_sha256") != ready_hash
                or report.get("counts") != counts
                or report.get("passed") is not True
                or report.get("schema_version") != SCHEMA_VERSION
            ):
                raise PublicationError("READY report changed during publication")
            write_json_atomic(report_dest, report)
            os.rename(stage, destination)  # Same volume, no overwrite under lock.
            _sync_directory(root)
            updated = SnapshotRegistry(
                REGISTRY_SCHEMA_VERSION,
                registry.active_snapshot_id,
                (*registry.snapshots, entry),
                registry.history,
            )
            _write_registry(root, updated)
            return entry
        finally:
            stage.unlink(missing_ok=True)


def _activate_locked(
    root: Path, registry: SnapshotRegistry, snapshot_id: str, operation: str
) -> Path:
    entry = next((s for s in registry.snapshots if s.snapshot_id == snapshot_id), None)
    if entry is None:
        raise PublicationError(f"Unknown published snapshot: {snapshot_id}")
    if registry.active_snapshot_id == snapshot_id:
        raise PublicationError(f"Snapshot is already active: {snapshot_id}")
    path = _verify_registered(root, entry)
    event = ActivationEvent(
        registry.active_snapshot_id,
        snapshot_id,
        datetime.now(UTC).isoformat(),
        operation,
    )
    _write_registry(
        root,
        SnapshotRegistry(
            REGISTRY_SCHEMA_VERSION,
            snapshot_id,
            registry.snapshots,
            (*registry.history, event),
        ),
    )
    return path


def activate_snapshot(registry_dir: str | Path, snapshot_id: str) -> Path:
    """Atomically change the active pointer; never mutate DuckDB data files."""
    root = Path(registry_dir).resolve()
    _name(snapshot_id)
    with _registry_lock(root):
        return _activate_locked(root, _load_registry(root), snapshot_id, "activate")


def rollback_snapshot(registry_dir: str | Path) -> Path:
    """Undo the most recent activation; retain every published snapshot."""
    root = Path(registry_dir).resolve()
    with _registry_lock(root):
        registry = _load_registry(root)
        if not registry.history:
            raise PublicationError("No activation history to roll back")
        latest = registry.history[-1]
        if (
            latest.to_snapshot_id != registry.active_snapshot_id
            or latest.from_snapshot_id is None
        ):
            raise PublicationError("No previous active snapshot available for rollback")
        return _activate_locked(root, registry, latest.from_snapshot_id, "rollback")
