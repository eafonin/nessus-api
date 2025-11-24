"""Create scan on second scanner using the NessusScanner class with ReadError handling"""
import asyncio
import sys
sys.path.insert(0, '/home/nessus/projects/nessus-api/mcp-server')

from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest

async def main():
    # Second scanner configuration
    scanner = NessusScanner(
        url="https://172.30.0.4:8834",
        username="nessus",
        password="nessus",
        verify_ssl=False
    )

    print("Creating scan on second scanner (172.30.0.4)...")

    # Create scan request
    scan_request = ScanRequest(
        name="Scanner2 Test - 172.32.0.215",
        targets="172.32.0.215",
        description="Test scan from second scanner"
    )

    try:
        # Create scan
        print("Creating scan...")
        scan_id = await scanner.create_scan(scan_request)
        print(f"✓ Scan created with ID: {scan_id}")

        # Launch scan
        print("Launching scan...")
        scan_uuid = await scanner.launch_scan(scan_id)
        print(f"✓ Scan launched with UUID: {scan_uuid}")

        # Check status
        print("\nChecking scan status...")
        status = await scanner.get_status(scan_id)
        print(f"  Status: {status.get('status')}")
        print(f"  Name: {status.get('name')}")

        # Close session
        await scanner.close()

        print(f"\nScan is running. Access at: https://172.30.0.4:8834/#/scans/{scan_id}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        await scanner.close()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
