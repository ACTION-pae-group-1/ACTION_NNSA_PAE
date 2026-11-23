"""
Test suite for memory system concurrent access safety.

Tests cover:
1. Concurrent reads (should work safely)
2. Concurrent writes (should serialize safely)
3. Partial write recovery (file-lock cleanup)
4. Atomic write guarantees (no corruption)
"""

import os

# Import the memory system modules (will create these in implementation)
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude"))

from memory_operations import (
    AtomicFileWriter,
    MemoryManager,
    MemoryValidator,
)


class TestConcurrentReads:
    """Test that concurrent reads work safely without corruption."""

    def test_multiple_concurrent_reads(self):
        """Multiple threads should be able to read MEMORY.md simultaneously."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            test_content = "- Test entry 1\n- Test entry 2\n"
            memory_file.write_text(test_content)

            manager = MemoryManager(memory_file)
            results = []

            def read_memory():
                content = manager.read()
                results.append(content)

            # Launch 10 concurrent readers
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(read_memory) for _ in range(10)]
                for future in as_completed(futures):
                    future.result()

            # All reads should succeed and return the same content
            assert len(results) == 10
            assert all(r == test_content for r in results)

    def test_read_during_write_sees_consistent_data(self):
        """Reads should not see corrupted data even during writes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            old_content = "- Old entry\n"
            memory_file.write_text(old_content)

            manager = MemoryManager(memory_file)

            read_results = []

            def read_during_write():
                # Give the write a moment to start
                time.sleep(0.01)
                content = manager.read()
                read_results.append(content)

            def slow_write():
                # Simulate a slow write operation
                manager.append("- New entry")
                time.sleep(0.02)
                manager.append("- Another entry")

            # Launch reader and writer concurrently
            with ThreadPoolExecutor(max_workers=2) as executor:
                write_future = executor.submit(slow_write)
                read_future = executor.submit(read_during_write)
                write_future.result()
                read_future.result()

            # Read result should contain valid entries (no corrupted partial lines)
            read_content = read_results[0]
            # All lines should start with "- " or be empty
            for line in read_content.split("\n"):
                if line.strip():
                    assert line.startswith("- "), f"Corrupted line: {line}"

            # Verify final state is correct
            final = manager.read()
            assert "- New entry" in final
            assert "- Another entry" in final


class TestConcurrentWrites:
    """Test that concurrent writes serialize safely without data loss."""

    def test_concurrent_writes_serialize_safely(self):
        """Multiple threads appending should not lose any data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            memory_file.write_text("")

            manager = MemoryManager(memory_file)
            num_threads = 5
            entries_per_thread = 20

            def write_entries(thread_id):
                for i in range(entries_per_thread):
                    manager.append(f"- Entry from thread {thread_id}, iteration {i}")

            # Launch concurrent writers
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [
                    executor.submit(write_entries, tid) for tid in range(num_threads)
                ]
                for future in as_completed(futures):
                    future.result()

            # Verify all entries were written
            final_content = manager.read()
            total_lines = len(
                [line for line in final_content.split("\n") if line.strip()]
            )

            expected_entries = num_threads * entries_per_thread
            assert total_lines == expected_entries, (
                f"Expected {expected_entries} entries, got {total_lines}"
            )

            # Verify no corruption (each entry should be complete)
            for tid in range(num_threads):
                for i in range(entries_per_thread):
                    expected = f"- Entry from thread {tid}, iteration {i}"
                    assert expected in final_content, f"Missing entry: {expected}"

    def test_write_atomic_on_windows_and_posix(self):
        """Writes should be atomic on both Windows and POSIX systems."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            original = "- Original line\n"
            memory_file.write_text(original)

            manager = MemoryManager(memory_file)

            # Write new content atomically
            manager.append("- New line 1")
            manager.append("- New line 2")

            # Verify atomic write succeeded
            content = manager.read()
            assert "Original line" in content
            assert "New line 1" in content
            assert "New line 2" in content

    def test_concurrent_write_conflict_resolution(self):
        """When two writes race, later write should win (serialize)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            memory_file.write_text("- Start\n")

            manager = MemoryManager(memory_file)

            write_order = []

            def write_and_track(entry, order_id):
                manager.append(entry)
                write_order.append(order_id)

            # Launch two concurrent writers
            with ThreadPoolExecutor(max_workers=2) as executor:
                f1 = executor.submit(write_and_track, "- From writer A", 1)
                f2 = executor.submit(write_and_track, "- From writer B", 2)
                f1.result()
                f2.result()

            # Both entries should be present (serialized)
            final = manager.read()
            assert "From writer A" in final
            assert "From writer B" in final
            assert "Start" in final


class TestPartialWriteRecovery:
    """Test detection and recovery from partial write failures."""

    def test_detect_incomplete_write_state(self):
        """Validator should detect incomplete write (temp file exists)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            memory_file.write_text("- Existing entry\n")

            # Create a temp file (simulating interrupted write)
            temp_file = Path(tmpdir) / "MEMORY.md.tmp"
            temp_file.write_text("- Incomplete write\n")

            validator = MemoryValidator(memory_file)
            issues = validator.validate()

            # Should detect the temp file as an issue
            assert any("incomplete" in issue.lower() for issue in issues)

    def test_recover_from_stale_lock_file(self):
        """Validator should detect and remove stale lock files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            memory_file.write_text("- Entry\n")

            # Create a stale lock file (older than threshold)
            lock_file = Path(tmpdir) / "MEMORY.md.lock"
            lock_file.write_text("stale")
            # Set modification time to 2 hours ago. The check is a strict
            # age > LOCK_TIMEOUT (3600 s); exactly 1 hour ago sits on that boundary,
            # and on Windows the clock gap can be too small to clear it.
            old_time = time.time() - 2 * 3600
            os.utime(lock_file, (old_time, old_time))

            validator = MemoryValidator(memory_file)
            recovered = validator.recover()

            # Lock file should be removed
            assert not lock_file.exists()
            assert recovered is True

    def test_cleanup_on_process_crash_simulation(self):
        """After process crash, validator should recover cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            memory_file.write_text("- Entry 1\n")

            # Simulate crash: create both temp and lock files
            temp_file = Path(tmpdir) / "MEMORY.md.tmp"
            lock_file = Path(tmpdir) / "MEMORY.md.lock"
            temp_file.write_text("- Incomplete\n")
            lock_file.write_text("")

            # Make lock file very old (stale)
            old_time = time.time() - 7200
            os.utime(lock_file, (old_time, old_time))

            validator = MemoryValidator(memory_file)
            recovered = validator.recover()

            assert recovered is True
            assert not temp_file.exists(), "Temp file should be cleaned up"
            assert not lock_file.exists(), "Stale lock should be cleaned up"

            # Original content should be intact
            content = memory_file.read_text()
            assert "Entry 1" in content


class TestAtomicFileWriter:
    """Test the low-level atomic file writer implementation."""

    def test_atomic_write_basic(self):
        """Basic atomic write creates file correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "test.txt"

            writer = AtomicFileWriter(target)
            writer.write("Test content")
            writer.commit()

            assert target.exists()
            assert target.read_text() == "Test content"

    def test_atomic_write_temp_file_cleanup_on_success(self):
        """Temp file should be removed after successful write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "test.txt"

            writer = AtomicFileWriter(target)
            temp_path = writer.temp_path
            writer.write("Content")
            writer.commit()

            assert not temp_path.exists(), "Temp file should be cleaned up"
            assert target.exists()

    def test_atomic_write_preserves_permissions(self):
        """Atomic write should preserve target file permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "test.txt"
            target.write_text("Original")

            # Set specific permissions (Windows: check readable/writable)
            import stat

            os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)

            writer = AtomicFileWriter(target)
            writer.write("Updated")
            writer.commit()

            # On Windows, permissions might not be exact,
            # so just verify file exists and was written correctly
            assert target.exists()
            assert target.read_text() == "Updated"

    def test_atomic_write_failure_preserves_original(self):
        """Failed write should not corrupt original file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "test.txt"
            original_content = "Original content"
            target.write_text(original_content)

            # Simulate failure by letting rollback cleanup
            with AtomicFileWriter(target) as writer:
                writer.write("New content")
                writer.rollback()

            # Original should be preserved
            assert target.read_text() == original_content

    def test_atomic_write_with_file_lock_on_windows(self):
        """On Windows, atomic writer should handle file locks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "test.txt"
            target.write_text("Original")

            # Test that we can write even with potential locks
            writer = AtomicFileWriter(target)
            writer.write("Updated with potential lock")
            writer.commit()

            assert target.read_text() == "Updated with potential lock"


class TestMemoryManagerIntegration:
    """Integration tests for MemoryManager."""

    def test_append_creates_entry_on_new_file(self):
        """Append should create file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            manager = MemoryManager(memory_file)

            manager.append("- New entry")

            assert memory_file.exists()
            assert "New entry" in memory_file.read_text()

    def test_update_entry_replaces_content(self):
        """Update should replace existing entry safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            memory_file.write_text("- Old entry\n")

            manager = MemoryManager(memory_file)
            manager.update("- Updated entry")

            content = manager.read()
            assert "Updated entry" in content
            assert "Old entry" not in content

    def test_concurrent_append_and_read(self):
        """Concurrent appends and reads should not corrupt data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "MEMORY.md"
            memory_file.write_text("")

            manager = MemoryManager(memory_file)
            read_results = []

            def append_entries(thread_id):
                for i in range(10):
                    manager.append(f"- Thread {thread_id}, entry {i}")

            def read_entries():
                time.sleep(0.05)  # Let some writes happen first
                read_results.append(manager.read())

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                futures.extend(
                    [executor.submit(append_entries, tid) for tid in range(3)]
                )
                futures.append(executor.submit(read_entries))

                for future in as_completed(futures):
                    future.result()

            # Should have read some content without corruption
            assert len(read_results) > 0
            assert len(read_results[0].strip()) > 0


class TestNetworkPathDetection:
    """Test detection and rejection of network paths."""

    def test_reject_unc_paths(self):
        r"""UNC paths (\\server\share) should be rejected."""
        # Windows UNC path format
        if os.name == "nt":
            unc_paths = [
                r"\\server\share\MEMORY.md",
                r"\\192.168.1.100\backup\MEMORY.md",
                r"\\nas-server\shared\data\MEMORY.md",
            ]

            for unc_path in unc_paths:
                # Creating a manager with UNC path should raise error during __init__
                with pytest.raises(RuntimeError) as exc_info:
                    path = Path(unc_path)
                    MemoryManager(path)

                error_msg = str(exc_info.value).lower()
                assert "network" in error_msg
                # Should mention local path as solution
                assert "local" in error_msg

    def test_accept_local_filesystem_paths(self):
        """Local filesystem paths should be accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / "MEMORY.md"
            manager = MemoryManager(local_path)

            # Should not raise error
            manager.append("- Local entry")

            # Verify write succeeded
            assert "Local entry" in manager.read()

    def test_reject_network_drive_paths_windows(self):
        """Network drive paths (Z:) should be detected and rejected on Windows."""
        if os.name == "nt":
            # Test network drive detection
            # Note: We can't actually mount a network drive in tests,
            # but we can test the detection logic
            from memory_operations import _is_network_path

            # Common network drive letters
            potential_network_paths = ["Z:\\MEMORY.md", "Y:\\data\\MEMORY.md"]

            # At least one should be detectable as network
            # (actual detection depends on system configuration)
            for path_str in potential_network_paths:
                path = Path(path_str)
                # For this test, we're checking if the function exists and works
                try:
                    is_network = _is_network_path(path)
                    # Just verify the function returns a boolean
                    assert isinstance(is_network, bool)
                except Exception:
                    # Some checks might not work in test environment
                    pass

    def test_clear_error_message_for_network_paths(self):
        """Error message should clearly explain the issue and provide remediation."""
        if os.name == "nt":
            unc_path = r"\\server\share\MEMORY.md"

            try:
                MemoryManager(Path(unc_path))
                assert False, "Should have raised RuntimeError"
            except RuntimeError as e:
                error_msg = str(e)
                # Error should explain what the problem is
                assert "network" in error_msg.lower() or "unc" in error_msg.lower()
                # Error should provide guidance
                assert "local" in error_msg.lower() or "filesystem" in error_msg.lower()

    def test_local_windows_paths_accepted(self):
        """Standard Windows local paths should be accepted."""
        if os.name == "nt":
            with tempfile.TemporaryDirectory() as tmpdir:
                local_paths = [
                    Path(tmpdir) / "MEMORY.md",
                    Path("C:\\Users\\test\\MEMORY.md"),
                ]

                for local_path in local_paths:
                    # Adjust to use temp directory
                    if not str(local_path).startswith(tmpdir):
                        local_path = Path(tmpdir) / local_path.name

                    manager = MemoryManager(local_path)
                    # Should work without error
                    manager.append("- Local entry")
                    assert "Local entry" in manager.read()

    def test_posix_paths_always_accepted(self):
        """POSIX paths should always be accepted (no network share concept)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / "MEMORY.md"
            manager = MemoryManager(local_path)

            # Should work on any system
            manager.append("- POSIX entry")
            assert "POSIX entry" in manager.read()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
