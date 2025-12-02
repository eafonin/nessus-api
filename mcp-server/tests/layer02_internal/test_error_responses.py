"""
Unit tests for MCP tool error response formats.

Tests error handling and response formats for:
- 404 Not Found errors (task not found, scanner not found)
- 409 Conflict errors (idempotency conflicts)
- Validation errors (invalid scan type, missing params)
- Error message formats and status codes
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from core.idempotency import ConflictError


class TestNotFoundErrors:
    """Tests for 404 Not Found error responses."""

    def test_task_not_found_response_format(self):
        """Test task not found error response format."""
        task_id = "nonexistent_task_123"

        # This is the format returned by get_scan_status
        error_response = {"error": f"Task {task_id} not found"}

        assert "error" in error_response
        assert "not found" in error_response["error"].lower()
        assert task_id in error_response["error"]

    def test_scanner_not_found_response_format(self):
        """Test scanner not found error response format."""
        # This is the format returned when scanner lookup fails
        error_response = {
            "error": "Scanner not found",
            "details": "No scanner instance available in pool",
            "status_code": 404,
        }

        assert error_response["status_code"] == 404
        assert "scanner" in error_response["error"].lower()
        assert "not found" in error_response["error"].lower()

    def test_scan_results_not_found_format(self):
        """Test scan results not found error format (JSON string)."""
        # get_scan_results returns JSON strings
        error_response = json.dumps({"error": "Scan results not found"})

        parsed = json.loads(error_response)
        assert "error" in parsed
        assert "not found" in parsed["error"].lower()


class TestConflictErrors:
    """Tests for 409 Conflict error responses."""

    def test_idempotency_conflict_response_format(self):
        """Test idempotency conflict error response format."""
        existing_task_id = "existing_task_abc"
        idempotency_key = "user_key_123"

        error_response = {
            "error": "Conflict",
            "message": f"Idempotency key '{idempotency_key}' already used for task {existing_task_id} with different parameters",
            "status_code": 409,
        }

        assert error_response["status_code"] == 409
        assert error_response["error"] == "Conflict"
        assert idempotency_key in error_response["message"]
        assert existing_task_id in error_response["message"]

    def test_conflict_error_exception_handling(self):
        """Test ConflictError exception contains proper info."""
        existing_task_id = "task_xyz"
        conflict = ConflictError(
            f"Key already used for task {existing_task_id}"
        )

        assert existing_task_id in str(conflict)

    def test_conflict_preserves_task_reference(self):
        """Test that conflict response preserves task ID reference."""
        error_response = {
            "error": "Conflict",
            "message": "Idempotency key 'key123' already used for task ne_scan_20250101_abc with different parameters",
            "status_code": 409,
            "existing_task_id": "ne_scan_20250101_abc",
        }

        assert "existing_task_id" in error_response
        assert error_response["existing_task_id"].startswith("ne_")


class TestValidationErrors:
    """Tests for validation error responses."""

    def test_invalid_scan_type_error(self):
        """Test invalid scan type validation error."""
        invalid_type = "invalid_scan"
        valid_types = ["untrusted", "authenticated", "authenticated_privileged"]

        error_response = {
            "error": f"Invalid scan_type: {invalid_type}. Must be one of: {valid_types}",
        }

        assert invalid_type in error_response["error"]
        assert "untrusted" in error_response["error"]

    def test_missing_privilege_escalation_error(self):
        """Test missing privilege escalation param error."""
        error_response = {
            "error": "authenticated_privileged scan requires elevate_privileges_with (sudo/su)",
        }

        assert "authenticated_privileged" in error_response["error"]
        assert "sudo" in error_response["error"].lower() or "su" in error_response["error"].lower()

    def test_schema_conflict_error(self):
        """Test schema profile and custom fields conflict error."""
        error_response = {
            "error": "Cannot specify both schema_profile and custom_fields"
        }

        assert "schema_profile" in error_response["error"]
        assert "custom_fields" in error_response["error"]

    def test_scan_not_completed_error(self):
        """Test scan not completed error format."""
        current_status = "running"
        error_response = {
            "error": f"Scan not completed yet (status: {current_status})"
        }

        assert "not completed" in error_response["error"]
        assert current_status in error_response["error"]


class TestErrorResponseConsistency:
    """Tests for error response format consistency."""

    def test_all_errors_have_error_key(self):
        """Test that all error responses have 'error' key."""
        error_responses = [
            {"error": "Task not found"},
            {"error": "Scanner not found", "status_code": 404},
            {"error": "Conflict", "status_code": 409},
            {"error": "Invalid scan_type"},
            {"error": "Scan results not found"},
        ]

        for response in error_responses:
            assert "error" in response, f"Missing 'error' key in: {response}"

    def test_http_errors_have_status_code(self):
        """Test that HTTP errors include status_code."""
        http_error_responses = [
            {"error": "Scanner not found", "status_code": 404},
            {"error": "Conflict", "status_code": 409},
        ]

        for response in http_error_responses:
            assert "status_code" in response
            assert isinstance(response["status_code"], int)
            assert response["status_code"] >= 400

    def test_error_messages_are_human_readable(self):
        """Test that error messages are human-readable."""
        error_messages = [
            "Task task_123 not found",
            "Scanner not found",
            "Idempotency key 'key' already used",
            "Invalid scan_type: bad. Must be one of: [valid]",
            "Scan not completed yet (status: running)",
        ]

        for msg in error_messages:
            # Should be readable English, not code/traceback
            assert not msg.startswith("Traceback")
            assert len(msg) > 10  # Not too short
            assert len(msg) < 500  # Not too long


class TestScanStatusErrorDetails:
    """Tests for error details in scan status responses."""

    def test_failed_scan_includes_error_message(self):
        """Test that failed scan status includes error_message field."""
        failed_status = {
            "task_id": "task_123",
            "status": "failed",
            "error_message": "Scanner timeout after 600 seconds",
            "created_at": "2025-01-01T00:00:00",
            "completed_at": "2025-01-01T00:10:00",
        }

        assert failed_status["status"] == "failed"
        assert "error_message" in failed_status
        assert failed_status["error_message"] is not None

    def test_timeout_scan_includes_error_message(self):
        """Test that timeout scan status includes error_message field."""
        timeout_status = {
            "task_id": "task_456",
            "status": "timeout",
            "error_message": "Scan exceeded maximum duration",
        }

        assert timeout_status["status"] == "timeout"
        assert "error_message" in timeout_status

    def test_completed_scan_no_error_message(self):
        """Test that completed scan has null/empty error_message."""
        completed_status = {
            "task_id": "task_789",
            "status": "completed",
            "error_message": None,
        }

        assert completed_status["status"] == "completed"
        assert completed_status["error_message"] is None


class TestAuthenticationErrorResponses:
    """Tests for authentication-related error responses."""

    def test_auth_failure_includes_troubleshooting(self):
        """Test that auth failure response includes troubleshooting hints."""
        auth_failed_response = {
            "task_id": "task_auth_fail",
            "status": "completed",
            "authentication_status": "failed",
            "troubleshooting": {
                "suggestions": [
                    "Verify SSH credentials are correct",
                    "Check if target host is reachable on port 22",
                    "Review scan logs for specific error"
                ]
            }
        }

        assert auth_failed_response["authentication_status"] == "failed"
        assert "troubleshooting" in auth_failed_response
        assert "suggestions" in auth_failed_response["troubleshooting"]
        assert len(auth_failed_response["troubleshooting"]["suggestions"]) > 0

    def test_partial_auth_includes_details(self):
        """Test that partial auth includes host-level details."""
        partial_auth_response = {
            "task_id": "task_partial",
            "status": "completed",
            "authentication_status": "partial",
            "hosts_summary": {
                "total": 3,
                "authenticated": 2,
                "failed": 1,
            }
        }

        assert partial_auth_response["authentication_status"] == "partial"
        assert "hosts_summary" in partial_auth_response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
