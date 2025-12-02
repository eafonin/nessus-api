# Layer 04: Full Workflow Tests

[← Test Suite](../README.MD)

---

## Purpose

Complete E2E workflows that run real vulnerability scans. These tests validate the entire stack from scan submission through result retrieval.

**Duration**: 5-10 minutes per test
**Markers**: `@pytest.mark.layer04`, `@pytest.mark.slow`, `@pytest.mark.e2e`

---

## Tests

| Test File | Workflow Tested |
|-----------|-----------------|
| `test_untrusted_scan_workflow.py` | Submit untrusted scan → wait for completion → retrieve results |
| `test_authenticated_scan_workflow.py` | SSH authenticated scan with credential validation |
| `test_mcp_protocol_e2e.py` | Full MCP protocol stack (SSE transport, JSON-RPC) |
| `test_result_filtering_workflow.py` | Scan with severity/CVSS filtering on results |
| `test_pool_workflow.py` | Multi-scanner pool load distribution E2E |

---

## Running

```bash
# Run all layer04 tests (5-10+ minutes)
docker compose exec mcp-api pytest tests/layer04_full_workflow/ -v -s

# Run by marker
docker compose exec mcp-api pytest -m layer04 -v -s

# Run single workflow
docker compose exec mcp-api pytest tests/layer04_full_workflow/test_untrusted_scan_workflow.py -v -s

# Skip slow tests (runs layer01-03 only)
pytest -m "not layer04" -v
```

---

## Prerequisites

**IMPORTANT**: Always verify lower layers pass before running layer04:

```bash
# Run layers 01-03 first
pytest tests/layer01_infrastructure/ -v
pytest tests/layer02_internal/ -v
docker compose exec mcp-api pytest tests/layer03_external_basic/ -v
```

Layer04 requires:
- All lower layers passing
- Nessus scanner with available capacity
- Scan targets accessible
- Sufficient timeout (default 600s)

---

## If Tests Fail

### First Steps

1. **Check lower layers**: If layer01-03 pass, issue is workflow-specific
2. **Check scanner capacity**: `mcp__nessus-mcp__list_scanners`
3. **Check queue depth**: `mcp__nessus-mcp__get_queue_status`

### Workflow-Specific Issues

#### Untrusted scan workflow

- Verify target reachable: `ping 172.32.0.215`
- Check Nessus scan created: Look at Nessus WebUI
- Check worker logs: `docker compose logs worker`

#### Authenticated scan workflow

- Test SSH credentials manually
- Verify Plugin 141118 (Valid Credentials) in results
- Check credential injection in scan config

#### MCP protocol E2E

- Check MCP server logs
- Verify SSE connection maintained
- Check for timeout issues

#### Result filtering workflow

- Ensure scan has vulnerabilities to filter
- Check filter syntax in test
- Verify JSON-NL parsing

#### Pool workflow

- Both scanners must be healthy
- Check pool load balancing logic
- Verify queue distribution

### Timeout Issues

If tests timeout:

```python
# In test file, increase timeout
@pytest.mark.timeout(900)  # 15 minutes
async def test_long_scan():
    ...
```

Or set environment variable:
```bash
SCAN_TIMEOUT=900 docker compose exec mcp-api pytest ...
```

---

## Test Targets

| IP | Use Case | Duration |
|----|----------|----------|
| `172.32.0.215` | Primary target, has vulnerabilities | ~5 min |
| `172.30.0.9` | Authenticated scans (scan-target container) | ~5 min |
| `127.0.0.1` | Quick smoke test | ~1 min |

---

## Dependencies

- All lower layer tests passing
- Docker environment fully running
- Nessus scanner(s) with capacity
- 10+ minutes of available time
- Scan targets accessible

---

## See Also

- [Layer 03: External Basic](../layer03_external_basic/README.MD)
- [Testing Guide](../../docs/TESTING.md)
- [FEATURES.md](../../docs/FEATURES.md) - MCP tools being tested
