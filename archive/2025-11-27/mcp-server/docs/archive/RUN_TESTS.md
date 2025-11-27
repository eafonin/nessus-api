# Test Execution Guide

Quick reference for running MCP server tests by phase.

---

## Phase-Based Test Execution

### Phase 0: Task Management & Queue Infrastructure

```bash
cd /home/nessus/projects/nessus-api/mcp-server
source ../venv/bin/activate

# Run all Phase 0 tests
pytest tests/integration/test_phase0.py -v

# Or by marker
pytest -m phase0 -v
```

**Tests included:**
- Queue operations (Redis)
- Task manager (file-based storage)
- Idempotency (duplicate detection)
- State transitions

---

### Phase 1: Nessus Scanner Integration

```bash
cd /home/nessus/projects/nessus-api/mcp-server
source ../venv/bin/activate

# Run ALL Phase 1 tests (recommended)
pytest tests/integration/test_phase1.py -v

# Or by marker
pytest -m phase1 -v

# Specific test suites:

# 1. READ operations only (quick, ~10 seconds)
pytest tests/integration/test_phase1.py::TestReadOperations -v

# 2. WRITE operations only (quick, ~15 seconds)
pytest tests/integration/test_phase1.py::TestWriteOperations -v

# 3. Complete scan with vulnerability export (slow, ~3 minutes)
pytest tests/integration/test_phase1.py::test_complete_scan_workflow_with_export -v -s

# 4. Error handling
pytest tests/integration/test_phase1.py::TestErrorHandling -v

# 5. Session management
pytest tests/integration/test_phase1.py::TestSessionManagement -v
```

**Tests included:**
- ✅ Dynamic X-API-Token fetching
- ✅ Authentication
- ✅ READ operations (list scans, get status, export)
- ✅ WRITE operations (create, launch, stop, delete)
- ✅ **Complete scan workflow with >0 vulnerabilities**
- ✅ Error handling (401/403/404/409)
- ✅ Session management

**Requirements verified:**
1. ✅ Dynamic X-API-Token Fetching
2. ✅ Start scan, wait for completion, download results
3. ✅ Export must have >0 vulnerabilities (last run: 40 found)

---

### Phase 2: Schema-Driven Result Parsing (Future)

```bash
# Placeholder for Phase 2
pytest tests/integration/test_phase2.py -v
# Or: pytest -m phase2 -v
```

---

### Phase 3: Observability (Future)

```bash
# Placeholder for Phase 3
pytest tests/integration/test_phase3.py -v
# Or: pytest -m phase3 -v
```

---

### Phase 4: Production Hardening (Future)

```bash
# Placeholder for Phase 4
pytest tests/integration/test_phase4.py -v
# Or: pytest -m phase4 -v
```

---

## Quick Test Commands

### Run Everything
```bash
pytest tests/integration/ -v
```

### Run Only Quick Tests
```bash
pytest -m "quick and not slow" -v
```

### Run Only Slow Tests (scans)
```bash
pytest -m slow -v
```

### Run Only Integration Tests
```bash
pytest -m integration -v
```

### Run Specific Test by Name
```bash
# Dynamic token fetching
pytest tests/integration/test_nessus_read_write_operations.py::TestReadOperations::test_fetch_api_token -v

# Complete scan workflow
pytest tests/integration/test_complete_scan_with_results.py -v -s
```

---

## Test Output Options

### Verbose with Output
```bash
pytest tests/integration/test_phase1.py -v -s
```

### Show Only Failed Tests
```bash
pytest tests/integration/test_phase1.py -v --tb=short --maxfail=1
```

### Run with Coverage
```bash
pytest tests/integration/test_phase1.py -v --cov=scanners --cov-report=html
```

---

## Environment Variables

Tests use these environment variables (with defaults):

```bash
export NESSUS_URL="https://172.32.0.209:8834"  # Default
export NESSUS_USERNAME="nessus"                # Default
export NESSUS_PASSWORD="nessus"                # Default
```

---

## Test Results Summary

### Phase 0 Status
- **Status**: ✅ Passing (previous implementation)
- **Duration**: ~5 seconds
- **Tests**: 15+ tests

### Phase 1 Status
- **Status**: ✅ All Passing
- **Duration**:
  - Quick tests (READ/WRITE): ~30 seconds
  - Complete scan workflow: ~3 minutes
- **Tests**: 14 tests + complete workflow
- **Last Results**:
  - Dynamic token: ✅ `778F4A9C-D797-4817-B110-EC427B724486`
  - Complete scan: ✅ 40 vulnerabilities found
  - Export size: ✅ 2,063,924 bytes

---

## Continuous Integration

For CI/CD pipelines:

```bash
#!/bin/bash
# run_tests.sh

set -e

cd /home/nessus/projects/nessus-api/mcp-server
source ../venv/bin/activate

echo "Running Phase 0 tests..."
pytest tests/integration/test_phase0.py -v

echo "Running Phase 1 tests..."
pytest tests/integration/test_phase1.py -v

echo "All tests passed!"
```

---

## Troubleshooting

### Nessus Not Accessible
```bash
# Check Nessus status
curl -k https://localhost:8834/server/status

# Check Docker container
cd /home/nessus/docker/nessus
docker compose ps
docker compose logs nessus-pro | tail -50
```

### Tests Hanging
- Increase timeouts in test files
- Check network connectivity to Nessus
- Verify Redis is running (for Phase 0)

### Import Errors
```bash
# Ensure virtual environment is activated
source ../venv/bin/activate

# Verify pytest-asyncio installed
pip install pytest-asyncio
```

---

## Quick Reference Card

| Command | Purpose |
|---------|---------|
| `pytest tests/integration/test_phase0.py -v` | Run Phase 0 tests |
| `pytest tests/integration/test_phase1.py -v` | Run Phase 1 tests |
| `pytest -m phase1 -v` | Run all Phase 1 tests by marker |
| `pytest tests/integration/ -v` | Run all integration tests |
| `pytest -k "test_complete_scan" -v -s` | Run scan workflow test |

---

**Last Updated**: 2025-11-07
**Status**: Phase 0 + Phase 1 Complete ✅
