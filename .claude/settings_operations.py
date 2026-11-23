"""
Settings thread-safety through launch-time snapshot pattern.

Provides:
1. SettingsSnapshot - Immutable snapshot of settings at a moment in time
2. SettingsManager - Type-safe access to settings from snapshot
3. SnapshotRegistry - Tracks snapshots for each workflow

Why this is needed:
- Workflows read settings at various points during execution
- If settings change mid-flight, workflows see inconsistent state
- Solution: Snapshot settings at launch time, never re-read during execution
"""

import json
import logging
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

# Configure logging for snapshot lifecycle visibility
logger = logging.getLogger(__name__)

# TTL for snapshots: 24 hours in seconds
SNAPSHOT_TTL_SECONDS = 24 * 3600


class SettingsSnapshot:
    """
    Immutable snapshot of settings at a moment in time.

    Captures all settings from the file at creation time and prevents
    any modifications. Workflows use this snapshot exclusively.

    Why immutable:
    - Prevents accidental modifications
    - Ensures consistency throughout workflow execution
    - Makes it obvious when settings are being overridden
    """

    def __init__(self, settings_file: Path):
        """
        Create a snapshot of settings at this moment.

        Args:
            settings_file: Path to settings.json file
        """
        self.settings_file = Path(settings_file)
        self._settings = self._load_settings()
        self._created_at = self._get_timestamp()
        logger.debug(f"SettingsSnapshot created for {settings_file}")

    def _load_settings(self) -> Dict[str, Any]:
        """Load and deserialize settings from file."""
        try:
            if not self.settings_file.exists():
                return {}

            content = self.settings_file.read_text(encoding="utf-8")
            # Deep copy to isolate snapshot from file changes
            return deepcopy(json.loads(content))
        except (json.JSONDecodeError, IOError) as e:
            raise RuntimeError(
                f"Failed to load settings snapshot from {self.settings_file}: {e}"
            ) from e

    def _get_timestamp(self) -> float:
        """
        Get current timestamp for snapshot creation time.

        Uses time.monotonic() to avoid clock skew issues (NTP adjustments, DST, etc.).
        Monotonic time never goes backward, making TTL calculations reliable.

        Returns:
            Current monotonic time in seconds
        """
        return time.monotonic()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value by key with optional default.

        Args:
            key: Setting key to retrieve
            default: Default value if key not found

        Returns:
            Setting value or default if not found
        """
        return self._settings.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Get setting value by key. Raises KeyError if not found."""
        return self._settings[key]

    def __contains__(self, key: str) -> bool:
        """Check if setting key exists."""
        return key in self._settings

    def to_dict(self) -> Dict[str, Any]:
        """Return a copy of all settings as dictionary."""
        return deepcopy(self._settings)

    def __setitem__(self, key: str, value: Any):
        """Prevent modification of snapshot."""
        raise TypeError("SettingsSnapshot is immutable")

    def __setattr__(self, name: str, value: Any):
        """Override to allow initialization but prevent later modifications."""
        if name in ("_settings", "settings_file", "_created_at"):
            # Allow internal attributes during __init__
            super().__setattr__(name, value)
        else:
            raise AttributeError(f"Cannot modify SettingsSnapshot.{name}")


class SettingsManager:
    """
    Type-safe settings manager that always uses snapshot.

    Provides convenient methods to access settings with type safety
    and sensible defaults. Never re-reads settings.json.
    """

    def __init__(self, settings_file: Path, snapshot: SettingsSnapshot):
        """
        Initialize manager with settings file path and snapshot.

        Args:
            settings_file: Path to settings.json (for reference only)
            snapshot: SettingsSnapshot to use for all access
        """
        self.settings_file = Path(settings_file)
        self.snapshot = snapshot

    def get_timeout(self, default: int = 300) -> int:
        """Get workflow timeout setting."""
        value = self.snapshot.get("timeout", default)
        return int(value) if value is not None else default

    def get_max_workers(self, default: int = 2) -> int:
        """Get max concurrent workers setting."""
        value = self.snapshot.get("max_workers", default)
        return int(value) if value is not None else default

    def get_max_retries(self, default: int = 3) -> int:
        """Get max retry attempts setting."""
        value = self.snapshot.get("max_retries", default)
        return int(value) if value is not None else default

    def get_enabled(self, default: bool = True) -> bool:
        """Get enabled flag setting."""
        value = self.snapshot.get("enabled", default)
        if isinstance(value, bool):
            return value
        return default

    def get_debug_mode(self, default: bool = False) -> bool:
        """Get debug mode flag setting."""
        value = self.snapshot.get("debug_mode", default)
        if isinstance(value, bool):
            return value
        return default

    def get_name(self, default: str = "workflow") -> str:
        """Get workflow name setting."""
        value = self.snapshot.get("name", default)
        return str(value) if value is not None else default

    def get_value(self, default: Any = None) -> Any:
        """Get a generic value setting."""
        return self.snapshot.get("value", default)

    def get_agent_type(self, default: str = "claude") -> str:
        """Get agent type setting."""
        value = self.snapshot.get("agent_type", default)
        return str(value) if value is not None else default


class SnapshotRegistry:
    """
    Registry of snapshots for active workflows.

    Tracks which workflows are running with which settings snapshots.
    Used for monitoring and debugging workflow state.
    """

    def __init__(self):
        """Initialize empty snapshot registry."""
        self._snapshots: Dict[str, SettingsSnapshot] = {}
        self._lock = threading.RLock()

    def register(self, workflow_id: str, snapshot: SettingsSnapshot) -> None:
        """
        Register a snapshot for a workflow.

        Args:
            workflow_id: Unique workflow identifier
            snapshot: SettingsSnapshot for this workflow
        """
        with self._lock:
            self._snapshots[workflow_id] = snapshot
            logger.debug(
                f"Registered snapshot for workflow: {workflow_id} "
                f"(total: {len(self._snapshots)})"
            )

    def get(self, workflow_id: str) -> Optional[SettingsSnapshot]:
        """
        Get registered snapshot for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            SettingsSnapshot if registered, None otherwise
        """
        with self._lock:
            return self._snapshots.get(workflow_id)

    def unregister(self, workflow_id: str) -> bool:
        """
        Unregister a workflow's snapshot and trigger cleanup of expired snapshots.

        This method also runs background cleanup to remove any snapshots that have
        exceeded their TTL, preventing accumulation of orphaned snapshots in case
        workflow crashes bypass normal cleanup paths.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if snapshot was registered and removed
        """
        with self._lock:
            found = False
            if workflow_id in self._snapshots:
                del self._snapshots[workflow_id]
                logger.debug(f"Unregistered snapshot for workflow: {workflow_id}")
                found = True
            else:
                logger.debug(f"Snapshot not found for unregister: {workflow_id}")

            # Trigger cleanup of expired snapshots (prevents orphan accumulation)
            cleaned = self._cleanup_expired_snapshots_unsafe()
            if cleaned > 0:
                logger.debug(
                    f"Unregister triggered cleanup of {cleaned} expired snapshots"
                )

            return found

    def _cleanup_expired_snapshots(self) -> int:
        """
        Remove snapshots that have exceeded TTL (thread-safe wrapper).

        This method acquires the lock before cleaning up. Call this when
        you want automatic cleanup to run.

        Returns:
            Number of snapshots removed
        """
        with self._lock:
            return self._cleanup_expired_snapshots_unsafe()

    def _cleanup_expired_snapshots_unsafe(self) -> int:
        """
        Remove snapshots that have exceeded TTL (NOT thread-safe).

        Internal method - assumes caller holds self._lock.

        Uses time.monotonic() for reliable age calculation despite clock skew.

        Returns:
            Number of snapshots removed
        """
        now = time.monotonic()
        to_remove = []

        # Find all snapshots that have expired
        for workflow_id, snapshot in self._snapshots.items():
            if hasattr(snapshot, "_created_at") and snapshot._created_at is not None:
                age = now - snapshot._created_at
                if age > SNAPSHOT_TTL_SECONDS:
                    to_remove.append(workflow_id)
                    logger.debug(
                        f"Snapshot {workflow_id} expired "
                        f"(age: {age:.1f}s > {SNAPSHOT_TTL_SECONDS}s)"
                    )

        # Remove expired snapshots
        for workflow_id in to_remove:
            del self._snapshots[workflow_id]
            logger.info(f"Removed expired snapshot: {workflow_id}")

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} expired snapshots")

        return len(to_remove)

    def get_all(self) -> Dict[str, SettingsSnapshot]:
        """
        Get all registered snapshots.

        Returns:
            Dictionary of workflow_id -> SettingsSnapshot
        """
        with self._lock:
            return deepcopy(self._snapshots)

    def count(self) -> int:
        """Get number of currently registered workflows."""
        with self._lock:
            return len(self._snapshots)

    def clear(self) -> None:
        """Clear all registered snapshots."""
        with self._lock:
            self._snapshots.clear()


# Global singleton registry
_global_registry = SnapshotRegistry()


def get_global_registry() -> SnapshotRegistry:
    """Get the global snapshot registry instance."""
    return _global_registry


def create_workflow_snapshot(settings_file: Path) -> SettingsSnapshot:
    """
    Create a new settings snapshot for a workflow launch.

    This should be called exactly once at workflow launch time,
    and the snapshot should be passed to all workflow phases.

    Args:
        settings_file: Path to settings.json

    Returns:
        New SettingsSnapshot
    """
    return SettingsSnapshot(settings_file)


def create_settings_manager(
    settings_file: Path,
    snapshot: SettingsSnapshot,
) -> SettingsManager:
    """
    Create a settings manager for accessing settings through snapshot.

    Args:
        settings_file: Path to settings.json (for reference)
        snapshot: SettingsSnapshot to use for all access

    Returns:
        New SettingsManager
    """
    return SettingsManager(settings_file, snapshot)
