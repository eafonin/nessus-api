"""Unit tests for Admin CLI (DLQ handler)."""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Test helper imports
from tools.admin_cli import format_timestamp, truncate


class TestHelperFunctions:
    """Test CLI helper functions."""

    def test_format_timestamp_valid(self):
        """Test formatting valid ISO timestamp."""
        ts = "2024-01-15T10:30:45"
        result = format_timestamp(ts)
        assert "2024-01-15" in result
        assert "10:30:45" in result

    def test_format_timestamp_invalid(self):
        """Test formatting invalid timestamp."""
        result = format_timestamp("not a date")
        assert result == "not a date"

    def test_format_timestamp_none(self):
        """Test formatting None timestamp."""
        result = format_timestamp(None)
        assert result == "N/A"

    def test_truncate_short_string(self):
        """Test truncate with short string."""
        result = truncate("hello", 10)
        assert result == "hello"

    def test_truncate_long_string(self):
        """Test truncate with long string."""
        result = truncate("hello world this is a long string", 10)
        assert len(result) == 10
        assert result.endswith("...")

    def test_truncate_empty(self):
        """Test truncate with empty string."""
        result = truncate("", 10)
        assert result == ""


class TestQueueDLQMethods:
    """Test queue DLQ methods (integration tests with mock Redis)."""

    @pytest.fixture
    def mock_queue(self):
        """Create queue with mocked Redis client."""
        with patch("core.queue.redis.from_url") as mock_from_url:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_from_url.return_value = mock_client

            from core.queue import TaskQueue
            queue = TaskQueue(redis_url="redis://localhost:6379")
            queue.redis_client = mock_client
            return queue

    def test_get_dlq_task_found(self, mock_queue):
        """Test finding a task in DLQ."""
        task_data = {"task_id": "task123", "error": "test error"}
        mock_queue.redis_client.zrange.return_value = [json.dumps(task_data)]

        result = mock_queue.get_dlq_task("task123", pool="nessus")

        assert result is not None
        assert result["task_id"] == "task123"
        assert result["error"] == "test error"

    def test_get_dlq_task_not_found(self, mock_queue):
        """Test task not in DLQ."""
        other_task = {"task_id": "other", "error": "error"}
        mock_queue.redis_client.zrange.return_value = [json.dumps(other_task)]

        result = mock_queue.get_dlq_task("task123", pool="nessus")

        assert result is None

    def test_get_dlq_task_empty_dlq(self, mock_queue):
        """Test empty DLQ."""
        mock_queue.redis_client.zrange.return_value = []

        result = mock_queue.get_dlq_task("task123", pool="nessus")

        assert result is None

    def test_retry_dlq_task_success(self, mock_queue):
        """Test successfully retrying a DLQ task."""
        task_data = {
            "task_id": "task123",
            "scan_type": "untrusted",
            "error": "old error",
            "failed_at": "2024-01-01T00:00:00"
        }
        mock_queue.redis_client.zrange.return_value = [
            (json.dumps(task_data), 1234567890.0)
        ]
        mock_queue.redis_client.zrem.return_value = 1
        mock_queue.redis_client.lpush.return_value = 1

        result = mock_queue.retry_dlq_task("task123", pool="nessus")

        assert result is True
        mock_queue.redis_client.zrem.assert_called_once()
        mock_queue.redis_client.lpush.assert_called_once()

    def test_retry_dlq_task_not_found(self, mock_queue):
        """Test retry when task not in DLQ."""
        mock_queue.redis_client.zrange.return_value = []

        result = mock_queue.retry_dlq_task("nonexistent", pool="nessus")

        assert result is False
        mock_queue.redis_client.lpush.assert_not_called()

    def test_clear_dlq_all(self, mock_queue):
        """Test clearing entire DLQ."""
        mock_queue.redis_client.delete.return_value = 5

        result = mock_queue.clear_dlq(pool="nessus")

        assert result == 5
        mock_queue.redis_client.delete.assert_called_once_with("nessus:queue:dead")

    def test_clear_dlq_before_timestamp(self, mock_queue):
        """Test clearing DLQ entries before timestamp."""
        mock_queue.redis_client.zremrangebyscore.return_value = 3

        result = mock_queue.clear_dlq(before_timestamp=1234567890.0, pool="nessus")

        assert result == 3
        mock_queue.redis_client.zremrangebyscore.assert_called_once()


class TestCLICommands:
    """Test CLI command handlers."""

    @pytest.fixture
    def mock_queue(self):
        """Create mock queue object."""
        queue = Mock()
        queue.default_pool = "nessus"
        return queue

    def test_cmd_stats(self, mock_queue):
        """Test stats command."""
        from tools.admin_cli import cmd_stats

        mock_args = Mock()
        mock_args.pool = "nessus"
        mock_args.all_pools = False

        with patch("tools.admin_cli.get_queue_stats") as mock_get_stats:
            mock_get_stats.return_value = {
                "pool": "nessus",
                "queue_depth": 5,
                "dlq_size": 2,
                "next_tasks": [],
                "timestamp": "2024-01-15T10:00:00"
            }

            result = cmd_stats(mock_queue, mock_args)

        assert result == 0
        mock_get_stats.assert_called_once()

    def test_cmd_list_dlq_empty(self, mock_queue):
        """Test list-dlq with empty DLQ."""
        from tools.admin_cli import cmd_list_dlq

        mock_queue.get_dlq_tasks.return_value = []

        mock_args = Mock()
        mock_args.pool = "nessus"
        mock_args.limit = 20

        result = cmd_list_dlq(mock_queue, mock_args)

        assert result == 0
        mock_queue.get_dlq_tasks.assert_called_once()

    def test_cmd_list_dlq_with_tasks(self, mock_queue):
        """Test list-dlq with tasks."""
        from tools.admin_cli import cmd_list_dlq

        mock_queue.get_dlq_tasks.return_value = [
            {"task_id": "t1", "scan_type": "untrusted", "error": "err1", "failed_at": "2024-01-01"},
            {"task_id": "t2", "scan_type": "trusted", "error": "err2", "failed_at": "2024-01-02"},
        ]

        mock_args = Mock()
        mock_args.pool = "nessus"
        mock_args.limit = 20

        result = cmd_list_dlq(mock_queue, mock_args)

        assert result == 0

    def test_cmd_inspect_dlq_found(self, mock_queue):
        """Test inspect-dlq when task found."""
        from tools.admin_cli import cmd_inspect_dlq

        mock_queue.get_dlq_task.return_value = {
            "task_id": "task123",
            "scan_type": "untrusted",
            "error": "connection failed"
        }

        mock_args = Mock()
        mock_args.pool = "nessus"
        mock_args.task_id = "task123"

        result = cmd_inspect_dlq(mock_queue, mock_args)

        assert result == 0
        mock_queue.get_dlq_task.assert_called_once_with("task123", pool="nessus")

    def test_cmd_inspect_dlq_not_found(self, mock_queue):
        """Test inspect-dlq when task not found."""
        from tools.admin_cli import cmd_inspect_dlq

        mock_queue.get_dlq_task.return_value = None

        mock_args = Mock()
        mock_args.pool = "nessus"
        mock_args.task_id = "nonexistent"

        result = cmd_inspect_dlq(mock_queue, mock_args)

        assert result == 1

    def test_cmd_retry_dlq_success(self, mock_queue):
        """Test retry-dlq success."""
        from tools.admin_cli import cmd_retry_dlq

        mock_queue.retry_dlq_task.return_value = True

        mock_args = Mock()
        mock_args.pool = "nessus"
        mock_args.task_id = "task123"
        mock_args.yes = True

        result = cmd_retry_dlq(mock_queue, mock_args)

        assert result == 0
        mock_queue.retry_dlq_task.assert_called_once()

    def test_cmd_retry_dlq_not_found(self, mock_queue):
        """Test retry-dlq when task not found."""
        from tools.admin_cli import cmd_retry_dlq

        mock_queue.retry_dlq_task.return_value = False

        mock_args = Mock()
        mock_args.pool = "nessus"
        mock_args.task_id = "nonexistent"
        mock_args.yes = True

        result = cmd_retry_dlq(mock_queue, mock_args)

        assert result == 1

    def test_cmd_purge_dlq_without_confirm(self, mock_queue):
        """Test purge-dlq without --confirm flag."""
        from tools.admin_cli import cmd_purge_dlq

        mock_args = Mock()
        mock_args.pool = "nessus"
        mock_args.confirm = False

        result = cmd_purge_dlq(mock_queue, mock_args)

        assert result == 1
        mock_queue.clear_dlq.assert_not_called()
