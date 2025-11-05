# Phase 1: Real Nessus Integration + Queue

> **Duration**: Week 1 (after Phase 0)
> **Goal**: Replace mock scanner with real async Nessus, add Redis queue and worker
> **Status**: 🔴 Not Started
> **Prerequisites**: Phase 0 complete and verified

---

## Overview

Phase 1 transitions from mock testing to production-ready Nessus integration. We add:
- **Real Nessus Scanner**: Native async (httpx) implementation, no subprocess calls
- **Redis Queue**: FIFO task queue with atomic operations
- **Scanner Worker**: Background service that consumes queue and executes scans
- **Idempotency System**: Prevents duplicate scans on retry
- **Trace ID Middleware**: Per-request tracing through entire lifecycle

**Why This Order?**
- Queue decouples API from execution (scalability)
- Worker enables true async (no blocking tool calls)
- Idempotency enables safe retries (production requirement)
- Trace IDs enable debugging (observability foundation)

---

## Phase 1 Task List

### 1.1: Native Async Nessus Scanner
- [ ] Create `scanners/nessus_scanner.py`
- [ ] Implement authentication (session tokens)
- [ ] Implement `create_scan()` with template UUID
- [ ] Implement `launch_scan()`
- [ ] Implement `get_status()` with progress mapping
- [ ] Implement `export_results()` with polling
- [ ] Implement `stop_scan()` and `delete_scan()`
- [ ] Test against real Nessus instance
- [ ] Compare with existing scripts behavior

### 1.2: Scanner Registry & Configuration
- [ ] Create `scanners/registry.py`
- [ ] Implement `ScannerRegistry` class
- [ ] Load from `config/scanners.yaml`
- [ ] Support multiple instances
- [ ] Implement round-robin selection
- [ ] Add hot-reload on SIGHUP
- [ ] Test registry with multiple scanners

### 1.3: Redis Queue Implementation
- [ ] Create `core/queue.py`
- [ ] Implement `TaskQueue` class
- [ ] `enqueue()` - LPUSH to `nessus:queue`
- [ ] `dequeue()` - BRPOP from `nessus:queue`
- [ ] Dead Letter Queue (DLQ) on `nessus:queue:dead`
- [ ] Test queue operations with Redis

### 1.4: Worker with State Machine
- [ ] Create `worker/scanner_worker.py`
- [ ] Implement main worker loop
- [ ] Consume tasks from queue (BRPOP)
- [ ] Execute scan workflow:
  - [ ] Update state to RUNNING
  - [ ] Create scan via scanner
  - [ ] Launch scan
  - [ ] Poll until complete
  - [ ] Update state to COMPLETED/FAILED
- [ ] Handle errors with DLQ
- [ ] Add graceful shutdown (SIGTERM/SIGINT)
- [ ] Test worker with real Nessus

### 1.5: Idempotency System
- [ ] Create `core/idempotency.py`
- [ ] Implement `IdempotencyManager` class
- [ ] `extract_idempotency_key()` - header OR arg
- [ ] `check()` - validate existing key
- [ ] `store()` - SETNX with 48h TTL
- [ ] Request hash for conflict detection
- [ ] Return 409 on hash mismatch
- [ ] Test idempotent retries

### 1.6: Trace ID Middleware
- [ ] Create `core/middleware.py`
- [ ] Implement `TraceMiddleware`
- [ ] Generate trace_id per request (UUID4)
- [ ] Propagate via `request.state.trace_id`
- [ ] Add to all log messages
- [ ] Add to task metadata
- [ ] Return in X-Trace-Id header
- [ ] Test trace ID flow

### 1.7: Enhanced MCP Tools
- [ ] Update `run_untrusted_scan()`:
  - [ ] Add idempotency_key parameter
  - [ ] Extract trace_id from middleware
  - [ ] Enqueue to Redis (not immediate execution)
  - [ ] Return queue position
- [ ] Update `get_scan_status()`:
  - [ ] Add scanner_instance to response
  - [ ] Add nessus_scan_id to response
  - [ ] Get real progress from Nessus if running
- [ ] Add `list_scanners()` tool
- [ ] Test all tools with real Nessus

### 1.8: Real Nessus Integration Tests
- [ ] Create `tests/integration/test_real_nessus.py`
- [ ] Test full workflow (submit → queue → execute → results)
- [ ] Test idempotent retry (same task_id)
- [ ] Test multiple concurrent scans
- [ ] Test scan timeout handling
- [ ] Compare results with existing scripts

---

## Detailed Implementation

### 1.1: Native Async Nessus Scanner

**File: `scanners/nessus_scanner.py`**
```python
"""Native async Nessus scanner implementation."""
import asyncio
import httpx
from typing import Dict, Any, Optional
from .base import ScannerInterface, ScanRequest


class NessusScanner(ScannerInterface):
    """
    Native async Nessus scanner using httpx.

    No subprocess calls - pure async/await.
    """

    # Template UUIDs (from Nessus API)
    TEMPLATES = {
        "advanced_scan": "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66",
        "basic_network_scan": "731a8e52-3ea6-a291-ec0a-d2ff0619c19d7bd788d6be818b65",
        "web_app_scan": "e9cfb74f-947b-8fa7-f0c7-f3fbbe1c520a878248c99a5ba89c",
    }

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.access_key = access_key
        self.secret_key = secret_key

        self._session: Optional[httpx.AsyncClient] = None
        self._session_token: Optional[str] = None
        self._static_token = "af824aba-e642-4e63-a49b-0810542ad8a5"  # From existing scripts

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create async HTTP session."""
        if not self._session:
            self._session = httpx.AsyncClient(
                verify=False,  # Self-signed cert
                timeout=30.0,
                follow_redirects=True
            )
        return self._session

    async def _authenticate(self) -> None:
        """Authenticate with Nessus and get session token."""
        if self._session_token:
            return  # Already authenticated

        client = await self._get_session()

        # POST /session for web UI authentication
        response = await client.post(
            f"{self.url}/session",
            json={
                "username": self.username,
                "password": self.password
            },
            headers={
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()

        data = response.json()
        self._session_token = data["token"]

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        if not self._session_token:
            raise ValueError("Not authenticated - call _authenticate() first")

        return {
            "X-API-Token": self._static_token,
            "X-Cookie": f"token={self._session_token}",
            "Content-Type": "application/json"
        }

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

        # Get template UUID
        template_uuid = self.TEMPLATES["advanced_scan"]

        # Build scan settings
        settings = {
            "name": request.name,
            "text_targets": request.targets,
            "description": request.description or request.name,
            "enabled": True,
            "folder_id": 3,  # My Scans
            "scanner_id": 1,  # Local scanner
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
            headers=self._build_headers()
        )
        response.raise_for_status()

        data = response.json()
        scan_id = data["scan"]["id"]

        return scan_id

    def _build_credentials(self, creds: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Nessus credentials structure from request.

        Reference: manage_credentials.py for exact format
        """
        # Simplified for Phase 1 - just SSH password
        # TODO Phase 2: Full credential structure with escalation

        return {
            "add": {
                "Host": {
                    "SSH": [
                        {
                            "auth_method": "password",
                            "username": creds.get("username"),
                            "password": creds.get("password"),
                            "elevate_privileges_with": "Nothing",  # No escalation for trusted_basic
                        }
                    ]
                }
            }
        }

    async def launch_scan(self, scan_id: int) -> str:
        """Launch scan asynchronously."""
        await self._authenticate()
        client = await self._get_session()

        response = await client.post(
            f"{self.url}/scans/{scan_id}/launch",
            headers=self._build_headers()
        )
        response.raise_for_status()

        data = response.json()
        scan_uuid = data["scan_uuid"]

        return scan_uuid

    async def get_status(self, scan_id: int) -> Dict[str, Any]:
        """Get current scan status."""
        await self._authenticate()
        client = await self._get_session()

        response = await client.get(
            f"{self.url}/scans/{scan_id}",
            headers=self._build_headers()
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
            "info": info,
        }

    def _map_nessus_status(self, nessus_status: str) -> str:
        """Map Nessus scan states to MCP states."""
        NESSUS_TO_MCP_STATUS = {
            "pending": "queued",
            "running": "running",
            "paused": "running",  # Treat paused as still running
            "completed": "completed",
            "canceled": "failed",
            "stopped": "failed",
            "aborted": "failed",
        }
        return NESSUS_TO_MCP_STATUS.get(nessus_status, "unknown")

    async def export_results(self, scan_id: int) -> bytes:
        """Export scan results in native .nessus format."""
        await self._authenticate()
        client = await self._get_session()

        # Request export
        response = await client.post(
            f"{self.url}/scans/{scan_id}/export",
            json={"format": "nessus"},
            headers=self._build_headers()
        )
        response.raise_for_status()

        file_id = response.json()["file"]

        # Poll for export completion (max 5 minutes)
        for _ in range(150):  # 5 min / 2 sec
            status_response = await client.get(
                f"{self.url}/scans/{scan_id}/export/{file_id}/status",
                headers=self._build_headers()
            )
            status_response.raise_for_status()

            if status_response.json()["status"] == "ready":
                break

            await asyncio.sleep(2)
        else:
            raise TimeoutError(f"Export did not complete in 5 minutes")

        # Download export
        download_response = await client.get(
            f"{self.url}/scans/{scan_id}/export/{file_id}/download",
            headers=self._build_headers()
        )
        download_response.raise_for_status()

        return download_response.content

    async def stop_scan(self, scan_id: int) -> bool:
        """Stop running scan."""
        await self._authenticate()
        client = await self._get_session()

        response = await client.post(
            f"{self.url}/scans/{scan_id}/stop",
            headers=self._build_headers()
        )

        return response.status_code == 200

    async def delete_scan(self, scan_id: int) -> bool:
        """Delete scan."""
        await self._authenticate()
        client = await self._get_session()

        response = await client.delete(
            f"{self.url}/scans/{scan_id}",
            headers=self._build_headers()
        )

        return response.status_code == 200

    async def close(self):
        """Cleanup HTTP session."""
        if self._session:
            await self._session.aclose()
```

**Test File: `tests/integration/test_nessus_scanner.py`**
```python
"""Test real Nessus scanner."""
import pytest
import os
from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nessus_create_and_launch():
    """Test scan creation and launch with real Nessus."""
    scanner = NessusScanner(
        url=os.getenv("NESSUS_URL", "https://localhost:8834"),
        username=os.getenv("NESSUS_USERNAME", "nessus"),
        password=os.getenv("NESSUS_PASSWORD", "nessus")
    )

    try:
        # Create scan
        scan_id = await scanner.create_scan(
            ScanRequest(
                targets="192.168.1.1",
                name="Phase 1 Integration Test",
                scan_type="untrusted"
            )
        )
        assert scan_id > 0, "Scan ID should be positive"

        # Launch scan
        scan_uuid = await scanner.launch_scan(scan_id)
        assert scan_uuid, "Scan UUID should be returned"

        # Check status
        status = await scanner.get_status(scan_id)
        assert status["status"] in ["queued", "running"], f"Unexpected status: {status}"

        # Stop scan (cleanup)
        await scanner.stop_scan(scan_id)

        # Delete scan (cleanup)
        await scanner.delete_scan(scan_id)

    finally:
        await scanner.close()
```

---

### 1.2: Scanner Registry & Configuration

**File: `config/scanners.yaml`**
```yaml
# Scanner instance configuration

nessus:
  - instance_id: prod
    name: "Production Nessus"
    url: https://localhost:8834
    username: ${NESSUS_USERNAME_1}
    password: ${NESSUS_PASSWORD_1}
    enabled: true
    max_concurrent_scans: 10

  # Example: Additional instance
  # - instance_id: dev
  #   name: "Development Nessus"
  #   url: https://nessus-dev:8834
  #   username: ${NESSUS_USERNAME_2}
  #   password: ${NESSUS_PASSWORD_2}
  #   enabled: true
  #   max_concurrent_scans: 5
```

**File: `scanners/registry.py`**
```python
"""Scanner registry for managing multiple scanner instances."""
import os
import signal
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import logging
from .nessus_scanner import NessusScanner
from .mock_scanner import MockNessusScanner

logger = logging.getLogger(__name__)


class ScannerRegistry:
    """
    Registry for scanner instances.

    Supports:
    - Multiple instances of same scanner type
    - Round-robin load balancing
    - Hot-reload on SIGHUP
    """

    def __init__(self, config_file: str = "config/scanners.yaml"):
        self.config_file = Path(config_file)
        self._instances: Dict[str, Dict[str, Any]] = {}
        self._load_config()

        # Setup SIGHUP handler for hot-reload
        signal.signal(signal.SIGHUP, self._handle_reload)

    def _load_config(self) -> None:
        """Load scanner configuration from YAML."""
        if not self.config_file.exists():
            logger.warning(f"Config file not found: {self.config_file}")
            return

        with open(self.config_file) as f:
            config = yaml.safe_load(f)

        # Parse Nessus instances
        for scanner_config in config.get("nessus", []):
            instance_id = scanner_config["instance_id"]

            # Substitute environment variables
            url = scanner_config["url"]
            username = self._expand_env(scanner_config["username"])
            password = self._expand_env(scanner_config["password"])
            enabled = scanner_config.get("enabled", True)

            if enabled:
                scanner = NessusScanner(
                    url=url,
                    username=username,
                    password=password
                )

                key = f"nessus:{instance_id}"
                self._instances[key] = {
                    "scanner": scanner,
                    "config": scanner_config,
                    "last_used": 0
                }

                logger.info(f"Registered scanner: {key}")

    def _expand_env(self, value: str) -> str:
        """Expand ${VAR} environment variables."""
        if value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1]
            return os.getenv(var_name, "")
        return value

    def _handle_reload(self, signum, frame):
        """Handle SIGHUP for config reload."""
        logger.info("Received SIGHUP, reloading scanner config...")
        self._instances.clear()
        self._load_config()

    def get_instance(
        self,
        scanner_type: str = "nessus",
        instance_id: Optional[str] = None
    ) -> Any:
        """
        Get scanner instance (round-robin if instance_id not specified).

        Args:
            scanner_type: Scanner type (e.g., "nessus")
            instance_id: Specific instance ID, or None for round-robin

        Returns:
            Scanner instance

        Raises:
            ValueError: If no instances available
        """
        if instance_id:
            key = f"{scanner_type}:{instance_id}"
            if key not in self._instances:
                raise ValueError(f"Scanner not found: {key}")
            return self._instances[key]["scanner"]

        # Round-robin: get least recently used
        candidates = [
            (key, data) for key, data in self._instances.items()
            if key.startswith(f"{scanner_type}:")
        ]

        if not candidates:
            raise ValueError(f"No enabled {scanner_type} instances")

        # Sort by last_used, pick first
        candidates.sort(key=lambda x: x[1]["last_used"])
        key, data = candidates[0]

        # Update last_used
        data["last_used"] = time.time()

        return data["scanner"]

    def list_instances(
        self,
        scanner_type: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """List all registered scanner instances."""
        results = []

        for key, data in self._instances.items():
            if scanner_type and not key.startswith(f"{scanner_type}:"):
                continue

            config = data["config"]
            results.append({
                "scanner_type": key.split(":")[0],
                "instance_id": config["instance_id"],
                "name": config.get("name", ""),
                "url": config["url"],
                "enabled": config.get("enabled", True),
            })

        return results
```

---

### 1.3: Redis Queue Implementation

**File: `core/queue.py`**
```python
"""Redis-based task queue."""
import json
import redis
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TaskQueue:
    """
    Simple FIFO queue using Redis.

    Uses:
    - nessus:queue - main task queue (LPUSH/BRPOP)
    - nessus:queue:dead - dead letter queue for failed tasks
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.queue_key = "nessus:queue"
        self.dlq_key = "nessus:queue:dead"

    def enqueue(self, task: Dict[str, Any]) -> None:
        """
        Enqueue task for processing.

        Args:
            task: Task dictionary (must be JSON-serializable)
        """
        task_json = json.dumps(task)
        self.redis_client.lpush(self.queue_key, task_json)
        logger.info(f"Enqueued task: {task.get('task_id')}")

    def dequeue(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Dequeue task (blocking).

        Args:
            timeout: Block timeout in seconds

        Returns:
            Task dictionary, or None if timeout
        """
        result = self.redis_client.brpop(self.queue_key, timeout=timeout)

        if not result:
            return None

        _, task_json = result
        task = json.loads(task_json)

        logger.info(f"Dequeued task: {task.get('task_id')}")
        return task

    def move_to_dlq(self, task: Dict[str, Any], error: str) -> None:
        """
        Move failed task to dead letter queue.

        Args:
            task: Failed task
            error: Error message
        """
        task["error"] = error
        task["failed_at"] = datetime.utcnow().isoformat()

        # Use sorted set with timestamp as score
        score = datetime.utcnow().timestamp()
        task_json = json.dumps(task)

        self.redis_client.zadd(self.dlq_key, {task_json: score})
        logger.warning(f"Moved task to DLQ: {task.get('task_id')}, error: {error}")

    def get_queue_depth(self) -> int:
        """Get number of tasks in queue."""
        return self.redis_client.llen(self.queue_key)

    def get_dlq_size(self) -> int:
        """Get number of tasks in DLQ."""
        return self.redis_client.zcard(self.dlq_key)
```

---

### 1.4: Worker with State Machine

**File: `worker/scanner_worker.py`**
```python
"""Background worker for processing scan tasks."""
import asyncio
import signal
import logging
from typing import Optional
from core.queue import TaskQueue
from core.task_manager import TaskManager
from core.types import ScanState
from scanners.registry import ScannerRegistry
from scanners.base import ScanRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScannerWorker:
    """
    Background worker that consumes task queue and executes scans.

    Features:
    - FIFO task processing
    - State machine enforcement
    - Error handling with DLQ
    - Graceful shutdown
    """

    def __init__(
        self,
        queue: TaskQueue,
        task_manager: TaskManager,
        scanner_registry: ScannerRegistry,
        max_retries: int = 3
    ):
        self.queue = queue
        self.task_manager = task_manager
        self.scanner_registry = scanner_registry
        self.max_retries = max_retries
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown."""
        logger.info("Received shutdown signal, finishing current task...")
        self.running = False

    async def run(self) -> None:
        """Main worker loop."""
        logger.info("Worker started, waiting for tasks...")

        while self.running:
            # Dequeue task (blocking with timeout)
            task_data = self.queue.dequeue(timeout=5)

            if not task_data:
                continue  # Timeout, retry

            # Process task
            try:
                await self._process_task(task_data)
            except Exception as e:
                logger.error(f"Fatal error processing task: {e}", exc_info=True)
                self.queue.move_to_dlq(task_data, str(e))

        logger.info("Worker stopped gracefully")

    async def _process_task(self, task_data: dict) -> None:
        """
        Process single task.

        Workflow:
        1. Transition to RUNNING
        2. Create scan via scanner
        3. Launch scan
        4. Poll until complete
        5. Export results
        6. Transition to COMPLETED
        """
        task_id = task_data["task_id"]
        trace_id = task_data["trace_id"]
        payload = task_data["payload"]

        logger.info(f"Processing task: {task_id}, trace_id: {trace_id}")

        try:
            # Get scanner instance
            scanner = self.scanner_registry.get_instance(
                task_data["scanner_type"],
                task_data.get("scanner_instance_id")
            )

            # Transition to RUNNING
            self.task_manager.update_status(
                task_id,
                ScanState.RUNNING
            )

            # Create scan
            scan_id = await scanner.create_scan(
                ScanRequest(
                    targets=payload["targets"],
                    name=payload["name"],
                    scan_type=task_data["scan_type"],
                    description=payload.get("description", ""),
                    credentials=payload.get("credentials"),
                    schema_profile=payload.get("schema_profile", "brief")
                )
            )

            # Update task with scan_id
            self.task_manager.update_status(
                task_id,
                ScanState.RUNNING,
                nessus_scan_id=scan_id
            )

            # Launch scan
            scan_uuid = await scanner.launch_scan(scan_id)
            logger.info(f"Launched scan {scan_id}, UUID: {scan_uuid}")

            # Poll until complete (with timeout)
            timeout = 24 * 3600  # 24 hours
            poll_interval = 30  # 30 seconds
            elapsed = 0

            while elapsed < timeout:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                status = await scanner.get_status(scan_id)
                scanner_status = status["status"]

                if scanner_status == "completed":
                    # Export results
                    results = await scanner.export_results(scan_id)

                    # Save results
                    task_dir = self.task_manager.data_dir / task_id
                    (task_dir / "scan_native.nessus").write_bytes(results)

                    # Transition to COMPLETED
                    self.task_manager.update_status(
                        task_id,
                        ScanState.COMPLETED
                    )

                    logger.info(f"Task completed: {task_id}")
                    return

                elif scanner_status == "failed":
                    # Scanner reported failure
                    self.task_manager.update_status(
                        task_id,
                        ScanState.FAILED,
                        error_message="Scanner reported failure"
                    )
                    return

            # Timeout
            logger.warning(f"Task timeout: {task_id}")
            await scanner.stop_scan(scan_id)
            self.task_manager.update_status(
                task_id,
                ScanState.TIMEOUT
            )

        except Exception as e:
            logger.error(f"Task failed: {task_id}, error: {e}", exc_info=True)
            self.task_manager.update_status(
                task_id,
                ScanState.FAILED,
                error_message=str(e)
            )


# Entry point
async def main():
    """Worker entry point."""
    import os

    queue = TaskQueue(redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))
    task_manager = TaskManager(data_dir=os.getenv("DATA_DIR", "/app/data/tasks"))
    scanner_registry = ScannerRegistry(config_file=os.getenv("SCANNER_CONFIG", "config/scanners.yaml"))

    worker = ScannerWorker(queue, task_manager, scanner_registry)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
```

**File: `mcp-server-source/Dockerfile.worker`**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-worker.txt .
RUN pip install --no-cache-dir -r requirements-worker.txt

# Copy source code
COPY . .

# Run worker
CMD ["python", "-m", "worker.scanner_worker"]
```

**Update: `dev1/docker-compose.yml`** (add worker service)
```yaml
  scanner-worker:
    build:
      context: ../mcp-server-source
      dockerfile: Dockerfile.worker
    container_name: nessus-mcp-worker-dev
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/app/data/tasks
      - SCANNER_CONFIG=/app/config/scanners.yaml
      - LOG_LEVEL=DEBUG
      - NESSUS_USERNAME_1=${NESSUS_USERNAME_1}
      - NESSUS_PASSWORD_1=${NESSUS_PASSWORD_1}
    volumes:
      - ../mcp-server-source:/app:ro
      - ./data:/app/data
      - ./logs:/app/logs
      - ../mcp-server-source/config:/app/config:ro
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
```

---

### 1.5-1.8: Remaining Components

Due to message length, see detailed code in:
- **Idempotency**: [ARCHITECTURE_v2.2.md](./ARCHITECTURE_v2.2.md) Section 2
- **Trace ID Middleware**: [ARCHITECTURE_v2.2.md](./ARCHITECTURE_v2.2.md) Section 3
- **Enhanced Tools**: Update `tools/mcp_server.py` to use queue instead of immediate execution

---

## Phase 1 Completion Checklist

### Deliverables

- [ ] **Real Nessus Scanner**: Async implementation tested
- [ ] **Scanner Registry**: Multi-instance support with hot-reload
- [ ] **Redis Queue**: FIFO with DLQ working
- [ ] **Worker Service**: Consuming queue, executing scans
- [ ] **Idempotency System**: Prevents duplicate scans
- [ ] **Trace ID Middleware**: Per-request tracking
- [ ] **Enhanced Tools**: Queue-based, not immediate execution
- [ ] **Integration Tests**: Real Nessus workflow passes

### Verification Commands

```bash
# 1. Build all services
cd dev1
docker compose build

# 2. Start environment
docker compose up -d

# 3. Check all services healthy
docker compose ps

# 4. Test with real Nessus
cd ../mcp-server-source
python client/test_client.py

# 5. Integration tests
pytest tests/integration/test_real_nessus.py -v

# 6. Check queue depth
docker exec nessus-mcp-redis-dev redis-cli LLEN nessus:queue

# 7. Check worker logs
docker compose logs -f scanner-worker
```

### Success Criteria

✅ **Phase 1 is complete when:**
1. Worker consumes tasks from queue
2. Real Nessus scan executes successfully
3. Task progresses through states: QUEUED → RUNNING → COMPLETED
4. Idempotent retry returns same task_id
5. Trace IDs propagate through entire workflow
6. Integration tests pass with real Nessus

---

## Next Steps

Once Phase 1 is complete:
1. Update [README.md](./README.md) progress tracker
2. Commit: "feat: Complete Phase 1 - Real Nessus Integration + Queue"
3. Tag: `git tag phase-1-complete`
4. Move to [PHASE_2_SCHEMA_RESULTS.md](./PHASE_2_SCHEMA_RESULTS.md)

---

**Phase 1 Status**: 🔴 Not Started → Update as you progress
