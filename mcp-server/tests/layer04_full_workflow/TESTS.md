# Layer 04: Full Workflow Tests

[← Test Suite](../README.MD) | [Layer README](README.MD)

---

## Overview

End-to-end tests that run complete scan workflows with real Nessus scanners.

- **Test Count**: 42 tests
- **Duration**: 5-10 minutes
- **Marker**: `@pytest.mark.layer04`, `@pytest.mark.slow`, `@pytest.mark.e2e`

---

## test_authenticated_scan_workflow.py (9 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_create_scan_with_ssh_credentials` | SSH creds for randy@172.32.0.215 | `scan_id > 0` | Create auth scan. Pass: valid scan_id created. |
| `test_create_scan_with_sudo_credentials` | Sudo creds for testauth_sudo_pass | `scan_id > 0` | Create sudo scan. Pass: valid scan_id. |
| `test_authenticated_scan_randy` | Full scan of 172.32.0.215 with randy creds | Completed, results exported | Full auth scan. Pass: completed, results > 1000 bytes. |
| `test_mcp_tool_validation_only` | Invalid scan_type, missing escalation | Error responses | MCP validation. Pass: correct errors returned. |
| `test_bad_credentials_detected` | Invalid SSH creds | No Plugin 141118 | Bad creds detected. Pass: no valid creds plugin. |
| `test_privileged_scan_sudo_with_password` | testauth_sudo_pass@172.30.0.9 | Completed with auth success | Sudo with password. Pass: completed, results valid. |
| `test_privileged_scan_sudo_nopasswd` | testauth_sudo_nopass@172.30.0.9 | Completed with auth success | Sudo NOPASSWD. Pass: completed, results valid. |
| `test_verify_scan_target_reachable` | Check 172.30.0.9:22 | Reachable or skip | Target reachable. Pass: port open. |
| `test_verify_external_host_reachable` | Check 172.32.0.215:22 | Reachable or warning | External reachable. Pass: port open or warning logged. |

---

## test_complete_scan_with_results.py (1 test)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_complete_scan_workflow_with_export` | Create→Launch→Poll→Export→Verify for 172.32.0.215 | Complete results with vulnerabilities | Full workflow. Pass: valid XML, vuln_count > 0, severity counts logged. |

---

## test_mcp_protocol_e2e.py (18 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_mcp_connection_and_initialization` | MCP_URL | Session with capabilities | Connection. Pass: session not None, has tools capability. |
| `test_mcp_list_tools` | - | Required tools present | List tools. Pass: run_untrusted_scan, get_scan_status, etc. present. |
| `test_mcp_list_tasks_e2e` | `limit=5` | `{"tasks": [...], "total": int}` | List tasks E2E. Pass: has tasks and total. |
| `test_mcp_get_scan_status_e2e` | Non-existent task_id | Error response | Status E2E. Pass: error for missing task. |
| `test_mcp_list_scanners_e2e` | - | `{"scanners": [...], "total": int}` | List scanners E2E. Pass: has scanners. |
| `test_mcp_get_queue_status_e2e` | - | Has queue_depth | Queue status E2E. Pass: has depth info. |
| `test_mcp_invalid_scan_type_error` | `scan_type="invalid_type_xyz"` | Error with scan_type mention | Invalid type error. Pass: error mentions scan_type. |
| `test_mcp_missing_required_params` | Missing targets | Error or exception | Missing params. Pass: error response or exception. |
| `test_mcp_run_untrusted_scan_e2e` | Submit→Poll→Complete | Final status in [completed, failed] | Full untrusted E2E. Pass: terminal state reached. |
| `test_mcp_run_authenticated_scan_e2e` | Submit auth scan→Poll→Complete | Final status with auth info | Full auth E2E. Pass: completed with validation. |
| `test_queue_position_in_response` | Submit scan | `queue_position: int` | Queue position. Pass: position in response. |
| `test_queue_position_multiple_submits` | 3 rapid submissions | Non-decreasing positions | Multiple positions. Pass: positions non-decreasing. |
| `test_unreachable_target_handling` | 10.255.255.1 (unreachable) | Queued successfully | Unreachable handling. Pass: queued, valid status. |
| `test_invalid_target_format_handling` | Empty targets | Error or accepted | Invalid format. Pass: handled gracefully. |
| `test_task_status_shows_error_details` | Failed tasks | Error details in status | Error details. Pass: has error info for failed. |
| `test_scan_with_timeout_target` | Unreachable target, wait | Eventually completes/fails | Timeout handling. Pass: reaches terminal state. |
| `test_estimated_wait_increases_with_queue_depth` | 5 rapid submissions | Wait times increase by ~15min each | Wait estimation. Pass: each adds 15min. |
| `test_queue_status_reflects_submissions` | Submit then check status | Depth >= 0 | Status reflects. Pass: valid depth. |

---

## test_queue_position_accuracy.py (12 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_queue_position_in_submission_response` | Submit scan | `queue_position: int >= 0` | Position in response. Pass: has valid position. |
| `test_queue_position_increments` | 3 submissions | Non-negative positions | Positions increment. Pass: all >= 0. |
| `test_queue_status_reflects_submissions` | Submit then check | `queue_depth >= 0` | Status reflects. Pass: valid depth. |
| `test_queue_status_has_depth` | - | `queue_depth: int >= 0` | Has depth. Pass: int >= 0. |
| `test_queue_status_has_dlq_size` | - | `dlq_size: int >= 0` | Has DLQ size. Pass: int >= 0. |
| `test_queue_status_has_next_tasks` | - | `next_tasks: list` | Has next tasks. Pass: is list. |
| `test_queue_status_has_timestamp` | - | `timestamp: not None` | Has timestamp. Pass: not None. |
| `test_queue_depth_matches_pool_capacity_awareness` | Queue and pool status | Both >= 0 | Coherent values. Pass: both non-negative. |
| `test_active_scans_vs_queue_depth` | Pool and queue status | Both >= 0 | Both non-negative. Pass: valid values. |
| `test_queue_position_decreases_as_scans_complete` | Submit and monitor | Status valid | Position tracking. Pass: status in valid states. |
| `test_multiple_scan_queue_ordering` | 2 submissions | Both in list_tasks or completed | Ordering. Pass: all tasks trackable. |
| `test_queue_provides_reasonable_estimates` | Queue and pool status | All values reasonable | Reasonable estimates. Pass: valid for estimation. |

---

## test_untrusted_scan_workflow.py (2 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_complete_e2e_workflow_untrusted_scan` | Full workflow: connect→submit→poll→results | Completed with vulnerabilities | Full E2E. Pass: all steps succeed, vulns found. |
| `test_e2e_with_result_filtering` | Full workflow + severity filter + CVSS filter + custom fields | Filtered results | Filter E2E. Pass: filters work, correct results. |

---

## See Also

- [Layer 03: External Basic Tests](../layer03_external_basic/TESTS.md)
- [Testing Guide](../../docs/TESTING.md)
