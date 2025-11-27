# MCP Client Library

> Python client for Nessus MCP Server

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `nessus_fastmcp_client.py` | ~350 | High-level FastMCP client wrapper |
| `client_smoke.py` | ~100 | Quick smoke test script |
| `test_client.py` | ~80 | Client testing utilities |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| [examples/](examples/README_NEW.MD) | Progressive usage examples |

## NessusFastMCPClient

High-level async client wrapping FastMCP:

```python
from client.nessus_fastmcp_client import NessusFastMCPClient

async with NessusFastMCPClient(url="http://localhost:8835/mcp") as client:
    # Submit scan
    task = await client.submit_scan(
        targets="192.168.1.0/24",
        scan_name="Network Audit"
    )

    # Wait for completion
    status = await client.wait_for_completion(task["task_id"], timeout=600)

    # Get results
    results = await client.get_results(
        task["task_id"],
        schema_profile="brief",
        filters={"severity": "4"}
    )
```

### Constructor

```python
NessusFastMCPClient(
    url: str = None,           # MCP server URL (uses MCP_SERVER_URL env)
    timeout: float = 30.0,     # Request timeout
    log_handler: Callable = None,  # Custom log handler
    progress_handler: Callable = None,  # Progress callback
    debug: bool = False        # Enable debug logging
)
```

### Methods

| Method | Description |
|--------|-------------|
| `ping()` | Verify server connectivity |
| `list_tools()` | List available MCP tools |
| `submit_scan()` | Submit scan request |
| `get_status()` | Get task status |
| `wait_for_completion()` | Poll until terminal state |
| `get_results()` | Retrieve scan results |
| `list_tasks()` | List recent tasks |
| `list_scanners()` | List scanner instances |
| `get_pool_status()` | Get pool capacity |
| `get_queue_status()` | Get queue metrics |

### Scan Methods

```python
# Unauthenticated scan
await client.submit_scan(
    targets="192.168.1.1",
    scan_name="Quick Scan",
    scan_type="untrusted",
    scanner_pool="nessus"
)

# Authenticated scan (SSH)
await client.submit_authenticated_scan(
    targets="192.168.1.1",
    scan_name="Auth Scan",
    ssh_username="admin",
    ssh_password="secret",
    elevate_with="sudo"
)
```

### Progress Monitoring

```python
def on_progress(status):
    print(f"Progress: {status.get('progress', 0)}%")

client = NessusFastMCPClient(progress_handler=on_progress)
await client.wait_for_completion(task_id, poll_interval=10)
```

### Result Filtering

```python
# Critical vulnerabilities only
results = await client.get_results(
    task_id,
    filters={"severity": "4", "cvss_score": ">7.0"}
)

# Specific fields
results = await client.get_results(
    task_id,
    schema_profile="brief",
    custom_fields=["host", "cve", "cvss_score", "solution"]
)
```

## client_smoke.py

Quick connectivity test:

```bash
python -m client.client_smoke

# Output:
# ✓ Connected to MCP server
# ✓ Tools available: 9
# ✓ Scanners available: 2
# ✓ Smoke test passed
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_URL` | `http://localhost:8835/mcp` | MCP server endpoint |

**Note**: Inside Docker containers, use `http://mcp-api:8000/mcp`

## Architecture

```
NessusFastMCPClient
        │
        ↓
    FastMCP Client
        │
        ↓
    HTTP/SSE Transport
        │
        ↓
    MCP Server (tools/mcp_server.py)
```

## Dependencies

- `fastmcp` - FastMCP client library
- `httpx` - HTTP client (via FastMCP)

## Usage in Tests

```python
from client.nessus_fastmcp_client import NessusFastMCPClient

@pytest.fixture
async def mcp_client():
    async with NessusFastMCPClient() as client:
        yield client

async def test_scan_workflow(mcp_client):
    task = await mcp_client.submit_scan(...)
    assert task["status"] == "queued"
```
