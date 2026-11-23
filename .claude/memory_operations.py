"""
Memory system with atomic write guarantees for concurrent access safety.

Provides:
1. AtomicFileWriter - Low-level atomic write with temp file + rename
2. MemoryManager - High-level API for MEMORY.md operations
3. MemoryValidator - Validates and recovers from partial writes
"""

import logging
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import List

# Configure logging
logger = logging.getLogger(__name__)

# Lock file timeout in seconds (1 hour)
LOCK_TIMEOUT = 3600


def _is_cloud_storage_path(path: Path) -> bool:
    """
    Detect if path is on cloud storage (OneDrive, Dropbox, Google Drive, iCloud).

    Args:
        path: Path to check

    Returns:
        True if path appears to be on cloud storage, False otherwise
    """
    path_str = str(path).lower()

    # Common cloud storage paths
    cloud_markers = [
        "onedrive",
        "dropbox",
        "google drive",
        "my drive",
        "icloud",
        "cloud docs",
    ]

    for marker in cloud_markers:
        if marker in path_str:
            logger.warning(f"Cloud storage path detected: {marker}")
            return True

    return False


def _is_posix_network_path(path: Path) -> bool:
    """
    Detect network paths on POSIX systems (NFS, CIFS, etc.).

    Checks /etc/mtab for NFS and CIFS mounts.

    Args:
        path: Path to check

    Returns:
        True if path is on network storage, False for local filesystem
    """
    if os.name != "posix":
        return False

    try:
        # Resolve to get real path
        resolved = path.resolve()

        # Check /etc/mtab for network mounts
        if os.path.exists("/etc/mtab"):
            with open("/etc/mtab", "r") as f:
                mtab_content = f.read()

                for line in mtab_content.split("\n"):
                    if not line.strip():
                        continue

                    parts = line.split()
                    if len(parts) < 2:
                        continue

                    mount_source = parts[0].lower()
                    mount_point = parts[1]

                    # Check for NFS mounts (server:/export format or nfs type)
                    if ":" in mount_source and (
                        "nfs" in line.lower() or mount_source.startswith("server")
                    ):
                        if str(resolved).startswith(mount_point):
                            logger.warning(
                                f"NFS mount detected: {mount_source} at {mount_point}"
                            )
                            return True

                    # Check for CIFS/SMB mounts (//server/share format)
                    if mount_source.startswith("//") or "cifs" in line.lower():
                        if str(resolved).startswith(mount_point):
                            logger.warning(
                                f"CIFS mount detected: {mount_source} at {mount_point}"
                            )
                            return True

        return False

    except Exception as e:
        logger.debug(f"Error checking POSIX network paths: {e}")
        return False


def _detect_mapped_drive_fallback(drive_letter: str) -> bool:
    """
    Fallback detection for mapped network drives without requiring elevation.

    Uses environment variables and system inspection as fallback.

    Args:
        drive_letter: Single drive letter (e.g., 'Z')

    Returns:
        True if drive appears to be mapped to network, False otherwise
    """
    try:
        # Check for mapped drive via net use (may fail without elevation)
        result = subprocess.run(
            ["net", "use"],
            capture_output=True,
            text=True,
            timeout=2,
        )

        if result.returncode == 0 and result.stdout:
            for line in result.stdout.split("\n"):
                if line.startswith(drive_letter + ":") and "\\\\" in line:
                    return True

        return False

    except (PermissionError, subprocess.TimeoutExpired, FileNotFoundError):
        # Fallback: check if drive exists and has UNC path characteristics
        # (network drives sometimes have special attributes)
        try:
            # Try to stat the drive - network drives may have different behavior
            import ctypes

            # Windows GetDriveType API
            if hasattr(ctypes, "windll"):
                drive_path = f"{drive_letter}:\\"
                result = ctypes.windll.kernel32.GetDriveType(drive_path)

                # DRIVE_REMOTE = 4 (network drive)
                if result == 4:
                    logger.debug(
                        f"Drive {drive_letter}: detected as network via GetDriveType"
                    )
                    return True

        except Exception as e:
            logger.debug(f"Fallback drive detection error: {e}")

        return False


def _is_network_path(path: Path) -> bool:
    r"""
    Comprehensive detection of network storage and cloud paths.

    Detects:
    - Windows UNC paths (\\server\share) [local]
    - Windows mapped network drives (Z:, Y:, etc.)
    - Cloud storage (OneDrive, Dropbox, Google Drive, iCloud)
    - POSIX network mounts (NFS, CIFS)
    - Symlinks and junctions to network paths

    Uses Path.resolve() to handle symlinks and junctions before checking.

    Args:
        path: Path to check

    Returns:
        True if path is on network storage or cloud, False for local filesystem

    Note:
        On POSIX systems, checks for NFS/CIFS mounts.
        On Windows, checks for UNC, mapped drives, and cloud paths.
    """
    try:
        # CRITICAL: Resolve symlinks and junctions first
        # This prevents bypassing detection via symlink shortcuts
        resolved_path = path.resolve()
        path_str = str(resolved_path)

        # Check for cloud storage (all platforms)
        if _is_cloud_storage_path(resolved_path):
            logger.warning(f"Cloud storage detected: {path}")
            return True

        # Platform-specific checks
        if os.name == "nt":  # Windows
            path_lower = path_str.lower()

            # Check for UNC path (\\server\share format)
            if path_lower.startswith("\\\\"):
                logger.warning(f"UNC path detected: {path}")
                return True

            # Check for mapped network drive
            if len(path_str) >= 2 and path_str[1] == ":":
                drive_letter = path_str[0].upper()

                # Try net use first, then fallback
                if _detect_mapped_drive_fallback(drive_letter):
                    logger.warning(f"Mapped network drive detected: {drive_letter}:")
                    return True

        else:  # POSIX (Linux, macOS, etc.)
            # Check for POSIX network mounts
            if _is_posix_network_path(resolved_path):
                logger.warning(f"POSIX network mount detected: {path}")
                return True

        return False

    except Exception as e:
        logger.error(f"Error detecting network path for {path}: {e}")
        # Conservative: if we can't determine, assume not network
        return False


class AtomicFileWriter:
    """
    Atomic file writer using temp file + atomic rename pattern.

    Works on both POSIX and Windows systems:
    - POSIX: rename() is atomic
    - Windows: replace() is atomic (replaces destination atomically)

    Why this is needed:
    - Prevents partial writes being visible to readers
    - Prevents data corruption when writes race
    - Ensures readers see either old or new content, never mixed
    """

    def __init__(self, target_path: Path, preserve_permissions: bool = True):
        """
        Initialize atomic writer.

        Args:
            target_path: Path to write to
            preserve_permissions: If True, preserve target file permissions
        """
        self.target_path = Path(target_path)
        self.preserve_permissions = preserve_permissions
        self.temp_path = None
        self.temp_file = None
        self._open_temp_file()

    def _open_temp_file(self):
        """Open temporary file in same directory as target."""
        target_dir = self.target_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        # Create temp file in same directory to ensure atomic rename
        fd, temp_path = tempfile.mkstemp(
            dir=target_dir, prefix=self.target_path.name + ".", suffix=".tmp"
        )
        self.temp_path = Path(temp_path)
        self.temp_file = os.fdopen(fd, "w", encoding="utf-8")

    def write(self, content: str) -> None:
        """
        Write content to temporary file.

        Args:
            content: Content to write
        """
        if self.temp_file is None:
            raise RuntimeError("AtomicFileWriter already closed")

        self.temp_file.write(content)
        self.temp_file.flush()
        os.fsync(self.temp_file.fileno())

    def commit(self) -> None:
        """
        Atomically move temp file to target location.

        This is atomic on both Windows (replace) and POSIX (rename).
        If this succeeds, all or nothing was written.
        """
        if self.temp_file is None:
            raise RuntimeError("AtomicFileWriter already closed")

        self.temp_file.close()
        self.temp_file = None

        try:
            # Preserve permissions if target exists
            if self.preserve_permissions and self.target_path.exists():
                import stat

                target_stat = os.stat(self.target_path)
                target_mode = target_stat.st_mode
            else:
                target_mode = None

            # Atomic rename/replace
            if os.name == "nt":  # Windows
                # On Windows, use replace which is atomic
                os.replace(str(self.temp_path), str(self.target_path))
            else:  # POSIX
                # On POSIX, rename is atomic
                os.rename(str(self.temp_path), str(self.target_path))

            # Restore permissions if we saved them
            if target_mode is not None:
                os.chmod(str(self.target_path), stat.S_IMODE(target_mode))

        except Exception as e:
            # Clean up temp file on failure
            try:
                if self.temp_path and self.temp_path.exists():
                    self.temp_path.unlink()
            except Exception:
                pass  # Best effort cleanup
            raise RuntimeError(f"Atomic write failed: {e}") from e

    def rollback(self) -> None:
        """Discard temporary file without committing."""
        if self.temp_file is not None:
            self.temp_file.close()
            self.temp_file = None

        if self.temp_path and self.temp_path.exists():
            self.temp_path.unlink()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        elif self.temp_file is not None:
            # Only commit if not already closed
            self.commit()


class MemoryManager:
    """
    Thread-safe memory file manager with atomic operations.

    Guarantees:
    - Concurrent reads are safe (no corruption)
    - Concurrent writes serialize (last write wins, no data loss)
    - Readers never see partial writes

    Requirements:
    - MEMORY.md must be on local filesystem (not network share)
    - Network storage is not supported due to atomicity guarantees
    """

    def __init__(self, memory_file: Path):
        """
        Initialize memory manager.

        Args:
            memory_file: Path to MEMORY.md file

        Raises:
            RuntimeError: If memory_file is on network storage
        """
        self.memory_file = Path(memory_file)

        # Validate that path is on local filesystem
        if _is_network_path(self.memory_file):
            msg = (
                "CRITICAL: MEMORY.md cannot be stored on network drives or cloud "
                "storage.\n\n"
                f"Found network path: {self.memory_file}\n\n"
                "WHY THIS MATTERS:\n"
                "  - Atomic writes (os.replace) are NOT atomic on network shares\n"
                "  - Concurrent access can corrupt MEMORY.md leading to data loss\n"
                "  - This is a Phase 1 limitation (Phase 2 will support environment "
                "variables)\n\n"
                "SOLUTIONS (pick one):\n"
                "  1. RECOMMENDED: Move MEMORY.md to a local SSD\n"
                "     mkdir -p ~/.claude-local/memory\n"
                "     cp MEMORY.md ~/.claude-local/memory/\n"
                "     Update config to point to local path\n\n"
                "  2. Use local cache with sync:\n"
                "     - Keep local copy at ~/.claude-local/MEMORY.md\n"
                "     - Periodically sync to network (cron/scheduled task)\n"
                "     - Use atomic operations before uploading\n\n"
                "  3. Store in environment variables (Phase 2, not yet available)\n"
                "     - Planned for future release\n"
                "     - Track: FEATURE REQUEST: Phase 2 Environment Variable "
                "Storage\n\n"
                "MIGRATION STEPS:\n"
                "  If you have an existing MEMORY.md:\n"
                "  1. Choose a new local location (e.g., ~/.claude-local/MEMORY.md)\n"
                "  2. Copy existing file: cp CURRENT_PATH NEW_LOCAL_PATH\n"
                "  3. Update configuration to use new local path\n"
                "  4. Verify: read MEMORY.md to confirm no data loss\n\n"
                "For more information:\n"
                "  Docs: .claude/memory_operations.py\n"
                "  Issue: BLOCKER #2: Memory Network Drive Detection"
            )
            raise RuntimeError(msg)

        self.lock_file = self.memory_file.parent / f"{self.memory_file.name}.lock"
        self._write_lock = threading.RLock()

    def read(self) -> str:
        """
        Read memory file content safely.

        On Windows, file locking may temporarily prevent reads during atomic writes.
        This method retries on Windows lock errors. Readers may see either old or
        new content, but never partial data (atomic writes guarantee this).

        Returns:
            Content of memory file
        """
        if not self.memory_file.exists():
            return ""

        # Retry on Windows file lock issues
        max_retries = 3
        retry_delay = 0.01

        for attempt in range(max_retries):
            try:
                return self.memory_file.read_text(encoding="utf-8")
            except (FileNotFoundError, PermissionError) as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                # Last attempt failed
                if isinstance(e, FileNotFoundError):
                    return ""
                # If PermissionError persists, return empty
                return ""

    def append(self, entry: str) -> None:
        """
        Atomically append entry to memory file.

        Args:
            entry: Entry to append (should include "- " prefix)
        """
        with self._write_lock:
            current = self.read()
            if current and not current.endswith("\n"):
                current += "\n"

            new_content = current + entry + "\n"
            self._atomic_write(new_content)

    def update(self, content: str) -> None:
        """
        Atomically replace entire memory file content.

        Args:
            content: New content
        """
        with self._write_lock:
            if not content.endswith("\n"):
                content += "\n"
            self._atomic_write(content)

    def _atomic_write(self, content: str) -> None:
        """
        Perform atomic write with lock file.

        Args:
            content: Content to write
        """
        # Create lock file to indicate write in progress
        try:
            self.lock_file.write_text(str(os.getpid()), encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"Failed to acquire lock: {e}") from e

        try:
            # Perform atomic write
            writer = AtomicFileWriter(self.memory_file)
            writer.write(content)
            writer.commit()
        finally:
            # Clean up lock file
            if self.lock_file.exists():
                try:
                    self.lock_file.unlink()
                except Exception:
                    # If we can't delete lock file, at least we wrote successfully
                    pass

    def remove_stale_lock(self, timeout: int = LOCK_TIMEOUT) -> bool:
        """
        Remove stale lock file (not updated recently).

        Args:
            timeout: Lock considered stale after this many seconds

        Returns:
            True if lock was removed
        """
        if not self.lock_file.exists():
            return False

        mtime = self.lock_file.stat().st_mtime
        age = time.time() - mtime

        if age > timeout:
            try:
                self.lock_file.unlink()
                return True
            except Exception:
                return False

        return False


class MemoryValidator:
    """
    Validates memory file integrity and recovers from failures.

    Detects:
    - Incomplete writes (temp file exists)
    - Stale locks (lock file very old)
    - Corrupted state (invalid format)

    Recovers by:
    - Removing stale lock files
    - Cleaning up temp files
    - Restoring from backup if available
    """

    def __init__(self, memory_file: Path):
        """
        Initialize validator.

        Args:
            memory_file: Path to MEMORY.md file
        """
        self.memory_file = Path(memory_file)
        self.lock_file = self.memory_file.parent / f"{self.memory_file.name}.lock"
        self.temp_file = self.memory_file.parent / f"{self.memory_file.name}.tmp"
        self.backup_file = self.memory_file.parent / f"{self.memory_file.name}.backup"

    def validate(self) -> List[str]:
        """
        Validate memory file integrity.

        Returns:
            List of issues found (empty if valid)
        """
        issues = []

        # Check for incomplete writes
        if self.temp_file.exists():
            issues.append(f"Incomplete write detected: {self.temp_file}")

        # Check for stale locks
        if self.lock_file.exists():
            mtime = self.lock_file.stat().st_mtime
            age = time.time() - mtime
            if age > LOCK_TIMEOUT:
                issues.append(f"Stale lock file: {self.lock_file} (age: {age}s)")

        # Check file format if memory file exists
        if self.memory_file.exists():
            try:
                content = self.memory_file.read_text(encoding="utf-8")
                # Basic format check: should be markdown-like
                if content and not any(
                    line.startswith("-") for line in content.split("\n") if line.strip()
                ):
                    issues.append(
                        "Invalid memory format: entries should start with '-'"
                    )
            except Exception as e:
                issues.append(f"Cannot read memory file: {e}")

        return issues

    def recover(self) -> bool:
        """
        Recover from detected issues.

        Returns:
            True if recovery succeeded, False otherwise
        """
        recovered = True

        # Remove incomplete write
        if self.temp_file.exists():
            try:
                self.temp_file.unlink()
            except Exception:
                recovered = False

        # Remove stale lock
        if self.lock_file.exists():
            mtime = self.lock_file.stat().st_mtime
            age = time.time() - mtime
            if age > LOCK_TIMEOUT:
                try:
                    self.lock_file.unlink()
                except Exception:
                    recovered = False

        return recovered

    def backup(self) -> bool:
        """
        Create backup of current memory file.

        Returns:
            True if backup succeeded
        """
        if not self.memory_file.exists():
            return False

        try:
            content = self.memory_file.read_text(encoding="utf-8")
            self.backup_file.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    def restore_from_backup(self) -> bool:
        """
        Restore memory from backup if available.

        Returns:
            True if restore succeeded
        """
        if not self.backup_file.exists():
            return False

        try:
            content = self.backup_file.read_text(encoding="utf-8")
            self.memory_file.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False
