#!/usr/bin/env python3
"""Smoke test for TaskQueue implementation."""

import sys
sys.path.insert(0, '/app')

from core.queue import TaskQueue, get_queue_stats

def main():
    print("=" * 60)
    print("TaskQueue Smoke Test")
    print("=" * 60)

    # Initialize queue with Redis URL
    print("\n1. Connecting to Redis...")
    queue = TaskQueue(
        redis_url="redis://redis:6379",
        queue_key="nessus:queue:smoke_test",
        dlq_key="nessus:queue:smoke_test:dead"
    )
    print("   ✅ Connected to Redis")

    # Clean up any existing test data
    queue.redis_client.delete(queue.queue_key)
    queue.redis_client.delete(queue.dlq_key)

    # Test 1: Enqueue/Dequeue
    print("\n2. Testing enqueue/dequeue...")
    task1 = {
        "task_id": "test-001",
        "trace_id": "trace-001",
        "scanner_type": "nessus",
        "payload": {"targets": "192.168.1.1"}
    }

    depth = queue.enqueue(task1)
    print(f"   Enqueued task, queue depth: {depth}")
    assert depth == 1, "Queue depth should be 1"

    dequeued = queue.dequeue(timeout=2)
    assert dequeued is not None, "Should dequeue task"
    assert dequeued["task_id"] == "test-001", "Task ID mismatch"
    print(f"   ✅ Dequeued task: {dequeued['task_id']}")

    # Test 2: FIFO Order
    print("\n3. Testing FIFO ordering...")
    for i in range(5):
        queue.enqueue({"task_id": f"task-{i}", "trace_id": f"trace-{i}"})

    print(f"   Enqueued 5 tasks, queue depth: {queue.get_queue_depth()}")

    for i in range(5):
        task = queue.dequeue(timeout=2)
        assert task["task_id"] == f"task-{i}", f"Expected task-{i}, got {task['task_id']}"

    print("   ✅ FIFO ordering verified")

    # Test 3: Dead Letter Queue
    print("\n4. Testing Dead Letter Queue...")
    failed_task = {
        "task_id": "failed-001",
        "trace_id": "trace-failed",
        "payload": {"targets": "10.0.0.1"}
    }

    queue.move_to_dlq(failed_task, "Scanner authentication failed")
    dlq_size = queue.get_dlq_size()
    print(f"   Moved task to DLQ, size: {dlq_size}")
    assert dlq_size == 1, "DLQ should have 1 task"

    dlq_tasks = queue.get_dlq_tasks(start=0, end=0)
    assert len(dlq_tasks) == 1, "Should retrieve 1 DLQ task"
    assert dlq_tasks[0]["error"] == "Scanner authentication failed"
    print(f"   ✅ DLQ task retrieved with error: {dlq_tasks[0]['error']}")

    # Test 4: Peek without removing
    print("\n5. Testing peek...")
    queue.enqueue({"task_id": "peek-1"})
    queue.enqueue({"task_id": "peek-2"})
    queue.enqueue({"task_id": "peek-3"})

    peeked = queue.peek(count=2)
    assert len(peeked) == 2, "Should peek 2 tasks"
    assert queue.get_queue_depth() == 3, "Queue depth should remain 3"
    print(f"   ✅ Peeked {len(peeked)} tasks, queue depth still {queue.get_queue_depth()}")

    # Test 5: Queue stats
    print("\n6. Testing queue statistics...")
    stats = get_queue_stats(queue)
    print(f"   Queue depth: {stats['queue_depth']}")
    print(f"   DLQ size: {stats['dlq_size']}")
    print(f"   Next tasks: {len(stats['next_tasks'])}")
    print(f"   Timestamp: {stats['timestamp']}")
    assert "queue_depth" in stats
    assert "dlq_size" in stats
    assert "next_tasks" in stats
    print("   ✅ Queue stats retrieved")

    # Cleanup
    print("\n7. Cleanup...")
    queue.redis_client.delete(queue.queue_key)
    queue.clear_dlq()
    queue.close()
    print("   ✅ Cleaned up test data")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
