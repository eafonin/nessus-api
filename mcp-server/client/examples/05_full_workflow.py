#!/usr/bin/env python3
"""
Example 5: Complete Scan Workflow

Demonstrates:
- Full end-to-end scan workflow
- Comprehensive error handling
- Queue status monitoring
- Scanner information
- Result parsing and analysis

Usage:
    python 05_full_workflow.py
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.nessus_fastmcp_client import NessusFastMCPClient


async def main():
    """Complete workflow example with error handling."""

    print("="  * 70)
    print(" " * 15 + "NESSUS MCP CLIENT - FULL WORKFLOW")
    print("=" * 70)
    print()

    try:
        async with NessusFastMCPClient(
            url="http://localhost:8835/mcp",
            timeout=60.0,
            debug=True
        ) as client:

            # Step 1: Server health check
            print("STEP 1: Server Health Check")
            print("-" * 70)
            try:
                await client.ping()
                print("✓ MCP server is healthy")
            except Exception as e:
                print(f"✗ Server unreachable: {e}")
                return
            print()

            # Step 2: List available scanners
            print("STEP 2: Available Scanners")
            print("-" * 70)
            scanners_info = await client.list_scanners()
            scanners = scanners_info.get('scanners', [])
            print(f"Registered scanners: {len(scanners)}")
            for scanner in scanners:
                status = "✓ Enabled" if scanner.get('enabled') else "✗ Disabled"
                print(f"  - {scanner.get('name')} ({scanner.get('scanner_type')}): {status}")
            print()

            # Step 3: Check queue status
            print("STEP 3: Queue Status")
            print("-" * 70)
            queue = await client.get_queue_status()
            print(f"Main queue depth: {queue.get('main_queue_depth', 0)}")
            print(f"Dead letter queue: {queue.get('dlq_depth', 0)}")
            if queue.get('main_queue_depth', 0) > 0:
                print("⚠ Queue has pending tasks. Your scan will be queued.")
            print()

            # Step 4: Submit scan
            print("STEP 4: Submit Scan")
            print("-" * 70)

            targets = input("Enter target IP/range (default: 192.168.1.1): ").strip() or "192.168.1.1"
            scan_name = f"Full Workflow Scan - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            task = await client.submit_scan(
                targets=targets,
                scan_name=scan_name,
                description="Complete workflow demonstration"
            )

            task_id = task["task_id"]
            print(f"✓ Scan submitted successfully")
            print(f"  Task ID: {task_id}")
            print(f"  Status: {task['status']}")
            print(f"  Idempotent: {task.get('idempotent', False)}")
            print()

            # Step 5: Wait for completion with progress
            print("STEP 5: Monitor Scan Progress")
            print("-" * 70)
            print("Waiting for scan to complete (timeout: 10 minutes)...")
            print()

            def progress_callback(status):
                progress = status.get('progress', 0)
                task_status = status['status']
                bar_length = 50
                filled = int(bar_length * progress / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f"\r  [{bar}] {progress}% - {task_status}", end='', flush=True)

            try:
                final_status = await client.wait_for_completion(
                    task_id=task_id,
                    timeout=600,
                    poll_interval=10,
                    progress_callback=progress_callback
                )
                print()  # New line after progress bar
                print()
                print(f"✓ Scan completed: {final_status['status']}")

            except TimeoutError:
                print()
                print()
                print("✗ Scan timed out after 10 minutes")
                print("  The scan may still be running. Check status manually.")
                return
            print()

            # Step 6: Retrieve and analyze results
            print("STEP 6: Analyze Results")
            print("-" * 70)

            # Get vulnerability summary
            summary = await client.get_vulnerability_summary(task_id)

            print("Vulnerability Summary by Severity:")
            print(f"  Critical (4): {summary.get('4', 0)}")
            print(f"  High (3):     {summary.get('3', 0)}")
            print(f"  Medium (2):   {summary.get('2', 0)}")
            print(f"  Low (1):      {summary.get('1', 0)}")
            total = sum(summary.values())
            print(f"  Total:        {total}")
            print()

            if summary.get('4', 0) > 0:
                # Get critical vulnerabilities
                print("Critical Vulnerabilities:")
                critical = await client.get_critical_vulnerabilities(task_id)

                for i, vuln in enumerate(critical[:5], 1):
                    print(f"\n  {i}. {vuln.get('plugin_name', 'Unknown')}")
                    print(f"     Host: {vuln.get('host')}")
                    print(f"     CVSS: {vuln.get('cvss_score', 'N/A')}")
                    cve = vuln.get('cve', [])
                    if cve:
                        print(f"     CVE: {', '.join(cve if isinstance(cve, list) else [cve])}")
                    if vuln.get('exploit_available'):
                        print(f"     ⚠ EXPLOIT AVAILABLE")

                if len(critical) > 5:
                    print(f"\n  ... and {len(critical) - 5} more critical vulnerabilities")
            else:
                print("No critical vulnerabilities found.")
            print()

            # Step 7: Export results (demo - show JSON-NL format)
            print("STEP 7: Export Options")
            print("-" * 70)
            print("JSON-NL format available for export:")
            print(f"  - All data: page=0")
            print(f"  - Paginated: page=1, page_size=40")
            print(f"  - Filtered: filters={{'severity': '4'}}")
            print()

            # Get first page of all vulns
            results = await client.get_results(
                task_id=task_id,
                schema_profile="minimal",
                page=1,
                page_size=5
            )

            lines = results.strip().split('\n')
            print(f"Sample output ({len(lines)} lines):")
            for line in lines[:3]:
                data = json.loads(line)
                print(f"  - Type: {data.get('type')}")
            print()

            # Success summary
            print("=" * 70)
            print(" " * 25 + "WORKFLOW COMPLETE")
            print("=" * 70)
            print()
            print(f"✓ Successfully scanned {targets}")
            print(f"✓ Found {total} total vulnerabilities")
            print(f"✓ Task ID: {task_id}")
            print()

    except KeyboardInterrupt:
        print()
        print()
        print("⚠ Interrupted by user")
    except Exception as e:
        print()
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
