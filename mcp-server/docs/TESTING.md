# Testing Guide

[← README](README.MD) | [Architecture →](ARCHITECTURE.md)

---

## Overview

The test suite is organized into 4 layers, from basic infrastructure checks to full E2E workflows. This layered approach enables systematic troubleshooting: if layer01 passes but layer03 fails, the issue is in external integration, not infrastructure.

### Test Layers

| Layer | Directory | Duration | Purpose |
|-------|-----------|----------|---------|
| **Layer 01** | `layer01_infrastructure/` | <1s | WebUI accessible, Redis up, target accounts working |
| **Layer 02** | `layer02_internal/` | ~30s | Queue, task manager, config parsing, validators |
| **Layer 03** | `layer03_external_basic/` | ~1min | Single MCP tool calls, scanner operations |
| **Layer 04** | `layer04_full_workflow/` | 5-10min | Complete scan→results E2E workflows |

---

## Quick Start

### Run All Tests by Layer

```bash
cd /home/nessus/projects/nessus-api/mcp-server

# Layer 01: Quick infrastructure validation
pytest tests/layer01_infrastructure/ -v

# Layer 02: Internal functionality (no external services)
pytest tests/layer02_internal/ -v

# Layer 03: External basic (requires Nessus, Redis, MCP)
docker compose exec mcp-api pytest tests/layer03_external_basic/ -v -s

# Layer 04: Full E2E workflows (5-10 min)
docker compose exec mcp-api pytest tests/layer04_full_workflow/ -v -s
```

### Run Tests by Marker

```bash
# Run specific layer
pytest -m layer01

# Run layers 01 and 02 only (quick validation)
pytest -m "layer01 or layer02"

# Skip slow E2E tests
pytest -m "not layer04"

# Run tests requiring real Nessus scanner
pytest -m requires_nessus
```

---

## Test Categories

### Layer 01: Infrastructure Tests

Basic connectivity and access validation. These tests should pass before running any other layer.

| Test File | Purpose |
|-----------|---------|
| `test_nessus_connectivity.py` | Nessus WebUI reachable, SSL works, endpoints respond |
| `test_redis_connectivity.py` | Redis server accessible, basic operations work |
| `test_target_accounts.py` | SSH test accounts accessible on scan targets |
| `test_both_scanners.py` | Both scanner instances responding |

**Markers**: `@pytest.mark.layer01`

### Layer 02: Internal Tests

Core functionality that doesn't require external services (uses mocks).

| Test File | Purpose |
|-----------|---------|
| `test_task_manager.py` | State machine transitions, task persistence |
| `test_queue.py` | FIFO operations, DLQ handling |
| `test_pool_registry.py` | Scanner pool management, load balancing |
| `test_circuit_breaker.py` | Scanner health detection |
| `test_health.py` | Health endpoint responses |
| `test_housekeeping.py` | Task cleanup, expiration |
| `test_metrics.py` | Prometheus metrics |
| `test_logging_config.py` | Structured logging |
| `test_ip_utils.py` | CIDR parsing, IP validation |
| `test_nessus_validator.py` | Authentication detection from results |
| `test_admin_cli.py` | CLI command parsing |
| `test_idempotency.py` | Idempotency key handling |

**Markers**: `@pytest.mark.layer02`

### Layer 03: External Basic Tests

Single tool calls with real services. Each test validates one specific integration point.

| Test File | Purpose |
|-----------|---------|
| `test_mcp_tools_basic.py` | MCP connection, tool listing, basic calls |
| `test_scanner_operations.py` | Nessus API: create/launch/delete scan |
| `test_pool_selection.py` | Pool-based scanner selection |
| `test_schema_parsing.py` | XML parser, schema profiles, filters |
| `test_authenticated_credentials.py` | Credential injection for SSH scans |

**Markers**: `@pytest.mark.layer03`, `@pytest.mark.requires_nessus`, `@pytest.mark.requires_mcp`

### Layer 04: Full Workflow Tests

Complete E2E workflows that run real scans. These are slow (5-10 minutes each).

| Test File | Purpose |
|-----------|---------|
| `test_untrusted_scan_workflow.py` | Full untrusted scan: submit→wait→results |
| `test_authenticated_scan_workflow.py` | SSH authenticated scan with credential validation |
| `test_mcp_protocol_e2e.py` | Full MCP protocol stack validation |
| `test_result_filtering_workflow.py` | Scan with severity/CVSS filtering |
| `test_pool_workflow.py` | Multi-scanner pool load distribution |

**Markers**: `@pytest.mark.layer04`, `@pytest.mark.slow`, `@pytest.mark.e2e`

---

## Pytest Markers Reference

| Marker | Purpose | Example |
|--------|---------|---------|
| `layer01` | Infrastructure checks | `pytest -m layer01` |
| `layer02` | Internal functionality | `pytest -m layer02` |
| `layer03` | External basic | `pytest -m layer03` |
| `layer04` | Full workflow | `pytest -m layer04` |
| `requires_nessus` | Needs real Nessus scanner | `pytest -m requires_nessus` |
| `requires_redis` | Needs Redis connection | `pytest -m requires_redis` |
| `requires_mcp` | Needs MCP server | `pytest -m requires_mcp` |
| `slow` | Long-running tests (> 1 min) | `pytest -m "not slow"` |
| `e2e` | End-to-end tests | `pytest -m e2e` |
| `authenticated` | Uses SSH credentials | `pytest -m authenticated` |

### Combining Markers

```bash
# Run layer03 tests that don't require MCP
pytest -m "layer03 and not requires_mcp"

# Run all tests except slow ones
pytest -m "not slow"

# Run only authenticated scan tests
pytest -m "authenticated and layer04"
```

---

## Running Tests

### Docker Environment (Recommended)

Most tests require Docker network access to reach Nessus, Redis, and MCP services.

```bash
# Start the stack
cd /home/nessus/projects/nessus-api/dev1
docker compose up -d

# Run tests inside container
docker compose exec mcp-api pytest tests/ -v -s

# Run specific layer
docker compose exec mcp-api pytest tests/layer03_external_basic/ -v -s

# Run with coverage
docker compose exec mcp-api pytest tests/ --cov=. --cov-report=term-missing
```

### Host Machine (Limited)

Only layer02 tests work reliably from the host. Tests requiring Docker network will fail.

```bash
cd /home/nessus/projects/nessus-api/mcp-server
source venv/bin/activate

# Run only internal tests (no external dependencies)
pytest tests/layer02_internal/ -v

# Skip tests requiring Docker network
pytest -m "not requires_nessus and not requires_redis and not requires_mcp"
```

---

## Test Client

The test suite uses `NessusFastMCPClient` for all MCP interactions:

```python
from client.nessus_fastmcp_client import NessusFastMCPClient

async def test_scan_workflow():
    async with NessusFastMCPClient("http://mcp-api:8000/mcp") as client:
        # Submit scan
        task = await client.submit_scan(
            targets="192.168.1.1",
            scan_name="Integration Test"
        )

        # Wait for completion
        final = await client.wait_for_completion(
            task["task_id"],
            timeout=600,
            poll_interval=10
        )

        # Get results
        results = await client.get_results(
            task["task_id"],
            schema_profile="brief"
        )
```

See `tests/client/nessus_fastmcp_client.py` for the full client implementation.

---

## Troubleshooting

### Redis Connection Fails from Host

**Symptom**: `ConnectionError: Connection reset by peer`

**Cause**: Docker's NAT interferes with Redis protocol.

**Solution**: Run tests inside Docker: `docker compose exec mcp-api pytest ...`

### Nessus Scanner Not Accessible

**Symptom**: `httpx.ConnectError: All connection attempts failed`

**Cause**: Nessus is only accessible from Docker network.

**Solution**:
1. Verify Nessus is running: `docker ps | grep nessus`
2. Run tests inside Docker network

### Test Timeout

**Symptom**: Test exceeds timeout (default 600s).

**Cause**: Nessus scan taking longer than expected.

**Solution**:
- Increase timeout in test: `@pytest.mark.timeout(900)`
- Use smaller target range
- Check scanner performance

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection URL |
| `NESSUS_URL` | `https://vpn-gateway:8834` | Nessus scanner URL |
| `NESSUS_USERNAME` | `nessus` | Nessus login |
| `NESSUS_PASSWORD` | `nessus` | Nessus password |
| `MCP_SERVER_URL` | `http://mcp-api:8000/mcp` | MCP server endpoint |
| `SCAN_TARGET_IP` | `172.30.0.9` | Test target IP |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Coverage

Run coverage report:

```bash
docker compose exec mcp-api pytest tests/ \
    --cov=core --cov=scanners --cov=tools --cov=schema \
    --cov-report=term-missing \
    --cov-report=html:coverage_html

# View HTML report
open coverage_html/index.html
```

---

## Related Documentation

- [FEATURES.md](FEATURES.md) - MCP tools being tested
- [API.md](API.md) - API endpoints and responses
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [tests/README.MD](../tests/README.MD) - Test suite overview
