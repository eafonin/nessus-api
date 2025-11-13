# Phase 4 Implementation Status

**Date**: 2025-11-10
**Status**: Ready to Begin
**Prerequisites**: ✅ All Complete (Phases 0-3)

---

## Current State Summary

### Completed Phases
- **Phase 0**: ✅ Foundation (task storage, queue, scanner wrapper)
- **Phase 1**: ✅ Real Nessus Integration (dynamic X-API-Token, tests passing)
- **Phase 2**: ✅ Schema & Results Parsing (NessusParser, filter infrastructure)
- **Phase 3**: ✅ Observability (structured logging, 8 Prometheus metrics, health checks)

### Scanner Infrastructure
**Scanner 1** (Primary):
- URL: `https://localhost:8834` (host IP: `https://172.32.0.209:8834`)
- Network: VPN Gateway (WireGuard)
- Status: ✅ Active, ready
- Location: `/home/nessus/docker/nessus/`

**Scanner 2** (Secondary):
- URL: `https://localhost:8836` (host IP: `https://172.32.0.209:8836`)
- Network: Direct (no VPN)
- Status: 🟡 Activating (expected ~6-11 min total)
- Location: `/home/nessus/docker/nessus2/`
- Activation Code: `YGHZ-GELQ-RNZX-QSSH-4XD5`

---

## Existing Components

### Already Implemented (From Phases 0-3)

**Scanner Registry** (`mcp-server/scanners/registry.py`):
- ✅ YAML-based configuration loading
- ✅ Environment variable substitution
- ✅ Round-robin load balancing
- ✅ Hot-reload on SIGHUP
- ❌ NO per-scanner concurrency tracking (Redis)

**Queue System** (`mcp-server/core/queue.py`):
- ✅ Redis FIFO queue
- ✅ DLQ support
- ✅ Single global queue
- ❌ NO per-scanner queues
- ❌ NO multi-queue routing

**Scanner Configuration** (`mcp-server/config/scanners.yaml`):
- ✅ YAML structure defined
- ✅ Single scanner configured
- ❌ Needs second scanner entry

**MCP Tools** (`mcp-server/tools/mcp_server.py`):
- ✅ 6 MCP tools functional
- ❌ NO scanner instance selection parameter
- ❌ NO capacity-aware routing

**Task Manager** (`mcp-server/core/task_manager.py`):
- ✅ File-based task storage
- ✅ Status tracking
- ❌ NO validation stats storage

**Observability** (Phase 3):
- ✅ Structured JSON logging (structlog)
- ✅ 8 Prometheus metrics
- ✅ Health check endpoints (`/health`, `/metrics`)
- ✅ Trace ID propagation
- ✅ Worker instrumentation (39 log events)

---

## Phase 4 Implementation Plan

### Priority 1: Core Multi-Scanner Functionality

Based on user requirements: **Multi-scanner pool + Production Docker**

#### Task 4.1: Scanner Pool Management (Redis Concurrency)
**Status**: 🔴 Not Started
**Files to Modify/Create**:
- ✏️ `mcp-server/scanners/registry.py` - Add Redis-based concurrency tracking
  - `increment_running(scanner_id)` → Redis SET operations
  - `decrement_running(scanner_id)` → Redis SET operations
  - `get_available_instance(scanner_type)` → Check capacity before returning
  - `get_running_count(scanner_id)` → Count of active scans
- ✏️ `mcp-server/config/scanners.yaml` - Add Scanner 2 configuration
  - instance_id: `local2`
  - URL: `https://localhost:8836`
  - max_concurrent_scans: 2 (conservative for testing)

**Redis Keys**:
```
nessus:scanners:local:running → SET of task_ids
nessus:scanners:local2:running → SET of task_ids
```

#### Task 4.2: Multi-Queue System
**Status**: 🔴 Not Started
**Files to Modify**:
- ✏️ `mcp-server/core/queue.py` - Add multi-queue support
  - `enqueue_for_scanner(task, scanner_instance_id)` - Route to specific scanner queue
  - `enqueue_global(task)` - Route to global overflow queue
  - `dequeue_for_scanner(scanner_instance_id)` - Check `[scanner_queue, global_queue]`
  - `get_all_queue_stats()` - Return per-scanner + global queue depths

**Redis Keys**:
```
nessus:queue:nessus:local → LIST (per-scanner queue)
nessus:queue:nessus:local2 → LIST (per-scanner queue)
nessus:queue:global → LIST (overflow queue)
```

#### Task 4.3: Enhanced MCP Tools
**Status**: 🔴 Not Started
**Files to Modify**:
- ✏️ `mcp-server/tools/mcp_server.py` - Add scanner selection to all scan tools
  - New parameter: `scanner_instance: Optional[str] = None`
  - **Routing Logic**:
    1. User specifies scanner + has capacity → route to scanner queue
    2. User specifies scanner + NO capacity → queue for that scanner
    3. No scanner specified + capacity available → pick scanner with capacity
    4. No scanner specified + NO capacity → global queue
  - Enhanced return: `{scanner_instance, scanner_url, queue_position, estimated_wait_time}`

#### Task 4.9: Production Docker Configuration
**Status**: 🔴 Not Started
**Files to Create**:
- 📝 `mcp-server/prod/docker-compose.yml` - Production configuration
  - Multi-stage Dockerfiles (python:3.12-slim)
  - Resource limits (CPU, memory)
  - One worker per scanner:
    - `worker-local` with `SCANNER_INSTANCE_ID=local`
    - `worker-local2` with `SCANNER_INSTANCE_ID=local2`
  - Restart policies: `always`
- 📝 `mcp-server/prod/.env.prod.example` - Production env template

---

### Priority 2: Advanced Features (Deferred)

These tasks will be implemented after core multi-scanner functionality is working:

- **Task 4.4**: Result Validation with Authentication Detection
- **Task 4.5**: Worker Enhancement for Scanner Pool
- **Task 4.6**: Enhanced Task Metadata
- **Task 4.7**: Enhanced Status API
- **Task 4.8**: Per-Scanner Prometheus Metrics
- **Task 4.10**: TTL Housekeeping
- **Task 4.11**: Dead Letter Queue Handler
- **Task 4.12**: Error Recovery & Circuit Breaker

---

## Implementation Approach

### Step-by-Step Plan

**Step 1**: Scanner Pool Management (Task 4.1)
1. Update `config/scanners.yaml` with Scanner 2
2. Implement Redis concurrency tracking in `registry.py`
3. Write unit tests for concurrency tracking
4. Integration test: Two scanners, verify capacity enforcement

**Step 2**: Multi-Queue System (Task 4.2)
1. Implement per-scanner queue methods in `queue.py`
2. Maintain backward compatibility with existing single queue
3. Write unit tests for queue routing
4. Integration test: Route tasks to different scanners

**Step 3**: Enhanced MCP Tools (Task 4.3)
1. Add `scanner_instance` parameter to all 6 MCP tools
2. Implement 4-way routing logic
3. Update return format with scanner info
4. Integration test: User specifies scanner, verify correct routing

**Step 4**: Production Docker (Task 4.9)
1. Create `prod/docker-compose.yml` with two workers
2. Configure resource limits
3. Test production deployment locally
4. Verify both scanners processing concurrently

**Step 5**: Integration Testing
1. Test concurrent scans across both scanners
2. Test capacity limits (max_concurrent_scans)
3. Test queue overflow to global queue
4. Test scanner failure scenarios

---

## Testing Strategy

### Unit Tests (After Each Task)
- `tests/unit/test_scanner_registry.py` - Concurrency tracking
- `tests/unit/test_queue.py` - Multi-queue routing
- `tests/unit/test_mcp_tools.py` - Scanner selection logic

### Integration Tests (After Task Groups)
- `tests/integration/test_phase4_multi_scanner.py` - End-to-end multi-scanner workflow
- `tests/integration/test_phase4_capacity.py` - Concurrency limit enforcement
- `tests/integration/test_phase4_queue_routing.py` - Queue routing correctness

---

## Current Implementation Status

### Task 4.1: Scanner Pool Management
- [ ] Update `config/scanners.yaml` with Scanner 2
- [ ] Implement `increment_running()` / `decrement_running()` in registry
- [ ] Implement `get_available_instance()` with capacity check
- [ ] Add `get_running_count()` method
- [ ] Write unit tests
- [ ] Integration test

### Task 4.2: Multi-Queue System
- [ ] Implement `enqueue_for_scanner()`
- [ ] Implement `enqueue_global()`
- [ ] Implement `dequeue_for_scanner()` (checks scanner + global queues)
- [ ] Implement `get_all_queue_stats()`
- [ ] Write unit tests
- [ ] Integration test

### Task 4.3: Enhanced MCP Tools
- [ ] Add `scanner_instance` parameter to `submit_scan`
- [ ] Add `scanner_instance` parameter to `submit_trusted_scan`
- [ ] Add `scanner_instance` parameter to `submit_privileged_scan`
- [ ] Add `scanner_instance` parameter to `submit_custom_scan`
- [ ] Add `scanner_instance` parameter to `submit_quick_scan`
- [ ] Add `scanner_instance` parameter to `submit_compliance_scan`
- [ ] Implement routing logic in scan submission
- [ ] Update return format with scanner info
- [ ] Write unit tests
- [ ] Integration test

### Task 4.9: Production Docker Configuration
- [ ] Create `prod/docker-compose.yml`
- [ ] Create `prod/Dockerfile.api` (multi-stage)
- [ ] Create `prod/Dockerfile.worker` (multi-stage)
- [ ] Configure worker-local (SCANNER_INSTANCE_ID=local)
- [ ] Configure worker-local2 (SCANNER_INSTANCE_ID=local2)
- [ ] Set resource limits
- [ ] Set restart policies
- [ ] Create `.env.prod.example`
- [ ] Test production deployment
- [ ] Integration test with both workers

---

## Success Criteria

### Phase 4 Core (Priority 1) Complete When:
- ✅ Two Nessus scanners configured and operational
- ✅ Redis-based concurrency tracking enforces `max_concurrent_scans`
- ✅ Tasks route to correct per-scanner queues
- ✅ Global overflow queue handles capacity overload
- ✅ Users can specify scanner in MCP tool calls
- ✅ Production Docker config with two workers
- ✅ Integration tests pass for multi-scanner scenarios
- ✅ Both scanners can process scans concurrently

### Phase 4 Advanced (Priority 2) Complete When:
- ✅ Result validation detects authentication failures
- ✅ Enhanced status API shows validation stats
- ✅ Per-scanner Prometheus metrics
- ✅ TTL housekeeping runs automatically
- ✅ DLQ handler CLI functional
- ✅ Circuit breaker protects against failing scanners

---

## Next Steps

1. **Immediate**: Verify Scanner 2 activation completes successfully
   - Check: `curl -k https://localhost:8836/server/status`
   - Expected: `"status": "ready"`, `"feed_status": {"progress": 100}`

2. **Next**: Begin Task 4.1 (Scanner Pool Management)
   - Update `config/scanners.yaml` with Scanner 2
   - Implement Redis concurrency tracking

3. **Then**: Proceed through tasks 4.2, 4.3, 4.9 sequentially

---

## Files Delivered (This Session)

**Scanner 2 Setup**:
- `/home/nessus/docker/nessus2/docker-compose.yml`
- `/home/nessus/docker/nessus2/README.md`
- `/home/nessus/docker/nessus2/wg/wg0.conf` (copied from Scanner 1)

**Phase 3 Completion** (Previous Session):
- `mcp-server/core/logging_config.py`
- `mcp-server/core/metrics.py`
- `mcp-server/core/health.py`
- `mcp-server/tests/unit/test_logging_config.py`
- `mcp-server/tests/unit/test_metrics.py`
- `mcp-server/tests/unit/test_health.py`
- `mcp-server/tests/integration/test_phase3_observability.py`
- `mcp-server/phases/phase3/PHASE3_COMPLETION.md`

**Documentation**:
- `/home/nessus/docker/nessus/PERSISTENCE_TEST_REPORT.md`
- `mcp-server/phases/PHASE4_STATUS.md` (this file)

---

**Status**: ✅ Ready to begin Phase 4 implementation
**Blockers**: None (waiting for Scanner 2 activation to complete, ~5 more minutes)
**Maintainer**: Development Team
