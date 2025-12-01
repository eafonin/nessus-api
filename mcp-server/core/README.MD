<!-- README Navigation -->
<!-- L3: mcp-server/core/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Task management, queuing, and observability -->

# Core Infrastructure

> Foundation modules for task management, queuing, and observability

**↑ Parent**: [MCP Server](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

## Module Overview

| Module | Lines | Purpose |
|--------|-------|---------|
| `types.py` | 51 | Type definitions (Task, ScanState, transitions) |
| `task_manager.py` | 155 | Task lifecycle with file-based storage |
| `queue.py` | 430 | Redis-based per-pool task queue |
| `circuit_breaker.py` | 270 | Scanner failure handling pattern |
| `health.py` | 80 | Dependency health checks |
| `housekeeping.py` | 650 | Cleanup expired tasks/orphaned scans |
| `idempotency.py` | 100 | Duplicate request prevention |
| `ip_utils.py` | 110 | CIDR parsing and IP validation |
| `logging_config.py` | 35 | Structured JSON logging |
| `metrics.py` | 240 | Prometheus metrics collection |
| `middleware.py` | 20 | HTTP request tracing |

## Key Workflows

### Task Lifecycle

```
MCP Request → TaskQueue.enqueue() → Worker.dequeue()
                                         ↓
                                 TaskManager.create_task()
                                         ↓
                              Status: queued → running → completed
                                         ↓
                                 Results stored to filesystem
```

### State Machine

Defined in `types.py`:

```
QUEUED ──→ RUNNING ──→ COMPLETED
  │           │
  │           ├──→ FAILED
  │           │
  │           └──→ TIMEOUT
  │
  └──→ FAILED (before start)
```

Terminal states: `COMPLETED`, `FAILED`, `TIMEOUT`

## Module Details

### types.py

Core type definitions:

- `ScanState` enum: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `TIMEOUT`
- `VALID_TRANSITIONS` dict: Enforces valid state changes
- `Task` dataclass: Task metadata (id, status, payload, timestamps, validation)
- `StateTransitionError`: Raised on invalid transitions

### task_manager.py

File-based task persistence:

- `generate_task_id()` - Creates unique ID: `{type}_{instance}_{timestamp}_{uuid}`
- `TaskManager.create_task()` - Write task to `data/tasks/{id}/task.json`
- `TaskManager.get_task()` - Read task metadata
- `TaskManager.update_status()` - State transition with validation
- `mark_completed_with_validation()` - Complete with auth status
- `mark_failed_with_validation()` - Fail with partial results

### queue.py

Redis-based per-pool FIFO queue:

```
Pool Architecture:
- {pool}:queue       - Main task queue (LPUSH/BRPOP)
- {pool}:queue:dead  - Dead Letter Queue (sorted set)

Example: nessus:queue, nessus:queue:dead
```

Key methods:
- `enqueue(task, pool)` - Add task to pool queue
- `dequeue(pool, timeout)` - Blocking pop from queue
- `move_to_dlq(task, error, pool)` - Move failed task to DLQ
- `get_queue_depth(pool)` - Current queue size
- `list_pools()` - All registered pools

### circuit_breaker.py

Scanner failure protection:

```
States:
  CLOSED ──(N failures)──→ OPEN ──(timeout)──→ HALF_OPEN
     ↑                                             │
     └────────────(success)────────────────────────┘
                      │
     OPEN ←──(failure)─┘
```

Configuration:
- `failure_threshold` - Failures before opening (default: 5)
- `recovery_timeout` - Seconds before half-open (default: 60)
- `success_threshold` - Successes to close (default: 2)

### health.py

Dependency health checks:

- `check_redis(url)` - Ping Redis server
- `check_filesystem(path)` - Test write access
- `check_all_dependencies()` - Combined health status

Returns: `{"status": "healthy"|"unhealthy", "redis_healthy": bool, ...}`

### housekeeping.py

Cleanup operations:

- Expire tasks older than retention period
- Detect orphaned Nessus scans (no matching task)
- Clean up DLQ entries
- Remove stale files from data directory

Configurable retention periods and batch sizes.

### idempotency.py

Duplicate prevention via Redis:

- Store idempotency keys with TTL
- Return cached response for duplicate requests
- Key format: `idempotency:{key}`

### ip_utils.py

Target validation:

- `parse_cidr(target)` - Parse CIDR notation to IP list
- `expand_targets(targets)` - Expand comma-separated targets
- `validate_target(target)` - Check IP/CIDR validity
- `is_private_ip(ip)` - Check RFC1918 ranges

### logging_config.py

Structured logging setup:

- JSON format for production
- Correlation IDs for request tracing
- Log levels configurable via environment

### metrics.py

Prometheus metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `nessus_scans_total` | Counter | Scans by status |
| `nessus_scan_duration_seconds` | Histogram | Scan duration |
| `nessus_queue_depth` | Gauge | Queue size per pool |
| `nessus_circuit_state` | Gauge | Circuit breaker state |
| `nessus_api_latency_seconds` | Histogram | API call latency |

### middleware.py

HTTP middleware:

- Request tracing with correlation IDs
- Timing instrumentation

## Dependencies

```
core/
├── types.py           # No dependencies
├── task_manager.py    # → types.py
├── queue.py           # → redis
├── circuit_breaker.py # → prometheus_client
├── health.py          # → redis
├── housekeeping.py    # → task_manager, queue, scanners
├── idempotency.py     # → redis
├── ip_utils.py        # → ipaddress (stdlib)
├── logging_config.py  # → structlog
├── metrics.py         # → prometheus_client
└── middleware.py      # → starlette
```

## Usage Examples

### Create and Track Task

```python
from core.types import Task, ScanState
from core.task_manager import TaskManager, generate_task_id

manager = TaskManager(data_dir="/app/data/tasks")
task_id = generate_task_id("nessus", "scanner1")

task = Task(
    task_id=task_id,
    trace_id="abc123",
    scan_type="untrusted",
    scanner_type="nessus",
    scanner_instance_id="scanner1",
    status=ScanState.QUEUED.value,
    payload={"targets": "192.168.1.0/24"},
    created_at=datetime.utcnow().isoformat()
)

manager.create_task(task)
manager.update_status(task_id, ScanState.RUNNING)
manager.update_status(task_id, ScanState.COMPLETED)
```

### Queue Operations

```python
from core.queue import TaskQueue

queue = TaskQueue(redis_url="redis://localhost:6379")
queue.enqueue(task_dict, pool="nessus")

# Worker loop
while True:
    task = queue.dequeue(pool="nessus", timeout=5)
    if task:
        process(task)
```
