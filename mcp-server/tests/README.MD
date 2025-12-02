# Test Suite

[← MCP Server](../README.MD) | [Testing Guide](../docs/TESTING.md)

---

## Overview

The test suite uses a 4-layer architecture designed for systematic troubleshooting. Each layer builds on the previous: if layer01 passes but layer03 fails, the issue is in external integration, not infrastructure.

```text
Layer 04: Full Workflow      [5-10 min]  Complete scan → results E2E
    ↑ depends on
Layer 03: External Basic     [~1 min]    Single MCP tool calls
    ↑ depends on
Layer 02: Internal           [~30 sec]   Core modules (mocked deps)
    ↑ depends on
Layer 01: Infrastructure     [<1 sec]    Connectivity & access
```

---

## Quick Start

```bash
cd /home/nessus/projects/nessus-api/mcp-server

# Run layer by layer (recommended troubleshooting approach)
pytest tests/layer01_infrastructure/ -v          # Infrastructure
pytest tests/layer02_internal/ -v                # Internal
docker compose exec mcp-api pytest tests/layer03_external_basic/ -v   # External
docker compose exec mcp-api pytest tests/layer04_full_workflow/ -v -s # Full E2E

# Run by marker
pytest -m layer01                    # Single layer
pytest -m "layer01 or layer02"       # Multiple layers
pytest -m "not layer04"              # Skip slow tests
```

---

## Directory Structure

```text
tests/
├── README.MD                   # This file
├── conftest.py                 # Root pytest config, markers
├── TEST_REFACTOR_PLAN.md       # Migration plan (temporary)
│
├── layer01_infrastructure/     # Connectivity checks [<1s]
│   ├── README.MD
│   ├── test_nessus_connectivity.py
│   ├── test_redis_connectivity.py
│   ├── test_target_accounts.py
│   └── test_both_scanners.py
│
├── layer02_internal/           # Core modules [~30s]
│   ├── README.MD
│   ├── test_task_manager.py
│   ├── test_queue.py
│   ├── test_pool_registry.py
│   └── ... (12 files)
│
├── layer03_external_basic/     # Single tool calls [~1min]
│   ├── README.MD
│   ├── test_mcp_tools_basic.py
│   ├── test_scanner_operations.py
│   └── ... (5 files)
│
├── layer04_full_workflow/      # E2E workflows [5-10min]
│   ├── README.MD
│   ├── test_untrusted_scan_workflow.py
│   ├── test_authenticated_scan_workflow.py
│   └── ... (5 files)
│
├── fixtures/                   # Sample data for tests
│   └── sample_scan.nessus
│
└── client/                     # Test utilities
    └── nessus_fastmcp_client.py
```

---

## Test Layers

### Layer 01: Infrastructure

**Purpose**: Verify all services are accessible before running any other tests.

| Test | What it checks |
|------|----------------|
| `test_nessus_connectivity.py` | Nessus WebUI reachable, SSL, auth endpoints |
| `test_redis_connectivity.py` | Redis server up, basic operations |
| `test_target_accounts.py` | SSH test accounts on scan targets |
| `test_both_scanners.py` | Both scanner instances responding |

**Markers**: `@pytest.mark.layer01`

**If these fail**: Check Docker containers are running, network connectivity.

### Layer 02: Internal

**Purpose**: Test core modules in isolation using mocks. No external services needed.

| Test | Module tested |
|------|---------------|
| `test_task_manager.py` | `core/task_manager.py` - state machine |
| `test_queue.py` | `core/queue.py` - FIFO, DLQ |
| `test_pool_registry.py` | `scanners/registry.py` - pool management |
| `test_circuit_breaker.py` | `core/circuit_breaker.py` |
| `test_health.py` | `core/health.py` |
| `test_housekeeping.py` | `core/housekeeping.py` |
| `test_metrics.py` | `core/metrics.py` |
| `test_logging_config.py` | `core/logging_config.py` |
| `test_ip_utils.py` | `core/ip_utils.py` |
| `test_nessus_validator.py` | `scanners/nessus_validator.py` |
| `test_admin_cli.py` | `tools/admin_cli.py` |
| `test_idempotency.py` | Idempotency key handling |

**Markers**: `@pytest.mark.layer02`

**If these fail**: Bug in core logic, check recent code changes.

### Layer 03: External Basic

**Purpose**: Test single MCP tool calls and scanner operations with real services.

| Test | What it validates |
|------|-------------------|
| `test_mcp_tools_basic.py` | MCP connection, tool listing, basic calls |
| `test_scanner_operations.py` | Nessus API: create/launch/delete |
| `test_pool_selection.py` | Pool-based scanner selection |
| `test_schema_parsing.py` | XML parser, schema profiles, filters |
| `test_authenticated_credentials.py` | SSH credential injection |

**Markers**: `@pytest.mark.layer03`, `@pytest.mark.requires_nessus`, `@pytest.mark.requires_mcp`

**If these fail**: Issue with specific integration point (Nessus API, MCP protocol).

### Layer 04: Full Workflow

**Purpose**: Complete E2E workflows. Runs real scans (5-10 minutes each).

| Test | Workflow tested |
|------|-----------------|
| `test_untrusted_scan_workflow.py` | Submit → wait → results |
| `test_authenticated_scan_workflow.py` | SSH auth scan with credential validation |
| `test_mcp_protocol_e2e.py` | Full MCP protocol stack |
| `test_result_filtering_workflow.py` | Scan with severity/CVSS filters |
| `test_pool_workflow.py` | Multi-scanner pool distribution |

**Markers**: `@pytest.mark.layer04`, `@pytest.mark.slow`, `@pytest.mark.e2e`

**If these fail**: Check lower layers first. If layer01-03 pass, issue is workflow-specific.

---

## Pytest Markers

| Marker | Purpose |
|--------|---------|
| `layer01` | Infrastructure tests |
| `layer02` | Internal module tests |
| `layer03` | External basic tests |
| `layer04` | Full E2E workflows |
| `requires_nessus` | Needs Nessus scanner |
| `requires_redis` | Needs Redis |
| `requires_mcp` | Needs MCP server |
| `slow` | Takes > 1 minute |
| `e2e` | End-to-end test |
| `authenticated` | Uses SSH credentials |

---

## Test Targets

> **IP Limit Warning**: Nessus license has limited IP count. Only use approved targets.

| IP | Host | Credentials | Notes |
|----|------|-------------|-------|
| `172.32.0.215` | External host | `randy` / `randylovesgoldfish1998` | Primary target |
| `172.30.0.9` | scan-target container | See below | Privileged scan tests |

### Privileged Scan Test Users (172.30.0.9)

| Username | Password | Sudo | Purpose |
|----------|----------|------|---------|
| `testauth_sudo_pass` | `TestPass123!` | with password | Test escalation_password |
| `testauth_sudo_nopass` | `TestPass123!` | NOPASSWD | Test passwordless sudo |
| `testauth_nosudo` | `TestPass123!` | none | Test unprivileged auth |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NESSUS_URL` | `https://vpn-gateway:8834` | Nessus scanner URL |
| `NESSUS_USERNAME` | `nessus` | Scanner login |
| `NESSUS_PASSWORD` | `nessus` | Scanner password |
| `REDIS_URL` | `redis://redis:6379` | Redis URL |
| `MCP_SERVER_URL` | `http://mcp-api:8000/mcp` | MCP endpoint |
| `SCAN_TARGET_IP` | `172.30.0.9` | Test target |

---

## Troubleshooting

### Layer 01 failures

- Check `docker compose ps` - all containers running?
- Check network: `docker compose exec mcp-api ping redis`
- Check Nessus: `curl -k https://vpn-gateway:8834/server/status`

### Layer 02 failures

- Run locally: `pytest tests/layer02_internal/ -v`
- No external dependencies, issue is in code

### Layer 03 failures

- Run from Docker: `docker compose exec mcp-api pytest tests/layer03_external_basic/ -v -s`
- Check MCP server logs: `docker compose logs mcp-api`

### Layer 04 failures

- First verify layers 01-03 pass
- Check scanner capacity: `mcp__nessus-mcp__list_scanners`
- Increase timeout if scans are slow

---

## See Also

- [Testing Guide](../docs/TESTING.md) - Detailed testing documentation
- [FEATURES.md](../docs/FEATURES.md) - MCP tools being tested
- [TEST_REFACTOR_PLAN.md](TEST_REFACTOR_PLAN.md) - Migration plan
