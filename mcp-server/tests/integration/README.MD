<!-- README Navigation -->
<!-- L4: mcp-server/tests/integration/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: E2E tests with real Redis and MCP server -->

# Integration Tests

> End-to-end tests with real Redis and MCP server

**↑ Parent**: [Test Suite](../README.MD) | **↑↑ MCP Server**: [README](../../README.MD) | **↑↑↑ Root**: [Nessus MCP Server](../../../README.MD)

## Running Tests

```bash
# Quick smoke test
pytest tests/integration/test_fastmcp_client_smoke.py -v

# Phase tests (infrastructure)
pytest tests/integration/test_phase0.py tests/integration/test_phase2.py -v

# Full integration suite
pytest tests/integration/ -v

# E2E with real scanners (slow, 5-10 min)
pytest tests/integration/test_mcp_client_e2e.py -v --timeout=600
```

## Test Categories

### MCP Client Tests

| File | Duration | Description |
|------|----------|-------------|
| `test_fastmcp_client_smoke.py` | ~5s | Basic MCP tool calls |
| `test_fastmcp_client.py` | ~30s | Client wrapper functionality |
| `test_fastmcp_client_e2e.py` | ~5min | Full scan workflow via MCP |
| `test_mcp_client_e2e.py` | ~10min | Comprehensive E2E with results |

### Phase Tests

Development milestones with incremental validation:

| File | Phase | Description |
|------|-------|-------------|
| `test_phase0.py` | 0 | Foundation - queue, task manager |
| `test_phase1.py` | 1 | Real Nessus - scan creation/status |
| `test_phase1_workflow.py` | 1 | Complete scan workflow |
| `test_phase0_phase1_real_nessus.py` | 0-1 | Combined real scanner tests |
| `test_phase2.py` | 2 | Schema - results parsing/filtering |
| `test_phase3_observability.py` | 3 | Metrics, logging, tracing |

### Scanner Tests

| File | Duration | Description |
|------|----------|-------------|
| `test_nessus_scanner.py` | ~30s | Scanner wrapper unit tests |
| `test_nessus_standalone.py` | ~1min | Direct Nessus API calls |
| `test_nessus_read_write_operations.py` | ~2min | Scan CRUD operations |
| `test_scanner_wrapper_comparison.py` | ~1min | Mock vs real scanner comparison |
| `test_connectivity.py` | ~10s | Network connectivity checks |

### Workflow Tests

| File | Duration | Description |
|------|----------|-------------|
| `test_pool_workflow.py` | ~1min | Pool selection, load balancing |
| `test_queue.py` | ~30s | Queue operations, backpressure |
| `test_idempotency.py` | ~30s | Duplicate request handling |
| `test_complete_scan_with_results.py` | ~5min | Full scan with result retrieval |
| `test_authenticated_scan_workflow.py` | ~10min | SSH authenticated scans |

## Configuration

### conftest.py Fixtures

```python
@pytest.fixture
def mcp_client():
    """FastMCP client connected to test server."""

@pytest.fixture
def scanner_registry():
    """Initialized scanner pool registry."""

@pytest.fixture
def redis_client():
    """Redis client for queue/task operations."""
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_URL` | `http://localhost:8836` | MCP server endpoint |
| `NESSUS_URL` | `https://172.30.0.3:8834` | Scanner URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |

## Pytest Marks

```bash
# Skip slow tests
pytest tests/integration/ -m "not slow"

# Run only E2E tests
pytest tests/integration/ -m e2e

# Skip tests requiring scanner
pytest tests/integration/ -m "not scanner"
```

## Documentation

See `TEST_WORKFLOW_PHASES_0_1.md` for detailed phase test documentation.
