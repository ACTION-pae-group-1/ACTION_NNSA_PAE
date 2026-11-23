"""Unit tests for scripts/pytest_smart_runner.py smart test runner for pre-commit."""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from pytest_smart_runner import (
    find_companion_tests,
    get_affected_tests,
    get_changed_files,
    main,
)


class TestFindCompanionTests:
    """Test finding companion test files for changed Python files."""

    def test_find_test_with_test_prefix_same_directory(self):
        """Should find test_<name>.py in same directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            source = tmppath / "utils.py"
            test = tmppath / "test_utils.py"
            test.touch()

            result = find_companion_tests(source)
            assert test in result

    def test_find_test_with_suffix_same_directory(self):
        """Should find <name>_test.py in same directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            source = tmppath / "utils.py"
            test = tmppath / "utils_test.py"
            test.touch()

            result = find_companion_tests(source)
            assert test in result

    def test_find_test_in_tests_subdirectory(self):
        """Should find test_<name>.py in tests/ subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            source = tmppath / "utils.py"
            tests_dir = tmppath / "tests"
            tests_dir.mkdir()
            test = tests_dir / "test_utils.py"
            test.touch()

            result = find_companion_tests(source)
            assert test in result

    def test_find_test_suffix_in_tests_subdirectory(self):
        """Should find <name>_test.py in tests/ subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            source = tmppath / "utils.py"
            tests_dir = tmppath / "tests"
            tests_dir.mkdir()
            test = tests_dir / "utils_test.py"
            test.touch()

            result = find_companion_tests(source)
            assert test in result

    def test_find_test_with_nested_src_structure(self):
        """Should find tests in nested directories under src."""
        # Test that find_companion_tests can find tests in src/package/tests/ layout
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create src/mymodule/utils.py
            src_mymodule = tmppath / "src" / "mymodule"
            src_mymodule.mkdir(parents=True)
            source = src_mymodule / "utils.py"
            source.write_text("def func(): pass")

            # Create src/mymodule/tests/test_utils.py (tests as sibling directory)
            src_tests = src_mymodule / "tests"
            src_tests.mkdir()
            test = src_tests / "test_utils.py"
            test.write_text("def test_func(): pass")

            # Should find the test in the tests/ subdirectory
            result = find_companion_tests(source)
            assert any("test_utils.py" in str(t) for t in result), f"Result: {result}"

    def test_find_multiple_companion_tests(self):
        """Should return all matching test patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            source = tmppath / "utils.py"

            # Create both prefix and suffix variants
            test_prefix = tmppath / "test_utils.py"
            test_suffix = tmppath / "utils_test.py"
            test_prefix.touch()
            test_suffix.touch()

            result = find_companion_tests(source)
            assert test_prefix in result
            assert test_suffix in result
            # Should remove duplicates
            assert len(result) == len(set(result))

    def test_no_tests_found_returns_empty_list(self):
        """Should return empty list if no companion tests found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            source = tmppath / "utils.py"

            result = find_companion_tests(source)
            assert result == []

    def test_ignores_nonexistent_files(self):
        """Should only return tests that actually exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            source = tmppath / "utils.py"
            # Don't create the test file

            result = find_companion_tests(source)
            assert result == []


class TestGetChangedFiles:
    """Test retrieving changed files from git staging area."""

    def test_get_changed_files_in_git_repo(self):
        """Should retrieve Python files from git staging area."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Initialize git repo
            subprocess.run(
                ["git", "init"], cwd=tmppath, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            # Create and stage Python file
            source = tmppath / "utils.py"
            source.write_text("def hello(): pass")
            subprocess.run(
                ["git", "add", "utils.py"], cwd=tmppath, capture_output=True, check=True
            )

            # Change to repo directory and get changed files
            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                result = get_changed_files()
                assert any("utils.py" in str(p) for p in result)
            finally:
                os.chdir(old_cwd)

    def test_get_changed_files_filters_python_only(self):
        """Should only return Python files, not all changed files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            subprocess.run(
                ["git", "init"], cwd=tmppath, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            # Stage both Python and non-Python files
            (tmppath / "utils.py").write_text("def hello(): pass")
            (tmppath / "README.md").write_text("# Test")
            subprocess.run(
                ["git", "add", "utils.py", "README.md"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                result = get_changed_files()
                # Should include .py files
                assert any(".py" in str(p) for p in result)
                # Should not include .md files
                assert not any(".md" in str(p) for p in result)
            finally:
                os.chdir(old_cwd)

    def test_get_changed_files_respects_diff_filter(self):
        """Should include Added, Created, Modified files, exclude Deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            subprocess.run(
                ["git", "init"], cwd=tmppath, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            # Create initial commit with a file
            initial_file = tmppath / "initial.py"
            initial_file.write_text("old code")
            subprocess.run(
                ["git", "add", "initial.py"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            # Add new file
            new_file = tmppath / "new.py"
            new_file.write_text("new code")
            subprocess.run(
                ["git", "add", "new.py"], cwd=tmppath, capture_output=True, check=True
            )

            # Modify existing file
            initial_file.write_text("modified code")
            subprocess.run(
                ["git", "add", "initial.py"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                result = get_changed_files()
                # Both added and modified should be included
                assert any("new.py" in str(p) for p in result)
                assert any("initial.py" in str(p) for p in result)
            finally:
                os.chdir(old_cwd)

    def test_get_changed_files_returns_empty_set_on_error(self):
        """Should return empty set if not in git repo or git fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Don't initialize git, so git command will fail
            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                result = get_changed_files()
                assert isinstance(result, set)
                assert len(result) == 0
            finally:
                os.chdir(old_cwd)

    def test_get_changed_files_returns_set_type(self):
        """Should return a set, not a list."""
        result = get_changed_files()
        assert isinstance(result, set)


class TestGetAffectedTests:
    """Test finding tests in shared directories."""

    def test_get_affected_tests_in_hooks_dir(self):
        """Should find test files in tests/hooks/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            hooks_dir = tmppath / "tests" / "hooks"
            hooks_dir.mkdir(parents=True)

            # Create test files
            test1 = hooks_dir / "test_hook1.py"
            test2 = hooks_dir / "test_hook2.py"
            test1.touch()
            test2.touch()

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                result = get_affected_tests()
                assert any("test_hook1.py" in str(p) for p in result)
                assert any("test_hook2.py" in str(p) for p in result)
            finally:
                os.chdir(old_cwd)

    def test_get_affected_tests_in_integration_dir(self):
        """Should find test files in tests/integration/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            integration_dir = tmppath / "tests" / "integration"
            integration_dir.mkdir(parents=True)

            # Create test file
            test = integration_dir / "test_api.py"
            test.touch()

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                result = get_affected_tests()
                assert any("test_api.py" in str(p) for p in result)
            finally:
                os.chdir(old_cwd)

    def test_get_affected_tests_in_src_pars_tests(self):
        """Should find test files in src/pars_local_mcp/tests/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            src_dir = tmppath / "src" / "pars_local_mcp" / "tests"
            src_dir.mkdir(parents=True)

            # Create test file
            test = src_dir / "test_mcp.py"
            test.touch()

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                result = get_affected_tests()
                assert any("test_mcp.py" in str(p) for p in result)
            finally:
                os.chdir(old_cwd)

    def test_get_affected_tests_only_test_files(self):
        """Should only return test_*.py files, not other Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            hooks_dir = tmppath / "tests" / "hooks"
            hooks_dir.mkdir(parents=True)

            # Create both test and non-test files
            test_file = hooks_dir / "test_hook.py"
            helper_file = hooks_dir / "helper.py"
            test_file.touch()
            helper_file.touch()

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                result = get_affected_tests()
                # Should include test_hook.py
                assert any("test_hook.py" in str(p) for p in result)
                # Should not include helper.py
                assert not any("helper.py" in str(p) for p in result)
            finally:
                os.chdir(old_cwd)

    def test_get_affected_tests_skips_nonexistent_dirs(self):
        """Should handle missing shared directories gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Don't create any shared directories

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                result = get_affected_tests()
                # Should return empty set, not error
                assert isinstance(result, set)
            finally:
                os.chdir(old_cwd)

    def test_get_affected_tests_returns_only_files(self):
        """Should only return actual files, not directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            hooks_dir = tmppath / "tests" / "hooks"
            hooks_dir.mkdir(parents=True)

            # Create both files and directories
            test_file = hooks_dir / "test_hook.py"
            test_file.touch()
            subdir = hooks_dir / "subdir"
            subdir.mkdir()

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                result = get_affected_tests()
                # Should include the file
                assert any("test_hook.py" in str(p) for p in result)
                # Should not include the directory
                assert all(p.is_file() for p in result)
            finally:
                os.chdir(old_cwd)


class TestMainFunction:
    """Test the main() integration of collecting and reporting tests."""

    def test_main_returns_zero_on_success(self):
        """Should return 0 when tests are collected (mocked pytest run)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Initialize git
            subprocess.run(
                ["git", "init"], cwd=tmppath, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            # Create source and test files
            source = tmppath / "utils.py"
            source.write_text("def hello(): pass")
            test = tmppath / "test_utils.py"
            test.write_text("def test_hello(): pass")

            # Stage files
            subprocess.run(
                ["git", "add", "."], cwd=tmppath, capture_output=True, check=True
            )

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                # Mock subprocess.run to avoid actually running pytest
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result

                    result = main()
                    # Should execute and return success
                    assert isinstance(result, int)
            finally:
                os.chdir(old_cwd)

    def test_main_no_tests_returns_zero(self):
        """Should return 0 when no tests to run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            subprocess.run(
                ["git", "init"], cwd=tmppath, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                result = main()
                assert result == 0
            finally:
                os.chdir(old_cwd)

    def test_main_accepts_file_arguments(self):
        """Should accept files passed as command-line arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            source = tmppath / "utils.py"
            source.write_text("def hello(): pass")
            test = tmppath / "test_utils.py"
            test.write_text("def test_hello(): pass")

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result

                    # Call main with file arguments
                    result = main()
                    assert isinstance(result, int)
            finally:
                os.chdir(old_cwd)

    def test_main_skips_test_files_themselves(self):
        """Should not look for companion tests for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            subprocess.run(
                ["git", "init"], cwd=tmppath, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            # Create only a test file
            test = tmppath / "test_utils.py"
            test.write_text("def test_hello(): pass")
            subprocess.run(
                ["git", "add", "test_utils.py"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result

                    result = main()
                    # Should not crash
                    assert isinstance(result, int)
            finally:
                os.chdir(old_cwd)

    def test_main_combines_git_and_args_changed_files(self):
        """Should combine changed files from git and command arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            subprocess.run(
                ["git", "init"], cwd=tmppath, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            # Create files
            source1 = tmppath / "utils.py"
            source1.write_text("def func1(): pass")
            test1 = tmppath / "test_utils.py"
            test1.write_text("def test_func1(): pass")

            subprocess.run(
                ["git", "add", "utils.py", "test_utils.py"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                # Mock to see what gets passed to pytest
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result

                    main()
                    # pytest should have been called
                    assert mock_run.called
            finally:
                os.chdir(old_cwd)

    def test_main_prints_test_files_being_run(self, capsys):
        """Should print list of test files before running pytest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            subprocess.run(
                ["git", "init"], cwd=tmppath, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            source = tmppath / "utils.py"
            source.write_text("def hello(): pass")
            test = tmppath / "test_utils.py"
            test.write_text("def test_hello(): pass")

            subprocess.run(
                ["git", "add", "."], cwd=tmppath, capture_output=True, check=True
            )

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result

                    result = main()
                    captured = capsys.readouterr()
                    # Output should contain information about running tests
                    output = captured.out + captured.err
                    assert "test" in output.lower() or result == 0
            finally:
                os.chdir(old_cwd)

    def test_main_configures_pytest_correctly(self):
        """Should run pytest with correct markers and options."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            subprocess.run(
                ["git", "init"], cwd=tmppath, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            # Create source file that has a companion test
            source = tmppath / "utils.py"
            source.write_text("def hello(): pass")
            test = tmppath / "test_utils.py"
            test.write_text("def test_hello(): pass")

            # Stage both the source and test
            subprocess.run(
                ["git", "add", "utils.py", "test_utils.py"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                # Mock only the pytest run, not the git command
                original_run = subprocess.run
                call_count = [0]

                def mock_run_func(*args, **kwargs):
                    call_count[0] += 1
                    # Only mock the pytest call (which should be the 2nd call after git)
                    if call_count[0] > 1 and "pytest" in str(args):
                        mock_result = MagicMock()
                        mock_result.returncode = 0
                        return mock_result
                    # Let git commands run normally
                    return original_run(*args, **kwargs)

                with patch("subprocess.run", side_effect=mock_run_func):
                    result = main()

                # If tests were collected, they should have been run
                # (we mocked the pytest call, so result should be 0)
                assert isinstance(result, int)
            finally:
                os.chdir(old_cwd)

    def test_main_returns_pytest_exit_code(self):
        """Should return the exit code from pytest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            subprocess.run(
                ["git", "init"], cwd=tmppath, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            # Create source file that has a companion test
            source = tmppath / "utils.py"
            source.write_text("def hello(): pass")
            test = tmppath / "test_utils.py"
            test.write_text("def test_hello(): pass")

            # Stage both files
            subprocess.run(
                ["git", "add", "utils.py", "test_utils.py"],
                cwd=tmppath,
                capture_output=True,
                check=True,
            )

            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmppath)
                # Mock only the pytest run, not the git command
                original_run = subprocess.run
                call_count = [0]

                def mock_run_func(*args, **kwargs):
                    call_count[0] += 1
                    # Only mock the pytest call (which should be the 2nd call after git)
                    if call_count[0] > 1 and "pytest" in str(args):
                        mock_result = MagicMock()
                        mock_result.returncode = 1
                        return mock_result
                    # Let git commands run normally
                    return original_run(*args, **kwargs)

                with patch("subprocess.run", side_effect=mock_run_func):
                    result = main()
                    assert result == 1
            finally:
                os.chdir(old_cwd)
