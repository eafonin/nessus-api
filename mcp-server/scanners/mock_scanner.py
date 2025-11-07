"""Mock scanner for testing and development."""
import asyncio
from pathlib import Path
from typing import Dict, Any
from .base import ScannerInterface, ScanRequest


class MockNessusScanner(ScannerInterface):
    """Mock Nessus scanner using fixture files."""

    def __init__(self, fixtures_dir: str = "tests/fixtures", scan_duration: int = 5):
        self.fixtures_dir = Path(fixtures_dir)
        self.scan_duration = scan_duration
        self._scans: Dict[int, Dict[str, Any]] = {}
        self._scan_counter = 1000

    async def create_scan(self, request: ScanRequest) -> int:
        """Create mock scan."""
        scan_id = self._scan_counter
        self._scan_counter += 1

        self._scans[scan_id] = {
            "id": scan_id,
            "name": request.name,
            "targets": request.targets,
            "scan_type": request.scan_type,
            "status": "pending",
            "progress": 0,
            "uuid": f"mock-uuid-{scan_id}",
        }

        await asyncio.sleep(0.1)  # Simulate API delay
        return scan_id

    async def launch_scan(self, scan_id: int) -> str:
        """Launch mock scan."""
        if scan_id not in self._scans:
            raise ValueError(f"Scan {scan_id} not found")

        self._scans[scan_id]["status"] = "running"
        self._scans[scan_id]["progress"] = 10

        # Simulate scan completion after duration
        asyncio.create_task(self._simulate_scan(scan_id))

        await asyncio.sleep(0.1)
        return self._scans[scan_id]["uuid"]

    async def _simulate_scan(self, scan_id: int):
        """Simulate scan progression."""
        interval = self.scan_duration / 4
        for progress in [25, 50, 75, 100]:
            await asyncio.sleep(interval)
            if scan_id in self._scans:
                self._scans[scan_id]["progress"] = progress

        if scan_id in self._scans:
            self._scans[scan_id]["status"] = "completed"

    async def get_status(self, scan_id: int) -> Dict[str, Any]:
        """Get mock scan status."""
        if scan_id not in self._scans:
            raise ValueError(f"Scan {scan_id} not found")

        scan = self._scans[scan_id]
        return {
            "status": scan["status"],
            "progress": scan["progress"],
            "uuid": scan["uuid"],
            "info": scan,
        }

    async def export_results(self, scan_id: int) -> bytes:
        """Return mock .nessus file."""
        # Load fixture file if exists
        fixture_file = self.fixtures_dir / "sample_scan.nessus"
        if fixture_file.exists():
            return fixture_file.read_bytes()

        # Fallback: minimal mock XML
        return b"""<?xml version="1.0" ?>
<NessusClientData_v2>
  <Report name="Mock Scan">
    <ReportHost name="192.168.1.1">
      <ReportItem pluginID="12345" pluginName="Mock Vulnerability" severity="2">
        <description>Mock vulnerability for testing</description>
        <cve>CVE-2023-12345</cve>
        <cvss_base_score>7.5</cvss_base_score>
        <exploit_available>true</exploit_available>
        <solution>Update to latest version</solution>
      </ReportItem>
    </ReportHost>
  </Report>
</NessusClientData_v2>"""

    async def stop_scan(self, scan_id: int) -> bool:
        """Stop mock scan."""
        if scan_id in self._scans:
            self._scans[scan_id]["status"] = "stopped"
            return True
        return False

    async def delete_scan(self, scan_id: int) -> bool:
        """Delete mock scan."""
        if scan_id in self._scans:
            del self._scans[scan_id]
            return True
        return False

    async def close(self) -> None:
        """Cleanup mock scanner resources (no-op for mock)."""
        pass
