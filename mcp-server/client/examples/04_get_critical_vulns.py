#!/usr/bin/env python3
"""
Example 4: Get Critical Vulnerabilities

Demonstrates:
- Retrieving scan results with filtering
- Parsing JSON-NL format
- Helper method for critical vulnerabilities
- Schema profiles (minimal, brief, full)

Usage:
    python 04_get_critical_vulns.py <task_id>
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client.nessus_fastmcp_client import NessusFastMCPClient


async def main() -> None:
    """Get critical vulnerabilities example."""

    if len(sys.argv) < 2:
        print("Usage: python 04_get_critical_vulns.py <task_id>")
        print()
        print("Example:")
        print("  python 04_get_critical_vulns.py nessus-local-20251108-143022")
        sys.exit(1)

    task_id = sys.argv[1]

    async with NessusFastMCPClient(
        url="http://localhost:8836/mcp", debug=False
    ) as client:
        print(f"Retrieving results for: {task_id}")
        print("=" * 60)
        print()

        # Method 1: Use helper method (easiest)
        print("Method 1: Using helper method")
        print("-" * 60)

        critical = await client.get_critical_vulnerabilities(task_id)

        print(f"Found {len(critical)} critical vulnerabilities")
        print()

        for i, vuln in enumerate(critical[:5], 1):  # Show first 5
            print(f"{i}. Host: {vuln.get('host')}")
            print(f"   Plugin: {vuln.get('plugin_name')}")
            print(f"   Severity: {vuln.get('severity')} (Critical)")
            print(f"   CVSS: {vuln.get('cvss_score', 'N/A')}")
            cve = vuln.get("cve", [])
            if cve:
                print(f"   CVE: {', '.join(cve if isinstance(cve, list) else [cve])}")
            print()

        if len(critical) > 5:
            print(f"... and {len(critical) - 5} more critical vulnerabilities")
            print()

        # Method 2: Use get_results with filters (more control)
        print("Method 2: Using get_results with filters")
        print("-" * 60)

        results = await client.get_results(
            task_id=task_id,
            schema_profile="minimal",  # Smaller schema
            filters={
                "severity": "4",
                "exploit_available": True,
            },  # Critical with exploits
            page=0,  # Get all data
        )

        # Parse JSON-NL format
        exploitable_critical = []
        for line in results.strip().split("\n"):
            data = json.loads(line)
            if data.get("type") == "vulnerability":
                exploitable_critical.append(data)

        print(f"Found {len(exploitable_critical)} EXPLOITABLE critical vulnerabilities")
        print()

        for i, vuln in enumerate(exploitable_critical[:3], 1):  # Show first 3
            print(f"{i}. Host: {vuln.get('host')}")
            print(f"   Plugin ID: {vuln.get('plugin_id')}")
            print(f"   Severity: {vuln.get('severity')}")
            print(f"   CVSS: {vuln.get('cvss_score', 'N/A')}")
            print(f"   Exploit Available: {vuln.get('exploit_available')}")
            print()

        # Method 3: Get all vulnerabilities with schema profiles
        print("Method 3: Schema profiles comparison")
        print("-" * 60)

        # Minimal schema
        minimal_results = await client.get_results(
            task_id=task_id, schema_profile="minimal", page=1, page_size=10
        )

        # Brief schema (default)
        brief_results = await client.get_results(
            task_id=task_id, schema_profile="brief", page=1, page_size=10
        )

        print(f"Minimal schema size: {len(minimal_results)} bytes")
        print(f"Brief schema size: {len(brief_results)} bytes")
        print(
            f"Size reduction: ~{100 - (len(minimal_results) / len(brief_results) * 100):.0f}%"
        )
        print()

        print("✓ Example completed!")
        print()
        print("See full workflow example:")
        print("  python 05_full_workflow.py")


if __name__ == "__main__":
    asyncio.run(main())
