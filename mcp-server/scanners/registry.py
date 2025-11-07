"""Scanner registry for managing multiple scanner instances."""
import os
import signal
import yaml
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from .nessus_scanner import NessusScanner
from .mock_scanner import MockNessusScanner

logger = logging.getLogger(__name__)


class ScannerRegistry:
    """
    Registry for scanner instances.

    Supports:
    - Multiple instances of same scanner type
    - Round-robin load balancing
    - Hot-reload on SIGHUP
    - Environment variable substitution
    """

    def __init__(self, config_file: str = "config/scanners.yaml"):
        self.config_file = Path(config_file)
        self._instances: Dict[str, Dict[str, Any]] = {}
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
                self._instances[key] = {
                    "scanner": scanner,
                    "config": scanner_config,
                    "last_used": 0,
                    "type": "nessus"
                }

                logger.info(f"Registered scanner: {key} ({scanner_config.get('name', instance_id)})")

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
            "type": "mock"
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
        Get scanner instance (round-robin if instance_id not specified).

        Args:
            scanner_type: Scanner type (e.g., "nessus")
            instance_id: Specific instance ID, or None for round-robin

        Returns:
            Scanner instance

        Raises:
            ValueError: If no instances available
        """
        if instance_id:
            key = f"{scanner_type}:{instance_id}"
            if key not in self._instances:
                raise ValueError(f"Scanner not found: {key}")
            return self._instances[key]["scanner"]

        # Round-robin: get least recently used
        candidates = [
            (key, data) for key, data in self._instances.items()
            if key.startswith(f"{scanner_type}:")
        ]

        if not candidates:
            raise ValueError(f"No enabled {scanner_type} instances")

        # Sort by last_used, pick first
        candidates.sort(key=lambda x: x[1]["last_used"])
        key, data = candidates[0]

        # Update last_used
        data["last_used"] = time.time()

        return data["scanner"]

    def list_instances(
        self,
        scanner_type: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """List all registered scanner instances."""
        results = []

        for key, data in self._instances.items():
            if scanner_type and not key.startswith(f"{scanner_type}:"):
                continue

            config = data["config"]
            results.append({
                "scanner_type": data["type"],
                "instance_id": config["instance_id"],
                "name": config.get("name", config["instance_id"]),
                "url": config.get("url", "N/A"),
                "enabled": config.get("enabled", True),
                "max_concurrent_scans": config.get("max_concurrent_scans", 0),
            })

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
