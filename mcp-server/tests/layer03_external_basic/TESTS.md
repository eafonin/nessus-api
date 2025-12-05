# Layer 03: External Basic Tests

[← Test Suite](../README.MD) | [Layer README](README.MD)

---

## Overview

Integration tests using real external systems (MCP server, Redis) with simple operations.

- **Test Count**: 79 tests
- **Duration**: ~1 minute
- **Marker**: `@pytest.mark.layer03`

---

## test_mcp_tools_basic.py (19 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_client_connects_successfully` | MCP_SERVER_URL | `client.is_connected() == True` | Client connects. Pass: connected. |
| `test_client_ping` | Client | `True` | Ping works. Pass: returns True. |
| `test_client_list_tools` | Client | 6+ tools including run_untrusted_scan, get_scan_status | List tools. Pass: required tools present. |
| `test_submit_scan_basic` | `targets="192.168.1.1"`, `scan_name="Test"` | `{"task_id": ..., "status": "queued"}` | Basic submission. Pass: has task_id, status=queued. |
| `test_submit_scan_with_description` | With description | Task queued, description stored | With description. Pass: task created. |
| `test_idempotency` | Same idempotency_key twice | Same task_id both times | Idempotency. Pass: task_id1 == task_id2. |
| `test_get_status` | Valid task_id | Status dict with task_id, status | Get status. Pass: has required fields. |
| `test_list_tasks` | `limit=10` | `{"tasks": [...], "total": int}` | List tasks. Pass: has tasks array, total. |
| `test_list_tasks_with_filter` | `status="queued"` | Only queued tasks | Filter works. Pass: all tasks have status=queued. |
| `test_get_queue_status` | - | `{"queue_depth": int, "dlq_size": int}` | Queue status. Pass: has depth info. |
| `test_list_scanners` | - | `{"scanners": [...]}` | List scanners. Pass: has scanners array. |
| `test_invalid_task_id` | `"invalid-task-id-12345"` | Error response | Invalid ID. Pass: has error or None status. |
| `test_timeout_error` | Very small timeout | Exception raised | Timeout handling. Pass: raises exception. |
| `test_progress_callback_called` | With callback | Callback invoked at least once | Progress callback. Pass: callback_invoked > 0. |
| `test_get_results_basic` | `task_id`, `schema_profile="minimal"` | JSON-NL string with ≥3 lines | Get results basic. Pass: schema + metadata + pagination. |
| `test_get_critical_vulnerabilities` | `task_id` | List of vulns with severity="4" | Get critical vulns. Pass: all severity=4. |
| `test_get_vulnerability_summary` | `task_id` | Dict with severity counts | Get vuln summary. Pass: has severity keys. |
| `test_wait_for_completion` | `task_id`, `timeout=600` | Final status dict | Wait for completion. Pass: status in [completed, failed]. |
| `test_scan_and_wait` | `targets`, `scan_name` | Final status dict | Scan and wait. Pass: status in [completed, failed], has task_id. |

---

## test_pool_operations.py (17 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_list_pools_returns_pools` | - | `{"pools": [list]}` | Returns pools. Pass: pools is non-empty list. |
| `test_list_pools_includes_default` | - | `{"default_pool": str}` | Has default. Pass: default_pool in pools list. |
| `test_list_pools_contains_nessus` | - | "nessus" in pools | Has nessus. Pass: nessus in list. |
| `test_list_pools_response_format` | - | Only pools and default_pool keys | Correct format. Pass: exactly expected keys. |
| `test_get_pool_status_default` | No pool specified | Status with pool, total_scanners | Default status. Pass: has required fields. |
| `test_get_pool_status_specific_pool` | `scanner_pool="nessus"` | `pool == "nessus"` | Specific pool. Pass: correct pool returned. |
| `test_get_pool_status_includes_scanners_list` | - | `scanners: [list]` | Has scanners list. Pass: scanners is list. |
| `test_get_pool_status_scanner_details` | - | Scanner has instance_key, active_scans, max_concurrent | Scanner details. Pass: all fields present. |
| `test_get_pool_status_capacity_metrics` | - | Has total_scanners, total_capacity, total_active, available_capacity | Capacity metrics. Pass: all ints present. |
| `test_get_pool_status_utilization` | - | `utilization_pct: 0-100` | Utilization. Pass: float 0-100. |
| `test_get_pool_status_capacity_math` | - | `available_capacity == total_capacity - total_active` | Math correct. Pass: equation holds. |
| `test_get_pool_status_scanner_type` | - | `scanner_type: "nessus"` | Scanner type. Pass: correct type. |
| `test_list_pools_then_get_status` | For each pool | Status for each pool | All pools have status. Pass: all succeed. |
| `test_default_pool_matches_list` | - | Default pool status matches default | Default matches. Pass: pool names match. |
| `test_pool_scanner_count_consistency` | - | `total_scanners == len(scanners)` | Count consistent. Pass: counts match. |
| `test_empty_pool_status` | Possibly empty pool | Valid structure | Empty handled. Pass: total_scanners >= 0. |
| `test_pool_utilization_when_idle` | No active scans | `utilization_pct == 0`, available == total | Idle utilization. Pass: 0% util, full capacity. |

---

## test_pool_selection.py (15 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_enqueue_to_multiple_pools` | Tasks to 3 pools | Each pool has 1 task | Multiple pools. Pass: correct depths. |
| `test_dequeue_from_specific_pool` | Dequeue from nessus only | Only nessus task returned | Specific dequeue. Pass: correct task, others remain. |
| `test_dequeue_any_fifo_order` | 5 tasks to same pool | Returned in order | FIFO order. Pass: task-0 through task-4 in order. |
| `test_dequeue_any_across_pools` | Task in dmz only, dequeue from [nessus, dmz] | DMZ task returned | Cross-pool dequeue. Pass: returns dmz task. |
| `test_pool_isolation` | Task in dmz, dequeue from nessus | `None` | Pool isolation. Pass: None, dmz task remains. |
| `test_move_to_dlq_per_pool` | Tasks to different DLQs | Each pool DLQ has 1 | Per-pool DLQ. Pass: correct DLQ sizes. |
| `test_clear_dlq_per_pool` | Clear one pool's DLQ | Only that DLQ cleared | Per-pool clear. Pass: one cleared, other unchanged. |
| `test_peek_per_pool` | Tasks in different pools | Peek returns correct task | Per-pool peek. Pass: correct task per pool. |
| `test_get_queue_stats_per_pool` | Different depths per pool | Correct stats per pool | Per-pool stats. Pass: pool in stats, correct depth. |
| `test_get_all_pool_stats` | 3 pools with tasks | Aggregated totals | All pool stats. Pass: totals correct. |
| `test_worker_consumes_from_specified_pools` | Tasks in 3 pools, consume from 2 | Third pool unchanged | Worker pool filtering. Pass: lan task remains. |
| `test_worker_round_robin_consumption` | 3 tasks each in 2 pools | All 6 consumed | Round robin. Pass: 6 consumed, 3 from each. |
| `test_default_pool_behavior` | Enqueue without pool | Goes to default (nessus) | Default behavior. Pass: in nessus queue. |
| `test_dequeue_without_pool` | Dequeue without pool | From default pool | Default dequeue. Pass: returns from nessus. |
| `test_scanner_pool_in_task_data` | Task with scanner_pool field | Uses that pool | Task pool respected. Pass: in specified pool. |

---

## test_scanner_operations.py (3 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_nessus_authentication` | Scanner creds | `_session_token is not None` | Auth works. Pass: token set. |
| `test_nessus_create_and_launch` | Create, launch, check, stop, delete | `scan_id > 0`, uuid, status in [queued, running] | Full lifecycle. Pass: all steps succeed. |
| `test_nessus_status_mapping` | Various Nessus statuses | Correct mapped statuses | Status mapping. Pass: pending→queued, running→running, completed→completed. |

---

## test_schema_parsing.py (25 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_parse_nessus_file` | Real .nessus file | `{"scan_metadata": {...}, "vulnerabilities": [...]}` | Parse file. Pass: has metadata and vulns. |
| `test_parser_handles_cve_lists` | XML with 2 CVEs | `cve: ["CVE-2021-1234", "CVE-2021-5678"]` | Multiple CVEs. Pass: list with both. |
| `test_schema_profiles_exist` | - | minimal, summary, brief, full exist | Profiles exist. Pass: all in SCHEMAS. |
| `test_minimal_schema_fields` | `get_schema_fields("minimal")` | 6 fields: host, plugin_id, severity, cve, cvss_score, exploit_available | Minimal fields. Pass: exactly 6 fields. |
| `test_full_schema_returns_none` | `get_schema_fields("full")` | `None` | Full returns None. Pass: None (all fields). |
| `test_invalid_profile_raises_error` | `get_schema_fields("invalid")` | `ValueError("Invalid schema profile")` | Invalid profile. Pass: raises ValueError. |
| `test_custom_fields_with_default_profile` | `custom_fields=["host", "severity"]` | `["host", "severity"]` | Custom fields. Pass: returns custom list. |
| `test_mutual_exclusivity` | Non-default profile + custom_fields | `ValueError("Cannot specify both")` | Mutual exclusivity. Pass: raises ValueError. |
| `test_string_filter_substring` | Filter by plugin_name="Apache" | Only Apache results | Substring filter. Pass: only matching. |
| `test_string_filter_case_insensitive` | Filter by "apache" (lowercase) | Matches "Apache" | Case insensitive. Pass: matches. |
| `test_number_filter_greater_than` | `cvss_score: ">7.0"` | Only > 7.0 | Greater than. Pass: all > 7.0. |
| `test_number_filter_greater_equal` | `cvss_score: ">=7.0"` | Only >= 7.0 | Greater equal. Pass: all >= 7.0. |
| `test_boolean_filter` | `exploit_available: True` | Only True | Boolean filter. Pass: only True values. |
| `test_list_filter` | `cve: "CVE-2021"` | Contains matching CVE | List filter. Pass: CVE in list. |
| `test_multiple_filters_and_logic` | `severity: "4", cvss_score: ">7.0"` | Matches both | AND logic. Pass: both conditions. |
| `test_compare_number_operators` | All operators | Correct boolean results | All operators work. Pass: >, >=, <, <=, = all correct. |
| `test_converter_basic` | Sample XML, brief profile | JSON-NL with schema, metadata, vulns, pagination | Basic convert. Pass: all line types present. |
| `test_converter_minimal_schema` | minimal profile | Only minimal fields | Minimal schema. Pass: limited fields. |
| `test_converter_custom_fields` | Custom fields list | Profile="custom", fields match | Custom fields. Pass: custom in schema. |
| `test_converter_with_filters` | `filters={"severity": "4"}` | Only severity 4, filters in schema | Filtering. Pass: only matching, filters_applied set. |
| `test_converter_pagination` | `page=1, page_size=1` (clamped to 10) | Correct pagination info | Pagination. Pass: page_size clamped, has_next calculated. |
| `test_converter_page_zero_returns_all` | `page=0` | All data, no pagination line | All data. Pass: 4 lines (no pagination). |
| `test_end_to_end_with_real_scan` | Real .nessus, severity filter | Filtered results | E2E with filter. Pass: only severity 4, correct format. |
| `test_real_scan_pagination_multi_page` | Real data, page_size=10 | 4 pages, correct navigation | Multi-page. Pass: 4 pages, has_next correct. |
| `test_real_scan_filters_with_pagination` | Severity filter + pagination | 11 critical, 2 pages | Filter + pagination. Pass: correct counts. |

---

## See Also

- [Layer 02: Internal Tests](../layer02_internal/TESTS.md)
- [Layer 04: Full Workflow Tests](../layer04_full_workflow/TESTS.md)
- [Testing Guide](../../docs/TESTING.md)
