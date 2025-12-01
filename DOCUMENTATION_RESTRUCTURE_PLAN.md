# Documentation Restructure Plan

> Hierarchical README structure for Claude agent navigation

## Overview

This plan defines a consistent structure for 26 README files across the nessus-api project, enabling Claude agents to navigate documentation hierarchically with clear parent/child relationships.

---

## 1. Hierarchy Definition

### L1: Root (1 file)
| File | Purpose |
|------|---------|
| `README.md` | Project entry point, navigation hub |

### L2: Major Sections (4 files)
| File | Purpose | Children |
|------|---------|----------|
| `dev1/README.MD` | Development environment | 2 |
| `docs/README.MD` | Reference documentation | 1 |
| `scanners-infra/README.md` | Scanner infrastructure | 2 |
| `mcp-server/README.md` | MCP server code | 11 |

### L3: Subsections (16 files)
| Parent | File | Purpose |
|--------|------|---------|
| dev1/ | `data/README.MD` | Task result storage |
| dev1/ | `logs/README.MD` | Application logs |
| docs/ | `fastMCPServer/README.MD` | FastMCP framework docs |
| scanners-infra/ | `nginx/README.MD` | Reverse proxy |
| scanners-infra/ | `wg/README.MD` | WireGuard VPN |
| mcp-server/ | `client/README.MD` | Python client library |
| mcp-server/ | `config/README.MD` | Scanner configuration |
| mcp-server/ | `core/README.MD` | Task management, queue |
| mcp-server/ | `docker/README.MD` | Docker build files |
| mcp-server/ | `docs/README.md` | Internal documentation |
| mcp-server/ | `prod/README.MD` | Production deployment |
| mcp-server/ | `scanners/README.md` | Scanner abstraction |
| mcp-server/ | `schema/README.MD` | Result parsing |
| mcp-server/ | `tools/README.MD` | MCP server implementation |
| mcp-server/ | `worker/README.MD` | Background processor |
| mcp-server/ | `tests/README.md` | Test suite |

### L4: Deep Subsections (5 files, context-based)
| Parent | File | Keep? | Rationale |
|--------|------|-------|-----------|
| mcp-server/client/ | `examples/README.md` | **Yes** | Substantial content (430 lines) |
| mcp-server/tests/ | `client/README.MD` | **Merge** | Minimal content (43 lines) |
| mcp-server/tests/ | `fixtures/README.MD` | **Merge** | Minimal content (33 lines) |
| mcp-server/tests/ | `integration/README.MD` | **Yes** | Substantial content (107 lines) |
| mcp-server/tests/ | `unit/README.MD` | **Yes** | Moderate content (85 lines) |

this structure is as good as it was intended, do nothing.

---

## 2. Duplicate Content Analysis

### High Duplication (Consolidate)

| Content | Found In | Canonical Location | Action |
|---------|----------|-------------------|--------|
| Architecture diagrams | Root, dev1, mcp-server, scanners-infra | `mcp-server/docs/ARCHITECTURE_v2.2.md` | Keep brief in each, link to canonical |
| Environment variables | 7 files | Per-service README | Keep relevant subset, link to full list |
| MCP Tools list | Root, mcp-server, tools | `mcp-server/docs/API.md` | Brief table + link |
| Docker commands | 4 files | `dev1/README.MD` (dev), `prod/README.MD` (prod) | Keep in appropriate context |

### Recommended Canonical Sources

| Topic | Canonical File | Summary Locations |
|-------|---------------|-------------------|
| Full API reference | `mcp-server/docs/API.md` | Root, mcp-server, tools |
| Architecture | `mcp-server/docs/ARCHITECTURE_v2.2.md` | Root, mcp-server |
| Scanner pools | `mcp-server/docs/SCANNER_POOLS.md` | config, scanners |
| Network topology | `scanners-infra/ARCHITECTURE.md` | scanners-infra, nginx, wg |
| Testing guide | `mcp-server/docs/TESTING.md` | tests, tests/* |

---

## 3. Navigation Header Format

### Standard Header (Minimal)

```markdown
<!-- README Navigation -->
<!-- L[N]: [path/from/root] -->
<!-- Parent: [relative/path/to/parent/README.MD] -->
<!-- Purpose: [one-line description] -->

# Title

> One-line description (blockquote)

**↑ Parent**: [Parent Name](../README.MD)
```

### Examples

**L1 (Root)**:
```markdown
<!-- README Navigation -->
<!-- L1: / -->
<!-- Purpose: Project entry point and navigation hub -->

# Nessus MCP Server

> Model Context Protocol server for Nessus vulnerability scanning
```

**L2 (dev1)**:
```markdown
<!-- README Navigation -->
<!-- L2: dev1/ -->
<!-- Parent: ../README.md -->
<!-- Purpose: Development environment with hot reload -->

# Development Environment

> Local development deployment with hot reload and debug logging

**↑ Parent**: [Nessus MCP Server](../README.md)
```

**L3 (mcp-server/core)**:
```markdown
<!-- README Navigation -->
<!-- L3: mcp-server/core/ -->
<!-- Parent: ../README.md -->
<!-- Purpose: Task management, queuing, and observability -->

# Core Infrastructure

> Foundation modules for task management, queuing, and observability

**↑ Parent**: [MCP Server](../README.md) | **↑↑ Root**: [Nessus MCP Server](../../README.md)
```

**L4 (mcp-server/tests/integration)**:
```markdown
<!-- README Navigation -->
<!-- L4: mcp-server/tests/integration/ -->
<!-- Parent: ../README.md -->
<!-- Purpose: E2E tests with real Redis and MCP server -->

# Integration Tests

> End-to-end tests with real Redis and MCP server

**↑ Parent**: [Tests](../README.md) | **↑↑ MCP Server**: [README](../../README.md) | **↑↑↑ Root**: [Nessus MCP Server](../../../README.md)
```

---

## 4. Common Section Structure

### Recommended Sections by Level

| Section | L1 | L2 | L3 | L4 |
|---------|:--:|:--:|:--:|:--:|
| Navigation header | ✓ | ✓ | ✓ | ✓ |
| Quick Navigation (tables) | ✓ | ✓ | - | - |
| Purpose/Overview | ✓ | ✓ | ✓ | ✓ |
| Quick Start | ✓ | ✓ | - | - |
| Directory Structure | ✓ | ✓ | - | - |
| Module/File Details | - | - | ✓ | ✓ |
| Usage Examples | - | ✓ | ✓ | ✓ |
| Configuration | ✓ | ✓ | ✓ | - |
| Troubleshooting | - | ✓ | ✓ | - |
| See Also (links) | ✓ | ✓ | ✓ | ✓ |

### Section Order

1. **Navigation header** (HTML comment + markdown link)
2. **Title** (H1)
3. **Tagline** (blockquote)
4. **Parent link** (markdown)
5. **Quick Navigation** (table for L1/L2)
6. **Overview/Purpose**
7. **Quick Start** (L1/L2 only)
8. **Directory Structure** (L1/L2 only)
9. **Main content** (varies by purpose)
10. **See Also** (related documentation links)

---

## 5. File Naming Standardization

### Current State
- Mixed: `README.md` (10 files) vs `README.MD` (16 files)

### Action
Rename all to `README.MD` (uppercase extension) per user preference.

**Files to rename** (lowercase → uppercase):
```
README.md → README.MD
├── /README.md
├── mcp-server/README.md
├── mcp-server/client/examples/README.md
├── mcp-server/docs/README.md
├── mcp-server/scanners/README.md
├── mcp-server/tests/README.md
├── scanners-infra/README.md
├── docs/fastMCPServer/README.MD (already correct)
└── ... (verify each)
```

---

## 6. Content Consolidation Actions

### Brief + Link Pattern

For duplicated content, use this pattern:

```markdown
## MCP Tools

| Tool | Description |
|------|-------------|
| `run_untrusted_scan` | Network-only vulnerability scan |
| `get_scan_status` | Check scan progress |
| ... | ... |

→ **Full API reference**: [API.md](mcp-server/docs/API.md)
```

---

## 7. Implementation Order

### Phase 1: Header Addition (All Files)
Add navigation headers to all 26 files without changing content.

### Phase 2: File Renaming
Standardize to `README.MD` (10 git mv operations).

### Phase 3: Content Consolidation
1. Merge L4 test files into L3
2. Apply "brief + link" pattern to duplicates

### Phase 4: Structure Standardization
Apply common section structure to each level.

---

## 8. Files Summary

| Level | Count | Files |
|-------|-------|-------|
| L1 | 1 | Root README |
| L2 | 4 | dev1, docs, scanners-infra, mcp-server |
| L3 | 16 | All subdirectories |
| L4 | 3 | examples, integration, unit (after merge) |
| **Total** | **24** | (26 → 24 after merging 2) |

---

## Approval Required

Before proceeding with implementation:

1. **Header format** - Is the minimal HTML comment + markdown link format acceptable?
2. **Content consolidation** - Approve merging tests/client + tests/fixtures into tests/README.md
3. **Duplicate handling** - Confirm "brief + link" pattern for shared content
4. **Implementation order** - Start with Phase 1 (headers) or proceed with all phases?
