# Test Workflow: Phases 0 + 1 Functionality

> **Purpose**: Comprehensive test workflow demonstrating MCP server functionality for vulnerability scanning
> **Based on**: nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md
> **Test Hosts**: 172.32.0.215 (randy/randylovesgoldfish1998), 172.32.0.209 (Nessus server)
> **Date**: 2025-11-07

---

## Overview

This workflow tests the complete scan lifecycle through the MCP server:

1. ✅ **Phase 0**: Task queue, task manager, idempotency
2. ✅ **Phase 1**: Nessus scanner integration (READ + WRITE operations)

## Prerequisites

### 1. Environment Setup

```bash
# Activate virtual environment
cd /home/nessus/projects/nessus-api
source venv/bin/activate

# Verify Nessus is accessible
curl -k https://172.32.0.209:8834/server/status

# Expected output:
# {"status":"ready","progress":null,"must_destroy_session":false}
```

### 2. Nessus Configuration

- **URL**: https://172.32.0.209:8834
- **Credentials**: nessus / nessus
- **License**: Nessus Essentials (16 IP limit)
- **Restriction**: `scan_api: false` (bypassed via Web UI simulation)

### 3. Test Hosts

| Host | Purpose | Credentials |
|------|---------|-------------|
| 172.32.0.209 | Nessus server itself | N/A (network scan only) |
| 172.32.0.215 | Ubuntu target | randy / randylovesgoldfish1998 |

---

## Workflow 1: Untrusted Network Scan (Phase 0 + 1)

**Objective**: Scan target without credentials (network discovery only)

### Step 1.1: Dynamic X-API-Token Fetching

```bash
# Test wrapper's token fetching
cd /home/nessus/projects/nessus-api
python nessusAPIWrapper/get_api_token.py

# Expected: UUID-like token (e.g., 778F4A9C-D797-4817-B110-EC427B724486)
```

**MCP Scanner Equivalent**:
```python
# Automatically called during authentication
await scanner._fetch_api_token()
assert scanner._api_token is not None
```

### Step 1.2: Authentication Test

```bash
# Test wrapper authentication
python -c "
import sys
sys.path.insert(0, 'nessusAPIWrapper')
from manage_scans import authenticate
api_token, session_token = authenticate('nessus', 'nessus')
print(f'API Token: {api_token}')
print(f'Session Token: {session_token[:20]}...')
"
```

**MCP Scanner Equivalent**:
```bash
cd mcp-server
python -c "
import asyncio
from scanners.nessus_scanner import NessusScanner

async def test():
    scanner = NessusScanner(
        url='https://172.32.0.209:8834',
        username='nessus',
        password='nessus',
        verify_ssl=False
    )
    await scanner._authenticate()
    print(f'✓ API Token: {scanner._api_token}')
    print(f'✓ Session Token: {scanner._session_token[:20]}...')
    await scanner.close()

asyncio.run(test())
"
```

### Step 1.3: Create Untrusted Scan

**Wrapper Method**:
```bash
python nessusAPIWrapper/manage_scans.py create \
    "Test Untrusted Scan" \
    "172.32.0.209" \
    "Network discovery without credentials"

# Expected: [SUCCESS] New scan ID: <scan_id>
```

**MCP Scanner Method**:
```bash
cd mcp-server
python -c "
import asyncio
from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest

async def test():
    scanner = NessusScanner(
        url='https://172.32.0.209:8834',
        username='nessus',
        password='nessus',
        verify_ssl=False
    )

    request = ScanRequest(
        name='MCP Test - Untrusted Scan',
        targets='172.32.0.209',
        description='Network discovery test',
        scan_type='untrusted'
    )

    scan_id = await scanner.create_scan(request)
    print(f'✓ Created scan ID: {scan_id}')

    # Cleanup
    await scanner.delete_scan(scan_id)
    await scanner.close()

asyncio.run(test())
"
```

### Step 1.4: Launch, Monitor, and Export Scan

**Complete Workflow Test**:
```bash
cd mcp-server
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestWriteOperations::test_export_results_from_completed_scan -v -s
```

**Expected Output**:
```
✓ Created scan ID=<id>
✓ Launched scan UUID=<uuid>
  [10s] Status: running, Progress: 5%
  [20s] Status: running, Progress: 15%
  ...
  [180s] Status: completed, Progress: 100%
✓ Scan completed, exporting results...
✓ Exported results: <bytes> bytes
```

---

## Workflow 2: READ Operations Testing

**Objective**: Verify all READ operations work with Nessus Essentials API

### Test 2.1: Server Status Check

```bash
cd mcp-server
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestReadOperations::test_get_server_status -v -s
```

### Test 2.2: List Scans

```bash
cd mcp-server
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestReadOperations::test_list_scans -v -s
```

### Test 2.3: Get Scan Details

```bash
cd mcp-server
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestReadOperations::test_get_scan_details -v -s
```

---

## Workflow 3: WRITE Operations Testing

**Objective**: Verify Web UI simulation bypasses `scan_api: false` restriction

### Test 3.1: Create Scan

```bash
cd mcp-server
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestWriteOperations::test_create_scan_untrusted -v -s
```

### Test 3.2: Full Lifecycle (Create → Launch → Stop → Delete)

```bash
cd mcp-server
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestWriteOperations::test_create_launch_stop_delete_workflow -v -s
```

**Expected Output**:
```
✓ Step 1: Created scan ID=<id>
✓ Step 2: Launched scan UUID=<uuid>
✓ Step 3: Scan status=running, progress=<percent>%
✓ Step 4: Stopped scan
✓ Step 5: Final status=failed
✓ Step 6: Deleted scan
```

---

## Workflow 4: Error Handling Tests

**Objective**: Verify proper error handling for edge cases

### Test 4.1: Invalid Credentials

```bash
cd mcp-server
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestErrorHandling::test_invalid_credentials -v -s
```

### Test 4.2: Non-Existent Scan

```bash
cd mcp-server
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestErrorHandling::test_scan_not_found -v -s
```

### Test 4.3: Double Launch Prevention

```bash
cd mcp-server
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestErrorHandling::test_launch_already_running_scan -v -s
```

---

## Workflow 5: Phase 0 + Phase 1 Integration

**Objective**: Test complete MCP server workflow (queue → worker → scanner)

### Test 5.1: Queue Operations

```bash
cd mcp-server
python -m pytest tests/integration/test_queue.py -v
```

### Test 5.2: Task Manager

```bash
cd mcp-server
python -m pytest tests/integration/test_phase0_integration.py -v
```

### Test 5.3: Idempotency

```bash
cd mcp-server
python -m pytest tests/integration/test_idempotency.py -v
```

### Test 5.4: End-to-End Workflow

**NOTE**: This requires the MCP server and worker to be running.

```bash
# Terminal 1: Start Redis (if not running)
# (Redis should already be running from Docker)

# Terminal 2: Start scanner worker
cd mcp-server
source ../venv/bin/activate
export NESSUS_URL=https://172.32.0.209:8834
export NESSUS_USERNAME=nessus
export NESSUS_PASSWORD=nessus
python -m worker.scanner_worker

# Terminal 3: Run end-to-end test
cd mcp-server
source ../venv/bin/activate
python -m pytest tests/integration/test_phase1_workflow.py -v -s
```

---

## Workflow 6: Authenticated Scan (Future: Phase 1B)

**Objective**: Scan target with SSH credentials (172.32.0.215)

**NOTE**: Credential configuration not yet implemented. This workflow is a placeholder.

### Step 6.1: Create Scan with Credentials

```bash
# Wrapper method (for reference)
python nessusAPIWrapper/manage_scans.py create \
    "Authenticated Scan - 172.32.0.215" \
    "172.32.0.215" \
    "SSH credential scan"

# Get scan ID, then configure credentials
python nessusAPIWrapper/manage_credentials.py <scan_id>

# Edit scan_<id>_ssh_credentials.json:
# {
#   "username": "randy",
#   "password": "randylovesgoldfish1998",
#   "elevate_privileges_with": "Nothing"
# }

# Import credentials
python nessusAPIWrapper/manage_credentials.py <scan_id> scan_<id>_ssh_credentials.json

# Launch scan
python nessusAPIWrapper/launch_scan.py launch <scan_id>
```

**MCP Scanner Method** (planned for Phase 1B):
```python
# Future implementation
request = ScanRequest(
    name="MCP Test - Authenticated Scan",
    targets="172.32.0.215",
    description="SSH credential scan",
    scan_type="trusted_basic",
    credentials={
        "username": "randy",
        "password": "randylovesgoldfish1998",
        "auth_method": "password",
        "elevate_privileges_with": "Nothing"
    }
)
```

---

## Success Criteria

### Phase 0 (Task Management)
- ✅ Tasks can be queued to Redis
- ✅ Task manager stores task metadata
- ✅ Idempotency prevents duplicate scans
- ✅ State transitions follow valid rules

### Phase 1 (Scanner Integration)
- ✅ X-API-Token dynamically fetched from nessus6.js
- ✅ Authentication produces valid session token
- ✅ READ operations work (list scans, get status, export results)
- ✅ WRITE operations work (create, launch, stop, delete scans)
- ✅ Web UI simulation bypasses `scan_api: false` restriction
- ✅ Error handling for 401/403/404/409 HTTP status codes
- ✅ Session cleanup prevents resource leaks

### Integration
- ✅ Worker picks up tasks from queue
- ✅ Scanner executes scans via Nessus
- ✅ Results exported as .nessus XML
- ✅ Task state updated throughout lifecycle

---

## Running Full Test Suite

```bash
cd mcp-server
source ../venv/bin/activate

# Run all integration tests
python -m pytest tests/integration/test_nessus_read_write_operations.py -v -s

# Run specific test categories
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestReadOperations -v
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestWriteOperations -v
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestErrorHandling -v
python -m pytest tests/integration/test_nessus_read_write_operations.py::TestSessionManagement -v
```

---

## Troubleshooting

### Issue: Connection Refused to Nessus

```bash
# Check Nessus is running
curl -k https://172.32.0.209:8834/server/status

# If fails, verify Docker container
cd /home/nessus/docker/nessus
docker compose ps
docker compose logs nessus-pro | tail -50
```

### Issue: X-API-Token Extraction Failed

```bash
# Manually test token extraction
python nessusAPIWrapper/get_api_token.py

# Should output UUID-like token
# If fails, check Nessus Web UI is accessible:
curl -k https://172.32.0.209:8834/nessus6.js | grep -o 'getApiToken[^}]\+return[^}]\+' | head -1
```

### Issue: HTTP 412 Precondition Failed

**Cause**: Using API endpoints instead of Web UI simulation

**Solution**: Ensure scanner uses Web UI headers:
- `X-API-Token`: Dynamically fetched token
- `X-Cookie`: Session token
- `X-KL-kfa-Ajax-Request: Ajax_Request` (for launch/stop operations)

### Issue: Scan Not Starting

```bash
# Check scan status
cd mcp-server
python -c "
import asyncio
from scanners.nessus_scanner import NessusScanner

async def check(scan_id):
    scanner = NessusScanner(
        url='https://172.32.0.209:8834',
        username='nessus',
        password='nessus',
        verify_ssl=False
    )
    status = await scanner.get_status(scan_id)
    print(f'Status: {status}')
    await scanner.close()

asyncio.run(check(<scan_id>))
"
```

---

## Next Steps

1. **Phase 1B**: Add credential configuration support
2. **Phase 2**: Implement schema-driven result parsing (.nessus XML → JSON)
3. **Phase 3**: Add observability (logging, metrics, tracing)
4. **Phase 4**: Production hardening (secrets management, rate limiting, monitoring)

---

## References

- [MCP_WORKFLOW_GUIDE.md](../../nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md) - Wrapper workflow patterns
- [README.md](../../nessusAPIWrapper/README.md) - Wrapper overview and authentication
- [PHASE_0_FOUNDATION.md](../phases/PHASE_0_FOUNDATION.md) - Task management design
- [PHASE_1A_SCANNER_REWRITE.md](../phases/PHASE_1A_SCANNER_REWRITE.md) - Scanner implementation plan
- [PHASE_1A_COMPLETION_REPORT.md](../phases/PHASE_1A_COMPLETION_REPORT.md) - Previous implementation status

---

**Document Version**: 1.0
**Created**: 2025-11-07
**Last Updated**: 2025-11-07
**Status**: Ready for Testing
