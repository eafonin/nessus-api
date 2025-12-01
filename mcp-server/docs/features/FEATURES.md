# Nessus MCP Server - Feature Documentation

> **[↑ Features Index](README.md)** | **[Architecture →](ARCHITECTURE.md)** | **[Requirements →](REQUIREMENTS.md)**

## Overview

The Nessus MCP Server provides an MCP (Model Context Protocol) interface for vulnerability scanning using Tenable Nessus. It supports network-only and authenticated scanning with asynchronous queue-based processing.

---

## Feature Categories

| Category | Description |
|----------|-------------|
| [Scanning](#1-vulnerability-scanning) | Network and authenticated vulnerability scans |
| [Queue System](#2-queue-system) | Async task queue with Redis |
| [Results](#3-results-retrieval) | Schema-based result filtering |
| [Observability](#4-observability) | Logging, metrics, health checks |
| [Multi-Scanner](#5-multi-scanner-support) | Scanner pools and load balancing |
| [Operations](OPERATIONS.md) | Admin CLI, TTL housekeeping, circuit breaker |

---

## 1. Vulnerability Scanning

### 1.1 Network Scanning (Untrusted)

External attack surface scanning without authentication.

**MCP Tool**: `run_untrusted_scan()`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| targets | string | Yes | IP addresses or CIDR ranges |
| name | string | Yes | Scan name for identification |
| description | string | No | Optional description |
| schema_profile | string | No | Output schema (default: brief) |
| idempotency_key | string | No | Prevent duplicate scans |
| scanner_pool | string | No | Target scanner pool |
| scanner_instance | string | No | Specific scanner instance |

**Response**:
```json
{
  "task_id": "nessus_scanner1_1732..._abc123",
  "trace_id": "uuid-v4",
  "status": "queued",
  "scanner_pool": "nessus",
  "scanner_instance": "scanner1",
  "queue_position": 1,
  "estimated_wait_minutes": 15
}
```

### 1.2 Authenticated Scanning

SSH-based authenticated scanning for deeper vulnerability detection.

**MCP Tool**: `run_authenticated_scan()`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| targets | string | Yes | IP addresses or hostnames |
| name | string | Yes | Scan name |
| scan_type | string | Yes | `authenticated` or `authenticated_privileged` |
| ssh_username | string | Yes | SSH username |
| ssh_password | string | Yes | SSH password |
| elevate_privileges_with | string | No | `Nothing`, `sudo`, `su`, `su+sudo`, `pbrun`, `dzdo` |
| escalation_account | string | No | Account to escalate to (default: root) |
| escalation_password | string | No | Password for privilege escalation |

**Scan Types**:

| Type | Description | Use Case |
|------|-------------|----------|
| `untrusted` | Network-only, no authentication | External attack surface |
| `authenticated` | SSH login to target | Internal vulnerability assessment |
| `authenticated_privileged` | SSH + sudo/root escalation | Full system audit, compliance |

**Authentication Detection**:
- Plugin 141118: "Valid Credentials Provided" (confirms success)
- Plugin 110385: "Insufficient Privilege" (need escalation)
- Plugin 19506: "Credentialed checks: yes/no/partial"

### 1.3 Scan Lifecycle

```text
QUEUED → RUNNING → COMPLETED
                 ↘ FAILED
                 ↘ TIMEOUT (24h)
```

**State Transitions**:
- `QUEUED`: Task created, waiting in queue
- `RUNNING`: Worker processing, Nessus scanning
- `COMPLETED`: Scan finished, results available
- `FAILED`: Error occurred (auth failure, scanner error)
- `TIMEOUT`: 24-hour limit exceeded

---

## 2. Queue System

### 2.1 Redis Task Queue

Asynchronous FIFO queue for scan task processing.

**Architecture**:
- Queue key: `{pool}:queue` (e.g., `nessus:queue`)
- Dead Letter Queue: `{pool}:queue:dead`
- Blocking dequeue with BRPOP (no CPU spin)

**MCP Tool**: `get_queue_status()`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| scanner_pool | string | No | Pool name (default: nessus) |

**Response**:
```json
{
  "pool": "nessus",
  "queue_depth": 3,
  "dlq_size": 0,
  "next_tasks": [...],
  "timestamp": "2025-12-01T12:00:00Z"
}
```

### 2.2 Idempotency

Prevent duplicate scan submissions using idempotency keys.

**Behavior**:
- Same `idempotency_key` returns existing task_id
- Keys stored in Redis with TTL
- Useful for retry-safe submissions

### 2.3 Task Management

**MCP Tool**: `list_tasks()`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | int | No | Max tasks to return (default: 10) |
| status_filter | string | No | Filter by status |
| scanner_pool | string | No | Filter by pool |
| target_filter | string | No | Filter by target IP/CIDR |

**Target Filtering**:
- CIDR-aware matching
- Query IP within stored subnet
- Query subnet contains/overlaps stored targets

---

## 3. Results Retrieval

### 3.1 Schema Profiles

Predefined field selections for different use cases.

**MCP Tool**: `get_scan_results()`

| Profile | Fields | Size Reduction | Use Case |
|---------|--------|----------------|----------|
| `minimal` | 6 fields | ~80% | Quick triage |
| `summary` | 9 fields | ~60% | LLM analysis |
| `brief` | 11 fields | ~40% | Detailed review (DEFAULT) |
| `full` | All fields | 0% | Complete export |

**Minimal Fields**: host, plugin_id, severity, cve, cvss_score, exploit_available

**Summary Adds**: plugin_name, cvss3_base_score, synopsis

**Brief Adds**: description, solution

### 3.2 Filtering

Generic filtering engine for vulnerability results.

| Filter Type | Syntax | Example |
|-------------|--------|---------|
| String | Substring match | `"plugin_name": "SQL"` |
| Number | Operators | `"cvss_score": ">7.0"` |
| Boolean | Exact match | `"exploit_available": true` |
| List | Contains | `"cve": "CVE-2021"` |

**Logic**: All filters use AND (must all match).

### 3.3 Pagination

Handle large result sets with pagination.

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| page | 1 | 1-N, or 0 | Page number (0 = all) |
| page_size | 40 | 10-100 | Lines per page |

**Output Format**: JSON-NL (newline-delimited JSON)
- Line 1: Schema definition
- Line 2: Scan metadata
- Lines 3+: Vulnerabilities
- Last line: Pagination info

---

## 4. Observability

### 4.1 Structured Logging

JSON-formatted logs with trace ID propagation.

**Log Events**:
- `tool_invocation`: MCP tool called
- `task_created`: New task created
- `scan_enqueued`: Task added to queue
- `state_transition`: Task state changed
- `scan_progress`: Progress update (25%, 50%, 75%, 100%)
- `scan_completed`: Scan finished
- `authentication_status`: Auth success/failure

**Format**:
```json
{
  "timestamp": "2025-12-01T12:00:00.123456Z",
  "level": "info",
  "event": "scan_completed",
  "trace_id": "abc-123",
  "task_id": "nessus_scanner1_...",
  "authentication_status": "success",
  "hosts_scanned": 5,
  "total_vulnerabilities": 42
}
```

### 4.2 Prometheus Metrics

8 core metrics exposed at `/metrics`.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `nessus_scans_total` | Counter | scan_type, status | Total scans |
| `nessus_api_requests_total` | Counter | tool, status | API requests |
| `nessus_active_scans` | Gauge | - | Currently running |
| `nessus_scanner_instances` | Gauge | scanner_type, enabled | Scanner count |
| `nessus_queue_depth` | Gauge | queue | Queue depth |
| `nessus_dlq_size` | Gauge | - | Dead letter queue |
| `nessus_task_duration_seconds` | Histogram | - | Scan duration |
| `nessus_ttl_deletions_total` | Counter | - | TTL cleanups |

### 4.3 Health Checks

**Endpoint**: `/health`

**Checks**:
- Redis connectivity (PING)
- Filesystem writability
- Scanner availability

**Response**:
```json
{
  "status": "healthy",
  "redis_healthy": true,
  "filesystem_healthy": true
}
```

---

## 5. Multi-Scanner Support

### 5.1 Scanner Registry

YAML-based multi-instance scanner configuration.

**Configuration** (`config/scanners.yaml`):
```yaml
scanners:
  nessus:
    - instance_id: scanner1
      url: https://nessus1.local:8834
      username: ${NESSUS_USER}
      password: ${NESSUS_PASS}
      max_concurrent_scans: 2
      enabled: true
```

**Features**:
- Environment variable substitution
- Per-instance concurrent scan limits
- Enable/disable without removal
- SIGHUP hot-reload

### 5.2 Scanner Pools

Logical grouping of scanner instances.

**MCP Tool**: `list_pools()`

**Response**:
```json
{
  "pools": ["nessus", "nessus_dmz"],
  "default_pool": "nessus"
}
```

### 5.3 Load Balancing

Automatic scanner selection within pools.

**MCP Tool**: `list_scanners()`

**Response per scanner**:
```json
{
  "instance_id": "scanner1",
  "pool": "nessus",
  "url": "https://...",
  "enabled": true,
  "max_concurrent_scans": 2,
  "active_scans": 1,
  "available_capacity": 1,
  "utilization_pct": 50.0
}
```

**Selection Algorithm**: Least loaded scanner with available capacity.

### 5.4 Pool Status

Aggregate metrics per pool.

**MCP Tool**: `get_pool_status()`

**Response**:
```json
{
  "pool": "nessus",
  "total_scanners": 2,
  "total_capacity": 4,
  "total_active": 2,
  "available_capacity": 2,
  "utilization_pct": 50.0
}
```

---

## 6. Status & Monitoring

### 6.1 Scan Status

**MCP Tool**: `get_scan_status()`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| task_id | string | Yes | Task ID from scan submission |

**Response Fields**:

| Field | Description |
|-------|-------------|
| status | Current state (queued/running/completed/failed) |
| progress | 0-100 if running |
| authentication_status | success/failed/partial/not_applicable |
| validation_warnings | List of warnings |
| results_summary | Hosts scanned, vuln counts (if completed) |
| troubleshooting | Hints for failed auth |

### 6.2 Results Summary

Included in status for completed tasks:

```json
{
  "results_summary": {
    "hosts_scanned": 5,
    "total_vulnerabilities": 42,
    "severity_breakdown": {
      "critical": 2,
      "high": 8,
      "medium": 15,
      "low": 7,
      "info": 10
    },
    "file_size_kb": 256.5,
    "auth_plugins_found": 12
  }
}
```

### 6.3 Troubleshooting

Included when authentication fails:

```json
{
  "troubleshooting": {
    "likely_cause": "Credentials rejected or inaccessible target",
    "next_steps": [
      "Verify credentials in scanner configuration",
      "Check target allows SSH/WinRM from scanner IP",
      "Verify target firewall rules",
      "Check credential permissions on target"
    ]
  }
}
```

---

## MCP Tools Summary

| Tool | Description | Category |
|------|-------------|----------|
| `run_untrusted_scan` | Network-only vulnerability scan | Scanning |
| `run_authenticated_scan` | SSH-authenticated vulnerability scan | Scanning |
| `get_scan_status` | Get task status with progress | Status |
| `get_scan_results` | Retrieve filtered scan results | Results |
| `list_tasks` | List recent tasks with filtering | Status |
| `list_scanners` | List scanner instances with load | Multi-Scanner |
| `list_pools` | List available scanner pools | Multi-Scanner |
| `get_pool_status` | Get pool utilization metrics | Multi-Scanner |
| `get_queue_status` | Get queue depth and metrics | Queue |

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastmcp | 2.13.0.2 | MCP server framework |
| mcp | >=1.18.0 | MCP protocol |
| starlette | 0.49.1 | SSE transport (PINNED) |
| anyio | 4.6.2.post1 | Async support (PINNED) |
| uvicorn | 0.38.0 | ASGI server |
| httpx | >=0.27.0 | Async HTTP client |
| redis | >=5.0.0 | Task queue |
| structlog | 24.1.0 | Structured logging |
| prometheus-client | >=0.20.0 | Metrics |
| pyyaml | >=6.0.1 | Configuration |

---

*Generated: 2025-12-01*
*Source: Consolidated from Phase 0-6 documentation*
