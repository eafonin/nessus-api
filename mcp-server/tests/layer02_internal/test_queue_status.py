"""
Unit tests for get_queue_status MCP tool functionality.

Tests the queue status reporting:
- Queue depth calculation
- DLQ size tracking
- Next tasks preview
- Pool-specific stats
- Timestamp generation
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from core.queue import TaskQueue, get_queue_stats, DEFAULT_POOL


class TestGetQueueStatsBasic:
    """Basic tests for get_queue_stats function."""

    @pytest.fixture
    def mock_queue(self):
        """Create mock TaskQueue."""
        queue = MagicMock(spec=TaskQueue)
        queue.default_pool = "nessus"
        queue.get_queue_depth.return_value = 5
        queue.get_dlq_size.return_value = 2
        queue.peek.return_value = [
            {"task_id": "task_001", "name": "Scan 1"},
            {"task_id": "task_002", "name": "Scan 2"},
            {"task_id": "task_003", "name": "Scan 3"},
        ]
        return queue

    def test_get_queue_stats_default_pool(self, mock_queue):
        """Test get_queue_stats with default pool."""
        stats = get_queue_stats(mock_queue)

        assert stats["pool"] == "nessus"
        assert stats["queue_depth"] == 5
        assert stats["dlq_size"] == 2
        assert len(stats["next_tasks"]) == 3
        assert "timestamp" in stats

    def test_get_queue_stats_specific_pool(self, mock_queue):
        """Test get_queue_stats with specific pool."""
        mock_queue.get_queue_depth.return_value = 10
        mock_queue.get_dlq_size.return_value = 0
        mock_queue.peek.return_value = []

        stats = get_queue_stats(mock_queue, pool="nessus_dmz")

        assert stats["pool"] == "nessus_dmz"
        mock_queue.get_queue_depth.assert_called_with(pool="nessus_dmz")
        mock_queue.get_dlq_size.assert_called_with(pool="nessus_dmz")
        mock_queue.peek.assert_called_with(count=3, pool="nessus_dmz")

    def test_get_queue_stats_empty_queue(self, mock_queue):
        """Test get_queue_stats with empty queue."""
        mock_queue.get_queue_depth.return_value = 0
        mock_queue.get_dlq_size.return_value = 0
        mock_queue.peek.return_value = []

        stats = get_queue_stats(mock_queue)

        assert stats["queue_depth"] == 0
        assert stats["dlq_size"] == 0
        assert stats["next_tasks"] == []

    def test_get_queue_stats_timestamp_format(self, mock_queue):
        """Test that timestamp is in ISO format."""
        stats = get_queue_stats(mock_queue)

        # Should be parseable as ISO datetime
        timestamp = stats["timestamp"]
        parsed = datetime.fromisoformat(timestamp)
        assert parsed is not None


class TestGetQueueStatsPoolIsolation:
    """Tests for pool isolation in queue stats."""

    @pytest.fixture
    def mock_queue(self):
        """Create mock TaskQueue with pool-aware responses."""
        queue = MagicMock(spec=TaskQueue)
        queue.default_pool = "nessus"

        def depth_by_pool(pool="nessus"):
            return {"nessus": 5, "nessus_dmz": 10, "nuclei": 0}.get(pool, 0)

        def dlq_by_pool(pool="nessus"):
            return {"nessus": 2, "nessus_dmz": 1, "nuclei": 0}.get(pool, 0)

        def peek_by_pool(count=3, pool="nessus"):
            tasks = {
                "nessus": [{"task_id": f"nessus_{i}"} for i in range(3)],
                "nessus_dmz": [{"task_id": f"dmz_{i}"} for i in range(2)],
                "nuclei": [],
            }
            return tasks.get(pool, [])[:count]

        queue.get_queue_depth.side_effect = depth_by_pool
        queue.get_dlq_size.side_effect = dlq_by_pool
        queue.peek.side_effect = peek_by_pool

        return queue

    def test_nessus_pool_stats(self, mock_queue):
        """Test stats for nessus pool."""
        stats = get_queue_stats(mock_queue, pool="nessus")

        assert stats["pool"] == "nessus"
        assert stats["queue_depth"] == 5
        assert stats["dlq_size"] == 2
        assert len(stats["next_tasks"]) == 3
        assert all("nessus_" in t["task_id"] for t in stats["next_tasks"])

    def test_dmz_pool_stats(self, mock_queue):
        """Test stats for nessus_dmz pool."""
        stats = get_queue_stats(mock_queue, pool="nessus_dmz")

        assert stats["pool"] == "nessus_dmz"
        assert stats["queue_depth"] == 10
        assert stats["dlq_size"] == 1
        assert len(stats["next_tasks"]) == 2
        assert all("dmz_" in t["task_id"] for t in stats["next_tasks"])

    def test_empty_pool_stats(self, mock_queue):
        """Test stats for empty pool."""
        stats = get_queue_stats(mock_queue, pool="nuclei")

        assert stats["pool"] == "nuclei"
        assert stats["queue_depth"] == 0
        assert stats["dlq_size"] == 0
        assert stats["next_tasks"] == []


class TestQueueStatsResponseFormat:
    """Tests for queue stats response format."""

    @pytest.fixture
    def mock_queue(self):
        """Create mock TaskQueue."""
        queue = MagicMock(spec=TaskQueue)
        queue.default_pool = "nessus"
        queue.get_queue_depth.return_value = 3
        queue.get_dlq_size.return_value = 1
        queue.peek.return_value = [
            {"task_id": "t1", "trace_id": "tr1", "targets": "192.168.1.0/24"},
        ]
        return queue

    def test_response_contains_all_required_fields(self, mock_queue):
        """Test that response contains all required fields."""
        stats = get_queue_stats(mock_queue)

        required_fields = ["pool", "queue_depth", "dlq_size", "next_tasks", "timestamp"]
        for field in required_fields:
            assert field in stats, f"Missing required field: {field}"

    def test_response_types_are_correct(self, mock_queue):
        """Test that response field types are correct."""
        stats = get_queue_stats(mock_queue)

        assert isinstance(stats["pool"], str)
        assert isinstance(stats["queue_depth"], int)
        assert isinstance(stats["dlq_size"], int)
        assert isinstance(stats["next_tasks"], list)
        assert isinstance(stats["timestamp"], str)

    def test_next_tasks_limited_to_three(self, mock_queue):
        """Test that next_tasks preview is limited."""
        mock_queue.peek.return_value = [
            {"task_id": f"task_{i}"} for i in range(10)
        ]

        stats = get_queue_stats(mock_queue)

        # peek is called with count=3
        mock_queue.peek.assert_called_with(count=3, pool="nessus")


class TestQueueDepthCalculation:
    """Tests for queue depth calculation accuracy."""

    @pytest.fixture
    def mock_queue(self):
        """Create mock TaskQueue."""
        queue = MagicMock(spec=TaskQueue)
        queue.default_pool = "nessus"
        queue.peek.return_value = []
        queue.get_dlq_size.return_value = 0
        return queue

    def test_queue_depth_zero(self, mock_queue):
        """Test queue depth when queue is empty."""
        mock_queue.get_queue_depth.return_value = 0

        stats = get_queue_stats(mock_queue)
        assert stats["queue_depth"] == 0

    def test_queue_depth_positive(self, mock_queue):
        """Test queue depth with queued tasks."""
        mock_queue.get_queue_depth.return_value = 42

        stats = get_queue_stats(mock_queue)
        assert stats["queue_depth"] == 42

    def test_queue_depth_large_number(self, mock_queue):
        """Test queue depth with large queue."""
        mock_queue.get_queue_depth.return_value = 10000

        stats = get_queue_stats(mock_queue)
        assert stats["queue_depth"] == 10000


class TestDLQSizeTracking:
    """Tests for DLQ size tracking."""

    @pytest.fixture
    def mock_queue(self):
        """Create mock TaskQueue."""
        queue = MagicMock(spec=TaskQueue)
        queue.default_pool = "nessus"
        queue.peek.return_value = []
        queue.get_queue_depth.return_value = 0
        return queue

    def test_dlq_size_zero(self, mock_queue):
        """Test DLQ size when empty."""
        mock_queue.get_dlq_size.return_value = 0

        stats = get_queue_stats(mock_queue)
        assert stats["dlq_size"] == 0

    def test_dlq_size_positive(self, mock_queue):
        """Test DLQ size with failed tasks."""
        mock_queue.get_dlq_size.return_value = 5

        stats = get_queue_stats(mock_queue)
        assert stats["dlq_size"] == 5

    def test_dlq_independent_of_queue(self, mock_queue):
        """Test that DLQ size is independent of queue depth."""
        mock_queue.get_queue_depth.return_value = 10
        mock_queue.get_dlq_size.return_value = 3

        stats = get_queue_stats(mock_queue)
        assert stats["queue_depth"] == 10
        assert stats["dlq_size"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
