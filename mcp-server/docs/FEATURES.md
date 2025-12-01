# Nessus MCP Server - Features

> **Last Updated**: 2025-12-01
> **Audience**: MCP consumers, LLM integrators, security engineers

---

## MCP Tool Reference

The server exposes 9 MCP tools for vulnerability scanning operations.

### Scan Submission Tools

#### `run_untrusted_scan`

Submit a network-only vulnerability scan (no credentials).

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `targets` | string | Yes | - | IP addresses or CIDR ranges |
| `name` | string | Yes | - | Scan name for identification |
| `description` | string | No | "" | Optional description |
| `schema_profile` | string | No | "brief" | Output schema (minimal\|summary\|brief\|full) |
| `idempotency_key` | string | No | null | Key for duplicate prevention |
| `scanner_pool` | string | No | "nessus" | Scanner pool to use |
| `scanner_instance` | string | No | null | Specific scanner instance |

**Returns**:

```json
{
  "task_id": "ne_scan_20251201_143022_a1b2c3d4",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "scanner_pool": "nessus",
  "scanner_instance": "scanner1",
  "scanner_url": "https://172.30.0.3:8834",
  "queue_position": 1,
  "estimated_wait_minutes": 15,
  "message": "Scan enqueued successfully..."
}
```

---

#### `run_authenticated_scan`

Submit an authenticated vulnerability scan with SSH credentials.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `targets` | string | Yes | - | IP addresses or hostnames |
| `name` | string | Yes | - | Scan name |
| `scan_type` | string | Yes | - | "authenticated" or "authenticated_privileged" |
| `ssh_username` | string | Yes | - | SSH username |
| `ssh_password` | string | Yes | - | SSH password |
| `description` | string | No | "" | Optional description |
| `schema_profile` | string | No | "brief" | Output schema |
| `elevate_privileges_with` | string | No | "Nothing" | "Nothing", "sudo", or "su" |
| `escalation_account` | string | No | "" | Account to escalate to |
| `escalation_password` | string | No | "" | Escalation password |
| `idempotency_key` | string | No | null | Duplicate prevention key |
| `scanner_pool` | string | No | "nessus" | Scanner pool |
| `scanner_instance` | string | No | null | Specific scanner |

**Scan Types**:

- `authenticated`: SSH login only (no privilege escalation)
- `authenticated_privileged`: SSH + sudo/su escalation

**Example (privileged scan)**:

```python
run_authenticated_scan(
    targets="172.32.0.209",
    name="Full System Audit",
    scan_type="authenticated_privileged",
    ssh_username="admin",
    ssh_password="password123",
    elevate_privileges_with="sudo",
    escalation_password="password123"
)
```

---

### Status & Results Tools

#### `get_scan_status`

Get current status of a scan task.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | Task ID from scan submission |

**Returns**:

```json
{
  "task_id": "ne_scan_20251201_143022_a1b2c3d4",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "scan_type": "untrusted",
  "scanner_pool": "nessus",
  "scanner_instance": "scanner1",
  "targets": "192.168.1.0/24",
  "name": "Network Scan",
  "nessus_scan_id": 42,
  "created_at": "2025-12-01T14:30:22Z",
  "started_at": "2025-12-01T14:30:25Z",
  "completed_at": "2025-12-01T14:45:33Z",
  "authentication_status": "not_applicable",
  "results_summary": {
    "hosts_scanned": 254,
    "total_vulnerabilities": 127,
    "severity_breakdown": {"critical": 3, "high": 12, "medium": 45, "low": 67},
    "file_size_kb": 2340.5
  }
}
```

**Status Values**:

| Status | Description |
|--------|-------------|
| `queued` | Waiting in Redis queue |
| `running` | Scan active on Nessus |
| `completed` | Finished, results available |
| `failed` | Error occurred |
| `timeout` | Exceeded 24h limit |

---

#### `get_scan_results`

Get scan results in paginated JSON-NL format.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | string | Yes | - | Task ID |
| `page` | int | No | 1 | Page number (0 = all data) |
| `page_size` | int | No | 40 | Results per page (10-100) |
| `schema_profile` | string | No | "brief" | Field profile |
| `custom_fields` | list | No | null | Custom field list |
| `filters` | dict | No | null | Filter criteria |

**Returns**: JSON-NL string (newline-delimited JSON)

```
{"type": "schema", "profile": "brief", "fields": [...], "filters_applied": {...}, "total_vulnerabilities": 127}
{"type": "scan_metadata", "scan_name": "Network Scan", ...}
{"type": "vulnerability", "host": "192.168.1.1", "plugin_id": 12345, "severity": "4", ...}
{"type": "vulnerability", "host": "192.168.1.2", "plugin_id": 67890, ...}
{"type": "pagination", "page": 1, "page_size": 40, "total_pages": 4, "has_next": true}
```

---

#### `list_tasks`

List recent tasks with optional filtering.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | int | No | 10 | Max tasks to return |
| `status_filter` | string | No | null | Filter by status |
| `scanner_pool` | string | No | null | Filter by pool |
| `target_filter` | string | No | null | Filter by target IP/CIDR |

**Target Filter**: CIDR-aware matching. Query "192.168.1.5" matches stored "192.168.1.0/24".

---

### Infrastructure Tools

#### `list_scanners`

List all registered scanner instances with load information.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scanner_pool` | string | No | Filter by pool |

**Returns**:

```json
{
  "scanners": [
    {
      "scanner_type": "nessus",
      "pool": "nessus",
      "instance_id": "scanner1",
      "instance_key": "nessus:scanner1",
      "name": "Nessus Scanner 1",
      "url": "https://172.30.0.3:8834",
      "enabled": true,
      "max_concurrent_scans": 2,
      "active_scans": 1,
      "available_capacity": 1,
      "utilization_pct": 50.0
    }
  ],
  "total": 2,
  "pools": ["nessus"]
}
```

---

#### `list_pools`

List all available scanner pools.

**Returns**:

```json
{
  "pools": ["nessus", "nessus_dmz"],
  "default_pool": "nessus"
}
```

---

#### `get_pool_status`

Get pool capacity and utilization.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `scanner_pool` | string | No | "nessus" | Pool name |

**Returns**:

```json
{
  "pool": "nessus",
  "scanner_type": "nessus",
  "total_scanners": 2,
  "total_capacity": 4,
  "total_active": 1,
  "available_capacity": 3,
  "utilization_pct": 25.0,
  "scanners": [...]
}
```

---

#### `get_queue_status`

Get Redis queue metrics for a pool.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `scanner_pool` | string | No | "nessus" | Pool name |

**Returns**:

```json
{
  "pool": "nessus",
  "queue_depth": 3,
  "dlq_size": 0,
  "next_tasks": [...],
  "timestamp": "2025-12-01T14:30:22Z"
}
```

---

## Schema Profiles

Predefined field sets for vulnerability output.

| Profile | Fields |
|---------|--------|
| `minimal` | host, plugin_id, severity, cve, cvss_score, exploit_available |
| `summary` | minimal + plugin_name, cvss3_base_score, synopsis |
| `brief` | summary + description, solution |
| `full` | All available fields (no filtering) |

**Mutual Exclusivity**: Cannot specify both `schema_profile` (non-default) and `custom_fields`.

---

## Filtering Syntax

Filters use AND logic (all must match).

### String Filters

Case-insensitive substring match:

```json
{"plugin_name": "ssh"}       // Contains "ssh"
{"cve": "CVE-2021"}          // Contains "CVE-2021"
```

### Numeric Filters

Comparison operators:

```json
{"cvss_score": ">7.0"}       // Greater than 7.0
{"cvss_score": ">=5.0"}      // Greater or equal
{"severity": "4"}            // Exact match (Critical)
```

### Boolean Filters

Exact match:

```json
{"exploit_available": true}
```

### List Filters

Any element contains substring:

```json
{"cve": "2021"}              // Any CVE contains "2021"
```

---

## Pagination

- `page=1` (default): First page of results
- `page=0`: Return ALL results (no pagination)
- `page_size`: 10-100, clamped automatically

Last line of JSON-NL includes pagination metadata:

```json
{
  "type": "pagination",
  "page": 1,
  "page_size": 40,
  "total_pages": 4,
  "has_next": true,
  "next_page": 2
}
```

---

## Authentication Detection

For authenticated scans, the system detects credential success via Nessus plugins.

**Detection Methods**:

1. **Plugin 19506** (Nessus Scan Information): Contains "Credentialed checks : yes|no|partial"
2. **Auth-Required Plugins**: Count of plugins that only work with valid credentials

**Status Values**:

| Status | Description |
|--------|-------------|
| `success` | Credentials accepted |
| `failed` | Credentials rejected |
| `partial` | Some hosts authenticated |
| `not_applicable` | Untrusted scan (no credentials) |

**Auth-Required Plugin IDs**:
- 20811: Windows Compliance Checks
- 21643: Windows Local Security Checks
- 12634: Unix/Linux Local Security Checks
- 22869: Installed Software Enumeration

---

## Idempotency

Prevent duplicate scans using idempotency keys.

**Usage**:

```python
run_untrusted_scan(
    targets="192.168.1.0/24",
    name="Daily Scan",
    idempotency_key="daily-scan-20251201"
)
```

**Behavior**:
- If key exists with matching parameters: Return existing task
- If key exists with different parameters: Return 409 Conflict
- If key doesn't exist: Create new task

**TTL**: 48 hours

---

## Queue Position and Wait Estimation

When a scan is queued:

```json
{
  "queue_position": 3,
  "estimated_wait_minutes": 45
}
```

**Wait Estimate**: `queue_position * 15 minutes` (average scan time)

---

## Error Responses

### Task Not Found

```json
{"error": "Task ne_scan_xxx not found"}
```

### Scan Not Completed

```json
{"error": "Scan not completed yet (status: running)"}
```

### Scanner Not Found

```json
{
  "error": "Scanner not found",
  "message": "No enabled scanners in pool 'nessus_dmz'",
  "status_code": 404
}
```

### Idempotency Conflict

```json
{
  "error": "Conflict",
  "message": "Idempotency key 'xxx' exists with different request parameters",
  "status_code": 409
}
```

---

## Use Case Examples

### Basic Network Scan

```python
# Submit scan
result = run_untrusted_scan(
    targets="192.168.1.0/24",
    name="Network Discovery"
)
task_id = result["task_id"]

# Poll until complete
while True:
    status = get_scan_status(task_id)
    if status["status"] in ["completed", "failed", "timeout"]:
        break
    time.sleep(30)

# Get critical findings
results = get_scan_results(
    task_id=task_id,
    filters={"severity": "4"}  # Critical only
)
```

### Authenticated Linux Audit

```python
result = run_authenticated_scan(
    targets="172.32.0.215",
    name="Linux Server Audit",
    scan_type="authenticated_privileged",
    ssh_username="admin",
    ssh_password="secretpass",
    elevate_privileges_with="sudo",
    escalation_password="secretpass"
)

# Check authentication status after completion
status = get_scan_status(result["task_id"])
print(f"Auth status: {status['authentication_status']}")
```

### Filtered Results with Custom Fields

```python
results = get_scan_results(
    task_id="ne_scan_xxx",
    custom_fields=["host", "cve", "cvss_score", "exploit_available"],
    filters={
        "cvss_score": ">=7.0",
        "exploit_available": true
    },
    page=0  # Get all matching
)
```

---

## Limitations

1. **Single Nessus Vendor**: Currently only supports Nessus scanners
2. **SSH Only**: Authenticated scans use SSH (no WinRM/SNMP)
3. **AND Filter Logic**: No OR conditions in filters
4. **24h Timeout**: Scans exceeding 24 hours are stopped
5. **File-Based Storage**: Results stored on filesystem (no database)

---

## Cross-References

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: System design and data flow
- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Configuration and operations
- **[REQUIREMENTS.md](REQUIREMENTS.md)**: Requirements traceability

---

*Features document generated from source code analysis*
