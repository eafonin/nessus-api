"""
Test both Nessus scanners with complete scan workflow.

Target: 172.32.0.215
Scanners:
- Scanner 1: https://172.30.0.3:8834
- Scanner 2: https://172.30.0.4:8834
"""

import asyncio
import sys
from pathlib import Path

# Add mcp-server to path
sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))

from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest

# Target configuration
TARGET_HOST = "172.32.0.215"

# Scanner configurations
SCANNERS = [
    {
        "name": "Scanner 1",
        "url": "https://172.30.0.3:8834",
        "username": "nessus",
        "password": "nessus"
    },
    {
        "name": "Scanner 2",
        "url": "https://172.30.0.4:8834",
        "username": "nessus",
        "password": "nessus"
    }
]


async def run_scan_on_scanner(scanner_config: dict, scanner_num: int):
    """Run complete scan workflow on a single scanner."""
    scanner_name = scanner_config["name"]

    print(f"\n{'#'*80}")
    print(f"#  {scanner_name.upper()} - STARTING WORKFLOW")
    print(f"#  URL: {scanner_config['url']}")
    print(f"#  Target: {TARGET_HOST}")
    print(f"{'#'*80}\n")

    scanner = NessusScanner(
        url=scanner_config["url"],
        username=scanner_config["username"],
        password=scanner_config["password"],
        verify_ssl=False
    )

    scan_id = None

    try:
        # STEP 1: Create Scan
        print(f"{'='*80}")
        print(f"STEP 1: Creating non-authenticated scan on {scanner_name}")
        print(f"{'='*80}")
        print(f"Target: {TARGET_HOST}")
        print(f"Scan Type: untrusted (no credentials)")

        request = ScanRequest(
            name=f"Dual Scanner Test - {scanner_name} - {TARGET_HOST}",
            targets=TARGET_HOST,
            description=f"Non-authenticated scan from {scanner_name}",
            scan_type="untrusted"
        )

        scan_id = await scanner.create_scan(request)
        print(f"✓ Created scan ID: {scan_id}")
        print()

        await asyncio.sleep(2)

        # STEP 2: Launch Scan
        print(f"{'='*80}")
        print(f"STEP 2: Launching scan on {scanner_name}")
        print(f"{'='*80}")

        scan_uuid = await scanner.launch_scan(scan_id)
        print(f"✓ Launched scan UUID: {scan_uuid}")
        print(f"✓ Scan is now running...")
        print()

        await asyncio.sleep(3)

        # STEP 3: Monitor Progress
        print(f"{'='*80}")
        print(f"STEP 3: Monitoring scan progress on {scanner_name}")
        print(f"{'='*80}")
        print(f"Will check every 10 seconds (max 15 minutes)")
        print()

        max_wait = 900  # 15 minutes
        poll_interval = 10  # Check every 10 seconds
        elapsed = 0
        last_progress = -1

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            status = await scanner.get_status(scan_id)
            current_status = status['status']
            current_progress = status['progress']

            # Print every update
            if current_progress != last_progress:
                print(f"  [{elapsed:4d}s] Status: {current_status:10s} | Progress: {current_progress:3d}%")
                last_progress = current_progress

            if current_status == "completed":
                print(f"\n✓ Scan completed after {elapsed} seconds")
                await asyncio.sleep(3)
                break
            elif current_status == "failed":
                info = status.get('info', {})
                print(f"\n✗ Scan failed: {info.get('status')}")
                return None
        else:
            print(f"\n⚠ Scan did not complete in {max_wait} seconds, stopping...")
            await scanner.stop_scan(scan_id)
            return None

        print()

        # STEP 4: Export Results
        print(f"{'='*80}")
        print(f"STEP 4: Exporting results from {scanner_name}")
        print(f"{'='*80}")

        results = await scanner.export_results(scan_id)
        print(f"✓ Exported {len(results):,} bytes")

        # Save to file
        output_file = Path(f"/tmp/scanner{scanner_num}_scan_{scan_id}_results.nessus")
        output_file.write_bytes(results)
        print(f"✓ Results saved to: {output_file}")
        print()

        await asyncio.sleep(2)

        # STEP 5: Show Results Summary
        print(f"{'='*80}")
        print(f"STEP 5: Results summary from {scanner_name}")
        print(f"{'='*80}")

        # Parse results
        results_str = results.decode('utf-8')

        # Count vulnerabilities
        vuln_count = results_str.count('<ReportItem')

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
        print(f"  ─────────────────")
        print(f"  Total:    {vuln_count}")
        print()

        # Show sample findings (first 5 plugin names)
        import re
        plugin_names = re.findall(r'<pluginName>(.*?)</pluginName>', results_str)
        if plugin_names:
            print(f"Sample Findings (first 5):")
            for i, name in enumerate(plugin_names[:5], 1):
                print(f"  {i}. {name}")
            if len(plugin_names) > 5:
                print(f"  ... and {len(plugin_names) - 5} more")
        print()

        # Success!
        print(f"{'='*80}")
        print(f"✅ {scanner_name.upper()} - SCAN COMPLETED SUCCESSFULLY")
        print(f"   Found {vuln_count} findings | Results saved to {output_file}")
        print(f"{'='*80}\n")

        return {
            "scanner_name": scanner_name,
            "scan_id": scan_id,
            "vuln_count": vuln_count,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "info": info,
            "output_file": str(output_file)
        }

    except Exception as e:
        print(f"\n{'!'*80}")
        print(f"ERROR on {scanner_name}: {type(e).__name__}: {e}")
        print(f"{'!'*80}\n")
        import traceback
        traceback.print_exc()
        return None

    finally:
        # Cleanup
        if scan_id:
            try:
                await scanner.delete_scan(scan_id)
                print(f"✓ Cleaned up scan ID {scan_id} from {scanner_name}\n")
            except Exception as e:
                print(f"⚠ Cleanup warning for {scanner_name}: {e}\n")

        await scanner.close()


async def main():
    """Run scans on both scanners sequentially."""
    print("\n" + "="*80)
    print("DUAL SCANNER TEST - TARGET: 172.32.0.215")
    print("="*80)
    print(f"Scanners to test: {len(SCANNERS)}")
    print("Scan type: Non-authenticated (untrusted)")
    print("="*80 + "\n")

    results = []

    for i, scanner_config in enumerate(SCANNERS, 1):
        result = await run_scan_on_scanner(scanner_config, i)
        if result:
            results.append(result)

        # Brief pause between scanners
        if i < len(SCANNERS):
            print(f"\n{'~'*80}")
            print(f"Pausing 5 seconds before starting next scanner...")
            print(f"{'~'*80}\n")
            await asyncio.sleep(5)

    # Final Summary
    print("\n" + "#"*80)
    print("#  FINAL SUMMARY - ALL SCANNERS")
    print("#"*80 + "\n")

    if results:
        for result in results:
            print(f"{result['scanner_name']}:")
            print(f"  Scan ID: {result['scan_id']}")
            print(f"  Total Findings: {result['vuln_count']}")
            print(f"  Critical: {result['critical']} | High: {result['high']} | Medium: {result['medium']} | Low: {result['low']} | Info: {result['info']}")
            print(f"  Results: {result['output_file']}")
            print()

        print(f"✅ Successfully completed {len(results)}/{len(SCANNERS)} scans")
    else:
        print(f"❌ No scans completed successfully")

    print("#"*80 + "\n")

    return len(results)


if __name__ == "__main__":
    successful_scans = asyncio.run(main())
    sys.exit(0 if successful_scans == len(SCANNERS) else 1)
