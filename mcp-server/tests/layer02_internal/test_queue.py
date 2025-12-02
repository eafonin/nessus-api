"""Unit tests for pool-based queue operations."""

import json
from unittest.mock import MagicMock, patch

import pytest

# Mock redis module before importing TaskQueue
mock_redis_module = MagicMock()


@pytest.fixture(scope="module", autouse=True)
def mock_redis_import():
    """Mock redis import at module level."""
    with patch.dict("sys.modules", {"redis": mock_redis_module}):
        yield


class TestTaskQueuePools:
    """Test TaskQueue pool functionality."""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        mock = MagicMock()
        mock.ping.return_value = True
        mock.lpush.return_value = 1
        mock.brpop.return_value = None
        mock.llen.return_value = 0
        mock.zcard.return_value = 0
        mock.zadd.return_value = 1
        mock.lrange.return_value = []
        mock.delete.return_value = 1
        return mock

    @pytest.fixture
    def task_queue(self, mock_redis_client):
        """TaskQueue with mocked Redis."""
        from core.queue import TaskQueue

        # Patch redis.from_url to return our mock
        with patch("core.queue.redis") as mock_redis:
            mock_redis.from_url.return_value = mock_redis_client
            mock_redis.ConnectionError = Exception
            mock_redis.RedisError = Exception

            queue = TaskQueue(redis_url="redis://localhost:6379")
            return queue

    def test_queue_key_generation(self, task_queue):
        """Test pool-specific queue key generation."""
        assert task_queue._queue_key("nessus") == "nessus:queue"
        assert task_queue._queue_key("nessus_dmz") == "nessus_dmz:queue"
        assert task_queue._queue_key("nuclei") == "nuclei:queue"

    def test_dlq_key_generation(self, task_queue):
        """Test pool-specific DLQ key generation."""
        assert task_queue._dlq_key("nessus") == "nessus:queue:dead"
        assert task_queue._dlq_key("nessus_dmz") == "nessus_dmz:queue:dead"
        assert task_queue._dlq_key("nuclei") == "nuclei:queue:dead"

    def test_enqueue_to_default_pool(self, task_queue):
        """Test enqueue uses default pool when not specified."""
        task = {"task_id": "test-001", "payload": {"targets": "192.168.1.1"}}
        task_queue.enqueue(task)

        # Should use default pool "nessus"
        task_queue.redis_client.lpush.assert_called_once()
        call_args = task_queue.redis_client.lpush.call_args
        assert call_args[0][0] == "nessus:queue"

    def test_enqueue_to_specific_pool(self, task_queue):
        """Test enqueue to specific pool."""
        task = {"task_id": "test-001", "payload": {"targets": "192.168.1.1"}}
        task_queue.enqueue(task, pool="nessus_dmz")

        task_queue.redis_client.lpush.assert_called_once()
        call_args = task_queue.redis_client.lpush.call_args
        assert call_args[0][0] == "nessus_dmz:queue"

    def test_enqueue_uses_task_scanner_pool(self, task_queue):
        """Test enqueue uses scanner_pool from task data."""
        task = {
            "task_id": "test-001",
            "scanner_pool": "nessus_lan",
            "payload": {"targets": "10.0.0.1"},
        }
        task_queue.enqueue(task)

        task_queue.redis_client.lpush.assert_called_once()
        call_args = task_queue.redis_client.lpush.call_args
        assert call_args[0][0] == "nessus_lan:queue"

    def test_enqueue_pool_param_takes_precedence(self, task_queue):
        """Test pool parameter takes precedence over task scanner_pool."""
        task = {
            "task_id": "test-001",
            "scanner_pool": "nessus_lan",
            "payload": {"targets": "10.0.0.1"},
        }
        task_queue.enqueue(task, pool="nessus_dmz")

        task_queue.redis_client.lpush.assert_called_once()
        call_args = task_queue.redis_client.lpush.call_args
        assert call_args[0][0] == "nessus_dmz:queue"

    def test_dequeue_from_default_pool(self, task_queue):
        """Test dequeue from default pool."""
        task_data = {"task_id": "test-001"}
        task_queue.redis_client.brpop.return_value = (
            "nessus:queue",
            json.dumps(task_data),
        )

        result = task_queue.dequeue()

        task_queue.redis_client.brpop.assert_called_once_with("nessus:queue", timeout=5)
        assert result["task_id"] == "test-001"

    def test_dequeue_from_specific_pool(self, task_queue):
        """Test dequeue from specific pool."""
        task_data = {"task_id": "test-002"}
        task_queue.redis_client.brpop.return_value = (
            "nessus_dmz:queue",
            json.dumps(task_data),
        )

        result = task_queue.dequeue(pool="nessus_dmz")

        task_queue.redis_client.brpop.assert_called_once_with(
            "nessus_dmz:queue", timeout=5
        )
        assert result["task_id"] == "test-002"

    def test_dequeue_any_from_multiple_pools(self, task_queue):
        """Test dequeue_any from multiple pools."""
        task_data = {"task_id": "test-003", "scanner_pool": "nessus"}
        task_queue.redis_client.brpop.return_value = (
            "nessus:queue",
            json.dumps(task_data),
        )

        pools = ["nessus", "nessus_dmz", "nessus_lan"]
        result = task_queue.dequeue_any(pools)

        task_queue.redis_client.brpop.assert_called_once()
        call_args = task_queue.redis_client.brpop.call_args
        # Check all pool keys are passed
        assert "nessus:queue" in call_args[0][0]
        assert "nessus_dmz:queue" in call_args[0][0]
        assert "nessus_lan:queue" in call_args[0][0]
        assert result["task_id"] == "test-003"

    def test_dequeue_any_timeout(self, task_queue):
        """Test dequeue_any returns None on timeout."""
        task_queue.redis_client.brpop.return_value = None

        result = task_queue.dequeue_any(["nessus", "nessus_dmz"])

        assert result is None

    def test_get_queue_depth_for_pool(self, task_queue):
        """Test get_queue_depth for specific pool."""
        task_queue.redis_client.llen.return_value = 5

        depth = task_queue.get_queue_depth(pool="nessus_dmz")

        task_queue.redis_client.llen.assert_called_once_with("nessus_dmz:queue")
        assert depth == 5

    def test_get_dlq_size_for_pool(self, task_queue):
        """Test get_dlq_size for specific pool."""
        task_queue.redis_client.zcard.return_value = 3

        size = task_queue.get_dlq_size(pool="nuclei")

        task_queue.redis_client.zcard.assert_called_once_with("nuclei:queue:dead")
        assert size == 3

    def test_move_to_dlq_uses_pool(self, task_queue):
        """Test move_to_dlq uses pool-specific DLQ."""
        task = {"task_id": "test-001", "scanner_pool": "nessus_dmz"}

        task_queue.move_to_dlq(task, "Test error")

        task_queue.redis_client.zadd.assert_called_once()
        call_args = task_queue.redis_client.zadd.call_args
        assert call_args[0][0] == "nessus_dmz:queue:dead"

    def test_peek_from_specific_pool(self, task_queue):
        """Test peek from specific pool."""
        task_data = [json.dumps({"task_id": "test-001"})]
        task_queue.redis_client.lrange.return_value = task_data

        result = task_queue.peek(count=1, pool="nessus_lan")

        task_queue.redis_client.lrange.assert_called_once_with(
            "nessus_lan:queue", -1, -1
        )
        assert len(result) == 1

    def test_clear_dlq_for_pool(self, task_queue):
        """Test clear_dlq for specific pool."""
        task_queue.redis_client.delete.return_value = 5

        removed = task_queue.clear_dlq(pool="nessus_dmz")

        task_queue.redis_client.delete.assert_called_once_with("nessus_dmz:queue:dead")
        assert removed == 5


class TestGetQueueStats:
    """Test get_queue_stats helper function."""

    def test_get_queue_stats_default_pool(self):
        """Test get_queue_stats uses default pool."""
        from core.queue import get_queue_stats

        mock_queue = MagicMock()
        mock_queue.default_pool = "nessus"
        mock_queue.get_queue_depth.return_value = 10
        mock_queue.get_dlq_size.return_value = 2
        mock_queue.peek.return_value = [{"task_id": "test-001"}]

        stats = get_queue_stats(mock_queue)

        assert stats["pool"] == "nessus"
        assert stats["queue_depth"] == 10
        assert stats["dlq_size"] == 2
        assert len(stats["next_tasks"]) == 1

    def test_get_queue_stats_specific_pool(self):
        """Test get_queue_stats for specific pool."""
        from core.queue import get_queue_stats

        mock_queue = MagicMock()
        mock_queue.default_pool = "nessus"
        mock_queue.get_queue_depth.return_value = 5
        mock_queue.get_dlq_size.return_value = 1
        mock_queue.peek.return_value = []

        stats = get_queue_stats(mock_queue, pool="nessus_dmz")

        mock_queue.get_queue_depth.assert_called_with(pool="nessus_dmz")
        mock_queue.get_dlq_size.assert_called_with(pool="nessus_dmz")
        mock_queue.peek.assert_called_with(count=3, pool="nessus_dmz")
        assert stats["pool"] == "nessus_dmz"


class TestGetAllPoolStats:
    """Test get_all_pool_stats helper function."""

    def test_get_all_pool_stats(self):
        """Test aggregating stats across all pools."""
        from core.queue import get_all_pool_stats

        mock_queue = MagicMock()

        def queue_depth_side_effect(pool=None):
            return {"nessus": 5, "nessus_dmz": 3, "nuclei": 0}.get(pool, 0)

        def dlq_size_side_effect(pool=None):
            return {"nessus": 1, "nessus_dmz": 2, "nuclei": 0}.get(pool, 0)

        mock_queue.get_queue_depth.side_effect = queue_depth_side_effect
        mock_queue.get_dlq_size.side_effect = dlq_size_side_effect

        pools = ["nessus", "nessus_dmz", "nuclei"]
        stats = get_all_pool_stats(mock_queue, pools)

        assert stats["total_queue_depth"] == 8  # 5 + 3 + 0
        assert stats["total_dlq_size"] == 3  # 1 + 2 + 0
        assert len(stats["pools"]) == 3
        assert stats["pools"][0]["pool"] == "nessus"
        assert stats["pools"][0]["queue_depth"] == 5
