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

## Test Environment

Tests run against the **dev1** environment (`/home/nessus/projects/nessus-api/dev1/`).

```bash
# Start dev1 environment (required for Layer 03/04 tests)
cd /home/nessus/projects/nessus-api/dev1
docker compose up -d

# Verify services are running
docker compose ps
```

**Services provided by dev1:**
| Service | Container | Purpose |
|---------|-----------|---------|
| `redis` | nessus-mcp-redis-dev | Task queue |
| `mcp-api` | nessus-mcp-api-dev | MCP server (port 8836) |
| `scanner-worker` | nessus-mcp-worker-dev | Scan processor |
| `scan-target` | scan-target | SSH test target (172.30.0.9) |
| `autoheal` | autoheal-mcp-dev | Auto-restart unhealthy containers |

---

## Quick Start

```bash
cd /home/nessus/projects/nessus-api/mcp-server

# Layer 01-02: Run locally (no Docker needed)
pytest tests/layer01_infrastructure/ -v          # Infrastructure
pytest tests/layer02_internal/ -v                # Internal

# Layer 03-04: Run inside mcp-api container (requires dev1 environment)
cd /home/nessus/projects/nessus-api/dev1
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
├── README.MD                        # This file
├── TEST_DOCUMENTATION_GUIDE.md      # Format guide for test docs
├── conftest.py                      # Root pytest config, markers
├── reconcile_tests.py               # Documentation reconciliation script
│
├── layer01_infrastructure/          # Connectivity checks [<1s]
│   ├── README.MD                    # Layer overview
│   ├── TESTS.md                     # Test catalog (23 tests)
│   ├── test_nessus_connectivity.py
│   ├── test_redis_connectivity.py
│   ├── test_target_accounts.py
│   └── test_both_scanners.py
│
├── layer02_internal/                # Core modules [~30s]
│   ├── README.MD
│   ├── TESTS.md                     # Test catalog (343 tests)
│   ├── test_task_manager.py
│   ├── test_queue.py
│   ├── test_pool_registry.py
│   └── ... (16 files)
│
├── layer03_external_basic/          # Single tool calls [~1min]
│   ├── README.MD
│   ├── TESTS.md                     # Test catalog (79 tests)
│   ├── test_mcp_tools_basic.py
│   ├── test_scanner_operations.py
│   └── ... (5 files)
│
├── layer04_full_workflow/           # E2E workflows [5-10min]
│   ├── README.MD
│   ├── TESTS.md                     # Test catalog (42 tests)
│   ├── test_untrusted_scan_workflow.py
│   ├── test_authenticated_scan_workflow.py
│   └── ... (5 files)
│
├── fixtures/                        # Sample data for tests
│   └── sample_scan.nessus
│
└── client/                          # Test utilities
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

These are set automatically by the dev1 docker-compose.yml:

| Variable | Default (dev1) | Description |
|----------|----------------|-------------|
| `NESSUS_URL` | `https://nessus-pro-1:8834` | Nessus scanner URL |
| `NESSUS_USERNAME` | `nessus` | Scanner login |
| `NESSUS_PASSWORD` | `nessus` | Scanner password |
| `REDIS_URL` | `redis://redis:6379` | Redis URL |
| `MCP_SERVER_URL` | `http://mcp-api:8000/mcp` | MCP endpoint |
| `SCAN_TARGET_IP` | `172.30.0.9` | Test target (scan-target container) |

---

## Troubleshooting

### Layer 01 failures

```bash
cd /home/nessus/projects/nessus-api/dev1
docker compose ps                              # All containers running?
docker compose exec mcp-api ping redis         # Network connectivity
curl -k https://nessus-pro-1:8834/server/status  # Nessus reachable
```

### Layer 02 failures

- Run locally: `pytest tests/layer02_internal/ -v`
- No external dependencies, issue is in code

### Layer 03 failures

```bash
cd /home/nessus/projects/nessus-api/dev1
docker compose exec mcp-api pytest tests/layer03_external_basic/ -v -s
docker compose logs mcp-api                    # Check MCP server logs
```

### Layer 04 failures

- First verify layers 01-03 pass
- Check scanner capacity: `mcp__nessus-mcp__list_scanners`
- Increase timeout if scans are slow

---

## Test Documentation

Test documentation is split by layer for modularity and context-efficiency. Each layer directory contains:

- **README.MD** - Layer overview, purpose, troubleshooting
- **TESTS.md** - Test catalog with arguments, returns, pass criteria

### Documentation Files

| File | Purpose | Tests |
|------|---------|-------|
| [layer01_infrastructure/TESTS.md](layer01_infrastructure/TESTS.md) | Infrastructure tests | 23 |
| [layer02_internal/TESTS.md](layer02_internal/TESTS.md) | Unit tests with mocks | 343 |
| [layer03_external_basic/TESTS.md](layer03_external_basic/TESTS.md) | Integration tests | 79 |
| [layer04_full_workflow/TESTS.md](layer04_full_workflow/TESTS.md) | E2E workflow tests | 42 |
| [TEST_DOCUMENTATION_GUIDE.md](TEST_DOCUMENTATION_GUIDE.md) | Format guide for creating new layers | - |

### Documentation Format

Each `TESTS.md` uses this table format:

```markdown
| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_function_name` | `param=value` | `expected: type` | What is tested. Pass: condition. |
```

### Agent-Optimized Lookup (Grep Patterns)

Test docs are structured for grep-based lookup. **Do NOT load full files into context unless required**

```bash
# Find test by name across all layers
grep -r "test_scanner_reachable" tests/*/TESTS.md

# Find DLQ-related tests
grep -ri "DLQ" tests/*/TESTS.md

# Find authentication tests
grep -ri "auth\|credential\|ssh" tests/*/TESTS.md

# Find error-handling tests
grep -r "raises.*Error\|ValueError" tests/*/TESTS.md
```

### Generating Test Run Reports

After running tests, generate a consolidated report using the **same format as TESTS.md** plus status/duration/error:

```bash
# Run tests with JSON output
pytest tests/ --json-report --json-report-file=test_results.json

# Generate markdown report (see TEST_DOCUMENTATION_GUIDE.md for script)
python tests/generate_test_report.py test_results.json
```

This creates `TEST_RUN_REPORT.md` with:
- **Single flat table** - All tests, grep-friendly
- **Same columns as TESTS.md** - Test, File, Arguments, Returns, Description
- **Plus runtime columns** - Status, Duration, Error
- **Full file paths** - `layer02_internal/test_queue.py` for layer extraction

```bash
# Find test and extract layer from report
grep "test_opens_after_threshold" tests/TEST_RUN_REPORT.md | grep -oE "layer[0-9]+_[a-z_]+"
# Output: layer02_internal

# Find all failed tests
grep "| failed |" tests/TEST_RUN_REPORT.md

# Find source file for test
grep "test_circuit_breaker" tests/TEST_RUN_REPORT.md | cut -d'|' -f3
```

### Reconciliation Script

Use `reconcile_tests.py` to verify documentation completeness:

```bash
python3 tests/reconcile_tests.py           # Full detailed report
python3 tests/reconcile_tests.py --summary # Summary statistics
python3 tests/reconcile_tests.py --stubs   # Generate stub entries for missing tests
```

### Quick Reference: Test File → Layer Mapping

| Layer | Test Files | Tests |
|-------|------------|-------|
| 01 | `test_nessus_connectivity`, `test_redis_connectivity`, `test_both_scanners`, `test_target_accounts` | 23 |
| 02 | `test_admin_cli`, `test_authenticated_scans`, `test_circuit_breaker`, `test_error_responses`, `test_health`, `test_housekeeping`, `test_idempotency`, `test_ip_utils`, `test_list_tasks`, `test_logging_config`, `test_metrics`, `test_nessus_validator`, `test_pool_registry`, `test_queue`, `test_queue_status`, `test_task_manager` | 343 |
| 03 | `test_mcp_tools_basic`, `test_pool_operations`, `test_pool_selection`, `test_scanner_operations`, `test_schema_parsing` | 79 |
| 04 | `test_authenticated_scan_workflow`, `test_complete_scan_with_results`, `test_mcp_protocol_e2e`, `test_queue_position_accuracy`, `test_untrusted_scan_workflow` | 42 |

---

## See Also

- [TEST_DOCUMENTATION_GUIDE.md](TEST_DOCUMENTATION_GUIDE.md) - Format guide for test documentation
- [Testing Guide](../docs/TESTING.md) - Detailed testing documentation
- [FEATURES.md](../docs/FEATURES.md) - MCP tools being tested
