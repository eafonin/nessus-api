# Claude Code Context - Nessus API Project

## Current Focus
**MCP Server Implementation - Phase 0: Foundation & Mock Infrastructure**
- Status: 🔴 Not Started
- Start: Read `mcp-server/README.md` → Open `mcp-server/PHASE_0_FOUNDATION.md`

## Quick Orientation

### Existing & Stable
- `nessusAPIWrapper/` - 10 production-ready Nessus automation scripts
- `docs/` - Comprehensive documentation including FastMCP framework guide

### In Development (Phase 0)
- `mcp-server/` - MCP server implementation (stub files exist, need implementation)
- `dev1/` - Development environment (doesn't exist yet, will create in Phase 0)

## Python Environment
**CRITICAL**: Always activate venv before running Python:
```bash
source /home/nessus/projects/nessus-api/venv/bin/activate
```

## Key Documents

**For MCP Server Work**:
1. `mcp-server/README.md` - Master tracker, always read first
2. `mcp-server/PHASE_0_FOUNDATION.md` - Current implementation guide
3. `mcp-server/ARCHITECTURE_v2.2.md` - Technical design reference

**For Project Conventions**:
- `PROJECT_SETUP.md` - Directory structure, git workflow, conventions

## Session Workflow

**Start**:
- Check `mcp-server/README.md` for current phase status
- Open active phase document (`PHASE_0_FOUNDATION.md`)

**During**:
- Mark tasks ✅ in phase document as you complete them
- Run tests: `pytest tests/` before committing
- Commit frequently: `git commit -m "feat(phase-0): task description"`

**End**:
- Update "Last Updated" in `mcp-server/README.md`
- Commit all work
- Note any blockers in phase document

## Common Commands
```bash
# Activate venv
source venv/bin/activate

# Run tests
pytest tests/test_phase0_integration.py -v

# Check imports
import-linter

# Docker (Phase 0+)
cd dev1 && docker compose up --build
```

## Quick Rules
- ✅ Use venv for all Python operations
- ✅ Follow directory structure in `PROJECT_SETUP.md`
- ✅ Test before committing
- ✅ Update progress trackers in phase documents
- ❌ Don't create docs without user approval
- ❌ Don't violate import boundaries (tools/worker can import core/schema/scanners, not vice versa)

---
**Last Updated**: 2025-11-05
