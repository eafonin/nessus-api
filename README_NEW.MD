# Nessus MCP Server

> Model Context Protocol server for Nessus vulnerability scanning

## Quick Navigation

This file provides directory navigation for Claude Code agents. For full documentation, see [README.md](README.md).

## Directory Index

| Directory | README | Description |
|-----------|--------|-------------|
| [mcp-server/](mcp-server/) | [README_NEW.MD](mcp-server/README_NEW.MD) | Main MCP server code |
| [dev1/](dev1/) | [README.MD](dev1/README.MD) | Development deployment |
| [scanners-infra/](scanners-infra/) | [README_NEW.MD](scanners-infra/README_NEW.MD) | Nessus scanner infrastructure |
| [docs/](docs/) | [README.MD](docs/README.MD) | Reference documentation |
| [.claude/skills/](.claude/skills/) | - | Claude Code skills |

## MCP Server Subdirectories

| Directory | README | Description |
|-----------|--------|-------------|
| [mcp-server/core/](mcp-server/core/) | [README.MD](mcp-server/core/README.MD) | Core infrastructure |
| [mcp-server/scanners/](mcp-server/scanners/) | [README_NEW.MD](mcp-server/scanners/README_NEW.MD) | Scanner implementations |
| [mcp-server/tools/](mcp-server/tools/) | [README.MD](mcp-server/tools/README.MD) | MCP tools and server |
| [mcp-server/worker/](mcp-server/worker/) | [README.MD](mcp-server/worker/README.MD) | Background worker |
| [mcp-server/schema/](mcp-server/schema/) | [README.MD](mcp-server/schema/README.MD) | Result schemas |
| [mcp-server/client/](mcp-server/client/) | [README.MD](mcp-server/client/README.MD) | MCP client library |
| [mcp-server/tests/](mcp-server/tests/) | [README_NEW.MD](mcp-server/tests/README_NEW.MD) | Test suite |
| [mcp-server/config/](mcp-server/config/) | [README.MD](mcp-server/config/README.MD) | Configuration files |
| [mcp-server/docker/](mcp-server/docker/) | [README.MD](mcp-server/docker/README.MD) | Docker build files |
| [mcp-server/prod/](mcp-server/prod/) | [README.MD](mcp-server/prod/README.MD) | Production deployment |
| [mcp-server/docs/](mcp-server/docs/) | [README_NEW.MD](mcp-server/docs/README_NEW.MD) | Internal documentation |

## Claude Code Skills

| Skill | README | Description |
|-------|--------|-------------|
| [nessus-scanner/](.claude/skills/nessus-scanner/) | [README.md](.claude/skills/nessus-scanner/README.md) | Nessus scanning skill |
| [markdown-writer/](.claude/skills/markdown-writer/) | [README_NEW.MD](.claude/skills/markdown-writer/README_NEW.MD) | Documentation skill |

## Key Documentation

| Document | Path | Description |
|----------|------|-------------|
| Main README | [README.md](README.md) | Full project documentation |
| API Reference | [mcp-server/docs/API.md](mcp-server/docs/API.md) | MCP tool API |
| Architecture | [mcp-server/docs/ARCHITECTURE_v2.2.md](mcp-server/docs/ARCHITECTURE_v2.2.md) | System design |
| Scanner Pools | [mcp-server/docs/SCANNER_POOLS.md](mcp-server/docs/SCANNER_POOLS.md) | Pool configuration |
| Monitoring | [mcp-server/docs/MONITORING.md](mcp-server/docs/MONITORING.md) | Observability guide |
| Testing | [mcp-server/docs/TESTING.md](mcp-server/docs/TESTING.md) | Test guide |

## Quick Start

```bash
# Start scanner infrastructure
cd scanners-infra && docker compose up -d

# Start MCP server (development)
cd dev1 && docker compose up -d

# Register with Claude Code
claude mcp add --transport http nessus-mcp http://localhost:8836/mcp
```

## Project Structure

```
nessus-api/
├── README.md              # Full documentation
├── README_NEW.MD          # This navigation file
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

## MCP Tools

| Tool | Description |
|------|-------------|
| `run_untrusted_scan` | Network-only vulnerability scan |
| `run_authenticated_scan` | SSH authenticated scan |
| `get_scan_status` | Check scan progress |
| `get_scan_results` | Get paginated results |
| `list_scanners` | List scanner instances |
| `list_pools` | List scanner pools |
| `get_pool_status` | Pool capacity info |
| `get_queue_status` | Queue metrics |
| `list_tasks` | Recent task history |

## See Also

- [README.md](README.md) - Full project documentation
- [FastMCP Documentation](docs/fastMCPServer/INDEX.md) - Framework reference
