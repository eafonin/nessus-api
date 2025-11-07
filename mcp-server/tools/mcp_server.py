"""FastMCP server with queue-based scan execution (Phase 1)."""
import os
import uuid
from datetime import datetime

from fastmcp import FastMCP
from core.task_manager import TaskManager, generate_task_id
from core.types import Task, ScanState
from core.queue import TaskQueue, get_queue_stats
from scanners.registry import ScannerRegistry


# =============================================================================
# FastMCP Server Configuration
# =============================================================================
mcp = FastMCP("Nessus MCP Server - Phase 1")

# Initialize components
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
DATA_DIR = os.getenv("DATA_DIR", "/app/data/tasks")
SCANNER_CONFIG = os.getenv("SCANNER_CONFIG", "/app/config/scanners.yaml")

task_manager = TaskManager(data_dir=DATA_DIR)
task_queue = TaskQueue(redis_url=REDIS_URL)
scanner_registry = ScannerRegistry(config_file=SCANNER_CONFIG)


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool()
async def run_untrusted_scan(
    targets: str,
    name: str,
    description: str = "",
    schema_profile: str = "brief",
    idempotency_key: str | None = None,
) -> dict:
    """
    Run network-only vulnerability scan (no credentials).

    Phase 1: Enqueues scan to Redis queue for async worker processing.

    Args:
        targets: IP addresses or CIDR ranges (e.g., "192.168.1.0/24")
        name: Scan name for identification
        description: Optional scan description
        schema_profile: Output schema (minimal|summary|brief|full)
        idempotency_key: Optional key for idempotent retries

    Returns:
        {
            "task_id": "...",
            "trace_id": "...",
            "status": "queued",
            "scanner_type": "nessus",
            "scanner_instance": "local",
            "queue_position": 1,
            "message": "Scan enqueued successfully"
        }
    """
    # Generate IDs
    trace_id = str(uuid.uuid4())
    scanner_type = "nessus"
    scanner_instance = "local"  # Default instance
    task_id = generate_task_id(scanner_type, scanner_instance)

    # TODO: Implement idempotency check when Task 1.5 complete
    # if idempotency_key:
    #     existing_task_id = await idempotency_manager.check(idempotency_key, {...})
    #     if existing_task_id:
    #         return existing task info

    # Create task
    task = Task(
        task_id=task_id,
        trace_id=trace_id,
        scan_type="untrusted",
        scanner_type=scanner_type,
        scanner_instance_id=scanner_instance,
        status=ScanState.QUEUED.value,
        payload={
            "targets": targets,
            "name": name,
            "description": description,
            "schema_profile": schema_profile,
        },
        created_at=datetime.utcnow().isoformat(),
    )

    # Store task metadata
    task_manager.create_task(task)

    # Enqueue task for worker processing
    task_data = {
        "task_id": task_id,
        "trace_id": trace_id,
        "scan_type": "untrusted",
        "scanner_type": scanner_type,
        "scanner_instance_id": scanner_instance,
        "payload": task.payload,
    }

    queue_depth = task_queue.enqueue(task_data)

    # TODO: Store idempotency key when Task 1.5 complete
    # if idempotency_key:
    #     await idempotency_manager.store(idempotency_key, task_id, {...})

    return {
        "task_id": task_id,
        "trace_id": trace_id,
        "status": "queued",
        "scanner_type": scanner_type,
        "scanner_instance": scanner_instance,
        "queue_position": queue_depth,
        "message": "Scan enqueued successfully. Worker will process asynchronously."
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
            "progress": 0-100 (if available from scanner),
            "scanner_type": "nessus",
            "scanner_instance": "local",
            "nessus_scan_id": ... (if scan created),
            "created_at": "...",
            "started_at": "...",
            "completed_at": "...",
            "error_message": "..." (if failed)
        }
    """
    task = task_manager.get_task(task_id)

    if not task:
        return {"error": f"Task {task_id} not found"}

    # Build base response
    response = {
        "task_id": task.task_id,
        "trace_id": task.trace_id,
        "status": task.status,
        "scanner_type": task.scanner_type,
        "scanner_instance": task.scanner_instance_id,
        "nessus_scan_id": task.nessus_scan_id,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error_message": task.error_message,
    }

    # Get live progress from scanner if running
    if task.status == "running" and task.nessus_scan_id:
        try:
            scanner = scanner_registry.get_instance(
                scanner_type=task.scanner_type,
                instance_id=task.scanner_instance_id
            )

            status_info = await scanner.get_status(task.nessus_scan_id)
            response["progress"] = status_info.get("progress", 0)
            response["scanner_status"] = status_info.get("status")

        except Exception as e:
            # Scanner query failed - task status remains unchanged
            response["scanner_error"] = str(e)

    return response


@mcp.tool()
async def list_scanners() -> dict:
    """
    List all registered scanner instances and their status.

    Returns:
        {
            "scanners": [
                {
                    "scanner_type": "nessus",
                    "instance_id": "local",
                    "name": "Local Nessus Scanner",
                    "url": "https://172.32.0.209:8834",
                    "enabled": true
                },
                ...
            ],
            "total": 1
        }
    """
    scanners = scanner_registry.list_instances(enabled_only=True)

    return {
        "scanners": scanners,
        "total": len(scanners)
    }


@mcp.tool()
async def get_queue_status() -> dict:
    """
    Get current Redis queue status and metrics.

    Returns:
        {
            "queue_depth": 0,
            "dlq_size": 0,
            "next_tasks": [...],
            "timestamp": "..."
        }
    """
    stats = get_queue_stats(task_queue)
    return stats


@mcp.tool()
async def list_tasks(
    limit: int = 10,
    status_filter: str | None = None
) -> dict:
    """
    List recent tasks from task manager.

    Args:
        limit: Maximum number of tasks to return (default: 10)
        status_filter: Optional filter by status (queued|running|completed|failed|timeout)

    Returns:
        {
            "tasks": [
                {
                    "task_id": "...",
                    "status": "...",
                    "created_at": "...",
                    ...
                },
                ...
            ],
            "total": 10
        }
    """
    # Get all task directories
    task_dirs = sorted(
        task_manager.data_dir.glob("*/task.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    tasks = []
    for task_file in task_dirs[:limit * 2]:  # Read more than limit for filtering
        try:
            task = task_manager.get_task(task_file.parent.name)
            if task:
                # Apply status filter if provided
                if status_filter and task.status != status_filter:
                    continue

                tasks.append({
                    "task_id": task.task_id,
                    "trace_id": task.trace_id,
                    "status": task.status,
                    "scan_type": task.scan_type,
                    "scanner_type": task.scanner_type,
                    "scanner_instance": task.scanner_instance_id,
                    "created_at": task.created_at,
                    "started_at": task.started_at,
                    "completed_at": task.completed_at,
                    "nessus_scan_id": task.nessus_scan_id,
                })

                if len(tasks) >= limit:
                    break
        except Exception:
            continue

    return {
        "tasks": tasks,
        "total": len(tasks)
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
