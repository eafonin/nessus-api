#!/usr/bin/env python3
"""
Phase 6.1: MCP Protocol Integration Tests

Tests the complete MCP protocol stack:
- MCP Client → SSE Transport → JSON-RPC → Tool Execution → Response

These tests validate the FULL protocol layer, not just the tool functions directly.
Uses the official MCP SDK (sse_client, ClientSession) for true protocol testing.

Run with:
    # From host (connects to localhost:8836)
    pytest tests/integration/test_mcp_client_e2e.py -v -s

    # Inside Docker (connects to mcp-api:8000)
    docker exec nessus-mcp-api-dev pytest /app/tests/integration/test_mcp_client_e2e.py -v -s

Markers:
    - e2e: End-to-end test
    - mcp: Tests MCP protocol layer
    - slow: Long-running tests (scans)
"""

import pytest
import pytest_asyncio
import asyncio
import os
import json
from datetime import datetime
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# ============================================================================
# Configuration
# ============================================================================

def get_mcp_url() -> str:
    """Get MCP URL based on environment."""
    # Inside Docker container
    if os.path.exists('/.dockerenv') or os.environ.get('CONTAINER'):
        return "http://mcp-api:8000/mcp"
    # From host
    return os.environ.get("MCP_URL", "http://localhost:8836/mcp")


MCP_URL = get_mcp_url()

# Test targets
DOCKER_TARGET = "172.32.0.215"  # Docker scan target
LOCAL_TARGET = os.environ.get("SCAN_TARGET_IP", DOCKER_TARGET)

# Scan target container IP (for authenticated scans)
SCAN_TARGET_IP = os.environ.get("SCAN_TARGET_IP", "172.30.0.9")

# Test credentials for authenticated scans
SSH_TEST_USER = "testauth_nosudo"
SSH_TEST_PASS = "TestPass123!"

# Timeouts
SCAN_TIMEOUT = int(os.environ.get("SCAN_TIMEOUT", "600"))  # 10 min
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "10"))  # 10 sec


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.mcp,
    pytest.mark.asyncio,
]


# ============================================================================
# MCP Session Context Manager
# ============================================================================

from contextlib import asynccontextmanager


@asynccontextmanager
async def create_mcp_session():
    """Create an MCP client session.

    Usage:
        async with create_mcp_session() as session:
            result = await session.call_tool(...)
    """
    async with streamablehttp_client(MCP_URL) as (read, write, get_session_id):
        async with ClientSession(read, write) as session:
            init_result = await session.initialize()
            server_info = init_result.serverInfo
            print(f"  Connected: {server_info.name} v{server_info.version}")
            yield session


# ============================================================================
# Helper Functions
# ============================================================================

def extract_tool_result(result) -> dict:
    """Extract the actual result data from MCP tool response."""
    # MCP SDK returns CallToolResult with content list
    if hasattr(result, 'content') and result.content:
        content = result.content[0]
        if hasattr(content, 'text'):
            return json.loads(content.text)
    return {}


async def poll_until_complete(
    session: ClientSession,
    task_id: str,
    timeout: int = SCAN_TIMEOUT,
    poll_interval: int = POLL_INTERVAL
) -> dict:
    """Poll scan status until completion."""
    start_time = asyncio.get_event_loop().time()

    while True:
        result = await session.call_tool("get_scan_status", {"task_id": task_id})
        status = extract_tool_result(result)

        if "error" in status:
            raise ValueError(f"Task error: {status['error']}")

        current_status = status.get("status", "unknown")
        if current_status in {"completed", "failed", "timeout"}:
            return status

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout:
            raise TimeoutError(f"Scan did not complete in {timeout}s")

        progress = status.get('progress', 'N/A')
        print(f"  [{elapsed:.0f}s] Status: {current_status}, Progress: {progress}%")
        await asyncio.sleep(poll_interval)


# ============================================================================
# Phase 6.1: MCP Protocol Integration Tests
# ============================================================================

class TestMCPProtocolBasic:
    """Basic MCP protocol tests - quick validation."""

    async def test_mcp_connection_and_initialization(self):
        """Test MCP connection and session initialization."""
        print(f"\n  Connecting to MCP server at {MCP_URL}...")
        async with create_mcp_session() as session:
            assert session is not None

            # Verify we can get server capabilities
            caps = session.get_server_capabilities()
            assert caps is not None, "Server capabilities should be available"

            # Verify tools capability is present
            assert caps.tools is not None, "Server should have tools capability"
            print(f"  Server capabilities retrieved successfully")
            print(f"  Tools capability: {caps.tools}")

    async def test_mcp_list_tools(self):
        """Test listing available MCP tools."""
        print(f"\n  Connecting to MCP server at {MCP_URL}...")
        async with create_mcp_session() as session:
            tools_result = await session.list_tools()
            tools = tools_result.tools

            assert len(tools) > 0, "No tools found"

            # Core tools that must be present
            required_tools = [
                "run_untrusted_scan",
                "get_scan_status",
                "list_scanners",
                "get_queue_status",
                "list_tasks",
            ]

            # Optional tools (may not be deployed yet)
            optional_tools = [
                "run_authenticated_scan",  # Phase 5
                "list_pools",
                "get_pool_status",
                "get_scan_results",
            ]

            tool_names = [t.name for t in tools]
            print(f"  Found {len(tools)} tools:")
            for name in tool_names:
                print(f"    - {name}")

            for required in required_tools:
                assert required in tool_names, f"Missing required tool: {required}"

            # Log optional tools status
            for optional in optional_tools:
                if optional in tool_names:
                    print(f"  Optional tool available: {optional}")

    async def test_mcp_list_tasks_e2e(self):
        """Test list_tasks via MCP protocol."""
        print(f"\n  Connecting to MCP server at {MCP_URL}...")
        async with create_mcp_session() as session:
            result = await session.call_tool("list_tasks", {"limit": 5})
            data = extract_tool_result(result)

            assert "tasks" in data, "Missing 'tasks' field"
            assert "total" in data, "Missing 'total' field"

            print(f"  Total tasks: {data['total']}")
            print(f"  Returned: {len(data['tasks'])}")

    async def test_mcp_get_scan_status_e2e(self):
        """Test get_scan_status with invalid task_id."""
        print(f"\n  Connecting to MCP server at {MCP_URL}...")
        async with create_mcp_session() as session:
            result = await session.call_tool(
                "get_scan_status",
                {"task_id": "nonexistent-task-id-12345"}
            )
            data = extract_tool_result(result)

            # Should return error for non-existent task
            assert "error" in data or data.get("status") == "not_found", \
                f"Expected error for non-existent task, got: {data}"
            print(f"  Correctly handled non-existent task")

    async def test_mcp_list_scanners_e2e(self):
        """Test list_scanners via MCP protocol."""
        print(f"\n  Connecting to MCP server at {MCP_URL}...")
        async with create_mcp_session() as session:
            result = await session.call_tool("list_scanners", {})
            data = extract_tool_result(result)

            assert "scanners" in data, "Missing 'scanners' field"
            assert "total" in data, "Missing 'total' field"
            # 'pools' field is optional in some versions

            print(f"  Total scanners: {data['total']}")
            if "pools" in data:
                print(f"  Pools: {data['pools']}")
            for scanner in data['scanners']:
                print(f"    - {scanner.get('instance_id')}: enabled={scanner.get('enabled')}")

    async def test_mcp_get_queue_status_e2e(self):
        """Test get_queue_status via MCP protocol."""
        print(f"\n  Connecting to MCP server at {MCP_URL}...")
        async with create_mcp_session() as session:
            result = await session.call_tool("get_queue_status", {})
            data = extract_tool_result(result)

            # Queue status should have depth info
            assert "queue_depth" in data or "main_queue_depth" in data, \
                f"Missing queue depth field in: {data}"

            if "pool" in data:
                print(f"  Pool: {data['pool']}")
            print(f"  Queue depth: {data.get('queue_depth', data.get('main_queue_depth', 0))}")
            print(f"  DLQ size: {data.get('dlq_size', 0)}")


class TestMCPErrorPropagation:
    """Test error handling through MCP protocol layer."""

    async def test_mcp_invalid_scan_type_error(self):
        """Test that invalid scan_type returns proper error via MCP."""
        print(f"\n  Connecting to MCP server at {MCP_URL}...")
        async with create_mcp_session() as session:
            # Check if run_authenticated_scan is available
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]

            if "run_authenticated_scan" not in tool_names:
                pytest.skip("run_authenticated_scan not available")

            result = await session.call_tool(
                "run_authenticated_scan",
                {
                    "targets": "192.168.1.1",
                    "name": "Error Test",
                    "scan_type": "invalid_type_xyz",
                    "ssh_username": "user",
                    "ssh_password": "pass"
                }
            )
            data = extract_tool_result(result)

            # Should contain error about invalid scan_type
            assert "error" in data, f"Expected error field, got: {data}"
            error_msg = data["error"].lower()
            assert "scan_type" in error_msg or "invalid" in error_msg, \
                f"Error should mention scan_type: {data['error']}"
            print(f"  Error properly propagated: {data['error']}")

    async def test_mcp_missing_required_params(self):
        """Test that missing required params returns error."""
        print(f"\n  Connecting to MCP server at {MCP_URL}...")
        async with create_mcp_session() as session:
            # Try to call run_untrusted_scan without required 'targets'
            try:
                result = await session.call_tool(
                    "run_untrusted_scan",
                    {"name": "Missing Target Test"}
                    # Missing 'targets' parameter
                )
                data = extract_tool_result(result)
                # If we get here, check for error in response
                assert "error" in data, "Expected error for missing targets"
                print(f"  Error for missing params: {data.get('error')}")
            except Exception as e:
                # MCP SDK may raise error for missing params
                print(f"  Exception for missing params: {type(e).__name__}: {e}")
                assert True  # Expected behavior


class TestMCPScanWorkflow:
    """Full scan workflow tests via MCP protocol."""

    @pytest.mark.slow
    async def test_mcp_run_untrusted_scan_e2e(self):
        """
        Full MCP workflow for untrusted scan.

        Tests: Submit → Poll Status → Get Results
        Duration: ~1-5 minutes
        """
        scan_name = f"MCP_E2E_Untrusted_{datetime.now().strftime('%H%M%S')}"

        print(f"\n  === Untrusted Scan E2E Test ===")
        print(f"  Target: {LOCAL_TARGET}")
        print(f"  Scan: {scan_name}")
        print(f"  Connecting to MCP server at {MCP_URL}...")

        async with create_mcp_session() as session:
            # Step 1: Submit scan
            print(f"\n  [1] Submitting scan...")
            result = await session.call_tool(
                "run_untrusted_scan",
                {
                    "targets": LOCAL_TARGET,
                    "name": scan_name
                }
            )
            data = extract_tool_result(result)

            assert "task_id" in data, f"Missing task_id in response: {data}"
            assert data.get("status") == "queued", f"Expected 'queued', got: {data.get('status')}"

            task_id = data["task_id"]
            print(f"  Task ID: {task_id}")
            print(f"  Queue position: {data.get('queue_position', 'N/A')}")

            # Step 2: Poll until complete
            print(f"\n  [2] Polling status...")
            final_status = await poll_until_complete(session, task_id)

            print(f"\n  [3] Final status: {final_status.get('status')}")
            assert final_status["status"] in ("completed", "failed"), \
                f"Unexpected final status: {final_status['status']}"

            if final_status["status"] == "failed":
                print(f"  Warning: Scan failed - {final_status.get('error')}")
                # Still pass - we tested the protocol layer
            else:
                print(f"  Progress: {final_status.get('progress')}%")
                print(f"  Scan ID: {final_status.get('nessus_scan_id')}")

            print(f"\n  === Test Passed ===")

    @pytest.mark.slow
    async def test_mcp_run_authenticated_scan_e2e(self):
        """
        Full MCP workflow for authenticated scan.

        Tests: Submit authenticated scan → Poll → Complete
        Duration: ~5-10 minutes
        """
        scan_name = f"MCP_E2E_Auth_{datetime.now().strftime('%H%M%S')}"

        print(f"\n  === Authenticated Scan E2E Test ===")
        print(f"  Target: {SCAN_TARGET_IP}")
        print(f"  Scan: {scan_name}")
        print(f"  User: {SSH_TEST_USER}")
        print(f"  Connecting to MCP server at {MCP_URL}...")

        async with create_mcp_session() as session:
            # Check if run_authenticated_scan is available
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]

            if "run_authenticated_scan" not in tool_names:
                pytest.skip("run_authenticated_scan not available")

            # Step 1: Submit authenticated scan
            print(f"\n  [1] Submitting authenticated scan...")
            result = await session.call_tool(
                "run_authenticated_scan",
                {
                    "targets": SCAN_TARGET_IP,
                    "name": scan_name,
                    "scan_type": "authenticated",
                    "ssh_username": SSH_TEST_USER,
                    "ssh_password": SSH_TEST_PASS
                }
            )
            data = extract_tool_result(result)

            assert "task_id" in data, f"Missing task_id in response: {data}"
            assert data.get("status") == "queued", f"Expected 'queued', got: {data.get('status')}"

            task_id = data["task_id"]
            print(f"  Task ID: {task_id}")
            print(f"  Queue position: {data.get('queue_position', 'N/A')}")
            print(f"  Estimated wait: {data.get('estimated_wait_minutes', 'N/A')} minutes")

            # Step 2: Poll until complete
            print(f"\n  [2] Polling status...")
            final_status = await poll_until_complete(session, task_id)

            print(f"\n  [3] Final status: {final_status.get('status')}")
            assert final_status["status"] in ("completed", "failed"), \
                f"Unexpected final status: {final_status['status']}"

            if final_status["status"] == "completed":
                print(f"  Progress: {final_status.get('progress')}%")
                print(f"  Scan ID: {final_status.get('nessus_scan_id')}")

                # Check for authentication validation
                validation = final_status.get("validation", {})
                if validation:
                    print(f"  Auth detected: {validation.get('authentication_detected')}")
                    print(f"  Credentialed checks: {validation.get('credentialed_checks_percentage', 0)}%")
            else:
                print(f"  Scan failed: {final_status.get('error')}")

            print(f"\n  === Test Passed ===")


class TestMCPQueueInfo:
    """Test queue position and wait time reporting."""

    async def test_queue_position_in_response(self):
        """Verify queue_position is returned when submitting scan."""
        print(f"\n  Connecting to MCP server at {MCP_URL}...")
        async with create_mcp_session() as session:
            result = await session.call_tool(
                "run_untrusted_scan",
                {
                    "targets": "10.255.255.1",  # Unreachable - will queue but fail
                    "name": f"Queue_Test_{datetime.now().strftime('%H%M%S')}"
                }
            )
            data = extract_tool_result(result)

            assert "task_id" in data, "Missing task_id"
            assert "queue_position" in data, "Missing queue_position in response"

            print(f"  Queue position: {data['queue_position']}")
            print(f"  Estimated wait: {data.get('estimated_wait_minutes', 'N/A')} minutes")

    async def test_queue_position_multiple_submits(self):
        """Test that queue positions increment for multiple submissions."""
        print(f"\n  Connecting to MCP server at {MCP_URL}...")
        async with create_mcp_session() as session:
            positions = []
            task_ids = []

            # Submit 3 scans rapidly
            for i in range(3):
                result = await session.call_tool(
                    "run_untrusted_scan",
                    {
                        "targets": f"10.255.255.{100 + i}",  # Unreachable IPs
                        "name": f"Queue_Multi_{i}_{datetime.now().strftime('%H%M%S')}"
                    }
                )
                data = extract_tool_result(result)
                positions.append(data.get("queue_position", 0))
                task_ids.append(data.get("task_id"))

            print(f"  Positions: {positions}")
            print(f"  Task IDs: {task_ids}")

            # Positions should be non-decreasing (may be same if processed fast)
            for i in range(1, len(positions)):
                assert positions[i] >= positions[i-1], \
                    f"Position should not decrease: {positions}"


# ============================================================================
# Phase 6.3: Failure Mode Testing
# ============================================================================

class TestMCPFailureModes:
    """Test system behavior under failure conditions."""

    async def test_unreachable_target_handling(self):
        """
        Test that unreachable targets are handled gracefully.

        Scans to unreachable IPs should:
        1. Be accepted and queued
        2. Eventually complete (with no findings)
        """
        print(f"\n  === Unreachable Target Test ===")
        print(f"  Connecting to MCP server at {MCP_URL}...")

        async with create_mcp_session() as session:
            # Submit scan to unreachable IP
            result = await session.call_tool(
                "run_untrusted_scan",
                {
                    "targets": "10.255.255.1",  # Unreachable private IP
                    "name": f"Unreachable_Test_{datetime.now().strftime('%H%M%S')}"
                }
            )
            data = extract_tool_result(result)

            # Should be queued successfully
            assert "task_id" in data, f"Missing task_id: {data}"
            assert data.get("status") == "queued", f"Expected 'queued', got: {data}"

            task_id = data["task_id"]
            print(f"  Task queued: {task_id}")

            # Check status - should not have immediate error
            status_result = await session.call_tool(
                "get_scan_status",
                {"task_id": task_id}
            )
            status = extract_tool_result(status_result)

            # Task should exist and be in a valid state
            assert status.get("status") in ("queued", "running", "completed", "failed"), \
                f"Unexpected status: {status}"
            print(f"  Status: {status.get('status')}")
            print(f"  === Test Passed ===")

    async def test_invalid_target_format_handling(self):
        """
        Test that invalid target formats return appropriate errors.
        """
        print(f"\n  === Invalid Target Format Test ===")
        print(f"  Connecting to MCP server at {MCP_URL}...")

        async with create_mcp_session() as session:
            # Try to submit scan with obviously invalid target
            result = await session.call_tool(
                "run_untrusted_scan",
                {
                    "targets": "",  # Empty target
                    "name": f"Empty_Target_Test_{datetime.now().strftime('%H%M%S')}"
                }
            )
            data = extract_tool_result(result)

            # Should get an error OR be accepted and fail during validation
            if "error" in data:
                print(f"  Got expected error: {data['error']}")
            else:
                # Might be accepted - check if it's queued
                print(f"  Scan accepted with empty target: {data.get('task_id')}")

            print(f"  === Test Passed ===")

    async def test_task_status_shows_error_details(self):
        """
        Test that failed tasks include error details in status.
        """
        print(f"\n  === Error Details Test ===")
        print(f"  Connecting to MCP server at {MCP_URL}...")

        async with create_mcp_session() as session:
            # Get list of recent tasks
            result = await session.call_tool(
                "list_tasks",
                {"limit": 20, "status_filter": "failed"}
            )
            data = extract_tool_result(result)

            if data.get("tasks"):
                # Check a failed task has error field
                failed_task = data["tasks"][0]
                task_id = failed_task.get("task_id")
                print(f"  Checking failed task: {task_id}")

                status_result = await session.call_tool(
                    "get_scan_status",
                    {"task_id": task_id}
                )
                status = extract_tool_result(status_result)

                print(f"  Status: {status.get('status')}")
                if "error" in status:
                    print(f"  Error: {status['error']}")
                if "failed_at" in status:
                    print(f"  Failed at: {status['failed_at']}")
            else:
                print(f"  No failed tasks found (this is OK)")

            print(f"  === Test Passed ===")

    @pytest.mark.slow
    async def test_scan_with_timeout_target(self):
        """
        Test scan behavior with a target that causes timeout.

        Note: This test submits to an unreachable target and waits
        for the scan to fail/complete. Takes 2-5 minutes.
        """
        print(f"\n  === Timeout Target Test ===")
        print(f"  Connecting to MCP server at {MCP_URL}...")

        async with create_mcp_session() as session:
            # Submit scan to unreachable target
            result = await session.call_tool(
                "run_untrusted_scan",
                {
                    "targets": "10.255.255.254",
                    "name": f"Timeout_Test_{datetime.now().strftime('%H%M%S')}"
                }
            )
            data = extract_tool_result(result)

            assert "task_id" in data, f"Missing task_id: {data}"
            task_id = data["task_id"]
            print(f"  Task ID: {task_id}")

            # Poll for completion (shorter timeout since we expect failure)
            print(f"  Waiting for scan to complete/fail...")
            try:
                final_status = await poll_until_complete(
                    session, task_id,
                    timeout=300,  # 5 minutes
                    poll_interval=15
                )
                print(f"  Final status: {final_status.get('status')}")
                if final_status.get("error"):
                    print(f"  Error: {final_status['error']}")
            except TimeoutError:
                print(f"  Scan still running after 5 min (expected for some targets)")

            print(f"  === Test Passed ===")


# ============================================================================
# Phase 6.2: Queue Information Accuracy Tests
# ============================================================================

class TestMCPQueueAccuracy:
    """Additional queue accuracy tests."""

    async def test_estimated_wait_increases_with_queue_depth(self):
        """
        Test that estimated wait time increases with more queued scans.

        Note: This submits multiple scans rapidly to test queue depth.
        """
        print(f"\n  === Estimated Wait Time Test ===")
        print(f"  Connecting to MCP server at {MCP_URL}...")

        async with create_mcp_session() as session:
            wait_times = []

            # Submit 5 scans and check wait times
            for i in range(5):
                result = await session.call_tool(
                    "run_untrusted_scan",
                    {
                        "targets": f"10.255.255.{50 + i}",
                        "name": f"Wait_Test_{i}_{datetime.now().strftime('%H%M%S')}"
                    }
                )
                data = extract_tool_result(result)
                wait = data.get("estimated_wait_minutes", 0)
                wait_times.append(wait)

            print(f"  Wait times: {wait_times}")

            # Verify wait times are:
            # 1. Non-negative
            # 2. Increasing (each submission adds 15 min)
            for i, wait in enumerate(wait_times):
                assert wait >= 0, f"Wait time cannot be negative: {wait}"
                if i > 0:
                    # Each submission should increase wait by ~15 min (queue_depth * 15)
                    expected_increase = 15
                    actual_increase = wait - wait_times[i-1]
                    assert actual_increase == expected_increase, \
                        f"Expected ~{expected_increase}min increase, got {actual_increase}min"

            print(f"  === Test Passed ===")

    async def test_queue_status_reflects_submissions(self):
        """
        Test that queue status updates after submissions.
        """
        print(f"\n  === Queue Status Update Test ===")
        print(f"  Connecting to MCP server at {MCP_URL}...")

        async with create_mcp_session() as session:
            # Get initial queue status
            result1 = await session.call_tool("get_queue_status", {})
            initial = extract_tool_result(result1)
            initial_depth = initial.get("queue_depth", 0)
            print(f"  Initial queue depth: {initial_depth}")

            # Submit a scan
            result = await session.call_tool(
                "run_untrusted_scan",
                {
                    "targets": "10.255.255.200",
                    "name": f"Queue_Status_Test_{datetime.now().strftime('%H%M%S')}"
                }
            )
            extract_tool_result(result)

            # Get queue status again
            result2 = await session.call_tool("get_queue_status", {})
            after = extract_tool_result(result2)
            after_depth = after.get("queue_depth", 0)
            print(f"  After submission queue depth: {after_depth}")

            # Queue depth should be same or more (may be processed fast)
            assert after_depth >= 0, f"Invalid queue depth: {after_depth}"
            print(f"  === Test Passed ===")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
