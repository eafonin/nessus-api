# Nessus MCP Server - API Reference

> Complete reference for all MCP tools and their parameters

---

## MCP Tools Overview

| Tool | Description | Phase |
|------|-------------|-------|
| `run_untrusted_scan` | Network-only vulnerability scan | Phase 1 |
| `run_authenticated_scan` | SSH-authenticated vulnerability scan | Phase 5 |
| `get_scan_status` | Get task status with validation results | Phase 1 |
| `get_scan_results` | Get paginated scan results | Phase 2 |
| `list_scanners` | List registered scanner instances | Phase 4 |
| `list_pools` | List available scanner pools | Phase 4 |
| `get_pool_status` | Get pool capacity and utilization | Phase 4 |
| `get_queue_status` | Get Redis queue status | Phase 1 |
| `list_tasks` | List recent tasks | Phase 1 |

---

## Scan Tools

### run_untrusted_scan

Run a network-only vulnerability scan without credentials.

```python
run_untrusted_scan(
    targets: str,                    # Required: IP addresses or CIDR ranges
    name: str,                       # Required: Scan name
    description: str = "",           # Optional: Scan description
    schema_profile: str = "brief",   # Optional: Result detail level
    idempotency_key: str = None,     # Optional: Duplicate prevention key
    scanner_pool: str = None,        # Optional: Pool name (default: "nessus")
    scanner_instance: str = None,    # Optional: Specific scanner instance
) -> dict
```

**Returns:**
```json
{
    "task_id": "nessus-scanner1-20251126-abc123",
    "trace_id": "uuid-v4",
    "status": "queued",
    "scanner_pool": "nessus",
    "scanner_instance": "scanner1",
    "scanner_url": "https://172.30.0.3:8834",
    "queue_position": 1,
    "estimated_wait_minutes": 15,
    "message": "Scan enqueued successfully. Worker will process asynchronously."
}
```

**Example:**
```python
result = await run_untrusted_scan(
    targets="192.168.1.0/24",
    name="Network Discovery",
    description="Weekly network scan"
)
```

---

### run_authenticated_scan

Run an SSH-authenticated vulnerability scan (Phase 5).

Authenticated scans log into target systems via SSH to perform deeper vulnerability assessment than unauthenticated network scans. Detects 10x more vulnerabilities by checking installed packages, configurations, and permissions.

```python
run_authenticated_scan(
    targets: str,                         # Required: IP addresses or hostnames
    name: str,                            # Required: Scan name
    scan_type: str,                       # Required: "authenticated" or "authenticated_privileged"
    ssh_username: str,                    # Required: SSH username
    ssh_password: str,                    # Required: SSH password
    description: str = "",                # Optional: Scan description
    schema_profile: str = "brief",        # Optional: Result detail level
    elevate_privileges_with: str = "Nothing",  # Optional: "Nothing", "sudo", "su"
    escalation_account: str = "",         # Optional: Account to escalate to (default: root)
    escalation_password: str = "",        # Optional: Password for privilege escalation
    idempotency_key: str = None,          # Optional: Duplicate prevention key
    scanner_pool: str = None,             # Optional: Pool name
    scanner_instance: str = None,         # Optional: Specific scanner instance
) -> dict
```

**Scan Types:**

| Type | Description | Credentials | Use Case |
|------|-------------|-------------|----------|
| `authenticated` | SSH login to target | username/password | Internal vulnerability assessment |
| `authenticated_privileged` | SSH + sudo/root escalation | username/password + escalation | Full system audit, compliance |

**Escalation Methods:**
- `Nothing` - No privilege escalation (for `authenticated` type)
- `sudo` - Most common, sudo to root
- `su` - Switch user
- `su+sudo` - Combined su then sudo
- `pbrun` - PowerBroker
- `dzdo` - Centrify DirectAuthorize

**Returns:**
```json
{
    "task_id": "nessus-scanner1-20251126-def456",
    "trace_id": "uuid-v4",
    "status": "queued",
    "scan_type": "authenticated",
    "scanner_pool": "nessus",
    "scanner_instance": "scanner1",
    "scanner_url": "https://172.30.0.3:8834",
    "queue_position": 1,
    "estimated_wait_minutes": 15,
    "message": "Authenticated scan enqueued successfully. Worker will process asynchronously."
}
```

**Example 1: Authenticated scan (SSH only):**
```python
result = await run_authenticated_scan(
    targets="172.32.0.215",
    name="Internal Server Audit",
    scan_type="authenticated",
    ssh_username="scanuser",
    ssh_password="password123"
)
```

**Example 2: Authenticated privileged scan (SSH + sudo with password):**
```python
result = await run_authenticated_scan(
    targets="172.32.0.209",
    name="Full System Audit",
    scan_type="authenticated_privileged",
    ssh_username="scanuser",
    ssh_password="password123",
    elevate_privileges_with="sudo",
    escalation_password="password123"  # sudo password
)
```

**Example 3: Authenticated privileged scan (SSH + sudo NOPASSWD):**
```python
result = await run_authenticated_scan(
    targets="172.32.0.209",
    name="Full System Audit (NOPASSWD)",
    scan_type="authenticated_privileged",
    ssh_username="scanuser",
    ssh_password="password123",
    elevate_privileges_with="sudo"
    # No escalation_password needed for NOPASSWD
)
```

**Validation Errors:**
```json
// Invalid scan_type
{"error": "Invalid scan_type: xyz. Must be one of: ('authenticated', 'authenticated_privileged')"}

// Missing escalation for privileged scan
{"error": "authenticated_privileged scan requires elevate_privileges_with (sudo/su)"}
```

---

## Status & Results Tools

### get_scan_status

Get current status of a scan task with validation results.

```python
get_scan_status(task_id: str) -> dict
```

**Returns (running):**
```json
{
    "task_id": "nessus-scanner1-20251126-abc123",
    "trace_id": "uuid-v4",
    "status": "running",
    "scan_type": "authenticated",
    "scanner_pool": "nessus",
    "scanner_instance": "scanner1",
    "targets": "192.168.1.100",
    "name": "Server Audit",
    "nessus_scan_id": 123,
    "created_at": "2025-11-26T10:00:00Z",
    "started_at": "2025-11-26T10:00:05Z",
    "progress": 45,
    "authentication_status": null
}
```

**Returns (completed):**
```json
{
    "task_id": "nessus-scanner1-20251126-abc123",
    "trace_id": "uuid-v4",
    "status": "completed",
    "scan_type": "authenticated",
    "scanner_pool": "nessus",
    "scanner_instance": "scanner1",
    "targets": "192.168.1.100",
    "name": "Server Audit",
    "nessus_scan_id": 123,
    "created_at": "2025-11-26T10:00:00Z",
    "started_at": "2025-11-26T10:00:05Z",
    "completed_at": "2025-11-26T10:08:30Z",
    "authentication_status": "success",
    "validation_warnings": [],
    "results_summary": {
        "hosts_scanned": 1,
        "total_vulnerabilities": 65,
        "severity_breakdown": {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 2,
            "info": 60
        },
        "file_size_kb": 245.3,
        "auth_plugins_found": 5
    }
}
```

**Authentication Status Values:**
| Status | Description |
|--------|-------------|
| `success` | Credentials worked, full authenticated scan |
| `partial` | Logged in but limited access (need sudo) |
| `failed` | Credentials rejected |
| `not_applicable` | Untrusted scan (no credentials) |

**Troubleshooting (auth failed):**
```json
{
    "status": "completed",
    "authentication_status": "failed",
    "troubleshooting": {
        "likely_cause": "Credentials rejected or inaccessible target",
        "next_steps": [
            "Verify credentials in scanner configuration",
            "Check target allows SSH/WinRM from scanner IP",
            "Verify target firewall rules",
            "Check credential permissions on target",
            "Review scan logs for specific error"
        ]
    }
}
```

---

### get_scan_results

Get paginated scan results in JSON-NL format.

```python
get_scan_results(
    task_id: str,                        # Required: Task ID
    page: int = 1,                       # Optional: Page number (0 for all)
    page_size: int = 40,                 # Optional: Lines per page (10-100)
    schema_profile: str = "brief",       # Optional: minimal|summary|brief|full
    custom_fields: List[str] = None,     # Optional: Custom field selection
    filters: Dict[str, Any] = None,      # Optional: Filter criteria
) -> str  # JSON-NL string
```

**Example with filters:**
```python
results = await get_scan_results(
    task_id="nessus-scanner1-20251126-abc123",
    page=1,
    page_size=50,
    filters={"severity": "4"}  # Critical only
)
```

---

## Authentication Detection

### Key Plugins

| Plugin ID | Name | Indicates |
|-----------|------|-----------|
| 141118 | Valid Credentials Provided | Authentication SUCCESS |
| 110385 | Insufficient Privilege | Need sudo escalation |
| 19506 | Nessus Scan Information | Contains "Credentialed checks: yes/no" |
| 22869 | Software Enumeration (SSH) | Auth success - can list packages |
| 97993 | OS Identification over SSH | Auth success - can identify OS |

### hosts_summary.credential Field

In scan results, each host has a `credential` field:
```json
{
    "hostname": "172.32.0.215",
    "credential": "true",   // "true" = auth success
    "critical": 0,
    "high": 1
}
```

---

## Task Management Tools

### list_tasks

List recent scan tasks with optional filtering. Supports CIDR-aware target search.

```python
list_tasks(
    limit: int = 10,                    # Optional: Max tasks to return
    status_filter: str = None,          # Optional: queued|running|completed|failed|timeout
    scanner_pool: str = None,           # Optional: Filter by pool name
    target_filter: str = None,          # Optional: CIDR-aware target search (NEW)
) -> dict
```

**Target Filter (CIDR-aware matching):**

The `target_filter` parameter supports intelligent IP/CIDR matching:

| Query | Stored Target | Match? | Logic |
|-------|---------------|--------|-------|
| `10.0.0.5` | `10.0.0.5` | Yes | Exact IP match |
| `10.0.0.5` | `10.0.0.0/24` | Yes | IP within subnet |
| `10.0.0.0/24` | `10.0.0.5` | Yes | Subnet contains IP |
| `10.0.0.0/24` | `10.0.0.0/16` | Yes | Overlapping subnets |
| `192.168.1.1` | `10.0.0.0/8` | No | No overlap |

**Returns:**
```json
{
    "tasks": [
        {
            "task_id": "ne_scan_20251127_132509_ff257655",
            "trace_id": "uuid-v4",
            "status": "completed",
            "scan_type": "authenticated_privileged",
            "scanner_pool": "nessus",
            "scanner_type": "nessus",
            "scanner_instance": "scanner2",
            "targets": "172.30.0.9",
            "name": "Privileged Scan - Server Audit",
            "created_at": "2025-11-27T13:25:09Z",
            "started_at": "2025-11-27T13:25:11Z",
            "completed_at": "2025-11-27T13:28:44Z",
            "nessus_scan_id": 63
        }
    ],
    "total": 1
}
```

**Examples:**

```python
# List all recent tasks
list_tasks(limit=20)

# Find scans of a specific IP
list_tasks(target_filter="172.30.0.9")

# Find scans covering a subnet
list_tasks(target_filter="172.30.0.0/24")

# Combined filters: completed scans of a target
list_tasks(
    target_filter="10.0.0.0/8",
    status_filter="completed",
    limit=50
)
```

---

## Error Handling

### Common Errors

**Scanner not found:**
```json
{
    "error": "Scanner not found",
    "message": "No scanner available in pool 'nessus_dmz'",
    "status_code": 404
}
```

**Idempotency conflict:**
```json
{
    "error": "Conflict",
    "message": "Idempotency key 'abc123' already used with different parameters",
    "status_code": 409
}
```

**Invalid credentials:**
```json
{
    "error": "SSH credential missing required field: password"
}
```

---

## Security Considerations

### Credential Handling

- Credentials are passed through Redis queue in task payload
- Redis is internal (Docker network only, not exposed externally)
- Credentials are ephemeral (per-scan, not stored permanently)
- Passwords are sanitized from all logs

### Best Practices

1. Use dedicated scan service accounts with minimal privileges
2. For privileged scans, prefer `sudo NOPASSWD` for specific commands
3. Rotate credentials regularly
4. Monitor `authentication_status` for failed auth attempts
5. Use idempotency keys to prevent duplicate scans

---

## Test Users Reference

### Available on 172.32.0.209 (Docker Host)

| Username | Password | Sudo Config | Use Case |
|----------|----------|-------------|----------|
| `testauth_sudo_pass` | `TestPass123!` | sudo with password | Test privileged with escalation_password |
| `testauth_sudo_nopass` | `TestPass123!` | sudo NOPASSWD | Test privileged without escalation_password |
| `testauth_nosudo` | `TestPass123!` | No sudo | Test authenticated (non-privileged) |
| `nessus` | `nessus` | sudo with password | Existing scanner user |

### Available on 172.32.0.215 (External Host)

| Username | Password | Access |
|----------|----------|--------|
| `randy` | `randylovesgoldfish1998` | Full root SSH access |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-07 | Initial API with untrusted scans |
| 2.0 | 2025-11-25 | Phase 4: Scanner pools, validation |
| 3.0 | 2025-11-26 | Phase 5: Authenticated scans |
| 3.1 | 2025-11-27 | Historical scan search: CIDR-aware `target_filter` in `list_tasks`, exposed `targets`/`name` fields |
