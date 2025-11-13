"""Unit tests for Prometheus metrics."""
import pytest
from prometheus_client import REGISTRY
from core.metrics import (
    scans_total,
    api_requests_total,
    ttl_deletions_total,
    active_scans,
    scanner_instances,
    queue_depth,
    dlq_size,
    task_duration_seconds,
    metrics_response,
    record_tool_call,
    record_scan_submission,
    record_scan_completion,
    update_active_scans_count,
    update_queue_metrics,
    update_scanner_instances_metric
)


class TestMetricsDefinitions:
    """Test that all metrics are properly defined."""

    def test_scans_total_counter_exists(self):
        """Test that scans_total counter is defined."""
        assert scans_total is not None
        assert scans_total._name == "nessus_scans_total"
        assert "scan_type" in scans_total._labelnames
        assert "status" in scans_total._labelnames

    def test_api_requests_total_counter_exists(self):
        """Test that api_requests_total counter is defined."""
        assert api_requests_total is not None
        assert api_requests_total._name == "nessus_api_requests_total"
        assert "tool" in api_requests_total._labelnames
        assert "status" in api_requests_total._labelnames

    def test_ttl_deletions_total_counter_exists(self):
        """Test that ttl_deletions_total counter is defined."""
        assert ttl_deletions_total is not None
        assert ttl_deletions_total._name == "nessus_ttl_deletions_total"

    def test_active_scans_gauge_exists(self):
        """Test that active_scans gauge is defined."""
        assert active_scans is not None
        assert active_scans._name == "nessus_active_scans"

    def test_scanner_instances_gauge_exists(self):
        """Test that scanner_instances gauge is defined."""
        assert scanner_instances is not None
        assert scanner_instances._name == "nessus_scanner_instances"
        assert "scanner_type" in scanner_instances._labelnames
        assert "enabled" in scanner_instances._labelnames

    def test_queue_depth_gauge_exists(self):
        """Test that queue_depth gauge is defined."""
        assert queue_depth is not None
        assert queue_depth._name == "nessus_queue_depth"
        assert "queue" in queue_depth._labelnames

    def test_dlq_size_gauge_exists(self):
        """Test that dlq_size gauge is defined."""
        assert dlq_size is not None
        assert dlq_size._name == "nessus_dlq_size"

    def test_task_duration_histogram_exists(self):
        """Test that task_duration_seconds histogram is defined."""
        assert task_duration_seconds is not None
        assert task_duration_seconds._name == "nessus_task_duration_seconds"


class TestMetricsHelpers:
    """Test metric helper functions."""

    def test_record_tool_call_increments_counter(self):
        """Test that record_tool_call increments the api_requests_total counter."""
        # Get initial value
        initial = api_requests_total.labels(tool="test_tool", status="success")._value.get()

        # Record tool call
        record_tool_call("test_tool", "success")

        # Check increment
        final = api_requests_total.labels(tool="test_tool", status="success")._value.get()
        assert final == initial + 1

    def test_record_tool_call_default_status(self):
        """Test that record_tool_call uses 'success' as default status."""
        initial = api_requests_total.labels(tool="default_test", status="success")._value.get()

        record_tool_call("default_test")

        final = api_requests_total.labels(tool="default_test", status="success")._value.get()
        assert final == initial + 1

    def test_record_scan_submission_increments_counter(self):
        """Test that record_scan_submission increments the scans_total counter."""
        initial = scans_total.labels(scan_type="untrusted", status="queued")._value.get()

        record_scan_submission("untrusted", "queued")

        final = scans_total.labels(scan_type="untrusted", status="queued")._value.get()
        assert final == initial + 1

    def test_record_scan_completion_increments_counter(self):
        """Test that record_scan_completion increments the scans_total counter."""
        initial = scans_total.labels(scan_type="untrusted", status="completed")._value.get()

        record_scan_completion("untrusted", "completed")

        final = scans_total.labels(scan_type="untrusted", status="completed")._value.get()
        assert final == initial + 1

    def test_update_active_scans_count_sets_gauge(self):
        """Test that update_active_scans_count sets the active_scans gauge."""
        update_active_scans_count(5)

        assert active_scans._value.get() == 5

        update_active_scans_count(0)

        assert active_scans._value.get() == 0

    def test_update_queue_metrics_sets_gauges(self):
        """Test that update_queue_metrics sets queue depth gauges."""
        update_queue_metrics(main_depth=10, dlq_depth=2)

        assert queue_depth.labels(queue="main")._value.get() == 10
        assert queue_depth.labels(queue="dead")._value.get() == 2
        assert dlq_size._value.get() == 2

    def test_update_scanner_instances_metric_sets_gauge(self):
        """Test that update_scanner_instances_metric sets scanner_instances gauge."""
        update_scanner_instances_metric("nessus", enabled_count=3, disabled_count=1)

        assert scanner_instances.labels(scanner_type="nessus", enabled="true")._value.get() == 3
        assert scanner_instances.labels(scanner_type="nessus", enabled="false")._value.get() == 1


class TestMetricsResponse:
    """Test metrics response generation."""

    def test_metrics_response_returns_bytes(self):
        """Test that metrics_response returns bytes."""
        response = metrics_response()
        assert isinstance(response, bytes)

    def test_metrics_response_contains_prometheus_format(self):
        """Test that metrics_response contains Prometheus text format."""
        response = metrics_response()
        text = response.decode('utf-8')

        # Should contain HELP and TYPE lines
        assert "# HELP" in text or "# TYPE" in text

        # Should contain at least one of our metric names
        assert "nessus_" in text

    def test_metrics_response_contains_all_metrics(self):
        """Test that metrics_response includes all defined metrics."""
        response = metrics_response()
        text = response.decode('utf-8')

        # Check for presence of all metric names
        assert "nessus_scans_total" in text
        assert "nessus_api_requests_total" in text
        assert "nessus_active_scans" in text
        assert "nessus_scanner_instances" in text
        assert "nessus_queue_depth" in text
        assert "nessus_dlq_size" in text
        assert "nessus_task_duration_seconds" in text

    def test_metrics_response_valid_prometheus_format(self):
        """Test that metrics_response is in valid Prometheus format."""
        response = metrics_response()
        text = response.decode('utf-8')

        lines = text.split('\n')

        # Should have HELP, TYPE, and metric lines
        help_lines = [l for l in lines if l.startswith('# HELP')]
        type_lines = [l for l in lines if l.startswith('# TYPE')]
        metric_lines = [l for l in lines if l and not l.startswith('#')]

        assert len(help_lines) > 0
        assert len(type_lines) > 0
        assert len(metric_lines) > 0

    def test_histogram_buckets_defined(self):
        """Test that task_duration_seconds histogram has correct buckets."""
        # Expected buckets: 60, 300, 600, 1800, 3600, 7200, 14400
        expected_buckets = [60, 300, 600, 1800, 3600, 7200, 14400]

        # Get histogram buckets (excluding +Inf)
        buckets = [b for b in task_duration_seconds._upper_bounds if b != float('inf')]

        assert buckets == expected_buckets


class TestMetricsLabels:
    """Test metric labels work correctly."""

    def test_scans_total_with_different_labels(self):
        """Test that scans_total tracks different scan types separately."""
        initial_untrusted = scans_total.labels(scan_type="untrusted", status="queued")._value.get()
        initial_trusted = scans_total.labels(scan_type="trusted", status="queued")._value.get()

        record_scan_submission("untrusted", "queued")
        record_scan_submission("trusted", "queued")

        final_untrusted = scans_total.labels(scan_type="untrusted", status="queued")._value.get()
        final_trusted = scans_total.labels(scan_type="trusted", status="queued")._value.get()

        assert final_untrusted == initial_untrusted + 1
        assert final_trusted == initial_trusted + 1

    def test_api_requests_with_different_tools(self):
        """Test that api_requests_total tracks different tools separately."""
        initial_tool1 = api_requests_total.labels(tool="tool1", status="success")._value.get()
        initial_tool2 = api_requests_total.labels(tool="tool2", status="success")._value.get()

        record_tool_call("tool1", "success")
        record_tool_call("tool2", "success")

        final_tool1 = api_requests_total.labels(tool="tool1", status="success")._value.get()
        final_tool2 = api_requests_total.labels(tool="tool2", status="success")._value.get()

        assert final_tool1 == initial_tool1 + 1
        assert final_tool2 == initial_tool2 + 1

    def test_scanner_instances_with_different_types(self):
        """Test that scanner_instances tracks different scanner types separately."""
        update_scanner_instances_metric("nessus", 2, 0)
        update_scanner_instances_metric("openvas", 1, 1)

        nessus_enabled = scanner_instances.labels(scanner_type="nessus", enabled="true")._value.get()
        openvas_enabled = scanner_instances.labels(scanner_type="openvas", enabled="true")._value.get()

        assert nessus_enabled == 2
        assert openvas_enabled == 1
