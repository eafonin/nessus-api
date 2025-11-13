#!/usr/bin/env python3
"""
Demonstration of Phase 3 Structured Logging with Phase 0/1 Operations

This script demonstrates how structured logging works throughout the system:
- Phase 0: Task queue operations
- Phase 1: Scan workflow operations
"""
import sys
import os
import uuid
from datetime import datetime

# Add mcp-server to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 80)
print("STRUCTURED LOGGING DEMONSTRATION - PHASE 0 & PHASE 1")
print("=" * 80)
print()

# Initialize structured logging
from core.logging_config import configure_logging, get_logger
from core.metrics import record_tool_call, record_scan_submission
from core.task_manager import TaskManager, generate_task_id
from core.queue import TaskQueue
from core.types import Task, ScanState

# Configure logging to INFO level
configure_logging(log_level="INFO")
logger = get_logger(__name__)

print("✅ Structured logging initialized")
print("=" * 80)
print()

# Initialize components
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DATA_DIR = "/tmp/nessus-demo-tasks"
os.makedirs(DATA_DIR, exist_ok=True)

task_manager = TaskManager(data_dir=DATA_DIR)
task_queue = TaskQueue(redis_url=REDIS_URL)

logger.info(
    "system_initialized",
    component="demo",
    redis_url=REDIS_URL,
    data_dir=DATA_DIR
)

print("\n" + "=" * 80)
print("DEMONSTRATION 1: PHASE 0 - Queue Operations")
print("=" * 80)
print()

# PHASE 0 Demo: Queue operations
print("ACTION: Enqueuing scan task to Redis queue...")
print()

trace_id = str(uuid.uuid4())
task_id = generate_task_id("nessus", "local")

logger.info(
    "tool_invocation",
    tool="run_untrusted_scan",
    trace_id=trace_id,
    task_id=task_id,
    targets="192.168.1.0/24",
    scan_name="Demo Network Scan"
)

# Create task
task = Task(
    task_id=task_id,
    trace_id=trace_id,
    scan_type="untrusted",
    scanner_type="nessus",
    scanner_instance_id="local",
    status=ScanState.QUEUED.value,
    payload={
        "targets": "192.168.1.0/24",
        "name": "Demo Network Scan",
        "description": "Demonstration of structured logging",
        "schema_profile": "brief",
    },
    created_at=datetime.utcnow().isoformat(),
)

# Store task
task_manager.create_task(task)

logger.info(
    "task_created",
    task_id=task_id,
    trace_id=trace_id,
    status="queued",
    scan_type="untrusted"
)

# Enqueue
task_data = {
    "task_id": task_id,
    "trace_id": trace_id,
    "scan_type": "untrusted",
    "scanner_type": "nessus",
    "scanner_instance_id": "local",
    "payload": task.payload,
}

try:
    queue_depth = task_queue.enqueue(task_data)

    logger.info(
        "scan_enqueued",
        task_id=task_id,
        trace_id=trace_id,
        queue_position=queue_depth,
        queue_name="main"
    )

    # Record metrics
    record_tool_call("run_untrusted_scan", "success")
    record_scan_submission("untrusted", "queued")

    print(f"✅ Task enqueued successfully (queue position: {queue_depth})")

except Exception as e:
    logger.error(
        "enqueue_failed",
        task_id=task_id,
        trace_id=trace_id,
        error=str(e),
        error_type=type(e).__name__
    )
    print(f"❌ Enqueue failed: {e}")

print()
print("=" * 80)
print("DEMONSTRATION 2: PHASE 1 - Scan Workflow State Transitions")
print("=" * 80)
print()

# PHASE 1 Demo: Simulate scan workflow
print("ACTION: Simulating scan workflow with state transitions...")
print()

# State: RUNNING
logger.info(
    "scan_state_transition",
    task_id=task_id,
    trace_id=trace_id,
    from_state="queued",
    to_state="running",
    nessus_scan_id=12345
)

print("  State: QUEUED → RUNNING")

# Simulate progress updates
for progress in [25, 50, 75]:
    logger.info(
        "scan_progress",
        task_id=task_id,
        trace_id=trace_id,
        nessus_scan_id=12345,
        progress=progress,
        status="running"
    )
    print(f"  Progress: {progress}%")

# State: COMPLETED
logger.info(
    "scan_state_transition",
    task_id=task_id,
    trace_id=trace_id,
    from_state="running",
    to_state="completed",
    nessus_scan_id=12345,
    duration_seconds=450
)

print("  State: RUNNING → COMPLETED")

logger.info(
    "scan_completed",
    task_id=task_id,
    trace_id=trace_id,
    nessus_scan_id=12345,
    status="completed",
    duration_seconds=450,
    results_file="/app/data/tasks/{}/scan_native.nessus".format(task_id)
)

print()
print("✅ Scan workflow completed")

print()
print("=" * 80)
print("DEMONSTRATION 3: Error Handling with Structured Logs")
print("=" * 80)
print()

print("ACTION: Simulating error scenarios...")
print()

# Error scenario 1: Timeout
error_task_id = generate_task_id("nessus", "local")
error_trace_id = str(uuid.uuid4())

logger.warning(
    "scan_timeout_warning",
    task_id=error_task_id,
    trace_id=error_trace_id,
    nessus_scan_id=12346,
    timeout_threshold=3600,
    elapsed_seconds=3650
)

logger.error(
    "scan_failed",
    task_id=error_task_id,
    trace_id=error_trace_id,
    nessus_scan_id=12346,
    error="Scan exceeded maximum timeout",
    error_code="TIMEOUT",
    final_status="timeout"
)

print("  ❌ Error logged: Scan timeout")

# Error scenario 2: Scanner connectivity
logger.error(
    "scanner_connection_failed",
    scanner_type="nessus",
    scanner_instance="local",
    scanner_url="https://172.32.0.209:8834",
    error="Connection refused",
    retry_count=3
)

print("  ❌ Error logged: Scanner connectivity issue")

print()
print("=" * 80)
print("DEMONSTRATION 4: Metrics Recording")
print("=" * 80)
print()

print("Recording metrics for monitoring...")
print()

from core.metrics import (
    update_active_scans_count,
    update_queue_metrics,
    metrics_response
)

# Update metrics
update_active_scans_count(3)
update_queue_metrics(main_depth=5, dlq_depth=0)

logger.info(
    "metrics_updated",
    active_scans=3,
    queue_depth=5,
    dlq_size=0
)

print("✅ Metrics updated:")
print("  - Active scans: 3")
print("  - Queue depth: 5")
print("  - DLQ size: 0")

print()
print("=" * 80)
print("DEMONSTRATION COMPLETE")
print("=" * 80)
print()
print("📊 All logs above are in JSON format with:")
print("  ✅ ISO 8601 timestamps")
print("  ✅ Trace IDs for request correlation")
print("  ✅ Structured fields (task_id, status, etc.)")
print("  ✅ Log levels (info, warning, error)")
print("  ✅ Logger names for component tracking")
print()
print("📈 Prometheus metrics have been recorded and can be scraped via /metrics endpoint")
print()
