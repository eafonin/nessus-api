"""
Layer 01 Infrastructure Test Fixtures.

These fixtures support connectivity and access validation tests.
"""

import os

import pytest

# =============================================================================
# Configuration
# =============================================================================

NESSUS_URL = os.getenv("NESSUS_URL", "https://vpn-gateway:8834")
NESSUS_USERNAME = os.getenv("NESSUS_USERNAME", "nessus")
NESSUS_PASSWORD = os.getenv("NESSUS_PASSWORD", "nessus")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

SCAN_TARGET_IP = os.getenv("SCAN_TARGET_IP", "172.30.0.9")
EXTERNAL_HOST_IP = os.getenv("EXTERNAL_HOST_IP", "172.32.0.215")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def nessus_url():
    """Return configured Nessus URL."""
    return NESSUS_URL


@pytest.fixture
def nessus_credentials():
    """Return Nessus credentials as dict."""
    return {"username": NESSUS_USERNAME, "password": NESSUS_PASSWORD}


@pytest.fixture
def redis_url():
    """Return configured Redis URL."""
    return REDIS_URL


@pytest.fixture
def scan_target():
    """Return primary scan target IP."""
    return SCAN_TARGET_IP


@pytest.fixture
def external_host():
    """Return external host IP."""
    return EXTERNAL_HOST_IP


@pytest.fixture
def test_credentials():
    """Return test account credentials for scan targets."""
    return {
        "scan_target": {
            "ip": SCAN_TARGET_IP,
            "users": {
                "sudo_pass": {
                    "username": "testauth_sudo_pass",
                    "password": "TestPass123!",
                },
                "sudo_nopass": {
                    "username": "testauth_sudo_nopass",
                    "password": "TestPass123!",
                },
                "nosudo": {
                    "username": "testauth_nosudo",
                    "password": "TestPass123!",
                },
            },
        },
        "external_host": {
            "ip": EXTERNAL_HOST_IP,
            "users": {
                "randy": {
                    "username": "randy",
                    "password": "randylovesgoldfish1998",
                }
            },
        },
    }
