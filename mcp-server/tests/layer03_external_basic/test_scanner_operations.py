"""Test real Nessus scanner."""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scanners.base import ScanRequest
from scanners.nessus_scanner import NessusScanner


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nessus_authentication():
    """Test Nessus authentication."""
    scanner = NessusScanner(
        url=os.getenv("NESSUS_URL", "https://localhost:8834"),
        username=os.getenv("NESSUS_USERNAME", "nessus"),
        password=os.getenv("NESSUS_PASSWORD", "nessus"),
        verify_ssl=False,
    )

    try:
        # Authenticate
        await scanner._authenticate()
        assert scanner._session_token is not None, "Session token should be set"
        print(f"✓ Authenticated successfully, token: {scanner._session_token[:20]}...")

    finally:
        await scanner.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nessus_create_and_launch():
    """Test scan creation and launch with real Nessus."""
    scanner = NessusScanner(
        url=os.getenv("NESSUS_URL", "https://localhost:8834"),
        username=os.getenv("NESSUS_USERNAME", "nessus"),
        password=os.getenv("NESSUS_PASSWORD", "nessus"),
        verify_ssl=False,
    )

    try:
        # Create scan
        print("\n1. Creating scan...")
        scan_id = await scanner.create_scan(
            ScanRequest(
                targets="192.168.1.1",
                name="Phase 1 Integration Test",
                scan_type="untrusted",
                description="Automated test from Phase 1 implementation",
            )
        )
        assert scan_id > 0, "Scan ID should be positive"
        print(f"   ✓ Scan created with ID: {scan_id}")

        # Launch scan
        print("2. Launching scan...")
        scan_uuid = await scanner.launch_scan(scan_id)
        assert scan_uuid, "Scan UUID should be returned"
        print(f"   ✓ Scan launched with UUID: {scan_uuid}")

        # Check status
        print("3. Checking status...")
        status = await scanner.get_status(scan_id)
        assert status["status"] in ["queued", "running"], (
            f"Unexpected status: {status['status']}"
        )
        print(f"   ✓ Scan status: {status['status']}, progress: {status['progress']}%")

        # Wait a bit to let it start
        await asyncio.sleep(5)

        # Check status again
        status = await scanner.get_status(scan_id)
        print(
            f"   ✓ Updated status: {status['status']}, progress: {status['progress']}%"
        )

        # Stop scan (cleanup)
        print("4. Stopping scan...")
        stopped = await scanner.stop_scan(scan_id)
        assert stopped, "Scan should be stopped"
        print("   ✓ Scan stopped")

        # Wait for stop to complete
        await asyncio.sleep(2)

        # Delete scan (cleanup)
        print("5. Deleting scan...")
        deleted = await scanner.delete_scan(scan_id)
        assert deleted, "Scan should be deleted"
        print("   ✓ Scan deleted")

        print("\n✅ All tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    finally:
        await scanner.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_nessus_status_mapping():
    """Test Nessus status mapping."""
    scanner = NessusScanner(
        url=os.getenv("NESSUS_URL", "https://localhost:8834"),
        username=os.getenv("NESSUS_USERNAME", "nessus"),
        password=os.getenv("NESSUS_PASSWORD", "nessus"),
        verify_ssl=False,
    )

    # Test status mapping
    assert scanner._map_nessus_status("pending") == "queued"
    assert scanner._map_nessus_status("running") == "running"
    assert scanner._map_nessus_status("paused") == "running"
    assert scanner._map_nessus_status("completed") == "completed"
    assert scanner._map_nessus_status("canceled") == "failed"
    assert scanner._map_nessus_status("stopped") == "failed"
    assert scanner._map_nessus_status("aborted") == "failed"
    assert scanner._map_nessus_status("unknown_status") == "unknown"

    print("✓ All status mappings correct")

    await scanner.close()


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_nessus_scanner.py -v -s
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
