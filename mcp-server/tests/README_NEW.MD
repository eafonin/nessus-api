# Test Suite

> Layered test architecture for Nessus MCP Server

## Quick Reference

```bash
# Fast validation (~20s)
pytest tests/unit/ -q

# Infrastructure tests (~1min)
pytest tests/integration/test_phase0.py tests/integration/test_phase2.py -q

# Full suite (~5min, requires running services)
pytest tests/ -v
```

## Directory Structure

```
tests/
├── fixtures/        # Sample data files
├── client/          # Test client utilities
├── unit/            # Isolated component tests (<1s)
├── integration/     # E2E tests with services (1-10min)
└── test_phase0_integration.py  # Root-level phase test
```

## Subdirectories

| Directory | Purpose | Duration |
|-----------|---------|----------|
| [fixtures/](fixtures/README.MD) | Sample Nessus scan output for parser tests | - |
| [client/](client/README.MD) | Async HTTP client for workflow testing | - |
| [unit/](unit/README.MD) | 12 test files covering core modules | <1s |
| [integration/](integration/README.MD) | 20 test files for E2E workflows | 1-10min |

## Test Layers

```
Layer 4: E2E Tests           [5-10 min]  Full scan → results workflow
    ↑
Layer 3: Integration Tests   [1-3 min]   Scanner + MCP client
    ↑
Layer 2: Infrastructure      [~5 sec]    Queue, tasks, idempotency
    ↑
Layer 1: Unit Tests          [<1 sec]    Isolated components
```

## Running Tests

### From Docker

```bash
# Unit tests
docker compose exec mcp-api pytest tests/unit/ -v

# Quick pipeline
docker compose exec mcp-api tests/run_test_pipeline.sh --quick

# Full pipeline with E2E
docker compose exec mcp-api tests/run_test_pipeline.sh --full
```

### Local Development

```bash
cd mcp-server
source venv/bin/activate
pytest tests/unit/ -v
```

## Test Pipeline Script

`run_test_pipeline.sh` provides layered test execution:

| Flag | Tests Run | Duration |
|------|-----------|----------|
| (none) | Unit + infrastructure | ~30s |
| `--quick` | Unit + Phase 0/2 + smoke | ~1min |
| `--full` | All tests including E2E | ~10min |

## Key Files

| File | Purpose |
|------|---------|
| `run_test_pipeline.sh` | Orchestrates test layers |
| `test_phase0_integration.py` | Root-level Phase 0 validation |
| `integration/conftest.py` | Shared fixtures for integration tests |

## Coverage

```bash
# Generate coverage report
pytest tests/unit/ --cov=core --cov=schema --cov=tools --cov-report=html

# View report
open htmlcov/index.html
```
