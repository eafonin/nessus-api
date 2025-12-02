"""Unit tests for authenticated scan functionality (Phase 5)."""

from unittest.mock import AsyncMock, Mock

import pytest

from scanners.base import ScanRequest
from scanners.nessus_scanner import NessusScanner


class TestCredentialValidation:
    """Test credential validation logic."""

    @pytest.fixture
    def scanner(self):
        """Create scanner instance for testing."""
        return NessusScanner(
            url="https://127.0.0.1:8834",
            username="test",
            password="test",
            verify_ssl=False,
        )

    def test_missing_username_raises(self, scanner):
        """Test missing username raises validation error."""
        credentials = {"type": "ssh", "password": "pass"}

        with pytest.raises(ValueError, match="missing required field: username"):
            scanner._validate_credentials(credentials)

    def test_missing_password_raises(self, scanner):
        """Test missing password raises validation error."""
        credentials = {"type": "ssh", "username": "user"}

        with pytest.raises(ValueError, match="missing required field: password"):
            scanner._validate_credentials(credentials)

    def test_invalid_escalation_method_raises(self, scanner):
        """Test invalid escalation method raises error."""
        credentials = {
            "type": "ssh",
            "username": "user",
            "password": "pass",
            "elevate_privileges_with": "invalid_method",
        }

        with pytest.raises(ValueError, match="Invalid escalation method"):
            scanner._validate_credentials(credentials)

    def test_valid_ssh_credentials_pass(self, scanner):
        """Test valid SSH credentials pass validation."""
        credentials = {"type": "ssh", "username": "testuser", "password": "testpass"}

        # Should not raise
        scanner._validate_credentials(credentials)

    def test_valid_sudo_credentials_pass(self, scanner):
        """Test valid sudo escalation credentials pass."""
        credentials = {
            "type": "ssh",
            "username": "testuser",
            "password": "testpass",
            "elevate_privileges_with": "sudo",
            "escalation_password": "sudopass",
        }

        # Should not raise
        scanner._validate_credentials(credentials)

    def test_all_valid_escalation_methods(self, scanner):
        """Test all valid escalation methods pass."""
        valid_methods = [
            "Nothing",
            "sudo",
            "su",
            "su+sudo",
            "pbrun",
            "dzdo",
            ".k5login",
            "Cisco 'enable'",
            "Checkpoint Gaia 'expert'",
        ]

        for method in valid_methods:
            credentials = {
                "type": "ssh",
                "username": "user",
                "password": "pass",
                "elevate_privileges_with": method,
            }
            # Should not raise
            scanner._validate_credentials(credentials)

    def test_unsupported_credential_type_raises(self, scanner):
        """Test unsupported credential type raises error."""
        credentials = {"type": "windows", "username": "admin", "password": "pass"}

        with pytest.raises(ValueError, match="Unsupported credential type"):
            scanner._validate_credentials(credentials)

    def test_empty_credentials_pass(self, scanner):
        """Test empty/None credentials pass (untrusted scan)."""
        scanner._validate_credentials(None)
        scanner._validate_credentials({})


class TestCredentialPayloadBuilder:
    """Test credential payload generation."""

    @pytest.fixture
    def scanner(self):
        """Create scanner instance for testing."""
        return NessusScanner(
            url="https://127.0.0.1:8834",
            username="test",
            password="test",
            verify_ssl=False,
        )

    def test_basic_ssh_password_credentials(self, scanner):
        """Test basic SSH password credential payload."""
        credentials = {"type": "ssh", "username": "testuser", "password": "testpass"}

        payload = scanner._build_credentials_payload(credentials)

        assert "add" in payload
        assert "Host" in payload["add"]
        assert "SSH" in payload["add"]["Host"]

        ssh_cred = payload["add"]["Host"]["SSH"][0]
        assert ssh_cred["username"] == "testuser"
        assert ssh_cred["password"] == "testpass"
        assert ssh_cred["auth_method"] == "password"
        assert ssh_cred["elevate_privileges_with"] == "Nothing"
        assert ssh_cred["custom_password_prompt"] == ""
        assert ssh_cred["target_priority_list"] == ""

    def test_ssh_sudo_with_password(self, scanner):
        """Test SSH with sudo escalation requiring password."""
        credentials = {
            "type": "ssh",
            "username": "testauth_sudo_pass",
            "password": "TestPass123!",
            "elevate_privileges_with": "sudo",
            "escalation_password": "TestPass123!",
        }

        payload = scanner._build_credentials_payload(credentials)

        ssh_cred = payload["add"]["Host"]["SSH"][0]
        assert ssh_cred["elevate_privileges_with"] == "sudo"
        assert ssh_cred["escalation_password"] == "TestPass123!"

    def test_ssh_sudo_with_escalation_account(self, scanner):
        """Test SSH with sudo and custom escalation account."""
        credentials = {
            "type": "ssh",
            "username": "scanuser",
            "password": "scanpass",
            "elevate_privileges_with": "sudo",
            "escalation_account": "admin",
            "escalation_password": "adminpass",
        }

        payload = scanner._build_credentials_payload(credentials)

        ssh_cred = payload["add"]["Host"]["SSH"][0]
        assert ssh_cred["escalation_account"] == "admin"
        assert ssh_cred["escalation_password"] == "adminpass"

    def test_ssh_sudo_nopasswd(self, scanner):
        """Test SSH with sudo NOPASSWD (no escalation_password)."""
        credentials = {
            "type": "ssh",
            "username": "testauth_sudo_nopass",
            "password": "TestPass123!",
            "elevate_privileges_with": "sudo",
            # No escalation_password
        }

        payload = scanner._build_credentials_payload(credentials)

        ssh_cred = payload["add"]["Host"]["SSH"][0]
        assert ssh_cred["elevate_privileges_with"] == "sudo"
        assert "escalation_password" not in ssh_cred

    def test_payload_structure_complete(self, scanner):
        """Test complete payload structure for Nessus API."""
        credentials = {"type": "ssh", "username": "user", "password": "pass"}

        payload = scanner._build_credentials_payload(credentials)

        # Verify structure matches Nessus API requirements
        assert payload == {
            "add": {
                "Host": {
                    "SSH": [
                        {
                            "auth_method": "password",
                            "username": "user",
                            "password": "pass",
                            "elevate_privileges_with": "Nothing",
                            "custom_password_prompt": "",
                            "target_priority_list": "",
                        }
                    ]
                }
            },
            "edit": {},
            "delete": [],
        }

    def test_su_escalation(self, scanner):
        """Test su escalation method."""
        credentials = {
            "type": "ssh",
            "username": "user",
            "password": "pass",
            "elevate_privileges_with": "su",
            "escalation_password": "rootpass",
        }

        payload = scanner._build_credentials_payload(credentials)

        ssh_cred = payload["add"]["Host"]["SSH"][0]
        assert ssh_cred["elevate_privileges_with"] == "su"
        assert ssh_cred["escalation_password"] == "rootpass"


class TestScanRequestWithCredentials:
    """Test ScanRequest creation with credentials."""

    def test_scan_request_with_credentials(self):
        """Test ScanRequest accepts credentials."""
        credentials = {
            "type": "ssh",
            "username": "testuser",
            "password": "testpass",
            "elevate_privileges_with": "sudo",
        }

        request = ScanRequest(
            targets="172.32.0.215",
            name="Test Auth Scan",
            scan_type="authenticated",
            description="Test authenticated scan",
            credentials=credentials,
        )

        assert request.credentials == credentials
        assert request.scan_type == "authenticated"
        assert request.targets == "172.32.0.215"

    def test_scan_request_without_credentials(self):
        """Test ScanRequest works without credentials (untrusted)."""
        request = ScanRequest(
            targets="172.32.0.215", name="Test Untrusted Scan", scan_type="untrusted"
        )

        assert request.credentials is None
        assert request.scan_type == "untrusted"


class TestCreateScanWithCredentials:
    """Test create_scan method with credentials (mocked)."""

    @pytest.fixture
    def scanner(self):
        """Create scanner instance for testing."""
        return NessusScanner(
            url="https://127.0.0.1:8834",
            username="test",
            password="test",
            verify_ssl=False,
        )

    @pytest.mark.asyncio
    async def test_create_scan_includes_credentials_in_payload(self, scanner):
        """Test create_scan includes credentials in API payload."""
        credentials = {
            "type": "ssh",
            "username": "testuser",
            "password": "testpass",
            "elevate_privileges_with": "Nothing",
        }

        request = ScanRequest(
            targets="192.168.1.1", name="Test Scan", credentials=credentials
        )

        # Mock HTTP client and authentication
        mock_response = Mock()
        mock_response.json.return_value = {"scan": {"id": 123}}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.get = AsyncMock()

        scanner._session = mock_client
        scanner._session_token = "test_token"
        scanner._api_token = "test_api_token"

        # Call create_scan
        scan_id = await scanner.create_scan(request)

        assert scan_id == 123

        # Verify credentials were included in payload
        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")

        assert "credentials" in payload
        assert payload["credentials"]["add"]["Host"]["SSH"][0]["username"] == "testuser"
        assert payload["credentials"]["add"]["Host"]["SSH"][0]["password"] == "testpass"

    @pytest.mark.asyncio
    async def test_create_scan_without_credentials(self, scanner):
        """Test create_scan works without credentials."""
        request = ScanRequest(
            targets="192.168.1.1", name="Test Untrusted Scan", credentials=None
        )

        # Mock HTTP client and authentication
        mock_response = Mock()
        mock_response.json.return_value = {"scan": {"id": 456}}
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.get = AsyncMock()

        scanner._session = mock_client
        scanner._session_token = "test_token"
        scanner._api_token = "test_api_token"

        # Call create_scan
        scan_id = await scanner.create_scan(request)

        assert scan_id == 456

        # Verify credentials were NOT included in payload
        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")

        assert "credentials" not in payload
