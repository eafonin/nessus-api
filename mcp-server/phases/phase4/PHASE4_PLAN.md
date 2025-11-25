# Phase 4 Implementation Plan

**Date**: 2025-11-25
**Status**: In Progress
**Completed**: Pool architecture, load-based selection

---

## Completed Work

### Pool Architecture (Committed: b9e1ef9)
- [x] Pool-based queue isolation (`{pool}:queue`)
- [x] Load-based scanner selection (lowest utilization)
- [x] `scanner_pool` parameter on MCP tools
- [x] Multi-pool worker support (`WORKER_POOLS` env)
- [x] Hot-reload via SIGHUP
- [x] Documentation: `docs/SCANNER_POOLS.md`

### Dropped
- ~~Task 4.2: Per-scanner-instance multi-queue~~ (pools sufficient)

---

## Remaining Tasks

### Priority 1: Core Functionality

#### Task 4.3: Enhanced MCP Tools (Partial)
**Status**: 70% complete
**Remaining**:
- [ ] Add `scanner_instance` parameter (specific scanner targeting)
- [ ] Return `scanner_instance` and `scanner_url` in response
- [ ] Add `estimated_wait_time` calculation

**Files**: `tools/mcp_server.py`
**Effort**: ~2 hours

---

#### Task 4.5: Worker Enhancement for Scanner Pool
**Status**: 50% complete
**Remaining**:
- [ ] Validate scan results after export (call validator)
- [ ] Handle validation result (mark failed if auth failed)
- [ ] Pass `scan_type` to validator for auth detection
- [ ] Log authentication status for all scans
- [ ] Metric increment on validation failure

**Files**: `worker/scanner_worker.py`
**Effort**: ~3 hours

---

#### Task 4.6: Enhanced Task Metadata
**Status**: Not started
**Work**:
- [ ] Add `validation_stats: Optional[Dict]` to `mark_completed()`
- [ ] Add `validation_warnings: Optional[List[str]]` to `mark_completed()`
- [ ] Add `authentication_status: Optional[str]` to task
- [ ] Store validation data in task.json

**Files**: `core/task_manager.py`
**Effort**: ~2 hours

---

#### Task 4.7: Enhanced Status API
**Status**: Not started
**Work**:
- [ ] Add `scanner_instance` field to status response
- [ ] Add `results_summary` section (hosts, vulns, severity breakdown)
- [ ] Add `warnings` field for validation warnings
- [ ] Add `authentication_status` field
- [ ] Add `troubleshooting` section for failed auth

**Files**: `tools/mcp_server.py` (get_scan_status tool)
**Effort**: ~2 hours

---

#### Task 4.8: Per-Scanner Prometheus Metrics
**Status**: Not started
**Work**:
- [ ] `nessus_scanner_active_scans{pool, scanner_instance}`
- [ ] `nessus_scanner_capacity{pool, scanner_instance}`
- [ ] `nessus_scanner_utilization_pct{pool, scanner_instance}`
- [ ] `nessus_pool_queue_depth{pool}`
- [ ] `nessus_validation_failures_total{reason}`
- [ ] `nessus_auth_failures_total{pool, scan_type}`
- [ ] Periodic metrics update function

**Files**: `core/metrics.py`
**Effort**: ~3 hours

---

#### Task 4.9: Production Docker Configuration
**Status**: Not started
**Work**:
- [ ] Create `prod/docker-compose.yml`
- [ ] Multi-stage Dockerfile (python:3.12-slim)
- [ ] Resource limits (CPU, memory)
- [ ] One worker per pool configuration
- [ ] Restart policies
- [ ] Create `.env.prod.example`
- [ ] Health checks

**Files**: `prod/docker-compose.yml`, `prod/Dockerfile.api`, `prod/Dockerfile.worker`
**Effort**: ~4 hours

---

### Priority 2: Operational Features

#### Task 4.10: TTL Housekeeping
**Status**: Not started
**Work**:
- [ ] Create `core/housekeeping.py`
- [ ] `cleanup_expired_tasks()` - delete tasks older than TTL
- [ ] Check `last_accessed_at` timestamp
- [ ] Remove task directories (scan results, logs)
- [ ] Update metrics (`ttl_deletions_total`)
- [ ] Periodic scheduler (hourly)

**Files**: `core/housekeeping.py`
**Effort**: ~2 hours

---

#### Task 4.11: Dead Letter Queue Handler
**Status**: Not started
**Work**:
- [ ] Create `tools/admin_cli.py`
- [ ] `list-dlq` - show failed tasks
- [ ] `inspect-dlq <task_id>` - view details
- [ ] `retry-dlq <task_id>` - re-queue task
- [ ] `purge-dlq` - clear all (with confirmation)
- [ ] `stats` - queue statistics

**Files**: `tools/admin_cli.py`
**Effort**: ~3 hours

---

#### Task 4.12: Error Recovery & Circuit Breaker
**Status**: Not started
**Work**:
- [ ] Retry logic (3 attempts for transient errors)
- [ ] Exponential backoff (1s, 2s, 4s)
- [ ] Circuit breaker per scanner
  - Track consecutive failures
  - Disable after 5 failures
  - Auto-re-enable after 5 min cooldown
- [ ] Distinguish transient vs permanent errors
- [ ] Metric: `nessus_scanner_circuit_breaker_open{scanner}`

**Files**: `worker/scanner_worker.py`, `scanners/registry.py`
**Effort**: ~4 hours

---

## Implementation Order

### Phase 4A: Core Enhancement (Day 1-2)
1. **Task 4.6**: Enhanced Task Metadata (2h)
   - Foundation for validation storage
2. **Task 4.5**: Worker Enhancement (3h)
   - Validation integration
3. **Task 4.3**: Enhanced MCP Tools (2h)
   - Scanner instance targeting

### Phase 4B: Observability & Status (Day 2-3)
4. **Task 4.7**: Enhanced Status API (2h)
   - Expose validation in status
5. **Task 4.8**: Per-Scanner Metrics (3h)
   - Pool/scanner metrics

### Phase 4C: Production Ready (Day 3-4)
6. **Task 4.9**: Production Docker (4h)
   - Multi-worker deployment

### Phase 4D: Operations (Day 4-5)
7. **Task 4.10**: TTL Housekeeping (2h)
8. **Task 4.11**: DLQ Handler (3h)
9. **Task 4.12**: Error Recovery (4h)

---

## Dependencies

```
Task 4.6 (Task Metadata)
    └── Task 4.5 (Worker Enhancement) - needs metadata storage
         └── Task 4.7 (Status API) - needs validation data
              └── Task 4.8 (Metrics) - can parallel with 4.7

Task 4.9 (Docker) - independent, can start anytime
Task 4.10 (TTL) - independent
Task 4.11 (DLQ) - independent
Task 4.12 (Circuit Breaker) - depends on 4.5
```

---

## Success Criteria

Phase 4 complete when:
- [ ] Multiple pools configured and operational
- [ ] Per-scanner concurrency limits enforced
- [ ] Validation stats visible in status API
- [ ] Per-scanner/pool metrics exposed
- [ ] Production Docker deployment working
- [ ] TTL housekeeping running
- [ ] DLQ CLI functional
- [ ] Circuit breaker protecting against failing scanners

---

## Files Summary

| Task | New Files | Modified Files |
|------|-----------|----------------|
| 4.3 | - | `tools/mcp_server.py` |
| 4.5 | - | `worker/scanner_worker.py` |
| 4.6 | - | `core/task_manager.py` |
| 4.7 | - | `tools/mcp_server.py` |
| 4.8 | - | `core/metrics.py` |
| 4.9 | `prod/docker-compose.yml`, `prod/Dockerfile.*` | - |
| 4.10 | `core/housekeeping.py` | `worker/scanner_worker.py` |
| 4.11 | `tools/admin_cli.py` | - |
| 4.12 | - | `worker/scanner_worker.py`, `scanners/registry.py` |

---

**Total Estimated Effort**: ~25 hours
**Recommended Duration**: 4-5 days
