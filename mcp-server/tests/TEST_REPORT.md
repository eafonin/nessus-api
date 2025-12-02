# Test Report: Nessus MCP Server

Comprehensive test documentation organized by the 4-layer test architecture.

---

## Layer 01: Infrastructure (23 tests)

Tests that verify external dependencies are accessible before running any other tests.

### test_nessus_connectivity.py (10 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_dns_resolution` | `layer01_infrastructure/test_nessus_connectivity.py` | `hostname` from NESSUS_URL env | `ip_address: str` | Verifies Nessus hostname resolves. Pass: non-empty IP. |
| `test_tcp_port_connectivity` | `layer01_infrastructure/test_nessus_connectivity.py` | `hostname`, `port=8834` | `result: int` (0=success) | Verifies TCP port 8834 is open. Pass: returns 0. |
| `test_https_reachable` | `layer01_infrastructure/test_nessus_connectivity.py` | `NESSUS_URL/server/status` | `status_code: int` | Verifies HTTPS endpoint responds. Pass: status 200. |
| `test_server_status_ready` | `layer01_infrastructure/test_nessus_connectivity.py` | `NESSUS_URL/server/status` | `{"status": "ready"}` | Verifies Nessus reports ready. Pass: status == "ready". |
| `test_ssl_bypass_works` | `layer01_infrastructure/test_nessus_connectivity.py` | `NESSUS_URL/server/status`, `verify=False` | `status_code: 200` | Verifies SSL bypass works. Pass: status 200. |
| `test_self_signed_cert_detected` | `layer01_infrastructure/test_nessus_connectivity.py` | `NESSUS_URL/server/status`, `verify=True` | `ConnectError` or success | Verifies self-signed cert detected. Pass: raises ConnectError or succeeds. |
| `test_server_status_endpoint` | `layer01_infrastructure/test_nessus_connectivity.py` | `NESSUS_URL/server/status` | `status_code: 200` | Verifies /server/status accessible. Pass: status 200. |
| `test_server_properties_endpoint` | `layer01_infrastructure/test_nessus_connectivity.py` | `NESSUS_URL/server/properties` | `status_code: 200` | Verifies /server/properties accessible. Pass: status 200. |
| `test_authentication_endpoint_accessible` | `layer01_infrastructure/test_nessus_connectivity.py` | `NESSUS_URL/session`, invalid creds | `status_code: 200\|401\|403` | Verifies /session responds. Pass: status in [200, 401, 403]. |
| `test_server_properties_retrievable` | `layer01_infrastructure/test_nessus_connectivity.py` | `NESSUS_URL/server/properties` | `{"nessus_type": ...}` | Verifies properties contain nessus_type. Pass: key exists. |

### test_redis_connectivity.py (6 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_dns_resolution` | `layer01_infrastructure/test_redis_connectivity.py` | `REDIS_HOST` env | `ip_address: str` | Verifies Redis hostname resolves. Pass: non-empty IP. |
| `test_tcp_port_connectivity` | `layer01_infrastructure/test_redis_connectivity.py` | `REDIS_HOST`, `REDIS_PORT=6379` | `result: int` (0=success) | Verifies Redis port is open. Pass: connect_ex returns 0. |
| `test_ping` | `layer01_infrastructure/test_redis_connectivity.py` | Redis client fixture | `True` | Verifies PING works. Pass: returns True. |
| `test_set_get` | `layer01_infrastructure/test_redis_connectivity.py` | `key`, `value` | `value: str` | Verifies SET/GET work. Pass: get returns set value. |
| `test_list_operations` | `layer01_infrastructure/test_redis_connectivity.py` | `key`, items list | `length: 2`, `item` | Verifies LPUSH/LLEN/RPOP. Pass: length=2, rpop returns item. |
| `test_info_command` | `layer01_infrastructure/test_redis_connectivity.py` | Redis client | `{"redis_version": ...}` | Verifies INFO returns server info. Pass: has required keys. |

### test_both_scanners.py (3 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_scanner_reachable` | `layer01_infrastructure/test_both_scanners.py` | `url` param from fixture | `status_code: 200` | Verifies scanner HTTPS reachable. Pass: status 200. |
| `test_scanner_ready` | `layer01_infrastructure/test_both_scanners.py` | Scanner `/server/status` | `{"status": "ready"}` | Verifies scanner reports ready. Pass: status == "ready". |
| `test_scanners_have_different_uuids` | `layer01_infrastructure/test_both_scanners.py` | Both scanners | `uuids: list[str]` | Verifies unique UUIDs. Pass: all UUIDs unique. |

### test_target_accounts.py (4 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_scan_target_ssh_port` | `layer01_infrastructure/test_target_accounts.py` | `SCAN_TARGET_IP`, port 22 | `bool` | Verifies scan-target SSH port open. Pass: port open. |
| `test_external_host_ssh_port` | `layer01_infrastructure/test_target_accounts.py` | `EXTERNAL_HOST_IP`, port 22 | `bool` | Verifies external host SSH port open. Pass: port open. |
| `test_scan_target_accepts_connections` | `layer01_infrastructure/test_target_accounts.py` | `SCAN_TARGET_IP:22` | `banner: str` | Verifies SSH banner received. Pass: "SSH" in banner. |
| `test_credentials_documented` | `layer01_infrastructure/test_target_accounts.py` | Credential structure | `credentials: dict` | Documents test credentials. Pass: has required structure. |

---

## Layer 02: Internal/Unit Tests (343 tests)

Unit tests for internal components using mocks. No external dependencies.

### test_admin_cli.py (21 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_format_timestamp_valid` | `layer02_internal/test_admin_cli.py` | `ts="2024-01-15T10:30:45"` | `"2024-01-15 10:30:45"` | Formats valid ISO timestamp. Pass: contains date and time. |
| `test_format_timestamp_invalid` | `layer02_internal/test_admin_cli.py` | `ts="not a date"` | `"not a date"` | Returns invalid timestamp unchanged. Pass: returns input. |
| `test_format_timestamp_none` | `layer02_internal/test_admin_cli.py` | `ts=None` | `"N/A"` | Handles None timestamp. Pass: returns "N/A". |
| `test_truncate_short_string` | `layer02_internal/test_admin_cli.py` | `s="hello"`, `max_len=10` | `"hello"` | Short string unchanged. Pass: returns input. |
| `test_truncate_long_string` | `layer02_internal/test_admin_cli.py` | `s="hello world..."`, `max_len=10` | `"hello w..."` | Long string truncated with "...". Pass: len=10, ends with "...". |
| `test_truncate_empty` | `layer02_internal/test_admin_cli.py` | `s=""`, `max_len=10` | `""` | Empty string unchanged. Pass: returns "". |
| `test_get_dlq_task_found` | `layer02_internal/test_admin_cli.py` | `task_id="task123"`, mock Redis with task | `{"task_id": "task123", "error": "test error"}` | Finds task in DLQ. Pass: returns task dict. |
| `test_get_dlq_task_not_found` | `layer02_internal/test_admin_cli.py` | `task_id="task123"`, mock Redis with different task | `None` | Task not in DLQ. Pass: returns None. |
| `test_get_dlq_task_empty_dlq` | `layer02_internal/test_admin_cli.py` | `task_id="task123"`, empty mock | `None` | Empty DLQ. Pass: returns None. |
| `test_retry_dlq_task_success` | `layer02_internal/test_admin_cli.py` | `task_id="task123"`, task in DLQ | `True` | Successfully retries DLQ task. Pass: returns True, zrem and lpush called. |
| `test_retry_dlq_task_not_found` | `layer02_internal/test_admin_cli.py` | `task_id="nonexistent"`, empty DLQ | `False` | Retry non-existent task. Pass: returns False, lpush not called. |
| `test_clear_dlq_all` | `layer02_internal/test_admin_cli.py` | `pool="nessus"` | `5` (deleted count) | Clears entire DLQ. Pass: returns delete count, deletes correct key. |
| `test_clear_dlq_before_timestamp` | `layer02_internal/test_admin_cli.py` | `before_timestamp=1234567890.0` | `3` (removed count) | Clears DLQ entries before timestamp. Pass: returns count, zremrangebyscore called. |
| `test_cmd_stats` | `layer02_internal/test_admin_cli.py` | `pool="nessus"`, mock stats | `0` (exit code) | Stats command succeeds. Pass: returns 0, get_queue_stats called. |
| `test_cmd_list_dlq_empty` | `layer02_internal/test_admin_cli.py` | `pool="nessus"`, empty DLQ | `0` | List-dlq with empty DLQ. Pass: returns 0. |
| `test_cmd_list_dlq_with_tasks` | `layer02_internal/test_admin_cli.py` | `pool="nessus"`, 2 tasks in DLQ | `0` | List-dlq with tasks. Pass: returns 0. |
| `test_cmd_inspect_dlq_found` | `layer02_internal/test_admin_cli.py` | `task_id="task123"`, task exists | `0` | Inspect found task. Pass: returns 0, get_dlq_task called with correct args. |
| `test_cmd_inspect_dlq_not_found` | `layer02_internal/test_admin_cli.py` | `task_id="nonexistent"` | `1` | Inspect non-existent task. Pass: returns 1 (error). |
| `test_cmd_retry_dlq_success` | `layer02_internal/test_admin_cli.py` | `task_id="task123"`, `yes=True` | `0` | Retry succeeds. Pass: returns 0, retry_dlq_task called. |
| `test_cmd_retry_dlq_not_found` | `layer02_internal/test_admin_cli.py` | `task_id="nonexistent"`, `yes=True` | `1` | Retry non-existent. Pass: returns 1. |
| `test_cmd_purge_dlq_without_confirm` | `layer02_internal/test_admin_cli.py` | `confirm=False` | `1` | Purge without --confirm. Pass: returns 1, clear_dlq not called. |

### test_authenticated_scans.py (18 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_missing_username_raises` | `layer02_internal/test_authenticated_scans.py` | `{"type": "ssh", "password": "pass"}` | `ValueError("missing required field: username")` | Missing username validation. Pass: raises ValueError with message. |
| `test_missing_password_raises` | `layer02_internal/test_authenticated_scans.py` | `{"type": "ssh", "username": "user"}` | `ValueError("missing required field: password")` | Missing password validation. Pass: raises ValueError. |
| `test_invalid_escalation_method_raises` | `layer02_internal/test_authenticated_scans.py` | `elevate_privileges_with="invalid_method"` | `ValueError("Invalid escalation method")` | Invalid escalation method. Pass: raises ValueError. |
| `test_valid_ssh_credentials_pass` | `layer02_internal/test_authenticated_scans.py` | `{"type": "ssh", "username": "testuser", "password": "testpass"}` | No exception | Valid SSH credentials. Pass: no exception raised. |
| `test_valid_sudo_credentials_pass` | `layer02_internal/test_authenticated_scans.py` | SSH creds + `elevate_privileges_with="sudo"`, `escalation_password` | No exception | Valid sudo creds. Pass: no exception. |
| `test_all_valid_escalation_methods` | `layer02_internal/test_authenticated_scans.py` | 9 valid methods: Nothing, sudo, su, su+sudo, pbrun, dzdo, .k5login, Cisco 'enable', Checkpoint Gaia 'expert' | No exception | All valid methods pass. Pass: none raise. |
| `test_unsupported_credential_type_raises` | `layer02_internal/test_authenticated_scans.py` | `{"type": "windows", ...}` | `ValueError("Unsupported credential type")` | Unsupported type. Pass: raises ValueError. |
| `test_empty_credentials_pass` | `layer02_internal/test_authenticated_scans.py` | `None` or `{}` | No exception | Empty/None credentials (untrusted scan). Pass: no exception. |
| `test_basic_ssh_password_credentials` | `layer02_internal/test_authenticated_scans.py` | SSH password creds | `{"add": {"Host": {"SSH": [{...}]}}}` | Builds basic SSH payload. Pass: correct structure with username, password, auth_method. |
| `test_ssh_sudo_with_password` | `layer02_internal/test_authenticated_scans.py` | SSH + sudo + escalation_password | Payload with `elevate_privileges_with="sudo"` | Builds sudo payload. Pass: has sudo and escalation_password. |
| `test_ssh_sudo_with_escalation_account` | `layer02_internal/test_authenticated_scans.py` | SSH + sudo + escalation_account | Payload with `escalation_account` | Builds payload with custom escalation account. Pass: has escalation_account. |
| `test_ssh_sudo_nopasswd` | `layer02_internal/test_authenticated_scans.py` | SSH + sudo, no escalation_password | Payload without escalation_password | NOPASSWD sudo. Pass: elevate=sudo but no escalation_password. |
| `test_payload_structure_complete` | `layer02_internal/test_authenticated_scans.py` | Basic SSH creds | Complete Nessus API payload structure | Full payload structure. Pass: exact match with add/edit/delete keys. |
| `test_su_escalation` | `layer02_internal/test_authenticated_scans.py` | SSH + `elevate_privileges_with="su"` | Payload with su escalation | Su escalation method. Pass: elevate=su with escalation_password. |
| `test_scan_request_with_credentials` | `layer02_internal/test_authenticated_scans.py` | ScanRequest with credentials dict | `request.credentials == credentials` | ScanRequest accepts credentials. Pass: credentials stored correctly. |
| `test_scan_request_without_credentials` | `layer02_internal/test_authenticated_scans.py` | ScanRequest without credentials | `request.credentials is None` | ScanRequest without creds (untrusted). Pass: credentials is None. |
| `test_create_scan_includes_credentials_in_payload` | `layer02_internal/test_authenticated_scans.py` | ScanRequest with creds, mocked HTTP | `scan_id: 123`, payload contains credentials | Create scan includes creds. Pass: credentials in API payload. |
| `test_create_scan_without_credentials` | `layer02_internal/test_authenticated_scans.py` | ScanRequest without creds, mocked HTTP | `scan_id: 456`, no credentials in payload | Create scan without creds. Pass: no credentials key in payload. |

### test_circuit_breaker.py (27 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_initial_state_closed` | `layer02_internal/test_circuit_breaker.py` | `name="test"` | `state == CircuitState.CLOSED` | Circuit starts closed. Pass: state is CLOSED. |
| `test_allow_request_when_closed` | `layer02_internal/test_circuit_breaker.py` | Closed circuit | `True` | Requests allowed when closed. Pass: allow_request() returns True. |
| `test_record_success_keeps_closed` | `layer02_internal/test_circuit_breaker.py` | Closed circuit + success | `state == CLOSED` | Success keeps closed. Pass: state remains CLOSED. |
| `test_single_failure_stays_closed` | `layer02_internal/test_circuit_breaker.py` | `failure_threshold=3`, 1 failure | `state == CLOSED`, `_failure_count == 1` | Single failure doesn't open. Pass: closed with count=1. |
| `test_opens_after_threshold` | `layer02_internal/test_circuit_breaker.py` | `failure_threshold=3`, 3 failures | `state == OPEN` | Opens after threshold. Pass: state becomes OPEN on 3rd failure. |
| `test_blocks_requests_when_open` | `layer02_internal/test_circuit_breaker.py` | Open circuit | `allow_request() == False` | Blocks requests when open. Pass: returns False. |
| `test_reset_closes_circuit` | `layer02_internal/test_circuit_breaker.py` | Open circuit + reset() | `state == CLOSED`, `_failure_count == 0` | Manual reset closes. Pass: state CLOSED, count reset. |
| `test_transitions_to_half_open` | `layer02_internal/test_circuit_breaker.py` | `recovery_timeout=0.1`, wait 0.15s | `state == HALF_OPEN` | Transitions to half-open after timeout. Pass: state is HALF_OPEN. |
| `test_half_open_allows_limited_requests` | `layer02_internal/test_circuit_breaker.py` | `half_open_max_requests=2` | 2 True, then False | Half-open allows limited requests. Pass: 2 allowed, 3rd blocked. |
| `test_success_in_half_open_closes` | `layer02_internal/test_circuit_breaker.py` | Half-open + success | `state == CLOSED` | Success in half-open closes. Pass: state becomes CLOSED. |
| `test_failure_in_half_open_reopens` | `layer02_internal/test_circuit_breaker.py` | Half-open + failure | `state == OPEN` | Failure in half-open reopens. Pass: state becomes OPEN. |
| `test_get_status_closed` | `layer02_internal/test_circuit_breaker.py` | Closed circuit | `{"name": "test", "state": "closed", "failure_count": 0}` | Status when closed. Pass: correct status dict. |
| `test_get_status_open` | `layer02_internal/test_circuit_breaker.py` | Open circuit | `{"state": "open", "time_until_recovery": >0}` | Status when open. Pass: includes time_until_recovery. |
| `test_success_resets_failure_count` | `layer02_internal/test_circuit_breaker.py` | 2 failures + 1 success | `_failure_count == 0` | Success resets failure count. Pass: count reset to 0. |
| `test_get_creates_breaker` | `layer02_internal/test_circuit_breaker.py` | `registry.get("scanner1")` | CircuitBreaker with name="scanner1" | Registry creates breakers. Pass: returns breaker with correct name. |
| `test_get_returns_same_breaker` | `layer02_internal/test_circuit_breaker.py` | `registry.get("scanner1")` twice | Same object | Registry returns same breaker. Pass: cb1 is cb2. |
| `test_get_different_breakers` | `layer02_internal/test_circuit_breaker.py` | `get("scanner1")`, `get("scanner2")` | Different objects | Registry creates different breakers. Pass: cb1 is not cb2. |
| `test_get_all_status` | `layer02_internal/test_circuit_breaker.py` | Registry with 2 breakers | `{"scanner1": {...}, "scanner2": {...}}` | Get all breaker status. Pass: both scanners in status. |
| `test_reset_specific` | `layer02_internal/test_circuit_breaker.py` | Open breaker + reset("scanner1") | `True`, state CLOSED | Reset specific breaker. Pass: returns True, state CLOSED. |
| `test_reset_nonexistent` | `layer02_internal/test_circuit_breaker.py` | `reset("nonexistent")` | `False` | Reset non-existent. Pass: returns False. |
| `test_reset_all` | `layer02_internal/test_circuit_breaker.py` | 2 open breakers + reset_all() | Both CLOSED | Reset all breakers. Pass: both states CLOSED. |
| `test_custom_defaults` | `layer02_internal/test_circuit_breaker.py` | `failure_threshold=10`, `recovery_timeout=60.0` | Breaker with custom values | Custom registry defaults. Pass: breaker has custom threshold/timeout. |
| `test_error_message` | `layer02_internal/test_circuit_breaker.py` | `CircuitOpenError("msg", circuit_name="scanner1")` | Error with message and circuit_name | Error includes info. Pass: str contains message, has circuit_name attr. |
| `test_state_metric_updated` | `layer02_internal/test_circuit_breaker.py` | State transitions | Gauge values 0→1→2 | Prometheus metric updated. Pass: gauge shows 0 (closed), 1 (open), 2 (half-open). |
| `test_failure_counter_incremented` | `layer02_internal/test_circuit_breaker.py` | Record failure | Counter +1 | Failure counter incremented. Pass: counter increases by 1. |
| `test_opens_counter_incremented` | `layer02_internal/test_circuit_breaker.py` | Open circuit | Opens counter +1 | Opens counter incremented. Pass: counter increases when circuit opens. |
| `test_concurrent_access` | `layer02_internal/test_circuit_breaker.py` | 4 threads × 50 failures | `_failure_count == 200`, no errors | Thread safety. Pass: count=200, no exceptions. |

### test_error_responses.py (18 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_task_not_found_response_format` | `layer02_internal/test_error_responses.py` | `task_id="nonexistent_task_123"` | `{"error": "Task ... not found"}` | Task not found format. Pass: has "error" key, contains "not found" and task_id. |
| `test_scanner_not_found_response_format` | `layer02_internal/test_error_responses.py` | Scanner lookup failure | `{"error": "Scanner not found", "status_code": 404}` | Scanner not found format. Pass: status_code=404, error contains "scanner". |
| `test_scan_results_not_found_format` | `layer02_internal/test_error_responses.py` | Non-existent results | JSON string `{"error": "Scan results not found"}` | Results not found format. Pass: JSON parseable, has error key. |
| `test_idempotency_conflict_response_format` | `layer02_internal/test_error_responses.py` | Conflict with existing key | `{"error": "Conflict", "status_code": 409, "message": ...}` | Idempotency conflict format. Pass: status=409, message has key and task_id. |
| `test_conflict_error_exception_handling` | `layer02_internal/test_error_responses.py` | ConflictError exception | Exception with task_id in message | ConflictError contains info. Pass: task_id in str(exception). |
| `test_conflict_preserves_task_reference` | `layer02_internal/test_error_responses.py` | Conflict response | `existing_task_id` field present | Conflict preserves task ref. Pass: has existing_task_id field. |
| `test_invalid_scan_type_error` | `layer02_internal/test_error_responses.py` | `scan_type="invalid_scan"` | Error with invalid type and valid types | Invalid scan_type error. Pass: error contains invalid type and "untrusted". |
| `test_missing_privilege_escalation_error` | `layer02_internal/test_error_responses.py` | authenticated_privileged without escalation | Error mentioning sudo/su | Missing escalation error. Pass: mentions authenticated_privileged and sudo/su. |
| `test_schema_conflict_error` | `layer02_internal/test_error_responses.py` | Both schema_profile and custom_fields | Error about conflict | Schema conflict error. Pass: mentions both schema_profile and custom_fields. |
| `test_scan_not_completed_error` | `layer02_internal/test_error_responses.py` | `status="running"` | `{"error": "Scan not completed yet (status: running)"}` | Scan not completed error. Pass: contains "not completed" and status. |
| `test_all_errors_have_error_key` | `layer02_internal/test_error_responses.py` | Various error responses | All have "error" key | Consistent error format. Pass: all responses have "error" key. |
| `test_http_errors_have_status_code` | `layer02_internal/test_error_responses.py` | HTTP error responses | All have integer status_code >= 400 | HTTP errors have status. Pass: status_code is int >= 400. |
| `test_error_messages_are_human_readable` | `layer02_internal/test_error_responses.py` | Various error messages | Readable strings | Human-readable errors. Pass: no tracebacks, 10-500 chars. |
| `test_failed_scan_includes_error_message` | `layer02_internal/test_error_responses.py` | Failed scan status | Has `error_message` field | Failed scan has error. Pass: status="failed", error_message not None. |
| `test_timeout_scan_includes_error_message` | `layer02_internal/test_error_responses.py` | Timeout scan status | Has `error_message` field | Timeout has error. Pass: status="timeout", has error_message. |
| `test_completed_scan_no_error_message` | `layer02_internal/test_error_responses.py` | Completed scan status | `error_message: None` | Completed has no error. Pass: status="completed", error_message is None. |
| `test_auth_failure_includes_troubleshooting` | `layer02_internal/test_error_responses.py` | Auth failed response | `troubleshooting.suggestions` list | Auth failure troubleshooting. Pass: has troubleshooting with suggestions list. |
| `test_partial_auth_includes_details` | `layer02_internal/test_error_responses.py` | Partial auth response | `hosts_summary` dict | Partial auth details. Pass: has hosts_summary with total/authenticated/failed. |

### test_health.py (17 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_check_redis_success` | `layer02_internal/test_health.py` | `redis://redis:6379` | `bool` | Redis check returns bool. Pass: isinstance(result, bool). |
| `test_check_redis_connection_success` | `layer02_internal/test_health.py` | Mocked successful ping | `True` | Mocked Redis success. Pass: returns True, ping called. |
| `test_check_redis_connection_failure` | `layer02_internal/test_health.py` | Mocked connection error | `False` | Mocked Redis failure. Pass: returns False. |
| `test_check_redis_ping_failure` | `layer02_internal/test_health.py` | Mocked ping failure | `False` | Ping fails. Pass: returns False. |
| `test_check_filesystem_success_with_existing_dir` | `layer02_internal/test_health.py` | Existing temp directory | `True` | Filesystem check with existing dir. Pass: returns True. |
| `test_check_filesystem_success_creates_dir` | `layer02_internal/test_health.py` | Non-existent directory | `True`, directory created | Creates directory if needed. Pass: True and dir exists. |
| `test_check_filesystem_write_test` | `layer02_internal/test_health.py` | Temp directory | `True`, no leftover file | Write test cleans up. Pass: True, .health_check file removed. |
| `test_check_filesystem_readonly_failure` | `layer02_internal/test_health.py` | Read-only directory | `bool` | Read-only handling. Pass: returns bool (behavior depends on permissions). |
| `test_check_filesystem_nonexistent_parent` | `layer02_internal/test_health.py` | `/root/nonexistent/parent/dir` | `bool` | Non-existent parent. Pass: returns bool. |
| `test_check_all_dependencies_all_healthy` | `layer02_internal/test_health.py` | Both mocked True | `{"status": "healthy", "redis_healthy": True, "filesystem_healthy": True}` | All healthy. Pass: status="healthy", both True. |
| `test_check_all_dependencies_redis_unhealthy` | `layer02_internal/test_health.py` | Redis False, FS True | `{"status": "unhealthy", "redis_healthy": False}` | Redis unhealthy. Pass: status="unhealthy". |
| `test_check_all_dependencies_filesystem_unhealthy` | `layer02_internal/test_health.py` | Redis True, FS False | `{"status": "unhealthy", "filesystem_healthy": False}` | FS unhealthy. Pass: status="unhealthy". |
| `test_check_all_dependencies_all_unhealthy` | `layer02_internal/test_health.py` | Both False | `{"status": "unhealthy"}` | All unhealthy. Pass: both False. |
| `test_check_all_dependencies_returns_dict` | `layer02_internal/test_health.py` | Mocked healthy | Dict with required keys | Returns proper dict. Pass: has status, redis_healthy, filesystem_healthy, redis_url, data_dir. |
| `test_check_all_dependencies_preserves_urls` | `layer02_internal/test_health.py` | Custom URLs | URLs in response | URLs preserved. Pass: redis_url and data_dir match inputs. |
| `test_filesystem_check_with_real_tempdir` | `layer02_internal/test_health.py` | Real temp dir | `True` | Filesystem check with real tempdir. Pass: returns True. |
| `test_filesystem_creates_nested_directories` | `layer02_internal/test_health.py` | Nested path in temp dir | `True`, nested dirs exist | Creates nested dirs. Pass: True, all levels exist. |

### test_housekeeping.py (18 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_default_initialization` | `layer02_internal/test_housekeeping.py` | No args | `data_dir="/app/data/tasks"`, `completed_ttl=7d`, `failed_ttl=30d` | Default values. Pass: defaults set correctly. |
| `test_custom_initialization` | `layer02_internal/test_housekeeping.py` | Custom values | Custom TTLs | Custom values. Pass: custom values applied. |
| `test_cleanup_nonexistent_directory` | `layer02_internal/test_housekeeping.py` | `/nonexistent/path` | `{"deleted_count": 0, "errors": ["...does not exist"]}` | Non-existent dir. Pass: count=0, error message. |
| `test_cleanup_empty_directory` | `layer02_internal/test_housekeeping.py` | Empty temp dir | `{"deleted_count": 0, "errors": []}` | Empty dir. Pass: count=0, no errors. |
| `test_cleanup_completed_task_old` | `layer02_internal/test_housekeeping.py` | Completed task, age=10d, TTL=7d | `{"deleted_count": 1}`, task deleted | Old completed deleted. Pass: count=1, task dir removed. |
| `test_cleanup_completed_task_recent` | `layer02_internal/test_housekeeping.py` | Completed task, age=3d, TTL=7d | `{"deleted_count": 0}`, task exists | Recent completed kept. Pass: count=0, task exists. |
| `test_cleanup_failed_task_old` | `layer02_internal/test_housekeeping.py` | Failed task, age=35d, TTL=30d | `{"deleted_count": 1}` | Old failed deleted. Pass: count=1. |
| `test_cleanup_failed_task_recent` | `layer02_internal/test_housekeeping.py` | Failed task, age=10d, TTL=30d | `{"deleted_count": 0}` | Recent failed kept. Pass: count=0, task exists. |
| `test_cleanup_timeout_task_old` | `layer02_internal/test_housekeeping.py` | Timeout task, age=35d | `{"deleted_count": 1}` | Old timeout deleted. Pass: count=1. |
| `test_cleanup_skips_running_tasks` | `layer02_internal/test_housekeeping.py` | Running task, age=100d | `{"deleted_count": 0, "skipped": 1}` | Running never deleted. Pass: skipped=1, task exists. |
| `test_cleanup_skips_queued_tasks` | `layer02_internal/test_housekeeping.py` | Queued task, age=100d | `{"deleted_count": 0, "skipped": 1}` | Queued never deleted. Pass: skipped=1, task exists. |
| `test_cleanup_multiple_tasks` | `layer02_internal/test_housekeeping.py` | 4 tasks: old completed, recent completed, old failed, running | `{"deleted_count": 2, "skipped": 1}` | Multiple tasks handled. Pass: correct counts, correct tasks remain. |
| `test_cleanup_tracks_freed_bytes` | `layer02_internal/test_housekeeping.py` | Task with data, deleted | `{"freed_bytes": >0, "freed_mb": >=0}` | Tracks freed space. Pass: freed_bytes > 0. |
| `test_cleanup_handles_invalid_json` | `layer02_internal/test_housekeeping.py` | Invalid task.json | `{"errors": ["Invalid JSON..."]}` | Invalid JSON handled. Pass: error captured, no crash. |
| `test_get_stats_empty` | `layer02_internal/test_housekeeping.py` | Empty directory | `{"total_tasks": 0, "by_status": {}}` | Stats for empty dir. Pass: zero counts. |
| `test_get_stats_counts_by_status` | `layer02_internal/test_housekeeping.py` | 4 tasks with different statuses | `{"total_tasks": 4, "by_status": {"completed": 2, "failed": 1, "running": 1}}` | Counts by status. Pass: correct counts. |
| `test_get_stats_tracks_expired` | `layer02_internal/test_housekeeping.py` | Mix of expired/fresh tasks | `{"expired": {"completed": 1, "failed": 1}}` | Tracks expired. Pass: correct expired counts. |
| `test_ttl_deletions_metric_incremented` | `layer02_internal/test_housekeeping.py` | Delete task, check metric | Counter +1 | Metric incremented. Pass: ttl_deletions_total increases. |

### test_idempotency.py (13 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_hash_request_consistent` | `layer02_internal/test_idempotency.py` | Same params twice | Same 64-char hash | Consistent hashing. Pass: hash1 == hash2, len=64. |
| `test_hash_request_key_order_independent` | `layer02_internal/test_idempotency.py` | Same params, different order | Same hash | Order independent. Pass: hash1 == hash2. |
| `test_hash_request_different_params` | `layer02_internal/test_idempotency.py` | Different params | Different hashes | Different params → different hashes. Pass: hash1 != hash2. |
| `test_hash_request_none_normalization` | `layer02_internal/test_idempotency.py` | `description: None` twice | Same hash | None normalized. Pass: hash1 == hash2. |
| `test_hash_request_bool_normalization` | `layer02_internal/test_idempotency.py` | `enabled: True` twice | Same hash | Booleans normalized. Pass: hash1 == hash2. |
| `test_store_new_key` | `layer02_internal/test_idempotency.py` | New idempotency key | `True` | Store new key. Pass: returns True. |
| `test_store_existing_key` | `layer02_internal/test_idempotency.py` | Store same key twice | `True`, then `False` | Existing key rejected. Pass: first True, second False. |
| `test_check_nonexistent_key` | `layer02_internal/test_idempotency.py` | Non-existent key | `None` | Check missing key. Pass: returns None. |
| `test_check_matching_key` | `layer02_internal/test_idempotency.py` | Stored key + same params | `task_id` | Check matching key. Pass: returns stored task_id. |
| `test_check_conflicting_params` | `layer02_internal/test_idempotency.py` | Stored key + different params | `ConflictError` | Conflicting params. Pass: raises ConflictError with "different request parameters". |
| `test_store_ttl_set` | `layer02_internal/test_idempotency.py` | Store key, check Redis TTL | TTL ~172800s (48h) | TTL set correctly. Pass: TTL between 172700-172800. |
| `test_full_workflow_with_retry` | `layer02_internal/test_idempotency.py` | Check→Store→Retry same→Retry different | None→True→task_id→ConflictError | Full workflow. Pass: correct sequence of responses. |
| `test_concurrent_store_operations` | `layer02_internal/test_idempotency.py` | 10 concurrent stores | Only 1 succeeds | Atomic SETNX. Pass: exactly 1 True in results. |

### test_ip_utils.py (55 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_parse_ipv4_address` | `layer02_internal/test_ip_utils.py` | `"192.168.1.1"` | `IPv4Address` | Parse IPv4. Pass: correct address type. |
| `test_parse_ipv4_cidr` | `layer02_internal/test_ip_utils.py` | `"10.0.0.0/8"` | `IPv4Network` | Parse CIDR. Pass: correct network. |
| `test_parse_ipv4_cidr_non_strict` | `layer02_internal/test_ip_utils.py` | `"192.168.1.5/24"` | `"192.168.1.0/24"` | Non-strict CIDR. Pass: normalized to network address. |
| `test_parse_ipv6_address` | `layer02_internal/test_ip_utils.py` | `"::1"` | `IPv6Address` | Parse IPv6. Pass: correct type. |
| `test_parse_ipv6_cidr` | `layer02_internal/test_ip_utils.py` | `"2001:db8::/32"` | `IPv6Network` | Parse IPv6 CIDR. Pass: correct network. |
| `test_parse_hostname_returns_none` | `layer02_internal/test_ip_utils.py` | `"scan-target.local"` | `None` | Hostname returns None. Pass: None for hostnames. |
| `test_parse_invalid_returns_none` | `layer02_internal/test_ip_utils.py` | `"999.999.999.999"` | `None` | Invalid IP returns None. Pass: None for invalid. |
| `test_parse_empty_returns_none` | `layer02_internal/test_ip_utils.py` | `""` | `None` | Empty returns None. Pass: None. |
| `test_parse_whitespace_trimmed` | `layer02_internal/test_ip_utils.py` | `"  192.168.1.1  "` | Correct IP | Whitespace trimmed. Pass: correct address. |
| `test_ip_equals_ip` | `layer02_internal/test_ip_utils.py` | Two identical IPs | `True` | IP exact match. Pass: True. |
| `test_ip_not_equals_ip` | `layer02_internal/test_ip_utils.py` | Two different IPs | `False` | IP non-match. Pass: False. |
| `test_ip_in_network` | `layer02_internal/test_ip_utils.py` | IP within network | `True` | IP in network. Pass: True. |
| `test_ip_not_in_network` | `layer02_internal/test_ip_utils.py` | IP outside network | `False` | IP not in network. Pass: False. |
| `test_network_contains_ip` | `layer02_internal/test_ip_utils.py` | Network contains IP (reversed) | `True` | Network contains IP. Pass: True. |
| `test_networks_overlap` | `layer02_internal/test_ip_utils.py` | Overlapping networks | `True` | Networks overlap. Pass: True. |
| `test_networks_no_overlap` | `layer02_internal/test_ip_utils.py` | Non-overlapping networks | `False` | No overlap. Pass: False. |
| `test_ip_exact_match` | `layer02_internal/test_ip_utils.py` | `targets_match("192.168.1.1", "192.168.1.1")` | `True` | Exact IP match. Pass: True. |
| `test_ip_no_match` | `layer02_internal/test_ip_utils.py` | Different IPs | `False` | IP no match. Pass: False. |
| `test_ip_in_cidr_hit` | `layer02_internal/test_ip_utils.py` | IP within stored CIDR | `True` | IP in CIDR hit. Pass: True. |
| `test_ip_in_large_cidr_hit` | `layer02_internal/test_ip_utils.py` | IP in /8 network | `True` | Large CIDR hit. Pass: True. |
| `test_ip_at_network_boundary_hit` | `layer02_internal/test_ip_utils.py` | Network address | `True` | Boundary hit. Pass: True. |
| `test_ip_at_broadcast_boundary_hit` | `layer02_internal/test_ip_utils.py` | Broadcast address | `True` | Broadcast hit. Pass: True. |
| `test_ip_not_in_cidr_miss` | `layer02_internal/test_ip_utils.py` | IP outside CIDR | `False` | CIDR miss. Pass: False. |
| `test_ip_adjacent_cidr_miss` | `layer02_internal/test_ip_utils.py` | Adjacent but outside | `False` | Adjacent miss. Pass: False. |
| `test_cidr_contains_ip_hit` | `layer02_internal/test_ip_utils.py` | Query CIDR contains stored IP | `True` | CIDR contains IP. Pass: True. |
| `test_cidr_overlap_subset_hit` | `layer02_internal/test_ip_utils.py` | Query is subset | `True` | Subset hit. Pass: True. |
| `test_cidr_overlap_superset_hit` | `layer02_internal/test_ip_utils.py` | Query is superset | `True` | Superset hit. Pass: True. |
| `test_cidr_exact_match_hit` | `layer02_internal/test_ip_utils.py` | Same CIDR | `True` | Exact CIDR match. Pass: True. |
| `test_cidr_no_overlap_miss` | `layer02_internal/test_ip_utils.py` | Non-overlapping CIDRs | `False` | No overlap miss. Pass: False. |
| `test_multiple_targets_match_first_hit` | `layer02_internal/test_ip_utils.py` | Query matches first of list | `True` | Multiple targets first. Pass: True. |
| `test_multiple_targets_match_second_hit` | `layer02_internal/test_ip_utils.py` | Query matches second of list | `True` | Multiple targets second. Pass: True. |
| `test_multiple_targets_match_cidr_in_list_hit` | `layer02_internal/test_ip_utils.py` | Query IP matches CIDR in list | `True` | IP matches CIDR in list. Pass: True. |
| `test_multiple_targets_cidr_query_hit` | `layer02_internal/test_ip_utils.py` | Query CIDR contains stored IP | `True` | CIDR query contains stored IP. Pass: True. |
| `test_multiple_targets_no_match_miss` | `layer02_internal/test_ip_utils.py` | Query matches none | `False` | Multiple targets miss. Pass: False. |
| `test_multiple_targets_cidr_no_overlap_miss` | `layer02_internal/test_ip_utils.py` | Query CIDR doesn't overlap stored | `False` | CIDR no overlap. Pass: False. |
| `test_hostname_exact_match_hit` | `layer02_internal/test_ip_utils.py` | Same hostname | `True` | Hostname match. Pass: True. |
| `test_hostname_case_insensitive_hit` | `layer02_internal/test_ip_utils.py` | Different case | `True` | Case insensitive. Pass: True. |
| `test_hostname_in_list_hit` | `layer02_internal/test_ip_utils.py` | Hostname in target list | `True` | Hostname in list. Pass: True. |
| `test_hostname_no_match_miss` | `layer02_internal/test_ip_utils.py` | Different hostname | `False` | Hostname miss. Pass: False. |
| `test_hostname_vs_ip_miss` | `layer02_internal/test_ip_utils.py` | Hostname vs IP | `False` | Hostname vs IP miss. Pass: False. |
| `test_ip_vs_hostname_miss` | `layer02_internal/test_ip_utils.py` | IP query vs hostname target | `False` | IP vs hostname miss. Pass: False. |
| `test_empty_query_miss` | `layer02_internal/test_ip_utils.py` | Empty query | `False` | Empty query miss. Pass: False. |
| `test_empty_stored_targets_miss` | `layer02_internal/test_ip_utils.py` | Empty stored targets | `False` | Empty stored miss. Pass: False. |
| `test_both_empty_miss` | `layer02_internal/test_ip_utils.py` | Both query and stored empty | `False` | Both empty miss. Pass: False. |
| `test_empty_entries_in_list` | `layer02_internal/test_ip_utils.py` | Empty entries in comma list | `True` | Empty entries skipped. Pass: True. |
| `test_whitespace_handling` | `layer02_internal/test_ip_utils.py` | Whitespace in list | `True` | Whitespace handled. Pass: True. |
| `test_ip_different_network_miss` | `layer02_internal/test_ip_utils.py` | IP in different network | `False` | Different network miss. Pass: False. |
| `test_large_cidr_contains_ip_hit` | `layer02_internal/test_ip_utils.py` | /8 network contains IP | `True` | Large CIDR contains IP. Pass: True. |
| `test_cidr_not_contains_ip_miss` | `layer02_internal/test_ip_utils.py` | CIDR doesn't contain IP | `False` | CIDR not contains IP. Pass: False. |
| `test_cidr_partial_overlap_hit` | `layer02_internal/test_ip_utils.py` | Partially overlapping CIDRs | `True` | Partial overlap hit. Pass: True. |
| `test_cidr_adjacent_no_overlap_miss` | `layer02_internal/test_ip_utils.py` | Adjacent non-overlapping CIDRs | `False` | Adjacent no overlap. Pass: False. |
| `test_scenario_scan_target_172_30_0_9` | `layer02_internal/test_ip_utils.py` | Real scenario matching | Correct matches | Real scenario. Pass: correct match/miss. |
| `test_scenario_large_network_scan` | `layer02_internal/test_ip_utils.py` | /8 network search | Hosts within match | Large network. Pass: internal IPs match, external miss. |
| `test_scenario_multiple_network_scan` | `layer02_internal/test_ip_utils.py` | Multiple networks | Correct matches per network | Multiple networks. Pass: each network matches correctly. |
| `test_scenario_subnet_search_for_specific_scans` | `layer02_internal/test_ip_utils.py` | Subnet search for scans | Correct overlap detection | Subnet search. Pass: /16 matches /24, IP, /8. |

### test_list_tasks.py (14 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_filter_by_status_completed` | `layer02_internal/test_list_tasks.py` | `status="completed"` | 1 task with status "completed" | Filter by completed. Pass: only completed tasks returned. |
| `test_filter_by_status_running` | `layer02_internal/test_list_tasks.py` | `status="running"` | 1 task with status "running" | Filter by running. Pass: only running tasks. |
| `test_filter_by_status_queued` | `layer02_internal/test_list_tasks.py` | `status="queued"` | 1 task with status "queued" | Filter by queued. Pass: only queued tasks. |
| `test_filter_by_pool_nessus` | `layer02_internal/test_list_tasks.py` | `pool="nessus"` | 3 tasks in nessus pool | Filter by nessus pool. Pass: correct task IDs. |
| `test_filter_by_pool_dmz` | `layer02_internal/test_list_tasks.py` | `pool="nessus_dmz"` | 1 task in dmz pool | Filter by dmz pool. Pass: only dmz tasks. |
| `test_combined_filter_status_and_pool` | `layer02_internal/test_list_tasks.py` | `status="completed"`, `pool="nessus"` | 1 task matching both | Combined filter. Pass: only matching task. |
| `test_limit_respects_count` | `layer02_internal/test_list_tasks.py` | `limit=2` | ≤2 tasks | Limit respected. Pass: len ≤ limit. |
| `test_no_results_returns_empty` | `layer02_internal/test_list_tasks.py` | `status="timeout"` (none exist) | Empty list | No results. Pass: empty list. |
| `test_target_filter_exact_ip_match` | `layer02_internal/test_list_tasks.py` | `target_filter="10.0.0.50"` | 1 task with exact target | Exact IP filter. Pass: matching task. |
| `test_target_filter_ip_in_cidr` | `layer02_internal/test_list_tasks.py` | `target_filter="192.168.1.100"` | 1 task with CIDR containing IP | IP in CIDR filter. Pass: matching task. |
| `test_target_filter_cidr_contains_stored_ip` | `layer02_internal/test_list_tasks.py` | `target_filter="10.0.0.0/24"` | 1 task with IP in that CIDR | CIDR contains IP filter. Pass: matching task. |
| `test_target_filter_no_match` | `layer02_internal/test_list_tasks.py` | `target_filter="8.8.8.8"` | Empty list | No match filter. Pass: empty list. |
| `test_response_contains_required_fields` | `layer02_internal/test_list_tasks.py` | Any task | Dict with all required fields | Required fields present. Pass: has task_id, trace_id, status, etc. |
| `test_response_values_match_task` | `layer02_internal/test_list_tasks.py` | Specific task | Values match task attributes | Values match. Pass: all values equal task attrs. |

### test_logging_config.py (9 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_configure_logging_sets_log_level` | `layer02_internal/test_logging_config.py` | `log_level="DEBUG"` | No exception | Sets log level. Pass: no exception. |
| `test_configure_logging_default_level` | `layer02_internal/test_logging_config.py` | No args | No exception | Default level (INFO). Pass: no exception. |
| `test_get_logger_returns_structured_logger` | `layer02_internal/test_logging_config.py` | `get_logger("test_module")` | Logger with info/error/debug methods | Returns structured logger. Pass: has logging methods. |
| `test_get_logger_without_name` | `layer02_internal/test_logging_config.py` | `get_logger()` | Logger with methods | Logger without name. Pass: has methods. |
| `test_json_output_format` | `layer02_internal/test_logging_config.py` | Log message | JSON with event, key1, key2, timestamp | JSON format. Pass: valid JSON with all keys. |
| `test_timestamp_format` | `layer02_internal/test_logging_config.py` | Log message | ISO 8601 timestamp | ISO timestamp. Pass: contains "T" or "-". |
| `test_log_levels` | `layer02_internal/test_logging_config.py` | debug/info/warning/error | 4+ log records | All levels work. Pass: ≥4 records captured. |
| `test_structured_data_logging` | `layer02_internal/test_logging_config.py` | Structured data dict | JSON with all keys preserved | Structured data. Pass: all keys in JSON. |
| `test_exception_logging` | `layer02_internal/test_logging_config.py` | Exception with exc_info=True | Log record captured | Exception logging. Pass: record captured. |

### test_metrics.py (45 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_scans_total_counter_exists` | `layer02_internal/test_metrics.py` | - | Counter with name, labels | Counter exists. Pass: has scan_type, status labels. |
| `test_api_requests_total_counter_exists` | `layer02_internal/test_metrics.py` | - | Counter with tool, status labels | API counter exists. Pass: has required labels. |
| `test_ttl_deletions_total_counter_exists` | `layer02_internal/test_metrics.py` | - | Counter exists | TTL counter exists. Pass: has correct name. |
| `test_active_scans_gauge_exists` | `layer02_internal/test_metrics.py` | - | Gauge exists | Active scans gauge. Pass: correct name. |
| `test_scanner_instances_gauge_exists` | `layer02_internal/test_metrics.py` | - | Gauge with scanner_type, enabled labels | Scanner gauge. Pass: has labels. |
| `test_queue_depth_gauge_exists` | `layer02_internal/test_metrics.py` | - | Gauge with queue label | Queue depth gauge. Pass: has queue label. |
| `test_dlq_size_gauge_exists` | `layer02_internal/test_metrics.py` | - | Gauge exists | DLQ gauge exists. Pass: correct name. |
| `test_task_duration_histogram_exists` | `layer02_internal/test_metrics.py` | - | Histogram exists | Duration histogram. Pass: correct name. |
| `test_record_tool_call_increments_counter` | `layer02_internal/test_metrics.py` | `tool="test_tool"`, `status="success"` | Counter +1 | Tool call increments. Pass: counter increases. |
| `test_record_tool_call_default_status` | `layer02_internal/test_metrics.py` | `tool="default_test"` | Counter +1 for status="success" | Default status. Pass: uses "success". |
| `test_record_scan_submission_increments_counter` | `layer02_internal/test_metrics.py` | `scan_type="untrusted"`, `status="queued"` | Counter +1 | Submission increments. Pass: counter increases. |
| `test_record_scan_completion_increments_counter` | `layer02_internal/test_metrics.py` | `scan_type="untrusted"`, `status="completed"` | Counter +1 | Completion increments. Pass: counter increases. |
| `test_update_active_scans_count_sets_gauge` | `layer02_internal/test_metrics.py` | `count=5` then `count=0` | Gauge = 5 then 0 | Active scans updated. Pass: gauge matches. |
| `test_update_queue_metrics_sets_gauges` | `layer02_internal/test_metrics.py` | `main_depth=10`, `dlq_depth=2` | Gauges set correctly | Queue metrics updated. Pass: all gauges correct. |
| `test_update_scanner_instances_metric_sets_gauge` | `layer02_internal/test_metrics.py` | `nessus`, enabled=3, disabled=1 | Gauge values set | Scanner instances updated. Pass: both labels set. |
| `test_metrics_response_returns_bytes` | `layer02_internal/test_metrics.py` | - | `bytes` | Response is bytes. Pass: isinstance bytes. |
| `test_metrics_response_contains_prometheus_format` | `layer02_internal/test_metrics.py` | - | Contains "# HELP" or "# TYPE" | Prometheus format. Pass: has format markers. |
| `test_metrics_response_contains_all_metrics` | `layer02_internal/test_metrics.py` | - | Contains all metric names | All metrics present. Pass: all names in response. |
| `test_metrics_response_valid_prometheus_format` | `layer02_internal/test_metrics.py` | - | HELP, TYPE, metric lines | Valid format. Pass: has all line types. |
| `test_histogram_buckets_defined` | `layer02_internal/test_metrics.py` | - | Buckets [60, 300, 600, 1800, 3600, 7200, 14400] | Correct buckets. Pass: exact match. |
| `test_scans_total_with_different_labels` | `layer02_internal/test_metrics.py` | Different scan_types | Separate counters | Label isolation. Pass: each type tracked separately. |
| `test_api_requests_with_different_tools` | `layer02_internal/test_metrics.py` | Different tools | Separate counters | Tool isolation. Pass: each tool tracked separately. |
| `test_scanner_instances_with_different_types` | `layer02_internal/test_metrics.py` | nessus and openvas | Separate gauges | Type isolation. Pass: each type tracked. |
| `test_pool_queue_depth_gauge_exists` | `layer02_internal/test_metrics.py` | - | Gauge with pool label | Pool queue gauge. Pass: has pool label. |
| `test_pool_dlq_depth_gauge_exists` | `layer02_internal/test_metrics.py` | - | Gauge with pool label | Pool DLQ gauge. Pass: has pool label. |
| `test_update_pool_queue_depth_sets_gauge` | `layer02_internal/test_metrics.py` | Pool depths | Correct values | Pool depth updated. Pass: values match. |
| `test_update_pool_dlq_depth_sets_gauge` | `layer02_internal/test_metrics.py` | Pool DLQ depths | Correct values | Pool DLQ updated. Pass: values match. |
| `test_update_all_pool_queue_metrics` | `layer02_internal/test_metrics.py` | List of pool stats | All pools updated | All pools updated. Pass: all values correct. |
| `test_validation_total_counter_exists` | `layer02_internal/test_metrics.py` | - | Counter with pool, result labels | Validation counter. Pass: has labels. |
| `test_validation_failures_counter_exists` | `layer02_internal/test_metrics.py` | - | Counter with pool, reason labels | Validation failures. Pass: has labels. |
| `test_auth_failures_counter_exists` | `layer02_internal/test_metrics.py` | - | Counter with pool, scan_type labels | Auth failures. Pass: has labels. |
| `test_record_validation_result_success` | `layer02_internal/test_metrics.py` | `is_valid=True` | success counter +1 | Validation success. Pass: counter increases. |
| `test_record_validation_result_failure` | `layer02_internal/test_metrics.py` | `is_valid=False` | failed counter +1 | Validation failure. Pass: counter increases. |
| `test_record_validation_failure_reason` | `layer02_internal/test_metrics.py` | `reason="auth_failed"` | Reason counter +1 | Failure reason. Pass: correct label incremented. |
| `test_record_validation_failure_different_reasons` | `layer02_internal/test_metrics.py` | 5 different reasons | Each reason tracked | Multiple reasons. Pass: all reasons tracked. |
| `test_record_auth_failure` | `layer02_internal/test_metrics.py` | `scan_type="trusted_basic"` | Counter +1 | Auth failure. Pass: counter increases. |
| `test_record_auth_failure_different_scan_types` | `layer02_internal/test_metrics.py` | Different scan types | Each type tracked | Scan type isolation. Pass: each tracked. |
| `test_scanner_active_scans_gauge_exists` | `layer02_internal/test_metrics.py` | - | Gauge with scanner_instance label | Scanner active. Pass: has label. |
| `test_scanner_capacity_gauge_exists` | `layer02_internal/test_metrics.py` | - | Gauge with scanner_instance label | Scanner capacity. Pass: has label. |
| `test_scanner_utilization_gauge_exists` | `layer02_internal/test_metrics.py` | - | Gauge with scanner_instance label | Utilization gauge. Pass: has label. |
| `test_update_scanner_metrics` | `layer02_internal/test_metrics.py` | active=3, capacity=10 | All gauges set, utilization=30% | Scanner metrics. Pass: correct values. |
| `test_update_scanner_metrics_full_capacity` | `layer02_internal/test_metrics.py` | active=5, capacity=5 | utilization=100% | Full capacity. Pass: 100%. |
| `test_update_scanner_metrics_zero_capacity` | `layer02_internal/test_metrics.py` | active=0, capacity=0 | utilization=0% | Zero capacity. Pass: 0% (no divide by zero). |
| `test_update_all_scanner_metrics` | `layer02_internal/test_metrics.py` | List of scanner stats | All scanners updated | All scanners. Pass: all values correct. |
| `test_metrics_response_contains_phase4_metrics` | `layer02_internal/test_metrics.py` | - | Contains Phase 4 metric names | Phase 4 metrics. Pass: all new metrics present. |

### test_nessus_validator.py (18 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_file_not_found` | `layer02_internal/test_nessus_validator.py` | Non-existent file | `is_valid=False`, error="not found" | File not found. Pass: invalid with error. |
| `test_empty_file` | `layer02_internal/test_nessus_validator.py` | Empty file | `is_valid=False`, error="too small" | Empty file. Pass: invalid, file_size_bytes=0. |
| `test_invalid_xml` | `layer02_internal/test_nessus_validator.py` | Invalid XML content | `is_valid=False`, error="Invalid XML" | Invalid XML. Pass: invalid with XML error. |
| `test_no_hosts` | `layer02_internal/test_nessus_validator.py` | XML with no hosts | `is_valid=False`, error="No hosts" | No hosts. Pass: invalid with no hosts error. |
| `test_untrusted_scan_success` | `layer02_internal/test_nessus_validator.py` | Valid untrusted scan XML | `is_valid=True`, auth_status="not_applicable" | Untrusted success. Pass: valid, not_applicable auth. |
| `test_untrusted_scan_severity_counts` | `layer02_internal/test_nessus_validator.py` | Untrusted scan XML | `severity_counts: {critical: 0, high: 0, medium: 1, low: 1, info: 2}` | Severity counts. Pass: correct counts. |
| `test_trusted_scan_auth_success` | `layer02_internal/test_nessus_validator.py` | Trusted scan with "Credentialed checks : yes" | `is_valid=True`, auth_status="success" | Trusted auth success. Pass: valid, auth=success. |
| `test_trusted_scan_auth_failed` | `layer02_internal/test_nessus_validator.py` | Trusted scan with "Credentialed checks : no" | `is_valid=False`, auth_status="failed" | Trusted auth failed. Pass: invalid, auth=failed. |
| `test_trusted_scan_auth_partial` | `layer02_internal/test_nessus_validator.py` | Trusted scan with "Credentialed checks : partial" | `is_valid=True`, auth_status="partial" | Partial auth. Pass: valid with warning, auth=partial. |
| `test_trusted_privileged_scan_failed` | `layer02_internal/test_nessus_validator.py` | Privileged scan with failed auth | `is_valid=False`, auth_status="failed" | Privileged auth failed. Pass: invalid, error mentions trusted_privileged. |
| `test_severity_counts_trusted` | `layer02_internal/test_nessus_validator.py` | Trusted scan with vulns | Correct severity counts | Trusted severity. Pass: correct counts by severity. |
| `test_host_count` | `layer02_internal/test_nessus_validator.py` | Multi-host XML | `hosts_scanned: 3` | Host count. Pass: correct count. |
| `test_expected_hosts_warning` | `layer02_internal/test_nessus_validator.py` | 3 hosts, expected 5 | `is_valid=True`, warning="less than expected" | Expected hosts warning. Pass: valid with warning. |
| `test_expected_hosts_met` | `layer02_internal/test_nessus_validator.py` | 3 hosts, expected 3 | `is_valid=True`, no warnings | Expected hosts met. Pass: no warnings. |
| `test_auth_inferred_from_plugins` | `layer02_internal/test_nessus_validator.py` | No plugin 19506, but 5+ auth plugins | `is_valid=True`, auth_status="success" | Auth inferred. Pass: auth=success from plugin count. |
| `test_convenience_function` | `layer02_internal/test_nessus_validator.py` | `validate_scan_results(file, scan_type)` | `ValidationResult` | Convenience function. Pass: returns ValidationResult. |
| `test_default_values` | `layer02_internal/test_nessus_validator.py` | `ValidationResult(is_valid=True)` | Defaults: error=None, warnings=[], stats={}, auth="unknown" | Default values. Pass: all defaults correct. |
| `test_with_values` | `layer02_internal/test_nessus_validator.py` | ValidationResult with all fields | All fields set | With values. Pass: all fields match inputs. |

### test_pool_registry.py (20 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_list_pools` | `layer02_internal/test_pool_registry.py` | Registry with 2 pools | `["nessus", "nessus_dmz"]` | List pools. Pass: both pools listed. |
| `test_get_default_pool` | `layer02_internal/test_pool_registry.py` | Registry | `"nessus"` | Default pool. Pass: returns "nessus". |
| `test_get_scanner_count_all` | `layer02_internal/test_pool_registry.py` | Registry with 3 scanners | `3` | Total count. Pass: 3 scanners. |
| `test_get_scanner_count_by_pool` | `layer02_internal/test_pool_registry.py` | By pool | nessus=2, dmz=1 | Count by pool. Pass: correct per-pool counts. |
| `test_list_instances_all` | `layer02_internal/test_pool_registry.py` | Registry | 3 instances with pool info | All instances. Pass: 3 instances, pools included. |
| `test_list_instances_by_pool` | `layer02_internal/test_pool_registry.py` | By pool | Pool-specific instances | By pool. Pass: only that pool's scanners. |
| `test_get_instance_by_pool` | `layer02_internal/test_pool_registry.py` | `pool="nessus"`, `instance_id="scanner1"` | Scanner instance | Get specific. Pass: returns scanner. |
| `test_get_instance_not_found` | `layer02_internal/test_pool_registry.py` | Non-existent instance | `ValueError("Scanner not found")` | Not found. Pass: raises ValueError. |
| `test_get_available_scanner_from_pool` | `layer02_internal/test_pool_registry.py` | `pool="nessus"` | Scanner + key starting with "nessus:" | Available scanner. Pass: returns scanner with correct key. |
| `test_get_available_scanner_from_empty_pool` | `layer02_internal/test_pool_registry.py` | Non-existent pool | `ValueError("No enabled scanners")` | Empty pool. Pass: raises ValueError. |
| `test_get_pool_status` | `layer02_internal/test_pool_registry.py` | `pool="nessus"` | Status dict with capacity info | Pool status. Pass: has pool, total_scanners, total_capacity, utilization. |
| `test_get_pool_status_dmz` | `layer02_internal/test_pool_registry.py` | `pool="nessus_dmz"` | DMZ pool status | DMZ status. Pass: correct values for DMZ. |
| `test_least_loaded_selection` | `layer02_internal/test_pool_registry.py` | Scanner1 load=3, Scanner2 load=1 | Scanner2 selected | Least loaded. Pass: selects scanner2. |
| `test_acquire_increments_active_scans` | `layer02_internal/test_pool_registry.py` | Acquire scanner | active_scans +1 | Acquire increments. Pass: count increases. |
| `test_release_decrements_active_scans` | `layer02_internal/test_pool_registry.py` | Release scanner | active_scans -1 | Release decrements. Pass: count decreases. |
| `test_acquire_specific_instance` | `layer02_internal/test_pool_registry.py` | Specific instance_id | That scanner returned | Specific acquire. Pass: returns requested scanner. |
| `test_get_scanner_load` | `layer02_internal/test_pool_registry.py` | Scanner with load | Load info dict | Get load. Pass: has active_scans, max, utilization_pct, available_capacity. |
| `test_pools_are_isolated` | `layer02_internal/test_pool_registry.py` | Multiple pools | Each pool has own scanners | Pool isolation. Pass: no key overlap. |
| `test_pool_status_independent` | `layer02_internal/test_pool_registry.py` | Load on one pool | Only that pool shows load | Status independent. Pass: other pools unaffected. |
| `test_acquire_respects_pool` | `layer02_internal/test_pool_registry.py` | Acquire from specific pool | Key starts with that pool | Respects pool. Pass: key prefix matches pool. |

### test_queue.py (18 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_queue_key_generation` | `layer02_internal/test_queue.py` | Various pools | `"nessus:queue"`, `"nessus_dmz:queue"` | Key generation. Pass: correct format. |
| `test_dlq_key_generation` | `layer02_internal/test_queue.py` | Various pools | `"nessus:queue:dead"`, etc. | DLQ key generation. Pass: correct format. |
| `test_enqueue_to_default_pool` | `layer02_internal/test_queue.py` | Task without pool | Uses "nessus:queue" | Default pool. Pass: correct key used. |
| `test_enqueue_to_specific_pool` | `layer02_internal/test_queue.py` | `pool="nessus_dmz"` | Uses "nessus_dmz:queue" | Specific pool. Pass: correct key. |
| `test_enqueue_uses_task_scanner_pool` | `layer02_internal/test_queue.py` | Task with scanner_pool="nessus_lan" | Uses "nessus_lan:queue" | Task pool used. Pass: scanner_pool respected. |
| `test_enqueue_pool_param_takes_precedence` | `layer02_internal/test_queue.py` | Task with scanner_pool, explicit pool param | Uses pool param | Param precedence. Pass: param overrides task. |
| `test_dequeue_from_default_pool` | `layer02_internal/test_queue.py` | Default pool | Dequeues from "nessus:queue" | Default dequeue. Pass: correct key. |
| `test_dequeue_from_specific_pool` | `layer02_internal/test_queue.py` | `pool="nessus_dmz"` | Dequeues from "nessus_dmz:queue" | Specific dequeue. Pass: correct key. |
| `test_dequeue_any_from_multiple_pools` | `layer02_internal/test_queue.py` | `["nessus", "nessus_dmz", "nessus_lan"]` | Task from any pool | Dequeue any. Pass: all keys in brpop call. |
| `test_dequeue_any_timeout` | `layer02_internal/test_queue.py` | No tasks | `None` | Dequeue timeout. Pass: returns None. |
| `test_get_queue_depth_for_pool` | `layer02_internal/test_queue.py` | `pool="nessus_dmz"` | Depth from that pool | Pool depth. Pass: correct key used. |
| `test_get_dlq_size_for_pool` | `layer02_internal/test_queue.py` | `pool="nuclei"` | DLQ size for pool | Pool DLQ size. Pass: correct key. |
| `test_move_to_dlq_uses_pool` | `layer02_internal/test_queue.py` | Task with scanner_pool | Uses pool-specific DLQ | Move to DLQ. Pass: correct key. |
| `test_peek_from_specific_pool` | `layer02_internal/test_queue.py` | `pool="nessus_lan"` | Tasks from that pool | Peek pool. Pass: correct key. |
| `test_clear_dlq_for_pool` | `layer02_internal/test_queue.py` | `pool="nessus_dmz"` | Clears that pool's DLQ | Clear DLQ. Pass: correct key. |
| `test_get_queue_stats_default_pool` | `layer02_internal/test_queue.py` | Default pool | Stats with pool="nessus" | Default stats. Pass: pool in stats. |
| `test_get_queue_stats_specific_pool` | `layer02_internal/test_queue.py` | `pool="nessus_dmz"` | Stats for that pool | Specific stats. Pass: pool matches. |
| `test_get_all_pool_stats` | `layer02_internal/test_queue.py` | 3 pools with different depths | Aggregated stats | All pool stats. Pass: totals correct. |

### test_queue_status.py (16 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_get_queue_stats_default_pool` | `layer02_internal/test_queue_status.py` | Mock queue | Stats with pool, depth, dlq, tasks | Default stats. Pass: all fields present. |
| `test_get_queue_stats_specific_pool` | `layer02_internal/test_queue_status.py` | `pool="nessus_dmz"` | Stats for that pool | Specific pool. Pass: correct pool in response. |
| `test_get_queue_stats_empty_queue` | `layer02_internal/test_queue_status.py` | Empty queue | `queue_depth: 0`, `next_tasks: []` | Empty queue. Pass: zeros and empty list. |
| `test_get_queue_stats_timestamp_format` | `layer02_internal/test_queue_status.py` | Any queue | ISO format timestamp | Timestamp format. Pass: parseable as datetime. |
| `test_nessus_pool_stats` | `layer02_internal/test_queue_status.py` | Mock with nessus data | Nessus-specific stats | Nessus stats. Pass: correct values. |
| `test_dmz_pool_stats` | `layer02_internal/test_queue_status.py` | Mock with dmz data | DMZ-specific stats | DMZ stats. Pass: correct values. |
| `test_empty_pool_stats` | `layer02_internal/test_queue_status.py` | Empty nuclei pool | Zero stats | Empty pool. Pass: zeros. |
| `test_response_contains_all_required_fields` | `layer02_internal/test_queue_status.py` | Any queue | Has pool, queue_depth, dlq_size, next_tasks, timestamp | Required fields. Pass: all present. |
| `test_response_types_are_correct` | `layer02_internal/test_queue_status.py` | Any queue | Correct types for each field | Correct types. Pass: str, int, list types. |
| `test_next_tasks_limited_to_three` | `layer02_internal/test_queue_status.py` | Queue with many tasks | peek called with count=3 | Limited preview. Pass: count=3 in call. |
| `test_queue_depth_zero` | `layer02_internal/test_queue_status.py` | Empty queue | `queue_depth: 0` | Zero depth. Pass: 0. |
| `test_queue_depth_positive` | `layer02_internal/test_queue_status.py` | Queue with 42 tasks | `queue_depth: 42` | Positive depth. Pass: 42. |
| `test_queue_depth_large_number` | `layer02_internal/test_queue_status.py` | Queue with 10000 tasks | `queue_depth: 10000` | Large depth. Pass: 10000. |
| `test_dlq_size_zero` | `layer02_internal/test_queue_status.py` | Empty DLQ | `dlq_size: 0` | Zero DLQ. Pass: 0. |
| `test_dlq_size_positive` | `layer02_internal/test_queue_status.py` | DLQ with 5 tasks | `dlq_size: 5` | Positive DLQ. Pass: 5. |
| `test_dlq_independent_of_queue` | `layer02_internal/test_queue_status.py` | Queue=10, DLQ=3 | Both values independent | Independent values. Pass: both correct. |

### test_task_manager.py (16 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_create_and_get_task` | `layer02_internal/test_task_manager.py` | Sample task | Same task retrieved | Create/get. Pass: all fields match. |
| `test_get_nonexistent_task` | `layer02_internal/test_task_manager.py` | Non-existent ID | `None` | Get missing. Pass: returns None. |
| `test_update_status_valid_transition` | `layer02_internal/test_task_manager.py` | QUEUED → RUNNING | Status updated, started_at set | Valid transition. Pass: status="running", started_at not None. |
| `test_update_status_invalid_transition` | `layer02_internal/test_task_manager.py` | QUEUED → COMPLETED | `StateTransitionError` | Invalid transition. Pass: raises error. |
| `test_task_with_validation_fields` | `layer02_internal/test_task_manager.py` | Task with validation_stats, warnings, auth_status | All fields stored | Validation fields. Pass: all fields retrievable. |
| `test_mark_completed_with_validation_success` | `layer02_internal/test_task_manager.py` | Running task + validation data | Status=completed, validation data stored | Completed with validation. Pass: all fields set. |
| `test_mark_completed_with_partial_auth` | `layer02_internal/test_task_manager.py` | Partial auth status | auth_status="partial", 2 warnings | Partial auth. Pass: auth and warnings correct. |
| `test_mark_failed_with_validation` | `layer02_internal/test_task_manager.py` | Failure with validation context | Status=failed, error and auth data | Failed with validation. Pass: all fields set. |
| `test_mark_completed_without_validation` | `layer02_internal/test_task_manager.py` | No validation data | Status=completed, validation fields None | Without validation. Pass: None for validation fields. |
| `test_backward_compatibility_no_validation_fields` | `layer02_internal/test_task_manager.py` | Old task without validation | Validation fields are None | Backward compat. Pass: None for new fields. |
| `test_untrusted_scan_not_applicable_auth` | `layer02_internal/test_task_manager.py` | Untrusted scan completed | auth_status="not_applicable" | Untrusted auth. Pass: not_applicable. |
| `test_trusted_scan_success_auth` | `layer02_internal/test_task_manager.py` | Trusted scan with auth success | auth_status="success", auth_plugins_found | Trusted success. Pass: correct auth status. |
| `test_trusted_scan_failed_auth` | `layer02_internal/test_task_manager.py` | Trusted scan with auth failure | Status=failed, auth_status="failed", error message | Trusted failure. Pass: failed with error. |
| `test_generate_task_id_format` | `layer02_internal/test_task_manager.py` | `scanner_type="nessus"`, `instance="scanner1"` | Format: `ne_scan_YYYYMMDD_HHMMSS_hexrandom` | ID format. Pass: 5 parts, correct prefixes. |
| `test_generate_task_id_unique` | `layer02_internal/test_task_manager.py` | Generate 100 IDs | All unique | Unique IDs. Pass: 100 unique values. |
| `test_generate_task_id_different_scanner_types` | `layer02_internal/test_task_manager.py` | nessus vs qualys | Different prefixes (ne vs qu) | Type prefixes. Pass: different first parts. |

---

## Layer 03: External Basic (79 tests)

Integration tests using real external systems (MCP server, Redis) but with simple operations.

### test_mcp_tools_basic.py (19 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_client_connects_successfully` | `layer03_external_basic/test_mcp_tools_basic.py` | MCP_SERVER_URL | `client.is_connected() == True` | Client connects. Pass: connected. |
| `test_client_ping` | `layer03_external_basic/test_mcp_tools_basic.py` | Client | `True` | Ping works. Pass: returns True. |
| `test_client_list_tools` | `layer03_external_basic/test_mcp_tools_basic.py` | Client | 6+ tools including run_untrusted_scan, get_scan_status | List tools. Pass: required tools present. |
| `test_submit_scan_basic` | `layer03_external_basic/test_mcp_tools_basic.py` | `targets="192.168.1.1"`, `scan_name="Test"` | `{"task_id": ..., "status": "queued"}` | Basic submission. Pass: has task_id, status=queued. |
| `test_submit_scan_with_description` | `layer03_external_basic/test_mcp_tools_basic.py` | With description | Task queued, description stored | With description. Pass: task created. |
| `test_idempotency` | `layer03_external_basic/test_mcp_tools_basic.py` | Same idempotency_key twice | Same task_id both times | Idempotency. Pass: task_id1 == task_id2. |
| `test_get_status` | `layer03_external_basic/test_mcp_tools_basic.py` | Valid task_id | Status dict with task_id, status | Get status. Pass: has required fields. |
| `test_list_tasks` | `layer03_external_basic/test_mcp_tools_basic.py` | `limit=10` | `{"tasks": [...], "total": int}` | List tasks. Pass: has tasks array, total. |
| `test_list_tasks_with_filter` | `layer03_external_basic/test_mcp_tools_basic.py` | `status="queued"` | Only queued tasks | Filter works. Pass: all tasks have status=queued. |
| `test_get_queue_status` | `layer03_external_basic/test_mcp_tools_basic.py` | - | `{"queue_depth": int, "dlq_size": int}` | Queue status. Pass: has depth info. |
| `test_list_scanners` | `layer03_external_basic/test_mcp_tools_basic.py` | - | `{"scanners": [...]}` | List scanners. Pass: has scanners array. |
| `test_invalid_task_id` | `layer03_external_basic/test_mcp_tools_basic.py` | `"invalid-task-id-12345"` | Error response | Invalid ID. Pass: has error or None status. |
| `test_timeout_error` | `layer03_external_basic/test_mcp_tools_basic.py` | Very small timeout | Exception raised | Timeout handling. Pass: raises exception. |
| `test_progress_callback_called` | `layer03_external_basic/test_mcp_tools_basic.py` | With callback | Callback invoked at least once | Progress callback. Pass: callback_invoked > 0. |
| `test_get_results_basic` | `layer03_external_basic/test_mcp_tools_basic.py` | `task_id`, `schema_profile="minimal"` | JSON-NL string with ≥3 lines | Get results basic. Pass: schema + metadata + pagination. |
| `test_get_critical_vulnerabilities` | `layer03_external_basic/test_mcp_tools_basic.py` | `task_id` | List of vulns with severity="4" | Get critical vulns. Pass: all severity=4. |
| `test_get_vulnerability_summary` | `layer03_external_basic/test_mcp_tools_basic.py` | `task_id` | Dict with severity counts | Get vuln summary. Pass: has severity keys. |
| `test_wait_for_completion` | `layer03_external_basic/test_mcp_tools_basic.py` | `task_id`, `timeout=600` | Final status dict | Wait for completion. Pass: status in [completed, failed]. |
| `test_scan_and_wait` | `layer03_external_basic/test_mcp_tools_basic.py` | `targets`, `scan_name` | Final status dict | Scan and wait. Pass: status in [completed, failed], has task_id. |

### test_pool_operations.py (17 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_list_pools_returns_pools` | `layer03_external_basic/test_pool_operations.py` | - | `{"pools": [list]}` | Returns pools. Pass: pools is non-empty list. |
| `test_list_pools_includes_default` | `layer03_external_basic/test_pool_operations.py` | - | `{"default_pool": str}` | Has default. Pass: default_pool in pools list. |
| `test_list_pools_contains_nessus` | `layer03_external_basic/test_pool_operations.py` | - | "nessus" in pools | Has nessus. Pass: nessus in list. |
| `test_list_pools_response_format` | `layer03_external_basic/test_pool_operations.py` | - | Only pools and default_pool keys | Correct format. Pass: exactly expected keys. |
| `test_get_pool_status_default` | `layer03_external_basic/test_pool_operations.py` | No pool specified | Status with pool, total_scanners | Default status. Pass: has required fields. |
| `test_get_pool_status_specific_pool` | `layer03_external_basic/test_pool_operations.py` | `scanner_pool="nessus"` | `pool == "nessus"` | Specific pool. Pass: correct pool returned. |
| `test_get_pool_status_includes_scanners_list` | `layer03_external_basic/test_pool_operations.py` | - | `scanners: [list]` | Has scanners list. Pass: scanners is list. |
| `test_get_pool_status_scanner_details` | `layer03_external_basic/test_pool_operations.py` | - | Scanner has instance_key, active_scans, max_concurrent | Scanner details. Pass: all fields present. |
| `test_get_pool_status_capacity_metrics` | `layer03_external_basic/test_pool_operations.py` | - | Has total_scanners, total_capacity, total_active, available_capacity | Capacity metrics. Pass: all ints present. |
| `test_get_pool_status_utilization` | `layer03_external_basic/test_pool_operations.py` | - | `utilization_pct: 0-100` | Utilization. Pass: float 0-100. |
| `test_get_pool_status_capacity_math` | `layer03_external_basic/test_pool_operations.py` | - | `available_capacity == total_capacity - total_active` | Math correct. Pass: equation holds. |
| `test_get_pool_status_scanner_type` | `layer03_external_basic/test_pool_operations.py` | - | `scanner_type: "nessus"` | Scanner type. Pass: correct type. |
| `test_list_pools_then_get_status` | `layer03_external_basic/test_pool_operations.py` | For each pool | Status for each pool | All pools have status. Pass: all succeed. |
| `test_default_pool_matches_list` | `layer03_external_basic/test_pool_operations.py` | - | Default pool status matches default | Default matches. Pass: pool names match. |
| `test_pool_scanner_count_consistency` | `layer03_external_basic/test_pool_operations.py` | - | `total_scanners == len(scanners)` | Count consistent. Pass: counts match. |
| `test_empty_pool_status` | `layer03_external_basic/test_pool_operations.py` | Possibly empty pool | Valid structure | Empty handled. Pass: total_scanners >= 0. |
| `test_pool_utilization_when_idle` | `layer03_external_basic/test_pool_operations.py` | No active scans | `utilization_pct == 0`, available == total | Idle utilization. Pass: 0% util, full capacity. |

### test_pool_selection.py (15 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_enqueue_to_multiple_pools` | `layer03_external_basic/test_pool_selection.py` | Tasks to 3 pools | Each pool has 1 task | Multiple pools. Pass: correct depths. |
| `test_dequeue_from_specific_pool` | `layer03_external_basic/test_pool_selection.py` | Dequeue from nessus only | Only nessus task returned | Specific dequeue. Pass: correct task, others remain. |
| `test_dequeue_any_fifo_order` | `layer03_external_basic/test_pool_selection.py` | 5 tasks to same pool | Returned in order | FIFO order. Pass: task-0 through task-4 in order. |
| `test_dequeue_any_across_pools` | `layer03_external_basic/test_pool_selection.py` | Task in dmz only, dequeue from [nessus, dmz] | DMZ task returned | Cross-pool dequeue. Pass: returns dmz task. |
| `test_pool_isolation` | `layer03_external_basic/test_pool_selection.py` | Task in dmz, dequeue from nessus | `None` | Pool isolation. Pass: None, dmz task remains. |
| `test_move_to_dlq_per_pool` | `layer03_external_basic/test_pool_selection.py` | Tasks to different DLQs | Each pool DLQ has 1 | Per-pool DLQ. Pass: correct DLQ sizes. |
| `test_clear_dlq_per_pool` | `layer03_external_basic/test_pool_selection.py` | Clear one pool's DLQ | Only that DLQ cleared | Per-pool clear. Pass: one cleared, other unchanged. |
| `test_peek_per_pool` | `layer03_external_basic/test_pool_selection.py` | Tasks in different pools | Peek returns correct task | Per-pool peek. Pass: correct task per pool. |
| `test_get_queue_stats_per_pool` | `layer03_external_basic/test_pool_selection.py` | Different depths per pool | Correct stats per pool | Per-pool stats. Pass: pool in stats, correct depth. |
| `test_get_all_pool_stats` | `layer03_external_basic/test_pool_selection.py` | 3 pools with tasks | Aggregated totals | All pool stats. Pass: totals correct. |
| `test_worker_consumes_from_specified_pools` | `layer03_external_basic/test_pool_selection.py` | Tasks in 3 pools, consume from 2 | Third pool unchanged | Worker pool filtering. Pass: lan task remains. |
| `test_worker_round_robin_consumption` | `layer03_external_basic/test_pool_selection.py` | 3 tasks each in 2 pools | All 6 consumed | Round robin. Pass: 6 consumed, 3 from each. |
| `test_default_pool_behavior` | `layer03_external_basic/test_pool_selection.py` | Enqueue without pool | Goes to default (nessus) | Default behavior. Pass: in nessus queue. |
| `test_dequeue_without_pool` | `layer03_external_basic/test_pool_selection.py` | Dequeue without pool | From default pool | Default dequeue. Pass: returns from nessus. |
| `test_scanner_pool_in_task_data` | `layer03_external_basic/test_pool_selection.py` | Task with scanner_pool field | Uses that pool | Task pool respected. Pass: in specified pool. |

### test_scanner_operations.py (3 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_nessus_authentication` | `layer03_external_basic/test_scanner_operations.py` | Scanner creds | `_session_token is not None` | Auth works. Pass: token set. |
| `test_nessus_create_and_launch` | `layer03_external_basic/test_scanner_operations.py` | Create, launch, check, stop, delete | `scan_id > 0`, uuid, status in [queued, running] | Full lifecycle. Pass: all steps succeed. |
| `test_nessus_status_mapping` | `layer03_external_basic/test_scanner_operations.py` | Various Nessus statuses | Correct mapped statuses | Status mapping. Pass: pending→queued, running→running, completed→completed, etc. |

### test_schema_parsing.py (25 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_parse_nessus_file` | `layer03_external_basic/test_schema_parsing.py` | Real .nessus file | `{"scan_metadata": {...}, "vulnerabilities": [...]}` | Parse file. Pass: has metadata and vulns. |
| `test_parser_handles_cve_lists` | `layer03_external_basic/test_schema_parsing.py` | XML with 2 CVEs | `cve: ["CVE-2021-1234", "CVE-2021-5678"]` | Multiple CVEs. Pass: list with both. |
| `test_schema_profiles_exist` | `layer03_external_basic/test_schema_parsing.py` | - | minimal, summary, brief, full exist | Profiles exist. Pass: all in SCHEMAS. |
| `test_minimal_schema_fields` | `layer03_external_basic/test_schema_parsing.py` | `get_schema_fields("minimal")` | 6 fields: host, plugin_id, severity, cve, cvss_score, exploit_available | Minimal fields. Pass: exactly 6 fields. |
| `test_full_schema_returns_none` | `layer03_external_basic/test_schema_parsing.py` | `get_schema_fields("full")` | `None` | Full returns None. Pass: None (all fields). |
| `test_invalid_profile_raises_error` | `layer03_external_basic/test_schema_parsing.py` | `get_schema_fields("invalid")` | `ValueError("Invalid schema profile")` | Invalid profile. Pass: raises ValueError. |
| `test_custom_fields_with_default_profile` | `layer03_external_basic/test_schema_parsing.py` | `custom_fields=["host", "severity"]` | `["host", "severity"]` | Custom fields. Pass: returns custom list. |
| `test_mutual_exclusivity` | `layer03_external_basic/test_schema_parsing.py` | Non-default profile + custom_fields | `ValueError("Cannot specify both")` | Mutual exclusivity. Pass: raises ValueError. |
| `test_string_filter_substring` | `layer03_external_basic/test_schema_parsing.py` | Filter by plugin_name="Apache" | Only Apache results | Substring filter. Pass: only matching. |
| `test_string_filter_case_insensitive` | `layer03_external_basic/test_schema_parsing.py` | Filter by "apache" (lowercase) | Matches "Apache" | Case insensitive. Pass: matches. |
| `test_number_filter_greater_than` | `layer03_external_basic/test_schema_parsing.py` | `cvss_score: ">7.0"` | Only > 7.0 | Greater than. Pass: all > 7.0. |
| `test_number_filter_greater_equal` | `layer03_external_basic/test_schema_parsing.py` | `cvss_score: ">=7.0"` | Only >= 7.0 | Greater equal. Pass: all >= 7.0. |
| `test_boolean_filter` | `layer03_external_basic/test_schema_parsing.py` | `exploit_available: True` | Only True | Boolean filter. Pass: only True values. |
| `test_list_filter` | `layer03_external_basic/test_schema_parsing.py` | `cve: "CVE-2021"` | Contains matching CVE | List filter. Pass: CVE in list. |
| `test_multiple_filters_and_logic` | `layer03_external_basic/test_schema_parsing.py` | `severity: "4", cvss_score: ">7.0"` | Matches both | AND logic. Pass: both conditions. |
| `test_compare_number_operators` | `layer03_external_basic/test_schema_parsing.py` | All operators | Correct boolean results | All operators work. Pass: >, >=, <, <=, = all correct. |
| `test_converter_basic` | `layer03_external_basic/test_schema_parsing.py` | Sample XML, brief profile | JSON-NL with schema, metadata, vulns, pagination | Basic convert. Pass: all line types present. |
| `test_converter_minimal_schema` | `layer03_external_basic/test_schema_parsing.py` | minimal profile | Only minimal fields | Minimal schema. Pass: limited fields. |
| `test_converter_custom_fields` | `layer03_external_basic/test_schema_parsing.py` | Custom fields list | Profile="custom", fields match | Custom fields. Pass: custom in schema. |
| `test_converter_with_filters` | `layer03_external_basic/test_schema_parsing.py` | `filters={"severity": "4"}` | Only severity 4, filters in schema | Filtering. Pass: only matching, filters_applied set. |
| `test_converter_pagination` | `layer03_external_basic/test_schema_parsing.py` | `page=1, page_size=1` (clamped to 10) | Correct pagination info | Pagination. Pass: page_size clamped, has_next calculated. |
| `test_converter_page_zero_returns_all` | `layer03_external_basic/test_schema_parsing.py` | `page=0` | All data, no pagination line | All data. Pass: 4 lines (no pagination). |
| `test_end_to_end_with_real_scan` | `layer03_external_basic/test_schema_parsing.py` | Real .nessus, severity filter | Filtered results | E2E with filter. Pass: only severity 4, correct format. |
| `test_real_scan_pagination_multi_page` | `layer03_external_basic/test_schema_parsing.py` | Real data, page_size=10 | 4 pages, correct navigation | Multi-page. Pass: 4 pages, has_next correct. |
| `test_real_scan_filters_with_pagination` | `layer03_external_basic/test_schema_parsing.py` | Severity filter + pagination | 11 critical, 2 pages | Filter + pagination. Pass: correct counts. |

---

## Layer 04: Full Workflow (42 tests)

End-to-end tests that run complete scan workflows with real Nessus scanners.

### test_authenticated_scan_workflow.py (9 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_create_scan_with_ssh_credentials` | `layer04_full_workflow/test_authenticated_scan_workflow.py` | SSH creds for randy@172.32.0.215 | `scan_id > 0` | Create auth scan. Pass: valid scan_id created. |
| `test_create_scan_with_sudo_credentials` | `layer04_full_workflow/test_authenticated_scan_workflow.py` | Sudo creds for testauth_sudo_pass | `scan_id > 0` | Create sudo scan. Pass: valid scan_id. |
| `test_authenticated_scan_randy` | `layer04_full_workflow/test_authenticated_scan_workflow.py` | Full scan of 172.32.0.215 with randy creds | Completed, results exported | Full auth scan. Pass: completed, results > 1000 bytes. |
| `test_mcp_tool_validation_only` | `layer04_full_workflow/test_authenticated_scan_workflow.py` | Invalid scan_type, missing escalation | Error responses | MCP validation. Pass: correct errors returned. |
| `test_bad_credentials_detected` | `layer04_full_workflow/test_authenticated_scan_workflow.py` | Invalid SSH creds | No Plugin 141118 | Bad creds detected. Pass: no valid creds plugin. |
| `test_privileged_scan_sudo_with_password` | `layer04_full_workflow/test_authenticated_scan_workflow.py` | testauth_sudo_pass@172.30.0.9 | Completed with auth success | Sudo with password. Pass: completed, results valid. |
| `test_privileged_scan_sudo_nopasswd` | `layer04_full_workflow/test_authenticated_scan_workflow.py` | testauth_sudo_nopass@172.30.0.9 | Completed with auth success | Sudo NOPASSWD. Pass: completed, results valid. |
| `test_verify_scan_target_reachable` | `layer04_full_workflow/test_authenticated_scan_workflow.py` | Check 172.30.0.9:22 | Reachable or skip | Target reachable. Pass: port open. |
| `test_verify_external_host_reachable` | `layer04_full_workflow/test_authenticated_scan_workflow.py` | Check 172.32.0.215:22 | Reachable or warning | External reachable. Pass: port open or warning logged. |

### test_complete_scan_with_results.py (1 test)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_complete_scan_workflow_with_export` | `layer04_full_workflow/test_complete_scan_with_results.py` | Create→Launch→Poll→Export→Verify for 172.32.0.215 | Complete results with vulnerabilities | Full workflow. Pass: valid XML, vuln_count > 0, severity counts logged. |

### test_mcp_protocol_e2e.py (18 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_mcp_connection_and_initialization` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | MCP_URL | Session with capabilities | Connection. Pass: session not None, has tools capability. |
| `test_mcp_list_tools` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | - | Required tools present | List tools. Pass: run_untrusted_scan, get_scan_status, etc. present. |
| `test_mcp_list_tasks_e2e` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | `limit=5` | `{"tasks": [...], "total": int}` | List tasks E2E. Pass: has tasks and total. |
| `test_mcp_get_scan_status_e2e` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | Non-existent task_id | Error response | Status E2E. Pass: error for missing task. |
| `test_mcp_list_scanners_e2e` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | - | `{"scanners": [...], "total": int}` | List scanners E2E. Pass: has scanners. |
| `test_mcp_get_queue_status_e2e` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | - | Has queue_depth | Queue status E2E. Pass: has depth info. |
| `test_mcp_invalid_scan_type_error` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | `scan_type="invalid_type_xyz"` | Error with scan_type mention | Invalid type error. Pass: error mentions scan_type. |
| `test_mcp_missing_required_params` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | Missing targets | Error or exception | Missing params. Pass: error response or exception. |
| `test_mcp_run_untrusted_scan_e2e` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | Submit→Poll→Complete | Final status in [completed, failed] | Full untrusted E2E. Pass: terminal state reached. |
| `test_mcp_run_authenticated_scan_e2e` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | Submit auth scan→Poll→Complete | Final status with auth info | Full auth E2E. Pass: completed with validation. |
| `test_queue_position_in_response` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | Submit scan | `queue_position: int` | Queue position. Pass: position in response. |
| `test_queue_position_multiple_submits` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | 3 rapid submissions | Non-decreasing positions | Multiple positions. Pass: positions non-decreasing. |
| `test_unreachable_target_handling` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | 10.255.255.1 (unreachable) | Queued successfully | Unreachable handling. Pass: queued, valid status. |
| `test_invalid_target_format_handling` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | Empty targets | Error or accepted | Invalid format. Pass: handled gracefully. |
| `test_task_status_shows_error_details` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | Failed tasks | Error details in status | Error details. Pass: has error info for failed. |
| `test_scan_with_timeout_target` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | Unreachable target, wait | Eventually completes/fails | Timeout handling. Pass: reaches terminal state. |
| `test_estimated_wait_increases_with_queue_depth` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | 5 rapid submissions | Wait times increase by ~15min each | Wait estimation. Pass: each adds 15min. |
| `test_queue_status_reflects_submissions` | `layer04_full_workflow/test_mcp_protocol_e2e.py` | Submit then check status | Depth >= 0 | Status reflects. Pass: valid depth. |

### test_queue_position_accuracy.py (12 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_queue_position_in_submission_response` | `layer04_full_workflow/test_queue_position_accuracy.py` | Submit scan | `queue_position: int >= 0` | Position in response. Pass: has valid position. |
| `test_queue_position_increments` | `layer04_full_workflow/test_queue_position_accuracy.py` | 3 submissions | Non-negative positions | Positions increment. Pass: all >= 0. |
| `test_queue_status_reflects_submissions` | `layer04_full_workflow/test_queue_position_accuracy.py` | Submit then check | `queue_depth >= 0` | Status reflects. Pass: valid depth. |
| `test_queue_status_has_depth` | `layer04_full_workflow/test_queue_position_accuracy.py` | - | `queue_depth: int >= 0` | Has depth. Pass: int >= 0. |
| `test_queue_status_has_dlq_size` | `layer04_full_workflow/test_queue_position_accuracy.py` | - | `dlq_size: int >= 0` | Has DLQ size. Pass: int >= 0. |
| `test_queue_status_has_next_tasks` | `layer04_full_workflow/test_queue_position_accuracy.py` | - | `next_tasks: list` | Has next tasks. Pass: is list. |
| `test_queue_status_has_timestamp` | `layer04_full_workflow/test_queue_position_accuracy.py` | - | `timestamp: not None` | Has timestamp. Pass: not None. |
| `test_queue_depth_matches_pool_capacity_awareness` | `layer04_full_workflow/test_queue_position_accuracy.py` | Queue and pool status | Both >= 0 | Coherent values. Pass: both non-negative. |
| `test_active_scans_vs_queue_depth` | `layer04_full_workflow/test_queue_position_accuracy.py` | Pool and queue status | Both >= 0 | Both non-negative. Pass: valid values. |
| `test_queue_position_decreases_as_scans_complete` | `layer04_full_workflow/test_queue_position_accuracy.py` | Submit and monitor | Status valid | Position tracking. Pass: status in valid states. |
| `test_multiple_scan_queue_ordering` | `layer04_full_workflow/test_queue_position_accuracy.py` | 2 submissions | Both in list_tasks or completed | Ordering. Pass: all tasks trackable. |
| `test_queue_provides_reasonable_estimates` | `layer04_full_workflow/test_queue_position_accuracy.py` | Queue and pool status | All values reasonable | Reasonable estimates. Pass: valid for estimation. |

### test_untrusted_scan_workflow.py (2 tests)

| Test | File | Arguments | Returns | Description |
|------|------|-----------|---------|-------------|
| `test_complete_e2e_workflow_untrusted_scan` | `layer04_full_workflow/test_untrusted_scan_workflow.py` | Full workflow: connect→submit→poll→results | Completed with vulnerabilities | Full E2E. Pass: all steps succeed, vulns found. |
| `test_e2e_with_result_filtering` | `layer04_full_workflow/test_untrusted_scan_workflow.py` | Full workflow + severity filter + CVSS filter + custom fields | Filtered results | Filter E2E. Pass: filters work, correct results. |

---

## Summary

| Layer | Tests | Purpose |
|-------|-------|---------|
| Layer 01 | 25 | Infrastructure connectivity (Nessus, Redis, targets) |
| Layer 02 | 343 | Unit tests with mocks (internal components) |
| Layer 03 | 79 | Integration tests (MCP tools, pool operations) |
| Layer 04 | 42 | Full E2E workflows (complete scan cycles) |
| **Total** | **489** | |

## Running Tests

```bash
# All tests
pytest tests/ -v

# By layer
pytest tests/layer01_infrastructure/ -v
pytest tests/layer02_internal/ -v
pytest tests/layer03_external_basic/ -v
pytest tests/layer04_full_workflow/ -v

# Skip slow tests
pytest tests/ -v -m "not slow"

# Only integration tests
pytest tests/ -v -m integration
```
