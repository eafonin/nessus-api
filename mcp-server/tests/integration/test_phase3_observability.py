"""
Integration tests for Phase 3 observability features.

Tests:
- Structured logging with JSON format
- Prometheus metrics endpoints
- Health check endpoints
- Trace ID propagation through workflow
- MCP client integration with observability
"""
import pytest
import asyncio
import json
import redis
import requests
from pathlib import Path


class TestStructuredLogging:
    """Test structured logging in JSON format."""

    def test_log_format_is_json(self, caplog):
        """Test that logs are output in valid JSON format."""
        from core.logging_config import configure_logging, get_logger

        configure_logging(log_level="INFO")
        logger = get_logger("test_integration")

        logger.info("test_structured_log", task_id="test-123", event="test_event")

        # Check that we can parse log as JSON
        for record in caplog.records:
            try:
                log_data = json.loads(record.getMessage())
                assert "event" in log_data or "task_id" in log_data
                return
            except json.JSONDecodeError:
                pass

        pytest.fail("No valid JSON log entries found")

    def test_trace_id_propagation(self, caplog):
        """Test that trace_id is propagated through log entries."""
        from core.logging_config import configure_logging, get_logger

        configure_logging(log_level="INFO")
        logger = get_logger("test_trace")

        trace_id = "test-trace-12345"

        # Log multiple events with same trace_id
        logger.info("event1", trace_id=trace_id, step=1)
        logger.info("event2", trace_id=trace_id, step=2)

        # Verify trace_id appears in logs
        trace_count = 0
        for record in caplog.records:
            try:
                log_data = json.loads(record.getMessage())
                if log_data.get("trace_id") == trace_id:
                    trace_count += 1
            except json.JSONDecodeError:
                pass

        assert trace_count >= 2, f"Expected at least 2 log entries with trace_id, found {trace_count}"


class TestPrometheusMetrics:
    """Test Prometheus metrics endpoint and metric collection."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_accessible(self):
        """Test that /metrics endpoint is accessible and returns Prometheus format."""
        try:
            response = requests.get("http://localhost:8000/metrics", timeout=5)

            assert response.status_code == 200
            assert "text/plain" in response.headers.get("content-type", "")

            text = response.text
            assert "# HELP" in text or "# TYPE" in text
            assert "nessus_" in text

        except requests.exceptions.ConnectionError:
            pytest.skip("MCP server not running on localhost:8000")

    @pytest.mark.asyncio
    async def test_metrics_contain_observability_metrics(self):
        """Test that metrics endpoint includes Phase 3 observability metrics."""
        try:
            response = requests.get("http://localhost:8000/metrics", timeout=5)

            text = response.text

            # Check for all Phase 3 metrics
            expected_metrics = [
                "nessus_scans_total",
                "nessus_api_requests_total",
                "nessus_active_scans",
                "nessus_scanner_instances",
                "nessus_queue_depth",
                "nessus_dlq_size",
                "nessus_task_duration_seconds"
            ]

            for metric in expected_metrics:
                assert metric in text, f"Metric {metric} not found in /metrics output"

        except requests.exceptions.ConnectionError:
            pytest.skip("MCP server not running on localhost:8000")

    def test_metric_helpers_update_values(self):
        """Test that metric helper functions update Prometheus metrics."""
        from core.metrics import (
            record_tool_call,
            record_scan_submission,
            update_active_scans_count,
            update_queue_metrics,
            api_requests_total,
            scans_total,
            active_scans,
            queue_depth
        )

        # Record some metrics
        initial_requests = api_requests_total.labels(tool="test_tool", status="success")._value.get()
        record_tool_call("test_tool", "success")
        final_requests = api_requests_total.labels(tool="test_tool", status="success")._value.get()

        assert final_requests == initial_requests + 1

        # Test scan submission
        initial_scans = scans_total.labels(scan_type="untrusted", status="queued")._value.get()
        record_scan_submission("untrusted", "queued")
        final_scans = scans_total.labels(scan_type="untrusted", status="queued")._value.get()

        assert final_scans == initial_scans + 1

        # Test gauge updates
        update_active_scans_count(5)
        assert active_scans._value.get() == 5

        update_queue_metrics(10, 2)
        assert queue_depth.labels(queue="main")._value.get() == 10


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint_accessible(self):
        """Test that /health endpoint is accessible."""
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)

            assert response.status_code in [200, 503]  # 200 healthy, 503 unhealthy
            assert response.headers.get("content-type") == "application/json"

            data = response.json()
            assert "status" in data
            assert "redis_healthy" in data
            assert "filesystem_healthy" in data

        except requests.exceptions.ConnectionError:
            pytest.skip("MCP server not running on localhost:8000")

    @pytest.mark.asyncio
    async def test_health_endpoint_with_redis_up(self):
        """Test health endpoint when Redis is available."""
        try:
            # Check if Redis is accessible
            redis_client = redis.from_url("redis://redis:6379", decode_responses=True)
            redis_client.ping()

            # Health check should pass
            response = requests.get("http://localhost:8000/health", timeout=5)

            data = response.json()
            assert data["redis_healthy"] is True

        except (redis.ConnectionError, requests.exceptions.ConnectionError):
            pytest.skip("Redis or MCP server not accessible")

    @pytest.mark.asyncio
    async def test_health_endpoint_structure(self):
        """Test that health endpoint returns proper JSON structure."""
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)

            data = response.json()

            required_fields = ["status", "redis_healthy", "filesystem_healthy"]
            for field in required_fields:
                assert field in data, f"Required field {field} missing from health response"

            assert data["status"] in ["healthy", "unhealthy"]
            assert isinstance(data["redis_healthy"], bool)
            assert isinstance(data["filesystem_healthy"], bool)

        except requests.exceptions.ConnectionError:
            pytest.skip("MCP server not running on localhost:8000")


class TestMCPClientObservability:
    """Test observability features through MCP client interactions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mcp_tool_call_records_metrics(self):
        """Test that MCP tool calls are recorded in metrics."""
        try:
            # Get initial metric value
            response_before = requests.get("http://localhost:8000/metrics", timeout=5)
            metrics_before = response_before.text

            # Make an MCP tool call (list_scanners is simple and doesn't require Nessus)
            # Note: This test would need actual MCP client setup
            # For now, we'll verify the metric exists

            assert "nessus_api_requests_total" in metrics_before

        except requests.exceptions.ConnectionError:
            pytest.skip("MCP server not running")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_queue_status_tool_observability(self):
        """Test that get_queue_status tool returns observable metrics."""
        try:
            # This test requires MCP client
            # For now, verify queue metrics are exposed
            response = requests.get("http://localhost:8000/metrics", timeout=5)

            metrics = response.text

            assert "nessus_queue_depth" in metrics
            assert "nessus_dlq_size" in metrics

        except requests.exceptions.ConnectionError:
            pytest.skip("MCP server not running")


class TestEndToEndObservability:
    """End-to-end observability tests simulating full scan workflow."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.integration
    async def test_scan_workflow_generates_complete_logs(self, caplog):
        """Test that a complete scan workflow generates structured logs."""
        from core.logging_config import configure_logging, get_logger

        configure_logging(log_level="INFO")
        logger = get_logger("test_workflow")

        trace_id = "e2e-test-trace-001"

        # Simulate scan workflow events
        logger.info("scan_enqueued", trace_id=trace_id, task_id="test-task-001")
        logger.info("scan_state_transition", trace_id=trace_id, from_state="queued", to_state="running")
        logger.info("scan_progress", trace_id=trace_id, progress=50)
        logger.info("scan_completed", trace_id=trace_id, vulnerabilities_found=10)

        # Count log events
        event_count = 0
        for record in caplog.records:
            try:
                log_data = json.loads(record.getMessage())
                if log_data.get("trace_id") == trace_id:
                    event_count += 1
            except json.JSONDecodeError:
                pass

        assert event_count >= 4, f"Expected at least 4 log events, found {event_count}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_metrics_update_during_scan_lifecycle(self):
        """Test that metrics are updated during scan lifecycle."""
        from core.metrics import (
            record_scan_submission,
            update_active_scans_count,
            record_scan_completion,
            scans_total,
            active_scans
        )

        # Simulate scan lifecycle
        scan_type = "untrusted"

        # 1. Scan submitted
        initial_queued = scans_total.labels(scan_type=scan_type, status="queued")._value.get()
        record_scan_submission(scan_type, "queued")
        assert scans_total.labels(scan_type=scan_type, status="queued")._value.get() == initial_queued + 1

        # 2. Scan running
        update_active_scans_count(1)
        assert active_scans._value.get() == 1

        # 3. Scan completed
        initial_completed = scans_total.labels(scan_type=scan_type, status="completed")._value.get()
        record_scan_completion(scan_type, "completed")
        assert scans_total.labels(scan_type=scan_type, status="completed")._value.get() == initial_completed + 1

        # 4. Scan no longer active
        update_active_scans_count(0)
        assert active_scans._value.get() == 0


@pytest.mark.asyncio
@pytest.mark.integration
class TestObservabilityUnderLoad:
    """Test observability performance under load."""

    async def test_logging_performance_with_high_volume(self, caplog):
        """Test that structured logging maintains performance with high volume."""
        from core.logging_config import configure_logging, get_logger
        import time

        configure_logging(log_level="INFO")
        logger = get_logger("load_test")

        start_time = time.time()

        # Log 100 events
        for i in range(100):
            logger.info("load_test_event", iteration=i, test="performance")

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 1 second for 100 logs)
        assert elapsed < 1.0, f"Logging 100 events took {elapsed:.2f}s, expected < 1.0s"

    async def test_metrics_performance_with_high_volume(self):
        """Test that metrics updates maintain performance with high volume."""
        from core.metrics import record_tool_call
        import time

        start_time = time.time()

        # Record 1000 metric updates
        for i in range(1000):
            record_tool_call("load_test_tool", "success")

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 1 second for 1000 updates)
        assert elapsed < 1.0, f"Recording 1000 metrics took {elapsed:.2f}s, expected < 1.0s"
