<!-- README Navigation -->
<!-- L3: mcp-server/docs/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: MCP server internal documentation index -->

# Documentation

> MCP server documentation index

**↑ Parent**: [MCP Server](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

---

## Core Documents

| Document | Purpose | Audience |
|----------|---------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, component interaction | Developers, Architects |
| [FEATURES.md](FEATURES.md) | MCP tool reference, capabilities | API Consumers, LLM Integrators |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Traceability matrix | PMs, QA, Compliance |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Docker, configuration, operations | DevOps, Operators |

---

## Reference Documents

| Document | Purpose |
|----------|---------|
| [API.md](API.md) | Detailed API reference (complementary) |
| [SCANNER_POOLS.md](SCANNER_POOLS.md) | Pool configuration deep-dive |
| [MONITORING.md](MONITORING.md) | Metrics, health checks, troubleshooting |
| [HOUSEKEEPING.md](HOUSEKEEPING.md) | TTL cleanup, stale scan management |
| [PER_POOL_BACKPRESSURE.md](PER_POOL_BACKPRESSURE.md) | Queue backpressure design |
| [TESTING.md](TESTING.md) | Test suite guide |
| [Static Analysis](../staticAnalysis/README.md) | Ruff + MyPy static code analysis |
| [EXTERNAL_RESOURCES.md](EXTERNAL_RESOURCES.md) | External documentation links |

---

## Quick Links

### For Developers

- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md) - Component overview, data flow, state machine
- **Features**: [FEATURES.md](FEATURES.md) - MCP tools, schema profiles, filtering
- **Testing**: [TESTING.md](TESTING.md) - Running tests, fixtures
- **Static Analysis**: [staticAnalysis/](../staticAnalysis/README.md) - Ruff linting, MyPy type checking
- **External Docs**: [EXTERNAL_RESOURCES.md](EXTERNAL_RESOURCES.md) - FastMCP, Nessus API, MCP Protocol

### For Operators

- **Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md) - Docker compose, environment variables
- **Scanner Pools**: [SCANNER_POOLS.md](SCANNER_POOLS.md) - Adding scanners, pool configuration
- **Monitoring**: [MONITORING.md](MONITORING.md) - Prometheus metrics, health checks
- **Housekeeping**: [HOUSEKEEPING.md](HOUSEKEEPING.md) - Task cleanup, retention

### For API Consumers

- **Features**: [FEATURES.md](FEATURES.md) - Complete tool reference with examples
- **API Reference**: [API.md](API.md) - Detailed parameter documentation

---

## Document Summaries

### ARCHITECTURE.md

System design documentation:
- Module structure and responsibilities
- Component interaction patterns
- Data flow diagrams (scan submission, result retrieval)
- Task state machine
- Key abstractions (TaskManager, ScannerRegistry, TaskQueue)

### FEATURES.md

Capability catalog for MCP consumers:
- 9 MCP tools with parameters and examples
- Scan types (untrusted, authenticated, privileged)
- Schema profiles (minimal, summary, brief, full)
- Filtering syntax and examples
- Pagination behavior
- Authentication detection
- Error responses

### REQUIREMENTS.md

Living traceability matrix:
- Functional Requirements (FR) - scan operations, status, results
- Non-Functional Requirements (NFR) - performance, reliability, observability
- Tool Requirements (TR) - per-tool checklist
- Integration Requirements (IR) - Nessus, Redis, Docker
- Future roadmap

### DEPLOYMENT.md

Operational deployment guide:
- Docker compose configurations (dev, prod)
- Environment variables reference
- Network topology
- Scanner pool configuration (scanners.yaml)
- Health checks and monitoring
- Admin CLI commands
- Troubleshooting guide

---

## Operational Caveats

Common issues documented in [MONITORING.md](MONITORING.md#troubleshooting):

| Issue | Symptom | Reference |
|-------|---------|-----------|
| High queue depth | Queue growing, scans delayed | [Troubleshooting](MONITORING.md#high-queue-depth) |
| Growing DLQ | Failed tasks accumulating | [Troubleshooting](MONITORING.md#growing-dlq) |
| Disk space | Health check warnings | [Troubleshooting](MONITORING.md#disk-space-issues) |

---

## Archive

Historical and superseded documents: [archive/](archive/)
