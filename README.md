# Nessus MCP Server

> Model Context Protocol server for Nessus vulnerability scanning with Claude Code

**Version:** 1.0.0
**Status:** Production Ready

## Overview

Full-stack vulnerability scanning solution that integrates Nessus scanners with Claude Code via the Model Context Protocol (MCP). Clone, configure, and run to get AI-powered vulnerability scanning.

## Features

- **MCP Integration** - Claude Code can launch scans, check status, and analyze results
- **Dual Scanner Support** - Pool-based load balancing across multiple Nessus instances
- **Authenticated Scans** - SSH credential support for deeper vulnerability assessment
- **Async Architecture** - Redis-backed queue with background workers
- **Schema Filtering** - Configurable result detail levels (minimal/summary/brief/full)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- WireGuard VPN (for scanner plugin updates)
- Nessus Essentials license (free from [Tenable](https://www.tenable.com/products/nessus/nessus-essentials))

### 1. Start Scanner Infrastructure

```bash
cd scanners-infra

# Edit docker-compose.yml - replace activation codes with yours
# Get free codes at: https://www.tenable.com/products/nessus/nessus-essentials

# Configure WireGuard VPN in wg/wg0.conf

docker compose up -d
```

Wait 2-3 minutes for Nessus scanners to initialize.

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

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code                             │
│                          │                                   │
│                     MCP Protocol                             │
│                          ▼                                   │
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

## MCP Tools

| Tool | Description |
|------|-------------|
| `run_untrusted_scan` | Network-only vulnerability scan |
| `run_authenticated_scan` | SSH authenticated scan |
| `get_scan_status` | Check scan progress |
| `get_scan_results` | Get paginated results with filtering |
| `list_scanners` | List scanner instances |
| `list_pools` | List scanner pools |
| `get_pool_status` | Pool capacity info |
| `get_queue_status` | Queue metrics |
| `list_tasks` | Recent task history |

## Usage Examples

### Basic Network Scan

```
User: Scan 192.168.1.0/24 for vulnerabilities
Claude: [Uses run_untrusted_scan, monitors status, returns top vulnerabilities]
```

### Authenticated Scan

```
User: Run an authenticated scan on 192.168.1.100 with user 'admin'
Claude: [Asks for password, uses run_authenticated_scan with SSH credentials]
```

### Filter Results

```
User: Show me only critical vulnerabilities from that scan
Claude: [Uses get_scan_results with filters={"severity": "4"}]
```

## Project Structure

```
nessus-api/
├── scanners-infra/       # Nessus scanner infrastructure
│   ├── docker-compose.yml
│   ├── nginx/            # Reverse proxy
│   └── wg/               # WireGuard VPN config
│
├── mcp-server/           # MCP server code
│   ├── core/             # Task manager, state machine
│   ├── scanners/         # Nessus client, registry
│   ├── tools/            # MCP tool implementations
│   ├── worker/           # Background processor
│   ├── schema/           # Results conversion
│   ├── client/           # MCP client
│   ├── tests/            # Test suite
│   ├── docker/           # Dockerfiles
│   ├── config/           # Scanner configuration
│   ├── prod/             # Production deployment
│   └── docs/             # Documentation
│
├── dev1/                 # Development deployment
│   └── docker-compose.yml
│
├── docs/
│   └── fastMCPServer/    # FastMCP framework reference
│
└── .claude/skills/       # Claude Code skills
    ├── nessus-scanner/
    └── markdown-writer/
```

## Configuration

### Scanner Configuration

Edit `mcp-server/config/scanners.yaml`:

```yaml
pools:
  nessus:
    scanner_type: nessus
    instances:
      scanner1:
        url: https://172.30.0.3:8834
        username: nessus
        password: nessus
        max_concurrent_scans: 5
      scanner2:
        url: https://172.30.0.4:8834
        username: nessus
        password: nessus
        max_concurrent_scans: 5
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_CONCURRENT_SCANS` | `5` | Per-scanner limit |

## Documentation

- [API Reference](mcp-server/docs/API.md)
- [Architecture](mcp-server/docs/ARCHITECTURE_v2.2.md)
- [Scanner Pools](mcp-server/docs/SCANNER_POOLS.md)
- [Monitoring](mcp-server/docs/MONITORING.md)
- [Testing](mcp-server/docs/TESTING.md)

## Development

### Setup

```bash
cd mcp-server
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

### Run Tests

```bash
pytest tests/
```

### Hot Reload Development

The `dev1/docker-compose.yml` mounts source code for hot reload during development.

## License

Nessus Essentials is free for up to 16 IPs. Get your activation code at:
https://www.tenable.com/products/nessus/nessus-essentials

## Acknowledgments

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [Nessus](https://www.tenable.com/products/nessus) - Vulnerability scanner
- [Claude Code](https://claude.ai/claude-code) - AI coding assistant
