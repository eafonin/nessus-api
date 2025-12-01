<!-- README Navigation -->
<!-- L4: mcp-server/tests/client/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: HTTP client wrapper for MCP server testing -->

# Test Client Utilities

> HTTP client wrapper for MCP server testing

**↑ Parent**: [Test Suite](../README.MD) | **↑↑ MCP Server**: [README](../../README.MD) | **↑↑↑ Root**: [Nessus MCP Server](../../../README.MD)

## Files

| File | Purpose |
|------|---------|
| `nessus_client.py` | Async HTTP client for workflow validation |

## NessusMCPClient

Async context manager client for integration testing:

```python
async with NessusMCPClient(base_url="http://localhost:8000") as client:
    result = await client.submit_scan(targets="192.168.1.0/24", name="test")
    status = await client.poll_until_complete(result["task_id"])
    results = await client.get_results(result["task_id"])
```

### Methods

| Method | Description |
|--------|-------------|
| `submit_scan()` | Submit scan request, returns task_id |
| `get_status()` | Get current scan status |
| `poll_until_complete()` | Poll until terminal state (completed/failed/timeout) |
| `get_results()` | Retrieve scan results in JSON-NL format |
| `pause_scan()` | Pause running scan |
| `resume_scan()` | Resume paused scan |
| `stop_scan()` | Stop scan execution |
| `delete_scan()` | Delete scan and results |

### Configuration

- `base_url` - MCP server URL (default: `http://localhost:8000`)
- `auth_token` - Optional Bearer token for authentication

## Status

Methods are stubbed for future implementation. Currently integration tests use FastMCP client directly.
