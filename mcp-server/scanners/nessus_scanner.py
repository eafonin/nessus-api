"""Native async Nessus scanner implementation."""
import asyncio
import httpx
from typing import Dict, Any, Optional
from .base import ScannerInterface, ScanRequest


class NessusScanner(ScannerInterface):
    """
    Native async Nessus scanner using httpx.

    No subprocess calls - pure async/await.
    """

    # Template UUIDs (from Nessus API)
    # These are standard Nessus template UUIDs - may need verification
    TEMPLATES = {
        "advanced_scan": "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66",
        "basic_network_scan": "731a8e52-3ea6-a291-ec0a-d2ff0619c19d7bd788d6be818b65",
        "web_app_scan": "e9cfb74f-947b-8fa7-f0c7-f3fbbe1c520a878248c99a5ba89c",
    }

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        verify_ssl: bool = False
    ):
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.access_key = access_key
        self.secret_key = secret_key
        self.verify_ssl = verify_ssl

        self._session: Optional[httpx.AsyncClient] = None
        self._session_token: Optional[str] = None

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create async HTTP session."""
        if not self._session:
            self._session = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=30.0,
                follow_redirects=True
            )
        return self._session

    async def _authenticate(self) -> None:
        """Authenticate with Nessus and get session token."""
        if self._session_token:
            return  # Already authenticated

        client = await self._get_session()

        # POST /session for web UI authentication
        response = await client.post(
            f"{self.url}/session",
            json={
                "username": self.username,
                "password": self.password
            },
            headers={
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()

        data = response.json()
        self._session_token = data["token"]

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        if not self._session_token:
            raise ValueError("Not authenticated - call _authenticate() first")

        return {
            "X-Cookie": f"token={self._session_token}",
            "Content-Type": "application/json"
        }

    async def create_scan(self, request: ScanRequest) -> int:
        """
        Create Nessus scan using native async calls.

        Maps scan_type to appropriate Nessus configuration:
        - untrusted: No credentials
        - trusted_basic: SSH with no escalation
        - trusted_privileged: SSH with sudo/su escalation
        """
        await self._authenticate()
        client = await self._get_session()

        # Get template UUID (use advanced_scan for Phase 1)
        template_uuid = self.TEMPLATES["advanced_scan"]

        # Build scan settings
        settings = {
            "name": request.name,
            "text_targets": request.targets,
            "description": request.description or request.name,
            "enabled": True,
            "folder_id": 3,  # My Scans
            "scanner_id": 1,  # Local scanner
        }

        # Add credentials if provided
        if request.credentials:
            settings["credentials"] = self._build_credentials(request.credentials)

        # Create scan
        response = await client.post(
            f"{self.url}/scans",
            json={
                "uuid": template_uuid,
                "settings": settings
            },
            headers=self._build_headers()
        )
        response.raise_for_status()

        data = response.json()
        scan_id = data["scan"]["id"]

        return scan_id

    def _build_credentials(self, creds: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Nessus credentials structure from request.

        Reference: manage_credentials.py for exact format
        """
        # Simplified for Phase 1 - just SSH password
        # TODO Phase 2: Full credential structure with escalation

        return {
            "add": {
                "Host": {
                    "SSH": [
                        {
                            "auth_method": "password",
                            "username": creds.get("username"),
                            "password": creds.get("password"),
                            "elevate_privileges_with": "Nothing",  # No escalation for trusted_basic
                        }
                    ]
                }
            }
        }

    async def launch_scan(self, scan_id: int) -> str:
        """Launch scan asynchronously."""
        await self._authenticate()
        client = await self._get_session()

        response = await client.post(
            f"{self.url}/scans/{scan_id}/launch",
            headers=self._build_headers()
        )
        response.raise_for_status()

        data = response.json()
        scan_uuid = data["scan_uuid"]

        return scan_uuid

    async def get_status(self, scan_id: int) -> Dict[str, Any]:
        """Get current scan status."""
        await self._authenticate()
        client = await self._get_session()

        response = await client.get(
            f"{self.url}/scans/{scan_id}",
            headers=self._build_headers()
        )
        response.raise_for_status()

        data = response.json()
        info = data["info"]

        # Map Nessus status to our status
        nessus_status = info["status"]
        mapped_status = self._map_nessus_status(nessus_status)

        return {
            "status": mapped_status,
            "progress": info.get("progress", 0),
            "uuid": info["uuid"],
            "info": info,
        }

    def _map_nessus_status(self, nessus_status: str) -> str:
        """Map Nessus scan states to MCP states."""
        NESSUS_TO_MCP_STATUS = {
            "pending": "queued",
            "running": "running",
            "paused": "running",  # Treat paused as still running
            "completed": "completed",
            "canceled": "failed",
            "stopped": "failed",
            "aborted": "failed",
        }
        return NESSUS_TO_MCP_STATUS.get(nessus_status, "unknown")

    async def export_results(self, scan_id: int) -> bytes:
        """Export scan results in native .nessus format."""
        await self._authenticate()
        client = await self._get_session()

        # Request export
        response = await client.post(
            f"{self.url}/scans/{scan_id}/export",
            json={"format": "nessus"},
            headers=self._build_headers()
        )
        response.raise_for_status()

        file_id = response.json()["file"]

        # Poll for export completion (max 5 minutes)
        for _ in range(150):  # 5 min / 2 sec
            status_response = await client.get(
                f"{self.url}/scans/{scan_id}/export/{file_id}/status",
                headers=self._build_headers()
            )
            status_response.raise_for_status()

            if status_response.json()["status"] == "ready":
                break

            await asyncio.sleep(2)
        else:
            raise TimeoutError(f"Export did not complete in 5 minutes")

        # Download export
        download_response = await client.get(
            f"{self.url}/scans/{scan_id}/export/{file_id}/download",
            headers=self._build_headers()
        )
        download_response.raise_for_status()

        return download_response.content

    async def stop_scan(self, scan_id: int) -> bool:
        """Stop running scan."""
        await self._authenticate()
        client = await self._get_session()

        response = await client.post(
            f"{self.url}/scans/{scan_id}/stop",
            headers=self._build_headers()
        )

        return response.status_code == 200

    async def delete_scan(self, scan_id: int) -> bool:
        """Delete scan."""
        await self._authenticate()
        client = await self._get_session()

        response = await client.delete(
            f"{self.url}/scans/{scan_id}",
            headers=self._build_headers()
        )

        return response.status_code == 200

    async def close(self):
        """Cleanup HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None
            self._session_token = None
