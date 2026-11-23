"""Unit tests for .claude/hooks/tool_input_preflight.py input normalization."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks"))

from tool_input_preflight import main as preflight_main


class TestPreflight:
    """Test tool input preflight normalization via hook entry point."""

    def test_read_tool_with_valid_file(self):
        """Should allow Read tool with valid file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            # Create a test file
            test_file = tmppath / "test.py"
            test_file.write_text("print('hello')")

            payload = {
                "tool_name": "Read",
                "tool_input": {"file_path": str(test_file)},
                "cwd": str(tmppath),
            }

            # Should not raise
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                # Hook processes input and emits via stderr
                exit_code = preflight_main()
                # Should succeed or emit advisory (not fatal)
                assert exit_code in (0, 1)

    def test_read_tool_with_secret_file_blocked(self):
        """Should block Read tool attempting to read secret files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            # Try to read .env (secret file)
            payload = {
                "tool_name": "Read",
                "tool_input": {"file_path": str(tmppath / ".env")},
                "cwd": str(tmppath),
            }

            # Hook should block this
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should return error
                assert exit_code != 0

    def test_bash_tool_with_safe_command(self):
        """Should allow Bash tool with safe commands."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            payload = {
                "tool_name": "Bash",
                "tool_input": {"command": "ls -la"},
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should succeed
                assert exit_code == 0

    def test_edit_tool_normalization(self):
        """Should process Edit tool inputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            # Create a test file
            test_file = tmppath / "app.py"
            test_file.write_text("def hello():\n    pass")

            payload = {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": str(test_file),
                    "old_string": "def hello():",
                    "new_string": "def greet():",
                },
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should succeed or return advisory
                assert exit_code in (0, 1)

    def test_write_tool_normalization(self):
        """Should process Write tool inputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            payload = {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(tmppath / "new_file.py"),
                    "content": "print('hello')",
                },
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should succeed
                assert exit_code == 0

    def test_write_tool_missing_file_path(self):
        """Should flag Write tool missing required file_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            payload = {
                "tool_name": "Write",
                "tool_input": {
                    "content": "print('hello')",
                    # Missing file_path
                },
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should return error
                assert exit_code != 0

    def test_empty_payload(self):
        """Should reject empty payload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            with patch("sys.stdin") as mock_stdin, patch("sys.stdout"):
                mock_stdin.read.return_value = ""
                # Should return error for empty payload
                exit_code = preflight_main()
                assert exit_code != 0

    def test_invalid_json_payload(self):
        """Should reject invalid JSON payload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            with patch("sys.stdin") as mock_stdin, patch("sys.stderr"):
                mock_stdin.read.return_value = "not valid json"
                exit_code = preflight_main()
                # Should return error
                assert exit_code != 0

    def test_glob_tool_normalization(self):
        """Should process Glob tool inputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            payload = {
                "tool_name": "Glob",
                "tool_input": {
                    "pattern": "**/*.py",
                    "path": str(tmppath),
                },
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should succeed
                assert exit_code == 0

    def test_grep_tool_normalization(self):
        """Should process Grep tool inputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            payload = {
                "tool_name": "Grep",
                "tool_input": {
                    "pattern": "def.*:",
                    "path": str(tmppath),
                },
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should succeed
                assert exit_code == 0

    def test_path_traversal_protection(self):
        """Should block path traversal attempts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            payload = {
                "tool_name": "Read",
                "tool_input": {"file_path": "../../etc/passwd"},
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should block path traversal
                assert exit_code != 0

    @pytest.mark.xfail(reason="git add -f blocking logic not yet implemented")
    def test_git_add_force_blocked(self):
        """Should block git add -f (force-add bypasses gitignore)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            payload = {
                "tool_name": "Bash",
                "tool_input": {"command": "git add -f secrets.json"},
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should block force-add
                assert exit_code != 0

    def test_git_add_wildcard_blocked(self):
        """Should block git add with wildcards."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            payload = {
                "tool_name": "Bash",
                "tool_input": {"command": "git add *.py"},
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should block wildcard staging
                assert exit_code != 0

    def test_skip_environment_with_git_blocked(self):
        """Should block SKIP=1 with git commit (hook bypass)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            payload = {
                "tool_name": "Bash",
                "tool_input": {"command": "SKIP=1 git commit -m 'test'"},
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should block hook-bypass environment variables
                assert exit_code != 0

    def test_husky_environment_with_git_blocked(self):
        """Should block HUSKY=1 with git push (hook bypass)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            payload = {
                "tool_name": "Bash",
                "tool_input": {"command": "HUSKY=0 git push origin main"},
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should block hook-bypass environment variables
                assert exit_code != 0

    def test_lefthook_environment_with_git_blocked(self):
        """Should block LEFTHOOK=1 with git commands (hook bypass)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()

            payload = {
                "tool_name": "Bash",
                "tool_input": {"command": "LEFTHOOK=0 git commit -m 'test'"},
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should block hook-bypass environment variables
                assert exit_code != 0

    def test_git_add_safe_exact_file(self):
        """Should allow git add with exact file (no bypasses)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()
            (tmppath / "app.py").write_text("pass")

            payload = {
                "tool_name": "Bash",
                "tool_input": {"command": "git add app.py"},
                "cwd": str(tmppath),
            }

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps(payload)
                exit_code = preflight_main()
                # Should succeed: exact file staging is safe
                assert exit_code == 0
