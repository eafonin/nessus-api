# README Generation Plan

> Iterative execution plan for generating LLM-optimized documentation

## Overview

This plan generates README files for all project directories, optimized for Claude Code agent consumption. Work proceeds bottom-up, ensuring child READMEs exist before parent READMEs link to them.

## Execution Rules

1. **Bottom-up order** - Complete leaf directories before parent directories
2. **Naming convention** - Use `README_NEW.MD` where README already exists
3. **Checkpoint after each batch** - User reviews before proceeding
4. **Mark completed** - Update status in this document as tasks complete
5. **Flag oversized** - Mark any README exceeding 1000 lines for decomposition

## Directory Structure Summary

```
nessus-api/
├── .claude/skills/           # Claude Code skills (include in root README)
│   ├── markdown-writer/      # Markdown generation skill
│   └── nessus-scanner/       # [SKIP - already documented]
├── dev1/                     # Development deployment
│   ├── data/                 # Runtime data (structure only)
│   └── logs/                 # Runtime logs (structure only)
├── docs/                     # External reference docs
│   └── fastMCPServer/        # FastMCP framework docs (single index)
├── mcp-server/               # Main MCP server code
│   ├── client/               # MCP client library
│   ├── config/               # Configuration files (structure only)
│   ├── core/                 # Core infrastructure
│   ├── docker/               # Docker build files
│   ├── docs/                 # Internal documentation
│   ├── prod/                 # Production deployment
│   ├── scanners/             # Scanner implementations
│   ├── schema/               # Result schema/filtering
│   ├── tests/                # Test suite
│   ├── tools/                # MCP tools and server
│   └── worker/               # Background worker
├── scanners-infra/           # Nessus scanner infrastructure
│   ├── nginx/                # Reverse proxy
│   └── wg/                   # WireGuard VPN
└── archive/                  # [SKIP - archived code]
```

## Existing READMEs (will create README_NEW.MD)

| Path | Action |
|------|--------|
| `/README.md` | Create `README_NEW.MD` |
| `/mcp-server/README.md` | Create `README_NEW.MD` |
| `/mcp-server/docs/README.md` | Create `README_NEW.MD` |
| `/mcp-server/scanners/README.md` | Create `README_NEW.MD` |
| `/mcp-server/tests/README.md` | Create `README_NEW.MD` |
| `/mcp-server/client/examples/README.md` | Create `README_NEW.MD` |
| `/scanners-infra/README.md` | Create `README_NEW.MD` |
| `.claude/skills/markdown-writer/README.md` | Create `README_NEW.MD` |
| `.claude/skills/markdown-writer/examples/README.md` | Create `README_NEW.MD` |

## Batch Execution Plan

---

### Batch 1: mcp-server/tests/ subtree

**Status**: `[x] completed`

Test directories - leaf nodes first, then parent.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 1.1 | `mcp-server/tests/fixtures/` | No | No | `README.MD` |
| 1.2 | `mcp-server/tests/client/` | Yes | No | `README.MD` |
| 1.3 | `mcp-server/tests/unit/` | Yes | No | `README.MD` |
| 1.4 | `mcp-server/tests/integration/` | Yes | No | `README.MD` |
| 1.5 | `mcp-server/tests/` | Yes | Yes | `README_NEW.MD` |

**Content requirements**:
- `fixtures/`: Document test data files
- `client/`: Test client utilities
- `unit/`: Summarize by category (circuit_breaker, health, housekeeping, ip_utils, logging, metrics, validators, pool/queue, task_manager, authenticated_scans, admin_cli)
- `integration/`: Summarize by category (connectivity, MCP client, Phase tests 0-3, scan workflows, queue, idempotency)
- `tests/`: Link to subdirs, pytest config, how to run tests

---

### Batch 2: mcp-server/core/

**Status**: `[x] completed`

Core infrastructure modules.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 2.1 | `mcp-server/core/` | Yes | No | `README.MD` |

**Python files (12 modules)**:
- `circuit_breaker.py` - Scanner health circuit breaker pattern
- `health.py` - Health check endpoints (/health, /ready)
- `housekeeping.py` - Cleanup expired tasks and orphaned scans
- `idempotency.py` - Duplicate request prevention via Redis
- `ip_utils.py` - CIDR parsing, IP expansion, target validation
- `logging_config.py` - Structured JSON logging setup
- `metrics.py` - Prometheus metrics collection
- `middleware.py` - HTTP middleware (request tracing)
- `queue.py` - Redis queue operations (enqueue, dequeue, DLQ)
- `task_manager.py` - Task state machine (queued→running→completed)
- `types.py` - Type definitions and enums

**Workflow focus**: Task lifecycle, queue processing, health monitoring

---

### Batch 3: mcp-server/schema/

**Status**: `[x] completed`

Result schema and filtering.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 3.1 | `mcp-server/schema/` | Yes | No | `README.MD` |

**Python files (5 modules)**:
- `converter.py` - Nessus XML to normalized schema conversion
- `filters.py` - Result filtering (severity, CVSS, plugin ID)
- `jsonl_converter.py` - JSON-NL paginated output format
- `parser.py` - Nessus .nessus XML file parsing
- `profiles.py` - Schema profiles (minimal/summary/brief/full)

**Workflow focus**: Nessus output → parsed → filtered → formatted

---

### Batch 4: mcp-server/worker/

**Status**: `[x] completed`

Background scan processor.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 4.1 | `mcp-server/worker/` | Yes | No | `README.MD` |

**Python files (1 module)**:
- `scanner_worker.py` - Background worker that polls queue, executes scans, stores results

**Workflow focus**: Queue polling → scanner dispatch → result storage → task completion

---

### Batch 5: mcp-server/tools/

**Status**: `[x] completed`

MCP server and tools.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 5.1 | `mcp-server/tools/` | Yes | No | `README.MD` |

**Python files (5 modules)**:
- `admin_cli.py` - Admin CLI for queue/task management
- `mcp_server.py` - FastMCP server initialization and lifespan
- `mcp_tools.py` - MCP tool definitions (run_scan, get_status, etc.)
- `run_server.py` - Server entry point (uvicorn launcher)
- `test_asgi_direct.py` - Direct ASGI testing utility

**Workflow focus**: MCP protocol handling, tool dispatch, server lifecycle

---

### Batch 6: mcp-server/client/

**Status**: `[x] completed`

MCP client library.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 6.1 | `mcp-server/client/examples/` | Yes | Yes | `README_NEW.MD` |
| 6.2 | `mcp-server/client/` | Yes | No | `README.MD` |

**Python files in client/**:
- `client_smoke.py` - Quick smoke test
- `nessus_fastmcp_client.py` - FastMCP client wrapper
- `test_client.py` - Client testing utilities

**Python files in examples/** (6 scripts):
- `01_basic_usage.py` → `06_e2e_workflow_test.py` - Progressive complexity examples

---

### Batch 7: mcp-server/config/

**Status**: `[x] completed`

Configuration files (structure only).

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 7.1 | `mcp-server/config/` | No | No | `README.MD` |

**Content**: Document YAML structure for `scanners.yaml` (pools, instances, credentials)

---

### Batch 8: mcp-server/docker/ and mcp-server/prod/

**Status**: `[x] completed`

Docker and production deployment.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 8.1 | `mcp-server/docker/` | No | No | `README.MD` |
| 8.2 | `mcp-server/prod/` | No | No | `README.MD` |

**Docker files in docker/**:
- `Dockerfile.api` - MCP API server image
- `Dockerfile.worker` - Background worker image
- `Dockerfile.scan-target` - Test scan target (SSH server)
- `Dockerfile.test` - Test runner image

**Docker files in prod/**:
- `Dockerfile.api`, `Dockerfile.worker` - Production images
- `docker-compose.yml` - Production stack

---

### Batch 9: mcp-server/scanners/

**Status**: `[x] completed`

Scanner implementations.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 9.1 | `mcp-server/scanners/` | Yes | Yes | `README_NEW.MD` |

**Python files (7 modules)**:
- `api_token_fetcher.py` - Nessus API token management
- `base.py` - Abstract scanner interface
- `mock_scanner.py` - Mock scanner for testing
- `nessus.py` - Low-level Nessus API client
- `nessus_scanner.py` - High-level Nessus scanner wrapper
- `nessus_validator.py` - Scan result validation
- `registry.py` - Scanner pool registry (load balancing)

**Workflow focus**: Scanner abstraction, pool management, Nessus API interaction

---

### Batch 10: mcp-server/docs/

**Status**: `[x] completed`

Internal documentation index.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 10.1 | `mcp-server/docs/` | No | Yes | `README_NEW.MD` |

**Existing docs to link**:
- `API.md` - MCP tool API reference
- `ARCHITECTURE_v2.2.md` - System architecture
- `HOUSEKEEPING.md` - Cleanup operations
- `MONITORING.md` - Observability guide
- `PER_POOL_BACKPRESSURE.md` - Queue backpressure
- `SCANNER_POOLS.md` - Pool configuration
- `TESTING.md` - Test guide

---

### Batch 11: mcp-server/ parent

**Status**: `[x] completed`

Main MCP server directory.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 11.1 | `mcp-server/` | Yes | Yes | `README_NEW.MD` |

**Root-level Python files**:
- `monitor_and_export.py` - Monitoring and export utility
- `run_e2e_test_interactive.py` - Interactive E2E test
- `test_both_scanners.py` - Dual scanner test

**Content**: Link to all subdirectory READMEs with descriptions

---

### Batch 12: scanners-infra/ subtree

**Status**: `[x] completed`

Nessus scanner infrastructure.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 12.1 | `scanners-infra/nginx/` | No | No | `README.MD` |
| 12.2 | `scanners-infra/wg/` | No | No | `README.MD` |
| 12.3 | `scanners-infra/` | No | Yes | `README_NEW.MD` |

**Content requirements**:
- `nginx/`: Reverse proxy config, SSL certs
- `wg/`: WireGuard VPN for plugin updates
- `scanners-infra/`: Docker stack for Nessus scanners

---

### Batch 13: dev1/ subtree

**Status**: `[x] completed`

Development deployment.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 13.1 | `dev1/data/` | No | No | `README.MD` |
| 13.2 | `dev1/logs/` | No | No | `README.MD` |
| 13.3 | `dev1/` | No | No | `README.MD` |

**Content requirements**:
- `data/`: Structure only - task result storage
- `logs/`: Structure only - application logs
- `dev1/`: Docker compose for development, hot reload setup

---

### Batch 14: docs/ subtree

**Status**: `[x] completed`

External reference documentation.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 14.1 | `docs/fastMCPServer/` | No | No | `README.MD` |
| 14.2 | `docs/` | No | No | `README.MD` |

**Content requirements**:
- `fastMCPServer/`: Single index listing all files in all subdirs (advanced/, authentication/, clients/, deployment/, integrations/, patterns/)
- `docs/`: Link to fastMCPServer index

---

### Batch 15: .claude/skills/markdown-writer/ subtree

**Status**: `[x] completed`

Markdown writer skill.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 15.1 | `skills/markdown-writer/references/` | No | No | `README.MD` |
| 15.2 | `skills/markdown-writer/scripts/` | Yes | No | `README.MD` |
| 15.3 | `skills/markdown-writer/examples/` | No | Yes | `README_NEW.MD` |
| 15.4 | `skills/markdown-writer/` | Yes | Yes | `README_NEW.MD` |

**Python files in scripts/**:
- `analyze_docs.py` - Find orphaned docs, broken links
- `validate_markdown.py` - Quality validation

---

### Batch 16: Root README

**Status**: `[x] completed`

Global project README.

| # | Directory | Has Python | Existing README | Output File |
|---|-----------|------------|-----------------|-------------|
| 16.1 | `/` (root) | No | Yes | `README_NEW.MD` |

**Content requirements**:
- Project overview for Claude Code agent
- Link to: mcp-server/, dev1/, docs/, scanners-infra/, .claude/skills/
- Quick start sections
- Architecture overview

---

## Progress Tracking

| Batch | Scope | Status | Files | Notes |
|-------|-------|--------|-------|-------|
| 1 | mcp-server/tests/ | `[x] completed` | 5/5 | |
| 2 | mcp-server/core/ | `[x] completed` | 1/1 | |
| 3 | mcp-server/schema/ | `[x] completed` | 1/1 | |
| 4 | mcp-server/worker/ | `[x] completed` | 1/1 | |
| 5 | mcp-server/tools/ | `[x] completed` | 1/1 | |
| 6 | mcp-server/client/ | `[x] completed` | 2/2 | |
| 7 | mcp-server/config/ | `[x] completed` | 1/1 | |
| 8 | mcp-server/docker+prod | `[x] completed` | 2/2 | |
| 9 | mcp-server/scanners/ | `[x] completed` | 1/1 | |
| 10 | mcp-server/docs/ | `[x] completed` | 1/1 | |
| 11 | mcp-server/ parent | `[x] completed` | 1/1 | |
| 12 | scanners-infra/ | `[x] completed` | 3/3 | |
| 13 | dev1/ | `[x] completed` | 3/3 | |
| 14 | docs/ | `[x] completed` | 2/2 | |
| 15 | .claude/skills/markdown-writer/ | `[x] completed` | 4/4 | |
| 16 | Root | `[x] completed` | 1/1 | |

**Total**: 30 README files to create

## Flagged for Decomposition

Files exceeding 1000 lines will be listed here after creation:

| File | Lines | Recommended Action |
|------|-------|-------------------|
| (none yet) | | |

## Execution Commands

To start a batch:
```
Execute Batch N from README_GENERATION_PLAN.md
```

To check progress:
```
Show status of README generation plan
```

To validate after batch:
```bash
python .claude/skills/markdown-writer/scripts/analyze_docs.py .
```

## Notes

- Skip `archive/` directory entirely
- Skip `.claude/skills/nessus-scanner/` (already well-documented)
- Runtime data directories (`dev1/data/`, `dev1/logs/`, `mcp-server/config/`) get structure-only documentation
- All READMEs optimized for Claude Code agent context loading
- Use markdown skill guidelines for formatting
