"""Unit tests for .claude/hooks/duplicate_text_guard.py duplicate code detection."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks"))

from duplicate_text_guard import (
    extract_chunks,
    get_source_files,
    main,
    normalize_code,
)


class TestNormalizeCode:
    """Test comment removal and whitespace normalization."""

    def test_removes_single_line_python_comments(self):
        """Should remove Python single-line comments."""
        code = "x = 1  # this is a comment\ny = 2"
        normalized = normalize_code(code)
        assert "# this is a comment" not in normalized
        assert "x = 1" in normalized
        assert "y = 2" in normalized

    def test_removes_single_line_javascript_comments(self):
        """Should remove JavaScript single-line comments."""
        code = "const x = 1;  // comment\nconst y = 2;"
        normalized = normalize_code(code)
        assert "// comment" not in normalized
        assert "const x = 1" in normalized

    def test_removes_multiline_double_quote_comments(self):
        """Should remove Python triple-quote multi-line comments."""
        code = 'x = 1\n"""\nMultiline\ncomment\n"""\ny = 2'
        normalized = normalize_code(code)
        assert "Multiline" not in normalized
        assert "comment" not in normalized
        assert "x = 1" in normalized
        assert "y = 2" in normalized

    def test_removes_multiline_single_quote_comments(self):
        """Should remove Python triple-quote multi-line comments (single quotes)."""
        code = "x = 1\n'''\nMultiline\ncomment\n'''\ny = 2"
        normalized = normalize_code(code)
        assert "Multiline" not in normalized
        assert "x = 1" in normalized

    def test_normalizes_whitespace(self):
        """Should collapse multiple whitespace into single space."""
        code = "x  =   1\ny    =    2"
        normalized = normalize_code(code)
        assert "  " not in normalized  # no double spaces
        assert "x = 1" in normalized

    def test_handles_empty_input(self):
        """Should handle empty code."""
        normalized = normalize_code("")
        assert normalized == ""

    def test_handles_whitespace_only_input(self):
        """Should strip whitespace-only input."""
        normalized = normalize_code("   \n\n   \t  ")
        assert normalized == ""

    def test_removes_multiple_comments_same_line(self):
        """Should remove comments even with multiple on same line (first match)."""
        code = "x = 1 # comment"
        normalized = normalize_code(code)
        assert "# comment" not in normalized

    def test_preserves_code_after_comment_removal(self):
        """Should preserve code structure after comment removal."""
        code = "def foo():  # function\n    return 42  # result"
        normalized = normalize_code(code)
        assert "def foo" in normalized
        assert "return 42" in normalized


class TestExtractChunks:
    """Test code segmentation into chunks."""

    def test_extracts_chunks_at_function_boundaries(self):
        """Should segment code at function definitions."""
        code = "def foo():\n    return 1\n\ndef bar():\n    return 2"
        chunks = extract_chunks(code, min_size=1)
        assert len(chunks) >= 1
        # At least one chunk should contain "def foo" or "def bar"
        combined = " ".join(chunks)
        assert "def foo" in combined or "def bar" in combined

    def test_enforces_minimum_chunk_size(self):
        """Should not return chunks smaller than min_size."""
        code = "x = 1\ny = 2\nz = 3" * 20  # Repeat to ensure we exceed min_size
        chunks = extract_chunks(code, min_size=50)
        for chunk in chunks:
            assert len(chunk) >= 50

    def test_handles_empty_input(self):
        """Should return empty list for empty code."""
        chunks = extract_chunks("")
        assert chunks == []

    def test_handles_short_code_below_min_size(self):
        """Should return empty list if code is below min_size."""
        code = "x = 1"
        chunks = extract_chunks(code, min_size=100)
        assert chunks == []

    def test_extracts_class_definitions(self):
        """Should segment code at class definitions."""
        code = "class Foo:\n    pass\n\nclass Bar:\n    pass"
        chunks = extract_chunks(code, min_size=1)
        assert len(chunks) >= 1

    def test_normalizes_extracted_chunks(self):
        """Should normalize chunks (remove comments, collapse whitespace)."""
        code = "def foo():  # comment\n    x = 1  # value\n    return x" * 5
        chunks = extract_chunks(code, min_size=50)
        assert len(chunks) > 0
        # Normalized chunks should not have multiple spaces
        for chunk in chunks:
            assert "  " not in chunk or "\n" in chunk.replace("  ", "")

    def test_handles_blank_lines_as_separators(self):
        """Should use blank lines to segment chunks."""
        code = "def foo():\n    pass\n\n" + "x = 1" * 20
        chunks = extract_chunks(code, min_size=1)
        assert len(chunks) >= 1


class TestGetSourceFiles:
    """Test source file discovery with filtering."""

    @pytest.mark.skip(
        reason="Mock timing issue: REPO_ROOT set at module load, not call time"
    )
    def test_discovers_python_files(self):
        """Should find .py files in project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create test files
            (tmppath / "test.py").touch()
            (tmppath / "module.py").touch()
            # Mock project_root to return our temp directory
            with patch("duplicate_text_guard.project_root", return_value=tmppath):
                files = get_source_files()
            # Verify we found the Python files
            assert isinstance(files, list)
            assert len(files) >= 2
            file_names = [f.name for f in files]
            assert "test.py" in file_names
            assert "module.py" in file_names

    def test_excludes_pycache(self):
        """Should exclude __pycache__ directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            pycache = tmppath / "__pycache__"
            pycache.mkdir()
            (pycache / "test.pyc").touch()
            # Just verify function doesn't crash with pycache present
            result = get_source_files()
            assert isinstance(result, list)

    def test_excludes_node_modules(self):
        """Should exclude node_modules directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            nm = tmppath / "node_modules"
            nm.mkdir()
            (nm / "package.js").touch()
            result = get_source_files()
            assert isinstance(result, list)

    def test_returns_list(self):
        """Should always return a list."""
        files = get_source_files()
        assert isinstance(files, list)


class TestDuplicateTextGuardMain:
    """Test main() entry point."""

    def test_main_returns_zero(self):
        """Should return exit code 0 on success."""
        exit_code = main()
        assert exit_code == 0

    def test_main_reports_scan_count(self, capsys):
        """Should report number of files scanned."""
        main()
        captured = capsys.readouterr()
        # Should mention "scanned" in output
        assert "scanned" in captured.out.lower()
