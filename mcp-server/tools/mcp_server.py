"""FastMCP server with queue-based scan execution (Phase 1 + 2)."""
import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastmcp import FastMCP
from core.task_manager import TaskManager, generate_task_id
from core.types import Task, ScanState
from core.queue import TaskQueue, get_queue_stats
from core.idempotency import IdempotencyManager, ConflictError
from core.ip_utils import targets_match
from scanners.registry import ScannerRegistry
from schema.converter import NessusToJsonNL
from core.metrics import metrics_response, record_tool_call, record_scan_submission
from core.health import check_all_dependencies
from core.logging_config import configure_logging, get_logger
from starlette.responses import PlainTextResponse, JSONResponse


# =============================================================================
# FastMCP Server Configuration
# =============================================================================
# Configure structured logging
configure_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

mcp = FastMCP("Nessus MCP Server - Phase 1")

# Initialize components
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
DATA_DIR = os.getenv("DATA_DIR", "/app/data/tasks")
SCANNER_CONFIG = os.getenv("SCANNER_CONFIG", "/app/config/scanners.yaml")

task_manager = TaskManager(data_dir=DATA_DIR)
task_queue = TaskQueue(redis_url=REDIS_URL)
scanner_registry = ScannerRegistry(config_file=SCANNER_CONFIG)
idempotency_manager = IdempotencyManager(redis_client=task_queue.redis_client)

logger.info("mcp_server_initialized", redis_url=REDIS_URL, data_dir=DATA_DIR, scanner_config=SCANNER_CONFIG)


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
    scanner_pool: str | None = None,
    scanner_instance: str | None = None,
) -> dict:
    """
    Run network-only vulnerability scan (no credentials).

    Phase 1: Enqueues scan to Redis queue for async worker processing.
    Phase 4: Supports scanner pools with load-based selection.

    Args:
        targets: IP addresses or CIDR ranges (e.g., "192.168.1.0/24")
        name: Scan name for identification
        description: Optional scan description
        schema_profile: Output schema (minimal|summary|brief|full)
        idempotency_key: Optional key for idempotent retries
        scanner_pool: Scanner pool (e.g., "nessus", "nessus_dmz").
                     Defaults to "nessus" pool.
        scanner_instance: Optional scanner instance ID (e.g., "scanner1").
                         If not specified, selects least loaded scanner in pool.

    Returns:
        {
            "task_id": "...",
            "trace_id": "...",
            "status": "queued",
            "scanner_pool": "nessus",
            "scanner_instance": "scanner1",
            "queue_position": 1,
            "message": "Scan enqueued successfully"
        }
    """
    # Generate IDs
    trace_id = str(uuid.uuid4())
    target_pool = scanner_pool or scanner_registry.get_default_pool()

    # Select scanner: use specified or get least loaded in pool
    try:
        if scanner_instance:
            # Validate scanner exists
            _ = scanner_registry.get_instance(pool=target_pool, instance_id=scanner_instance)
            selected_instance = scanner_instance
        else:
            # Get least loaded scanner in pool
            _, instance_key = scanner_registry.get_available_scanner(pool=target_pool)
            selected_instance = instance_key.split(":")[-1]  # Extract instance ID from key
    except ValueError as e:
        return {
            "error": "Scanner not found",
            "message": str(e),
            "status_code": 404,
        }

    logger.info(
        "tool_invocation",
        tool="run_untrusted_scan",
        trace_id=trace_id,
        targets=targets,
        name=name,
        idempotency_key=idempotency_key,
        scanner_pool=target_pool,
        scanner_instance=selected_instance,
    )

    # Check idempotency key if provided
    if idempotency_key:
        request_params = {
            "targets": targets,
            "name": name,
            "description": description,
            "schema_profile": schema_profile,
            "scanner_pool": target_pool,
            "scanner_instance": selected_instance,
        }

        try:
            existing_task_id = await idempotency_manager.check(idempotency_key, request_params)
            if existing_task_id:
                # Return existing task
                existing_task = task_manager.get_task(existing_task_id)
                return {
                    "task_id": existing_task_id,
                    "trace_id": existing_task.trace_id,
                    "status": existing_task.status,
                    "scanner_pool": existing_task.scanner_pool,
                    "scanner_instance": existing_task.scanner_instance_id,
                    "message": "Returning existing task (idempotency key matched)",
                    "idempotent": True,
                }
        except ConflictError as e:
            return {
                "error": "Conflict",
                "message": str(e),
                "status_code": 409,
            }

    task_id = generate_task_id(target_pool, selected_instance)

    # Create task
    task = Task(
        task_id=task_id,
        trace_id=trace_id,
        scan_type="untrusted",
        scanner_type=target_pool.split("_")[0],  # nessus_dmz -> nessus
        scanner_pool=target_pool,
        scanner_instance_id=selected_instance,
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

    # Enqueue task for worker processing (to pool-specific queue)
    task_data = {
        "task_id": task_id,
        "trace_id": trace_id,
        "scan_type": "untrusted",
        "scanner_pool": target_pool,
        "scanner_instance_id": selected_instance,
        "payload": task.payload,
    }

    queue_depth = task_queue.enqueue(task_data, pool=target_pool)

    # Store idempotency key if provided
    if idempotency_key:
        await idempotency_manager.store(idempotency_key, task_id, request_params)

    # Record metrics and log success
    record_tool_call("run_untrusted_scan", "success")
    record_scan_submission("untrusted", "queued")

    # Get scanner URL for transparency
    scanner_info = scanner_registry.get_instance_info(pool=target_pool, instance_id=selected_instance)
    scanner_url = scanner_info.get("url", "unknown") if scanner_info else "unknown"

    # Estimate wait time (rough: queue_position * 15 minutes average scan time)
    estimated_wait_minutes = queue_depth * 15

    logger.info(
        "scan_enqueued",
        task_id=task_id,
        trace_id=trace_id,
        scanner_pool=target_pool,
        queue_position=queue_depth
    )

    return {
        "task_id": task_id,
        "trace_id": trace_id,
        "status": "queued",
        "scanner_pool": target_pool,
        "scanner_instance": selected_instance,
        "scanner_url": scanner_url,
        "queue_position": queue_depth,
        "estimated_wait_minutes": estimated_wait_minutes,
        "message": "Scan enqueued successfully. Worker will process asynchronously."
    }


@mcp.tool()
async def run_authenticated_scan(
    targets: str,
    name: str,
    scan_type: str,
    ssh_username: str,
    ssh_password: str,
    description: str = "",
    schema_profile: str = "brief",
    elevate_privileges_with: str = "Nothing",
    escalation_account: str = "",
    escalation_password: str = "",
    idempotency_key: str | None = None,
    scanner_pool: str | None = None,
    scanner_instance: str | None = None,
) -> dict:
    """
    Run an authenticated vulnerability scan with SSH credentials (Phase 5).

    Authenticated scans log into target systems via SSH to perform deeper
    vulnerability assessment than unauthenticated network scans.

    Args:
        targets: IP addresses or hostnames to scan (comma-separated)
        name: Human-readable scan name
        scan_type: "authenticated" (SSH only) or "authenticated_privileged" (SSH + sudo)
        ssh_username: SSH username for target authentication
        ssh_password: SSH password for target authentication
        description: Optional scan description
        schema_profile: Result detail level (minimal|summary|brief|full)
        elevate_privileges_with: "Nothing", "sudo", "su" (for authenticated_privileged)
        escalation_account: Account to escalate to (default: root)
        escalation_password: Password for privilege escalation (if required)
        idempotency_key: Optional key for duplicate prevention
        scanner_pool: Optional pool name for scanner selection
        scanner_instance: Optional specific scanner instance

    Returns:
        {
            "task_id": "...",
            "trace_id": "...",
            "status": "queued",
            "scan_type": "authenticated|authenticated_privileged",
            "scanner_pool": "nessus",
            "scanner_instance": "scanner1",
            "queue_position": 1,
            "message": "Authenticated scan enqueued successfully"
        }

    Authentication Detection (after scan completion):
        - authentication_status: "success" | "partial" | "failed"
        - Plugin 141118: "Valid Credentials Provided" (confirms success)
        - Plugin 110385: "Insufficient Privilege" (need sudo escalation)
        - hosts_summary.credential: "true" | "false"

    Example (authenticated scan - SSH only):
        run_authenticated_scan(
            targets="172.32.0.215",
            name="Internal Server Audit",
            scan_type="authenticated",
            ssh_username="randy",
            ssh_password="password123"
        )

    Example (authenticated_privileged scan - SSH + sudo):
        run_authenticated_scan(
            targets="172.32.0.209",
            name="Full System Audit",
            scan_type="authenticated_privileged",
            ssh_username="testauth_sudo_pass",
            ssh_password="TestPass123!",
            elevate_privileges_with="sudo",
            escalation_password="TestPass123!"
        )
    """
    # Generate IDs
    trace_id = str(uuid.uuid4())

    # Validate scan_type
    valid_types = ("authenticated", "authenticated_privileged")
    if scan_type not in valid_types:
        return {
            "error": f"Invalid scan_type: {scan_type}. Must be one of: {valid_types}",
            "trace_id": trace_id
        }

    # Validate privileged scan has escalation configured
    if scan_type == "authenticated_privileged" and elevate_privileges_with == "Nothing":
        return {
            "error": "authenticated_privileged scan requires elevate_privileges_with (sudo/su)",
            "trace_id": trace_id
        }

    # Pool selection
    target_pool = scanner_pool or scanner_registry.get_default_pool()

    # Select scanner: use specified or get least loaded in pool
    try:
        if scanner_instance:
            _ = scanner_registry.get_instance(pool=target_pool, instance_id=scanner_instance)
            selected_instance = scanner_instance
        else:
            _, instance_key = scanner_registry.get_available_scanner(pool=target_pool)
            selected_instance = instance_key.split(":")[-1]
    except ValueError as e:
        return {
            "error": "Scanner not found",
            "message": str(e),
            "status_code": 404,
        }

    logger.info(
        "tool_invocation",
        tool="run_authenticated_scan",
        trace_id=trace_id,
        targets=targets,
        name=name,
        scan_type=scan_type,
        ssh_username=ssh_username,
        elevate_privileges_with=elevate_privileges_with,
        idempotency_key=idempotency_key,
        scanner_pool=target_pool,
        scanner_instance=selected_instance,
    )

    # Build credentials structure
    credentials = {
        "type": "ssh",
        "auth_method": "password",
        "username": ssh_username,
        "password": ssh_password,
        "elevate_privileges_with": elevate_privileges_with,
    }

    if elevate_privileges_with != "Nothing":
        if escalation_password:
            credentials["escalation_password"] = escalation_password
        if escalation_account:
            credentials["escalation_account"] = escalation_account

    # Check idempotency key if provided
    if idempotency_key:
        request_params = {
            "targets": targets,
            "name": name,
            "scan_type": scan_type,
            "description": description,
            "schema_profile": schema_profile,
            "scanner_pool": target_pool,
            "scanner_instance": selected_instance,
            "ssh_username": ssh_username,
            "elevate_privileges_with": elevate_privileges_with,
        }

        try:
            existing_task_id = await idempotency_manager.check(idempotency_key, request_params)
            if existing_task_id:
                existing_task = task_manager.get_task(existing_task_id)
                return {
                    "task_id": existing_task_id,
                    "trace_id": existing_task.trace_id,
                    "status": existing_task.status,
                    "scan_type": existing_task.scan_type,
                    "scanner_pool": existing_task.scanner_pool,
                    "scanner_instance": existing_task.scanner_instance_id,
                    "message": "Returning existing task (idempotency key matched)",
                    "idempotent": True,
                }
        except ConflictError as e:
            return {
                "error": "Conflict",
                "message": str(e),
                "status_code": 409,
            }

    task_id = generate_task_id(target_pool, selected_instance)

    # Create task with credentials in payload
    task = Task(
        task_id=task_id,
        trace_id=trace_id,
        scan_type=scan_type,
        scanner_type=target_pool.split("_")[0],
        scanner_pool=target_pool,
        scanner_instance_id=selected_instance,
        status=ScanState.QUEUED.value,
        payload={
            "targets": targets,
            "name": name,
            "description": description,
            "schema_profile": schema_profile,
            "credentials": credentials,
        },
        created_at=datetime.utcnow().isoformat(),
    )

    # Store task metadata
    task_manager.create_task(task)

    # Enqueue task for worker processing
    task_data = {
        "task_id": task_id,
        "trace_id": trace_id,
        "scan_type": scan_type,
        "scanner_pool": target_pool,
        "scanner_instance_id": selected_instance,
        "payload": task.payload,
    }

    queue_depth = task_queue.enqueue(task_data, pool=target_pool)

    # Store idempotency key if provided
    if idempotency_key:
        await idempotency_manager.store(idempotency_key, task_id, request_params)

    # Record metrics
    record_tool_call("run_authenticated_scan", "success")
    record_scan_submission(scan_type, "queued")

    # Get scanner URL for transparency
    scanner_info = scanner_registry.get_instance_info(pool=target_pool, instance_id=selected_instance)
    scanner_url = scanner_info.get("url", "unknown") if scanner_info else "unknown"

    # Estimate wait time
    estimated_wait_minutes = queue_depth * 15

    logger.info(
        "authenticated_scan_enqueued",
        task_id=task_id,
        trace_id=trace_id,
        scan_type=scan_type,
        scanner_pool=target_pool,
        queue_position=queue_depth
    )

    return {
        "task_id": task_id,
        "trace_id": trace_id,
        "status": "queued",
        "scan_type": scan_type,
        "scanner_pool": target_pool,
        "scanner_instance": selected_instance,
        "scanner_url": scanner_url,
        "queue_position": queue_depth,
        "estimated_wait_minutes": estimated_wait_minutes,
        "message": f"{scan_type.replace('_', ' ').title()} scan enqueued successfully. Worker will process asynchronously."
    }


@mcp.tool()
async def get_scan_status(task_id: str) -> dict:
    """
    Get current status of scan task with validation results (Phase 4).

    Args:
        task_id: Task ID from run_untrusted_scan()

    Returns:
        {
            "task_id": "...",
            "trace_id": "...",
            "status": "queued|running|completed|failed|timeout",
            "progress": 0-100 (if available from scanner),
            "scanner_pool": "nessus",
            "scanner_instance": "scanner1",
            "nessus_scan_id": ... (if scan created),
            "created_at": "...",
            "started_at": "...",
            "completed_at": "...",
            "error_message": "..." (if failed),
            "authentication_status": "success|failed|partial|not_applicable" (Phase 4),
            "validation_warnings": [...] (Phase 4),
            "results_summary": {...} (if completed, Phase 4),
            "troubleshooting": {...} (if auth failed, Phase 4)
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
        "scan_type": task.scan_type,
        "scanner_pool": task.scanner_pool or task.scanner_type,  # Backward compat
        "scanner_type": task.scanner_type,
        "scanner_instance": task.scanner_instance_id,
        "targets": task.payload.get("targets", "") if task.payload else "",
        "name": task.payload.get("name", "") if task.payload else "",
        "nessus_scan_id": task.nessus_scan_id,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error_message": task.error_message,
        # Phase 4: Validation fields
        "authentication_status": task.authentication_status,
        "validation_warnings": task.validation_warnings,
    }

    # Add results_summary for completed tasks with validation stats
    if task.status == "completed" and task.validation_stats:
        response["results_summary"] = {
            "hosts_scanned": task.validation_stats.get("hosts_scanned", 0),
            "total_vulnerabilities": task.validation_stats.get("total_vulnerabilities", 0),
            "severity_breakdown": task.validation_stats.get("severity_counts", {}),
            "file_size_kb": round(task.validation_stats.get("file_size_bytes", 0) / 1024, 1),
            "auth_plugins_found": task.validation_stats.get("auth_plugins_found", 0),
        }

    # Add troubleshooting for failed auth
    if task.authentication_status == "failed":
        response["troubleshooting"] = {
            "likely_cause": "Credentials rejected or inaccessible target",
            "next_steps": [
                "Verify credentials in scanner configuration",
                "Check target allows SSH/WinRM from scanner IP",
                "Verify target firewall rules",
                "Check credential permissions on target",
                "Review scan logs for specific error"
            ]
        }

    # Get live progress from scanner if running
    if task.status == "running" and task.nessus_scan_id:
        try:
            # Use pool for scanner lookup
            pool = task.scanner_pool or task.scanner_type
            scanner = scanner_registry.get_instance(
                pool=pool,
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
async def list_scanners(scanner_pool: str | None = None) -> dict:
    """
    List all registered scanner instances with load information.

    Phase 4: Includes active scan counts, capacity, and pool information.

    Args:
        scanner_pool: Optional pool filter (e.g., "nessus", "nessus_dmz")

    Returns:
        {
            "scanners": [
                {
                    "scanner_type": "nessus",
                    "pool": "nessus",
                    "instance_id": "scanner1",
                    "instance_key": "nessus:scanner1",
                    "name": "Nessus Scanner 1",
                    "url": "https://172.30.0.3:8834",
                    "enabled": true,
                    "max_concurrent_scans": 5,
                    "active_scans": 2,
                    "available_capacity": 3,
                    "utilization_pct": 40.0
                },
                ...
            ],
            "total": 2,
            "pools": ["nessus"]
        }
    """
    scanners = scanner_registry.list_instances(
        enabled_only=True,
        include_load=True,
        pool=scanner_pool
    )

    return {
        "scanners": scanners,
        "total": len(scanners),
        "pools": scanner_registry.list_pools()
    }


@mcp.tool()
async def list_pools() -> dict:
    """
    List all available scanner pools.

    Returns:
        {
            "pools": ["nessus", "nessus_dmz"],
            "default_pool": "nessus"
        }
    """
    return {
        "pools": scanner_registry.list_pools(),
        "default_pool": scanner_registry.get_default_pool()
    }


@mcp.tool()
async def get_pool_status(scanner_pool: str | None = None) -> dict:
    """
    Get scanner pool status with overall capacity and utilization.

    Phase 4: Shows aggregate pool metrics and per-scanner breakdown.

    Args:
        scanner_pool: Pool name (e.g., "nessus", "nessus_dmz").
                     Defaults to "nessus" pool.

    Returns:
        {
            "pool": "nessus",
            "scanner_type": "nessus",
            "total_scanners": 2,
            "total_capacity": 10,
            "total_active": 3,
            "available_capacity": 7,
            "utilization_pct": 30.0,
            "scanners": [
                {
                    "instance_key": "nessus:scanner1",
                    "active_scans": 2,
                    "max_concurrent_scans": 5,
                    "utilization_pct": 40.0,
                    "available_capacity": 3
                },
                ...
            ]
        }
    """
    target_pool = scanner_pool or scanner_registry.get_default_pool()
    return scanner_registry.get_pool_status(pool=target_pool)


@mcp.tool()
async def get_queue_status(scanner_pool: str | None = None) -> dict:
    """
    Get current Redis queue status and metrics for a pool.

    Args:
        scanner_pool: Pool name (e.g., "nessus", "nessus_dmz").
                     Defaults to "nessus" pool.

    Returns:
        {
            "pool": "nessus",
            "queue_depth": 0,
            "dlq_size": 0,
            "next_tasks": [...],
            "timestamp": "..."
        }
    """
    target_pool = scanner_pool or scanner_registry.get_default_pool()
    stats = get_queue_stats(task_queue, pool=target_pool)
    return stats


@mcp.tool()
async def list_tasks(
    limit: int = 10,
    status_filter: str | None = None,
    scanner_pool: str | None = None,
    target_filter: str | None = None,
) -> dict:
    """
    List recent tasks from task manager.

    Args:
        limit: Maximum number of tasks to return (default: 10)
        status_filter: Optional filter by status (queued|running|completed|failed|timeout)
        scanner_pool: Optional filter by pool (e.g., "nessus", "nessus_dmz")
        target_filter: Optional filter by target IP/CIDR (CIDR-aware matching).
                      Matches if query IP is within stored subnet, or query subnet
                      contains/overlaps stored targets.
                      Examples: "192.168.1.5", "10.0.0.0/24"

    Returns:
        {
            "tasks": [
                {
                    "task_id": "...",
                    "status": "...",
                    "scanner_pool": "nessus",
                    "targets": "192.168.1.0/24",
                    "name": "Network Scan",
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

    # When filtering by target, we may need to scan more files
    scan_multiplier = 10 if target_filter else 2

    tasks = []
    for task_file in task_dirs[:limit * scan_multiplier]:
        try:
            task = task_manager.get_task(task_file.parent.name)
            if task:
                # Apply status filter if provided
                if status_filter and task.status != status_filter:
                    continue

                # Apply pool filter if provided
                task_pool = task.scanner_pool or task.scanner_type
                if scanner_pool and task_pool != scanner_pool:
                    continue

                # Apply target filter if provided (CIDR-aware)
                if target_filter:
                    stored_targets = task.payload.get("targets", "") if task.payload else ""
                    if not targets_match(target_filter, stored_targets):
                        continue

                tasks.append({
                    "task_id": task.task_id,
                    "trace_id": task.trace_id,
                    "status": task.status,
                    "scan_type": task.scan_type,
                    "scanner_pool": task_pool,
                    "scanner_type": task.scanner_type,
                    "scanner_instance": task.scanner_instance_id,
                    "targets": task.payload.get("targets", "") if task.payload else "",
                    "name": task.payload.get("name", "") if task.payload else "",
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


@mcp.tool()
async def get_scan_results(
    task_id: str,
    page: int = 1,
    page_size: int = 40,
    schema_profile: str = "brief",
    custom_fields: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get scan results in paginated JSON-NL format (Phase 2).

    Args:
        task_id: Task ID from run_*_scan()
        page: Page number (1-indexed), or 0 for ALL data
        page_size: Lines per page (10-100, clamped automatically)
        schema_profile: Predefined schema (minimal|summary|brief|full)
        custom_fields: Custom field list (mutually exclusive with non-default schema_profile)
        filters: Filter dict (e.g., {"severity": "4", "cvss_score": ">7.0"})

    Returns:
        JSON-NL string with schema, metadata, vulnerabilities, pagination
    """
    # Validate mutual exclusivity
    if schema_profile != "brief" and custom_fields is not None:
        return json.dumps({
            "error": "Cannot specify both schema_profile and custom_fields"
        })

    # Get task
    task = task_manager.get_task(task_id)
    if not task:
        return json.dumps({"error": f"Task {task_id} not found"})

    if task.status != "completed":
        return json.dumps({
            "error": f"Scan not completed yet (status: {task.status})"
        })

    # Load .nessus file
    nessus_file = task_manager.data_dir / task_id / "scan_native.nessus"
    if not nessus_file.exists():
        return json.dumps({"error": "Scan results not found"})

    nessus_data = nessus_file.read_bytes()

    # Convert to JSON-NL
    converter = NessusToJsonNL()
    try:
        results = converter.convert(
            nessus_data=nessus_data,
            schema_profile=schema_profile,
            custom_fields=custom_fields,
            filters=filters,
            page=page,
            page_size=page_size
        )
        return results
    except ValueError as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# Health & Metrics Endpoint Functions
# =============================================================================
# NOTE: These functions are defined here but registered to the Starlette app
# after it's created below (see "Register HTTP endpoints" section)

async def health(request):
    """
    Health check endpoint.

    Checks:
    - Redis connectivity (PING)
    - Filesystem writability (touch test)

    Returns:
        200 OK if healthy, 503 Service Unavailable if unhealthy
    """
    health_status = check_all_dependencies(REDIS_URL, DATA_DIR)

    if health_status["status"] == "healthy":
        return JSONResponse(status_code=200, content=health_status)
    else:
        return JSONResponse(status_code=503, content=health_status)


async def metrics(request):
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format:
    - nessus_scans_total
    - nessus_api_requests_total
    - nessus_active_scans
    - nessus_scanner_instances
    - nessus_queue_depth
    - nessus_dlq_size
    - nessus_task_duration_seconds
    - nessus_ttl_deletions_total
    """
    return PlainTextResponse(metrics_response())


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
# Using http_app with streamable-http transport (modern FastMCP 2.13+ API)
# streamable-http uses /messages POST endpoint for bidirectional communication
# This replaces the deprecated sse_app() method
app = mcp.http_app(path="/mcp", transport="streamable-http", stateless_http=True)

# =============================================================================
# Register HTTP Endpoints
# =============================================================================
# Add health and metrics endpoints to the Starlette app
# These need to be added after the app is created above
from starlette.routing import Route

app.routes.append(Route("/health", endpoint=health, methods=["GET"]))
app.routes.append(Route("/metrics", endpoint=metrics, methods=["GET"]))
