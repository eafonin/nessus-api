# Nessus MCP Server - Test Suite

> Layered test architecture for reliable MCP server development

---

## Quick Start

```bash
# Run all core tests (~20 seconds)
docker compose exec mcp-api pytest tests/unit/ tests/integration/test_phase0.py \
  tests/integration/test_phase2.py tests/integration/test_fastmcp_client_smoke.py -q

# Run quick test pipeline
docker compose exec mcp-api tests/run_test_pipeline.sh --quick

# Run full test pipeline (includes scanner tests)
docker compose exec mcp-api tests/run_test_pipeline.sh

# Run E2E tests (5-10 minutes, requires active scan)
docker compose exec mcp-api tests/run_test_pipeline.sh --full
```

---

## Test Layers

The test suite is organized into progressive layers, each building on the previous:

```text
Layer 4: E2E Tests              [5-10 min]  Full scan workflow
    ↑
Layer 3: Integration Tests      [1-3 min]   Scanner + MCP client
    ↑
Layer 2: Infrastructure Tests   [~5 sec]    Queue, tasks, idempotency
    ↑
Layer 1: Unit Tests             [<1 sec]    Isolated components
```

### Layer 1: Unit Tests

**Location**: `tests/unit/`

**Purpose**: Fast, isolated tests for individual components with no external dependencies.

| File | Tests | Description |
|------|-------|-------------|
| `test_logging_config.py` | 9 | Structured logging (structlog) |
| `test_metrics.py` | 23 | Prometheus metrics |
| `test_health.py` | 17 | Health check endpoints |

**Run**:
```bash
docker compose exec mcp-api pytest tests/unit/ -v
```

---

### Layer 2: Infrastructure Tests

**Location**: `tests/integration/test_phase0.py`

**Purpose**: Test core queue and task management infrastructure. Requires Redis but not Nessus scanner.

**Components Tested**:
- Redis queue operations (FIFO, DLQ)
- Task storage and retrieval
- Idempotency handling (SHA256 + Redis SETNX)
- Concurrent operations
- MCP client basic connectivity

**Run**:
```bash
docker compose exec mcp-api pytest tests/integration/test_phase0.py -v
```

---

### Layer 3: Integration Tests

#### Scanner Integration (`test_phase1.py`)

**Purpose**: Test Nessus scanner integration via the scanner wrapper.

**Components Tested**:
- X-API-Token dynamic fetching
- Authentication flow
- READ operations (list scans, get status)
- WRITE operations (create, launch, stop, delete)
- Session management

**Run**:
```bash
docker compose exec mcp-api pytest tests/integration/test_phase1.py -v
```

#### Schema/Results Tests (`test_phase2.py`)

**Purpose**: Test result parsing and schema profiles. Uses fixture files, no live scanner needed.

**Components Tested**:
- NessusParser (XML parsing)
- Schema profiles (minimal, brief, full)
- Filtering (severity, CVSS, boolean)
- JSON-NL output format
- Pagination

**Run**:
```bash
docker compose exec mcp-api pytest tests/integration/test_phase2.py -v
```

#### FastMCP Client Smoke Test (`test_fastmcp_client_smoke.py`)

**Purpose**: Quick validation of MCP client connectivity (~20 seconds).

**Components Tested**:
- Connection to MCP server
- Tool discovery (6 tools)
- Scan submission
- Status retrieval
- Queue operations

**Run**:
```bash
docker compose exec mcp-api pytest tests/integration/test_fastmcp_client_smoke.py -v -s
```

---

### Layer 4: E2E Tests

**Location**: `tests/integration/test_fastmcp_client_e2e.py`

**Purpose**: Complete end-to-end workflow validation. Takes 5-10 minutes per test.

**Workflow Tested**:
1. Connect to MCP server
2. Submit scan
3. Monitor progress with callbacks
4. Wait for completion
5. Retrieve results with filtering
6. Validate vulnerability data

**Run**:
```bash
docker compose exec mcp-api pytest tests/integration/test_fastmcp_client_e2e.py -v -s
```

---

## Directory Structure

```text
tests/
├── README.md                    # This file
├── run_test_pipeline.sh         # Automated test runner
├── conftest.py                  # Shared pytest fixtures (root)
│
├── unit/                        # Layer 1: Unit tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_logging_config.py
│   ├── test_metrics.py
│   └── test_health.py
│
├── integration/                 # Layers 2-4: Integration tests
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures (scanner, redis)
│   ├── test_phase0.py           # Layer 2: Infrastructure
│   ├── test_phase1.py           # Layer 3: Scanner integration
│   ├── test_phase2.py           # Layer 3: Schema/Results
│   ├── test_idempotency.py      # Layer 2: Idempotency system
│   ├── test_queue.py            # Layer 2: Redis queue
│   ├── test_fastmcp_client.py           # Layer 3: MCP client
│   ├── test_fastmcp_client_smoke.py     # Layer 3: Quick smoke test
│   └── test_fastmcp_client_e2e.py       # Layer 4: Full E2E
│
├── fixtures/                    # Test data
│   └── sample_scan.nessus       # Sample Nessus XML for parsing tests
│
├── client/                      # Client test utilities
│   └── client_smoke.py          # Manual smoke test script
│
└── test_phase0_integration.py   # Legacy Phase 0 tests
```

---

## Shared Fixtures

The `tests/integration/conftest.py` provides shared fixtures for all integration tests:

| Fixture | Type | Description |
|---------|------|-------------|
| `scanner` | `NessusScanner` | Authenticated scanner instance with auto-cleanup |
| `redis_client` | `redis.Redis` | Redis client for queue operations |
| `nessus_config` | `dict` | Nessus connection configuration |
| `redis_config` | `dict` | Redis connection configuration |
| `sample_target` | `str` | Safe test target (127.0.0.1) |
| `sample_scan_name` | `str` | Standard test scan name |

### Custom Pytest Markers

```python
@pytest.mark.phase0      # Phase 0 tests (task management)
@pytest.mark.phase1      # Phase 1 tests (scanner integration)
@pytest.mark.phase2      # Phase 2 tests (schema/results)
@pytest.mark.phase3      # Phase 3 tests (observability)
@pytest.mark.integration # All integration tests
@pytest.mark.slow        # Long-running tests
```

**Run by marker**:
```bash
docker compose exec mcp-api pytest -m phase1 -v
docker compose exec mcp-api pytest -m "integration and not slow" -v
```

---

## Test Pipeline

The `run_test_pipeline.sh` script orchestrates running tests in the correct order:

### Usage

```bash
# Standard run (unit + integration, skips E2E)
./tests/run_test_pipeline.sh

# Quick run (skips scanner tests)
./tests/run_test_pipeline.sh --quick

# Full run (includes E2E tests, 5-10 minutes)
./tests/run_test_pipeline.sh --full
```

### Pipeline Phases

| Phase | Tests | Time | Description |
|-------|-------|------|-------------|
| 1 | Unit tests | ~1s | Logging, metrics, health |
| 2 | Infrastructure | ~5s | Queue, idempotency, Phase 0 |
| 3 | Integration | ~2m | Scanner, schema, MCP client |
| 4 | E2E (optional) | ~10m | Full scan workflow |

---

## Environment Variables

Tests use these environment variables (with defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `NESSUS_URL` | `https://172.32.0.209:8834` | Nessus scanner URL |
| `NESSUS_USERNAME` | `admin` | Scanner username |
| `NESSUS_PASSWORD` | `Adm1n@Nessus!` | Scanner password |
| `REDIS_HOST` | `redis` | Redis host (Docker service name) |
| `REDIS_PORT` | `6379` | Redis port |
| `MCP_SERVER_URL` | `http://mcp-api:8000/mcp` | MCP server URL (inside Docker) |
| `TEST_TARGET` | `172.32.0.215` | Default scan target |

---

## Test Targets

> **Important**: Due to Nessus license IP limitations, only use the approved targets below for test scans.

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

### Usage Examples

```python
# Untrusted scan (no credentials)
await client.submit_scan(
    targets="172.32.0.215",
    scan_name="Untrusted Scan Test"
)

# Trusted scan with root credentials (172.32.0.215)
await client.submit_scan(
    targets="172.32.0.215",
    scan_name="Trusted Scan Test",
    scan_type="trusted",
    credentials={
        "ssh_username": "randy",
        "ssh_password": "randylovesgoldfish1998"
    }
)

# Privileged scan on Docker host (172.32.0.209)
await client.submit_scan(
    targets="172.32.0.209",
    scan_name="Privileged Scan Test",
    scan_type="privileged",
    credentials={
        "ssh_username": "nessus",
        "ssh_password": "nessus",
        "escalation_method": "sudo"
    }
)

# Privileged scan with sudo NOPASSWD (no escalation_password needed)
await client.submit_scan(
    targets="172.32.0.209",
    scan_name="Privileged Scan NOPASSWD",
    scan_type="authenticated_privileged",
    credentials={
        "ssh_username": "testauth_sudo_nopass",
        "ssh_password": "TestPass123!",
        "elevate_privileges_with": "sudo"
    }
)

# Authenticated scan (non-privileged, Plugin 110385 expected)
await client.submit_scan(
    targets="172.32.0.209",
    scan_name="Authenticated Scan (no sudo)",
    scan_type="authenticated",
    credentials={
        "ssh_username": "testauth_nosudo",
        "ssh_password": "TestPass123!"
    }
)
```

### IP Limits

The Nessus license has a limited IP count. To avoid exhausting the limit:
- **DO NOT** scan random IPs or large subnets
- **DO NOT** add new targets without approval
- **ALWAYS** use the two approved targets above
- For network discovery tests, use `/32` (single host) scans only

---

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

---

## Troubleshooting

### Tests can't connect to MCP server

**Symptom**: `Connection refused` or `400 Bad Request`

**Solution**: Ensure you're using the correct URL for the environment:
- Inside Docker: `http://mcp-api:8000/mcp`
- From host: `http://localhost:8835/mcp` (or mapped port)

### Scanner fixture not found

**Symptom**: `fixture 'scanner' not found`

**Solution**: Ensure `conftest.py` exists in `tests/integration/` with the scanner fixture defined.

### Tests timeout waiting for scan

**Symptom**: `TimeoutError: Scan did not complete in Xs`

**Solution**:
1. Check Nessus scanner is running: `curl -k https://172.32.0.209:8834/server/status`
2. Increase timeout in test
3. Use smoke test instead of E2E for quick validation

### Import errors

**Symptom**: `ModuleNotFoundError`

**Solution**: Tests run inside Docker container where paths are set. Run via:
```bash
docker compose exec mcp-api pytest tests/...
```

---

## Test Status

| Layer | Tests | Status | Notes |
|-------|-------|--------|-------|
| Unit | 49 | All passing | Fast, no dependencies |
| Phase 0 | 28 | All passing | Redis required |
| Phase 1 | 16 | Most passing | Scanner required |
| Phase 2 | 25 | All passing | Uses fixtures |
| FastMCP Smoke | 1 | Passing | Quick validation |
| E2E | 2 | Available | 5-10 min runtime |

**Total**: 103+ tests covering all layers

---

## See Also

- [Architecture v2.2](../docs/ARCHITECTURE_v2.2.md) - System design and components
- [FastMCP Client](../client/nessus_fastmcp_client.py) - Production MCP client
- [Phase 3: Observability](../phases/PHASE_3_OBSERVABILITY.md) - Testing phase requirements
- [Docker Network Config](../docs/DOCKER_NETWORK_CONFIG.md) - Network topology

---

**Last Updated**: 2025-11-25
