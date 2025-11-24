#!/usr/bin/env python3
"""
Interactive E2E Test - Run Full Workflow with Progress Display

This script runs the complete E2E workflow and displays progress in real-time.
Perfect for manual validation and Web UI cross-checking.

Usage:
    python run_e2e_test_interactive.py [target_ip]
"""

import asyncio
import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from client.nessus_fastmcp_client import NessusFastMCPClient


def print_section(title: str):
    """Print formatted section header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()


def print_progress(status: dict):
    """Print progress bar."""
    progress = status.get('progress', 0)
    task_status = status.get('status', 'unknown')

    # Create progress bar
    bar_length = 50
    filled = int(bar_length * progress / 100)
    bar = '█' * filled + '░' * (bar_length - filled)

    elapsed_time = ""
    if status.get('started_at'):
        # Simple timestamp display
        elapsed_time = f" | Started: {status['started_at'][-8:]}"

    print(f"\r  [{bar}] {progress:3d}% - {task_status:<12}{elapsed_time}", end='', flush=True)


async def main():
    """Run interactive E2E test."""

    # Configuration
    target = sys.argv[1] if len(sys.argv) > 1 else "172.32.0.215"
    mcp_url = "http://mcp-api:8000/mcp"

    print_section("FastMCP Client - Full E2E Test with Scan Completion")
    print(f"  MCP Server: {mcp_url}")
    print(f"  Target:     {target}")
    print(f"  Started:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        async with NessusFastMCPClient(url=mcp_url, timeout=30) as client:

            # ==================================================================
            # Step 1: Connect and Verify
            # ==================================================================

            print_section("Step 1: Connect to MCP Server")
            await client.ping()
            print("  ✓ Connected and verified")

            tools = await client.list_tools()
            print(f"  ✓ Found {len(tools)} MCP tools")

            # ==================================================================
            # Step 2: Submit Scan
            # ==================================================================

            print_section("Step 2: Submit Untrusted Scan")
            scan_name = f"E2E Test - {datetime.now().strftime('%Y%m%d-%H%M%S')}"
            print(f"  Scan Name: {scan_name}")
            print(f"  Target:    {target}")

            task = await client.submit_scan(
                targets=target,
                scan_name=scan_name,
                description="Full E2E test with Web UI validation",
                scan_type="untrusted"
            )

            task_id = task["task_id"]
            print(f"  ✓ Scan submitted successfully")
            print(f"  Task ID: {task_id}")
            print()

            # ==================================================================
            # IMPORTANT: MANUAL WEB UI VALIDATION POINT
            # ==================================================================

            print_section("⚠️  WEB UI VALIDATION CHECKPOINT")
            print("  Please verify in the Nessus Web UI:")
            print()
            print(f"  1. Open: https://172.32.0.209:8443/")
            print(f"     (Scanner 1 Web UI)")
            print()
            print(f"  2. Navigate to: My Scans")
            print()
            print(f"  3. Find scan: \"{scan_name}\"")
            print()
            print(f"  4. Verify:")
            print(f"     - Scan status shows 'Running' or 'Pending'")
            print(f"     - Target: {target}")
            print(f"     - Policy: Basic Network Scan")
            print()
            print("  Press ENTER to continue monitoring...")
            input()

            # ==================================================================
            # Step 3: Wait for Completion with Progress
            # ==================================================================

            print_section("Step 3: Monitor Scan Progress")
            print("  Waiting for scan completion (5-10 minutes)...")
            print()

            start_time = time.time()
            last_progress = -1

            try:
                while True:
                    status = await client.get_status(task_id)

                    # Display progress if changed
                    current_progress = status.get('progress', 0)
                    if current_progress != last_progress:
                        print_progress(status)
                        last_progress = current_progress

                    # Check for completion
                    task_status = status.get('status')
                    if task_status in ['completed', 'failed', 'cancelled']:
                        print()  # New line after progress bar
                        print()
                        break

                    # Wait before next check
                    await asyncio.sleep(10)

                    # Timeout check
                    if time.time() - start_time > 600:
                        print()
                        print()
                        print("  ⚠️  Timeout reached (10 minutes)")
                        print("  Scan may still be running - check Web UI")
                        return

                elapsed = time.time() - start_time

                if task_status == 'completed':
                    print(f"  ✓ Scan completed successfully!")
                    print(f"  Duration: {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
                else:
                    print(f"  ✗ Scan failed with status: {task_status}")
                    if status.get('error_message'):
                        print(f"  Error: {status['error_message']}")
                    return

                # ==================================================================
                # IMPORTANT: MANUAL WEB UI VALIDATION POINT #2
                # ==================================================================

                print_section("⚠️  WEB UI VALIDATION CHECKPOINT #2")
                print("  Please verify scan completion in Web UI:")
                print()
                print(f"  1. Refresh the Nessus Web UI")
                print(f"  2. Find scan: \"{scan_name}\"")
                print(f"  3. Verify:")
                print(f"     - Status shows 'Completed'")
                print(f"     - Vulnerabilities count matches results below")
                print(f"     - Can view/export results")
                print()
                print("  Press ENTER to retrieve results...")
                input()

                # ==================================================================
                # Step 4: Retrieve Results
                # ==================================================================

                print_section("Step 4: Retrieve Scan Results")

                # Get vulnerability summary
                summary = await client.get_vulnerability_summary(task_id)

                print("  Vulnerability Summary:")
                print(f"    Critical (4): {summary.get('4', 0)}")
                print(f"    High (3):     {summary.get('3', 0)}")
                print(f"    Medium (2):   {summary.get('2', 0)}")
                print(f"    Low (1):      {summary.get('1', 0)}")
                total_vulns = sum(summary.values())
                print(f"    ─────────────────────────")
                print(f"    Total:        {total_vulns}")
                print()

                # Get critical vulnerabilities details
                if summary.get('4', 0) > 0:
                    print(f"  Retrieving critical vulnerabilities...")
                    critical_vulns = await client.get_critical_vulnerabilities(task_id)
                    print(f"  ✓ Retrieved {len(critical_vulns)} critical vulnerabilities")

                    if critical_vulns:
                        print()
                        print("  Sample Critical Vulnerability:")
                        sample = critical_vulns[0]
                        print(f"    Plugin ID:   {sample.get('plugin_id')}")
                        print(f"    Name:        {sample.get('plugin_name', 'N/A')}")
                        print(f"    Host:        {sample.get('host')}")
                        print(f"    CVSS Score:  {sample.get('cvss_score', 'N/A')}")
                        if sample.get('cve'):
                            print(f"    CVE:         {sample.get('cve')}")

                # ==================================================================
                # IMPORTANT: MANUAL WEB UI VALIDATION POINT #3
                # ==================================================================

                print_section("⚠️  FINAL WEB UI VALIDATION")
                print("  Please compare results with Web UI:")
                print()
                print(f"  1. In Web UI, click on scan: \"{scan_name}\"")
                print(f"  2. View 'Vulnerabilities' tab")
                print(f"  3. Compare counts:")
                print(f"     - Critical: Web UI = {summary.get('4', 0)} (should match)")
                print(f"     - High:     Web UI = {summary.get('3', 0)} (should match)")
                print(f"     - Medium:   Web UI = {summary.get('2', 0)} (should match)")
                print(f"     - Low:      Web UI = {summary.get('1', 0)} (should match)")
                print()
                print(f"  4. Verify a few vulnerabilities match by:")
                print(f"     - Plugin ID")
                print(f"     - Name")
                print(f"     - Severity")
                print()

                # ==================================================================
                # Success Summary
                # ==================================================================

                print_section("✅ E2E Test COMPLETED Successfully")
                print()
                print("  Results Summary:")
                print(f"    ✓ Scan submitted via FastMCP client")
                print(f"    ✓ Scan completed in {elapsed/60:.1f} minutes")
                print(f"    ✓ Total vulnerabilities found: {total_vulns}")
                print(f"    ✓ Results retrieved and parsed")
                print()
                print("  Validation Steps:")
                print(f"    ☑ Verified scan in Web UI (during execution)")
                print(f"    ☑ Verified completion in Web UI")
                print(f"    ☑ Compared vulnerability counts (Web UI vs API)")
                print()
                print(f"  Task ID: {task_id}")
                print(f"  Scan Name: {scan_name}")
                print()

    except Exception as e:
        print()
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
