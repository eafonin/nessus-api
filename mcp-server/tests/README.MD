<!-- README Navigation -->
<!-- L3: mcp-server/tests/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Layered test architecture for MCP Server -->

# Test Suite

> Layered test architecture for Nessus MCP Server

**↑ Parent**: [MCP Server](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

## Quick Reference

```bash
# Fast validation (~20s)
pytest tests/unit/ -q

# Infrastructure tests (~1min)
pytest tests/integration/test_phase0.py tests/integration/test_phase2.py -q

# Full suite (~5min, requires running services)
pytest tests/ -v
```

## Directory Structure

```text
tests/
├── fixtures/        # Sample Nessus XML for parser tests
├── client/          # Test client utilities
├── unit/            # Isolated component tests (<1s)
├── integration/     # E2E tests with services (1-10min)
├── run_test_pipeline.sh      # Orchestrates test layers
├── test_phase0_integration.py # Root-level phase validation
└── conftest.py      # Root pytest configuration
```

## Subdirectories

| Directory | Purpose | Duration |
|-----------|---------|----------|
| [fixtures/](fixtures/README.MD) | Sample Nessus scan output for parser tests | - |
| [client/](client/README.MD) | Async HTTP client for workflow testing | - |
| [unit/](unit/README.MD) | 12 test files covering core modules | <1s |
| [integration/](integration/README.MD) | 20 test files for E2E workflows | 1-10min |

## Test Layers

```text
Layer 4: E2E Tests           [5-10 min]  Full scan → results workflow
    ↑
Layer 3: Integration Tests   [1-3 min]   Scanner + MCP client
    ↑
Layer 2: Infrastructure      [~5 sec]    Queue, tasks, idempotency
    ↑
Layer 1: Unit Tests          [<1 sec]    Isolated components
```

### Layer 1: Unit Tests

**Location**: `tests/unit/`

Fast, isolated tests with no external dependencies. Uses mocks for Redis, Nessus API, HTTP clients.

```bash
docker compose exec mcp-api pytest tests/unit/ -v
```

### Layer 2: Infrastructure Tests

**Location**: `tests/integration/test_phase0.py`

Tests core queue and task management. Requires Redis but not Nessus scanner.

**Components**: Redis queue operations, task storage, idempotency handling, concurrent operations.

```bash
docker compose exec mcp-api pytest tests/integration/test_phase0.py -v
```

### Layer 3: Integration Tests

**Location**: `tests/integration/test_phase1.py`, `test_phase2.py`, `test_fastmcp_client_smoke.py`

Tests scanner integration and result parsing. Some tests require live Nessus scanner.

```bash
# Scanner integration
docker compose exec mcp-api pytest tests/integration/test_phase1.py -v

# Schema/results (uses fixtures, no scanner needed)
docker compose exec mcp-api pytest tests/integration/test_phase2.py -v

# MCP client smoke test (~20s)
docker compose exec mcp-api pytest tests/integration/test_fastmcp_client_smoke.py -v -s
```

### Layer 4: E2E Tests

**Location**: `tests/integration/test_fastmcp_client_e2e.py`, `test_mcp_client_e2e.py`

Complete end-to-end workflow validation. Takes 5-10 minutes per test.

```bash
docker compose exec mcp-api pytest tests/integration/test_fastmcp_client_e2e.py -v -s
```

## Running Tests

### From Docker

```bash
# Unit tests
docker compose exec mcp-api pytest tests/unit/ -v

# Quick pipeline
docker compose exec mcp-api tests/run_test_pipeline.sh --quick

# Full pipeline with E2E
docker compose exec mcp-api tests/run_test_pipeline.sh --full
```

### Local Development

```bash
cd mcp-server
source venv/bin/activate
pytest tests/unit/ -v
```

## Test Pipeline Script

`run_test_pipeline.sh` provides layered test execution:

| Flag | Tests Run | Duration |
|------|-----------|----------|
| (none) | Unit + infrastructure | ~30s |
| `--quick` | Unit + Phase 0/2 + smoke | ~1min |
| `--full` | All tests including E2E | ~10min |

## Environment Variables

Tests use these environment variables with defaults configured in `integration/conftest.py`:

### Scanner Configuration

| Variable | Docker Default | Host Default | Description |
|----------|----------------|--------------|-------------|
| `NESSUS_URL` | `https://172.30.0.3:8834` | - | Nessus scanner URL (internal bridge) |
| `NESSUS_USERNAME` | `nessus` | - | Scanner username |
| `NESSUS_PASSWORD` | `nessus` | - | Scanner password |

### Infrastructure

| Variable | Docker Default | Host Default | Description |
|----------|----------------|--------------|-------------|
| `REDIS_HOST` | `redis` | `localhost` | Redis hostname |
| `REDIS_PORT` | `6379` | `6379` | Redis port |
| `REDIS_DB` | `0` | `0` | Redis database number |

### MCP Server

| Variable | Docker Default | Host Default | Description |
|----------|----------------|--------------|-------------|
| `MCP_SERVER_URL` | `http://mcp-api:8000/mcp` | `http://localhost:8836/mcp` | MCP server endpoint |
| `TEST_TARGET` | `172.32.0.215` | - | Default scan target |

## Test Targets

> **Important**: Nessus license has limited IP count. Only use approved targets below.

### Approved Scan Targets

| IP | Host | Auth Type | Credentials | Notes |
|----|------|-----------|-------------|-------|
| `172.32.0.215` | External host | Root (SSH) | `randy` / `randylovesgoldfish1998` | Primary test target, full sudo |
| `172.32.0.209` | Docker host | Non-root (SSH) | `nessus` / `nessus` | Nessus server host, sudo available |

### Test Users for Privilege Escalation (172.32.0.209)

| Username | Password | Sudo Config | Purpose |
|----------|----------|-------------|---------|
| `testauth_sudo_pass` | `TestPass123!` | sudo with password | Test `authenticated_privileged` with escalation_password |
| `testauth_sudo_nopass` | `TestPass123!` | sudo NOPASSWD | Test `authenticated_privileged` without escalation_password |
| `testauth_nosudo` | `TestPass123!` | No sudo | Test `authenticated` (Plugin 110385 expected) |

### IP Limits Warning

- **DO NOT** scan random IPs or large subnets
- **DO NOT** add new targets without approval
- **ALWAYS** use the two approved targets above
- For network discovery tests, use `/32` (single host) scans only

## Shared Fixtures

The `tests/integration/conftest.py` provides shared fixtures:

| Fixture | Type | Description |
|---------|------|-------------|
| `scanner` | `NessusScanner` | Authenticated scanner instance |
| `redis_client` | `redis.Redis` | Redis client for queue operations |
| `nessus_config` | `dict` | Nessus connection configuration |
| `redis_config` | `dict` | Redis connection configuration |
| `sample_target` | `str` | Safe test target (127.0.0.1) |
| `sample_scan_name` | `str` | Standard test scan name |
| `queue_prefix` | `str` | Queue key prefix (nessus:queue) |
| `task_prefix` | `str` | Task key prefix (nessus:task) |

## Pytest Markers

Custom markers registered in `integration/conftest.py`:

```python
@pytest.mark.phase0      # Phase 0 tests (task management, queue)
@pytest.mark.phase1      # Phase 1 tests (scanner integration)
@pytest.mark.phase2      # Phase 2 tests (schema/results)
@pytest.mark.phase3      # Phase 3 tests (observability)
@pytest.mark.phase4      # Phase 4 tests (production)
@pytest.mark.integration # All integration tests
@pytest.mark.slow        # Long-running tests
@pytest.mark.requires_nessus  # Tests requiring Nessus scanner
```

**Run by marker**:

```bash
docker compose exec mcp-api pytest -m phase1 -v
docker compose exec mcp-api pytest -m "integration and not slow" -v
```

## Writing New Tests

### Unit Test Template

```python
"""Unit tests for [component]."""
import pytest
from unittest.mock import Mock, patch

class TestComponentName:
    """Test [component] functionality."""

    def test_basic_operation(self):
        """Test [what it does]."""
        # Arrange
        # Act
        # Assert
        pass

    def test_edge_case(self):
        """Test [edge case description]."""
        pass
```

### Integration Test Template

```python
"""Integration tests for [feature]."""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

class TestFeatureName:
    """Test [feature] with real dependencies."""

    @pytest.mark.asyncio
    async def test_with_scanner(self, scanner):
        """Test [operation] with real scanner."""
        await scanner._authenticate()
        # Test code here

    @pytest.mark.asyncio
    async def test_with_redis(self, redis_client):
        """Test [operation] with real Redis."""
        redis_client.set("test_key", "value")
        # Test code here
```

## Coverage

```bash
# Generate coverage report
pytest tests/unit/ --cov=core --cov=schema --cov=tools --cov-report=html

# View report
open htmlcov/index.html
```

## Troubleshooting

### Tests can't connect to MCP server

**Symptom**: `Connection refused` or `400 Bad Request`

**Solution**: Use correct URL for environment:
- Inside Docker: `http://mcp-api:8000/mcp`
- From host: `http://localhost:8836/mcp`

### Scanner fixture not found

**Symptom**: `fixture 'scanner' not found`

**Solution**: Ensure `conftest.py` exists in `tests/integration/` with scanner fixture defined.

### Tests timeout waiting for scan

**Symptom**: `TimeoutError: Scan did not complete in Xs`

**Solution**:
1. Check Nessus scanner is running: `curl -k https://172.30.0.3:8834/server/status`
2. Increase timeout in test
3. Use smoke test instead of E2E for quick validation

### Import errors

**Symptom**: `ModuleNotFoundError`

**Solution**: Tests run inside Docker container where paths are set:

```bash
docker compose exec mcp-api pytest tests/...
```

## See Also

- [fixtures/README.MD](fixtures/README.MD) - Sample data files
- [client/README.MD](client/README.MD) - Test client utilities
- [unit/README.MD](unit/README.MD) - Unit test documentation
- [integration/README.MD](integration/README.MD) - Integration test documentation
