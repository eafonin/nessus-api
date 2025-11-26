"""Scanner registry for managing multiple scanner instances.

Phase 4 enhancements:
- Pool-based scanner grouping (nessus, nessus_dmz, nuclei, etc.)
- Per-scanner active scan tracking
- Load-based scanner selection (least loaded within pool)
- Concurrent scan limit enforcement
"""
import os
import signal
import yaml
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
import logging
import asyncio
from .nessus_scanner import NessusScanner
from .mock_scanner import MockNessusScanner

logger = logging.getLogger(__name__)

# Default concurrent scan limit per scanner
# Limit to 2 to avoid prolonging individual scan times
DEFAULT_MAX_CONCURRENT_SCANS = 2

# Default pool name for backward compatibility
DEFAULT_POOL = "nessus"


class ScannerRegistry:
    """
    Registry for scanner instances organized by pool.

    Pool Architecture:
    - Pools group scanners by vendor/zone (e.g., nessus, nessus_dmz, nuclei)
    - Each pool has its own Redis queue for task isolation
    - Load balancing happens within each pool
    - Scanner key format: {pool}:{instance_id}

    Supports:
    - Pool-based scanner grouping
    - Load-based scanner selection (least loaded within pool)
    - Per-scanner active scan tracking
    - Concurrent scan limit enforcement
    - Hot-reload on SIGHUP
    - Environment variable substitution
    """

    def __init__(self, config_file: str = "config/scanners.yaml"):
        self.config_file = Path(config_file)
        self._instances: Dict[str, Dict[str, Any]] = {}
        self._pools: Set[str] = set()  # Track available pools
        self._lock = asyncio.Lock()  # For thread-safe active_scans updates
        self._load_config()

        # Setup SIGHUP handler for hot-reload
        try:
            signal.signal(signal.SIGHUP, self._handle_reload)
        except AttributeError:
            # SIGHUP not available on Windows
            logger.warning("SIGHUP signal not available on this platform")

    def _load_config(self) -> None:
        """Load scanner configuration from YAML.

        Config format (pool-based):
            pool_name:  # e.g., nessus, nessus_dmz, nuclei
              - instance_id: scanner1
                name: "Scanner 1"
                url: ${NESSUS_URL}
                username: ${NESSUS_USERNAME}
                password: ${NESSUS_PASSWORD}
                enabled: true
                max_concurrent_scans: 2
        """
        if not self.config_file.exists():
            logger.warning(
                "scanner_config_missing",
                config_file=str(self.config_file),
                action="generating_example_config"
            )
            self._generate_example_config()
            logger.warning(
                "scanner_config_generated",
                config_file=str(self.config_file),
                message="ALERT: Example scanners.yaml generated. Edit with your scanner details and restart."
            )
            self._register_mock_scanner()
            return

        try:
            with open(self.config_file) as f:
                config = yaml.safe_load(f)

            if not config:
                logger.warning("Empty config file, using mock scanner")
                self._register_mock_scanner()
                return

            # Parse all pools from config
            # Each top-level key is a pool name (nessus, nessus_dmz, nuclei, etc.)
            for pool_name, pool_scanners in config.items():
                if not isinstance(pool_scanners, list):
                    logger.warning(f"Invalid pool config for '{pool_name}': expected list")
                    continue

                self._pools.add(pool_name)

                for scanner_config in pool_scanners:
                    instance_id = scanner_config.get("instance_id")
                    if not instance_id:
                        logger.warning(f"Scanner in pool '{pool_name}' missing instance_id, skipping")
                        continue

                    enabled = scanner_config.get("enabled", True)
                    if not enabled:
                        logger.info(f"Skipping disabled scanner: {pool_name}:{instance_id}")
                        continue

                    # Substitute environment variables
                    url = self._expand_env(scanner_config.get("url", ""))
                    username = self._expand_env(scanner_config.get("username", ""))
                    password = self._expand_env(scanner_config.get("password", ""))

                    # Determine scanner type from pool name prefix
                    # nessus, nessus_dmz, nessus_lan -> NessusScanner
                    # nuclei -> future NucleiScanner
                    # openvas -> future OpenVASScanner
                    if pool_name.startswith("nessus"):
                        scanner = NessusScanner(
                            url=url,
                            username=username,
                            password=password,
                            verify_ssl=False  # Default to False for self-signed certs
                        )
                        scanner_type = "nessus"
                    else:
                        # Future: Add other scanner types here
                        logger.warning(f"Unknown scanner type for pool '{pool_name}', skipping")
                        continue

                    key = f"{pool_name}:{instance_id}"
                    max_concurrent = scanner_config.get("max_concurrent_scans", DEFAULT_MAX_CONCURRENT_SCANS)
                    self._instances[key] = {
                        "scanner": scanner,
                        "config": scanner_config,
                        "last_used": 0,
                        "type": scanner_type,
                        "pool": pool_name,
                        "active_scans": 0,
                        "max_concurrent_scans": max_concurrent,
                    }

                    logger.info(
                        f"Registered scanner: {key} ({scanner_config.get('name', instance_id)}) "
                        f"pool={pool_name} max_concurrent={max_concurrent}"
                    )

            if not self._instances:
                logger.warning("No enabled scanners found, using mock scanner")
                self._register_mock_scanner()

        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            logger.info("Using mock scanner as fallback")
            self._register_mock_scanner()

    def _register_mock_scanner(self, pool: str = DEFAULT_POOL) -> None:
        """Register mock scanner as fallback."""
        mock_scanner = MockNessusScanner()
        key = f"{pool}:mock"
        self._pools.add(pool)
        self._instances[key] = {
            "scanner": mock_scanner,
            "config": {"instance_id": "mock", "name": "Mock Scanner"},
            "last_used": 0,
            "type": "mock",
            "pool": pool,
            "active_scans": 0,
            "max_concurrent_scans": DEFAULT_MAX_CONCURRENT_SCANS,
        }
        logger.info(f"Registered scanner: {key} (Mock Scanner) pool={pool}")

    def _generate_example_config(self) -> None:
        """Generate example scanners.yaml with documented options."""
        example_config = """\
# Scanner Pool Configuration
#
# ALERT: This is an auto-generated example config.
# Edit this file with your actual scanner details and restart the MCP server.
#
# Environment variable substitution: ${VAR_NAME} or ${VAR_NAME:-default}

# =============================================================================
# Pool: nessus (default pool)
# =============================================================================

nessus:
  # Scanner 1 - Primary scanner
  - instance_id: scanner1
    name: "Nessus Scanner 1"
    url: ${NESSUS_URL:-https://localhost:8834}
    username: ${NESSUS_USERNAME:-admin}
    password: ${NESSUS_PASSWORD}
    enabled: true
    max_concurrent_scans: 2  # Limit to avoid prolonging scan times

  # Scanner 2 - Secondary scanner (optional)
  # - instance_id: scanner2
  #   name: "Nessus Scanner 2"
  #   url: ${NESSUS_URL_2:-https://scanner2:8834}
  #   username: ${NESSUS_USERNAME_2:-admin}
  #   password: ${NESSUS_PASSWORD_2}
  #   enabled: true
  #   max_concurrent_scans: 2

# =============================================================================
# Example: Zone-specific pools (uncomment to enable)
# =============================================================================

# nessus_dmz:
#   - instance_id: dmz-scanner1
#     name: "DMZ Nessus Scanner"
#     url: ${NESSUS_DMZ_URL}
#     username: ${NESSUS_DMZ_USERNAME}
#     password: ${NESSUS_DMZ_PASSWORD}
#     enabled: true
#     max_concurrent_scans: 2
"""
        try:
            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                f.write(example_config)
        except Exception as e:
            logger.error(
                "failed_to_generate_config",
                config_file=str(self.config_file),
                error=str(e)
            )

    def _expand_env(self, value: str) -> str:
        """
        Expand ${VAR} or ${VAR:-default} environment variables.

        Examples:
            ${NESSUS_URL} -> os.getenv("NESSUS_URL", "")
            ${NESSUS_URL:-https://localhost:8834} -> os.getenv("NESSUS_URL", "https://localhost:8834")
        """
        if not value or not isinstance(value, str):
            return value

        if value.startswith("${") and value.endswith("}"):
            # Extract variable name and default value
            inner = value[2:-1]
            if ":-" in inner:
                var_name, default = inner.split(":-", 1)
                return os.getenv(var_name, default)
            else:
                var_name = inner
                return os.getenv(var_name, "")

        return value

    def _handle_reload(self, signum, frame):
        """Handle SIGHUP for config reload."""
        logger.info("Received SIGHUP, reloading scanner config...")
        self._instances.clear()
        self._pools.clear()
        self._load_config()

    def list_pools(self) -> List[str]:
        """List all available scanner pools."""
        return sorted(self._pools)

    def get_default_pool(self) -> str:
        """Get the default pool name."""
        return DEFAULT_POOL

    def get_instance(
        self,
        scanner_type: str = "nessus",
        instance_id: Optional[str] = None,
        pool: Optional[str] = None
    ) -> Any:
        """
        Get scanner instance by ID.

        Args:
            scanner_type: Scanner type (e.g., "nessus") - deprecated, use pool
            instance_id: Specific instance ID
            pool: Pool name (e.g., "nessus", "nessus_dmz"). Takes precedence over scanner_type.

        Returns:
            Scanner instance

        Raises:
            ValueError: If instance not found
        """
        # Pool takes precedence over scanner_type for backward compatibility
        target_pool = pool or scanner_type

        if instance_id:
            key = f"{target_pool}:{instance_id}"
            if key not in self._instances:
                raise ValueError(f"Scanner not found: {key}")
            return self._instances[key]["scanner"]

        # If no instance specified, use least loaded selection
        scanner, _ = self.get_available_scanner(pool=target_pool)
        return scanner

    def get_available_scanner(
        self,
        scanner_type: str = "nessus",
        pool: Optional[str] = None
    ) -> Tuple[Any, str]:
        """
        Get least loaded scanner with available capacity from a pool.

        Selection criteria (in order):
        1. Must have available capacity (active_scans < max_concurrent_scans)
        2. Prefer scanner with lowest utilization (active_scans / max_concurrent_scans)
        3. Tie-breaker: least recently used

        Args:
            scanner_type: Scanner type (e.g., "nessus") - deprecated, use pool
            pool: Pool name (e.g., "nessus", "nessus_dmz"). Takes precedence over scanner_type.

        Returns:
            Tuple of (scanner instance, instance_key)

        Raises:
            ValueError: If no instances in pool
        """
        # Pool takes precedence over scanner_type for backward compatibility
        target_pool = pool or scanner_type
        candidates = []

        for key, data in self._instances.items():
            if not key.startswith(f"{target_pool}:"):
                continue

            active = data["active_scans"]
            max_concurrent = data["max_concurrent_scans"]

            # Check capacity
            if active < max_concurrent:
                utilization = active / max_concurrent if max_concurrent > 0 else 0
                candidates.append((key, data, utilization))

        if not candidates:
            # No available scanners - return any scanner for queueing
            fallback = [
                (key, data) for key, data in self._instances.items()
                if key.startswith(f"{target_pool}:")
            ]
            if not fallback:
                raise ValueError(f"No enabled scanners in pool '{target_pool}'")

            # Return least loaded even if at capacity
            fallback.sort(key=lambda x: x[1]["active_scans"])
            key, data = fallback[0]
            data["last_used"] = time.time()
            return data["scanner"], key

        # Sort by utilization, then last_used for tie-breaker
        candidates.sort(key=lambda x: (x[2], x[1]["last_used"]))
        key, data, _ = candidates[0]

        # Update last_used
        data["last_used"] = time.time()

        return data["scanner"], key

    async def acquire_scanner(
        self,
        scanner_type: str = "nessus",
        instance_id: Optional[str] = None,
        pool: Optional[str] = None
    ) -> Tuple[Any, str]:
        """
        Acquire scanner and increment active_scans count.

        Args:
            scanner_type: Scanner type (e.g., "nessus") - deprecated, use pool
            instance_id: Optional specific instance ID
            pool: Pool name (e.g., "nessus", "nessus_dmz"). Takes precedence over scanner_type.

        Returns:
            Tuple of (scanner instance, instance_key)
        """
        # Pool takes precedence over scanner_type for backward compatibility
        target_pool = pool or scanner_type

        async with self._lock:
            if instance_id:
                key = f"{target_pool}:{instance_id}"
                if key not in self._instances:
                    raise ValueError(f"Scanner not found: {key}")
                data = self._instances[key]
                data["active_scans"] += 1
                data["last_used"] = time.time()
                logger.info(f"Acquired scanner {key}: active_scans={data['active_scans']}/{data['max_concurrent_scans']}")
                return data["scanner"], key

            # Get least loaded scanner from pool
            scanner, key = self.get_available_scanner(pool=target_pool)
            data = self._instances[key]
            data["active_scans"] += 1
            logger.info(f"Acquired scanner {key}: active_scans={data['active_scans']}/{data['max_concurrent_scans']}")
            return scanner, key

    async def release_scanner(self, instance_key: str) -> None:
        """
        Release scanner and decrement active_scans count.

        Args:
            instance_key: Scanner key (e.g., "nessus:scanner1")
        """
        async with self._lock:
            if instance_key not in self._instances:
                logger.warning(f"Cannot release unknown scanner: {instance_key}")
                return

            data = self._instances[instance_key]
            if data["active_scans"] > 0:
                data["active_scans"] -= 1
                logger.info(f"Released scanner {instance_key}: active_scans={data['active_scans']}/{data['max_concurrent_scans']}")
            else:
                logger.warning(f"Attempted to release scanner {instance_key} with active_scans=0")

    def get_scanner_load(self, instance_key: str) -> Dict[str, Any]:
        """
        Get load information for a specific scanner.

        Returns:
            Dict with active_scans, max_concurrent_scans, utilization_pct
        """
        if instance_key not in self._instances:
            return {"error": f"Scanner not found: {instance_key}"}

        data = self._instances[instance_key]
        max_concurrent = data["max_concurrent_scans"]
        active = data["active_scans"]
        utilization = (active / max_concurrent * 100) if max_concurrent > 0 else 0

        return {
            "instance_key": instance_key,
            "active_scans": active,
            "max_concurrent_scans": max_concurrent,
            "utilization_pct": round(utilization, 1),
            "available_capacity": max_concurrent - active,
        }

    def get_pool_status(self, scanner_type: str = "nessus", pool: Optional[str] = None) -> Dict[str, Any]:
        """
        Get overall pool status.

        Args:
            scanner_type: Scanner type (e.g., "nessus") - deprecated, use pool
            pool: Pool name (e.g., "nessus", "nessus_dmz"). Takes precedence over scanner_type.

        Returns:
            Dict with total capacity, active scans, and per-scanner breakdown
        """
        # Pool takes precedence over scanner_type for backward compatibility
        target_pool = pool or scanner_type

        total_capacity = 0
        total_active = 0
        scanners = []

        for key, data in self._instances.items():
            if not key.startswith(f"{target_pool}:"):
                continue

            total_capacity += data["max_concurrent_scans"]
            total_active += data["active_scans"]
            scanners.append(self.get_scanner_load(key))

        utilization = (total_active / total_capacity * 100) if total_capacity > 0 else 0

        return {
            "pool": target_pool,
            "scanner_type": target_pool.split("_")[0],  # nessus_dmz -> nessus
            "total_scanners": len(scanners),
            "total_capacity": total_capacity,
            "total_active": total_active,
            "available_capacity": total_capacity - total_active,
            "utilization_pct": round(utilization, 1),
            "scanners": scanners,
        }

    def list_instances(
        self,
        scanner_type: Optional[str] = None,
        enabled_only: bool = True,
        include_load: bool = True,
        pool: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all registered scanner instances with optional load info.

        Args:
            scanner_type: Filter by scanner type - deprecated, use pool
            enabled_only: Only return enabled scanners
            include_load: Include load metrics (active_scans, utilization)
            pool: Filter by pool name. Takes precedence over scanner_type.
        """
        # Pool takes precedence over scanner_type for backward compatibility
        filter_pool = pool or scanner_type
        results = []

        for key, data in self._instances.items():
            if filter_pool and not key.startswith(f"{filter_pool}:"):
                continue

            config = data["config"]
            max_concurrent = data["max_concurrent_scans"]
            active = data["active_scans"]

            instance_info = {
                "scanner_type": data["type"],
                "pool": data.get("pool", data["type"]),
                "instance_id": config["instance_id"],
                "instance_key": key,
                "name": config.get("name", config["instance_id"]),
                "url": config.get("url", "N/A"),
                "enabled": config.get("enabled", True),
                "max_concurrent_scans": max_concurrent,
            }

            if include_load:
                utilization = (active / max_concurrent * 100) if max_concurrent > 0 else 0
                instance_info.update({
                    "active_scans": active,
                    "available_capacity": max_concurrent - active,
                    "utilization_pct": round(utilization, 1),
                })

            results.append(instance_info)

        return results

    def get_instance_info(
        self,
        pool: str,
        instance_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get info dict for a specific scanner instance.

        Args:
            pool: Pool name (e.g., "nessus", "nessus_dmz")
            instance_id: Scanner instance ID

        Returns:
            Dict with instance info or None if not found
        """
        key = f"{pool}:{instance_id}"
        if key not in self._instances:
            return None

        data = self._instances[key]
        config = data["config"]
        max_concurrent = data["max_concurrent_scans"]
        active = data["active_scans"]
        utilization = (active / max_concurrent * 100) if max_concurrent > 0 else 0

        return {
            "scanner_type": data["type"],
            "pool": data.get("pool", data["type"]),
            "instance_id": config["instance_id"],
            "instance_key": key,
            "name": config.get("name", config["instance_id"]),
            "url": config.get("url", "N/A"),
            "enabled": config.get("enabled", True),
            "max_concurrent_scans": max_concurrent,
            "active_scans": active,
            "available_capacity": max_concurrent - active,
            "utilization_pct": round(utilization, 1),
        }

    async def get_scanner(
        self,
        pool: str,
        instance_id: str,
        fallback_to_pool: bool = True
    ) -> Optional["BaseScanner"]:
        """Get a scanner instance for direct API calls.

        Use this when you need to call scanner methods directly (e.g., stop_scan, delete_scan).
        The returned scanner is NOT acquired from the semaphore pool - do not use it for
        running new scans (use acquire() instead).

        Args:
            pool: Pool name (e.g., "nessus", "nessus_dmz")
            instance_id: Scanner instance ID
            fallback_to_pool: If True and specific instance not found, return any scanner
                             from the same pool. Useful for cleanup operations where the
                             original scanner may no longer be configured.

        Returns:
            Scanner instance or None if not found
        """
        key = f"{pool}:{instance_id}"
        if key in self._instances:
            return self._instances[key]["scanner"]

        # Specific instance not found, try fallback to any scanner in pool
        if fallback_to_pool:
            for k, data in self._instances.items():
                if data.get("pool") == pool:
                    logger.info(f"Scanner {key} not found, using fallback: {k}")
                    return data["scanner"]

        logger.warning(f"Scanner not found: {key} (no fallback available)")
        return None

    def get_scanner_count(self, scanner_type: Optional[str] = None, pool: Optional[str] = None) -> int:
        """Get count of registered scanners.

        Args:
            scanner_type: Filter by scanner type - deprecated, use pool
            pool: Filter by pool name. Takes precedence over scanner_type.
        """
        filter_pool = pool or scanner_type
        if filter_pool:
            return len([k for k in self._instances.keys() if k.startswith(f"{filter_pool}:")])
        return len(self._instances)

    def get_all_scanners(self) -> List[Tuple[str, Any]]:
        """Get all registered scanner instances.

        Returns:
            List of tuples (instance_key, scanner_instance)
            Example: [("nessus:scanner1", <NessusScanner>), ("nessus:scanner2", <NessusScanner>)]
        """
        return [(key, data["scanner"]) for key, data in self._instances.items()]

    async def close_all(self) -> None:
        """Close all scanner instances."""
        for key, data in self._instances.items():
            scanner = data["scanner"]
            if hasattr(scanner, "close"):
                try:
                    await scanner.close()
                    logger.info(f"Closed scanner: {key}")
                except Exception as e:
                    logger.error(f"Error closing scanner {key}: {e}")
