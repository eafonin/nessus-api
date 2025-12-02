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
├── TEST_REPORT.md              # Test documentation (grep-optimized)
├── reconcile_tests.py          # Documentation reconciliation script
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

## Test Documentation (TEST_REPORT.md)

The [TEST_REPORT.md](TEST_REPORT.md) file contains detailed documentation for all 487 tests:
- Test arguments (actual parameter values)
- Expected return values
- Pass/fail criteria descriptions

### Documentation Format (Mandatory)

All tests **must** be documented in TEST_REPORT.md using this format:

```markdown
### test_file_name.py (N tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_function_name` | `layer0X_dir/test_file.py` | `param=value` | `expected: type` | What is tested. Pass: condition. |
```

**File column**: Each test row includes the relative path from `tests/` directory for grep-friendly lookup.

**Update requirement**: TEST_REPORT.md must be updated when tests are added, modified, or removed.

### Reconciliation Script

Use `reconcile_tests.py` to verify documentation completeness:

```bash
python3 tests/reconcile_tests.py           # Full detailed report
python3 tests/reconcile_tests.py --summary # Summary statistics
python3 tests/reconcile_tests.py --fix     # Show corrected header counts
python3 tests/reconcile_tests.py --stubs   # Generate stub entries for missing tests
```

### Agent-Optimized Lookup (Grep Patterns)

TEST_REPORT.md is structured for grep-based lookup. **Do NOT load the full file into context.**

Each table row contains: `| Test | File | Arguments | Returns | Description |`

#### Search by Test Name (Most Common)

```bash
# Find test by name - returns file path, args, returns, description
grep "test_scanner_reachable" tests/TEST_REPORT.md
# Output: | `test_scanner_reachable` | `layer01_infrastructure/test_both_scanners.py` | `url` param | `status_code: 200` | ... |
```

#### Search by File Name

```bash
# Find all tests in a specific file
grep "test_queue.py" tests/TEST_REPORT.md

# Find tests in a layer directory
grep "layer03_external_basic" tests/TEST_REPORT.md
```

#### Search by Functionality

```bash
# Find DLQ-related tests
grep -i "DLQ" tests/TEST_REPORT.md

# Find authentication tests
grep -i "auth\|credential\|ssh" tests/TEST_REPORT.md

# Find error-handling tests
grep "raises.*Error\|ValueError\|Exception" tests/TEST_REPORT.md
```

#### Layer Information

```bash
# Which layer is a test in? (extract from file path)
grep "test_initial_state_closed" tests/TEST_REPORT.md | grep -oE "layer[0-9]+_[a-z_]+"
# Output: layer02_internal

# List all layers with test counts
grep "^## Layer" tests/TEST_REPORT.md
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

- [TEST_REPORT.md](TEST_REPORT.md) - Detailed test documentation (grep, don't load)
- [Testing Guide](../docs/TESTING.md) - Detailed testing documentation
- [FEATURES.md](../docs/FEATURES.md) - MCP tools being tested
- [TEST_REFACTOR_PLAN.md](TEST_REFACTOR_PLAN.md) - Migration plan
