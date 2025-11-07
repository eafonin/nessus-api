# Nessus MCP Server Documentation

> **Project Status**: Phase 1 In Progress
> **Last Updated**: 2025-11-06

---

## 📚 Documentation Index

### Core Documentation
- [**Project README**](../README.md) - Project overview and quickstart
- [**Architecture**](../ARCHITECTURE_v2.2.md) - System architecture and design decisions
- [**Requirements**](../NESSUS_MCP_SERVER_REQUIREMENTS.md) - Complete requirements specification

### Phase Documentation
- [**Phase 0: Foundation**](../phases/PHASE_0_FOUNDATION.md) - Mock infrastructure setup ✅ COMPLETE
  - [Phase 0 Status](../phases/phase0/PHASE0_STATUS.md) - Completion report
- [**Phase 1: Real Nessus**](../phases/PHASE_1_REAL_NESSUS.md) - Nessus integration + Queue 🔄 IN PROGRESS
- [**Phase 2: Schema**](../phases/PHASE_2_SCHEMA_RESULTS.md) - Result transformation
- [**Phase 3: Observability**](../phases/PHASE_3_OBSERVABILITY.md) - Logging and monitoring
- [**Phase 4: Production**](../phases/PHASE_4_PRODUCTION.md) - Production deployment

### Component Documentation
- [**Nessus Docker Setup**](../../../docker/nessus/README.md) - Docker environment for Nessus scanner
  - [Activation Troubleshooting](../../../docker/nessus/TROUBLESHOOTING_ACTIVATION.md) - Detailed activation debugging guide
- [**Scanner Implementation**](./scanner-guide.md) - Scanner interface and implementations
- [**MCP Tools**](./tools-guide.md) - MCP tool specifications
- [**Task Management**](./task-management.md) - Task lifecycle and state machine

### Integration Guides
- [**Testing Guide**](./testing-guide.md) - Running tests and integration workflows
- [**API Guide**](./api-guide.md) - Using the Nessus MCP API
- [**Deployment Guide**](./deployment-guide.md) - Deploying to production

---

## 🏗️ Project Structure

```
nessus-api/
├── mcp-server/                    # MCP server implementation
│   ├── scanners/                  # Scanner implementations
│   │   ├── base.py               # Scanner interface
│   │   ├── nessus_scanner.py     # Real Nessus scanner ✅
│   │   ├── mock_scanner.py       # Mock scanner for testing ✅
│   │   └── registry.py           # Scanner registry ✅
│   ├── core/                      # Core business logic
│   │   ├── types.py              # Data structures and state machine ✅
│   │   ├── task_manager.py       # Task lifecycle management ✅
│   │   ├── queue.py              # Redis task queue (Phase 1)
│   │   ├── idempotency.py        # Idempotency system (Phase 1)
│   │   └── middleware.py         # Trace ID middleware (Phase 1)
│   ├── tools/                     # MCP tools
│   │   ├── mcp_server.py         # FastMCP server ✅
│   │   └── run_server.py         # Server entry point
│   ├── worker/                    # Background workers
│   │   └── scanner_worker.py     # Scan execution worker (Phase 1)
│   ├── schema/                    # Result transformation (Phase 2)
│   ├── client/                    # Test clients
│   │   └── test_client.py        # MCP test client ✅
│   ├── tests/                     # Test suites
│   │   ├── integration/          # Integration tests
│   │   └── unit/                 # Unit tests
│   ├── config/                    # Configuration files
│   │   └── scanners.yaml         # Scanner registry config ✅
│   └── docs/                      # Documentation
│       └── README.md             # This file
├── docker/nessus/                 # Nessus Docker environment
│   ├── docker-compose.yml        # Docker Compose config
│   ├── README.md                 # Nessus setup guide
│   └── wg/                       # WireGuard VPN config
└── dev1/                          # Development environment
    ├── docker-compose.yml        # Dev services (Redis, MCP API)
    └── logs/                     # Application logs
```

---

## 🚀 Quick Links

### For Developers
- [Setting up development environment](./setup-dev.md)
- [Running tests](./testing-guide.md)
- [Contributing guidelines](../CONTRIBUTING.md)

### For Operators
- [Deployment checklist](./deployment-guide.md)
- [Monitoring and alerting](./monitoring.md)
- [Troubleshooting common issues](./troubleshooting.md)

### External Resources
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Nessus API Reference](https://developer.tenable.com/docs/nessus-api)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)

---

## 📊 Implementation Progress

### Phase 0: Foundation ✅ COMPLETE
- [x] Project structure
- [x] Mock scanner
- [x] Task manager with state machine
- [x] Basic MCP tools
- [x] Docker environment
- [x] Integration tests

### Phase 1: Real Nessus 🔄 IN PROGRESS
- [x] Native async Nessus scanner
- [x] Scanner registry
- [x] Nessus scanner integration tests
- [ ] Redis task queue
- [ ] Background scanner worker
- [ ] Idempotency system
- [ ] Trace ID middleware
- [ ] Update MCP tools (queue-based)
- [ ] Phase 1 integration tests

### Phase 2: Schema & Results ⏳ PLANNED
- [ ] Result parser
- [ ] Schema transformations
- [ ] Output profiles

### Phase 3: Observability ⏳ PLANNED
- [ ] Structured logging
- [ ] Prometheus metrics
- [ ] Tracing integration

### Phase 4: Production ⏳ PLANNED
- [ ] Multi-worker deployment
- [ ] Redis Sentinel
- [ ] Production monitoring

---

## 📝 Notes

### Current Configuration
- **Nessus URL**: https://172.32.0.209:8834 (use host IP, NOT localhost)
- **Nessus Credentials**: nessus / nessus
- **MCP Server**: localhost:8835 (dev)
- **Redis**: localhost:6379
- **Transport**: SSE (Server-Sent Events)

### Network Configuration
- **Important**: Nessus runs through VPN gateway (network_mode: service)
- **Host Access**: Must use host IP (172.32.0.209), localhost connections timeout
- **Root Cause**: Docker network routing through VPN container prevents localhost binding
- **Environment**: Set `NESSUS_URL=https://172.32.0.209:8834`

### Known Issues
- SSE transport requires specific version pins (see [Phase 0 Status](../phases/phase0/PHASE0_STATUS.md))
- Nessus activation codes invalidated on volume removal
- Localhost connections to Nessus fail (use host IP instead)

---

**Last Updated**: 2025-11-06
**Contributors**: Claude Code Agent
**License**: (To be determined)
