"""Nessus scan result validator with authentication detection."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a Nessus scan."""
    is_valid: bool
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    authentication_status: str = "unknown"  # success|failed|partial|not_applicable


class NessusValidator:
    """
    Validates Nessus scan results with authentication detection.

    Key Features:
    - XML structure validation
    - Host count verification
    - Authentication status from plugin 19506
    - Authenticated plugin count analysis
    """

    # Plugin 19506: Nessus Scan Information (contains credential status)
    SCAN_INFO_PLUGIN_ID = "19506"

    # Plugins that ONLY work with authentication
    AUTH_REQUIRED_PLUGINS = {
        "20811": "Windows Compliance Checks",
        "21643": "Windows Local Security Checks",
        "97833": "Windows Security Update Check",
        "66334": "MS Windows Patch Enumeration",
        "12634": "Unix/Linux Local Security Checks",
        "51192": "Debian Local Security Checks",
        "33851": "Red Hat Local Security Checks",
        "22869": "Installed Software Enumeration",
    }

    # Minimum authenticated plugins for trusted scan validation
    MIN_AUTH_PLUGINS = 5

    def validate(
        self,
        nessus_file: Path,
        scan_type: str = "untrusted",
        expected_hosts: int = 0
    ) -> ValidationResult:
        """
        Validate Nessus scan results.

        Args:
            nessus_file: Path to .nessus file
            scan_type: "untrusted"|"trusted_basic"|"trusted_privileged"
            expected_hosts: Expected host count (0 = don't check)

        Returns:
            ValidationResult with is_valid, stats, authentication_status
        """
        warnings = []
        stats = {}

        # 1. File existence check
        if not nessus_file.exists():
            return ValidationResult(
                is_valid=False,
                error=f"Results file not found: {nessus_file}",
                authentication_status="unknown"
            )

        # 2. File size check
        file_size = nessus_file.stat().st_size
        stats["file_size_bytes"] = file_size

        # Real Nessus files are typically > 1KB, but we use a low threshold
        # to allow unit tests with minimal XML
        if file_size < 50:
            return ValidationResult(
                is_valid=False,
                error=f"Results file too small ({file_size} bytes)",
                stats=stats,
                authentication_status="unknown"
            )

        # 3. XML parsing
        try:
            tree = ET.parse(nessus_file)
            root = tree.getroot()
        except ET.ParseError as e:
            return ValidationResult(
                is_valid=False,
                error=f"Invalid XML: {e}",
                stats=stats,
                authentication_status="unknown"
            )

        # 4. Host analysis
        hosts = root.findall(".//ReportHost")
        stats["hosts_scanned"] = len(hosts)

        if len(hosts) == 0:
            return ValidationResult(
                is_valid=False,
                error="No hosts in scan results",
                stats=stats,
                authentication_status="unknown"
            )

        if expected_hosts > 0 and len(hosts) < expected_hosts:
            warnings.append(
                f"Host count ({len(hosts)}) less than expected ({expected_hosts})"
            )

        # 5. Plugin analysis
        all_plugins = root.findall(".//ReportItem")
        stats["total_plugins"] = len(all_plugins)

        # Count authenticated plugins
        auth_plugin_count = 0
        for item in all_plugins:
            plugin_id = item.get("pluginID", "")
            if plugin_id in self.AUTH_REQUIRED_PLUGINS:
                auth_plugin_count += 1

        stats["auth_plugins_found"] = auth_plugin_count

        # 6. Authentication status detection
        cred_status = self._parse_credentialed_status(root)
        stats["credentialed_status_raw"] = cred_status

        # Determine authentication status
        if scan_type == "untrusted":
            auth_status = "not_applicable"
        elif cred_status == "yes":
            auth_status = "success"
        elif cred_status == "no":
            auth_status = "failed"
        elif cred_status == "partial":
            auth_status = "partial"
        elif auth_plugin_count >= self.MIN_AUTH_PLUGINS:
            # Fallback: infer from plugin count
            auth_status = "success"
        elif scan_type in ("trusted_basic", "trusted_privileged"):
            # Trusted scan but no auth evidence
            auth_status = "failed"
        else:
            auth_status = "unknown"

        # 7. Validation based on scan type
        if scan_type in ("trusted_basic", "trusted_privileged"):
            if auth_status == "failed":
                return ValidationResult(
                    is_valid=False,
                    error=(
                        f"Authentication FAILED for {scan_type} scan. "
                        f"Plugin 19506 reports: Credentialed checks = {cred_status or 'not found'}. "
                        f"Only {auth_plugin_count} authenticated plugins found (minimum: {self.MIN_AUTH_PLUGINS}). "
                        f"Results contain only network-level data."
                    ),
                    warnings=warnings,
                    stats=stats,
                    authentication_status=auth_status
                )
            elif auth_status == "partial":
                warnings.append(
                    "Partial authentication: some hosts authenticated, some failed"
                )

        # 8. Vulnerability counts
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for item in all_plugins:
            severity = int(item.get("severity", "0"))
            if severity == 4:
                severity_counts["critical"] += 1
            elif severity == 3:
                severity_counts["high"] += 1
            elif severity == 2:
                severity_counts["medium"] += 1
            elif severity == 1:
                severity_counts["low"] += 1
            else:
                severity_counts["info"] += 1

        stats["severity_counts"] = severity_counts
        stats["total_vulnerabilities"] = sum(
            v for k, v in severity_counts.items() if k != "info"
        )

        return ValidationResult(
            is_valid=True,
            warnings=warnings,
            stats=stats,
            authentication_status=auth_status
        )

    def _parse_credentialed_status(self, root: ET.Element) -> Optional[str]:
        """
        Parse plugin 19506 output for credential status.

        Looks for: "Credentialed checks : yes|no|partial"

        Returns:
            "yes", "no", "partial", or None if not found
        """
        for item in root.findall(".//ReportItem"):
            if item.get("pluginID") == self.SCAN_INFO_PLUGIN_ID:
                output = item.findtext("plugin_output", "")
                for line in output.split("\n"):
                    line_lower = line.lower()
                    if "credentialed checks" in line_lower:
                        if "yes" in line_lower:
                            return "yes"
                        elif "no" in line_lower:
                            return "no"
                        elif "partial" in line_lower:
                            return "partial"
        return None


def validate_scan_results(
    nessus_file: Path,
    scan_type: str = "untrusted",
    expected_hosts: int = 0
) -> ValidationResult:
    """Convenience function for validation."""
    validator = NessusValidator()
    return validator.validate(nessus_file, scan_type, expected_hosts)
