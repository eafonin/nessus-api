# Layer 02: Internal Tests

[← Test Suite](../README.MD) | [Layer README](README.MD)

---

## Overview

Unit tests for internal components using mocks. No external dependencies required.

- **Test Count**: 343 tests
- **Duration**: ~30 seconds
- **Marker**: `@pytest.mark.layer02`

---

## test_admin_cli.py (21 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_format_timestamp_valid` | `ts="2024-01-15T10:30:45"` | `"2024-01-15 10:30:45"` | Formats valid ISO timestamp. Pass: contains date and time. |
| `test_format_timestamp_invalid` | `ts="not a date"` | `"not a date"` | Returns invalid timestamp unchanged. Pass: returns input. |
| `test_format_timestamp_none` | `ts=None` | `"N/A"` | Handles None timestamp. Pass: returns "N/A". |
| `test_truncate_short_string` | `s="hello"`, `max_len=10` | `"hello"` | Short string unchanged. Pass: returns input. |
| `test_truncate_long_string` | `s="hello world..."`, `max_len=10` | `"hello w..."` | Long string truncated with "...". Pass: len=10, ends with "...". |
| `test_truncate_empty` | `s=""`, `max_len=10` | `""` | Empty string unchanged. Pass: returns "". |
| `test_get_dlq_task_found` | `task_id="task123"`, mock Redis with task | `{"task_id": "task123", "error": "test error"}` | Finds task in DLQ. Pass: returns task dict. |
| `test_get_dlq_task_not_found` | `task_id="task123"`, mock Redis with different task | `None` | Task not in DLQ. Pass: returns None. |
| `test_get_dlq_task_empty_dlq` | `task_id="task123"`, empty mock | `None` | Empty DLQ. Pass: returns None. |
| `test_retry_dlq_task_success` | `task_id="task123"`, task in DLQ | `True` | Successfully retries DLQ task. Pass: returns True, zrem and lpush called. |
| `test_retry_dlq_task_not_found` | `task_id="nonexistent"`, empty DLQ | `False` | Retry non-existent task. Pass: returns False, lpush not called. |
| `test_clear_dlq_all` | `pool="nessus"` | `5` (deleted count) | Clears entire DLQ. Pass: returns delete count, deletes correct key. |
| `test_clear_dlq_before_timestamp` | `before_timestamp=1234567890.0` | `3` (removed count) | Clears DLQ entries before timestamp. Pass: returns count, zremrangebyscore called. |
| `test_cmd_stats` | `pool="nessus"`, mock stats | `0` (exit code) | Stats command succeeds. Pass: returns 0, get_queue_stats called. |
| `test_cmd_list_dlq_empty` | `pool="nessus"`, empty DLQ | `0` | List-dlq with empty DLQ. Pass: returns 0. |
| `test_cmd_list_dlq_with_tasks` | `pool="nessus"`, 2 tasks in DLQ | `0` | List-dlq with tasks. Pass: returns 0. |
| `test_cmd_inspect_dlq_found` | `task_id="task123"`, task exists | `0` | Inspect found task. Pass: returns 0, get_dlq_task called with correct args. |
| `test_cmd_inspect_dlq_not_found` | `task_id="nonexistent"` | `1` | Inspect non-existent task. Pass: returns 1 (error). |
| `test_cmd_retry_dlq_success` | `task_id="task123"`, `yes=True` | `0` | Retry succeeds. Pass: returns 0, retry_dlq_task called. |
| `test_cmd_retry_dlq_not_found` | `task_id="nonexistent"`, `yes=True` | `1` | Retry non-existent. Pass: returns 1. |
| `test_cmd_purge_dlq_without_confirm` | `confirm=False` | `1` | Purge without --confirm. Pass: returns 1, clear_dlq not called. |

---

## test_authenticated_scans.py (18 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_missing_username_raises` | `{"type": "ssh", "password": "pass"}` | `ValueError("missing required field: username")` | Missing username validation. Pass: raises ValueError with message. |
| `test_missing_password_raises` | `{"type": "ssh", "username": "user"}` | `ValueError("missing required field: password")` | Missing password validation. Pass: raises ValueError. |
| `test_invalid_escalation_method_raises` | `elevate_privileges_with="invalid_method"` | `ValueError("Invalid escalation method")` | Invalid escalation method. Pass: raises ValueError. |
| `test_valid_ssh_credentials_pass` | `{"type": "ssh", "username": "testuser", "password": "testpass"}` | No exception | Valid SSH credentials. Pass: no exception raised. |
| `test_valid_sudo_credentials_pass` | SSH creds + `elevate_privileges_with="sudo"`, `escalation_password` | No exception | Valid sudo creds. Pass: no exception. |
| `test_all_valid_escalation_methods` | 9 valid methods | No exception | All valid methods pass. Pass: none raise. |
| `test_unsupported_credential_type_raises` | `{"type": "windows", ...}` | `ValueError("Unsupported credential type")` | Unsupported type. Pass: raises ValueError. |
| `test_empty_credentials_pass` | `None` or `{}` | No exception | Empty/None credentials (untrusted scan). Pass: no exception. |
| `test_basic_ssh_password_credentials` | SSH password creds | `{"add": {"Host": {"SSH": [{...}]}}}` | Builds basic SSH payload. Pass: correct structure. |
| `test_ssh_sudo_with_password` | SSH + sudo + escalation_password | Payload with `elevate_privileges_with="sudo"` | Builds sudo payload. Pass: has sudo and escalation_password. |
| `test_ssh_sudo_with_escalation_account` | SSH + sudo + escalation_account | Payload with `escalation_account` | Builds payload with custom escalation account. Pass: has escalation_account. |
| `test_ssh_sudo_nopasswd` | SSH + sudo, no escalation_password | Payload without escalation_password | NOPASSWD sudo. Pass: elevate=sudo but no escalation_password. |
| `test_payload_structure_complete` | Basic SSH creds | Complete Nessus API payload structure | Full payload structure. Pass: exact match with add/edit/delete keys. |
| `test_su_escalation` | SSH + `elevate_privileges_with="su"` | Payload with su escalation | Su escalation method. Pass: elevate=su with escalation_password. |
| `test_scan_request_with_credentials` | ScanRequest with credentials dict | `request.credentials == credentials` | ScanRequest accepts credentials. Pass: credentials stored correctly. |
| `test_scan_request_without_credentials` | ScanRequest without credentials | `request.credentials is None` | ScanRequest without creds (untrusted). Pass: credentials is None. |
| `test_create_scan_includes_credentials_in_payload` | ScanRequest with creds, mocked HTTP | `scan_id: 123`, payload contains credentials | Create scan includes creds. Pass: credentials in API payload. |
| `test_create_scan_without_credentials` | ScanRequest without creds, mocked HTTP | `scan_id: 456`, no credentials in payload | Create scan without creds. Pass: no credentials key in payload. |

---

## test_circuit_breaker.py (27 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_initial_state_closed` | `name="test"` | `state == CircuitState.CLOSED` | Circuit starts closed. Pass: state is CLOSED. |
| `test_allow_request_when_closed` | Closed circuit | `True` | Requests allowed when closed. Pass: allow_request() returns True. |
| `test_record_success_keeps_closed` | Closed circuit + success | `state == CLOSED` | Success keeps closed. Pass: state remains CLOSED. |
| `test_single_failure_stays_closed` | `failure_threshold=3`, 1 failure | `state == CLOSED`, `_failure_count == 1` | Single failure doesn't open. Pass: closed with count=1. |
| `test_opens_after_threshold` | `failure_threshold=3`, 3 failures | `state == OPEN` | Opens after threshold. Pass: state becomes OPEN on 3rd failure. |
| `test_blocks_requests_when_open` | Open circuit | `allow_request() == False` | Blocks requests when open. Pass: returns False. |
| `test_reset_closes_circuit` | Open circuit + reset() | `state == CLOSED`, `_failure_count == 0` | Manual reset closes. Pass: state CLOSED, count reset. |
| `test_transitions_to_half_open` | `recovery_timeout=0.1`, wait 0.15s | `state == HALF_OPEN` | Transitions to half-open after timeout. Pass: state is HALF_OPEN. |
| `test_half_open_allows_limited_requests` | `half_open_max_requests=2` | 2 True, then False | Half-open allows limited requests. Pass: 2 allowed, 3rd blocked. |
| `test_success_in_half_open_closes` | Half-open + success | `state == CLOSED` | Success in half-open closes. Pass: state becomes CLOSED. |
| `test_failure_in_half_open_reopens` | Half-open + failure | `state == OPEN` | Failure in half-open reopens. Pass: state becomes OPEN. |
| `test_get_status_closed` | Closed circuit | `{"name": "test", "state": "closed", "failure_count": 0}` | Status when closed. Pass: correct status dict. |
| `test_get_status_open` | Open circuit | `{"state": "open", "time_until_recovery": >0}` | Status when open. Pass: includes time_until_recovery. |
| `test_success_resets_failure_count` | 2 failures + 1 success | `_failure_count == 0` | Success resets failure count. Pass: count reset to 0. |
| `test_get_creates_breaker` | `registry.get("scanner1")` | CircuitBreaker with name="scanner1" | Registry creates breakers. Pass: returns breaker with correct name. |
| `test_get_returns_same_breaker` | `registry.get("scanner1")` twice | Same object | Registry returns same breaker. Pass: cb1 is cb2. |
| `test_get_different_breakers` | `get("scanner1")`, `get("scanner2")` | Different objects | Registry creates different breakers. Pass: cb1 is not cb2. |
| `test_get_all_status` | Registry with 2 breakers | `{"scanner1": {...}, "scanner2": {...}}` | Get all breaker status. Pass: both scanners in status. |
| `test_reset_specific` | Open breaker + reset("scanner1") | `True`, state CLOSED | Reset specific breaker. Pass: returns True, state CLOSED. |
| `test_reset_nonexistent` | `reset("nonexistent")` | `False` | Reset non-existent. Pass: returns False. |
| `test_reset_all` | 2 open breakers + reset_all() | Both CLOSED | Reset all breakers. Pass: both states CLOSED. |
| `test_custom_defaults` | `failure_threshold=10`, `recovery_timeout=60.0` | Breaker with custom values | Custom registry defaults. Pass: breaker has custom threshold/timeout. |
| `test_error_message` | `CircuitOpenError("msg", circuit_name="scanner1")` | Error with message and circuit_name | Error includes info. Pass: str contains message, has circuit_name attr. |
| `test_state_metric_updated` | State transitions | Gauge values 0→1→2 | Prometheus metric updated. Pass: gauge shows 0, 1, 2 for states. |
| `test_failure_counter_incremented` | Record failure | Counter +1 | Failure counter incremented. Pass: counter increases by 1. |
| `test_opens_counter_incremented` | Open circuit | Opens counter +1 | Opens counter incremented. Pass: counter increases when circuit opens. |
| `test_concurrent_access` | 4 threads × 50 failures | `_failure_count == 200`, no errors | Thread safety. Pass: count=200, no exceptions. |

---

## test_error_responses.py (18 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_task_not_found_response_format` | `task_id="nonexistent_task_123"` | `{"error": "Task ... not found"}` | Task not found format. Pass: has "error" key, contains "not found" and task_id. |
| `test_scanner_not_found_response_format` | Scanner lookup failure | `{"error": "Scanner not found", "status_code": 404}` | Scanner not found format. Pass: status_code=404. |
| `test_scan_results_not_found_format` | Non-existent results | JSON string `{"error": "Scan results not found"}` | Results not found format. Pass: JSON parseable, has error key. |
| `test_idempotency_conflict_response_format` | Conflict with existing key | `{"error": "Conflict", "status_code": 409, "message": ...}` | Idempotency conflict format. Pass: status=409. |
| `test_conflict_error_exception_handling` | ConflictError exception | Exception with task_id in message | ConflictError contains info. Pass: task_id in str(exception). |
| `test_conflict_preserves_task_reference` | Conflict response | `existing_task_id` field present | Conflict preserves task ref. Pass: has existing_task_id field. |
| `test_invalid_scan_type_error` | `scan_type="invalid_scan"` | Error with invalid type and valid types | Invalid scan_type error. Pass: error contains invalid type and "untrusted". |
| `test_missing_privilege_escalation_error` | authenticated_privileged without escalation | Error mentioning sudo/su | Missing escalation error. Pass: mentions authenticated_privileged and sudo/su. |
| `test_schema_conflict_error` | Both schema_profile and custom_fields | Error about conflict | Schema conflict error. Pass: mentions both schema_profile and custom_fields. |
| `test_scan_not_completed_error` | `status="running"` | `{"error": "Scan not completed yet (status: running)"}` | Scan not completed error. Pass: contains "not completed" and status. |
| `test_all_errors_have_error_key` | Various error responses | All have "error" key | Consistent error format. Pass: all responses have "error" key. |
| `test_http_errors_have_status_code` | HTTP error responses | All have integer status_code >= 400 | HTTP errors have status. Pass: status_code is int >= 400. |
| `test_error_messages_are_human_readable` | Various error messages | Readable strings | Human-readable errors. Pass: no tracebacks, 10-500 chars. |
| `test_failed_scan_includes_error_message` | Failed scan status | Has `error_message` field | Failed scan has error. Pass: status="failed", error_message not None. |
| `test_timeout_scan_includes_error_message` | Timeout scan status | Has `error_message` field | Timeout has error. Pass: status="timeout", has error_message. |
| `test_completed_scan_no_error_message` | Completed scan status | `error_message: None` | Completed has no error. Pass: status="completed", error_message is None. |
| `test_auth_failure_includes_troubleshooting` | Auth failed response | `troubleshooting.suggestions` list | Auth failure troubleshooting. Pass: has troubleshooting with suggestions list. |
| `test_partial_auth_includes_details` | Partial auth response | `hosts_summary` dict | Partial auth details. Pass: has hosts_summary with total/authenticated/failed. |

---

## test_health.py (17 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_check_redis_success` | `redis://redis:6379` | `bool` | Redis check returns bool. Pass: isinstance(result, bool). |
| `test_check_redis_connection_success` | Mocked successful ping | `True` | Mocked Redis success. Pass: returns True, ping called. |
| `test_check_redis_connection_failure` | Mocked connection error | `False` | Mocked Redis failure. Pass: returns False. |
| `test_check_redis_ping_failure` | Mocked ping failure | `False` | Ping fails. Pass: returns False. |
| `test_check_filesystem_success_with_existing_dir` | Existing temp directory | `True` | Filesystem check with existing dir. Pass: returns True. |
| `test_check_filesystem_success_creates_dir` | Non-existent directory | `True`, directory created | Creates directory if needed. Pass: True and dir exists. |
| `test_check_filesystem_write_test` | Temp directory | `True`, no leftover file | Write test cleans up. Pass: True, .health_check file removed. |
| `test_check_filesystem_readonly_failure` | Read-only directory | `bool` | Read-only handling. Pass: returns bool (behavior depends on permissions). |
| `test_check_filesystem_nonexistent_parent` | `/root/nonexistent/parent/dir` | `bool` | Non-existent parent. Pass: returns bool. |
| `test_check_all_dependencies_all_healthy` | Both mocked True | `{"status": "healthy", "redis_healthy": True, "filesystem_healthy": True}` | All healthy. Pass: status="healthy", both True. |
| `test_check_all_dependencies_redis_unhealthy` | Redis False, FS True | `{"status": "unhealthy", "redis_healthy": False}` | Redis unhealthy. Pass: status="unhealthy". |
| `test_check_all_dependencies_filesystem_unhealthy` | Redis True, FS False | `{"status": "unhealthy", "filesystem_healthy": False}` | FS unhealthy. Pass: status="unhealthy". |
| `test_check_all_dependencies_all_unhealthy` | Both False | `{"status": "unhealthy"}` | All unhealthy. Pass: both False. |
| `test_check_all_dependencies_returns_dict` | Mocked healthy | Dict with required keys | Returns proper dict. Pass: has status, redis_healthy, filesystem_healthy, redis_url, data_dir. |
| `test_check_all_dependencies_preserves_urls` | Custom URLs | URLs in response | URLs preserved. Pass: redis_url and data_dir match inputs. |
| `test_filesystem_check_with_real_tempdir` | Real temp dir | `True` | Filesystem check with real tempdir. Pass: returns True. |
| `test_filesystem_creates_nested_directories` | Nested path in temp dir | `True`, nested dirs exist | Creates nested dirs. Pass: True, all levels exist. |

---

## test_housekeeping.py (18 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_default_initialization` | No args | `data_dir="/app/data/tasks"`, `completed_ttl=7d`, `failed_ttl=30d` | Default values. Pass: defaults set correctly. |
| `test_custom_initialization` | Custom values | Custom TTLs | Custom values. Pass: custom values applied. |
| `test_cleanup_nonexistent_directory` | `/nonexistent/path` | `{"deleted_count": 0, "errors": ["...does not exist"]}` | Non-existent dir. Pass: count=0, error message. |
| `test_cleanup_empty_directory` | Empty temp dir | `{"deleted_count": 0, "errors": []}` | Empty dir. Pass: count=0, no errors. |
| `test_cleanup_completed_task_old` | Completed task, age=10d, TTL=7d | `{"deleted_count": 1}`, task deleted | Old completed deleted. Pass: count=1, task dir removed. |
| `test_cleanup_completed_task_recent` | Completed task, age=3d, TTL=7d | `{"deleted_count": 0}`, task exists | Recent completed kept. Pass: count=0, task exists. |
| `test_cleanup_failed_task_old` | Failed task, age=35d, TTL=30d | `{"deleted_count": 1}` | Old failed deleted. Pass: count=1. |
| `test_cleanup_failed_task_recent` | Failed task, age=10d, TTL=30d | `{"deleted_count": 0}` | Recent failed kept. Pass: count=0, task exists. |
| `test_cleanup_timeout_task_old` | Timeout task, age=35d | `{"deleted_count": 1}` | Old timeout deleted. Pass: count=1. |
| `test_cleanup_skips_running_tasks` | Running task, age=100d | `{"deleted_count": 0, "skipped": 1}` | Running never deleted. Pass: skipped=1, task exists. |
| `test_cleanup_skips_queued_tasks` | Queued task, age=100d | `{"deleted_count": 0, "skipped": 1}` | Queued never deleted. Pass: skipped=1, task exists. |
| `test_cleanup_multiple_tasks` | 4 tasks: old completed, recent completed, old failed, running | `{"deleted_count": 2, "skipped": 1}` | Multiple tasks handled. Pass: correct counts. |
| `test_cleanup_tracks_freed_bytes` | Task with data, deleted | `{"freed_bytes": >0, "freed_mb": >=0}` | Tracks freed space. Pass: freed_bytes > 0. |
| `test_cleanup_handles_invalid_json` | Invalid task.json | `{"errors": ["Invalid JSON..."]}` | Invalid JSON handled. Pass: error captured, no crash. |
| `test_get_stats_empty` | Empty directory | `{"total_tasks": 0, "by_status": {}}` | Stats for empty dir. Pass: zero counts. |
| `test_get_stats_counts_by_status` | 4 tasks with different statuses | `{"total_tasks": 4, "by_status": {"completed": 2, "failed": 1, "running": 1}}` | Counts by status. Pass: correct counts. |
| `test_get_stats_tracks_expired` | Mix of expired/fresh tasks | `{"expired": {"completed": 1, "failed": 1}}` | Tracks expired. Pass: correct expired counts. |
| `test_ttl_deletions_metric_incremented` | Delete task, check metric | Counter +1 | Metric incremented. Pass: ttl_deletions_total increases. |

---

## test_idempotency.py (13 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_hash_request_consistent` | Same params twice | Same 64-char hash | Consistent hashing. Pass: hash1 == hash2, len=64. |
| `test_hash_request_key_order_independent` | Same params, different order | Same hash | Order independent. Pass: hash1 == hash2. |
| `test_hash_request_different_params` | Different params | Different hashes | Different params → different hashes. Pass: hash1 != hash2. |
| `test_hash_request_none_normalization` | `description: None` twice | Same hash | None normalized. Pass: hash1 == hash2. |
| `test_hash_request_bool_normalization` | `enabled: True` twice | Same hash | Booleans normalized. Pass: hash1 == hash2. |
| `test_store_new_key` | New idempotency key | `True` | Store new key. Pass: returns True. |
| `test_store_existing_key` | Store same key twice | `True`, then `False` | Existing key rejected. Pass: first True, second False. |
| `test_check_nonexistent_key` | Non-existent key | `None` | Check missing key. Pass: returns None. |
| `test_check_matching_key` | Stored key + same params | `task_id` | Check matching key. Pass: returns stored task_id. |
| `test_check_conflicting_params` | Stored key + different params | `ConflictError` | Conflicting params. Pass: raises ConflictError with "different request parameters". |
| `test_store_ttl_set` | Store key, check Redis TTL | TTL ~172800s (48h) | TTL set correctly. Pass: TTL between 172700-172800. |
| `test_full_workflow_with_retry` | Check→Store→Retry same→Retry different | None→True→task_id→ConflictError | Full workflow. Pass: correct sequence of responses. |
| `test_concurrent_store_operations` | 10 concurrent stores | Only 1 succeeds | Atomic SETNX. Pass: exactly 1 True in results. |

---

## test_ip_utils.py (55 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_parse_ipv4_address` | `"192.168.1.1"` | `IPv4Address` | Parse IPv4. Pass: correct address type. |
| `test_parse_ipv4_cidr` | `"10.0.0.0/8"` | `IPv4Network` | Parse CIDR. Pass: correct network. |
| `test_parse_ipv4_cidr_non_strict` | `"192.168.1.5/24"` | `"192.168.1.0/24"` | Non-strict CIDR. Pass: normalized to network address. |
| `test_parse_ipv6_address` | `"::1"` | `IPv6Address` | Parse IPv6. Pass: correct type. |
| `test_parse_ipv6_cidr` | `"2001:db8::/32"` | `IPv6Network` | Parse IPv6 CIDR. Pass: correct network. |
| `test_parse_hostname_returns_none` | `"scan-target.local"` | `None` | Hostname returns None. Pass: None for hostnames. |
| `test_parse_invalid_returns_none` | `"999.999.999.999"` | `None` | Invalid IP returns None. Pass: None for invalid. |
| `test_parse_empty_returns_none` | `""` | `None` | Empty returns None. Pass: None. |
| `test_parse_whitespace_trimmed` | `"  192.168.1.1  "` | Correct IP | Whitespace trimmed. Pass: correct address. |
| `test_ip_equals_ip` | Two identical IPs | `True` | IP exact match. Pass: True. |
| `test_ip_not_equals_ip` | Two different IPs | `False` | IP non-match. Pass: False. |
| `test_ip_in_network` | IP within network | `True` | IP in network. Pass: True. |
| `test_ip_not_in_network` | IP outside network | `False` | IP not in network. Pass: False. |
| `test_network_contains_ip` | Network contains IP (reversed) | `True` | Network contains IP. Pass: True. |
| `test_networks_overlap` | Overlapping networks | `True` | Networks overlap. Pass: True. |
| `test_networks_no_overlap` | Non-overlapping networks | `False` | No overlap. Pass: False. |
| `test_ip_exact_match` | `targets_match("192.168.1.1", "192.168.1.1")` | `True` | Exact IP match. Pass: True. |
| `test_ip_no_match` | Different IPs | `False` | IP no match. Pass: False. |
| `test_ip_in_cidr_hit` | IP within stored CIDR | `True` | IP in CIDR hit. Pass: True. |
| `test_ip_in_large_cidr_hit` | IP in /8 network | `True` | Large CIDR hit. Pass: True. |
| `test_ip_at_network_boundary_hit` | Network address | `True` | Boundary hit. Pass: True. |
| `test_ip_at_broadcast_boundary_hit` | Broadcast address | `True` | Broadcast hit. Pass: True. |
| `test_ip_not_in_cidr_miss` | IP outside CIDR | `False` | CIDR miss. Pass: False. |
| `test_ip_adjacent_cidr_miss` | Adjacent but outside | `False` | Adjacent miss. Pass: False. |
| `test_cidr_contains_ip_hit` | Query CIDR contains stored IP | `True` | CIDR contains IP. Pass: True. |
| `test_cidr_overlap_subset_hit` | Query is subset | `True` | Subset hit. Pass: True. |
| `test_cidr_overlap_superset_hit` | Query is superset | `True` | Superset hit. Pass: True. |
| `test_cidr_exact_match_hit` | Same CIDR | `True` | Exact CIDR match. Pass: True. |
| `test_cidr_no_overlap_miss` | Non-overlapping CIDRs | `False` | No overlap miss. Pass: False. |
| `test_multiple_targets_match_first_hit` | Query matches first of list | `True` | Multiple targets first. Pass: True. |
| `test_multiple_targets_match_second_hit` | Query matches second of list | `True` | Multiple targets second. Pass: True. |
| `test_multiple_targets_match_cidr_in_list_hit` | Query IP matches CIDR in list | `True` | IP matches CIDR in list. Pass: True. |
| `test_multiple_targets_cidr_query_hit` | Query CIDR contains stored IP | `True` | CIDR query contains stored IP. Pass: True. |
| `test_multiple_targets_no_match_miss` | Query matches none | `False` | Multiple targets miss. Pass: False. |
| `test_multiple_targets_cidr_no_overlap_miss` | Query CIDR doesn't overlap stored | `False` | CIDR no overlap. Pass: False. |
| `test_hostname_exact_match_hit` | Same hostname | `True` | Hostname match. Pass: True. |
| `test_hostname_case_insensitive_hit` | Different case | `True` | Case insensitive. Pass: True. |
| `test_hostname_in_list_hit` | Hostname in target list | `True` | Hostname in list. Pass: True. |
| `test_hostname_no_match_miss` | Different hostname | `False` | Hostname miss. Pass: False. |
| `test_hostname_vs_ip_miss` | Hostname vs IP | `False` | Hostname vs IP miss. Pass: False. |
| `test_ip_vs_hostname_miss` | IP query vs hostname target | `False` | IP vs hostname miss. Pass: False. |
| `test_empty_query_miss` | Empty query | `False` | Empty query miss. Pass: False. |
| `test_empty_stored_targets_miss` | Empty stored targets | `False` | Empty stored miss. Pass: False. |
| `test_both_empty_miss` | Both query and stored empty | `False` | Both empty miss. Pass: False. |
| `test_empty_entries_in_list` | Empty entries in comma list | `True` | Empty entries skipped. Pass: True. |
| `test_whitespace_handling` | Whitespace in list | `True` | Whitespace handled. Pass: True. |
| `test_ip_different_network_miss` | IP in different network | `False` | Different network miss. Pass: False. |
| `test_large_cidr_contains_ip_hit` | /8 network contains IP | `True` | Large CIDR contains IP. Pass: True. |
| `test_cidr_not_contains_ip_miss` | CIDR doesn't contain IP | `False` | CIDR not contains IP. Pass: False. |
| `test_cidr_partial_overlap_hit` | Partially overlapping CIDRs | `True` | Partial overlap hit. Pass: True. |
| `test_cidr_adjacent_no_overlap_miss` | Adjacent non-overlapping CIDRs | `False` | Adjacent no overlap. Pass: False. |
| `test_scenario_scan_target_172_30_0_9` | Real scenario matching | Correct matches | Real scenario. Pass: correct match/miss. |
| `test_scenario_large_network_scan` | /8 network search | Hosts within match | Large network. Pass: internal IPs match, external miss. |
| `test_scenario_multiple_network_scan` | Multiple networks | Correct matches per network | Multiple networks. Pass: each network matches correctly. |
| `test_scenario_subnet_search_for_specific_scans` | Subnet search for scans | Correct overlap detection | Subnet search. Pass: /16 matches /24, IP, /8. |

---

## test_list_tasks.py (14 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_filter_by_status_completed` | `status="completed"` | 1 task with status "completed" | Filter by completed. Pass: only completed tasks returned. |
| `test_filter_by_status_running` | `status="running"` | 1 task with status "running" | Filter by running. Pass: only running tasks. |
| `test_filter_by_status_queued` | `status="queued"` | 1 task with status "queued" | Filter by queued. Pass: only queued tasks. |
| `test_filter_by_pool_nessus` | `pool="nessus"` | 3 tasks in nessus pool | Filter by nessus pool. Pass: correct task IDs. |
| `test_filter_by_pool_dmz` | `pool="nessus_dmz"` | 1 task in dmz pool | Filter by dmz pool. Pass: only dmz tasks. |
| `test_combined_filter_status_and_pool` | `status="completed"`, `pool="nessus"` | 1 task matching both | Combined filter. Pass: only matching task. |
| `test_limit_respects_count` | `limit=2` | ≤2 tasks | Limit respected. Pass: len ≤ limit. |
| `test_no_results_returns_empty` | `status="timeout"` (none exist) | Empty list | No results. Pass: empty list. |
| `test_target_filter_exact_ip_match` | `target_filter="10.0.0.50"` | 1 task with exact target | Exact IP filter. Pass: matching task. |
| `test_target_filter_ip_in_cidr` | `target_filter="192.168.1.100"` | 1 task with CIDR containing IP | IP in CIDR filter. Pass: matching task. |
| `test_target_filter_cidr_contains_stored_ip` | `target_filter="10.0.0.0/24"` | 1 task with IP in that CIDR | CIDR contains IP filter. Pass: matching task. |
| `test_target_filter_no_match` | `target_filter="8.8.8.8"` | Empty list | No match filter. Pass: empty list. |
| `test_response_contains_required_fields` | Any task | Dict with all required fields | Required fields present. Pass: has task_id, trace_id, status, etc. |
| `test_response_values_match_task` | Specific task | Values match task attributes | Values match. Pass: all values equal task attrs. |

---

## test_logging_config.py (9 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_configure_logging_sets_log_level` | `log_level="DEBUG"` | No exception | Sets log level. Pass: no exception. |
| `test_configure_logging_default_level` | No args | No exception | Default level (INFO). Pass: no exception. |
| `test_get_logger_returns_structured_logger` | `get_logger("test_module")` | Logger with info/error/debug methods | Returns structured logger. Pass: has logging methods. |
| `test_get_logger_without_name` | `get_logger()` | Logger with methods | Logger without name. Pass: has methods. |
| `test_json_output_format` | Log message | JSON with event, key1, key2, timestamp | JSON format. Pass: valid JSON with all keys. |
| `test_timestamp_format` | Log message | ISO 8601 timestamp | ISO timestamp. Pass: contains "T" or "-". |
| `test_log_levels` | debug/info/warning/error | 4+ log records | All levels work. Pass: ≥4 records captured. |
| `test_structured_data_logging` | Structured data dict | JSON with all keys preserved | Structured data. Pass: all keys in JSON. |
| `test_exception_logging` | Exception with exc_info=True | Log record captured | Exception logging. Pass: record captured. |

---

## test_metrics.py (45 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_scans_total_counter_exists` | - | Counter with name, labels | Counter exists. Pass: has scan_type, status labels. |
| `test_api_requests_total_counter_exists` | - | Counter with tool, status labels | API counter exists. Pass: has required labels. |
| `test_ttl_deletions_total_counter_exists` | - | Counter exists | TTL counter exists. Pass: has correct name. |
| `test_active_scans_gauge_exists` | - | Gauge exists | Active scans gauge. Pass: correct name. |
| `test_scanner_instances_gauge_exists` | - | Gauge with scanner_type, enabled labels | Scanner gauge. Pass: has labels. |
| `test_queue_depth_gauge_exists` | - | Gauge with queue label | Queue depth gauge. Pass: has queue label. |
| `test_dlq_size_gauge_exists` | - | Gauge exists | DLQ gauge exists. Pass: correct name. |
| `test_task_duration_histogram_exists` | - | Histogram exists | Duration histogram. Pass: correct name. |
| `test_record_tool_call_increments_counter` | `tool="test_tool"`, `status="success"` | Counter +1 | Tool call increments. Pass: counter increases. |
| `test_record_tool_call_default_status` | `tool="default_test"` | Counter +1 for status="success" | Default status. Pass: uses "success". |
| `test_record_scan_submission_increments_counter` | `scan_type="untrusted"`, `status="queued"` | Counter +1 | Submission increments. Pass: counter increases. |
| `test_record_scan_completion_increments_counter` | `scan_type="untrusted"`, `status="completed"` | Counter +1 | Completion increments. Pass: counter increases. |
| `test_update_active_scans_count_sets_gauge` | `count=5` then `count=0` | Gauge = 5 then 0 | Active scans updated. Pass: gauge matches. |
| `test_update_queue_metrics_sets_gauges` | `main_depth=10`, `dlq_depth=2` | Gauges set correctly | Queue metrics updated. Pass: all gauges correct. |
| `test_update_scanner_instances_metric_sets_gauge` | `nessus`, enabled=3, disabled=1 | Gauge values set | Scanner instances updated. Pass: both labels set. |
| `test_metrics_response_returns_bytes` | - | `bytes` | Response is bytes. Pass: isinstance bytes. |
| `test_metrics_response_contains_prometheus_format` | - | Contains "# HELP" or "# TYPE" | Prometheus format. Pass: has format markers. |
| `test_metrics_response_contains_all_metrics` | - | Contains all metric names | All metrics present. Pass: all names in response. |
| `test_metrics_response_valid_prometheus_format` | - | HELP, TYPE, metric lines | Valid format. Pass: has all line types. |
| `test_histogram_buckets_defined` | - | Buckets [60, 300, 600, 1800, 3600, 7200, 14400] | Correct buckets. Pass: exact match. |
| `test_scans_total_with_different_labels` | Different scan_types | Separate counters | Label isolation. Pass: each type tracked separately. |
| `test_api_requests_with_different_tools` | Different tools | Separate counters | Tool isolation. Pass: each tool tracked separately. |
| `test_scanner_instances_with_different_types` | nessus and openvas | Separate gauges | Type isolation. Pass: each type tracked. |
| `test_pool_queue_depth_gauge_exists` | - | Gauge with pool label | Pool queue gauge. Pass: has pool label. |
| `test_pool_dlq_depth_gauge_exists` | - | Gauge with pool label | Pool DLQ gauge. Pass: has pool label. |
| `test_update_pool_queue_depth_sets_gauge` | Pool depths | Correct values | Pool depth updated. Pass: values match. |
| `test_update_pool_dlq_depth_sets_gauge` | Pool DLQ depths | Correct values | Pool DLQ updated. Pass: values match. |
| `test_update_all_pool_queue_metrics` | List of pool stats | All pools updated | All pools updated. Pass: all values correct. |
| `test_validation_total_counter_exists` | - | Counter with pool, result labels | Validation counter. Pass: has labels. |
| `test_validation_failures_counter_exists` | - | Counter with pool, reason labels | Validation failures. Pass: has labels. |
| `test_auth_failures_counter_exists` | - | Counter with pool, scan_type labels | Auth failures. Pass: has labels. |
| `test_record_validation_result_success` | `is_valid=True` | success counter +1 | Validation success. Pass: counter increases. |
| `test_record_validation_result_failure` | `is_valid=False` | failed counter +1 | Validation failure. Pass: counter increases. |
| `test_record_validation_failure_reason` | `reason="auth_failed"` | Reason counter +1 | Failure reason. Pass: correct label incremented. |
| `test_record_validation_failure_different_reasons` | 5 different reasons | Each reason tracked | Multiple reasons. Pass: all reasons tracked. |
| `test_record_auth_failure` | `scan_type="trusted_basic"` | Counter +1 | Auth failure. Pass: counter increases. |
| `test_record_auth_failure_different_scan_types` | Different scan types | Each type tracked | Scan type isolation. Pass: each tracked. |
| `test_scanner_active_scans_gauge_exists` | - | Gauge with scanner_instance label | Scanner active. Pass: has label. |
| `test_scanner_capacity_gauge_exists` | - | Gauge with scanner_instance label | Scanner capacity. Pass: has label. |
| `test_scanner_utilization_gauge_exists` | - | Gauge with scanner_instance label | Utilization gauge. Pass: has label. |
| `test_update_scanner_metrics` | active=3, capacity=10 | All gauges set, utilization=30% | Scanner metrics. Pass: correct values. |
| `test_update_scanner_metrics_full_capacity` | active=5, capacity=5 | utilization=100% | Full capacity. Pass: 100%. |
| `test_update_scanner_metrics_zero_capacity` | active=0, capacity=0 | utilization=0% | Zero capacity. Pass: 0% (no divide by zero). |
| `test_update_all_scanner_metrics` | List of scanner stats | All scanners updated | All scanners. Pass: all values correct. |
| `test_metrics_response_contains_phase4_metrics` | - | Contains Phase 4 metric names | Phase 4 metrics. Pass: all new metrics present. |

---

## test_nessus_validator.py (18 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_file_not_found` | Non-existent file | `is_valid=False`, error="not found" | File not found. Pass: invalid with error. |
| `test_empty_file` | Empty file | `is_valid=False`, error="too small" | Empty file. Pass: invalid, file_size_bytes=0. |
| `test_invalid_xml` | Invalid XML content | `is_valid=False`, error="Invalid XML" | Invalid XML. Pass: invalid with XML error. |
| `test_no_hosts` | XML with no hosts | `is_valid=False`, error="No hosts" | No hosts. Pass: invalid with no hosts error. |
| `test_untrusted_scan_success` | Valid untrusted scan XML | `is_valid=True`, auth_status="not_applicable" | Untrusted success. Pass: valid, not_applicable auth. |
| `test_untrusted_scan_severity_counts` | Untrusted scan XML | `severity_counts: {critical: 0, high: 0, medium: 1, low: 1, info: 2}` | Severity counts. Pass: correct counts. |
| `test_trusted_scan_auth_success` | Trusted scan with "Credentialed checks : yes" | `is_valid=True`, auth_status="success" | Trusted auth success. Pass: valid, auth=success. |
| `test_trusted_scan_auth_failed` | Trusted scan with "Credentialed checks : no" | `is_valid=False`, auth_status="failed" | Trusted auth failed. Pass: invalid, auth=failed. |
| `test_trusted_scan_auth_partial` | Trusted scan with "Credentialed checks : partial" | `is_valid=True`, auth_status="partial" | Partial auth. Pass: valid with warning, auth=partial. |
| `test_trusted_privileged_scan_failed` | Privileged scan with failed auth | `is_valid=False`, auth_status="failed" | Privileged auth failed. Pass: invalid, error mentions trusted_privileged. |
| `test_severity_counts_trusted` | Trusted scan with vulns | Correct severity counts | Trusted severity. Pass: correct counts by severity. |
| `test_host_count` | Multi-host XML | `hosts_scanned: 3` | Host count. Pass: correct count. |
| `test_expected_hosts_warning` | 3 hosts, expected 5 | `is_valid=True`, warning="less than expected" | Expected hosts warning. Pass: valid with warning. |
| `test_expected_hosts_met` | 3 hosts, expected 3 | `is_valid=True`, no warnings | Expected hosts met. Pass: no warnings. |
| `test_auth_inferred_from_plugins` | No plugin 19506, but 5+ auth plugins | `is_valid=True`, auth_status="success" | Auth inferred. Pass: auth=success from plugin count. |
| `test_convenience_function` | `validate_scan_results(file, scan_type)` | `ValidationResult` | Convenience function. Pass: returns ValidationResult. |
| `test_default_values` | `ValidationResult(is_valid=True)` | Defaults: error=None, warnings=[], stats={}, auth="unknown" | Default values. Pass: all defaults correct. |
| `test_with_values` | ValidationResult with all fields | All fields set | With values. Pass: all fields match inputs. |

---

## test_pool_registry.py (20 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_list_pools` | Registry with 2 pools | `["nessus", "nessus_dmz"]` | List pools. Pass: both pools listed. |
| `test_get_default_pool` | Registry | `"nessus"` | Default pool. Pass: returns "nessus". |
| `test_get_scanner_count_all` | Registry with 3 scanners | `3` | Total count. Pass: 3 scanners. |
| `test_get_scanner_count_by_pool` | By pool | nessus=2, dmz=1 | Count by pool. Pass: correct per-pool counts. |
| `test_list_instances_all` | Registry | 3 instances with pool info | All instances. Pass: 3 instances, pools included. |
| `test_list_instances_by_pool` | By pool | Pool-specific instances | By pool. Pass: only that pool's scanners. |
| `test_get_instance_by_pool` | `pool="nessus"`, `instance_id="scanner1"` | Scanner instance | Get specific. Pass: returns scanner. |
| `test_get_instance_not_found` | Non-existent instance | `ValueError("Scanner not found")` | Not found. Pass: raises ValueError. |
| `test_get_available_scanner_from_pool` | `pool="nessus"` | Scanner + key starting with "nessus:" | Available scanner. Pass: returns scanner with correct key. |
| `test_get_available_scanner_from_empty_pool` | Non-existent pool | `ValueError("No enabled scanners")` | Empty pool. Pass: raises ValueError. |
| `test_get_pool_status` | `pool="nessus"` | Status dict with capacity info | Pool status. Pass: has pool, total_scanners, total_capacity, utilization. |
| `test_get_pool_status_dmz` | `pool="nessus_dmz"` | DMZ pool status | DMZ status. Pass: correct values for DMZ. |
| `test_least_loaded_selection` | Scanner1 load=3, Scanner2 load=1 | Scanner2 selected | Least loaded. Pass: selects scanner2. |
| `test_acquire_increments_active_scans` | Acquire scanner | active_scans +1 | Acquire increments. Pass: count increases. |
| `test_release_decrements_active_scans` | Release scanner | active_scans -1 | Release decrements. Pass: count decreases. |
| `test_acquire_specific_instance` | Specific instance_id | That scanner returned | Specific acquire. Pass: returns requested scanner. |
| `test_get_scanner_load` | Scanner with load | Load info dict | Get load. Pass: has active_scans, max, utilization_pct, available_capacity. |
| `test_pools_are_isolated` | Multiple pools | Each pool has own scanners | Pool isolation. Pass: no key overlap. |
| `test_pool_status_independent` | Load on one pool | Only that pool shows load | Status independent. Pass: other pools unaffected. |
| `test_acquire_respects_pool` | Acquire from specific pool | Key starts with that pool | Respects pool. Pass: key prefix matches pool. |

---

## test_queue.py (18 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_queue_key_generation` | Various pools | `"nessus:queue"`, `"nessus_dmz:queue"` | Key generation. Pass: correct format. |
| `test_dlq_key_generation` | Various pools | `"nessus:queue:dead"`, etc. | DLQ key generation. Pass: correct format. |
| `test_enqueue_to_default_pool` | Task without pool | Uses "nessus:queue" | Default pool. Pass: correct key used. |
| `test_enqueue_to_specific_pool` | `pool="nessus_dmz"` | Uses "nessus_dmz:queue" | Specific pool. Pass: correct key. |
| `test_enqueue_uses_task_scanner_pool` | Task with scanner_pool="nessus_lan" | Uses "nessus_lan:queue" | Task pool used. Pass: scanner_pool respected. |
| `test_enqueue_pool_param_takes_precedence` | Task with scanner_pool, explicit pool param | Uses pool param | Param precedence. Pass: param overrides task. |
| `test_dequeue_from_default_pool` | Default pool | Dequeues from "nessus:queue" | Default dequeue. Pass: correct key. |
| `test_dequeue_from_specific_pool` | `pool="nessus_dmz"` | Dequeues from "nessus_dmz:queue" | Specific dequeue. Pass: correct key. |
| `test_dequeue_any_from_multiple_pools` | `["nessus", "nessus_dmz", "nessus_lan"]` | Task from any pool | Dequeue any. Pass: all keys in brpop call. |
| `test_dequeue_any_timeout` | No tasks | `None` | Dequeue timeout. Pass: returns None. |
| `test_get_queue_depth_for_pool` | `pool="nessus_dmz"` | Depth from that pool | Pool depth. Pass: correct key used. |
| `test_get_dlq_size_for_pool` | `pool="nuclei"` | DLQ size for pool | Pool DLQ size. Pass: correct key. |
| `test_move_to_dlq_uses_pool` | Task with scanner_pool | Uses pool-specific DLQ | Move to DLQ. Pass: correct key. |
| `test_peek_from_specific_pool` | `pool="nessus_lan"` | Tasks from that pool | Peek pool. Pass: correct key. |
| `test_clear_dlq_for_pool` | `pool="nessus_dmz"` | Clears that pool's DLQ | Clear DLQ. Pass: correct key. |
| `test_get_queue_stats_default_pool` | Default pool | Stats with pool="nessus" | Default stats. Pass: pool in stats. |
| `test_get_queue_stats_specific_pool` | `pool="nessus_dmz"` | Stats for that pool | Specific stats. Pass: pool matches. |
| `test_get_all_pool_stats` | 3 pools with different depths | Aggregated stats | All pool stats. Pass: totals correct. |

---

## test_queue_status.py (16 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_get_queue_stats_default_pool` | Mock queue | Stats with pool, depth, dlq, tasks | Default stats. Pass: all fields present. |
| `test_get_queue_stats_specific_pool` | `pool="nessus_dmz"` | Stats for that pool | Specific pool. Pass: correct pool in response. |
| `test_get_queue_stats_empty_queue` | Empty queue | `queue_depth: 0`, `next_tasks: []` | Empty queue. Pass: zeros and empty list. |
| `test_get_queue_stats_timestamp_format` | Any queue | ISO format timestamp | Timestamp format. Pass: parseable as datetime. |
| `test_nessus_pool_stats` | Mock with nessus data | Nessus-specific stats | Nessus stats. Pass: correct values. |
| `test_dmz_pool_stats` | Mock with dmz data | DMZ-specific stats | DMZ stats. Pass: correct values. |
| `test_empty_pool_stats` | Empty nuclei pool | Zero stats | Empty pool. Pass: zeros. |
| `test_response_contains_all_required_fields` | Any queue | Has pool, queue_depth, dlq_size, next_tasks, timestamp | Required fields. Pass: all present. |
| `test_response_types_are_correct` | Any queue | Correct types for each field | Correct types. Pass: str, int, list types. |
| `test_next_tasks_limited_to_three` | Queue with many tasks | peek called with count=3 | Limited preview. Pass: count=3 in call. |
| `test_queue_depth_zero` | Empty queue | `queue_depth: 0` | Zero depth. Pass: 0. |
| `test_queue_depth_positive` | Queue with 42 tasks | `queue_depth: 42` | Positive depth. Pass: 42. |
| `test_queue_depth_large_number` | Queue with 10000 tasks | `queue_depth: 10000` | Large depth. Pass: 10000. |
| `test_dlq_size_zero` | Empty DLQ | `dlq_size: 0` | Zero DLQ. Pass: 0. |
| `test_dlq_size_positive` | DLQ with 5 tasks | `dlq_size: 5` | Positive DLQ. Pass: 5. |
| `test_dlq_independent_of_queue` | Queue=10, DLQ=3 | Both values independent | Independent values. Pass: both correct. |

---

## test_task_manager.py (16 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_create_and_get_task` | Sample task | Same task retrieved | Create/get. Pass: all fields match. |
| `test_get_nonexistent_task` | Non-existent ID | `None` | Get missing. Pass: returns None. |
| `test_update_status_valid_transition` | QUEUED → RUNNING | Status updated, started_at set | Valid transition. Pass: status="running", started_at not None. |
| `test_update_status_invalid_transition` | QUEUED → COMPLETED | `StateTransitionError` | Invalid transition. Pass: raises error. |
| `test_task_with_validation_fields` | Task with validation_stats, warnings, auth_status | All fields stored | Validation fields. Pass: all fields retrievable. |
| `test_mark_completed_with_validation_success` | Running task + validation data | Status=completed, validation data stored | Completed with validation. Pass: all fields set. |
| `test_mark_completed_with_partial_auth` | Partial auth status | auth_status="partial", 2 warnings | Partial auth. Pass: auth and warnings correct. |
| `test_mark_failed_with_validation` | Failure with validation context | Status=failed, error and auth data | Failed with validation. Pass: all fields set. |
| `test_mark_completed_without_validation` | No validation data | Status=completed, validation fields None | Without validation. Pass: None for validation fields. |
| `test_backward_compatibility_no_validation_fields` | Old task without validation | Validation fields are None | Backward compat. Pass: None for new fields. |
| `test_untrusted_scan_not_applicable_auth` | Untrusted scan completed | auth_status="not_applicable" | Untrusted auth. Pass: not_applicable. |
| `test_trusted_scan_success_auth` | Trusted scan with auth success | auth_status="success", auth_plugins_found | Trusted success. Pass: correct auth status. |
| `test_trusted_scan_failed_auth` | Trusted scan with auth failure | Status=failed, auth_status="failed", error message | Trusted failure. Pass: failed with error. |
| `test_generate_task_id_format` | `scanner_type="nessus"`, `instance="scanner1"` | Format: `ne_scan_YYYYMMDD_HHMMSS_hexrandom` | ID format. Pass: 5 parts, correct prefixes. |
| `test_generate_task_id_unique` | Generate 100 IDs | All unique | Unique IDs. Pass: 100 unique values. |
| `test_generate_task_id_different_scanner_types` | nessus vs qualys | Different prefixes (ne vs qu) | Type prefixes. Pass: different first parts. |

---

## See Also

- [Layer 01: Infrastructure Tests](../layer01_infrastructure/TESTS.md)
- [Layer 03: External Basic Tests](../layer03_external_basic/TESTS.md)
- [Testing Guide](../../docs/TESTING.md)
