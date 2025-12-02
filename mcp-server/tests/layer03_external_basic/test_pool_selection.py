"""Integration tests for pool-based workflow operations.

These tests verify end-to-end pool functionality with real Redis.
Requires: Redis running on localhost:6379 (or REDIS_URL env var)
"""

import os

import pytest

# Skip if Redis not available
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


@pytest.fixture
def redis_available():
    """Check if Redis is available."""
    try:
        import redis

        client = redis.from_url(REDIS_URL)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


@pytest.fixture
def task_queue(redis_available):
    """Create TaskQueue connected to Redis."""
    if not redis_available:
        pytest.skip("Redis not available")

    from core.queue import TaskQueue

    queue = TaskQueue(redis_url=REDIS_URL)

    # Clear test queues before test
    for pool in ["nessus", "nessus_dmz", "nessus_lan", "test_pool"]:
        queue.redis_client.delete(f"{pool}:queue")
        queue.redis_client.delete(f"{pool}:queue:dead")

    yield queue
    queue.close()


class TestPoolQueueWorkflow:
    """Test pool-based queue operations with real Redis."""

    def test_enqueue_to_multiple_pools(self, task_queue):
        """Test enqueueing tasks to different pools."""
        # Enqueue to different pools
        task1 = {"task_id": "task-001", "scanner_pool": "nessus"}
        task2 = {"task_id": "task-002", "scanner_pool": "nessus_dmz"}
        task3 = {"task_id": "task-003", "scanner_pool": "nessus_lan"}

        task_queue.enqueue(task1, pool="nessus")
        task_queue.enqueue(task2, pool="nessus_dmz")
        task_queue.enqueue(task3, pool="nessus_lan")

        # Verify each pool has exactly one task
        assert task_queue.get_queue_depth(pool="nessus") == 1
        assert task_queue.get_queue_depth(pool="nessus_dmz") == 1
        assert task_queue.get_queue_depth(pool="nessus_lan") == 1

    def test_dequeue_from_specific_pool(self, task_queue):
        """Test dequeuing from specific pool."""
        # Enqueue to different pools
        task_queue.enqueue({"task_id": "nessus-001"}, pool="nessus")
        task_queue.enqueue({"task_id": "dmz-001"}, pool="nessus_dmz")

        # Dequeue from nessus pool only
        result = task_queue.dequeue(pool="nessus", timeout=1)

        assert result["task_id"] == "nessus-001"
        assert task_queue.get_queue_depth(pool="nessus") == 0
        assert task_queue.get_queue_depth(pool="nessus_dmz") == 1

    def test_dequeue_any_fifo_order(self, task_queue):
        """Test dequeue_any respects FIFO within pools."""
        # Enqueue multiple tasks to same pool
        for i in range(5):
            task_queue.enqueue({"task_id": f"task-{i}"}, pool="nessus")

        # Dequeue in order
        for i in range(5):
            result = task_queue.dequeue(pool="nessus", timeout=1)
            assert result["task_id"] == f"task-{i}"

    def test_dequeue_any_across_pools(self, task_queue):
        """Test dequeue_any gets task from any specified pool."""
        # Enqueue to nessus_dmz only
        task_queue.enqueue({"task_id": "dmz-task"}, pool="nessus_dmz")

        # Dequeue from any pool (nessus is empty)
        result = task_queue.dequeue_any(["nessus", "nessus_dmz"], timeout=1)

        assert result["task_id"] == "dmz-task"

    def test_pool_isolation(self, task_queue):
        """Test that pools are isolated - dequeue doesn't cross pools."""
        # Enqueue to nessus_dmz
        task_queue.enqueue({"task_id": "dmz-task"}, pool="nessus_dmz")

        # Try to dequeue from nessus (should timeout/return None)
        result = task_queue.dequeue(pool="nessus", timeout=1)

        assert result is None
        # Task still in dmz
        assert task_queue.get_queue_depth(pool="nessus_dmz") == 1

    def test_move_to_dlq_per_pool(self, task_queue):
        """Test DLQ is pool-specific."""
        task1 = {"task_id": "task-001"}
        task2 = {"task_id": "task-002"}

        task_queue.move_to_dlq(task1, "Error 1", pool="nessus")
        task_queue.move_to_dlq(task2, "Error 2", pool="nessus_dmz")

        assert task_queue.get_dlq_size(pool="nessus") == 1
        assert task_queue.get_dlq_size(pool="nessus_dmz") == 1

        # Verify DLQ tasks
        nessus_dlq = task_queue.get_dlq_tasks(pool="nessus")
        dmz_dlq = task_queue.get_dlq_tasks(pool="nessus_dmz")

        assert nessus_dlq[0]["task_id"] == "task-001"
        assert dmz_dlq[0]["task_id"] == "task-002"

    def test_clear_dlq_per_pool(self, task_queue):
        """Test clearing DLQ is pool-specific."""
        # Add to both DLQs
        task_queue.move_to_dlq({"task_id": "task-001"}, "Error", pool="nessus")
        task_queue.move_to_dlq({"task_id": "task-002"}, "Error", pool="nessus_dmz")

        # Clear only nessus DLQ
        task_queue.clear_dlq(pool="nessus")

        assert task_queue.get_dlq_size(pool="nessus") == 0
        assert task_queue.get_dlq_size(pool="nessus_dmz") == 1

    def test_peek_per_pool(self, task_queue):
        """Test peeking at pool-specific queue."""
        task_queue.enqueue({"task_id": "nessus-001"}, pool="nessus")
        task_queue.enqueue({"task_id": "dmz-001"}, pool="nessus_dmz")

        nessus_peek = task_queue.peek(pool="nessus")
        dmz_peek = task_queue.peek(pool="nessus_dmz")

        assert nessus_peek[0]["task_id"] == "nessus-001"
        assert dmz_peek[0]["task_id"] == "dmz-001"


class TestPoolStatsWorkflow:
    """Test pool statistics with real Redis."""

    def test_get_queue_stats_per_pool(self, task_queue):
        """Test queue stats are pool-specific."""
        from core.queue import get_queue_stats

        # Setup different queues
        for i in range(5):
            task_queue.enqueue({"task_id": f"task-{i}"}, pool="nessus")
        for i in range(3):
            task_queue.enqueue({"task_id": f"dmz-{i}"}, pool="nessus_dmz")

        nessus_stats = get_queue_stats(task_queue, pool="nessus")
        dmz_stats = get_queue_stats(task_queue, pool="nessus_dmz")

        assert nessus_stats["pool"] == "nessus"
        assert nessus_stats["queue_depth"] == 5
        assert dmz_stats["pool"] == "nessus_dmz"
        assert dmz_stats["queue_depth"] == 3

    def test_get_all_pool_stats(self, task_queue):
        """Test aggregating stats across pools."""
        from core.queue import get_all_pool_stats

        # Setup different queues
        task_queue.enqueue({"task_id": "task-1"}, pool="nessus")
        task_queue.enqueue({"task_id": "task-2"}, pool="nessus")
        task_queue.enqueue({"task_id": "dmz-1"}, pool="nessus_dmz")
        task_queue.move_to_dlq({"task_id": "failed-1"}, "Error", pool="nessus")

        stats = get_all_pool_stats(task_queue, ["nessus", "nessus_dmz", "nessus_lan"])

        assert stats["total_queue_depth"] == 3
        assert stats["total_dlq_size"] == 1
        assert len(stats["pools"]) == 3


class TestWorkerPoolConsumption:
    """Test worker consuming from pool queues."""

    def test_worker_consumes_from_specified_pools(self, task_queue):
        """Test worker only consumes from configured pools."""
        # Enqueue to multiple pools
        task_queue.enqueue({"task_id": "nessus-001"}, pool="nessus")
        task_queue.enqueue({"task_id": "dmz-001"}, pool="nessus_dmz")
        task_queue.enqueue({"task_id": "lan-001"}, pool="nessus_lan")

        # Simulate worker consuming only from nessus and dmz
        worker_pools = ["nessus", "nessus_dmz"]

        # Dequeue all from worker pools
        consumed = []
        while True:
            task = task_queue.dequeue_any(worker_pools, timeout=1)
            if not task:
                break
            consumed.append(task["task_id"])

        # Should have consumed from nessus and dmz but not lan
        assert "nessus-001" in consumed
        assert "dmz-001" in consumed
        assert "lan-001" not in consumed

        # lan task still in queue
        assert task_queue.get_queue_depth(pool="nessus_lan") == 1

    def test_worker_round_robin_consumption(self, task_queue):
        """Test worker consumes fairly from multiple pools."""
        # Enqueue tasks to multiple pools
        for i in range(3):
            task_queue.enqueue({"task_id": f"nessus-{i}"}, pool="nessus")
            task_queue.enqueue({"task_id": f"dmz-{i}"}, pool="nessus_dmz")

        # Consume all tasks
        worker_pools = ["nessus", "nessus_dmz"]
        consumed = []

        while (
            task_queue.get_queue_depth(pool="nessus")
            + task_queue.get_queue_depth(pool="nessus_dmz")
            > 0
        ):
            task = task_queue.dequeue_any(worker_pools, timeout=1)
            if task:
                consumed.append(task["task_id"])

        # All tasks should be consumed
        assert len(consumed) == 6
        assert sum(1 for t in consumed if t.startswith("nessus-")) == 3
        assert sum(1 for t in consumed if t.startswith("dmz-")) == 3


class TestPoolBackwardCompatibility:
    """Test backward compatibility with pre-pool code."""

    def test_default_pool_behavior(self, task_queue):
        """Test default pool is used when pool not specified."""
        # Enqueue without specifying pool
        task_queue.enqueue({"task_id": "task-001"})

        # Should be in default pool
        assert task_queue.get_queue_depth() == 1
        assert task_queue.get_queue_depth(pool="nessus") == 1

    def test_dequeue_without_pool(self, task_queue):
        """Test dequeue uses default pool when not specified."""
        task_queue.enqueue({"task_id": "task-001"}, pool="nessus")

        # Dequeue without specifying pool
        result = task_queue.dequeue(timeout=1)

        assert result["task_id"] == "task-001"

    def test_scanner_pool_in_task_data(self, task_queue):
        """Test scanner_pool in task data is respected."""
        # Enqueue task with scanner_pool in data
        task = {
            "task_id": "task-001",
            "scanner_pool": "nessus_dmz",
            "payload": {"targets": "192.168.1.1"},
        }
        task_queue.enqueue(task)  # No pool param, should use task's scanner_pool

        # Should be in nessus_dmz
        assert task_queue.get_queue_depth(pool="nessus_dmz") == 1
        assert task_queue.get_queue_depth(pool="nessus") == 0
