#!/usr/bin/env python3
"""Normalize common local-model tool mistakes before execution.

This is the only active hook that mutates tool input. It repairs only
unambiguous, intent-preserving mistakes and blocks unsafe or ambiguous calls.
"""

from __future__ import annotations

import ast
import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from hook_common import (
    HookError,
    deny,
    emit_preflight_result,
    env_bool,
    env_int,
    is_within,
    payload_cwd,
    project_root,
    read_payload,
    tool_name,
)

SUPPORTED_TOOLS = {
    "Read",
    "Edit",
    "Write",
    "Glob",
    "Grep",
    "NotebookEdit",
    "TodoWrite",
    "Bash",
}
PATH_ALIASES = (
    "path",
    "full_path",
    "fullPath",
    "filePath",
    "filepath",
    "filename",
    "file",
    "target_path",
    "target",
)
CONTENT_ALIASES = ("contents", "text", "body", "source")
OLD_ALIASES = ("old", "old_text", "search", "search_text")
NEW_ALIASES = ("new", "new_text", "replacement", "replace_with")
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
}
TEXT_EXTENSIONS = {
    ".py",
    ".pyi",
    ".json",
    ".toml",
    ".sh",
    ".bash",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".vue",
    ".css",
    ".scss",
    ".html",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
}
PYTHON_TOOLS = {
    "pytest",
    "py.test",
    "ruff",
    "mypy",
    "black",
    "isort",
    "flake8",
    "pylint",
    "bandit",
}
NETWORK_PROGRAMS = {
    "curl",
    "wget",
    "ftp",
    "lftp",
    "scp",
    "sftp",
    "ssh",
    "rsync",
    "nc",
    "ncat",
    "netcat",
    "telnet",
}
DEFAULT_ALLOWED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "host.docker.internal",
    "gitlab.aws.juce.nnsa.doe.gov",
}


class PreflightError(ValueError):
    """The request cannot be repaired safely."""


def take_alias(data: dict[str, Any], canonical: str, aliases: tuple[str, ...]) -> Any:
    value = data.get(canonical)
    if value is not None:
        return value
    for alias in aliases:
        if alias in data:
            return data[alias]
    return None


def clean_path_text(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise PreflightError("A non-empty file path is required.")
    value = raw.strip().strip("\"'")
    if "\x00" in value:
        raise PreflightError("File paths may not contain a NUL byte.")
    if value.startswith("file://"):
        parsed = urlsplit(value)
        value = unquote(parsed.path)
    return value


def resolve_project_path(
    raw: Any, payload: Mapping[str, Any], *, allow_root_rebase: bool = True
) -> Path:
    text = clean_path_text(raw)
    root = project_root(payload)
    candidate = Path(text).expanduser()

    if candidate.is_absolute():
        resolved = candidate.resolve(strict=False)
        if is_within(resolved, root):
            return resolved

        # Common local-model error: /.claude/... or /backend/... intended as
        # project-root-relative. Rebase only recognizable project top-levels.
        if allow_root_rebase and env_bool("CLAUDE_REBASE_ROOT_RELATIVE_PATHS", True):
            parts = candidate.parts[1:]
            if parts:
                top = parts[0]
                project_top = root / top
                system_top_exists = (Path("/") / top).exists()
                should_rebase = top == ".claude" or (
                    project_top.exists() and not system_top_exists
                )
                if should_rebase:
                    rebased = (root.joinpath(*parts)).resolve(strict=False)
                    if is_within(rebased, root):
                        return rebased

        # Stale /workspaces/<old-project>/... path: preserve only the suffix
        # after the old project directory.
        parts = candidate.parts
        if len(parts) >= 4 and parts[1] == "workspaces":
            rebased = root.joinpath(*parts[3:]).resolve(strict=False)
            if is_within(rebased, root):
                return rebased
        raise PreflightError(f"Resolved path is outside project root: {resolved}")

    cwd = payload_cwd(payload)
    base = cwd if is_within(cwd, root) else root
    resolved = (base / candidate).resolve(strict=False)
    if not is_within(resolved, root):
        raise PreflightError(f"Resolved path is outside project root: {resolved}")
    return resolved


def iter_files(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        base = Path(current)
        for name in files:
            yield base / name


def unique_prefix_file(raw: str, root: Path) -> Path | None:
    name = Path(raw).name.casefold()
    if not name:
        return None
    matches: list[Path] = []
    for path in iter_files(root):
        if path.name.casefold().startswith(name):
            matches.append(path.resolve(strict=False))
            if len(matches) > 1:
                return None
    return matches[0] if len(matches) == 1 else None


def strip_line_suffix(raw: str) -> tuple[str, int | None, int | None]:
    patterns = (
        r"^(.*)#L(\d+)(?:-L?(\d+))?$",
        r"^(.*):(\d+)(?:-(\d+))?$",
    )
    for pattern in patterns:
        match = re.match(pattern, raw)
        if match and match.group(1):
            start = int(match.group(2))
            end = int(match.group(3) or start)
            return match.group(1), start, max(start, end)
    return raw, None, None


def normalize_file_path(
    data: dict[str, Any],
    payload: Mapping[str, Any],
    notes: list[str],
    *,
    canonical: str = "file_path",
    aliases: tuple[str, ...] = PATH_ALIASES,
    must_exist: bool = False,
    allow_prefix: bool = False,
) -> Path:
    raw = take_alias(data, canonical, aliases)
    if raw is None:
        raise PreflightError(f"{tool_name(payload)} requires {canonical}.")
    text = clean_path_text(raw)
    line_start = line_end = None
    if canonical == "file_path" and tool_name(payload) == "Read":
        text, line_start, line_end = strip_line_suffix(text)

    path = resolve_project_path(text, payload)
    if must_exist and not path.exists() and allow_prefix:
        found = unique_prefix_file(text, project_root(payload))
        if found is not None:
            path = found
            notes.append("expanded a uniquely matching partial file name")
    if must_exist and not path.exists():
        raise PreflightError(f"Target does not exist: {path}")
    if must_exist and not path.is_file():
        raise PreflightError(f"Target is not a file: {path}")

    for key in (canonical, *aliases):
        data.pop(key, None)
    data[canonical] = str(path)
    if str(raw) != str(path):
        notes.append(f"normalized {canonical} to an absolute project path")
    if line_start is not None:
        data.setdefault("offset", line_start)
        data.setdefault("limit", line_end - line_start + 1)
        notes.append("converted a line-suffixed path to Read offset and limit")
    return path


def unwrap_fence(text: str) -> str:
    match = re.fullmatch(r"\s*```[^\n]*\n(.*?)\n```\s*", text, re.DOTALL)
    return match.group(1) if match else text


def validate_source(path: Path, source: str) -> str | None:
    suffix = path.suffix.lower()
    try:
        if suffix in {".py", ".pyi"}:
            ast.parse(source, filename=str(path), type_comments=True)
        elif suffix == ".json":
            json.loads(source)
        elif suffix == ".toml":
            try:
                import tomllib
            except ModuleNotFoundError:
                return None
            tomllib.loads(source)
        elif suffix in {".sh", ".bash"} and shutil.which("bash"):
            with tempfile.NamedTemporaryFile(
                "w", suffix=suffix, encoding="utf-8"
            ) as handle:
                handle.write(source)
                handle.flush()
                result = subprocess.run(
                    ["bash", "-n", handle.name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            if result.returncode != 0:
                return (result.stderr or result.stdout).strip()
        elif suffix in {".js", ".mjs", ".cjs"} and shutil.which("node"):
            with tempfile.NamedTemporaryFile(
                "w", suffix=suffix, encoding="utf-8"
            ) as handle:
                handle.write(source)
                handle.flush()
                result = subprocess.run(
                    ["node", "--check", handle.name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            if result.returncode != 0:
                return (result.stderr or result.stdout).strip()
    except (SyntaxError, ValueError, OSError, subprocess.SubprocessError) as exc:
        return str(exc)
    return None


def prune(data: dict[str, Any], allowed: set[str]) -> None:
    if not env_bool("CLAUDE_PREFLIGHT_PRUNE_UNKNOWN_FIELDS", True):
        return
    for key in list(data):
        if key not in allowed:
            del data[key]


def normalize_read(
    data: dict[str, Any], payload: Mapping[str, Any], notes: list[str]
) -> None:
    path = normalize_file_path(data, payload, notes, must_exist=True, allow_prefix=True)
    for field in ("offset", "limit"):
        if field in data and not isinstance(data[field], int):
            try:
                data[field] = int(data[field])
            except (TypeError, ValueError):
                raise PreflightError(f"Read.{field} must be an integer.")
        if field in data and data[field] < 1:
            data[field] = 1
            notes.append(f"clamped Read.{field} to 1")
    if "pages" in data:
        if path.suffix.lower() != ".pdf":
            data.pop("pages", None)
            notes.append("removed PDF pages from a non-PDF Read")
        elif not isinstance(data["pages"], str) or not re.fullmatch(
            r"\d+(?:-\d+)?", data["pages"]
        ):
            raise PreflightError(
                "Read.pages must be a page number or range such as 1-5."
            )
    prune(data, {"file_path", "offset", "limit", "pages"})


def normalize_write(
    data: dict[str, Any],
    payload: Mapping[str, Any],
    notes: list[str],
    advisories: list[str],
) -> None:
    path = normalize_file_path(data, payload, notes)
    content = take_alias(data, "content", CONTENT_ALIASES)
    if not isinstance(content, str):
        raise PreflightError("Write requires string content.")
    for key in ("content", *CONTENT_ALIASES):
        data.pop(key, None)
    if path.suffix.lower() != ".md":
        unwrapped = unwrap_fence(content)
        if unwrapped != content:
            content = unwrapped
            notes.append("removed a whole-value Markdown fence")
    if (
        env_bool("CLAUDE_ENSURE_FINAL_NEWLINE", True)
        and path.suffix.lower() in TEXT_EXTENSIONS
    ):
        if content and not content.endswith("\n"):
            content += "\n"
            notes.append("added a final newline")
    error = validate_source(path, content)
    if error:
        raise PreflightError(
            f"Proposed Write has invalid {path.suffix or 'text'} syntax: {error}"
        )
    enforce_tdd_companion(path, payload, advisories)
    if env_bool("CLAUDE_AUTO_CREATE_WRITE_PARENTS", True):
        path.parent.mkdir(parents=True, exist_ok=True)
    data["content"] = content
    prune(data, {"file_path", "content"})


def strip_read_gutters(text: str) -> str:
    lines = text.splitlines(keepends=True)
    cleaned: list[str] = []
    changed = False
    pattern = re.compile(r"^\s*\d+(?:\t|\s*(?:->|→|:|\|))")
    for line in lines:
        updated = pattern.sub("", line, count=1)
        changed = changed or updated != line
        cleaned.append(updated)
    return "".join(cleaned) if changed else text


def unique_trailing_space_match(content: str, requested: str) -> str | None:
    content_lines = content.splitlines(keepends=True)
    request_lines = requested.splitlines(keepends=True)
    if not request_lines:
        return None

    def clean(line: str) -> str:
        return line.rstrip("\r\n").rstrip(" \t")

    wanted = [clean(line) for line in request_lines]
    matches: list[str] = []
    for index in range(len(content_lines) - len(request_lines) + 1):
        block = content_lines[index : index + len(request_lines)]
        if [clean(line) for line in block] == wanted:
            matches.append("".join(block))
            if len(matches) > 1:
                return None
    return matches[0] if len(matches) == 1 else None


def smallest_unique_changed_block(
    content: str,
    requested_old: str,
    requested_new: str,
) -> tuple[str, str] | None:
    """Reduce one stale large Edit to its smallest exact unique changed block.

    Local models often send an entire function or class even when only one line
    changes. If unrelated surrounding context is stale, the native Edit fails.
    This helper compares the requested old/new strings, keeps the full intended
    change, and trims only unchanged outer lines. It returns a replacement only
    when the resulting old block occurs exactly once in the current file.
    """
    old_lines = requested_old.splitlines(keepends=True)
    new_lines = requested_new.splitlines(keepends=True)
    if not old_lines:
        return None

    matcher = difflib.SequenceMatcher(
        None,
        old_lines,
        new_lines,
        autojunk=False,
    )
    changed = [opcode for opcode in matcher.get_opcodes() if opcode[0] != "equal"]
    if not changed:
        return None

    first = changed[0]
    last = changed[-1]
    old_start, old_end = first[1], last[2]
    new_start, new_end = first[3], last[4]

    max_before = min(old_start, new_start)
    max_after = min(len(old_lines) - old_end, len(new_lines) - new_end)
    candidates: list[tuple[int, int, str, str]] = []

    # Try the least context first. Increase context only until the old block is
    # unique. This preserves the entire requested change while discarding stale
    # outer context that does not participate in the change.
    for before in range(max_before + 1):
        for after in range(max_after + 1):
            old_block = "".join(old_lines[old_start - before : old_end + after])
            if not old_block or old_block == requested_old:
                continue
            if content.count(old_block) != 1:
                continue
            new_block = "".join(new_lines[new_start - before : new_end + after])
            candidates.append((len(old_block), before + after, old_block, new_block))

    if not candidates:
        return None
    _length, _context, old_block, new_block = min(candidates)
    return old_block, new_block


def normalize_edit(
    data: dict[str, Any],
    payload: Mapping[str, Any],
    notes: list[str],
    advisories: list[str],
) -> None:
    path = normalize_file_path(data, payload, notes, must_exist=True)
    old = take_alias(data, "old_string", OLD_ALIASES)
    new = take_alias(data, "new_string", NEW_ALIASES)
    if not isinstance(old, str) or not old:
        raise PreflightError("Edit requires a non-empty old_string.")
    if not isinstance(new, str):
        raise PreflightError("Edit requires string new_string.")
    replace_all = data.get("replace_all", False)
    if isinstance(replace_all, str):
        replace_all = replace_all.strip().lower() in {"1", "true", "yes", "on"}
    if not isinstance(replace_all, bool):
        raise PreflightError("Edit.replace_all must be a boolean.")
    if old == new:
        raise PreflightError("Edit old_string and new_string are identical.")
    enforce_tdd_companion(path, payload, advisories)

    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            content = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise PreflightError(f"Unable to read Edit target: {exc}") from exc

    exact = content.count(old)
    if exact == 0:
        gutterless = strip_read_gutters(old)
        candidates: list[str] = []
        for requested in dict.fromkeys((gutterless, old)):
            if requested and content.count(requested) == 1:
                candidates.append(requested)
            else:
                trailing = unique_trailing_space_match(content, requested)
                if trailing is not None:
                    candidates.append(trailing)
        candidates = list(dict.fromkeys(candidates))
        if len(candidates) == 1:
            old = candidates[0]
            notes.append("aligned old_string to one exact on-disk block")
            exact = 1
        else:
            reduced = smallest_unique_changed_block(content, gutterless, new)
            if reduced is not None:
                old, new = reduced
                exact = 1
                notes.append(
                    "reduced a stale large Edit to the smallest exact unique "
                    "changed block"
                )
            else:
                raise PreflightError(
                    "old_string was not found exactly. Read the current file and "
                    "retry with the smallest exact unique block, usually 1-5 lines "
                    "around the change."
                )

    if exact > 1 and not replace_all:
        raise PreflightError(
            f"old_string occurs {exact} times. Include more surrounding "
            "context, or set replace_all=true only when every occurrence "
            "should change."
        )
    if "\r\n" in old and "\r\n" not in new:
        new = new.replace("\n", "\r\n")
        notes.append("preserved CRLF line endings in new_string")

    proposed = (
        content.replace(old, new) if replace_all else content.replace(old, new, 1)
    )
    error = validate_source(path, proposed)
    if error:
        raise PreflightError(
            f"Proposed Edit has invalid {path.suffix or 'text'} syntax: {error}"
        )

    for key in ("old_string", *OLD_ALIASES, "new_string", *NEW_ALIASES):
        data.pop(key, None)
    data["old_string"] = old
    data["new_string"] = new
    if replace_all:
        data["replace_all"] = True
    else:
        data.pop("replace_all", None)
    prune(data, {"file_path", "old_string", "new_string", "replace_all"})


def normalize_glob(
    data: dict[str, Any], payload: Mapping[str, Any], notes: list[str]
) -> None:
    pattern = take_alias(data, "pattern", ("glob", "query", "search"))
    if not isinstance(pattern, str) or not pattern.strip():
        pattern = "**/*"
        notes.append("supplied the default Glob pattern **/*")
    raw_path = take_alias(data, "path", ("root", "directory", "cwd"))
    path = (
        project_root(payload)
        if raw_path is None
        else resolve_project_path(raw_path, payload)
    )
    if not path.is_dir():
        raise PreflightError(f"Glob.path must be a directory: {path}")
    if "\x00" in pattern:
        raise PreflightError("Glob.pattern may not contain a NUL byte.")
    data.clear()
    data.update({"pattern": pattern.strip(), "path": str(path)})


def normalize_grep(
    data: dict[str, Any], payload: Mapping[str, Any], notes: list[str]
) -> None:
    pattern = take_alias(data, "pattern", ("query", "search", "text"))
    if not isinstance(pattern, str) or not pattern:
        raise PreflightError("Grep requires a non-empty pattern.")
    if "\x00" in pattern:
        raise PreflightError("Grep.pattern may not contain a NUL byte.")
    try:
        re.compile(pattern)
    except re.error:
        if env_bool("CLAUDE_GREP_INVALID_REGEX_AS_LITERAL", True):
            pattern = re.escape(pattern)
            notes.append("escaped an invalid regex as a literal search")
        else:
            raise PreflightError("Grep pattern is not a valid regular expression.")
    raw_path = take_alias(data, "path", ("root", "directory", "cwd"))
    path = (
        project_root(payload)
        if raw_path is None
        else resolve_project_path(raw_path, payload)
    )
    output_mode = data.get("output_mode", "files_with_matches")
    if output_mode not in {"files_with_matches", "content", "count"}:
        output_mode = "files_with_matches"
    updated = {
        "pattern": pattern,
        "path": str(path),
        "output_mode": output_mode,
    }
    for key in (
        "glob",
        "type",
        "-i",
        "-n",
        "-A",
        "-B",
        "-C",
        "multiline",
        "head_limit",
        "offset",
    ):
        if key in data:
            updated[key] = data[key]
    updated.setdefault("head_limit", 100)
    data.clear()
    data.update(updated)


def normalize_notebook(
    data: dict[str, Any], payload: Mapping[str, Any], notes: list[str]
) -> None:
    path = normalize_file_path(
        data,
        payload,
        notes,
        canonical="notebook_path",
        aliases=("path", "file_path", "notebook", "filename"),
        must_exist=True,
    )
    mode = data.get("edit_mode", data.get("mode", "replace"))
    if mode not in {"replace", "insert", "delete"}:
        raise PreflightError(
            "NotebookEdit.edit_mode must be replace, insert, or delete."
        )
    source = take_alias(data, "new_source", ("source", "cell_source", "content"))
    cell_id = data.get("cell_id", data.get("cell", data.get("cell_index")))

    if isinstance(cell_id, int) or (isinstance(cell_id, str) and cell_id.isdigit()):
        index = int(cell_id)
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"))
            cells = notebook.get("cells", [])
            candidate = cells[index]
            resolved_id = candidate.get("id") if isinstance(candidate, dict) else None
        except (OSError, json.JSONDecodeError, IndexError, TypeError, ValueError):
            resolved_id = None
        if not isinstance(resolved_id, str) or not resolved_id:
            raise PreflightError(
                "Numeric notebook cell index could not be mapped to a stable cell_id."
            )
        cell_id = resolved_id
        notes.append("mapped a numeric notebook cell index to cell_id")

    if mode in {"replace", "delete"} and not isinstance(cell_id, str):
        raise PreflightError(f"NotebookEdit {mode} requires cell_id.")
    if mode != "delete" and not isinstance(source, str):
        raise PreflightError(f"NotebookEdit {mode} requires new_source.")

    updated: dict[str, Any] = {"notebook_path": str(path), "edit_mode": mode}
    if isinstance(cell_id, str):
        updated["cell_id"] = cell_id
    if isinstance(source, str):
        updated["new_source"] = source
    if mode == "insert":
        cell_type = data.get("cell_type", "code")
        if cell_type not in {"code", "markdown"}:
            raise PreflightError("NotebookEdit.cell_type must be code or markdown.")
        updated["cell_type"] = cell_type
    data.clear()
    data.update(updated)


def todo_status(value: Any) -> str:
    text = str(value or "pending").strip().lower().replace("-", "_").replace(" ", "_")
    if text in {"done", "complete", "completed", "finished", "closed"}:
        return "completed"
    if text in {"doing", "active", "started", "in_progress", "wip"}:
        return "in_progress"
    return "pending"


def todo_active(content: str) -> str:
    base = content.strip().rstrip(".")
    return f"Working on: {base}"


def parse_todo_items(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return list(raw.values())
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, list):
                return decoded
        except json.JSONDecodeError:
            pass
        items = []
        for line in raw.splitlines():
            text = re.sub(
                r"^\s*(?:[-*+]\s*(?:\[[ xX]\])?|\d+[.)])\s*", "", line
            ).strip()
            if text:
                items.append(text)
        return items
    return []


def normalize_todo(
    data: dict[str, Any], payload: Mapping[str, Any], notes: list[str]
) -> None:
    raw = take_alias(
        data, "todos", ("tasks", "items", "todoItems", "todo_list", "taskList")
    )
    if raw is None and any(
        key in data for key in ("content", "title", "description", "text", "task")
    ):
        raw = [data]
    if raw is None:
        raise PreflightError("TodoWrite requires todos.")
    if raw == []:
        data.clear()
        data["todos"] = []
        return

    todos: list[dict[str, str]] = []
    for item in parse_todo_items(raw):
        if isinstance(item, str):
            content = item.strip()
            status = "pending"
            active = None
        elif isinstance(item, Mapping):
            content_value = next(
                (
                    item.get(key)
                    for key in (
                        "content",
                        "title",
                        "description",
                        "text",
                        "task",
                        "taskName",
                    )
                    if item.get(key) is not None
                ),
                None,
            )
            content = str(content_value or "").strip()
            status_value = next(
                (
                    item.get(key)
                    for key in ("status", "state", "phase", "progress", "taskStatus")
                    if item.get(key) is not None
                ),
                None,
            )
            if (
                item.get("isCompleted") is True
                or item.get("isDone") is True
                or item.get("checked") is True
            ):
                status_value = "completed"
            status = todo_status(status_value)
            active_value = next(
                (
                    item.get(key)
                    for key in ("activeForm", "active_form", "active", "working")
                    if item.get(key) is not None
                ),
                None,
            )
            active = str(active_value).strip() if active_value is not None else None
        else:
            continue
        if not content:
            continue
        todos.append(
            {
                "content": content,
                "status": status,
                "activeForm": active or todo_active(content),
            }
        )
    if not todos:
        raise PreflightError("TodoWrite contained no usable Todo items.")
    if env_bool("CLAUDE_TODO_SINGLE_IN_PROGRESS", True):
        seen_active = False
        for todo in todos:
            if todo["status"] == "in_progress":
                if seen_active:
                    todo["status"] = "pending"
                else:
                    seen_active = True
    data.clear()
    data["todos"] = todos
    notes.append("normalized TodoWrite items to content/status/activeForm")


TDD_BACKEND_EXTENSIONS = {".py"}
TDD_FRONTEND_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".vue"}
TDD_EXCLUDED_PARTS = {"tests", "test", "__tests__", "migrations", "generated"}
SHELL_CONTROL_TOKENS = {"&&", "||", ";", "|", "&"}


def policy_mode(name: str, default: str) -> str:
    mode = os.environ.get(name, default).strip().lower()
    return mode if mode in {"off", "advisory", "strict"} else default


def production_kind(path: Path, root: Path) -> str | None:
    try:
        relative = path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return None
    parts = relative.parts
    lowered = {part.casefold() for part in parts[:-1]}
    if TDD_EXCLUDED_PARTS.intersection(lowered):
        return None
    if len(parts) >= 3 and parts[:2] == ("backend", "app"):
        if path.suffix.lower() in TDD_BACKEND_EXTENSIONS and path.name != "__init__.py":
            return "python"
    if len(parts) >= 3 and parts[:2] == ("frontend", "src"):
        if path.name.endswith(".d.ts"):
            return None
        if path.suffix.lower() in TDD_FRONTEND_EXTENSIONS:
            return "frontend"
    return None


def companion_name_matches(source: Path, candidate: Path, kind: str) -> bool:
    name = candidate.name.casefold()
    stem = source.stem.casefold()
    if kind == "python":
        return candidate.suffix.lower() == ".py" and (
            name == f"test_{stem}.py"
            or name == f"{stem}_test.py"
            or name.startswith(f"test_{stem}_")
            or name.startswith(f"{stem}_test_")
        )
    return bool(
        re.fullmatch(
            rf"{re.escape(stem)}(?:\.[^.]+)*\.(?:test|spec)\.(?:js|jsx|ts|tsx)",
            name,
        )
    )


def companion_roots(source: Path, root: Path, kind: str) -> list[Path]:
    candidates: list[Path]
    if kind == "python":
        candidates = [
            root / "backend/app/tests",
            root / "backend/tests",
            root / "tests",
            source.parent,
            source.parent / "tests",
        ]
    else:
        candidates = [
            root / "frontend/tests",
            root / "frontend/src/tests",
            source.parent,
            source.parent / "__tests__",
        ]
    result: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        if resolved in seen or not resolved.is_dir() or not is_within(resolved, root):
            continue
        seen.add(resolved)
        result.append(resolved)
    return result


def find_companion_tests(source: Path, root: Path) -> list[Path]:
    kind = production_kind(source, root)
    if kind is None:
        return []
    matches: list[Path] = []
    seen: set[Path] = set()
    for search_root in companion_roots(source, root, kind):
        for current, dirs, files in os.walk(search_root):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
            base = Path(current)
            for name in files:
                candidate = (base / name).resolve(strict=False)
                if candidate in seen:
                    continue
                seen.add(candidate)
                if companion_name_matches(source, candidate, kind):
                    matches.append(candidate)
    return sorted(matches)


def handle_policy_violation(
    mode: str,
    message: str,
    advisories: list[str],
) -> None:
    if mode == "strict":
        raise PreflightError(message)
    if mode == "advisory":
        advisories.append(message)


def enforce_tdd_companion(
    path: Path,
    payload: Mapping[str, Any],
    advisories: list[str],
) -> None:
    mode = policy_mode("CLAUDE_TDD_COMPANION_MODE", "strict")
    if mode == "off":
        return
    root = project_root(payload)
    if production_kind(path, root) is None:
        return
    if find_companion_tests(path, root):
        return
    handle_policy_violation(
        mode,
        "TDD companion required before changing production code: "
        f"{path}. Create a focused matching test first, run it to a genuine assertion "
        "failure, then retry the production change.",
        advisories,
    )


def shell_groups(command: str) -> list[list[str]]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError as exc:
        raise PreflightError(f"Bash command could not be parsed safely: {exc}") from exc
    groups: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token and all(character in ";&|" for character in token):
            if current:
                groups.append(current)
                current = []
        else:
            current.append(token)
    if current:
        groups.append(current)
    return groups


def command_executable_index(group: list[str]) -> int | None:
    """Return the actual executable index for a simple command group."""
    index = 0
    assignment = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
    while index < len(group) and assignment.match(group[index]):
        index += 1

    while index < len(group):
        name = Path(group[index]).name
        if name in {"command", "builtin", "exec", "nohup"}:
            index += 1
            while index < len(group) and group[index].startswith("-"):
                index += 1
            continue
        if name == "env":
            index += 1
            while index < len(group):
                token = group[index]
                if assignment.match(token):
                    index += 1
                    continue
                if token in {"-C", "--chdir", "-u", "--unset"}:
                    index += 2
                    continue
                if token.startswith(("--chdir=", "--unset=")):
                    index += 1
                    continue
                if token.startswith("-"):
                    index += 1
                    continue
                break
            continue
        break
    return index if index < len(group) else None


def parse_git_group(group: list[str], cwd: Path) -> tuple[str, int, Path] | None:
    """Parse a direct git command without mistaking arguments to echo/printf for Git."""
    git_index = command_executable_index(group)
    if git_index is None or Path(group[git_index]).name != "git":
        return None

    index = git_index + 1
    git_cwd = cwd
    while index < len(group):
        token = group[index]
        if token == "-C":
            if index + 1 >= len(group):
                raise PreflightError("git -C is missing its directory.")
            target = Path(group[index + 1]).expanduser()
            git_cwd = (target if target.is_absolute() else git_cwd / target).resolve(
                strict=False
            )
            index += 2
            continue
        if token.startswith("-C") and token != "-C":
            target = Path(token[2:]).expanduser()
            git_cwd = (target if target.is_absolute() else git_cwd / target).resolve(
                strict=False
            )
            index += 1
            continue
        if token in {"-c", "--config-env", "--git-dir", "--work-tree"}:
            if index + 1 >= len(group):
                raise PreflightError(f"{token} is missing its value.")
            index += 2
            continue
        if token.startswith(("--git-dir=", "--work-tree=", "--config-env=")):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        break
    if index >= len(group):
        return None
    return group[index], index, git_cwd


def git_actions(command: str, payload: Mapping[str, Any]) -> list[tuple[str, Path]]:
    actions: list[tuple[str, Path]] = []
    current = payload_cwd(payload)
    for group in shell_groups(command):
        executable = command_executable_index(group)
        if executable is not None and Path(group[executable]).name == "cd":
            arguments = group[executable + 1 :]
            if arguments and arguments[0] == "--":
                arguments = arguments[1:]
            if len(arguments) != 1 or any(
                marker in arguments[0] for marker in ("$", "`")
            ):
                raise PreflightError(
                    "Git delivery uses a dynamic or ambiguous cd target."
                )
            target = Path(arguments[0]).expanduser()
            current = (target if target.is_absolute() else current / target).resolve(
                strict=False
            )
            continue
        parsed = parse_git_group(group, current)
        if parsed is None:
            continue
        subcommand, _index, git_cwd = parsed
        if subcommand in {"commit", "push"}:
            actions.append((subcommand, git_cwd))
    return actions


def run_git(cwd: Path, *args: str) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    output = result.stdout if result.returncode == 0 else result.stderr
    return result.returncode, output.strip()


def git_root(cwd: Path) -> Path:
    code, output = run_git(cwd, "rev-parse", "--show-toplevel")
    if code != 0 or not output:
        raise PreflightError(f"Git command would run outside a valid repository: {cwd}")
    root = Path(output).resolve(strict=False)
    if not is_within(root, project_root({"cwd": str(cwd)})):
        raise PreflightError(
            f"Git repository is outside the configured project: {root}"
        )
    return root


def staged_paths(repo: Path) -> list[Path]:
    code, output = run_git(
        repo,
        "diff",
        "--cached",
        "--name-only",
        "--diff-filter=ACMR",
        "-z",
    )
    if code != 0:
        raise PreflightError("Unable to inspect staged paths before commit.")
    return [repo / raw for raw in output.split("\0") if raw]


def staged_numstat(repo: Path) -> tuple[int, int, int]:
    code, output = run_git(repo, "diff", "--cached", "--numstat")
    if code != 0:
        raise PreflightError("Unable to inspect the staged diff before commit.")
    files = changed = binary = 0
    for line in output.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        files += 1
        if parts[0] == "-" or parts[1] == "-":
            binary += 1
            continue
        try:
            changed += int(parts[0]) + int(parts[1])
        except ValueError as exc:
            raise PreflightError(f"Unexpected git numstat line: {line}") from exc
    return files, changed, binary


def enforce_staged_tdd(repo: Path, paths: list[Path], advisories: list[str]) -> None:
    mode = policy_mode("CLAUDE_TDD_COMPANION_MODE", "strict")
    if mode == "off":
        return
    staged = {path.resolve(strict=False) for path in paths}
    missing: list[Path] = []
    for source in paths:
        if production_kind(source, repo) is None:
            continue
        companions = find_companion_tests(source, repo)
        # Test must exist (on disk) or be staged in this commit
        test_exists = any(
            test.exists() or test.resolve(strict=False) in staged for test in companions
        )
        if not test_exists:
            missing.append(source)
    if not missing:
        return
    listing = "\n".join(f"- {path.relative_to(repo)}" for path in missing[:20])
    handle_policy_violation(
        mode,
        "TDD commit gate: production code must have a matching test file "
        "(existing or staged).\n" + listing,
        advisories,
    )


def trunk_ref(repo: Path) -> str | None:
    configured = os.environ.get("CLAUDE_TRUNK_BRANCH", "").strip()
    if configured:
        return configured
    code, symbolic = run_git(
        repo,
        "symbolic-ref",
        "--quiet",
        "--short",
        "refs/remotes/origin/HEAD",
    )
    if code == 0 and symbolic:
        return symbolic
    for candidate in ("main", "master", "origin/main", "origin/master"):
        code, _ = run_git(repo, "rev-parse", "--verify", candidate)
        if code == 0:
            return candidate
    return None


def branch_age_hours(repo: Path) -> tuple[float | None, str]:
    code, _ = run_git(repo, "rev-parse", "--verify", "HEAD")
    if code != 0:
        return 0.0, "repository has no commits yet"
    code, branch = run_git(repo, "branch", "--show-current")
    if code != 0 or not branch:
        return None, "current branch could not be determined"
    trunk = trunk_ref(repo)
    if trunk is None:
        return None, "trunk branch could not be determined"
    if branch == trunk or branch == trunk.rsplit("/", 1)[-1]:
        return 0.0, f"current branch is trunk ({trunk})"
    code, _ = run_git(repo, "merge-base", trunk, "HEAD")
    if code != 0:
        return None, f"branch {branch!r} has no merge base with {trunk!r}"
    code, timestamps = run_git(
        repo,
        "log",
        "--reverse",
        "--format=%ct",
        f"{trunk}..HEAD",
    )
    if code != 0:
        return None, f"unique commits for branch {branch!r} could not be inspected"
    values = [line for line in timestamps.splitlines() if line.isdigit()]
    if not values:
        return 0.0, f"branch {branch!r} has no commits beyond {trunk!r}"
    age = max(0.0, (time.time() - int(values[0])) / 3600.0)
    return age, f"branch {branch!r} is {age:.1f} hours old"


def enforce_minimum_cd(
    repo: Path,
    action: str,
    advisories: list[str],
) -> None:
    mode = policy_mode("CLAUDE_MIN_CD_MODE", "advisory")
    if mode == "off":
        return
    violations: list[str] = []
    if action == "commit":
        files, changed, binary = staged_numstat(repo)
        if files == 0:
            raise PreflightError("git commit has no staged changes.")
        file_limit = env_int("CLAUDE_MAX_COMMIT_FILES", 25)
        line_limit = env_int("CLAUDE_MAX_COMMIT_LINES", 500)
        if files > file_limit:
            violations.append(
                f"staged diff touches {files} files; limit is {file_limit}"
            )
        if changed > line_limit:
            violations.append(
                f"staged diff changes {changed} text lines; limit is {line_limit}"
            )
        if violations:
            violations.append(f"binary files in staged diff: {binary}")
    age, detail = branch_age_hours(repo)
    if age is None:
        violations.append(detail)
    else:
        age_limit = env_int("CLAUDE_MAX_BRANCH_AGE_HOURS", 48)
        if age > age_limit:
            violations.append(f"{detail}; limit is {age_limit} hours")
    if not violations:
        return
    handle_policy_violation(
        mode,
        "Minimum CD check:\n- " + "\n- ".join(violations),
        advisories,
    )


def enforce_delivery_policies(
    command: str,
    payload: Mapping[str, Any],
    advisories: list[str],
) -> None:
    for action, cwd in git_actions(command, payload):
        repo = git_root(cwd)
        if action == "commit":
            paths = staged_paths(repo)
            enforce_staged_tdd(repo, paths, advisories)
        enforce_minimum_cd(repo, action, advisories)


def selected_python_project(payload: Mapping[str, Any]) -> Path:
    root = project_root(payload)
    configured = os.environ.get("CLAUDE_PYTHON_PROJECT_DIR", "auto").strip()
    if configured and configured.lower() != "auto":
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve(strict=False)
        if is_within(candidate, root) and candidate.is_dir():
            return candidate
    cwd = payload_cwd(payload)
    if is_within(cwd, root):
        for candidate in (cwd, *cwd.parents):
            if (candidate / "uv.lock").exists() or (
                candidate / "pyproject.toml"
            ).exists():
                return candidate
            if candidate == root:
                break
    backend = root / "backend"
    if (backend / "uv.lock").exists() or (backend / "pyproject.toml").exists():
        return backend.resolve(strict=False)
    return root


def split_simple_project_command(command: str) -> tuple[str, list[str]] | None:
    command = command.strip()
    match = re.match(r"^cd\s+(.+?)\s*&&\s*(.+)$", command, re.DOTALL)
    if match:
        command = match.group(2).strip()
    match = re.match(r"^(?:source|\.)\s+\S+activate\s*&&\s*(.+)$", command, re.DOTALL)
    if match:
        command = match.group(1).strip()
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if not tokens:
        return None

    lower = [Path(token).name.lower() for token in tokens]
    if lower[0] in {"python", "python3"} and len(tokens) >= 3 and tokens[1] == "-m":
        module = Path(tokens[2]).name.lower()
        if module in PYTHON_TOOLS:
            return "pytest" if module == "py.test" else module, tokens[3:]
    if lower[0] in {"pytest", "py.test"}:
        return "pytest", tokens[1:]
    if lower[0] == "uv":
        try:
            run_index = lower.index("run")
        except ValueError:
            return None
        tail = tokens[run_index + 1 :]
        if (
            len(tail) >= 3
            and Path(tail[0]).name.lower() in {"python", "python3"}
            and tail[1] == "-m"
        ):
            module = Path(tail[2]).name.lower()
            if module in PYTHON_TOOLS:
                return "pytest" if module == "py.test" else module, tail[3:]
        if tail and Path(tail[0]).name.lower() in PYTHON_TOOLS:
            name = (
                "pytest"
                if Path(tail[0]).name.lower() == "py.test"
                else Path(tail[0]).name.lower()
            )
            return name, tail[1:]
    if lower[0] in PYTHON_TOOLS:
        name = "pytest" if lower[0] == "py.test" else lower[0]
        return name, tokens[1:]
    return None


def normalize_python_command(
    command: str, payload: Mapping[str, Any], notes: list[str]
) -> tuple[str, bool]:
    parsed = split_simple_project_command(command)
    if parsed is None or not env_bool("CLAUDE_NORMALIZE_PYTHON_PROJECT_TOOLS", True):
        return command, False
    tool, arguments = parsed
    project = selected_python_project(payload)
    uv = shutil.which("uv")
    if (project / "uv.lock").exists():
        if not uv:
            raise PreflightError(
                f"{project} is uv-managed, but uv is not installed on PATH."
            )
        rendered = shlex.join(
            ["uv", "--directory", str(project), "run", tool, *arguments]
        )
    else:
        executable = project / ".venv" / "bin" / tool
        if executable.is_file():
            rendered = shlex.join([str(executable), *arguments])
        elif tool == "pytest" and (project / ".venv" / "bin" / "python").is_file():
            rendered = shlex.join(
                [str(project / ".venv" / "bin" / "python"), "-m", "pytest", *arguments]
            )
        elif shutil.which(tool):
            rendered = shlex.join([shutil.which(tool) or tool, *arguments])
        else:
            raise PreflightError(
                f"No installed local runner was found for {tool} in {project}."
            )
    if rendered != command:
        notes.append(f"normalized {tool} through the selected Python project")
    return rendered, True


def validate_cd_targets(command: str, payload: Mapping[str, Any]) -> None:
    root = project_root(payload)
    cwd = payload_cwd(payload)
    for match in re.finditer(r"(?:^|[;&|]\s*)cd\s+([^;&|]+)", command):
        try:
            tokens = shlex.split(match.group(1).strip())
        except ValueError:
            raise PreflightError("Bash cd target could not be parsed safely.")
        if not tokens:
            raise PreflightError("Bash cd target is missing.")
        raw = tokens[0]
        if any(marker in raw for marker in ("$", "`")):
            raise PreflightError(
                "Dynamic Bash cd targets are not allowed for project commands."
            )
        target = Path(raw).expanduser()
        if not target.is_absolute():
            target = cwd / target
        if not is_within(target.resolve(strict=False), root):
            raise PreflightError(
                f"Bash command changes directory outside the project: {target}"
            )


def git_policy_error(command: str) -> str | None:
    lowered = command.lower()
    if "core.hookspath" in lowered:
        return "Changing or overriding Git core.hooksPath is not allowed."
    if re.search(
        r"\bgit\s+add\s+(?:-a\b|--all\b|-u\b|--update\b|\.?/??\s*(?:$|[;&|]))", lowered
    ):
        return "Broad Git staging is not allowed; stage exact files."
    if re.search(r"\bgit\s+add\b[^;&|]*[*?[]", command):
        return "Wildcard Git staging is not allowed; stage exact files."
    if re.search(
        r"\bgit\s+commit\b[^;&|]*(?:--no-verify|(?:^|\s)-n(?:\s|$)|(?:^|\s)-a(?:\s|$)|--all)",
        lowered,
    ):
        return "Git commit bypass/all flags are not allowed."
    if re.search(
        r"\bgit\s+push\b[^;&|]*(?:--force\b|--force-with-lease\b|\s-f\b|--mirror\b)",
        lowered,
    ):
        return "Force-push and mirror operations are not allowed."
    if re.search(
        r"(?:^|[;&|]\s*)(?:skip|husky|lefthook)=\S+\s+git\s+(?:commit|push)", lowered
    ):
        return "Git hook-bypass environment assignments are not allowed."
    return None


def allowed_hosts() -> set[str]:
    result = set(DEFAULT_ALLOWED_HOSTS)
    result.update(
        host.strip().lower().rstrip(".")
        for host in os.environ.get("CLAUDE_EGRESS_ALLOW_HOSTS", "").split(",")
        if host.strip()
    )
    return result


def host_allowed(host: str) -> bool:
    candidate = host.lower().strip("[]").rstrip(".")
    return any(
        candidate == allowed or candidate.endswith("." + allowed)
        for allowed in allowed_hosts()
    )


def remote_host(remote: str) -> str | None:
    if "://" in remote:
        try:
            return urlsplit(remote).hostname
        except ValueError:
            return None
    match = re.match(r"(?:[^@]+@)?(\[[0-9A-Fa-f:]+\]|[^:]+):", remote)
    return match.group(1) if match else None


def git_push_selection(
    command: str, payload: Mapping[str, Any]
) -> tuple[bool, str | None]:
    """Return whether a direct git push is present and its resolved remote."""
    current = payload_cwd(payload)
    for group in shell_groups(command):
        executable = command_executable_index(group)
        if executable is not None and Path(group[executable]).name == "cd":
            arguments = group[executable + 1 :]
            if arguments and arguments[0] == "--":
                arguments = arguments[1:]
            if len(arguments) != 1 or any(
                marker in arguments[0] for marker in ("$", "`")
            ):
                return True, None
            target = Path(arguments[0]).expanduser()
            current = (target if target.is_absolute() else current / target).resolve(
                strict=False
            )
            continue

        parsed = parse_git_group(group, current)
        if parsed is None:
            continue
        subcommand, subcommand_index, git_cwd = parsed
        if subcommand != "push":
            continue

        remote_name: str | None = None
        arguments = group[subcommand_index + 1 :]
        index = 0
        while index < len(arguments):
            token = arguments[index]
            if token == "--":
                index += 1
                continue
            if token in {"--repo"}:
                if index + 1 >= len(arguments):
                    return True, None
                remote_name = arguments[index + 1]
                break
            if token.startswith("--repo="):
                remote_name = token.split("=", 1)[1]
                break
            if token.startswith("-"):
                index += 1
                continue
            remote_name = token
            break
        remote_name = remote_name or "origin"
        if "://" in remote_name or re.match(r"(?:[^@]+@)?[^:]+:", remote_name):
            return True, remote_name
        code, remote = run_git(git_cwd, "remote", "get-url", "--push", remote_name)
        return True, remote if code == 0 and remote else None
    return False, None


def egress_policy_error(command: str, payload: Mapping[str, Any]) -> str | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = []
    programs = {Path(token).name.lower() for token in tokens}
    network = programs.intersection(NETWORK_PROGRAMS)
    hosts: set[str] = set()
    for raw_url in re.findall(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s'\"<>]+", command):
        try:
            parsed = urlsplit(raw_url.rstrip(".,);]"))
        except ValueError:
            continue
        if parsed.hostname:
            hosts.add(parsed.hostname)
    for match in re.finditer(
        r"(?:[^\s@:/]+@)?(\[[0-9A-Fa-f:]+\]|[A-Za-z0-9.-]+):(?!//)[^\s]+", command
    ):
        hosts.add(match.group(1))

    # rsync is also a local copier. Treat it as egress only when a remote
    # operand is visible.
    if "rsync" in network and not hosts:
        network.remove("rsync")

    if tokens and Path(tokens[0]).name.lower() in {"curl", "wget"}:
        if tokens[1:] and all(
            token in {"--help", "-h", "--version", "-V"} for token in tokens[1:]
        ):
            network.discard(Path(tokens[0]).name.lower())

    has_push, remote = git_push_selection(command, payload)
    if has_push:
        network.add("git-push")
        if remote:
            host = remote_host(remote)
            if host:
                hosts.add(host)
        if not remote:
            return "Git push remote could not be resolved statically."

    if not network:
        return None
    if not hosts:
        return "Network destination could not be resolved statically."
    forbidden = sorted(host for host in hosts if not host_allowed(host))
    if forbidden:
        return "External network destination is not approved: " + ", ".join(forbidden)
    return None


def timeout_milliseconds(value: Any) -> int:
    if isinstance(value, bool):
        raise PreflightError("Bash.timeout must be a duration, not a boolean.")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.fullmatch(r"\s*(\d+)\s*(ms|s|m|h)?\s*", value, re.IGNORECASE)
        if not match:
            raise PreflightError(
                "Bash.timeout must be milliseconds or a value such as 30s or 5m."
            )
        amount = int(match.group(1))
        unit = (match.group(2) or "ms").lower()
        return amount * {"ms": 1, "s": 1000, "m": 60000, "h": 3600000}[unit]
    raise PreflightError("Bash.timeout must be an integer or duration string.")


def normalize_bash(
    data: dict[str, Any],
    payload: Mapping[str, Any],
    notes: list[str],
    advisories: list[str],
) -> None:
    command = take_alias(data, "command", ("cmd", "script", "shell"))
    if not isinstance(command, str) or not command.strip():
        raise PreflightError("Bash requires a non-empty command.")
    command = command.strip()
    fence = re.fullmatch(
        r"\s*```(?:bash|sh|shell)?\n(.*?)\n```\s*", command, re.DOTALL | re.IGNORECASE
    )
    if fence:
        command = fence.group(1).strip()
        notes.append("removed a shell Markdown fence")
    command = re.sub(r"^\s*(?:\$|>)\s+", "", command, count=1)

    command, long_python_command = normalize_python_command(command, payload, notes)
    validate_cd_targets(command, payload)
    if error := git_policy_error(command):
        raise PreflightError(error)
    if error := egress_policy_error(command, payload):
        raise PreflightError(error)
    enforce_delivery_policies(command, payload, advisories)

    updated: dict[str, Any] = {"command": command}
    if "description" in data and isinstance(data["description"], str):
        updated["description"] = data["description"]
    background = data.get("run_in_background")
    if background is True or (
        isinstance(background, str)
        and background.strip().lower() in {"1", "true", "yes", "on"}
    ):
        updated["run_in_background"] = True
    timeout = data.get("timeout")
    if timeout is not None:
        timeout = timeout_milliseconds(timeout)
    if long_python_command:
        desired = env_int("CLAUDE_BASH_LONG_COMMAND_TIMEOUT_MS", 600000)
        timeout = max(timeout or 0, desired)
    if timeout is not None:
        maximum = env_int("BASH_MAX_TIMEOUT_MS", 900000)
        updated["timeout"] = min(timeout, maximum)
    data.clear()
    data.update(updated)


def normalize(
    tool: str,
    data: dict[str, Any],
    payload: Mapping[str, Any],
    notes: list[str],
    advisories: list[str],
) -> None:
    if tool == "Read":
        normalize_read(data, payload, notes)
    elif tool == "Write":
        normalize_write(data, payload, notes, advisories)
    elif tool == "Edit":
        normalize_edit(data, payload, notes, advisories)
    elif tool == "Glob":
        normalize_glob(data, payload, notes)
    elif tool == "Grep":
        normalize_grep(data, payload, notes)
    elif tool == "NotebookEdit":
        normalize_notebook(data, payload, notes)
    elif tool == "TodoWrite":
        normalize_todo(data, payload, notes)
    elif tool == "Bash":
        normalize_bash(data, payload, notes, advisories)


def main() -> int:
    try:
        payload = read_payload()
    except HookError as exc:
        return deny(str(exc), label="TOOL-INPUT")
    name = tool_name(payload)
    if name not in SUPPORTED_TOOLS:
        return 0
    raw = payload.get("tool_input")
    if not isinstance(raw, Mapping):
        return deny(f"{name}.tool_input must be a JSON object.", label="TOOL-INPUT")
    original = dict(raw)
    updated = dict(raw)
    notes: list[str] = []
    advisories: list[str] = []
    try:
        normalize(name, updated, payload, notes, advisories)
    except PreflightError as exc:
        return deny(str(exc), label="TOOL-PREFLIGHT")
    except Exception as exc:
        return deny(
            f"Unexpected preflight error ({type(exc).__name__}): {exc}",
            label="TOOL-PREFLIGHT-INTERNAL",
        )
    emit_preflight_result(
        original,
        updated,
        notes=notes,
        advisories=advisories,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
