# Documentation

> MCP server internal documentation

## Documents

| Document | Purpose |
|----------|---------|
| [API.md](API.md) | MCP tool API reference |
| [ARCHITECTURE_v2.2.md](ARCHITECTURE_v2.2.md) | System architecture overview |
| [SCANNER_POOLS.md](SCANNER_POOLS.md) | Pool configuration guide |
| [MONITORING.md](MONITORING.md) | Observability and metrics |
| [HOUSEKEEPING.md](HOUSEKEEPING.md) | Cleanup operations |
| [PER_POOL_BACKPRESSURE.md](PER_POOL_BACKPRESSURE.md) | Queue backpressure design |
| [TESTING.md](TESTING.md) | Test suite guide |

## Quick Links

### For Developers

- **Architecture**: [ARCHITECTURE_v2.2.md](ARCHITECTURE_v2.2.md) - Component overview, data flow
- **API Reference**: [API.md](API.md) - MCP tool parameters and responses
- **Testing**: [TESTING.md](TESTING.md) - Running tests, fixtures

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
- Future target network limits

### TESTING.md

Test guide:
- Test layers
- Running tests
- Writing tests
- CI/CD integration
