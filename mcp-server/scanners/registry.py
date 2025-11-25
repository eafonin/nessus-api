"""Scanner registry for managing multiple scanner instances.

Phase 4 enhancements:
- Per-scanner active scan tracking
- Load-based scanner selection (least loaded)
- Concurrent scan limit enforcement
"""
import os
import signal
import yaml
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
import asyncio
from .nessus_scanner import NessusScanner
from .mock_scanner import MockNessusScanner

logger = logging.getLogger(__name__)

# Default concurrent scan limit per scanner
DEFAULT_MAX_CONCURRENT_SCANS = 5


class ScannerRegistry:
    """
    Registry for scanner instances.

    Supports:
    - Multiple instances of same scanner type
    - Load-based scanner selection (least loaded first)
    - Per-scanner active scan tracking
    - Concurrent scan limit enforcement
    - Hot-reload on SIGHUP
    - Environment variable substitution
    """

    def __init__(self, config_file: str = "config/scanners.yaml"):
        self.config_file = Path(config_file)
        self._instances: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()  # For thread-safe active_scans updates
        self._load_config()

        # Setup SIGHUP handler for hot-reload
        try:
            signal.signal(signal.SIGHUP, self._handle_reload)
        except AttributeError:
            # SIGHUP not available on Windows
            logger.warning("SIGHUP signal not available on this platform")

    def _load_config(self) -> None:
        """Load scanner configuration from YAML."""
        if not self.config_file.exists():
            logger.warning(f"Config file not found: {self.config_file}")
            logger.info("Using mock scanner as fallback")
            self._register_mock_scanner()
            return

        try:
            with open(self.config_file) as f:
                config = yaml.safe_load(f)

            if not config:
                logger.warning("Empty config file, using mock scanner")
                self._register_mock_scanner()
                return

            # Parse Nessus instances
            nessus_configs = config.get("nessus", [])
            if not nessus_configs:
                logger.warning("No Nessus instances configured, using mock scanner")
                self._register_mock_scanner()
                return

            for scanner_config in nessus_configs:
                instance_id = scanner_config["instance_id"]
                enabled = scanner_config.get("enabled", True)

                if not enabled:
                    logger.info(f"Skipping disabled scanner: nessus:{instance_id}")
                    continue

                # Substitute environment variables
                url = self._expand_env(scanner_config["url"])
                username = self._expand_env(scanner_config.get("username", ""))
                password = self._expand_env(scanner_config.get("password", ""))

                # Create scanner instance
                scanner = NessusScanner(
                    url=url,
                    username=username,
                    password=password,
                    verify_ssl=False  # Default to False for self-signed certs
                )

                key = f"nessus:{instance_id}"
                max_concurrent = scanner_config.get("max_concurrent_scans", DEFAULT_MAX_CONCURRENT_SCANS)
                self._instances[key] = {
                    "scanner": scanner,
                    "config": scanner_config,
                    "last_used": 0,
                    "type": "nessus",
                    "active_scans": 0,
                    "max_concurrent_scans": max_concurrent,
                }

                logger.info(f"Registered scanner: {key} ({scanner_config.get('name', instance_id)}) max_concurrent={max_concurrent}")

            if not self._instances:
                logger.warning("No enabled scanners found, using mock scanner")
                self._register_mock_scanner()

        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            logger.info("Using mock scanner as fallback")
            self._register_mock_scanner()

    def _register_mock_scanner(self) -> None:
        """Register mock scanner as fallback."""
        mock_scanner = MockNessusScanner()
        self._instances["nessus:mock"] = {
            "scanner": mock_scanner,
            "config": {"instance_id": "mock", "name": "Mock Scanner"},
            "last_used": 0,
            "type": "mock",
            "active_scans": 0,
            "max_concurrent_scans": DEFAULT_MAX_CONCURRENT_SCANS,
        }
        logger.info("Registered scanner: nessus:mock (Mock Scanner)")

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
        self._load_config()

    def get_instance(
        self,
        scanner_type: str = "nessus",
        instance_id: Optional[str] = None
    ) -> Any:
        """
        Get scanner instance by ID.

        Args:
            scanner_type: Scanner type (e.g., "nessus")
            instance_id: Specific instance ID

        Returns:
            Scanner instance

        Raises:
            ValueError: If instance not found
        """
        if instance_id:
            key = f"{scanner_type}:{instance_id}"
            if key not in self._instances:
                raise ValueError(f"Scanner not found: {key}")
            return self._instances[key]["scanner"]

        # If no instance specified, use least loaded selection
        return self.get_available_scanner(scanner_type)

    def get_available_scanner(
        self,
        scanner_type: str = "nessus"
    ) -> Tuple[Any, str]:
        """
        Get least loaded scanner with available capacity.

        Selection criteria (in order):
        1. Must have available capacity (active_scans < max_concurrent_scans)
        2. Prefer scanner with lowest utilization (active_scans / max_concurrent_scans)
        3. Tie-breaker: least recently used

        Args:
            scanner_type: Scanner type (e.g., "nessus")

        Returns:
            Tuple of (scanner instance, instance_key)

        Raises:
            ValueError: If no instances with available capacity
        """
        candidates = []

        for key, data in self._instances.items():
            if not key.startswith(f"{scanner_type}:"):
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
                if key.startswith(f"{scanner_type}:")
            ]
            if not fallback:
                raise ValueError(f"No enabled {scanner_type} instances")

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
        instance_id: Optional[str] = None
    ) -> Tuple[Any, str]:
        """
        Acquire scanner and increment active_scans count.

        Args:
            scanner_type: Scanner type (e.g., "nessus")
            instance_id: Optional specific instance ID

        Returns:
            Tuple of (scanner instance, instance_key)
        """
        async with self._lock:
            if instance_id:
                key = f"{scanner_type}:{instance_id}"
                if key not in self._instances:
                    raise ValueError(f"Scanner not found: {key}")
                data = self._instances[key]
                data["active_scans"] += 1
                data["last_used"] = time.time()
                logger.info(f"Acquired scanner {key}: active_scans={data['active_scans']}/{data['max_concurrent_scans']}")
                return data["scanner"], key

            # Get least loaded scanner
            scanner, key = self.get_available_scanner(scanner_type)
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

    def get_pool_status(self, scanner_type: str = "nessus") -> Dict[str, Any]:
        """
        Get overall pool status for a scanner type.

        Returns:
            Dict with total capacity, active scans, and per-scanner breakdown
        """
        total_capacity = 0
        total_active = 0
        scanners = []

        for key, data in self._instances.items():
            if not key.startswith(f"{scanner_type}:"):
                continue

            total_capacity += data["max_concurrent_scans"]
            total_active += data["active_scans"]
            scanners.append(self.get_scanner_load(key))

        utilization = (total_active / total_capacity * 100) if total_capacity > 0 else 0

        return {
            "scanner_type": scanner_type,
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
        include_load: bool = True
    ) -> List[Dict[str, Any]]:
        """List all registered scanner instances with optional load info."""
        results = []

        for key, data in self._instances.items():
            if scanner_type and not key.startswith(f"{scanner_type}:"):
                continue

            config = data["config"]
            max_concurrent = data["max_concurrent_scans"]
            active = data["active_scans"]

            instance_info = {
                "scanner_type": data["type"],
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

    def get_scanner_count(self, scanner_type: Optional[str] = None) -> int:
        """Get count of registered scanners."""
        if scanner_type:
            return len([k for k in self._instances.keys() if k.startswith(f"{scanner_type}:")])
        return len(self._instances)

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
