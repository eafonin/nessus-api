<!-- README Navigation -->
<!-- L2: dev1/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Development environment with hot reload -->

# Development Environment

> Local development deployment with hot reload and debug logging

**↑ Parent**: [Nessus MCP Server](../README.MD)

## Quick Start

```bash
# Start development stack
cd dev1
docker compose up -d

# View logs
docker compose logs -f

# Stop stack
docker compose down
```

## Services

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| Redis | nessus-mcp-redis-dev | 6379 | Task queue and state storage |
| MCP API | nessus-mcp-api-dev | 8836 | MCP server endpoint |
| Worker | nessus-mcp-worker-dev | - | Background scan processor |

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Development Stack                         │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐               │
│  │  Redis  │◄────│ MCP API │     │ Worker  │               │
│  │  :6379  │     │  :8836  │     │         │               │
│  └─────────┘     └────┬────┘     └────┬────┘               │
│       ▲               │               │                     │
│       └───────────────┴───────────────┘                     │
│                       │ default network                     │
└───────────────────────┼─────────────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         │    scanner_bridge network   │
         │   (nessus-shared_vpn_net)   │
         └──────────────┼──────────────┘
                        │
    ┌───────────────────┴───────────────────┐
    │                                       │
┌───┴───┐                             ┌─────┴─────┐
│Scanner│ 172.30.0.3:8834             │ Scanner 2 │ 172.30.0.4:8834
└───────┘                             └───────────┘
```

## Configuration Files

### docker-compose.yml

Main compose file defining all services:

```yaml
services:
  redis:          # Task queue
  mcp-api:        # MCP server (port 8836)
  scanner-worker: # Background processor
```

### .env.dev

Environment overrides for development:

```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
REDIS_URL=redis://redis:6379
DATA_DIR=/app/data/tasks
```

## Hot Reload

Source code is mounted as volumes for live development:

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `../mcp-server/scanners/` | `/app/scanners/` | Scanner implementations |
| `../mcp-server/core/` | `/app/core/` | Core infrastructure |
| `../mcp-server/schema/` | `/app/schema/` | Result schemas |
| `../mcp-server/tools/` | `/app/tools/` | MCP tools |
| `../mcp-server/client/` | `/app/client/` | Client library |
| `../mcp-server/worker/` | `/app/worker/` | Worker code |

Changes to Python files take effect without rebuild.

## Directory Structure

```
dev1/
├── docker-compose.yml   # Service definitions
├── .env.dev             # Environment config
├── data/                # Persistent task storage
│   └── tasks/           # Task results
└── logs/                # Application logs
```

| Directory | README | Description |
|-----------|--------|-------------|
| [data/](data/) | [README.MD](data/README.MD) | Task result storage |
| [logs/](logs/) | [README.MD](logs/README.MD) | Application logs |

## Runtime Directories

### data/tasks/

Stores scan task results and metadata. Created by Docker with root ownership.

**Task directory structure**:
```
data/tasks/{task_id}/
├── task.json           # Task state and metadata
└── scan_native.nessus  # Raw Nessus XML (completed scans)
```

**Task ID format**: `{scanner}_{pool}_{timestamp}_{uuid}`
- Example: `ne_loca_20251127_130210_83ce08fb`

**task.json contents**:
```json
{
  "task_id": "ne_loca_20251127_130210_83ce08fb",
  "status": "completed",
  "scanner_pool": "nessus",
  "targets": "192.168.1.0/24",
  "created_at": "2025-11-27T13:02:10Z",
  "completed_at": "2025-11-27T13:15:42Z",
  "results_summary": {"critical": 2, "high": 5, "medium": 12}
}
```

### logs/

Application logs directory. Currently unused (logs go to stdout for Docker).

## Common Operations

### Rebuild after Dockerfile changes

```bash
docker compose build --no-cache
docker compose up -d
```

### Reset all data

```bash
docker compose down -v
sudo rm -rf data/tasks/*
docker compose up -d
```

### Check service health

```bash
# All services
docker compose ps

# API health
curl http://localhost:8836/health

# Redis connectivity
docker exec nessus-mcp-redis-dev redis-cli ping
```

### View specific service logs

```bash
# API logs
docker compose logs -f mcp-api

# Worker logs
docker compose logs -f scanner-worker

# Redis logs
docker compose logs -f redis
```

### Connect to container shell

```bash
# API container
docker exec -it nessus-mcp-api-dev /bin/bash

# Worker container
docker exec -it nessus-mcp-worker-dev /bin/bash
```

## Environment Variables

### MCP API Service

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection URL |
| `DATA_DIR` | `/app/data/tasks` | Task storage directory |
| `LOG_LEVEL` | `DEBUG` | Logging verbosity |
| `ENVIRONMENT` | `development` | Environment identifier |
| `NESSUS_URL` | `https://172.30.0.3:8834` | Default scanner URL |

### Worker Service

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection URL |
| `DATA_DIR` | `/app/data/tasks` | Task storage directory |
| `SCANNER_CONFIG` | `/app/config/scanners.yaml` | Scanner pool config |
| `LOG_LEVEL` | `DEBUG` | Logging verbosity |

## Troubleshooting

### API not responding

```bash
# Check container status
docker compose ps

# Check API logs for errors
docker compose logs mcp-api | tail -50

# Restart API
docker compose restart mcp-api
```

### Worker not processing tasks

```bash
# Check worker logs
docker compose logs scanner-worker | tail -50

# Verify Redis connectivity
docker exec nessus-mcp-worker-dev python -c "import redis; r=redis.from_url('redis://redis:6379'); print(r.ping())"

# Check queue status
docker exec nessus-mcp-redis-dev redis-cli LLEN nessus:queue
```

### Scanner connectivity issues

```bash
# Test scanner access from API container
docker exec nessus-mcp-api-dev curl -k https://172.30.0.3:8834

# Verify network connectivity
docker network inspect nessus-shared_vpn_net
```

### Permission denied on data directory

The `data/` directory is created by Docker with root ownership. To fix:

```bash
# Option 1: Change ownership
sudo chown -R $USER:$USER data/

# Option 2: Use from container
docker exec nessus-mcp-api-dev ls -la /app/data/tasks/
```

## See Also

- [MCP Server README](../mcp-server/README.md) - Main server documentation
- [Docker Build Files](../mcp-server/docker/README.MD) - Dockerfile details
- [Scanner Configuration](../mcp-server/config/README.MD) - Scanner pool setup
- [Production Deployment](../mcp-server/prod/README.MD) - Production configuration
