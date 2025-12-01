#!/usr/bin/env python3
"""
Example 2: Wait for Scan Completion

Demonstrates:
- Polling scan status
- Progress monitoring with callbacks
- Handling scan completion
- Timeout handling

Usage:
    python 02_wait_for_completion.py [task_id]

    If no task_id provided, submits a new scan first.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.nessus_fastmcp_client import NessusFastMCPClient


def progress_callback(status):
    """Callback function for progress updates."""
    progress = status.get('progress', 0)
    task_status = status['status']
    print(f"   Progress: {progress}% - Status: {task_status}")


async def main():
    """Wait for completion example."""

    async with NessusFastMCPClient(
        url="http://localhost:8836/mcp",
        debug=False  # Disable debug for cleaner output
    ) as client:

        # Get task_id from command line or submit new scan
        if len(sys.argv) > 1:
            task_id = sys.argv[1]
            print(f"Monitoring existing scan: {task_id}\n")
        else:
            print("No task_id provided. Submitting new scan...\n")
            task = await client.submit_scan(
                targets="192.168.1.1",
                scan_name="Example Wait Scan",
                description="Demonstration scan from Example 2"
            )
            task_id = task["task_id"]
            print(f"Scan submitted: {task_id}\n")

        # Wait for completion with progress callback
        print("Waiting for scan to complete...")
        print("(This may take 5-10 minutes for a real Nessus scan)\n")

        try:
            final_status = await client.wait_for_completion(
                task_id=task_id,
                timeout=600,  # 10 minutes
                poll_interval=10,  # Check every 10 seconds
                progress_callback=progress_callback
            )

            print(f"\n✓ Scan completed!")
            print(f"   Status: {final_status['status']}")
            print(f"   Duration: {final_status.get('duration_seconds', 'N/A')} seconds")

            if final_status['status'] == 'completed':
                print(f"\nNext: Retrieve results with:")
                print(f"  python 04_get_critical_vulns.py {task_id}")
            else:
                print(f"\n⚠ Scan finished with status: {final_status['status']}")

        except TimeoutError:
            print(f"\n✗ Scan did not complete within 600 seconds")
            print(f"   Task may still be running. Check status manually:")
            print(f"   python 01_basic_usage.py")


if __name__ == "__main__":
    asyncio.run(main())
