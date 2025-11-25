"""Unit tests for TaskManager with validation metadata support."""
import pytest
import tempfile
import shutil
from pathlib import Path

from core.types import Task, ScanState, StateTransitionError
from core.task_manager import TaskManager, generate_task_id


class TestTaskManagerBasic:
    """Basic TaskManager operations."""

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
    def sample_task(self):
        """Sample task without validation fields."""
        return Task(
            task_id="test123",
            trace_id="trace123",
            scan_type="untrusted",
            scanner_type="nessus",
            scanner_instance_id="scanner1",
            status="queued",
            payload={"targets": "192.168.1.1"},
            created_at="2025-01-01T00:00:00",
        )

    def test_create_and_get_task(self, task_manager, sample_task):
        """Test creating and retrieving a task."""
        task_manager.create_task(sample_task)
        loaded = task_manager.get_task("test123")

        assert loaded is not None
        assert loaded.task_id == "test123"
        assert loaded.scan_type == "untrusted"
        assert loaded.status == "queued"

    def test_get_nonexistent_task(self, task_manager):
        """Test retrieving non-existent task returns None."""
        result = task_manager.get_task("nonexistent")
        assert result is None

    def test_update_status_valid_transition(self, task_manager, sample_task):
        """Test valid state transition."""
        task_manager.create_task(sample_task)
        task_manager.update_status("test123", ScanState.RUNNING)

        loaded = task_manager.get_task("test123")
        assert loaded.status == "running"
        assert loaded.started_at is not None

    def test_update_status_invalid_transition(self, task_manager, sample_task):
        """Test invalid state transition raises error."""
        task_manager.create_task(sample_task)

        # QUEUED -> COMPLETED is invalid
        with pytest.raises(StateTransitionError):
            task_manager.update_status("test123", ScanState.COMPLETED)


class TestTaskManagerValidationMetadata:
    """Tests for validation metadata support (Phase 4)."""

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
    def running_task(self, task_manager):
        """Create a task in RUNNING state."""
        task = Task(
            task_id="val_test_001",
            trace_id="trace_val_001",
            scan_type="trusted_basic",
            scanner_type="nessus",
            scanner_instance_id="scanner1",
            scanner_pool="nessus",
            status="queued",
            payload={"targets": "192.168.1.1", "credentials": "ssh_creds"},
            created_at="2025-01-01T00:00:00",
        )
        task_manager.create_task(task)
        task_manager.update_status("val_test_001", ScanState.RUNNING)
        return task

    def test_task_with_validation_fields(self, task_manager):
        """Test creating task with validation fields."""
        task = Task(
            task_id="val_full_001",
            trace_id="trace_val_full",
            scan_type="untrusted",
            scanner_type="nessus",
            scanner_instance_id="scanner1",
            status="completed",
            payload={"targets": "192.168.1.1"},
            created_at="2025-01-01T00:00:00",
            validation_stats={"hosts_scanned": 1, "vuln_count": 5},
            validation_warnings=["Low host count"],
            authentication_status="not_applicable",
        )
        task_manager.create_task(task)

        loaded = task_manager.get_task("val_full_001")
        assert loaded.validation_stats == {"hosts_scanned": 1, "vuln_count": 5}
        assert loaded.validation_warnings == ["Low host count"]
        assert loaded.authentication_status == "not_applicable"

    def test_mark_completed_with_validation_success(self, task_manager, running_task):
        """Test marking task completed with validation data."""
        validation_stats = {
            "hosts_scanned": 5,
            "total_vulnerabilities": 23,
            "severity_counts": {"critical": 2, "high": 5, "medium": 10, "low": 6},
            "auth_plugins_found": 15,
            "file_size_bytes": 125000,
        }

        task_manager.mark_completed_with_validation(
            task_id="val_test_001",
            validation_stats=validation_stats,
            validation_warnings=["Scan completed quickly, verify scope"],
            authentication_status="success",
        )

        loaded = task_manager.get_task("val_test_001")
        assert loaded.status == "completed"
        assert loaded.completed_at is not None
        assert loaded.validation_stats == validation_stats
        assert loaded.validation_warnings == ["Scan completed quickly, verify scope"]
        assert loaded.authentication_status == "success"

    def test_mark_completed_with_partial_auth(self, task_manager, running_task):
        """Test marking completed with partial authentication."""
        task_manager.mark_completed_with_validation(
            task_id="val_test_001",
            validation_stats={"hosts_scanned": 10, "auth_plugins_found": 3},
            validation_warnings=[
                "Partial authentication: 3 of 10 hosts authenticated",
                "Windows hosts may have incomplete results",
            ],
            authentication_status="partial",
        )

        loaded = task_manager.get_task("val_test_001")
        assert loaded.authentication_status == "partial"
        assert len(loaded.validation_warnings) == 2

    def test_mark_failed_with_validation(self, task_manager, running_task):
        """Test marking task failed with validation context."""
        task_manager.mark_failed_with_validation(
            task_id="val_test_001",
            error_message="Authentication FAILED: Credentials rejected",
            validation_stats={"hosts_scanned": 1, "auth_plugins_found": 0},
            authentication_status="failed",
        )

        loaded = task_manager.get_task("val_test_001")
        assert loaded.status == "failed"
        assert loaded.completed_at is not None
        assert loaded.error_message == "Authentication FAILED: Credentials rejected"
        assert loaded.authentication_status == "failed"
        assert loaded.validation_stats["auth_plugins_found"] == 0

    def test_mark_completed_without_validation(self, task_manager, running_task):
        """Test marking completed without validation (backward compat)."""
        task_manager.mark_completed_with_validation(
            task_id="val_test_001",
            validation_stats=None,
            validation_warnings=None,
            authentication_status=None,
        )

        loaded = task_manager.get_task("val_test_001")
        assert loaded.status == "completed"
        assert loaded.validation_stats is None
        assert loaded.validation_warnings is None
        assert loaded.authentication_status is None

    def test_backward_compatibility_no_validation_fields(self, task_manager):
        """Test loading task without validation fields (backward compat)."""
        # Simulate old task without validation fields
        task = Task(
            task_id="old_task",
            trace_id="old_trace",
            scan_type="untrusted",
            scanner_type="nessus",
            scanner_instance_id="scanner1",
            status="completed",
            payload={"targets": "192.168.1.1"},
            created_at="2025-01-01T00:00:00",
        )
        task_manager.create_task(task)

        loaded = task_manager.get_task("old_task")
        # Should load with None for validation fields
        assert loaded.validation_stats is None
        assert loaded.validation_warnings is None
        assert loaded.authentication_status is None


class TestTaskManagerUntrustedScans:
    """Tests for untrusted scan validation metadata."""

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

    def test_untrusted_scan_not_applicable_auth(self, task_manager):
        """Test untrusted scan with not_applicable auth status."""
        task = Task(
            task_id="untrusted_001",
            trace_id="trace_untrusted",
            scan_type="untrusted",
            scanner_type="nessus",
            scanner_instance_id="scanner1",
            status="queued",
            payload={"targets": "192.168.1.0/24"},
            created_at="2025-01-01T00:00:00",
        )
        task_manager.create_task(task)
        task_manager.update_status("untrusted_001", ScanState.RUNNING)

        task_manager.mark_completed_with_validation(
            task_id="untrusted_001",
            validation_stats={
                "hosts_scanned": 50,
                "total_vulnerabilities": 120,
                "severity_counts": {"critical": 5, "high": 15, "medium": 50, "low": 50},
            },
            validation_warnings=[],
            authentication_status="not_applicable",
        )

        loaded = task_manager.get_task("untrusted_001")
        assert loaded.authentication_status == "not_applicable"
        assert loaded.validation_stats["hosts_scanned"] == 50


class TestTaskManagerTrustedScans:
    """Tests for trusted scan validation metadata."""

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

    def test_trusted_scan_success_auth(self, task_manager):
        """Test trusted scan with successful authentication."""
        task = Task(
            task_id="trusted_001",
            trace_id="trace_trusted",
            scan_type="trusted_privileged",
            scanner_type="nessus",
            scanner_instance_id="scanner1",
            status="queued",
            payload={"targets": "192.168.1.100", "credentials": "root_creds"},
            created_at="2025-01-01T00:00:00",
        )
        task_manager.create_task(task)
        task_manager.update_status("trusted_001", ScanState.RUNNING)

        task_manager.mark_completed_with_validation(
            task_id="trusted_001",
            validation_stats={
                "hosts_scanned": 1,
                "total_vulnerabilities": 45,
                "auth_plugins_found": 25,
                "credentialed_status_raw": "yes",
            },
            validation_warnings=[],
            authentication_status="success",
        )

        loaded = task_manager.get_task("trusted_001")
        assert loaded.authentication_status == "success"
        assert loaded.validation_stats["auth_plugins_found"] == 25

    def test_trusted_scan_failed_auth(self, task_manager):
        """Test trusted scan with failed authentication."""
        task = Task(
            task_id="trusted_fail_001",
            trace_id="trace_trusted_fail",
            scan_type="trusted_basic",
            scanner_type="nessus",
            scanner_instance_id="scanner1",
            status="queued",
            payload={"targets": "192.168.1.100", "credentials": "bad_creds"},
            created_at="2025-01-01T00:00:00",
        )
        task_manager.create_task(task)
        task_manager.update_status("trusted_fail_001", ScanState.RUNNING)

        task_manager.mark_failed_with_validation(
            task_id="trusted_fail_001",
            error_message=(
                "Authentication FAILED for trusted_basic scan. "
                "Plugin 19506 reports: Credentialed checks = no."
            ),
            validation_stats={
                "hosts_scanned": 1,
                "total_vulnerabilities": 8,
                "auth_plugins_found": 0,
                "credentialed_status_raw": "no",
            },
            authentication_status="failed",
        )

        loaded = task_manager.get_task("trusted_fail_001")
        assert loaded.status == "failed"
        assert loaded.authentication_status == "failed"
        assert "Authentication FAILED" in loaded.error_message


class TestGenerateTaskId:
    """Tests for task ID generation."""

    def test_generate_task_id_format(self):
        """Test task ID format."""
        task_id = generate_task_id("nessus", "scanner1")

        parts = task_id.split("_")
        # Format: {type}_{instance}_{date}_{time}_{random}
        assert len(parts) == 5
        assert parts[0] == "ne"  # First 2 chars of scanner_type
        assert parts[1] == "scan"  # First 4 chars of instance_id
        # parts[2] is date (YYYYMMDD), parts[3] is time (HHMMSS), parts[4] is random hex
        assert len(parts[4]) == 8  # Random hex suffix

    def test_generate_task_id_unique(self):
        """Test task IDs are unique."""
        ids = {generate_task_id("nessus", "scanner1") for _ in range(100)}
        assert len(ids) == 100

    def test_generate_task_id_different_scanner_types(self):
        """Test task IDs differ for different scanner types."""
        id1 = generate_task_id("nessus", "scanner1")
        id2 = generate_task_id("qualys", "scanner1")

        # Type prefix should differ
        assert id1.split("_")[0] != id2.split("_")[0]
        assert id1.split("_")[0] == "ne"
        assert id2.split("_")[0] == "qu"
