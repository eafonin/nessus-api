"""Unit tests for TTL housekeeping."""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from core.housekeeping import Housekeeper


class TestHousekeeperInit:
    """Test Housekeeper initialization."""

    def test_default_initialization(self):
        """Test Housekeeper with default values."""
        hk = Housekeeper()
        assert hk.data_dir == Path("/app/data/tasks")
        assert hk.completed_ttl == timedelta(days=7)
        assert hk.failed_ttl == timedelta(days=30)

    def test_custom_initialization(self):
        """Test Housekeeper with custom values."""
        hk = Housekeeper(
            data_dir="/custom/path",
            completed_ttl_days=3,
            failed_ttl_days=14
        )
        assert hk.data_dir == Path("/custom/path")
        assert hk.completed_ttl == timedelta(days=3)
        assert hk.failed_ttl == timedelta(days=14)


class TestHousekeeperCleanup:
    """Test Housekeeper cleanup functionality."""

    def _create_task(self, task_dir: Path, status: str, age_days: int = 0):
        """Helper to create a task directory with task.json."""
        task_dir.mkdir(parents=True, exist_ok=True)
        task_file = task_dir / "task.json"

        task_data = {
            "task_id": task_dir.name,
            "status": status,
            "created_at": (datetime.utcnow() - timedelta(days=age_days)).isoformat()
        }
        task_file.write_text(json.dumps(task_data))

        # Create a dummy results file to have some size
        (task_dir / "results.nessus").write_text("dummy results" * 100)

        # Set modification time to simulate age
        if age_days > 0:
            import os
            old_time = (datetime.utcnow() - timedelta(days=age_days)).timestamp()
            os.utime(task_file, (old_time, old_time))

    def test_cleanup_nonexistent_directory(self):
        """Test cleanup with nonexistent directory."""
        hk = Housekeeper(data_dir="/nonexistent/path")
        result = hk.cleanup()

        assert result["deleted_count"] == 0
        assert "does not exist" in result["errors"][0]

    def test_cleanup_empty_directory(self):
        """Test cleanup with empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hk = Housekeeper(data_dir=tmpdir)
            result = hk.cleanup()

            assert result["deleted_count"] == 0
            assert result["errors"] == []

    def test_cleanup_completed_task_old(self):
        """Test cleanup deletes old completed tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task_old_completed"
            self._create_task(task_dir, "completed", age_days=10)

            hk = Housekeeper(data_dir=tmpdir, completed_ttl_days=7)
            result = hk.cleanup()

            assert result["deleted_count"] == 1
            assert not task_dir.exists()

    def test_cleanup_completed_task_recent(self):
        """Test cleanup keeps recent completed tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task_recent_completed"
            self._create_task(task_dir, "completed", age_days=3)

            hk = Housekeeper(data_dir=tmpdir, completed_ttl_days=7)
            result = hk.cleanup()

            assert result["deleted_count"] == 0
            assert task_dir.exists()

    def test_cleanup_failed_task_old(self):
        """Test cleanup deletes old failed tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task_old_failed"
            self._create_task(task_dir, "failed", age_days=35)

            hk = Housekeeper(data_dir=tmpdir, failed_ttl_days=30)
            result = hk.cleanup()

            assert result["deleted_count"] == 1
            assert not task_dir.exists()

    def test_cleanup_failed_task_recent(self):
        """Test cleanup keeps recent failed tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task_recent_failed"
            self._create_task(task_dir, "failed", age_days=10)

            hk = Housekeeper(data_dir=tmpdir, failed_ttl_days=30)
            result = hk.cleanup()

            assert result["deleted_count"] == 0
            assert task_dir.exists()

    def test_cleanup_timeout_task_old(self):
        """Test cleanup deletes old timeout tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task_old_timeout"
            self._create_task(task_dir, "timeout", age_days=35)

            hk = Housekeeper(data_dir=tmpdir, failed_ttl_days=30)
            result = hk.cleanup()

            assert result["deleted_count"] == 1

    def test_cleanup_skips_running_tasks(self):
        """Test cleanup never deletes running tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task_running"
            self._create_task(task_dir, "running", age_days=100)

            hk = Housekeeper(data_dir=tmpdir)
            result = hk.cleanup()

            assert result["deleted_count"] == 0
            assert result["skipped"] == 1
            assert task_dir.exists()

    def test_cleanup_skips_queued_tasks(self):
        """Test cleanup never deletes queued tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task_queued"
            self._create_task(task_dir, "queued", age_days=100)

            hk = Housekeeper(data_dir=tmpdir)
            result = hk.cleanup()

            assert result["deleted_count"] == 0
            assert result["skipped"] == 1
            assert task_dir.exists()

    def test_cleanup_multiple_tasks(self):
        """Test cleanup handles multiple tasks correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Old completed - should delete
            self._create_task(Path(tmpdir) / "task1", "completed", age_days=10)
            # Recent completed - keep
            self._create_task(Path(tmpdir) / "task2", "completed", age_days=3)
            # Old failed - should delete
            self._create_task(Path(tmpdir) / "task3", "failed", age_days=35)
            # Running - keep
            self._create_task(Path(tmpdir) / "task4", "running", age_days=50)

            hk = Housekeeper(data_dir=tmpdir, completed_ttl_days=7, failed_ttl_days=30)
            result = hk.cleanup()

            assert result["deleted_count"] == 2
            assert result["skipped"] == 1
            assert not (Path(tmpdir) / "task1").exists()
            assert (Path(tmpdir) / "task2").exists()
            assert not (Path(tmpdir) / "task3").exists()
            assert (Path(tmpdir) / "task4").exists()

    def test_cleanup_tracks_freed_bytes(self):
        """Test cleanup tracks freed disk space."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task_with_data"
            self._create_task(task_dir, "completed", age_days=10)

            hk = Housekeeper(data_dir=tmpdir, completed_ttl_days=7)
            result = hk.cleanup()

            assert result["deleted_count"] == 1
            assert result["freed_bytes"] > 0
            assert result["freed_mb"] >= 0

    def test_cleanup_handles_invalid_json(self):
        """Test cleanup handles invalid task.json gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task_invalid"
            task_dir.mkdir()
            (task_dir / "task.json").write_text("not valid json")

            hk = Housekeeper(data_dir=tmpdir)
            result = hk.cleanup()

            assert result["deleted_count"] == 0
            assert len(result["errors"]) == 1
            assert "Invalid JSON" in result["errors"][0]


class TestHousekeeperStats:
    """Test Housekeeper statistics functionality."""

    def _create_task(self, task_dir: Path, status: str, age_days: int = 0):
        """Helper to create a task directory."""
        task_dir.mkdir(parents=True, exist_ok=True)
        task_file = task_dir / "task.json"
        task_file.write_text(json.dumps({
            "task_id": task_dir.name,
            "status": status
        }))
        if age_days > 0:
            import os
            old_time = (datetime.utcnow() - timedelta(days=age_days)).timestamp()
            os.utime(task_file, (old_time, old_time))

    def test_get_stats_empty(self):
        """Test stats for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hk = Housekeeper(data_dir=tmpdir)
            stats = hk.get_stats()

            assert stats["total_tasks"] == 0
            assert stats["total_size_mb"] == 0
            assert stats["by_status"] == {}

    def test_get_stats_counts_by_status(self):
        """Test stats counts tasks by status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_task(Path(tmpdir) / "t1", "completed")
            self._create_task(Path(tmpdir) / "t2", "completed")
            self._create_task(Path(tmpdir) / "t3", "failed")
            self._create_task(Path(tmpdir) / "t4", "running")

            hk = Housekeeper(data_dir=tmpdir)
            stats = hk.get_stats()

            assert stats["total_tasks"] == 4
            assert stats["by_status"]["completed"] == 2
            assert stats["by_status"]["failed"] == 1
            assert stats["by_status"]["running"] == 1

    def test_get_stats_tracks_expired(self):
        """Test stats tracks expired tasks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Expired completed
            self._create_task(Path(tmpdir) / "t1", "completed", age_days=10)
            # Not expired completed
            self._create_task(Path(tmpdir) / "t2", "completed", age_days=3)
            # Expired failed
            self._create_task(Path(tmpdir) / "t3", "failed", age_days=35)

            hk = Housekeeper(data_dir=tmpdir, completed_ttl_days=7, failed_ttl_days=30)
            stats = hk.get_stats()

            assert stats["expired"]["completed"] == 1
            assert stats["expired"]["failed"] == 1


class TestMetricsIntegration:
    """Test metrics are updated during cleanup."""

    def test_ttl_deletions_metric_incremented(self):
        """Test ttl_deletions_total metric is incremented."""
        from core.metrics import ttl_deletions_total

        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task_to_delete"
            task_dir.mkdir()
            (task_dir / "task.json").write_text(json.dumps({
                "task_id": "test",
                "status": "completed"
            }))

            # Set old modification time
            import os
            old_time = (datetime.utcnow() - timedelta(days=10)).timestamp()
            os.utime(task_dir / "task.json", (old_time, old_time))

            # Get initial metric value
            initial = ttl_deletions_total._value.get()

            hk = Housekeeper(data_dir=tmpdir, completed_ttl_days=7)
            hk.cleanup()

            # Verify metric incremented
            assert ttl_deletions_total._value.get() == initial + 1
