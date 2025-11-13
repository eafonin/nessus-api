#!/usr/bin/env python3
"""
Demonstration of Phase 3 Structured Logging (No External Dependencies)

Shows structured JSON logging output for Phase 0/1 operations.
"""
import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

print("=" * 80)
print("STRUCTURED LOGGING DEMONSTRATION - PHASE 0 & PHASE 1")
print("=" * 80)
print("\nThis demonstrates how ALL operations are logged as structured JSON.\n")
print("Notice how each JSON log includes:")
print("  - 'timestamp': ISO 8601 format with microsecond precision")
print("  - 'event': Descriptive event name")
print("  - 'trace_id': Unique ID to correlate related operations")
print("  - 'level': Log severity (info, warning, error)")
print("  - Additional context fields specific to each operation")
print("\n" + "=" * 80)
print()

# Initialize structured logging
from core.logging_config import configure_logging, get_logger

configure_logging(log_level="INFO")
logger = get_logger("nessus_mcp_demo")

print("ACTION: System initialization with configuration")
print("-" * 80)

logger.info(
    "system_initialized",
    component="mcp_server",
    redis_url="redis://redis:6379",
    data_dir="/app/data/tasks",
    scanner_config="/app/config/scanners.yaml"
)

print()
print("\n" + "=" * 80)
print("PHASE 0: Queue-Based Scan Execution")
print("=" * 80)
print()

# Generate IDs
trace_id = str(uuid.uuid4())
task_id = f"nessus-local-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

print("ACTION 1: User invokes run_untrusted_scan MCP tool")
print("-" * 80)

logger.info(
    "tool_invocation",
    tool="run_untrusted_scan",
    trace_id=trace_id,
    targets="192.168.1.0/24",
    name="Production Network Scan",
    idempotency_key=None
)

print()
print("ACTION 2: Create task in task manager")
print("-" * 80)

logger.info(
    "task_created",
    task_id=task_id,
    trace_id=trace_id,
    scan_type="untrusted",
    scanner_type="nessus",
    scanner_instance="local",
    status="queued"
)

print()
print("ACTION 3: Enqueue task to Redis queue")
print("-" * 80)

logger.info(
    "scan_enqueued",
    task_id=task_id,
    trace_id=trace_id,
    queue_position=3,
    message="Scan enqueued successfully"
)

print()
print("\n" + "=" * 80)
print("PHASE 1: Scan Workflow with State Transitions")
print("=" * 80)
print()

nessus_scan_id = 42

print("ACTION 4: Worker dequeues task and starts scan")
print("-" * 80)

logger.info(
    "task_dequeued",
    task_id=task_id,
    trace_id=trace_id,
    worker_id="worker-01"
)

logger.info(
    "scan_state_transition",
    task_id=task_id,
    trace_id=trace_id,
    from_state="queued",
    to_state="running",
    nessus_scan_id=nessus_scan_id
)

print()
print("ACTION 5: Scan makes progress (multiple updates)")
print("-" * 80)

for progress_pct in [25, 50, 75, 100]:
    logger.info(
        "scan_progress",
        task_id=task_id,
        trace_id=trace_id,
        nessus_scan_id=nessus_scan_id,
        progress=progress_pct,
        scanner_status="running"
    )

print()
print("ACTION 6: Scan completes successfully")
print("-" * 80)

logger.info(
    "scan_state_transition",
    task_id=task_id,
    trace_id=trace_id,
    from_state="running",
    to_state="completed",
    nessus_scan_id=nessus_scan_id
)

logger.info(
    "scan_completed",
    task_id=task_id,
    trace_id=trace_id,
    nessus_scan_id=nessus_scan_id,
    duration_seconds=623,
    vulnerabilities_found=47,
    hosts_scanned=12
)

print()
print("\n" + "=" * 80)
print("ERROR SCENARIOS: Structured Error Logging")
print("=" * 80)
print()

error_task_id = f"nessus-local-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-err"
error_trace_id = str(uuid.uuid4())

print("SCENARIO 1: Scan timeout")
print("-" * 80)

logger.warning(
    "scan_timeout_approaching",
    task_id=error_task_id,
    trace_id=error_trace_id,
    nessus_scan_id=43,
    elapsed_seconds=3500,
    timeout_threshold=3600
)

logger.error(
    "scan_failed",
    task_id=error_task_id,
    trace_id=error_trace_id,
    nessus_scan_id=43,
    error_type="timeout",
    error_message="Scan exceeded maximum timeout of 3600 seconds",
    final_status="timeout"
)

print()
print("SCENARIO 2: Scanner connectivity failure")
print("-" * 80)

logger.error(
    "scanner_connection_failed",
    scanner_type="nessus",
    scanner_instance="local",
    scanner_url="https://172.32.0.209:8834",
    error="Connection refused",
    retry_attempt=3,
    max_retries=3
)

print()
print("SCENARIO 3: Invalid credentials")
print("-" * 80)

logger.error(
    "authentication_failed",
    scanner_type="nessus",
    scanner_instance="local",
    error_code=401,
    error_message="Invalid API credentials"
)

print()
print("\n" + "=" * 80)
print("OPERATIONAL METRICS: Health Checks and Queue Status")
print("=" * 80)
print()

print("ACTION 7: Health check endpoint called")
print("-" * 80)

logger.info(
    "health_check_performed",
    redis_healthy=True,
    filesystem_healthy=True,
    overall_status="healthy",
    response_code=200
)

print()
print("ACTION 8: Metrics endpoint called")
print("-" * 80)

logger.info(
    "metrics_scraped",
    scrape_duration_ms=15,
    metrics_count=8,
    active_scans=4,
    queue_depth=7,
    dlq_size=0
)

print()
print("\n" + "=" * 80)
print("DEMONSTRATION COMPLETE")
print("=" * 80)
print()
print("📊 KEY OBSERVATIONS:")
print()
print("1. STRUCTURED FORMAT")
print("   - All logs are valid JSON (one per line)")
print("   - Easy to parse with log aggregation tools (ELK, Splunk, CloudWatch)")
print()
print("2. TRACE CORRELATION")
print("   - Same trace_id appears across all related operations")
print("   - Can track a single scan from request → queue → execution → completion")
print()
print("3. RICH CONTEXT")
print("   - Every log includes relevant fields (task_id, nessus_scan_id, etc.)")
print("   - No need to parse unstructured log messages")
print()
print("4. SEARCHABLE")
print("   - Query by trace_id: Find all logs for a specific scan")
print("   - Query by event: Find all 'scan_failed' events")
print("   - Query by level: Find all errors")
print()
print("5. TIMESTAMPS")
print("   - ISO 8601 format with microsecond precision")
print("   - Includes timezone information")
print()
print("✅ This logging integrates with Phase 0 (queue) and Phase 1 (workflow)")
print("✅ Production-ready for monitoring and debugging")
print()
