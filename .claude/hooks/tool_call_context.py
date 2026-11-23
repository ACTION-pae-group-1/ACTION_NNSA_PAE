#!/usr/bin/env python3
"""Give local models a short, exact tool contract before they create calls."""

from __future__ import annotations

import sys

from hook_common import HookError, emit_context, env_bool, project_root, read_payload


def session_contract(root: str) -> str:
    return f"""TOOL-CALL CONTRACT
Project root: {root}

Use only tools present in the current live tool list. The native delegation
tool is Agent; Explore is an Agent subtype/permission form when available,
not a standalone tool name. If Agent is unavailable or times out, continue
in the main session with Glob, Grep, Read, Edit, Write, and focused Bash.

Read:
{{"file_path":"{root}/path/to/file"}}
Use an absolute file path. Read existing files before Edit, and before a
full-file Write when the host requires it.

Write:
{{"file_path":"{root}/path/to/file","content":"complete file content"}}
Both exact keys are required. Write replaces the whole file;
use Edit for a partial change.

Edit:
{{"file_path":"{root}/path/to/file",
"old_string":"smallest exact unique current block, usually 1-5 lines",
"new_string":"replacement"}}
All three exact keys are required. Keep old_string as small as possible
while still unique, usually 1-5 lines around the intended change.
It must match exactly once. If it matches more than once, add only enough
surrounding context to make it unique; use replace_all=true only when
every occurrence should change. Never switch to a full-file Write
merely because an Edit failed.

Glob:
{{"pattern":"**/*name*","path":"{root}"}}
Grep:
{{"pattern":"symbol_name","path":"{root}","output_mode":"content"}}

TodoWrite, only when the live tool list exposes it:
{{"todos":[{{"content":"Task",
"status":"in_progress",
"activeForm":"Working on the task"}}]}}
Each item requires content, status, and activeForm.
status is pending, in_progress, or completed.

TDD for behavior changes:
Create or update the focused matching test first, run it to a genuine
assertion failure, implement the smallest change, then rerun the
focused test and affected suite. Production files under backend/app
and frontend/src require a companion test; commits must stage the
matching test change. A missing runner or collection error is not a
valid RED result.

Minimum CD:
Keep commits at or below 25 files and 500 changed text lines, and
keep feature branches under 48 hours. The default is advisory;
Git safety and the TDD companion gate remain strict.

Backend Python commands:
uv --directory {root}/backend run pytest <focused-test>
uv --directory {root}/backend run ruff check .

Instead of
uv --directory /workspaces/[Project_Name]/backend run pytest \\
  backend/app/tests/services/test_capability_proposals.py
Do
uv --directory /workspaces/[Project_Name]/backend run pytest \\
  app/tests/services/test_capability_proposals.py

Do not activate a virtual environment or use bare pytest when the backend is uv-managed.

On any tool failure, diagnose the actual error and continue when a safe
main-session path exists. Do not hand the task back for manual IDE editing
after one failed Agent, Edit, Write, or Bash call."""


def prompt_contract(root: str) -> str:
    return (
        "TOOL SCHEMA CHECK: use exact native tool names and required keys. "
        f"Write requires absolute file_path under {root} plus content. "
        "Edit requires file_path, old_string, and new_string; "
        "old_string should be the smallest exact unique block, usually 1-5 lines. "
        "TodoWrite items require content, status, and activeForm. "
        "Production changes require a focused matching test; "
        "stage source and test together. "
        "Use Agent with an Explore subtype only when Agent is available; "
        "otherwise use Glob -> Grep -> Read. "
        f"Run backend tests as uv --directory {root}/backend run pytest "
        "<focused-test>."
    )


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "session"
    try:
        payload = read_payload(required=False)
    except HookError:
        payload = {}
    root = str(project_root(payload))

    if mode == "session":
        if not env_bool("CLAUDE_TOOL_CALL_SESSION_CONTEXT", True):
            return 0
        emit_context("SessionStart", session_contract(root), limit=10000)
        return 0
    if mode == "prompt":
        if not env_bool("CLAUDE_TOOL_CALL_PROMPT_REMINDER", True):
            return 0
        emit_context("UserPromptSubmit", prompt_contract(root), limit=3000)
        return 0

    print("Expected mode: session or prompt", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
