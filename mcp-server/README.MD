<!-- README Navigation -->
<!-- L2: mcp-server/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: MCP server core implementation -->

# MCP Server

> Nessus vulnerability scanning via Model Context Protocol

**↑ Parent**: [Nessus MCP Server](../README.MD)

## Quick Start

```bash
# Development
cd dev1 && docker compose up -d

# Register with Claude Code
claude mcp add --transport http nessus-mcp http://localhost:8836/mcp
```

## Directory Structure

```text
mcp-server/
├── core/           # Task management, queue, metrics
├── schema/         # Result parsing and filtering
├── scanners/       # Scanner abstraction and Nessus client
├── tools/          # MCP server and tool definitions
├── worker/         # Background scan processor
├── client/         # Python MCP client library
├── config/         # Scanner pool configuration
├── docker/         # Development Dockerfiles
├── prod/           # Production deployment
├── docs/           # Internal documentation
└── tests/          # Test suite
```

## Subdirectories

| Directory | Purpose | README |
|-----------|---------|--------|
| [core/](core/README.MD) | Task lifecycle, Redis queue, metrics | Core infrastructure |
| [schema/](schema/README.MD) | Nessus XML parsing, filtering, JSON-NL | Result processing |
| [scanners/](scanners/README.md) | Scanner interface, Nessus client, pools | Scanner abstraction |
| [tools/](tools/README.MD) | FastMCP server, MCP tool implementations | MCP server |
| [worker/](worker/README.MD) | Background scan processor | Task execution |
| [client/](client/README.MD) | NessusFastMCPClient wrapper | Python client |
| [config/](config/README.MD) | scanners.yaml configuration | Pool config |
| [docker/](docker/README.MD) | Development container images | Build files |
| [prod/](prod/README.MD) | Production deployment | Production |
| [docs/](docs/README.md) | Architecture, API, testing docs | Documentation |
| [tests/](tests/README.md) | Unit and integration tests | Test suite |

## Root-Level Files

| File | Purpose |
|------|---------|
| `requirements-api.txt` | API server dependencies |
| `requirements-worker.txt` | Worker dependencies |
| `requirements-dev.txt` | Development dependencies |

## Architecture Overview

```text
Claude Code
    │
    ↓ MCP Protocol
┌───────────────────────────────────────────────┐
│              MCP Server (FastMCP)              │
│  tools/mcp_server.py                          │
│  ┌─────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ run_scan    │ │ get_status │ │ results  │ │
│  └──────┬──────┘ └─────┬──────┘ └────┬─────┘ │
└─────────┼──────────────┼─────────────┼───────┘
          │              │             │
          ↓              ↓             ↓
     ┌────────┐    ┌───────────┐  ┌────────┐
     │ Redis  │    │   Task    │  │ Schema │
     │ Queue  │    │  Manager  │  │ Parser │
     └────────┘    └───────────┘  └────────┘
          │              │
          ↓              ↓
     ┌─────────────────────────────────────┐
     │        Scanner Worker               │
     │  worker/scanner_worker.py           │
     │  ┌────────────────────────────────┐ │
     │  │ Poll Queue → Execute → Store   │ │
     │  └────────────────────────────────┘ │
     └─────────────────────────────────────┘
                     │
                     ↓
     ┌─────────────────────────────────────┐
     │        Scanner Registry             │
     │  scanners/registry.py               │
     │  ┌────────────┐ ┌────────────┐     │
     │  │  Pool:     │ │  Pool:     │     │
     │  │  nessus    │ │  nessus_dmz│     │
     │  └────────────┘ └────────────┘     │
     └─────────────────────────────────────┘
                     │
                     ↓
     ┌─────────────────────────────────────┐
     │        Nessus Scanners              │
     │  (External - scanners-infra/)       │
     └─────────────────────────────────────┘
```

For detailed architecture including idempotency, trace IDs, state machine, data flows etc, see [docs/ARCHITECTURE_v2.2.md](docs/ARCHITECTURE_v2.2.md).

## MCP Tools

| Tool | Description |
|------|-------------|
| `run_untrusted_scan` | Network-only vulnerability scan |
| `run_authenticated_scan` | SSH authenticated scan |
| `get_scan_status` | Check scan progress |
| `get_scan_results` | Retrieve paginated results |
| `list_scanners` | List scanner instances |
| `list_pools` | List scanner pools |
| `get_pool_status` | Pool capacity info |
| `get_queue_status` | Queue metrics |
| `list_tasks` | Recent task history |

## Scan Types

| Type | Description | Tool |
|------|-------------|------|
| Untrusted | Network-only scan, no credentials | `run_untrusted_scan` |
| Authenticated | SSH user access, no privilege escalation | `run_authenticated_scan(scan_type="authenticated")` |
| Authenticated Privileged | SSH + sudo/su for root access | `run_authenticated_scan(scan_type="authenticated_privileged")` |

## Development

### Local Setup

```bash
cd mcp-server
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires services)
pytest tests/integration/ -v
```

### Docker Development

```bash
cd dev1
docker compose up -d
docker compose logs -f mcp-api
```

## Configuration

Scanner pools configured in `config/scanners.yaml`:

```yaml
nessus:
  - instance_id: scanner1
    url: https://172.30.0.3:8834
    username: nessus
    password: nessus
    max_concurrent_scans: 2
```

See [docs/SCANNER_POOLS.md](docs/SCANNER_POOLS.md) for pool configuration details.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `DATA_DIR` | `/app/data/tasks` | Task storage |
| `SCANNER_CONFIG` | `/app/config/scanners.yaml` | Pool config |
| `LOG_LEVEL` | `INFO` | Logging level |

## Operations

For monitoring, metrics, troubleshooting, and operational guidance, see [docs/MONITORING.md](docs/MONITORING.md).

Key operational features:
- Prometheus metrics at `/metrics`
- Health checks at `/health`
- Circuit breaker for scanner failure protection
- TTL housekeeping for automatic disk cleanup
- Admin CLI for queue management

## Documentation

| Document | Description |
|----------|-------------|
| [docs/ARCHITECTURE_v2.2.md](docs/ARCHITECTURE_v2.2.md) | System architecture, data flows, design decisions |
| [docs/API.md](docs/API.md) | MCP tool API reference with examples |
| [docs/SCANNER_POOLS.md](docs/SCANNER_POOLS.md) | Pool configuration and load balancing |
| [docs/MONITORING.md](docs/MONITORING.md) | Metrics, health checks, troubleshooting |
| [docs/HOUSEKEEPING.md](docs/HOUSEKEEPING.md) | Task cleanup and retention |
| [docs/TESTING.md](docs/TESTING.md) | Test suite guide |
| [tests/README.md](tests/README.md) | Detailed test documentation |
| [EXTERNAL_RESOURCES.md](docs/EXTERNAL_RESOURCES.md) | External documentation and resources |