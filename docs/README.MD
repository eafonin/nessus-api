<!-- README Navigation -->
<!-- L2: docs/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Reference documentation and external resources -->

# Documentation

> Reference documentation and external resources

**↑ Parent**: [Nessus MCP Server](../README.MD)

## Contents

### External References

| Directory | Description |
|-----------|-------------|
| [fastMCPServer/](fastMCPServer/README.MD) | FastMCP framework documentation |

### Project Documentation

| File | Description |
|------|-------------|
| [DOCKER_SETUP.md](DOCKER_SETUP.md) | Docker environment setup guide |
| [NESSUS_ESSENTIALS_LIMITATIONS.md](NESSUS_ESSENTIALS_LIMITATIONS.md) | Nessus Essentials scanner limitations |
| [nessus_automation_prompt.md](nessus_automation_prompt.md) | Nessus automation reference |
| [UNIFIED_MODE_IMPLEMENTATION_SUMMARY.md](UNIFIED_MODE_IMPLEMENTATION_SUMMARY.md) | Unified mode implementation notes |

## Primary Documentation

The main project documentation lives in the `mcp-server/docs/` directory:

- [API Reference](../mcp-server/docs/API.md) - MCP tool API documentation
- [Architecture](../mcp-server/docs/ARCHITECTURE_v2.2.md) - System architecture
- [Monitoring](../mcp-server/docs/MONITORING.md) - Observability guide
- [Testing](../mcp-server/docs/TESTING.md) - Test guide

See [mcp-server/docs/README.md](../mcp-server/docs/README.md) for the complete documentation index.

## Directory Structure

```
docs/
├── README.MD                              # This file
├── fastMCPServer/                         # FastMCP framework docs
│   ├── INDEX.md                           # Main index
│   ├── server.md, tools.md, etc.          # Core docs
│   ├── advanced/                          # Advanced features
│   ├── authentication/                    # Auth mechanisms
│   ├── clients/                           # Client library
│   ├── deployment/                        # HTTP deployment
│   ├── integrations/                      # Third-party
│   └── patterns/                          # Best practices
├── DOCKER_SETUP.md                        # Docker setup
├── NESSUS_ESSENTIALS_LIMITATIONS.md       # Scanner limitations
├── nessus_automation_prompt.md            # Automation reference
└── UNIFIED_MODE_IMPLEMENTATION_SUMMARY.md # Implementation notes
```

## See Also

- [MCP Server Documentation](../mcp-server/docs/README.md) - Main project docs
- [Development Environment](../dev1/README.MD) - Local development setup
