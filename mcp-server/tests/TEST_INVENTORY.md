# Test Inventory

**Generated**: 2025-12-02
**Total Tests**: 489

This document provides a complete inventory of all tests organized by layer.

---

## Summary by Layer

| Layer | Description | Test Count | Estimated Duration |
|-------|-------------|------------|-------------------|
| Layer 01 | Infrastructure | 25 | <5 seconds |
| Layer 02 | Internal | 343 | ~30 seconds |
| Layer 03 | External Basic | 79 | ~2 minutes |
| Layer 04 | Full Workflow | 42 | 5-10 minutes |
| **Total** | | **489** | |

---

## Layer 01: Infrastructure (25 tests)

Connectivity and access checks for external dependencies.

| File | Test Class | Test Name | Type |
|------|------------|-----------|------|
| test_both_scanners.py | TestBothScannersConnectivity | test_scanner_reachable[Scanner 1] | async |
| test_both_scanners.py | TestBothScannersConnectivity | test_scanner_reachable[Scanner 2] | async |
| test_both_scanners.py | TestBothScannersConnectivity | test_scanner_ready[Scanner 1] | async |
| test_both_scanners.py | TestBothScannersConnectivity | test_scanner_ready[Scanner 2] | async |
| test_both_scanners.py | TestScannersIndependent | test_scanners_have_different_uuids | async |
| test_nessus_connectivity.py | TestNessusConnectivity | test_dns_resolution | sync |
| test_nessus_connectivity.py | TestNessusConnectivity | test_tcp_port_connectivity | sync |
| test_nessus_connectivity.py | TestNessusConnectivity | test_https_reachable | async |
| test_nessus_connectivity.py | TestNessusConnectivity | test_server_status_ready | async |
| test_nessus_connectivity.py | TestNessusSSL | test_ssl_bypass_works | async |
| test_nessus_connectivity.py | TestNessusSSL | test_self_signed_cert_detected | async |
| test_nessus_connectivity.py | TestNessusEndpoints | test_server_status_endpoint | async |
| test_nessus_connectivity.py | TestNessusEndpoints | test_server_properties_endpoint | async |
| test_nessus_connectivity.py | TestNessusEndpoints | test_authentication_endpoint_accessible | async |
| test_nessus_connectivity.py | TestNessusServerProperties | test_server_properties_retrievable | async |
| test_redis_connectivity.py | TestRedisConnectivity | test_dns_resolution | sync |
| test_redis_connectivity.py | TestRedisConnectivity | test_tcp_port_connectivity | sync |
| test_redis_connectivity.py | TestRedisOperations | test_ping | sync |
| test_redis_connectivity.py | TestRedisOperations | test_set_get | sync |
| test_redis_connectivity.py | TestRedisOperations | test_list_operations | sync |
| test_redis_connectivity.py | TestRedisOperations | test_info_command | sync |
| test_target_accounts.py | TestScanTargetReachable | test_scan_target_ssh_port | sync |
| test_target_accounts.py | TestScanTargetReachable | test_external_host_ssh_port | sync |
| test_target_accounts.py | TestTargetAccountsExist | test_scan_target_accepts_connections | sync |
| test_target_accounts.py | TestTargetAccountCredentials | test_credentials_documented | sync |

---

## Layer 02: Internal (343 tests)

Core module unit tests with mocked dependencies.

### test_admin_cli.py (21 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestFormatTimestamp | test_format_timestamp_valid | sync |
| TestFormatTimestamp | test_format_timestamp_invalid | sync |
| TestFormatTimestamp | test_format_timestamp_none | sync |
| TestTruncate | test_truncate_short_string | sync |
| TestTruncate | test_truncate_long_string | sync |
| TestTruncate | test_truncate_empty | sync |
| TestDLQOperations | test_get_dlq_task_found | sync |
| TestDLQOperations | test_get_dlq_task_not_found | sync |
| TestDLQOperations | test_get_dlq_task_empty_dlq | sync |
| TestDLQOperations | test_retry_dlq_task_success | sync |
| TestDLQOperations | test_retry_dlq_task_not_found | sync |
| TestDLQOperations | test_clear_dlq_all | sync |
| TestDLQOperations | test_clear_dlq_before_timestamp | sync |
| TestCLICommands | test_cmd_stats | sync |
| TestCLICommands | test_cmd_list_dlq_empty | sync |
| TestCLICommands | test_cmd_list_dlq_with_tasks | sync |
| TestCLICommands | test_cmd_inspect_dlq_found | sync |
| TestCLICommands | test_cmd_inspect_dlq_not_found | sync |
| TestCLICommands | test_cmd_retry_dlq_success | sync |
| TestCLICommands | test_cmd_retry_dlq_not_found | sync |
| TestCLICommands | test_cmd_purge_dlq_without_confirm | sync |

### test_authenticated_scans.py (18 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestCredentialValidation | test_missing_username_raises | sync |
| TestCredentialValidation | test_missing_password_raises | sync |
| TestCredentialValidation | test_invalid_escalation_method_raises | sync |
| TestCredentialValidation | test_valid_ssh_credentials_pass | sync |
| TestCredentialValidation | test_valid_sudo_credentials_pass | sync |
| TestCredentialValidation | test_all_valid_escalation_methods | sync |
| TestCredentialValidation | test_unsupported_credential_type_raises | sync |
| TestCredentialValidation | test_empty_credentials_pass | sync |
| TestBuildCredentials | test_basic_ssh_password_credentials | sync |
| TestBuildCredentials | test_ssh_sudo_with_password | sync |
| TestBuildCredentials | test_ssh_sudo_with_escalation_account | sync |
| TestBuildCredentials | test_ssh_sudo_nopasswd | sync |
| TestBuildCredentials | test_payload_structure_complete | sync |
| TestBuildCredentials | test_su_escalation | sync |
| TestScanRequest | test_scan_request_with_credentials | sync |
| TestScanRequest | test_scan_request_without_credentials | sync |
| TestScanCreation | test_create_scan_includes_credentials_in_payload | async |
| TestScanCreation | test_create_scan_without_credentials | async |

### test_circuit_breaker.py (27 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestCircuitBreakerStates | test_initial_state_closed | sync |
| TestCircuitBreakerStates | test_allow_request_when_closed | sync |
| TestCircuitBreakerStates | test_record_success_keeps_closed | sync |
| TestCircuitBreakerStates | test_single_failure_stays_closed | sync |
| TestCircuitBreakerStates | test_opens_after_threshold | sync |
| TestCircuitBreakerStates | test_blocks_requests_when_open | sync |
| TestCircuitBreakerStates | test_reset_closes_circuit | sync |
| TestCircuitBreakerHalfOpen | test_transitions_to_half_open | sync |
| TestCircuitBreakerHalfOpen | test_half_open_allows_limited_requests | sync |
| TestCircuitBreakerHalfOpen | test_success_in_half_open_closes | sync |
| TestCircuitBreakerHalfOpen | test_failure_in_half_open_reopens | sync |
| TestCircuitBreakerStatus | test_get_status_closed | sync |
| TestCircuitBreakerStatus | test_get_status_open | sync |
| TestCircuitBreakerRecovery | test_success_resets_failure_count | sync |
| TestCircuitBreakerManager | test_get_creates_breaker | sync |
| TestCircuitBreakerManager | test_get_returns_same_breaker | sync |
| TestCircuitBreakerManager | test_get_different_breakers | sync |
| TestCircuitBreakerManager | test_get_all_status | sync |
| TestCircuitBreakerManager | test_reset_specific | sync |
| TestCircuitBreakerManager | test_reset_nonexistent | sync |
| TestCircuitBreakerManager | test_reset_all | sync |
| TestCircuitBreakerManager | test_custom_defaults | sync |
| TestCircuitBreakerError | test_error_message | sync |
| TestCircuitBreakerMetrics | test_state_metric_updated | sync |
| TestCircuitBreakerMetrics | test_failure_counter_incremented | sync |
| TestCircuitBreakerMetrics | test_opens_counter_incremented | sync |
| TestCircuitBreakerConcurrency | test_concurrent_access | sync |

### test_error_responses.py (18 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestNotFoundErrors | test_task_not_found_response_format | sync |
| TestNotFoundErrors | test_scanner_not_found_response_format | sync |
| TestNotFoundErrors | test_scan_results_not_found_format | sync |
| TestConflictErrors | test_idempotency_conflict_response_format | sync |
| TestConflictErrors | test_conflict_error_exception_handling | sync |
| TestConflictErrors | test_conflict_preserves_task_reference | sync |
| TestValidationErrors | test_invalid_scan_type_error | sync |
| TestValidationErrors | test_missing_privilege_escalation_error | sync |
| TestValidationErrors | test_schema_conflict_error | sync |
| TestValidationErrors | test_scan_not_completed_error | sync |
| TestErrorResponseConsistency | test_all_errors_have_error_key | sync |
| TestErrorResponseConsistency | test_http_errors_have_status_code | sync |
| TestErrorResponseConsistency | test_error_messages_are_human_readable | sync |
| TestScanStatusErrorDetails | test_failed_scan_includes_error_message | sync |
| TestScanStatusErrorDetails | test_timeout_scan_includes_error_message | sync |
| TestScanStatusErrorDetails | test_completed_scan_no_error_message | sync |
| TestAuthenticationErrorResponses | test_auth_failure_includes_troubleshooting | sync |
| TestAuthenticationErrorResponses | test_partial_auth_includes_details | sync |

### test_health.py (17 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestCheckRedis | test_check_redis_success | sync |
| TestCheckRedis | test_check_redis_connection_success | sync |
| TestCheckRedis | test_check_redis_connection_failure | sync |
| TestCheckRedis | test_check_redis_ping_failure | sync |
| TestCheckFilesystem | test_check_filesystem_success_with_existing_dir | sync |
| TestCheckFilesystem | test_check_filesystem_success_creates_dir | sync |
| TestCheckFilesystem | test_check_filesystem_write_test | sync |
| TestCheckFilesystem | test_check_filesystem_readonly_failure | sync |
| TestCheckFilesystem | test_check_filesystem_nonexistent_parent | sync |
| TestCheckAllDependencies | test_check_all_dependencies_all_healthy | sync |
| TestCheckAllDependencies | test_check_all_dependencies_redis_unhealthy | sync |
| TestCheckAllDependencies | test_check_all_dependencies_filesystem_unhealthy | sync |
| TestCheckAllDependencies | test_check_all_dependencies_all_unhealthy | sync |
| TestCheckAllDependencies | test_check_all_dependencies_returns_dict | sync |
| TestCheckAllDependencies | test_check_all_dependencies_preserves_urls | sync |
| TestRealFilesystem | test_filesystem_check_with_real_tempdir | sync |
| TestRealFilesystem | test_filesystem_creates_nested_directories | sync |

### test_housekeeping.py (18 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestTaskCleanerInit | test_default_initialization | sync |
| TestTaskCleanerInit | test_custom_initialization | sync |
| TestTaskCleaner | test_cleanup_nonexistent_directory | sync |
| TestTaskCleaner | test_cleanup_empty_directory | sync |
| TestTaskCleaner | test_cleanup_completed_task_old | sync |
| TestTaskCleaner | test_cleanup_completed_task_recent | sync |
| TestTaskCleaner | test_cleanup_failed_task_old | sync |
| TestTaskCleaner | test_cleanup_failed_task_recent | sync |
| TestTaskCleaner | test_cleanup_timeout_task_old | sync |
| TestTaskCleaner | test_cleanup_skips_running_tasks | sync |
| TestTaskCleaner | test_cleanup_skips_queued_tasks | sync |
| TestTaskCleaner | test_cleanup_multiple_tasks | sync |
| TestTaskCleaner | test_cleanup_tracks_freed_bytes | sync |
| TestTaskCleaner | test_cleanup_handles_invalid_json | sync |
| TestTaskCleanerStats | test_get_stats_empty | sync |
| TestTaskCleanerStats | test_get_stats_counts_by_status | sync |
| TestTaskCleanerStats | test_get_stats_tracks_expired | sync |
| TestTaskCleanerMetrics | test_ttl_deletions_metric_incremented | sync |

### test_idempotency.py (13 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestHashRequest | test_hash_request_consistent | async |
| TestHashRequest | test_hash_request_key_order_independent | async |
| TestHashRequest | test_hash_request_different_params | async |
| TestHashRequest | test_hash_request_none_normalization | async |
| TestHashRequest | test_hash_request_bool_normalization | async |
| TestIdempotencyStore | test_store_new_key | async |
| TestIdempotencyStore | test_store_existing_key | async |
| TestIdempotencyCheck | test_check_nonexistent_key | async |
| TestIdempotencyCheck | test_check_matching_key | async |
| TestIdempotencyCheck | test_check_conflicting_params | async |
| TestIdempotencyTTL | test_store_ttl_set | async |
| TestIdempotencyWorkflow | test_full_workflow_with_retry | async |
| TestIdempotencyConcurrency | test_concurrent_store_operations | async |

### test_ip_utils.py (55 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestParseNetwork | test_parse_ipv4_address | sync |
| TestParseNetwork | test_parse_ipv4_cidr | sync |
| TestParseNetwork | test_parse_ipv4_cidr_non_strict | sync |
| TestParseNetwork | test_parse_ipv6_address | sync |
| TestParseNetwork | test_parse_ipv6_cidr | sync |
| TestParseNetwork | test_parse_hostname_returns_none | sync |
| TestParseNetwork | test_parse_invalid_returns_none | sync |
| TestParseNetwork | test_parse_empty_returns_none | sync |
| TestParseNetwork | test_parse_whitespace_trimmed | sync |
| TestNetworkComparison | test_ip_equals_ip | sync |
| TestNetworkComparison | test_ip_not_equals_ip | sync |
| TestNetworkComparison | test_ip_in_network | sync |
| TestNetworkComparison | test_ip_not_in_network | sync |
| TestNetworkComparison | test_network_contains_ip | sync |
| TestNetworkComparison | test_networks_overlap | sync |
| TestNetworkComparison | test_networks_no_overlap | sync |
| TestTargetsMatchIPvsIP | test_ip_exact_match | sync |
| TestTargetsMatchIPvsIP | test_ip_no_match | sync |
| TestTargetsMatchIPvsCIDR | test_ip_in_cidr_hit | sync |
| TestTargetsMatchIPvsCIDR | test_ip_in_large_cidr_hit | sync |
| TestTargetsMatchIPvsCIDR | test_ip_at_network_boundary_hit | sync |
| TestTargetsMatchIPvsCIDR | test_ip_at_broadcast_boundary_hit | sync |
| TestTargetsMatchIPvsCIDR | test_ip_not_in_cidr_miss | sync |
| TestTargetsMatchIPvsCIDR | test_ip_adjacent_cidr_miss | sync |
| TestTargetsMatchIPvsCIDR | test_ip_different_network_miss | sync |
| TestTargetsMatchCIDRvsIP | test_cidr_contains_ip_hit | sync |
| TestTargetsMatchCIDRvsIP | test_large_cidr_contains_ip_hit | sync |
| TestTargetsMatchCIDRvsIP | test_cidr_not_contains_ip_miss | sync |
| TestTargetsMatchCIDRvsCIDR | test_cidr_overlap_subset_hit | sync |
| TestTargetsMatchCIDRvsCIDR | test_cidr_overlap_superset_hit | sync |
| TestTargetsMatchCIDRvsCIDR | test_cidr_exact_match_hit | sync |
| TestTargetsMatchCIDRvsCIDR | test_cidr_partial_overlap_hit | sync |
| TestTargetsMatchCIDRvsCIDR | test_cidr_no_overlap_miss | sync |
| TestTargetsMatchCIDRvsCIDR | test_cidr_adjacent_no_overlap_miss | sync |
| TestTargetsMatchMultiple | test_multiple_targets_match_first_hit | sync |
| TestTargetsMatchMultiple | test_multiple_targets_match_second_hit | sync |
| TestTargetsMatchMultiple | test_multiple_targets_match_cidr_in_list_hit | sync |
| TestTargetsMatchMultiple | test_multiple_targets_cidr_query_hit | sync |
| TestTargetsMatchMultiple | test_multiple_targets_no_match_miss | sync |
| TestTargetsMatchMultiple | test_multiple_targets_cidr_no_overlap_miss | sync |
| TestTargetsMatchHostnames | test_hostname_exact_match_hit | sync |
| TestTargetsMatchHostnames | test_hostname_case_insensitive_hit | sync |
| TestTargetsMatchHostnames | test_hostname_in_list_hit | sync |
| TestTargetsMatchHostnames | test_hostname_no_match_miss | sync |
| TestTargetsMatchHostnames | test_hostname_vs_ip_miss | sync |
| TestTargetsMatchHostnames | test_ip_vs_hostname_miss | sync |
| TestTargetsMatchEdgeCases | test_empty_query_miss | sync |
| TestTargetsMatchEdgeCases | test_empty_stored_targets_miss | sync |
| TestTargetsMatchEdgeCases | test_both_empty_miss | sync |
| TestTargetsMatchEdgeCases | test_whitespace_handling | sync |
| TestTargetsMatchEdgeCases | test_empty_entries_in_list | sync |
| TestTargetsMatchRealScenarios | test_scenario_scan_target_172_30_0_9 | sync |
| TestTargetsMatchRealScenarios | test_scenario_large_network_scan | sync |
| TestTargetsMatchRealScenarios | test_scenario_multiple_network_scan | sync |
| TestTargetsMatchRealScenarios | test_scenario_subnet_search_for_specific_scans | sync |

### test_list_tasks.py (14 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestListTasksFiltering | test_filter_by_status_completed | sync |
| TestListTasksFiltering | test_filter_by_status_running | sync |
| TestListTasksFiltering | test_filter_by_status_queued | sync |
| TestListTasksFiltering | test_filter_by_pool_nessus | sync |
| TestListTasksFiltering | test_filter_by_pool_dmz | sync |
| TestListTasksFiltering | test_combined_filter_status_and_pool | sync |
| TestListTasksFiltering | test_limit_respects_count | sync |
| TestListTasksFiltering | test_no_results_returns_empty | sync |
| TestListTasksTargetFiltering | test_target_filter_exact_ip_match | sync |
| TestListTasksTargetFiltering | test_target_filter_ip_in_cidr | sync |
| TestListTasksTargetFiltering | test_target_filter_cidr_contains_stored_ip | sync |
| TestListTasksTargetFiltering | test_target_filter_no_match | sync |
| TestListTasksResponseFormat | test_response_contains_required_fields | sync |
| TestListTasksResponseFormat | test_response_values_match_task | sync |

### test_logging_config.py (9 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestConfigureLogging | test_configure_logging_sets_log_level | sync |
| TestConfigureLogging | test_configure_logging_default_level | sync |
| TestGetLogger | test_get_logger_returns_structured_logger | sync |
| TestGetLogger | test_get_logger_without_name | sync |
| TestLogOutput | test_json_output_format | sync |
| TestLogOutput | test_timestamp_format | sync |
| TestLogOutput | test_log_levels | sync |
| TestLogOutput | test_structured_data_logging | sync |
| TestLogOutput | test_exception_logging | sync |

### test_metrics.py (45 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestMetricDefinitions | test_scans_total_counter_exists | sync |
| TestMetricDefinitions | test_api_requests_total_counter_exists | sync |
| TestMetricDefinitions | test_ttl_deletions_total_counter_exists | sync |
| TestMetricDefinitions | test_active_scans_gauge_exists | sync |
| TestMetricDefinitions | test_scanner_instances_gauge_exists | sync |
| TestMetricDefinitions | test_queue_depth_gauge_exists | sync |
| TestMetricDefinitions | test_dlq_size_gauge_exists | sync |
| TestMetricDefinitions | test_task_duration_histogram_exists | sync |
| TestRecordFunctions | test_record_tool_call_increments_counter | sync |
| TestRecordFunctions | test_record_tool_call_default_status | sync |
| TestRecordFunctions | test_record_scan_submission_increments_counter | sync |
| TestRecordFunctions | test_record_scan_completion_increments_counter | sync |
| TestUpdateFunctions | test_update_active_scans_count_sets_gauge | sync |
| TestUpdateFunctions | test_update_queue_metrics_sets_gauges | sync |
| TestUpdateFunctions | test_update_scanner_instances_metric_sets_gauge | sync |
| TestMetricsEndpoint | test_metrics_response_returns_bytes | sync |
| TestMetricsEndpoint | test_metrics_response_contains_prometheus_format | sync |
| TestMetricsEndpoint | test_metrics_response_contains_all_metrics | sync |
| TestMetricsEndpoint | test_metrics_response_valid_prometheus_format | sync |
| TestHistogramBuckets | test_histogram_buckets_defined | sync |
| TestMetricLabels | test_scans_total_with_different_labels | sync |
| TestMetricLabels | test_api_requests_with_different_tools | sync |
| TestMetricLabels | test_scanner_instances_with_different_types | sync |
| TestPoolMetrics | test_pool_queue_depth_gauge_exists | sync |
| TestPoolMetrics | test_pool_dlq_depth_gauge_exists | sync |
| TestPoolMetrics | test_update_pool_queue_depth_sets_gauge | sync |
| TestPoolMetrics | test_update_pool_dlq_depth_sets_gauge | sync |
| TestPoolMetrics | test_update_all_pool_queue_metrics | sync |
| TestValidationMetrics | test_validation_total_counter_exists | sync |
| TestValidationMetrics | test_validation_failures_counter_exists | sync |
| TestValidationMetrics | test_auth_failures_counter_exists | sync |
| TestValidationMetrics | test_record_validation_result_success | sync |
| TestValidationMetrics | test_record_validation_result_failure | sync |
| TestValidationMetrics | test_record_validation_failure_reason | sync |
| TestValidationMetrics | test_record_validation_failure_different_reasons | sync |
| TestValidationMetrics | test_record_auth_failure | sync |
| TestValidationMetrics | test_record_auth_failure_different_scan_types | sync |
| TestScannerMetrics | test_scanner_active_scans_gauge_exists | sync |
| TestScannerMetrics | test_scanner_capacity_gauge_exists | sync |
| TestScannerMetrics | test_scanner_utilization_gauge_exists | sync |
| TestScannerMetrics | test_update_scanner_metrics | sync |
| TestScannerMetrics | test_update_scanner_metrics_full_capacity | sync |
| TestScannerMetrics | test_update_scanner_metrics_zero_capacity | sync |
| TestScannerMetrics | test_update_all_scanner_metrics | sync |
| TestMetricsIntegration | test_metrics_response_contains_phase4_metrics | sync |

### test_nessus_validator.py (18 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestValidatorErrors | test_file_not_found | sync |
| TestValidatorErrors | test_empty_file | sync |
| TestValidatorErrors | test_invalid_xml | sync |
| TestValidatorErrors | test_no_hosts | sync |
| TestUntrustedScan | test_untrusted_scan_success | sync |
| TestUntrustedScan | test_untrusted_scan_severity_counts | sync |
| TestTrustedScan | test_trusted_scan_auth_success | sync |
| TestTrustedScan | test_trusted_scan_auth_failed | sync |
| TestTrustedScan | test_trusted_scan_auth_partial | sync |
| TestPrivilegedScan | test_trusted_privileged_scan_failed | sync |
| TestSeverityCounts | test_severity_counts_trusted | sync |
| TestHostCount | test_host_count | sync |
| TestHostCount | test_expected_hosts_warning | sync |
| TestHostCount | test_expected_hosts_met | sync |
| TestPluginInference | test_auth_inferred_from_plugins | sync |
| TestConvenience | test_convenience_function | sync |
| TestValidationResult | test_default_values | sync |
| TestValidationResult | test_with_values | sync |

### test_pool_registry.py (20 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestPoolRegistry | test_list_pools | sync |
| TestPoolRegistry | test_get_default_pool | sync |
| TestPoolRegistry | test_get_scanner_count_all | sync |
| TestPoolRegistry | test_get_scanner_count_by_pool | sync |
| TestPoolRegistry | test_list_instances_all | sync |
| TestPoolRegistry | test_list_instances_by_pool | sync |
| TestPoolRegistry | test_get_instance_by_pool | sync |
| TestPoolRegistry | test_get_instance_not_found | sync |
| TestScannerSelection | test_get_available_scanner_from_pool | sync |
| TestScannerSelection | test_get_available_scanner_from_empty_pool | sync |
| TestPoolStatus | test_get_pool_status | sync |
| TestPoolStatus | test_get_pool_status_dmz | sync |
| TestLoadBalancing | test_least_loaded_selection | sync |
| TestScannerAcquisition | test_acquire_increments_active_scans | async |
| TestScannerAcquisition | test_release_decrements_active_scans | async |
| TestScannerAcquisition | test_acquire_specific_instance | async |
| TestScannerLoad | test_get_scanner_load | sync |
| TestPoolIsolation | test_pools_are_isolated | sync |
| TestPoolIsolation | test_pool_status_independent | sync |
| TestPoolIsolation | test_acquire_respects_pool | async |

### test_queue.py (18 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestTaskQueueKeys | test_queue_key_generation | sync |
| TestTaskQueueKeys | test_dlq_key_generation | sync |
| TestTaskQueueEnqueue | test_enqueue_to_default_pool | sync |
| TestTaskQueueEnqueue | test_enqueue_to_specific_pool | sync |
| TestTaskQueueEnqueue | test_enqueue_uses_task_scanner_pool | sync |
| TestTaskQueueEnqueue | test_enqueue_pool_param_takes_precedence | sync |
| TestTaskQueueDequeue | test_dequeue_from_default_pool | sync |
| TestTaskQueueDequeue | test_dequeue_from_specific_pool | sync |
| TestTaskQueueDequeueAny | test_dequeue_any_from_multiple_pools | sync |
| TestTaskQueueDequeueAny | test_dequeue_any_timeout | sync |
| TestTaskQueuePools | test_get_queue_depth_for_pool | sync |
| TestTaskQueuePools | test_get_dlq_size_for_pool | sync |
| TestTaskQueuePools | test_move_to_dlq_uses_pool | sync |
| TestTaskQueuePools | test_peek_from_specific_pool | sync |
| TestTaskQueuePools | test_clear_dlq_for_pool | sync |
| TestGetQueueStats | test_get_queue_stats_default_pool | sync |
| TestGetQueueStats | test_get_queue_stats_specific_pool | sync |
| TestGetAllPoolStats | test_get_all_pool_stats | sync |

### test_queue_status.py (16 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestGetQueueStatsBasic | test_get_queue_stats_default_pool | sync |
| TestGetQueueStatsBasic | test_get_queue_stats_specific_pool | sync |
| TestGetQueueStatsBasic | test_get_queue_stats_empty_queue | sync |
| TestGetQueueStatsBasic | test_get_queue_stats_timestamp_format | sync |
| TestGetQueueStatsPoolIsolation | test_nessus_pool_stats | sync |
| TestGetQueueStatsPoolIsolation | test_dmz_pool_stats | sync |
| TestGetQueueStatsPoolIsolation | test_empty_pool_stats | sync |
| TestQueueStatsResponseFormat | test_response_contains_all_required_fields | sync |
| TestQueueStatsResponseFormat | test_response_types_are_correct | sync |
| TestQueueStatsResponseFormat | test_next_tasks_limited_to_three | sync |
| TestQueueDepthCalculation | test_queue_depth_zero | sync |
| TestQueueDepthCalculation | test_queue_depth_positive | sync |
| TestQueueDepthCalculation | test_queue_depth_large_number | sync |
| TestDLQSizeTracking | test_dlq_size_zero | sync |
| TestDLQSizeTracking | test_dlq_size_positive | sync |
| TestDLQSizeTracking | test_dlq_independent_of_queue | sync |

### test_task_manager.py (16 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestTaskManagerBasic | test_create_and_get_task | sync |
| TestTaskManagerBasic | test_get_nonexistent_task | sync |
| TestTaskManagerBasic | test_update_status_valid_transition | sync |
| TestTaskManagerBasic | test_update_status_invalid_transition | sync |
| TestTaskManagerValidationMetadata | test_task_with_validation_fields | sync |
| TestTaskManagerValidationMetadata | test_mark_completed_with_validation_success | sync |
| TestTaskManagerValidationMetadata | test_mark_completed_with_partial_auth | sync |
| TestTaskManagerValidationMetadata | test_mark_failed_with_validation | sync |
| TestTaskManagerValidationMetadata | test_mark_completed_without_validation | sync |
| TestTaskManagerValidationMetadata | test_backward_compatibility_no_validation_fields | sync |
| TestTaskManagerUntrustedScans | test_untrusted_scan_not_applicable_auth | sync |
| TestTaskManagerTrustedScans | test_trusted_scan_success_auth | sync |
| TestTaskManagerTrustedScans | test_trusted_scan_failed_auth | sync |
| TestGenerateTaskId | test_generate_task_id_format | sync |
| TestGenerateTaskId | test_generate_task_id_unique | sync |
| TestGenerateTaskId | test_generate_task_id_different_scanner_types | sync |

---

## Layer 03: External Basic (79 tests)

Single MCP tool calls with real services.

### test_mcp_tools_basic.py (19 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestClientConnection | test_client_connects_successfully | async |
| TestClientConnection | test_client_ping | async |
| TestClientConnection | test_client_list_tools | async |
| TestScanSubmission | test_submit_scan_basic | async |
| TestScanSubmission | test_submit_scan_with_description | async |
| TestScanSubmission | test_idempotency | async |
| TestScanSubmission | test_get_status | async |
| TestQueueOperations | test_list_tasks | async |
| TestQueueOperations | test_list_tasks_with_filter | async |
| TestQueueOperations | test_get_queue_status | async |
| TestQueueOperations | test_list_scanners | async |
| TestResultsRetrieval | test_get_results_basic | async |
| TestResultsRetrieval | test_get_critical_vulnerabilities | async |
| TestResultsRetrieval | test_get_vulnerability_summary | async |
| TestScanWorkflow | test_wait_for_completion | async |
| TestScanWorkflow | test_scan_and_wait | async |
| TestErrorHandling | test_invalid_task_id | async |
| TestErrorHandling | test_timeout_error | async |
| TestProgressCallback | test_progress_callback_called | async |

### test_pool_operations.py (17 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestListPools | test_list_pools_returns_pools | async |
| TestListPools | test_list_pools_includes_default | async |
| TestListPools | test_list_pools_contains_nessus | async |
| TestListPools | test_list_pools_response_format | async |
| TestGetPoolStatus | test_get_pool_status_default | async |
| TestGetPoolStatus | test_get_pool_status_specific_pool | async |
| TestGetPoolStatus | test_get_pool_status_includes_scanners_list | async |
| TestGetPoolStatus | test_get_pool_status_scanner_details | async |
| TestGetPoolStatus | test_get_pool_status_capacity_metrics | async |
| TestGetPoolStatus | test_get_pool_status_utilization | async |
| TestGetPoolStatus | test_get_pool_status_capacity_math | async |
| TestGetPoolStatus | test_get_pool_status_scanner_type | async |
| TestPoolOperationsIntegration | test_list_pools_then_get_status | async |
| TestPoolOperationsIntegration | test_default_pool_matches_list | async |
| TestPoolOperationsIntegration | test_pool_scanner_count_consistency | async |
| TestPoolOperationsEdgeCases | test_empty_pool_status | async |
| TestPoolOperationsEdgeCases | test_pool_utilization_when_idle | async |

### test_pool_selection.py (15 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestPoolEnqueue | test_enqueue_to_multiple_pools | sync |
| TestPoolDequeue | test_dequeue_from_specific_pool | sync |
| TestPoolDequeue | test_dequeue_any_fifo_order | sync |
| TestPoolDequeue | test_dequeue_any_across_pools | sync |
| TestPoolIsolation | test_pool_isolation | sync |
| TestPoolDLQ | test_move_to_dlq_per_pool | sync |
| TestPoolDLQ | test_clear_dlq_per_pool | sync |
| TestPoolPeek | test_peek_per_pool | sync |
| TestPoolStats | test_get_queue_stats_per_pool | sync |
| TestPoolStats | test_get_all_pool_stats | sync |
| TestWorkerConsumption | test_worker_consumes_from_specified_pools | sync |
| TestWorkerConsumption | test_worker_round_robin_consumption | sync |
| TestDefaultPool | test_default_pool_behavior | sync |
| TestDefaultPool | test_dequeue_without_pool | sync |
| TestTaskPoolData | test_scanner_pool_in_task_data | sync |

### test_scanner_operations.py (3 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestNessusScanner | test_nessus_authentication | async |
| TestNessusScanner | test_nessus_create_and_launch | async |
| TestNessusScanner | test_nessus_status_mapping | async |

### test_schema_parsing.py (25 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestParser | test_parse_nessus_file | sync |
| TestParser | test_parser_handles_cve_lists | sync |
| TestProfiles | test_schema_profiles_exist | sync |
| TestProfiles | test_minimal_schema_fields | sync |
| TestProfiles | test_full_schema_returns_none | sync |
| TestProfiles | test_invalid_profile_raises_error | sync |
| TestCustomFields | test_custom_fields_with_default_profile | sync |
| TestCustomFields | test_mutual_exclusivity | sync |
| TestFilters | test_string_filter_substring | sync |
| TestFilters | test_string_filter_case_insensitive | sync |
| TestFilters | test_number_filter_greater_than | sync |
| TestFilters | test_number_filter_greater_equal | sync |
| TestFilters | test_boolean_filter | sync |
| TestFilters | test_list_filter | sync |
| TestFilters | test_multiple_filters_and_logic | sync |
| TestCompareNumber | test_compare_number_operators | sync |
| TestConverter | test_converter_basic | sync |
| TestConverter | test_converter_minimal_schema | sync |
| TestConverter | test_converter_custom_fields | sync |
| TestConverter | test_converter_with_filters | sync |
| TestConverter | test_converter_pagination | sync |
| TestConverter | test_converter_page_zero_returns_all | sync |
| TestRealScanE2E | test_end_to_end_with_real_scan | sync |
| TestRealScanE2E | test_real_scan_pagination_multi_page | sync |
| TestRealScanE2E | test_real_scan_filters_with_pagination | sync |

---

## Layer 04: Full Workflow (42 tests)

Complete E2E workflows with real scans.

### test_authenticated_scan_workflow.py (9 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestCredentialInjection | test_create_scan_with_ssh_credentials | async |
| TestCredentialInjection | test_create_scan_with_sudo_credentials | async |
| TestQuickAuthenticatedScan | test_authenticated_scan_randy | async |
| TestQuickAuthenticatedScan | test_mcp_tool_validation_only | async |
| TestQuickAuthenticatedScan | test_bad_credentials_detected | async |
| TestPrivilegedScans | test_privileged_scan_sudo_with_password | async |
| TestPrivilegedScans | test_privileged_scan_sudo_nopasswd | async |
| TestTargetReachability | test_verify_scan_target_reachable | async |
| TestTargetReachability | test_verify_external_host_reachable | async |

### test_complete_scan_with_results.py (1 test)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestCompleteScanWorkflow | test_complete_scan_workflow_with_export | async |

### test_mcp_protocol_e2e.py (18 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestMCPConnection | test_mcp_connection_and_initialization | async |
| TestMCPConnection | test_mcp_list_tools | async |
| TestMCPReadOperations | test_mcp_list_tasks_e2e | async |
| TestMCPReadOperations | test_mcp_get_scan_status_e2e | async |
| TestMCPReadOperations | test_mcp_list_scanners_e2e | async |
| TestMCPReadOperations | test_mcp_get_queue_status_e2e | async |
| TestMCPErrorHandling | test_mcp_invalid_scan_type_error | async |
| TestMCPErrorHandling | test_mcp_missing_required_params | async |
| TestMCPScanOperations | test_mcp_run_untrusted_scan_e2e | async |
| TestMCPScanOperations | test_mcp_run_authenticated_scan_e2e | async |
| TestMCPQueuePosition | test_queue_position_in_response | async |
| TestMCPQueuePosition | test_queue_position_multiple_submits | async |
| TestMCPEdgeCases | test_unreachable_target_handling | async |
| TestMCPEdgeCases | test_invalid_target_format_handling | async |
| TestMCPEdgeCases | test_task_status_shows_error_details | async |
| TestMCPEdgeCases | test_scan_with_timeout_target | async |
| TestMCPQueueIntegration | test_estimated_wait_increases_with_queue_depth | async |
| TestMCPQueueIntegration | test_queue_status_reflects_submissions | async |

### test_queue_position_accuracy.py (12 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestQueuePositionReporting | test_queue_position_in_submission_response | async |
| TestQueuePositionReporting | test_queue_position_increments | async |
| TestQueuePositionReporting | test_queue_status_reflects_submissions | async |
| TestQueueStatusAccuracy | test_queue_status_has_depth | async |
| TestQueueStatusAccuracy | test_queue_status_has_dlq_size | async |
| TestQueueStatusAccuracy | test_queue_status_has_next_tasks | async |
| TestQueueStatusAccuracy | test_queue_status_has_timestamp | async |
| TestQueuePositionVsPoolStatus | test_queue_depth_matches_pool_capacity_awareness | async |
| TestQueuePositionVsPoolStatus | test_active_scans_vs_queue_depth | async |
| TestQueuePositionWithRealScans | test_queue_position_decreases_as_scans_complete | async |
| TestQueuePositionWithRealScans | test_multiple_scan_queue_ordering | async |
| TestWaitTimeEstimation | test_queue_provides_reasonable_estimates | async |

### test_untrusted_scan_workflow.py (2 tests)

| Test Class | Test Name | Type |
|------------|-----------|------|
| TestE2EWorkflow | test_complete_e2e_workflow_untrusted_scan | async |
| TestE2EWorkflow | test_e2e_with_result_filtering | async |

---

## Running Tests

```bash
# Quick validation (layers 01-02)
docker compose exec mcp-api tests/run_test_pipeline.sh --quick

# Standard tests (layers 01-03)
docker compose exec mcp-api tests/run_test_pipeline.sh

# Full E2E tests (all layers)
docker compose exec mcp-api tests/run_test_pipeline.sh --full

# Run specific layer
docker compose exec mcp-api pytest tests/layer01_infrastructure/ -v
docker compose exec mcp-api pytest tests/layer02_internal/ -v
docker compose exec mcp-api pytest tests/layer03_external_basic/ -v
docker compose exec mcp-api pytest tests/layer04_full_workflow/ -v

# Run by marker
docker compose exec mcp-api pytest -m layer01 -v
docker compose exec mcp-api pytest -m "layer01 or layer02" -v
docker compose exec mcp-api pytest -m "not layer04" -v
```
