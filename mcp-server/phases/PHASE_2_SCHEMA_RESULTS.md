# Phase 2: Schema System & Results

> **Duration**: Week 2
> **Goal**: JSON-NL converter with flexible schemas and filtering
> **Status**: 🔴 Not Started
> **Prerequisites**: Phase 1 complete, scans producing .nessus files

---

## Overview

Phase 2 adds the ability to retrieve and filter scan results in LLM-friendly format:
- **Schema Profiles**: 4 predefined + custom field selection
- **Nessus XML Parser**: Extract vulnerabilities from .nessus files
- **JSON-NL Converter**: One vulnerability per line, self-describing
- **Generic Filtering**: Filter on any attribute (severity, CVE, host, etc.)
- **Pagination**: Configurable page sizes, page=0 for all data
- **Filter Echo**: First line includes applied filters for LLM reasoning

---

## Phase 2 Task List

### 2.1: Schema Profiles Definition
- [ ] Create `schema/profiles.py`
- [ ] Define `SCHEMAS` dict with 4 profiles
- [ ] `minimal`: 6 core fields
- [ ] `summary`: minimal + 3 fields
- [ ] `brief`: summary + 2 fields (default)
- [ ] `full`: all fields (no filtering)
- [ ] Helper functions: `get_schema_fields(profile)`

### 2.2: Nessus XML Parser
- [ ] Create `schema/parser.py`
- [ ] Parse `.nessus` XML files (lxml)
- [ ] Extract ReportHost elements
- [ ] Extract ReportItem (vulnerabilities)
- [ ] Build vulnerability dictionaries
- [ ] Extract scan metadata (name, targets, timestamps)
- [ ] Test parser with real .nessus files

### 2.3: JSON-NL Converter
- [ ] Create `schema/converter.py`
- [ ] `NessusToJsonNL` class
- [ ] `convert()` method:
  - [ ] Line 1: Schema definition + filters_applied
  - [ ] Line 2: Scan metadata
  - [ ] Lines 3+: Vulnerabilities (one per line)
  - [ ] Last line: Pagination info
- [ ] Field projection based on schema
- [ ] Test converter output format

### 2.4: Generic Filtering Engine
- [ ] Create `schema/filters.py`
- [ ] `apply_filters()` function
- [ ] String filter: case-insensitive substring
- [ ] Number filter: >, >=, <, <=, = operators
- [ ] Boolean filter: exact match
- [ ] List filter: any element contains
- [ ] AND logic (all filters must match)
- [ ] Test filtering with various attributes

### 2.5: Pagination Logic
- [ ] Implement pagination in converter
- [ ] Default: 40 lines per page
- [ ] Range: 10-100 lines
- [ ] `page=0`: return all data (no limit)
- [ ] Calculate total_pages
- [ ] Add next_page indicator
- [ ] Test pagination edge cases

### 2.6: Results Retrieval Tool
- [ ] Add `get_scan_results()` tool to `mcp_server.py`
- [ ] Parameters: task_id, page, page_size, schema_profile, custom_fields, filters
- [ ] Validate mutual exclusivity (profile vs custom_fields)
- [ ] Load .nessus file from task directory
- [ ] Call converter with parameters
- [ ] Return JSON-NL string
- [ ] Test tool with various schemas and filters

### 2.7: Schema Tests
- [ ] Unit tests for parser
- [ ] Unit tests for converter
- [ ] Unit tests for filters
- [ ] Integration test: scan → results → filter → verify
- [ ] Test custom_fields vs schema_profile conflict (400 error)
- [ ] Test page=0 returns all data

---

## Key Implementation Details

### Schema Profiles

**File: `schema/profiles.py`**
```python
"""Schema profile definitions."""

SCHEMAS = {
    "minimal": [
        "host", "plugin_id", "severity", "cve",
        "cvss_score", "exploit_available"
    ],
    "summary": [
        "host", "plugin_id", "severity", "cve", "cvss_score", "exploit_available",
        "plugin_name", "cvss3_base_score", "synopsis"
    ],
    "brief": [
        "host", "plugin_id", "severity", "cve", "cvss_score", "exploit_available",
        "plugin_name", "cvss3_base_score", "synopsis",
        "description", "solution"
    ],
    "full": None  # All fields
}


def get_schema_fields(profile: str) -> list:
    """Get field list for schema profile."""
    if profile not in SCHEMAS:
        raise ValueError(f"Unknown schema profile: {profile}")
    return SCHEMAS[profile]
```

### Nessus XML Parser

**File: `schema/parser.py`**
```python
"""Parse Nessus .nessus XML files."""
import xml.etree.ElementTree as ET
from typing import List, Dict, Any


def parse_nessus_file(nessus_data: bytes) -> Dict[str, Any]:
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
            vuln = {
                "type": "vulnerability",
                "host": host,
                "plugin_id": int(item.get("pluginID")),
                "plugin_name": item.get("pluginName"),
                "severity": item.get("severity"),
                "port": item.get("port"),
                "protocol": item.get("protocol"),
            }

            # Extract child elements
            for child in item:
                vuln[child.tag] = child.text

            vulnerabilities.append(vuln)

    return {
        "scan_metadata": scan_metadata,
        "vulnerabilities": vulnerabilities
    }
```

### JSON-NL Converter

**File: `schema/converter.py`**
```python
"""Convert Nessus data to JSON-NL format."""
import json
from typing import List, Dict, Any, Optional
from .parser import parse_nessus_file
from .profiles import get_schema_fields
from .filters import apply_filters


class NessusToJsonNL:
    """Convert Nessus XML to JSON-NL with schemas and filtering."""

    def convert(
        self,
        nessus_data: bytes,
        schema_profile: str = "brief",
        custom_fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 40
    ) -> str:
        """
        Convert to JSON-NL format.

        Returns multi-line string (JSON-NL).
        """
        # Parse Nessus data
        parsed = parse_nessus_file(nessus_data)
        all_vulns = parsed["vulnerabilities"]
        scan_meta = parsed["scan_metadata"]

        # Determine fields
        if custom_fields:
            fields = custom_fields
            profile = "custom"
        elif schema_profile == "full":
            fields = None  # All fields
            profile = "full"
        else:
            fields = get_schema_fields(schema_profile)
            profile = schema_profile

        # Apply field projection
        if fields:
            all_vulns = [
                {k: v for k, v in vuln.items() if k in fields or k == "type"}
                for vuln in all_vulns
            ]

        # Apply filters
        if filters:
            all_vulns = apply_filters(all_vulns, filters)

        # Pagination
        total_vulns = len(all_vulns)
        if page == 0:
            # Return all
            page_vulns = all_vulns
            total_pages = 1
        else:
            total_pages = (total_vulns + page_size - 1) // page_size
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_vulns = all_vulns[start_idx:end_idx]

        # Build JSON-NL output
        lines = []

        # Line 1: Schema with filters_applied
        lines.append(json.dumps({
            "type": "schema",
            "profile": profile,
            "fields": fields or "all",
            "filters_applied": filters or {},
            "total_vulnerabilities": total_vulns,
            "total_pages": total_pages
        }))

        # Line 2: Scan metadata
        lines.append(json.dumps({
            "type": "scan_metadata",
            **scan_meta
        }))

        # Lines 3+: Vulnerabilities
        for vuln in page_vulns:
            lines.append(json.dumps(vuln))

        # Last line: Pagination
        if page != 0:
            lines.append(json.dumps({
                "type": "pagination",
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "next_page": page + 1 if page < total_pages else None
            }))

        return "\n".join(lines)
```

### Generic Filtering

**File: `schema/filters.py`**
```python
"""Generic filtering engine."""
from typing import List, Dict, Any


def apply_filters(vulns: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """
    Apply filters to vulnerability list.

    AND logic: all filters must match.
    """
    return [v for v in vulns if matches_all_filters(v, filters)]


def matches_all_filters(vuln: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """Check if vulnerability matches all filters."""
    for field, filter_value in filters.items():
        if field not in vuln:
            return False

        vuln_value = vuln[field]

        # String filter
        if isinstance(vuln_value, str) and isinstance(filter_value, str):
            if filter_value.lower() not in vuln_value.lower():
                return False

        # Number filter with operators
        elif isinstance(filter_value, str) and filter_value[0] in "<>=":
            try:
                num_value = float(vuln_value)
                if not compare_number(num_value, filter_value):
                    return False
            except (ValueError, TypeError):
                return False

        # Boolean filter
        elif isinstance(filter_value, bool):
            if bool(vuln_value) != filter_value:
                return False

        # List filter
        elif isinstance(vuln_value, list):
            found = any(str(filter_value).lower() in str(item).lower() for item in vuln_value)
            if not found:
                return False

    return True


def compare_number(value: float, operator_str: str) -> bool:
    """Compare number with operator string like '>7.0'."""
    if operator_str.startswith(">="):
        return value >= float(operator_str[2:])
    elif operator_str.startswith("<="):
        return value <= float(operator_str[2:])
    elif operator_str.startswith(">"):
        return value > float(operator_str[1:])
    elif operator_str.startswith("<"):
        return value < float(operator_str[1:])
    elif operator_str.startswith("="):
        return value == float(operator_str[1:])
    return False
```

### Results Tool

**Update: `tools/mcp_server.py`**
```python
@mcp.tool()
async def get_scan_results(
    task_id: str,
    page: int = 1,
    page_size: int = 40,
    schema_profile: str = "brief",
    custom_fields: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get scan results in paginated JSON-NL format.

    Args:
        task_id: Task ID from run_*_scan()
        page: Page number (1-indexed), or 0 for ALL data
        page_size: Lines per page (10-100)
        schema_profile: Predefined schema (minimal|summary|brief|full)
        custom_fields: Custom field list (mutually exclusive with schema_profile)
        filters: Filter dict (e.g., {"severity": "Critical", "cvss_score": ">7.0"})

    Returns:
        JSON-NL string with schema, metadata, vulnerabilities, pagination
    """
    # Validate mutual exclusivity
    if schema_profile != "brief" and custom_fields is not None:
        raise ValueError(
            "Cannot specify both schema_profile and custom_fields"
        )

    # Get task
    task = task_manager.get_task(task_id)
    if not task:
        return json.dumps({"error": f"Task {task_id} not found"})

    if task.status != "completed":
        return json.dumps({
            "error": f"Scan not completed yet (status: {task.status})"
        })

    # Load .nessus file
    nessus_file = task_manager.data_dir / task_id / "scan_native.nessus"
    if not nessus_file.exists():
        return json.dumps({"error": "Scan results not found"})

    nessus_data = nessus_file.read_bytes()

    # Convert to JSON-NL
    converter = NessusToJsonNL()
    results = converter.convert(
        nessus_data=nessus_data,
        schema_profile=schema_profile,
        custom_fields=custom_fields,
        filters=filters,
        page=page,
        page_size=page_size
    )

    return results
```

---

## Phase 2 Completion Checklist

### Deliverables
- [ ] Schema profiles defined (4 + custom)
- [ ] Nessus XML parser working
- [ ] JSON-NL converter produces correct format
- [ ] Generic filtering engine handles all types
- [ ] Pagination working (page=0 returns all)
- [ ] `get_scan_results()` tool functional
- [ ] Filter echo in first line
- [ ] Tests pass for all schemas and filters

### Verification
```bash
# Parse real .nessus file
python -c "from schema.parser import parse_nessus_file; \
           data = open('dev1/data/TASK_ID/scan_native.nessus', 'rb').read(); \
           print(parse_nessus_file(data))"

# Get results with filter
curl -X POST http://localhost:8835/tools/call \
  -d '{"name":"get_scan_results", "arguments":{"task_id":"...","filters":{"severity":"Critical"}}}'

# Test pagination
pytest tests/test_converter.py -v
```

### Success Criteria
✅ Phase 2 complete when:
1. All schema profiles return correct fields
2. Filtering works on any attribute
3. page=0 returns complete dataset
4. Filters echoed in first line
5. Tests pass

---

**Next**: [PHASE_3_OBSERVABILITY.md](./PHASE_3_OBSERVABILITY.md)
