# Nessus MCP Server - Architecture v2.0 (Docker-Optimized)

> **Purpose**: Docker-based MCP server with Redis queue, enabling rapid iterative development with Claude agents
> **Priority**: Working prototype first, then iterate with tests
> **Target Workflow**: Untrusted scan → Status polling → Default schema results

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
│  │  │  MCP HTTP API   │  │  Redis Queue     │            │ │
│  │  │  Port: 8835     │──│  Port: 6379      │            │ │
│  │  │  (FastMCP)      │  │  - Task Queue    │            │ │
│  │  └─────────────────┘  │  - Dead Letter Q  │            │ │
│  │           │           └──────────────────┘            │ │
│  │           │                     │                      │ │
│  │  ┌─────────────────────────────┴────────┐            │ │
│  │  │         Shared Volume: /app/data      │            │ │
│  │  │  - tasks/{task_id}/                   │            │ │
│  │  │  - logs/                              │            │ │
│  │  └───────────────┬───────────────────────┘            │ │
│  │                  │                                     │ │
│  │  ┌───────────────▼──────────┐  ┌──────────────────┐  │ │
│  │  │   Scanner Worker         │  │  Existing Nessus  │  │ │
│  │  │   (Queue Consumer)       │──│  Port: 8834       │  │ │
│  │  │   - Process Queue        │  │  (External)       │  │ │
│  │  │   - Execute Scans        │  └──────────────────┘  │ │
│  │  └──────────────────────────┘                         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions
- **Redis** for queue (robust, handles concurrency, persistent)
- **Shared volume** for file storage (simple, direct access)
- **Single worker** initially (can scale later)
- **Dead letter queue** for failed tasks (LLM retry opportunity)

---

## 2. Phased Implementation Plan (Optimized for Quick Prototype)

### Phase 0: Minimal Working Prototype (Week 1)
**Goal**: One complete workflow working end-to-end

```python
# Workflow: Untrusted scan → Poll status → Get results (default schema)
# No auth, no filtering, no pagination, just basics working
```

Components:
1. Basic Docker Compose setup
2. Minimal FastMCP server with 3 tools
3. Redis queue setup
4. Simple worker that calls existing scripts
5. File storage for results

### Phase 1: Core Infrastructure (Days 1-3)
```python
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

  mcp-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8835:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/app/data
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis

  scanner-worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - REDIS_URL=redis://redis:6379
      - NESSUS_URL=http://host.docker.internal:8834
      - DATA_DIR=/app/data
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis

volumes:
  redis-data:
  data:
  logs:
```

### Phase 2: Scanner Abstraction (Days 4-5)
```python
# scanners/base.py
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, Optional
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
        """Get scan status and progress"""
        pass

    @abstractmethod
    async def export_results(self, scan_id: int, format: str) -> bytes:
        """Export scan results in specified format"""
        pass
```

### Phase 3: Refactored Scanner Implementation (Days 6-7)
```python
# scanners/nessus_scanner.py
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# Add existing scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "nessusAPIWrapper"))

# Import existing scripts
import manage_scans
import launch_scan as launch_module
import export_vulnerabilities_detailed

class NessusScanner(ScannerInterface):
    """Wraps existing Nessus scripts with clean interface"""

    def __init__(self, url: str, credentials: Dict[str, Any]):
        self.url = url
        self.creds = credentials
        self._api_token = None
        self._session_token = None

    async def _authenticate(self):
        """Get authentication tokens"""
        if not self._api_token:
            # TODO: Call manage_scans.authenticate()
            pass

    async def create_scan(self, request: ScanRequest) -> int:
        """Create Nessus scan using existing manage_scans.py"""
        await self._authenticate()

        # TODO: Call manage_scans.create_scan()
        # For now, return mock
        return 123

    async def launch_scan(self, scan_id: int) -> str:
        """Launch scan using existing launch_scan.py"""
        # TODO: Call launch_module.launch_scan()
        return f"scan_uuid_{scan_id}"

    async def get_status(self, scan_id: int) -> Dict[str, Any]:
        """Get status using existing scripts"""
        # TODO: Parse list_scans.py output
        return {
            "status": "running",
            "progress": 45
        }

    async def export_results(self, scan_id: int, format: str) -> bytes:
        """Export using export_vulnerabilities_detailed.py"""
        # TODO: Call export script
        return b"mock_nessus_data"
```

### Phase 4: Queue System (Days 8-9)
```python
# core/queue.py
import redis
import json
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class Task:
    """Task representation in queue"""
    task_id: str
    scan_type: str
    payload: Dict[str, Any]
    status: str = "queued"
    created_at: str = ""
    retry_count: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

class TaskQueue:
    """Redis-backed task queue with dead letter support"""

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.main_queue = "nessus:queue:pending"
        self.processing = "nessus:queue:processing"
        self.dead_letter = "nessus:queue:dead"
        self.task_data = "nessus:tasks:"  # Hash prefix

    async def enqueue(self, task: Task) -> int:
        """Add task to queue"""
        # Store task data
        self.redis.hset(
            f"{self.task_data}{task.task_id}",
            mapping=asdict(task)
        )

        # Add to queue
        position = self.redis.lpush(self.main_queue, task.task_id)
        return self.redis.llen(self.main_queue)

    async def dequeue(self) -> Optional[Task]:
        """Get next task (blocking)"""
        # Move from pending to processing atomically
        task_id = self.redis.brpoplpush(
            self.main_queue,
            self.processing,
            timeout=5
        )

        if task_id:
            task_data = self.redis.hgetall(f"{self.task_data}{task_id}")
            return Task(**task_data)
        return None

    async def complete(self, task_id: str):
        """Mark task as completed"""
        self.redis.lrem(self.processing, 1, task_id)
        self.redis.hset(f"{self.task_data}{task_id}", "status", "completed")

    async def fail(self, task_id: str, error: str):
        """Move task to dead letter queue"""
        self.redis.lrem(self.processing, 1, task_id)
        self.redis.lpush(self.dead_letter, task_id)
        self.redis.hset(
            f"{self.task_data}{task_id}",
            mapping={"status": "failed", "error": error}
        )

    async def get_position(self, task_id: str) -> int:
        """Get queue position for task"""
        # TODO: Find position in list
        return 0
```

### Phase 5: MCP Tools Implementation (Days 10-11)
```python
# tools/scan_tools.py
from fastmcp import FastMCP
from typing import Dict, Any
from core.queue import TaskQueue, Task
from core.task_manager import TaskManager
import uuid

mcp = FastMCP("Nessus Scanner")
queue = TaskQueue("redis://redis:6379")
task_mgr = TaskManager("/app/data")

@mcp.tool()
async def run_untrusted_scan(
    targets: str,
    name: str,
    description: str = "",
    schema_profile: str = "brief"
) -> Dict[str, Any]:
    """
    Run network-only vulnerability scan (no credentials).

    This is the MINIMAL PROTOTYPE implementation.
    TODO markers indicate areas for enhancement.
    """
    # Generate task ID
    task_id = f"ns_proto_{uuid.uuid4().hex[:8]}"

    # Create task
    task = Task(
        task_id=task_id,
        scan_type="untrusted",
        payload={
            "targets": targets,
            "name": name,
            "description": description,
            "schema_profile": schema_profile
        }
    )

    # Enqueue
    queue_position = await queue.enqueue(task)

    # Create task directory
    await task_mgr.create_task(task_id, task.payload)

    return {
        "task_id": task_id,
        "status": "queued",
        "queue_position": queue_position
    }

@mcp.tool()
async def get_scan_status(task_id: str) -> Dict[str, Any]:
    """
    Check status of scan task.

    TODO: Add progress percentage
    TODO: Add error details for failed tasks
    """
    task_data = await task_mgr.get_task_status(task_id)

    return {
        "task_id": task_id,
        "status": task_data.get("status", "unknown"),
        "created_at": task_data.get("created_at"),
        "completed_at": task_data.get("completed_at")
    }

@mcp.tool()
async def get_scan_results(
    task_id: str,
    page: int = 1,
    page_size: int = 40
) -> str:
    """
    Get scan results in JSON-NL format.

    PROTOTYPE: Returns pre-generated default schema only.
    TODO: Add pagination
    TODO: Add filtering
    TODO: Add custom schema support
    """
    # Check if completed
    status = await task_mgr.get_task_status(task_id)
    if status.get("status") != "completed":
        return json.dumps({"error": "Scan not completed"})

    # Read pre-generated default schema file
    results_path = f"/app/data/tasks/{task_id}/scan_schema_brief.jsonl"

    try:
        with open(results_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return json.dumps({"error": "Results not found"})
```

### Phase 6: Worker Implementation (Days 12-13)
```python
# worker.py
import asyncio
import logging
from pathlib import Path
from core.queue import TaskQueue
from scanners.nessus_scanner import NessusScanner
from schema.converter import NessusToJsonNL
import json

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    handlers=[
        logging.FileHandler("/app/logs/worker.jsonl"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScanWorker:
    """Process scan tasks from queue"""

    def __init__(self, redis_url: str, nessus_url: str, data_dir: str):
        self.queue = TaskQueue(redis_url)
        self.scanner = NessusScanner(nessus_url, {
            "username": "nessus",
            "password": "nessus"
        })
        self.data_dir = Path(data_dir)
        self.converter = NessusToJsonNL()

    async def process_task(self, task):
        """Process single scan task"""
        task_dir = self.data_dir / "tasks" / task.task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Processing task {task.task_id}")

            # 1. Create scan
            scan_request = ScanRequest(
                targets=task.payload["targets"],
                name=task.payload["name"],
                scan_type=task.scan_type
            )
            scan_id = await self.scanner.create_scan(scan_request)

            # Save scan_id
            (task_dir / "scan_id.txt").write_text(str(scan_id))

            # 2. Launch scan
            scan_uuid = await self.scanner.launch_scan(scan_id)
            logger.info(f"Launched scan {scan_id} with UUID {scan_uuid}")

            # 3. Poll until complete
            while True:
                status = await self.scanner.get_status(scan_id)
                if status["status"] == "completed":
                    break
                await asyncio.sleep(30)  # Poll every 30 seconds

            # 4. Export results
            nessus_data = await self.scanner.export_results(scan_id, "nessus")
            (task_dir / "scan_native.nessus").write_bytes(nessus_data)

            # 5. Generate default schema (brief)
            jsonl_data = self.converter.convert(
                nessus_data,
                schema_profile="brief"
            )
            (task_dir / "scan_schema_brief.jsonl").write_text(jsonl_data)

            # Mark complete
            await self.queue.complete(task.task_id)
            logger.info(f"Task {task.task_id} completed")

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            await self.queue.fail(task.task_id, str(e))

    async def run(self):
        """Main worker loop"""
        logger.info("Worker started")

        while True:
            task = await self.queue.dequeue()
            if task:
                await self.process_task(task)
            else:
                await asyncio.sleep(1)  # No tasks, wait

if __name__ == "__main__":
    import os

    worker = ScanWorker(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        nessus_url=os.getenv("NESSUS_URL", "http://localhost:8834"),
        data_dir=os.getenv("DATA_DIR", "/app/data")
    )

    asyncio.run(worker.run())
```

---

## 3. Component Interfaces (For Claude Implementation)

### 3.1 Task Manager Interface
```python
# core/task_manager.py
from typing import Dict, Any, Optional
from pathlib import Path
import json

class TaskManager:
    """Manages task lifecycle and storage"""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    async def create_task(self, task_id: str, request: Dict[str, Any]) -> None:
        """Create task directory and metadata"""
        # TODO: Create directory structure
        # TODO: Write task.json with initial status
        pass

    async def update_status(self, task_id: str, status: str) -> None:
        """Update task status"""
        # TODO: Update task.json
        pass

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task metadata"""
        # TODO: Read task.json
        return {"status": "unknown"}

    async def cleanup_old_tasks(self, ttl_hours: int = 24) -> int:
        """Delete tasks older than TTL"""
        # TODO: Check last_accessed_at
        # TODO: Delete old directories
        return 0
```

### 3.2 Schema Converter Interface
```python
# schema/converter.py
from typing import List, Dict, Any
import json

class NessusToJsonNL:
    """Convert Nessus format to JSON-NL"""

    # Predefined schemas
    SCHEMAS = {
        "minimal": ["host", "plugin_id", "severity", "cve", "cvss_score", "exploit_available"],
        "brief": ["host", "plugin_id", "plugin_name", "severity", "cve", "description", "solution"],
        "summary": ["host", "plugin_id", "plugin_name", "severity", "cve", "cvss3_base_score", "synopsis"],
        "full": None  # All fields
    }

    def convert(self, nessus_data: bytes, schema_profile: str = "brief") -> str:
        """
        Convert Nessus data to JSON-NL format.

        Returns multi-line string:
        Line 1: Schema definition
        Line 2: Scan metadata
        Lines 3+: Vulnerability data
        """
        # TODO: Parse .nessus XML
        # TODO: Extract fields based on schema
        # TODO: Generate JSON-NL

        # Mock implementation for prototype
        lines = []
        lines.append(json.dumps({
            "type": "schema",
            "profile": schema_profile,
            "fields": self.SCHEMAS.get(schema_profile, [])
        }))
        lines.append(json.dumps({
            "type": "scan_metadata",
            "task_id": "mock_task"
        }))
        lines.append(json.dumps({
            "type": "vulnerability",
            "host": "192.168.1.1",
            "plugin_id": 12345,
            "severity": "High"
        }))

        return "\n".join(lines)
```

### 3.3 Error Handler Interface
```python
# core/error_handler.py
from typing import Dict, Any
import logging

class DeadLetterProcessor:
    """Process failed tasks from dead letter queue"""

    def __init__(self, queue: TaskQueue):
        self.queue = queue
        self.logger = logging.getLogger(__name__)

    async def get_failed_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks in dead letter queue"""
        # TODO: Fetch from Redis dead letter queue
        # TODO: Include error details
        return []

    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        # TODO: Move from dead letter back to main queue
        # TODO: Increment retry count
        # TODO: Check max retries
        return False

    async def purge_task(self, task_id: str) -> bool:
        """Permanently remove failed task"""
        # TODO: Delete from dead letter queue
        # TODO: Archive task data
        return False
```

---

## 4. Development Workflow for Claude Agents

### 4.1 Implementation Order (Prototype First)
```
Day 1-3:   Docker setup + Redis + Basic FastMCP
Day 4-5:   Scanner interface + Nessus wrapper stub
Day 6-7:   Queue system + Worker skeleton
Day 8-9:   Minimal working scan (untrusted only)
Day 10-11: Status polling + Basic results
Day 12-13: Testing & debugging
Week 3:    Add remaining scan types
Week 4:    Schema & filtering
Week 5:    Production hardening
```

### 4.2 Testing Strategy
```python
# tests/test_integration.py
import pytest
from fastmcp import FastMCP
import asyncio

@pytest.mark.asyncio
async def test_minimal_workflow():
    """Test the basic untrusted scan workflow"""

    # 1. Submit scan
    result = await mcp.call_tool("run_untrusted_scan", {
        "targets": "192.168.1.1",
        "name": "Test Scan"
    })
    assert "task_id" in result

    # 2. Check status
    await asyncio.sleep(2)
    status = await mcp.call_tool("get_scan_status", {
        "task_id": result["task_id"]
    })
    assert status["status"] in ["queued", "running"]

    # 3. Wait and get results (mock for testing)
    # TODO: Mock scanner for faster tests
```

### 4.3 TODO Tracking for Claude
```python
# Each file has TODO markers like:
# TODO: [PRIORITY-1] Core functionality
# TODO: [PRIORITY-2] Enhancements
# TODO: [PRIORITY-3] Nice-to-have

# Claude can search for TODOs:
grep -r "TODO:" --include="*.py" | sort
```

---

## 5. Configuration Files

### 5.1 Dockerfile.api
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install FastMCP and dependencies
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Copy existing scripts (for reference/testing)
COPY nessusAPIWrapper /app/nessusAPIWrapper

# Copy MCP server code
COPY mcp-server /app/mcp-server
WORKDIR /app/mcp-server

# Run FastMCP server
CMD ["python", "-m", "fastmcp", "run", "tools.scan_tools:mcp", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.2 Dockerfile.worker
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements-worker.txt .
RUN pip install --no-cache-dir -r requirements-worker.txt

# Copy existing scripts
COPY nessusAPIWrapper /app/nessusAPIWrapper

# Copy worker code
COPY mcp-server /app/mcp-server
WORKDIR /app/mcp-server

# Run worker
CMD ["python", "worker.py"]
```

### 5.3 requirements-api.txt
```
fastmcp>=0.1.0
redis>=5.0.0
httpx>=0.24.0
pydantic>=2.0.0
```

### 5.4 requirements-worker.txt
```
redis>=5.0.0
httpx>=0.24.0
lxml>=4.9.0  # For parsing .nessus XML
pytenable>=1.4.0
requests>=2.31.0
```

---

## 6. Monitoring & Debugging

### 6.1 Log Structure (JSON-NL)
```json
{"time": "2025-01-01T12:00:00", "level": "INFO", "component": "worker", "task_id": "ns_proto_12345678", "message": "Task started"}
{"time": "2025-01-01T12:00:05", "level": "INFO", "component": "scanner", "scan_id": 123, "message": "Scan created"}
{"time": "2025-01-01T12:30:00", "level": "INFO", "component": "worker", "task_id": "ns_proto_12345678", "message": "Task completed"}
```

### 6.2 Health Check Endpoint
```python
@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Check system health"""
    return {
        "status": "healthy",
        "redis": queue.redis.ping(),
        "worker": check_worker_heartbeat(),
        "storage": check_storage_available()
    }
```

---

## 7. Quick Start Commands

```bash
# 1. Build and start all services
docker-compose up --build

# 2. Watch logs
docker-compose logs -f mcp-api
docker-compose logs -f scanner-worker

# 3. Test with curl
curl -X POST http://localhost:8835/tool/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "run_untrusted_scan",
    "arguments": {
      "targets": "192.168.1.1",
      "name": "Test Scan"
    }
  }'

# 4. Check Redis queue
docker-compose exec redis redis-cli
> LLEN nessus:queue:pending
> LLEN nessus:queue:dead

# 5. View task data
ls -la ./data/tasks/

# 6. Restart worker after code changes
docker-compose restart scanner-worker
```

---

## 8. Next Steps for Claude Implementation

### Priority 1: Get Prototype Working
1. [ ] Implement TaskManager.create_task()
2. [ ] Implement NessusScanner.create_scan() using existing scripts
3. [ ] Get basic worker loop running
4. [ ] Test end-to-end with mock data

### Priority 2: Real Scanner Integration
1. [ ] Refactor manage_scans.py into class methods
2. [ ] Handle authentication tokens properly
3. [ ] Parse real .nessus XML files
4. [ ] Generate proper JSON-NL output

### Priority 3: Production Features
1. [ ] Add pagination to get_scan_results()
2. [ ] Implement filtering logic
3. [ ] Add remaining scan types (trusted, privileged)
4. [ ] Implement TTL cleanup
5. [ ] Add retry logic for failed tasks

---

## Notes for Claude Agents

1. **Start Simple**: Focus on getting the untrusted scan working first
2. **Use Stubs**: Implement interfaces with TODO markers, fill in later
3. **Test Early**: Use mock data to test the flow before real Nessus integration
4. **Log Everything**: Use structured logging for easy debugging
5. **Fail Gracefully**: Send errors to dead letter queue for analysis

This architecture prioritizes:
- **Quick prototype** (basic workflow in Week 1)
- **Iterative development** (clear TODOs and phases)
- **Simple but robust** (Redis queue, dead letter, structured logs)
- **Claude-friendly** (type hints, interfaces, stubs)