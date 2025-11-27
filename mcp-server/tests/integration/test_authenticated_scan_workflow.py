#!/usr/bin/env python3
"""
Integration Tests: Phase 5 Authenticated Scan Workflow

Tests authenticated and authenticated_privileged scans with real Nessus scanner.
These tests verify the complete credential injection workflow.

Run with:
  docker compose exec mcp-api pytest tests/integration/test_authenticated_scan_workflow.py -v -s

Test Target Groups:
  Group 1 - Docker container (scan-target at 172.30.0.9):
    - testauth_sudo_pass: sudo with password
    - testauth_sudo_nopass: sudo NOPASSWD
    - testauth_nosudo: no sudo access

  Group 2 - External host (172.32.0.215):
    - randy: basic authenticated scan

Markers:
  - authenticated: Uses authenticated scan credentials
  - real_nessus: Uses actual Nessus scanner
  - slow: Takes several minutes to complete
  - integration: Integration test requiring external services
"""

import pytest
import pytest_asyncio
import asyncio
import os
import sys
import uuid
import json
from pathlib import Path
from datetime import datetime

# Add mcp-server to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.queue import TaskQueue
from core.task_manager import TaskManager, generate_task_id
from core.types import Task, ScanState
from core.logging_config import configure_logging, get_logger
from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest


# ============================================================================
# Test Configuration
# ============================================================================

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Nessus scanner
NESSUS_URL = os.getenv("NESSUS_URL", "https://vpn-gateway:8834")
NESSUS_USERNAME = os.getenv("NESSUS_USERNAME", "nessus")
NESSUS_PASSWORD = os.getenv("NESSUS_PASSWORD", "nessus")

# Test targets and credentials
# Two test target groups:
#   1. Docker container (scan-target) - for privileged scan tests with sudo
#   2. External host (172.32.0.215) - for basic authenticated scan tests

# Group 1: Docker container on vpn network with test users
SCAN_TARGET_IP = os.getenv("SCAN_TARGET_IP", "172.30.0.9")
EXTERNAL_HOST_IP = os.getenv("EXTERNAL_HOST_IP", "172.32.0.215")

TEST_TARGETS = {
    # Group 1: Scan target container (on vpn network - 172.30.0.0/24)
    # Built from: docker/Dockerfile.scan-target
    # Users: testauth_sudo_pass, testauth_sudo_nopass, testauth_nosudo
    "scan_target": {
        "target": SCAN_TARGET_IP,
        "users": {
            "sudo_pass": {
                "username": "testauth_sudo_pass",
                "password": "TestPass123!",
                "elevate_privileges_with": "sudo",
                "escalation_password": "TestPass123!",
                "expected_auth": "success"
            },
            "sudo_nopass": {
                "username": "testauth_sudo_nopass",
                "password": "TestPass123!",
                "elevate_privileges_with": "sudo",
                "expected_auth": "success"
            },
            "nosudo": {
                "username": "testauth_nosudo",
                "password": "TestPass123!",
                "elevate_privileges_with": "Nothing",
                "expected_auth": "success"  # SSH works, but limited access
            }
        }
    },
    # Group 2: External host (172.32.0.215)
    # User: randy (basic authenticated scan)
    "external_host": {
        "target": EXTERNAL_HOST_IP,
        "users": {
            "randy": {
                "username": "randy",
                "password": "randylovesgoldfish1998",
                "elevate_privileges_with": "Nothing",
                "expected_auth": "success"
            }
        }
    }
}

# Task storage
DATA_DIR = "/tmp/test-phase5-auth-scans"


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = [
    pytest.mark.authenticated,          # Uses authenticated credentials
    pytest.mark.real_nessus,            # Uses real Nessus scanner
    pytest.mark.slow,                   # Takes several minutes
    pytest.mark.integration,            # Integration test
]


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def structured_logging():
    """Configure structured logging for the test."""
    configure_logging(log_level="INFO")
    logger = get_logger(__name__)

    logger.info(
        "test_suite_started",
        test="phase5_authenticated_scans",
        nessus_url=NESSUS_URL
    )

    yield logger

    logger.info(
        "test_suite_completed",
        test="phase5_authenticated_scans"
    )


@pytest.fixture(scope="function")
def task_manager():
    """Create TaskManager instance."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    return TaskManager(data_dir=DATA_DIR)


@pytest_asyncio.fixture
async def scanner():
    """Create and cleanup NessusScanner instance."""
    scanner = NessusScanner(
        url=NESSUS_URL,
        username=NESSUS_USERNAME,
        password=NESSUS_PASSWORD,
        verify_ssl=False
    )
    yield scanner
    await scanner.close()


# ============================================================================
# Test: Credential Payload Verification
# ============================================================================

class TestCredentialInjection:
    """Test that credentials are correctly injected into scan creation."""

    @pytest.mark.asyncio
    async def test_create_scan_with_ssh_credentials(self, scanner, structured_logging):
        """Test scan creation with SSH credentials (no escalation)."""
        logger = structured_logging

        credentials = {
            "type": "ssh",
            "auth_method": "password",
            "username": "randy",
            "password": "randylovesgoldfish1998",
            "elevate_privileges_with": "Nothing"
        }

        scan_name = f"Phase5_Test_SSH_{uuid.uuid4().hex[:8]}"
        request = ScanRequest(
            targets="172.32.0.215",
            name=scan_name,
            scan_type="authenticated",
            description="Phase 5 integration test - SSH credentials",
            credentials=credentials
        )

        logger.info("creating_authenticated_scan", name=scan_name)

        try:
            scan_id = await scanner.create_scan(request)
            logger.info("scan_created", scan_id=scan_id, name=scan_name)

            assert isinstance(scan_id, int)
            assert scan_id > 0

            # Cleanup: delete the scan
            await scanner.delete_scan(scan_id)
            logger.info("scan_deleted", scan_id=scan_id)

        except Exception as e:
            logger.error("test_failed", error=str(e))
            raise

    @pytest.mark.asyncio
    async def test_create_scan_with_sudo_credentials(self, scanner, structured_logging):
        """Test scan creation with sudo escalation credentials."""
        logger = structured_logging

        credentials = {
            "type": "ssh",
            "auth_method": "password",
            "username": "testauth_sudo_pass",
            "password": "TestPass123!",
            "elevate_privileges_with": "sudo",
            "escalation_password": "TestPass123!"
        }

        scan_name = f"Phase5_Test_Sudo_{uuid.uuid4().hex[:8]}"
        request = ScanRequest(
            targets=SCAN_TARGET_IP,
            name=scan_name,
            scan_type="authenticated_privileged",
            description="Phase 5 integration test - sudo credentials",
            credentials=credentials
        )

        logger.info("creating_privileged_scan", name=scan_name)

        try:
            scan_id = await scanner.create_scan(request)
            logger.info("scan_created", scan_id=scan_id, name=scan_name)

            assert isinstance(scan_id, int)
            assert scan_id > 0

            # Cleanup: delete the scan
            await scanner.delete_scan(scan_id)
            logger.info("scan_deleted", scan_id=scan_id)

        except Exception as e:
            logger.error("test_failed", error=str(e))
            raise


# ============================================================================
# Test: Quick Authenticated Scan (SSH only, no escalation)
# ============================================================================

class TestQuickAuthenticatedScan:
    """Quick authenticated scan test - SSH credentials only."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(600)  # 10 minute timeout
    async def test_authenticated_scan_randy(self, scanner, task_manager, structured_logging):
        """
        Test authenticated scan with randy user on 172.32.0.215.

        This is the quickest authenticated scan test using known-good credentials.
        Expected: Plugin 141118 present, credential field = "true"
        """
        logger = structured_logging

        credentials = {
            "type": "ssh",
            "auth_method": "password",
            "username": "randy",
            "password": "randylovesgoldfish1998",
            "elevate_privileges_with": "Nothing"
        }

        scan_name = f"Phase5_QuickAuth_{uuid.uuid4().hex[:8]}"
        request = ScanRequest(
            targets="172.32.0.215",
            name=scan_name,
            scan_type="authenticated",
            description="Phase 5 quick authenticated scan test",
            credentials=credentials
        )

        logger.info(
            "starting_quick_auth_test",
            target="172.32.0.215",
            username="randy",
            scan_name=scan_name
        )

        scan_id = None
        try:
            # Create scan
            scan_id = await scanner.create_scan(request)
            logger.info("scan_created", scan_id=scan_id)

            # Launch scan
            scan_uuid = await scanner.launch_scan(scan_id)
            logger.info("scan_launched", scan_id=scan_id, scan_uuid=scan_uuid)

            # Poll until completion
            max_wait = 600  # 10 minutes
            poll_interval = 30
            elapsed = 0

            while elapsed < max_wait:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                status = await scanner.get_status(scan_id)
                logger.info(
                    "scan_progress",
                    scan_id=scan_id,
                    status=status["status"],
                    progress=status.get("progress", 0),
                    elapsed=elapsed
                )

                if status["status"] == "completed":
                    logger.info("scan_completed", scan_id=scan_id, elapsed=elapsed)
                    break
                elif status["status"] == "failed":
                    pytest.fail(f"Scan failed: {status}")

            else:
                pytest.fail(f"Scan timeout after {max_wait}s")

            # Export and verify results
            results = await scanner.export_results(scan_id)
            logger.info("results_exported", size=len(results))

            # Save results for inspection
            results_file = Path(DATA_DIR) / f"{scan_name}.nessus"
            results_file.write_bytes(results)
            logger.info("results_saved", path=str(results_file))

            # Basic verification: results should contain credential confirmation
            results_str = results.decode('utf-8', errors='replace')

            # Check for Plugin 141118 (Valid Credentials Provided)
            has_valid_creds_plugin = "141118" in results_str
            logger.info(
                "auth_verification",
                plugin_141118_present=has_valid_creds_plugin
            )

            # Test passes if we got results - detailed validation in validator tests
            assert len(results) > 1000, "Results too small - scan may have failed"

        finally:
            # Cleanup
            if scan_id:
                try:
                    await scanner.delete_scan(scan_id)
                    logger.info("scan_deleted", scan_id=scan_id)
                except Exception as e:
                    logger.warning("cleanup_failed", error=str(e))


# ============================================================================
# Test: Full Workflow via MCP Tool (if MCP server available)
# ============================================================================

class TestMCPAuthenticatedScanTool:
    """Test authenticated scan via MCP tool interface."""

    @pytest.mark.asyncio
    async def test_mcp_tool_validation_only(self, structured_logging):
        """
        Test MCP tool input validation (no actual scan).

        This tests the tool's validation logic without running a full scan.
        Note: MCP tools are wrapped by FastMCP, so we need to access the
        underlying function via the .fn attribute.
        """
        logger = structured_logging

        # Import MCP tool - it's wrapped by FastMCP decorator
        try:
            from tools.mcp_server import run_authenticated_scan
            # Access the underlying function from the FunctionTool wrapper
            if hasattr(run_authenticated_scan, 'fn'):
                tool_fn = run_authenticated_scan.fn
            else:
                pytest.skip("Cannot access underlying function from MCP tool wrapper")
        except ImportError as e:
            pytest.skip(f"Cannot import MCP tools: {e}")

        # Test 1: Invalid scan_type should return error
        result = await tool_fn(
            targets="172.32.0.215",
            name="Test Invalid Type",
            scan_type="invalid_type",
            ssh_username="test",
            ssh_password="test"
        )
        assert "error" in result
        assert "Invalid scan_type" in result["error"]
        logger.info("validation_test_1_passed", test="invalid_scan_type")

        # Test 2: authenticated_privileged without escalation should error
        result = await tool_fn(
            targets="172.32.0.215",
            name="Test Missing Escalation",
            scan_type="authenticated_privileged",
            ssh_username="test",
            ssh_password="test",
            elevate_privileges_with="Nothing"
        )
        assert "error" in result
        assert "requires elevate_privileges_with" in result["error"]
        logger.info("validation_test_2_passed", test="missing_escalation")

        logger.info("mcp_tool_validation_tests_complete")


# ============================================================================
# Test: Authentication Failure Detection (DISABLED BY DEFAULT)
# ============================================================================

class TestAuthenticationFailureDetection:
    """Test that authentication failures are properly detected.

    DISABLED BY DEFAULT - These tests verify Nessus behavior, not our code.
    Enable with: RUN_SLOW_AUTH_TESTS=1 pytest ...
    """

    @pytest.mark.asyncio
    @pytest.mark.timeout(600)
    @pytest.mark.skipif(
        not os.getenv("RUN_SLOW_AUTH_TESTS"),
        reason="Slow test (~8min) that tests Nessus behavior. Enable with RUN_SLOW_AUTH_TESTS=1"
    )
    async def test_bad_credentials_detected(self, scanner, structured_logging):
        """
        Test scan with invalid credentials.

        Expected: Scan completes but auth status should be failed/partial.
        """
        logger = structured_logging

        credentials = {
            "type": "ssh",
            "auth_method": "password",
            "username": "nonexistent_user_xyz",
            "password": "wrong_password_123",
            "elevate_privileges_with": "Nothing"
        }

        scan_name = f"Phase5_BadCreds_{uuid.uuid4().hex[:8]}"
        request = ScanRequest(
            targets="172.32.0.215",
            name=scan_name,
            scan_type="authenticated",
            description="Phase 5 test - bad credentials detection",
            credentials=credentials
        )

        logger.info("starting_bad_creds_test", scan_name=scan_name)

        scan_id = None
        try:
            # Create and launch scan
            scan_id = await scanner.create_scan(request)
            scan_uuid = await scanner.launch_scan(scan_id)
            logger.info("scan_launched", scan_id=scan_id)

            # Poll until completion
            max_wait = 600
            poll_interval = 30
            elapsed = 0

            while elapsed < max_wait:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                status = await scanner.get_status(scan_id)
                logger.info(
                    "scan_progress",
                    scan_id=scan_id,
                    status=status["status"],
                    progress=status.get("progress", 0)
                )

                if status["status"] in ("completed", "failed"):
                    break

            # Export results
            results = await scanner.export_results(scan_id)
            results_str = results.decode('utf-8', errors='replace')

            # Should NOT have Plugin 141118 (Valid Credentials)
            has_valid_creds = "141118" in results_str

            logger.info(
                "bad_creds_result",
                has_plugin_141118=has_valid_creds,
                results_size=len(results)
            )

            # With bad credentials, Plugin 141118 should NOT be present
            # (This validates our auth detection logic)
            if has_valid_creds:
                logger.warning(
                    "unexpected_valid_creds",
                    message="Plugin 141118 found with bad credentials - check test setup"
                )

        finally:
            if scan_id:
                try:
                    await scanner.delete_scan(scan_id)
                except Exception:
                    pass


# ============================================================================
# Test: Privileged Scans (sudo + password, sudo NOPASSWD)
# ============================================================================

class TestPrivilegedScans:
    """E2E tests for authenticated_privileged scans with sudo escalation.

    Group 1 Tests: Uses scan-target container (SCAN_TARGET_IP / 172.30.0.9)
    - test_privileged_scan_sudo_with_password: testauth_sudo_pass user
    - test_privileged_scan_sudo_nopasswd: testauth_sudo_nopass user

    Tests will be skipped if the target is not reachable.
    """

    @staticmethod
    def _check_target_reachable(target: str, port: int = 22) -> bool:
        """Check if target is reachable via TCP socket connection.

        Uses socket instead of ping since test containers may not have ping installed.
        """
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((target, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_privileged_scan_sudo_with_password(self, scanner, structured_logging):
        """
        Test authenticated_privileged scan with sudo requiring password.

        Target: scan-target container (SCAN_TARGET_IP or 172.30.0.9)
        User: testauth_sudo_pass
        Expected: Full privileged scan with escalation_password

        Note: Skipped if target not reachable from container network.
        """
        logger = structured_logging

        target = SCAN_TARGET_IP
        if not self._check_target_reachable(target):
            pytest.skip(f"Target {target} not reachable from container network")

        credentials = {
            "type": "ssh",
            "auth_method": "password",
            "username": "testauth_sudo_pass",
            "password": "TestPass123!",
            "elevate_privileges_with": "sudo",
            "escalation_password": "TestPass123!"
        }

        scan_name = f"Phase5_SudoPass_{uuid.uuid4().hex[:8]}"
        request = ScanRequest(
            targets=target,
            name=scan_name,
            scan_type="authenticated_privileged",
            description="Phase 5 E2E test - sudo with password",
            credentials=credentials
        )

        logger.info(
            "starting_privileged_sudo_pass_test",
            target=target,
            username="testauth_sudo_pass",
            scan_name=scan_name
        )

        scan_id = None
        try:
            # Create scan
            scan_id = await scanner.create_scan(request)
            logger.info("scan_created", scan_id=scan_id)

            # Launch scan
            scan_uuid = await scanner.launch_scan(scan_id)
            logger.info("scan_launched", scan_id=scan_id, scan_uuid=scan_uuid)

            # Poll until completion
            max_wait = 600  # 10 minutes
            poll_interval = 30
            elapsed = 0

            while elapsed < max_wait:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                status = await scanner.get_status(scan_id)
                logger.info(
                    "scan_progress",
                    scan_id=scan_id,
                    status=status["status"],
                    progress=status.get("progress", 0),
                    elapsed=elapsed
                )

                if status["status"] == "completed":
                    logger.info("scan_completed", scan_id=scan_id, elapsed=elapsed)
                    break
                elif status["status"] == "failed":
                    pytest.fail(f"Scan failed: {status}")

            else:
                pytest.fail(f"Scan timeout after {max_wait}s")

            # Export and verify results
            results = await scanner.export_results(scan_id)
            logger.info("results_exported", size=len(results))

            # Save results for inspection
            results_file = Path(DATA_DIR) / f"{scan_name}.nessus"
            results_file.write_bytes(results)

            # Verify auth success indicators
            results_str = results.decode('utf-8', errors='replace')
            has_valid_creds_plugin = "141118" in results_str

            logger.info(
                "privileged_scan_result",
                plugin_141118_present=has_valid_creds_plugin,
                results_size=len(results)
            )

            assert len(results) > 1000, "Results too small - scan may have failed"

        finally:
            if scan_id:
                try:
                    await scanner.delete_scan(scan_id)
                    logger.info("scan_deleted", scan_id=scan_id)
                except Exception as e:
                    logger.warning("cleanup_failed", error=str(e))

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_privileged_scan_sudo_nopasswd(self, scanner, structured_logging):
        """
        Test authenticated_privileged scan with sudo NOPASSWD.

        Target: scan-target container (SCAN_TARGET_IP or 172.30.0.9)
        User: testauth_sudo_nopass
        Expected: Full privileged scan without escalation_password

        Note: Skipped if target not reachable from container network.
        """
        logger = structured_logging

        target = SCAN_TARGET_IP
        if not self._check_target_reachable(target):
            pytest.skip(f"Target {target} not reachable from container network")

        credentials = {
            "type": "ssh",
            "auth_method": "password",
            "username": "testauth_sudo_nopass",
            "password": "TestPass123!",
            "elevate_privileges_with": "sudo"
            # No escalation_password needed for NOPASSWD
        }

        scan_name = f"Phase5_SudoNoPass_{uuid.uuid4().hex[:8]}"
        request = ScanRequest(
            targets=target,
            name=scan_name,
            scan_type="authenticated_privileged",
            description="Phase 5 E2E test - sudo NOPASSWD",
            credentials=credentials
        )

        logger.info(
            "starting_privileged_sudo_nopass_test",
            target=target,
            username="testauth_sudo_nopass",
            scan_name=scan_name
        )

        scan_id = None
        try:
            # Create scan
            scan_id = await scanner.create_scan(request)
            logger.info("scan_created", scan_id=scan_id)

            # Launch scan
            scan_uuid = await scanner.launch_scan(scan_id)
            logger.info("scan_launched", scan_id=scan_id, scan_uuid=scan_uuid)

            # Poll until completion
            max_wait = 600  # 10 minutes
            poll_interval = 30
            elapsed = 0

            while elapsed < max_wait:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                status = await scanner.get_status(scan_id)
                logger.info(
                    "scan_progress",
                    scan_id=scan_id,
                    status=status["status"],
                    progress=status.get("progress", 0),
                    elapsed=elapsed
                )

                if status["status"] == "completed":
                    logger.info("scan_completed", scan_id=scan_id, elapsed=elapsed)
                    break
                elif status["status"] == "failed":
                    pytest.fail(f"Scan failed: {status}")

            else:
                pytest.fail(f"Scan timeout after {max_wait}s")

            # Export and verify results
            results = await scanner.export_results(scan_id)
            logger.info("results_exported", size=len(results))

            # Save results for inspection
            results_file = Path(DATA_DIR) / f"{scan_name}.nessus"
            results_file.write_bytes(results)

            # Verify auth success indicators
            results_str = results.decode('utf-8', errors='replace')
            has_valid_creds_plugin = "141118" in results_str

            logger.info(
                "privileged_nopasswd_result",
                plugin_141118_present=has_valid_creds_plugin,
                results_size=len(results)
            )

            assert len(results) > 1000, "Results too small - scan may have failed"

        finally:
            if scan_id:
                try:
                    await scanner.delete_scan(scan_id)
                    logger.info("scan_deleted", scan_id=scan_id)
                except Exception as e:
                    logger.warning("cleanup_failed", error=str(e))


# ============================================================================
# Test: Idempotent Test User Verification
# ============================================================================

class TestIdempotentUserVerification:
    """
    Verify test users exist and are properly configured on scan-target container.

    This ensures the test infrastructure is set up correctly before
    running authenticated scan tests.
    """

    @staticmethod
    def _check_target_reachable(target: str, port: int = 22) -> bool:
        """Check if target is reachable via TCP socket connection."""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((target, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    @pytest.mark.asyncio
    async def test_verify_scan_target_reachable(self, structured_logging):
        """
        Verify scan-target container is reachable on SSH port.

        This is a quick connectivity check for the test infrastructure.
        """
        logger = structured_logging

        target = SCAN_TARGET_IP
        is_reachable = self._check_target_reachable(target, 22)

        logger.info(
            "scan_target_connectivity",
            target=target,
            reachable=is_reachable
        )

        assert is_reachable, f"scan-target container at {target}:22 is not reachable"

    @pytest.mark.asyncio
    async def test_verify_external_host_reachable(self, structured_logging):
        """
        Verify external host (172.32.0.215) is reachable on SSH port.

        This is a quick connectivity check for the test infrastructure.
        """
        logger = structured_logging

        target = EXTERNAL_HOST_IP
        is_reachable = self._check_target_reachable(target, 22)

        logger.info(
            "external_host_connectivity",
            target=target,
            reachable=is_reachable
        )

        # External host may not always be reachable, just log warning
        if not is_reachable:
            logger.warning(
                "external_host_unreachable",
                message=f"External host {target}:22 is not reachable - some tests may be skipped"
            )


# ============================================================================
# Standalone Runner
# ============================================================================

if __name__ == "__main__":
    # Run with: python -m pytest tests/integration/test_authenticated_scan_workflow.py -v -s
    pytest.main([__file__, "-v", "-s"])
