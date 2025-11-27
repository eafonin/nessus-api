# MCP Tools

> FastMCP server implementation and MCP tool definitions

## Module Overview

| File | Lines | Purpose |
|------|-------|---------|
| `mcp_server.py` | ~500 | FastMCP server with tool implementations |
| `mcp_tools.py` | ~140 | Tool interface definitions (reference) |
| `admin_cli.py` | ~200 | Admin CLI for queue management |
| `run_server.py` | 33 | Uvicorn server launcher |
| `test_asgi_direct.py` | ~50 | Direct ASGI testing utility |

## MCP Tools

Tools exposed via Model Context Protocol:

### Scan Execution

| Tool | Description |
|------|-------------|
| `run_untrusted_scan` | Network-only scan (no credentials) |
| `run_authenticated_scan` | SSH authenticated scan |
| `get_scan_status` | Check scan progress |
| `get_scan_results` | Retrieve paginated results |

### Scan Control

| Tool | Description |
|------|-------------|
| `pause_scan` | Pause running scan |
| `resume_scan` | Resume paused scan |
| `stop_scan` | Stop scan execution |
| `delete_scan` | Delete scan and results |

### Infrastructure

| Tool | Description |
|------|-------------|
| `list_scanners` | List scanner instances |
| `list_pools` | List scanner pools |
| `get_pool_status` | Pool capacity info |
| `get_queue_status` | Queue depth and metrics |
| `list_tasks` | Recent task history |

## File Details

### mcp_server.py

Main FastMCP server implementation:

```python
from fastmcp import FastMCP

mcp = FastMCP("Nessus MCP Server")

@mcp.tool()
async def run_untrusted_scan(targets: str, name: str, ...) -> dict:
    # 1. Generate task_id and trace_id
    # 2. Check idempotency
    # 3. Select scanner from pool
    # 4. Create task in TaskManager
    # 5. Enqueue to Redis
    # 6. Return task_id, status, queue_position
```

**Key components initialized**:
- `TaskManager` - Task persistence
- `TaskQueue` - Redis queue
- `ScannerRegistry` - Pool management
- `IdempotencyManager` - Duplicate prevention
- `NessusToJsonNL` - Results conversion

**Endpoints added**:
- `/health` - Health check
- `/ready` - Readiness probe
- `/metrics` - Prometheus metrics

### mcp_tools.py

Reference tool definitions (interface only):

```python
@mcp.tool()
async def run_untrusted_scan(...) -> Dict[str, Any]:
    """Submit untrusted (unauthenticated) vulnerability scan."""
    pass  # Implemented in mcp_server.py
```

Used as reference for tool signatures and documentation.

### admin_cli.py

CLI for queue administration:

```bash
# Queue statistics
python -m tools.admin_cli stats --pool nessus
python -m tools.admin_cli stats --all-pools

# Dead Letter Queue management
python -m tools.admin_cli list-dlq --pool nessus --limit 20
python -m tools.admin_cli inspect-dlq TASK_ID --pool nessus
python -m tools.admin_cli retry-dlq TASK_ID --pool nessus
python -m tools.admin_cli purge-dlq --pool nessus --confirm
```

**Commands**:

| Command | Description |
|---------|-------------|
| `stats` | Show queue depth, DLQ size |
| `list-dlq` | List failed tasks in DLQ |
| `inspect-dlq` | Show task details and error |
| `retry-dlq` | Re-enqueue failed task |
| `purge-dlq` | Delete all DLQ entries |

### run_server.py

Uvicorn launcher for production:

```python
import uvicorn
from tools.mcp_server import app

uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Why direct uvicorn.run()**:
- FastMCP's `run_*_async()` creates new app instance
- Bypasses customizations in `mcp_server.py`
- Direct run ensures exact configured app is served

### test_asgi_direct.py

Testing utility for direct ASGI calls without HTTP:

```python
# Test tool calls directly
response = await test_tool_call("run_untrusted_scan", {
    "targets": "192.168.1.1",
    "name": "test"
})
```

## Running the Server

### Docker (Production)

```bash
cd dev1
docker compose up mcp-api
```

### Local Development

```bash
cd mcp-server
source venv/bin/activate
python -m tools.run_server
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `DATA_DIR` | `/app/data/tasks` | Task storage |
| `SCANNER_CONFIG` | `/app/config/scanners.yaml` | Scanner pools |
| `LOG_LEVEL` | `INFO` | Logging level |

## Tool Usage Examples

### via Claude Code

```
User: Scan 192.168.1.0/24 for vulnerabilities
Claude: [Uses run_untrusted_scan tool]
```

### via MCP Client

```python
from mcp import Client

async with Client("http://localhost:8836/mcp") as client:
    result = await client.call_tool("run_untrusted_scan", {
        "targets": "192.168.1.0/24",
        "name": "Network Scan"
    })
```

## Response Formats

### run_untrusted_scan Response

```json
{
    "task_id": "ne_scan_20251126_123456_abc123",
    "trace_id": "uuid-here",
    "status": "queued",
    "scanner_pool": "nessus",
    "scanner_instance": "scanner1",
    "queue_position": 1,
    "message": "Scan enqueued successfully"
}
```

### get_scan_status Response

```json
{
    "task_id": "ne_scan_...",
    "status": "running",
    "progress": 45,
    "nessus_scan_id": 123,
    "created_at": "2025-11-26T12:34:56",
    "started_at": "2025-11-26T12:35:00"
}
```

### get_scan_results Response (JSON-NL)

```
{"type": "schema", "profile": "brief", "fields": [...]}
{"type": "scan_metadata", "scan_name": "..."}
{"type": "vulnerability", "host": "192.168.1.1", ...}
{"type": "vulnerability", "host": "192.168.1.2", ...}
{"type": "pagination", "page": 1, "total_pages": 5}
```

## Dependencies

```
tools/
├── mcp_server.py
│   ├── fastmcp
│   ├── core/task_manager.py
│   ├── core/queue.py
│   ├── core/idempotency.py
│   ├── scanners/registry.py
│   └── schema/converter.py
├── admin_cli.py
│   └── core/queue.py
└── run_server.py
    └── uvicorn
```
