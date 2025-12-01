<!-- README Navigation -->
<!-- L3: mcp-server/prod/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Production-ready Docker deployment -->

# Production Deployment

> Production-ready Docker deployment

**↑ Parent**: [MCP Server](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Production stack definition |
| `Dockerfile.api` | Production API image |
| `Dockerfile.worker` | Production worker image |

## Quick Start

```bash
cd mcp-server/prod

# Build and start
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## Services

### redis

Redis queue with persistence.

**Configuration**:
- AOF persistence enabled
- 512MB memory limit
- LRU eviction policy
- Health check every 10s

### mcp-api

MCP server endpoint.

**Port**: `${MCP_PORT:-8836}` → 8000
**Resources**: 1 CPU, 1GB RAM
**Health check**: HTTP `/health`

### worker

Background scan processor.

**Resources**: 2 CPU, 2GB RAM
**Health check**: Redis connectivity
**Restart**: Always (with back-off)

## docker-compose.yml Structure

```yaml
services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  mcp-api:
    build:
      context: ..
      dockerfile: prod/Dockerfile.api
    ports:
      - "${MCP_PORT:-8836}:8000"
    depends_on:
      redis:
        condition: service_healthy

  worker:
    build:
      context: ..
      dockerfile: prod/Dockerfile.worker
    depends_on:
      - redis
      - mcp-api

volumes:
  redis_data:

networks:
  mcp-network:
  nessus-shared_vpn_net:
    external: true
```

## Environment Variables

Set in `.env` or shell:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_PORT` | `8836` | Exposed API port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `NESSUS_URL` | - | Primary scanner URL |
| `NESSUS_USERNAME` | - | Scanner username |
| `NESSUS_PASSWORD` | - | Scanner password |

## Production Considerations

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

### Health Checks

All services have health checks:
- Redis: `redis-cli ping`
- API: `curl http://localhost:8000/health`
- Worker: Redis ping

### Restart Policy

```yaml
restart: always
```

### Volume Persistence

- `redis_data` - Redis AOF persistence
- `../data` - Task results (bind mount)
- `../config` - Scanner config (read-only)

## Networking

### Internal Network

`mcp-network` - Services communicate internally.

### External Network

`nessus-shared_vpn_net` - Scanner access via VPN.

## Deployment Commands

```bash
# Build without cache
docker compose build --no-cache

# Start in detached mode
docker compose up -d

# Scale workers
docker compose up -d --scale worker=3

# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v
```

## Monitoring

```bash
# Service status
docker compose ps

# Resource usage
docker stats

# Logs
docker compose logs -f mcp-api
docker compose logs -f worker
```

## Differences from Development

| Aspect | Development | Production |
|--------|-------------|------------|
| Source mounts | Yes (hot reload) | No (built into image) |
| Log level | DEBUG | INFO |
| Resource limits | None | Enforced |
| Restart policy | `no` | `always` |
| Health checks | Basic | Comprehensive |
