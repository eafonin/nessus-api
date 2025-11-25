# Monitoring & Operations Guide

> Observability, alerting, and operational tools for the Nessus MCP Server

---

## Overview

This guide covers monitoring and operational aspects of the Nessus MCP Server:

| Component | Purpose | Documentation |
|-----------|---------|---------------|
| [Prometheus Metrics](#prometheus-metrics) | Real-time observability | Counters, gauges, histograms |
| [Circuit Breaker](#circuit-breaker) | Scanner failure protection | Automatic recovery |
| [TTL Housekeeping](#ttl-housekeeping) | Automatic disk cleanup | Configurable retention |
| [Admin CLI](#admin-cli) | Queue management | DLQ inspection and retry |
| [Health Checks](#health-checks) | Service status | Redis, disk, scanner checks |

---

## Quick Start

### View Metrics

```bash
# Prometheus endpoint
curl http://localhost:8835/metrics

# Key metrics to monitor
curl -s http://localhost:8835/metrics | grep -E "nessus_(active|queue|circuit)"
```

### Check Queue Status

```bash
# Queue statistics
python -m tools.admin_cli stats --pool nessus

# All pools overview
python -m tools.admin_cli stats --all-pools
```

### View Failed Tasks

```bash
# List DLQ entries
python -m tools.admin_cli list-dlq --pool nessus --limit 10

# Inspect specific task
python -m tools.admin_cli inspect-dlq TASK_ID --pool nessus
```

---

## Prometheus Metrics

### Endpoint

Metrics are exposed at `/metrics` in Prometheus text format:

```bash
curl http://localhost:8835/metrics
```

### Available Metrics

#### Scan Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `nessus_scans_total` | Counter | `scan_type`, `status` | Total scans by type and status |
| `nessus_active_scans` | Gauge | - | Currently running scans |
| `nessus_task_duration_seconds` | Histogram | - | Scan duration distribution |

#### Queue Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `nessus_queue_depth` | Gauge | `queue` | Tasks in main/dead queue |
| `nessus_pool_queue_depth` | Gauge | `pool` | Tasks queued per pool |
| `nessus_pool_dlq_depth` | Gauge | `pool` | DLQ size per pool |
| `nessus_dlq_size` | Gauge | - | Total DLQ entries |

#### Scanner Pool Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `nessus_scanner_active_scans` | Gauge | `scanner_instance` | Active scans per scanner |
| `nessus_scanner_capacity` | Gauge | `scanner_instance` | Max concurrent per scanner |
| `nessus_scanner_utilization_pct` | Gauge | `scanner_instance` | Utilization percentage |
| `nessus_pool_total_capacity` | Gauge | - | Total pool capacity |
| `nessus_pool_total_active` | Gauge | - | Total active across pool |

#### Validation Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `nessus_validation_total` | Counter | `pool`, `result` | Validation results (success/failed) |
| `nessus_validation_failures_total` | Counter | `pool`, `reason` | Failures by reason |
| `nessus_auth_failures_total` | Counter | `pool`, `scan_type` | Auth failures for trusted scans |

**Validation failure reasons**: `auth_failed`, `xml_invalid`, `empty_scan`, `file_not_found`, `other`

#### Circuit Breaker Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `nessus_circuit_state` | Gauge | `scanner_instance` | State: 0=closed, 1=open, 2=half_open |
| `nessus_circuit_failures_total` | Counter | `scanner_instance` | Total recorded failures |
| `nessus_circuit_opens_total` | Counter | `scanner_instance` | Times circuit opened |

#### API Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `nessus_api_requests_total` | Counter | `tool`, `status` | API calls by tool and status |
| `nessus_ttl_deletions_total` | Counter | - | Tasks deleted by housekeeping |
| `nessus_scanner_instances` | Gauge | `scanner_type`, `enabled` | Registered scanner count |

### Example Prometheus Queries

```promql
# Scan success rate (last 1h)
sum(rate(nessus_scans_total{status="completed"}[1h])) /
sum(rate(nessus_scans_total[1h]))

# Queue depth trend
nessus_pool_queue_depth{pool="nessus"}

# Scanner utilization
nessus_scanner_utilization_pct{scanner_instance=~"nessus:.*"}

# Auth failure rate for trusted scans
sum(rate(nessus_auth_failures_total[1h])) by (scan_type)

# Circuit breaker status (alert if open)
nessus_circuit_state > 0
```

### Alerting Rules

Example Prometheus alerting rules:

```yaml
groups:
  - name: nessus-mcp
    rules:
      - alert: NessusCircuitOpen
        expr: nessus_circuit_state > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker open for {{ $labels.scanner_instance }}"

      - alert: NessusDLQGrowing
        expr: nessus_pool_dlq_depth > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DLQ has {{ $value }} failed tasks for pool {{ $labels.pool }}"

      - alert: NessusHighQueueDepth
        expr: nessus_pool_queue_depth > 50
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Queue depth {{ $value }} for pool {{ $labels.pool }}"

      - alert: NessusAuthFailureSpike
        expr: rate(nessus_auth_failures_total[5m]) > 0.1
        labels:
          severity: critical
        annotations:
          summary: "High auth failure rate for {{ $labels.scan_type }} scans"
```

---

## Circuit Breaker

The circuit breaker prevents cascading failures when scanners become unavailable.

### States

```
┌─────────┐   N failures   ┌─────────┐   timeout    ┌───────────┐
│ CLOSED  │ ─────────────→ │  OPEN   │ ──────────→ │ HALF_OPEN │
│ (normal)│                │(failing)│              │ (testing) │
└─────────┘                └─────────┘              └───────────┘
     ↑                                                    │
     │                    success                         │
     └────────────────────────────────────────────────────┘
                              │
                          failure
                              ↓
                         ┌─────────┐
                         │  OPEN   │
                         └─────────┘
```

### Configuration

Circuit breaker settings are configured per scanner:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `failure_threshold` | 5 | Failures before opening |
| `recovery_timeout` | 30s | Time before testing recovery |
| `half_open_max_requests` | 1 | Requests allowed in half-open |

### How It Works

1. **CLOSED** (normal operation)
   - Requests pass through to scanner
   - Failures are counted
   - After `failure_threshold` failures → OPEN

2. **OPEN** (failing, reject requests)
   - Requests fail fast without trying scanner
   - After `recovery_timeout` → HALF_OPEN

3. **HALF_OPEN** (testing recovery)
   - Limited requests allowed (`half_open_max_requests`)
   - On success → CLOSED
   - On failure → OPEN

### Monitoring Circuit State

```bash
# Check circuit state via metrics
curl -s http://localhost:8835/metrics | grep circuit_state

# Values: 0=closed (normal), 1=open (failing), 2=half_open (testing)
```

### Manual Reset

If a circuit is stuck open after scanner recovery:

```python
from core.circuit_breaker import get_circuit_breaker_registry

registry = get_circuit_breaker_registry()

# Reset specific scanner
registry.reset("nessus:scanner1")

# Reset all circuits
registry.reset_all()
```

---

## TTL Housekeeping

Automatic cleanup of old task directories to prevent disk exhaustion.

### Retention Periods

| Task Status | Default TTL | Environment Variable |
|-------------|-------------|---------------------|
| `completed` | 7 days | `COMPLETED_TTL_DAYS` |
| `failed` | 30 days | `FAILED_TTL_DAYS` |
| `timeout` | 30 days | `FAILED_TTL_DAYS` |
| `running` | Never | (protected) |
| `queued` | Never | (protected) |

### Configuration

Environment variables for the worker:

```bash
# Enable/disable housekeeping
HOUSEKEEPING_ENABLED=true

# Cleanup interval (hours)
HOUSEKEEPING_INTERVAL_HOURS=1

# Retention periods (days)
COMPLETED_TTL_DAYS=7
FAILED_TTL_DAYS=30
```

### Manual Cleanup

Run housekeeping manually:

```python
from core.housekeeping import Housekeeper

hk = Housekeeper(
    data_dir="/app/data/tasks",
    completed_ttl_days=7,
    failed_ttl_days=30
)

# Preview what would be deleted
stats = hk.get_stats()
print(f"Total tasks: {stats['total_tasks']}")
print(f"Expired completed: {stats['expired']['completed']}")
print(f"Expired failed: {stats['expired']['failed']}")

# Run cleanup
result = hk.cleanup()
print(f"Deleted: {result['deleted_count']} tasks")
print(f"Freed: {result['freed_mb']} MB")
```

### Monitoring Cleanup

```bash
# Check TTL deletions metric
curl -s http://localhost:8835/metrics | grep ttl_deletions

# View worker logs for cleanup activity
docker compose logs worker | grep -i housekeeping
```

---

## Admin CLI

Command-line tool for queue management and DLQ operations.

### Installation

The CLI is included with the MCP server:

```bash
python -m tools.admin_cli --help
```

### Commands

#### stats - Queue Statistics

```bash
# Single pool statistics
python -m tools.admin_cli stats --pool nessus

# All pools overview
python -m tools.admin_cli stats --all-pools
```

**Output**:
```
============================================================
Queue Statistics: nessus
============================================================
Queue Depth:  5
DLQ Size:     2
Timestamp:    2025-11-25T19:30:00

Next tasks in queue:
----------------------------------------
  1. task_20251125_193000_a - untrusted
  2. task_20251125_193001_b - trusted_basic
```

#### list-dlq - List Failed Tasks

```bash
# List recent DLQ entries
python -m tools.admin_cli list-dlq --pool nessus --limit 20
```

**Output**:
```
================================================================================
Dead Letter Queue: nessus (3 tasks)
================================================================================
Task ID                  Type         Error                          Failed At
--------------------------------------------------------------------------------
task_20251125_180000_x   untrusted    Connection timeout             2025-11-25 18:00:00
task_20251125_170000_y   trusted      Auth failed                    2025-11-25 17:00:00
--------------------------------------------------------------------------------
Total: 3 tasks
```

#### inspect-dlq - Detailed Task View

```bash
python -m tools.admin_cli inspect-dlq task_20251125_180000_x --pool nessus
```

**Output**:
```json
{
  "task_id": "task_20251125_180000_x",
  "scan_type": "untrusted",
  "payload": {
    "targets": "192.168.1.1",
    "name": "Test Scan"
  },
  "error": "Connection timeout",
  "failed_at": "2025-11-25T18:00:00"
}
```

#### retry-dlq - Re-queue Failed Task

```bash
# Interactive confirmation
python -m tools.admin_cli retry-dlq task_20251125_180000_x --pool nessus

# Skip confirmation
python -m tools.admin_cli retry-dlq task_20251125_180000_x --pool nessus -y
```

#### purge-dlq - Clear All Failed Tasks

```bash
# Requires --confirm flag and interactive confirmation
python -m tools.admin_cli purge-dlq --pool nessus --confirm
```

### Environment Configuration

```bash
# Custom Redis URL
python -m tools.admin_cli --redis-url redis://custom-host:6379 stats

# Default pool
python -m tools.admin_cli --pool nessus_dmz list-dlq
```

---

## Health Checks

### Endpoints

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `/health` | Overall health | JSON with component status |
| `/health/ready` | Readiness probe | 200 if ready, 503 if not |
| `/health/live` | Liveness probe | 200 if alive |

### Health Response

```bash
curl http://localhost:8835/health
```

```json
{
  "status": "healthy",
  "checks": {
    "redis": {"status": "ok", "latency_ms": 1.2},
    "disk": {"status": "ok", "free_gb": 45.2, "used_pct": 32},
    "scanners": {"status": "ok", "available": 2, "total": 2}
  },
  "timestamp": "2025-11-25T19:30:00Z"
}
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Docker Health Check

Configured in `prod/docker-compose.yml`:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

---

## Grafana Dashboards

### Recommended Panels

**Overview Row**:
- Active scans (gauge)
- Queue depth (graph)
- Scan success rate (stat)
- DLQ size (stat)

**Scanner Row**:
- Utilization per scanner (graph)
- Circuit breaker states (state timeline)
- Scanner capacity vs active (bar)

**Validation Row**:
- Validation success/failure (pie)
- Auth failures by scan type (graph)
- Failure reasons breakdown (bar)

**Operations Row**:
- TTL deletions (counter)
- API request rate (graph)
- Task duration histogram (heatmap)

### Example Dashboard JSON

See [grafana/nessus-mcp-dashboard.json](./grafana/nessus-mcp-dashboard.json) for a complete dashboard definition.

---

## Troubleshooting

### High Queue Depth

**Symptoms**: `nessus_pool_queue_depth` growing steadily

**Causes**:
1. Scanner at capacity
2. Worker not running
3. Scanner unreachable

**Resolution**:
```bash
# Check worker status
docker compose ps worker

# Check scanner utilization
curl -s http://localhost:8835/metrics | grep utilization

# Check circuit breaker
curl -s http://localhost:8835/metrics | grep circuit_state
```

### Growing DLQ

**Symptoms**: `nessus_pool_dlq_depth` increasing

**Causes**:
1. Scanner connectivity issues
2. Invalid scan configurations
3. Authentication failures

**Resolution**:
```bash
# Inspect failed tasks
python -m tools.admin_cli list-dlq --pool nessus

# Check specific task error
python -m tools.admin_cli inspect-dlq TASK_ID --pool nessus

# Retry after fixing issue
python -m tools.admin_cli retry-dlq TASK_ID --pool nessus -y
```

### Circuit Breaker Open

**Symptoms**: `nessus_circuit_state` = 1

**Causes**:
1. Scanner unreachable
2. Repeated failures
3. Network issues

**Resolution**:
```bash
# Check scanner connectivity
curl -k https://nessus-scanner:8834

# Monitor for recovery (half-open = 2)
watch -n5 'curl -s http://localhost:8835/metrics | grep circuit_state'

# Manual reset if scanner recovered
python -c "from core.circuit_breaker import get_circuit_breaker_registry; get_circuit_breaker_registry().reset('nessus:scanner1')"
```

### Disk Space Issues

**Symptoms**: Health check shows low disk space

**Resolution**:
```bash
# Check task directory size
du -sh /app/data/tasks/

# Check housekeeping stats
python -c "
from core.housekeeping import Housekeeper
hk = Housekeeper('/app/data/tasks')
print(hk.get_stats())
"

# Force cleanup with shorter TTL
python -c "
from core.housekeeping import Housekeeper
hk = Housekeeper('/app/data/tasks', completed_ttl_days=1)
print(hk.cleanup())
"
```

---

## See Also

- [Scanner Pools](./SCANNER_POOLS.md) - Pool configuration and load balancing
- [Architecture](./ARCHITECTURE_v2.2.md) - System design and data flows
- [Phase 4 Status](../phases/PHASE4_STATUS.md) - Implementation details
- [Production Docker](../prod/docker-compose.yml) - Production deployment
