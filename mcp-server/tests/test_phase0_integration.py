"""Phase 0 integration test."""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.test_client import NessusMCPClient


@pytest.mark.asyncio
async def test_scan_submission_workflow():
    """Test scan submission and initial status check.

    This test verifies:
    - Scan can be submitted successfully
    - Task ID and trace ID are returned
    - Scanner instance is assigned

    Note: This does NOT wait for scan completion (use E2E tests for that).
    """
    async with NessusMCPClient() as client:
        # Submit scan
        task = await client.submit_scan(
            targets="127.0.0.1",  # Safe localhost target
            name="Integration Test Scan"
        )

        assert "task_id" in task, "Task ID not returned"
        assert "trace_id" in task, "Trace ID not returned"
        assert task["status"] == "queued", f"Unexpected status: {task['status']}"
        assert "scanner_instance" in task, "Scanner instance not assigned"

        # Verify we can get status immediately
        status = await client.get_status(task["task_id"])
        assert status["task_id"] == task["task_id"]
        assert "status" in status


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
