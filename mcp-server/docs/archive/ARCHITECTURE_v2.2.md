# Nessus MCP Server - Architecture v2.2 (Production-Ready)

> **Purpose**: Production-grade Docker-based MCP server with Redis queue, idempotency, observability, and comprehensive error handling
> **Changes from v2.1**: Added idempotency, trace IDs, Prometheus metrics, state machine enforcement, native async scanner implementation
> **Status**: Ready for implementation

---

## 1. High-Level Architecture

### Container Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                   Docker Host (Single Machine)               │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                 Docker Compose Network                  │ │
│  │                                                         │ │
│  │  ┌─────────────────┐  ┌──────────────────┐            │ │
│  │  │  MCP HTTP API   │  │  Redis           │            │ │
│  │  │  Port: 8836     │──│  Port: 6379      │            │ │
│  │  │  - 10 MCP Tools │  │  - Task Queue    │            │ │
│  │  │  - Idempotency  │  │  - Dead Letter Q │            │ │
│  │  │  - /metrics     │  │  - Scanner Reg   │            │ │
│  │  │  - Trace IDs    │  │  - Idempotency   │            │ │
│  │  └─────────────────┘  └──────────────────┘            │ │
│  │           │                     │                      │ │
│  │  ┌─────────────────────────────┴────────┐            │ │
│  │  │         Shared Volume: /app/data      │            │ │
│  │  │  - tasks/{task_id}/                   │            │ │
│  │  │    ├── task.json (trace_id)           │            │ │
│  │  │    ├── scan_native.nessus             │            │ │
│  │  │    ├── scan_schema_*.jsonl            │            │ │
│  │  │    └── scanner_logs/                  │            │ │
│  │  └───────────────┬───────────────────────┘            │ │
│  │                  │                                     │ │
│  │  ┌───────────────▼──────────┐  ┌──────────────────┐  │ │
│  │  │   Scanner Worker         │  │  Existing Nessus  │  │ │
│  │  │   - Queue Consumer       │──│  Port: 8834       │  │ │
│  │  │   - Native Async         │  │  Instance: "prod" │  │ │
│  │  │   - State Machine        │  └──────────────────┘  │ │
│  │  │   - TTL Housekeeping     │                         │ │
│  │  └──────────────────────────┘                         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Features (v2.2)
- **Idempotency**: HTTP header OR tool arg, prevents duplicate scans on retry
- **Trace IDs**: Per-request tracing through entire scan lifecycle
- **State Machine**: TaskManager enforces valid state transitions
- **Observability**: Prometheus metrics, structured JSON logs
- **Native Async**: No subprocess calls, pure async/await Nessus integration
- **Redis Queue**: FIFO with dead letter queue (DLQ) for failed tasks

---

## 2. Idempotency System

### 2.1 Idempotency Key Format

**Acceptance Methods** (prefer header, fallback to arg):
```python
# Priority 1: HTTP header
X-Idempotency-Key: client-retry-abc123

# Priority 2: Tool argument
{
  "targets": "192.168.1.1",
  "name": "Test Scan",
  "idempotency_key": "client-retry-abc123"
}

# If both provided: MUST match, else 400 Bad Request
```

**Validation Logic**:
```python
def extract_idempotency_key(request_headers: Dict, tool_args: Dict) -> Optional[str]:
    """Extract and validate idempotency key from header or arg"""
    header_key = request_headers.get("X-Idempotency-Key")
    arg_key = tool_args.get("idempotency_key")

    if header_key and arg_key:
        if header_key != arg_key:
            raise ValueError("Idempotency key mismatch between header and argument")
        return header_key

    return header_key or arg_key
```

### 2.2 Implementation

**Location**: Tool handler (before task creation)

```python
# tools/scan_tools.py
@mcp.tool()
async def run_untrusted_scan(
    targets: str,
    name: str,
    description: str = "",
    schema_profile: str = "brief",
    scanner_type: str = "nessus",
    scanner_instance: Optional[str] = None,
    debug_mode: bool = False,
    idempotency_key: Optional[str] = None  # Optional tool argument
) -> Dict[str, Any]:
    """Run network-only vulnerability scan (no credentials)."""

    # Extract idempotency key (header takes precedence)
    idemp_key = extract_idempotency_key(request.headers, locals())

    if idemp_key:
        # Check for existing task
        existing_task_id = await check_idempotency(
            idemp_key,
            request_params={
                "targets": targets,
                "name": name,
                "description": description,
                "schema_profile": schema_profile,
                "scanner_type": scanner_type,
                "scanner_instance": scanner_instance,
                "debug_mode": debug_mode
            }
        )

        if existing_task_id:
            # Return existing task (idempotent)
            return await get_existing_task_response(existing_task_id)

    # Continue with normal task creation...
    instance = registry.get_instance(scanner_type, scanner_instance)
    task_id = generate_task_id(scanner_type, instance.instance_id)

    # Store idempotency mapping
    if idemp_key:
        await store_idempotency_mapping(idemp_key, task_id, request_params)

    # ... rest of tool logic
```

### 2.3 Redis Storage

```python
# core/idempotency.py
import hashlib
import json
from typing import Dict, Any, Optional

class IdempotencyManager:
    """Manages idempotency keys and request deduplication"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl_hours = 48  # Keep mappings for 2 days

    def _hash_request(self, params: Dict[str, Any]) -> str:
        """Create deterministic hash of normalized request"""
        # Normalize params (sort keys, handle None, etc.)
        normalized = json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def check(
        self,
        idemp_key: str,
        request_params: Dict[str, Any]
    ) -> Optional[str]:
        """
        Check if idempotency key exists.

        Returns:
            - task_id if key exists and hash matches
            - Raises 409 Conflict if key exists but hash differs
            - None if key doesn't exist
        """
        key = f"idemp:{idemp_key}"
        stored_data = self.redis.get(key)

        if not stored_data:
            return None

        stored = json.loads(stored_data)
        stored_task_id = stored["task_id"]
        stored_hash = stored["request_hash"]

        current_hash = self._hash_request(request_params)

        if stored_hash != current_hash:
            logger.warning(
                f"Idempotency key reused with different params",
                extra={
                    "idemp_key": idemp_key,
                    "stored_hash": stored_hash,
                    "current_hash": current_hash
                }
            )
            raise ConflictError(
                f"Idempotency key '{idemp_key}' exists with different request parameters"
            )

        return stored_task_id

    async def store(
        self,
        idemp_key: str,
        task_id: str,
        request_params: Dict[str, Any]
    ) -> bool:
        """
        Store idempotency mapping using SETNX (atomic).

        Returns:
            True if stored (new key)
            False if key already exists (race condition)
        """
        key = f"idemp:{idemp_key}"
        request_hash = self._hash_request(request_params)

        data = json.dumps({
            "task_id": task_id,
            "request_hash": request_hash,
            "created_at": datetime.utcnow().isoformat()
        })

        # SETNX: set only if not exists (atomic)
        success = self.redis.set(
            key,
            data,
            nx=True,  # Only set if not exists
            ex=self.ttl_hours * 3600  # TTL in seconds
        )

        return bool(success)
```

---

## 3. Trace ID System

### 3.1 Trace ID Generation

**Scope**: One trace ID per HTTP request, propagates through entire workflow

```python
# api/middleware.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class TraceMiddleware(BaseHTTPMiddleware):
    """Add trace_id to every request"""

    async def dispatch(self, request, call_next):
        # Generate or extract trace ID
        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())

        # Store in request state for tool access
        request.state.trace_id = trace_id

        # Propagate to response headers
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id

        return response
```

### 3.2 Trace ID Propagation

**Through Logs**:
```python
# Setup structured logging with trace_id
import logging
import contextvars

trace_context = contextvars.ContextVar("trace_id", default="unknown")

class TraceFormatter(logging.Formatter):
    """Add trace_id to all log records"""

    def format(self, record):
        record.trace_id = trace_context.get("unknown")
        return super().format(record)

# Configure
logging.basicConfig(
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "trace_id": "%(trace_id)s", "message": "%(message)s"}',
    handlers=[
        logging.FileHandler("/app/logs/api.jsonl"),
        logging.StreamHandler()
    ]
)
```

**Through Task Metadata**:
```python
# Store in task.json
{
  "task_id": "ns_a3f2_20250101_120345_b1c2d3e4",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "created_at": "2025-01-01T12:00:00Z",
  ...
}
```

**Through Redis Queue**:
```python
@dataclass
class Task:
    task_id: str
    trace_id: str  # NEW: propagate trace ID
    scan_type: str
    scanner_type: str
    scanner_instance_id: str
    payload: Dict[str, Any]
    status: str = "queued"
    created_at: str = ""
```

---

## 4. State Machine Enforcement

### 4.1 Valid State Transitions

```python
# core/state_machine.py
from enum import Enum
from typing import Set, Dict

class ScanState(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

# Valid transitions
VALID_TRANSITIONS: Dict[ScanState, Set[ScanState]] = {
    ScanState.QUEUED: {ScanState.RUNNING, ScanState.FAILED},
    ScanState.RUNNING: {ScanState.COMPLETED, ScanState.FAILED, ScanState.TIMEOUT},
    ScanState.COMPLETED: set(),  # Terminal state
    ScanState.FAILED: set(),     # Terminal state
    ScanState.TIMEOUT: set(),    # Terminal state
}

class StateTransitionError(Exception):
    """Raised when invalid state transition attempted"""
    pass
```

### 4.2 TaskManager as Single Writer

```python
# core/task_manager.py
from pathlib import Path
from datetime import datetime
import json
import fcntl  # File locking
from typing import Dict, Any

class TaskManager:
    """
    Single writer for task state.
    All status updates go through this class.
    """

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    async def transition_state(
        self,
        task_id: str,
        new_state: ScanState,
        trace_id: str,
        **metadata
    ) -> None:
        """
        Enforce state machine transitions.

        Only valid transitions allowed per VALID_TRANSITIONS.
        Uses file locking to prevent concurrent writes.
        """
        task_file = self.data_dir / "tasks" / task_id / "task.json"

        # Lock file for atomic read-modify-write
        with open(task_file, "r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)

            try:
                # Read current state
                data = json.load(f)
                current_state = ScanState(data["status"])

                # Validate transition
                if new_state not in VALID_TRANSITIONS.get(current_state, set()):
                    raise StateTransitionError(
                        f"Invalid transition: {current_state.value} → {new_state.value}"
                    )

                # Update state
                data["status"] = new_state.value

                # Update timestamps
                if new_state == ScanState.RUNNING:
                    data["started_at"] = datetime.utcnow().isoformat()
                elif new_state in {ScanState.COMPLETED, ScanState.FAILED, ScanState.TIMEOUT}:
                    data["completed_at"] = datetime.utcnow().isoformat()

                    # Calculate execution time
                    if "started_at" in data:
                        start = datetime.fromisoformat(data["started_at"])
                        end = datetime.utcnow()
                        data["execution_time"] = (end - start).total_seconds()

                # Add any additional metadata
                data.update(metadata)

                # Write back
                f.seek(0)
                f.truncate()
                json.dump(data, f, indent=2)

                logger.info(
                    f"State transition: {current_state.value} → {new_state.value}",
                    extra={"task_id": task_id, "trace_id": trace_id}
                )

            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # Worker calls these methods (not file I/O directly)

    async def mark_running(self, task_id: str, trace_id: str, scan_id: int):
        """Worker: mark task as running"""
        await self.transition_state(
            task_id,
            ScanState.RUNNING,
            trace_id,
            nessus_scan_id=scan_id
        )

    async def mark_completed(self, task_id: str, trace_id: str):
        """Worker: mark task as completed"""
        await self.transition_state(task_id, ScanState.COMPLETED, trace_id)

    async def mark_failed(self, task_id: str, trace_id: str, error: str):
        """Worker: mark task as failed"""
        await self.transition_state(
            task_id,
            ScanState.FAILED,
            trace_id,
            error_message=error
        )

    async def mark_timeout(self, task_id: str, trace_id: str):
        """Worker: mark task as timeout"""
        await self.transition_state(task_id, ScanState.TIMEOUT, trace_id)
```

---

## 5. Native Async Nessus Scanner

### 5.1 Scanner Interface

```python
# scanners/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ScanRequest:
    """Unified scan request structure"""
    targets: str
    name: str
    scan_type: str = "untrusted"
    credentials: Optional[Dict[str, Any]] = None
    schema_profile: str = "brief"

class ScannerInterface(ABC):
    """Clean interface for scanner operations"""

    @abstractmethod
    async def create_scan(self, request: ScanRequest) -> int:
        """Create scan, return Nessus scan_id"""
        pass

    @abstractmethod
    async def launch_scan(self, scan_id: int) -> str:
        """Launch scan, return scan_uuid"""
        pass

    @abstractmethod
    async def get_status(self, scan_id: int) -> Dict[str, Any]:
        """
        Get scan status and progress.

        Returns:
            {
                "status": "pending|running|completed|...",
                "progress": 0-100,
                "uuid": "...",
                "info": {...}
            }
        """
        pass

    @abstractmethod
    async def export_results(self, scan_id: int, format: str = "nessus") -> bytes:
        """Export scan results in specified format"""
        pass

    @abstractmethod
    async def stop_scan(self, scan_id: int) -> bool:
        """Stop running scan"""
        pass
```

### 5.2 Native Async Nessus Implementation

```python
# scanners/nessus_scanner.py
import httpx
from typing import Dict, Any, Optional
from pathlib import Path

class NessusScanner(ScannerInterface):
    """
    Native async Nessus scanner implementation.

    DOES NOT use existing scripts (those are for testing only).
    Pure async/await with httpx for all Nessus API calls.
    """

    def __init__(self, url: str, credentials: Dict[str, Any]):
        self.url = url.rstrip("/")
        self.creds = credentials
        self._session: Optional[httpx.AsyncClient] = None
        self._api_token: Optional[str] = None
        self._session_token: Optional[str] = None

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create async HTTP session"""
        if not self._session:
            self._session = httpx.AsyncClient(
                verify=False,  # Self-signed cert
                timeout=30.0
            )
        return self._session

    async def _authenticate(self) -> None:
        """Authenticate with Nessus and get tokens"""
        if self._api_token:
            return  # Already authenticated

        client = await self._get_session()

        # POST /session for web UI authentication
        response = await client.post(
            f"{self.url}/session",
            json={
                "username": self.creds["username"],
                "password": self.creds["password"]
            },
            headers={
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()

        data = response.json()
        self._api_token = data["token"]

        # TODO: Also get API keys for SDK operations if needed

    async def create_scan(self, request: ScanRequest) -> int:
        """
        Create Nessus scan using native async calls.

        Maps scan_type to appropriate Nessus configuration:
        - untrusted: No credentials
        - trusted_basic: SSH with no escalation
        - trusted_privileged: SSH with sudo/su escalation
        """
        await self._authenticate()
        client = await self._get_session()

        # Get template UUID (Advanced Scan)
        template_uuid = "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66"

        # Build scan settings
        settings = {
            "name": request.name,
            "text_targets": request.targets,
            "description": request.name,
            "enabled": True,
            "folder_id": 3,  # My Scans
            "scanner_id": 1   # Local scanner
        }

        # Add credentials if provided
        if request.credentials:
            settings["credentials"] = self._build_credentials(request.credentials)

        # Create scan
        response = await client.post(
            f"{self.url}/scans",
            json={
                "uuid": template_uuid,
                "settings": settings
            },
            headers={
                "X-API-Token": self._api_token,
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()

        data = response.json()
        scan_id = data["scan"]["id"]

        return scan_id

    def _build_credentials(self, creds: Dict[str, Any]) -> Dict[str, Any]:
        """Build Nessus credentials structure from request"""
        # TODO: Map credentials dict to Nessus format
        # This is complex nested structure - see manage_credentials.py for reference
        pass

    async def launch_scan(self, scan_id: int) -> str:
        """Launch scan asynchronously"""
        await self._authenticate()
        client = await self._get_session()

        response = await client.post(
            f"{self.url}/scans/{scan_id}/launch",
            headers={"X-API-Token": self._api_token}
        )
        response.raise_for_status()

        data = response.json()
        scan_uuid = data["scan_uuid"]

        return scan_uuid

    async def get_status(self, scan_id: int) -> Dict[str, Any]:
        """Get current scan status"""
        await self._authenticate()
        client = await self._get_session()

        response = await client.get(
            f"{self.url}/scans/{scan_id}",
            headers={"X-API-Token": self._api_token}
        )
        response.raise_for_status()

        data = response.json()
        info = data["info"]

        # Map Nessus status to our status
        nessus_status = info["status"]
        mapped_status = self._map_nessus_status(nessus_status)

        return {
            "status": mapped_status,
            "progress": info.get("progress", 0),
            "uuid": info["uuid"],
            "info": info
        }

    def _map_nessus_status(self, nessus_status: str) -> str:
        """Map Nessus scan states to MCP states"""
        NESSUS_TO_MCP_STATUS = {
            "pending": "queued",
            "running": "running",
            "paused": "running",      # Treat paused as still running
            "completed": "completed",
            "canceled": "failed",
            "stopped": "failed",
            "aborted": "failed",
        }
        return NESSUS_TO_MCP_STATUS.get(nessus_status, "unknown")

    async def export_results(self, scan_id: int, format: str = "nessus") -> bytes:
        """Export scan results"""
        await self._authenticate()
        client = await self._get_session()

        # Request export
        response = await client.post(
            f"{self.url}/scans/{scan_id}/export",
            json={"format": format},
            headers={"X-API-Token": self._api_token}
        )
        response.raise_for_status()

        file_id = response.json()["file"]

        # Poll for export completion
        while True:
            status_response = await client.get(
                f"{self.url}/scans/{scan_id}/export/{file_id}/status",
                headers={"X-API-Token": self._api_token}
            )
            status_response.raise_for_status()

            if status_response.json()["status"] == "ready":
                break

            await asyncio.sleep(2)

        # Download export
        download_response = await client.get(
            f"{self.url}/scans/{scan_id}/export/{file_id}/download",
            headers={"X-API-Token": self._api_token}
        )
        download_response.raise_for_status()

        return download_response.content

    async def stop_scan(self, scan_id: int) -> bool:
        """Stop running scan"""
        await self._authenticate()
        client = await self._get_session()

        response = await client.post(
            f"{self.url}/scans/{scan_id}/stop",
            headers={"X-API-Token": self._api_token}
        )

        return response.status_code == 200

    async def close(self):
        """Cleanup HTTP session"""
        if self._session:
            await self._session.aclose()
```

### 5.3 Testing with Existing Scripts

**Purpose**: Use existing scripts in `nessusAPIWrapper/` for result comparison only

```python
# tests/test_scanner_integration.py
import subprocess
import json
from pathlib import Path

async def test_create_scan_matches_existing():
    """Verify native async implementation matches existing script behavior"""

    # Call native async implementation
    scanner = NessusScanner("http://localhost:8834", {...})
    native_scan_id = await scanner.create_scan(ScanRequest(
        targets="192.168.1.1",
        name="Test Scan"
    ))

    # Call existing script for comparison
    result = subprocess.run([
        "python",
        "../nessusAPIWrapper/manage_scans.py",
        "create",
        "Test Scan Comparison",
        "192.168.1.1"
    ], capture_output=True, text=True)

    # Extract scan_id from script output
    # Example output: "[SUCCESS] New scan ID: 123"
    script_scan_id = int(result.stdout.split("scan ID: ")[1].strip())

    # Compare configurations
    native_config = await scanner.get_scan_config(native_scan_id)
    script_config = await scanner.get_scan_config(script_scan_id)

    # Assert key fields match
    assert native_config["settings"]["text_targets"] == script_config["settings"]["text_targets"]
    assert native_config["settings"]["name"] != script_config["settings"]["name"]  # Different names

    # Cleanup
    await scanner.delete_scan(native_scan_id)
    await scanner.delete_scan(script_scan_id)
```

---

## 6. Observability & Metrics

### 6.1 Prometheus Metrics Endpoint

```python
# api/metrics.py
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

# Define metrics
scans_total = Counter(
    "nessus_scans_total",
    "Total scans submitted",
    ["scan_type", "status"]
)

api_requests_total = Counter(
    "nessus_api_requests_total",
    "Total MCP tool calls",
    ["tool", "status"]
)

active_scans = Gauge(
    "nessus_active_scans",
    "Currently running scans"
)

scanner_instances = Gauge(
    "nessus_scanner_instances",
    "Registered scanner instances",
    ["scanner_type", "enabled"]
)

queue_depth = Gauge(
    "nessus_queue_depth",
    "Tasks in queue",
    ["queue"]  # pending, processing, dead
)

task_duration_seconds = Histogram(
    "nessus_task_duration_seconds",
    "Task execution duration",
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400]  # 1m to 4h
)

ttl_deletions_total = Counter(
    "nessus_ttl_deletions_total",
    "Tasks deleted by TTL cleanup"
)

dlq_size = Gauge(
    "nessus_dlq_size",
    "Tasks in dead letter queue"
)

# Endpoint
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### 6.2 Metrics Integration

```python
# Update metrics throughout codebase

# In tool handlers
@mcp.tool()
async def run_untrusted_scan(...):
    with api_requests_total.labels(tool="run_untrusted_scan", status="success").count_exceptions():
        # Tool logic
        scans_total.labels(scan_type="untrusted", status="queued").inc()
        return result

# In worker
async def process_task(task):
    active_scans.inc()
    start_time = time.time()

    try:
        # Process task
        await ...

        scans_total.labels(scan_type=task.scan_type, status="completed").inc()
        task_duration_seconds.observe(time.time() - start_time)

    except Exception:
        scans_total.labels(scan_type=task.scan_type, status="failed").inc()

    finally:
        active_scans.dec()

# In housekeeping
async def cleanup_expired_tasks():
    deleted = await task_mgr.cleanup_expired_tasks()
    ttl_deletions_total.inc(deleted)

# In queue manager
async def update_queue_metrics():
    """Update queue depth metrics"""
    queue_depth.labels(queue="pending").set(redis.llen("nessus:queue:pending"))
    queue_depth.labels(queue="processing").set(redis.llen("nessus:queue:processing"))
    queue_depth.labels(queue="dead").set(redis.llen("nessus:queue:dead"))
    dlq_size.set(redis.llen("nessus:queue:dead"))
```

---

## 7. Error Handling Guidelines

### 7.1 Tool-Level Error Handling

**TODO**: Define standard error response format and HTTP/MCP error code mapping

**Outline**:
- Standard JSON error body structure
- Error codes (400, 404, 409, 500, etc.)
- Mapping to MCP protocol errors
- Examples for each tool

### 7.2 Worker Error Recovery

**TODO**: Define retry policies, DLQ handling, and human-action triggers

**Outline**:
- Exponential backoff for transient errors
- Max retry count before DLQ
- DLQ triage workflow (manual review, retry, purge)
- Human-action flags for stuck tasks

### 7.3 Redis/Network Failures

**TODO**: Define readiness gating, exponential backoff, circuit-breaker patterns

**Outline**:
- Healthcheck readiness checks (Redis ping, disk space)
- Exponential backoff on connection failures
- Circuit-breaker thresholds (e.g., 5 failures in 60s = open)
- Alert triggers for operations team

### 7.4 Filesystem Issues

**TODO**: Define safeguards for disk-full, permission errors, and remediation

**Outline**:
- Disk space check in `/ready` endpoint (warn at 80%, fail at 90%)
- Permission validation on startup
- Graceful degradation (read-only mode?)
- Remediation procedures (expand volume, clean temp files)

### 7.5 Scanner Errors

**TODO**: Map Nessus errors to MCP failed status with reason codes

**Outline**:
- Nessus authentication failures → failed with "auth_error"
- Nessus scan canceled/paused → map to state machine
- Nessus API rate limits → retry with backoff
- Network timeouts → DLQ after N retries

---

## 8. Complete MCP Tools (Enhanced)

### 8.1 Enhanced Tool Signatures

```python
# tools/scan_tools.py
from fastmcp import FastMCP
from typing import Dict, Any, Optional, List

mcp = FastMCP("Nessus Scanner")

@mcp.tool()
async def run_untrusted_scan(
    targets: str,
    name: str,
    description: str = "",
    schema_profile: str = "brief",
    scanner_type: str = "nessus",
    scanner_instance: Optional[str] = None,
    debug_mode: bool = False,
    idempotency_key: Optional[str] = None  # NEW
) -> Dict[str, Any]:
    """
    Run network-only vulnerability scan (no credentials).

    Supports idempotency via X-Idempotency-Key header or argument.
    Returns existing task if key matches.
    """
    # Extract trace_id and idempotency_key
    trace_id = request.state.trace_id
    idemp_key = extract_idempotency_key(request.headers, locals())

    # ... idempotency check (see section 2.2)

    # Generate task_id
    instance = registry.get_instance(scanner_type, scanner_instance)
    task_id = generate_task_id(scanner_type, instance.instance_id)

    # Create task with trace_id
    task = Task(
        task_id=task_id,
        trace_id=trace_id,  # NEW
        scan_type="untrusted",
        scanner_type=scanner_type,
        scanner_instance_id=instance.instance_id,
        payload={...}
    )

    # ... rest of logic
```

### 8.2 Enhanced Status Tool

```python
@mcp.tool()
async def get_scan_status(task_id: str) -> Dict[str, Any]:
    """
    Get current status of scan task.

    Returns enhanced status including:
    - Scanner instance used
    - Nessus scan_id
    - Progress percentage (when available)
    - Trace ID for debugging
    """
    metadata = await task_mgr.get_task_metadata(task_id)

    # Get queue position if queued
    queue_position = None
    if metadata["status"] == "queued":
        queue_position = await queue.get_position(task_id)

    # Get progress from Nessus if running
    progress = None
    nessus_scan_id = metadata.get("nessus_scan_id")

    if metadata["status"] == "running" and nessus_scan_id:
        # Query Nessus for actual progress
        scanner_instance = registry.get_instance(
            metadata["scanner_type"],
            metadata["scanner_instance_id"]
        )
        scanner = NessusScanner(scanner_instance.url, scanner_instance.credentials)

        status_info = await scanner.get_status(nessus_scan_id)
        progress = status_info.get("progress")

    return {
        "task_id": task_id,
        "trace_id": metadata.get("trace_id"),  # NEW
        "status": metadata["status"],
        "progress": progress,  # NEW: actual from Nessus
        "scanner_instance": metadata.get("scanner_instance_id"),  # NEW
        "nessus_scan_id": nessus_scan_id,  # NEW
        "created_at": metadata.get("created_at"),
        "started_at": metadata.get("started_at"),
        "completed_at": metadata.get("completed_at"),
        "queue_position": queue_position,
        "error_message": metadata.get("error_message")
    }
```

### 8.3 Enhanced Results Tool with Filter Echo

```python
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
    Get scan results in paginated JSON-NL format with filtering.

    First line echoes applied filters so LLMs can reason about deltas.

    Args:
        schema_profile: Predefined schema (minimal|summary|brief|full)
        custom_fields: Custom field list (mutually exclusive with schema_profile)

    Raises:
        ValueError: If both schema_profile and custom_fields are provided
    """
    # Enforce mutual exclusivity
    if schema_profile != "brief" and custom_fields is not None:
        raise ValueError(
            "Cannot specify both schema_profile and custom_fields. "
            "Use schema_profile for predefined schemas OR custom_fields for custom schema."
        )

    # ... existing validation logic (task exists, status=completed, etc.)

    # Determine field list
    fields = custom_fields if custom_fields else get_schema_fields(schema_profile)

    # Generate results
    converter = NessusToJsonNL()
    results = converter.convert(
        nessus_data,
        schema_profile=schema_profile,
        custom_fields=custom_fields,
        filters=filters,
        page=page,
        page_size=page_size
    )

    # First line will include filters_applied for transparency
    # See Section 9 for converter implementation

    return results
```

---

## 9. JSON-NL Converter (Detailed Pseudo-Code)

### 9.1 Converter Implementation

```python
# schema/converter.py
from typing import List, Dict, Any, Optional
import json
import xml.etree.ElementTree as ET

class NessusToJsonNL:
    """Convert Nessus XML to JSON-NL with schema profiles and filtering"""

    # Predefined schema profiles (in order of detail)
    SCHEMAS = {
        "minimal": [
            "host", "plugin_id", "severity", "cve",
            "cvss_score", "exploit_available"
        ],
        "summary": [
            "host", "plugin_id", "severity", "cve", "cvss_score", "exploit_available",
            "plugin_name", "cvss3_base_score", "synopsis"
        ],
        "brief": [
            "host", "plugin_id", "severity", "cve", "cvss_score", "exploit_available",
            "plugin_name", "cvss3_base_score", "synopsis",
            "description", "solution"
        ],
        "full": None  # All fields
    }

    def convert(
        self,
        nessus_data: bytes,
        schema_profile: str = "brief",
        custom_fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 40
    ) -> str:
        """
        Convert Nessus XML to paginated JSON-NL format.

        Returns:
            Multi-line string (JSON-NL format):
            Line 1: Schema definition with filters_applied
            Line 2: Scan metadata
            Lines 3+: Vulnerability data (paginated)
            Last line: Pagination info
        """
        # TODO: Parse .nessus XML with lxml
        root = ET.fromstring(nessus_data)

        # Determine fields to include
        if custom_fields:
            fields = custom_fields
            profile = "custom"
        elif schema_profile == "full":
            fields = None  # All fields
            profile = "full"
        else:
            fields = self.SCHEMAS.get(schema_profile, self.SCHEMAS["brief"])
            profile = schema_profile

        # TODO: Extract all vulnerabilities from XML
        all_vulnerabilities = self._extract_vulnerabilities(root, fields)

        # TODO: Apply filters (before pagination)
        if filters:
            all_vulnerabilities = [
                v for v in all_vulnerabilities
                if self._matches_filters(v, filters)
            ]

        # Calculate pagination
        total_vulns = len(all_vulnerabilities)

        if page == 0:
            # Return all data, no pagination
            page_vulns = all_vulnerabilities
            total_pages = 1
        else:
            # Paginate
            total_pages = (total_vulns + page_size - 1) // page_size
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_vulns = all_vulnerabilities[start_idx:end_idx]

        # Build JSON-NL output
        lines = []

        # Line 1: Schema definition WITH filters_applied
        schema_def = {
            "type": "schema",
            "profile": profile,
            "fields": fields or "all",
            "filters_applied": filters or {},  # Echo filters for LLM reasoning
            "total_vulnerabilities": total_vulns,
            "total_pages": total_pages
        }
        lines.append(json.dumps(schema_def))

        # Line 2: Scan metadata
        scan_meta = self._extract_scan_metadata(root)
        lines.append(json.dumps(scan_meta))

        # Lines 3+: Vulnerability data
        for vuln in page_vulns:
            lines.append(json.dumps(vuln))

        # Last line: Pagination (if applicable)
        if page != 0:
            pagination = {
                "type": "pagination",
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "next_page": page + 1 if page < total_pages else None
            }
            lines.append(json.dumps(pagination))

        return "\n".join(lines)

    def _extract_vulnerabilities(
        self,
        root: ET.Element,
        fields: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Extract vulnerability data from Nessus XML"""
        vulnerabilities = []

        # TODO: Parse ReportHost elements
        for report_host in root.findall(".//ReportHost"):
            host = report_host.get("name")

            # TODO: Parse ReportItem (vulnerabilities)
            for item in report_host.findall("ReportItem"):
                vuln = {
                    "type": "vulnerability",
                    "host": host,
                    "plugin_id": int(item.get("pluginID")),
                    "plugin_name": item.get("pluginName"),
                    "severity": item.get("severity"),
                    "port": item.get("port"),
                    "protocol": item.get("protocol"),
                }

                # TODO: Extract child elements (CVE, CVSS, description, etc.)
                for child in item:
                    vuln[child.tag] = child.text

                # Apply field selection
                if fields:
                    vuln = {k: v for k, v in vuln.items() if k in fields or k == "type"}

                vulnerabilities.append(vuln)

        return vulnerabilities

    def _matches_filters(self, vuln: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if vulnerability matches all filters (AND logic)"""
        for field, filter_value in filters.items():
            if field not in vuln:
                return False

            vuln_value = vuln[field]

            # String filter (case-insensitive substring)
            if isinstance(vuln_value, str) and isinstance(filter_value, str):
                if filter_value.lower() not in vuln_value.lower():
                    return False

            # Number filter (comparison operators)
            elif isinstance(filter_value, str) and filter_value[0] in "<>=":
                # TODO: Parse operator and compare
                try:
                    num_value = float(vuln_value)
                    operator = filter_value[0]
                    if filter_value[1] in "=>":  # >=, <=
                        operator += filter_value[1]
                        compare_value = float(filter_value[2:])
                    else:
                        compare_value = float(filter_value[1:])

                    if operator == ">" and num_value <= compare_value:
                        return False
                    elif operator == ">=" and num_value < compare_value:
                        return False
                    elif operator == "<" and num_value >= compare_value:
                        return False
                    elif operator == "<=" and num_value > compare_value:
                        return False
                    elif operator == "=" and num_value != compare_value:
                        return False

                except (ValueError, TypeError):
                    return False

            # Boolean filter (exact match)
            elif isinstance(filter_value, bool):
                if bool(vuln_value) != filter_value:
                    return False

            # List filter (contains)
            elif isinstance(vuln_value, list):
                found = False
                for item in vuln_value:
                    if str(filter_value).lower() in str(item).lower():
                        found = True
                        break
                if not found:
                    return False

        return True

    def _extract_scan_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """Extract scan-level metadata"""
        # TODO: Extract from NessusClientData_v2/Report elements
        return {
            "type": "scan_metadata",
            "scan_name": root.find(".//Report").get("name"),
            # ... more metadata
        }
```

---

## 10. Python Test Client

### 10.1 Minimal Test Client

```python
# tests/client/mcp_client.py
import httpx
from typing import Dict, Any, Optional

class NessusMCPClient:
    """
    Minimal Python client for testing MCP workflows.

    Wraps MCP HTTP API for easy testing and validation.
    """

    def __init__(self, base_url: str = "http://localhost:8836"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient()

    async def submit_scan(
        self,
        targets: str,
        name: str,
        scan_type: str = "untrusted",
        idempotency_key: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit a scan and return task info"""

        tool_map = {
            "untrusted": "run_untrusted_scan",
            "trusted": "run_trusted_scan",
            "privileged": "run_privileged_scan"
        }

        tool = tool_map[scan_type]

        headers = {}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        response = await self.client.post(
            f"{self.base_url}/tools/{tool}",
            json={"targets": targets, "name": name, **kwargs},
            headers=headers
        )
        response.raise_for_status()

        return response.json()

    async def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get scan status"""
        response = await self.client.post(
            f"{self.base_url}/tools/get_scan_status",
            json={"task_id": task_id}
        )
        response.raise_for_status()
        return response.json()

    async def poll_until_complete(
        self,
        task_id: str,
        timeout: int = 3600,
        poll_interval: int = 30
    ) -> Dict[str, Any]:
        """Poll status until scan completes or times out"""
        import asyncio

        start_time = asyncio.get_event_loop().time()

        while True:
            status = await self.get_status(task_id)

            if status["status"] in {"completed", "failed", "timeout"}:
                return status

            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Scan did not complete in {timeout}s")

            await asyncio.sleep(poll_interval)

    async def get_results(
        self,
        task_id: str,
        page: int = 1,
        filters: Optional[Dict] = None
    ) -> str:
        """Fetch results (JSON-NL string)"""
        response = await self.client.post(
            f"{self.base_url}/tools/get_scan_results",
            json={
                "task_id": task_id,
                "page": page,
                "filters": filters or {}
            }
        )
        response.raise_for_status()
        return response.text

    async def close(self):
        """Cleanup"""
        await self.client.aclose()
```

### 10.2 Example Test Usage

```python
# tests/test_workflow.py
import pytest
from tests.client.mcp_client import NessusMCPClient

@pytest.mark.asyncio
async def test_complete_untrusted_workflow():
    """Test full workflow: submit → poll → retrieve results"""

    client = NessusMCPClient()

    try:
        # Submit scan
        task = await client.submit_scan(
            targets="192.168.1.1",
            name="Integration Test Scan",
            scan_type="untrusted"
        )

        task_id = task["task_id"]
        assert task["status"] == "queued"

        # Poll until complete (with timeout)
        final_status = await client.poll_until_complete(task_id, timeout=600)
        assert final_status["status"] == "completed"

        # Retrieve results
        results = await client.get_results(task_id, page=0)

        # Validate JSON-NL format
        lines = results.strip().split("\n")
        assert len(lines) >= 2  # At least schema + metadata

        # Parse first line (schema)
        import json
        schema_line = json.loads(lines[0])
        assert schema_line["type"] == "schema"
        assert "fields" in schema_line

    finally:
        await client.close()
```

---

## 11. Docker Configuration (Enhanced)

### 11.1 docker-compose.yml

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: nessus-mcp-redis
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - mcp-network

  mcp-api:
    build:
      context: ..
      dockerfile: mcp-server/Dockerfile.api
    container_name: nessus-mcp-api
    ports:
      - "8836:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/app/data
      - LOG_DIR=/app/logs
      - NESSUS_URL=${NESSUS_URL:-http://host.docker.internal:8834}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - mcp-network

  scanner-worker:
    build:
      context: ..
      dockerfile: mcp-server/Dockerfile.worker
    container_name: nessus-mcp-worker
    environment:
      - REDIS_URL=redis://redis:6379
      - NESSUS_URL=${NESSUS_URL:-http://host.docker.internal:8834}
      - DATA_DIR=/app/data
      - LOG_DIR=/app/logs
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import redis; r=redis.from_url('redis://redis:6379'); r.ping()"]
      interval: 30s
      timeout: 10s
      retries: 3
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - mcp-network

networks:
  mcp-network:
    driver: bridge

volumes:
  redis-data:
```

### 11.2 .env.example

```bash
# Nessus Scanner Configuration
NESSUS_URL=http://host.docker.internal:8834

# For Linux users joining external Nessus network:
# NESSUS_URL=http://nessus-scanner:8834

# Redis Configuration (default is fine for most cases)
REDIS_URL=redis://redis:6379

# Data directories (container paths)
DATA_DIR=/app/data
LOG_DIR=/app/logs
```

---

## 12. Implementation Timeline

### Week 1: Core Infrastructure
```
Day 1-2:   Scaffolding, Redis queue, TaskManager with state machine
Day 3-4:   Idempotency system, trace ID middleware
Day 5-6:   Scanner registry, native async Nessus implementation (stubs)
Day 7:     Health checks, basic metrics
```

### Week 2: MCP Tools & Worker
```
Day 8-9:   All 10 MCP tools with idempotency support
Day 10-11: Worker implementation with state transitions
Day 12-13: Native Nessus integration (create, launch, poll, export)
```

### Week 3: Schema & Results
```
Day 14-15: JSON-NL converter with XML parsing
Day 16-17: Filtering, pagination, schema profiles
Day 18-19: TTL housekeeping, DLQ processing
```

### Week 4: Testing & Observability
```
Day 20-21: Python test client, integration tests
Day 22-23: Prometheus metrics, logging cleanup
Day 24-25: Error handling, edge cases
```

### Week 5: Production Hardening
```
Day 26-27: Docker optimization, healthchecks
Day 28-29: Documentation, examples
Day 30:    Final integration test, deployment guide
```

---

## 13. Future Enhancements

### 13.1 API Validation (Pydantic)

**Tighten API validation**: Pydantic models for all tool inputs/outputs; reject profile+custom_fields combos.

```python
from pydantic import BaseModel, Field, validator

class RunUntrustedScanRequest(BaseModel):
    targets: str = Field(..., description="IP addresses or CIDR ranges")
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    schema_profile: str = Field("brief", regex="^(minimal|summary|brief|full)$")
    custom_schema: Optional[Dict[str, List[str]]] = None

    @validator('custom_schema')
    def profile_and_custom_exclusive(cls, v, values):
        if v and values.get('schema_profile') != 'brief':
            raise ValueError("Cannot specify both schema_profile and custom_schema")
        return v

    @validator('targets')
    def validate_targets(cls, v):
        # TODO: Validate IP/CIDR format
        return v
```

### 13.2 OpenAPI Documentation

**OpenAPI docs for the MCP HTTP layer** so non-LLM clients can integrate easily.

```yaml
openapi: 3.0.0
info:
  title: Nessus MCP Server API
  version: 2.2.0
  description: MCP server for Nessus vulnerability scanning

paths:
  /tools/run_untrusted_scan:
    post:
      summary: Submit untrusted scan
      parameters:
        - name: X-Idempotency-Key
          in: header
          schema:
            type: string
        - name: X-Trace-Id
          in: header
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RunUntrustedScanRequest'
      responses:
        '200':
          description: Scan queued
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TaskResponse'
        '409':
          description: Idempotency key conflict

  /metrics:
    get:
      summary: Prometheus metrics
      responses:
        '200':
          description: Metrics in Prometheus format
          content:
            text/plain:
              schema:
                type: string
```

### 13.3 Additional Enhancements

- Webhook notifications for scan completion
- Scan scheduling (cron-like)
- Result aggregation/analytics dashboard
- Additional scanner backends (OpenVAS, Qualys)
- OR filter logic (in addition to AND)
- Regular expression filtering
- Database backend (if file system proves inadequate)

---

## 14. Quick Reference

### 14.1 Key Endpoints

```bash
# Submit scan with idempotency
curl -X POST http://localhost:8836/tools/run_untrusted_scan \
  -H "X-Idempotency-Key: my-retry-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": "192.168.1.1",
    "name": "Test Scan"
  }'

# Check status (with trace_id in response)
curl -X POST http://localhost:8836/tools/get_scan_status \
  -d '{"task_id": "ns_a3f2_20250101_120345_b1c2d3e4"}'

# Get results with filters (echoed in first line)
curl -X POST http://localhost:8836/tools/get_scan_results \
  -d '{
    "task_id": "ns_a3f2_20250101_120345_b1c2d3e4",
    "filters": {"severity": "Critical", "exploit_available": true}
  }'

# Prometheus metrics
curl http://localhost:8836/metrics
```

### 14.2 Redis Inspection

```bash
# Check queue depths
docker exec nessus-mcp-redis redis-cli LLEN nessus:queue:pending
docker exec nessus-mcp-redis redis-cli LLEN nessus:queue:processing
docker exec nessus-mcp-redis redis-cli LLEN nessus:queue:dead

# Check idempotency keys
docker exec nessus-mcp-redis redis-cli KEYS "idemp:*"

# View task data
docker exec nessus-mcp-redis redis-cli HGETALL nessus:tasks:ns_a3f2_20250101_120345_b1c2d3e4
```

### 14.3 Logs

```bash
# API logs (with trace_id)
tail -f mcp-server/logs/api.jsonl | jq -r '.trace_id + " | " + .message'

# Worker logs
tail -f mcp-server/logs/worker.jsonl | jq -r '.task_id + " | " + .message'

# Filter by trace_id
cat mcp-server/logs/api.jsonl | jq -r 'select(.trace_id == "550e8400-...") | .message'
```

---

## Summary of v2.2 Enhancements

This v2.2 architecture adds production-grade features on top of v2.1:

1. ✅ **Idempotency System** - HTTP header OR tool arg, prevents duplicate scans
2. ✅ **Trace IDs** - Per-request tracing through logs, queue, and task metadata
3. ✅ **State Machine Enforcement** - TaskManager as single writer with file locking
4. ✅ **Prometheus Metrics** - 8 metrics on /metrics endpoint
5. ✅ **Native Async Scanner** - Pure async/await, no subprocess calls
6. ✅ **Enhanced Status** - Includes scanner_instance, nessus_scan_id, actual progress
7. ✅ **Filter Echo** - First JSON-NL line includes filters_applied for LLM reasoning
8. ✅ **Test Client** - Minimal Python client for workflow validation
9. ✅ **Error Handling Outline** - 5-section framework (TODOs for implementation)
10. ✅ **Future Enhancements** - Pydantic validation, OpenAPI docs

**Ready for implementation with clear, actionable specifications.**
