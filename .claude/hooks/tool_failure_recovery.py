#!/usr/bin/env python3
"""
Handles tool failures by tracking consecutive 'not found' Edit attempts
and issuing a warning to the user to reread the file.
"""

import sys
from pathlib import Path

from hook_common import emit_context, read_payload

# State directory for tracking consecutive failures
# Path is relative to the project root, handled by the harness
STATE_DIR = Path(".claude/hooks/state")


def get_failure_count(file_path: str) -> int:
    state_dir = STATE_DIR.resolve()
    state_dir.mkdir(parents=True, exist_ok=True)

    # Create a safe filename for the state file
    # Replace path separators and non-alphanumeric characters
    safe_name = "".join(c for c in file_path if c.isalnum() or c in "./_-").replace(
        "/", "_"
    )
    state_file = state_dir / f"{safe_name}.count"

    if state_file.exists():
        try:
            return int(state_file.read_text().strip())
        except (ValueError, OSError):
            return 0
    return 0


def increment_failure_count(file_path: str) -> int:
    count = get_failure_count(file_path)
    count += 1
    state_dir = STATE_DIR.resolve()
    state_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c for c in file_path if c.isalnum() or c in "./_-").replace(
        "/", "_"
    )
    state_file = state_dir / f"{safe_name}.count"
    state_file.write_text(str(count))
    return count


def main() -> int:
    try:
        payload = read_payload()
    except Exception:
        return 0

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})

    # We only care about Edit failures
    if tool_name != "Edit":
        return 0

    file_path = tool_input.get("file_path")
    if not file_path:
        return 0

    # Check if the error message suggests a "not found" or "exact match" issue
    error_msg = ""
    if "tool_response" in payload:
        resp = payload["tool_response"]
        if "error" in resp:
            error_msg = str(resp["error"])

    failure_patterns = [
        "not found",
        "exact match",
        "did not match",
        "could not be found",
        "not found exactly",
    ]

    if any(p in error_msg.lower() for p in failure_patterns):
        count = increment_failure_count(file_path)
        if count >= 2:
            warning = (
                f"⚠️ WARNING: Edit on {file_path} failed {count} times in a row. "
                "Please reread the file and ensure you have the correct 'old_string'."
            )
            emit_context("PostToolUseFailure", warning)

    return 0


if __name__ == "__main__":
    sys.exit(main())
