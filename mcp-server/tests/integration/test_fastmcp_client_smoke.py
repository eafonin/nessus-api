#!/usr/bin/env python3
"""
FastMCP Client Smoke Test

Quick validation test that verifies FastMCP client can:
1. Connect to MCP server
2. Submit a scan
3. Monitor scan progress (briefly)
4. Retrieve basic status

This test does NOT wait for scan completion (fast test).

Run with:
    docker compose exec mcp-api pytest tests/integration/test_fastmcp_client_smoke.py -v -s
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.nessus_fastmcp_client import NessusFastMCPClient


# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-api:8000/mcp")
TARGET_HOST = os.getenv("TEST_TARGET", "172.32.0.215")

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.asyncio
async def test_fastmcp_client_smoke():
    """
    Smoke test: Verify FastMCP client can connect, submit scan, and get status.

    This is a quick test that doesn't wait for scan completion.
    """

    print()
    print("=" * 70)
    print("FastMCP Client Smoke Test")
    print("=" * 70)
    print()

    async with NessusFastMCPClient(url=MCP_SERVER_URL, timeout=30) as client:

        # Step 1: Connection
        print("✓ Step 1: Connected to MCP server")
        assert client.is_connected()

        # Step 2: Ping
        ping_result = await client.ping()
        assert ping_result is True
        print("✓ Step 2: Ping successful")

        # Step 3: List tools
        tools = await client.list_tools()
        assert len(tools) >= 6
        tool_names = [t["name"] for t in tools]
        assert "run_untrusted_scan" in tool_names
        assert "get_scan_status" in tool_names
        assert "get_scan_results" in tool_names
        print(f"✓ Step 3: Found {len(tools)} MCP tools")

        # Step 4: Get queue status
        queue = await client.get_queue_status()
        assert "queue_depth" in queue or "main_queue_depth" in queue
        print(f"✓ Step 4: Queue status retrieved")

        # Step 5: List scanners
        scanners = await client.list_scanners()
        assert "scanners" in scanners
        assert len(scanners["scanners"]) > 0
        print(f"✓ Step 5: Found {len(scanners['scanners'])} scanner(s)")

        # Step 6: Submit scan
        scan_name = f"Smoke Test - {datetime.now().strftime('%Y%m%d-%H%M%S')}"
        task = await client.submit_scan(
            targets=TARGET_HOST,
            scan_name=scan_name,
            description="FastMCP client smoke test",
            scan_type="untrusted"
        )

        assert "task_id" in task
        assert task["status"] == "queued"
        task_id = task["task_id"]
        print(f"✓ Step 6: Scan submitted - Task ID: {task_id}")

        # Step 7: Get status immediately
        status = await client.get_status(task_id)
        assert status["task_id"] == task_id
        assert "status" in status
        print(f"✓ Step 7: Status retrieved - {status['status']}")

        # Step 8: Wait briefly to see if scan starts
        print("  Waiting 15 seconds to check scan progress...")
        await asyncio.sleep(15)

        status = await client.get_status(task_id)
        print(f"✓ Step 8: Status after 15s - {status['status']} ({status.get('progress', 0)}%)")

        # Step 9: List recent tasks
        tasks = await client.list_tasks(limit=5)
        assert "tasks" in tasks
        assert "total" in tasks
        print(f"✓ Step 9: Listed tasks - {tasks['total']} total")

        print()
        print("=" * 70)
        print("✅ SMOKE TEST PASSED - All FastMCP Client Operations Work!")
        print("=" * 70)
        print()
        print(f"Task {task_id} is running in background")
        print("For full E2E test with completion, run: test_fastmcp_client_e2e.py")
        print()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
