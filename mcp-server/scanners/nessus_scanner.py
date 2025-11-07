"""
Native async Nessus scanner implementation using proven wrapper patterns.

This implementation follows the exact HTTP patterns from nessusAPIWrapper/,
validated to work with Nessus Essentials and bypass scan_api: false restriction.

References:
- NESSUS_HTTP_PATTERNS.md - Extracted patterns
- nessusAPIWrapper/manage_scans.py - Authentication and create
- nessusAPIWrapper/launch_scan.py - Launch and stop
- nessusAPIWrapper/export_vulnerabilities.py - Export workflow
- HTTPX_READERROR_INVESTIGATION.md - ReadError workaround (Option 4)
"""
import asyncio
import httpx
import logging
from typing import Dict, Any, Optional, Callable, Awaitable, TypeVar
from .base import ScannerInterface, ScanRequest

logger = logging.getLogger(__name__)

T = TypeVar('T')


class NessusScanner(ScannerInterface):
    """
    Native async Nessus scanner using httpx with Web UI simulation.

    Features:
    - Web UI authentication (session tokens)
    - Bypasses scan_api: false restriction
    - Pure async/await (no subprocess calls)
    - Error handling for 412/403/404/409
    """

    # Static API token (never changes) - from wrapper
    STATIC_API_TOKEN = "af824aba-e642-4e63-a49b-0810542ad8a5"

    # Template UUID for Advanced Scan
    TEMPLATE_ADVANCED_SCAN = "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66"

    # Folder and scanner IDs
    FOLDER_MY_SCANS = 3
    SCANNER_LOCAL = 1

    # Status mapping: Nessus → MCP
    STATUS_MAP = {
        "pending": "queued",
        "running": "running",
        "paused": "running",  # Treat paused as still running
        "completed": "completed",
        "canceled": "failed",
        "stopped": "failed",
        "aborted": "failed",
        "empty": "queued",  # Never launched
    }

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        verify_ssl: bool = False
    ):
        """
        Initialize Nessus scanner.

        Args:
            url: Nessus URL (e.g., https://172.18.0.2:8834)
            username: Nessus username
            password: Nessus password
            verify_ssl: Enable SSL verification (False for self-signed certs)
        """
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl

        # HTTP session and tokens
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
        """
        Authenticate with Nessus Web UI and get session token.

        Pattern from: manage_scans.py:27-84
        """
        if self._session_token:
            return  # Already authenticated

        client = await self._get_session()

        # Minimal headers for authentication
        headers = {
            'Content-Type': 'application/json',
            'X-API-Token': self.STATIC_API_TOKEN
        }

        payload = {
            'username': self.username,
            'password': self.password
        }

        try:
            response = await client.post(
                f"{self.url}/session",
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            data = response.json()
            self._session_token = data.get('token')

            if not self._session_token:
                raise ValueError("No session token in response")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError(f"Authentication failed: invalid credentials")
            elif e.response.status_code == 403:
                raise ValueError(f"Authentication forbidden: check Nessus permissions")
            raise ValueError(f"Authentication failed: HTTP {e.response.status_code}")

    def _build_headers(self, web_ui_marker: bool = False) -> Dict[str, str]:
        """
        Build authenticated request headers.

        Args:
            web_ui_marker: Add X-KL-kfa-Ajax-Request header (required for launch/stop)

        Returns:
            Headers dict
        """
        if not self._session_token:
            raise ValueError("Not authenticated - call _authenticate() first")

        headers = {
            'Content-Type': 'application/json',
            'X-API-Token': self.STATIC_API_TOKEN,
            'X-Cookie': f'token={self._session_token}'
        }

        if web_ui_marker:
            # CRITICAL: Web UI simulation marker for launch/stop operations
            headers['X-KL-kfa-Ajax-Request'] = 'Ajax_Request'

        return headers

    async def _handle_read_error(
        self,
        operation_name: str,
        request_func: Callable[[], Awaitable[T]],
        verify_func: Optional[Callable[[], Awaitable[Optional[T]]]] = None,
        allow_412: bool = True
    ) -> T:
        """
        Execute write operation with ReadError workaround.

        Nessus server bug: Returns HTTP 412 with Connection: close, then closes
        TCP connection before sending promised response body. This causes
        httpx.ReadError on all write operations (POST/PUT/DELETE).

        Workaround (Option 4 from HTTPX_READERROR_INVESTIGATION.md):
        1. Try operation
        2. If ReadError caught, call verify_func to check if operation succeeded
        3. If verification confirms success, return result
        4. Otherwise raise ValueError

        Args:
            operation_name: Name of operation for logging
            request_func: Async function that makes the HTTP request
            verify_func: Optional async function to verify operation success
            allow_412: If True, treat HTTP 412 as expected failure (not error)

        Returns:
            Result from request_func or verify_func

        Raises:
            ValueError: If operation failed (confirmed by verification)
        """
        try:
            return await request_func()

        except httpx.ReadError as e:
            logger.warning(f"{operation_name}: ReadError caught (Nessus server bug)")
            logger.debug(f"{operation_name}: Error details: {e}")

            if verify_func:
                logger.info(f"{operation_name}: Verifying operation result...")
                result = await verify_func()

                if result is not None:
                    logger.warning(
                        f"{operation_name}: Operation succeeded despite ReadError"
                    )
                    return result

            # No verification function or verification returned None
            logger.error(f"{operation_name}: Operation failed (no result confirmed)")
            raise ValueError(
                f"{operation_name} failed: Nessus API unavailable "
                "(scan_api: false restriction causes HTTP 412 + connection drop)"
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 412 and allow_412:
                # HTTP 412 is expected for Nessus Essentials
                logger.warning(
                    f"{operation_name}: HTTP 412 Precondition Failed "
                    "(Nessus Essentials limitation)"
                )
                raise ValueError(
                    f"{operation_name} blocked: Nessus Essentials (scan_api: false)"
                )
            # Re-raise other HTTP errors
            raise

    async def create_scan(self, request: ScanRequest) -> int:
        """
        Create Nessus scan using Web UI pattern.

        Pattern from: manage_scans.py:312-424
        ReadError handling: HTTPX_READERROR_INVESTIGATION.md Option 4

        Args:
            request: Scan request parameters

        Returns:
            scan_id: Nessus scan ID (integer)

        Raises:
            ValueError: If scan creation fails
        """
        await self._authenticate()
        client = await self._get_session()

        # Build scan payload - pattern from wrapper
        payload = {
            "uuid": self.TEMPLATE_ADVANCED_SCAN,
            "settings": {
                "name": request.name,
                "text_targets": request.targets,
                "description": request.description or request.name,
                "enabled": True,
                "folder_id": self.FOLDER_MY_SCANS,
                "scanner_id": self.SCANNER_LOCAL,
                "launch_now": False  # Always explicit launch
            }
        }

        async def _do_create() -> int:
            """Execute create scan HTTP request."""
            response = await client.post(
                f"{self.url}/scans",
                json=payload,
                headers=self._build_headers()
            )
            response.raise_for_status()

            data = response.json()
            scan_id = data["scan"]["id"]

            if not isinstance(scan_id, int) or scan_id <= 0:
                raise ValueError(f"Invalid scan_id returned: {scan_id}")

            return scan_id

        async def _verify_create() -> Optional[int]:
            """Verify scan was created by checking scan list."""
            try:
                # List all scans and find one with matching name
                response = await client.get(
                    f"{self.url}/scans",
                    headers=self._build_headers()
                )
                response.raise_for_status()
                data = response.json()

                scans = data.get("scans", [])
                for scan in scans:
                    if scan.get("name") == request.name:
                        scan_id = scan.get("id")
                        if isinstance(scan_id, int) and scan_id > 0:
                            logger.info(
                                f"Verified scan created: ID={scan_id}, "
                                f"Name={request.name}"
                            )
                            return scan_id

                logger.warning(f"No scan found with name: {request.name}")
                return None

            except Exception as e:
                logger.error(f"Verification failed: {e}")
                return None

        # Use ReadError handler with verification
        try:
            return await self._handle_read_error(
                operation_name="create_scan",
                request_func=_do_create,
                verify_func=_verify_create,
                allow_412=True
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise ValueError("Forbidden: API restriction (use Web UI headers)")
            elif e.response.status_code == 400:
                raise ValueError(f"Bad request: {e.response.text[:200]}")
            raise ValueError(f"Scan creation failed: HTTP {e.response.status_code}")

    async def launch_scan(self, scan_id: int) -> str:
        """
        Launch Nessus scan using Web UI simulation.

        Pattern from: launch_scan.py:117-163

        CRITICAL: Requires X-KL-kfa-Ajax-Request header to bypass API restriction.

        Args:
            scan_id: Nessus scan ID

        Returns:
            scan_uuid: Scan UUID string

        Raises:
            ValueError: If launch fails
        """
        await self._authenticate()
        client = await self._get_session()

        try:
            response = await client.post(
                f"{self.url}/scans/{scan_id}/launch",
                json={},  # Empty payload
                headers=self._build_headers(web_ui_marker=True)  # CRITICAL!
            )
            response.raise_for_status()

            data = response.json()
            scan_uuid = data.get("scan_uuid")

            if not scan_uuid:
                raise ValueError("No scan_uuid in response")

            return scan_uuid

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise ValueError("Forbidden: Missing X-KL-kfa-Ajax-Request header")
            elif e.response.status_code == 404:
                raise ValueError(f"Scan {scan_id} not found")
            elif e.response.status_code == 409:
                raise ValueError(f"Scan {scan_id} already running")
            raise ValueError(f"Scan launch failed: HTTP {e.response.status_code}")

    async def get_status(self, scan_id: int) -> Dict[str, Any]:
        """
        Get scan status and progress.

        Pattern from: list_scans.py + inline GET /scans/{id}

        Args:
            scan_id: Nessus scan ID

        Returns:
            {
                "status": "queued|running|completed|failed",
                "progress": 0-100,
                "uuid": "scan-uuid",
                "info": {...}  # Full Nessus response
            }

        Raises:
            ValueError: If scan not found
        """
        await self._authenticate()
        client = await self._get_session()

        try:
            response = await client.get(
                f"{self.url}/scans/{scan_id}",
                headers=self._build_headers()
            )
            response.raise_for_status()

            data = response.json()
            info = data.get("info", {})

            # Map Nessus status to MCP status
            nessus_status = info.get("status", "unknown")
            mapped_status = self.STATUS_MAP.get(nessus_status, "unknown")

            return {
                "status": mapped_status,
                "progress": info.get("progress", 0),
                "uuid": info.get("uuid", ""),
                "info": info  # Full response for debugging
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Scan {scan_id} not found")
            raise ValueError(f"Status check failed: HTTP {e.response.status_code}")

    async def export_results(self, scan_id: int) -> bytes:
        """
        Export scan results in native .nessus XML format.

        Pattern from: export_vulnerabilities.py:142-171

        Three-step process:
        1. Request export (POST /scans/{id}/export)
        2. Poll export status (GET /scans/{id}/export/{file_id}/status)
        3. Download export (GET /scans/{id}/export/{file_id}/download)

        Args:
            scan_id: Nessus scan ID

        Returns:
            Raw .nessus XML bytes

        Raises:
            ValueError: If export fails
            TimeoutError: If export doesn't complete in 5 minutes
        """
        await self._authenticate()
        client = await self._get_session()

        try:
            # Step 1: Request export
            response = await client.post(
                f"{self.url}/scans/{scan_id}/export",
                json={"format": "nessus"},
                headers=self._build_headers()
            )
            response.raise_for_status()

            file_id = response.json().get("file")
            if not file_id:
                raise ValueError("No file ID in export response")

            # Step 2: Poll export status (max 5 minutes)
            max_iterations = 150  # 150 × 2 seconds = 5 minutes
            for iteration in range(max_iterations):
                await asyncio.sleep(2)

                status_response = await client.get(
                    f"{self.url}/scans/{scan_id}/export/{file_id}/status",
                    headers=self._build_headers()
                )
                status_response.raise_for_status()

                status = status_response.json().get("status")
                if status == "ready":
                    break
            else:
                raise TimeoutError(f"Export did not complete in {max_iterations * 2} seconds")

            # Step 3: Download export
            download_response = await client.get(
                f"{self.url}/scans/{scan_id}/export/{file_id}/download",
                headers=self._build_headers()
            )
            download_response.raise_for_status()

            return download_response.content

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Scan {scan_id} not found or no results available")
            raise ValueError(f"Export failed: HTTP {e.response.status_code}")

    async def stop_scan(self, scan_id: int) -> bool:
        """
        Stop running scan.

        Pattern from: launch_scan.py:166-213

        Args:
            scan_id: Nessus scan ID

        Returns:
            True if stopped successfully

        Raises:
            ValueError: If stop fails
        """
        await self._authenticate()
        client = await self._get_session()

        try:
            response = await client.post(
                f"{self.url}/scans/{scan_id}/stop",
                json={},
                headers=self._build_headers(web_ui_marker=True)  # Requires marker
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Scan {scan_id} not found")
            elif e.response.status_code == 409:
                # Already stopped or not running
                return True
            raise ValueError(f"Stop scan failed: HTTP {e.response.status_code}")

    async def delete_scan(self, scan_id: int) -> bool:
        """
        Delete scan (two-step: move to trash, then delete).

        Pattern from: manage_scans.py:612-629

        Args:
            scan_id: Nessus scan ID

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If delete fails
        """
        await self._authenticate()
        client = await self._get_session()

        try:
            # Step 1: Move to trash folder
            await client.put(
                f"{self.url}/scans/{scan_id}",
                json={"folder_id": 2},  # Folder 2 = Trash
                headers=self._build_headers()
            )

            # Step 2: Delete from trash
            response = await client.delete(
                f"{self.url}/scans/{scan_id}",
                headers=self._build_headers()
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Already deleted
                return True
            raise ValueError(f"Delete scan failed: HTTP {e.response.status_code}")

    async def close(self) -> None:
        """Cleanup HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None
            self._session_token = None
