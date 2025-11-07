"""
Comprehensive integration tests for Nessus scanner READ and WRITE operations.

Tests both API-based (READ) and Web UI simulation (WRITE) endpoints following
patterns from nessusAPIWrapper/.

Test Hosts:
- 172.32.0.215 (randy / randylovesgoldfish1998) - For authenticated scans
- 172.32.0.209 - Nessus host itself (for network discovery)

Based on: nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add mcp-server to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest

# Test Configuration
NESSUS_URL = os.getenv("NESSUS_URL", "https://172.32.0.209:8834")
NESSUS_USERNAME = os.getenv("NESSUS_USERNAME", "nessus")
NESSUS_PASSWORD = os.getenv("NESSUS_PASSWORD", "nessus")

# Test Hosts
TEST_HOST_UNAUTHENTICATED = "172.32.0.209"  # Nessus server (network scan only)
TEST_HOST_AUTHENTICATED = "172.32.0.215"  # Target with SSH credentials
TEST_HOST_SSH_USERNAME = "randy"
TEST_HOST_SSH_PASSWORD = "randylovesgoldfish1998"


@pytest.fixture
async def scanner():
    """Create scanner instance for tests."""
    s = NessusScanner(
        url=NESSUS_URL,
        username=NESSUS_USERNAME,
        password=NESSUS_PASSWORD,
        verify_ssl=False
    )
    yield s
    await s.close()


class TestReadOperations:
    """Test READ operations (API-based, work with Nessus Essentials)."""

    @pytest.mark.asyncio
    async def test_fetch_api_token(self, scanner):
        """Test dynamic X-API-Token fetching."""
        await scanner._fetch_api_token()

        assert scanner._api_token is not None
        assert len(scanner._api_token) > 0
        # Token format: UUID-like (e.g., 778F4A9C-D797-4817-B110-EC427B724486)
        assert "-" in scanner._api_token
        print(f"\n✓ Fetched X-API-Token: {scanner._api_token}")

    @pytest.mark.asyncio
    async def test_authentication(self, scanner):
        """Test Web UI authentication and session token acquisition."""
        await scanner._authenticate()

        assert scanner._session_token is not None
        assert len(scanner._session_token) > 0
        assert scanner._api_token is not None
        print(f"\n✓ Authentication successful, session token: {scanner._session_token[:20]}...")

    @pytest.mark.asyncio
    async def test_get_server_status(self, scanner):
        """Test server status check (READ operation)."""
        await scanner._authenticate()
        client = await scanner._get_session()

        response = await client.get(
            f"{scanner.url}/server/status",
            headers=scanner._build_headers()
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        print(f"\n✓ Server status: {data.get('status')}")

    @pytest.mark.asyncio
    async def test_list_scans(self, scanner):
        """Test listing scans (READ operation)."""
        await scanner._authenticate()
        client = await scanner._get_session()

        response = await client.get(
            f"{scanner.url}/scans",
            headers=scanner._build_headers()
        )

        assert response.status_code == 200
        data = response.json()
        assert "scans" in data or "folders" in data

        scan_count = len(data.get("scans", []))
        print(f"\n✓ Found {scan_count} scans")

    @pytest.mark.asyncio
    async def test_get_scan_details(self, scanner):
        """Test retrieving scan configuration (READ operation)."""
        await scanner._authenticate()
        client = await scanner._get_session()

        # First get list of scans
        response = await client.get(
            f"{scanner.url}/scans",
            headers=scanner._build_headers()
        )
        scans = response.json().get("scans", [])

        if not scans:
            pytest.skip("No scans available to test scan details")

        # Get details of first scan
        scan_id = scans[0]["id"]
        details_response = await client.get(
            f"{scanner.url}/scans/{scan_id}",
            headers=scanner._build_headers()
        )

        assert details_response.status_code == 200
        details = details_response.json()
        assert "info" in details
        print(f"\n✓ Retrieved scan {scan_id} details: {details['info'].get('name')}")


class TestWriteOperations:
    """Test WRITE operations (Web UI simulation, bypasses scan_api: false)."""

    @pytest.mark.asyncio
    async def test_create_scan_untrusted(self, scanner):
        """Test creating unauthenticated scan (WRITE operation)."""
        request = ScanRequest(
            name="Test Scan - Untrusted Network Discovery",
            targets=TEST_HOST_UNAUTHENTICATED,
            description="Integration test: untrusted network scan",
            scan_type="untrusted"
        )

        scan_id = await scanner.create_scan(request)

        assert isinstance(scan_id, int)
        assert scan_id > 0
        print(f"\n✓ Created untrusted scan: ID={scan_id}")

        # Cleanup
        await scanner.delete_scan(scan_id)

    @pytest.mark.asyncio
    async def test_create_launch_stop_delete_workflow(self, scanner):
        """Test complete scan lifecycle (WRITE operations)."""
        # 1. Create scan
        request = ScanRequest(
            name="Test Scan - Full Lifecycle",
            targets=TEST_HOST_UNAUTHENTICATED,
            description="Integration test: full lifecycle workflow",
            scan_type="untrusted"
        )

        scan_id = await scanner.create_scan(request)
        assert scan_id > 0
        print(f"\n✓ Step 1: Created scan ID={scan_id}")

        try:
            # 2. Launch scan
            scan_uuid = await scanner.launch_scan(scan_id)
            assert scan_uuid is not None
            assert len(scan_uuid) > 0
            print(f"✓ Step 2: Launched scan UUID={scan_uuid}")

            # 3. Wait a few seconds for scan to start
            await asyncio.sleep(5)

            # 4. Get status
            status = await scanner.get_status(scan_id)
            assert status["status"] in ["queued", "running"]
            print(f"✓ Step 3: Scan status={status['status']}, progress={status['progress']}%")

            # 5. Stop scan
            stopped = await scanner.stop_scan(scan_id)
            assert stopped is True
            print(f"✓ Step 4: Stopped scan")

            # 6. Wait for scan to fully transition to stopped state
            await asyncio.sleep(5)
            status = await scanner.get_status(scan_id)
            print(f"✓ Step 5: Final status={status['status']}")

        finally:
            # 7. Delete scan
            deleted = await scanner.delete_scan(scan_id)
            assert deleted is True
            print(f"✓ Step 6: Deleted scan")

    @pytest.mark.asyncio
    async def test_export_results_from_completed_scan(self, scanner):
        """Test exporting results from a completed scan."""
        # Create and launch a quick scan
        request = ScanRequest(
            name="Test Scan - Export Test",
            targets=TEST_HOST_UNAUTHENTICATED,
            description="Integration test: export results",
            scan_type="untrusted"
        )

        scan_id = await scanner.create_scan(request)
        print(f"\n✓ Created scan ID={scan_id}")

        try:
            # Launch scan
            scan_uuid = await scanner.launch_scan(scan_id)
            print(f"✓ Launched scan UUID={scan_uuid}")

            # Wait for scan to complete (poll every 10 seconds, max 10 minutes)
            max_wait = 600  # 10 minutes
            poll_interval = 10
            elapsed = 0

            while elapsed < max_wait:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                status = await scanner.get_status(scan_id)
                print(f"  [{elapsed}s] Status: {status['status']}, Progress: {status['progress']}%")

                if status["status"] == "completed":
                    break
                elif status["status"] == "failed":
                    pytest.fail(f"Scan failed: {status.get('info', {})}")
            else:
                # Scan didn't complete in time, stop it
                await scanner.stop_scan(scan_id)
                pytest.skip(f"Scan did not complete in {max_wait} seconds")

            # Export results
            print(f"✓ Scan completed, exporting results...")
            results = await scanner.export_results(scan_id)

            assert results is not None
            assert isinstance(results, bytes)
            assert len(results) > 0
            assert b"<?xml" in results
            assert b"<NessusClientData_v2>" in results
            print(f"✓ Exported results: {len(results)} bytes")

        finally:
            # Cleanup
            await scanner.delete_scan(scan_id)

    @pytest.mark.asyncio
    async def test_scan_status_mapping(self, scanner):
        """Test that Nessus status codes are correctly mapped to MCP status."""
        # Verify status map exists
        status_map = scanner.STATUS_MAP

        assert "pending" in status_map
        assert "running" in status_map
        assert "completed" in status_map
        assert "canceled" in status_map
        assert "paused" in status_map
        assert "empty" in status_map

        # Verify mappings make sense
        assert status_map["pending"] == "queued"
        assert status_map["running"] == "running"
        assert status_map["completed"] == "completed"
        assert status_map["canceled"] == "failed"
        assert status_map["paused"] == "running"

        print("\n✓ Status mapping verified")


class TestErrorHandling:
    """Test error handling for various failure scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_credentials(self):
        """Test authentication with invalid credentials."""
        scanner = NessusScanner(
            url=NESSUS_URL,
            username="invalid_user",
            password="invalid_password",
            verify_ssl=False
        )

        try:
            with pytest.raises(ValueError, match="Authentication failed"):
                await scanner._authenticate()
            print("\n✓ Invalid credentials correctly rejected")
        finally:
            await scanner.close()

    @pytest.mark.asyncio
    async def test_scan_not_found(self, scanner):
        """Test operations on non-existent scan ID."""
        await scanner._authenticate()

        invalid_scan_id = 99999

        with pytest.raises(ValueError, match="not found"):
            await scanner.get_status(invalid_scan_id)

        print("\n✓ Non-existent scan correctly raises error")

    @pytest.mark.asyncio
    async def test_launch_already_running_scan(self, scanner):
        """Test launching a scan that's already running."""
        # Create and launch scan
        request = ScanRequest(
            name="Test Scan - Double Launch",
            targets=TEST_HOST_UNAUTHENTICATED,
            description="Integration test: double launch",
            scan_type="untrusted"
        )

        scan_id = await scanner.create_scan(request)

        try:
            # Launch first time
            await scanner.launch_scan(scan_id)
            await asyncio.sleep(2)

            # Try to launch again
            with pytest.raises(ValueError, match="already running|409"):
                await scanner.launch_scan(scan_id)

            print("\n✓ Double launch correctly rejected")

            # Stop the scan
            await scanner.stop_scan(scan_id)

        finally:
            await scanner.delete_scan(scan_id)


class TestSessionManagement:
    """Test HTTP session and token management."""

    @pytest.mark.asyncio
    async def test_session_reuse(self, scanner):
        """Test that session is reused across multiple operations."""
        await scanner._authenticate()
        first_token = scanner._session_token

        # Second authentication should reuse token
        await scanner._authenticate()
        second_token = scanner._session_token

        assert first_token == second_token
        print("\n✓ Session token correctly reused")

    @pytest.mark.asyncio
    async def test_session_cleanup(self, scanner):
        """Test that cleanup properly closes session."""
        await scanner._authenticate()
        assert scanner._session is not None
        assert scanner._session_token is not None
        assert scanner._api_token is not None

        await scanner.close()

        assert scanner._session is None
        assert scanner._session_token is None
        assert scanner._api_token is None
        print("\n✓ Session cleanup successful")


@pytest.mark.asyncio
async def test_complete_authenticated_scan_workflow(scanner):
    """
    Complete workflow test with authenticated scan on 172.32.0.215.

    NOTE: This requires SSH credentials to be configured after scan creation.
    For now, we'll create the scan but skip credential configuration.
    """
    request = ScanRequest(
        name="Test Scan - Authenticated Target",
        targets=TEST_HOST_AUTHENTICATED,
        description=f"Integration test: authenticated scan of {TEST_HOST_AUTHENTICATED}",
        scan_type="trusted_basic"
    )

    scan_id = await scanner.create_scan(request)
    print(f"\n✓ Created authenticated scan ID={scan_id}")

    try:
        # TODO: Add credential configuration here when Phase 1B is implemented
        # For now, just verify scan was created
        status = await scanner.get_status(scan_id)
        assert status["status"] in ["queued", "empty"]
        print(f"✓ Scan created with status: {status['status']}")

    finally:
        await scanner.delete_scan(scan_id)
        print(f"✓ Cleaned up scan")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
