"""
Layer 04 Full Workflow Test Fixtures.

These fixtures support complete E2E workflow tests that run real scans.
"""

import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio

from core.logging_config import configure_logging, get_logger
from core.task_manager import TaskManager
from scanners.nessus_scanner import NessusScanner

# =============================================================================
# Configuration
# =============================================================================

NESSUS_URL = os.getenv("NESSUS_URL", "https://vpn-gateway:8834")
NESSUS_USERNAME = os.getenv("NESSUS_USERNAME", "nessus")
NESSUS_PASSWORD = os.getenv("NESSUS_PASSWORD", "nessus")

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-api:8000/mcp")

SCAN_TARGET_IP = os.getenv("SCAN_TARGET_IP", "172.30.0.9")
EXTERNAL_HOST_IP = os.getenv("EXTERNAL_HOST_IP", "172.32.0.215")

# Timeout for scan completion (default 10 minutes)
SCAN_TIMEOUT = int(os.getenv("SCAN_TIMEOUT", "600"))

# Test data directory
DATA_DIR = os.getenv("TEST_DATA_DIR", "/tmp/test-layer04-workflows")


# =============================================================================
# Logging Fixture
# =============================================================================


@pytest.fixture(scope="module")
def structured_logging():
    """Configure structured logging for workflow tests."""
    configure_logging(log_level="INFO")
    logger = get_logger(__name__)
    logger.info("layer04_test_suite_started")
    yield logger
    logger.info("layer04_test_suite_completed")


# =============================================================================
# Scanner Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def scanner():
    """Async scanner with automatic cleanup."""
    scanner = NessusScanner(
        url=NESSUS_URL,
        username=NESSUS_USERNAME,
        password=NESSUS_PASSWORD,
        verify_ssl=False,
    )
    yield scanner
    await scanner.close()


# =============================================================================
# Task Manager Fixtures
# =============================================================================


@pytest.fixture
def task_manager():
    """TaskManager with isolated test directory."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    return TaskManager(data_dir=DATA_DIR)


# =============================================================================
# MCP Client Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def mcp_client():
    """Connected MCP client for workflow tests."""
    from client.nessus_fastmcp_client import NessusFastMCPClient

    client = NessusFastMCPClient(MCP_SERVER_URL)
    await client.connect()
    yield client
    await client.close()


# =============================================================================
# Test Target Fixtures
# =============================================================================


@pytest.fixture
def scan_target():
    """Primary scan target (scan-target container)."""
    return SCAN_TARGET_IP


@pytest.fixture
def external_host():
    """External host target."""
    return EXTERNAL_HOST_IP


@pytest.fixture
def scan_timeout():
    """Timeout in seconds for scan completion."""
    return SCAN_TIMEOUT


# =============================================================================
# Credential Fixtures
# =============================================================================


@pytest.fixture
def ssh_credentials_randy():
    """SSH credentials for randy user on external host."""
    return {
        "type": "ssh",
        "auth_method": "password",
        "username": "randy",
        "password": "randylovesgoldfish1998",
        "elevate_privileges_with": "Nothing",
    }


@pytest.fixture
def ssh_credentials_sudo_pass():
    """SSH credentials for sudo with password user."""
    return {
        "type": "ssh",
        "auth_method": "password",
        "username": "testauth_sudo_pass",
        "password": "TestPass123!",
        "elevate_privileges_with": "sudo",
        "escalation_password": "TestPass123!",
    }


@pytest.fixture
def ssh_credentials_sudo_nopass():
    """SSH credentials for sudo NOPASSWD user."""
    return {
        "type": "ssh",
        "auth_method": "password",
        "username": "testauth_sudo_nopass",
        "password": "TestPass123!",
        "elevate_privileges_with": "sudo",
    }


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def unique_scan_name():
    """Generate unique scan name for test isolation."""
    return f"Layer04_Test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def results_dir():
    """Directory for saving scan results."""
    path = Path(DATA_DIR) / "results"
    path.mkdir(parents=True, exist_ok=True)
    return path


# =============================================================================
# Cleanup Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_test_scans(scanner):
    """
    Cleanup fixture that tracks and deletes scans created during tests.

    Usage is automatic - just create scans normally and they'll be cleaned up.
    """
    created_scan_ids = []

    # Provide a way for tests to register scans for cleanup
    def register_scan(scan_id):
        created_scan_ids.append(scan_id)

    yield register_scan

    # Cleanup after test
    import asyncio

    for scan_id in created_scan_ids:
        try:
            asyncio.get_event_loop().run_until_complete(scanner.delete_scan(scan_id))
        except Exception:
            pass  # Ignore cleanup errors
