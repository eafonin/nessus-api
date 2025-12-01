<!-- README Navigation -->
<!-- L1: / (Project Root) -->
<!-- Purpose: Project entry point and navigation hub -->

# Nessus MCP Server

> Model Context Protocol server for Nessus vulnerability scanning with Claude Code

**Version:** 1.0.0 | **Status:** Production Ready

## Quick Navigation

| Directory | README | Purpose |
|-----------|--------|---------|
| [mcp-server/](mcp-server/) | [README.MD](mcp-server/README.MD) | MCP server code |
| [dev1/](dev1/) | [README.MD](dev1/README.MD) | Development deployment |
| [scanners-infra/](scanners-infra/) | [README.MD](scanners-infra/README.MD) | Nessus scanner infrastructure |
| [docs/](docs/) | [README.MD](docs/README.MD) | Reference documentation |

## MCP Server Modules

| Module | README | Purpose |
|--------|--------|---------|
| [core/](mcp-server/core/) | [README.MD](mcp-server/core/README.MD) | Task manager, queue, health checks |
| [scanners/](mcp-server/scanners/) | [README.MD](mcp-server/scanners/README.MD) | Nessus client, scanner registry |
| [tools/](mcp-server/tools/) | [README.MD](mcp-server/tools/README.MD) | MCP tool implementations |
| [worker/](mcp-server/worker/) | [README.MD](mcp-server/worker/README.MD) | Background scan processor |
| [schema/](mcp-server/schema/) | [README.MD](mcp-server/schema/README.MD) | JSON-NL result conversion |
| [client/](mcp-server/client/) | [README.MD](mcp-server/client/README.MD) | MCP client library |
| [tests/](mcp-server/tests/) | [README.MD](mcp-server/tests/README.MD) | Test suite |
| [config/](mcp-server/config/) | [README.MD](mcp-server/config/README.MD) | Scanner configuration |
| [docker/](mcp-server/docker/) | [README.MD](mcp-server/docker/README.MD) | Dockerfiles |
| [prod/](mcp-server/prod/) | [README.MD](mcp-server/prod/README.MD) | Production deployment |
| [docs/](mcp-server/docs/) | [README.MD](mcp-server/docs/README.MD) | Internal documentation |

## Claude Code Skills

| Skill | README | Purpose |
|-------|--------|---------|
| [nessus-scanner/](.claude/skills/nessus-scanner/) | [README.md](.claude/skills/nessus-scanner/README.md) | Vulnerability scanning workflow |
| [markdown-writer/](.claude/skills/markdown-writer/) | [README.md](.claude/skills/markdown-writer/README.md) | Documentation generation |

## Documentation Index

| Document | Path | Description |
|----------|------|-------------|
| API Reference | [mcp-server/docs/API.md](mcp-server/docs/API.md) | MCP tool signatures |
| Architecture | [mcp-server/docs/ARCHITECTURE_v2.2.md](mcp-server/docs/ARCHITECTURE_v2.2.md) | System design |
| Scanner Pools | [mcp-server/docs/SCANNER_POOLS.md](mcp-server/docs/SCANNER_POOLS.md) | Pool configuration |
| Monitoring | [mcp-server/docs/MONITORING.md](mcp-server/docs/MONITORING.md) | Observability guide |
| Testing | [mcp-server/docs/TESTING.md](mcp-server/docs/TESTING.md) | Test guide |
| FastMCP | [docs/fastMCPServer/INDEX.md](docs/fastMCPServer/INDEX.md) | Framework reference |

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `run_untrusted_scan` | Network-only vulnerability scan (no credentials) |
| `run_authenticated_scan` | SSH authenticated scan with optional sudo |
| `get_scan_status` | Check scan progress and authentication status |
| `get_scan_results` | Paginated JSON-NL results with filtering |
| `list_scanners` | List scanner instances with load info |
| `list_pools` | List available scanner pools |
| `get_pool_status` | Pool capacity and utilization |
| `get_queue_status` | Redis queue metrics |
| `list_tasks` | Recent task history with CIDR-aware filtering |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- WireGuard VPN config (for scanner plugin updates)
- Nessus Essentials license ([free from Tenable](https://www.tenable.com/products/nessus/nessus-essentials))

### 1. Start Scanner Infrastructure

```bash
cd scanners-infra

# Configure WireGuard VPN in wg/wg0.conf
# Edit docker-compose.yml with your Nessus activation codes

docker compose up -d
# Wait 2-3 minutes for Nessus initialization
```

### 2. Start MCP Server

```bash
cd dev1
docker compose up -d
```

### 3. Register with Claude Code

```bash
claude mcp add --transport http nessus-mcp http://localhost:8836/mcp
```

### 4. Verify

```bash
claude /tools  # Should show nessus-mcp tools
```

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code                            │
│                          │                                  │
│                     MCP Protocol                            │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              MCP Server (dev1/)                      │   │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────────────┐  │   │
│  │  │ MCP API │────│  Redis  │────│ Scanner Worker  │  │   │
│  │  │ :8836   │    │ :6379   │    │                 │  │   │
│  │  └─────────┘    └─────────┘    └────────┬────────┘  │   │
│  └─────────────────────────────────────────┼───────────┘   │
│                                            │               │
│  ┌─────────────────────────────────────────┼───────────┐   │
│  │         Scanner Infrastructure          │           │   │
│  │            (scanners-infra/)            ▼           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────────────┐   │   │
│  │  │Scanner 1 │  │Scanner 2 │  │   VPN Gateway   │   │   │
│  │  │ :8834    │  │ :8834    │  │   (Gluetun)     │   │   │
│  │  └──────────┘  └──────────┘  └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Network:** `172.30.0.0/24` (nessus-shared_vpn_net)
- `172.30.0.2` VPN Gateway
- `172.30.0.3` Scanner 1
- `172.30.0.4` Scanner 2
- `172.30.0.5` MCP Worker
- `172.30.0.6` MCP API

## Configuration

### Scanner Pool Configuration

File: `mcp-server/config/scanners.yaml`

```yaml
nessus:
  - instance_id: scanner1
    name: "Nessus Scanner 1"
    url: ${NESSUS_URL:-https://172.30.0.3:8834}
    username: ${NESSUS_USERNAME:-nessus}
    password: ${NESSUS_PASSWORD:-nessus}
    enabled: true
    max_concurrent_scans: 2

  - instance_id: scanner2
    name: "Nessus Scanner 2"
    url: ${NESSUS_URL_2:-https://172.30.0.4:8834}
    username: ${NESSUS_USERNAME_2:-nessus}
    password: ${NESSUS_PASSWORD_2:-nessus}
    enabled: true
    max_concurrent_scans: 2
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `DATA_DIR` | `/app/data/tasks` | Task storage |
| `SCANNER_CONFIG` | `/app/config/scanners.yaml` | Scanner config |
| `LOG_LEVEL` | `INFO` | Logging level |

## Usage Examples

### Network Scan
```text
User: Scan 192.168.1.0/24 for vulnerabilities
Claude: [Uses run_untrusted_scan, monitors via get_scan_status, returns results]
```

### Authenticated Scan
```text
User: Run authenticated scan on 192.168.1.100 with SSH user 'admin'
Claude: [Uses run_authenticated_scan with SSH credentials]
```

### Filter Critical Vulnerabilities
```text
User: Show only critical vulnerabilities from that scan
Claude: [Uses get_scan_results with filters={"severity": "4"}]
```

## Project Structure

```text
nessus-api/
├── README.md              # This file
├── mcp-server/            # MCP server code
│   ├── core/              # Task manager, queue, health
│   ├── scanners/          # Nessus client, registry
│   ├── tools/             # MCP tool definitions
│   ├── worker/            # Background processor
│   ├── schema/            # Result conversion
│   ├── client/            # MCP client library
│   ├── tests/             # Test suite
│   ├── config/            # Scanner configuration
│   ├── docker/            # Dockerfiles
│   ├── prod/              # Production deployment
│   └── docs/              # Documentation
├── dev1/                  # Development deployment
│   ├── data/              # Task storage
│   └── logs/              # Application logs
├── scanners-infra/        # Scanner infrastructure
│   ├── nginx/             # Reverse proxy
│   └── wg/                # WireGuard VPN
├── docs/                  # Reference docs
│   └── fastMCPServer/     # FastMCP framework
└── .claude/skills/        # Claude Code skills
    ├── nessus-scanner/
    └── markdown-writer/
```

## Development

```bash
cd mcp-server
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/
```

Hot reload: `dev1/docker-compose.yml` mounts source code for development.

## License

Nessus Essentials: Free for up to 16 IPs. Get activation code at:
https://www.tenable.com/products/nessus/nessus-essentials

## Acknowledgments

- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [Nessus](https://www.tenable.com/products/nessus) - Vulnerability scanner
- [Claude Code](https://claude.ai/claude-code) - AI coding assistant
