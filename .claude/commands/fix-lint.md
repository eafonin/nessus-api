# Auto-Fix Linting Issues

Automatically fix code style and formatting issues using Ruff.

## Instructions

1. Activate the project virtual environment
2. Navigate to the mcp-server directory
3. Run Ruff formatter to fix formatting
4. Run Ruff with --fix to auto-fix linting issues
5. Report what was fixed

## Commands to Execute

```bash
source /home/nessus/projects/nessus-api/venv/bin/activate
cd /home/nessus/projects/nessus-api/mcp-server

# Format code
echo "=== RUFF FORMAT ==="
ruff format .

# Auto-fix linting issues
echo "=== RUFF FIX ==="
ruff check . --fix

# Show remaining issues (if any)
echo "=== REMAINING ISSUES ==="
ruff check . --statistics
```

## Safety

- Only fixes auto-fixable issues (safe fixes)
- Does NOT use --unsafe-fixes by default
- Review changes with `git diff` before committing

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
- Documentation: `mcp-server/staticAnalysis/README.md`
