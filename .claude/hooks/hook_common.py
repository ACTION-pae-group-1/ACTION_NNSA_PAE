#!/usr/bin/env python3
"""Small shared helpers for repository-scoped Claude Code hooks."""

from __future__ import annotations

import contextlib

try:
    import fcntl
except ImportError:  # Windows fallback
    fcntl = None  # type: ignore[assignment]
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

BLOCK_EXIT = 2
JsonObject = dict[str, Any]


class HookError(ValueError):
    """Invalid hook input or an unsafe operation."""


def read_payload(*, required: bool = True) -> JsonObject:
    raw = sys.stdin.read()
    if not raw.strip():
        if required:
            raise HookError("Hook received no JSON object on standard input.")
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HookError(
            f"Invalid hook JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise HookError("Hook payload must be a JSON object.")
    return value


def tool_name(payload: Mapping[str, Any]) -> str:
    value = payload.get("tool_name")
    return value if isinstance(value, str) else ""


def tool_input(payload: Mapping[str, Any]) -> JsonObject:
    value = payload.get("tool_input")
    return dict(value) if isinstance(value, Mapping) else {}


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def env_int(name: str, default: int, *, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.environ.get(name, str(default))))
    except ValueError:
        return default


def payload_cwd(payload: Mapping[str, Any]) -> Path:
    value = payload.get("cwd")
    if isinstance(value, str) and value.strip():
        return Path(value).expanduser().resolve(strict=False)
    return Path.cwd().resolve(strict=False)


def find_project_root(start: Path) -> Path:
    current = start.resolve(strict=False)
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").is_dir():
            return candidate
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() or (
            candidate / "package.json"
        ).exists():
            return candidate
    return current


def project_root(payload: Mapping[str, Any] | None = None) -> Path:
    configured = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve(strict=False)
    return find_project_root(payload_cwd(payload or {}))


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def deny(message: str, *, label: str = "PREFLIGHT") -> int:
    print(f"[{label}] {message}", file=sys.stderr)
    return BLOCK_EXIT


def emit_context(event: str, message: str, *, limit: int = 12000) -> None:
    if len(message) > limit:
        message = message[:limit] + "\n[context truncated]"
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": message,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )
    sys.stdout.write("\n")


def emit_updated_input(
    updated: Mapping[str, Any], notes: list[str] | None = None
) -> None:
    output: JsonObject = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": dict(updated),
        }
    }
    if notes and env_bool("CLAUDE_PREFLIGHT_VERBOSE", False):
        output["hookSpecificOutput"]["additionalContext"] = (
            "Normalized before execution: " + "; ".join(dict.fromkeys(notes))
        )
    json.dump(output, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def emit_preflight_result(
    original: Mapping[str, Any],
    updated: Mapping[str, Any],
    *,
    notes: list[str] | None = None,
    advisories: list[str] | None = None,
) -> None:
    """Emit one PreToolUse result with optional normalization and policy context."""
    changed = dict(original) != dict(updated)
    context: list[str] = []
    if advisories:
        context.extend(message for message in advisories if message)
    if notes and env_bool("CLAUDE_PREFLIGHT_VERBOSE", False):
        context.append(
            "Normalized before execution: " + "; ".join(dict.fromkeys(notes))
        )
    if not changed and not context:
        return

    specific: JsonObject = {"hookEventName": "PreToolUse"}
    if changed:
        specific["updatedInput"] = dict(updated)
    if context:
        specific["additionalContext"] = "\n\n".join(dict.fromkeys(context))
    json.dump({"hookSpecificOutput": specific}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(
                value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def update_json_locked(
    path: Path,
    default: JsonObject,
    mutate: Callable[[JsonObject], None],
) -> JsonObject:
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (FileNotFoundError, OSError, json.JSONDecodeError):
                value = dict(default)
            if not isinstance(value, dict):
                value = dict(default)
            mutate(value)
            write_json_atomic(path, value)
            return value
        finally:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def safe_fingerprint(tool: str, value: Mapping[str, Any]) -> str:
    """Hash a tool call without storing file contents in runtime state."""
    redacted: JsonObject = {}
    for key, item in sorted(value.items()):
        if key in {"content", "old_string", "new_string", "source"} and isinstance(
            item, str
        ):
            redacted[key] = {
                "length": len(item),
                "sha256": hashlib.sha256(item.encode("utf-8")).hexdigest(),
            }
        else:
            redacted[key] = item
    encoded = json.dumps([tool, redacted], sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def error_text(payload: Mapping[str, Any]) -> str:
    """Collect bounded human-readable error text from a failure payload."""
    parts: list[str] = []

    def visit(value: Any, depth: int = 0) -> None:
        if depth > 4 or sum(map(len, parts)) > 16000:
            return
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, Mapping):
            for key, child in value.items():
                if str(key).lower() in {
                    "error",
                    "message",
                    "stderr",
                    "stdout",
                    "content",
                    "result",
                    "tool_response",
                }:
                    visit(child, depth + 1)
        elif isinstance(value, list):
            for child in value[:20]:
                visit(child, depth + 1)

    for key in ("error", "message", "tool_response"):
        if key in payload:
            visit(payload[key])
    return "\n".join(parts)[:16000]
