# Phase 6: Resilience & End-to-End Testing

> Status: **COMPLETE** ✅
> Priority: High - validates production readiness
> Last Updated: 2025-11-26

## Implementation Status

| Component | Status | Tests |
|-----------|--------|-------|
| Phase 6.1: MCP Protocol Tests | COMPLETE ✅ | 8 tests passing |
| Phase 6.2: Queue Accuracy Tests | COMPLETE ✅ | 4 tests passing |
| Phase 6.3: Failure Mode Tests | COMPLETE ✅ | 3 tests passing |
| Slow E2E Tests | COMPLETE ✅ | 3 tests passing (marked @slow) |

**Total: 18 tests (15 quick + 3 slow)**

**Test File:** `tests/integration/test_mcp_client_e2e.py`

**Run Quick Tests:**
```bash
docker exec nessus-mcp-api-dev pytest /app/tests/integration/test_mcp_client_e2e.py -v -s -m "not slow"
```

**Run All Tests (including slow):**
```bash
docker exec nessus-mcp-api-dev pytest /app/tests/integration/test_mcp_client_e2e.py -v -s
```

---

## Overview

Phase 6 focuses on end-to-end validation through the MCP protocol stack and resilience testing. Current tests bypass the MCP transport layer and call functions directly. This phase adds tests that exercise the complete system.

### Design Principle: Queues Queue

The queue system should never reject requests. Instead:
- Accept all valid requests
- Report queue position and estimated wait time
- Process in order as capacity becomes available

---

## Core Objectives

### 1. MCP Protocol Integration Tests
**Current gap:** Tests call `scanner.create_scan()` and `tool.fn()` directly, bypassing MCP protocol.

**What to test:**
- Full MCP client → SSE transport → JSON-RPC → tool execution → response
- Error propagation through MCP protocol
- Concurrent MCP requests

### 2. Queue Information Accuracy
**What to test:**
- Queue position reported correctly
- Estimated wait time is reasonable
- Position updates as queue drains

### 3. Failure Mode Testing
**What to test:**
- Scanner unavailable during scan
- Worker crash mid-scan
- Graceful recovery and retry

---

## Scanner Concurrency Policy

Each scanner in the pool has a concurrency limit:

```
MAX_CONCURRENT_SCANS_PER_SCANNER = 2  (configurable)
```

**Behavior:**
- Scanners can technically handle more concurrent scans
- More concurrent = longer individual scan times
- We limit to 2 per scanner for predictable timing
- Additional scans queue and wait

**Example with 2 scanners, limit=2:**
```
Scanner1: [scan1, scan2] running, [scan5, scan6] queued
Scanner2: [scan3, scan4] running, [scan7, scan8] queued

Submit scan9 → queued at position 5, est wait ~40min
```

---

## Detailed Scope

### Phase 6.1: MCP Client Integration Tests

```
tests/integration/test_mcp_client_e2e.py
```

**Test Cases:**

| Test | Description | Duration |
|------|-------------|----------|
| `test_mcp_run_untrusted_scan_e2e` | Full MCP flow for untrusted scan | ~1min |
| `test_mcp_run_authenticated_scan_e2e` | Full MCP flow for auth scan | ~8min |
| `test_mcp_get_scan_status_e2e` | Status check via MCP | <1s |
| `test_mcp_get_scan_results_e2e` | Results retrieval via MCP | <1s |
| `test_mcp_list_tasks_e2e` | List tasks via MCP | <1s |
| `test_mcp_error_propagation` | Invalid params return proper error | <1s |

**Implementation approach:**
```python
import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

class TestMCPClientE2E:
    """End-to-end tests via actual MCP client."""

    @pytest_asyncio.fixture
    async def mcp_client(self):
        """Connect to running MCP server."""
        async with sse_client(f"http://localhost:{MCP_PORT}/sse") as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    @pytest.mark.asyncio
    async def test_mcp_run_authenticated_scan_e2e(self, mcp_client):
        """Test authenticated scan via actual MCP client."""
        result = await mcp_client.call_tool(
            "run_authenticated_scan",
            arguments={
                "targets": "172.30.0.9",
                "name": "MCP E2E Test",
                "scan_type": "authenticated",
                "ssh_username": "testauth_nosudo",
                "ssh_password": "TestPass123!"
            }
        )

        assert "task_id" in result
        assert result["status"] == "queued"
        assert "queue_position" in result
        assert "estimated_wait_minutes" in result

    @pytest.mark.asyncio
    async def test_mcp_error_propagation(self, mcp_client):
        """Test that errors propagate correctly through MCP."""
        result = await mcp_client.call_tool(
            "run_authenticated_scan",
            arguments={
                "targets": "192.168.1.1",
                "name": "Test",
                "scan_type": "invalid_type",  # Should error
                "ssh_username": "user",
                "ssh_password": "pass"
            }
        )

        assert "error" in result
        assert "Invalid scan_type" in result["error"]
```

---

### Phase 6.2: Queue Information Accuracy Tests

```
tests/integration/test_queue_accuracy.py
```

**Test Cases:**

| Test | Description |
|------|-------------|
| `test_queue_position_increments` | Each submission gets next position |
| `test_queue_position_reported_in_status` | get_scan_status shows position |
| `test_estimated_wait_calculation` | Wait time based on avg scan duration |
| `test_queue_position_updates` | Position decreases as queue drains |

**Implementation approach:**
```python
class TestQueueAccuracy:
    """Test queue position and wait time accuracy."""

    @pytest.mark.asyncio
    async def test_queue_position_increments(self, mcp_client):
        """Each submission should get incrementing position."""
        positions = []

        for i in range(3):
            result = await mcp_client.call_tool(
                "run_untrusted_scan",
                arguments={
                    "targets": f"192.168.1.{i}",
                    "name": f"Queue_Test_{i}"
                }
            )
            positions.append(result.get("queue_position", 0))

        # Positions should increment (or be close if processed fast)
        assert positions[1] >= positions[0]
        assert positions[2] >= positions[1]

    @pytest.mark.asyncio
    async def test_estimated_wait_reasonable(self, mcp_client):
        """Estimated wait should be based on queue depth."""
        result = await mcp_client.call_tool(
            "run_untrusted_scan",
            arguments={"targets": "192.168.1.1", "name": "Wait_Test"}
        )

        wait_minutes = result.get("estimated_wait_minutes", 0)
        queue_position = result.get("queue_position", 1)

        # Rough check: wait should scale with position
        # Assuming ~8min per scan average
        expected_min = queue_position * 5  # minimum
        expected_max = queue_position * 15  # maximum

        assert expected_min <= wait_minutes <= expected_max or wait_minutes == 0
```

---

### Phase 6.3: Failure Mode Testing

```
tests/integration/test_failure_modes.py
```

**Test Cases:**

| Test | Description | Simulation |
|------|-------------|------------|
| `test_scanner_unavailable_at_launch` | Scanner down when starting scan | Mock HTTP error |
| `test_scanner_recovers` | Scanner comes back, scan resumes | Stop/start mock |
| `test_task_status_shows_failure` | Failed scans have proper status | Check status API |
| `test_invalid_target_handling` | Unreachable target handled | Use fake IP |

**Implementation approach:**
```python
class TestFailureModes:
    """Test system behavior under failure conditions."""

    @pytest.mark.asyncio
    async def test_scanner_unavailable_at_launch(self, mcp_client):
        """Test behavior when scanner is unreachable."""
        # This requires either:
        # 1. A mock scanner that can be toggled
        # 2. Testing with a known-bad scanner URL
        # 3. Network-level blocking

        # For now, test with unreachable target (different failure mode)
        result = await mcp_client.call_tool(
            "run_untrusted_scan",
            arguments={
                "targets": "10.255.255.1",  # Likely unreachable
                "name": "Unreachable_Test"
            }
        )

        # Should still queue successfully
        assert result["status"] == "queued"

        # Wait for processing
        await asyncio.sleep(30)

        # Check status - scan should complete (with no results)
        status = await mcp_client.call_tool(
            "get_scan_status",
            arguments={"task_id": result["task_id"]}
        )

        # Scan completes but finds no hosts
        assert status["status"] in ("completed", "running")

    @pytest.mark.asyncio
    async def test_task_status_shows_failure_reason(self, mcp_client):
        """Failed tasks should include failure reason."""
        # Submit with intentionally bad config
        # (would need scanner mock to simulate mid-scan failure)
        pass  # Implement when mock infrastructure available
```

---

## Implementation Priority

| Priority | Component | Effort | Value |
|----------|-----------|--------|-------|
| **P0** | MCP Client E2E Tests | 1.5 days | High - validates full stack |
| **P1** | Queue Accuracy Tests | 0.5 days | Medium - user experience |
| **P1** | Failure Mode Tests | 1 day | Medium - reliability |

**Total: ~3 days**

---

## Test Infrastructure Requirements

### For MCP E2E Tests
- MCP server running on known port
- Redis available
- Nessus scanner available (scan-target container)

### For Queue Tests
- You may submit unroutable targets, it will take a couple minutes for a scan to fail
- At least one scan must be attempted via valid target
- You may add one valid, then fill rest with bogus targets, then enqueue some more bogus, then enqueue real target

### For Failure Mode Tests
- Test with unreachable targets, it will take couple of minutes to fail scan targeting unreachable ip

---

## Success Criteria

1. **MCP E2E**: All scan types work through full MCP protocol
2. **Queue Accuracy**: Position and wait time within reasonable bounds
3. **Failure Modes**: Graceful handling, proper error messages

---

## Configuration

### Scanner Concurrency (configured in Phase 5)

```yaml
# config/scanners.yaml - per scanner
max_concurrent_scans: 2

# scanners/registry.py - default
DEFAULT_MAX_CONCURRENT_SCANS = 2
```

### MCP Test Port

```python
# tests/conftest.py
MCP_TEST_PORT = int(os.getenv("MCP_TEST_PORT", "8000"))
```

---

## Out of Scope (Phase 6)

- Performance/load testing
- Queue rejection logic (queues should queue, not reject)
- Multi-worker testing
- Auto-retry logic

---

## Future Phases

| Phase | Focus |
|-------|-------|
| Phase 7 | Scan cancellation, batch submission |
| Phase 8 | Webhooks, scheduled scans |
| Phase 9 | Multi-worker, horizontal scaling |