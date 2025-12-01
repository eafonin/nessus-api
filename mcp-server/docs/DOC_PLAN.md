# Documentation Rewrite Plan - MCP Server

> **Status**: COMPLETED
> **Last Updated**: 2025-12-01
> **Completed**: 2025-12-01
> **Location**: `mcp-server/docs/`

---

## Overview

This plan defines scope, tasks, and deliverables for rewriting three core documentation files:
1. **ARCHITECTURE.md** - System design and component interaction
2. **FEATURES.md** - Capability catalog with usage examples
3. **REQUIREMENTS.md** - Living traceability matrix

Plus one new document:
4. **DEPLOYMENT.md** - Docker, configuration, and operations

---

## Document Scope Definitions

### 1. ARCHITECTURE.md

**Purpose**: Technical system design for developers and architects understanding the system.

**Audience**: New developers, system architects, code reviewers.

**Scope** (INCLUDE):
- [ ] System overview diagram (ASCII)
- [ ] Component list with responsibilities
- [ ] Data flow diagrams (scan submission, result retrieval)
- [ ] State machine (task lifecycle)
- [ ] Module structure (`core/`, `scanners/`, `schema/`, `tools/`, `worker/`)
- [ ] Inter-component communication patterns
- [ ] Key abstractions (TaskManager, ScannerRegistry, TaskQueue)

**Scope** (EXCLUDE - goes to DEPLOYMENT.md):
- Docker compose configurations
- Environment variables
- Port mappings
- Network topology
- Operational commands

**Source of Truth**:
- `tools/mcp_server.py` - MCP tool definitions
- `core/task_manager.py` - Task lifecycle
- `core/queue.py` - Queue operations
- `scanners/registry.py` - Scanner pool management
- `worker/scanner_worker.py` - Worker loop
- `schema/` - Result transformation pipeline

**Target Size**: ~300-400 lines

---

### 2. FEATURES.md

**Purpose**: Comprehensive capability catalog for MCP consumers and integrators.

**Audience**: API consumers, LLM integrators, security engineers using the MCP tools.

**Scope** (INCLUDE):
- [ ] MCP tool reference (9 tools with parameters, return types)
- [ ] Scan types explained (untrusted, authenticated, authenticated_privileged)
- [ ] Schema profiles (minimal, summary, brief, full) with field lists
- [ ] Filtering syntax and examples
- [ ] Pagination behavior
- [ ] Authentication detection (plugin IDs, status values)
- [ ] Idempotency behavior
- [ ] Queue position and wait time estimation
- [ ] Error responses and troubleshooting hints
- [ ] Use case examples (code snippets)
- [ ] Limitations and constraints

**Scope** (EXCLUDE):
- Internal implementation details
- Docker/deployment
- Architecture diagrams

**Source of Truth**:
- `tools/mcp_server.py` - Tool docstrings and signatures
- `schema/profiles.py` - Schema profile definitions
- `schema/filters.py` - Filter syntax
- `scanners/nessus_validator.py` - Auth detection plugins
- `client/examples/` - Usage examples

**Target Size**: ~500-600 lines

---

### 3. REQUIREMENTS.md

**Purpose**: Living traceability matrix linking requirements to implementation.

**Audience**: Project managers, QA engineers, compliance reviewers.

**Scope** (INCLUDE):
- [ ] Functional Requirements (FR) with status
- [ ] Non-Functional Requirements (NFR) with targets and actuals
- [ ] MCP Tool Requirements (TR) - per-tool requirement checklist
- [ ] Integration Requirements (IR) - Nessus, Redis, Docker
- [ ] Test Requirements (TestR) - coverage targets
- [ ] Dependency Requirements - pinned versions with rationale
- [ ] Future Roadmap (planned but not implemented)

**Scope** (EXCLUDE):
- Historical phase documentation
- Implementation details
- How-to guides

**Source of Truth**:
- `tools/mcp_server.py` - Implemented tool capabilities
- `requirements-api.txt`, `requirements-worker.txt` - Dependencies
- `tests/` - Test coverage
- `pyproject.toml` - Version constraints

**Target Size**: ~250-350 lines

---

### 4. DEPLOYMENT.md (NEW)

**Purpose**: Deployment, configuration, and operational guidance.

**Audience**: DevOps engineers, operators, anyone deploying the system.

**Scope** (INCLUDE):
- [ ] Docker Compose configurations (dev, prod)
- [ ] Environment variables reference
- [ ] Network topology (ASCII diagram)
- [ ] Port mappings
- [ ] Volume mounts
- [ ] Scanner pool configuration (`scanners.yaml`)
- [ ] Health checks and monitoring endpoints
- [ ] Admin CLI commands (DLQ, stats)
- [ ] TTL housekeeping configuration
- [ ] Circuit breaker configuration
- [ ] Troubleshooting guide
- [ ] Quick start commands

**Scope** (EXCLUDE):
- Architecture internals
- Feature usage
- Requirements traceability

**Source of Truth**:
- `dev1/docker-compose.yml` - Development setup
- `prod/docker-compose.yml` - Production setup
- `config/scanners.yaml` - Scanner configuration
- `tools/admin_cli.py` - Admin commands
- `core/housekeeping.py` - TTL config
- `core/circuit_breaker.py` - Circuit breaker config

**Target Size**: ~300-400 lines

---

## Staged Execution Plan

### Stage 1: Research & Inventory

**Goal**: Build complete understanding of current implementation from source code.

| Task | Source Files | Deliverable |
|------|--------------|-------------|
| 1.1 | Catalog MCP tools | `tools/mcp_server.py` | Tool inventory with signatures |
| 1.2 | Map task lifecycle | `core/task_manager.py`, `core/types.py` | State machine diagram |
| 1.3 | Document queue operations | `core/queue.py` | Queue behavior notes |
| 1.4 | Map scanner registry | `scanners/registry.py` | Pool/instance model |
| 1.5 | Document worker loop | `worker/scanner_worker.py` | Processing flow |
| 1.6 | Map schema pipeline | `schema/*.py` | Transform pipeline |
| 1.7 | Extract env vars | Docker compose files | Env var inventory |
| 1.8 | Document admin CLI | `tools/admin_cli.py` | Command reference |

**Checkpoint File**: `docs/RESEARCH_NOTES.md` (temporary, delete after Stage 4)

---

### Stage 2: Write ARCHITECTURE.md

**Goal**: Create authoritative architecture document from source code.

| Task | Description | Status |
|------|-------------|--------|
| 2.1 | Write system overview section | [ ] |
| 2.2 | Create component diagram (ASCII) | [ ] |
| 2.3 | Document module responsibilities | [ ] |
| 2.4 | Write data flow: scan submission | [ ] |
| 2.5 | Write data flow: result retrieval | [ ] |
| 2.6 | Document state machine | [ ] |
| 2.7 | Document key abstractions | [ ] |
| 2.8 | Add cross-references to other docs | [ ] |
| 2.9 | Review against source code | [ ] |

**Output**: `docs/ARCHITECTURE.md` (replaces `docs/ARCHITECTURE_v2.2.md`)

---

### Stage 3: Write FEATURES.md

**Goal**: Create comprehensive capability catalog.

| Task | Description | Status |
|------|-------------|--------|
| 3.1 | Write MCP tool reference (9 tools) | [ ] |
| 3.2 | Document scan types with examples | [ ] |
| 3.3 | Document schema profiles | [ ] |
| 3.4 | Document filtering syntax | [ ] |
| 3.5 | Document pagination | [ ] |
| 3.6 | Document auth detection | [ ] |
| 3.7 | Document idempotency | [ ] |
| 3.8 | Add use case examples | [ ] |
| 3.9 | Document limitations | [ ] |
| 3.10 | Review against tool docstrings | [ ] |

**Output**: `docs/FEATURES.md` (replaces `docs/features/FEATURES.md`)

---

### Stage 4: Write REQUIREMENTS.md

**Goal**: Create living traceability matrix.

| Task | Description | Status |
|------|-------------|--------|
| 4.1 | Define FR matrix from implemented features | [ ] |
| 4.2 | Define NFR matrix with measured values | [ ] |
| 4.3 | Define TR matrix per MCP tool | [ ] |
| 4.4 | Define IR matrix (integrations) | [ ] |
| 4.5 | Define TestR matrix with counts | [ ] |
| 4.6 | Document dependency requirements | [ ] |
| 4.7 | Define future roadmap section | [ ] |
| 4.8 | Review against test suite | [ ] |

**Output**: `docs/REQUIREMENTS.md` (replaces `docs/features/REQUIREMENTS.md`)

---

### Stage 5: Write DEPLOYMENT.md

**Goal**: Create operational deployment guide.

| Task | Description | Status |
|------|-------------|--------|
| 5.1 | Document dev docker-compose | [ ] |
| 5.2 | Document prod docker-compose | [ ] |
| 5.3 | Create network topology diagram | [ ] |
| 5.4 | Document all environment variables | [ ] |
| 5.5 | Document scanners.yaml config | [ ] |
| 5.6 | Document health check endpoints | [ ] |
| 5.7 | Document admin CLI commands | [ ] |
| 5.8 | Document TTL housekeeping | [ ] |
| 5.9 | Document circuit breaker | [ ] |
| 5.10 | Write troubleshooting guide | [ ] |
| 5.11 | Write quick start section | [ ] |

**Output**: `docs/DEPLOYMENT.md` (new file)

---

### Stage 6: Cleanup & Validation

**Goal**: Remove obsolete docs, validate cross-references.

| Task | Description | Status |
|------|-------------|--------|
| 6.1 | Archive `docs/ARCHITECTURE_v2.2.md` | [ ] |
| 6.2 | Archive `docs/features/*.md` (old versions) | [ ] |
| 6.3 | Update `docs/README.MD` index | [ ] |
| 6.4 | Update `mcp-server/README.MD` links | [ ] |
| 6.5 | Validate all cross-doc links | [ ] |
| 6.6 | Delete `docs/RESEARCH_NOTES.md` | [ ] |
| 6.7 | Final review of all 4 docs | [ ] |

**Output**: Clean docs/ directory with 4 canonical documents

---

## File Inventory

### Files to CREATE

| File | Stage |
|------|-------|
| `docs/ARCHITECTURE.md` | 2 |
| `docs/FEATURES.md` | 3 |
| `docs/REQUIREMENTS.md` | 4 |
| `docs/DEPLOYMENT.md` | 5 |
| `docs/RESEARCH_NOTES.md` | 1 (temporary) |

### Files to ARCHIVE (move to `docs/archive/`)

| File | Reason |
|------|--------|
| `docs/ARCHITECTURE_v2.2.md` | Replaced by new ARCHITECTURE.md |
| `docs/features/ARCHITECTURE.md` | Consolidated |
| `docs/features/FEATURES.md` | Consolidated |
| `docs/features/REQUIREMENTS.md` | Consolidated |
| `docs/features/OPERATIONS.md` | Merged into DEPLOYMENT.md |
| `docs/features/DEVELOPMENT.md` | Merged into ARCHITECTURE.md / README |

### Files to KEEP (no changes needed)

| File | Reason |
|------|--------|
| `docs/API.md` | Detailed API reference (complementary) |
| `docs/TESTING.md` | Test-specific documentation |
| `docs/SCANNER_POOLS.md` | Deep-dive reference |
| `docs/MONITORING.md` | Deep-dive reference |
| `docs/HOUSEKEEPING.md` | Deep-dive reference |

---

## Context Recovery Instructions

If Claude Code loses context mid-execution:

1. **Read this file first**: `mcp-server/docs/DOC_PLAN.md`
2. **Check current stage**: Look at checkbox status in Staged Execution Plan
3. **Resume from last incomplete task**: Each task is atomic and can be resumed
4. **Source of truth**: Always consult source code files listed in each document scope
5. **Temporary notes**: Check `docs/RESEARCH_NOTES.md` if Stage 1 completed

---

## Quality Checklist

Before marking any document complete:

- [ ] All sections from scope definition included
- [ ] No content from EXCLUDE list present
- [ ] Source code consulted for accuracy
- [ ] Cross-references to other docs added
- [ ] "Last Updated" date set
- [ ] ASCII diagrams render correctly
- [ ] Code examples are syntactically correct
- [ ] No broken markdown links

---

*Plan created: 2025-12-01*
*Plan author: Claude Code + User collaboration*
