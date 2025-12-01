#!/usr/bin/env python3
"""
Example 1: Basic FastMCP Client Usage

Demonstrates:
- Connecting to MCP server
- Submitting a scan
- Checking scan status
- Basic error handling

Usage:
    python 01_basic_usage.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.nessus_fastmcp_client import NessusFastMCPClient


async def main():
    """Basic usage example."""

    # Create client (debug=True for verbose logging)
    async with NessusFastMCPClient(
        url="http://localhost:8836/mcp",
        timeout=30.0,
        debug=True
    ) as client:

        # 1. Ping server to verify connection
        print("1. Pinging MCP server...")
        await client.ping()
        print("   ✓ Server is reachable\n")

        # 2. List available tools
        print("2. Listing available MCP tools...")
        tools = await client.list_tools()
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description']}")
        print()

        # 3. Submit a scan
        print("3. Submitting scan...")
        task = await client.submit_scan(
            targets="192.168.1.1",
            scan_name="Example Basic Scan",
            description="Demonstration scan from Example 1"
        )

        task_id = task["task_id"]
        print(f"   ✓ Scan submitted: {task_id}")
        print(f"   Status: {task['status']}\n")

        # 4. Check scan status
        print("4. Checking scan status...")
        status = await client.get_status(task_id)
        print(f"   Task ID: {status['task_id']}")
        print(f"   Status: {status['status']}")
        print(f"   Progress: {status.get('progress', 0)}%\n")

        # 5. List all tasks
        print("5. Listing recent tasks...")
        tasks = await client.list_tasks(limit=5)
        print(f"   Total tasks: {tasks['total']}")
        for t in tasks['tasks'][:3]:
            print(f"   - {t['task_id']}: {t['status']}")
        print()

        print("✓ Example completed successfully!")
        print(f"\nNext: Wait for scan to complete with:")
        print(f"  python 02_wait_for_completion.py {task_id}")


if __name__ == "__main__":
    asyncio.run(main())
