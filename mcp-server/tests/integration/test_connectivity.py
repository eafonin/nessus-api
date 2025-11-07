"""
Docker Network Connectivity Test for Phase 1A.

This test verifies that MCP containers can reach the Nessus instance
before implementing the scanner. Run this test FIRST to validate networking.

Usage:
    # From host
    pytest tests/integration/test_connectivity.py -v -s

    # From container
    docker exec nessus-mcp-api-dev pytest /app/tests/integration/test_connectivity.py -v -s
"""
import pytest
import httpx
import os
import socket


@pytest.mark.asyncio
async def test_nessus_reachability_from_host():
    """Test that Nessus is reachable from host machine."""
    nessus_url = os.getenv("NESSUS_URL", "https://localhost:8834")

    print(f"\n🔍 Testing connectivity to: {nessus_url}")

    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            response = await client.get(f"{nessus_url}/server/status")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            data = response.json()
            assert "status" in data, "Response missing 'status' field"
            assert data["status"] == "ready", f"Nessus not ready: {data['status']}"

            print(f"✅ Nessus is reachable from host")
            print(f"   Status: {data['status']}")
            print(f"   Response: {data}")

        except httpx.ConnectError as e:
            pytest.fail(f"❌ Cannot connect to Nessus at {nessus_url}: {e}")
        except httpx.TimeoutException:
            pytest.fail(f"❌ Connection timeout to {nessus_url}")
        except Exception as e:
            pytest.fail(f"❌ Unexpected error: {e}")


@pytest.mark.asyncio
async def test_nessus_ssl_certificate_handling():
    """Test that self-signed SSL certificates are handled correctly."""
    nessus_url = os.getenv("NESSUS_URL", "https://localhost:8834")

    print(f"\n🔒 Testing SSL certificate handling: {nessus_url}")

    # Test with verify=False (should work)
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            response = await client.get(f"{nessus_url}/server/status")
            assert response.status_code == 200
            print(f"✅ SSL certificate bypassed successfully (verify=False)")
        except Exception as e:
            pytest.fail(f"❌ Failed even with verify=False: {e}")

    # Test with verify=True (should fail with self-signed cert)
    async with httpx.AsyncClient(verify=True, timeout=10.0) as client:
        try:
            response = await client.get(f"{nessus_url}/server/status")
            # If it succeeds, cert is actually valid (not self-signed)
            print(f"ℹ️  SSL certificate appears to be valid (not self-signed)")
        except httpx.ConnectError as e:
            # Expected for self-signed certs
            print(f"✅ Self-signed certificate detected (expected): {type(e).__name__}")


@pytest.mark.asyncio
async def test_nessus_basic_endpoints():
    """Test basic Nessus endpoints are accessible."""
    nessus_url = os.getenv("NESSUS_URL", "https://localhost:8834")
    endpoints = [
        ("/server/status", 200, "Server status endpoint"),
        ("/server/properties", 200, "Server properties endpoint"),
    ]

    print(f"\n📡 Testing Nessus API endpoints:")

    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        for path, expected_status, description in endpoints:
            try:
                response = await client.get(f"{nessus_url}{path}")
                assert response.status_code == expected_status, \
                    f"Expected {expected_status}, got {response.status_code}"

                print(f"   ✅ {description}: {path}")

            except Exception as e:
                pytest.fail(f"❌ Failed {description} ({path}): {e}")


def test_dns_resolution():
    """Test DNS resolution of Nessus hostname."""
    nessus_url = os.getenv("NESSUS_URL", "https://localhost:8834")

    # Extract hostname from URL
    hostname = nessus_url.split("://")[1].split(":")[0]

    print(f"\n🌐 Testing DNS resolution for: {hostname}")

    try:
        ip_address = socket.gethostbyname(hostname)
        print(f"   ✅ Hostname '{hostname}' resolves to: {ip_address}")
        assert ip_address, "IP address should not be empty"

    except socket.gaierror as e:
        pytest.fail(f"❌ DNS resolution failed for '{hostname}': {e}")


def test_tcp_port_connectivity():
    """Test TCP port connectivity to Nessus."""
    nessus_url = os.getenv("NESSUS_URL", "https://localhost:8834")

    # Extract hostname and port
    parts = nessus_url.split("://")[1].split(":")
    hostname = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 443

    print(f"\n🔌 Testing TCP connectivity to {hostname}:{port}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)

    try:
        result = sock.connect_ex((hostname, port))
        sock.close()

        if result == 0:
            print(f"   ✅ TCP port {port} is open and accepting connections")
        else:
            pytest.fail(f"❌ TCP port {port} is closed or unreachable (error code: {result})")

    except socket.gaierror as e:
        pytest.fail(f"❌ DNS resolution failed: {e}")
    except socket.timeout:
        pytest.fail(f"❌ Connection timeout to {hostname}:{port}")
    except Exception as e:
        pytest.fail(f"❌ Unexpected error: {e}")


@pytest.mark.asyncio
async def test_authentication_endpoint():
    """Test that authentication endpoint is accessible (doesn't actually auth)."""
    nessus_url = os.getenv("NESSUS_URL", "https://localhost:8834")

    print(f"\n🔐 Testing authentication endpoint accessibility:")

    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            # POST without credentials should return 401 (but endpoint is accessible)
            response = await client.post(
                f"{nessus_url}/session",
                json={"username": "test", "password": "test"},
                headers={"Content-Type": "application/json"}
            )

            # We expect either 401 (bad creds) or 200 (if test/test works by chance)
            assert response.status_code in [200, 401, 403], \
                f"Unexpected status: {response.status_code}"

            if response.status_code == 401:
                print(f"   ✅ Authentication endpoint accessible (returned 401 as expected)")
            elif response.status_code == 200:
                print(f"   ℹ️  Authentication endpoint accessible (test credentials worked?)")
            else:
                print(f"   ✅ Authentication endpoint accessible (status: {response.status_code})")

        except Exception as e:
            pytest.fail(f"❌ Authentication endpoint failed: {e}")


@pytest.mark.asyncio
async def test_nessus_version_info():
    """Test retrieving Nessus version information."""
    nessus_url = os.getenv("NESSUS_URL", "https://localhost:8834")

    print(f"\n📋 Retrieving Nessus version information:")

    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            response = await client.get(f"{nessus_url}/server/properties")

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Nessus version info:")
                print(f"      Version: {data.get('nessus_version', 'unknown')}")
                print(f"      Type: {data.get('nessus_type', 'unknown')}")
                print(f"      Scanner UUID: {data.get('scanner_uuid', 'unknown')}")

        except Exception as e:
            # Non-critical - version info nice to have but not required
            print(f"   ℹ️  Could not retrieve version info (non-critical): {e}")


# Summary test - runs all connectivity checks in sequence
@pytest.mark.asyncio
async def test_comprehensive_connectivity():
    """
    Comprehensive connectivity test that validates all network requirements.

    This test should PASS before proceeding with scanner implementation.
    """
    print("\n" + "=" * 70)
    print("🚀 PHASE 1A CONNECTIVITY TEST - COMPREHENSIVE CHECK")
    print("=" * 70)

    try:
        # 1. DNS Resolution
        test_dns_resolution()

        # 2. TCP Port
        test_tcp_port_connectivity()

        # 3. HTTPS Connectivity
        await test_nessus_reachability_from_host()

        # 4. SSL Handling
        await test_nessus_ssl_certificate_handling()

        # 5. API Endpoints
        await test_nessus_basic_endpoints()

        # 6. Auth Endpoint
        await test_authentication_endpoint()

        # 7. Version Info (optional)
        await test_nessus_version_info()

        print("\n" + "=" * 70)
        print("✅ ALL CONNECTIVITY TESTS PASSED")
        print("=" * 70)
        print("➡️  You can now proceed with Phase 1A scanner implementation")
        print("=" * 70 + "\n")

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ CONNECTIVITY TEST FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        print("\nFix network connectivity before proceeding with Phase 1A")
        print("=" * 70 + "\n")
        raise


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_connectivity.py -v -s
    pytest.main([__file__, "-v", "-s"])
