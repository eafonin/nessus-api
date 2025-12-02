"""Scanner interface abstraction for pluggable scanner backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ScanRequest:
    """Scan request parameters."""

    targets: str
    name: str
    scan_type: str = "untrusted"
    description: str = ""
    credentials: dict[str, Any] | None = None
    schema_profile: str = "brief"


class ScannerInterface(ABC):
    """Abstract base class for scanner backends (Nessus, OpenVAS, etc.)."""

    @abstractmethod
    async def create_scan(self, request: ScanRequest) -> int:
        """Create scan in scanner, return scanner-specific scan ID."""
        pass

    @abstractmethod
    async def launch_scan(self, scan_id: int) -> str:
        """Launch scan, return scan_uuid."""
        pass

    @abstractmethod
    async def get_status(self, scan_id: int) -> dict[str, Any]:
        """
        Get scan status and progress.

        Returns:
            {
                "status": "pending|running|completed",
                "progress": 0-100,
                "uuid": "...",
                "info": {...}
            }
        """
        pass

    @abstractmethod
    async def export_results(self, scan_id: int) -> bytes:
        """Export scan results in native format."""
        pass

    @abstractmethod
    async def stop_scan(self, scan_id: int) -> bool:
        """Stop running scan."""
        pass

    @abstractmethod
    async def delete_scan(self, scan_id: int) -> bool:
        """Delete scan."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Cleanup scanner resources (HTTP sessions, connections).

        Should be called when scanner is no longer needed.
        """
        pass
