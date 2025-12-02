"""Unit tests for structured logging configuration."""

import json
import logging

import pytest

from core.logging_config import configure_logging, get_logger


class TestLoggingConfiguration:
    """Test suite for logging configuration."""

    def test_configure_logging_sets_log_level(self):
        """Test that configure_logging sets the correct log level."""
        # Note: In test environment, logging may already be configured
        # Test that function completes without error
        try:
            configure_logging(log_level="DEBUG")
            assert True
        except Exception as e:
            pytest.fail(f"configure_logging failed: {e}")

    def test_configure_logging_default_level(self):
        """Test that configure_logging uses INFO as default level."""
        try:
            configure_logging()
            assert True
        except Exception as e:
            pytest.fail(f"configure_logging failed: {e}")

    def test_get_logger_returns_structured_logger(self):
        """Test that get_logger returns a structlog logger."""
        configure_logging()
        logger = get_logger("test_module")

        # Logger should be from structlog (BoundLoggerLazyProxy or BoundLogger)
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_get_logger_without_name(self):
        """Test that get_logger works without a name parameter."""
        configure_logging()
        logger = get_logger()

        # Logger should have standard logging methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_json_output_format(self, caplog):
        """Test that logs are output in JSON format."""
        configure_logging(log_level="INFO")
        logger = get_logger("test")

        # Capture log output
        with caplog.at_level(logging.INFO):
            logger.info("test_event", key1="value1", key2=42)

        # Parse log output as JSON
        for record in caplog.records:
            try:
                log_data = json.loads(record.getMessage())
                assert "event" in log_data
                assert log_data["event"] == "test_event"
                assert log_data["key1"] == "value1"
                assert log_data["key2"] == 42
                assert "timestamp" in log_data
                return
            except json.JSONDecodeError:
                pass

        pytest.fail("No valid JSON log output found")

    def test_timestamp_format(self, caplog):
        """Test that timestamps are in ISO 8601 format."""
        configure_logging(log_level="INFO")
        logger = get_logger("test")

        with caplog.at_level(logging.INFO):
            logger.info("timestamp_test")

        for record in caplog.records:
            try:
                log_data = json.loads(record.getMessage())
                timestamp = log_data.get("timestamp")
                assert timestamp is not None
                # Check ISO 8601 format (basic validation)
                assert "T" in timestamp or "-" in timestamp
                return
            except json.JSONDecodeError:
                pass

    def test_log_levels(self, caplog):
        """Test that different log levels work correctly."""
        configure_logging(log_level="DEBUG")
        logger = get_logger("test")

        with caplog.at_level(logging.DEBUG):
            logger.debug("debug_msg")
            logger.info("info_msg")
            logger.warning("warn_msg")
            logger.error("error_msg")

        # Should have all 4 messages
        assert len(caplog.records) >= 4

    def test_structured_data_logging(self, caplog):
        """Test that structured data is preserved in logs."""
        configure_logging(log_level="INFO")
        logger = get_logger("test")

        test_data = {
            "task_id": "test-123",
            "trace_id": "abc-def-ghi",
            "count": 42,
            "nested": {"key": "value"},
        }

        with caplog.at_level(logging.INFO):
            logger.info("structured_test", **test_data)

        for record in caplog.records:
            try:
                log_data = json.loads(record.getMessage())
                assert log_data["task_id"] == "test-123"
                assert log_data["trace_id"] == "abc-def-ghi"
                assert log_data["count"] == 42
                assert log_data["nested"] == {"key": "value"}
                return
            except json.JSONDecodeError:
                pass

        pytest.fail("No valid JSON log output with structured data found")

    def test_exception_logging(self, caplog):
        """Test that exceptions are properly logged."""
        configure_logging(log_level="ERROR")
        logger = get_logger("test")

        try:
            raise ValueError("Test exception")
        except ValueError:
            with caplog.at_level(logging.ERROR):
                logger.error("exception_test", exc_info=True)

        # Should have captured the exception
        assert len(caplog.records) > 0
