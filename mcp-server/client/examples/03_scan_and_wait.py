#!/usr/bin/env python3
"""
Example 3: Scan and Wait (Convenience Method)

Demonstrates:
- One-line scan submission and completion waiting
- Progress monitoring during execution
- Handling scan results

Usage:
    python 03_scan_and_wait.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.nessus_fastmcp_client import NessusFastMCPClient


def on_progress(status):
    """Progress callback for real-time updates."""
    progress = status.get('progress', 0)
    task_status = status['status']

    # Create progress bar
    bar_length = 40
    filled = int(bar_length * progress / 100)
    bar = '█' * filled + '░' * (bar_length - filled)

    print(f"\r   [{bar}] {progress}% - {task_status}", end='', flush=True)


async def main():
    """Scan and wait example."""

    async with NessusFastMCPClient(
        url="http://localhost:8836/mcp",
        debug=False
    ) as client:

        print("Scan and Wait Example")
        print("=" * 60)
        print()

        targets = input("Enter target IP (default: 192.168.1.1): ").strip() or "192.168.1.1"
        scan_name = input("Enter scan name (default: Quick Scan): ").strip() or "Quick Scan"

        print()
        print(f"Submitting scan: {scan_name}")
        print(f"Targets: {targets}")
        print()

        # One method call handles submit + wait
        try:
            final_status = await client.scan_and_wait(
                targets=targets,
                scan_name=scan_name,
                description="Automated scan from Example 3",
                timeout=600,
                poll_interval=10,
                progress_callback=on_progress
            )

            print()  # New line after progress bar
            print()
            print("✓ Scan completed successfully!")
            print()
            print("Scan Details:")
            print(f"  Task ID: {final_status['task_id']}")
            print(f"  Status: {final_status['status']}")
            print(f"  Progress: {final_status.get('progress', 0)}%")

            # Get quick summary
            task_id = final_status['task_id']
            summary = await client.get_vulnerability_summary(task_id)

            print()
            print("Vulnerability Summary:")
            print(f"  Critical (4): {summary.get('4', 0)}")
            print(f"  High (3):     {summary.get('3', 0)}")
            print(f"  Medium (2):   {summary.get('2', 0)}")
            print(f"  Low (1):      {summary.get('1', 0)}")
            print()

            total = sum(summary.values())
            if total > 0:
                print(f"Total vulnerabilities found: {total}")
                print()
                print(f"Get detailed results with:")
                print(f"  python 04_get_critical_vulns.py {task_id}")
            else:
                print("No vulnerabilities found.")

        except TimeoutError:
            print()
            print("✗ Scan timed out after 600 seconds")
            print("  The scan may still be running in the background.")


if __name__ == "__main__":
    asyncio.run(main())
