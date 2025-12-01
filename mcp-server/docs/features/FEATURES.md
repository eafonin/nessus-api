# Nessus MCP Server - Features & Capabilities

> Consolidated feature reference for the Nessus MCP Server
> Version: 1.0 | Last Updated: 2025-12-01

---

## Quick Navigation

- [1. MCP Tools (API)](#1-mcp-tools-api)
- [2. Scanner Integration](#2-scanner-integration)
- [3. Queue & Task Management](#3-queue--task-management)
- [4. Results Processing](#4-results-processing)
- [5. Observability](#5-observability)
- [6. Production Features](#6-production-features)
- [7. Administration](#7-administration)

---

## 1. MCP Tools (API)

### 1.1 Scan Submission Tools

#### run_untrusted_scan

Network-only vulnerability scan without credentials.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `targets` | string | Yes | - | IP addresses or CIDR ranges |
| `name` | string | Yes | - | Scan name for identification |
| `description` | string | No | "" | Optional scan description |
| `schema_profile` | string | No | "brief" | Output schema (minimal\|summary\|brief\|full) |
| `idempotency_key` | string | No | null | Key for idempotent retries |
| `scanner_pool` | string | No | "nessus" | Scanner pool for routing |
| `scanner_instance` | string | No | null | Specific scanner instance |

**Response:**
```json
{
  "task_id": "ne_prod_20251201_120000_abc123",
  "trace_id": "uuid",
  "status": "queued",
  "scanner_pool": "nessus",
  "scanner_instance": "scanner1",
  "queue_position": 1,
  "estimated_wait_minutes": 15,
  "message": "Scan enqueued successfully"
}
```

---

#### run_authenticated_scan

SSH-authenticated vulnerability scan with credential injection.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `targets` | string | Yes | - | IP addresses or hostnames |
| `name` | string | Yes | - | Scan name |
| `scan_type` | string | Yes | - | "authenticated" or "authenticated_privileged" |
| `ssh_username` | string | Yes | - | SSH username |
| `ssh_password` | string | Yes | - | SSH password |
| `elevate_privileges_with` | string | No | "Nothing" | "sudo", "su", "su+sudo", "pbrun", "dzdo" |
| `escalation_account` | string | No | "root" | Account to escalate to |
| `escalation_password` | string | No | "" | Password for escalation |
| `schema_profile` | string | No | "brief" | Output schema |
| `idempotency_key` | string | No | null | Idempotent retry key |
| `scanner_pool` | string | No | "nessus" | Scanner pool |
| `scanner_instance` | string | No | null | Specific scanner |

**Scan Types:**
- `authenticated` - SSH login only, no privilege escalation
- `authenticated_privileged` - SSH login + sudo/su escalation

**Authentication Detection:**
- Plugin 141118: "Valid Credentials Provided" confirms success
- Plugin 110385: "Insufficient Privilege" indicates need for escalation
- hosts_summary.credential field in results

---

### 1.2 Status & Monitoring Tools

#### get_scan_status

Get current status of a scan task with validation results.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | Task ID from scan submission |

**Response (completed scan):**
```json
{
  "task_id": "ne_prod_20251201_120000_abc123",
  "trace_id": "uuid",
  "status": "completed",
  "scanner_pool": "nessus",
  "scanner_instance": "scanner1",
  "nessus_scan_id": 123,
  "created_at": "2025-12-01T12:00:00Z",
  "started_at": "2025-12-01T12:00:05Z",
  "completed_at": "2025-12-01T12:15:00Z",
  "authentication_status": "success",
  "validation_warnings": [],
  "results_summary": {
    "hosts_scanned": 1,
    "total_vulnerabilities": 42,
    "severity_breakdown": {
      "critical": 11,
      "high": 9,
      "medium": 15,
      "low": 7
    },
    "file_size_kb": 125.5,
    "auth_plugins_found": 23
  }
}
```

**Response (failed authentication):**
```json
{
  "task_id": "...",
  "status": "failed",
  "authentication_status": "failed",
  "error_message": "Authentication FAILED...",
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

#### list_tasks

List recent tasks with filtering capabilities.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | int | No | 10 | Maximum tasks to return |
| `status_filter` | string | No | null | Filter by status |
| `scanner_pool` | string | No | null | Filter by pool |
| `target_filter` | string | No | null | Filter by target (CIDR-aware) |

**Status Values:** `queued`, `running`, `completed`, `failed`, `timeout`

---

#### get_queue_status

Get Redis queue metrics for a pool.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `scanner_pool` | string | No | "nessus" | Pool name |

**Response:**
```json
{
  "pool": "nessus",
  "queue_depth": 3,
  "dlq_size": 0,
  "next_tasks": ["task1", "task2", "task3"],
  "timestamp": "2025-12-01T12:00:00Z"
}
```

---

### 1.3 Scanner Management Tools

#### list_scanners

List registered scanner instances with load information.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `scanner_pool` | string | No | null | Filter by pool |

**Response:**
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
  "total": 1,
  "pools": ["nessus"]
}
```

---

#### list_pools

List available scanner pools.

**Response:**
```json
{
  "pools": ["nessus", "nessus_dmz"],
  "default_pool": "nessus"
}
```

---

#### get_pool_status

Get aggregate pool metrics and per-scanner breakdown.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `scanner_pool` | string | No | "nessus" | Pool name |

**Response:**
```json
{
  "pool": "nessus",
  "scanner_type": "nessus",
  "total_scanners": 2,
  "total_capacity": 4,
  "total_active": 1,
  "available_capacity": 3,
  "utilization_pct": 25.0,
  "scanners": [
    {
      "instance_key": "nessus:scanner1",
      "active_scans": 1,
      "max_concurrent_scans": 2,
      "utilization_pct": 50.0,
      "available_capacity": 1
    }
  ]
}
```

---

### 1.4 Results Retrieval Tools

#### get_scan_results

Get scan results in paginated JSON-NL format.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | string | Yes | - | Task ID |
| `page` | int | No | 1 | Page number (0 = all data) |
| `page_size` | int | No | 40 | Results per page (10-100) |
| `schema_profile` | string | No | "brief" | Predefined schema |
| `custom_fields` | list | No | null | Custom field list |
| `filters` | dict | No | null | Filter criteria |

**Schema Profiles:**
| Profile | Fields | Use Case |
|---------|--------|----------|
| `minimal` | host, plugin_id, severity, cve, cvss_score, exploit_available | Quick triage |
| `summary` | minimal + plugin_name, cvss3_base_score, synopsis | LLM analysis |
| `brief` | summary + description, solution | Detailed review (default) |
| `full` | All fields | Complete data |

**Filter Examples:**
```json
{
  "severity": "4",
  "cvss_score": ">7.0",
  "exploit_available": true,
  "cve": "CVE-2021"
}
```

**JSON-NL Output Format:**
```
{"type": "schema", "profile": "brief", "fields": [...], "total_vulnerabilities": 40}
{"type": "scan_metadata", "scan_name": "Test Scan", "policy_name": "..."}
{"type": "vulnerability", "host": "192.168.1.1", "plugin_id": "12345", ...}
{"type": "pagination", "page": 1, "page_size": 10, "has_next": true}
```

---

## 2. Scanner Integration

### 2.1 Native Async Nessus Scanner

Pure async/await implementation using httpx for all Nessus API operations.

**Capabilities:**
- Session-based authentication with token management
- Scan creation with policy templates
- Scan launch and status polling
- Results export (nessus format)
- Scan stop/delete operations
- SSL verification handling for self-signed certificates

**Status Mapping:**
| Nessus Status | MCP Status |
|---------------|------------|
| pending | queued |
| running | running |
| paused | running |
| completed | completed |
| canceled | failed |
| stopped | failed |
| aborted | failed |

---

### 2.2 Scanner Registry

Multi-instance scanner management with pool-based routing.

**Features:**
- YAML configuration with environment variable substitution
- Pool-based scanner grouping
- Per-scanner concurrency limits
- Load-based scanner selection (lowest utilization wins)
- Instance enable/disable
- Hot-reload configuration via SIGHUP

**Configuration Example (`config/scanners.yaml`):**
```yaml
nessus:
  scanner1:
    name: "Primary Scanner"
    url: "https://172.30.0.3:8834"
    username: "${NESSUS_USERNAME:-nessus}"
    password: "${NESSUS_PASSWORD}"
    enabled: true
    max_concurrent_scans: 2
```

---

### 2.3 Scan Result Validation

Post-scan validation with authentication detection.

**Validation Checks:**
- File existence and size
- XML structure validity
- Host count verification
- Plugin analysis for auth-only plugins

**Authentication Detection Methods:**
1. Plugin 19506 ("Nessus Scan Information") credential status
2. Auth-required plugin count (fallback)
3. hosts_summary.credential field

**Authentication Statuses:**
- `success` - Credentials accepted, authenticated plugins found
- `failed` - Credentials rejected or inaccessible
- `partial` - Some hosts authenticated, some failed
- `not_applicable` - Untrusted scan (no credentials)

---

## 3. Queue & Task Management

### 3.1 Redis Task Queue

FIFO queue implementation with reliable delivery.

**Queue Keys:**
- `{pool}:queue` - Main task queue (LPUSH/BRPOP)
- `{pool}:queue:dead` - Dead Letter Queue (ZADD with timestamp)

**Operations:**
- **Enqueue**: LPUSH to pool queue
- **Dequeue**: BRPOP with 5-second timeout (no busy-wait)
- **DLQ Move**: ZADD with timestamp score for failed tasks

---

### 3.2 Task State Machine

Enforced state transitions with file locking.

```
QUEUED
   │
   ├─ Worker dequeues
   │
   ▼
RUNNING
   │
   ├─→ COMPLETED (success, results exported)
   ├─→ FAILED (error, moved to DLQ)
   └─→ TIMEOUT (24h exceeded, scan stopped)
```

**Valid Transitions:**
| From | To |
|------|-----|
| QUEUED | RUNNING, FAILED |
| RUNNING | COMPLETED, FAILED, TIMEOUT |
| COMPLETED | (terminal) |
| FAILED | (terminal) |
| TIMEOUT | (terminal) |

---

### 3.3 Task Manager

Single writer for task state with file-based persistence.

**Task Storage:**
```
/app/data/tasks/{task_id}/
├── task.json          # Task metadata
├── scan_native.nessus # Raw scan results
└── scanner_logs/      # Scanner output
```

**Task Metadata Fields:**
```json
{
  "task_id": "ne_prod_20251201_120000_abc123",
  "trace_id": "uuid",
  "scan_type": "untrusted",
  "scanner_type": "nessus",
  "scanner_instance_id": "scanner1",
  "scanner_pool": "nessus",
  "status": "completed",
  "payload": {"targets": "...", "name": "..."},
  "created_at": "2025-12-01T12:00:00Z",
  "started_at": "2025-12-01T12:00:05Z",
  "completed_at": "2025-12-01T12:15:00Z",
  "nessus_scan_id": 123,
  "validation_stats": {...},
  "validation_warnings": [],
  "authentication_status": "not_applicable"
}
```

---

### 3.4 Idempotency System

Request deduplication with conflict detection.

**Key Sources (priority order):**
1. HTTP header: `X-Idempotency-Key`
2. Tool argument: `idempotency_key`

**Behavior:**
- Same key + same params → Return existing task
- Same key + different params → 409 Conflict error
- New key → Create new task

**Storage:** Redis with 48-hour TTL

---

### 3.5 Background Scanner Worker

Async task processor with graceful shutdown.

**Features:**
- Concurrent scan processing (configurable limit)
- Multi-pool support via `WORKER_POOLS` env var
- 30-second status poll interval
- 24-hour timeout protection
- Graceful shutdown (60-second cleanup)
- Automatic DLQ routing for failures

---

## 4. Results Processing

### 4.1 XML Parser

Parses .nessus files extracting vulnerabilities and metadata.

**Extracted Data:**
- Scan metadata (name, policy, timestamps)
- Per-host results (ReportHost elements)
- Per-vulnerability data (ReportItem elements)
- CVE lists (aggregated)
- CVSS scores (converted to float)

---

### 4.2 Filtering Engine

Type-aware generic filtering with AND logic.

**Filter Types:**
| Type | Behavior | Example |
|------|----------|---------|
| String | Case-insensitive substring | `"severity": "critical"` |
| Number | Comparison operators | `"cvss_score": ">7.0"` |
| Boolean | Exact match | `"exploit_available": true` |
| List | Any element contains | `"cve": "CVE-2021"` |

**Operators:** `>`, `>=`, `<`, `<=`, `=`

---

### 4.3 JSON-NL Converter

Transforms Nessus XML to structured JSON-NL output.

**Output Structure:**
1. Schema line (profile, fields, filters applied, totals)
2. Scan metadata line
3. Vulnerability lines (paginated)
4. Pagination line (if paginated)

---

## 5. Observability

### 5.1 Structured Logging

JSON output with structlog for machine parsing.

**Log Fields:**
- ISO 8601 timestamps with microseconds
- Trace ID propagation
- Multi-level support (DEBUG, INFO, WARNING, ERROR)

**Worker Events (39 events):**
- task_dequeued
- scan_state_transition
- scan_progress (25%, 50%, 75%, 100%)
- scan_completed / scan_failed
- scanner_connection_failed
- authentication_failed

---

### 5.2 Prometheus Metrics

8 core metrics plus pool-specific metrics.

**Core Metrics:**
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `nessus_scans_total` | Counter | scan_type, status | Total scans by type and outcome |
| `nessus_api_requests_total` | Counter | tool, status | MCP tool call counts |
| `nessus_active_scans` | Gauge | - | Currently running scans |
| `nessus_scanner_instances` | Gauge | scanner_type, enabled | Registered scanner count |
| `nessus_queue_depth` | Gauge | queue | Tasks in queue |
| `nessus_dlq_size` | Gauge | - | Dead letter queue size |
| `nessus_task_duration_seconds` | Histogram | - | Scan execution duration |
| `nessus_ttl_deletions_total` | Counter | - | Housekeeping deletions |

**Pool Metrics:**
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `nessus_pool_queue_depth` | Gauge | pool | Tasks queued per pool |
| `nessus_pool_dlq_depth` | Gauge | pool | DLQ size per pool |
| `nessus_validation_total` | Counter | pool, result | Validation counts |
| `nessus_validation_failures_total` | Counter | pool, reason | Failure breakdown |
| `nessus_auth_failures_total` | Counter | pool, scan_type | Auth failures |

**Endpoint:** `GET /metrics` (Prometheus text format)

---

### 5.3 Health Checks

Dependency health verification.

**Checks:**
- Redis PING connectivity
- Filesystem write test with auto-directory creation

**Endpoints:**
- `GET /health` - Returns 200 (healthy) or 503 (unhealthy)

**Response:**
```json
{
  "status": "healthy",
  "redis_healthy": true,
  "filesystem_healthy": true,
  "redis_url": "redis://redis:6379",
  "data_dir": "/app/data/tasks"
}
```

---

## 6. Production Features

### 6.1 Pool Architecture

Isolated scanner groups for network segmentation.

**Use Cases:**
- Internal vs DMZ scanners
- Geographic distribution
- Workload isolation

**Queue Isolation:**
- Each pool has separate Redis queue
- Worker can subscribe to multiple pools
- Tasks routed to specified pool

---

### 6.2 Load-Based Scanner Selection

Automatic selection of least-loaded scanner in pool.

**Algorithm:**
1. Get all enabled scanners in pool
2. Calculate utilization: `active_scans / max_concurrent_scans`
3. Select scanner with lowest utilization
4. Optionally specify `scanner_instance` to override

---

### 6.3 Per-Scanner Concurrency Limits

Configurable concurrent scan limits per scanner.

**Default:** 2 concurrent scans per scanner

**Rationale:**
- Prevents scanner overload
- Ensures predictable scan timing
- Queue absorbs overflow

---

### 6.4 Circuit Breaker

Protection against cascading scanner failures.

**States:**
- `CLOSED` - Normal operation, tracking failures
- `OPEN` - Too many failures, rejecting requests
- `HALF_OPEN` - After cooldown, testing recovery

**Configuration:**
- `failure_threshold`: 5 failures to open
- `cooldown_seconds`: 300 seconds before half-open
- `success_threshold`: 2 successes to close

---

### 6.5 Production Docker Configuration

Multi-stage builds with resource limits.

**Services:**
- `redis` - Task queue with persistence
- `mcp-api` - MCP HTTP server
- `worker-main` - Scanner worker(s)

**Features:**
- Health checks on all services
- Resource limits (CPU, memory)
- Persistent Redis volume
- Non-root user execution
- Auto-restart policies

---

## 7. Administration

### 7.1 TTL Housekeeping

Automatic cleanup of old task data.

**Retention Periods:**
- Completed tasks: 7 days (configurable)
- Failed/timeout tasks: 30 days (configurable)
- Running/queued tasks: Never deleted

**Features:**
- Hourly cleanup cycle
- Disk space tracking
- Metric recording (`ttl_deletions_total`)

---

### 7.2 DLQ Handler CLI

Admin tool for Dead Letter Queue management.

**Commands:**
```bash
# Show queue statistics
python -m tools.admin_cli stats --pool nessus

# List failed tasks
python -m tools.admin_cli list-dlq --pool nessus --limit 20

# Inspect specific task
python -m tools.admin_cli inspect-dlq <task_id> --pool nessus

# Retry failed task
python -m tools.admin_cli retry-dlq <task_id> --pool nessus

# Clear all DLQ tasks
python -m tools.admin_cli purge-dlq --pool nessus --confirm
```

---

### 7.3 Configuration Hot-Reload

Live configuration updates without restart.

**Mechanism:** SIGHUP signal to worker process

**Reloadable Settings:**
- Scanner instances
- Pool membership
- Concurrency limits
- Enable/disable state

---

## Appendix A: Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection URL |
| `DATA_DIR` | `/app/data/tasks` | Task data directory |
| `SCANNER_CONFIG` | `/app/config/scanners.yaml` | Scanner registry config |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_CONCURRENT_SCANS` | `2` | Default scanner concurrency |
| `WORKER_POOLS` | `nessus` | Comma-separated pool list |
| `MCP_PORT` | `8836` | MCP server port |
| `NESSUS_URL` | - | Nessus scanner URL |
| `NESSUS_USERNAME` | - | Nessus credentials |
| `NESSUS_PASSWORD` | - | Nessus credentials |

---

## Appendix B: Implementation Status

| Feature | Phase | Status |
|---------|-------|--------|
| Native Async Scanner | 0 | Complete |
| Scanner Registry | 0 | Complete |
| Redis Task Queue | 1 | Complete |
| State Machine | 1 | Complete |
| MCP Tools (scan/status) | 1 | Complete |
| XML Parser | 2 | Complete |
| Schema Profiles | 2 | Complete |
| Filtering Engine | 2 | Complete |
| JSON-NL Converter | 2 | Complete |
| Structured Logging | 3 | Complete |
| Prometheus Metrics | 3 | Complete |
| Health Checks | 3 | Complete |
| Pool Architecture | 4 | Complete |
| Validation System | 4 | Complete |
| Production Docker | 4 | Complete |
| TTL Housekeeping | 4 | Complete |
| DLQ CLI | 4 | Complete |
| Circuit Breaker | 4 | Complete |
| Authenticated Scans | 5 | Complete |
| E2E Tests | 6 | Complete |

---

## Appendix C: Test Coverage

| Component | Tests |
|-----------|-------|
| Task Manager | 16 |
| Nessus Validator | 18 |
| Pool Registry | 17 |
| Pool Queue | 15 |
| Health Checks | 17 |
| Metrics | 45 |
| Housekeeping | 18 |
| Admin CLI | 21 |
| Circuit Breaker | 27 |
| Authenticated Scans | 18 |
| MCP E2E | 18 |
| **Total** | **220+** |
