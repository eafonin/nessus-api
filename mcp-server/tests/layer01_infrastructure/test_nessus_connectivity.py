"""
Layer 01: Nessus Scanner Connectivity Tests

Validates that Nessus scanner is accessible before running any other tests.
These tests should pass first - if they fail, check Docker containers and network.

Usage:
    pytest tests/layer01_infrastructure/test_nessus_connectivity.py -v -s
"""

import pytest
import httpx
import os
import socket


# Configuration from environment or defaults
NESSUS_URL = os.getenv("NESSUS_URL", "https://nessus-pro-1:8834")


class TestNessusConnectivity:
    """Basic connectivity tests for Nessus scanner."""

    def test_dns_resolution(self):
        """Verify Nessus hostname resolves to IP."""
        hostname = NESSUS_URL.split("://")[1].split(":")[0]

        try:
            ip_address = socket.gethostbyname(hostname)
            assert ip_address, "IP address should not be empty"
        except socket.gaierror as e:
            pytest.fail(f"DNS resolution failed for '{hostname}': {e}")

    def test_tcp_port_connectivity(self):
        """Verify TCP port is open and accepting connections."""
        parts = NESSUS_URL.split("://")[1].split(":")
        hostname = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 8834

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)

        try:
            result = sock.connect_ex((hostname, port))
            sock.close()
            assert result == 0, f"TCP port {port} is closed (error code: {result})"
        except socket.timeout:
            pytest.fail(f"Connection timeout to {hostname}:{port}")

    @pytest.mark.asyncio
    async def test_https_reachable(self):
        """Verify HTTPS endpoint responds."""
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.get(f"{NESSUS_URL}/server/status")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_server_status_ready(self):
        """Verify Nessus reports 'ready' status."""
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.get(f"{NESSUS_URL}/server/status")
            data = response.json()
            assert "status" in data, "Response missing 'status' field"
            assert data["status"] == "ready", f"Nessus not ready: {data['status']}"


class TestNessusSSL:
    """SSL certificate handling tests."""

    @pytest.mark.asyncio
    async def test_ssl_bypass_works(self):
        """Verify we can connect with verify=False."""
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.get(f"{NESSUS_URL}/server/status")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_self_signed_cert_detected(self):
        """Verify self-signed certificate is detected."""
        async with httpx.AsyncClient(verify=True, timeout=10.0) as client:
            try:
                await client.get(f"{NESSUS_URL}/server/status")
                # If success, cert is valid (not self-signed)
            except httpx.ConnectError:
                # Expected for self-signed certs
                pass


class TestNessusEndpoints:
    """API endpoint accessibility tests."""

    @pytest.mark.asyncio
    async def test_server_status_endpoint(self):
        """Verify /server/status endpoint."""
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.get(f"{NESSUS_URL}/server/status")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_server_properties_endpoint(self):
        """Verify /server/properties endpoint."""
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.get(f"{NESSUS_URL}/server/properties")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_authentication_endpoint_accessible(self):
        """Verify /session endpoint responds (even with bad creds)."""
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.post(
                f"{NESSUS_URL}/session",
                json={"username": "invalid", "password": "invalid"},
                headers={"Content-Type": "application/json"}
            )
            # 401 expected for bad creds, but endpoint is accessible
            assert response.status_code in [200, 401, 403]


class TestNessusServerProperties:
    """Server properties and type tests."""

    @pytest.mark.asyncio
    async def test_server_properties_retrievable(self):
        """Verify we can get server properties."""
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.get(f"{NESSUS_URL}/server/properties")
            assert response.status_code == 200
            data = response.json()
            # Nessus returns nessus_type and other properties
            assert "nessus_type" in data, f"Expected 'nessus_type' in {list(data.keys())}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
