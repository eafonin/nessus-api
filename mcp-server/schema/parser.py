"""Parse Nessus .nessus XML files."""

import xml.etree.ElementTree as ET
from typing import Any


def parse_nessus_file(nessus_data: bytes) -> dict[str, Any]:
    """
    Parse .nessus XML file.

    Returns:
        {
            "scan_metadata": {...},
            "vulnerabilities": [...]
        }
    """
    root = ET.fromstring(nessus_data)

    # Extract scan metadata
    report_elem = root.find(".//Report")
    scan_metadata = {
        "scan_name": report_elem.get("name") if report_elem is not None else "Unknown",
    }

    # Extract vulnerabilities
    vulnerabilities = []

    for report_host in root.findall(".//ReportHost"):
        host = report_host.get("name")

        for item in report_host.findall("ReportItem"):
            # Extract attributes
            vuln: dict[str, Any] = {
                "type": "vulnerability",
                "host": host,
                "plugin_id": item.get("pluginID"),
                "plugin_name": item.get("pluginName"),
                "plugin_family": item.get("pluginFamily"),
                "severity": item.get("severity"),
                "port": item.get("port"),
                "svc_name": item.get("svc_name"),
                "protocol": item.get("protocol"),
            }

            # Extract child elements
            for child in item:
                tag = child.tag
                text = child.text or ""

                # Handle specific fields
                if tag == "cve":
                    # CVEs can appear multiple times, collect them in a list
                    if "cve" not in vuln:
                        vuln["cve"] = []
                    vuln["cve"].append(text)
                elif tag in ["cvss_base_score", "cvss3_base_score", "cvss_score"]:
                    # Convert scores to float
                    try:
                        vuln[tag] = float(text) if text else None
                    except ValueError:
                        vuln[tag] = text
                elif tag == "exploit_available":
                    # Convert to boolean
                    vuln[tag] = text.lower() == "true"
                else:
                    vuln[tag] = text

            vulnerabilities.append(vuln)

    return {"scan_metadata": scan_metadata, "vulnerabilities": vulnerabilities}
