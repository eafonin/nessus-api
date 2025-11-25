"""
Shared pytest fixtures for integration tests.

This conftest.py provides:
- Common Nessus scanner configuration
- Shared fixtures (scanner, redis)
- Custom pytest marks registration
"""

import os
import pytest
import redis
from scanners.nessus_scanner import NessusScanner


# =============================================================================
# Configuration
# =============================================================================

# Nessus Scanner Configuration
# These can be overridden via environment variables
NESSUS_URL = os.getenv("NESSUS_URL", "https://172.32.0.209:8834")
NESSUS_USERNAME = os.getenv("NESSUS_USERNAME", "admin")
NESSUS_PASSWORD = os.getenv("NESSUS_PASSWORD", "Adm1n@Nessus!")

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "phase0: Phase 0 tests (task management, queue)")
    config.addinivalue_line("markers", "phase1: Phase 1 tests (Nessus scanner integration)")
    config.addinivalue_line("markers", "phase2: Phase 2 tests (schema and results)")
    config.addinivalue_line("markers", "phase3: Phase 3 tests (observability)")
    config.addinivalue_line("markers", "phase4: Phase 4 tests (production)")
    config.addinivalue_line("markers", "integration: Integration tests requiring external services")
    config.addinivalue_line("markers", "slow: Tests that take a long time to run")
    config.addinivalue_line("markers", "requires_nessus: Tests requiring Nessus scanner")


# =============================================================================
# Shared Fixtures
# =============================================================================

@pytest.fixture
def scanner():
    """
    Create a NessusScanner instance for tests.

    Automatically handles setup and teardown.
    Configuration comes from environment variables.

    Note: This is a sync fixture that returns an async-capable object.
    The scanner methods are async, but fixture setup/teardown is sync.

    Usage:
        @pytest.mark.asyncio
        async def test_something(scanner):
            await scanner._authenticate()
            # ... test code ...
    """
    s = NessusScanner(
        url=NESSUS_URL,
        username=NESSUS_USERNAME,
        password=NESSUS_PASSWORD,
        verify_ssl=False
    )
    yield s
    # Note: close() is async, but we can't await in a sync fixture
    # The httpx client will be cleaned up when garbage collected
    # For proper cleanup in production, use context managers in tests


@pytest.fixture
def redis_client():
    """
    Create a Redis client for tests.

    Usage:
        def test_something(redis_client):
            redis_client.set("key", "value")
    """
    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )
    yield client
    client.close()


@pytest.fixture
def queue_prefix():
    """Return the standard queue prefix for tests."""
    return "nessus:queue"


@pytest.fixture
def task_prefix():
    """Return the standard task prefix for tests."""
    return "nessus:task"


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_target():
    """Return a safe target for testing."""
    return "127.0.0.1"


@pytest.fixture
def sample_scan_name():
    """Return a standard scan name for testing."""
    return "Integration Test Scan"


# =============================================================================
# Utility Fixtures
# =============================================================================

@pytest.fixture
def nessus_config():
    """
    Return Nessus configuration as a dict.

    Useful for tests that need to create their own scanner instances.
    """
    return {
        "url": NESSUS_URL,
        "username": NESSUS_USERNAME,
        "password": NESSUS_PASSWORD,
        "verify_ssl": False,
    }


@pytest.fixture
def redis_config():
    """
    Return Redis configuration as a dict.

    Useful for tests that need to create their own Redis connections.
    """
    return {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": REDIS_DB,
    }
