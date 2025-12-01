# Nessus MCP Server - Development Guide

> **[↑ Features Index](README.md)** | **[← Operations](OPERATIONS.md)** | **[Features →](FEATURES.md)**

## Overview

This guide covers development practices, testing procedures, and conventions for the Nessus MCP Server.

---

## 1. FastMCP Client Requirement

### Mandatory Usage Rule

**All development work** involving the Nessus MCP Server **MUST** use `NessusFastMCPClient` for testing, debugging, and integration. This is mandatory, not a recommendation.

### DO: Use FastMCP Client

```python
from client.nessus_fastmcp_client import NessusFastMCPClient

async with NessusFastMCPClient("http://localhost:8835/mcp") as client:
    task = await client.submit_scan(targets="192.168.1.1", scan_name="Test")
    assert task["status"] == "queued"
```

### DO NOT: Use Direct HTTP/curl

```bash
# INCORRECT - Do not use
curl -X POST http://localhost:8835/mcp -d '{"method": "tools/call", ...}'
```

### Rationale

| Benefit | Description |
|---------|-------------|
| Type Safety | Catches errors at development time via typed signatures |
| Consistency | Single, standardized API across all code |
| Testability | Clean, Pythonic test interface |
| Debugging | Built-in debug mode with request/response logging |
| Error Handling | Structured exceptions (TimeoutError, ConnectionError, ValueError) |

### Client Location

| Purpose | Path |
|---------|------|
| Implementation | `mcp-server/client/nessus_fastmcp_client.py` |
| Examples | `mcp-server/client/examples/` |
| Integration tests | `mcp-server/tests/integration/test_fastmcp_client.py` |

---

## 2. Testing

### 2.1 Environment Setup

```bash
# Always activate virtual environment
cd /home/nessus/projects/nessus-api
source venv/bin/activate

# Navigate to mcp-server
cd mcp-server
```

### 2.2 Running Tests

```bash
# Unit tests (no external dependencies)
pytest tests/unit/ -v

# Integration tests - Phase 2 (no external deps)
pytest tests/integration/test_phase2.py -v
# Expected: 25/25 PASSED

# Integration tests - Phase 1 (requires Redis + Nessus)
pytest tests/integration/test_phase1.py -v

# All integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=term-missing
```

### 2.3 Test Categories

| Test Type | Location | Dependencies | Count |
|-----------|----------|--------------|-------|
| Unit tests | `tests/unit/` | None | 121+ |
| Phase 1 integration | `tests/integration/test_phase1.py` | Redis, Nessus | 15+ |
| Phase 2 integration | `tests/integration/test_phase2.py` | None | 25+ |
| FastMCP client | `tests/integration/test_fastmcp_client.py` | MCP Server | 8+ |

### 2.4 Manual Scan Testing

```bash
# List scans
python nessusAPIWrapper/list_scans.py

# Check status
python nessusAPIWrapper/check_status.py

# Launch scan
python nessusAPIWrapper/launch_scan.py [SCAN_ID]

# Export results
python nessusAPIWrapper/export_vulnerabilities_detailed.py [SCAN_ID]
```

---

## 3. File Organization

### 3.1 MCP Server Core

| Purpose | Path |
|---------|------|
| Main server | `mcp-server/tools/mcp_server.py` |
| Scanner wrapper | `mcp-server/scanners/nessus_scanner.py` |
| Scanner registry | `mcp-server/scanners/registry.py` |
| Queue | `mcp-server/core/queue.py` |
| Worker | `mcp-server/worker/scanner_worker.py` |
| Task manager | `mcp-server/core/task_manager.py` |
| Idempotency | `mcp-server/core/idempotency.py` |

### 3.2 Client

| Purpose | Path |
|---------|------|
| FastMCP client | `mcp-server/client/nessus_fastmcp_client.py` |
| Client examples | `mcp-server/client/examples/` |
| Smoke tests | `mcp-server/client/client_smoke.py` |

### 3.3 Schema System

| Purpose | Path |
|---------|------|
| Schema definitions | `mcp-server/schema/` |
| XML parser | `mcp-server/schema/parser.py` |
| Profile definitions | `mcp-server/schema/profiles.py` |
| Filter engine | `mcp-server/schema/filters.py` |

### 3.4 Configuration

| Purpose | Path |
|---------|------|
| Scanner config | `mcp-server/config/scanners.yaml` |
| Docker compose | `dev1/docker-compose.yml` |
| Requirements | `mcp-server/requirements-api.txt` |

### 3.5 Documentation

| Purpose | Path |
|---------|------|
| Features docs | `mcp-server/docs/features/` |
| Phase planning | `mcp-server/docs/phases/` |
| Main README | `mcp-server/README.md` |

---

## 4. Development Workflow

### 4.1 Starting Services

```bash
# Start full stack
cd /home/nessus/docker/nessus-shared && docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f scanner-worker
```

### 4.2 Running MCP Server Locally

```bash
cd /home/nessus/projects/nessus-api
source venv/bin/activate
python mcp-server/tools/mcp_server.py
```

### 4.3 Code Style

- Python 3.12+
- Type hints required for public functions
- Async/await for I/O operations
- Structured logging via `structlog`

### 4.4 Pre-commit Checks

```bash
# Run linting
ruff check mcp-server/

# Run type checking
mypy mcp-server/

# Run tests
pytest tests/ -v
```

---

## 5. Debugging

### 5.1 Enable Debug Logging

```bash
LOG_LEVEL=DEBUG python mcp-server/tools/mcp_server.py
```

### 5.2 FastMCP Client Debug Mode

```python
async with NessusFastMCPClient("http://localhost:8835/mcp", debug=True) as client:
    # All requests/responses logged
    result = await client.list_scanners()
```

### 5.3 Trace ID Correlation

All logs for a single scan share the same `trace_id`. Use for debugging complete scan lifecycle:

```bash
# Find all logs for a specific trace
docker compose logs worker | grep "trace_id.*abc-123"
```

### 5.4 Common Debug Commands

```bash
# Check Redis connectivity
docker exec nessus-mcp-redis redis-cli PING

# Check queue depth
docker exec nessus-mcp-redis redis-cli LLEN nessus:queue

# View task file
cat /app/data/tasks/<task_id>/task.json | jq .

# Check scanner connectivity
curl -k https://172.30.0.3:8834/server/status
```

---

## 6. Conventions

### 6.1 Task ID Format

```text
{scanner_type}_{instance}_{timestamp}_{random}
```

Example: `nessus_scanner1_1732123456_abc123`

### 6.2 Idempotency Key Generation

- Hash: SHA256 of `(scan_type, targets, scan_name, description)`
- Storage: Redis with 48-hour TTL
- Behavior: Duplicate submissions return existing task_id with `idempotent: true`

### 6.3 State Transitions

Valid transitions only:

```text
QUEUED → RUNNING → COMPLETED
                 → FAILED
                 → TIMEOUT
```

RUNNING → RUNNING allowed for metadata updates (progress, etc.)

---

*Generated: 2025-12-01*
*Source: Consolidated from archived development documentation*
