# Quick Reference

## Current Status
**Phase 0**: Foundation & Mock Infrastructure (Not Started)
**Next**: Read `mcp-server/PHASE_0_FOUNDATION.md` and start Task 0.1

## Essential Commands

```bash
# Always activate venv first
source /home/nessus/projects/nessus-api/venv/bin/activate

# Run tests (Phase 0+)
pytest tests/test_phase0_integration.py -v

# Check import boundaries
cd mcp-server && import-linter

# Docker (Phase 0+)
cd dev1
docker compose up --build    # Build and start
docker compose logs -f       # View logs
docker compose down          # Stop
```

## Phase 0 Tasks (Quick View)
- [ ] 0.1: Project Structure Setup (create dev1/, directories)
- [ ] 0.2: Core Data Structures (ScanState, Task, types.py)
- [ ] 0.3: Mock Scanner (base.py, mock_scanner.py, fixtures)
- [ ] 0.4: Task Manager (task_manager.py with state machine)
- [ ] 0.5: Simple MCP Tool (mcp_server.py with 2 tools)
- [ ] 0.6: Docker Setup (Dockerfile.api, docker-compose.yml)
- [ ] 0.7: Test Client (test_client.py)
- [ ] 0.8: Integration Test (test_phase0_integration.py passes)

## Key Files
- `mcp-server/README.md` - Master tracker
- `mcp-server/PHASE_0_FOUNDATION.md` - Step-by-step guide
- `mcp-server/ARCHITECTURE_v2.2.md` - Design reference

## Common Mistakes to Avoid
- ❌ Running Python without venv
- ❌ Creating files in wrong directories
- ❌ Not updating progress checkboxes in phase docs
- ❌ Committing without running tests
