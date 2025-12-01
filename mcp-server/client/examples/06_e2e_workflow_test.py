#!/usr/bin/env python3
"""
Example 6: Complete E2E Workflow Test

Demonstrates the complete scan workflow:
1. Submit untrusted scan
2. Wait for completion with progress tracking
3. Export and analyze results

This is a simplified version of the full E2E integration test,
useful for manual testing and demonstration.

Usage:
    python 06_e2e_workflow_test.py [target_ip]

Default target: 172.32.0.215 (internal test host)
"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.nessus_fastmcp_client import NessusFastMCPClient


def print_section(title: str):
    """Print formatted section header."""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def on_progress(status):
    """Progress callback for real-time updates."""
    progress = status.get('progress', 0)
    task_status = status['status']

    # Create progress bar
    bar_length = 40
    filled = int(bar_length * progress / 100)
    bar = '█' * filled + '░' * (bar_length - filled)

    print(f"\r   [{bar}] {progress:3d}% - {task_status:<12}", end='', flush=True)


async def main():
    """Complete E2E workflow demonstration."""

    # Configuration
    target = sys.argv[1] if len(sys.argv) > 1 else "172.32.0.215"
    mcp_url = "http://localhost:8836/mcp"

    print_section("FastMCP Client - Complete E2E Workflow")
    print()
    print(f"  MCP Server: {mcp_url}")
    print(f"  Target:     {target}")
    print()

    try:
        async with NessusFastMCPClient(url=mcp_url, debug=False) as client:

            # ================================================================
            # Step 1: Submit Scan
            # ================================================================

            print_section("Step 1: Submit Scan")

            scan_name = "E2E Test - Manual"
            print(f"  Scan Name: {scan_name}")

            task = await client.submit_scan(
                targets=target,
                scan_name=scan_name,
                description="Manual E2E workflow test",
                scan_type="untrusted"
            )

            task_id = task["task_id"]
            print(f"  ✓ Scan submitted")
            print(f"  Task ID: {task_id}")

            # ================================================================
            # Step 2: Wait for Completion
            # ================================================================

            print_section("Step 2: Wait for Completion")
            print()

            try:
                final_status = await client.wait_for_completion(
                    task_id=task_id,
                    timeout=600,
                    poll_interval=10,
                    progress_callback=on_progress
                )
            except TimeoutError:
                print()
                print()
                print("  ✗ Scan timed out after 10 minutes")
                return

            print()
            print()

            if final_status["status"] == "failed":
                print(f"  ✗ Scan failed: {final_status.get('error', 'Unknown error')}")
                return

            print(f"  ✓ Scan completed successfully")
            print(f"  Task ID: {task_id}")

            # ================================================================
            # Step 3: Get Vulnerability Summary
            # ================================================================

            print_section("Step 3: Vulnerability Summary")

            summary = await client.get_vulnerability_summary(task_id)

            print(f"  Critical (4): {summary.get('4', 0)}")
            print(f"  High (3):     {summary.get('3', 0)}")
            print(f"  Medium (2):   {summary.get('2', 0)}")
            print(f"  Low (1):      {summary.get('1', 0)}")

            total_vulns = sum(summary.values())
            print()
            print(f"  Total:        {total_vulns}")

            # ================================================================
            # Step 4: Export Results (Multiple Schemas)
            # ================================================================

            print_section("Step 4: Export Results")

            # Minimal schema
            results_minimal = await client.get_results(
                task_id=task_id,
                schema_profile="minimal",
                page=1,
                page_size=10
            )

            vuln_count_minimal = len([
                line for line in results_minimal.split('\n')
                if line and json.loads(line).get('type') == 'vulnerability'
            ])

            print(f"  Minimal Schema: {vuln_count_minimal} vulnerabilities (page 1)")

            # Brief schema - all critical
            if summary.get('4', 0) > 0:
                results_critical = await client.get_results(
                    task_id=task_id,
                    schema_profile="brief",
                    filters={"severity": "4"},
                    page=0  # All data
                )

                critical_count = len([
                    line for line in results_critical.split('\n')
                    if line and json.loads(line).get('type') == 'vulnerability'
                ])

                print(f"  Critical Only:  {critical_count} vulnerabilities")

            # ================================================================
            # Step 5: Show Sample Critical Vulnerability
            # ================================================================

            if summary.get('4', 0) > 0:
                print_section("Step 5: Sample Critical Vulnerability")

                critical_vulns = await client.get_critical_vulnerabilities(task_id)

                if critical_vulns:
                    sample = critical_vulns[0]
                    print(f"  Plugin:   {sample.get('plugin_id')} - {sample.get('plugin_name', 'N/A')}")
                    print(f"  Host:     {sample.get('host')}")
                    print(f"  CVSS:     {sample.get('cvss_score', 'N/A')}")
                    if sample.get('cve'):
                        print(f"  CVE:      {sample.get('cve')}")
                    if sample.get('description'):
                        desc = sample['description'][:100]
                        print(f"  Desc:     {desc}...")

            # ================================================================
            # Success
            # ================================================================

            print_section("✓ E2E Workflow Complete")
            print()
            print(f"  Workflow validated:")
            print(f"    ✓ Scan submission")
            print(f"    ✓ Progress monitoring")
            print(f"    ✓ Scan completion")
            print(f"    ✓ Result retrieval")
            print(f"    ✓ Filtering and analysis")
            print()
            print(f"  Task ID: {task_id}")
            print(f"  Total Vulnerabilities: {total_vulns}")
            print()

    except Exception as e:
        print()
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
