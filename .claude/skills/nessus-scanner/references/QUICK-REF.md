# Nessus Scanner - Quick Reference

> Tool syntax and parameter reference

## Scan Submission Tools

### run_untrusted_scan

Network-only vulnerability scan (no credentials).

```python
run_untrusted_scan(
    targets: str,                    # Required: IPs or CIDR (e.g., "192.168.1.0/24")
    name: str,                       # Required: Scan name
    description: str = "",           # Optional: Description
    schema_profile: str = "brief",   # Optional: minimal|summary|brief|full
    idempotency_key: str = None,     # Optional: Duplicate prevention
    scanner_pool: str = None,        # Optional: Pool name (default: "nessus")
    scanner_instance: str = None,    # Optional: Specific scanner
)
```

**Returns:**
```json
{
    "task_id": "nessus-scanner1-20251126-abc123",
    "trace_id": "uuid",
    "status": "queued",
    "scanner_pool": "nessus",
    "scanner_instance": "scanner1",
    "queue_position": 1,
    "estimated_wait_minutes": 15
}
```

### run_authenticated_scan

SSH authenticated scan with optional privilege escalation.

```python
run_authenticated_scan(
    targets: str,                         # Required: IPs or hostnames
    name: str,                            # Required: Scan name
    scan_type: str,                       # Required: "authenticated" | "authenticated_privileged"
    ssh_username: str,                    # Required: SSH username
    ssh_password: str,                    # Required: SSH password
    description: str = "",                # Optional: Description
    schema_profile: str = "brief",        # Optional: Result detail level
    elevate_privileges_with: str = "Nothing",  # Optional: "Nothing"|"sudo"|"su"
    escalation_account: str = "",         # Optional: Target account (default: root)
    escalation_password: str = "",        # Optional: sudo/su password
    idempotency_key: str = None,          # Optional: Duplicate prevention
    scanner_pool: str = None,             # Optional: Pool name
    scanner_instance: str = None,         # Optional: Specific scanner
)
```

**Returns:** Same as `run_untrusted_scan` plus `scan_type` field.

## Status & Results Tools

### get_scan_status

```python
get_scan_status(task_id: str)
```

**Returns (running):**
```json
{
    "task_id": "...",
    "status": "running",
    "targets": "192.168.1.100",
    "name": "Server Audit",
    "progress": 45,
    "scan_type": "authenticated",
    "authentication_status": null
}
```

**Returns (completed):**
```json
{
    "task_id": "...",
    "status": "completed",
    "targets": "192.168.1.100",
    "name": "Server Audit",
    "authentication_status": "success",
    "results_summary": {
        "hosts_scanned": 1,
        "total_vulnerabilities": 65,
        "severity_breakdown": {
            "critical": 0, "high": 1, "medium": 2, "low": 2, "info": 60
        }
    }
}
```

**Status values:** `queued`, `running`, `completed`, `failed`, `timeout`

**Authentication status:** `success`, `partial`, `failed`, `not_applicable`

### get_scan_results

```python
get_scan_results(
    task_id: str,                        # Required: Task ID
    page: int = 1,                       # Optional: Page number (0 = all)
    page_size: int = 40,                 # Optional: Items per page (10-100)
    schema_profile: str = "brief",       # Optional: Field selection
    custom_fields: List[str] = None,     # Optional: Custom field list
    filters: Dict[str, Any] = None,      # Optional: Filter criteria
)
```

**Returns:** JSON-NL string with lines:
1. `{"type": "schema", ...}` - Field definitions
2. `{"type": "scan_metadata", ...}` - Scan info
3. `{"type": "vulnerability", ...}` - One per finding (repeated)
4. `{"type": "pagination", ...}` - Page info

## Management Tools

### list_scanners

```python
list_scanners(scanner_pool: str = None)
```

Returns scanner instances with load info.

### list_pools

```python
list_pools()
```

Returns available pools and default pool.

### get_pool_status

```python
get_pool_status(scanner_pool: str = None)
```

Returns pool capacity, utilization, per-scanner breakdown.

### get_queue_status

```python
get_queue_status(scanner_pool: str = None)
```

Returns queue depth, DLQ size, next tasks.

### list_tasks

```python
list_tasks(
    limit: int = 10,
    status_filter: str = None,           # queued|running|completed|failed|timeout
    scanner_pool: str = None,            # Filter by pool name
    target_filter: str = None,           # CIDR-aware target search (NEW)
)
```

Returns recent tasks with optional filtering. The `target_filter` supports CIDR-aware matching:

| Query | Stored Target | Match? |
|-------|---------------|--------|
| `10.0.0.5` | `10.0.0.0/24` | Yes (IP in subnet) |
| `10.0.0.0/24` | `10.0.0.5` | Yes (subnet contains IP) |
| `10.0.0.0/24` | `10.0.0.0/16` | Yes (overlapping) |

**Returns:**
```json
{
    "tasks": [{
        "task_id": "...",
        "status": "completed",
        "targets": "172.30.0.9",
        "name": "Server Audit",
        "scan_type": "authenticated",
        "created_at": "2025-11-27T13:25:09Z"
    }],
    "total": 1
}
```

## Schema Profiles

| Profile | Fields Included |
|---------|-----------------|
| `minimal` | host, plugin_id, severity |
| `summary` | + plugin_name, port |
| `brief` | + cvss_score, cve, synopsis |
| `full` | + description, solution, see_also |

## Filter Syntax

```python
# Severity (0=info, 1=low, 2=medium, 3=high, 4=critical)
filters={"severity": "4"}           # Exact match
filters={"severity": ">=3"}         # High and above

# CVSS score
filters={"cvss_score": ">7.0"}
filters={"cvss_score": ">=9.0"}

# Host
filters={"host": "192.168.1.100"}

# Combined
filters={"severity": ">=3", "cvss_score": ">7.0"}
```

## Common Patterns

### Wait for Completion

```python
while True:
    status = get_scan_status(task_id)
    if status["status"] in ["completed", "failed", "timeout"]:
        break
    await asyncio.sleep(30)
```

### Get All Critical Vulns

```python
results = get_scan_results(
    task_id=task_id,
    page=0,  # All results
    schema_profile="brief",
    filters={"severity": "4"}
)
```

### Top 5 by Severity

```python
results = get_scan_results(task_id=task_id, page=0, schema_profile="full")
vulns = [json.loads(line) for line in results.split('\n')
         if '"type": "vulnerability"' in line]
top5 = sorted(vulns, key=lambda x: (-x['severity'], -x.get('cvss_score', 0)))[:5]
```

### Search Historical Scans by Target

```python
# Find all scans of a specific IP
scans = list_tasks(target_filter="172.30.0.9", limit=20)

# Find scans covering a subnet (CIDR-aware)
scans = list_tasks(target_filter="10.0.0.0/24", limit=50)

# Combined: completed scans of a target
scans = list_tasks(
    target_filter="192.168.1.0/24",
    status_filter="completed",
    limit=100
)

# Results include targets and name for easy identification
for task in scans["tasks"]:
    print(f"{task['name']}: {task['targets']} ({task['status']})")
```
