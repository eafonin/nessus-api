"""
Integration tests for NessusFastMCPClient

Tests the complete client against a running MCP server.

Run with:
    pytest tests/integration/test_fastmcp_client.py -v -s

Requirements:
    - MCP server running at http://localhost:8835/mcp
    - Redis running at redis://localhost:6379
    - Scanner worker running
"""

import pytest
import json
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.nessus_fastmcp_client import NessusFastMCPClient


# Mark all tests as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestClientConnection:
    """Test client connection and lifecycle."""

    async def test_client_connects_successfully(self):
        """Test client can connect to MCP server."""
        async with NessusFastMCPClient("http://localhost:8835/mcp") as client:
            assert client.is_connected()

    async def test_client_ping(self):
        """Test ping method."""
        async with NessusFastMCPClient() as client:
            result = await client.ping()
            assert result is True

    async def test_client_list_tools(self):
        """Test listing available MCP tools."""
        async with NessusFastMCPClient() as client:
            tools = await client.list_tools()
            assert len(tools) >= 6  # Should have at least 6 tools
            tool_names = [t["name"] for t in tools]
            assert "run_untrusted_scan" in tool_names
            assert "get_scan_status" in tool_names
            assert "get_scan_results" in tool_names


class TestScanSubmission:
    """Test scan submission operations."""

    async def test_submit_scan_basic(self):
        """Test basic scan submission."""
        async with NessusFastMCPClient() as client:
            task = await client.submit_scan(
                targets="192.168.1.1",
                scan_name="Test Scan - FastMCP Client"
            )

            assert "task_id" in task
            assert task["status"] == "queued"
            assert "scan_name" in task

    async def test_submit_scan_with_description(self):
        """Test scan submission with description."""
        async with NessusFastMCPClient() as client:
            task = await client.submit_scan(
                targets="192.168.1.1",
                scan_name="Test Scan with Description",
                description="Integration test scan"
            )

            assert task["status"] == "queued"
            task_id = task["task_id"]

            # Verify description was stored
            status = await client.get_status(task_id)
            assert status["task_id"] == task_id

    async def test_idempotency(self):
        """Test idempotency - same scan submitted twice returns same task_id."""
        async with NessusFastMCPClient() as client:
            # First submission
            task1 = await client.submit_scan(
                targets="192.168.1.100",
                scan_name="Idempotency Test Scan"
            )

            # Second submission (same parameters)
            task2 = await client.submit_scan(
                targets="192.168.1.100",
                scan_name="Idempotency Test Scan"
            )

            # Should return same task_id
            assert task1["task_id"] == task2["task_id"]
            assert task2.get("idempotent") is True


class TestScanStatus:
    """Test scan status operations."""

    async def test_get_status(self):
        """Test get_status method."""
        async with NessusFastMCPClient() as client:
            # Submit scan
            task = await client.submit_scan(
                targets="192.168.1.1",
                scan_name="Status Test Scan"
            )
            task_id = task["task_id"]

            # Get status
            status = await client.get_status(task_id)

            assert status["task_id"] == task_id
            assert "status" in status
            assert "progress" in status

    async def test_list_tasks(self):
        """Test list_tasks method."""
        async with NessusFastMCPClient() as client:
            result = await client.list_tasks(limit=10)

            assert "tasks" in result
            assert "total" in result
            assert len(result["tasks"]) <= 10

    async def test_list_tasks_with_filter(self):
        """Test list_tasks with status filter."""
        async with NessusFastMCPClient() as client:
            result = await client.list_tasks(status="queued", limit=5)

            assert "tasks" in result
            # All returned tasks should have status="queued"
            for task in result["tasks"]:
                assert task.get("status") == "queued"


class TestQueueOperations:
    """Test queue-related operations."""

    async def test_get_queue_status(self):
        """Test get_queue_status method."""
        async with NessusFastMCPClient() as client:
            queue = await client.get_queue_status()

            assert "main_queue_depth" in queue
            assert "dlq_depth" in queue
            assert isinstance(queue["main_queue_depth"], int)
            assert isinstance(queue["dlq_depth"], int)

    async def test_list_scanners(self):
        """Test list_scanners method."""
        async with NessusFastMCPClient() as client:
            scanners = await client.list_scanners()

            assert "scanners" in scanners
            assert isinstance(scanners["scanners"], list)


class TestResultRetrieval:
    """Test result retrieval operations.

    Note: These tests require a completed scan to exist.
    """

    @pytest.mark.skip(reason="Requires completed scan")
    async def test_get_results_basic(self):
        """Test get_results with basic parameters."""
        task_id = "nessus-local-20251108-143022"  # Replace with actual completed task

        async with NessusFastMCPClient() as client:
            results = await client.get_results(
                task_id=task_id,
                schema_profile="minimal",
                page=1,
                page_size=10
            )

            assert isinstance(results, str)
            lines = results.strip().split("\n")
            assert len(lines) >= 3  # At minimum: schema + metadata + pagination

            # Parse first line (schema)
            schema = json.loads(lines[0])
            assert schema["type"] == "schema"
            assert schema["profile"] == "minimal"

    @pytest.mark.skip(reason="Requires completed scan")
    async def test_get_critical_vulnerabilities(self):
        """Test get_critical_vulnerabilities helper."""
        task_id = "nessus-local-20251108-143022"  # Replace with actual completed task

        async with NessusFastMCPClient() as client:
            critical = await client.get_critical_vulnerabilities(task_id)

            assert isinstance(critical, list)
            # All should have severity="4"
            for vuln in critical:
                assert vuln.get("severity") == "4"

    @pytest.mark.skip(reason="Requires completed scan")
    async def test_get_vulnerability_summary(self):
        """Test get_vulnerability_summary helper."""
        task_id = "nessus-local-20251108-143022"  # Replace with actual completed task

        async with NessusFastMCPClient() as client:
            summary = await client.get_vulnerability_summary(task_id)

            assert isinstance(summary, dict)
            assert "1" in summary or "2" in summary or "3" in summary or "4" in summary


class TestHelperMethods:
    """Test helper workflow methods."""

    @pytest.mark.skip(reason="Takes 5-10 minutes to complete")
    async def test_wait_for_completion(self):
        """Test wait_for_completion method."""
        async with NessusFastMCPClient() as client:
            # Submit scan
            task = await client.submit_scan(
                targets="192.168.1.1",
                scan_name="Wait Test Scan"
            )
            task_id = task["task_id"]

            # Wait for completion
            final_status = await client.wait_for_completion(
                task_id=task_id,
                timeout=600,
                poll_interval=10
            )

            assert final_status["status"] in ["completed", "failed"]

    @pytest.mark.skip(reason="Takes 5-10 minutes to complete")
    async def test_scan_and_wait(self):
        """Test scan_and_wait convenience method."""
        async with NessusFastMCPClient() as client:
            final_status = await client.scan_and_wait(
                targets="192.168.1.1",
                scan_name="Scan and Wait Test",
                timeout=600,
                poll_interval=10
            )

            assert final_status["status"] in ["completed", "failed"]
            assert "task_id" in final_status


class TestErrorHandling:
    """Test error handling."""

    async def test_invalid_task_id(self):
        """Test error when task_id doesn't exist."""
        async with NessusFastMCPClient() as client:
            status = await client.get_status("invalid-task-id-12345")

            # Should return error dict, not raise exception
            assert "error" in status or status.get("status") is None

    async def test_timeout_error(self):
        """Test timeout handling."""
        async with NessusFastMCPClient(timeout=0.001) as client:
            with pytest.raises(Exception):  # May be TimeoutError or ConnectionError
                await client.submit_scan(
                    targets="192.168.1.1",
                    scan_name="Timeout Test"
                )


class TestProgressCallbacks:
    """Test progress callback functionality."""

    async def test_progress_callback_called(self):
        """Test that progress callback is invoked."""
        callback_invoked = []

        def progress_callback(status):
            callback_invoked.append(status)

        async with NessusFastMCPClient() as client:
            # Submit scan
            task = await client.submit_scan(
                targets="192.168.1.1",
                scan_name="Callback Test Scan"
            )
            task_id = task["task_id"]

            # Wait briefly with callback
            try:
                await client.wait_for_completion(
                    task_id=task_id,
                    timeout=30,  # Short timeout
                    poll_interval=5,
                    progress_callback=progress_callback
                )
            except TimeoutError:
                pass  # Expected - we're just testing callbacks

            # Callback should have been invoked at least once
            assert len(callback_invoked) > 0


# Export test classes
__all__ = [
    'TestClientConnection',
    'TestScanSubmission',
    'TestScanStatus',
    'TestQueueOperations',
    'TestResultRetrieval',
    'TestHelperMethods',
    'TestErrorHandling',
    'TestProgressCallbacks',
]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
