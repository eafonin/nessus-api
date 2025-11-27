---
name: nessus-scanner
description: Use this skill for vulnerability scanning with the Nessus MCP Server. Handles scan submission, status monitoring, result filtering, and top vulnerability analysis with attack vector explanations.
---

# Nessus Scanner Skill

## Mission

Help users run vulnerability scans and analyze results effectively:

1. **Submit Scans** - Choose correct scan type (untrusted/authenticated/privileged)
2. **Monitor Progress** - Wait for completion, report status
3. **Filter Results** - Apply severity/CVSS/custom filters
4. **Analyze Top Vulnerabilities** - Extract top 5, explain attack vectors

## When to Use This Skill

Use this skill when user explicitly requests it OR mentions:
- Vulnerability scanning
- Security assessment
- Nessus scan
- Network scan for vulnerabilities
- Authenticated scan / credentialed scan

**Activation**: Explicit trigger preferred ("use nessus skill")

## Prerequisites

The Nessus MCP Server must be registered with Claude Code:

```bash
claude mcp add --transport http nessus-mcp http://localhost:8836/mcp
```

Tools available after registration:
- `run_untrusted_scan` - Network-only scan
- `run_authenticated_scan` - SSH authenticated scan
- `get_scan_status` - Check task status
- `get_scan_results` - Get paginated results
- `list_scanners` / `list_pools` / `get_pool_status` - Scanner management
- `get_queue_status` / `list_tasks` - Task management

## Operation Modes

### Mode 1: Quick Scan (Read Quick Ref)

**When**: User wants a simple scan with default options

**Process**:
1. Determine scan type needed (see Scan Selection below)
2. Submit scan with appropriate tool
3. Poll status until completed
4. Return summary with top 5 vulnerabilities

### Mode 2: Detailed Analysis (Read Quick Ref + Filtering)

**When**: User wants filtered results or specific analysis

**Process**:
1. Submit scan (or use existing task_id)
2. Wait for completion
3. Apply filters (severity, CVSS, etc.)
4. Analyze top vulnerabilities with attack vectors
5. Offer refiltering options

### Mode 3: Result Re-exploration

**When**: User has existing task_id, wants different view

**Process**:
1. Get results with new filters
2. Generate stats or focused analysis
3. Offer further refinement

### Mode 4: Historical Scan Search

**When**: User asks "have we scanned X before?" or "show me scans of this IP/network"

**Process**:
1. Use `list_tasks(target_filter="...")` with CIDR-aware matching
2. The filter intelligently matches:
   - Exact IP: `172.30.0.9` finds scans targeting that IP
   - IP in subnet: `172.30.0.9` finds scans targeting `172.30.0.0/24`
   - Subnet contains IP: `172.30.0.0/24` finds scans targeting `172.30.0.9`
   - Overlapping subnets: `10.0.0.0/24` finds scans targeting `10.0.0.0/8`
3. Present matching scans with targets, names, dates, and status
4. Offer to get results from a specific historical scan

## Scan Type Selection

| Situation | Scan Type | Tool |
|-----------|-----------|------|
| External network assessment | `untrusted` | `run_untrusted_scan` |
| Can't provide credentials | `untrusted` | `run_untrusted_scan` |
| Have SSH access to targets | `authenticated` | `run_authenticated_scan` |
| Need package/config checks | `authenticated` | `run_authenticated_scan` |
| Full system audit | `authenticated_privileged` | `run_authenticated_scan` |
| Compliance scanning | `authenticated_privileged` | `run_authenticated_scan` |
| Need root-level checks | `authenticated_privileged` | `run_authenticated_scan` |

**Decision Tree**:
```
Do you have SSH credentials for targets?
├─ No → run_untrusted_scan (network-only)
└─ Yes → Do you need root/sudo access?
         ├─ No → run_authenticated_scan (scan_type="authenticated")
         └─ Yes → run_authenticated_scan (scan_type="authenticated_privileged")
                  └─ Configure: elevate_privileges_with="sudo"
```

## Standard Workflows

### Workflow 1: Simple Network Scan

```
1. Call run_untrusted_scan(targets="...", name="...")
2. Store task_id from response
3. Poll get_scan_status(task_id) every 30s until status="completed"
4. Call get_scan_results(task_id, page=0, schema_profile="brief")
5. Parse JSON-NL, extract top 5 by severity
6. Present summary to user
```

### Workflow 2: Authenticated Scan

```
1. Confirm credentials with user (username, password)
2. Determine if privileged access needed
3. Call run_authenticated_scan(...) with appropriate scan_type
4. Wait for completion (check authentication_status in response)
5. If auth_status="failed", provide troubleshooting
6. Get and filter results
```

### Workflow 3: Result Analysis (Top 5)

```
1. Get full results: get_scan_results(task_id, page=0, schema_profile="full")
2. Parse JSON-NL lines
3. Filter to severity >= High (3+) or CVSS >= 7.0
4. Sort by: severity DESC, cvss_score DESC
5. Take top 5
6. For each vulnerability:
   - Extract: plugin_name, severity, cvss_score, cve, description
   - Identify vulnerability type (RCE, SQLi, XSS, etc.)
   - Explain potential attack vector based on type
7. Present formatted summary
```

### Workflow 4: Statistics Overview

```
1. Get results with schema_profile="summary" or "brief"
2. Count by severity level
3. Count by host
4. Identify hosts with critical/high findings
5. Present breakdown table
```

### Workflow 5: Historical Scan Search

```
1. User asks: "Have we scanned 172.30.0.9 before?" or "Show me scans of 10.0.0.0/8"
2. Call list_tasks(target_filter="172.30.0.9", limit=20)
3. CIDR-aware matching finds:
   - Exact matches (172.30.0.9)
   - Scans of containing subnets (172.30.0.0/24)
   - Any overlapping networks
4. Present results table:
   | Task ID | Name | Targets | Status | Date |
5. Offer: "Would you like to see results from any of these scans?"
```

**Example Response:**
```
Found 5 historical scans covering 172.30.0.9:

| # | Date       | Scan Name                    | Status    | Vulns |
|---|------------|------------------------------|-----------|-------|
| 1 | 2025-11-27 | Auth Scan - scan-target      | completed | 42    |
| 2 | 2025-11-27 | Priv Scan - RETRY            | completed | 42    |
| 3 | 2025-11-26 | MCP_E2E_Auth_123551          | completed | 40    |

Would you like me to show detailed results from any of these?
```

## Result Filtering

### Filter Syntax

Filters are passed as dict to `get_scan_results`:

```python
# By severity (0=info, 1=low, 2=medium, 3=high, 4=critical)
filters={"severity": "4"}           # Critical only
filters={"severity": ">=3"}         # High and Critical

# By CVSS score
filters={"cvss_score": ">7.0"}      # CVSS > 7.0
filters={"cvss_score": ">=9.0"}     # Critical CVSS

# By host
filters={"host": "192.168.1.100"}   # Specific host

# Combined
filters={"severity": ">=3", "cvss_score": ">7.0"}
```

### Schema Profiles

| Profile | Fields | Use Case |
|---------|--------|----------|
| `minimal` | host, plugin_id, severity | Quick counts |
| `summary` | + plugin_name, port | Overview |
| `brief` | + cvss_score, cve, synopsis | Standard analysis |
| `full` | + description, solution, see_also | Deep dive |

### Pagination

- `page=0` - Return ALL results (use for full analysis)
- `page=1, page_size=40` - First page of 40 items
- Check `pagination` line in response for `next_page`

## Top 5 Vulnerability Analysis

When presenting top vulnerabilities, include:

1. **Rank & Severity** - "#1 CRITICAL" or "#2 HIGH"
2. **Plugin Name** - What was detected
3. **Affected Host:Port** - Where it exists
4. **CVSS Score** - Numerical severity (if available)
5. **CVE** - Reference ID (if available)
6. **Attack Vector** - Brief explanation of how this could be exploited

**Attack Vector Explanation Approach**:
- RCE vulnerabilities: "Attacker can execute arbitrary code remotely"
- Authentication bypass: "Attacker can gain access without credentials"
- Information disclosure: "Sensitive data may be exposed to attackers"
- Privilege escalation: "Low-privilege attacker can gain elevated access"
- Default credentials: "System uses known default passwords"

Keep explanations concise (1-2 sentences). Let context guide depth.

## Error Handling

### Scan Submission Errors

| Error | Cause | Action |
|-------|-------|--------|
| "Scanner not found" | Pool/instance doesn't exist | Use `list_pools()` to find valid pools |
| "Conflict" (409) | Idempotency key reused | Generate new key or use existing task_id |

### Authentication Failures

If `authentication_status="failed"`:
1. Report to user: "Credentials were rejected by target"
2. Suggest: Verify username/password, check SSH access, verify firewall rules
3. Offer: Retry with corrected credentials or fall back to untrusted scan

### Scan Timeout

If `status="timeout"`:
1. Report: "Scan exceeded 24-hour limit"
2. Suggest: Reduce target scope, check network connectivity

## Quick Reference

### Scan Submission

```python
# Network-only scan
run_untrusted_scan(
    targets="192.168.1.0/24",
    name="Network Discovery"
)

# SSH authenticated scan
run_authenticated_scan(
    targets="192.168.1.100",
    name="Server Audit",
    scan_type="authenticated",
    ssh_username="scanuser",
    ssh_password="password123"
)

# Privileged scan with sudo
run_authenticated_scan(
    targets="192.168.1.100",
    name="Full Audit",
    scan_type="authenticated_privileged",
    ssh_username="scanuser",
    ssh_password="password123",
    elevate_privileges_with="sudo",
    escalation_password="password123"
)
```

### Status Check

```python
get_scan_status(task_id="nessus-scanner1-...")
# Returns: status, progress, authentication_status, results_summary
```

### Get Results

```python
# All results, full detail
get_scan_results(task_id="...", page=0, schema_profile="full")

# Filtered to critical
get_scan_results(task_id="...", page=0, filters={"severity": "4"})

# Paginated
get_scan_results(task_id="...", page=1, page_size=50)
```

## Response Patterns

### After Scan Submission

> "Scan submitted successfully.
> - Task ID: `{task_id}`
> - Status: queued (position {queue_position})
> - Estimated wait: ~{estimated_wait_minutes} minutes
>
> I'll monitor progress and notify you when complete."

### After Completion

> "Scan completed.
> - Hosts scanned: {hosts}
> - Total vulnerabilities: {total}
> - Breakdown: {critical} Critical, {high} High, {medium} Medium, {low} Low
>
> **Top 5 Vulnerabilities:**
> 1. **CRITICAL** - {name} on {host}:{port} (CVSS {score})
>    Attack vector: {explanation}
> ...
>
> Would you like me to filter by severity, get detailed info on specific findings, or generate a full report?"

## See Also

- [Quick Reference](./references/QUICK-REF.md) - Tool syntax details
- [Scan Selection Guide](./references/SCAN-SELECTION.md) - Detailed scan type guidance
- [Filtering Guide](./references/FILTERING.md) - Advanced filter strategies
