<!-- README Navigation -->
<!-- L3: mcp-server/docker/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Development container images -->

# Docker Build Files

> Development container images

**↑ Parent**: [MCP Server](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

## Files

| File | Target | Description |
|------|--------|-------------|
| `Dockerfile.api` | `mcp-api` | MCP server with FastMCP |
| `Dockerfile.worker` | `worker` | Background scan processor |
| `Dockerfile.scan-target` | `scan-target` | SSH test target for auth scans |
| `Dockerfile.test` | `test-runner` | Test execution environment |

## Building Images

### MCP API Server

```bash
docker build -f docker/Dockerfile.api -t mcp-api:dev .
```

**Base**: `python:3.11-slim`
**Port**: 8000
**Entrypoint**: `uvicorn tools.mcp_server:app`
**Healthcheck**: HTTP GET `/health`

### Scanner Worker

```bash
docker build -f docker/Dockerfile.worker -t worker:dev .
```

**Base**: `python:3.11-slim`
**Dependencies**: libxml2, libxslt (for XML parsing)
**Entrypoint**: `python -m worker.scanner_worker`
**Healthcheck**: Redis ping

### Scan Target (Testing)

```bash
docker build -f docker/Dockerfile.scan-target -t scan-target:test .
```

**Base**: `ubuntu:22.04`
**Port**: 22 (SSH)
**Purpose**: Test authenticated scans

**Test users**:
| User | Password | Sudo Access |
|------|----------|-------------|
| `testauth_sudo_pass` | `TestPass123!` | With password |
| `testauth_sudo_nopass` | `TestPass123!` | NOPASSWD |
| `testauth_nosudo` | `TestPass123!` | None |

### Test Runner

```bash
docker build -f docker/Dockerfile.test -t test-runner:dev .
```

**Purpose**: Execute pytest suite

## Image Contents

### API Image (`Dockerfile.api`)

```
/app/
├── scanners/    # Scanner implementations
├── core/        # Core modules
├── schema/      # Result formatting
├── tools/       # MCP server
├── config/      # Scanner config
└── data/tasks/  # Task storage
```

### Worker Image (`Dockerfile.worker`)

```
/app/
├── scanners/    # Scanner implementations
├── core/        # Core modules
├── schema/      # Result formatting
├── worker/      # Worker process
├── config/      # Scanner config
└── data/tasks/  # Task storage
```

## Environment Variables

### API Container

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `DATA_DIR` | `/app/data/tasks` | Task storage |
| `SCANNER_CONFIG` | `/app/config/scanners.yaml` | Scanner pools |

### Worker Container

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `MAX_CONCURRENT_SCANS` | `5` | Per-pool capacity |

## Development Usage

Images are used by `dev1/docker-compose.yml`:

```yaml
services:
  mcp-api:
    build:
      context: ../mcp-server
      dockerfile: docker/Dockerfile.api
```