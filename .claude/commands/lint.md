# Static Code Analysis

Run Ruff and MyPy static analysis on the MCP server codebase.

## Instructions

1. Activate the project virtual environment
2. Navigate to the mcp-server directory
3. Run Ruff linter to check for code quality issues
4. Run MyPy for type checking
5. Report results with error counts and file locations

## Commands to Execute

```bash
source /home/nessus/projects/nessus-api/venv/bin/activate
cd /home/nessus/projects/nessus-api/mcp-server

# Run Ruff check
echo "=== RUFF LINTER ==="
ruff check . --statistics

# Run MyPy
echo "=== MYPY TYPE CHECK ==="
mypy .
```

## First-Time Setup (if venv doesn't exist)

Check if setup is needed:
```bash
# Check if venv and tools exist
if [ -x "/home/nessus/projects/nessus-api/venv/bin/ruff" ] && [ -x "/home/nessus/projects/nessus-api/venv/bin/mypy" ]; then
    echo "Tools already installed, skipping setup"
else
    echo "Setting up venv and installing tools..."
    cd /home/nessus/projects/nessus-api
    python3 -m venv venv
    source venv/bin/activate
    pip install ruff mypy types-redis types-PyYAML pydantic
fi
```

## Configuration

- Ruff config: `mcp-server/pyproject.toml` [tool.ruff]
- MyPy config: `mcp-server/pyproject.toml` [tool.mypy]
- Documentation: `mcp-server/staticAnalysis/README.md`

## Output

Report:
1. Total error count for each tool
2. Top files with most errors (if any)
3. Summary of error categories

## Artifacts Directory

Store any analysis reports in: `mcp-server/staticAnalysis/`
