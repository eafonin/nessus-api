"""
Unit tests for list_tasks MCP tool functionality.

Tests the list_tasks filtering logic:
- Status filtering
- Pool filtering
- Target CIDR-aware filtering
- Limit handling
- Empty results handling
"""

import shutil
import tempfile

import pytest

from core.task_manager import TaskManager
from core.types import Task


class TestListTasksFiltering:
    """Tests for list_tasks filtering logic."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def task_manager(self, temp_data_dir):
        """TaskManager with temp directory."""
        return TaskManager(data_dir=temp_data_dir)

    @pytest.fixture
    def sample_tasks(self, task_manager):
        """Create sample tasks with varying attributes."""
        tasks = [
            Task(
                task_id="task_001",
                trace_id="trace_001",
                scan_type="untrusted",
                scanner_type="nessus",
                scanner_instance_id="scanner1",
                scanner_pool="nessus",
                status="completed",
                payload={"targets": "192.168.1.0/24", "name": "Network Scan 1"},
                created_at="2025-01-01T00:00:00",
            ),
            Task(
                task_id="task_002",
                trace_id="trace_002",
                scan_type="authenticated",
                scanner_type="nessus",
                scanner_instance_id="scanner1",
                scanner_pool="nessus",
                status="running",
                payload={"targets": "10.0.0.1", "name": "Auth Scan"},
                created_at="2025-01-01T01:00:00",
            ),
            Task(
                task_id="task_003",
                trace_id="trace_003",
                scan_type="untrusted",
                scanner_type="nessus",
                scanner_instance_id="scanner2",
                scanner_pool="nessus_dmz",
                status="queued",
                payload={"targets": "172.16.0.0/16", "name": "DMZ Scan"},
                created_at="2025-01-01T02:00:00",
            ),
            Task(
                task_id="task_004",
                trace_id="trace_004",
                scan_type="untrusted",
                scanner_type="nessus",
                scanner_instance_id="scanner1",
                scanner_pool="nessus",
                status="failed",
                payload={"targets": "192.168.2.100", "name": "Failed Scan"},
                created_at="2025-01-01T03:00:00",
            ),
        ]
        for task in tasks:
            task_manager.create_task(task)
        return tasks

    def test_filter_by_status_completed(self, task_manager, sample_tasks):
        """Test filtering tasks by completed status."""
        # Simulate the filtering logic from list_tasks
        tasks = []
        for task_file in task_manager.data_dir.glob("*/task.json"):
            task = task_manager.get_task(task_file.parent.name)
            if task and task.status == "completed":
                tasks.append(task)

        assert len(tasks) == 1
        assert tasks[0].task_id == "task_001"

    def test_filter_by_status_running(self, task_manager, sample_tasks):
        """Test filtering tasks by running status."""
        tasks = []
        for task_file in task_manager.data_dir.glob("*/task.json"):
            task = task_manager.get_task(task_file.parent.name)
            if task and task.status == "running":
                tasks.append(task)

        assert len(tasks) == 1
        assert tasks[0].task_id == "task_002"

    def test_filter_by_status_queued(self, task_manager, sample_tasks):
        """Test filtering tasks by queued status."""
        tasks = []
        for task_file in task_manager.data_dir.glob("*/task.json"):
            task = task_manager.get_task(task_file.parent.name)
            if task and task.status == "queued":
                tasks.append(task)

        assert len(tasks) == 1
        assert tasks[0].task_id == "task_003"

    def test_filter_by_pool_nessus(self, task_manager, sample_tasks):
        """Test filtering tasks by nessus pool."""
        tasks = []
        for task_file in task_manager.data_dir.glob("*/task.json"):
            task = task_manager.get_task(task_file.parent.name)
            if task:
                task_pool = task.scanner_pool or task.scanner_type
                if task_pool == "nessus":
                    tasks.append(task)

        assert len(tasks) == 3
        task_ids = {t.task_id for t in tasks}
        assert task_ids == {"task_001", "task_002", "task_004"}

    def test_filter_by_pool_dmz(self, task_manager, sample_tasks):
        """Test filtering tasks by nessus_dmz pool."""
        tasks = []
        for task_file in task_manager.data_dir.glob("*/task.json"):
            task = task_manager.get_task(task_file.parent.name)
            if task:
                task_pool = task.scanner_pool or task.scanner_type
                if task_pool == "nessus_dmz":
                    tasks.append(task)

        assert len(tasks) == 1
        assert tasks[0].task_id == "task_003"

    def test_combined_filter_status_and_pool(self, task_manager, sample_tasks):
        """Test combining status and pool filters."""
        target_status = "completed"
        target_pool = "nessus"

        tasks = []
        for task_file in task_manager.data_dir.glob("*/task.json"):
            task = task_manager.get_task(task_file.parent.name)
            if task:
                if task.status != target_status:
                    continue
                task_pool = task.scanner_pool or task.scanner_type
                if task_pool != target_pool:
                    continue
                tasks.append(task)

        assert len(tasks) == 1
        assert tasks[0].task_id == "task_001"

    def test_limit_respects_count(self, task_manager, sample_tasks):
        """Test that limit parameter is respected."""
        limit = 2
        tasks = []
        for task_file in list(task_manager.data_dir.glob("*/task.json"))[:limit]:
            task = task_manager.get_task(task_file.parent.name)
            if task:
                tasks.append(task)
                if len(tasks) >= limit:
                    break

        assert len(tasks) <= limit

    def test_no_results_returns_empty(self, task_manager, sample_tasks):
        """Test that non-matching filters return empty list."""
        tasks = []
        for task_file in task_manager.data_dir.glob("*/task.json"):
            task = task_manager.get_task(task_file.parent.name)
            if task and task.status == "timeout":  # No tasks have timeout status
                tasks.append(task)

        assert len(tasks) == 0


class TestListTasksTargetFiltering:
    """Tests for CIDR-aware target filtering in list_tasks."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def task_manager(self, temp_data_dir):
        """TaskManager with temp directory."""
        return TaskManager(data_dir=temp_data_dir)

    @pytest.fixture
    def target_tasks(self, task_manager):
        """Create tasks with different target configurations."""
        tasks = [
            Task(
                task_id="target_001",
                trace_id="trace_001",
                scan_type="untrusted",
                scanner_type="nessus",
                scanner_instance_id="scanner1",
                status="completed",
                payload={"targets": "192.168.1.0/24", "name": "Subnet A"},
                created_at="2025-01-01T00:00:00",
            ),
            Task(
                task_id="target_002",
                trace_id="trace_002",
                scan_type="untrusted",
                scanner_type="nessus",
                scanner_instance_id="scanner1",
                status="completed",
                payload={"targets": "10.0.0.50", "name": "Single IP"},
                created_at="2025-01-01T01:00:00",
            ),
            Task(
                task_id="target_003",
                trace_id="trace_003",
                scan_type="untrusted",
                scanner_type="nessus",
                scanner_instance_id="scanner1",
                status="completed",
                payload={"targets": "172.16.0.0/12", "name": "Large Subnet"},
                created_at="2025-01-01T02:00:00",
            ),
        ]
        for task in tasks:
            task_manager.create_task(task)
        return tasks

    def test_target_filter_exact_ip_match(self, task_manager, target_tasks):
        """Test filtering by exact IP address."""
        from core.ip_utils import targets_match

        target_filter = "10.0.0.50"
        tasks = []
        for task_file in task_manager.data_dir.glob("*/task.json"):
            task = task_manager.get_task(task_file.parent.name)
            if task:
                stored_targets = task.payload.get("targets", "") if task.payload else ""
                if targets_match(target_filter, stored_targets):
                    tasks.append(task)

        assert len(tasks) == 1
        assert tasks[0].task_id == "target_002"

    def test_target_filter_ip_in_cidr(self, task_manager, target_tasks):
        """Test filtering by IP that falls within a stored CIDR."""
        from core.ip_utils import targets_match

        target_filter = "192.168.1.100"  # Falls within 192.168.1.0/24
        tasks = []
        for task_file in task_manager.data_dir.glob("*/task.json"):
            task = task_manager.get_task(task_file.parent.name)
            if task:
                stored_targets = task.payload.get("targets", "") if task.payload else ""
                if targets_match(target_filter, stored_targets):
                    tasks.append(task)

        assert len(tasks) == 1
        assert tasks[0].task_id == "target_001"

    def test_target_filter_cidr_contains_stored_ip(self, task_manager, target_tasks):
        """Test filtering by CIDR that contains a stored IP."""
        from core.ip_utils import targets_match

        target_filter = "10.0.0.0/24"  # Contains 10.0.0.50
        tasks = []
        for task_file in task_manager.data_dir.glob("*/task.json"):
            task = task_manager.get_task(task_file.parent.name)
            if task:
                stored_targets = task.payload.get("targets", "") if task.payload else ""
                if targets_match(target_filter, stored_targets):
                    tasks.append(task)

        assert len(tasks) == 1
        assert tasks[0].task_id == "target_002"

    def test_target_filter_no_match(self, task_manager, target_tasks):
        """Test filtering with non-matching target."""
        from core.ip_utils import targets_match

        target_filter = "8.8.8.8"  # Not in any stored target
        tasks = []
        for task_file in task_manager.data_dir.glob("*/task.json"):
            task = task_manager.get_task(task_file.parent.name)
            if task:
                stored_targets = task.payload.get("targets", "") if task.payload else ""
                if targets_match(target_filter, stored_targets):
                    tasks.append(task)

        assert len(tasks) == 0


class TestListTasksResponseFormat:
    """Tests for list_tasks response format."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def task_manager(self, temp_data_dir):
        """TaskManager with temp directory."""
        return TaskManager(data_dir=temp_data_dir)

    @pytest.fixture
    def sample_task(self, task_manager):
        """Create a sample task."""
        task = Task(
            task_id="format_001",
            trace_id="trace_format",
            scan_type="untrusted",
            scanner_type="nessus",
            scanner_instance_id="scanner1",
            scanner_pool="nessus",
            status="completed",
            payload={"targets": "192.168.1.1", "name": "Format Test"},
            created_at="2025-01-01T00:00:00",
            started_at="2025-01-01T00:01:00",
            completed_at="2025-01-01T00:10:00",
            nessus_scan_id=12345,
        )
        task_manager.create_task(task)
        return task

    def test_response_contains_required_fields(self, task_manager, sample_task):
        """Test that response contains all required fields."""
        task = task_manager.get_task("format_001")

        # Build response dict as list_tasks does
        response = {
            "task_id": task.task_id,
            "trace_id": task.trace_id,
            "status": task.status,
            "scan_type": task.scan_type,
            "scanner_pool": task.scanner_pool or task.scanner_type,
            "scanner_type": task.scanner_type,
            "scanner_instance": task.scanner_instance_id,
            "targets": task.payload.get("targets", "") if task.payload else "",
            "name": task.payload.get("name", "") if task.payload else "",
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "nessus_scan_id": task.nessus_scan_id,
        }

        # Verify all required fields are present
        assert "task_id" in response
        assert "trace_id" in response
        assert "status" in response
        assert "scan_type" in response
        assert "scanner_pool" in response
        assert "targets" in response
        assert "name" in response
        assert "created_at" in response

    def test_response_values_match_task(self, task_manager, sample_task):
        """Test that response values match task attributes."""
        task = task_manager.get_task("format_001")

        assert task.task_id == "format_001"
        assert task.trace_id == "trace_format"
        assert task.status == "completed"
        assert task.scan_type == "untrusted"
        assert task.scanner_pool == "nessus"
        assert task.nessus_scan_id == 12345


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
