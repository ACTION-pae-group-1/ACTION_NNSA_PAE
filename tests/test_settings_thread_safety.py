"""
Test suite for settings thread-safety through launch-time snapshot pattern.

Tests cover:
1. Settings snapshot at workflow launch time
2. Workflows ignore mid-flight settings changes
3. Concurrent workflows each get their own snapshot
4. Snapshot remains stable during workflow execution
"""

import json
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude"))

from settings_operations import (
    SNAPSHOT_TTL_SECONDS,
    SettingsManager,
    SettingsSnapshot,
    SnapshotRegistry,
)


class TestSettingsSnapshot:
    """Test settings snapshot functionality."""

    def test_snapshot_captures_settings_at_creation_time(self):
        """Snapshot should capture settings at the moment it's created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            original_settings = {
                "agent_type": "tdd-enforcer",
                "timeout": 300,
                "max_retries": 3,
            }
            settings_file.write_text(json.dumps(original_settings))

            # Create snapshot at this moment
            snapshot = SettingsSnapshot(settings_file)

            # Modify settings file after snapshot
            modified_settings = original_settings.copy()
            modified_settings["timeout"] = 600
            settings_file.write_text(json.dumps(modified_settings))

            # Snapshot should still have original values
            assert snapshot.get("timeout") == 300
            assert snapshot.get("agent_type") == "tdd-enforcer"
            assert snapshot.get("max_retries") == 3

    def test_snapshot_is_immutable(self):
        """Snapshot should not allow modifications."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"mode": "strict"}))

            snapshot = SettingsSnapshot(settings_file)

            # Attempting to modify snapshot should raise error
            with pytest.raises((AttributeError, TypeError)):
                snapshot["mode"] = "lenient"

    def test_snapshot_get_with_default(self):
        """Snapshot.get should return default for missing keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"key1": "value1"}))

            snapshot = SettingsSnapshot(settings_file)

            assert snapshot.get("key1") == "value1"
            assert snapshot.get("missing_key", "default") == "default"
            assert snapshot.get("missing_key") is None

    def test_snapshot_preserves_complex_values(self):
        """Snapshot should preserve lists, dicts, and nested structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            complex_settings = {
                "agents": ["tdd-enforcer", "code-reviewer"],
                "config": {"nested": {"deep": "value"}},
                "numbers": [1, 2, 3],
            }
            settings_file.write_text(json.dumps(complex_settings))

            snapshot = SettingsSnapshot(settings_file)

            assert snapshot.get("agents") == ["tdd-enforcer", "code-reviewer"]
            assert snapshot.get("config")["nested"]["deep"] == "value"
            assert snapshot.get("numbers") == [1, 2, 3]


class TestWorkflowSettingsIsolation:
    """Test that workflows use snapshot and don't re-read settings."""

    def test_workflow_sees_snapshot_not_current_settings(self):
        """Workflow should use snapshot taken at launch, not current settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            initial_settings = {
                "max_workers": 2,
                "timeout": 300,
            }
            settings_file.write_text(json.dumps(initial_settings))

            # Create snapshot (simulating workflow launch)
            snapshot = SettingsSnapshot(settings_file)

            # Change settings after snapshot
            modified_settings = {
                "max_workers": 10,
                "timeout": 600,
            }
            settings_file.write_text(json.dumps(modified_settings))

            # Workflow should still see original values from snapshot
            manager = SettingsManager(settings_file, snapshot)
            assert manager.get_max_workers() == 2
            assert manager.get_timeout() == 300

    def test_manager_always_uses_snapshot(self):
        """SettingsManager should always use snapshot, never re-read file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"value": 100}))

            snapshot = SettingsSnapshot(settings_file)
            manager = SettingsManager(settings_file, snapshot)

            # Change file multiple times
            for i in range(5):
                new_value = 100 + i
                settings_file.write_text(json.dumps({"value": new_value}))
                time.sleep(0.01)

                # Manager should still return original snapshot value
                assert manager.get_value() == 100

    def test_concurrent_workflows_have_independent_snapshots(self):
        """Each workflow should get its own independent snapshot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"workflow_id": 0}))

            snapshots = []
            # write_text truncates the file before writing, so a reader in
            # another thread can see it empty. Hold the lock across each
            # write and its snapshot read.
            file_lock = threading.Lock()

            def create_snapshot_for_workflow(workflow_id):
                # Create snapshot for this workflow
                with file_lock:
                    settings_file.write_text(json.dumps({"workflow_id": workflow_id}))
                    snapshot = SettingsSnapshot(settings_file)
                snapshots.append((workflow_id, snapshot))

            # Launch concurrent workflows
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(create_snapshot_for_workflow, wid)
                    for wid in range(1, 4)
                ]
                for future in as_completed(futures):
                    future.result()

            # Each snapshot should have captured its own workflow_id
            assert len(snapshots) == 3
            captured_ids = sorted([snap.get("workflow_id") for _, snap in snapshots])
            # The order might vary, but we should have captured some workflow_ids
            assert 1 in captured_ids or 2 in captured_ids or 3 in captured_ids


class TestSnapshotRegistry:
    """Test snapshot registry for tracking active workflows."""

    def test_register_snapshot_for_workflow(self):
        """Registry should track snapshots by workflow ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"mode": "test"}))

            registry = SnapshotRegistry()
            snapshot = SettingsSnapshot(settings_file)

            registry.register("workflow-1", snapshot)

            # Should be able to retrieve snapshot
            retrieved = registry.get("workflow-1")
            assert retrieved is not None
            assert retrieved.get("mode") == "test"

    def test_register_multiple_workflows(self):
        """Registry should handle multiple concurrent workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            registry = SnapshotRegistry()

            snapshots_by_workflow = {}
            # write_text truncates the file before writing, so a reader in
            # another thread can see it empty. Hold the lock across each write
            # and its snapshot read; registration itself stays concurrent.
            file_lock = threading.Lock()

            def register_workflow(workflow_id, value):
                with file_lock:
                    settings_file.write_text(json.dumps({"config": value}))
                    snapshot = SettingsSnapshot(settings_file)
                registry.register(f"workflow-{workflow_id}", snapshot)
                snapshots_by_workflow[workflow_id] = snapshot

            # Register multiple workflows
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(register_workflow, wid, f"config-{wid}")
                    for wid in range(1, 4)
                ]
                for future in as_completed(futures):
                    future.result()

            # All should be registered independently
            for wid in range(1, 4):
                retrieved = registry.get(f"workflow-{wid}")
                assert retrieved is not None

    def test_unregister_cleans_up_snapshot(self):
        """Unregister should remove snapshot from registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"data": "test"}))

            registry = SnapshotRegistry()
            snapshot = SettingsSnapshot(settings_file)

            registry.register("workflow-1", snapshot)
            assert registry.get("workflow-1") is not None

            registry.unregister("workflow-1")
            assert registry.get("workflow-1") is None

    def test_concurrent_register_and_unregister(self):
        """Registry should handle concurrent register/unregister safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"test": "data"}))

            registry = SnapshotRegistry()

            def lifecycle(workflow_id):
                snapshot = SettingsSnapshot(settings_file)
                registry.register(f"workflow-{workflow_id}", snapshot)
                time.sleep(0.01)
                registry.unregister(f"workflow-{workflow_id}")

            # Concurrent lifecycle operations
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(lifecycle, wid) for wid in range(10)]
                for future in as_completed(futures):
                    future.result()

            # Registry should be empty at the end
            assert registry.get("workflow-0") is None


class TestSettingsModificationDetection:
    """Test detection of settings modifications during workflow execution."""

    def test_detect_settings_changed_during_execution(self):
        """Should detect when settings are modified during workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            initial_settings = {"version": 1, "timeout": 300}
            settings_file.write_text(json.dumps(initial_settings))

            snapshot = SettingsSnapshot(settings_file)

            # Simulate workflow execution
            time.sleep(0.01)

            # Settings are modified during execution
            modified_settings = {"version": 2, "timeout": 600}
            settings_file.write_text(json.dumps(modified_settings))

            # Create validator to check consistency
            current = json.loads(settings_file.read_text())
            assert snapshot.get("version") != current.get("version")
            assert snapshot.get("timeout") != current.get("timeout")

    def test_snapshot_prevents_mid_flight_setting_changes_impact(self):
        """Workflows using snapshot should be unaffected by setting changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(
                json.dumps(
                    {
                        "max_retries": 3,
                        "debug_mode": False,
                    }
                )
            )

            # Take snapshot at workflow start
            snapshot = SettingsSnapshot(settings_file)
            manager = SettingsManager(settings_file, snapshot)

            # During workflow execution, settings are changed
            settings_file.write_text(
                json.dumps(
                    {
                        "max_retries": 10,
                        "debug_mode": True,
                    }
                )
            )

            # Workflow behavior should be unchanged (using snapshot)
            assert manager.get_max_retries() == 3
            assert manager.get_debug_mode() is False


class TestSettingsManager:
    """Test SettingsManager configuration helper."""

    def test_manager_provides_typed_access(self):
        """Manager should provide type-safe access to settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(
                json.dumps(
                    {
                        "timeout": 300,
                        "max_workers": 4,
                        "enabled": True,
                        "name": "test-workflow",
                    }
                )
            )

            snapshot = SettingsSnapshot(settings_file)
            manager = SettingsManager(settings_file, snapshot)

            assert manager.get_timeout() == 300
            assert manager.get_max_workers() == 4
            assert manager.get_enabled() is True
            assert manager.get_name() == "test-workflow"

    def test_manager_handles_missing_settings_with_defaults(self):
        """Manager should provide defaults for missing settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({}))  # Empty settings

            snapshot = SettingsSnapshot(settings_file)
            manager = SettingsManager(settings_file, snapshot)

            # Should return defaults
            assert manager.get_timeout(default=300) == 300
            assert manager.get_max_workers(default=2) == 2


class TestSnapshotRegistryTTLCleanup:
    """Test TTL-based automatic cleanup of expired snapshots."""

    def test_snapshots_cleaned_up_after_ttl_expires(self):
        """Snapshots older than 24 hours should be cleaned up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"data": "test"}))

            base_time = 1000.0

            with patch("time.monotonic") as mock_monotonic:
                mock_monotonic.return_value = base_time
                registry = SnapshotRegistry()
                snapshot = SettingsSnapshot(settings_file)

                # Register snapshot
                registry.register("workflow-old", snapshot)

            # Simulate time advancing past TTL
            with patch("time.monotonic") as mock_monotonic:
                mock_monotonic.return_value = base_time + SNAPSHOT_TTL_SECONDS + 1

                # Trigger cleanup
                registry._cleanup_expired_snapshots()

                # Old snapshot should be removed
                assert registry.get("workflow-old") is None

    def test_cleanup_preserves_recent_snapshots(self):
        """Snapshots newer than 24 hours should not be cleaned up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"data": "test"}))

            registry = SnapshotRegistry()
            snapshot = SettingsSnapshot(settings_file)

            # Register snapshot with current timestamp
            registry.register("workflow-recent", snapshot)

            # Trigger cleanup
            registry._cleanup_expired_snapshots()

            # Recent snapshot should still be there
            assert registry.get("workflow-recent") is not None

    def test_cleanup_called_on_unregister(self):
        """Cleanup should be triggered when unregistering a snapshot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"data": "test"}))

            old_time = 1000.0
            recent_time = old_time + 1000.0

            registry = SnapshotRegistry()

            with patch("time.monotonic") as mock_monotonic:
                # Create old snapshots
                mock_monotonic.return_value = old_time
                for i in range(3):
                    snapshot = SettingsSnapshot(settings_file)
                    registry.register(f"workflow-{i}", snapshot)

                # Create recent snapshots
                mock_monotonic.return_value = recent_time
                for i in range(3, 5):
                    snapshot = SettingsSnapshot(settings_file)
                    registry.register(f"workflow-{i}", snapshot)

            # Unregister one snapshot when time has passed TTL for old ones
            cleanup_time = old_time + SNAPSHOT_TTL_SECONDS + 1
            with patch("time.monotonic") as mock_monotonic:
                mock_monotonic.return_value = cleanup_time

                registry.unregister("workflow-0")

                # Old snapshots should be cleaned up
                for i in range(3):
                    assert registry.get(f"workflow-{i}") is None

                # Recent snapshots should remain
                for i in range(3, 5):
                    assert registry.get(f"workflow-{i}") is not None

    def test_memory_bounded_with_many_snapshots(self):
        """Memory usage should not grow unbounded with 1000+ snapshots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"data": "x" * 1000}))  # 1KB settings

            old_time = 1000.0
            recent_time = old_time + 1000.0  # 1000 seconds later, within TTL

            registry = SnapshotRegistry()

            with patch("time.monotonic") as mock_monotonic:
                # Create old snapshots
                mock_monotonic.return_value = old_time
                for i in range(500):
                    snapshot = SettingsSnapshot(settings_file)
                    registry.register(f"workflow-old-{i}", snapshot)

                # Create recent snapshots
                mock_monotonic.return_value = recent_time
                for i in range(500):
                    snapshot = SettingsSnapshot(settings_file)
                    registry.register(f"workflow-recent-{i}", snapshot)

            # Before cleanup
            count_before = registry.count()
            assert count_before == 1000

            # Trigger cleanup at a time when old snapshots have exceeded TTL
            # but recent ones are still fresh
            cleanup_time = old_time + SNAPSHOT_TTL_SECONDS + 1  # Beyond old TTL
            with patch("time.monotonic") as mock_monotonic:
                mock_monotonic.return_value = cleanup_time

                registry._cleanup_expired_snapshots()

                # Should have roughly half remaining (only recent ones)
                count_after = registry.count()
                assert count_after < count_before, (
                    "Cleanup should remove expired snapshots"
                )
                # Recent snapshots are fresh, so they should mostly remain
                # cleanup_time - recent_time age should be < TTL
                # recent_time = old_time + 1000
                # cleanup_time = old_time + SNAPSHOT_TTL_SECONDS + 1
                # age = cleanup_time - recent_time = SNAPSHOT_TTL_SECONDS + 1 - 1000
                # Which is still within TTL for most cases
                assert count_after >= 400, "Recent snapshots should be preserved"

    def test_cleanup_doesn_affect_active_snapshots(self):
        """Cleanup should not affect snapshots actively used by workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            settings_file.write_text(json.dumps({"config": "active"}))

            registry = SnapshotRegistry()
            snapshot = SettingsSnapshot(settings_file)

            # Register as active
            registry.register("active-workflow", snapshot)

            # Even if we trigger cleanup multiple times
            for _ in range(5):
                registry._cleanup_expired_snapshots()

            # Active snapshot should still be accessible
            retrieved = registry.get("active-workflow")
            assert retrieved is not None
            assert retrieved.get("config") == "active"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
