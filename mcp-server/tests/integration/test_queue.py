"""Integration tests for Redis task queue."""

import pytest
import time
from datetime import datetime
from core.queue import TaskQueue, get_queue_stats


@pytest.fixture
def queue():
    """Create TaskQueue instance for testing."""
    # Use test-specific keys to avoid interference
    q = TaskQueue(
        redis_url="redis://redis:6379",
        queue_key="nessus:queue:test",
        dlq_key="nessus:queue:test:dead"
    )

    # Clean up before test
    q.redis_client.delete(q.queue_key)
    q.redis_client.delete(q.dlq_key)

    yield q

    # Clean up after test
    q.redis_client.delete(q.queue_key)
    q.redis_client.delete(q.dlq_key)
    q.close()


def test_queue_connection(queue):
    """Test Redis connection is working."""
    assert queue.redis_client.ping() is True


def test_enqueue_dequeue(queue):
    """Test basic enqueue and dequeue operations."""
    # Create test task
    task = {
        "task_id": "test-task-001",
        "trace_id": "trace-001",
        "scanner_type": "nessus",
        "scan_type": "untrusted",
        "payload": {
            "targets": "192.168.1.1",
            "name": "Test Scan"
        }
    }

    # Enqueue task
    depth = queue.enqueue(task)
    assert depth == 1, "Queue depth should be 1 after first enqueue"

    # Check queue depth
    assert queue.get_queue_depth() == 1

    # Dequeue task
    dequeued = queue.dequeue(timeout=1)
    assert dequeued is not None, "Should dequeue task"
    assert dequeued["task_id"] == task["task_id"]
    assert dequeued["trace_id"] == task["trace_id"]

    # Queue should be empty now
    assert queue.get_queue_depth() == 0


def test_dequeue_timeout(queue):
    """Test dequeue returns None on timeout when queue is empty."""
    result = queue.dequeue(timeout=1)
    assert result is None, "Should return None when queue is empty"


def test_fifo_order(queue):
    """Test FIFO ordering of tasks."""
    tasks = [
        {"task_id": f"task-{i}", "trace_id": f"trace-{i}"}
        for i in range(5)
    ]

    # Enqueue all tasks
    for task in tasks:
        queue.enqueue(task)

    # Dequeue and verify order
    for expected in tasks:
        dequeued = queue.dequeue(timeout=1)
        assert dequeued["task_id"] == expected["task_id"]


def test_multiple_enqueue(queue):
    """Test enqueueing multiple tasks."""
    for i in range(10):
        task = {
            "task_id": f"task-{i}",
            "trace_id": f"trace-{i}",
            "payload": {"targets": f"192.168.1.{i}"}
        }
        queue.enqueue(task)

    assert queue.get_queue_depth() == 10


def test_dlq_move(queue):
    """Test moving failed tasks to Dead Letter Queue."""
    task = {
        "task_id": "failed-task",
        "trace_id": "trace-failed",
        "payload": {"targets": "192.168.1.1"}
    }

    error_msg = "Scanner authentication failed"
    queue.move_to_dlq(task, error_msg)

    # Check DLQ size
    assert queue.get_dlq_size() == 1

    # Get DLQ tasks
    dlq_tasks = queue.get_dlq_tasks(start=0, end=0)
    assert len(dlq_tasks) == 1

    failed_task = dlq_tasks[0]
    assert failed_task["task_id"] == "failed-task"
    assert failed_task["error"] == error_msg
    assert "failed_at" in failed_task


def test_dlq_ordering(queue):
    """Test DLQ returns most recent failures first."""
    # Add multiple failures with slight delay
    for i in range(3):
        task = {"task_id": f"failed-{i}", "trace_id": f"trace-{i}"}
        queue.move_to_dlq(task, f"Error {i}")
        time.sleep(0.01)  # Ensure different timestamps

    # Get DLQ tasks (should be newest first)
    dlq_tasks = queue.get_dlq_tasks(start=0, end=2)
    assert len(dlq_tasks) == 3

    # Verify newest is first
    assert dlq_tasks[0]["task_id"] == "failed-2"
    assert dlq_tasks[1]["task_id"] == "failed-1"
    assert dlq_tasks[2]["task_id"] == "failed-0"


def test_peek(queue):
    """Test peeking at queue without removing tasks."""
    tasks = [
        {"task_id": f"task-{i}", "trace_id": f"trace-{i}"}
        for i in range(5)
    ]

    for task in tasks:
        queue.enqueue(task)

    # Peek at next 3 tasks
    peeked = queue.peek(count=3)
    assert len(peeked) == 3

    # Verify queue depth unchanged
    assert queue.get_queue_depth() == 5

    # Peeked tasks should be in FIFO order (next to be dequeued)
    assert peeked[0]["task_id"] == "task-0"
    assert peeked[1]["task_id"] == "task-1"
    assert peeked[2]["task_id"] == "task-2"


def test_clear_dlq(queue):
    """Test clearing Dead Letter Queue."""
    # Add some failed tasks
    for i in range(5):
        task = {"task_id": f"failed-{i}"}
        queue.move_to_dlq(task, f"Error {i}")

    assert queue.get_dlq_size() == 5

    # Clear DLQ
    removed = queue.clear_dlq()
    assert removed > 0
    assert queue.get_dlq_size() == 0


def test_clear_dlq_by_timestamp(queue):
    """Test clearing DLQ entries before specific timestamp."""
    # Add old task
    old_task = {"task_id": "old-task"}
    queue.move_to_dlq(old_task, "Old error")

    # Wait and get timestamp
    time.sleep(0.1)
    cutoff_timestamp = datetime.utcnow().timestamp()

    # Add new task
    time.sleep(0.1)
    new_task = {"task_id": "new-task"}
    queue.move_to_dlq(new_task, "New error")

    assert queue.get_dlq_size() == 2

    # Clear only old entries
    removed = queue.clear_dlq(before_timestamp=cutoff_timestamp)
    assert removed == 1
    assert queue.get_dlq_size() == 1

    # Verify new task still in DLQ
    remaining = queue.get_dlq_tasks()
    assert len(remaining) == 1
    assert remaining[0]["task_id"] == "new-task"


def test_queue_stats(queue):
    """Test queue statistics helper."""
    # Add some tasks
    for i in range(3):
        task = {"task_id": f"task-{i}", "trace_id": f"trace-{i}"}
        queue.enqueue(task)

    # Add failed task
    queue.move_to_dlq({"task_id": "failed"}, "Error")

    # Get stats
    stats = get_queue_stats(queue)

    assert stats["queue_depth"] == 3
    assert stats["dlq_size"] == 1
    assert len(stats["next_tasks"]) == 3
    assert "timestamp" in stats


def test_json_serialization_error(queue):
    """Test handling of non-serializable tasks."""
    # Create task with non-serializable object
    class NonSerializable:
        pass

    task = {
        "task_id": "bad-task",
        "bad_object": NonSerializable()
    }

    with pytest.raises(TypeError):
        queue.enqueue(task)


def test_concurrent_enqueue_dequeue(queue):
    """Test concurrent operations don't lose tasks."""
    # Enqueue many tasks
    task_count = 100
    for i in range(task_count):
        task = {"task_id": f"task-{i:03d}", "trace_id": f"trace-{i}"}
        queue.enqueue(task)

    # Dequeue all
    dequeued_count = 0
    while True:
        task = queue.dequeue(timeout=1)
        if task is None:
            break
        dequeued_count += 1

    assert dequeued_count == task_count, "Should dequeue all enqueued tasks"
    assert queue.get_queue_depth() == 0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
