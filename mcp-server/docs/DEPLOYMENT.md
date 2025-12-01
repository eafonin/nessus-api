# Nessus MCP Server - Deployment Guide

> **Last Updated**: 2025-12-01
> **Audience**: DevOps engineers, operators

---

## Quick Start

```bash
# Development (from project root)
cd dev1
docker compose up -d

# Production
cd mcp-server/prod
docker compose up -d

# Verify
curl http://localhost:8836/health
```

---

## Docker Compose Configurations

### Development (`dev1/docker-compose.yml`)

Hot-reload enabled, debug logging, direct scanner access.

**Services**:
- `redis`: Redis 7-alpine on port 6379
- `mcp-api`: FastMCP server on port 8836
- `scanner-worker`: Task processor
- `autoheal`: Auto-restart unhealthy containers

**Features**:
- Source code mounted for live changes
- Debug logging enabled
- Static IPs on scanner network (172.30.0.5, 172.30.0.6)

```bash
cd dev1
docker compose up -d

# View logs
docker compose logs -f mcp-api
docker compose logs -f scanner-worker
```

### Production (`mcp-server/prod/docker-compose.yml`)

Optimized for reliability and performance.

**Services**:
- `redis`: With AOF persistence, 512MB memory limit
- `mcp-api`: Resource limits (1 CPU, 1GB RAM)
- `worker-main`: Resource limits (2 CPU, 2GB RAM)
- `worker-dmz` (optional): Separate DMZ pool worker

**Features**:
- AOF persistence for Redis
- Health checks with restarts
- Resource limits
- Internal network isolation

```bash
cd mcp-server/prod
docker compose up -d
```

---

## Network Topology

```
┌────────────────────────────────────────────────────────────────┐
│                    Docker Host                                  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ default network (bridge)                                 │   │
│  │   redis ←→ mcp-api ←→ scanner-worker                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                    │                    │                       │
│                    └────────┬───────────┘                       │
│                             │                                   │
│  ┌──────────────────────────▼───────────────────────────────┐  │
│  │ scanner_bridge (nessus-shared_vpn_net)                    │  │
│  │   mcp-api (172.30.0.6) ───┬──→ nessus-pro-1 (172.30.0.3) │  │
│  │   worker  (172.30.0.5) ───┴──→ nessus-pro-2 (172.30.0.4) │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**IP Allocation (172.30.0.0/24)**:
| IP | Service |
|----|---------|
| 172.30.0.2 | vpn-gateway (scanners-infra) |
| 172.30.0.3 | nessus-pro-1 |
| 172.30.0.4 | nessus-pro-2 |
| 172.30.0.5 | mcp-worker |
| 172.30.0.6 | mcp-api |

---

## Environment Variables

### MCP API Server

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | redis://redis:6379 | Redis connection URL |
| `DATA_DIR` | /app/data/tasks | Task storage directory |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ENVIRONMENT` | production | Environment name |
| `MCP_SERVER_URL` | - | Internal MCP URL for client connections |

### Scanner Worker

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | redis://redis:6379 | Redis connection URL |
| `DATA_DIR` | /app/data/tasks | Task storage directory |
| `SCANNER_CONFIG` | /app/config/scanners.yaml | Scanner pool config file |
| `LOG_LEVEL` | INFO | Logging level |
| `WORKER_POOLS` | (all) | Comma-separated pool list to consume |

### Scanner Credentials

| Variable | Default | Description |
|----------|---------|-------------|
| `NESSUS_URL` | https://172.30.0.3:8834 | Primary scanner URL |
| `NESSUS_USERNAME` | nessus | Scanner username |
| `NESSUS_PASSWORD` | - | Scanner password |
| `NESSUS_URL_2` | https://172.30.0.4:8834 | Secondary scanner URL |

### Housekeeping

| Variable | Default | Description |
|----------|---------|-------------|
| `HOUSEKEEPING_ENABLED` | true | Enable TTL cleanup |
| `HOUSEKEEPING_INTERVAL_HOURS` | 1 | Cleanup frequency |
| `COMPLETED_TTL_DAYS` | 7 | Retain completed tasks |
| `FAILED_TTL_DAYS` | 30 | Retain failed tasks |
| `STALE_SCAN_HOURS` | 24 | Stale scan threshold |

---

## Scanner Pool Configuration

File: `mcp-server/config/scanners.yaml`

```yaml
# Pool: nessus (default)
nessus:
  - instance_id: scanner1
    name: "Nessus Scanner 1"
    url: ${NESSUS_URL:-https://172.30.0.3:8834}
    username: ${NESSUS_USERNAME:-nessus}
    password: ${NESSUS_PASSWORD}
    enabled: true
    max_concurrent_scans: 2

  - instance_id: scanner2
    name: "Nessus Scanner 2"
    url: ${NESSUS_URL_2:-https://172.30.0.4:8834}
    username: ${NESSUS_USERNAME_2:-nessus}
    password: ${NESSUS_PASSWORD_2}
    enabled: true
    max_concurrent_scans: 2

# Pool: nessus_dmz (optional)
# nessus_dmz:
#   - instance_id: dmz-scanner1
#     url: ${NESSUS_DMZ_URL}
#     max_concurrent_scans: 3
```

**Hot Reload**: Send SIGHUP to worker to reload scanners.yaml

```bash
docker exec nessus-mcp-worker-dev kill -HUP 1
```

---

## Volume Mounts

### Development

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `../mcp-server/scanners` | /app/scanners | Hot reload |
| `../mcp-server/core` | /app/core | Hot reload |
| `../mcp-server/tools` | /app/tools | Hot reload |
| `./data` | /app/data | Task storage |
| `./logs` | /app/logs | Log files |

### Production

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `../data` | /app/data | Task storage |
| `../config` | /app/config:ro | Scanner config |
| `redis_data` | /data | Redis persistence |

---

## Health Checks

### /health Endpoint

```bash
curl http://localhost:8836/health
```

Response:
```json
{
  "status": "healthy",
  "redis_healthy": true,
  "filesystem_healthy": true,
  "redis_url": "redis://redis:6379",
  "data_dir": "/app/data/tasks"
}
```

### Docker Health Checks

**mcp-api**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 5s
  retries: 3
```

**scanner-worker**:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import redis; r=redis.from_url('redis://redis:6379'); r.ping()"]
  interval: 30s
  timeout: 5s
  retries: 3
```

---

## Prometheus Metrics

Endpoint: `http://localhost:8836/metrics`

**Available Metrics**:

| Metric | Type | Description |
|--------|------|-------------|
| `nessus_scans_total` | Counter | Total scans by type and status |
| `nessus_active_scans` | Gauge | Currently running scans |
| `nessus_queue_depth` | Gauge | Tasks in queue |
| `nessus_dlq_size` | Gauge | Tasks in DLQ |
| `nessus_task_duration_seconds` | Histogram | Scan execution time |
| `nessus_ttl_deletions_total` | Counter | Tasks deleted by cleanup |

---

## Admin CLI

```bash
# Enter worker container
docker exec -it nessus-mcp-worker-dev bash

# Show queue stats
python -m tools.admin_cli stats --pool nessus
python -m tools.admin_cli stats --all-pools

# List DLQ tasks
python -m tools.admin_cli list-dlq --pool nessus --limit 20

# Inspect failed task
python -m tools.admin_cli inspect-dlq <task_id>

# Retry failed task
python -m tools.admin_cli retry-dlq <task_id> --yes

# Purge DLQ (dangerous)
python -m tools.admin_cli purge-dlq --pool nessus --confirm
```

---

## TTL Housekeeping

Automatic cleanup of old task directories.

**Configuration**:
- Completed tasks: 7 days retention
- Failed/timeout tasks: 30 days retention
- Cleanup interval: 1 hour

**Behavior**:
- Scans `/app/data/tasks/*/task.json`
- Deletes directories based on status and age
- Never deletes running/queued tasks
- Logs cleanup activity

---

## Circuit Breaker

Not currently implemented. Planned for future phases.

---

## Troubleshooting

### Scan Stuck in QUEUED

1. Check worker is running:
   ```bash
   docker compose ps
   ```

2. Check Redis connectivity:
   ```bash
   docker exec nessus-mcp-redis-dev redis-cli ping
   ```

3. Check queue depth:
   ```bash
   docker exec nessus-mcp-redis-dev redis-cli LLEN nessus:queue
   ```

4. Check worker logs:
   ```bash
   docker compose logs -f scanner-worker
   ```

### Scan FAILED

1. Check task details:
   ```bash
   cat dev1/data/tasks/<task_id>/task.json | jq .error_message
   ```

2. Check DLQ:
   ```bash
   python -m tools.admin_cli inspect-dlq <task_id>
   ```

3. Common causes:
   - Scanner authentication failed
   - Network connectivity to scanner
   - Scanner license expired

### Scanner Connectivity

1. Test from worker container:
   ```bash
   docker exec -it nessus-mcp-worker-dev curl -k https://nessus-pro-1:8834
   ```

2. Check scanner config:
   ```bash
   cat mcp-server/config/scanners.yaml
   ```

3. Verify network:
   ```bash
   docker network inspect nessus-shared_vpn_net
   ```

### Redis Connection Failed

1. Check Redis container:
   ```bash
   docker compose logs redis
   ```

2. Test connectivity:
   ```bash
   docker exec nessus-mcp-api-dev python -c "import redis; r=redis.from_url('redis://redis:6379'); print(r.ping())"
   ```

---

## Logs

### Log Locations

| Service | Path |
|---------|------|
| mcp-api | `dev1/logs/` or docker logs |
| scanner-worker | `dev1/logs/` or docker logs |
| redis | docker logs only |

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f mcp-api

# Filter by task_id (JSON logs)
docker compose logs mcp-api 2>&1 | grep "task_id.*ne_scan_xxx"
```

---

## Cross-References

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: System design
- **[FEATURES.md](FEATURES.md)**: Feature documentation
- **[REQUIREMENTS.md](REQUIREMENTS.md)**: Requirements traceability

---

*Deployment document generated from source code analysis*
