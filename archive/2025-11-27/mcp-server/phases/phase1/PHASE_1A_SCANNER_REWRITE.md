# Phase 1A: Scanner Interface Rewrite (Proven Patterns)

> **Purpose**: Replace scanner implementation with patterns proven in nessusAPIWrapper
> **Duration**: 2-3 days
> **Status**: 🟡 In Progress
> **Prerequisites**: Phase 0 concepts understood, working Nessus instance

---

## Problem Statement

The initial Phase 1 scanner implementation (`scanners/nessus_scanner.py`) was written from scratch without following the **proven patterns** established in `nessusAPIWrapper/`. This led to:

- **Unvalidated HTTP patterns** - No verification against working wrapper code
- **Potential API mismatches** - Header structure, endpoint paths, request formats
- **Missing error handling** - Wrapper has specific patterns for 412/403/404/409 errors
- **Untested authentication flow** - Session token handling differs from proven approach

## Solution: Pattern-Based Rewrite

Phase 1A will **rewrite the scanner interface** using the battle-tested patterns from `nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md`, ensuring:

1. ✅ **Proven authentication** - Exact header structure from `manage_scans.py:27-84`
2. ✅ **Validated endpoints** - HTTP paths/methods confirmed working
3. ✅ **Error handling** - Specific 412/403/404/409 patterns from wrappers
4. ✅ **Untrusted scan focus** - Network-only scans (no credentials yet)
5. ✅ **Raw .nessus export** - Defer schema transformation to Phase 2

---

## Scope of Phase 1A

### What Gets Rewritten

| Component | Action | Reason |
|-----------|--------|--------|
| `scanners/base.py` | **Review + Update** | Ensure interface matches wrapper capabilities |
| `scanners/nessus_scanner.py` | **Complete Rewrite** | Follow proven patterns from workflow guide |
| `worker/scanner_worker.py` | **Update Scanner Calls** | Adapt to new interface if needed |
| `tests/integration/test_nessus_scanner.py` | **New Tests** | Compare outputs with wrapper scripts |

### What Stays Intact

| Component | Status | Reason |
|-----------|--------|--------|
| `core/task_manager.py` | ✅ **Keep** | File-based storage works well |
| `core/queue.py` | ✅ **Keep** | Redis queue implementation solid |
| `core/types.py` | ✅ **Keep** | State machine is correct |
| `tools/mcp_server.py` | ✅ **Keep** | FastMCP tools structure good |
| Docker setup | ✅ **Keep** | Container architecture correct |

### Docker Networking Verification

**New Requirement**: Add connectivity test to ensure MCP containers can reach Nessus at `https://localhost:8834`.

---

## Phase 1A Task Breakdown

### Task 1.1: Docker Network Connectivity Test

**Objective**: Verify MCP containers can reach Nessus instance

**Actions**:
- [ ] Create `tests/integration/test_connectivity.py`
- [ ] Test HTTP connection to `https://localhost:8834/server/status`
- [ ] Verify SSL certificate handling (self-signed)
- [ ] Test from both `mcp-api` and `scanner-worker` containers
- [ ] Document network configuration in docker-compose.yml

**Validation**:
```bash
# From host
curl -k https://localhost:8834/server/status

# From container
docker exec nessus-mcp-api-dev curl -k https://localhost:8834/server/status
```

**Expected Output**: `{"status": "ready", "progress": null}`

---

### Task 1.2: Analyze Wrapper Patterns

**Objective**: Extract exact patterns from proven wrapper code

**Actions**:
- [ ] Read `nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md` completely
- [ ] Study `nessusAPIWrapper/manage_scans.py` authentication (lines 27-84)
- [ ] Study `nessusAPIWrapper/manage_scans.py` create_scan (lines 312-424)
- [ ] Study `nessusAPIWrapper/launch_scan.py` launch_scan (lines 117-163)
- [ ] Study `nessusAPIWrapper/list_scans.py` status checking (lines 18-50)
- [ ] Study `nessusAPIWrapper/export_vulnerabilities.py` export flow
- [ ] Document exact HTTP patterns (headers, endpoints, payloads)

**Deliverable**: Pattern extraction document with:
- Authentication flow (session token acquisition)
- Request header structure
- Endpoint URLs and methods
- Request/response formats
- Error codes and handling

---

### Task 1.3: Update Scanner Base Interface

**Objective**: Ensure `ScannerInterface` matches wrapper capabilities

**File**: `scanners/base.py`

**Review Checklist**:
- [ ] `create_scan()` signature supports untrusted scans
- [ ] `launch_scan()` returns scan_uuid (matches wrapper)
- [ ] `get_status()` returns progress + status + info dict
- [ ] `export_results()` returns raw bytes (.nessus XML)
- [ ] `stop_scan()` and `delete_scan()` signatures correct
- [ ] Add `close()` method for cleanup

**Potential Changes**:
```python
# May need to add these to ScanRequest
@dataclass
class ScanRequest:
    targets: str
    name: str
    scan_type: str = "untrusted"
    description: str = ""
    template_uuid: Optional[str] = None  # Allow override
    folder_id: int = 3  # My Scans
    scanner_id: int = 1  # Local scanner
```

---

### Task 1.4: Rewrite NessusScanner (Core Implementation)

**Objective**: Implement async scanner using proven wrapper patterns

**File**: `scanners/nessus_scanner.py`

**Implementation Checklist**:

#### 1.4.1: Authentication (Pattern from `manage_scans.py:27-84`)
- [ ] Implement `_authenticate()` method
- [ ] POST to `/session` with username/password
- [ ] Extract `token` from response
- [ ] Store session_token for subsequent requests
- [ ] Use static API token: `af824aba-e642-4e63-a49b-0810542ad8a5`
- [ ] Build headers exactly:
  ```python
  {
      "X-API-Token": "af824aba-e642-4e63-a49b-0810542ad8a5",
      "X-Cookie": f"token={session_token}",
      "Content-Type": "application/json"
  }
  ```

#### 1.4.2: Create Scan (Pattern from `manage_scans.py:312-424`)
- [ ] Implement `create_scan(request: ScanRequest) -> int`
- [ ] Use template UUID: `ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66`
- [ ] POST to `/scans` with exact payload structure:
  ```json
  {
    "uuid": "<template_uuid>",
    "settings": {
      "name": "<scan_name>",
      "text_targets": "<targets>",
      "description": "<description>",
      "enabled": true,
      "folder_id": 3,
      "scanner_id": 1
    }
  }
  ```
- [ ] Parse response for `scan.id`
- [ ] Return scan_id as integer

#### 1.4.3: Launch Scan (Pattern from `launch_scan.py:117-163`)
- [ ] Implement `launch_scan(scan_id: int) -> str`
- [ ] POST to `/scans/{scan_id}/launch`
- [ ] Include all required headers (X-API-Token, X-Cookie)
- [ ] Add Web UI simulation marker: `X-KL-kfa-Ajax-Request: Ajax_Request`
- [ ] Parse response for `scan_uuid`
- [ ] Return scan_uuid as string

#### 1.4.4: Get Status (Pattern from `list_scans.py` + inline checking)
- [ ] Implement `get_status(scan_id: int) -> Dict[str, Any]`
- [ ] GET `/scans/{scan_id}`
- [ ] Extract `info` section from response
- [ ] Map Nessus status to MCP status:
  ```python
  NESSUS_TO_MCP = {
      "pending": "queued",
      "running": "running",
      "paused": "running",
      "completed": "completed",
      "canceled": "failed",
      "stopped": "failed",
      "aborted": "failed",
  }
  ```
- [ ] Return dict with:
  ```python
  {
      "status": mapped_status,
      "progress": info.get("progress", 0),
      "uuid": info["uuid"],
      "info": info  # Full response for debugging
  }
  ```

#### 1.4.5: Export Results (Pattern from `export_vulnerabilities.py`)
- [ ] Implement `export_results(scan_id: int) -> bytes`
- [ ] POST to `/scans/{scan_id}/export` with `{"format": "nessus"}`
- [ ] Extract `file` ID from response
- [ ] Poll `/scans/{scan_id}/export/{file_id}/status` until ready
- [ ] Max poll time: 5 minutes (150 iterations × 2 seconds)
- [ ] GET `/scans/{scan_id}/export/{file_id}/download`
- [ ] Return raw bytes (XML content)

#### 1.4.6: Stop and Delete
- [ ] Implement `stop_scan(scan_id: int) -> bool`
- [ ] POST to `/scans/{scan_id}/stop`
- [ ] Return True if 200 OK
- [ ] Implement `delete_scan(scan_id: int) -> bool`
- [ ] DELETE `/scans/{scan_id}`
- [ ] Return True if 200 OK

#### 1.4.7: Error Handling Patterns
- [ ] Handle 412 Precondition Failed → "API restriction, use Web UI auth"
- [ ] Handle 403 Forbidden → Re-authenticate and retry once
- [ ] Handle 404 Not Found → "Scan ID not found"
- [ ] Handle 409 Conflict → "Scan already running or locked"
- [ ] Handle connection errors → Retry with exponential backoff (3 attempts)

#### 1.4.8: Session Management
- [ ] Implement `close()` method to cleanup httpx.AsyncClient
- [ ] Re-authenticate on 401 Unauthorized
- [ ] Token expiration handling

---

### Task 1.5: Update Worker Scanner Integration

**Objective**: Ensure worker uses new scanner interface correctly

**File**: `worker/scanner_worker.py`

**Review Checklist**:
- [ ] Worker calls `scanner.create_scan()` correctly
- [ ] Worker calls `scanner.launch_scan()` correctly
- [ ] Worker polls `scanner.get_status()` every 30 seconds
- [ ] Worker saves raw `.nessus` to `{task_dir}/scan_native.nessus`
- [ ] Worker handles scanner exceptions properly
- [ ] Worker calls `scanner.close()` on cleanup

**Potential Updates**:
```python
# In _process_task()
scanner = self.scanner_registry.get_instance(...)

try:
    # Create scan
    scan_id = await scanner.create_scan(ScanRequest(...))

    # Update task with scan_id
    self.task_manager.update_status(
        task_id, ScanState.RUNNING, nessus_scan_id=scan_id
    )

    # Launch scan
    scan_uuid = await scanner.launch_scan(scan_id)

    # Poll until complete (30 second intervals)
    while elapsed < timeout:
        await asyncio.sleep(30)
        status = await scanner.get_status(scan_id)

        if status["status"] == "completed":
            # Export results
            results = await scanner.export_results(scan_id)
            task_dir = self.task_manager.data_dir / task_id
            (task_dir / "scan_native.nessus").write_bytes(results)

            self.task_manager.update_status(task_id, ScanState.COMPLETED)
            return

finally:
    await scanner.close()
```

---

### Task 1.6: Integration Tests with Wrapper Comparison

**Objective**: Validate new scanner produces same results as wrapper

**File**: `tests/integration/test_nessus_scanner_vs_wrapper.py`

**Test Cases**:

#### Test 1: Authentication
```python
async def test_authentication_matches_wrapper():
    """Verify new scanner authenticates same as wrapper."""
    # Run wrapper authenticate
    wrapper_api_token, wrapper_session_token = authenticate("nessus", "nessus")

    # Run new scanner authenticate
    scanner = NessusScanner(...)
    await scanner._authenticate()

    # Compare tokens
    assert scanner._static_token == wrapper_api_token
    assert scanner._session_token == wrapper_session_token
```

#### Test 2: Scan Creation
```python
async def test_create_scan_matches_wrapper():
    """Compare scan creation outputs."""
    # Create scan with wrapper
    wrapper_result = create_scan(
        api_token, session_token,
        name="Test Scan",
        targets="172.32.0.215"
    )
    wrapper_scan_id = wrapper_result["scan"]["id"]

    # Create scan with new scanner
    scanner = NessusScanner(...)
    scanner_scan_id = await scanner.create_scan(
        ScanRequest(name="Test Scan", targets="172.32.0.215")
    )

    # Both should succeed and return integer IDs
    assert isinstance(wrapper_scan_id, int)
    assert isinstance(scanner_scan_id, int)

    # Cleanup both
    delete_scan(wrapper_scan_id, api_token, session_token)
    await scanner.delete_scan(scanner_scan_id)
```

#### Test 3: Launch Scan
```python
async def test_launch_scan_matches_wrapper():
    """Compare launch behavior."""
    # Create scan first
    scan_id = await scanner.create_scan(...)

    # Launch with new scanner
    scan_uuid = await scanner.launch_scan(scan_id)

    # Verify it's running
    status = await scanner.get_status(scan_id)
    assert status["status"] in ["queued", "running"]
    assert status["uuid"] == scan_uuid

    # Stop and cleanup
    await scanner.stop_scan(scan_id)
    await scanner.delete_scan(scan_id)
```

#### Test 4: Status Polling
```python
async def test_status_progression():
    """Verify status changes through lifecycle."""
    scan_id = await scanner.create_scan(...)
    scan_uuid = await scanner.launch_scan(scan_id)

    # Track status progression
    statuses_seen = []
    for _ in range(60):  # 30 minutes max
        await asyncio.sleep(30)
        status = await scanner.get_status(scan_id)
        statuses_seen.append(status["status"])

        if status["status"] == "completed":
            break

    # Should see progression: queued/running → running → completed
    assert "running" in statuses_seen
    assert statuses_seen[-1] == "completed"

    # Cleanup
    await scanner.delete_scan(scan_id)
```

#### Test 5: Export Results
```python
async def test_export_results_format():
    """Verify exported .nessus format matches wrapper."""
    # Run completed scan
    scan_id = await scanner.create_scan(...)
    await scanner.launch_scan(scan_id)

    # Wait for completion
    await poll_until_complete(scanner, scan_id, timeout=1800)

    # Export with new scanner
    scanner_results = await scanner.export_results(scan_id)

    # Verify XML structure
    assert scanner_results.startswith(b'<?xml version="1.0"')
    assert b'<NessusClientData_v2>' in scanner_results
    assert b'<Report' in scanner_results

    # Compare with wrapper export (same scan)
    wrapper_results = export_scan_file(scan_id, "Test", "nessus")

    # Both should be valid .nessus XML
    assert len(scanner_results) > 1000  # Non-trivial size

    # Cleanup
    await scanner.delete_scan(scan_id)
```

---

### Task 1.7: End-to-End MCP Server Test

**Objective**: Verify complete workflow through FastMCP tools

**File**: `tests/integration/test_phase1a_e2e.py`

**Test Scenario**:
```python
async def test_full_untrusted_scan_workflow():
    """
    Full workflow test:
    1. Submit scan via run_untrusted_scan tool
    2. Task queued to Redis
    3. Worker picks up task
    4. Scanner creates scan in Nessus
    5. Scanner launches scan
    6. Worker polls until complete
    7. Worker exports results
    8. Task marked COMPLETED
    9. get_scan_status returns final status
    """
    client = NessusMCPClient()

    try:
        # Submit scan
        task = await client.submit_scan(
            targets="172.32.0.215",
            name="Phase 1A E2E Test"
        )

        assert "task_id" in task
        assert task["status"] == "queued"

        # Poll until complete (30 minute timeout)
        final_status = await client.poll_until_complete(
            task["task_id"],
            timeout=1800,
            poll_interval=30
        )

        assert final_status["status"] == "completed"
        assert final_status["nessus_scan_id"] is not None

        # Verify results file exists
        task_dir = Path("/app/data/tasks") / task["task_id"]
        results_file = task_dir / "scan_native.nessus"
        assert results_file.exists()

        # Verify results are valid XML
        results = results_file.read_bytes()
        assert results.startswith(b'<?xml version="1.0"')
        assert b'<NessusClientData_v2>' in results

    finally:
        await client.close()
```

---

### Task 1.8: Documentation Updates

**Objective**: Document new scanner patterns and differences from Phase 1

**Actions**:
- [ ] Create `mcp-server/scanners/SCANNER_PATTERNS.md`
  - Document exact HTTP patterns used
  - Reference wrapper source for each pattern
  - Explain differences from original Phase 1 implementation
- [ ] Update `mcp-server/README.md`
  - Mark Phase 1A complete
  - Reference new scanner documentation
- [ ] Create `PHASE1A_COMPLETION_REPORT.md`
  - What was rewritten
  - What stayed the same
  - Test results comparison
  - Known limitations (untrusted only)

---

## Validation Strategy

### Pre-Implementation Validation

Before writing code:
1. ✅ Read all wrapper files referenced in MCP_WORKFLOW_GUIDE.md
2. ✅ Extract exact HTTP patterns into reference document
3. ✅ Verify Docker networking from containers
4. ✅ Test wrapper scripts still work (baseline)

### Post-Implementation Validation

After rewriting scanner:
1. ✅ Unit tests pass (authentication, create, launch, status, export)
2. ✅ Integration tests pass (comparison with wrapper outputs)
3. ✅ E2E test passes (full MCP workflow)
4. ✅ No regressions in TaskManager, Queue, or FastMCP tools
5. ✅ Worker successfully processes untrusted scan end-to-end

### Comparison Tests

For each operation, compare:
| Operation | Wrapper Output | Scanner Output | Match? |
|-----------|---------------|----------------|--------|
| Authenticate | token string | token string | ✅ |
| Create scan | scan_id int | scan_id int | ✅ |
| Launch scan | scan_uuid str | scan_uuid str | ✅ |
| Get status | status dict | status dict | ✅ |
| Export results | .nessus bytes | .nessus bytes | ✅ |

---

## Success Criteria

Phase 1A is complete when:

- [ ] **Docker connectivity verified** - Containers can reach Nessus at localhost:8834
- [ ] **Scanner rewritten** - Uses proven patterns from wrapper
- [ ] **Authentication works** - Exact headers and tokens from wrapper
- [ ] **Create scan works** - Returns scan_id matching wrapper behavior
- [ ] **Launch scan works** - Scan starts running in Nessus
- [ ] **Status polling works** - Progress updates every 30 seconds
- [ ] **Export works** - Raw .nessus XML saved successfully
- [ ] **Error handling works** - 412/403/404/409 handled per wrapper patterns
- [ ] **Integration tests pass** - All comparison tests green
- [ ] **E2E test passes** - Full MCP workflow completes
- [ ] **Worker unchanged** - Or updated minimally for new interface
- [ ] **No regressions** - TaskManager, Queue, FastMCP still work

---

## Timeline Estimate

| Task | Duration | Dependencies |
|------|----------|--------------|
| 1.1: Docker connectivity | 1 hour | None |
| 1.2: Analyze wrapper patterns | 3 hours | None |
| 1.3: Update base interface | 1 hour | Task 1.2 |
| 1.4: Rewrite NessusScanner | 8 hours | Task 1.2, 1.3 |
| 1.5: Update worker | 2 hours | Task 1.4 |
| 1.6: Integration tests | 4 hours | Task 1.4 |
| 1.7: E2E test | 2 hours | Task 1.5, 1.6 |
| 1.8: Documentation | 2 hours | All tasks |

**Total**: ~23 hours (2-3 days)

---

## Risk Mitigation

### Risk: Wrapper patterns don't work in async context

**Mitigation**:
- Wrapper uses `requests` (sync), scanner uses `httpx` (async)
- HTTP patterns are identical (POST/GET to same endpoints)
- Headers and payloads are byte-for-byte the same
- Only difference is async/await syntax

### Risk: Docker networking issues

**Mitigation**:
- Test connectivity FIRST (Task 1.1)
- Document network configuration
- Use `host.docker.internal` if needed (Mac/Windows)
- Use `--network host` if needed (Linux)

### Risk: Session token expiration during long scans

**Mitigation**:
- Wrapper already handles this (re-authenticate on 401)
- Implement same pattern in new scanner
- Add token refresh logic after N hours

### Risk: Breaking existing MCP components

**Mitigation**:
- Keep TaskManager, Queue, FastMCP untouched
- Only update scanner interface and worker calls
- Run existing unit tests after changes
- Rollback plan: Keep old scanner as `nessus_scanner_old.py`

---

## Rollback Plan

If Phase 1A fails or takes too long:

1. **Keep old implementation**:
   - Rename current `nessus_scanner.py` to `nessus_scanner_v1.py`
   - Keep in repo for reference

2. **Partial rollback**:
   - Use wrapper scripts directly via subprocess (temporary)
   - Async wrapper: `await asyncio.to_thread(wrapper_function)`
   - Not ideal but works

3. **Defer credentials**:
   - Phase 1A focuses on untrusted scans
   - Credentials can be added in Phase 1B
   - E2E workflow still validates core architecture

---

## Next Steps After Phase 1A

Once Phase 1A is complete:

1. **Merge to main**: Commit with message `feat: Complete Phase 1A - Scanner rewrite with proven patterns`
2. **Tag**: `git tag phase-1a-complete`
3. **Validate**: Run full test suite, verify no regressions
4. **Proceed to Phase 1B**: Add trusted_basic and trusted_privileged scan types
5. **Then Phase 2**: Schema transformation and result parsing

---

## Reference Documents

- **MCP Workflow Guide**: `nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md`
- **Wrapper README**: `nessusAPIWrapper/README.md`
- **Original Phase 0**: `mcp-server/phases/PHASE_0_FOUNDATION.md`
- **Original Phase 1**: `mcp-server/phases/PHASE_1_REAL_NESSUS.md`

---

**Document Version**: 1.0
**Created**: 2025-01-07
**Status**: 🟡 In Progress
**Owner**: MCP Server Development Team
