# Nessus API Wrapper Scripts

> **Purpose**: Production-ready Python scripts for automating Nessus Essentials vulnerability scanning
> **Key Innovation**: Bypasses `scan_api: false` restriction via Web UI simulation
> **Status**: Production Ready

---

## Overview

This directory contains Python automation scripts that provide full control over Nessus Essentials scans despite API limitations. The scripts are divided into two categories:

1. **API-Based Scripts** - Read-only operations using official API
2. **Web UI Simulation** - Full control operations bypassing API restrictions

All scripts are production-tested and documented. See [CODEBASE_INDEX.md](./CODEBASE_INDEX.md) for complete inventory.

---

## Quick Start

```bash
# Ensure virtual environment is activated
source /home/nessus/projects/nessus-api/venv/bin/activate

# List all scans
python nessusAPIWrapper/list_scans.py

# Create and launch a scan
python nessusAPIWrapper/manage_scans.py create "My Scan" "192.168.1.0/24"
python nessusAPIWrapper/launch_scan.py launch <scan_id>

# Export results
python nessusAPIWrapper/export_vulnerabilities_detailed.py <scan_id>
```

---

## Script Categories

### API-Based Scripts (Read-Only)

These scripts use official Nessus API with access/secret keys. Work with `api: true` flag.

| Script | Purpose | Key Features |
|--------|---------|--------------|
| `list_scans.py` | List all scans | Status, folder, timestamps |
| `scan_config.py` | View scan configuration | Targets, credentials (masked), settings |
| `check_status.py` | Server health check | Status, plugin feed, database |
| `test_scanner_status.py` | Scanner status test | License, plugin set, activation code, feed status |
| `export_vulnerabilities.py` | Quick export | Summary data, multiple formats |
| `export_vulnerabilities_detailed.py` | Full export | Complete plugin details, CVEs, CVSS |

### Web UI Simulation Scripts (Full Control)

These scripts simulate browser requests to bypass `scan_api: false` restriction.

| Script | Purpose | Key Features |
|--------|---------|--------------|
| `launch_scan.py` | Launch/stop scans | Non-blocking, UUID tracking |
| `edit_scan.py` | Edit scan parameters | Name, description, targets |
| `manage_credentials.py` | SSH credential management | JSON template workflow |
| `manage_scans.py` | Create/delete scans | Auto PLACEHOLDER credentials |
| `check_dropdown_options.py` | Extract field options | Helper for credentials |

---

## Authentication Methods

### Critical Distinction: API vs Web UI Endpoints

**Understanding when to use each authentication method:**

#### Nessus API (Official) - READ Operations
- **What**: Official Tenable-documented REST API
- **Authentication**: API keys (access_key/secret_key)
- **Key Generation**: Manual creation required in Nessus Web UI (Settings → API Keys → Generate)
- **Essentials Limitation**: Only READ operations allowed (`scan_api: false`)
- **Use Cases**:
  - ✅ List scans (`list_scans.py`)
  - ✅ View scan configuration (`scan_config.py`)
  - ✅ Check server status (`check_status.py`)
  - ✅ Export results (`export_*.py`)
  - ❌ Create/launch/edit/delete scans (HTTP 412 error)

#### Web UI Endpoints (Internal) - CHANGE Operations
- **What**: Internal endpoints used by browser interface (undocumented)
- **Authentication**: Username/password + X-API-Token (dynamically fetched)
- **Token Source**: Extracted from `nessus6.js` at runtime (installation-specific)
- **Essentials Support**: Full WRITE operations (bypasses `scan_api` restriction)
- **Use Cases**:
  - ✅ Create scans (`manage_scans.py`)
  - ✅ Launch/stop scans (`launch_scan.py`)
  - ✅ Edit scan parameters (`edit_scan.py`)
  - ✅ Manage credentials (`manage_credentials.py`)
  - ✅ Delete scans (`manage_scans.py`)

**Why This Matters**:
- API keys work for reading data but fail for write operations on Nessus Essentials
- Web UI simulation bypasses Essentials restrictions by mimicking browser behavior
- Both authentication methods can coexist (use API for reads, Web UI for writes)

### API Authentication (Read-Only)
```python
access_key = 'abc04cab...'
secret_key = '06332ecf...'
```

**Manual Setup Required**: Generate keys in Nessus Web UI → Settings → API Keys

Used by: `list_scans.py`, `scan_config.py`, `check_status.py`, `export_*.py`

### Web UI Authentication (Full Control)
```python
username = 'nessus'
password = 'nessus'
# Generates session token via POST /session
# X-API-Token fetched dynamically from nessus6.js
```

Used by: `launch_scan.py`, `edit_scan.py`, `manage_credentials.py`, `manage_scans.py`

### X-API-Token Requirement

Web UI simulation scripts require a special `X-API-Token` header that is:

- **Hardcoded in Nessus Web UI** (`/nessus6.js`)
- **Required for all write operations** (launch, stop, edit, create, delete scans)
- **NOT returned in authentication responses**
- **Changes when Nessus is rebuilt/reinstalled**

**Solution**: Scripts automatically fetch the current X-API-Token at runtime from `nessus6.js` using the `get_api_token.py` utility. This ensures scripts continue working after Nessus rebuilds without manual updates.

```python
# Automatic in all Web UI scripts
from get_api_token import extract_api_token_from_js

STATIC_API_TOKEN = extract_api_token_from_js()
if not STATIC_API_TOKEN:
    print("Error: Failed to fetch X-API-Token from Nessus Web UI")
    sys.exit(1)
```

**Note**: If scripts fail after Nessus rebuild, the X-API-Token has changed. The scripts will automatically fetch the new token on next run.

For detailed technical explanation, see [X-API-TOKEN_EXPLAINED.md](./X-API-TOKEN_EXPLAINED.md).

---

## Common Workflows

### Workflow 1: Create and Launch New Scan

```bash
# 1. Create scan (auto-adds PLACEHOLDER SSH credentials)
python nessusAPIWrapper/manage_scans.py create "New Server Scan" "172.32.0.100"
# Output: [SUCCESS] New scan ID: 30

# 2. Configure SSH credentials
python nessusAPIWrapper/manage_credentials.py 30
# Generates: scan_30_ssh_credentials.json

# 3. Edit JSON file with real credentials
# {
#   "username": "admin",
#   "password": "yourpassword",
#   "elevate_privileges_with": "Nothing"
# }

# 4. Import credentials
python nessusAPIWrapper/manage_credentials.py 30 scan_30_ssh_credentials.json

# 5. Launch scan
python nessusAPIWrapper/launch_scan.py launch 30

# 6. Monitor progress
python nessusAPIWrapper/list_scans.py

# 7. Export results when complete
python nessusAPIWrapper/export_vulnerabilities_detailed.py 30
```

### Workflow 2: Quick Scan Status Check

```bash
# Test scanner status (both scanners)
python nessusAPIWrapper/test_scanner_status.py

# Test specific scanner (JSON output)
python nessusAPIWrapper/test_scanner_status.py --scanner 2 --json

# List all scans with status
python nessusAPIWrapper/list_scans.py

# Check specific scan configuration
python nessusAPIWrapper/scan_config.py 24

# View server health
python nessusAPIWrapper/check_status.py
```

### Workflow 3: Bulk Operations

```bash
# Stop all running scans
python nessusAPIWrapper/launch_scan.py stop-all

# Export multiple completed scans
python nessusAPIWrapper/export_vulnerabilities_detailed.py 12
python nessusAPIWrapper/export_vulnerabilities_detailed.py 24
python nessusAPIWrapper/export_vulnerabilities_detailed.py 30
```

---

## Key Innovation: Bypassing API Restrictions

### The Problem
Nessus Essentials sets `scan_api: false` which blocks these API endpoints:
- `POST /scans` (create)
- `POST /scans/{id}/launch` (launch)
- `POST /scans/{id}/stop` (stop)
- `PUT /scans/{id}` (edit)
- `DELETE /scans/{id}` (delete)

### The Solution
Web UI routes use the **same backend** but with different authentication:
- API endpoints require: API keys (access_key/secret_key)
- Web UI routes require: Session token + static API token

By simulating Web UI requests with proper headers, we achieve full automation without Nessus Professional license.

---

## Configuration

All scripts are configured with hardcoded values (not production-ready for security):

```python
# In all scripts
NESSUS_URL = 'https://172.32.0.209:8834'

# API scripts
ACCESS_KEY = 'abc04cab...'
SECRET_KEY = '06332ecf...'

# Web UI scripts
USERNAME = 'nessus'
PASSWORD = 'nessus'
# STATIC_API_TOKEN - Auto-fetched from nessus6.js (no hardcoding needed)
```

**Notes**:
- Session tokens expire and are regenerated per script execution
- X-API-Token is dynamically fetched at runtime using `get_api_token.py`
- After Nessus rebuild, scripts automatically adapt to new X-API-Token

---

## Requirements

### Python Environment
```bash
# All scripts require virtual environment
source /home/nessus/projects/nessus-api/venv/bin/activate
```

### Dependencies (requirements.txt)
- `pytenable>=1.4.0` - Official Tenable API library
- `requests>=2.31.0` - HTTP library for Web UI simulation
- `urllib3>=2.0.0` - HTTP client (SSL warning suppression)

### Nessus Instance
- Docker container running at `https://localhost:8834`
- Nessus Essentials license (16 IPs)
- Network: 172.32.0.0/24 (via VPN gateway)

See [../docs/DOCKER_SETUP.md](../docs/DOCKER_SETUP.md) for Nessus configuration.

---

## Troubleshooting

### Error: "API is not available" (412)
This confirms `scan_api: false` restriction. Use Web UI simulation scripts:
- `manage_scans.py` instead of API create
- `launch_scan.py` instead of API launch
- `edit_scan.py` instead of API modify

### Error: Connection refused
- Verify Nessus is running: `curl -k https://localhost:8834/server/status`
- Check Docker containers: `docker ps` (in `/home/nessus/docker/nessus/`)

### Error: Authentication failed
- Verify username/password for Web UI scripts
- Verify access_key/secret_key for API scripts
- Check if user account is locked

### Error: SSL Certificate warnings
Expected with self-signed certificates. Suppressed with `urllib3.disable_warnings()`.

---

## Security Considerations

- Passwords in scan configurations are masked as `***REDACTED***`
- Nessus API does not expose stored credentials in plaintext
- SSL verification disabled for localhost (self-signed certificates)
- **NOT production-ready**: Credentials are hardcoded, no encryption at rest
- Session tokens expire and are regenerated per script execution

---

## File Organization

```
nessusAPIWrapper/
├── README.md                          # This file
├── CODEBASE_INDEX.md                  # Complete script inventory with details
│
├── API-Based Scripts (Read-Only)
│   ├── list_scans.py
│   ├── scan_config.py
│   ├── check_status.py
│   ├── test_scanner_status.py         # NEW: Scanner status test (both scanners)
│   ├── export_vulnerabilities.py
│   └── export_vulnerabilities_detailed.py
│
└── Web UI Simulation Scripts (Full Control)
    ├── launch_scan.py
    ├── edit_scan.py
    ├── manage_credentials.py
    ├── manage_scans.py
    └── check_dropdown_options.py
```

---

## Related Documentation

- [CODEBASE_INDEX.md](./CODEBASE_INDEX.md) - Detailed script documentation with examples
- [X-API-TOKEN_EXPLAINED.md](./X-API-TOKEN_EXPLAINED.md) - X-API-Token technical details and troubleshooting
- [../README.md](../README.md) - Project overview and architecture
- [../PROJECT_SETUP.md](../PROJECT_SETUP.md) - Development conventions and setup
- [../docs/DOCKER_SETUP.md](../docs/DOCKER_SETUP.md) - Nessus Docker configuration
- [../docs/NESSUS_ESSENTIALS_LIMITATIONS.md](../docs/NESSUS_ESSENTIALS_LIMITATIONS.md) - API restrictions

---

## External Resources

- **Tenable pyTenable Documentation**: https://pytenable.readthedocs.io
- **Nessus API Reference**: https://developer.tenable.com/reference/navigate
- **GitHub Repository**: https://github.com/eafonin/nessus-api

---

## For MCP Server Development

These scripts serve as **reference implementations** for the MCP server:
- Pattern for Nessus API interactions
- Error handling examples
- Credential management workflows
- Result export logic

**MCP server should NOT import these scripts directly**. Instead, implement native async versions following the patterns demonstrated here.

See [../mcp-server/README.md](../mcp-server/README.md) for MCP server implementation.

---

**Last Updated**: 2025-11-06
**Status**: Production Ready
**License**: Nessus Essentials 10.x
**Environment**: Ubuntu 24.04 | Docker | Python 3.12
