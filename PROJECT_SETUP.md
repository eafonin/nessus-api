# Nessus API Project Setup & Conventions

## Project Overview

This project provides Python automation for Nessus Essentials vulnerability scanning, bypassing API restrictions through Web UI simulation. It enables full scan lifecycle management (create, launch, stop, edit, delete) and comprehensive vulnerability reporting.

**High-Level Architecture:**
- **Backend**: Nessus Essentials running in Docker container with VPN gateway
- **API Layer**: Python scripts using `pytenable` library + custom HTTP requests
- **Authentication**: Dual approach (API keys for read, session tokens for control)
- **Key Innovation**: Web UI simulation to bypass `scan_api: false` limitation

## System Environment

### Server Details
- **Host**: nessus@37.18.107.123
- **OS**: Ubuntu 24.04 LTS (Linux 6.14.0-33-generic)
- **User**: uid=1001(nessus), groups: nessus, sudo, docker
- **Project Path**: `/home/nessus/projects/nessus-api/`
- **Docker Path**: `/home/nessus/docker/nessus/`

### Git Repository
- **Remote**: https://github.com/eafonin/nessus-api
- **Owner**: eafonin
- **Branch**: main
- **Credentials**: See `credentials.md` (git-ignored, local only)

## Directory Structure

```
/home/nessus/projects/nessus-api/
├── nessusAPIWrapper/              # Existing Nessus automation scripts
│   ├── CODEBASE_INDEX.md         # Script inventory and documentation
│   │
│   ├── API-Based Scripts (Read-Only):
│   │   ├── list_scans.py                      # List all scans with status
│   │   ├── scan_config.py                     # Display scan configuration
│   │   ├── check_status.py                    # Check Nessus server health
│   │   ├── export_vulnerabilities.py          # Quick vulnerability export
│   │   └── export_vulnerabilities_detailed.py # Full vulnerability details
│   │
│   └── Web UI Simulation Scripts (Full Control):
│       ├── launch_scan.py                     # Launch/stop scans
│       ├── edit_scan.py                       # Edit scan parameters
│       ├── manage_credentials.py              # SSH credential management
│       ├── manage_scans.py                    # Create/delete scans
│       └── check_dropdown_options.py          # Extract field options
│
├── mcp-server/                    # 🚀 MCP server implementation (Active Development)
│   ├── README.md                  # ⭐ START HERE - Master tracker for agents
│   ├── ARCHITECTURE_v2.2.md       # Complete technical design (54KB)
│   ├── NESSUS_MCP_SERVER_REQUIREMENTS.md  # Functional requirements (27KB)
│   │
│   ├── phases/                    # Implementation phase guides
│   │   ├── PHASE_0_FOUNDATION.md      # Phase 0: Mock infrastructure (36KB)
│   │   ├── PHASE_1_REAL_NESSUS.md     # Phase 1: Real Nessus + queue (30KB)
│   │   ├── PHASE_2_SCHEMA_RESULTS.md  # Phase 2: Schema & filtering (14KB)
│   │   ├── PHASE_3_OBSERVABILITY.md   # Phase 3: Metrics & tests (11KB)
│   │   ├── PHASE_4_PRODUCTION.md      # Phase 4: Production hardening (13KB)
│   │   └── phase0/                    # Phase 0 completion artifacts (✅ complete)
│   │
│   ├── archive/                   # Previous architectures & superseded docs
│   │
│   ├── scanners/                  # Scanner abstraction layer
│   │   ├── base.py                # ScannerInterface (abstract)
│   │   ├── mock_scanner.py        # Mock for testing (Phase 0)
│   │   ├── nessus.py              # Async Nessus scanner (Phase 1)
│   │   └── registry.py            # Multi-instance registry (Phase 1)
│   │
│   ├── core/                      # Core functionality
│   │   ├── task_manager.py        # Task lifecycle & state machine
│   │   ├── idempotency.py         # Duplicate scan prevention
│   │   └── middleware.py          # Trace ID tracking
│   │
│   ├── schema/                    # Results schema & conversion
│   │   ├── profiles.py            # Schema definitions (4 profiles)
│   │   └── jsonl_converter.py     # Nessus → JSON-NL converter
│   │
│   ├── tools/                     # MCP tool implementations
│   │   └── mcp_tools.py           # FastMCP server + 10 tools
│   │
│   ├── worker/                    # Background scanner worker
│   │   └── scanner_worker.py      # Queue consumer & executor
│   │
│   ├── tests/                     # Test suite
│   │   ├── client/                # Test clients (HTTP, FastMCP SDK)
│   │   ├── fixtures/              # Mock .nessus files
│   │   ├── unit/                  # Unit tests (Phase 3)
│   │   └── integration/           # Integration tests (Phase 3)
│   │
│   ├── config/                    # Configuration files
│   │   └── scanners.yaml          # Scanner instances
│   │
│   ├── Dockerfile.api             # API service image
│   ├── Dockerfile.worker          # Worker service image
│   ├── docker-compose.yml         # Base compose file
│   ├── requirements-*.txt         # Python dependencies
│   └── pyproject.toml             # Import linter config
│
├── dev1/                          # Development environment (Phase 0)
│   ├── docker-compose.yml         # Dev-specific overrides
│   ├── .env.dev                   # Dev environment vars
│   ├── data/                      # Dev task storage
│   └── logs/                      # Dev logs
│
├── prod/                          # Production environment (Phase 4)
│   ├── docker-compose.yml         # Prod config
│   ├── .env.prod                  # Prod environment vars
│   ├── data/                      # Prod task storage
│   └── logs/                      # Prod logs
│
├── docs/                          # Documentation
│   ├── DOCKER_SETUP.md           # Docker configuration and maintenance
│   ├── CODEBASE_INDEX.md         # General project documentation
│   └── fastMCPServer/            # FastMCP framework documentation (43 files)
│       └── INDEX.md              # Quick reference for MCP development
│
├── claudeScripts/                 # Throw-away scripts by Claude Code
│   └── [temporary scripts]       # One-off automation, testing, utilities
│
├── temp/                          # Intermediate outputs (git-ignored)
│   ├── [summaries]               # Generated analysis summaries
│   ├── [checkpoints]             # Intermediate processing results
│   └── [scratch files]           # Python scripts, CSVs, temp data
│
├── venv/                          # Python virtual environment (git-ignored)
│   └── [Python packages]         # pytenable, requests, urllib3
│
├── PROJECT_SETUP.md              # This file - project conventions
├── README.md                     # Main project documentation
├── credentials.md                # Sensitive credentials (git-ignored, see note)
├── requirements.txt              # Python dependencies
└── .gitignore                    # Git exclusions
```

## Python Environment

### IMPORTANT: Always Use Virtual Environment

**This project MUST use the Python virtual environment.** All Python operations should be executed within the venv.

### Setup (One-time)
```bash
cd /home/nessus/projects/nessus-api

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Daily Usage
```bash
# Always activate before running scripts
source /home/nessus/projects/nessus-api/venv/bin/activate

# Run scripts (note: scripts now in nessusAPIWrapper/)
python nessusAPIWrapper/list_scans.py
python nessusAPIWrapper/manage_scans.py create "Test" "192.168.1.1"

# Deactivate when done
deactivate
```

### Dependencies (requirements.txt)
- `pytenable>=1.4.0` - Official Tenable API library
- `requests>=2.31.0` - HTTP library for Web UI simulation
- `urllib3>=2.0.0` - HTTP client (SSL warning suppression)

### Verification
```bash
# Verify venv is active (should show project path)
which python

# Check installed packages
pip list | grep -E "pytenable|requests"
```

## Credentials & Secrets

### credentials.md

**Location**: `/home/nessus/projects/nessus-api/credentials.md`

**Purpose**: Central storage for all sensitive credentials and configuration

**Contents**:
- GitHub Personal Access Token
- Git configuration (username, email)
- SSH private keys (nessus server, memos dev VM, kali VM)
- SSH host configurations
- Project locations (Windows, Linux, MemOS VM)
- General passwords/passphrases
- Security notes and best practices

**Security**:
- File permissions: 600 (read/write owner only)
- Git-ignored (never committed)
- Referenced in project docs when needed
- Should be manually backed up to secure location

**For Claude Code Agents**:
- Credentials are available in context when needed for tasks
- Do NOT duplicate sensitive information into other files
- Reference credentials.md in documentation when appropriate
- Be mindful of context limits - avoid loading unnecessarily

### Nessus Authentication (Hardcoded in Scripts)

**API Keys** (Read-only operations):
```python
NESSUS_URL = 'https://localhost:8834'
ACCESS_KEY = 'abc04cab03684de788ba0c4614eaba6302d3fe26852da06040eac3879547e405'
SECRET_KEY = '06332ecfd4bc633667be4e20e139c9451a848c580da988c69679fde16ce9c837'
```

**Web UI Credentials** (Scan control):
```python
USERNAME = 'nessus'
PASSWORD = 'nessus'
STATIC_API_TOKEN = 'af824aba-e642-4e63-a49b-0810542ad8a5'
```

## Claude Code Agent Guidelines

### Working with This Project

1. **Python Environment**
   - ALWAYS activate venv before running Python scripts
   - Use: `source venv/bin/activate && python nessusAPIWrapper/script.py`
   - Never run scripts outside venv

2. **Directory Usage**
   - **nessusAPIWrapper/**: Existing Nessus automation scripts (stable, modify with care)
   - **mcp-server/**: MCP server implementation (planning phase, to be developed)
   - **docs/**: Only create/modify with user permission
   - **claudeScripts/**: Free to create throw-away scripts
   - **temp/**: Use for intermediate outputs, summaries, checkpoints
   - **Root**: Documentation and configuration files

3. **Script Development**
   - **Existing scripts** in nessusAPIWrapper/: Follow existing patterns
   - **New MCP server**: Follow architecture in mcp-server/NESSUS_MCP_SERVER_ARCHITECTURE.md
   - Use urllib3.disable_warnings() for SSL
   - Implement proper error handling
   - Add usage instructions in docstrings
   - Mask sensitive data in output (passwords, keys)

4. **Git Operations**
   - Check `.gitignore` before committing
   - Never commit: credentials.md, venv/, temp/, *.json exports
   - Use meaningful commit messages
   - Sync with remote: https://github.com/eafonin/nessus-api

5. **Documentation**
   - Update README.md when adding new scripts
   - Keep docs/ in sync with code changes
   - Document API endpoints, parameters, return values
   - Include usage examples

6. **Testing & Validation**
   - Test scripts against live Nessus instance (localhost:8834)
   - Verify API vs Web UI authentication requirements
   - Handle 412 errors gracefully (license restrictions)
   - Check scan_config_debug.json for detailed responses

### Common Workflows for Claude

#### Creating New Automation Script
1. Analyze existing scripts in nessusAPIWrapper/ for patterns
2. Create in nessusAPIWrapper/ directory (not claudeScripts/)
3. Add to README.md under appropriate section
4. Test with venv activated
5. Commit with descriptive message

#### Working on MCP Server Implementation
1. **Always start session by reading**: `mcp-server/README.md` ⭐
2. **Check current phase**: Look for "Current Phase" marker in README
3. **Follow active phase guide**: Open corresponding `mcp-server/phases/PHASE_X_*.md` file
4. **Reference architecture**: `mcp-server/ARCHITECTURE_v2.2.md` for design decisions
5. **Track progress**: Check/uncheck tasks in phase files as you complete them
6. **Commit frequently**: Small, logical commits with descriptive messages

**Key MCP Server Resources:**
- `mcp-server/README.md` - Master tracker (updated each session)
- `mcp-server/ARCHITECTURE_v2.2.md` - Complete technical design
- `mcp-server/phases/PHASE_1_REAL_NESSUS.md` - Current phase (Phase 0 complete ✅)
- `mcp-server/phases/phase0/PHASE0_STATUS.md` - Phase 0 completion report
- `mcp-server/NESSUS_MCP_SERVER_REQUIREMENTS.md` - Functional requirements
- FastMCP docs: `docs/fastMCPServer/INDEX.md`

**Implementation Approach:**
- Phase 0: Mock scanner, basic tools, Docker setup (Days 1-2)
- Phase 1: Real Nessus + Redis queue + worker (Week 1)
- Phase 2: Schema system + results retrieval (Week 2)
- Phase 3: Observability + testing (Week 3)
- Phase 4: Production hardening (Week 4)

#### Debugging Nessus API Issues
1. Use `nessusAPIWrapper/check_status.py` to verify server health
2. Check scan_config_debug.json for full API responses
3. Use `nessusAPIWrapper/check_dropdown_options.py` for credential field options
4. Enable verbose output in scripts (add print statements)
5. Save debug output to temp/ for analysis

#### Generating Reports/Summaries
1. Export data using `nessusAPIWrapper/export_vulnerabilities_detailed.py`
2. Process JSON in temp/ directory
3. Generate summary reports (CSV, Markdown)
4. Save final outputs to temp/
5. Ask user before moving to docs/

#### One-off Tasks
1. Create script in claudeScripts/
2. Use temp/ for intermediate data
3. Document results in temp/ if needed
4. Clean up when task is complete

## Nessus API Considerations

### License Limitations (Nessus Essentials)

**API Access**: `api: true` (read-only)
- List scans, view configs, export results
- Check server status, plugin info

**Scan Control**: `scan_api: false` (BLOCKED)
- Cannot create/launch/stop/edit/delete via API
- 412 Precondition Failed error
- **Workaround**: Web UI simulation (session tokens)

### Script Categories

**API Scripts** (pytenable library) - in nessusAPIWrapper/:
- list_scans.py
- scan_config.py
- check_status.py
- export_vulnerabilities.py
- export_vulnerabilities_detailed.py
- check_dropdown_options.py

**Web UI Scripts** (requests library) - in nessusAPIWrapper/:
- launch_scan.py
- edit_scan.py
- manage_credentials.py
- manage_scans.py

### Authentication Flow

**API (Read-only)**:
```python
from tenable.nessus import Nessus
nessus = Nessus(
    url='https://localhost:8834',
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    ssl_verify=False
)
```

**Web UI (Control)**:
```python
import requests

# 1. Authenticate and get session token
session_token = authenticate(USERNAME, PASSWORD)

# 2. Use session token in requests
headers = {
    'X-API-Token': STATIC_API_TOKEN,
    'X-Cookie': f'token={session_token}'
}

response = requests.post(url, json=payload, headers=headers, verify=False)
```

## Development Best Practices

### Code Style
- Follow PEP 8 conventions
- Use meaningful variable names
- Add docstrings to functions
- Include usage examples in module docstring

### Error Handling
```python
try:
    # API call
except Exception as e:
    print(f"[FAILED] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Output Formatting
```python
print("[SUCCESS] Operation completed")
print("[FAILED] Operation failed")
print("[INFO] Additional information")
print("[WARNING] Potential issue detected")
```

### Sensitive Data Masking
```python
def mask_sensitive(key, value):
    sensitive_keys = ['password', 'private_key', 'passphrase', 'secret', 'key_file']
    if any(sk in key.lower() for sk in sensitive_keys) and value:
        return "***REDACTED***"
    return value
```

## Troubleshooting

### Python Environment Issues
```bash
# Verify venv exists
ls -la venv/

# Recreate if needed
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Nessus Connection Issues
```bash
# Check if Nessus is running
docker compose -f /home/nessus/docker/nessus/docker-compose.yml ps

# Check API access
curl -k https://localhost:8834/server/status
```

### Permission Issues
```bash
# Verify credentials.md permissions
chmod 600 credentials.md

# Check project directory ownership
ls -la /home/nessus/projects/nessus-api/
```

## Quick Reference

### Activate Environment
```bash
source /home/nessus/projects/nessus-api/venv/bin/activate
```

### Run Common Operations
```bash
# List scans
python nessusAPIWrapper/list_scans.py

# Create scan
python nessusAPIWrapper/manage_scans.py create "Scan Name" "192.168.1.1"

# Export results
python nessusAPIWrapper/export_vulnerabilities_detailed.py 24
```

### Git Sync
```bash
# Check status
git status

# Commit changes
git add .
git commit -m "Description"

# Push to remote
git push origin main
```

### Docker Operations
```bash
# Start Nessus
cd /home/nessus/docker/nessus && docker compose up -d

# View logs
docker compose logs -f nessus-pro

# Stop Nessus
docker compose down
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-31
**Maintained By**: Claude Code + User
