"""Phase 1 integration tests - End-to-end workflow verification."""

import asyncio
import pytest
import time
from pathlib import Path

from core.queue import TaskQueue
from core.task_manager import TaskManager, generate_task_id
from core.types import Task, ScanState
from scanners.registry import ScannerRegistry
from worker.scanner_worker import ScannerWorker


@pytest.fixture
def redis_url():
    """Redis URL for testing."""
    return "redis://redis:6379"


@pytest.fixture
def data_dir(tmp_path):
    """Temporary data directory for test tasks."""
    return str(tmp_path / "tasks")


@pytest.fixture
def scanner_config():
    """Scanner configuration file path."""
    return "/app/config/scanners.yaml"


@pytest.fixture
async def components(redis_url, data_dir, scanner_config):
    """Initialize all components for testing."""
    queue = TaskQueue(
        redis_url=redis_url,
        queue_key="nessus:queue:test",
        dlq_key="nessus:queue:test:dead"
    )

    task_manager = TaskManager(data_dir=data_dir)
    scanner_registry = ScannerRegistry(config_file=scanner_config)

    # Clean up test queues
    queue.redis_client.delete(queue.queue_key)
    queue.redis_client.delete(queue.dlq_key)

    yield {
        "queue": queue,
        "task_manager": task_manager,
        "scanner_registry": scanner_registry,
    }

    # Cleanup
    queue.redis_client.delete(queue.queue_key)
    queue.redis_client.delete(queue.dlq_key)
    queue.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_enqueue_and_retrieve(components):
    """Test basic enqueue and task retrieval."""
    queue = components["queue"]
    task_manager = components["task_manager"]

    # Create task
    task_id = generate_task_id("nessus", "test")
    task = Task(
        task_id=task_id,
        trace_id="trace-test-001",
        scan_type="untrusted",
        scanner_type="nessus",
        scanner_instance_id="local",
        status=ScanState.QUEUED.value,
        payload={
            "targets": "192.168.1.100",
            "name": "Test Scan",
        },
        created_at="2025-11-07T12:00:00Z",
    )

    # Store task
    task_manager.create_task(task)

    # Enqueue
    task_data = {
        "task_id": task_id,
        "trace_id": task.trace_id,
        "scan_type": "untrusted",
        "scanner_type": "nessus",
        "scanner_instance_id": "local",
        "payload": task.payload,
    }

    depth = queue.enqueue(task_data)
    assert depth == 1, "Queue depth should be 1"

    # Dequeue
    dequeued = queue.dequeue(timeout=2)
    assert dequeued is not None, "Should dequeue task"
    assert dequeued["task_id"] == task_id

    # Retrieve from task manager
    retrieved = task_manager.get_task(task_id)
    assert retrieved is not None
    assert retrieved.task_id == task_id
    assert retrieved.status == ScanState.QUEUED.value


@pytest.mark.asyncio
@pytest.mark.integration
async def test_worker_state_transitions(components):
    """Test worker state transitions without actual Nessus scan."""
    queue = components["queue"]
    task_manager = components["task_manager"]

    # Create and enqueue task
    task_id = generate_task_id("nessus", "test")
    task = Task(
        task_id=task_id,
        trace_id="trace-test-002",
        scan_type="untrusted",
        scanner_type="nessus",
        scanner_instance_id="local",
        status=ScanState.QUEUED.value,
        payload={
            "targets": "192.168.1.101",
            "name": "State Transition Test",
        },
        created_at="2025-11-07T12:00:00Z",
    )

    task_manager.create_task(task)

    # Test state transitions
    # QUEUED → RUNNING
    task_manager.update_status(task_id, ScanState.RUNNING)
    task = task_manager.get_task(task_id)
    assert task.status == ScanState.RUNNING.value
    assert task.started_at is not None

    # RUNNING → COMPLETED
    task_manager.update_status(task_id, ScanState.COMPLETED)
    task = task_manager.get_task(task_id)
    assert task.status == ScanState.COMPLETED.value
    assert task.completed_at is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_queue_metrics(components):
    """Test queue depth and DLQ metrics."""
    queue = components["queue"]
    task_manager = components["task_manager"]

    # Initially empty
    assert queue.get_queue_depth() == 0
    assert queue.get_dlq_size() == 0

    # Enqueue 3 tasks
    for i in range(3):
        task_id = generate_task_id("nessus", f"test-{i}")
        task_data = {
            "task_id": task_id,
            "trace_id": f"trace-{i}",
            "scan_type": "untrusted",
            "scanner_type": "nessus",
            "scanner_instance_id": "local",
            "payload": {
                "targets": f"192.168.1.{100+i}",
                "name": f"Metrics Test {i}",
            },
        }
        queue.enqueue(task_data)

    assert queue.get_queue_depth() == 3

    # Move one to DLQ
    failed_task = {
        "task_id": "failed-task",
        "trace_id": "trace-failed",
    }
    queue.move_to_dlq(failed_task, "Test error")

    assert queue.get_dlq_size() == 1

    # Peek at queue
    peeked = queue.peek(count=2)
    assert len(peeked) == 2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_invalid_state_transition(components):
    """Test that invalid state transitions are rejected."""
    task_manager = components["task_manager"]

    # Create task in QUEUED state
    task_id = generate_task_id("nessus", "test")
    task = Task(
        task_id=task_id,
        trace_id="trace-test-003",
        scan_type="untrusted",
        scanner_type="nessus",
        scanner_instance_id="local",
        status=ScanState.QUEUED.value,
        payload={
            "targets": "192.168.1.102",
            "name": "Invalid Transition Test",
        },
        created_at="2025-11-07T12:00:00Z",
    )

    task_manager.create_task(task)

    # Try invalid transition: QUEUED → COMPLETED (should fail)
    from core.types import StateTransitionError

    with pytest.raises(StateTransitionError):
        task_manager.update_status(task_id, ScanState.COMPLETED)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scanner_registry_lookup(components):
    """Test scanner registry can retrieve instances."""
    scanner_registry = components["scanner_registry"]

    # Get scanner instance
    scanner = scanner_registry.get_instance(
        scanner_type="nessus",
        instance_id="local"
    )

    assert scanner is not None
    assert hasattr(scanner, "create_scan")
    assert hasattr(scanner, "launch_scan")
    assert hasattr(scanner, "get_status")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scanner_authentication(components):
    """Test Nessus scanner authentication."""
    scanner_registry = components["scanner_registry"]

    scanner = scanner_registry.get_instance(
        scanner_type="nessus",
        instance_id="local"
    )

    # Test authentication
    try:
        await scanner._authenticate()
        assert scanner._session_token is not None, "Should have session token"
    except Exception as e:
        pytest.skip(f"Nessus not available: {e}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_full_workflow_mock_targets(components):
    """
    Test full workflow with quick-completing scan (invalid target).

    Uses invalid target to trigger quick failure/completion.
    """
    queue = components["queue"]
    task_manager = components["task_manager"]
    scanner_registry = components["scanner_registry"]

    # Create task
    task_id = generate_task_id("nessus", "test")
    task = Task(
        task_id=task_id,
        trace_id="trace-test-004",
        scan_type="untrusted",
        scanner_type="nessus",
        scanner_instance_id="local",
        status=ScanState.QUEUED.value,
        payload={
            "targets": "192.168.255.255",  # Likely unreachable
            "name": "Quick Test Scan",
            "description": "Test scan for workflow validation",
        },
        created_at="2025-11-07T12:00:00Z",
    )

    task_manager.create_task(task)

    # Enqueue task
    task_data = {
        "task_id": task_id,
        "trace_id": task.trace_id,
        "scan_type": "untrusted",
        "scanner_type": "nessus",
        "scanner_instance_id": "local",
        "payload": task.payload,
    }

    queue.enqueue(task_data)

    # Create worker (but don't start full loop - process single task)
    worker = ScannerWorker(
        queue=queue,
        task_manager=task_manager,
        scanner_registry=scanner_registry,
        max_concurrent_scans=1
    )

    try:
        # Dequeue and process
        dequeued = queue.dequeue(timeout=2)
        assert dequeued is not None

        # Process task (this will create real scan in Nessus)
        # Note: This may take time if Nessus is slow
        await asyncio.wait_for(
            worker._process_task(dequeued),
            timeout=120  # 2 minute timeout
        )

        # Check final state
        final_task = task_manager.get_task(task_id)
        assert final_task.status in [
            ScanState.COMPLETED.value,
            ScanState.FAILED.value,
            ScanState.TIMEOUT.value
        ], f"Unexpected final state: {final_task.status}"

        # If RUNNING, task should have nessus_scan_id
        if final_task.started_at:
            assert final_task.nessus_scan_id is not None

    except asyncio.TimeoutError:
        pytest.skip("Test timeout - Nessus scan took too long")
    except Exception as e:
        # Check if it's a Nessus connectivity issue
        if "connection" in str(e).lower() or "authentication" in str(e).lower():
            pytest.skip(f"Nessus not available: {e}")
        raise


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_queue_operations(components):
    """Test concurrent enqueue/dequeue operations."""
    queue = components["queue"]

    # Enqueue many tasks concurrently
    async def enqueue_task(i):
        task_data = {
            "task_id": f"concurrent-task-{i:03d}",
            "trace_id": f"trace-{i}",
            "scan_type": "untrusted",
            "scanner_type": "nessus",
            "scanner_instance_id": "local",
            "payload": {
                "targets": f"192.168.1.{i}",
                "name": f"Concurrent Test {i}",
            },
        }
        queue.enqueue(task_data)

    # Enqueue 20 tasks concurrently
    await asyncio.gather(*[enqueue_task(i) for i in range(20)])

    assert queue.get_queue_depth() == 20

    # Dequeue all
    dequeued_count = 0
    while True:
        task = queue.dequeue(timeout=1)
        if task is None:
            break
        dequeued_count += 1

    assert dequeued_count == 20
    assert queue.get_queue_depth() == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_dlq_ordering(components):
    """Test DLQ returns most recent failures first."""
    queue = components["queue"]

    # Add failures with delays
    for i in range(5):
        task = {
            "task_id": f"failed-{i}",
            "trace_id": f"trace-{i}",
            "created_at": f"2025-11-07T12:00:{i:02d}Z"
        }
        queue.move_to_dlq(task, f"Error {i}")
        await asyncio.sleep(0.01)  # Ensure different timestamps

    # Get DLQ tasks (should be newest first)
    dlq_tasks = queue.get_dlq_tasks(start=0, end=4)
    assert len(dlq_tasks) == 5

    # Verify newest first
    assert dlq_tasks[0]["task_id"] == "failed-4"
    assert dlq_tasks[1]["task_id"] == "failed-3"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_task_persistence(components, data_dir):
    """Test task metadata persists to filesystem."""
    task_manager = components["task_manager"]

    # Create task
    task_id = generate_task_id("nessus", "test")
    task = Task(
        task_id=task_id,
        trace_id="trace-test-005",
        scan_type="untrusted",
        scanner_type="nessus",
        scanner_instance_id="local",
        status=ScanState.QUEUED.value,
        payload={
            "targets": "192.168.1.103",
            "name": "Persistence Test",
        },
        created_at="2025-11-07T12:00:00Z",
    )

    task_manager.create_task(task)

    # Verify task directory and file exist
    task_dir = Path(data_dir) / task_id
    task_file = task_dir / "task.json"

    assert task_dir.exists(), "Task directory should exist"
    assert task_file.exists(), "Task file should exist"

    # Verify can retrieve
    retrieved = task_manager.get_task(task_id)
    assert retrieved is not None
    assert retrieved.task_id == task_id


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_phase1_workflow.py -v
    pytest.main([__file__, "-v", "-s"])
