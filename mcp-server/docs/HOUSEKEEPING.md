# Housekeeping and Automatic Cleanup

> Automatic cleanup of task directories and Nessus scans to prevent resource exhaustion

## Overview

The MCP server includes three automatic housekeeping jobs that run periodically to clean up resources:

| Job | Purpose | Default Interval |
|-----|---------|------------------|
| **TTL Cleanup** | Delete old task directories | Every 1 hour |
| **Stale Scan Cleanup** | Mark abandoned tasks as timeout | Every 1 hour |
| **Nessus Scan Cleanup** | Delete old scans from Nessus | Every 1 hour |

All jobs are enabled by default and run in the scanner worker process.

## Configuration

### Environment Variables

```bash
# TTL-based task directory cleanup
HOUSEKEEPING_ENABLED=true              # Enable/disable task directory cleanup
HOUSEKEEPING_INTERVAL_HOURS=1          # Hours between cleanup runs
COMPLETED_TTL_DAYS=7                   # Days to keep completed task directories
FAILED_TTL_DAYS=30                     # Days to keep failed/timeout task directories

# Stale scan cleanup (task-centric)
STALE_SCAN_CLEANUP_ENABLED=true        # Enable/disable stale scan detection
STALE_SCAN_HOURS=24                    # Hours before running scan is considered stale
STALE_SCAN_DELETE_FROM_NESSUS=true     # Delete stale scans from Nessus

# Nessus scan cleanup (scanner-centric)
NESSUS_SCAN_CLEANUP_ENABLED=true       # Enable/disable Nessus scan cleanup
NESSUS_SCAN_RETENTION_HOURS=24         # Hours to keep finished scans on Nessus
```

## Housekeeping Jobs

### TTL Cleanup (Task Directories)

Deletes task directories based on task status and age.

**Retention Policy:**
- Completed tasks: 7 days (configurable)
- Failed/Timeout tasks: 30 days (configurable)
- Running/Queued tasks: Never deleted

**What gets deleted:**
- Task directory with all contents
- Results files, logs, metadata

**Log output:**
```
Housekeeping complete: deleted 5 tasks, freed 12.5 MB, 0 errors
```

### Stale Scan Cleanup (Task-Centric)

Detects running/queued tasks that have been active too long and marks them as timeout.

**Detection criteria:**
- Task status is `running` or `queued`
- Task age exceeds `STALE_SCAN_HOURS` (default: 24h)

**Actions taken:**
1. Stop scan on Nessus (if running)
2. Delete scan from Nessus (if configured)
3. Update task status to `timeout`
4. Set error message explaining the timeout

**Log output:**
```
Stale scan detected: task_123 (age=25h, nessus_id=456)
Stopped stale scan 456 on scanner1
Marked stale task task_123 as timeout
```

### Nessus Scan Cleanup (Scanner-Centric)

Directly queries each Nessus scanner and deletes old scans.

**How it works:**
1. Iterates over all configured scanners
2. Calls `GET /scans` API on each scanner
3. Deletes scans based on status and age

**Deletion criteria:**
- Finished scans (completed, canceled, imported) older than `NESSUS_SCAN_RETENTION_HOURS`
- Running scans older than `STALE_SCAN_HOURS` (stops first, then deletes)

**Benefits of scanner-centric approach:**
- No dependency on task records
- Cleans up orphaned scans (scans without task records)
- Works even if scanner config changed since scan was created
- Handles scans created outside the MCP system

**Log output:**
```
[nessus:scanner1] Found 8 scans
[nessus:scanner1] Deleted old scan 42 'MCP Scan 2025-11-24' (age=48.5h)
Nessus cleanup: 2 scanners, deleted 3, stopped 0, 0 errors
```

## Architecture

### Cleanup Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Scanner Worker Process                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  TTL Cleanup     │  │  Stale Scan      │  │  Nessus Scan   │ │
│  │  (Housekeeper)   │  │  Cleanup         │  │  Cleanup       │ │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬────────┘ │
│           │                     │                     │          │
│           ▼                     ▼                     ▼          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ Task Directories │  │ Task JSON Files  │  │ Nessus API     │ │
│  │ /app/data/tasks/ │  │ (status update)  │  │ GET /scans     │ │
│  └──────────────────┘  └──────────────────┘  │ DELETE /scans  │ │
│                                               └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Files

| File | Class/Function | Purpose |
|------|----------------|---------|
| `core/housekeeping.py` | `Housekeeper` | TTL-based task directory cleanup |
| `core/housekeeping.py` | `StaleScanCleaner` | Task-centric stale scan detection |
| `core/housekeeping.py` | `NessusScanCleaner` | Scanner-centric Nessus cleanup |
| `worker/scanner_worker.py` | `main()` | Starts background cleanup tasks |

## Monitoring

### Metrics

The following Prometheus metrics are available:

```
# TTL cleanup
ttl_deletions_total    # Counter: total task directories deleted

# Stale scan cleanup
# (tracked in logs, no dedicated metric)
```

### Log Messages

Key log messages to monitor:

```bash
# Successful cleanup
grep "Housekeeping complete" /var/log/worker.log
grep "Nessus cleanup:" /var/log/worker.log

# Errors
grep "Housekeeping error" /var/log/worker.log
grep "Nessus scan cleanup error" /var/log/worker.log

# Stale scan detection
grep "Stale scan detected" /var/log/worker.log
```

## Troubleshooting

### Scans Not Being Deleted

**Symptom:** Old scans remain on Nessus despite cleanup being enabled.

**Check:**
1. Verify cleanup is enabled: `NESSUS_SCAN_CLEANUP_ENABLED=true`
2. Check retention hours: `NESSUS_SCAN_RETENTION_HOURS=24`
3. Look for errors in logs: `grep "Nessus scan cleanup error"`

**Common causes:**
- Scanner authentication failing
- Scans in trash folder (excluded from cleanup)
- Scans are still "running" status on Nessus

### Task Directories Not Being Deleted

**Symptom:** Old task directories filling up disk.

**Check:**
1. Verify housekeeping enabled: `HOUSEKEEPING_ENABLED=true`
2. Check TTL settings: `COMPLETED_TTL_DAYS`, `FAILED_TTL_DAYS`
3. Verify task status in `task.json` (only completed/failed/timeout are cleaned)

**Common causes:**
- Tasks stuck in "running" status (check stale scan cleanup)
- Permission errors on task directories
- Invalid `task.json` files (JSON parse errors)

### Stale Tasks Not Being Marked

**Symptom:** Tasks remain in "running" status indefinitely.

**Check:**
1. Verify stale cleanup enabled: `STALE_SCAN_CLEANUP_ENABLED=true`
2. Check threshold: `STALE_SCAN_HOURS=24`
3. Look for scanner errors in logs

**Common causes:**
- Scanner instance ID in task doesn't match current config
- Scanner unreachable when cleanup runs

## See Also

- [Scanner Configuration](./SCANNER_CONFIG.md) - Configure scanner pools
- [Worker Architecture](./WORKER.md) - Background worker details
- [Metrics and Monitoring](./METRICS.md) - Prometheus metrics reference
