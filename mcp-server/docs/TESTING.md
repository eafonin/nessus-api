# Integration Testing Guide - Phase 0+1 with Real Nessus Scanner

This document explains how to run integration tests that validate the complete Phase 0 and Phase 1 workflows with a real Nessus scanner.

---

## Overview

### Test Categories

The test suite includes two types of tests, distinguished by pytest markers:

1. **Lightweight Tests** (unit/integration)
   - No markers or `@pytest.mark.unit`
   - Run anywhere (host machine, CI/CD)
   - No external dependencies (use mocks)
   - Fast execution (< 1 minute)

2. **Heavy Integration Tests**
   - `@pytest.mark.real_nessus` - Uses actual Nessus scanner
   - `@pytest.mark.requires_docker_network` - Must run inside Docker network
   - `@pytest.mark.slow` - Takes several minutes to complete
   - Requires Redis and Nessus scanner access

### Key Test Files

**`tests/integration/test_phase0_phase1_real_nessus.py`**
- Complete end-to-end test of Phase 0 + Phase 1 workflow
- Uses real Nessus scanner (NOT mocks)
- Demonstrates structured logging throughout
- Must run inside Docker network

**`tests/integration/test_fastmcp_client.py`** ⭐ **RECOMMENDED**
- FastMCP client integration tests
- 8 test classes covering all client functionality
- Type-safe, production-ready patterns
- See [FASTMCP_CLIENT_REQUIREMENT.md](./FASTMCP_CLIENT_REQUIREMENT.md)

---

## ⚠️ MANDATORY: FastMCP Client for Testing

**All future testing and integration MUST use the FastMCP Client:**

```python
# ✅ CORRECT - Use FastMCP Client
from client.nessus_fastmcp_client import NessusFastMCPClient

async def test_scan_workflow():
    async with NessusFastMCPClient("http://localhost:8835/mcp") as client:
        task = await client.submit_scan(
            targets="192.168.1.1",
            scan_name="Integration Test"
        )
        status = await client.get_status(task["task_id"])
        assert status["status"] == "queued"
```

**Benefits**:
- Type safety with method signatures
- Built-in error handling
- Progress callbacks
- Helper methods for common workflows
- 654 lines of production-ready code

**See**:
- [FASTMCP_CLIENT_REQUIREMENT.md](./FASTMCP_CLIENT_REQUIREMENT.md) - Mandatory requirement
- [FASTMCP_CLIENT_ARCHITECTURE.md](./FASTMCP_CLIENT_ARCHITECTURE.md) - Architecture
- [client/examples/](./client/examples/) - 5 progressive examples

---

## Quick Start: Docker-Based Testing

The easiest way to run integration tests is using the dedicated test environment:

```bash
cd /home/nessus/projects/nessus-api/mcp-server

# Start test environment (Redis + test runner)
docker compose -f docker-compose.test.yml up -d

# Run complete Phase 0+1 integration test with real Nessus
docker compose -f docker-compose.test.yml exec test-runner \
  pytest tests/integration/test_phase0_phase1_real_nessus.py -v -s -m real_nessus

# Run only lightweight Redis connectivity test
docker compose -f docker-compose.test.yml exec test-runner \
  pytest tests/integration/test_phase0_phase1_real_nessus.py::test_redis_connectivity_from_docker_network -v -s

# Cleanup when done
docker compose -f docker-compose.test.yml down -v
```

---

## Architecture: Docker Test Environment

### Components

1. **redis-test**
   - Redis 7.4.7 instance for testing
   - Isolated from production Redis
   - Connected to both `test-internal` and `nessus_nessus_net` networks

2. **test-runner**
   - Python 3.11 container with all dependencies
   - Has access to:
     - Redis (via `redis-test:6379`)
     - Nessus scanner (via `vpn-gateway:8834` on `nessus_nessus_net`)
   - Mounts source code as read-only volume for live updates

### Network Topology

```text
┌──────────────────────────────────────────────────────────────┐
│ nessus_nessus_net (external network)                         │
│                                                               │
│  ┌─────────────────┐       ┌─────────────────┐              │
│  │  vpn-gateway    │       │  test-runner    │              │
│  │  (Nessus Pro)   │◄──────│  (pytest)       │              │
│  │  :8834          │       │                 │              │
│  └─────────────────┘       └────────┬────────┘              │
│                                     │                        │
└─────────────────────────────────────┼────────────────────────┘
                                      │
┌─────────────────────────────────────┼────────────────────────┐
│ test-internal network               │                        │
│                                     │                        │
│                            ┌────────▼────────┐               │
│                            │  redis-test     │               │
│                            │  :6379          │               │
│                            └─────────────────┘               │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Test Workflow: Phase 0 + Phase 1

The complete integration test validates:

### Phase 0: Queue-Based Scan Execution

1. **Tool Invocation**
   - Simulates MCP tool call (`run_untrusted_scan`)
   - Generates `trace_id` for correlation

2. **Task Creation**
   - Creates task in TaskManager
   - Persists to filesystem

3. **Queue Operations**
   - Enqueues task to Redis queue
   - Verifies queue depth
   - Dequeues task (simulating worker)

**Structured Logs Emitted:**
```json
{"event": "tool_invocation", "tool": "run_untrusted_scan", "trace_id": "...", ...}
{"event": "task_created", "task_id": "...", "trace_id": "...", "status": "queued", ...}
{"event": "scan_enqueued", "task_id": "...", "queue_position": 1, ...}
{"event": "task_dequeued", "task_id": "...", "worker_id": "test-worker-01", ...}
```

### Phase 1: Scan Workflow with Real Nessus

4. **Scan Creation**
   - Creates scan in Nessus via API
   - Targets: `172.32.0.215` (Ubuntu server)

5. **Scan Launch**
   - Launches scan
   - State transition: `QUEUED → RUNNING`

6. **Progress Monitoring**
   - Polls scan status every 10 seconds
   - Logs progress updates (25%, 50%, 75%, 100%)

7. **Completion Handling**
   - State transition: `RUNNING → COMPLETED`
   - Exports scan results (.nessus XML)

8. **Results Verification**
   - Validates XML format
   - Counts vulnerabilities by severity
   - Saves results to task directory

9. **Cleanup**
   - Deletes scan from Nessus
   - Removes task data

**Structured Logs Emitted:**
```json
{"event": "scan_state_transition", "from_state": "queued", "to_state": "running", "nessus_scan_id": 42, ...}
{"event": "scan_progress", "progress": 50, "scanner_status": "running", ...}
{"event": "scan_state_transition", "from_state": "running", "to_state": "completed", ...}
{"event": "scan_completed", "duration_seconds": 450, "vulnerabilities_found": 47, ...}
```

---

## Running Tests

### Option 1: Docker Test Environment (Recommended)

```bash
# Start environment
docker compose -f docker-compose.test.yml up -d

# Run specific test
docker compose -f docker-compose.test.yml exec test-runner \
  pytest tests/integration/test_phase0_phase1_real_nessus.py::test_complete_phase0_phase1_workflow -v -s

# Run all Phase 0 tests
docker compose -f docker-compose.test.yml exec test-runner \
  pytest -v -s -m phase0

# Run all Phase 1 tests
docker compose -f docker-compose.test.yml exec test-runner \
  pytest -v -s -m phase1

# Run all tests marked as 'real_nessus'
docker compose -f docker-compose.test.yml exec test-runner \
  pytest -v -s -m real_nessus

# Cleanup
docker compose -f docker-compose.test.yml down -v
```

### Option 2: Host Machine (Limited)

**Note:** Host-based testing will FAIL for tests requiring Docker network access due to Redis connection issues.

```bash
# Activate virtual environment
source ../venv/bin/activate

# Run lightweight tests only (no Docker network required)
pytest tests/integration/test_queue.py -v -s -m "not requires_docker_network"

# Attempting to run tests marked 'requires_docker_network' will fail
# with "Connection reset by peer" error due to Docker port forwarding issues
```

---

## Pytest Markers Reference

| Marker | Purpose | Example |
|--------|---------|---------|
| `phase0` | Phase 0 tests (queue, task management) | `pytest -m phase0` |
| `phase1` | Phase 1 tests (scan workflow) | `pytest -m phase1` |
| `phase2` | Phase 2 tests (schema parsing) | `pytest -m phase2` |
| `integration` | Integration tests (may use external services) | `pytest -m integration` |
| `unit` | Unit tests (no external dependencies) | `pytest -m unit` |
| `slow` | Long-running tests (> 1 minute) | `pytest -m "not slow"` |
| `real_nessus` | Uses real Nessus scanner (NOT mocks) | `pytest -m real_nessus` |
| `requires_docker_network` | Must run inside Docker network | `pytest -m requires_docker_network` |

### Combining Markers

```bash
# Run all Phase 0 OR Phase 1 tests
pytest -m "phase0 or phase1"

# Run integration tests that are NOT slow
pytest -m "integration and not slow"

# Skip all tests requiring Docker network
pytest -m "not requires_docker_network"

# Run only quick unit tests
pytest -m "unit and quick"
```

---

## Troubleshooting

### Issue: Redis Connection Fails from Host

**Symptom:**
```text
redis.exceptions.ConnectionError: Error while reading from localhost:6379 : (104, 'Connection reset by peer')
```

**Cause:** Docker's NAT/port-forwarding interferes with Redis RESP protocol handshake.

**Solution:** Run tests inside Docker network using `docker-compose.test.yml`.

### Issue: Nessus Scanner Not Accessible

**Symptom:**
```text
httpx.ConnectError: All connection attempts failed
```

**Cause:** Nessus scanner is only accessible from `nessus_nessus_net` Docker network.

**Solution:**
1. Verify Nessus is running: `docker ps | grep nessus`
2. Check network connectivity:
   ```bash
   docker compose -f docker-compose.test.yml exec test-runner \
     curl -k https://vpn-gateway:8834/server/status
   ```

### Issue: Test Timeout

**Symptom:** Test exceeds 10-minute timeout.

**Cause:** Nessus scan is taking longer than expected (large target, many plugins).

**Solution:**
- Increase `max_wait` in test (currently 600 seconds)
- Use smaller target IP range
- Check Nessus scanner performance

---

## Redis Version Requirements

**CRITICAL:** Redis client version MUST match Redis server version.

- **Server:** Redis 7.4.7
- **Client:** redis-py >= 7.0.0, < 8.0.0

See `requirements-api.txt` for details.

---

## Environment Variables

### Test Runner Container

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis-test:6379` | Redis connection URL |
| `NESSUS_URL` | `https://vpn-gateway:8834` | Nessus scanner URL |
| `NESSUS_USERNAME` | `nessus` | Nessus login username |
| `NESSUS_PASSWORD` | `nessus` | Nessus login password |
| `LOG_LEVEL` | `INFO` | Structured logging level |

---

## File Structure

```text
mcp-server/
├── docker-compose.test.yml          # Test environment configuration
├── Dockerfile.test                  # Test runner container image
├── TESTING.md                       # This file
├── tests/
│   └── integration/
│       ├── test_phase0_phase1_real_nessus.py  # Main integration test
│       ├── test_queue.py            # Queue tests
│       ├── test_idempotency.py      # Idempotency tests
│       └── ...
├── pytest.ini                       # Pytest configuration & markers
├── requirements-api.txt             # Python dependencies
└── STRUCTURED_LOGGING_EXAMPLES.md   # JSON log examples
```

---

## Viewing Structured Logs

All tests emit structured JSON logs. To filter and analyze:

```bash
# Run test and pipe logs through jq for formatting
docker compose -f docker-compose.test.yml exec test-runner \
  pytest tests/integration/test_phase0_phase1_real_nessus.py -v -s 2>&1 | \
  grep -E '^\{' | jq

# Filter specific events
... | jq 'select(.event == "scan_progress")'

# Find all logs for specific trace_id
... | jq 'select(.trace_id == "76ea3daf-da0a-4ffb-9f89-862b4f34a22c")'

# Count events by type
... | jq -s 'group_by(.event) | map({event: .[0].event, count: length})'
```

---

## Next Steps

1. **Run the lightweight test** to verify Docker network connectivity:
   ```bash
   docker compose -f docker-compose.test.yml up -d
   docker compose -f docker-compose.test.yml exec test-runner \
     pytest tests/integration/test_phase0_phase1_real_nessus.py::test_redis_connectivity_from_docker_network -v -s
   ```

2. **Run the full integration test** (takes 5-10 minutes):
   ```bash
   docker compose -f docker-compose.test.yml exec test-runner \
     pytest tests/integration/test_phase0_phase1_real_nessus.py::test_complete_phase0_phase1_workflow -v -s -m real_nessus
   ```

3. **Analyze structured logs** to see Phase 3 observability in action.

4. **Integrate with CI/CD** by adding test commands to your pipeline.

---

## Summary

This testing infrastructure provides:

- ✅ **Isolated test environment** (dedicated Docker network)
- ✅ **Real Nessus integration** (not mocks)
- ✅ **Redis connectivity** from within Docker network
- ✅ **Structured logging** throughout entire workflow
- ✅ **Pytest markers** for test categorization
- ✅ **Long-term sustainability** (version-controlled, reproducible)

All Phase 0 and Phase 1 functionality is validated with actual Nessus scans, demonstrating production-ready observability through structured JSON logs.
