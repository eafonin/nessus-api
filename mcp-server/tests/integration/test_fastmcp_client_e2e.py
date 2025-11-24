#!/usr/bin/env python3
"""
End-to-End Integration Test: FastMCP Client Complete Workflow

This test validates the complete scan workflow using the FastMCP client:
1. Submit scan (untrusted/unauthenticated)
2. Wait for completion
3. Export and validate results

This serves as the FINAL validation layer that tests the entire stack:
- FastMCP Client → MCP Server (HTTP/SSE) → Redis Queue → Scanner Worker → Nessus Scanner

Run with:
    # Inside Docker (recommended)
    docker compose exec mcp-api pytest tests/integration/test_fastmcp_client_e2e.py -v -s

    # Outside Docker (requires MCP server at localhost:8835)
    pytest tests/integration/test_fastmcp_client_e2e.py -v -s

Markers:
    - e2e: End-to-end test covering entire workflow
    - real_nessus: Uses actual Nessus scanner (NOT mocks)
    - slow: Takes 5-10 minutes to complete
    - integration: Integration test requiring external services
"""

import pytest
import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add mcp-server to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.nessus_fastmcp_client import NessusFastMCPClient


# ============================================================================
# Test Configuration
# ============================================================================

# MCP Server URL
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8835/mcp")

# Test target (safe internal host for scanning)
# Default: Internal Docker network host
TARGET_HOST = os.getenv("TEST_TARGET", "172.32.0.215")

# Timeout for scan completion (seconds)
SCAN_TIMEOUT = int(os.getenv("SCAN_TIMEOUT", "600"))  # 10 minutes

# Poll interval for status checks (seconds)
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = [
    pytest.mark.e2e,                      # End-to-end test
    pytest.mark.real_nessus,              # Uses real Nessus scanner
    pytest.mark.slow,                     # Takes several minutes
    pytest.mark.integration,              # Integration test
    pytest.mark.asyncio,                  # Async test
]


# ============================================================================
# Test Helpers
# ============================================================================

def print_section(title: str):
    """Print formatted section header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_status(status: dict):
    """Print formatted status information."""
    print(f"  Task ID:      {status.get('task_id')}")
    print(f"  Status:       {status.get('status')}")
    print(f"  Progress:     {status.get('progress', 0)}%")
    print(f"  Scan Name:    {status.get('scan_name', 'N/A')}")

    if status.get('nessus_scan_id'):
        print(f"  Nessus Scan:  {status['nessus_scan_id']}")

    if status.get('error'):
        print(f"  Error:        {status['error']}")


def print_progress(status: dict):
    """Print progress bar."""
    progress = status.get('progress', 0)
    task_status = status.get('status', 'unknown')

    # Create progress bar
    bar_length = 40
    filled = int(bar_length * progress / 100)
    bar = '█' * filled + '░' * (bar_length - filled)

    print(f"\r  [{bar}] {progress:3d}% - {task_status:<12}", end='', flush=True)


def parse_jsonl_results(jsonl_data: str) -> dict:
    """Parse JSON-NL results into structured data."""
    parsed = {
        "schema": None,
        "metadata": None,
        "vulnerabilities": [],
        "pagination": None
    }

    for line in jsonl_data.strip().split('\n'):
        if not line.strip():
            continue

        data = json.loads(line)
        data_type = data.get("type")

        if data_type == "schema":
            parsed["schema"] = data
        elif data_type == "metadata":
            parsed["metadata"] = data
        elif data_type == "vulnerability":
            parsed["vulnerabilities"].append(data)
        elif data_type == "pagination":
            parsed["pagination"] = data

    return parsed


# ============================================================================
# Test: Complete E2E Workflow with FastMCP Client
# ============================================================================

@pytest.mark.asyncio
async def test_complete_e2e_workflow_untrusted_scan():
    """
    Test complete end-to-end workflow using FastMCP client.

    This test validates:
    1. Client connection to MCP server
    2. Scan submission (untrusted/unauthenticated)
    3. Status monitoring with progress tracking
    4. Waiting for completion
    5. Result retrieval with multiple schema profiles
    6. Result parsing and validation

    Expected behavior:
    - Scan completes successfully within timeout
    - Progress updates are received
    - Results are in valid JSON-NL format
    - Vulnerabilities are found (host is intentionally vulnerable)
    """

    print_section("Phase 3 E2E Test: FastMCP Client Complete Workflow")

    # ========================================================================
    # Step 1: Connect to MCP Server
    # ========================================================================

    print_section("Step 1: Connect to MCP Server")
    print(f"  MCP Server: {MCP_SERVER_URL}")

    async with NessusFastMCPClient(url=MCP_SERVER_URL, debug=False) as client:

        # Verify connection
        ping_result = await client.ping()
        assert ping_result is True, "Failed to ping MCP server"
        print("  ✓ Connected successfully")

        # List available tools
        tools = await client.list_tools()
        tool_names = [t["name"] for t in tools]
        print(f"  ✓ Found {len(tools)} MCP tools")
        assert "run_untrusted_scan" in tool_names
        assert "get_scan_status" in tool_names
        assert "get_scan_results" in tool_names

        # ====================================================================
        # Step 2: Submit Scan
        # ====================================================================

        print_section("Step 2: Submit Untrusted Scan")
        scan_name = f"E2E Test - {datetime.now().strftime('%Y%m%d-%H%M%S')}"
        print(f"  Scan Name: {scan_name}")
        print(f"  Target:    {TARGET_HOST}")

        task = await client.submit_scan(
            targets=TARGET_HOST,
            scan_name=scan_name,
            description="End-to-end integration test using FastMCP client",
            scan_type="untrusted"
        )

        # Validate submission response
        assert "task_id" in task, "task_id missing from submission response"
        assert task["status"] == "queued", f"Expected status 'queued', got '{task['status']}'"

        task_id = task["task_id"]
        print(f"  ✓ Scan submitted successfully")
        print(f"  Task ID: {task_id}")
        print(f"  Status:  {task['status']}")

        # ====================================================================
        # Step 3: Monitor Progress
        # ====================================================================

        print_section("Step 3: Wait for Scan Completion")
        print(f"  Timeout:       {SCAN_TIMEOUT}s")
        print(f"  Poll Interval: {POLL_INTERVAL}s")
        print()

        # Track progress updates
        progress_updates = []

        def on_progress(status: dict):
            """Callback for progress updates."""
            progress_updates.append(status)
            print_progress(status)

        # Wait for completion
        try:
            final_status = await client.wait_for_completion(
                task_id=task_id,
                timeout=SCAN_TIMEOUT,
                poll_interval=POLL_INTERVAL,
                progress_callback=on_progress
            )
        except TimeoutError as e:
            print()
            print()
            print(f"  ✗ Timeout: Scan did not complete within {SCAN_TIMEOUT}s")

            # Get final status for debugging
            status = await client.get_status(task_id)
            print()
            print_status(status)

            pytest.fail(f"Scan timed out after {SCAN_TIMEOUT}s")

        print()  # New line after progress bar
        print()

        # Validate completion
        assert final_status["status"] in ["completed", "failed"], \
            f"Expected terminal state, got '{final_status['status']}'"

        if final_status["status"] == "failed":
            print("  ✗ Scan failed")
            print_status(final_status)
            pytest.fail(f"Scan failed: {final_status.get('error', 'Unknown error')}")

        print("  ✓ Scan completed successfully")
        print_status(final_status)

        # Validate progress updates
        assert len(progress_updates) > 0, "No progress updates received"
        print(f"  ✓ Received {len(progress_updates)} progress updates")

        # ====================================================================
        # Step 4: Retrieve Results - Minimal Schema
        # ====================================================================

        print_section("Step 4: Retrieve Results (Minimal Schema)")

        results_minimal = await client.get_results(
            task_id=task_id,
            schema_profile="minimal",
            page=1,
            page_size=100
        )

        # Validate results format
        assert isinstance(results_minimal, str), "Results should be a string (JSON-NL)"
        assert len(results_minimal) > 0, "Results are empty"

        # Parse JSON-NL
        parsed_minimal = parse_jsonl_results(results_minimal)

        # Validate schema line
        assert parsed_minimal["schema"] is not None, "Schema missing"
        assert parsed_minimal["schema"]["type"] == "schema"
        assert parsed_minimal["schema"]["profile"] == "minimal"
        print(f"  ✓ Schema: {parsed_minimal['schema']['profile']}")

        # Validate metadata line
        assert parsed_minimal["metadata"] is not None, "Metadata missing"
        assert parsed_minimal["metadata"]["type"] == "metadata"
        assert parsed_minimal["metadata"]["scan_name"] == scan_name
        print(f"  ✓ Metadata: {parsed_minimal['metadata']['scan_name']}")

        # Validate vulnerabilities
        vuln_count_minimal = len(parsed_minimal["vulnerabilities"])
        print(f"  ✓ Vulnerabilities: {vuln_count_minimal}")

        # Validate minimal schema fields
        if vuln_count_minimal > 0:
            sample_vuln = parsed_minimal["vulnerabilities"][0]
            assert "host" in sample_vuln
            assert "plugin_id" in sample_vuln
            assert "severity" in sample_vuln
            print(f"  ✓ Sample vulnerability fields: host, plugin_id, severity")

        # Validate pagination
        assert parsed_minimal["pagination"] is not None, "Pagination missing"
        assert parsed_minimal["pagination"]["type"] == "pagination"
        print(f"  ✓ Pagination: page {parsed_minimal['pagination']['page']} of {parsed_minimal['pagination']['total_pages']}")

        # ====================================================================
        # Step 5: Retrieve Results - Brief Schema
        # ====================================================================

        print_section("Step 5: Retrieve Results (Brief Schema)")

        results_brief = await client.get_results(
            task_id=task_id,
            schema_profile="brief",
            page=0  # Get all data
        )

        parsed_brief = parse_jsonl_results(results_brief)

        assert parsed_brief["schema"]["profile"] == "brief"
        vuln_count_brief = len(parsed_brief["vulnerabilities"])
        print(f"  ✓ Schema: brief")
        print(f"  ✓ Vulnerabilities: {vuln_count_brief}")

        # Validate brief schema has more fields than minimal
        if vuln_count_brief > 0:
            sample_vuln = parsed_brief["vulnerabilities"][0]
            assert "host" in sample_vuln
            assert "plugin_id" in sample_vuln
            assert "severity" in sample_vuln
            assert "plugin_name" in sample_vuln
            assert "cvss_score" in sample_vuln
            print(f"  ✓ Sample vulnerability has extended fields")

        # ====================================================================
        # Step 6: Get Vulnerability Summary
        # ====================================================================

        print_section("Step 6: Get Vulnerability Summary")

        summary = await client.get_vulnerability_summary(task_id)

        assert isinstance(summary, dict), "Summary should be a dict"
        print(f"  Critical (4): {summary.get('4', 0)}")
        print(f"  High (3):     {summary.get('3', 0)}")
        print(f"  Medium (2):   {summary.get('2', 0)}")
        print(f"  Low (1):      {summary.get('1', 0)}")

        total_vulns = sum(summary.values())
        print(f"  Total:        {total_vulns}")

        # Validate at least some vulnerabilities were found
        # (Target host is intentionally vulnerable for testing)
        assert total_vulns > 0, "Expected to find vulnerabilities on target host"
        print(f"  ✓ Found {total_vulns} total vulnerabilities")

        # ====================================================================
        # Step 7: Get Critical Vulnerabilities
        # ====================================================================

        print_section("Step 7: Get Critical Vulnerabilities")

        if summary.get('4', 0) > 0:
            critical_vulns = await client.get_critical_vulnerabilities(task_id)

            assert isinstance(critical_vulns, list), "Critical vulns should be a list"
            assert len(critical_vulns) == summary['4'], \
                f"Expected {summary['4']} critical, got {len(critical_vulns)}"

            print(f"  ✓ Retrieved {len(critical_vulns)} critical vulnerabilities")

            # Validate all have severity="4"
            for vuln in critical_vulns:
                assert vuln.get("severity") == "4", \
                    f"Expected severity '4', got '{vuln.get('severity')}'"

            print(f"  ✓ All critical vulnerabilities have severity='4'")

            # Print sample critical vulnerability
            if critical_vulns:
                sample = critical_vulns[0]
                print()
                print("  Sample Critical Vulnerability:")
                print(f"    Plugin:   {sample.get('plugin_id')} - {sample.get('plugin_name', 'N/A')}")
                print(f"    Host:     {sample.get('host')}")
                print(f"    CVSS:     {sample.get('cvss_score', 'N/A')}")
                if sample.get('cve'):
                    print(f"    CVE:      {sample.get('cve')}")
        else:
            print(f"  ⚠ No critical vulnerabilities found (this is OK)")

        # ====================================================================
        # Step 8: Validate Queue Status
        # ====================================================================

        print_section("Step 8: Validate Queue Status")

        queue_status = await client.get_queue_status()

        assert "main_queue_depth" in queue_status
        assert "dlq_depth" in queue_status

        print(f"  Main Queue Depth: {queue_status['main_queue_depth']}")
        print(f"  DLQ Depth:        {queue_status['dlq_depth']}")
        print(f"  ✓ Queue status retrieved successfully")

        # ====================================================================
        # Step 9: Validate Scanner Registry
        # ====================================================================

        print_section("Step 9: Validate Scanner Registry")

        scanners = await client.list_scanners()

        assert "scanners" in scanners
        scanner_count = len(scanners["scanners"])

        print(f"  ✓ Found {scanner_count} registered scanner(s)")

        for scanner in scanners["scanners"]:
            print(f"    - {scanner.get('instance_id', 'unknown')}: {scanner.get('enabled', False)}")

        # ====================================================================
        # Final Summary
        # ====================================================================

        print_section("✓ E2E Test PASSED")
        print()
        print("  Complete workflow validated:")
        print(f"    ✓ Client connection")
        print(f"    ✓ Scan submission")
        print(f"    ✓ Progress monitoring ({len(progress_updates)} updates)")
        print(f"    ✓ Scan completion ({final_status['progress']}%)")
        print(f"    ✓ Result retrieval (minimal + brief schemas)")
        print(f"    ✓ Vulnerability summary ({total_vulns} total)")
        print(f"    ✓ Critical vulnerability filtering")
        print(f"    ✓ Queue status validation")
        print(f"    ✓ Scanner registry validation")
        print()
        print(f"  Task ID: {task_id}")
        print(f"  Scan Name: {scan_name}")
        print(f"  Duration: ~{SCAN_TIMEOUT - (SCAN_TIMEOUT - len(progress_updates) * POLL_INTERVAL)}s")
        print()


# ============================================================================
# Test: E2E with Filters
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_with_result_filtering():
    """
    Test E2E workflow with result filtering.

    This test validates:
    1. Scan submission and completion
    2. Filtering by severity
    3. Filtering by CVSS score
    4. Custom field selection
    """

    print_section("Phase 3 E2E Test: Result Filtering")

    async with NessusFastMCPClient(url=MCP_SERVER_URL, debug=False) as client:

        # ====================================================================
        # Submit and Wait
        # ====================================================================

        print_section("Submit Scan")

        scan_name = f"E2E Filter Test - {datetime.now().strftime('%Y%m%d-%H%M%S')}"

        final_status = await client.scan_and_wait(
            targets=TARGET_HOST,
            scan_name=scan_name,
            description="E2E test with result filtering",
            timeout=SCAN_TIMEOUT,
            poll_interval=POLL_INTERVAL,
            progress_callback=lambda s: print_progress(s)
        )

        print()
        print()

        assert final_status["status"] == "completed"
        task_id = final_status["task_id"]

        print(f"  ✓ Scan completed: {task_id}")

        # ====================================================================
        # Filter by Severity: Critical Only
        # ====================================================================

        print_section("Filter: Critical Vulnerabilities (Severity=4)")

        results_critical = await client.get_results(
            task_id=task_id,
            schema_profile="minimal",
            filters={"severity": "4"},
            page=0
        )

        parsed_critical = parse_jsonl_results(results_critical)
        critical_count = len(parsed_critical["vulnerabilities"])

        print(f"  ✓ Found {critical_count} critical vulnerabilities")

        # Validate all have severity="4"
        for vuln in parsed_critical["vulnerabilities"]:
            assert vuln.get("severity") == "4"

        # ====================================================================
        # Filter by CVSS Score
        # ====================================================================

        print_section("Filter: High CVSS Score (>7.0)")

        results_high_cvss = await client.get_results(
            task_id=task_id,
            schema_profile="brief",
            filters={"cvss_score": ">7.0"},
            page=0
        )

        parsed_high_cvss = parse_jsonl_results(results_high_cvss)
        high_cvss_count = len(parsed_high_cvss["vulnerabilities"])

        print(f"  ✓ Found {high_cvss_count} vulnerabilities with CVSS > 7.0")

        # Validate all have cvss_score > 7.0
        for vuln in parsed_high_cvss["vulnerabilities"]:
            cvss = float(vuln.get("cvss_score", 0))
            assert cvss > 7.0, f"Expected CVSS > 7.0, got {cvss}"

        # ====================================================================
        # Custom Fields
        # ====================================================================

        print_section("Custom Fields: host, plugin_id, plugin_name, cve")

        results_custom = await client.get_results(
            task_id=task_id,
            custom_fields=["host", "plugin_id", "plugin_name", "cve"],
            page=1,
            page_size=10
        )

        parsed_custom = parse_jsonl_results(results_custom)
        custom_count = len(parsed_custom["vulnerabilities"])

        print(f"  ✓ Retrieved {custom_count} vulnerabilities with custom fields")

        # Validate custom fields
        if custom_count > 0:
            sample = parsed_custom["vulnerabilities"][0]
            assert "host" in sample
            assert "plugin_id" in sample
            assert "plugin_name" in sample
            # cve may not be present in all vulnerabilities
            print(f"  ✓ Custom fields validated")

        print_section("✓ Filtering Test PASSED")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
