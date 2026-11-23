"""Tests for ruff_fix_and_stage script."""

from unittest import mock

from scripts.ruff_fix_and_stage import main


def test_main_no_arguments():
    """Test main with no arguments returns 0."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)
        result = main([])
        assert result == 0


def test_main_with_files():
    """Test main with file arguments re-stages them."""
    files = ["test.py", "another.py"]
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)
        main(files)
        # Verify git add was called with the files
        git_add_call = [c for c in mock_run.call_args_list if "git" in str(c)]
        assert len(git_add_call) > 0


def test_main_returns_1_on_changes():
    """Test main returns 1 when ruff makes changes."""
    with mock.patch("subprocess.run") as mock_run:
        # All calls return 0 initially, then trigger return 1
        mock_run.side_effect = [
            mock.Mock(returncode=1),  # ruff check
            mock.Mock(returncode=0),  # ruff format
            mock.Mock(returncode=0),  # git add
        ]
        result = main(["test.py"])
        assert result == 1
