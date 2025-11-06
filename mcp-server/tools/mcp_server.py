"""FastMCP server with mock scan tool."""
import uuid
from datetime import datetime

from fastmcp import FastMCP
from core.task_manager import TaskManager, generate_task_id
from core.types import Task, ScanState
from scanners.base import ScanRequest
from scanners.mock_scanner import MockNessusScanner


mcp = FastMCP("Nessus MCP Server - Phase 0")

# Initialize components
task_manager = TaskManager()
mock_scanner = MockNessusScanner()


@mcp.tool()
async def run_untrusted_scan(
    targets: str,
    name: str,
    description: str = "",
    schema_profile: str = "brief",
) -> dict:
    """
    Run network-only vulnerability scan (no credentials).

    Phase 0: Uses mock scanner for testing.

    Args:
        targets: IP addresses or CIDR ranges (e.g., "192.168.1.0/24")
        name: Scan name for identification
        description: Optional scan description
        schema_profile: Output schema (minimal|summary|brief|full)

    Returns:
        {
            "task_id": "...",
            "trace_id": "...",
            "status": "queued",
            "scanner_instance": "mock"
        }
    """
    # Generate IDs
    trace_id = str(uuid.uuid4())
    task_id = generate_task_id("nessus", "mock")

    # Create task
    task = Task(
        task_id=task_id,
        trace_id=trace_id,
        scan_type="untrusted",
        scanner_type="nessus",
        scanner_instance_id="mock",
        status=ScanState.QUEUED.value,
        payload={
            "targets": targets,
            "name": name,
            "description": description,
            "schema_profile": schema_profile,
        },
        created_at=datetime.utcnow().isoformat(),
    )

    task_manager.create_task(task)

    # Immediately "execute" with mock scanner (no queue yet in Phase 0)
    try:
        # Create scan
        scan_id = await mock_scanner.create_scan(
            ScanRequest(
                targets=targets,
                name=name,
                scan_type="untrusted",
                description=description,
                schema_profile=schema_profile
            )
        )

        # Update task
        task_manager.update_status(
            task_id,
            ScanState.RUNNING,
            nessus_scan_id=scan_id
        )

        # Launch scan
        await mock_scanner.launch_scan(scan_id)

    except Exception as e:
        task_manager.update_status(
            task_id,
            ScanState.FAILED,
            error_message=str(e)
        )

    return {
        "task_id": task_id,
        "trace_id": trace_id,
        "status": "queued",  # Simplified for Phase 0
        "scanner_instance": "mock",
        "message": "Scan submitted successfully (mock mode)"
    }


@mcp.tool()
async def get_scan_status(task_id: str) -> dict:
    """
    Get current status of scan task.

    Args:
        task_id: Task ID from run_untrusted_scan()

    Returns:
        {
            "task_id": "...",
            "trace_id": "...",
            "status": "queued|running|completed|failed|timeout",
            "progress": 0-100 (if available),
            "created_at": "...",
            "started_at": "...",
            "completed_at": "...",
            "nessus_scan_id": ...,
            "error_message": "..." (if failed)
        }
    """
    task = task_manager.get_task(task_id)

    if not task:
        return {"error": f"Task {task_id} not found"}

    # Get live progress from mock scanner if running
    progress = None
    if task.status == "running" and task.nessus_scan_id:
        try:
            status_info = await mock_scanner.get_status(task.nessus_scan_id)
            progress = status_info.get("progress")

            # Check if completed
            if status_info["status"] == "completed":
                task_manager.update_status(task_id, ScanState.COMPLETED)
                task = task_manager.get_task(task_id)
        except Exception as e:
            # Scanner error, mark task as failed
            task_manager.update_status(task_id, ScanState.FAILED, error_message=str(e))
            task = task_manager.get_task(task_id)

    return {
        "task_id": task.task_id,
        "trace_id": task.trace_id,
        "status": task.status,
        "progress": progress,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "nessus_scan_id": task.nessus_scan_id,
        "error_message": task.error_message,
    }


# =============================================================================
# ASGI App Configuration
# =============================================================================
# Create the ASGI app for uvicorn to serve.
#
# IMPORTANT: Version pins required to avoid "Task group is not initialized" error
# Bug: anyio >= 4.11.0 + starlette >= 0.50.0 causes task group initialization issues
# Fix: Pin to starlette==0.49.1, anyio==4.6.2.post1 (see requirements-api.txt)
#
# Using SSE transport (Server-Sent Events):
#   - Client→Server: HTTP POST /mcp with JSON-RPC requests
#   - Server→Client: SSE stream (text/event-stream) for responses
#   - This is the ONLY working transport with current MCP SDK + FastMCP versions
#   - StreamableHTTP also uses SSE internally (same behavior, different API)
#
# NOTE: SSE operational requirements:
#   - Proxy must not buffer (set X-Accel-Buffering: no)
#   - Long timeouts needed (3600s+)
#   - For multi-worker: sticky sessions OR Redis pub/sub
#
# The app is imported by run_server.py and served via uvicorn directly.
# Path "/mcp" is the endpoint where MCP clients connect.
# =============================================================================
app = mcp.sse_app(path="/mcp")
