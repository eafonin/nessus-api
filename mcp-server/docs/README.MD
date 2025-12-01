<!-- README Navigation -->
<!-- L3: mcp-server/docs/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: MCP server internal documentation index -->

# Documentation

> MCP server internal documentation index

**↑ Parent**: [MCP Server](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

For project overview, architecture diagram, and quickstart, see the [parent README](../README.md).

## Documents

| Document | Purpose |
|----------|---------|
| [API.md](API.md) | MCP tool API reference |
| [ARCHITECTURE_v2.2.md](ARCHITECTURE_v2.2.md) | System architecture overview |
| [SCANNER_POOLS.md](SCANNER_POOLS.md) | Pool configuration guide |
| [MONITORING.md](MONITORING.md) | Observability, metrics, troubleshooting |
| [HOUSEKEEPING.md](HOUSEKEEPING.md) | Task cleanup operations |
| [PER_POOL_BACKPRESSURE.md](PER_POOL_BACKPRESSURE.md) | Queue backpressure design |
| [TESTING.md](TESTING.md) | Test suite guide |
| [EXTERNAL_RESOURCES.md](EXTERNAL_RESOURCES.md) | External documentation links |

## Quick Links

### For Developers

- **Architecture**: [ARCHITECTURE_v2.2.md](ARCHITECTURE_v2.2.md) - Component overview, data flow
- **API Reference**: [API.md](API.md) - MCP tool parameters and responses
- **Testing**: [TESTING.md](TESTING.md) - Running tests, fixtures
- **External Docs**: [EXTERNAL_RESOURCES.md](EXTERNAL_RESOURCES.md) - FastMCP, Nessus API, MCP Protocol

### For Operators

- **Scanner Pools**: [SCANNER_POOLS.md](SCANNER_POOLS.md) - Adding scanners, pool configuration
- **Monitoring**: [MONITORING.md](MONITORING.md) - Prometheus metrics, health checks
- **Housekeeping**: [HOUSEKEEPING.md](HOUSEKEEPING.md) - Task cleanup, retention

### For Advanced Use

- **Backpressure**: [PER_POOL_BACKPRESSURE.md](PER_POOL_BACKPRESSURE.md) - Queue capacity management

## Document Summaries

### ARCHITECTURE_v2.2.md

System components and data flow:
- MCP server (FastMCP)
- Redis queue
- Scanner worker
- Scanner registry
- Task state machine

### API.md

MCP tool reference:
- `run_untrusted_scan` - Parameters, response format
- `run_authenticated_scan` - SSH credential handling
- `get_scan_status` - Status codes, progress
- `get_scan_results` - Filtering, pagination, JSON-NL

### SCANNER_POOLS.md

Pool configuration:
- Pool naming conventions
- Adding scanners
- Load balancing
- Multi-zone setups

### MONITORING.md

Observability:
- Prometheus metrics
- Health endpoints
- Log format
- Alerting suggestions
- Troubleshooting guide

### HOUSEKEEPING.md

Cleanup operations:
- Task expiration
- Orphan detection
- DLQ management
- Nessus scan cleanup

### PER_POOL_BACKPRESSURE.md

Queue management:
- Capacity calculation
- Per-pool limits
- Worker backpressure

### TESTING.md

Test guide:
- Test layers (unit, integration)
- Running tests
- Writing tests
- CI/CD integration

### EXTERNAL_RESOURCES.md

External documentation:
- FastMCP framework
- MCP Protocol specification
- Nessus API reference
- Redis, httpx, structlog docs

## Operational Caveats

Common operational issues and their solutions are documented in [MONITORING.md](MONITORING.md#troubleshooting):

| Issue | Symptom | Reference |
|-------|---------|-----------|
| High queue depth | Queue growing, scans delayed | [Troubleshooting](MONITORING.md#high-queue-depth) |
| Growing DLQ | Failed tasks accumulating | [Troubleshooting](MONITORING.md#growing-dlq) |
| Circuit breaker open | Scanner marked unavailable | [Troubleshooting](MONITORING.md#circuit-breaker-open) |
| Disk space | Health check warnings | [Troubleshooting](MONITORING.md#disk-space-issues) |

For circuit breaker behavior and configuration, see [Circuit Breaker](MONITORING.md#circuit-breaker).
