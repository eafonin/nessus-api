"""Phase 0 integration test."""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.test_client import NessusMCPClient


@pytest.mark.asyncio
async def test_mock_scan_workflow():
    """Test complete mock scan workflow."""
    async with NessusMCPClient() as client:
        # Submit scan
        task = await client.submit_scan(
            targets="192.168.1.1",
            name="Integration Test Scan"
        )

        assert "task_id" in task, "Task ID not returned"
        assert "trace_id" in task, "Trace ID not returned"
        assert task["status"] == "queued", f"Unexpected status: {task['status']}"
        assert task["scanner_instance"] == "mock", "Wrong scanner instance"

        # Poll until complete
        final_status = await client.poll_until_complete(
            task["task_id"],
            timeout=30  # Mock scan should complete in <10s
        )

        assert final_status["status"] == "completed", f"Scan did not complete: {final_status}"
        assert final_status.get("progress") == 100, "Progress not 100%"
        assert final_status["nessus_scan_id"] is not None, "No scan ID"
        assert final_status["started_at"] is not None, "No start time"
        assert final_status["completed_at"] is not None, "No completion time"


@pytest.mark.asyncio
async def test_get_status_nonexistent_task():
    """Test status check for non-existent task."""
    async with NessusMCPClient() as client:
        status = await client.get_status("nonexistent_task_id")
        assert "error" in status, "Should return error for non-existent task"
        assert "not found" in status["error"].lower()


if __name__ == "__main__":
    # Run with: pytest tests/test_phase0_integration.py -v
    pytest.main([__file__, "-v", "-s"])
