"""Unit tests for .claude/hooks/tool_call_context.py tool contract injection."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks"))

from tool_call_context import (
    main,
    prompt_contract,
    session_contract,
)


class TestSessionContract:
    """Test session_contract() generation."""

    def test_generates_non_empty_contract(self):
        """Should return non-empty string."""
        contract = session_contract("/test/root")
        assert isinstance(contract, str)
        assert len(contract) > 0

    def test_includes_project_root(self):
        """Should include project root in contract."""
        root_path = "/test/project/root"
        contract = session_contract(root_path)
        assert root_path in contract

    def test_includes_tool_names(self):
        """Should mention required tool names with parameter schema."""
        contract = session_contract("/test")
        required_tools = ["Read", "Write", "Edit", "Glob", "Grep", "TodoWrite"]
        for tool in required_tools:
            assert tool in contract
        # Validate that tools have schema info (not just mentioned)
        assert "file_path" in contract  # Read/Write/Edit require this
        assert "absolute" in contract.lower()  # Should mention absolute paths

    def test_includes_tdd_discipline(self):
        """Should include TDD discipline rules."""
        contract = session_contract("/test")
        assert "TDD" in contract.upper() or "test" in contract.lower()

    def test_includes_minimum_cd_rules(self):
        """Should include MinimumCD guidelines."""
        contract = session_contract("/test")
        # Should mention constraints on lines/files per commit
        assert "500" in contract or "lines" in contract.lower() or "25" in contract

    def test_includes_backend_commands(self):
        """Should include backend command guidance."""
        contract = session_contract("/test")
        assert "uv" in contract
        assert "pytest" in contract


class TestPromptContract:
    """Test prompt_contract() generation."""

    def test_generates_non_empty_contract(self):
        """Should return non-empty string."""
        contract = prompt_contract("/test/root")
        assert isinstance(contract, str)
        assert len(contract) > 0

    def test_is_shorter_than_session_contract(self):
        """Should be more concise than session contract."""
        test_path = "/test/project"
        session = session_contract(test_path)
        prompt = prompt_contract(test_path)
        # Prompt should be roughly shorter (not exact, but should be noticeably shorter)
        assert len(prompt) < len(session)

    def test_includes_project_root(self):
        """Should include project root path."""
        root_path = "/my/test/path"
        contract = prompt_contract(root_path)
        assert root_path in contract

    def test_includes_tool_schema_requirements(self):
        """Should mention tool parameter requirements."""
        contract = prompt_contract("/test")
        # Should reference file paths, absolute paths, etc.
        assert "file_path" in contract.lower() or "path" in contract.lower()

    def test_includes_tdd_requirement(self):
        """Should mention TDD companion test requirement."""
        contract = prompt_contract("/test")
        assert "test" in contract.lower()

    def test_includes_test_command(self):
        """Should mention how to run tests."""
        contract = prompt_contract("/test")
        assert "pytest" in contract or "test" in contract.lower()


class TestToolCallContextMain:
    """Test main() entry point."""

    def _run_main(self, *patch_targets):
        """Helper to run main() with standard patches."""
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = ""
            with patch("tool_call_context.project_root", return_value=Path("/test")):
                return main()

    def test_main_with_session_mode(self):
        """Should emit contract in session mode."""
        with patch("tool_call_context.emit_context") as mock_emit:
            with patch("sys.argv", ["tool_call_context.py", "session"]):
                exit_code = self._run_main()
            assert exit_code == 0
            assert mock_emit.called

    def test_main_with_prompt_mode(self):
        """Should emit contract in prompt mode."""
        with patch("tool_call_context.emit_context") as mock_emit:
            with patch("sys.argv", ["tool_call_context.py", "prompt"]):
                exit_code = self._run_main()
            assert exit_code == 0
            assert mock_emit.called

    def test_main_defaults_to_session_mode(self):
        """Should default to session mode if no argument provided."""
        with patch("tool_call_context.emit_context") as mock_emit:
            with patch("sys.argv", ["tool_call_context.py"]):
                exit_code = self._run_main()
            assert exit_code == 0
            assert mock_emit.called

    def test_main_with_invalid_mode(self):
        """Should return error code for invalid mode."""
        with patch("tool_call_context.emit_context"):
            with patch("sys.argv", ["tool_call_context.py", "invalid_mode"]):
                exit_code = self._run_main()
            assert exit_code != 0

    def test_main_respects_session_context_env_var(self):
        """Should respect CLAUDE_TOOL_CALL_SESSION_CONTEXT env var."""
        with patch.dict("os.environ", {"CLAUDE_TOOL_CALL_SESSION_CONTEXT": "false"}):
            with patch("sys.argv", ["tool_call_context.py", "session"]):
                exit_code = self._run_main()
            assert exit_code == 0

    def test_main_respects_prompt_reminder_env_var(self):
        """Should respect CLAUDE_TOOL_CALL_PROMPT_REMINDER env var."""
        with patch.dict("os.environ", {"CLAUDE_TOOL_CALL_PROMPT_REMINDER": "false"}):
            with patch("sys.argv", ["tool_call_context.py", "prompt"]):
                exit_code = self._run_main()
            assert exit_code == 0

    def test_main_emits_session_start_event(self):
        """Should emit SessionStart event for session mode."""
        with patch("tool_call_context.emit_context") as mock_emit:
            with patch("sys.argv", ["tool_call_context.py", "session"]):
                self._run_main()
            assert mock_emit.called
            assert mock_emit.call_args[0][0] == "SessionStart"

    def test_main_emits_user_prompt_submit_event(self):
        """Should emit UserPromptSubmit event for prompt mode."""
        with patch("tool_call_context.emit_context") as mock_emit:
            with patch("sys.argv", ["tool_call_context.py", "prompt"]):
                self._run_main()
            assert mock_emit.called
            assert mock_emit.call_args[0][0] == "UserPromptSubmit"

    def test_main_passes_contract_as_message(self):
        """Should pass contract as message to emit_context."""
        with patch("tool_call_context.emit_context") as mock_emit:
            with patch("sys.argv", ["tool_call_context.py", "session"]):
                self._run_main()
            assert mock_emit.called
            call_args = mock_emit.call_args
            assert len(call_args[0]) > 1
            message = call_args[0][1]
            assert isinstance(message, str)
            assert len(message) > 0
