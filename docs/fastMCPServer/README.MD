<!-- README Navigation -->
<!-- L3: docs/fastMCPServer/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: FastMCP framework reference documentation -->

# FastMCP Server Documentation

> External reference documentation for the FastMCP framework

**↑ Parent**: [Documentation](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

## Overview

This directory contains comprehensive documentation for FastMCP, the Python framework used to build the Nessus MCP Server. These docs are reference material from the FastMCP project.

## Main Index

See **[INDEX.md](INDEX.md)** for the complete documentation index with:
- Quick start guides for common tasks
- Detailed topic reference for all components
- Search tips and file organization

## Core Documents

| Document | Description |
|----------|-------------|
| [INDEX.md](INDEX.md) | Main documentation index |
| [server.md](server.md) | Core server documentation |
| [tools.md](tools.md) | Tool creation and usage |
| [resources.md](resources.md) | Resource exposure |
| [prompts.md](prompts.md) | Prompt templates |

## Subdirectories

| Directory | README | Description |
|-----------|--------|-------------|
| [advanced/](advanced/) | [README.MD](advanced/README.MD) | Advanced server features |
| [authentication/](authentication/) | [README.MD](authentication/README.MD) | Auth mechanisms |
| [clients/](clients/) | [README.MD](clients/README.MD) | Client library docs |
| [deployment/](deployment/) | [README.MD](deployment/README.MD) | HTTP deployment guides |
| [integrations/](integrations/) | [README.MD](integrations/README.MD) | Third-party integrations |
| [patterns/](patterns/) | [README.MD](patterns/README.MD) | Best practices |

## Directory Structure

```
fastMCPServer/
├── INDEX.md              # Main documentation index
├── server.md             # Core server documentation
├── tools.md              # Tool creation and usage
├── resources.md          # Resource exposure
├── prompts.md            # Prompt templates
├── advanced/             # Advanced server features
├── authentication/       # Auth mechanisms
├── clients/              # Client library docs
├── deployment/           # HTTP deployment guides
├── integrations/         # Third-party integrations
└── patterns/             # Best practices
```

## Key Topics for This Project

| Topic | File | Relevance |
|-------|------|-----------|
| HTTP Deployment | [deployment/http-deployment.md](deployment/http-deployment.md) | MCP API server setup |
| Tool Creation | [tools.md](tools.md) | MCP tool definitions |
| Client Usage | [clients/client.md](clients/client.md) | Test client implementation |
| Transports | [clients/transports.md](clients/transports.md) | SSE transport configuration |
| Context | [advanced/context.md](advanced/context.md) | Request context and logging |
| Progress | [advanced/server-progress.md](advanced/server-progress.md) | Scan progress reporting |

## See Also

- [MCP Server Tools](../../mcp-server/tools/README.MD) - Project tool implementations
- [MCP Server README](../../mcp-server/README.md) - Main server documentation
