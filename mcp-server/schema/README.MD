<!-- README Navigation -->
<!-- L3: mcp-server/schema/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Nessus result parsing, filtering, JSON-NL output -->

# Schema Module

> Nessus result parsing, filtering, and output formatting

**↑ Parent**: [MCP Server](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

## Data Flow

```
.nessus XML → parser.py → filters.py → profiles.py → jsonl_converter.py → JSON-NL
```

## Module Overview

| Module | Lines | Purpose |
|--------|-------|---------|
| `parser.py` | 74 | Parse Nessus XML to dict |
| `filters.py` | 73 | Apply filters to results |
| `profiles.py` | 66 | Schema field definitions |
| `converter.py` | 90 | High-level conversion |
| `jsonl_converter.py` | 61 | JSON-NL output format |

## Schema Profiles

Defined in `profiles.py` - control output verbosity:

| Profile | Fields | Use Case |
|---------|--------|----------|
| `minimal` | 6 | Quick severity overview |
| `summary` | 9 | Scan summary with names |
| `brief` | 11 | Standard analysis (default) |
| `full` | All | Complete data export |

### Field Definitions

```python
"minimal": ["host", "plugin_id", "severity", "cve", "cvss_score", "exploit_available"]

"summary": minimal + ["plugin_name", "cvss3_base_score", "synopsis"]

"brief": summary + ["description", "solution"]

"full": None  # All available fields
```

## Module Details

### parser.py

Parses `.nessus` XML files (Nessus export format):

```python
from schema.parser import parse_nessus_file

result = parse_nessus_file(nessus_xml_bytes)
# Returns:
# {
#     "scan_metadata": {"scan_name": "..."},
#     "vulnerabilities": [
#         {
#             "type": "vulnerability",
#             "host": "192.168.1.1",
#             "plugin_id": "12345",
#             "severity": "3",
#             "cve": ["CVE-2021-1234"],
#             "cvss_score": 7.5,
#             ...
#         }
#     ]
# }
```

Handles:
- Multiple CVEs per vulnerability (collected as list)
- CVSS score conversion to float
- Boolean exploit_available field
- All standard Nessus fields

### filters.py

Generic filtering with AND logic:

```python
from schema.filters import apply_filters

filtered = apply_filters(vulnerabilities, {
    "severity": "4",           # String match
    "cvss_score": ">7.0",      # Numeric comparison
    "exploit_available": True, # Boolean match
    "cve": "2021"             # List contains
})
```

**Filter Types**:

| Type | Syntax | Example |
|------|--------|---------|
| String | substring | `"severity": "4"` |
| Numeric | `>`, `>=`, `<`, `<=`, `=` | `"cvss_score": ">=7.5"` |
| Boolean | `true`/`false` | `"exploit_available": true` |
| List | contains | `"cve": "CVE-2021"` |

### profiles.py

Schema profile management:

```python
from schema.profiles import get_schema_fields

# Predefined profile
fields = get_schema_fields("summary")
# ['host', 'plugin_id', 'severity', 'cve', ...]

# Custom fields
fields = get_schema_fields("brief", custom_fields=["host", "cve", "solution"])
# ['host', 'cve', 'solution']

# Full schema (all fields)
fields = get_schema_fields("full")
# None (means no filtering)
```

### jsonl_converter.py

Converts to paginated JSON-NL output:

```
Line 1: {"type": "schema", "profile": "brief", "fields": [...], "filters_applied": {...}}
Line 2: {"type": "scan_metadata", "scan_name": "..."}
Line 3: {"type": "vulnerability", "host": "...", "plugin_id": "..."}
...
Last:   {"type": "pagination", "page": 1, "total_pages": 5, "total_items": 150}
```

**JSON-NL Benefits**:
- Streaming-friendly (one object per line)
- Parseable without loading entire response
- LLM-friendly for large result sets

## Usage Example

```python
from schema.parser import parse_nessus_file
from schema.filters import apply_filters
from schema.profiles import get_schema_fields

# 1. Parse Nessus file
with open("scan.nessus", "rb") as f:
    data = parse_nessus_file(f.read())

# 2. Filter results
critical = apply_filters(data["vulnerabilities"], {
    "severity": "4",
    "exploit_available": True
})

# 3. Get schema fields
fields = get_schema_fields("summary")

# 4. Project to fields
projected = [
    {k: v for k, v in vuln.items() if k in fields}
    for vuln in critical
]
```

## API Integration

Used by `get_scan_results` MCP tool:

```python
# MCP tool call
get_scan_results(
    task_id="ne_scan_20251126_...",
    schema_profile="brief",
    filters={"severity": "4", "cvss_score": ">7.0"},
    page=1,
    page_size=40
)
```

## Field Reference

Common vulnerability fields from Nessus:

| Field | Type | Description |
|-------|------|-------------|
| `host` | string | Target IP/hostname |
| `plugin_id` | string | Nessus plugin ID |
| `plugin_name` | string | Human-readable name |
| `plugin_family` | string | Plugin category |
| `severity` | string | 0-4 (info to critical) |
| `port` | string | Affected port |
| `protocol` | string | tcp/udp |
| `cve` | list | CVE identifiers |
| `cvss_score` | float | CVSS v2 base score |
| `cvss3_base_score` | float | CVSS v3 base score |
| `exploit_available` | bool | Known exploit exists |
| `synopsis` | string | Brief description |
| `description` | string | Full description |
| `solution` | string | Remediation steps |
| `see_also` | string | Reference URLs |
| `plugin_output` | string | Raw plugin output |
