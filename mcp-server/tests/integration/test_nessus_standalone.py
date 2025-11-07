#!/usr/bin/env python3
"""Standalone test for Nessus scanner (no pytest required)."""
import asyncio
import sys
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest


@pytest.mark.asyncio
async def test_authentication():
    """Test Nessus authentication."""
    print("\n" + "="*60)
    print("TEST 1: Nessus Authentication")
    print("="*60)

    scanner = NessusScanner(
        url="https://vpn-gateway:8834",
        username="nessus",
        password="nessus",
        verify_ssl=False
    )

    try:
        print("→ Authenticating with Nessus...")
        await scanner._authenticate()

        if scanner._session_token:
            print(f"✅ Authenticated successfully!")
            print(f"   Token: {scanner._session_token[:20]}...")
            return True
        else:
            print("❌ Authentication failed - no token received")
            return False

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False
    finally:
        await scanner.close()


@pytest.mark.asyncio
async def test_create_and_cleanup():
    """Test scan creation, launch, and cleanup."""
    print("\n" + "="*60)
    print("TEST 2: Create, Launch, Stop, Delete Scan")
    print("="*60)

    scanner = NessusScanner(
        url="https://vpn-gateway:8834",
        username="nessus",
        password="nessus",
        verify_ssl=False
    )

    try:
        # Create scan
        print("→ Creating scan...")
        scan_id = await scanner.create_scan(
            ScanRequest(
                targets="192.168.1.1",
                name="Phase 1 Integration Test",
                scan_type="untrusted",
                description="Automated test from Phase 1 implementation"
            )
        )
        print(f"✅ Scan created with ID: {scan_id}")

        # Launch scan
        print("→ Launching scan...")
        scan_uuid = await scanner.launch_scan(scan_id)
        print(f"✅ Scan launched with UUID: {scan_uuid}")

        # Check status
        print("→ Checking initial status...")
        status = await scanner.get_status(scan_id)
        print(f"✅ Status: {status['status']}, Progress: {status['progress']}%")

        # Wait a bit
        print("→ Waiting 5 seconds...")
        await asyncio.sleep(5)

        # Check status again
        print("→ Checking updated status...")
        status = await scanner.get_status(scan_id)
        print(f"✅ Status: {status['status']}, Progress: {status['progress']}%")

        # Stop scan
        print("→ Stopping scan...")
        stopped = await scanner.stop_scan(scan_id)
        if stopped:
            print("✅ Scan stopped")
        else:
            print("⚠️  Scan stop returned False")

        # Wait for stop to complete
        await asyncio.sleep(2)

        # Delete scan
        print("→ Deleting scan...")
        deleted = await scanner.delete_scan(scan_id)
        if deleted:
            print("✅ Scan deleted")
        else:
            print("⚠️  Scan delete returned False")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await scanner.close()


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("NESSUS SCANNER INTEGRATION TESTS")
    print("="*60)

    results = []

    # Test 1: Authentication
    results.append(await test_authentication())

    # Test 2: Create and cleanup
    results.append(await test_create_and_cleanup())

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if all(results):
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
