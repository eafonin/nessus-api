# Phase 0: Foundation & Mock Infrastructure

> **Duration**: Days 1-2
> **Goal**: Get basic Docker environment running with mocked scan workflow
> **Status**: 🔴 Not Started

---

## Overview

Phase 0 establishes the foundational structure and proves the end-to-end workflow works with a mock scanner. By the end of this phase, you should be able to submit a scan request, poll its status, and see it complete - all without touching real Nessus.

**Why Mock First?**
- Fast iteration (no network delays)
- Deterministic testing (no flaky scans)
- Validates architecture before complexity
- Generates fixture data for later phases

---

## Prerequisites

- [ ] Docker and Docker Compose installed
- [ ] Python 3.11+ available locally (for testing)
- [ ] Git repository cloned
- [ ] Read [README.md](./README.md) completely
- [ ] Reviewed [ARCHITECTURE_v2.2.md](./ARCHITECTURE_v2.2.md)

---

## Phase 0 Task List

### 0.1: Project Structure Setup
- [ ] Create `mcp-server-source/` directory
- [ ] Create `dev1/` directory
- [ ] Create `prod/` directory (placeholder for now)
- [ ] Create subdirectories:
  - [ ] `mcp-server-source/scanners/`
  - [ ] `mcp-server-source/core/`
  - [ ] `mcp-server-source/schema/`
  - [ ] `mcp-server-source/tools/`
  - [ ] `mcp-server-source/worker/`
  - [ ] `mcp-server-source/client/`
  - [ ] `mcp-server-source/tests/`
  - [ ] `mcp-server-source/tests/fixtures/`
  - [ ] `mcp-server-source/config/`
- [ ] Create all `__init__.py` files
- [ ] Create `pyproject.toml` with import-linter config
- [ ] Create three requirements files
- [ ] Test import structure with `import-linter`

### 0.2: Core Data Structures
- [ ] Create `core/types.py` with:
  - [ ] `ScanState` enum (QUEUED, RUNNING, COMPLETED, FAILED, TIMEOUT)
  - [ ] `VALID_TRANSITIONS` dictionary
  - [ ] `StateTransitionError` exception
  - [ ] `Task` dataclass
- [ ] Test state machine logic manually

### 0.3: Mock Scanner Implementation
- [ ] Create `scanners/base.py`:
  - [ ] `ScanRequest` dataclass
  - [ ] `ScannerInterface` abstract class
  - [ ] All 6 abstract methods defined
- [ ] Create `scanners/mock_scanner.py`:
  - [ ] `MockNessusScanner` class
  - [ ] `create_scan()` - returns incremental IDs
  - [ ] `launch_scan()` - triggers async progression
  - [ ] `_simulate_scan()` - background task (5 seconds, 25/50/75/100%)
  - [ ] `get_status()` - returns current state
  - [ ] `export_results()` - returns mock XML or fixture file
  - [ ] `stop_scan()` and `delete_scan()` stubs
- [ ] Create `tests/fixtures/sample_scan.nessus` (minimal valid XML)
- [ ] Test mock scanner in isolation (pytest)

### 0.4: Task Manager (Simplified)
- [ ] Create `core/task_manager.py`:
  - [ ] `generate_task_id()` function
  - [ ] `TaskManager` class with `data_dir` parameter
  - [ ] `create_task()` - creates directory + task.json
  - [ ] `get_task()` - reads task.json
  - [ ] `update_status()` - validates state transition, updates timestamps
  - [ ] `_task_to_dict()` - serialization helper
- [ ] Test task creation and status updates
- [ ] Verify file locking works (multiple processes)

### 0.5: Simple MCP Tool
- [ ] Create `tools/mcp_server.py`:
  - [ ] Import FastMCP
  - [ ] Initialize TaskManager and MockNessusScanner
  - [ ] Implement `run_untrusted_scan()`:
    - [ ] Generate trace_id and task_id
    - [ ] Create Task object
    - [ ] Save task with TaskManager
    - [ ] Call mock_scanner.create_scan()
    - [ ] Update task status to RUNNING
    - [ ] Call mock_scanner.launch_scan()
    - [ ] Return task info dict
  - [ ] Implement `get_scan_status()`:
    - [ ] Retrieve task from TaskManager
    - [ ] Get live progress from mock_scanner if running
    - [ ] Check if mock scan completed
    - [ ] Update task status if completed
    - [ ] Return status dict
- [ ] Test tools locally with FastMCP dev mode

### 0.6: Development Docker Setup
- [ ] Create `mcp-server-source/Dockerfile.api`:
  - [ ] Base: python:3.11-slim
  - [ ] Copy requirements-api.txt
  - [ ] Install dependencies
  - [ ] Copy source code
  - [ ] Expose port 8000
  - [ ] Add healthcheck (curl /health)
  - [ ] CMD: uvicorn with reload
- [ ] Create `dev1/docker-compose.yml`:
  - [ ] Redis service (7-alpine)
  - [ ] MCP API service
  - [ ] Volume mount for hot reload
  - [ ] Volume for data persistence
  - [ ] Environment variables
  - [ ] Health checks
  - [ ] Port 8835 exposed
- [ ] Create `dev1/.env.dev`
- [ ] Test build: `docker compose build`
- [ ] Test run: `docker compose up`
- [ ] Verify FastMCP server starts (check logs)
- [ ] Test hot reload (change code, see reload in logs)

### 0.7: Simple Test Client
- [ ] Create `mcp-server-source/client/test_client.py`:
  - [ ] `NessusMCPClient` class
  - [ ] `__init__()` with httpx.AsyncClient
  - [ ] `submit_scan()` - POST to /tools/run_untrusted_scan
  - [ ] `get_status()` - POST to /tools/get_scan_status
  - [ ] `poll_until_complete()` - loop with timeout
  - [ ] `close()` - cleanup
  - [ ] `main()` - example usage
- [ ] Test client standalone (requires Docker running)
- [ ] Verify client can submit and poll successfully

### 0.8: Phase 0 Integration Test
- [ ] Create `tests/test_phase0_integration.py`:
  - [ ] Import pytest and test_client
  - [ ] `test_mock_scan_workflow()` async function
  - [ ] Submit scan, assert task_id returned
  - [ ] Poll until complete, assert status=completed
  - [ ] Verify progress reaches 100%
- [ ] Run integration test: `pytest tests/test_phase0_integration.py -v`
- [ ] Test should pass in <30 seconds

---

## Detailed Implementation

### 0.1: Project Structure Setup

**Commands:**
```bash
cd /home/nessus/projects/nessus-api

# Create environment directories
mkdir -p dev1 prod

# Source directories already exist in mcp-server/
# Just need to add missing subdirectories
cd mcp-server
mkdir -p client tests/fixtures tests/unit tests/integration

# Verify structure
ls -la
```

**File: `mcp-server/pyproject.toml`**
```toml
[tool.import-linter]
root_packages = ["scanners", "core", "schema", "tools", "worker"]

[[tool.import-linter.contracts]]
name = "Layer boundaries"
type = "layers"
layers = [
    "tools",
    "worker",
    "core | schema | scanners",
]

[[tool.import-linter.contracts]]
name = "No circular dependencies"
type = "independence"
modules = [
    "scanners",
    "core",
    "schema",
]
```

**File: `mcp-server/requirements-api.txt`** (already exists, verify contents)
```txt
# FastMCP Framework
fastmcp>=0.3.0

# HTTP Server
uvicorn>=0.30.0
starlette>=0.37.0

# Async HTTP Client
httpx>=0.27.0

# Redis Client
redis>=5.0.0

# Configuration
pyyaml>=6.0.1

# Observability
structlog>=24.1.0
prometheus-client>=0.20.0
```

**File: `mcp-server-source/requirements-worker.txt`**
```txt
# Async HTTP Client
httpx>=0.27.0

# Redis Client
redis>=5.0.0

# Configuration
pyyaml>=6.0.1

# Logging
structlog>=24.1.0
```

**File: `mcp-server-source/requirements-dev.txt`**
```txt
# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
inline-snapshot>=0.12.0

# Code Quality
import-linter>=2.0.0
black>=24.0.0
mypy>=1.8.0

# Dev Client
httpx>=0.27.0
```

---

### 0.2: Core Data Structures

**File: `mcp-server-source/core/types.py`**
```python
"""Core type definitions."""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional


class ScanState(Enum):
    """Valid scan states."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Valid state transitions
VALID_TRANSITIONS: Dict[ScanState, set[ScanState]] = {
    ScanState.QUEUED: {ScanState.RUNNING, ScanState.FAILED},
    ScanState.RUNNING: {ScanState.COMPLETED, ScanState.FAILED, ScanState.TIMEOUT},
    ScanState.COMPLETED: set(),  # Terminal state
    ScanState.FAILED: set(),     # Terminal state
    ScanState.TIMEOUT: set(),    # Terminal state
}


class StateTransitionError(Exception):
    """Raised when invalid state transition is attempted."""
    pass


@dataclass
class Task:
    """Task representation."""
    task_id: str
    trace_id: str
    scan_type: str
    scanner_type: str
    scanner_instance_id: str
    status: str
    payload: Dict[str, Any]
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    nessus_scan_id: Optional[int] = None
    error_message: Optional[str] = None
```

**Test File: `tests/test_types.py`**
```python
"""Test core types."""
import pytest
from core.types import ScanState, VALID_TRANSITIONS, StateTransitionError


def test_valid_transitions():
    """Test state machine transitions."""
    # Valid: QUEUED → RUNNING
    assert ScanState.RUNNING in VALID_TRANSITIONS[ScanState.QUEUED]

    # Valid: RUNNING → COMPLETED
    assert ScanState.COMPLETED in VALID_TRANSITIONS[ScanState.RUNNING]

    # Invalid: COMPLETED → anything (terminal)
    assert len(VALID_TRANSITIONS[ScanState.COMPLETED]) == 0

    # Invalid: RUNNING → QUEUED (no backwards)
    assert ScanState.QUEUED not in VALID_TRANSITIONS[ScanState.RUNNING]
```

---

### 0.3: Mock Scanner Implementation

**File: `scanners/base.py`**
```python
"""Scanner interface definition."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class ScanRequest:
    """Unified scan request structure."""
    targets: str
    name: str
    scan_type: str = "untrusted"
    description: str = ""
    credentials: Optional[Dict[str, Any]] = None
    schema_profile: str = "brief"


class ScannerInterface(ABC):
    """Abstract scanner interface."""

    @abstractmethod
    async def create_scan(self, request: ScanRequest) -> int:
        """Create scan, return scanner's scan_id."""
        pass

    @abstractmethod
    async def launch_scan(self, scan_id: int) -> str:
        """Launch scan, return scan_uuid."""
        pass

    @abstractmethod
    async def get_status(self, scan_id: int) -> Dict[str, Any]:
        """
        Get scan status and progress.

        Returns:
            {
                "status": "pending|running|completed",
                "progress": 0-100,
                "uuid": "...",
                "info": {...}
            }
        """
        pass

    @abstractmethod
    async def export_results(self, scan_id: int) -> bytes:
        """Export scan results in native format."""
        pass

    @abstractmethod
    async def stop_scan(self, scan_id: int) -> bool:
        """Stop running scan."""
        pass

    @abstractmethod
    async def delete_scan(self, scan_id: int) -> bool:
        """Delete scan."""
        pass
```

**File: `scanners/mock_scanner.py`**
```python
"""Mock scanner for testing and development."""
import asyncio
from pathlib import Path
from typing import Dict, Any
from .base import ScannerInterface, ScanRequest


class MockNessusScanner(ScannerInterface):
    """Mock Nessus scanner using fixture files."""

    def __init__(self, fixtures_dir: str = "tests/fixtures", scan_duration: int = 5):
        self.fixtures_dir = Path(fixtures_dir)
        self.scan_duration = scan_duration
        self._scans: Dict[int, Dict[str, Any]] = {}
        self._scan_counter = 1000

    async def create_scan(self, request: ScanRequest) -> int:
        """Create mock scan."""
        scan_id = self._scan_counter
        self._scan_counter += 1

        self._scans[scan_id] = {
            "id": scan_id,
            "name": request.name,
            "targets": request.targets,
            "scan_type": request.scan_type,
            "status": "pending",
            "progress": 0,
            "uuid": f"mock-uuid-{scan_id}",
        }

        await asyncio.sleep(0.1)  # Simulate API delay
        return scan_id

    async def launch_scan(self, scan_id: int) -> str:
        """Launch mock scan."""
        if scan_id not in self._scans:
            raise ValueError(f"Scan {scan_id} not found")

        self._scans[scan_id]["status"] = "running"
        self._scans[scan_id]["progress"] = 10

        # Simulate scan completion after duration
        asyncio.create_task(self._simulate_scan(scan_id))

        await asyncio.sleep(0.1)
        return self._scans[scan_id]["uuid"]

    async def _simulate_scan(self, scan_id: int):
        """Simulate scan progression."""
        interval = self.scan_duration / 4
        for progress in [25, 50, 75, 100]:
            await asyncio.sleep(interval)
            if scan_id in self._scans:
                self._scans[scan_id]["progress"] = progress

        if scan_id in self._scans:
            self._scans[scan_id]["status"] = "completed"

    async def get_status(self, scan_id: int) -> Dict[str, Any]:
        """Get mock scan status."""
        if scan_id not in self._scans:
            raise ValueError(f"Scan {scan_id} not found")

        scan = self._scans[scan_id]
        return {
            "status": scan["status"],
            "progress": scan["progress"],
            "uuid": scan["uuid"],
            "info": scan,
        }

    async def export_results(self, scan_id: int) -> bytes:
        """Return mock .nessus file."""
        # Load fixture file if exists
        fixture_file = self.fixtures_dir / "sample_scan.nessus"
        if fixture_file.exists():
            return fixture_file.read_bytes()

        # Fallback: minimal mock XML
        return b"""<?xml version="1.0" ?>
<NessusClientData_v2>
  <Report name="Mock Scan">
    <ReportHost name="192.168.1.1">
      <ReportItem pluginID="12345" pluginName="Mock Vulnerability" severity="2">
        <description>Mock vulnerability for testing</description>
        <cve>CVE-2023-12345</cve>
        <cvss_base_score>7.5</cvss_base_score>
        <exploit_available>true</exploit_available>
        <solution>Update to latest version</solution>
      </ReportItem>
    </ReportHost>
  </Report>
</NessusClientData_v2>"""

    async def stop_scan(self, scan_id: int) -> bool:
        """Stop mock scan."""
        if scan_id in self._scans:
            self._scans[scan_id]["status"] = "stopped"
            return True
        return False

    async def delete_scan(self, scan_id: int) -> bool:
        """Delete mock scan."""
        if scan_id in self._scans:
            del self._scans[scan_id]
            return True
        return False
```

**Fixture File: `tests/fixtures/sample_scan.nessus`**
```xml
<?xml version="1.0" ?>
<NessusClientData_v2>
  <Report name="Sample Mock Scan">
    <ReportHost name="192.168.1.1">
      <ReportItem pluginID="10267" pluginName="SSH Server Type and Version Information" severity="0">
        <description>It is possible to obtain information about the remote SSH server.</description>
        <plugin_output>SSH version : SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5</plugin_output>
        <solution>n/a</solution>
      </ReportItem>
      <ReportItem pluginID="22964" pluginName="Service Detection" severity="0">
        <description>The remote service could be identified.</description>
        <port>22</port>
        <protocol>tcp</protocol>
      </ReportItem>
      <ReportItem pluginID="51192" pluginName="SSL Certificate Cannot Be Trusted" severity="2">
        <description>The SSL certificate is self-signed.</description>
        <cve>CVE-2023-99999</cve>
        <cvss_base_score>5.0</cvss_base_score>
        <cvss3_base_score>5.3</cvss3_base_score>
        <exploit_available>false</exploit_available>
        <solution>Purchase or generate a proper certificate.</solution>
      </ReportItem>
    </ReportHost>
  </Report>
</NessusClientData_v2>
```

---

### 0.4: Task Manager (Simplified)

**File: `core/task_manager.py`**
```python
"""Task manager with file-based storage."""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from .types import Task, ScanState, VALID_TRANSITIONS, StateTransitionError


def generate_task_id(scanner_type: str, instance_id: str) -> str:
    """Generate unique task ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_suffix = uuid.uuid4().hex[:8]
    type_prefix = scanner_type[:2].lower()
    instance_prefix = instance_id[:4].lower()
    return f"{type_prefix}_{instance_prefix}_{timestamp}_{random_suffix}"


class TaskManager:
    """Manages task lifecycle with file-based storage."""

    def __init__(self, data_dir: str = "/app/data/tasks"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def create_task(self, task: Task) -> None:
        """Create new task directory and metadata file."""
        task_dir = self.data_dir / task.task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        task_file = task_dir / "task.json"
        with open(task_file, "w") as f:
            json.dump(self._task_to_dict(task), f, indent=2)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task metadata."""
        task_file = self.data_dir / task_id / "task.json"
        if not task_file.exists():
            return None

        with open(task_file) as f:
            data = json.load(f)

        return Task(**data)

    def update_status(
        self,
        task_id: str,
        new_state: ScanState,
        **metadata
    ) -> None:
        """Update task status with state machine validation."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        current_state = ScanState(task.status)

        # Validate transition
        if new_state not in VALID_TRANSITIONS.get(current_state, set()):
            raise StateTransitionError(
                f"Invalid transition: {current_state.value} → {new_state.value}"
            )

        # Update timestamps
        if new_state == ScanState.RUNNING:
            task.started_at = datetime.utcnow().isoformat()
        elif new_state in {ScanState.COMPLETED, ScanState.FAILED, ScanState.TIMEOUT}:
            task.completed_at = datetime.utcnow().isoformat()

        task.status = new_state.value

        # Update additional metadata
        for key, value in metadata.items():
            if hasattr(task, key):
                setattr(task, key, value)

        # Write back
        task_file = self.data_dir / task_id / "task.json"
        with open(task_file, "w") as f:
            json.dump(self._task_to_dict(task), f, indent=2)

    @staticmethod
    def _task_to_dict(task: Task) -> dict:
        """Convert Task to dict for JSON serialization."""
        return {
            "task_id": task.task_id,
            "trace_id": task.trace_id,
            "scan_type": task.scan_type,
            "scanner_type": task.scanner_type,
            "scanner_instance_id": task.scanner_instance_id,
            "status": task.status,
            "payload": task.payload,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "nessus_scan_id": task.nessus_scan_id,
            "error_message": task.error_message,
        }
```

---

### 0.5: Simple MCP Tool

**File: `tools/mcp_server.py`**
```python
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
```

---

### 0.6: Development Docker Setup

**File: `mcp-server/Dockerfile.api`** (already exists, verify/update)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Copy source code
COPY . .

# Create data directory
RUN mkdir -p /app/data/tasks

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=2)"

# Run server (can be overridden in docker-compose)
CMD ["uvicorn", "tools.mcp_server:mcp.app", "--host", "0.0.0.0", "--port", "8000"]
```

**File: `dev1/docker-compose.yml`**
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: nessus-mcp-redis-dev
    ports:
      - "6379:6379"
    volumes:
      - redis_data_dev:/data
    command: redis-server --appendonly yes --maxmemory 256mb
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

  mcp-api:
    build:
      context: ../mcp-server
      dockerfile: Dockerfile.api
    container_name: nessus-mcp-api-dev
    ports:
      - "8835:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/app/data/tasks
      - LOG_LEVEL=DEBUG
      - ENVIRONMENT=development
    volumes:
      # Hot reload (mount source as read-only)
      - ../mcp-server:/app:ro
      # Data persistence
      - ./data:/app/data
      # Logs
      - ./logs:/app/logs
    depends_on:
      redis:
        condition: service_healthy
    # Override CMD for hot reload
    command: uvicorn tools.mcp_server:mcp.app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped

volumes:
  redis_data_dev:
    driver: local
```

**File: `dev1/.env.dev`**
```bash
# Development Environment Configuration

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Redis
REDIS_URL=redis://redis:6379

# Storage
DATA_DIR=/app/data/tasks

# Scanner (mock in Phase 0)
SCANNER_TYPE=mock
```

**Test Commands:**
```bash
# Build
cd dev1
docker compose build

# Start
docker compose up

# Check logs
docker compose logs -f mcp-api

# Check health
curl http://localhost:8835/health

# Stop
docker compose down
```

---

### 0.7: Simple Test Client

**File: `mcp-server/client/test_client.py`**
```python
"""Simple HTTP test client for MCP server."""
import asyncio
import httpx
from typing import Dict, Any


class NessusMCPClient:
    """Simple HTTP client for testing MCP server."""

    def __init__(self, base_url: str = "http://localhost:8835"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def submit_scan(
        self,
        targets: str,
        name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit untrusted scan."""
        response = await self.client.post(
            f"{self.base_url}/tools/call",
            json={
                "name": "run_untrusted_scan",
                "arguments": {
                    "targets": targets,
                    "name": name,
                    **kwargs
                }
            }
        )
        response.raise_for_status()
        result = response.json()

        # FastMCP wraps response in content array
        if "content" in result and len(result["content"]) > 0:
            return result["content"][0].get("data", result)
        return result

    async def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get scan status."""
        response = await self.client.post(
            f"{self.base_url}/tools/call",
            json={
                "name": "get_scan_status",
                "arguments": {"task_id": task_id}
            }
        )
        response.raise_for_status()
        result = response.json()

        # FastMCP wraps response
        if "content" in result and len(result["content"]) > 0:
            return result["content"][0].get("data", result)
        return result

    async def poll_until_complete(
        self,
        task_id: str,
        timeout: int = 300,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """Poll status until scan completes."""
        start_time = asyncio.get_event_loop().time()

        while True:
            status = await self.get_status(task_id)

            if "error" in status:
                raise ValueError(f"Task error: {status['error']}")

            if status["status"] in {"completed", "failed", "timeout"}:
                return status

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Scan did not complete in {timeout}s")

            progress_str = f"{status.get('progress', 'N/A')}%" if status.get('progress') else "N/A"
            print(f"[{elapsed:.1f}s] Status: {status['status']}, Progress: {progress_str}")
            await asyncio.sleep(poll_interval)

    async def close(self):
        """Cleanup."""
        await self.client.aclose()


# Example usage
async def main():
    """Example workflow."""
    client = NessusMCPClient()

    try:
        print("=" * 60)
        print("Phase 0: Mock Scan Workflow Test")
        print("=" * 60)

        # Submit scan
        print("\n1. Submitting scan...")
        task = await client.submit_scan(
            targets="192.168.1.1",
            name="Phase 0 Test Scan"
        )
        print(f"   ✓ Task submitted: {task['task_id']}")
        print(f"   ✓ Trace ID: {task['trace_id']}")
        print(f"   ✓ Scanner: {task['scanner_instance']}")

        # Poll until complete
        print("\n2. Polling status...")
        final_status = await client.poll_until_complete(task["task_id"], timeout=60)

        print("\n3. Final Status:")
        print(f"   ✓ Status: {final_status['status']}")
        print(f"   ✓ Progress: {final_status.get('progress', 'N/A')}%")
        print(f"   ✓ Scan ID: {final_status.get('nessus_scan_id')}")
        print(f"   ✓ Duration: {final_status['started_at']} → {final_status['completed_at']}")

        print("\n" + "=" * 60)
        print("✓ Phase 0 Test PASSED")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

**Run Test:**
```bash
# Ensure Docker is running
cd dev1
docker compose up -d

# Run client
cd ../mcp-server
python client/test_client.py
```

---

### 0.8: Phase 0 Integration Test

**File: `tests/test_phase0_integration.py`**
```python
"""Phase 0 integration test."""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.test_client import NessusMCPClient


@pytest.mark.asyncio
async def test_mock_scan_workflow():
    """Test complete mock scan workflow."""
    client = NessusMCPClient()

    try:
        # Submit scan
        task = await client.submit_scan(
            targets="192.168.1.1",
            name="Integration Test Scan"
        )

        assert "task_id" in task, "Task ID not returned"
        assert "trace_id" in task, "Trace ID not returned"
        assert task["status"] == "queued", f"Unexpected status: {task['status']}"
        assert task["scanner_instance"] == "mock", "Wrong scanner instance"

        # Poll until complete
        final_status = await client.poll_until_complete(
            task["task_id"],
            timeout=30  # Mock scan should complete in <10s
        )

        assert final_status["status"] == "completed", f"Scan did not complete: {final_status}"
        assert final_status.get("progress") == 100, "Progress not 100%"
        assert final_status["nessus_scan_id"] is not None, "No scan ID"
        assert final_status["started_at"] is not None, "No start time"
        assert final_status["completed_at"] is not None, "No completion time"

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_status_nonexistent_task():
    """Test status check for non-existent task."""
    client = NessusMCPClient()

    try:
        status = await client.get_status("nonexistent_task_id")
        assert "error" in status, "Should return error for non-existent task"
        assert "not found" in status["error"].lower()

    finally:
        await client.close()


if __name__ == "__main__":
    # Run with: pytest tests/test_phase0_integration.py -v
    pytest.main([__file__, "-v", "-s"])
```

**Run Integration Tests:**
```bash
# Ensure Docker is running
cd dev1
docker compose up -d

# Run tests
cd ../mcp-server
pytest tests/test_phase0_integration.py -v -s

# Expected output:
# tests/test_phase0_integration.py::test_mock_scan_workflow PASSED
# tests/test_phase0_integration.py::test_get_status_nonexistent_task PASSED
```

---

## Phase 0 Completion Checklist

### Deliverables

- [ ] **Project Structure**: All directories and files created
- [ ] **Core Types**: ScanState enum, Task dataclass working
- [ ] **Mock Scanner**: Creates, launches, and completes scans
- [ ] **Task Manager**: File-based storage with state validation
- [ ] **MCP Tools**: `run_untrusted_scan()` and `get_scan_status()` working
- [ ] **Docker Environment**: Dev compose stack builds and runs
- [ ] **Test Client**: Can submit scans and poll status
- [ ] **Integration Test**: Pytest passes (both tests)

### Verification Commands

```bash
# 1. Import linter passes
cd mcp-server-source
import-linter

# 2. Docker builds successfully
cd ../dev1
docker compose build

# 3. Docker runs successfully
docker compose up -d
docker compose ps  # Should show both services healthy

# 4. Manual test works
cd ../mcp-server-source
python client/test_client.py  # Should show "Phase 0 Test PASSED"

# 5. Pytest passes
pytest tests/test_phase0_integration.py -v  # Both tests should pass

# 6. Cleanup
cd ../dev1
docker compose down
```

### Success Criteria

✅ **Phase 0 is complete when:**
1. All checkboxes in "Phase 0 Task List" are marked
2. All deliverables are verified
3. Integration test passes consistently
4. Manual test client shows successful workflow
5. No import boundary violations
6. Docker environment stable (no crashes/restarts)

---

## Next Steps

Once Phase 0 is complete:
1. Update [README.md](./README.md) progress tracker
2. Commit all code with message: "feat: Complete Phase 0 - Foundation & Mock Infrastructure"
3. Tag commit: `git tag phase-0-complete`
4. Move to [PHASE_1_REAL_NESSUS.md](./PHASE_1_REAL_NESSUS.md)

---

## Troubleshooting

### Issue: Docker build fails
**Symptoms**: `docker compose build` fails with dependency errors
**Solutions**:
- Verify Python 3.11 base image pulls correctly
- Check requirements files have no typos
- Try: `docker compose build --no-cache`

### Issue: Mock scanner never completes
**Symptoms**: Scan stuck in "running" state
**Solutions**:
- Check `_simulate_scan()` task is actually running
- Verify `scan_duration` parameter (default 5 seconds)
- Check container logs: `docker compose logs mcp-api`

### Issue: Test client can't connect
**Symptoms**: Connection refused on port 8835
**Solutions**:
- Verify Docker is running: `docker compose ps`
- Check port mapping: `docker compose port mcp-api 8000`
- Check logs: `docker compose logs mcp-api`
- Verify FastMCP started: Look for "Uvicorn running" in logs

### Issue: State transition errors
**Symptoms**: `StateTransitionError` in logs
**Solutions**:
- Review VALID_TRANSITIONS in core/types.py
- Check task.json to see current state
- Verify state machine logic in task_manager.py

### Issue: Import linter failures
**Symptoms**: `import-linter` reports violations
**Solutions**:
- Check pyproject.toml layer definitions
- Verify no circular imports
- Use absolute imports (not relative) between packages

---

## Notes for Next Phase

**Carry Forward to Phase 1:**
- Replace MockNessusScanner with real async Nessus implementation
- Add Redis queue (currently bypassed - immediate execution)
- Add Worker service to consume queue
- Implement idempotency system
- Add trace ID middleware

**Keep from Phase 0:**
- Project structure (perfect as-is)
- Core types and state machine
- Task manager (will enhance, not replace)
- Test client (will extend with more features)
- Docker structure (just add worker service)

---

**Phase 0 Status**: 🔴 Not Started → Update to 🟡 In Progress → Update to 🟢 Complete
