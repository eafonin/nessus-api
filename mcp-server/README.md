# Nessus MCP Server - Implementation Tracker

> **Status**: 🚧 In Development
> **Current Phase**: Phase 3 - Observability & Testing (~70% Complete)
> **Phase 0**: ✅ Completed (2025-11-06)
> **Phase 1**: ✅ Completed (2025-11-07) - Real Nessus Integration + Queue
> **Phase 2**: ✅ Completed (2025-11-07) - Schema System & Results
> **Phase 3**: 🟡 In Progress (~70%) - Observability & Testing
> **Last Updated**: 2025-11-10

---

## 📋 Quick Navigation

### Implementation Phases
- [Phase 0: Foundation & Mock Infrastructure](./phases/PHASE_0_FOUNDATION.md) ✅ **COMPLETED** - [Status Report](./phases/phase0/PHASE0_STATUS.md)
- [Phase 1A: Scanner Rewrite](./phases/PHASE_1A_SCANNER_REWRITE.md) ✅ **COMPLETED** - [Completion Report](./phases/PHASE_1A_COMPLETION_REPORT.md)
- [Phase 1: Real Nessus Integration + Queue](./phases/PHASE_1_REAL_NESSUS.md) ⬅️ **IN PROGRESS**
- [Phase 2: Schema System & Results](./phases/PHASE_2_SCHEMA_RESULTS.md)
- [Phase 3: Observability & Testing](./phases/PHASE_3_OBSERVABILITY.md)
- [Phase 4: Production Hardening](./phases/PHASE_4_PRODUCTION.md)

### Phase 0 Completion Documents
- [Phase 0 Status Report](./phases/phase0/PHASE0_STATUS.md) - Complete implementation summary
- [Bug Fix Guide](./phases/phase0/FINAL_MINIMAL_CHANGES.md) - Task group initialization fix
- [Fix Summary](./phases/phase0/MINIMAL_FIX_SUMMARY.md) - Quick reference

### Phase 1A Completion Documents
- [Phase 1A Completion Report](./phases/PHASE_1A_COMPLETION_REPORT.md) - Scanner rewrite summary and validation
- [Nessus HTTP Patterns](./scanners/NESSUS_HTTP_PATTERNS.md) - Extracted patterns from proven wrapper code
- [Docker Network Configuration](./docs/DOCKER_NETWORK_CONFIG.md) - Network topology and URL configuration guide

### Key Documents
- **[Architecture v2.2](./docs/ARCHITECTURE_v2.2.md)** ⭐ - Complete technical design (READ THIS for design decisions)
  - Section 2: Idempotency System (duplicate scan prevention)
  - Section 3: Trace ID System (per-request tracking)
  - Section 4: State Machine Enforcement (valid transitions)
  - Section 5: Native Async Nessus Scanner (no subprocess calls)
  - Section 9: JSON-NL Converter (LLM-friendly results format)
- **[Requirements](./docs/NESSUS_MCP_SERVER_REQUIREMENTS.md)** - Functional requirements and acceptance criteria
- **[Test Suite](./tests/README.md)** ⭐ - Layered test architecture (unit → integration → E2E)
- **[Phase Status Tracking Guide](./phases/README.md)** - How to track and document implementation progress across phases
- **[Archived Docs](./archive/)** - Previous architecture versions and superseded guides

### FastMCP Client Documentation
- **[FastMCP Client Requirement](./docs/FASTMCP_CLIENT_REQUIREMENT.md)** ⚠️ **MANDATORY** - All future development MUST use FastMCP client
- **[FastMCP Client Architecture](./docs/FASTMCP_CLIENT_ARCHITECTURE.md)** - Complete architecture with detailed data flows
- **[Client Implementation](./client/nessus_fastmcp_client.py)** - Source code with 10 high-level methods
- **[Client Examples](./client/examples/README.md)** - 5 progressive examples from basic to full workflow
- **[Client Tests](./tests/integration/test_fastmcp_client.py)** - Integration test suite (8 test classes)

### Related Resources
- [Existing Nessus Scripts](../nessusAPIWrapper/) - Reference implementations (for comparison testing)
- [FastMCP Documentation](../docs/fastMCPServer/INDEX.md) - Framework guide

---

## 🎯 Project Overview

### What We're Building

An **MCP (Model Context Protocol) server** that exposes Nessus vulnerability scanning capabilities to AI agents with:

- **Async Task Queue**: Non-blocking scan submission with Redis-based FIFO queue
- **Three Scan Types**: Untrusted (network-only), Trusted (SSH), Privileged (sudo/root)
- **Pluggable Scanners**: Abstract interface supporting multiple scanner backends
- **LLM-Optimized Results**: JSON-NL format with flexible schemas and filtering
- **Production-Grade**: Idempotency, trace IDs, state machines, observability

### Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Code Strategy** | Pure async rewrite (no subprocess) | Clean, maintainable, async-first |
| **Environment** | Separate dev1/ and prod/ directories | Isolation, safe testing |
| **Scanner Interface** | Pluggable (Nessus-only Phase 1) | Future extensibility |
| **Development Approach** | Mock-first → Real integration | Fast iteration, reliable tests |
| **Client Evolution** | Simple HTTP → FastMCP SDK | Progressive complexity |
| **Testing Strategy** | Hybrid (integration → unit) | Practical, fast feedback |
| **Configuration** | YAML with hot-reload (SIGHUP) | Flexible, no downtime |
| **Deployment** | Docker image tags (dev→prod) | Rollback capability |

---

## 📊 Overall Progress Tracker

### Quick Status

- ✅ **Phase 0**: Complete (2025-11-06) - Foundation & Mock Infrastructure
- ✅ **Phase 1**: Complete (2025-11-07) - Real Nessus Integration + Queue
- ✅ **Phase 2**: Complete (2025-11-07) - Schema System & Results (25/25 tests passing)
- 🟡 **Phase 3**: ~70% Complete - Observability infrastructure done, tests need expansion
- 🔴 **Phase 4**: Not Started - Production Hardening

**See**: [phases/README.md](./phases/README.md) for detailed status tracking guide.

---

### Phase Completion Status

- [x] **Phase 0**: Foundation & Mock Infrastructure ✅ (Completed 2025-11-06)
  - [x] 0.1: Project Structure Setup
  - [x] 0.2: Core Data Structures
  - [x] 0.3: Mock Scanner Implementation
  - [x] 0.4: Task Manager (Simplified)
  - [x] 0.5: Simple MCP Tool
  - [x] 0.6: Development Docker Setup
  - [x] 0.7: Simple Test Client
  - [x] 0.8: Phase 0 Integration Test

- [x] **Phase 1**: Real Nessus Integration + Queue ✅ (Completed 2025-11-07)
  - [x] 1.1: Native Async Nessus Scanner (scanners/nessus_scanner.py - 604 lines)
  - [x] 1.2: Scanner Registry & Configuration (scanners/registry.py - 223 lines)
  - [x] 1.3: Redis Queue Implementation (core/queue.py - 294 lines)
  - [x] 1.4: Worker with State Machine (worker/scanner_worker.py - 392 lines)
  - [x] 1.5: Idempotency System (core/idempotency.py - 120 lines) - SHA256 + Redis SETNX
  - [x] 1.6: Trace ID Middleware (core/middleware.py - 25 lines)
  - [x] 1.7: Enhanced MCP Tools (6 tools: run_untrusted_scan, get_scan_status, list_scanners, get_queue_status, list_tasks, get_scan_results)
  - [x] 1.8: Real Nessus Integration Tests (test_phase0_phase1_real_nessus.py)

- [x] **Phase 2**: Schema System & Results ✅ (Completed 2025-11-07)
  - [x] 2.1: Schema Profiles Definition (4 profiles: minimal/summary/brief/full)
  - [x] 2.2: Nessus XML Parser (schema/parser.py - 73 lines)
  - [x] 2.3: JSON-NL Converter (schema/converter.py - 114 lines)
  - [x] 2.4: Generic Filtering Engine (schema/filters.py - 72 lines)
  - [x] 2.5: Pagination Logic (page=0 for all, or page_size chunks)
  - [x] 2.6: Results Retrieval Tool (get_scan_results MCP tool)
  - [x] 2.7: Schema Tests ✅ **25/25 PASSED**

- [ ] **Phase 3**: Observability & Testing (Week 3)
  - [x] 3.1: Structured Logging (structlog)
  - [x] 3.2: Prometheus Metrics
  - [x] 3.3: Health Check Endpoints
  - [ ] 3.4: Unit Test Suite
  - [ ] 3.5: Integration Test Suite
  - [x] 3.6: FastMCP SDK Client ✅ **COMPLETE** (NessusFastMCPClient + 5 examples + tests)

- [ ] **Phase 4**: Production Hardening (Week 4)
  - [ ] 4.1: Production Docker Config
  - [ ] 4.2: TTL Housekeeping
  - [ ] 4.3: Dead Letter Queue Handler
  - [ ] 4.4: Import Linting
  - [ ] 4.5: Error Recovery
  - [ ] 4.6: Load Testing
  - [ ] 4.7: Documentation
  - [ ] 4.8: Deployment Guide

---

## 🏗️ Project Structure

```
/home/nessus/projects/nessus-api/
├── nessusAPIWrapper/           # Existing scripts (reference only)
├── docs/                       # General documentation
├── mcp-server/                 # 🎯 MCP Server (source + docs)
│   ├── README.md              # This file - START HERE
│   ├── ARCHITECTURE_v2.2.md   # Complete design reference
│   ├── NESSUS_MCP_SERVER_REQUIREMENTS.md  # Functional requirements
│   │
│   ├── phases/                # Implementation phase guides
│   │   ├── PHASE_0_FOUNDATION.md
│   │   ├── PHASE_1_REAL_NESSUS.md
│   │   ├── PHASE_2_SCHEMA_RESULTS.md
│   │   ├── PHASE_3_OBSERVABILITY.md
│   │   ├── PHASE_4_PRODUCTION.md
│   │   └── phase0/            # Phase 0 completion artifacts
│   │       ├── PHASE0_STATUS.md
│   │       ├── FINAL_MINIMAL_CHANGES.md
│   │       └── MINIMAL_FIX_SUMMARY.md
│   │
│   ├── archive/               # Superseded documentation
│   │
│   ├── scanners/              # Scanner abstraction layer
│   │   ├── base.py            # ScannerInterface (abstract)
│   │   ├── mock_scanner.py    # Mock for testing (Phase 0)
│   │   ├── nessus_scanner.py  # Real Nessus async (Phase 1)
│   │   └── registry.py        # Multi-instance registry (Phase 1)
│   │
│   ├── core/                  # Core functionality
│   │   ├── types.py           # Data structures, state machine
│   │   ├── task_manager.py    # Task lifecycle management
│   │   ├── queue.py           # Redis FIFO queue (Phase 1)
│   │   ├── idempotency.py     # Duplicate prevention (Phase 1)
│   │   └── middleware.py      # Trace IDs (Phase 1)
│   │
│   ├── schema/                # Results schema & conversion
│   │   ├── profiles.py        # Schema definitions (Phase 2)
│   │   ├── parser.py          # Nessus XML parser (Phase 2)
│   │   ├── converter.py       # JSON-NL converter (Phase 2)
│   │   └── filters.py         # Generic filtering (Phase 2)
│   │
│   ├── tools/                 # MCP tool implementations
│   │   └── mcp_server.py      # FastMCP server + all tools
│   │
│   ├── worker/                # Background scanner worker
│   │   └── scanner_worker.py  # Queue consumer (Phase 1)
│   │
│   ├── client/                # FastMCP client (Phase 3)
│   │   ├── nessus_fastmcp_client.py  # Production FastMCP client (MANDATORY)
│   │   ├── examples/          # 5 progressive usage examples
│   │   │   ├── 01_basic_usage.py
│   │   │   ├── 02_wait_for_completion.py
│   │   │   ├── 03_scan_and_wait.py
│   │   │   ├── 04_get_critical_vulns.py
│   │   │   ├── 05_full_workflow.py
│   │   │   └── README.md
│   │   └── test_client.py     # Legacy simple HTTP client (deprecated)
│   │
│   ├── tests/                 # Test suite
│   │   ├── README.md          # ⭐ Test documentation (START HERE for testing)
│   │   ├── run_test_pipeline.sh  # Automated test runner
│   │   ├── conftest.py        # Shared pytest fixtures
│   │   ├── fixtures/          # Mock .nessus files
│   │   ├── unit/              # Layer 1: Unit tests (49 tests)
│   │   └── integration/       # Layers 2-4: Integration + E2E tests
│   │
│   ├── config/                # Configuration files
│   │   └── scanners.yaml      # Scanner instances (Phase 1)
│   │
│   ├── Dockerfile.api         # API service image
│   ├── Dockerfile.worker      # Worker service image
│   ├── docker-compose.yml     # Dev compose (Phase 0)
│   ├── requirements-*.txt     # Python dependencies
│   └── pyproject.toml         # Import linter config
│
├── dev1/                      # 🆕 Development environment (Phase 0)
│   ├── docker-compose.yml     # Dev-specific overrides
│   ├── .env.dev               # Dev environment vars
│   ├── data/                  # Dev task storage
│   └── logs/                  # Dev logs
│
└── prod/                      # 🆕 Production environment (Phase 4)
    ├── docker-compose.yml     # Prod-specific config
    ├── .env.prod              # Prod environment vars
    ├── data/                  # Prod task storage
    └── logs/                  # Prod logs
```

---

## 🔧 Core Concepts

### 1. Pluggable Scanner Architecture

**Design Pattern**: Strategy Pattern with Abstract Interface

```python
# scanners/base.py
class ScannerInterface(ABC):
    @abstractmethod
    async def create_scan(self, request: ScanRequest) -> int: ...
    @abstractmethod
    async def launch_scan(self, scan_id: int) -> str: ...
    @abstractmethod
    async def get_status(self, scan_id: int) -> Dict: ...
    @abstractmethod
    async def export_results(self, scan_id: int) -> bytes: ...
```

**Benefits**:
- Swap Nessus for OpenVAS without changing tools
- Mock scanner for testing
- Multiple instances of same scanner type

**Registry Pattern**:
```python
# scanners/registry.py
registry = ScannerRegistry()
registry.register("nessus", "prod", NessusScanner(...))
scanner = registry.get_instance("nessus", "prod")
```

### 2. State Machine Enforcement

**Valid Transitions**:
```
QUEUED ──────┬─→ RUNNING ──────┬─→ COMPLETED (terminal)
             │                 ├─→ FAILED (terminal)
             │                 └─→ TIMEOUT (terminal)
             └─→ FAILED (terminal)
```

**Single Writer Pattern**: TaskManager is the ONLY component that can update task status

**File Locking**: Uses `fcntl` to prevent concurrent writes

### 3. Async Task Queue

**Flow**:
```
Agent → MCP Tool → Redis Queue → Worker → Scanner → Results
  │                    │            │         │
  └─ Immediate        FIFO       Serial    Async
     Response                   Processing  Polling
```

**Redis Keys**:
- `nessus:queue` - Pending tasks (LPUSH/BRPOP)
- `nessus:queue:dead` - Failed tasks (sorted set)
- `idemp:{key}` - Idempotency mappings (48h TTL)

### 4. JSON-NL Result Format

**Structure**:
```json
{"type": "schema", "profile": "brief", "fields": [...], "filters_applied": {...}}
{"type": "scan_metadata", "task_id": "...", "scan_name": "...", ...}
{"type": "vulnerability", "host": "...", "plugin_id": 123, "severity": "Critical", ...}
{"type": "vulnerability", "host": "...", "plugin_id": 456, "severity": "High", ...}
{"type": "pagination", "page": 1, "total_pages": 5, "next_page": 2}
```

**Benefits**:
- Streamable (one line at a time)
- Self-describing (schema + data)
- Filter transparency (LLM can reason about applied filters)
- Bounded memory (pagination)

### 5. Two-Environment Strategy

**Development** (`dev1/`):
- Hot reload (volume mount source code)
- Debug logging
- Mock scanner for fast iteration
- Port 8835

**Production** (`prod/`):
- Built Docker images (nessus-mcp:prod tag)
- Info logging
- Real Nessus only
- Port 8836 (can run alongside dev)

**Migration**: `docker tag nessus-mcp:dev nessus-mcp:prod`

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose installed
- Python 3.11+ (for local development)
- Access to Nessus instance (URL, credentials)
- Git repository cloned

### Quick Start (Phase 0)

```bash
# 1. Create directories
cd /home/nessus/projects/nessus-api
mkdir -p dev1 prod mcp-server-source

# 2. Follow Phase 0 guide (✅ COMPLETED)
# See phases/PHASE_0_FOUNDATION.md for reference

# 3. Start development environment
cd dev1
docker compose up --build

# 4. Test with simple client
python ../mcp-server-source/client/test_client.py
```

---

## 📝 Session Checklist (For Claude Code)

When starting a new coding session, use this checklist:

### Session Start
- [ ] Read this README.md completely
- [ ] Check current phase status (see Progress Tracker above)
- [ ] Review open phase document (PHASE_X_*.md)
- [ ] Check git status for uncommitted changes
- [ ] Verify dev environment is running (`docker compose ps`)

### During Session
- [ ] Update task checkboxes in phase document as completed
- [ ] Run tests after each component (`pytest tests/`)
- [ ] Check import boundaries (`import-linter`)
- [ ] Commit working code frequently (small, logical commits)
- [ ] Update this README if progress milestones reached

### Session End
- [ ] Update "Last Updated" date in this README
- [ ] Mark completed tasks in Progress Tracker
- [ ] Commit all changes with descriptive message
- [ ] Note any blockers or next steps in phase document
- [ ] Push to remote if significant progress made

---

## 🧪 Testing

> **Full documentation**: [Test Suite README](./tests/README.md)

### Quick Test Commands

```bash
# Quick validation (~20 seconds, 103 tests)
docker compose exec mcp-api pytest tests/unit/ tests/integration/test_phase0.py \
  tests/integration/test_phase2.py tests/integration/test_fastmcp_client_smoke.py -q

# Run test pipeline
docker compose exec mcp-api tests/run_test_pipeline.sh --quick

# Full pipeline with E2E (5-10 minutes)
docker compose exec mcp-api tests/run_test_pipeline.sh --full
```

### Test Layers

| Layer | Tests | Time | Command |
|-------|-------|------|---------|
| Unit | 49 | <1s | `pytest tests/unit/ -v` |
| Infrastructure | 28 | ~5s | `pytest tests/integration/test_phase0.py -v` |
| Integration | 42 | ~2m | `pytest tests/integration/test_phase1.py tests/integration/test_phase2.py -v` |
| E2E | 2 | ~10m | `pytest tests/integration/test_fastmcp_client_e2e.py -v` |

### ⚠️ MANDATORY: Use FastMCP Client

**All testing MUST use the FastMCP Client:**

```python
# ✅ CORRECT - Use FastMCP Client
from client.nessus_fastmcp_client import NessusFastMCPClient

async with NessusFastMCPClient("http://localhost:8835/mcp") as client:
    task = await client.submit_scan(targets="192.168.1.1", scan_name="Test")
    status = await client.get_status(task["task_id"])
```

See [FASTMCP_CLIENT_REQUIREMENT.md](./docs/FASTMCP_CLIENT_REQUIREMENT.md) for details.

### Quick Examples

```bash
# Run basic client example
python client/examples/01_basic_usage.py

# Run full workflow example
python client/examples/05_full_workflow.py

# See all examples
ls -l client/examples/
```

---

## 📦 Build & Deployment

### Development Build
```bash
cd dev1
docker compose up --build
```

### Production Promotion
```bash
# Build and tag as dev
cd /home/nessus/projects/nessus-api/mcp-server-source
docker build -t nessus-mcp:dev -f Dockerfile.api .

# Test in dev environment
cd ../dev1
docker compose up

# Promote to production
docker tag nessus-mcp:dev nessus-mcp:prod

# Deploy to prod
cd ../prod
docker compose up -d
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue**: Docker containers not starting
- Check: `docker compose logs -f`
- Verify: Redis healthcheck passing
- Check: Port 8835/8836 not already in use

**Issue**: Mock scanner not responding
- Verify: Fixtures directory exists (`tests/fixtures/`)
- Check: sample_scan.nessus file present
- Review: Container logs for exceptions

**Issue**: Task status stuck in "queued"
- Check: Worker container running (`docker compose ps`)
- Verify: Redis queue has items (`redis-cli LLEN nessus:queue`)
- Review: Worker logs for errors

**Issue**: Import errors between modules
- Run: `import-linter` to check boundaries
- Verify: All `__init__.py` files present
- Check: Python path in Docker container

---

## 📚 Key Requirements Summary

### Functional Requirements

**FR-1: Three Scan Workflows**
- Untrusted (network-only, no credentials)
- Trusted (SSH user access, no escalation)
- Privileged (SSH + sudo/su/pbrun for root access)

**FR-2: Async Task Management**
- Non-blocking scan submission (<1s response)
- Redis FIFO queue for serialization
- Status polling with progress updates
- 24-hour timeout for long scans

**FR-3: Schema Flexibility**
- Four predefined profiles: minimal, summary, brief, full
- Custom field selection (mutually exclusive with profiles)
- Generic filtering on any attribute
- Pagination (10-100 lines/page, or page=0 for all)

**FR-4: Multi-Scanner Support**
- Abstract ScannerInterface
- Scanner registry with instances
- Round-robin load balancing
- Scanner health checks

**FR-5: Observability**
- Structured JSON logs with trace IDs
- Prometheus metrics (/metrics endpoint)
- Health checks for Redis, disk, scanners
- State machine validation logging

### Non-Functional Requirements

**NFR-1: Simplicity** (Priority: Highest)
- File system storage (no database)
- Redis for queue/registry only
- Clear separation of concerns
- Minimal dependencies

**NFR-2: Multi-Agent Collaboration**
- Shared state (all agents see all scans)
- No tenant isolation
- Concurrent submissions handled by queue

**NFR-3: Performance** (Priority: Low for Phase 1)
- Scan submission: <1s
- Status polling: <500ms
- Result pagination: <2s
- Handle 10+ concurrent agents

**NFR-4: Security**
- Bearer token authentication (HTTP)
- Scanner credentials in environment variables
- Password masking in responses
- No per-user access control (trusted system)

---

## 🔗 External Resources

- **FastMCP Framework**: https://github.com/jlowin/fastmcp
- **Nessus API Docs**: https://developer.tenable.com/reference/navigate
- **MCP Protocol Spec**: https://spec.modelcontextprotocol.io/
- **Redis Documentation**: https://redis.io/docs/
- **Prometheus Python Client**: https://github.com/prometheus/client_python

---

## 📞 Contact & Support

**Project Owner**: User (eafonin)
**Repository**: https://github.com/eafonin/nessus-api
**Branch**: main
**Environment**: Ubuntu 24.04 LTS, Docker, Python 3.12

---

## 🎯 Next Steps

1. **Phase 0 Complete**: See [completion report](./phases/phase0/PHASE0_STATUS.md) for details
2. **Starting Phase 1**: Read [PHASE_1_REAL_NESSUS.md](./phases/PHASE_1_REAL_NESSUS.md)
3. **If resuming**: Check Progress Tracker above, jump to current phase
4. **If blocked**: Review Troubleshooting section, check phase document for notes

---

**Remember**: Update this README after each significant milestone! 🚀
