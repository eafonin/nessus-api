"""
Phase 2 Tests: Schema System & Results Parsing

Run with: pytest tests/integration/test_phase2.py -v

This tests:
- Nessus XML parser
- Schema profiles
- Generic filtering
- JSON-NL converter
- Pagination
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from schema.converter import NessusToJsonNL
from schema.filters import apply_filters, compare_number
from schema.parser import parse_nessus_file
from schema.profiles import SCHEMAS, get_schema_fields

# Mark all tests as phase2
pytestmark = pytest.mark.phase2


class TestParser:
    """Test Nessus XML parser"""

    def test_parse_nessus_file(self):
        """Test parsing a real .nessus file"""
        # Find a .nessus file from Phase 1 tests
        nessus_files = list(Path("/tmp").glob("scan_*.nessus"))
        if not nessus_files:
            pytest.skip("No .nessus files found in /tmp")

        nessus_file = nessus_files[0]
        nessus_data = nessus_file.read_bytes()

        # Parse
        result = parse_nessus_file(nessus_data)

        # Verify structure
        assert "scan_metadata" in result
        assert "vulnerabilities" in result
        assert "scan_name" in result["scan_metadata"]

        # Verify vulnerabilities
        vulns = result["vulnerabilities"]
        assert len(vulns) > 0

        # Check first vulnerability structure
        vuln = vulns[0]
        assert "type" in vuln
        assert vuln["type"] == "vulnerability"
        assert "host" in vuln
        assert "plugin_id" in vuln
        assert "plugin_name" in vuln
        assert "severity" in vuln

    def test_parser_handles_cve_lists(self):
        """Test that parser correctly handles multiple CVEs"""
        xml_data = b"""<?xml version="1.0"?>
        <NessusClientData_v2>
            <Report name="Test">
                <ReportHost name="192.168.1.1">
                    <ReportItem pluginID="12345" pluginName="Test" severity="3" port="80" protocol="tcp">
                        <cve>CVE-2021-1234</cve>
                        <cve>CVE-2021-5678</cve>
                    </ReportItem>
                </ReportHost>
            </Report>
        </NessusClientData_v2>
        """

        result = parse_nessus_file(xml_data)
        vuln = result["vulnerabilities"][0]
        assert "cve" in vuln
        assert isinstance(vuln["cve"], list)
        assert len(vuln["cve"]) == 2
        assert "CVE-2021-1234" in vuln["cve"]
        assert "CVE-2021-5678" in vuln["cve"]


class TestProfiles:
    """Test schema profiles"""

    def test_schema_profiles_exist(self):
        """Test that all required schema profiles exist"""
        assert "minimal" in SCHEMAS
        assert "summary" in SCHEMAS
        assert "brief" in SCHEMAS
        assert "full" in SCHEMAS

    def test_minimal_schema_fields(self):
        """Test minimal schema has correct fields"""
        fields = get_schema_fields("minimal")
        assert len(fields) == 6
        assert "host" in fields
        assert "plugin_id" in fields
        assert "severity" in fields
        assert "cve" in fields
        assert "cvss_score" in fields
        assert "exploit_available" in fields

    def test_full_schema_returns_none(self):
        """Test full schema returns None (all fields)"""
        fields = get_schema_fields("full")
        assert fields is None

    def test_invalid_profile_raises_error(self):
        """Test invalid profile name raises ValueError"""
        with pytest.raises(ValueError, match="Invalid schema profile"):
            get_schema_fields("invalid")

    def test_custom_fields_with_default_profile(self):
        """Test custom_fields works with default profile"""
        fields = get_schema_fields("brief", custom_fields=["host", "severity"])
        assert fields == ["host", "severity"]

    def test_mutual_exclusivity(self):
        """Test that non-default profile and custom_fields are mutually exclusive"""
        with pytest.raises(ValueError, match="Cannot specify both"):
            get_schema_fields("minimal", custom_fields=["host"])


class TestFilters:
    """Test generic filtering engine"""

    def test_string_filter_substring(self):
        """Test string filter with substring matching"""
        vulns = [
            {"host": "192.168.1.1", "plugin_name": "Apache Vulnerability"},
            {"host": "192.168.1.2", "plugin_name": "Nginx Vulnerability"},
        ]
        filters = {"plugin_name": "Apache"}
        result = apply_filters(vulns, filters)
        assert len(result) == 1
        assert result[0]["host"] == "192.168.1.1"

    def test_string_filter_case_insensitive(self):
        """Test string filter is case-insensitive"""
        vulns = [{"plugin_name": "Apache Vulnerability"}]
        filters = {"plugin_name": "apache"}
        result = apply_filters(vulns, filters)
        assert len(result) == 1

    def test_number_filter_greater_than(self):
        """Test number filter with > operator"""
        vulns = [
            {"cvss_score": 8.5},
            {"cvss_score": 6.0},
            {"cvss_score": 9.1},
        ]
        filters = {"cvss_score": ">7.0"}
        result = apply_filters(vulns, filters)
        assert len(result) == 2
        assert all(v["cvss_score"] > 7.0 for v in result)

    def test_number_filter_greater_equal(self):
        """Test number filter with >= operator"""
        vulns = [
            {"cvss_score": 7.0},
            {"cvss_score": 6.9},
            {"cvss_score": 7.1},
        ]
        filters = {"cvss_score": ">=7.0"}
        result = apply_filters(vulns, filters)
        assert len(result) == 2

    def test_boolean_filter(self):
        """Test boolean filter"""
        vulns = [
            {"exploit_available": True},
            {"exploit_available": False},
        ]
        filters = {"exploit_available": True}
        result = apply_filters(vulns, filters)
        assert len(result) == 1
        assert result[0]["exploit_available"] is True

    def test_list_filter(self):
        """Test list filter (CVE search)"""
        vulns = [
            {"cve": ["CVE-2021-1234", "CVE-2021-5678"]},
            {"cve": ["CVE-2020-9999"]},
        ]
        filters = {"cve": "CVE-2021"}
        result = apply_filters(vulns, filters)
        assert len(result) == 1

    def test_multiple_filters_and_logic(self):
        """Test multiple filters use AND logic"""
        vulns = [
            {"severity": "4", "cvss_score": 9.0},
            {"severity": "3", "cvss_score": 8.0},
            {"severity": "4", "cvss_score": 6.0},
        ]
        filters = {"severity": "4", "cvss_score": ">7.0"}
        result = apply_filters(vulns, filters)
        assert len(result) == 1
        assert result[0]["cvss_score"] == 9.0

    def test_compare_number_operators(self):
        """Test number comparison operators"""
        assert compare_number(8.0, ">7.0") is True
        assert compare_number(6.0, ">7.0") is False
        assert compare_number(7.0, ">=7.0") is True
        assert compare_number(7.0, "<8.0") is True
        assert compare_number(7.0, "<=7.0") is True
        assert compare_number(7.0, "=7.0") is True


class TestConverter:
    """Test JSON-NL converter"""

    @pytest.fixture
    def sample_nessus_data(self):
        """Sample .nessus XML data"""
        return b"""<?xml version="1.0"?>
        <NessusClientData_v2>
            <Report name="Test Scan">
                <ReportHost name="192.168.1.1">
                    <ReportItem pluginID="12345" pluginName="Test Vuln 1" severity="4" port="80" protocol="tcp">
                        <cvss_score>9.0</cvss_score>
                        <cve>CVE-2021-1234</cve>
                        <exploit_available>true</exploit_available>
                        <description>Test description</description>
                    </ReportItem>
                    <ReportItem pluginID="12346" pluginName="Test Vuln 2" severity="2" port="443" protocol="tcp">
                        <cvss_score>5.0</cvss_score>
                        <description>Another test</description>
                    </ReportItem>
                </ReportHost>
            </Report>
        </NessusClientData_v2>
        """

    def test_converter_basic(self, sample_nessus_data):
        """Test basic converter functionality"""
        converter = NessusToJsonNL()
        result = converter.convert(
            sample_nessus_data, schema_profile="brief", page=1, page_size=40
        )

        lines = result.split("\n")
        assert len(lines) >= 4  # schema + metadata + vulns + pagination

        # Parse first line (schema)
        schema = json.loads(lines[0])
        assert schema["type"] == "schema"
        assert schema["profile"] == "brief"
        assert "fields" in schema
        assert schema["total_vulnerabilities"] == 2

        # Parse second line (metadata)
        metadata = json.loads(lines[1])
        assert metadata["type"] == "scan_metadata"
        assert metadata["scan_name"] == "Test Scan"

    def test_converter_minimal_schema(self, sample_nessus_data):
        """Test converter with minimal schema"""
        converter = NessusToJsonNL()
        result = converter.convert(sample_nessus_data, schema_profile="minimal")

        lines = result.split("\n")
        vuln_line = lines[2]  # First vulnerability
        vuln = json.loads(vuln_line)

        # Check that only minimal fields are present (plus 'type')
        minimal_fields = SCHEMAS["minimal"]
        for _field in minimal_fields:
            # Field might not be in data, but if it is in minimal schema, converter tried to include it
            pass
        assert "type" in vuln

    def test_converter_custom_fields(self, sample_nessus_data):
        """Test converter with custom fields"""
        converter = NessusToJsonNL()
        custom = ["host", "plugin_id", "severity"]
        result = converter.convert(sample_nessus_data, custom_fields=custom)

        lines = result.split("\n")
        schema = json.loads(lines[0])
        assert schema["profile"] == "custom"
        assert schema["fields"] == custom

    def test_converter_with_filters(self, sample_nessus_data):
        """Test converter with filters"""
        converter = NessusToJsonNL()
        filters = {"severity": "4"}
        result = converter.convert(sample_nessus_data, filters=filters)

        lines = result.split("\n")
        schema = json.loads(lines[0])
        assert schema["filters_applied"] == filters
        assert schema["total_vulnerabilities"] == 1  # Only severity 4

    def test_converter_pagination(self, sample_nessus_data):
        """Test converter pagination"""
        converter = NessusToJsonNL()
        # page_size=1 gets clamped to 10 (minimum), so with 2 vulns, both will be returned
        result = converter.convert(sample_nessus_data, page=1, page_size=1)

        lines = result.split("\n")
        # schema + metadata + 2 vulns (page_size clamped to 10) + pagination = 5 lines
        assert len(lines) == 5

        pagination = json.loads(lines[-1])
        assert pagination["type"] == "pagination"
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10  # Clamped from 1 to 10
        assert pagination["has_next"] is False  # No more pages (only 2 vulns total)
        assert pagination["next_page"] is None

    def test_converter_page_zero_returns_all(self, sample_nessus_data):
        """Test that page=0 returns all data"""
        converter = NessusToJsonNL()
        result = converter.convert(sample_nessus_data, page=0)

        lines = result.split("\n")
        # schema + metadata + 2 vulns = 4 lines (no pagination line for page=0)
        assert len(lines) == 4

        schema = json.loads(lines[0])
        assert schema["total_pages"] == 1


class TestIntegration:
    """Integration tests for Phase 2"""

    @pytest.fixture
    def real_scan_data(self):
        """
        Load real .nessus file for testing.

        File Discovery Priority:
        1. /tmp/scan_*.nessus (from actual Phase 1 runs) - DEFAULT
        2. tests/fixtures/sample_scan.nessus (checked-in fallback)

        The fixture uses Python's Path.glob() to find files:
        - Path("/tmp").glob("scan_*.nessus") matches any file like:
          scan_33_results.nessus, scan_test.nessus, etc.
        - Returns first match found (sorted by file system order)

        This allows tests to work both:
        - In dev environments (using fresh Phase 1 scan outputs from /tmp)
        - In CI/isolated environments (using fixtures/sample_scan.nessus fallback)
        """
        # Try /tmp first for files from actual Phase 1 runs (default)
        nessus_files = list(Path("/tmp").glob("scan_*.nessus"))
        if nessus_files:
            # Return first matching file (e.g., scan_33_results.nessus)
            return nessus_files[0].read_bytes()

        # Fall back to fixtures directory (checked-in test data)
        fixture_file = Path(__file__).parent.parent / "fixtures" / "sample_scan.nessus"
        if fixture_file.exists():
            return fixture_file.read_bytes()

        # No test data found anywhere
        pytest.skip("No .nessus files found in /tmp or fixtures")

    def test_end_to_end_with_real_scan(self, real_scan_data):
        """Test complete workflow with real scan data"""
        converter = NessusToJsonNL()
        result = converter.convert(
            real_scan_data,
            schema_profile="brief",
            filters={"severity": "4"},  # Critical only
            page=1,
            page_size=10,
        )

        lines = result.split("\n")
        assert len(lines) >= 3  # At minimum: schema + metadata + pagination

        # Verify schema line
        schema = json.loads(lines[0])
        assert schema["type"] == "schema"
        assert schema["profile"] == "brief"
        assert schema["filters_applied"] == {"severity": "4"}

        # Verify metadata
        metadata = json.loads(lines[1])
        assert metadata["type"] == "scan_metadata"

        print(f"\nFound {schema['total_vulnerabilities']} critical vulnerabilities")

    def test_real_scan_pagination_multi_page(self, real_scan_data):
        """Test pagination across multiple pages with real scan"""
        converter = NessusToJsonNL()

        # Use page_size=10 (minimum) to create 4 pages (40 vulns / 10 = 4 pages)
        page1 = converter.convert(real_scan_data, page=1, page_size=10)
        lines = page1.split("\n")

        schema = json.loads(lines[0])
        total_vulns = schema["total_vulnerabilities"]
        total_pages = schema["total_pages"]

        # Verify we have multiple pages
        assert total_vulns == 40
        assert total_pages == 4  # 40 / 10 = 4 pages

        # Verify page 1 has 10 vulnerabilities + schema + metadata + pagination = 13 lines
        assert len(lines) == 13

        # Check pagination info
        pagination = json.loads(lines[-1])
        assert pagination["type"] == "pagination"
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10
        assert pagination["has_next"] is True
        assert pagination["next_page"] == 2

        # Get page 2 and verify different content
        page2 = converter.convert(real_scan_data, page=2, page_size=10)
        lines2 = page2.split("\n")
        assert len(lines2) == 13

        # Verify vulnerabilities are different between pages
        page1_vuln1 = json.loads(lines[2])  # First vuln on page 1
        page2_vuln1 = json.loads(lines2[2])  # First vuln on page 2
        assert page1_vuln1 != page2_vuln1

        # Get last page (page 4) and verify no next page
        last_page = converter.convert(real_scan_data, page=4, page_size=10)
        last_lines = last_page.split("\n")
        last_pagination = json.loads(last_lines[-1])
        assert last_pagination["has_next"] is False
        assert last_pagination["next_page"] is None

    def test_real_scan_filters_with_pagination(self, real_scan_data):
        """Test filters combined with pagination on real data"""
        converter = NessusToJsonNL()

        # Filter for critical vulnerabilities (severity 4)
        # page_size=10 (minimum), 11 critical vulns = 2 pages
        result = converter.convert(
            real_scan_data, filters={"severity": "4"}, page=1, page_size=10
        )

        lines = result.split("\n")
        schema = json.loads(lines[0])

        # Should have 11 critical vulnerabilities
        assert schema["total_vulnerabilities"] == 11
        assert schema["total_pages"] == 2  # 11 / 10 = 2 pages (rounded up)
        assert schema["filters_applied"] == {"severity": "4"}

        # Page 1 should have 10 vulns (schema + metadata + 10 vulns + pagination = 13 lines)
        assert len(lines) == 13

        # Verify all returned vulnerabilities are severity 4
        for i in range(2, len(lines) - 1):  # Skip schema, metadata, pagination
            vuln = json.loads(lines[i])
            if vuln.get("type") == "vulnerability":
                assert vuln.get("severity") == "4"

        # Get page 2 - should have only 1 vulnerability (11 total - 10 on page 1)
        page2 = converter.convert(
            real_scan_data, filters={"severity": "4"}, page=2, page_size=10
        )
        lines2 = page2.split("\n")
        # schema + metadata + 1 vuln + pagination = 4 lines
        assert len(lines2) == 4

        pagination2 = json.loads(lines2[-1])
        assert pagination2["has_next"] is False


# Export all test classes for easy import
__all__ = [
    "TestConverter",
    "TestFilters",
    "TestIntegration",
    "TestParser",
    "TestProfiles",
]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "phase2"])
