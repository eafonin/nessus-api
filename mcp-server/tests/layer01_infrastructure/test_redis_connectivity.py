"""
Layer 01: Redis Connectivity Tests

Validates that Redis is accessible before running any other tests.
These tests should pass first - if they fail, check Docker containers.

Usage:
    pytest tests/layer01_infrastructure/test_redis_connectivity.py -v -s
"""

import pytest
import os
import socket


# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


class TestRedisConnectivity:
    """Basic connectivity tests for Redis."""

    def test_dns_resolution(self):
        """Verify Redis hostname resolves."""
        try:
            ip_address = socket.gethostbyname(REDIS_HOST)
            assert ip_address, "IP address should not be empty"
        except socket.gaierror as e:
            pytest.fail(f"DNS resolution failed for '{REDIS_HOST}': {e}")

    def test_tcp_port_connectivity(self):
        """Verify Redis port is open."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)

        try:
            result = sock.connect_ex((REDIS_HOST, REDIS_PORT))
            sock.close()
            assert result == 0, f"TCP port {REDIS_PORT} is closed (error code: {result})"
        except socket.timeout:
            pytest.fail(f"Connection timeout to {REDIS_HOST}:{REDIS_PORT}")


class TestRedisOperations:
    """Basic Redis operations tests."""

    @pytest.fixture
    def redis_client(self):
        """Create Redis client."""
        import redis
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=0,
            decode_responses=True,
            socket_timeout=5
        )
        yield client
        client.close()

    def test_ping(self, redis_client):
        """Verify PING command works."""
        response = redis_client.ping()
        assert response is True

    def test_set_get(self, redis_client):
        """Verify basic SET/GET operations."""
        test_key = "layer01_test_key"
        test_value = "layer01_test_value"

        # Set
        redis_client.set(test_key, test_value)

        # Get
        result = redis_client.get(test_key)
        assert result == test_value

        # Cleanup
        redis_client.delete(test_key)

    def test_list_operations(self, redis_client):
        """Verify list operations (used by queue)."""
        test_key = "layer01_test_list"

        # Push
        redis_client.lpush(test_key, "item1", "item2")

        # Length
        length = redis_client.llen(test_key)
        assert length == 2

        # Pop
        item = redis_client.rpop(test_key)
        assert item == "item1"

        # Cleanup
        redis_client.delete(test_key)

    def test_info_command(self, redis_client):
        """Verify INFO command returns server info."""
        info = redis_client.info()
        assert "redis_version" in info
        assert "connected_clients" in info


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
