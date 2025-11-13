# Structured Logging Examples - Phase 0 & Phase 1

This document shows actual JSON log output from Phase 3 structured logging implementation.

## Overview

All operations in the MCP server generate structured JSON logs with:
- **ISO 8601 timestamps** with microsecond precision
- **trace_id** for correlating related operations
- **event** names describing what happened
- **Rich context** fields specific to each operation
- **Log levels** (info, warning, error)

---

## PHASE 0: Queue Operations

### 1. System Initialization
```json
{
  "component": "mcp_server",
  "redis_url": "redis://redis:6379",
  "data_dir": "/app/data/tasks",
  "scanner_config": "/app/config/scanners.yaml",
  "event": "system_initialized",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.361784Z"
}
```

### 2. Tool Invocation (run_untrusted_scan)
```json
{
  "tool": "run_untrusted_scan",
  "trace_id": "76ea3daf-da0a-4ffb-9f89-862b4f34a22c",
  "targets": "192.168.1.0/24",
  "name": "Production Network Scan",
  "idempotency_key": null,
  "event": "tool_invocation",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.362187Z"
}
```

### 3. Task Created
```json
{
  "task_id": "nessus-local-20251108-093855",
  "trace_id": "76ea3daf-da0a-4ffb-9f89-862b4f34a22c",
  "scan_type": "untrusted",
  "scanner_type": "nessus",
  "scanner_instance": "local",
  "status": "queued",
  "event": "task_created",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.362301Z"
}
```

### 4. Scan Enqueued to Redis
```json
{
  "task_id": "nessus-local-20251108-093855",
  "trace_id": "76ea3daf-da0a-4ffb-9f89-862b4f34a22c",
  "queue_position": 3,
  "message": "Scan enqueued successfully",
  "event": "scan_enqueued",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.362365Z"
}
```

---

## PHASE 1: Scan Workflow

### 5. Task Dequeued by Worker
```json
{
  "task_id": "nessus-local-20251108-093855",
  "trace_id": "76ea3daf-da0a-4ffb-9f89-862b4f34a22c",
  "worker_id": "worker-01",
  "event": "task_dequeued",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.362426Z"
}
```

### 6. State Transition: QUEUED → RUNNING
```json
{
  "task_id": "nessus-local-20251108-093855",
  "trace_id": "76ea3daf-da0a-4ffb-9f89-862b4f34a22c",
  "from_state": "queued",
  "to_state": "running",
  "nessus_scan_id": 42,
  "event": "scan_state_transition",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.362480Z"
}
```

### 7. Scan Progress Updates
```json
{
  "task_id": "nessus-local-20251108-093855",
  "trace_id": "76ea3daf-da0a-4ffb-9f89-862b4f34a22c",
  "nessus_scan_id": 42,
  "progress": 25,
  "scanner_status": "running",
  "event": "scan_progress",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.362533Z"
}
```

```json
{
  "task_id": "nessus-local-20251108-093855",
  "trace_id": "76ea3daf-da0a-4ffb-9f89-862b4f34a22c",
  "nessus_scan_id": 42,
  "progress": 50,
  "scanner_status": "running",
  "event": "scan_progress",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.362582Z"
}
```

### 8. State Transition: RUNNING → COMPLETED
```json
{
  "task_id": "nessus-local-20251108-093855",
  "trace_id": "76ea3daf-da0a-4ffb-9f89-862b4f34a22c",
  "from_state": "running",
  "to_state": "completed",
  "nessus_scan_id": 42,
  "event": "scan_state_transition",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.362721Z"
}
```

### 9. Scan Completed
```json
{
  "task_id": "nessus-local-20251108-093855",
  "trace_id": "76ea3daf-da0a-4ffb-9f89-862b4f34a22c",
  "nessus_scan_id": 42,
  "duration_seconds": 623,
  "vulnerabilities_found": 47,
  "hosts_scanned": 12,
  "event": "scan_completed",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.362774Z"
}
```

---

## ERROR SCENARIOS

### 10. Timeout Warning
```json
{
  "task_id": "nessus-local-20251108-093855-err",
  "trace_id": "e53a8398-7b2d-45a5-8498-1207d7dd4f25",
  "nessus_scan_id": 43,
  "elapsed_seconds": 3500,
  "timeout_threshold": 3600,
  "event": "scan_timeout_approaching",
  "logger": "nessus_mcp_demo",
  "level": "warning",
  "timestamp": "2025-11-08T09:38:55.362885Z"
}
```

### 11. Scan Failure
```json
{
  "task_id": "nessus-local-20251108-093855-err",
  "trace_id": "e53a8398-7b2d-45a5-8498-1207d7dd4f25",
  "nessus_scan_id": 43,
  "error_type": "timeout",
  "error_message": "Scan exceeded maximum timeout of 3600 seconds",
  "final_status": "timeout",
  "event": "scan_failed",
  "logger": "nessus_mcp_demo",
  "level": "error",
  "timestamp": "2025-11-08T09:38:55.362957Z"
}
```

### 12. Scanner Connection Failed
```json
{
  "scanner_type": "nessus",
  "scanner_instance": "local",
  "scanner_url": "https://172.32.0.209:8834",
  "error": "Connection refused",
  "retry_attempt": 3,
  "max_retries": 3,
  "event": "scanner_connection_failed",
  "logger": "nessus_mcp_demo",
  "level": "error",
  "timestamp": "2025-11-08T09:38:55.363007Z"
}
```

### 13. Authentication Failed
```json
{
  "scanner_type": "nessus",
  "scanner_instance": "local",
  "error_code": 401,
  "error_message": "Invalid API credentials",
  "event": "authentication_failed",
  "logger": "nessus_mcp_demo",
  "level": "error",
  "timestamp": "2025-11-08T09:38:55.363054Z"
}
```

---

## OPERATIONAL METRICS

### 14. Health Check
```json
{
  "redis_healthy": true,
  "filesystem_healthy": true,
  "overall_status": "healthy",
  "response_code": 200,
  "event": "health_check_performed",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.363100Z"
}
```

### 15. Metrics Scraped
```json
{
  "scrape_duration_ms": 15,
  "metrics_count": 8,
  "active_scans": 4,
  "queue_depth": 7,
  "dlq_size": 0,
  "event": "metrics_scraped",
  "logger": "nessus_mcp_demo",
  "level": "info",
  "timestamp": "2025-11-08T09:38:55.363143Z"
}
```

---

## Key Benefits

### 1. Trace Correlation
All logs for a single scan share the same `trace_id`:
- `76ea3daf-da0a-4ffb-9f89-862b4f34a22c` appears in logs #2-9
- Can query logs by trace_id to see complete scan lifecycle

### 2. Structured Queries
Easy to query with log aggregation tools:
```
# Find all scan failures
level: "error" AND event: "scan_failed"

# Find all operations for a specific scan
trace_id: "76ea3daf-da0a-4ffb-9f89-862b4f34a22c"

# Find all scans that timed out
error_type: "timeout"

# Find all scanner connection issues
event: "scanner_connection_failed"
```

### 3. Rich Context
No need to parse log messages - all data is structured:
- `nessus_scan_id`, `task_id`, `worker_id` are separate fields
- `progress`, `duration_seconds`, `vulnerabilities_found` are numeric
- Boolean values like `redis_healthy` can be queried directly

### 4. Production-Ready
- ISO 8601 timestamps for consistent time parsing
- Microsecond precision for accurate timing analysis
- Logger names identify which component generated the log
- Level field enables filtering by severity

---

## Running the Demo

```bash
cd /home/nessus/projects/nessus-api/mcp-server
source ../venv/bin/activate
python demo_logging_only.py
```

This demonstrates:
- ✅ Phase 0: Queue operations (enqueue, dequeue)
- ✅ Phase 1: Scan workflow (state transitions, progress, completion)
- ✅ Error handling with structured context
- ✅ Operational metrics logging
