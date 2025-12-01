<!-- README Navigation -->
<!-- L4: mcp-server/docs/features/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Consolidated feature documentation index -->

# Features Documentation

> Consolidated feature documentation for the Nessus MCP Server

**↑ Parent**: [Documentation](../README.MD) | **↑↑ MCP Server**: [README](../../README.MD) | **↑↑↑ Root**: [Nessus MCP Server](../../../README.MD)

## Overview

This directory contains consolidated feature documentation for the Nessus MCP Server, generated from Phase 0-6 development documentation.

## Documents

| Document | Description |
|----------|-------------|
| [FEATURES.md](FEATURES.md) | Complete feature list with hierarchical organization |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, data flows, configuration |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Functional and non-functional requirements |
| [OPERATIONS.md](OPERATIONS.md) | Admin CLI, TTL housekeeping, circuit breaker, env vars |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Development practices, testing, file organization |

## Quick Links

### By Topic

- **Scanning**: [Features §1](FEATURES.md#1-vulnerability-scanning) | [Architecture: Scanner Layer](ARCHITECTURE.md#5-scanner-layer)
- **Queue**: [Features §2](FEATURES.md#2-queue-system) | [Architecture: Queue Layer](ARCHITECTURE.md#3-queue-layer)
- **Results**: [Features §3](FEATURES.md#3-results-retrieval) | [Requirements: TR4](REQUIREMENTS.md#tr4-get_scan_results)
- **Observability**: [Features §4](FEATURES.md#4-observability) | [Requirements: FR5](REQUIREMENTS.md#fr5-observability)
- **Multi-Scanner**: [Features §5](FEATURES.md#5-multi-scanner-support) | [Architecture: Configuration](ARCHITECTURE.md#configuration)
- **Operations**: [Admin CLI](OPERATIONS.md#1-admin-cli) | [Circuit Breaker](OPERATIONS.md#3-circuit-breaker) | [Env Vars](OPERATIONS.md#5-environment-variables)
- **Development**: [FastMCP Client](DEVELOPMENT.md#1-fastmcp-client-requirement) | [Testing](DEVELOPMENT.md#2-testing) | [File Locations](DEVELOPMENT.md#3-file-organization)

### By MCP Tool

| Tool | Features | Requirements |
|------|----------|--------------|
| `run_untrusted_scan` | [§1.1](FEATURES.md#11-network-scanning-untrusted) | [TR1](REQUIREMENTS.md#tr1-run_untrusted_scan) |
| `run_authenticated_scan` | [§1.2](FEATURES.md#12-authenticated-scanning) | [TR2](REQUIREMENTS.md#tr2-run_authenticated_scan) |
| `get_scan_status` | [§6.1](FEATURES.md#61-scan-status) | [TR3](REQUIREMENTS.md#tr3-get_scan_status) |
| `get_scan_results` | [§3.1](FEATURES.md#31-schema-profiles) | [TR4](REQUIREMENTS.md#tr4-get_scan_results) |
| `list_tasks` | [§2.3](FEATURES.md#23-task-management) | [TR5](REQUIREMENTS.md#tr5-list_tasks) |
| `list_scanners` | [§5.3](FEATURES.md#53-load-balancing) | [TR6](REQUIREMENTS.md#tr6-scanner-management-tools) |

## Archive

Previous documentation versions are preserved in `archive/`:
- `FEATURES.md` - Previous feature documentation
- `ARCHITECTURE_v2.3.md` - Previous architecture document

---

*Consolidated from 30 phase documents on 2025-12-01*
