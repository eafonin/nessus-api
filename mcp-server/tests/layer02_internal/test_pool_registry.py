"""Unit tests for pool-based scanner registry operations."""

from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
import yaml


class TestScannerRegistryPools:
    """Test ScannerRegistry pool functionality."""

    @pytest.fixture
    def mock_scanner(self):
        """Mock NessusScanner."""
        mock = MagicMock()
        mock.close = AsyncMock()
        return mock

    @pytest.fixture
    def pool_config(self):
        """Sample pool-based configuration."""
        return {
            "nessus": [
                {
                    "instance_id": "scanner1",
                    "name": "Nessus Scanner 1",
                    "url": "https://scanner1:8834",
                    "username": "admin",
                    "password": "secret",
                    "enabled": True,
                    "max_concurrent_scans": 5,
                },
                {
                    "instance_id": "scanner2",
                    "name": "Nessus Scanner 2",
                    "url": "https://scanner2:8834",
                    "username": "admin",
                    "password": "secret",
                    "enabled": True,
                    "max_concurrent_scans": 5,
                },
            ],
            "nessus_dmz": [
                {
                    "instance_id": "dmz-scanner1",
                    "name": "DMZ Scanner",
                    "url": "https://dmz-scanner:8834",
                    "username": "admin",
                    "password": "secret",
                    "enabled": True,
                    "max_concurrent_scans": 3,
                },
            ],
        }

    @pytest.fixture
    def registry(self, pool_config, mock_scanner):
        """ScannerRegistry with mocked config."""
        config_yaml = yaml.dump(pool_config)

        with patch("builtins.open", mock_open(read_data=config_yaml)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "scanners.registry.NessusScanner", return_value=mock_scanner
                ):
                    from scanners.registry import ScannerRegistry

                    return ScannerRegistry(config_file="/fake/config.yaml")

    def test_list_pools(self, registry):
        """Test listing all available pools."""
        pools = registry.list_pools()

        assert "nessus" in pools
        assert "nessus_dmz" in pools
        assert len(pools) == 2

    def test_get_default_pool(self, registry):
        """Test getting default pool."""
        default = registry.get_default_pool()

        assert default == "nessus"

    def test_get_scanner_count_all(self, registry):
        """Test getting total scanner count."""
        count = registry.get_scanner_count()

        assert count == 3  # 2 in nessus + 1 in nessus_dmz

    def test_get_scanner_count_by_pool(self, registry):
        """Test getting scanner count for specific pool."""
        nessus_count = registry.get_scanner_count(pool="nessus")
        dmz_count = registry.get_scanner_count(pool="nessus_dmz")

        assert nessus_count == 2
        assert dmz_count == 1

    def test_list_instances_all(self, registry):
        """Test listing all scanner instances."""
        instances = registry.list_instances()

        assert len(instances) == 3
        # Check pools are included
        pools = [i["pool"] for i in instances]
        assert "nessus" in pools
        assert "nessus_dmz" in pools

    def test_list_instances_by_pool(self, registry):
        """Test listing scanners for specific pool."""
        nessus_instances = registry.list_instances(pool="nessus")
        dmz_instances = registry.list_instances(pool="nessus_dmz")

        assert len(nessus_instances) == 2
        assert len(dmz_instances) == 1
        assert all(i["pool"] == "nessus" for i in nessus_instances)
        assert all(i["pool"] == "nessus_dmz" for i in dmz_instances)

    def test_get_instance_by_pool(self, registry):
        """Test getting specific scanner instance by pool."""
        scanner = registry.get_instance(pool="nessus", instance_id="scanner1")

        assert scanner is not None

    def test_get_instance_not_found(self, registry):
        """Test getting non-existent scanner."""
        with pytest.raises(ValueError, match="Scanner not found"):
            registry.get_instance(pool="nessus", instance_id="nonexistent")

    def test_get_available_scanner_from_pool(self, registry):
        """Test getting available scanner from pool."""
        scanner, key = registry.get_available_scanner(pool="nessus")

        assert scanner is not None
        assert key.startswith("nessus:")

    def test_get_available_scanner_from_empty_pool(self, registry):
        """Test getting scanner from non-existent pool."""
        with pytest.raises(ValueError, match="No enabled scanners"):
            registry.get_available_scanner(pool="nonexistent")

    def test_get_pool_status(self, registry):
        """Test getting pool status."""
        status = registry.get_pool_status(pool="nessus")

        assert status["pool"] == "nessus"
        assert status["total_scanners"] == 2
        assert status["total_capacity"] == 10  # 5 + 5
        assert status["total_active"] == 0
        assert status["utilization_pct"] == 0.0

    def test_get_pool_status_dmz(self, registry):
        """Test getting DMZ pool status."""
        status = registry.get_pool_status(pool="nessus_dmz")

        assert status["pool"] == "nessus_dmz"
        assert status["total_scanners"] == 1
        assert status["total_capacity"] == 3
        assert status["total_active"] == 0


class TestScannerRegistryLoadBalancing:
    """Test scanner load balancing within pools."""

    @pytest.fixture
    def mock_scanner(self):
        """Mock NessusScanner."""
        return MagicMock()

    @pytest.fixture
    def registry_with_load(self, mock_scanner):
        """Registry with scanners at different load levels."""
        config = {
            "nessus": [
                {
                    "instance_id": "scanner1",
                    "url": "https://scanner1:8834",
                    "enabled": True,
                    "max_concurrent_scans": 5,
                },
                {
                    "instance_id": "scanner2",
                    "url": "https://scanner2:8834",
                    "enabled": True,
                    "max_concurrent_scans": 5,
                },
            ]
        }
        config_yaml = yaml.dump(config)

        with patch("builtins.open", mock_open(read_data=config_yaml)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "scanners.registry.NessusScanner", return_value=mock_scanner
                ):
                    from scanners.registry import ScannerRegistry

                    registry = ScannerRegistry(config_file="/fake/config.yaml")

                    # Simulate load on scanner1
                    registry._instances["nessus:scanner1"]["active_scans"] = 3
                    registry._instances["nessus:scanner2"]["active_scans"] = 1

                    return registry

    def test_least_loaded_selection(self, registry_with_load):
        """Test that least loaded scanner is selected."""
        _scanner, key = registry_with_load.get_available_scanner(pool="nessus")

        # scanner2 has less load (1 vs 3)
        assert key == "nessus:scanner2"

    @pytest.mark.asyncio
    async def test_acquire_increments_active_scans(self, registry_with_load):
        """Test acquire_scanner increments active_scans."""
        initial_count = registry_with_load._instances["nessus:scanner2"]["active_scans"]

        _scanner, key = await registry_with_load.acquire_scanner(pool="nessus")

        assert key == "nessus:scanner2"  # Least loaded
        assert (
            registry_with_load._instances["nessus:scanner2"]["active_scans"]
            == initial_count + 1
        )

    @pytest.mark.asyncio
    async def test_release_decrements_active_scans(self, registry_with_load):
        """Test release_scanner decrements active_scans."""
        initial_count = registry_with_load._instances["nessus:scanner1"]["active_scans"]

        await registry_with_load.release_scanner("nessus:scanner1")

        assert (
            registry_with_load._instances["nessus:scanner1"]["active_scans"]
            == initial_count - 1
        )

    @pytest.mark.asyncio
    async def test_acquire_specific_instance(self, registry_with_load):
        """Test acquiring specific scanner instance."""
        _scanner, key = await registry_with_load.acquire_scanner(
            pool="nessus", instance_id="scanner1"
        )

        # Should return scanner1 even though it's more loaded
        assert key == "nessus:scanner1"

    def test_get_scanner_load(self, registry_with_load):
        """Test getting scanner load info."""
        load = registry_with_load.get_scanner_load("nessus:scanner1")

        assert load["instance_key"] == "nessus:scanner1"
        assert load["active_scans"] == 3
        assert load["max_concurrent_scans"] == 5
        assert load["utilization_pct"] == 60.0
        assert load["available_capacity"] == 2


class TestScannerRegistryPoolIsolation:
    """Test that pools are properly isolated."""

    @pytest.fixture
    def mock_scanner(self):
        """Mock NessusScanner."""
        return MagicMock()

    @pytest.fixture
    def multi_pool_registry(self, mock_scanner):
        """Registry with multiple pools."""
        config = {
            "nessus": [
                {
                    "instance_id": "main-1",
                    "url": "https://main:8834",
                    "enabled": True,
                    "max_concurrent_scans": 5,
                },
            ],
            "nessus_dmz": [
                {
                    "instance_id": "dmz-1",
                    "url": "https://dmz:8834",
                    "enabled": True,
                    "max_concurrent_scans": 3,
                },
            ],
            "nessus_lan": [
                {
                    "instance_id": "lan-1",
                    "url": "https://lan:8834",
                    "enabled": True,
                    "max_concurrent_scans": 5,
                },
            ],
        }
        config_yaml = yaml.dump(config)

        with patch("builtins.open", mock_open(read_data=config_yaml)):
            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "scanners.registry.NessusScanner", return_value=mock_scanner
                ):
                    from scanners.registry import ScannerRegistry

                    return ScannerRegistry(config_file="/fake/config.yaml")

    def test_pools_are_isolated(self, multi_pool_registry):
        """Test that pools don't share scanners."""
        nessus_scanners = multi_pool_registry.list_instances(pool="nessus")
        dmz_scanners = multi_pool_registry.list_instances(pool="nessus_dmz")
        lan_scanners = multi_pool_registry.list_instances(pool="nessus_lan")

        # Each pool has exactly one scanner
        assert len(nessus_scanners) == 1
        assert len(dmz_scanners) == 1
        assert len(lan_scanners) == 1

        # Keys don't overlap
        nessus_keys = {s["instance_key"] for s in nessus_scanners}
        dmz_keys = {s["instance_key"] for s in dmz_scanners}
        lan_keys = {s["instance_key"] for s in lan_scanners}

        assert nessus_keys.isdisjoint(dmz_keys)
        assert nessus_keys.isdisjoint(lan_keys)
        assert dmz_keys.isdisjoint(lan_keys)

    def test_pool_status_independent(self, multi_pool_registry):
        """Test pool status is independent."""
        # Simulate load on nessus pool
        multi_pool_registry._instances["nessus:main-1"]["active_scans"] = 3

        nessus_status = multi_pool_registry.get_pool_status(pool="nessus")
        dmz_status = multi_pool_registry.get_pool_status(pool="nessus_dmz")

        # Only nessus pool should show active scans
        assert nessus_status["total_active"] == 3
        assert dmz_status["total_active"] == 0

    @pytest.mark.asyncio
    async def test_acquire_respects_pool(self, multi_pool_registry):
        """Test acquire only returns scanner from specified pool."""
        _scanner, key = await multi_pool_registry.acquire_scanner(pool="nessus_dmz")

        assert key.startswith("nessus_dmz:")
        assert not key.startswith("nessus:main")
