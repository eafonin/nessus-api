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
from typing import Dict, Any, Optional, Callable, Awaitable, TypeVar, List
from .base import ScannerInterface, ScanRequest
from .api_token_fetcher import fetch_and_verify_token

logger = logging.getLogger(__name__)

T = TypeVar('T')


class NessusScanner(ScannerInterface):
    """
    Native async Nessus scanner using httpx with Web UI simulation.

    Features:
    - Web UI authentication (session tokens)
    - Dynamic X-API-Token fetching (auto-adapts to Nessus rebuilds)
    - Bypasses scan_api: false restriction
    - Pure async/await (no subprocess calls)
    - Error handling for 412/403/404/409
    - SSH credential injection for authenticated scans (Phase 5)
    """

    # Template UUID for Advanced Scan
    TEMPLATE_ADVANCED_SCAN = "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66"

    # Folder and scanner IDs
    FOLDER_MY_SCANS = 3
    SCANNER_LOCAL = 1

    # Valid SSH privilege escalation methods (from nessusAPIWrapper/manage_credentials.py)
    VALID_ESCALATION_METHODS = {
        "Nothing",           # No privilege escalation
        "sudo",              # Most common - sudo to root
        "su",                # Switch user
        "su+sudo",           # Combined su then sudo
        "pbrun",             # PowerBroker
        "dzdo",              # Centrify DirectAuthorize
        ".k5login",          # Kerberos
        "Cisco 'enable'",    # Network devices
        "Checkpoint Gaia 'expert'"  # Checkpoint firewalls
    }

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
        self._api_token: Optional[str] = None  # Dynamically fetched X-API-Token

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create async HTTP session."""
        if not self._session:
            self._session = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=30.0,
                follow_redirects=True
            )
        return self._session

    async def _fetch_api_token(self) -> None:
        """
        Fetch X-API-Token dynamically from Nessus Web UI.

        The X-API-Token is hardcoded in /nessus6.js and changes when Nessus
        is rebuilt/reinstalled. This method ensures we always have the current token.
        """
        if self._api_token:
            return  # Already fetched

        logger.info("Fetching X-API-Token from Nessus Web UI...")
        token = await fetch_and_verify_token(
            self.url,
            self.username,
            self.password,
            self.verify_ssl
        )

        if not token:
            raise ValueError(
                "Failed to fetch X-API-Token from Nessus Web UI. "
                "Ensure Nessus is accessible and nessus6.js is available."
            )

        self._api_token = token
        logger.info(f"X-API-Token fetched successfully: {token}")

    async def _authenticate(self) -> None:
        """
        Authenticate with Nessus Web UI and get session token.

        Pattern from: manage_scans.py:27-84 + dynamic token fetching
        """
        if self._session_token:
            return  # Already authenticated

        # Ensure we have X-API-Token before authenticating
        await self._fetch_api_token()

        client = await self._get_session()

        # Minimal headers for authentication
        headers = {
            'Content-Type': 'application/json',
            'X-API-Token': self._api_token
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

            logger.info(f"Authentication successful for user: {self.username}")

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
            'X-API-Token': self._api_token,
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

        Phase 5: Supports SSH credential injection for authenticated scans.
        Credentials are validated and included in payload when provided.

        Args:
            request: Scan request parameters (includes optional credentials)

        Returns:
            scan_id: Nessus scan ID (integer)

        Raises:
            ValueError: If scan creation fails or credentials invalid
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

        # Phase 5: Add credentials if provided (authenticated/authenticated_privileged scans)
        if request.credentials:
            self._validate_credentials(request.credentials)
            payload["credentials"] = self._build_credentials_payload(request.credentials)
            logger.info(
                f"Creating authenticated scan '{request.name}' with SSH credentials "
                f"(user={request.credentials.get('username')}, "
                f"escalation={request.credentials.get('elevate_privileges_with', 'Nothing')})"
            )

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

        # Retry logic for session expiration
        for attempt in range(2):
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
                if e.response.status_code == 401 and attempt == 0:
                    # Session expired - clear tokens and retry with fresh authentication
                    logger.warning(f"Session expired for scan {scan_id}, re-authenticating...")
                    self._session_token = None
                    self._api_token = None
                    await self._authenticate()
                    continue  # Retry
                elif e.response.status_code == 404:
                    raise ValueError(f"Scan {scan_id} not found")
                raise ValueError(f"Status check failed: HTTP {e.response.status_code}")

        raise ValueError(f"Status check failed after retry")

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
            elif e.response.status_code == 409:
                # Scan in transitional state (just stopped, being processed, etc.)
                # This is expected behavior - scan will be deleted eventually
                logger.warning(f"Scan {scan_id} in transitional state (HTTP 409), marked for deletion")
                return True
            raise ValueError(f"Delete scan failed: HTTP {e.response.status_code}")

    async def list_scans(self) -> List[Dict[str, Any]]:
        """
        List all scans on this Nessus instance.

        Returns:
            List of scan dictionaries with keys:
                - id: Scan ID
                - name: Scan name
                - status: Current status (running, completed, etc.)
                - creation_date: Unix timestamp when created
                - last_modification_date: Unix timestamp of last modification
                - folder_id: Folder ID (2 = Trash)

        Raises:
            ValueError: If API call fails
        """
        await self._authenticate()
        client = await self._get_session()

        try:
            response = await client.get(
                f"{self.url}/scans",
                headers=self._build_headers()
            )
            response.raise_for_status()
            data = response.json()

            # Return scans list (exclude trash folder by default)
            scans = data.get("scans", []) or []
            return [s for s in scans if s.get("folder_id") != 2]

        except httpx.HTTPStatusError as e:
            raise ValueError(f"List scans failed: HTTP {e.response.status_code}")

    def _validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate credential structure before use.

        Args:
            credentials: Credential dictionary

        Raises:
            ValueError: If credentials are invalid
        """
        if not credentials:
            return

        cred_type = credentials.get("type", "ssh")

        if cred_type == "ssh":
            # Required fields for SSH
            required = ["username", "password"]
            for field in required:
                if not credentials.get(field):
                    raise ValueError(f"SSH credential missing required field: {field}")

            # Validate escalation config
            escalation = credentials.get("elevate_privileges_with", "Nothing")
            if escalation not in self.VALID_ESCALATION_METHODS:
                raise ValueError(
                    f"Invalid escalation method: {escalation}. "
                    f"Valid options: {', '.join(sorted(self.VALID_ESCALATION_METHODS))}"
                )
        else:
            raise ValueError(f"Unsupported credential type: {cred_type}")

    def _build_credentials_payload(
        self,
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build Nessus credentials payload from request credentials.

        Pattern from nessusAPIWrapper/manage_credentials.py

        Args:
            credentials: Credential dictionary with SSH details

        Returns:
            Nessus API credentials payload structure
        """
        cred_type = credentials.get("type", "ssh")

        if cred_type == "ssh":
            ssh_cred = {
                "auth_method": credentials.get("auth_method", "password"),
                "username": credentials["username"],
                "password": credentials["password"],
                "elevate_privileges_with": credentials.get(
                    "elevate_privileges_with", "Nothing"
                ),
                "custom_password_prompt": "",
                "target_priority_list": ""
            }

            # Add escalation fields if using sudo/su
            escalation = credentials.get("elevate_privileges_with", "Nothing")
            if escalation not in ("Nothing", ""):
                if credentials.get("escalation_password"):
                    ssh_cred["escalation_password"] = credentials["escalation_password"]
                if credentials.get("escalation_account"):
                    ssh_cred["escalation_account"] = credentials["escalation_account"]

            return {
                "add": {
                    "Host": {
                        "SSH": [ssh_cred]
                    }
                },
                "edit": {},
                "delete": []
            }

        raise ValueError(f"Unsupported credential type: {cred_type}")

    async def close(self) -> None:
        """Cleanup HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None
            self._session_token = None
            self._api_token = None
