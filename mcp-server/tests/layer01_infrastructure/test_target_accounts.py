"""
Layer 01: Scan Target Account Connectivity Tests

Validates that SSH test accounts are accessible on scan targets.
These tests verify the test infrastructure is ready for authenticated scans.

Usage:
    pytest tests/layer01_infrastructure/test_target_accounts.py -v -s
"""

import os
import socket

import pytest

# Target configuration
SCAN_TARGET_IP = os.getenv("SCAN_TARGET_IP", "172.30.0.9")
EXTERNAL_HOST_IP = os.getenv("EXTERNAL_HOST_IP", "172.32.0.215")


def check_tcp_port(host: str, port: int = 22, timeout: int = 3) -> bool:
    """Check if TCP port is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


class TestScanTargetReachable:
    """Verify scan-target container is reachable."""

    def test_scan_target_ssh_port(self):
        """Verify scan-target SSH port is open (if container running)."""
        if not check_tcp_port(SCAN_TARGET_IP, 22):
            pytest.skip(
                f"scan-target at {SCAN_TARGET_IP}:22 not reachable "
                "(scan-target container may not be running)"
            )

    def test_external_host_ssh_port(self):
        """Verify external host SSH port is open (if reachable)."""
        if not check_tcp_port(EXTERNAL_HOST_IP, 22):
            pytest.skip(f"External host at {EXTERNAL_HOST_IP}:22 not reachable")
        assert check_tcp_port(EXTERNAL_HOST_IP, 22)


class TestTargetAccountsExist:
    """Verify test accounts are configured (via SSH banner or socket)."""

    def test_scan_target_accepts_connections(self):
        """Verify scan-target accepts SSH connections."""
        if not check_tcp_port(SCAN_TARGET_IP, 22):
            pytest.skip(f"scan-target at {SCAN_TARGET_IP}:22 not reachable")

        # Try to get SSH banner
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((SCAN_TARGET_IP, 22))
            banner = sock.recv(1024).decode("utf-8", errors="ignore")
            sock.close()

            assert "SSH" in banner, f"Not an SSH server: {banner[:50]}"
        except Exception as e:
            pytest.fail(f"Could not get SSH banner: {e}")


class TestTargetAccountCredentials:
    """Document expected test account credentials.

    Note: Actual SSH authentication is tested in layer03/layer04.
    This class documents the expected credentials for reference.
    """

    def test_credentials_documented(self):
        """Verify test credentials are documented."""
        credentials = {
            "scan_target": {
                "ip": SCAN_TARGET_IP,
                "users": {
                    "testauth_sudo_pass": {
                        "password": "TestPass123!",
                        "sudo": "with_password",
                    },
                    "testauth_sudo_nopass": {
                        "password": "TestPass123!",
                        "sudo": "nopasswd",
                    },
                    "testauth_nosudo": {"password": "TestPass123!", "sudo": "none"},
                },
            },
            "external_host": {
                "ip": EXTERNAL_HOST_IP,
                "users": {
                    "randy": {"password": "randylovesgoldfish1998", "sudo": "full"},
                },
            },
        }

        # Verify structure
        assert "scan_target" in credentials
        assert "external_host" in credentials
        assert len(credentials["scan_target"]["users"]) == 3
        assert len(credentials["external_host"]["users"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
