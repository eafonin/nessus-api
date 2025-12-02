"""
Test: Complete scan workflow with vulnerability export.

Target: 172.32.0.215 (Ubuntu server - should have vulnerabilities)
Goal: Start scan, wait for completion, export results with vulnerabilities
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest

# Test Configuration
NESSUS_URL = os.getenv("NESSUS_URL", "https://172.32.0.209:8834")
NESSUS_USERNAME = os.getenv("NESSUS_USERNAME", "nessus")
NESSUS_PASSWORD = os.getenv("NESSUS_PASSWORD", "nessus")

# Target with actual vulnerabilities
TARGET_HOST = "172.32.0.215"


@pytest.mark.asyncio
async def test_complete_scan_workflow_with_export():
    """
    Complete scan workflow:
    1. Create scan for 172.32.0.215
    2. Launch scan
    3. Wait for completion (up to 15 minutes)
    4. Export results
    5. Verify vulnerabilities found
    """
    scanner = NessusScanner(
        url=NESSUS_URL,
        username=NESSUS_USERNAME,
        password=NESSUS_PASSWORD,
        verify_ssl=False
    )

    try:
        # Step 1: Create scan
        print(f"\n{'='*60}")
        print(f"STEP 1: Creating scan for {TARGET_HOST}")
        print(f"{'='*60}")

        request = ScanRequest(
            name=f"Integration Test - Complete Scan {TARGET_HOST}",
            targets=TARGET_HOST,
            description=f"Full vulnerability scan of {TARGET_HOST} for integration testing",
            scan_type="untrusted"
        )

        scan_id = await scanner.create_scan(request)
        print(f"✓ Created scan ID: {scan_id}")

        # Brief pause after scan creation
        await asyncio.sleep(2)

        # Step 2: Launch scan
        print(f"\n{'='*60}")
        print(f"STEP 2: Launching scan")
        print(f"{'='*60}")

        scan_uuid = await scanner.launch_scan(scan_id)
        print(f"✓ Launched scan UUID: {scan_uuid}")

        # Brief pause after launch to let scan initialize
        await asyncio.sleep(3)

        # Step 3: Wait for completion
        print(f"\n{'='*60}")
        print(f"STEP 3: Monitoring scan progress")
        print(f"{'='*60}")

        max_wait = 900  # 15 minutes
        poll_interval = 15  # Check every 15 seconds
        elapsed = 0
        last_progress = -1

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            status = await scanner.get_status(scan_id)
            current_status = status['status']
            current_progress = status['progress']

            # Only print when progress changes
            if current_progress != last_progress:
                print(f"  [{elapsed:4d}s] Status: {current_status:10s} | Progress: {current_progress:3d}%")
                last_progress = current_progress

            if current_status == "completed":
                print(f"\n✓ Scan completed after {elapsed} seconds")
                # Brief pause after completion before exporting
                await asyncio.sleep(3)
                break
            elif current_status == "failed":
                info = status.get('info', {})
                print(f"\n✗ Scan failed: {info.get('status')}")
                pytest.fail(f"Scan failed: {info}")
        else:
            # Timeout - stop the scan
            print(f"\n⚠ Scan did not complete in {max_wait} seconds, stopping...")
            await scanner.stop_scan(scan_id)
            pytest.skip(f"Scan did not complete in {max_wait} seconds")

        # Step 4: Export results
        print(f"\n{'='*60}")
        print(f"STEP 4: Exporting results")
        print(f"{'='*60}")

        results = await scanner.export_results(scan_id)
        print(f"✓ Exported {len(results)} bytes")

        # Brief pause after export before deletion
        await asyncio.sleep(2)

        # Step 5: Verify results
        print(f"\n{'='*60}")
        print(f"STEP 5: Verifying results")
        print(f"{'='*60}")

        # Basic XML validation
        assert results is not None
        assert isinstance(results, bytes)
        assert len(results) > 1000, "Results file too small"
        assert b"<?xml" in results, "Not valid XML"
        assert b"<NessusClientData_v2>" in results, "Not valid .nessus format"
        print(f"✓ Valid .nessus XML format")

        # Save to file for inspection
        output_file = Path(f"/tmp/scan_{scan_id}_results.nessus")
        output_file.write_bytes(results)
        print(f"✓ Results saved to: {output_file}")

        # Check for vulnerabilities
        results_str = results.decode('utf-8')

        # Count ReportItem elements (vulnerabilities)
        vuln_count = results_str.count('<ReportItem')
        print(f"✓ Found {vuln_count} vulnerability entries")

        # Verify we have vulnerabilities
        assert vuln_count > 0, f"Expected vulnerabilities but found {vuln_count}"

        # Count by severity
        critical = results_str.count('severity="4"')
        high = results_str.count('severity="3"')
        medium = results_str.count('severity="2"')
        low = results_str.count('severity="1"')
        info = results_str.count('severity="0"')

        print(f"\nVulnerability Summary:")
        print(f"  Critical: {critical}")
        print(f"  High:     {high}")
        print(f"  Medium:   {medium}")
        print(f"  Low:      {low}")
        print(f"  Info:     {info}")
        print(f"  Total:    {vuln_count}")

        # Final success message
        print(f"\n{'='*60}")
        print(f"✅ TEST PASSED - Scan completed with {vuln_count} findings")
        print(f"{'='*60}\n")

    finally:
        # Cleanup
        try:
            await scanner.delete_scan(scan_id)
            print(f"✓ Cleaned up scan ID: {scan_id}")
        except Exception as e:
            print(f"⚠ Cleanup warning: {e}")

        await scanner.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
