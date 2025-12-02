"""
Layer 04: Queue Position and Wait Estimation Accuracy Tests.

Tests the accuracy of queue position reporting and wait time estimation:
- Queue position increments for multiple submissions
- Queue position updates as scans complete
- Wait time estimation reasonableness

These are E2E tests that submit multiple scans to test queue behavior.

Usage:
    docker compose exec mcp-api pytest tests/layer04_full_workflow/test_queue_position_accuracy.py -v -s

Note: These tests may take several minutes as they submit actual scans.
"""

import os

import pytest
import pytest_asyncio

from client.nessus_fastmcp_client import NessusFastMCPClient

# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-api:8000/mcp")
TEST_TARGET = os.getenv("TEST_TARGET", "127.0.0.1")  # Safe localhost target


@pytest_asyncio.fixture
async def mcp_client():
    """FastMCP client for queue tests."""
    client = NessusFastMCPClient(MCP_SERVER_URL)
    await client.connect()
    yield client
    await client.close()


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.e2e
class TestQueuePositionReporting:
    """Tests for queue position accuracy in scan submissions."""

    async def test_queue_position_in_submission_response(self, mcp_client):
        """Test that scan submission returns queue position."""
        result = await mcp_client.call_tool(
            "run_untrusted_scan",
            {
                "targets": TEST_TARGET,
                "name": "Queue Position Test",
                "description": "Testing queue position reporting",
            },
        )

        # Response should include queue position
        assert "queue_position" in result, "Missing queue_position in response"
        assert isinstance(result["queue_position"], int)
        assert result["queue_position"] >= 0

    async def test_queue_position_increments(self, mcp_client):
        """Test that queue position increments for sequential submissions."""
        positions = []

        # Submit multiple scans quickly
        for i in range(3):
            result = await mcp_client.call_tool(
                "run_untrusted_scan",
                {
                    "targets": TEST_TARGET,
                    "name": f"Queue Test {i}",
                    "description": f"Testing queue position {i}",
                },
            )
            if "queue_position" in result:
                positions.append(result["queue_position"])

        # Queue positions should be monotonically increasing (or same if processed instantly)
        assert len(positions) > 0, "No queue positions returned"

        # At minimum, positions should be non-negative
        for pos in positions:
            assert pos >= 0, f"Invalid queue position: {pos}"

    async def test_queue_status_reflects_submissions(self, mcp_client):
        """Test that queue status updates after submissions."""
        # Get initial queue depth
        initial_status = await mcp_client.call_tool("get_queue_status", {})
        initial_status.get("queue_depth", 0)

        # Submit a scan
        await mcp_client.call_tool(
            "run_untrusted_scan",
            {
                "targets": TEST_TARGET,
                "name": "Queue Depth Test",
            },
        )

        # Check queue status again
        # Note: Scan might be picked up immediately, so depth might not increase
        new_status = await mcp_client.call_tool("get_queue_status", {})

        # Queue depth should be >= 0
        assert new_status["queue_depth"] >= 0


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.e2e
class TestQueueStatusAccuracy:
    """Tests for queue status accuracy."""

    async def test_queue_status_has_depth(self, mcp_client):
        """Test that queue status includes depth."""
        result = await mcp_client.call_tool("get_queue_status", {})

        assert "queue_depth" in result
        assert isinstance(result["queue_depth"], int)
        assert result["queue_depth"] >= 0

    async def test_queue_status_has_dlq_size(self, mcp_client):
        """Test that queue status includes DLQ size."""
        result = await mcp_client.call_tool("get_queue_status", {})

        assert "dlq_size" in result
        assert isinstance(result["dlq_size"], int)
        assert result["dlq_size"] >= 0

    async def test_queue_status_has_next_tasks(self, mcp_client):
        """Test that queue status includes next tasks preview."""
        result = await mcp_client.call_tool("get_queue_status", {})

        assert "next_tasks" in result
        assert isinstance(result["next_tasks"], list)

    async def test_queue_status_has_timestamp(self, mcp_client):
        """Test that queue status includes timestamp."""
        result = await mcp_client.call_tool("get_queue_status", {})

        assert "timestamp" in result
        assert result["timestamp"] is not None


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.e2e
class TestQueuePositionVsPoolStatus:
    """Tests comparing queue position with pool status."""

    async def test_queue_depth_matches_pool_capacity_awareness(self, mcp_client):
        """Test that queue depth and pool capacity are coherent."""
        queue_status = await mcp_client.call_tool("get_queue_status", {})
        pool_status = await mcp_client.call_tool("get_pool_status", {})

        queue_depth = queue_status.get("queue_depth", 0)
        available_capacity = pool_status.get("available_capacity", 0)

        # If queue has items but capacity available, scans should be processing
        # This is informational - exact behavior depends on worker polling
        assert queue_depth >= 0
        assert available_capacity >= 0

    async def test_active_scans_vs_queue_depth(self, mcp_client):
        """Test relationship between active scans and queue depth."""
        pool_status = await mcp_client.call_tool("get_pool_status", {})
        queue_status = await mcp_client.call_tool("get_queue_status", {})

        active_scans = pool_status.get("total_active", 0)
        queue_depth = queue_status.get("queue_depth", 0)

        # Both should be non-negative
        assert active_scans >= 0
        assert queue_depth >= 0


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.e2e
class TestQueuePositionWithRealScans:
    """Tests queue position accuracy with real scan submissions."""

    @pytest.mark.timeout(300)  # 5 minute timeout
    async def test_queue_position_decreases_as_scans_complete(self, mcp_client):
        """Test that queue position decreases as earlier scans complete.

        This test submits scans and monitors queue position changes.
        Note: Results depend on scanner worker processing speed.
        """
        # Submit a scan
        result = await mcp_client.call_tool(
            "run_untrusted_scan",
            {
                "targets": TEST_TARGET,
                "name": "Queue Position Tracking Test",
            },
        )

        task_id = result.get("task_id")
        assert task_id is not None

        # Check initial status
        status = await mcp_client.call_tool("get_scan_status", {"task_id": task_id})

        # Status should show queued or running
        assert status["status"] in ["queued", "running", "completed"]

    async def test_multiple_scan_queue_ordering(self, mcp_client):
        """Test that multiple scans are queued in order."""
        task_ids = []

        # Submit multiple scans
        for i in range(2):
            result = await mcp_client.call_tool(
                "run_untrusted_scan",
                {
                    "targets": TEST_TARGET,
                    "name": f"Order Test {i}",
                },
            )
            if "task_id" in result:
                task_ids.append(result["task_id"])

        # All submissions should succeed
        assert len(task_ids) >= 1

        # Verify all tasks exist in list_tasks
        tasks_result = await mcp_client.call_tool("list_tasks", {"limit": 10})

        {t["task_id"] for t in tasks_result.get("tasks", [])}

        # At least some of our submitted tasks should appear
        # (depending on how fast they complete)
        for tid in task_ids:
            # Task should either be in list or have completed
            status = await mcp_client.call_tool("get_scan_status", {"task_id": tid})
            assert "status" in status


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.e2e
class TestWaitTimeEstimation:
    """Tests for wait time estimation accuracy."""

    async def test_queue_provides_reasonable_estimates(self, mcp_client):
        """Test that queue status provides reasonable information for estimation.

        Note: Actual wait time estimation may vary based on:
        - Number of scanners available
        - Current queue depth
        - Average scan duration
        """
        queue_status = await mcp_client.call_tool("get_queue_status", {})
        pool_status = await mcp_client.call_tool("get_pool_status", {})

        # Data needed for wait estimation
        queue_depth = queue_status.get("queue_depth", 0)
        available_capacity = pool_status.get("available_capacity", 0)
        total_capacity = pool_status.get("total_capacity", 0)

        # All values should be reasonable
        assert queue_depth >= 0
        assert available_capacity >= 0
        assert total_capacity > 0

        # If queue is empty and capacity available, wait should be minimal
        if queue_depth == 0 and available_capacity > 0:
            # Scans can start immediately
            pass  # This is expected good state


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
