# Nessus Scanner Failure Troubleshooting Guide

## Issue Summary

**Status**: ACTIVE INVESTIGATION NEEDED
**First Observed**: 2025-11-24
**Severity**: HIGH - Blocks E2E testing

Nessus scans are consistently failing/aborting after being queued, despite all MCP server code bugs being fixed. The failure occurs at the Nessus scanner level, not in our application code.

---

## Symptoms

### Observed Behavior
1. **Scan Creation**: ✅ Successful
   - Scans are created in Nessus
   - Nessus scan IDs are assigned (e.g., 47, 50, 53)
   - Scan metadata is correctly configured

2. **Scan Launch**: ✅ Successful
   - Worker successfully calls `launch_scan()`
   - Scan UUID is returned
   - No errors during launch

3. **Scan Queueing**: ✅ Successful
   - Scans enter "queued" state
   - Worker polls status successfully

4. **Scan Execution**: ❌ FAILS
   - Scans stay in "queued" for extended periods (60-150 seconds)
   - Then transition to "failed" or "aborted"
   - Progress remains at 0%
   - No actual scanning occurs

### Failed Scan Examples
```
Scan ID 47: Status "aborted"
- Name: SUCCESS Test - 20251124-152732
- Target: 172.32.0.215
- Created: 15:27:32, Aborted by: ~15:40:00

Scan ID 50: Status "aborted"
- Name: SessionRefresh-20251124-154852
- Target: 172.32.0.215
- Created: 15:48:52, Aborted by: 15:50:28

Scan ID 53: Status "failed"
- Name: SelfScan-20251124-155218
- Target: 172.30.0.3 (scanner itself)
- Created: 15:52:18, Failed by: 15:54:54
```

### Error Messages
- Worker logs: `"Scanner reported failure"`
- Nessus status: `"failed"` or `"aborted"`
- No detailed error messages in worker logs
- No exceptions thrown in application code

---

## Known Facts

### Scanner Environment
- **Scanner Type**: Nessus Professional/Essentials
- **Version**: Unknown (needs verification)
- **License**: Nessus Essentials (restricted)
  - Max IPs: 16
  - Type: "home"
  - Mode: 3
  - Restricted: true
- **Container**: `nessus-pro-1` (Docker)
- **Network**: 172.30.0.3:8834 on `nessus-shared_vpn_net`

### Scanner Configuration (from logs)
```
Scanner Settings:
  engine.min=4
  engine.max=16
  global.max_scans=0
  global.max_hosts=100
  engine.max_hosts=16
  engine.optimal_hosts=2
  (scan)max_hosts=100
  (scan)max_checks=5
```

### Scanner Logs
```bash
# No scan-specific errors found in scanner logs
docker logs nessus-pro-1 --tail 100 2>&1 | grep -iE "(scan|error|fail)"
# Returns: Only license info and configuration settings
```

### MCP Server Code Status
All application bugs have been fixed:
- ✅ X-API-Token extraction working
- ✅ Worker async processing working
- ✅ State transitions working
- ✅ Session refresh implemented
- ✅ Scanner connectivity configured

---

## Possible Root Causes

### Theory 1: Scanner License Restrictions ⚠️
**Likelihood**: HIGH

Nessus Essentials has known restrictions:
- Limited to 16 IPs per scan
- May have scan frequency limits
- May have concurrent scan limits
- "home" license type restrictions

**Evidence**:
- License shows `"restricted": true`
- Multiple rapid scan submissions
- No detailed error messages (typical of license violations)

**Next Steps**:
- Check Nessus Web UI for license warnings
- Review scanner logs in Nessus UI (Settings → About → View Logs)
- Try spacing out scans (wait 5+ minutes between submissions)
- Check if manual Web UI scans work

### Theory 2: Target Unreachability 🔍
**Likelihood**: MEDIUM

Target `172.32.0.215` may not be reachable from scanner network.

**Evidence**:
- Even self-scan (`172.30.0.3`) failed
- But scanner can receive API calls on 172.30.0.3:8834
- Scanner is on `nessus-shared_vpn_net` bridge network

**Counter-Evidence**:
- Scanner responds to HTTP requests on its own IP
- Network connectivity appears functional

**Next Steps**:
- Verify target 172.32.0.215 is up: `ping 172.32.0.215`
- Check scanner can route to target subnet
- Try scanning a known-good target (e.g., scanme.nmap.org)
- Check firewall rules on target

### Theory 3: Scanner Resource Exhaustion 🔍
**Likelihood**: MEDIUM

Scanner may be out of resources due to previous failed scans.

**Evidence**:
- Multiple scans created in short succession (47, 50, 53)
- All staying in queue
- Previous scan (47) still in "aborted" state

**Next Steps**:
- Check scanner resource usage: CPU, memory, disk
- Clear old/failed scans from scanner
- Restart scanner container
- Check scanner process health

### Theory 4: Scanner Policy/Configuration Issues 🔍
**Likelihood**: LOW

The "Advanced Scan" policy may have invalid settings.

**Evidence**:
- Scans use "Advanced Scan" policy
- No custom policy specified in requests

**Next Steps**:
- Try creating scan with different policy (e.g., "Basic Network Scan")
- Check if "Advanced Scan" policy exists and is valid
- Review policy settings in Nessus Web UI

### Theory 5: Scanner Database Corruption 🔍
**Likelihood**: LOW

Scanner database may be corrupted or locked.

**Evidence**:
- Consistent failure pattern across all scans
- No variation in behavior

**Next Steps**:
- Check scanner database integrity
- Restart scanner service
- Check for scanner update/rebuild requirements

---

## Investigation Steps

### Immediate Actions (Priority 1)
```bash
# 1. Check scanner Web UI for errors/warnings
#    Navigate to: https://172.30.0.3:8834
#    Login: nessus / nessus
#    Check: Settings → About → View Logs
#    Check: Recent Scans tab for error details

# 2. Check target connectivity from scanner container
docker exec nessus-pro-1 ping -c 3 172.32.0.215

# 3. Check scanner resource usage
docker stats nessus-pro-1 --no-stream

# 4. Check scanner container logs for detailed errors
docker logs nessus-pro-1 --tail 500 | grep -i error

# 5. Clear old failed scans
# Via Web UI: Scans → Select scan → More → Delete
# Or via API (delete scans 47, 50, 53)
```

### Diagnostic Scan Tests (Priority 2)
```bash
# Test 1: Manual Web UI scan
# 1. Go to Nessus Web UI
# 2. Create scan manually: New Scan → Basic Network Scan
# 3. Target: 172.30.0.3
# 4. Launch and observe behavior
# Expected: Should succeed if scanner is healthy

# Test 2: Scan with longer wait between attempts
# Wait 10 minutes after clearing old scans, then submit ONE scan
docker compose -f dev1/docker-compose.yml exec -T mcp-api python3 -c "
import asyncio
from client.nessus_fastmcp_client import NessusFastMCPClient
from datetime import datetime

async def test():
    async with NessusFastMCPClient(url='http://mcp-api:8000/mcp') as client:
        result = await client.submit_scan(
            targets='172.30.0.3',
            scan_name=f'Diagnostic-{datetime.now().strftime(\"%Y%m%d-%H%M%S\")}'
        )
        print(f'Submitted: {result[\"task_id\"]}')

asyncio.run(test())
"

# Test 3: Check scanner status endpoint
docker compose -f dev1/docker-compose.yml exec -T mcp-api python3 -c "
import asyncio
import httpx

async def check():
    async with httpx.AsyncClient(verify=False) as client:
        # Login
        r = await client.post(
            'https://172.30.0.3:8834/session',
            json={'username': 'nessus', 'password': 'nessus'},
            headers={'X-API-Token': '274e284f-0dd9-4b0e-9bce-e522e7d8990f'}
        )
        token = r.json()['token']

        # Get scanner status
        r = await client.get(
            'https://172.30.0.3:8834/server/status',
            headers={'X-Cookie': f'token={token}', 'X-API-Token': '274e284f-0dd9-4b0e-9bce-e522e7d8990f'}
        )
        print(r.json())

asyncio.run(check())
"
```

### Scanner Restart (Priority 3)
```bash
# If all else fails, try restarting the scanner
docker restart nessus-pro-1

# Wait for scanner to fully initialize (2-3 minutes)
sleep 180

# Verify scanner is up
curl -sk https://172.30.0.3:8834/server/status
```

---

## Workaround for Testing

While investigating scanner issues, use mock/stub scans for MCP server testing:

```python
# Option 1: Test with scan submission only (don't wait for completion)
# This verifies MCP server functionality without scanner dependency

# Option 2: Use a different scanner instance if available
# Configure SCANNER_2_URL in docker-compose.yml

# Option 3: Mock scanner responses for unit tests
# Allows testing of MCP server logic without real scanner
```

---

## Data Collection Checklist

Before troubleshooting session, collect:
- [ ] Nessus Web UI screenshots of failed scans
- [ ] Full scanner container logs: `docker logs nessus-pro-1 > scanner.log`
- [ ] Scanner status JSON: `GET /server/status`
- [ ] Scanner properties JSON: `GET /server/properties`
- [ ] List of existing scans: `GET /scans`
- [ ] Scanner license details: `GET /server/properties` → license info
- [ ] Network connectivity test results
- [ ] Resource usage snapshot: `docker stats nessus-pro-1`

---

## Timeline of Events

**15:27:32** - Scan 47 created (SUCCESS Test)
- Target: 172.32.0.215
- Result: Aborted after ~13 minutes

**15:40:00** (approx) - Scan 47 aborted
- Session token expiration issues observed
- Led to Bug #4 fix (session refresh)

**15:48:52** - Scan 50 created (SessionRefresh test)
- Target: 172.32.0.215
- Result: Aborted after 90 seconds

**15:52:18** - Scan 53 created (SelfScan test)
- Target: 172.30.0.3 (scanner itself)
- Result: Failed after 150 seconds

**Pattern**: All scans fail regardless of target, suggesting scanner-level issue

---

## Related Files

- Worker logs: `dev1/logs/worker.log`
- Task data: `dev1/data/tasks/{task_id}/task.json`
- Scanner implementation: `mcp-server/scanners/nessus_scanner.py`
- Worker polling logic: `mcp-server/worker/scanner_worker.py:202-294`

---

## Status: NEEDS INVESTIGATION

**Next Session Goals**:
1. Access Nessus Web UI and check for error messages
2. Review scanner internal logs via Web UI
3. Determine if license restrictions are causing failures
4. Test manual scan via Web UI to isolate scanner vs. API issue
5. Clear failed scans and test with single scan submission
6. If needed, restart scanner and retest

**Success Criteria**:
- At least one scan completes successfully from queued → running → completed
- Understand root cause of failure
- Implement fix or workaround
