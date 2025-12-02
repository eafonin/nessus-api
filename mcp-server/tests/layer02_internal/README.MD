# Layer 02: Internal Tests

[← Test Suite](../README.MD)

---

## Purpose

Test core modules in isolation using mocks. No external services required. These tests validate the internal logic of the MCP server components.

**Duration**: ~30 seconds
**Marker**: `@pytest.mark.layer02`

---

## Tests

| Test File | Module Tested | Key Functionality |
|-----------|---------------|-------------------|
| `test_task_manager.py` | `core/task_manager.py` | State machine transitions, task persistence |
| `test_queue.py` | `core/queue.py` | FIFO operations, DLQ handling |
| `test_pool_registry.py` | `scanners/registry.py` | Scanner pool management, load balancing |
| `test_circuit_breaker.py` | `core/circuit_breaker.py` | Scanner health detection |
| `test_health.py` | `core/health.py` | Health endpoint responses |
| `test_housekeeping.py` | `core/housekeeping.py` | Task cleanup, expiration |
| `test_metrics.py` | `core/metrics.py` | Prometheus metrics |
| `test_logging_config.py` | `core/logging_config.py` | Structured logging setup |
| `test_ip_utils.py` | `core/ip_utils.py` | CIDR parsing, IP validation |
| `test_nessus_validator.py` | `scanners/nessus_validator.py` | Auth detection from results |
| `test_admin_cli.py` | `tools/admin_cli.py` | CLI command parsing |
| `test_idempotency.py` | Idempotency handling | Key deduplication |

---

## Running

```bash
# Run all layer02 tests
pytest tests/layer02_internal/ -v

# Run by marker
pytest -m layer02 -v

# Run locally (no Docker needed)
cd mcp-server
source venv/bin/activate
pytest tests/layer02_internal/ -v

# Run single module
pytest tests/layer02_internal/test_task_manager.py -v
```

---

## If Tests Fail

These tests use mocks and don't depend on external services. Failures indicate:

1. **Logic bug** - Check recent code changes to the tested module
2. **Import error** - Ensure `sys.path` includes mcp-server root
3. **Mock setup** - Verify mock fixtures match current API

### Debugging

```bash
# Run with verbose output
pytest tests/layer02_internal/test_task_manager.py -v -s

# Run single test
pytest tests/layer02_internal/test_task_manager.py::TestTaskManagerBasic::test_create_and_get_task -v -s
```

---

## Dependencies

- Python 3.11+
- pytest, pytest-asyncio
- No external services (all mocked)

---

## See Also

- [Layer 01: Infrastructure](../layer01_infrastructure/README.MD)
- [Layer 03: External Basic](../layer03_external_basic/README.MD)
