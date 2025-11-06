# Phase 3: Observability & Testing

> **Duration**: Week 3
> **Goal**: Structured logging, Prometheus metrics, comprehensive tests, FastMCP SDK client
> **Status**: 🔴 Not Started
> **Prerequisites**: Phase 2 complete, results retrieval working

---

## Overview

Phase 3 adds production-grade observability and comprehensive test coverage:
- **Structured Logging**: JSON logs with trace IDs (structlog)
- **Prometheus Metrics**: 8 key metrics on /metrics endpoint
- **Health Checks**: API and worker readiness endpoints
- **Unit Tests**: >80% coverage on core logic
- **Integration Tests**: Full workflows with real Nessus
- **FastMCP SDK Client**: Real MCP protocol client for testing

---

## Phase 3 Task List

### 3.1: Structured Logging (structlog)
- [ ] Add structlog to requirements-api.txt and requirements-worker.txt
- [ ] Create `core/logging_config.py`
- [ ] Configure JSON formatter with trace_id
- [ ] Add logging to all components:
  - [ ] Tool invocations (trace_id, tool_name, args)
  - [ ] State transitions (task_id, old_state, new_state)
  - [ ] Scanner API calls (endpoint, status_code)
  - [ ] Queue operations (enqueue, dequeue)
  - [ ] Errors (exception, stack_trace)
- [ ] Test log output format

### 3.2: Prometheus Metrics
- [ ] Create `core/metrics.py`
- [ ] Define 8 core metrics:
  - [ ] `scans_total` (Counter: scan_type, status)
  - [ ] `api_requests_total` (Counter: tool, status)
  - [ ] `active_scans` (Gauge)
  - [ ] `scanner_instances` (Gauge: scanner_type, enabled)
  - [ ] `queue_depth` (Gauge: queue=main|dead)
  - [ ] `task_duration_seconds` (Histogram)
  - [ ] `ttl_deletions_total` (Counter)
  - [ ] `dlq_size` (Gauge)
- [ ] Instrument all tools with api_requests_total
- [ ] Update metrics in worker (active_scans, task_duration)
- [ ] Add `/metrics` endpoint to FastAPI
- [ ] Test metrics with curl

### 3.3: Health Check Endpoints
- [ ] Add `/health` endpoint to mcp_server.py
- [ ] Check Redis connectivity (PING)
- [ ] Check filesystem writability (touch test)
- [ ] Return 200 OK if healthy, 503 if not
- [ ] Add worker healthcheck script
- [ ] Update docker-compose healthchecks
- [ ] Test health endpoints

### 3.4: Unit Test Suite
- [ ] Create `tests/unit/` directory
- [ ] Test core/types.py (state machine)
- [ ] Test core/task_manager.py (CRUD operations)
- [ ] Test core/idempotency.py (key validation)
- [ ] Test scanners/mock_scanner.py (all methods)
- [ ] Test schema/parser.py (XML parsing)
- [ ] Test schema/converter.py (JSON-NL format)
- [ ] Test schema/filters.py (all filter types)
- [ ] Run with coverage: `pytest --cov=. --cov-report=html`
- [ ] Target: >80% coverage

### 3.5: Integration Test Suite
- [ ] Create `tests/integration/` directory
- [ ] Test end-to-end untrusted scan
- [ ] Test idempotent retry (same task_id)
- [ ] Test status polling until completion
- [ ] Test result retrieval with filters
- [ ] Test pagination (page=1, page=2, page=0)
- [ ] Test concurrent scans (5+ tasks)
- [ ] Test queue behavior (FIFO order)
- [ ] Test DLQ on failures
- [ ] Run against real Nessus

### 3.6: FastMCP SDK Client
- [ ] Create `client/fastmcp_client.py`
- [ ] Use FastMCP Client SDK
- [ ] Connect via HTTP transport
- [ ] Implement methods:
  - [ ] `submit_scan()` - call run_untrusted_scan tool
  - [ ] `get_status()` - call get_scan_status tool
  - [ ] `get_results()` - call get_scan_results tool
  - [ ] `list_scanners()` - call list_scanners tool
- [ ] Add examples
- [ ] Test against running server

---

## Key Implementation Details

### Structured Logging

**File: `core/logging_config.py`**
```python
"""Structured logging configuration."""
import structlog
import logging
from datetime import datetime


def configure_logging():
    """Configure structlog for JSON output."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        handlers=[logging.StreamHandler()]
    )
```

**Usage in tools:**
```python
import structlog

logger = structlog.get_logger()

@mcp.tool()
async def run_untrusted_scan(...):
    trace_id = request.state.trace_id

    logger.info(
        "tool_invocation",
        tool="run_untrusted_scan",
        trace_id=trace_id,
        targets=targets,
        name=name
    )
    # ... rest of logic
```

### Prometheus Metrics

**File: `core/metrics.py`**
```python
"""Prometheus metrics definitions."""
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# Counters
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

ttl_deletions_total = Counter(
    "nessus_ttl_deletions_total",
    "Tasks deleted by TTL cleanup"
)

# Gauges
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
    ["queue"]  # main, dead
)

dlq_size = Gauge(
    "nessus_dlq_size",
    "Tasks in dead letter queue"
)

# Histograms
task_duration_seconds = Histogram(
    "nessus_task_duration_seconds",
    "Task execution duration",
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400]
)


def metrics_response():
    """Return Prometheus metrics."""
    return generate_latest()
```

**Add /metrics endpoint:**
```python
# In tools/mcp_server.py
from starlette.responses import PlainTextResponse
from core.metrics import metrics_response

@mcp.app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(metrics_response())
```

### Health Checks

**File: `core/health.py`**
```python
"""Health check utilities."""
import redis
from pathlib import Path


def check_redis(redis_url: str) -> bool:
    """Check Redis connectivity."""
    try:
        r = redis.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        return True
    except:
        return False


def check_filesystem(data_dir: str) -> bool:
    """Check filesystem writability."""
    try:
        test_file = Path(data_dir) / ".health_check"
        test_file.touch()
        test_file.unlink()
        return True
    except:
        return False
```

**Add /health endpoint:**
```python
from core.health import check_redis, check_filesystem

@mcp.app.get("/health")
async def health():
    """Health check endpoint."""
    redis_ok = check_redis(os.getenv("REDIS_URL", "redis://localhost:6379"))
    fs_ok = check_filesystem(os.getenv("DATA_DIR", "/app/data/tasks"))

    if redis_ok and fs_ok:
        return {"status": "healthy"}
    else:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "redis": redis_ok,
                "filesystem": fs_ok
            }
        )
```

### FastMCP SDK Client

**File: `client/fastmcp_client.py`**
```python
"""FastMCP SDK client for testing."""
import asyncio
from fastmcp import Client
from typing import Dict, Any


class NessusFastMCPClient:
    """FastMCP SDK client wrapper."""

    def __init__(self, url: str = "http://localhost:8835"):
        self.client = Client(url, transport="http")

    async def connect(self):
        """Connect to MCP server."""
        await self.client.connect()

    async def submit_scan(self, targets: str, name: str, **kwargs) -> Dict[str, Any]:
        """Submit untrusted scan."""
        result = await self.client.call_tool(
            "run_untrusted_scan",
            arguments={"targets": targets, "name": name, **kwargs}
        )
        return result.data

    async def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get scan status."""
        result = await self.client.call_tool(
            "get_scan_status",
            arguments={"task_id": task_id}
        )
        return result.data

    async def get_results(
        self,
        task_id: str,
        page: int = 1,
        filters: Dict[str, Any] = None
    ) -> str:
        """Get scan results."""
        result = await self.client.call_tool(
            "get_scan_results",
            arguments={
                "task_id": task_id,
                "page": page,
                "filters": filters or {}
            }
        )
        return result.text  # JSON-NL string

    async def close(self):
        """Cleanup."""
        await self.client.close()


# Example usage
async def main():
    client = NessusFastMCPClient()

    await client.connect()
    try:
        task = await client.submit_scan("192.168.1.1", "SDK Test")
        print(f"Task: {task}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Phase 3 Completion Checklist

### Deliverables
- [ ] Structured JSON logs with trace IDs
- [ ] All 8 Prometheus metrics working
- [ ] Health check endpoints (/health, /metrics)
- [ ] Unit test suite >80% coverage
- [ ] Integration test suite (8+ tests)
- [ ] FastMCP SDK client functional

### Verification
```bash
# Check logs
docker compose logs mcp-api | jq .

# Check metrics
curl http://localhost:8835/metrics

# Check health
curl http://localhost:8835/health

# Run unit tests
pytest tests/unit/ -v --cov=.

# Run integration tests
pytest tests/integration/ -v

# Test FastMCP client
python client/fastmcp_client.py
```

### Success Criteria
✅ Phase 3 complete when:
1. All logs in JSON format with trace_id
2. Metrics endpoint returns data
3. Health checks pass
4. Unit tests >80% coverage
5. Integration tests pass
6. FastMCP client works

---

**Next**: [PHASE_4_PRODUCTION.md](./PHASE_4_PRODUCTION.md)
