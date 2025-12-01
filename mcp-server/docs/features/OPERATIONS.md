# Nessus MCP Server - Operations Guide

> **[↑ Features Index](README.md)** | **[← Features](FEATURES.md)** | **[Architecture →](ARCHITECTURE.md)**

## Overview

This guide covers operational aspects of the Nessus MCP Server including administration, monitoring, and maintenance tasks.

---

## 1. Admin CLI

### 1.1 DLQ Handler CLI

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

### 1.2 Quick Commands

```bash
# Health check
curl http://localhost:8836/health

# Prometheus metrics
curl http://localhost:8836/metrics

# Queue depth (direct Redis)
docker exec nessus-mcp-redis redis-cli LLEN nessus:queue

# DLQ size
docker exec nessus-mcp-redis redis-cli ZCARD nessus:queue:dead

# Hot reload scanner config
kill -SIGHUP $(pgrep -f scanner_worker)
```

---

## 2. TTL Housekeeping

Automatic cleanup of old task data runs as a background task in the worker.

### 2.1 Retention Periods

| Task Status | Retention | Rationale |
|-------------|-----------|-----------|
| Completed | 7 days | Results retrieved, storage reclaim |
| Failed | 30 days | Allow investigation time |
| Timeout | 30 days | Allow investigation time |
| Running | Never | Active tasks protected |
| Queued | Never | Pending tasks protected |

### 2.2 Housekeeping Behavior

- **Cleanup cycle**: Hourly
- **Disk space tracking**: Logged before/after cleanup
- **Metric recording**: `nessus_ttl_deletions_total` counter

### 2.3 Manual Cleanup

```bash
# Force cleanup (restart worker triggers immediate check)
docker compose restart worker

# Check disk usage
du -sh /app/data/tasks/
```

---

## 3. Circuit Breaker

Protection against cascading scanner failures.

### 3.1 States

```text
CLOSED ──(5 failures)──▶ OPEN ──(300s cooldown)──▶ HALF_OPEN
   ▲                                                    │
   │                                                    │
   └────────────(2 successes)───────────────────────────┘
```

### 3.2 Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `failure_threshold` | 5 | Consecutive failures to open circuit |
| `cooldown_seconds` | 300 | Seconds before attempting recovery |
| `success_threshold` | 2 | Successes needed to close circuit |

### 3.3 State Descriptions

| State | Behavior |
|-------|----------|
| **CLOSED** | Normal operation, tracking failure count |
| **OPEN** | Rejecting requests, waiting for cooldown |
| **HALF_OPEN** | Testing recovery with limited requests |

---

## 4. Configuration Hot-Reload

Live configuration updates without service restart.

### 4.1 Trigger

```bash
# Send SIGHUP to worker process
kill -SIGHUP $(pgrep -f scanner_worker)

# Or via Docker
docker exec nessus-mcp-worker pkill -SIGHUP -f scanner_worker
```

### 4.2 Reloadable Settings

| Setting | Reloadable | Notes |
|---------|------------|-------|
| Scanner instances | Yes | Add/remove scanners |
| Pool membership | Yes | Move scanners between pools |
| Concurrency limits | Yes | Adjust max_concurrent_scans |
| Enable/disable state | Yes | Toggle scanner availability |
| Redis URL | No | Requires restart |
| Data directory | No | Requires restart |

---

## 5. Environment Variables

### 5.1 Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection URL |
| `DATA_DIR` | `/app/data/tasks` | Task data storage directory |
| `SCANNER_CONFIG` | `/app/config/scanners.yaml` | Scanner registry config path |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MCP_PORT` | `8836` | MCP server HTTP port |

### 5.2 Worker Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKER_POOLS` | `nessus` | Comma-separated pool list to subscribe |
| `MAX_CONCURRENT_SCANS` | `2` | Default per-scanner concurrency limit |

### 5.3 Nessus Credentials

| Variable | Default | Description |
|----------|---------|-------------|
| `NESSUS_URL` | - | Nessus scanner URL (e.g., `https://172.30.0.3:8834`) |
| `NESSUS_USERNAME` | - | Nessus API username |
| `NESSUS_PASSWORD` | - | Nessus API password |

**Note**: These can be overridden per-scanner in `scanners.yaml` using environment variable substitution:
```yaml
nessus:
  scanner1:
    url: "${NESSUS_URL}"
    username: "${NESSUS_USERNAME:-admin}"
    password: "${NESSUS_PASSWORD}"
```

### 5.4 Optional Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TTL_COMPLETED_DAYS` | `7` | Days to retain completed tasks |
| `TTL_FAILED_DAYS` | `30` | Days to retain failed/timeout tasks |
| `CIRCUIT_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `CIRCUIT_COOLDOWN_SECONDS` | `300` | Cooldown before half-open |

---

## 6. Docker Operations

### 6.1 Development

```bash
cd mcp-server
docker compose up -d
docker compose logs -f worker
docker compose ps
```

### 6.2 Production

```bash
cd mcp-server/prod
docker compose -f docker-compose.yml up -d
docker compose logs -f
```

### 6.3 Service Management

```bash
# Restart specific service
docker compose restart worker

# Scale workers (if configured)
docker compose up -d --scale worker=2

# View resource usage
docker stats nessus-mcp-api nessus-mcp-worker nessus-mcp-redis
```

---

## 7. Troubleshooting

### 7.1 Common Issues

| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| Tasks stuck in QUEUED | Worker not running | Check worker logs, restart |
| Auth scan fails | Invalid credentials | Verify SSH access manually |
| Circuit OPEN | Scanner unreachable | Check network, scanner health |
| High DLQ count | Repeated failures | Inspect DLQ, check scanner |

### 7.2 Debug Commands

```bash
# Check worker connectivity to Redis
docker exec nessus-mcp-worker python -c "import redis; r=redis.from_url('redis://redis:6379'); print(r.ping())"

# Check scanner connectivity
docker exec nessus-mcp-worker curl -k https://172.30.0.3:8834/server/status

# View task details
cat /app/data/tasks/<task_id>/task.json | jq .

# Check recent logs
docker compose logs --tail=100 worker | grep -i error
```

### 7.3 Log Analysis

```bash
# Find failed scans
docker compose logs worker | grep '"status": "failed"'

# Find auth failures
docker compose logs worker | grep 'authentication_status.*failed'

# Find circuit breaker events
docker compose logs worker | grep 'circuit'
```

---

*Generated: 2025-12-01*
