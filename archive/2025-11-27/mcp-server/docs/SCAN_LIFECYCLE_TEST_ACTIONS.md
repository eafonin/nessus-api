# Nessus Scan Lifecycle Test Actions

**Aligned with nessusAPIWrapper functionality**

---

## Prerequisites

- [ ] Nessus server accessible (https://172.32.0.209:8834)
- [ ] Credentials: nessus/nessus
- [ ] Test target: 172.32.0.215 (or other safe target)
- [ ] Environment: NESSUS_URL set correctly for context (host vs container)

---

## Test Suite 1: Basic Workflow (Wrapper-Aligned)

### 1. List Scans (`list_scans.py`)
- [ ] Run: `python nessusAPIWrapper/list_scans.py`
- [ ] Verify authentication succeeds
- [ ] Verify scan list returned
- [ ] Check columns: ID, Name, Status, Last Modified, Targets, Progress
- [ ] Note any existing scans

### 2. Check Server Status (`check_status.py`)
- [ ] Run: `python nessusAPIWrapper/check_status.py`
- [ ] Verify server status returned
- [ ] Check scan_api setting (true/false)
- [ ] Note Nessus edition (Essentials vs Professional)

### 3. Create Scan Manually (UI)
**Note**: Wrapper doesn't support programmatic creation due to Nessus Essentials HTTP 412 limitation
- [ ] Open Nessus Web UI
- [ ] Navigate to Scans → New Scan
- [ ] Select "Basic Network Scan" template
- [ ] Enter name: `TEST_lifecycle_[timestamp]`
- [ ] Enter target: `172.32.0.215`
- [ ] Save scan (do NOT launch yet)
- [ ] Note the Scan ID from UI or list_scans.py

### 4. Get Scan Configuration (`scan_config.py`)
- [ ] Run: `python nessusAPIWrapper/scan_config.py [SCAN_ID]`
- [ ] Verify scan details returned
- [ ] Check Name matches
- [ ] Check Targets matches (settings.text_targets)
- [ ] Check Status is "empty" (not launched)
- [ ] Verify policy/template info present

### 5. Launch Scan (`launch_scan.py`)
- [ ] Run: `python nessusAPIWrapper/launch_scan.py [SCAN_ID]`
- [ ] Verify launch command sent
- [ ] Note scan UUID if returned
- [ ] Wait 10 seconds

### 6. Monitor Status (`list_scans.py`)
- [ ] Run: `python nessusAPIWrapper/list_scans.py`
- [ ] Find test scan in list
- [ ] Verify Status is "running" or "pending"
- [ ] Note Progress percentage
- [ ] Verify scan_start timestamp present
- [ ] Check Nessus Web UI matches

### 7. Check Detailed Status (`check_status.py [SCAN_ID]`)
**Note**: If check_status.py supports scan ID parameter
- [ ] Run: `python nessusAPIWrapper/check_status.py [SCAN_ID]`
- [ ] Verify detailed status returned
- [ ] Check info.status field
- [ ] Check info.progress field
- [ ] Verify hosts being scanned

### 8. Stop Scan (`launch_scan.py stop`)
**Note**: Assuming launch_scan.py has stop functionality
- [ ] Run stop command (check launch_scan.py for syntax)
- [ ] Verify stop command sent
- [ ] Wait 5 seconds
- [ ] Run list_scans.py
- [ ] Verify Status is "stopped" or "canceled"
- [ ] Check Web UI confirms stopped

### 9. Export Results (`export_vulnerabilities.py`)
- [ ] If scan completed naturally, export results
- [ ] Run: `python nessusAPIWrapper/export_vulnerabilities.py [SCAN_ID]`
- [ ] Verify export file created
- [ ] Check filename format
- [ ] Verify .nessus XML format
- [ ] Check file size > 0

### 10. Export Detailed Results (`export_vulnerabilities_detailed.py`)
- [ ] Run: `python nessusAPIWrapper/export_vulnerabilities_detailed.py [SCAN_ID]`
- [ ] Verify detailed export created
- [ ] Compare with regular export
- [ ] Check for additional details/plugins

### 11. Edit Scan (`edit_scan.py`)
- [ ] Run: `python nessusAPIWrapper/edit_scan.py [SCAN_ID]` (check syntax)
- [ ] Update scan name or targets
- [ ] Verify changes saved
- [ ] Run scan_config.py to confirm changes

### 12. Delete Scan (`manage_scans.py delete`)
- [ ] Run: `python nessusAPIWrapper/manage_scans.py delete [SCAN_ID]`
- [ ] Verify deletion command sent
- [ ] Run list_scans.py
- [ ] Verify scan no longer in list
- [ ] Check Web UI confirms deletion

---

## Test Suite 2: Error Handling

### 1. Invalid Scan ID
- [ ] Run: `python nessusAPIWrapper/list_scans.py` with bad ID
- [ ] Verify appropriate error message
- [ ] Check error doesn't crash script

### 2. Non-Existent Scan
- [ ] Run: `python nessusAPIWrapper/scan_config.py 999999`
- [ ] Verify 404 or "not found" error
- [ ] Check error handling graceful

### 3. Launch Already Running
- [ ] Create and launch scan
- [ ] Try to launch again while running
- [ ] Verify appropriate error or idempotent behavior

### 4. Export Before Completion
- [ ] Create scan but don't launch
- [ ] Try to export: `python nessusAPIWrapper/export_vulnerabilities.py [SCAN_ID]`
- [ ] Verify appropriate error (no results)

### 5. Authentication Failure
- [ ] Set wrong credentials in environment
- [ ] Run any wrapper script
- [ ] Verify authentication error reported
- [ ] Restore correct credentials

---

## Test Suite 3: Multiple Scans

### 1. Create Multiple Scans (UI)
- [ ] Create scan A (target: 172.32.0.215)
- [ ] Create scan B (target: 192.168.1.1)
- [ ] Create scan C (target: 10.0.0.1)

### 2. List All
- [ ] Run: `python nessusAPIWrapper/list_scans.py`
- [ ] Verify all 3 scans visible
- [ ] Note each scan ID

### 3. Launch Concurrently
- [ ] Launch scan A
- [ ] Launch scan B
- [ ] Launch scan C
- [ ] Wait 10 seconds

### 4. Monitor All
- [ ] Run list_scans.py repeatedly
- [ ] Verify all scans show status
- [ ] Check progress independently tracked
- [ ] Verify no interference between scans

### 5. Cleanup
- [ ] Stop or wait for completion
- [ ] Delete all test scans
- [ ] Verify list is clean

---

## Test Suite 4: Scan Configuration Checks

### 1. Check Dropdown Options (`check_dropdown_options.py`)
- [ ] Run: `python nessusAPIWrapper/check_dropdown_options.py`
- [ ] Verify available scan templates listed
- [ ] Check policy options
- [ ] Note scanner IDs available

### 2. Verify Settings via Config
- [ ] Create test scan with specific settings
- [ ] Run scan_config.py
- [ ] Verify: name, targets, folder_id, scanner_id
- [ ] Check credentials section (if applicable)

### 3. Credentials Management (`manage_credentials.py`)
- [ ] Create scan with SSH credentials needed
- [ ] Run: `python nessusAPIWrapper/manage_credentials.py [SCAN_ID]`
- [ ] Update SSH username/password
- [ ] Verify credentials saved
- [ ] Check scan_config.py shows credentials

---

## Test Suite 5: Export Formats & Data

### 1. Standard Export
- [ ] Complete a scan
- [ ] Export: `python nessusAPIWrapper/export_vulnerabilities.py [SCAN_ID]`
- [ ] Verify .nessus XML format
- [ ] Check XML structure: NessusClientData_v2
- [ ] Verify Report → ReportHost entries

### 2. Detailed Export
- [ ] Same scan, export detailed
- [ ] Export: `python nessusAPIWrapper/export_vulnerabilities_detailed.py [SCAN_ID]`
- [ ] Compare file sizes (detailed should be larger)
- [ ] Check additional data included

### 3. Export Parsing
- [ ] Parse exported XML
- [ ] Extract: targets, plugin IDs, severity counts
- [ ] Verify data completeness

---

## Test Suite 6: Status Monitoring Patterns

### 1. Status Progression
- [ ] Launch fresh scan
- [ ] Poll every 5 seconds with list_scans.py
- [ ] Document status progression:
  - [ ] empty → pending/running
  - [ ] running (progress 0% → 100%)
  - [ ] completed
- [ ] Time each stage

### 2. Progress Tracking
- [ ] During running scan, check progress
- [ ] Verify progress increments monotonically
- [ ] Note any progress jumps
- [ ] Check progress reaches exactly 100%

### 3. Timestamp Validation
- [ ] Check scan_start timestamp when launched
- [ ] Check scan_end timestamp when completed
- [ ] Calculate elapsed time
- [ ] Verify elapsed = end - start

---

## Test Suite 7: Nessus Essentials Limitations

### 1. Verify API Restriction
- [ ] Run: `python nessusAPIWrapper/check_status.py`
- [ ] Check output for scan_api setting
- [ ] If scan_api: false, document limitation
- [ ] Note: Create scan via API will fail with HTTP 412

### 2. Manual Workaround
- [ ] Document: Scans must be created via Web UI
- [ ] Verify: All other operations work (launch, stop, status, export, delete)
- [ ] Test full lifecycle with UI-created scan

### 3. HTTP 412 Handling
- [ ] If wrapper attempts create scan
- [ ] Verify graceful error handling
- [ ] Check error message is clear
- [ ] Verify no crashes or hangs

---

## Test Suite 8: Wrapper Script Inventory

### Scripts Available
- [x] `list_scans.py` - List all scans
- [x] `check_status.py` - Check server status
- [x] `scan_config.py` - Get scan configuration
- [x] `launch_scan.py` - Launch/stop scans
- [x] `export_vulnerabilities.py` - Export standard results
- [x] `export_vulnerabilities_detailed.py` - Export detailed results
- [x] `edit_scan.py` - Edit scan settings
- [x] `manage_scans.py` - Create/delete scans
- [x] `manage_credentials.py` - Update scan credentials
- [x] `check_dropdown_options.py` - View available options

### Test Each Script
- [ ] Verify each script runs without errors
- [ ] Check help/usage output (--help flag)
- [ ] Test with valid inputs
- [ ] Test with invalid inputs
- [ ] Verify error handling

---

## Test Suite 9: Integration Scenarios

### Scenario A: Quick Scan Workflow
1. [ ] List existing scans
2. [ ] Create scan in UI (name: QUICK_TEST)
3. [ ] Get scan ID from list
4. [ ] Launch scan
5. [ ] Poll status every 10s until complete
6. [ ] Export results
7. [ ] Delete scan

### Scenario B: Interrupted Scan Recovery
1. [ ] Create and launch scan
2. [ ] Let run for 30 seconds
3. [ ] Stop scan
4. [ ] Check status (stopped/canceled)
5. [ ] Re-launch same scan
6. [ ] Verify starts from beginning (not resume)
7. [ ] Let complete
8. [ ] Export and delete

### Scenario C: Scan Editing
1. [ ] Create scan with target A
2. [ ] Get config, verify target A
3. [ ] Edit scan to target B
4. [ ] Get config, verify target B
5. [ ] Launch and verify scans target B
6. [ ] Cleanup

### Scenario D: Credentials Update
1. [ ] Create scan requiring SSH
2. [ ] Initially use placeholder credentials
3. [ ] Launch (will fail/skip SSH checks)
4. [ ] Update credentials via manage_credentials.py
5. [ ] Re-launch scan
6. [ ] Verify SSH checks now work
7. [ ] Export and compare results

---

## Test Suite 10: Performance & Reliability

### 1. Rapid Polling
- [ ] Launch scan
- [ ] Poll list_scans.py every 1 second for 60 seconds
- [ ] Verify no rate limiting
- [ ] Verify no authentication issues
- [ ] Check response times consistent

### 2. Long-Running Scan
- [ ] Create scan with many targets
- [ ] Launch and monitor for 30+ minutes
- [ ] Verify status updates throughout
- [ ] Check progress increments smoothly
- [ ] Verify completion and export

### 3. Script Reliability
- [ ] Run each wrapper script 10 times
- [ ] Verify consistent behavior
- [ ] Check for intermittent failures
- [ ] Note any connection issues

---

## Verification Checklist (After Each Action)

- [ ] Check script exit code (0 = success)
- [ ] Read script output for errors
- [ ] Cross-check with Nessus Web UI
- [ ] Verify state changed as expected
- [ ] Check no leftover test data
- [ ] Verify no connection leaks

---

## Environment-Specific Notes

### From Host
- **Nessus URL**: `https://localhost:8834`
- **Port forwarding**: vpn-gateway → host

### From Containers
- **Nessus URL**: `https://172.18.0.2:8834` or `https://vpn-gateway:8834`
- **Direct network access**: nessus_net

### Current Setup
- **Nessus endpoint**: `https://172.32.0.209:8834` (VPN IP)
- **Set via**: `export NESSUS_URL=https://172.32.0.209:8834`

---

## Test Execution Log Template

```
Date: ____________________
Tester: __________________
Environment: Host / Container
Nessus Version: __________

Test Suite 1: Basic Workflow
[✓] 1.1 List Scans - Notes: ________________________________
[✓] 1.2 Check Status - Notes: ______________________________
[✗] 1.3 Create Scan - Error: _______________________________
...

Issues Found:
1. _________________________________________________________
2. _________________________________________________________

Recommendations:
1. _________________________________________________________
2. _________________________________________________________
```

---

**Last Updated**: 2025-11-07
**Aligned with**: nessusAPIWrapper/ functionality
**Related Docs**:
- `HTTPX_READERROR_INVESTIGATION.md` - Known HTTP 412 issue
- `DOCKER_NETWORK_CONFIG.md` - Network topology
- `nessusAPIWrapper/README.md` - Wrapper script documentation
