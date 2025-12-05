# Layer 03: External Basic Tests

[← Test Suite](../README.MD)

---

## Purpose

Test single MCP tool calls and scanner operations with real services. Each test validates one specific integration point without running full workflows.

**Duration**: ~1 minute
**Markers**: `@pytest.mark.layer03`, `@pytest.mark.requires_nessus`, `@pytest.mark.requires_mcp`

---

## Tests

| Test File | What it validates |
|-----------|-------------------|
| `test_mcp_tools_basic.py` | MCP connection, tool listing, single tool calls |
| `test_scanner_operations.py` | Nessus API: create scan, launch, delete |
| `test_pool_selection.py` | Pool-based scanner selection, load balancing |
| `test_pool_operations.py` | Pool listing and status operations |
| `test_schema_parsing.py` | XML parser, schema profiles (minimal/brief/full), filters |

---

## Running

```bash
# Run all layer03 tests (requires Docker)
docker compose exec mcp-api pytest tests/layer03_external_basic/ -v -s

# Run by marker
docker compose exec mcp-api pytest -m layer03 -v

# Run single test
docker compose exec mcp-api pytest tests/layer03_external_basic/test_mcp_tools_basic.py -v -s
```

---

## Prerequisites

Before running layer03 tests, verify layer01 passes:

```bash
pytest tests/layer01_infrastructure/ -v
```

Layer03 requires:
- Nessus scanner(s) accessible
- Redis running
- MCP server running

---

## If Tests Fail

### MCP tools basic fails

1. Check MCP server running: `docker compose logs mcp-api`
2. Verify endpoint: `curl http://localhost:8836/mcp`
3. Check FastMCP version compatibility

### Scanner operations fails

1. Verify layer01 connectivity tests pass
2. Check Nessus API directly: `curl -k https://vpn-gateway:8834/server/status`
3. Look for rate limiting or license issues

### Pool selection fails

1. Check scanner pool config: `config/scanners.yaml`
2. Verify both scanners healthy
3. Check Redis for stale pool data

### Schema parsing fails

1. Ensure test fixtures exist: `tests/fixtures/sample_scan.nessus`
2. Check for XML parser changes
3. Verify schema profile definitions

### Authenticated credentials fails

1. Test SSH manually to scan target
2. Verify credential payload format
3. Check Nessus API credential injection

---

## Dependencies

- Docker environment running
- Layer01 infrastructure tests passing
- Nessus scanner accessible
- MCP server running

---

## See Also

- [Layer 02: Internal](../layer02_internal/README.MD)
- [Layer 04: Full Workflow](../layer04_full_workflow/README.MD)
