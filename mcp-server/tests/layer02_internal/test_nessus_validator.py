"""Unit tests for NessusValidator with authentication detection."""

import shutil
import tempfile
from pathlib import Path

import pytest

from scanners.nessus_validator import (
    NessusValidator,
    ValidationResult,
    validate_scan_results,
)


class TestNessusValidatorBasic:
    """Basic NessusValidator operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def validator(self):
        """NessusValidator instance."""
        return NessusValidator()

    def test_file_not_found(self, validator, temp_dir):
        """Test validation of non-existent file."""
        result = validator.validate(temp_dir / "nonexistent.nessus")

        assert result.is_valid is False
        assert "not found" in result.error
        assert result.authentication_status == "unknown"

    def test_empty_file(self, validator, temp_dir):
        """Test validation of empty file."""
        empty_file = temp_dir / "empty.nessus"
        empty_file.write_text("")

        result = validator.validate(empty_file)

        assert result.is_valid is False
        assert "too small" in result.error
        assert result.stats["file_size_bytes"] == 0

    def test_invalid_xml(self, validator, temp_dir):
        """Test validation of invalid XML."""
        bad_xml = temp_dir / "bad.nessus"
        # Make file large enough to pass size check but still invalid XML
        bad_xml.write_text("This is not valid XML " * 10 + " <unclosed>")

        result = validator.validate(bad_xml)

        assert result.is_valid is False
        assert "Invalid XML" in result.error

    def test_no_hosts(self, validator, temp_dir):
        """Test validation of file with no hosts."""
        no_hosts_xml = temp_dir / "no_hosts.nessus"
        no_hosts_xml.write_text("""<?xml version="1.0"?>
<NessusClientData_v2>
    <Report name="Test">
    </Report>
</NessusClientData_v2>
""")

        result = validator.validate(no_hosts_xml)

        assert result.is_valid is False
        assert "No hosts" in result.error


class TestNessusValidatorUntrustedScans:
    """Tests for untrusted scan validation."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def validator(self):
        """NessusValidator instance."""
        return NessusValidator()

    @pytest.fixture
    def untrusted_scan_xml(self, temp_dir):
        """Sample untrusted scan results."""
        xml_file = temp_dir / "untrusted_scan.nessus"
        xml_file.write_text("""<?xml version="1.0"?>
<NessusClientData_v2>
    <Report name="Untrusted Scan">
        <ReportHost name="192.168.1.1">
            <HostProperties>
                <tag name="host-ip">192.168.1.1</tag>
            </HostProperties>
            <ReportItem port="22" severity="2" pluginID="10267" pluginName="SSH Server Detection">
                <plugin_output>SSH server detected</plugin_output>
            </ReportItem>
            <ReportItem port="80" severity="1" pluginID="10107" pluginName="HTTP Server Type">
                <plugin_output>Apache/2.4</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="0" pluginID="11936" pluginName="OS Identification">
                <plugin_output>Linux kernel</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="0" pluginID="19506" pluginName="Nessus Scan Information">
                <plugin_output>
Nessus version : 10.0.0
Plugin feed version : 202501010000
Type of scanner : Nessus Professional
Scanner edition : Professional
Scanner OS : Linux
Port scanners used : SYN scanner
Credentialed checks : no
</plugin_output>
            </ReportItem>
        </ReportHost>
    </Report>
</NessusClientData_v2>
""")
        return xml_file

    def test_untrusted_scan_success(self, validator, untrusted_scan_xml):
        """Test untrusted scan validation succeeds."""
        result = validator.validate(untrusted_scan_xml, scan_type="untrusted")

        assert result.is_valid is True
        assert result.authentication_status == "not_applicable"
        assert result.stats["hosts_scanned"] == 1
        assert result.stats["total_plugins"] == 4

    def test_untrusted_scan_severity_counts(self, validator, untrusted_scan_xml):
        """Test untrusted scan severity counting."""
        result = validator.validate(untrusted_scan_xml, scan_type="untrusted")

        severity = result.stats["severity_counts"]
        assert severity["critical"] == 0
        assert severity["high"] == 0
        assert severity["medium"] == 1  # SSH detection
        assert severity["low"] == 1  # HTTP server
        assert severity["info"] == 2  # OS identification, scan info


class TestNessusValidatorTrustedScans:
    """Tests for trusted scan validation with authentication detection."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def validator(self):
        """NessusValidator instance."""
        return NessusValidator()

    @pytest.fixture
    def trusted_scan_success_xml(self, temp_dir):
        """Sample trusted scan with successful authentication."""
        xml_file = temp_dir / "trusted_success.nessus"
        xml_file.write_text("""<?xml version="1.0"?>
<NessusClientData_v2>
    <Report name="Trusted Scan - Success">
        <ReportHost name="192.168.1.100">
            <HostProperties>
                <tag name="host-ip">192.168.1.100</tag>
            </HostProperties>
            <ReportItem port="0" severity="0" pluginID="19506" pluginName="Nessus Scan Information">
                <plugin_output>
Nessus version : 10.0.0
Scanner OS : Linux
Credentialed checks : yes
</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="4" pluginID="97833" pluginName="Windows Security Update Check">
                <plugin_output>Missing security update</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="3" pluginID="21643" pluginName="Windows Local Security Checks">
                <plugin_output>Local security issue found</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="2" pluginID="22869" pluginName="Installed Software Enumeration">
                <plugin_output>Software: Chrome 100.0</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="3" pluginID="12634" pluginName="Unix/Linux Local Security Checks">
                <plugin_output>Kernel vulnerability</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="2" pluginID="51192" pluginName="Debian Local Security Checks">
                <plugin_output>Package update available</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="3" pluginID="33851" pluginName="Red Hat Local Security Checks">
                <plugin_output>Red Hat update needed</plugin_output>
            </ReportItem>
        </ReportHost>
    </Report>
</NessusClientData_v2>
""")
        return xml_file

    @pytest.fixture
    def trusted_scan_failed_xml(self, temp_dir):
        """Sample trusted scan with failed authentication."""
        xml_file = temp_dir / "trusted_failed.nessus"
        xml_file.write_text("""<?xml version="1.0"?>
<NessusClientData_v2>
    <Report name="Trusted Scan - Auth Failed">
        <ReportHost name="192.168.1.100">
            <HostProperties>
                <tag name="host-ip">192.168.1.100</tag>
            </HostProperties>
            <ReportItem port="0" severity="0" pluginID="19506" pluginName="Nessus Scan Information">
                <plugin_output>
Nessus version : 10.0.0
Scanner OS : Linux
Credentialed checks : no
</plugin_output>
            </ReportItem>
            <ReportItem port="22" severity="2" pluginID="10267" pluginName="SSH Server Detection">
                <plugin_output>SSH server detected</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="1" pluginID="11936" pluginName="OS Identification">
                <plugin_output>Linux</plugin_output>
            </ReportItem>
        </ReportHost>
    </Report>
</NessusClientData_v2>
""")
        return xml_file

    @pytest.fixture
    def trusted_scan_partial_xml(self, temp_dir):
        """Sample trusted scan with partial authentication."""
        xml_file = temp_dir / "trusted_partial.nessus"
        xml_file.write_text("""<?xml version="1.0"?>
<NessusClientData_v2>
    <Report name="Trusted Scan - Partial Auth">
        <ReportHost name="192.168.1.100">
            <HostProperties>
                <tag name="host-ip">192.168.1.100</tag>
            </HostProperties>
            <ReportItem port="0" severity="0" pluginID="19506" pluginName="Nessus Scan Information">
                <plugin_output>
Nessus version : 10.0.0
Credentialed checks : partial
</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="3" pluginID="21643" pluginName="Windows Local Security Checks">
                <plugin_output>Auth succeeded for 1 of 2 hosts</plugin_output>
            </ReportItem>
        </ReportHost>
    </Report>
</NessusClientData_v2>
""")
        return xml_file

    def test_trusted_scan_auth_success(self, validator, trusted_scan_success_xml):
        """Test trusted scan with successful authentication."""
        result = validator.validate(trusted_scan_success_xml, scan_type="trusted_basic")

        assert result.is_valid is True
        assert result.authentication_status == "success"
        assert result.stats["credentialed_status_raw"] == "yes"
        assert result.stats["auth_plugins_found"] >= 5  # Has auth-only plugins

    def test_trusted_scan_auth_failed(self, validator, trusted_scan_failed_xml):
        """Test trusted scan with failed authentication."""
        result = validator.validate(trusted_scan_failed_xml, scan_type="trusted_basic")

        assert result.is_valid is False
        assert result.authentication_status == "failed"
        assert "Authentication FAILED" in result.error
        assert result.stats["credentialed_status_raw"] == "no"
        assert result.stats["auth_plugins_found"] == 0

    def test_trusted_scan_auth_partial(self, validator, trusted_scan_partial_xml):
        """Test trusted scan with partial authentication."""
        result = validator.validate(
            trusted_scan_partial_xml, scan_type="trusted_privileged"
        )

        assert result.is_valid is True  # Partial is still valid
        assert result.authentication_status == "partial"
        assert result.stats["credentialed_status_raw"] == "partial"
        assert "Partial authentication" in result.warnings[0]

    def test_trusted_privileged_scan_failed(self, validator, trusted_scan_failed_xml):
        """Test trusted_privileged scan also fails on auth failure."""
        result = validator.validate(
            trusted_scan_failed_xml, scan_type="trusted_privileged"
        )

        assert result.is_valid is False
        assert result.authentication_status == "failed"
        assert "trusted_privileged" in result.error

    def test_severity_counts_trusted(self, validator, trusted_scan_success_xml):
        """Test severity counts for trusted scan."""
        result = validator.validate(trusted_scan_success_xml, scan_type="trusted_basic")

        severity = result.stats["severity_counts"]
        assert severity["critical"] == 1  # Windows Security Update
        assert severity["high"] == 3  # Local checks
        assert severity["medium"] == 2  # Software enum, Debian
        assert severity["info"] == 1  # Scan info


class TestNessusValidatorHostCounts:
    """Tests for host count validation."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def validator(self):
        """NessusValidator instance."""
        return NessusValidator()

    @pytest.fixture
    def multi_host_xml(self, temp_dir):
        """Sample scan with multiple hosts."""
        xml_file = temp_dir / "multi_host.nessus"
        xml_file.write_text("""<?xml version="1.0"?>
<NessusClientData_v2>
    <Report name="Multi Host Scan">
        <ReportHost name="192.168.1.1">
            <ReportItem port="0" severity="0" pluginID="11936" pluginName="OS">
                <plugin_output>Host 1</plugin_output>
            </ReportItem>
        </ReportHost>
        <ReportHost name="192.168.1.2">
            <ReportItem port="0" severity="0" pluginID="11936" pluginName="OS">
                <plugin_output>Host 2</plugin_output>
            </ReportItem>
        </ReportHost>
        <ReportHost name="192.168.1.3">
            <ReportItem port="0" severity="0" pluginID="11936" pluginName="OS">
                <plugin_output>Host 3</plugin_output>
            </ReportItem>
        </ReportHost>
    </Report>
</NessusClientData_v2>
""")
        return xml_file

    def test_host_count(self, validator, multi_host_xml):
        """Test host counting."""
        result = validator.validate(multi_host_xml)

        assert result.is_valid is True
        assert result.stats["hosts_scanned"] == 3

    def test_expected_hosts_warning(self, validator, multi_host_xml):
        """Test warning when fewer hosts than expected."""
        result = validator.validate(multi_host_xml, expected_hosts=5)

        assert result.is_valid is True  # Still valid, just warning
        assert len(result.warnings) == 1
        assert "less than expected" in result.warnings[0]

    def test_expected_hosts_met(self, validator, multi_host_xml):
        """Test no warning when host count meets expectation."""
        result = validator.validate(multi_host_xml, expected_hosts=3)

        assert result.is_valid is True
        assert len(result.warnings) == 0


class TestNessusValidatorAuthInference:
    """Tests for authentication status inference from plugin counts."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def validator(self):
        """NessusValidator instance."""
        return NessusValidator()

    @pytest.fixture
    def auth_inferred_xml(self, temp_dir):
        """Scan with auth-only plugins but no plugin 19506 cred status."""
        xml_file = temp_dir / "auth_inferred.nessus"
        xml_file.write_text("""<?xml version="1.0"?>
<NessusClientData_v2>
    <Report name="Auth Inferred">
        <ReportHost name="192.168.1.100">
            <ReportItem port="0" severity="3" pluginID="21643" pluginName="Windows Local">
                <plugin_output>Local check 1</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="3" pluginID="97833" pluginName="Windows Update">
                <plugin_output>Local check 2</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="2" pluginID="22869" pluginName="Software Enum">
                <plugin_output>Local check 3</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="2" pluginID="12634" pluginName="Unix Local">
                <plugin_output>Local check 4</plugin_output>
            </ReportItem>
            <ReportItem port="0" severity="2" pluginID="51192" pluginName="Debian">
                <plugin_output>Local check 5</plugin_output>
            </ReportItem>
        </ReportHost>
    </Report>
</NessusClientData_v2>
""")
        return xml_file

    def test_auth_inferred_from_plugins(self, validator, auth_inferred_xml):
        """Test auth status inferred from plugin count when 19506 missing."""
        result = validator.validate(auth_inferred_xml, scan_type="trusted_basic")

        assert result.is_valid is True
        assert result.authentication_status == "success"
        assert result.stats["auth_plugins_found"] >= 5
        assert result.stats["credentialed_status_raw"] is None


class TestValidateScanResultsConvenience:
    """Tests for convenience function."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)

    def test_convenience_function(self, temp_dir):
        """Test validate_scan_results convenience function."""
        xml_file = temp_dir / "test.nessus"
        xml_file.write_text("""<?xml version="1.0"?>
<NessusClientData_v2>
    <Report name="Test">
        <ReportHost name="192.168.1.1">
            <ReportItem port="0" severity="0" pluginID="11936" pluginName="OS">
                <plugin_output>Test</plugin_output>
            </ReportItem>
        </ReportHost>
    </Report>
</NessusClientData_v2>
""")

        result = validate_scan_results(xml_file, scan_type="untrusted")

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.authentication_status == "not_applicable"


class TestValidationResultDataclass:
    """Tests for ValidationResult dataclass."""

    def test_default_values(self):
        """Test ValidationResult default values."""
        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.error is None
        assert result.warnings == []
        assert result.stats == {}
        assert result.authentication_status == "unknown"

    def test_with_values(self):
        """Test ValidationResult with values."""
        result = ValidationResult(
            is_valid=False,
            error="Test error",
            warnings=["warning1", "warning2"],
            stats={"hosts": 5},
            authentication_status="success",
        )

        assert result.is_valid is False
        assert result.error == "Test error"
        assert len(result.warnings) == 2
        assert result.stats["hosts"] == 5
        assert result.authentication_status == "success"
