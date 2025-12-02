"""
Layer 02 Internal Test Fixtures.

These fixtures support isolated unit tests with mocked dependencies.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock


# =============================================================================
# Directory Fixtures
# =============================================================================

@pytest.fixture
def temp_data_dir():
    """Create temporary data directory for task storage."""
    tmpdir = tempfile.mkdtemp(prefix="test_tasks_")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory."""
    tmpdir = tempfile.mkdtemp(prefix="test_config_")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client for queue tests."""
    mock = MagicMock()
    mock.lpush = MagicMock(return_value=1)
    mock.rpop = MagicMock(return_value=None)
    mock.llen = MagicMock(return_value=0)
    mock.get = MagicMock(return_value=None)
    mock.set = MagicMock(return_value=True)
    mock.delete = MagicMock(return_value=1)
    mock.pipeline = MagicMock(return_value=mock)
    mock.execute = MagicMock(return_value=[])
    return mock


@pytest.fixture
def mock_scanner():
    """Mock NessusScanner for isolated tests."""
    mock = MagicMock()
    mock.create_scan = AsyncMock(return_value=123)
    mock.launch_scan = AsyncMock(return_value="scan-uuid-123")
    mock.get_status = AsyncMock(return_value={"status": "running", "progress": 50})
    mock.export_results = AsyncMock(return_value=b"<xml>results</xml>")
    mock.delete_scan = AsyncMock(return_value=True)
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_task_manager():
    """Mock TaskManager for tests not focusing on task storage."""
    mock = MagicMock()
    mock.create_task = MagicMock()
    mock.get_task = MagicMock(return_value=None)
    mock.update_status = MagicMock()
    mock.list_tasks = MagicMock(return_value=[])
    return mock


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_task_data():
    """Sample task data for tests."""
    return {
        "task_id": "test-task-001",
        "trace_id": "trace-001",
        "scan_type": "untrusted",
        "scanner_type": "nessus",
        "scanner_instance_id": "scanner1",
        "scanner_pool": "nessus",
        "status": "queued",
        "payload": {
            "targets": "192.168.1.1",
            "name": "Test Scan"
        },
        "created_at": "2025-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_vulnerability():
    """Sample vulnerability data for schema tests."""
    return {
        "type": "vulnerability",
        "host": "192.168.1.1",
        "plugin_id": "12345",
        "plugin_name": "Test Vulnerability",
        "severity": "4",
        "cvss_score": 9.0,
        "cve": ["CVE-2021-1234"],
        "exploit_available": True,
        "description": "A test vulnerability"
    }


@pytest.fixture
def sample_nessus_xml():
    """Sample Nessus XML for parser tests."""
    return b"""<?xml version="1.0"?>
    <NessusClientData_v2>
        <Report name="Test Scan">
            <ReportHost name="192.168.1.1">
                <ReportItem pluginID="12345" pluginName="Test Vuln" severity="4" port="80" protocol="tcp">
                    <cvss_score>9.0</cvss_score>
                    <cve>CVE-2021-1234</cve>
                    <exploit_available>true</exploit_available>
                    <description>Test vulnerability description</description>
                </ReportItem>
            </ReportHost>
        </Report>
    </NessusClientData_v2>
    """
