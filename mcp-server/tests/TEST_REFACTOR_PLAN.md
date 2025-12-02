# Test Suite Refactoring Plan

**Status**: APPROVED
**Created**: 2025-12-02
**Updated**: 2025-12-02

---

## Approved Decisions

| Question | Decision |
|----------|----------|
| Layer naming | `layer01_infrastructure`, `layer02_internal`, etc. |
| Marker naming | `@pytest.mark.layer01`, `@pytest.mark.layer02`, etc. |
| Priority | Documentation first, then test restructuring |
| Dual scanner tests | Keep separate at lower layer, add pool test at higher layer |

**Rationale for layers**: Layered tests from basic to comprehensive enable narrowed troubleshooting. If layer01 passes but layer03 fails, the issue is in external integration, not infrastructure.

---

## Executive Summary

Refactor the test suite from development-era "phase" naming to a clean, layered architecture aligned with FEATURES.md. Consolidate overlapping tests, fix broken documentation references, and identify coverage gaps.

---

## 1. Current State Analysis

### 1.1 Test File Inventory

**Unit Tests (12 files)**:
| File | Tests | Covers |
|------|-------|--------|
| `test_task_manager.py` | ~18 | `core/task_manager.py` - state machine, persistence |
| `test_pool_queue.py` | ~12 | `core/queue.py` - FIFO, DLQ operations |
| `test_pool_registry.py` | ~15 | `scanners/registry.py` - pool management |
| `test_health.py` | ~17 | `core/health.py` - health endpoints |
| `test_housekeeping.py` | ~12 | `core/housekeeping.py` - cleanup |
| `test_circuit_breaker.py` | ~15 | `core/circuit_breaker.py` - scanner health |
| `test_metrics.py` | ~23 | `core/metrics.py` - Prometheus |
| `test_logging_config.py` | ~9 | `core/logging_config.py` - structlog |
| `test_ip_utils.py` | ~20 | `core/ip_utils.py` - CIDR parsing |
| `test_nessus_validator.py` | ~20 | `scanners/nessus_validator.py` - auth detection |
| `test_authenticated_scans.py` | ~15 | `tools/mcp_tools.py` - credential handling |
| `test_admin_cli.py` | ~10 | `tools/admin_cli.py` - CLI commands |

**Integration Tests (24 files)**:
| File | Duration | Purpose |
|------|----------|---------|
| `test_connectivity.py` | ~10s | Nessus WebUI reachable, SSL, endpoints |
| `test_queue.py` | ~30s | Redis queue operations |
| `test_idempotency.py` | ~30s | Idempotency key handling |
| `test_phase0.py` | - | Aggregator (imports other tests) |
| `test_phase1.py` | ~1min | Scanner integration |
| `test_phase1_workflow.py` | ~5min | Complete scan workflow |
| `test_phase2.py` | ~30s | Schema parsing, filters, pagination |
| `test_phase3_observability.py` | ~1min | Metrics, logging |
| `test_phase0_phase1_real_nessus.py` | ~5min | Combined Phase 0+1 with real scanner |
| `test_fastmcp_client_smoke.py` | ~20s | Quick MCP client validation |
| `test_fastmcp_client.py` | ~30s | MCP client wrapper tests |
| `test_fastmcp_client_e2e.py` | ~5-10min | Full scan workflow via MCP |
| `test_mcp_client_e2e.py` | ~10min | MCP protocol layer tests |
| `test_nessus_scanner.py` | ~30s | Scanner wrapper unit tests |
| `test_nessus_standalone.py` | ~1min | Direct Nessus API calls |
| `test_nessus_read_write_operations.py` | ~2min | Scan CRUD operations |
| `test_scanner_wrapper_comparison.py` | ~1min | Mock vs real scanner |
| `test_pool_workflow.py` | ~1min | Pool selection, load balancing |
| `test_complete_scan_with_results.py` | ~5min | Full scan with results |
| `test_authenticated_scan_workflow.py` | ~10min | SSH authenticated scans |
| `test_both_scanners.py` | ~2min | Dual scanner tests |

**Orphaned/Misplaced**:
- `tests/test_phase0_integration.py` - Root-level file (should be in integration/)
- `tests/client/nessus_client.py` - Stub client (incomplete TODO implementations)

### 1.2 Identified Issues

1. **Phase nomenclature** - "phase0", "phase1" etc. are development milestones, not functional descriptions
2. **Aggregator files** - `test_phase0.py` just imports other tests (confusing)
3. **Duplicate coverage** - 4 MCP client test files with overlapping scope
4. **Broken references** - TESTING.md references archived docs
5. **Stub code** - `tests/client/nessus_client.py` has TODO placeholders
6. **Orphaned files** - `test_phase0_integration.py` in wrong directory

---

## 2. Proposed Layer Structure

Based on your requirements, tests will be organized into 4 layers:

```
Layer 1: Infrastructure      [<1s]   WebUI accessible, auth working, target accounts
Layer 2: Internal            [~30s]  Queue, task manager, config parsing
Layer 3: External Basic      [~1min] Single MCP tool calls, scanner integration
Layer 4: Full Workflow       [5-10m] Complete scan → results workflow
```

### 2.1 New Directory Structure

```
tests/
├── README.MD                       # Overview (rewrite)
├── conftest.py                     # Root pytest config (update markers)
├── fixtures/                       # Sample data (keep as-is)
│   └── README.MD
│
├── layer01_infrastructure/         # Connectivity & basic checks [<1s]
│   ├── README.MD
│   ├── conftest.py
│   ├── test_nessus_connectivity.py     # ← from test_connectivity.py
│   ├── test_redis_connectivity.py      # NEW: Extract from test_queue.py
│   ├── test_target_accounts.py         # NEW: Extract from test_authenticated_scan_workflow.py
│   └── test_both_scanners.py           # ← from integration/ (KEEP SEPARATE per decision)
│
├── layer02_internal/               # Core internals (no external services) [~30s]
│   ├── README.MD
│   ├── conftest.py
│   ├── test_task_manager.py            # ← from unit/
│   ├── test_queue.py                   # ← from unit/test_pool_queue.py + integration/test_queue.py
│   ├── test_idempotency.py             # ← from integration/
│   ├── test_pool_registry.py           # ← from unit/
│   ├── test_circuit_breaker.py         # ← from unit/
│   ├── test_health.py                  # ← from unit/
│   ├── test_housekeeping.py            # ← from unit/
│   ├── test_metrics.py                 # ← from unit/
│   ├── test_logging_config.py          # ← from unit/
│   ├── test_ip_utils.py                # ← from unit/
│   ├── test_nessus_validator.py        # ← from unit/
│   └── test_admin_cli.py               # ← from unit/
│
├── layer03_external_basic/         # Single tool calls with real services [~1min]
│   ├── README.MD
│   ├── conftest.py
│   ├── test_mcp_tools_basic.py         # ← from test_fastmcp_client.py (TestClientConnection, etc.)
│   ├── test_scanner_operations.py      # ← from test_nessus_scanner.py + test_nessus_standalone.py
│   ├── test_pool_selection.py          # ← from test_pool_workflow.py
│   ├── test_schema_parsing.py          # ← from test_phase2.py (TestParser, TestProfiles, TestFilters)
│   └── test_authenticated_credentials.py # ← from test_authenticated_scan_workflow.py (TestCredentialInjection)
│
├── layer04_full_workflow/          # Complete E2E workflows [5-10min]
│   ├── README.MD
│   ├── conftest.py
│   ├── test_untrusted_scan_workflow.py # ← from test_fastmcp_client_e2e.py + test_complete_scan_with_results.py
│   ├── test_authenticated_scan_workflow.py # ← from test_authenticated_scan_workflow.py (TestQuickAuthenticatedScan, TestPrivilegedScans)
│   ├── test_mcp_protocol_e2e.py        # ← from test_mcp_client_e2e.py
│   ├── test_result_filtering_workflow.py # ← from test_fastmcp_client_e2e.py::test_e2e_with_result_filtering
│   └── test_pool_workflow.py           # NEW: Pool selection E2E (higher layer per decision)
│
├── client/                         # Test utilities (keep, but fix)
│   ├── README.MD
│   └── nessus_fastmcp_client.py    # KEEP (working client)
│   # DELETE: nessus_client.py (stub)
│
└── run_test_pipeline.sh            # Update for new structure
```

### 2.2 Files to DELETE

| File | Reason |
|------|--------|
| `tests/test_phase0_integration.py` | Orphaned, content merged elsewhere |
| `tests/client/nessus_client.py` | Stub with TODO placeholders |
| `integration/test_phase0.py` | Aggregator only (imports other tests) |
| `integration/test_phase1.py` | Content merged into layer3/layer4 |
| `integration/test_phase1_workflow.py` | Merged into layer4 |
| `integration/test_phase0_phase1_real_nessus.py` | Merged into layer4 |
| `integration/test_phase3_observability.py` | Merged into layer2 |
| `integration/test_fastmcp_client_smoke.py` | Merged into layer3 |
| `integration/run_e2e_test_interactive.py` | Script, not test |

---

## 3. Test → Feature Matrix

Mapping tests to FEATURES.md MCP tools:

### 3.1 Current Coverage

| MCP Tool | Unit Test | Integration Test | E2E Test | Coverage Status |
|----------|-----------|------------------|----------|-----------------|
| `run_untrusted_scan` | ✅ | ✅ | ✅ | **GOOD** |
| `run_authenticated_scan` | ✅ | ✅ | ✅ | **GOOD** |
| `get_scan_status` | ✅ | ✅ | ✅ | **GOOD** |
| `get_scan_results` | ✅ test_phase2 | ✅ | ✅ | **GOOD** |
| `list_tasks` | ❌ | ✅ | ✅ | **NEEDS UNIT** |
| `list_scanners` | ✅ | ✅ | ✅ | **GOOD** |
| `list_pools` | ✅ | ✅ | ❌ | **NEEDS E2E** |
| `get_pool_status` | ✅ | ✅ | ❌ | **NEEDS E2E** |
| `get_queue_status` | ❌ | ✅ | ✅ | **NEEDS UNIT** |

### 3.2 Feature Coverage Gaps

| Feature (from FEATURES.md) | Current Coverage | Gap |
|----------------------------|------------------|-----|
| Schema Profiles (minimal/summary/brief/full) | ✅ test_phase2 | - |
| Filtering Syntax (string/numeric/bool/list) | ✅ test_phase2 | - |
| Pagination (page=0 for all) | ✅ test_phase2 | - |
| Authentication Detection | ✅ test_nessus_validator | - |
| Idempotency (48h TTL) | ✅ test_idempotency | - |
| Queue Position / Wait Estimation | ❌ | **GAP: Need unit test** |
| Error Responses (404, 409) | ❌ | **GAP: Need explicit tests** |
| CIDR-aware target filtering | ✅ test_ip_utils | - |

### 3.3 New Tests to Create

1. **`layer2_internal/test_list_tasks.py`** - Unit tests for list_tasks filtering
2. **`layer2_internal/test_queue_status.py`** - Unit tests for get_queue_status
3. **`layer2_internal/test_error_responses.py`** - Error response format validation
4. **`layer3_external_basic/test_pool_operations.py`** - list_pools, get_pool_status
5. **`layer4_full_workflow/test_queue_position_accuracy.py`** - Queue wait estimation E2E

---

## 4. Documentation Fixes

### 4.1 TESTING.md Updates

**Current broken references**:
- `FASTMCP_CLIENT_REQUIREMENT.md` → Archived
- `FASTMCP_CLIENT_ARCHITECTURE.md` → Archived
- `TEST_WORKFLOW_PHASES_0_1.md` → Does not exist

**Fix**: Remove archived references, update to point to layer structure.

### 4.2 README Files to Update

| File | Action |
|------|--------|
| `tests/README.MD` | Rewrite for layer structure |
| `tests/unit/README.MD` | DELETE (merged into layers) |
| `tests/integration/README.MD` | DELETE (merged into layers) |
| `tests/layer1_infrastructure/README.MD` | CREATE |
| `tests/layer2_internal/README.MD` | CREATE |
| `tests/layer3_external_basic/README.MD` | CREATE |
| `tests/layer4_full_workflow/README.MD` | CREATE |

---

## 5. Pytest Marker Updates

### 5.1 Current Markers (to deprecate)

```python
@pytest.mark.phase0
@pytest.mark.phase1
@pytest.mark.phase2
@pytest.mark.phase3
@pytest.mark.phase4
```

### 5.2 New Markers

```python
@pytest.mark.layer01       # Infrastructure checks (<1s)
@pytest.mark.layer02       # Internal functionality (~30s)
@pytest.mark.layer03       # External basic (~1min)
@pytest.mark.layer04       # Full workflow (5-10min)

@pytest.mark.requires_nessus    # Keep
@pytest.mark.requires_redis     # NEW
@pytest.mark.requires_mcp       # NEW
@pytest.mark.slow               # Keep
@pytest.mark.e2e                # Keep
```

### 5.3 Usage Examples

```bash
# Run all layer01 tests (quick infrastructure validation)
pytest -m layer01

# Run layers 01-02 (infrastructure + internal)
pytest -m "layer01 or layer02"

# Run everything except slow E2E workflows
pytest -m "not layer04"

# Run specific layer with verbose output
pytest -m layer03 -v -s
```

---

## 6. Execution Plan

### Phase 1: Preparation (non-breaking)
1. Create new directory structure (empty)
2. Create new README files
3. Update TESTING.md (remove broken refs)
4. Update conftest.py with new markers

### Phase 2: Migration (test by test)
1. Copy tests to new locations with new names
2. Update imports and fixtures
3. Run both old and new to verify
4. Delete old files

### Phase 3: New Tests
1. Create coverage gap tests
2. Run full suite
3. Update run_test_pipeline.sh

### Phase 4: Cleanup
1. Delete deprecated directories
2. Remove old markers from conftest.py
3. Final documentation update

---

## 7. Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing CI/CD | Keep old markers temporarily, deprecate gradually |
| Lost test coverage | Run coverage report before/after |
| Import errors | Update sys.path in conftest.py |
| Fixture incompatibility | Create layer-specific conftest.py files |

---

## 8. Approval Checklist

- [ ] Layer structure approved
- [ ] File naming conventions approved
- [ ] Coverage gap priorities approved
- [ ] Timeline acceptable
- [ ] Documentation approach approved

---

## Questions for Approval

1. **Layer naming**: Is `layer1_infrastructure` clear, or prefer `01_infrastructure`?
2. **Marker prefix**: Keep `@pytest.mark.layer1` or use `@pytest.mark.l1`?
3. **Priority**: Start with documentation fixes or test restructuring?
4. **Dual scanner tests**: Keep `test_both_scanners.py` or merge into pool tests?
