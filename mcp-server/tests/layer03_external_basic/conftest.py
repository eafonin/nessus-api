"""
Layer 03 External Basic Test Fixtures.

These fixtures support single-operation integration tests with real services.
"""

import os
import pytest
import pytest_asyncio
import redis

from scanners.nessus_scanner import NessusScanner


# =============================================================================
# Configuration
# =============================================================================

NESSUS_URL = os.getenv("NESSUS_URL", "https://vpn-gateway:8834")
NESSUS_USERNAME = os.getenv("NESSUS_USERNAME", "nessus")
NESSUS_PASSWORD = os.getenv("NESSUS_PASSWORD", "nessus")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-api:8000/mcp")


# =============================================================================
# Scanner Fixtures
# =============================================================================

@pytest.fixture
def scanner():
    """
    Synchronous scanner fixture for basic tests.

    Note: Returns an async-capable scanner object.
    Methods are async and need to be awaited.
    """
    s = NessusScanner(
        url=NESSUS_URL,
        username=NESSUS_USERNAME,
        password=NESSUS_PASSWORD,
        verify_ssl=False
    )
    yield s


@pytest_asyncio.fixture
async def async_scanner():
    """
    Async scanner fixture with proper cleanup.

    Use this for tests that need guaranteed cleanup.
    """
    scanner = NessusScanner(
        url=NESSUS_URL,
        username=NESSUS_USERNAME,
        password=NESSUS_PASSWORD,
        verify_ssl=False
    )
    yield scanner
    await scanner.close()


# =============================================================================
# Redis Fixtures
# =============================================================================

@pytest.fixture
def redis_client():
    """Redis client for queue operation tests."""
    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )
    yield client
    client.close()


# =============================================================================
# MCP Client Fixtures
# =============================================================================

@pytest.fixture
def mcp_url():
    """Return configured MCP server URL."""
    return MCP_SERVER_URL


@pytest_asyncio.fixture
async def mcp_client():
    """
    FastMCP client for MCP tool tests.

    Provides a connected client ready for tool calls.
    """
    from client.nessus_fastmcp_client import NessusFastMCPClient

    client = NessusFastMCPClient(MCP_SERVER_URL)
    await client.connect()
    yield client
    await client.close()


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def nessus_config():
    """Nessus configuration as dict."""
    return {
        "url": NESSUS_URL,
        "username": NESSUS_USERNAME,
        "password": NESSUS_PASSWORD,
        "verify_ssl": False,
    }


@pytest.fixture
def redis_config():
    """Redis configuration as dict."""
    return {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": REDIS_DB,
    }


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_target():
    """Safe target for quick tests."""
    return "127.0.0.1"


@pytest.fixture
def real_target():
    """Real scan target (172.32.0.215)."""
    return os.getenv("SCAN_TARGET", "172.32.0.215")


@pytest.fixture
def queue_prefix():
    """Queue key prefix."""
    return "nessus:queue"


@pytest.fixture
def task_prefix():
    """Task key prefix."""
    return "nessus:task"
