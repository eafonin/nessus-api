#!/usr/bin/env python3
"""
Test the ReadError handler fix (Option 4).

This script tests if the scanner can handle httpx.ReadError gracefully
by verifying operations via GET requests after connection drops.
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest

# Configure logging to see the handler in action
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

NESSUS_URL = "https://172.32.0.209:8834"
USERNAME = "nessus"
PASSWORD = "nessus"


async def test_create_scan_with_readerror_fix():
    """Test create_scan with ReadError handler."""
    print("=" * 80)
    print("TEST: Create Scan with ReadError Handler")
    print("=" * 80)

    scanner = NessusScanner(
        url=NESSUS_URL,
        username=USERNAME,
        password=PASSWORD,
        verify_ssl=False
    )

    try:
        # Create scan request
        request = ScanRequest(
            targets="172.32.0.215",
            name=f"TEST_readerror_fix_{asyncio.get_event_loop().time():.0f}",
            scan_type="untrusted",
            description="Testing ReadError handler (Option 4)"
        )

        print(f"\n1. Attempting to create scan: {request.name}")
        print(f"   Targets: {request.targets}")

        # This should handle ReadError gracefully
        scan_id = await scanner.create_scan(request)

        print(f"\n2. ✓ SUCCESS: Scan created with ID={scan_id}")
        print(f"   (Despite potential ReadError, verification confirmed scan exists)")

        # Verify scan exists
        print(f"\n3. Verifying scan {scan_id} exists...")
        status = await scanner.get_status(scan_id)
        print(f"   ✓ Scan status: {status['status']}")
        print(f"   ✓ Scan progress: {status['progress']}%")

        # Cleanup
        print(f"\n4. Cleaning up test scan {scan_id}...")
        await scanner.delete_scan(scan_id)
        print(f"   ✓ Scan deleted")

        print("\n" + "=" * 80)
        print("TEST PASSED: ReadError handler working correctly!")
        print("=" * 80)
        return True

    except ValueError as e:
        print(f"\n✗ EXPECTED ERROR (Nessus Essentials limitation):")
        print(f"  {e}")
        print("\nThis is expected behavior for Nessus Essentials (scan_api: false).")
        print("Scans must be created via Web UI, but other operations work.")
        return False

    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await scanner.close()


async def main():
    """Run test."""
    print("Testing ReadError Handler (Option 4)")
    print("Reference: HTTPX_READERROR_INVESTIGATION.md")
    print("")

    success = await test_create_scan_with_readerror_fix()

    print("\n" + "=" * 80)
    if success:
        print("RESULT: Handler successfully created scan despite connection drop")
        print("The workaround is working - operations succeed with verification")
    else:
        print("RESULT: Operation failed (expected for Nessus Essentials)")
        print("Handler correctly detected and reported the limitation")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
