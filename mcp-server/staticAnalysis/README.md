# Static Code Analysis for MCP Server

This document describes how to run static code analysis (linting and type checking) on the MCP server codebase.

## Quick Reference

| Action | Command |
|--------|---------|
| Check all | `source venv/bin/activate && cd mcp-server && ruff check . && mypy .` |
| Auto-fix | `source venv/bin/activate && cd mcp-server && ruff format . && ruff check . --fix` |
| Claude command | `/lint` or `/fix-lint` |

## Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Ruff | >=0.8.0 | Linting + formatting (replaces flake8, black, isort) |
| MyPy | >=1.13.0 | Static type checking |

## First-Time Setup

### Check if setup is needed

```bash
# Check if venv and tools exist
if [ -x "/home/nessus/projects/nessus-api/venv/bin/ruff" ] && [ -x "/home/nessus/projects/nessus-api/venv/bin/mypy" ]; then
    echo "Tools already installed, skipping setup"
else
    echo "Setup required, proceeding..."
fi
```

### 1. Create and activate virtual environment

```bash
cd /home/nessus/projects/nessus-api
python3 -m venv venv
source venv/bin/activate
```

### 2. Install static analysis tools

```bash
pip install ruff mypy types-redis types-PyYAML pydantic
```

### 3. Verify installation

```bash
cd mcp-server
ruff check .
mypy .
```

Expected output when clean:
```
All checks passed!
Success: no issues found in 87 source files
```

## Running Analysis

### Method 1: CLI (Manual)

```bash
# Activate venv (from project root)
source /home/nessus/projects/nessus-api/venv/bin/activate

# Navigate to mcp-server
cd /home/nessus/projects/nessus-api/mcp-server

# Run linter
ruff check .

# Run type checker
mypy .

# Auto-fix safe issues
ruff format .
ruff check . --fix
```

### Method 2: Claude Slash Commands

| Command | Description |
|---------|-------------|
| `/lint` | Run Ruff and MyPy, report all errors |
| `/fix-lint` | Auto-fix formatting and safe lint issues |

## Configuration

All configuration is in `mcp-server/pyproject.toml`:

### Ruff Configuration

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "SIM", "ASYNC", "FAST", "S", "PTH", "RUF", "ANN", "TCH"]
```

Key settings:
- Line length: 100 characters
- Python version: 3.11
- Async checks enabled (critical for FastMCP)
- Security checks enabled

### MyPy Configuration

```toml
[tool.mypy]
python_version = "3.11"
strict = false  # Gradual adoption
check_untyped_defs = true
```

Uses per-module ignores for gradual type adoption. See `pyproject.toml` for full list.

## Per-File Ignores

Certain files have relaxed rules:

| Pattern | Ignored Rules | Reason |
|---------|---------------|--------|
| `tests/**/*.py` | S101, ANN, E501, PTH, SIM, etc. | Tests need flexibility |
| `tools/run_server.py` | S104 | Intentional 0.0.0.0 bind for Docker |
| `scanners/nessus_validator.py` | S314 | XML parsing of trusted data |
| `schema/parser.py` | S314 | XML parsing of internal data |

## Error Resolution

### Common Ruff Errors

| Code | Meaning | Fix |
|------|---------|-----|
| E501 | Line too long | Break line or shorten |
| ANN201 | Missing return type | Add `-> ReturnType` |
| PTH123 | Use `open()` | Replace with `Path.open()` |
| B904 | Missing `raise from` | Add `from err` or `from None` |

### Common MyPy Errors

| Code | Meaning | Fix |
|------|---------|-----|
| import-not-found | Missing stubs | Add to `ignore_missing_imports` or install stubs |
| type-arg | Missing generic params | Use `list[str]` not `list` |
| no-untyped-def | Missing annotations | Add type hints |

## Files in This Directory

| File | Description |
|------|-------------|
| README.md | This file - usage documentation |
| IMPLEMENTATION_LOG.md | History of static analysis implementation and decisions |

## Current Status

As of 2025-12-02:
- **Ruff**: 0 errors (reduced from 1019)
- **MyPy**: 0 errors (87 source files checked)
  - All errors fixed properly (not suppressed)
  - Only 3 orphan stub files excluded (unused reference files)
  - Tests excluded (test flexibility)
  - External libs without stubs: `ignore_missing_imports = true`

## Directory Structure

```
nessus-api/
├── venv/                          # Project virtual environment
│   └── bin/
│       ├── ruff
│       └── mypy
├── .claude/
│   └── commands/
│       ├── lint.md                # /lint command definition
│       └── fix-lint.md            # /fix-lint command definition
└── mcp-server/
    ├── pyproject.toml             # Ruff + MyPy configuration
    └── staticAnalysis/
        ├── README.md              # This file
        └── IMPLEMENTATION_LOG.md  # Implementation history
```
