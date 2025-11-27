# Result Filtering Guide

> Strategies for filtering and analyzing scan results

## Filter Basics

Filters are passed as a dict to `get_scan_results`:

```python
get_scan_results(
    task_id="...",
    filters={"field": "value"}
)
```

## Available Filters

### Severity Filter

Severity levels:
- `0` = Informational
- `1` = Low
- `2` = Medium
- `3` = High
- `4` = Critical

```python
# Exact match
filters={"severity": "4"}           # Critical only

# Comparison operators
filters={"severity": ">=3"}         # High and Critical
filters={"severity": ">2"}          # High and Critical
filters={"severity": "<=1"}         # Info and Low
```

### CVSS Score Filter

CVSS 3.0 scores range from 0.0 to 10.0:
- 0.0 = None
- 0.1-3.9 = Low
- 4.0-6.9 = Medium
- 7.0-8.9 = High
- 9.0-10.0 = Critical

```python
# Comparison operators
filters={"cvss_score": ">7.0"}      # High and Critical
filters={"cvss_score": ">=9.0"}     # Critical only
filters={"cvss_score": "<4.0"}      # Low and below
```

### Host Filter

```python
# Specific host
filters={"host": "192.168.1.100"}

# Note: Currently exact match only, no wildcards
```

### Combined Filters

Multiple filters are ANDed together:

```python
# Critical OR High vulnerabilities with CVSS > 7
filters={"severity": ">=3", "cvss_score": ">7.0"}

# Specific host, only high severity
filters={"host": "192.168.1.100", "severity": ">=3"}
```

## Schema Profiles

Control which fields are returned:

| Profile | Fields | Size | Use Case |
|---------|--------|------|----------|
| `minimal` | host, plugin_id, severity | Small | Counting, aggregation |
| `summary` | + plugin_name, port | Medium | Quick overview |
| `brief` | + cvss_score, cve, synopsis | Standard | Normal analysis |
| `full` | + description, solution, see_also | Large | Deep dive, reporting |

```python
# Quick stats (minimal data)
get_scan_results(task_id, schema_profile="minimal")

# Full details for report
get_scan_results(task_id, schema_profile="full")
```

## Pagination

### Get All Results

```python
get_scan_results(task_id, page=0)
```

Use `page=0` when you need to:
- Process all vulnerabilities
- Generate statistics
- Find top N items
- Create comprehensive reports

### Paginated Results

```python
# First page of 40 items
get_scan_results(task_id, page=1, page_size=40)

# Check pagination info in response
{"type": "pagination", "page": 1, "total_pages": 5, "next_page": 2}
```

Use pagination when:
- Results are very large (1000+)
- Displaying to user incrementally
- Memory-constrained environment

## Common Filter Strategies

### Strategy 1: Critical Issues First

Get only the most severe issues:

```python
results = get_scan_results(
    task_id=task_id,
    page=0,
    schema_profile="brief",
    filters={"severity": "4"}
)
```

### Strategy 2: Exploitable Vulnerabilities

Focus on high CVSS (likely exploitable):

```python
results = get_scan_results(
    task_id=task_id,
    page=0,
    schema_profile="full",
    filters={"cvss_score": ">=7.0"}
)
```

### Strategy 3: Per-Host Analysis

Analyze one host at a time:

```python
results = get_scan_results(
    task_id=task_id,
    page=0,
    filters={"host": "192.168.1.100"}
)
```

### Strategy 4: Actionable Items

High+ severity that needs attention:

```python
results = get_scan_results(
    task_id=task_id,
    page=0,
    schema_profile="full",  # Include solutions
    filters={"severity": ">=3"}
)
```

### Strategy 5: Statistics Collection

Minimal data for counting:

```python
results = get_scan_results(
    task_id=task_id,
    page=0,
    schema_profile="minimal"
)
# Parse and count by severity/host
```

## Processing Results

### JSON-NL Format

Results are returned as newline-delimited JSON:

```json
{"type": "schema", "profile": "brief", "fields": [...]}
{"type": "scan_metadata", "task_id": "...", ...}
{"type": "vulnerability", "host": "...", "severity": 4, ...}
{"type": "vulnerability", "host": "...", "severity": 3, ...}
{"type": "pagination", "page": 0, "total_lines": 65}
```

### Parsing Pattern

```python
import json

lines = results.strip().split('\n')
vulns = []
metadata = None

for line in lines:
    obj = json.loads(line)
    if obj["type"] == "vulnerability":
        vulns.append(obj)
    elif obj["type"] == "scan_metadata":
        metadata = obj
```

### Top 5 Extraction

```python
# Sort by severity (desc) then CVSS (desc)
sorted_vulns = sorted(
    vulns,
    key=lambda x: (-x['severity'], -x.get('cvss_score', 0))
)
top5 = sorted_vulns[:5]
```

### Statistics Generation

```python
from collections import Counter

severity_counts = Counter(v['severity'] for v in vulns)
host_counts = Counter(v['host'] for v in vulns)

stats = {
    "total": len(vulns),
    "by_severity": {
        "critical": severity_counts.get(4, 0),
        "high": severity_counts.get(3, 0),
        "medium": severity_counts.get(2, 0),
        "low": severity_counts.get(1, 0),
        "info": severity_counts.get(0, 0)
    },
    "by_host": dict(host_counts)
}
```

## Refiltering Pattern

When user wants a different view of existing results:

```python
# Original: all results
all_results = get_scan_results(task_id, page=0, schema_profile="brief")

# User: "Show me only critical"
critical_results = get_scan_results(
    task_id,
    page=0,
    schema_profile="brief",
    filters={"severity": "4"}
)

# User: "Get full details for those"
critical_full = get_scan_results(
    task_id,
    page=0,
    schema_profile="full",
    filters={"severity": "4"}
)
```

## Tips

1. **Start with brief profile** - has enough detail for most analysis
2. **Use page=0 for processing** - easier than handling pagination
3. **Upgrade to full only when needed** - for solutions, detailed descriptions
4. **Filter server-side** - more efficient than filtering in code
5. **Combine severity + CVSS** - catches both flagged and scored issues
