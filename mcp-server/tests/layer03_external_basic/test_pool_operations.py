"""
Layer 03: Pool Operations Integration Tests.

Tests MCP tools for scanner pool management:
- list_pools: List available scanner pools
- get_pool_status: Get capacity and utilization for a pool

These tests use the real MCP server and scanner registry.

Usage:
    docker compose exec mcp-api pytest tests/layer03_external_basic/test_pool_operations.py -v -s
"""

import pytest
import pytest_asyncio


@pytest.mark.asyncio
class TestListPools:
    """Tests for list_pools MCP tool."""

    async def test_list_pools_returns_pools(self, mcp_client):
        """Test that list_pools returns available pools."""
        result = await mcp_client.call_tool("list_pools", {})

        assert "pools" in result
        assert isinstance(result["pools"], list)
        assert len(result["pools"]) > 0

    async def test_list_pools_includes_default(self, mcp_client):
        """Test that list_pools includes default pool."""
        result = await mcp_client.call_tool("list_pools", {})

        assert "default_pool" in result
        assert result["default_pool"] is not None
        assert result["default_pool"] in result["pools"]

    async def test_list_pools_contains_nessus(self, mcp_client):
        """Test that nessus pool is available."""
        result = await mcp_client.call_tool("list_pools", {})

        # At minimum, nessus pool should exist
        assert "nessus" in result["pools"]

    async def test_list_pools_response_format(self, mcp_client):
        """Test list_pools response format is correct."""
        result = await mcp_client.call_tool("list_pools", {})

        # Should have exactly these keys
        expected_keys = {"pools", "default_pool"}
        assert set(result.keys()) == expected_keys


@pytest.mark.asyncio
class TestGetPoolStatus:
    """Tests for get_pool_status MCP tool."""

    async def test_get_pool_status_default(self, mcp_client):
        """Test get_pool_status with default pool."""
        result = await mcp_client.call_tool("get_pool_status", {})

        assert "pool" in result
        assert "total_scanners" in result
        assert "total_capacity" in result

    async def test_get_pool_status_specific_pool(self, mcp_client):
        """Test get_pool_status with specific pool."""
        result = await mcp_client.call_tool(
            "get_pool_status",
            {"scanner_pool": "nessus"}
        )

        assert result["pool"] == "nessus"

    async def test_get_pool_status_includes_scanners_list(self, mcp_client):
        """Test that pool status includes per-scanner breakdown."""
        result = await mcp_client.call_tool("get_pool_status", {})

        assert "scanners" in result
        assert isinstance(result["scanners"], list)

    async def test_get_pool_status_scanner_details(self, mcp_client):
        """Test that scanner details include required fields."""
        result = await mcp_client.call_tool("get_pool_status", {})

        if len(result["scanners"]) > 0:
            scanner = result["scanners"][0]
            expected_fields = [
                "instance_key",
                "active_scans",
                "max_concurrent_scans",
            ]
            for field in expected_fields:
                assert field in scanner, f"Missing field: {field}"

    async def test_get_pool_status_capacity_metrics(self, mcp_client):
        """Test that capacity metrics are present."""
        result = await mcp_client.call_tool("get_pool_status", {})

        # Capacity-related fields
        assert "total_scanners" in result
        assert "total_capacity" in result
        assert "total_active" in result
        assert "available_capacity" in result

        # Numeric types
        assert isinstance(result["total_scanners"], int)
        assert isinstance(result["total_capacity"], int)
        assert isinstance(result["total_active"], int)
        assert isinstance(result["available_capacity"], int)

    async def test_get_pool_status_utilization(self, mcp_client):
        """Test that utilization percentage is calculated."""
        result = await mcp_client.call_tool("get_pool_status", {})

        assert "utilization_pct" in result
        assert isinstance(result["utilization_pct"], (int, float))
        assert 0 <= result["utilization_pct"] <= 100

    async def test_get_pool_status_capacity_math(self, mcp_client):
        """Test that capacity math is consistent."""
        result = await mcp_client.call_tool("get_pool_status", {})

        # available_capacity should equal total_capacity - total_active
        expected_available = result["total_capacity"] - result["total_active"]
        assert result["available_capacity"] == expected_available

    async def test_get_pool_status_scanner_type(self, mcp_client):
        """Test that scanner_type is included."""
        result = await mcp_client.call_tool("get_pool_status", {})

        assert "scanner_type" in result
        assert result["scanner_type"] == "nessus"


@pytest.mark.asyncio
class TestPoolOperationsIntegration:
    """Integration tests combining pool operations."""

    async def test_list_pools_then_get_status(self, mcp_client):
        """Test getting status for each listed pool."""
        pools_result = await mcp_client.call_tool("list_pools", {})

        for pool in pools_result["pools"]:
            status_result = await mcp_client.call_tool(
                "get_pool_status",
                {"scanner_pool": pool}
            )
            assert status_result["pool"] == pool
            assert "total_scanners" in status_result

    async def test_default_pool_matches_list(self, mcp_client):
        """Test that default pool from list_pools is in pool status."""
        pools_result = await mcp_client.call_tool("list_pools", {})
        default_pool = pools_result["default_pool"]

        status_result = await mcp_client.call_tool("get_pool_status", {})

        # When no pool specified, should use default
        assert status_result["pool"] == default_pool

    async def test_pool_scanner_count_consistency(self, mcp_client):
        """Test that scanner count matches scanners list length."""
        result = await mcp_client.call_tool("get_pool_status", {})

        assert result["total_scanners"] == len(result["scanners"])


@pytest.mark.asyncio
class TestPoolOperationsEdgeCases:
    """Edge case tests for pool operations."""

    async def test_empty_pool_status(self, mcp_client):
        """Test status for pool that might be empty."""
        # This tests graceful handling - pool might exist but have no scanners
        result = await mcp_client.call_tool("get_pool_status", {})

        # Even if empty, structure should be correct
        assert "total_scanners" in result
        assert result["total_scanners"] >= 0

    async def test_pool_utilization_when_idle(self, mcp_client):
        """Test utilization calculation when no scans running."""
        result = await mcp_client.call_tool("get_pool_status", {})

        # If no active scans, utilization should be 0
        if result["total_active"] == 0:
            assert result["utilization_pct"] == 0.0
            assert result["available_capacity"] == result["total_capacity"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
