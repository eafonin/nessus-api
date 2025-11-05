"""Scanner interface abstraction for pluggable scanner backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class ScanRequest:
    """Scan request parameters."""
    targets: str
    name: str
    description: str = ""
    scan_type: str = "untrusted"
    # Add credentials, escalation, etc. based on scan_type


class ScannerInterface(ABC):
    """Abstract base class for scanner backends (Nessus, OpenVAS, etc.)."""

    @abstractmethod
    async def create_scan(self, request: ScanRequest) -> int:
        """Create scan in scanner, return scanner-specific scan ID."""
        pass

    @abstractmethod
    async def launch_scan(self, scan_id: int) -> bool:
        """Start the scan execution."""
        pass

    @abstractmethod
    async def get_status(self, scan_id: int) -> Dict[str, Any]:
        """Get current scan status and progress."""
        pass

    @abstractmethod
    async def get_results(self, scan_id: int, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Retrieve scan results with optional filters."""
        pass

    @abstractmethod
    async def pause_scan(self, scan_id: int) -> bool:
        """Pause a running scan."""
        pass

    @abstractmethod
    async def resume_scan(self, scan_id: int) -> bool:
        """Resume a paused scan."""
        pass

    @abstractmethod
    async def stop_scan(self, scan_id: int) -> bool:
        """Stop a running scan."""
        pass

    @abstractmethod
    async def delete_scan(self, scan_id: int) -> bool:
        """Delete scan from scanner."""
        pass
