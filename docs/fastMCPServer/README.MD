# FastMCP Server Documentation

> External reference documentation for the FastMCP framework

## Overview

This directory contains comprehensive documentation for FastMCP, the Python framework used to build the Nessus MCP Server. These docs are reference material from the FastMCP project.

## Main Index

See **[INDEX.md](INDEX.md)** for the complete documentation index with:
- Quick start guides for common tasks
- Detailed topic reference for all components
- Search tips and file organization

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
