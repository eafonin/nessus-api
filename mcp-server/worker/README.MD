<!-- README Navigation -->
<!-- L3: mcp-server/worker/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Background processor for scan task execution -->

# Scanner Worker

> Background processor for scan task execution

**↑ Parent**: [MCP Server](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

## Overview

The worker consumes tasks from Redis queues, executes scans via Nessus, and stores results.

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `scanner_worker.py` | 685 | Main worker loop and task processing |

## Architecture

```
Redis Queue ──BRPOP──→ Worker Loop ──acquire──→ Scanner Pool
                            │                         │
                            ↓                         ↓
                      Task Processing           Nessus Scanner
                            │                         │
                            ↓                         ↓
                      Filesystem              Poll → Export
                      (results)                      │
                            ↑                        │
                            └────────────────────────┘
```

## Task Processing Workflow

```
1. Dequeue task from pool queue (BRPOP)
2. Acquire scanner from pool (increments active_scans)
3. Transition task: QUEUED → RUNNING
4. Create scan in Nessus
5. Launch scan
6. Poll status every 30s until completion
7. Export results to filesystem
8. Validate results (auth detection, host counts)
9. Release scanner (decrements active_scans)
10. Transition task: RUNNING → COMPLETED|FAILED|TIMEOUT
```

## Per-Pool Backpressure

Worker implements backpressure per scanner pool:

- Capacity derived from `scanners.yaml` (sum of `max_concurrent_scans`)
- Only dequeues from pools with available capacity
- Tracks active tasks per pool

```python
# Example: 2 scanners with 5 concurrent each = 10 capacity
pools_with_capacity = self._get_pools_with_capacity()
if not pools_with_capacity:
    await asyncio.sleep(1)  # Wait for capacity
    continue
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `DATA_DIR` | `/app/data/tasks` | Task result storage |
| `SCANNER_CONFIG` | `/app/config/scanners.yaml` | Scanner pool config |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `WORKER_POOLS` | (all) | Comma-separated pool list |

### Housekeeping Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOUSEKEEPING_ENABLED` | `true` | Enable task cleanup |
| `HOUSEKEEPING_INTERVAL_HOURS` | `1` | Cleanup interval |
| `COMPLETED_TTL_DAYS` | `7` | Retain completed tasks |
| `FAILED_TTL_DAYS` | `30` | Retain failed tasks |

### Scan Cleanup Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STALE_SCAN_CLEANUP_ENABLED` | `true` | Detect stuck scans |
| `STALE_SCAN_HOURS` | `24` | Hours before scan is stale |
| `STALE_SCAN_DELETE_FROM_NESSUS` | `true` | Delete stale from Nessus |
| `NESSUS_SCAN_CLEANUP_ENABLED` | `true` | Clean finished Nessus scans |
| `NESSUS_SCAN_RETENTION_HOURS` | `24` | Keep in Nessus after completion |

## Running

### Docker (Production)

```bash
docker compose up worker
```

### Local Development

```bash
cd mcp-server
source venv/bin/activate
python -m worker.scanner_worker
```

### Specific Pools

```bash
# Only consume from nessus pool
WORKER_POOLS=nessus python -m worker.scanner_worker

# Multiple pools
WORKER_POOLS=nessus,nessus_dmz python -m worker.scanner_worker
```

## Signal Handling

Worker supports graceful shutdown:

- `SIGTERM` / `SIGINT` - Stop accepting new tasks
- Wait up to 60s for active tasks to complete
- Close scanner connections
- Cancel housekeeping background tasks

## Background Tasks

Worker runs background tasks concurrently:

1. **Task Housekeeping** - Delete old tasks from filesystem
2. **Stale Scan Cleanup** - Detect and handle stuck scans
3. **Nessus Scan Cleanup** - Delete old scans from Nessus

## Metrics

Worker updates Prometheus metrics every 30s:

| Metric | Description |
|--------|-------------|
| `nessus_pool_queue_depth` | Tasks waiting per pool |
| `nessus_pool_dlq_depth` | Failed tasks per pool |
| `nessus_scanner_active_scans` | Active scans per scanner |
| `nessus_validation_results_total` | Validation outcomes |
| `nessus_auth_failures_total` | Authentication failures |

## Error Handling

Failed tasks are:
1. Logged with trace_id
2. Task state → FAILED with error message
3. Moved to pool-specific Dead Letter Queue (DLQ)
4. Available for inspection via `get_queue_status()`

## Key Methods

### ScannerWorker

| Method | Description |
|--------|-------------|
| `start()` | Begin worker loop |
| `_worker_loop()` | Main polling loop |
| `_process_task()` | Execute single scan |
| `_poll_until_complete()` | Wait for scan completion |
| `_handle_error()` | Move to DLQ on failure |
| `_cleanup()` | Graceful shutdown |

## Dependencies

```
worker/
└── scanner_worker.py
    ├── core/queue.py        # Redis queue
    ├── core/task_manager.py # Task state
    ├── core/types.py        # ScanState enum
    ├── core/metrics.py      # Prometheus
    ├── core/housekeeping.py # Cleanup tasks
    ├── scanners/registry.py # Pool management
    └── scanners/nessus_validator.py # Result validation
```
