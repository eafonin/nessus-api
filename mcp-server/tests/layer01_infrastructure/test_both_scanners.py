"""
Layer 01: Both Scanners Connectivity Tests

Validates that both Nessus scanner instances are accessible.
This test keeps scanner verification at a low layer for troubleshooting.

Usage:
    pytest tests/layer01_infrastructure/test_both_scanners.py -v -s
"""

import os

import httpx
import pytest

# Scanner configurations
SCANNERS = [
    {
        "name": "Scanner 1",
        "url": os.getenv("NESSUS_SCANNER1_URL", "https://172.30.0.3:8834"),
    },
    {
        "name": "Scanner 2",
        "url": os.getenv("NESSUS_SCANNER2_URL", "https://172.30.0.4:8834"),
    },
]


class TestBothScannersConnectivity:
    """Verify both scanner instances are accessible."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scanner", SCANNERS, ids=[s["name"] for s in SCANNERS])
    async def test_scanner_reachable(self, scanner):
        """Verify scanner is reachable via HTTPS."""
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            try:
                response = await client.get(f"{scanner['url']}/server/status")
                assert response.status_code == 200, (
                    f"{scanner['name']} returned {response.status_code}"
                )
            except httpx.ConnectError as e:
                pytest.fail(f"{scanner['name']} not reachable at {scanner['url']}: {e}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scanner", SCANNERS, ids=[s["name"] for s in SCANNERS])
    async def test_scanner_ready(self, scanner):
        """Verify scanner reports ready status."""
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.get(f"{scanner['url']}/server/status")
            data = response.json()
            assert data.get("status") == "ready", (
                f"{scanner['name']} not ready: {data.get('status')}"
            )


class TestScannersIndependent:
    """Verify scanners are independent instances."""

    @pytest.mark.asyncio
    async def test_scanners_have_different_uuids(self):
        """Verify each scanner has a unique UUID."""
        uuids = []

        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            for scanner in SCANNERS:
                response = await client.get(f"{scanner['url']}/server/properties")
                if response.status_code == 200:
                    data = response.json()
                    uuid = data.get("scanner_uuid", data.get("uuid"))
                    if uuid:
                        uuids.append(uuid)

        # If we got UUIDs, they should be unique
        if len(uuids) >= 2:
            assert len(uuids) == len(set(uuids)), (
                f"Scanner UUIDs are not unique: {uuids}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
