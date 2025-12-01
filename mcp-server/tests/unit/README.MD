<!-- README Navigation -->
<!-- L4: mcp-server/tests/unit/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Isolated component tests, no external dependencies -->

# Unit Tests

> Isolated component tests with no external dependencies

**↑ Parent**: [Test Suite](../README.MD) | **↑↑ MCP Server**: [README](../../README.MD) | **↑↑↑ Root**: [Nessus MCP Server](../../../README.MD)

## Running Tests

```bash
# All unit tests
pytest tests/unit/ -v

# Specific category
pytest tests/unit/test_health.py -v

# With coverage
pytest tests/unit/ --cov=core --cov=schema
```

## Test Categories

### Infrastructure

| File | Tests | Module | Coverage |
|------|-------|--------|----------|
| `test_circuit_breaker.py` | ~15 | `core/circuit_breaker.py` | Scanner health states, failure thresholds |
| `test_health.py` | ~17 | `core/health.py` | Health endpoints, dependency checks |
| `test_housekeeping.py` | ~12 | `core/housekeeping.py` | Task cleanup, orphan detection |
| `test_logging_config.py` | ~9 | `core/logging_config.py` | Structlog setup, JSON formatting |
| `test_metrics.py` | ~23 | `core/metrics.py` | Prometheus counters, histograms |

### Core Logic

| File | Tests | Module | Coverage |
|------|-------|--------|----------|
| `test_task_manager.py` | ~18 | `core/task_manager.py` | State machine transitions, Redis persistence |
| `test_pool_queue.py` | ~12 | `core/queue.py` | Queue operations, DLQ handling |
| `test_pool_registry.py` | ~15 | `scanners/registry.py` | Pool management, load balancing |
| `test_ip_utils.py` | ~20 | `core/ip_utils.py` | CIDR parsing, IP expansion, validation |
| `test_idempotency.py` | - | `core/idempotency.py` | (in integration/) |

### Scanner/Validation

| File | Tests | Module | Coverage |
|------|-------|--------|----------|
| `test_nessus_validator.py` | ~20 | `scanners/nessus_validator.py` | Result validation, auth detection |
| `test_authenticated_scans.py` | ~15 | `tools/mcp_tools.py` | SSH credential handling, privilege escalation |

### Admin Tools

| File | Tests | Module | Coverage |
|------|-------|--------|----------|
| `test_admin_cli.py` | ~10 | `tools/admin_cli.py` | CLI commands, queue management |

## Key Test Patterns

### Mocking Redis

```python
@pytest.fixture
def mock_redis():
    with patch('core.task_manager.redis_client') as mock:
        yield mock
```

### State Machine Tests

```python
def test_task_transitions(task_manager):
    task = task_manager.create_task(...)
    assert task.status == "queued"

    task_manager.start_task(task.task_id)
    assert task.status == "running"

    task_manager.complete_task(task.task_id, results={...})
    assert task.status == "completed"
```

## Dependencies

Unit tests use mocks for:
- Redis client
- Nessus API
- HTTP clients
- File system (for fixtures)
