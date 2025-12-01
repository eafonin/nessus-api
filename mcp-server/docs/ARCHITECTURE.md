# Nessus MCP Server - Architecture

> **Last Updated**: 2025-12-01
> **Version**: 3.0 (Production Implementation)

---

## System Overview

The Nessus MCP Server provides an MCP (Model Context Protocol) interface for vulnerability scanning using Nessus scanners. It enables LLM agents to submit scans, monitor progress, and retrieve structured results.

```
                          MCP Clients
                               │
                               │ HTTP (SSE transport)
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                         Docker Host                                 │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐  │
│  │   MCP API       │   │     Redis       │   │  Scanner Worker │  │
│  │   (FastMCP)     │──▶│   (Queue +      │◀──│   (Async)       │  │
│  │   Port 8836     │   │    State)       │   │                 │  │
│  └────────┬────────┘   └─────────────────┘   └────────┬────────┘  │
│           │                                            │           │
│           ▼                                            ▼           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Shared Volume: /app/data/tasks                  │  │
│  │    {task_id}/task.json, {task_id}/scan_native.nessus        │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                        │           │
│                                                        ▼           │
│                                           ┌─────────────────────┐ │
│                                           │  Nessus Scanners    │ │
│                                           │  (Pool: nessus)     │ │
│                                           │  Scanner 1, 2, ...  │ │
│                                           └─────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

---

## Module Structure

```
mcp-server/
├── tools/
│   ├── mcp_server.py      # FastMCP server, 9 MCP tools
│   ├── run_server.py      # Uvicorn launcher
│   └── admin_cli.py       # DLQ management CLI
├── core/
│   ├── task_manager.py    # Task CRUD, state transitions
│   ├── types.py           # Task dataclass, ScanState enum
│   ├── queue.py           # Redis queue operations
│   ├── idempotency.py     # Duplicate scan prevention
│   ├── health.py          # Health check utilities
│   ├── housekeeping.py    # TTL cleanup, stale scan cleanup
│   └── metrics.py         # Prometheus metrics
├── scanners/
│   ├── registry.py        # Scanner pool management
│   ├── nessus_scanner.py  # Native async Nessus API client
│   ├── nessus_validator.py # Result validation, auth detection
│   └── base.py            # Scanner interface, ScanRequest
├── schema/
│   ├── converter.py       # Nessus XML to JSON-NL
│   ├── parser.py          # XML parsing
│   ├── profiles.py        # Schema profiles (minimal/summary/brief/full)
│   └── filters.py         # Result filtering
├── worker/
│   └── scanner_worker.py  # Async task processor
└── config/
    └── scanners.yaml      # Scanner pool configuration
```

---

## Component Responsibilities

### MCP API Server (`tools/mcp_server.py`)

- Exposes 9 MCP tools via FastMCP
- Uses SSE (Server-Sent Events) transport
- Creates tasks and enqueues to Redis
- Handles idempotency key validation
- Serves `/health` and `/metrics` endpoints

### Task Manager (`core/task_manager.py`)

- File-based task storage (`/app/data/tasks/{task_id}/task.json`)
- State machine enforcement via `update_status()`
- Validation result tracking (Phase 4)

### Task Queue (`core/queue.py`)

- Pool-based Redis queues: `{pool}:queue` (LIST)
- Dead Letter Queue: `{pool}:queue:dead` (SORTED SET)
- FIFO semantics (LPUSH/BRPOP)
- Blocking dequeue with timeout

### Scanner Registry (`scanners/registry.py`)

- Pool-based scanner grouping
- Load-based scanner selection (least utilized)
- Active scan tracking (acquire/release)
- SIGHUP hot-reload support

### Scanner Worker (`worker/scanner_worker.py`)

- Consumes tasks from pool queues
- Per-pool backpressure (capacity from scanners.yaml)
- Manages scan lifecycle: create → launch → poll → export
- Background housekeeping tasks

### Schema Converter (`schema/converter.py`)

- Transforms Nessus XML to JSON-NL
- Applies schema profiles and filters
- Paginated output

---

## Data Flow

### Scan Submission

```
1. Client calls run_untrusted_scan(targets, name, ...)
2. MCP API generates task_id, trace_id
3. Check idempotency key (if provided)
4. Select scanner: least loaded in pool
5. Create Task object, write task.json
6. Enqueue task data to Redis: {pool}:queue
7. Return task_id, queue_position to client
```

### Scan Processing (Worker)

```
1. BRPOP task from pool queue(s) with capacity
2. Acquire scanner (increment active_scans)
3. Update task status → RUNNING
4. Create scan in Nessus API
5. Launch scan
6. Poll status every 30s (24h timeout)
7. Export results (.nessus XML)
8. Validate results (auth detection, stats)
9. Update task status → COMPLETED/FAILED
10. Release scanner (decrement active_scans)
```

### Result Retrieval

```
1. Client calls get_scan_results(task_id, page, filters)
2. Load task.json, verify status=completed
3. Read scan_native.nessus from task directory
4. Parse XML, apply schema profile
5. Apply filters (severity, CVE, etc.)
6. Paginate results
7. Return JSON-NL string
```

---

## State Machine

```
          ┌──────────────────────────────────────┐
          │                                      │
          ▼                                      │
   ┌──────────┐      ┌─────────┐      ┌──────────────┐
   │  QUEUED  │─────▶│ RUNNING │─────▶│  COMPLETED   │
   └──────────┘      └─────────┘      └──────────────┘
        │                 │
        │                 │ (error)
        │                 ▼
        │           ┌──────────┐
        └──────────▶│  FAILED  │
        │           └──────────┘
        │                 │
        │                 │ (timeout)
        │                 ▼
        │           ┌──────────┐
        └──────────▶│ TIMEOUT  │
                    └──────────┘
```

**State Definitions** (`core/types.py`):

| State | Description |
|-------|-------------|
| `queued` | Task created, waiting in Redis queue |
| `running` | Worker processing, scan active on Nessus |
| `completed` | Scan finished, results available |
| `failed` | Error during processing (moved to DLQ) |
| `timeout` | Exceeded 24h limit, scan stopped |

**Valid Transitions**:
- QUEUED → RUNNING, FAILED
- RUNNING → RUNNING (metadata update), COMPLETED, FAILED, TIMEOUT
- COMPLETED, FAILED, TIMEOUT → (terminal)

---

## Key Abstractions

### Task (`core/types.py:31-50`)

```python
@dataclass
class Task:
    task_id: str
    trace_id: str
    scan_type: str           # untrusted|authenticated|authenticated_privileged
    scanner_type: str        # nessus
    scanner_instance_id: str # scanner1, scanner2, etc.
    status: str              # queued|running|completed|failed|timeout
    payload: Dict[str, Any]  # targets, name, credentials, etc.
    created_at: str
    scanner_pool: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    nessus_scan_id: Optional[int]
    error_message: Optional[str]
    validation_stats: Optional[Dict]
    validation_warnings: Optional[List]
    authentication_status: Optional[str]  # success|failed|partial|not_applicable
```

### TaskQueue (`core/queue.py`)

Pool-aware FIFO queue using Redis:
- Main queue: `{pool}:queue` (LIST, LPUSH/BRPOP)
- Dead Letter Queue: `{pool}:queue:dead` (SORTED SET, timestamp score)

Key methods:
- `enqueue(task, pool)` → queue_depth
- `dequeue(pool, timeout)` → task or None
- `dequeue_any(pools, timeout)` → task from any pool
- `move_to_dlq(task, error, pool)`

### ScannerRegistry (`scanners/registry.py`)

Pool-based scanner management:
- Scanner key format: `{pool}:{instance_id}` (e.g., `nessus:scanner1`)
- Each pool has its own Redis queue
- Load balancing within pools

Key methods:
- `get_available_scanner(pool)` → (scanner, instance_key)
- `acquire_scanner(pool, instance_id)` → increment active_scans
- `release_scanner(instance_key)` → decrement active_scans
- `get_pool_status(pool)` → capacity, utilization, per-scanner breakdown

Selection algorithm:
1. Filter scanners with available capacity
2. Sort by utilization (active_scans / max_concurrent_scans)
3. Tie-breaker: least recently used

---

## Inter-Component Communication

### API → Queue

```python
# tools/mcp_server.py:182-183
task_data = {"task_id": ..., "trace_id": ..., "payload": ...}
queue_depth = task_queue.enqueue(task_data, pool=target_pool)
```

### Worker → Queue

```python
# worker/scanner_worker.py:217-221
task_data = await asyncio.to_thread(
    self.queue.dequeue_any,
    pools=pools_with_capacity,
    timeout=5
)
```

### Worker → Scanner

```python
# worker/scanner_worker.py:276-279
scanner, instance_key = await self.scanner_registry.acquire_scanner(
    pool=scanner_pool,
    instance_id=scanner_instance_id
)
# ... use scanner ...
await self.scanner_registry.release_scanner(instance_key)
```

### Worker → TaskManager

```python
# worker/scanner_worker.py:283-286
self.task_manager.update_status(task_id, ScanState.RUNNING)
# ... process scan ...
self.task_manager.mark_completed_with_validation(task_id, validation_stats, ...)
```

---

## Cross-References

- **[FEATURES.md](FEATURES.md)**: MCP tool reference, schema profiles, filtering
- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Docker configuration, environment variables
- **[REQUIREMENTS.md](REQUIREMENTS.md)**: Functional and non-functional requirements

---

*Architecture document generated from source code analysis*
