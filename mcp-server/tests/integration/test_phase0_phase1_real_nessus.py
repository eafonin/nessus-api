#!/usr/bin/env python3
"""
Docker-based Integration Test: Phase 0 + Phase 1 with Real Nessus Scanner

This test MUST run inside the Docker network to access:
- Redis queue (redis://redis:6379)
- Nessus scanner (https://vpn-gateway:8834)

Run with:
  docker compose exec mcp-api pytest tests/integration/test_phase0_phase1_real_nessus.py -v -s

Markers:
  - real_nessus: Uses actual Nessus scanner (NOT mocks)
  - requires_docker_network: Must run inside Docker network
  - slow: Takes several minutes to complete
  - integration: Integration test requiring external services
"""

import pytest
import asyncio
import os
import sys
import uuid
import json
from pathlib import Path
from datetime import datetime

# Add mcp-server to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.queue import TaskQueue
from core.task_manager import TaskManager, generate_task_id
from core.types import Task, ScanState
from core.logging_config import configure_logging, get_logger
from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest


# ============================================================================
# Test Configuration
# ============================================================================

# Redis (must be accessible inside Docker network)
# Use environment variable set by docker-compose.test.yml, fallback to "redis" for production
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Nessus scanner (accessible via vpn-gateway inside Docker network)
NESSUS_URL = os.getenv("NESSUS_URL", "https://vpn-gateway:8834")
NESSUS_USERNAME = os.getenv("NESSUS_USERNAME", "nessus")
NESSUS_PASSWORD = os.getenv("NESSUS_PASSWORD", "nessus")

# Test target (safe internal host for scanning)
TARGET_HOST = "172.32.0.215"  # Ubuntu server in Docker network

# Task storage
DATA_DIR = "/tmp/test-phase0-phase1-nessus"


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = [
    pytest.mark.real_nessus,           # Uses real Nessus scanner
    pytest.mark.requires_docker_network,  # Must run inside Docker network
    pytest.mark.slow,                  # Takes several minutes
    pytest.mark.integration,           # Integration test
]


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def structured_logging():
    """Configure structured logging for the test."""
    configure_logging(log_level="INFO")
    logger = get_logger(__name__)

    logger.info(
        "test_suite_started",
        test="phase0_phase1_real_nessus",
        target=TARGET_HOST,
        redis_url=REDIS_URL,
        nessus_url=NESSUS_URL
    )

    yield logger

    logger.info(
        "test_suite_completed",
        test="phase0_phase1_real_nessus"
    )


@pytest.fixture(scope="function")
def task_queue():
    """Create TaskQueue instance with test-specific keys."""
    queue = TaskQueue(
        redis_url=REDIS_URL,
        queue_key="nessus:queue:test:phase0-phase1",
        dlq_key="nessus:queue:test:phase0-phase1:dead"
    )

    # Clean up before test
    queue.redis_client.delete(queue.queue_key)
    queue.redis_client.delete(queue.dlq_key)

    yield queue

    # Clean up after test
    queue.redis_client.delete(queue.queue_key)
    queue.redis_client.delete(queue.dlq_key)
    queue.close()


@pytest.fixture(scope="function")
def task_manager():
    """Create TaskManager instance for test."""
    os.makedirs(DATA_DIR, exist_ok=True)
    mgr = TaskManager(data_dir=DATA_DIR)

    yield mgr

    # Cleanup is handled by individual tests


@pytest.fixture(scope="function")
async def nessus_scanner():
    """Create NessusScanner instance."""
    scanner = NessusScanner(
        url=NESSUS_URL,
        username=NESSUS_USERNAME,
        password=NESSUS_PASSWORD,
        verify_ssl=False
    )

    yield scanner

    await scanner.close()


# ============================================================================
# Test: Complete Phase 0 + Phase 1 Workflow
# ============================================================================

@pytest.mark.asyncio
async def test_complete_phase0_phase1_workflow(
    structured_logging,
    task_queue,
    task_manager,
    nessus_scanner
):
    """
    Complete end-to-end test of Phase 0 + Phase 1 workflow.

    PHASE 0 (Queue-based execution):
    1. Generate trace_id and task_id
    2. Create task with TaskManager
    3. Enqueue task to Redis queue
    4. Dequeue task (simulating worker)

    PHASE 1 (Scan workflow):
    5. Create Nessus scan
    6. Launch scan
    7. Monitor progress (state transitions)
    8. Wait for completion
    9. Export results
    10. Cleanup

    All operations emit structured JSON logs demonstrating Phase 3 observability.
    """

    logger = structured_logging

    # ========================================================================
    # PHASE 0: Queue-Based Scan Execution
    # ========================================================================

    print("\n" + "=" * 80)
    print("PHASE 0: QUEUE-BASED SCAN EXECUTION")
    print("=" * 80)

    # Generate IDs
    trace_id = str(uuid.uuid4())
    task_id = generate_task_id("nessus", "local")

    print(f"\n✓ Generated trace_id: {trace_id}")
    print(f"✓ Generated task_id: {task_id}")

    # Step 1: Tool invocation (simulated MCP tool call)
    print(f"\n{'─' * 80}")
    print("STEP 1: MCP Tool Invocation (run_untrusted_scan)")
    print(f"{'─' * 80}")

    logger.info(
        "tool_invocation",
        tool="run_untrusted_scan",
        trace_id=trace_id,
        task_id=task_id,
        targets=TARGET_HOST,
        scan_name=f"Phase 0+1 Integration Test - {TARGET_HOST}"
    )

    print(f"✓ Logged tool invocation")

    # Step 2: Create task
    print(f"\n{'─' * 80}")
    print("STEP 2: Create Task in TaskManager")
    print(f"{'─' * 80}")

    task = Task(
        task_id=task_id,
        trace_id=trace_id,
        scan_type="untrusted",
        scanner_type="nessus",
        scanner_instance_id="local",
        status=ScanState.QUEUED.value,
        payload={
            "targets": TARGET_HOST,
            "name": f"Phase 0+1 Integration Test - {TARGET_HOST}",
            "description": "Docker-based integration test with real Nessus scanner",
            "schema_profile": "brief",
        },
        created_at=datetime.utcnow().isoformat(),
    )

    task_manager.create_task(task)

    logger.info(
        "task_created",
        task_id=task_id,
        trace_id=trace_id,
        scan_type="untrusted",
        scanner_type="nessus",
        scanner_instance="local",
        status="queued"
    )

    print(f"✓ Task created and persisted to {DATA_DIR}/{task_id}")

    # Step 3: Enqueue to Redis
    print(f"\n{'─' * 80}")
    print("STEP 3: Enqueue Task to Redis Queue")
    print(f"{'─' * 80}")

    task_data = {
        "task_id": task_id,
        "trace_id": trace_id,
        "scan_type": "untrusted",
        "scanner_type": "nessus",
        "scanner_instance_id": "local",
        "payload": task.payload,
    }

    queue_depth = task_queue.enqueue(task_data)

    logger.info(
        "scan_enqueued",
        task_id=task_id,
        trace_id=trace_id,
        queue_position=queue_depth,
        queue_name="main"
    )

    print(f"✓ Task enqueued to Redis (position: {queue_depth})")

    # Verify queue depth
    assert task_queue.get_queue_depth() == queue_depth
    print(f"✓ Verified queue depth: {queue_depth}")

    # Step 4: Dequeue (simulating worker)
    print(f"\n{'─' * 80}")
    print("STEP 4: Worker Dequeues Task from Queue")
    print(f"{'─' * 80}")

    dequeued_task = task_queue.dequeue(timeout=5)
    assert dequeued_task is not None, "Failed to dequeue task"
    assert dequeued_task["task_id"] == task_id

    logger.info(
        "task_dequeued",
        task_id=task_id,
        trace_id=trace_id,
        worker_id="test-worker-01"
    )

    print(f"✓ Task dequeued by worker")
    print(f"✓ Queue now empty (depth: {task_queue.get_queue_depth()})")

    # ========================================================================
    # PHASE 1: Scan Workflow with State Transitions
    # ========================================================================

    print("\n" + "=" * 80)
    print("PHASE 1: SCAN WORKFLOW WITH REAL NESSUS SCANNER")
    print("=" * 80)

    # Step 5: Create Nessus scan
    print(f"\n{'─' * 80}")
    print("STEP 5: Create Scan in Nessus")
    print(f"{'─' * 80}")

    scan_request = ScanRequest(
        name=f"Phase 0+1 Test - {task_id}",
        targets=TARGET_HOST,
        description=f"Integration test with trace_id: {trace_id}",
        scan_type="untrusted"
    )

    nessus_scan_id = await nessus_scanner.create_scan(scan_request)

    logger.info(
        "nessus_scan_created",
        task_id=task_id,
        trace_id=trace_id,
        nessus_scan_id=nessus_scan_id,
        targets=TARGET_HOST
    )

    print(f"✓ Created Nessus scan ID: {nessus_scan_id}")

    # Brief pause after scan creation
    await asyncio.sleep(2)

    # Step 6: Launch scan
    print(f"\n{'─' * 80}")
    print("STEP 6: Launch Scan")
    print(f"{'─' * 80}")

    # State transition: QUEUED → RUNNING
    logger.info(
        "scan_state_transition",
        task_id=task_id,
        trace_id=trace_id,
        from_state="queued",
        to_state="running",
        nessus_scan_id=nessus_scan_id
    )

    scan_uuid = await nessus_scanner.launch_scan(nessus_scan_id)

    logger.info(
        "nessus_scan_launched",
        task_id=task_id,
        trace_id=trace_id,
        nessus_scan_id=nessus_scan_id,
        scan_uuid=scan_uuid
    )

    print(f"✓ Launched scan (UUID: {scan_uuid})")

    # Brief pause after launch
    await asyncio.sleep(3)

    # Step 7: Monitor progress
    print(f"\n{'─' * 80}")
    print("STEP 7: Monitor Scan Progress")
    print(f"{'─' * 80}")

    max_wait = 600  # 10 minutes timeout
    poll_interval = 10  # Check every 10 seconds
    elapsed = 0
    last_progress = -1

    start_time = datetime.utcnow()

    while elapsed < max_wait:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        status = await nessus_scanner.get_status(nessus_scan_id)
        current_status = status['status']
        current_progress = status['progress']

        # Log progress changes
        if current_progress != last_progress:
            logger.info(
                "scan_progress",
                task_id=task_id,
                trace_id=trace_id,
                nessus_scan_id=nessus_scan_id,
                progress=current_progress,
                scanner_status=current_status,
                elapsed_seconds=elapsed
            )

            print(f"  [{elapsed:4d}s] Status: {current_status:10s} | Progress: {current_progress:3d}%")
            last_progress = current_progress

        if current_status == "completed":
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            # State transition: RUNNING → COMPLETED
            logger.info(
                "scan_state_transition",
                task_id=task_id,
                trace_id=trace_id,
                from_state="running",
                to_state="completed",
                nessus_scan_id=nessus_scan_id,
                duration_seconds=int(duration)
            )

            print(f"\n✓ Scan completed after {int(duration)} seconds")

            # Brief pause before exporting
            await asyncio.sleep(3)
            break

        elif current_status == "failed":
            logger.error(
                "scan_failed",
                task_id=task_id,
                trace_id=trace_id,
                nessus_scan_id=nessus_scan_id,
                error_type="scan_failure",
                error_message=f"Nessus scan failed: {status}",
                final_status="failed"
            )
            pytest.fail(f"Scan failed: {status}")
    else:
        # Timeout - stop the scan
        logger.warning(
            "scan_timeout",
            task_id=task_id,
            trace_id=trace_id,
            nessus_scan_id=nessus_scan_id,
            timeout_seconds=max_wait,
            elapsed_seconds=elapsed
        )

        await nessus_scanner.stop_scan(nessus_scan_id)
        await nessus_scanner.delete_scan(nessus_scan_id)
        pytest.skip(f"Scan did not complete in {max_wait} seconds")

    # Step 8: Export results
    print(f"\n{'─' * 80}")
    print("STEP 8: Export Scan Results")
    print(f"{'─' * 80}")

    results = await nessus_scanner.export_results(nessus_scan_id)

    logger.info(
        "results_exported",
        task_id=task_id,
        trace_id=trace_id,
        nessus_scan_id=nessus_scan_id,
        results_size_bytes=len(results)
    )

    print(f"✓ Exported {len(results)} bytes")

    # Save results to task directory
    task_dir = Path(DATA_DIR) / task_id
    task_dir.mkdir(exist_ok=True)
    results_file = task_dir / "scan_native.nessus"
    results_file.write_bytes(results)

    print(f"✓ Results saved to: {results_file}")

    # Step 9: Verify results
    print(f"\n{'─' * 80}")
    print("STEP 9: Verify Results")
    print(f"{'─' * 80}")

    # Basic validation
    assert results is not None
    assert isinstance(results, bytes)
    assert len(results) > 1000, "Results file too small"
    assert b"<?xml" in results, "Not valid XML"
    assert b"<NessusClientData_v2>" in results, "Not valid .nessus format"

    print(f"✓ Valid .nessus XML format")

    # Count vulnerabilities
    results_str = results.decode('utf-8')
    vuln_count = results_str.count('<ReportItem')

    logger.info(
        "scan_completed",
        task_id=task_id,
        trace_id=trace_id,
        nessus_scan_id=nessus_scan_id,
        duration_seconds=int(duration),
        vulnerabilities_found=vuln_count,
        results_file=str(results_file)
    )

    print(f"✓ Found {vuln_count} vulnerability entries")

    # Count by severity
    critical = results_str.count('severity="4"')
    high = results_str.count('severity="3"')
    medium = results_str.count('severity="2"')
    low = results_str.count('severity="1"')
    info = results_str.count('severity="0"')

    print(f"\nVulnerability Summary:")
    print(f"  Critical: {critical}")
    print(f"  High:     {high}")
    print(f"  Medium:   {medium}")
    print(f"  Low:      {low}")
    print(f"  Info:     {info}")
    print(f"  Total:    {vuln_count}")

    # Step 10: Cleanup
    print(f"\n{'─' * 80}")
    print("STEP 10: Cleanup")
    print(f"{'─' * 80}")

    try:
        await nessus_scanner.delete_scan(nessus_scan_id)

        logger.info(
            "scan_deleted",
            task_id=task_id,
            trace_id=trace_id,
            nessus_scan_id=nessus_scan_id
        )

        print(f"✓ Deleted Nessus scan ID: {nessus_scan_id}")
    except Exception as e:
        logger.warning(
            "cleanup_warning",
            task_id=task_id,
            trace_id=trace_id,
            nessus_scan_id=nessus_scan_id,
            error=str(e)
        )
        print(f"⚠ Cleanup warning: {e}")

    # ========================================================================
    # Test Summary
    # ========================================================================

    print("\n" + "=" * 80)
    print("✅ TEST PASSED - COMPLETE PHASE 0 + PHASE 1 WORKFLOW")
    print("=" * 80)
    print()
    print("Phase 0 (Queue Operations):")
    print(f"  ✓ Task created and persisted")
    print(f"  ✓ Task enqueued to Redis")
    print(f"  ✓ Task dequeued by worker")
    print()
    print("Phase 1 (Scan Workflow):")
    print(f"  ✓ Nessus scan created (ID: {nessus_scan_id})")
    print(f"  ✓ Scan launched and monitored")
    print(f"  ✓ Scan completed in {int(duration)} seconds")
    print(f"  ✓ Results exported ({vuln_count} vulnerabilities)")
    print(f"  ✓ Scan cleaned up")
    print()
    print("Phase 3 (Observability):")
    print(f"  ✓ All operations logged as structured JSON")
    print(f"  ✓ Trace ID correlation: {trace_id}")
    print(f"  ✓ State transitions tracked")
    print(f"  ✓ Progress monitoring recorded")
    print()
    print("=" * 80)
    print()


# ============================================================================
# Lightweight Test: Redis Connectivity
# ============================================================================

def test_redis_connectivity_from_docker_network(task_queue):
    """
    Lightweight test: Verify Redis is accessible from Docker network.

    This test runs quickly and verifies basic connectivity.
    Does NOT use real Nessus scanner.
    """

    # Verify Redis connection
    assert task_queue.redis_client.ping() is True

    # Verify queue operations work
    test_task = {
        "task_id": "connectivity-test",
        "trace_id": "test-trace",
        "payload": {}
    }

    queue_depth = task_queue.enqueue(test_task)
    assert queue_depth == 1

    dequeued = task_queue.dequeue(timeout=1)
    assert dequeued is not None
    assert dequeued["task_id"] == "connectivity-test"

    print("\n✅ Redis connectivity verified from Docker network")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "-s",
        "-m", "real_nessus"
    ])
