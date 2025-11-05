# Nessus Essentials Automation Scripts

## Overview

Python automation scripts for managing Nessus Essentials scans. This project includes **FULL SCAN AUTOMATION** via Web UI simulation, bypassing the `scan_api: false` API restrictions.

**Environment**: Linux (Ubuntu 24.04) | Docker-based Nessus | Python 3.12 Virtual Environment

## Quick Start

```bash
# Clone repository
git clone https://github.com/eafonin/nessus-api.git
cd nessus-api

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Verify Nessus is running
curl -k https://localhost:8834/server/status

# List scans
python list_scans.py
```

See [PROJECT_SETUP.md](PROJECT_SETUP.md) for detailed setup and conventions.

## Key Innovation

While Nessus Essentials restricts scan control via API (`scan_api: false`), this project **bypasses these restrictions** by simulating Web UI interactions using HTTP requests with proper authentication headers.

### What This Means

- Create, launch, stop, edit, and delete scans programmatically
- Manage SSH credentials via JSON templates
- Full automation capabilities without Nessus Professional license
- Read-only API operations for viewing and exporting results

## Project Structure

```
/home/nessus/projects/nessus-api/
├── nessusAPIWrapper/              # Existing Nessus automation scripts
│   ├── CODEBASE_INDEX.md         # Script inventory and documentation
│   │
│   ├── API-Based Scripts (Read-Only Operations)
│   │   ├── list_scans.py                       # List all scans
│   │   ├── scan_config.py                      # View scan configuration
│   │   ├── check_status.py                     # Check server status
│   │   ├── export_vulnerabilities.py           # Export vulnerability summaries
│   │   └── export_vulnerabilities_detailed.py  # Export FULL details
│   │
│   └── Web UI Simulation Scripts (Full Control)
│       ├── launch_scan.py                      # Launch/stop scans
│       ├── edit_scan.py                        # Edit scan parameters
│       ├── manage_credentials.py               # SSH credential management
│       ├── manage_scans.py                     # Create/delete scans
│       └── check_dropdown_options.py           # Extract field options
│
├── mcp-server/                    # 🚀 MCP server implementation (Active Development)
│   ├── README.md                  # ⭐ START HERE - Master implementation tracker
│   ├── ARCHITECTURE_v2.2.md       # Complete technical design (production-ready)
│   ├── NESSUS_MCP_SERVER_REQUIREMENTS.md  # Functional requirements
│   ├── PHASE_0-4.md              # 4 detailed implementation guides
│   ├── archive/                  # Previous architecture versions
│   ├── scanners/                 # Scanner abstraction layer (stubs ready)
│   ├── core/                     # Task management, queue, state machine (stubs ready)
│   ├── schema/                   # Results conversion & filtering (stubs ready)
│   ├── tools/                    # MCP tool implementations (stubs ready)
│   ├── worker/                   # Background scanner worker (stubs ready)
│   └── tests/                    # Test suite (to be created in Phase 0)
│
├── dev1/                          # Development environment (to be created in Phase 0)
├── prod/                          # Production environment (to be created in Phase 4)
│
├── docs/                          # Documentation
│   ├── DOCKER_SETUP.md           # Docker configuration and maintenance
│   ├── CODEBASE_INDEX.md         # General project documentation
│   └── fastMCPServer/            # FastMCP framework documentation (43 files)
│       └── INDEX.md              # Quick reference for MCP development
│
├── claudeScripts/                 # Throw-away scripts (temporary utilities)
├── temp/                          # Intermediate outputs (git-ignored)
├── venv/                          # Python virtual environment (git-ignored)
│
├── Documentation
│   ├── README.md                           # This file
│   ├── PROJECT_SETUP.md                    # Project conventions and setup guide
│   ├── NESSUS_ESSENTIALS_LIMITATIONS.md    # API restrictions
│   └── nessus_automation_prompt.md         # LLM usage template
│
├── requirements.txt               # Python dependencies
└── credentials.md                 # Sensitive credentials (git-ignored)
```

**Important**: This project uses a Python virtual environment. Always activate it before running scripts:
```bash
source venv/bin/activate
```

**Two Components:**
1. **nessusAPIWrapper/** - Production-ready scripts for direct Nessus automation
2. **mcp-server/** - MCP (Model Context Protocol) server for AI agent integration
   - Ready for Phase 0 implementation (see [mcp-server/README.md](mcp-server/README.md))
   - Complete documentation: Architecture, Requirements, 4 Phase Guides
   - Stub code structure ready (779 lines across scanners, core, schema, tools, worker)

## Authentication Methods

### API Authentication (Read-Only)
For viewing scans and exporting data:
```python
access_key = 'abc04cab03684de788ba0c4614eaba6302d3fe26852da06040eac3879547e405'
secret_key = '06332ecfd4bc633667be4e20e139c9451a848c580da988c69679fde16ce9c837'
```

### Web UI Authentication (Full Control)
For scan control operations:
```python
username = 'nessus'
password = 'nessus'
# Generates session token for X-Cookie header
# Combined with static X-API-Token header
```

---

## Script Reference

### API-Based Scripts (Read-Only)

#### 1. list_scans.py
**Purpose**: List all scans with status information

**Usage**:
```bash
python nessusAPIWrapper/list_scans.py
```

**Output**:
- Scan ID, name, status
- Folder location
- Last modification timestamp
- Enabled status
- UUID

**Authentication**: API keys (access_key/secret_key)

**API Requirement**: `api: true` (works with Essentials)

---

#### 2. scan_config.py
**Purpose**: Display detailed scan configuration including credentials

**Usage**:
```bash
python nessusAPIWrapper/scan_config.py [scan_id_or_name]
```

**Examples**:
```bash
python nessusAPIWrapper/scan_config.py                # Default scan
python nessusAPIWrapper/scan_config.py 12             # By ID
python nessusAPIWrapper/scan_config.py "172.32.0.209" # By partial name
```

**Output**:
- Basic scan info (ID, UUID, owner, policy)
- Target list
- SSH/Windows credentials (passwords masked)
- Schedule settings
- Plugin configuration
- Advanced options

**Authentication**: API keys

**API Requirement**: `api: true` (works with Essentials)

---

#### 3. check_status.py
**Purpose**: Check Nessus server health

**Usage**:
```bash
python nessusAPIWrapper/check_status.py
```

**Output**:
- Server status (ready/starting)
- Plugin feed status
- Database status

**Authentication**: API keys

**API Requirement**: `api: true` (works with Essentials)

---

#### 4. export_vulnerabilities.py
**Purpose**: Quick vulnerability export (summary data)

**Usage**:
```bash
python nessusAPIWrapper/export_vulnerabilities.py <scan_id_or_name> [format]
```

**Formats**: `json`, `csv`, `nessus`, `html`, `pdf`, `all`

**Examples**:
```bash
python nessusAPIWrapper/export_vulnerabilities.py 12 csv
python nessusAPIWrapper/export_vulnerabilities.py "172.32.0.215" all
```

**Output**:
- Vulnerability summary by severity
- Host summary with counts
- Top 10 critical/high vulnerabilities
- Export files: `vulns_{scan_name}_{timestamp}.{format}`

**Authentication**: API keys

**API Requirement**: `api: true` (works with Essentials)

---

#### 5. export_vulnerabilities_detailed.py
**Purpose**: Export FULL vulnerability details (RECOMMENDED for analysis)

**Usage**:
```bash
python nessusAPIWrapper/export_vulnerabilities_detailed.py <scan_id_or_name>
```

**Examples**:
```bash
python nessusAPIWrapper/export_vulnerabilities_detailed.py 24
python nessusAPIWrapper/export_vulnerabilities_detailed.py "corrosion"
```

**Output**:
- Complete plugin details (CVE, CVSS, descriptions)
- Exploit availability, patch dates, solutions
- Plugin output, risk factors, references
- VPR/EPSS scores, threat intelligence
- Export file: `vulns_detailed_{scan_name}_{timestamp}.json`

**Authentication**: API keys

**API Requirement**: `api: true` (works with Essentials)

**Note**: Takes longer (fetches full data for each plugin)

---

### Web UI Simulation Scripts (Full Control)

#### 6. launch_scan.py
**Purpose**: Launch, stop, and list scans via Web UI simulation

**Usage**:
```bash
python nessusAPIWrapper/launch_scan.py list                  # List scans
python nessusAPIWrapper/launch_scan.py launch <scan_id>      # Launch specific scan
python nessusAPIWrapper/launch_scan.py stop <scan_id>        # Stop specific scan
python nessusAPIWrapper/launch_scan.py stop-all              # Stop all running scans
```

**Examples**:
```bash
python nessusAPIWrapper/launch_scan.py list
python nessusAPIWrapper/launch_scan.py launch 24
python nessusAPIWrapper/launch_scan.py stop 12
python nessusAPIWrapper/launch_scan.py stop-all
```

**Output**:
- [SUCCESS] or [FAILED] status indicators
- Scan UUID for launched scans

**Authentication**: Web UI (username/password)

**Requires**: Session token from `/session` endpoint

**Bypasses**: `scan_api: false` restriction

---

#### 7. edit_scan.py
**Purpose**: Edit basic scan parameters (name, description, targets)

**Usage**:
```bash
python nessusAPIWrapper/edit_scan.py <scan_id> [--name NAME] [--description DESC] [--targets TARGETS]
```

**Examples**:
```bash
python nessusAPIWrapper/edit_scan.py 24 --name "Updated Scan"
python nessusAPIWrapper/edit_scan.py 24 --targets "172.32.0.1-254"
python nessusAPIWrapper/edit_scan.py 24 --name "Web Server Scan" --description "Weekly scan" --targets "192.168.1.10"
```

**Output**:
- [SUCCESS] Scan updated
- [FAILED] with error details

**Authentication**: Web UI (username/password)

**Requires**: Session token from `/session` endpoint

**Bypasses**: `scan_api: false` restriction

**Note**: Does NOT edit credentials (use manage_credentials.py for that)

---

#### 8. manage_credentials.py
**Purpose**: SSH credential management via JSON template workflow

**Usage**:
```bash
python nessusAPIWrapper/manage_credentials.py <scan_id>                     # Export template
python nessusAPIWrapper/manage_credentials.py <scan_id> <json_file>         # Import credentials
```

**Workflow**:
1. **Export template**: `python nessusAPIWrapper/manage_credentials.py 24`
   - Creates `scan_24_ssh_credentials.json`
   - Includes existing credentials with masked passwords (or PLACEHOLDER if created by manage_scans.py)
   - Shows available options for dropdown fields (auth methods, privilege escalation, etc.)

2. **Edit JSON file**: Fill in credentials
   ```json
   {
     "auth_method": "password",
     "username": "admin",
     "password": "secret123",
     "elevate_privileges_with": "Nothing"
   }
   ```

3. **Import credentials**: `python nessusAPIWrapper/manage_credentials.py 24 scan_24_ssh_credentials.json`
   - Updates scan with new credentials
   - Validates against available options
   - **Can create credentials from scratch** (replaces PLACEHOLDER or adds new)

**Output**:
- Export: JSON template file with all available fields
- Import: [SUCCESS] or [FAILED] with validation errors

**Authentication**: Web UI (username/password)

**Requires**: Session token from `/session` endpoint

**Bypasses**: `scan_api: false` restriction

**Key Feature**: Dynamically extracts dropdown options from Nessus configuration

---

#### 9. manage_scans.py
**Purpose**: Create and delete scans

**Usage**:
```bash
python nessusAPIWrapper/manage_scans.py create "Scan Name" "IP/CIDR" ["Description"]
python nessusAPIWrapper/manage_scans.py delete <scan_id>
```

**Examples**:
```bash
python nessusAPIWrapper/manage_scans.py create "Web Server Scan" "192.168.1.0/24"
python nessusAPIWrapper/manage_scans.py create "Host Scan" "172.32.0.215" "Production server"
python nessusAPIWrapper/manage_scans.py delete 25
```

**Output**:
- Create: [SUCCESS] New scan ID: 26
- Delete: [SUCCESS] Scan ID 25 deleted permanently

**Authentication**: Web UI (username/password)

**Requires**: Session token from `/session` endpoint

**Bypasses**: `scan_api: false` restriction

**Delete Process**: Fully automated (moves to trash, then permanently deletes)

**Create Process**:
- Uses "Advanced Scan" template by default
- **Automatically adds PLACEHOLDER SSH credentials** for easy updating later
- No manual UI configuration needed

---

#### 10. check_dropdown_options.py
**Purpose**: Extract available options for credential fields from Nessus configuration

**Usage**:
```bash
python nessusAPIWrapper/check_dropdown_options.py <scan_id>
```

**Output**:
- Lists all credential types (SSH, Windows, SNMP, etc.)
- Shows available options for dropdown fields
- Displays field types (radio, select, password, text)

**Authentication**: API keys

**Use Case**: Helper script for understanding credential field options

---

## Complete Workflow Examples

### Example 1: Create and Launch New Scan (Complete Automation)
```bash
# 1. Create scan with automatic PLACEHOLDER SSH credentials
python nessusAPIWrapper/manage_scans.py create "New Server Scan" "172.32.0.100"
# Output: [SUCCESS] New scan ID: 30
#         [INFO] Dummy SSH credentials added (username/password: PLACEHOLDER)

# 2. Configure SSH credentials
python nessusAPIWrapper/manage_credentials.py 30
# Creates scan_30_ssh_credentials.json

# Edit the JSON file:
# {
#   "username": "admin",
#   "password": "yourpassword",
#   "elevate_privileges_with": "Nothing"
# }

python nessusAPIWrapper/manage_credentials.py 30 scan_30_ssh_credentials.json
# Output: [SUCCESS] SSH credentials updated for scan 30

# 3. Launch scan
python nessusAPIWrapper/launch_scan.py launch 30

# 4. Monitor progress
python nessusAPIWrapper/list_scans.py

# 5. Export results (once completed)
python nessusAPIWrapper/export_vulnerabilities_detailed.py 30
```

### Example 2: Bulk Delete Scans
```bash
# List scans to find IDs
python nessusAPIWrapper/list_scans.py

# Delete scans with "test" in name (manually)
python nessusAPIWrapper/manage_scans.py delete 15
python nessusAPIWrapper/manage_scans.py delete 18
python nessusAPIWrapper/manage_scans.py delete 22
```

### Example 3: Edit Existing Scan
```bash
# Update scan targets
python nessusAPIWrapper/edit_scan.py 24 --targets "172.32.0.1-50"

# Launch updated scan
python nessusAPIWrapper/launch_scan.py launch 24

# Stop if needed
python nessusAPIWrapper/launch_scan.py stop 24
```

### Example 4: Daily Reporting
```bash
# Export all completed scans
python nessusAPIWrapper/list_scans.py  # Get scan IDs
python nessusAPIWrapper/export_vulnerabilities_detailed.py 12
python nessusAPIWrapper/export_vulnerabilities_detailed.py 24
python nessusAPIWrapper/export_vulnerabilities_detailed.py 30
```

---

## API vs Web UI Limitations

### What Works with API (scan_api: false)

| Operation | Endpoint | Status |
|-----------|----------|--------|
| List scans | `GET /scans` | Works |
| Scan details | `GET /scans/{id}` | Works |
| Scan config | `GET /editor/scan/{id}` | Works |
| Export scan | `POST /scans/{id}/export` | Works |
| Server status | `GET /server/properties` | Works |

### What Requires Web UI Simulation

| Operation | Endpoint | API Error | Web UI Workaround |
|-----------|----------|-----------|-------------------|
| Create scan | `POST /scans` | 412 Precondition Failed | manage_scans.py create |
| Launch scan | `POST /scans/{id}/launch` | 412 Precondition Failed | launch_scan.py launch |
| Stop scan | `POST /scans/{id}/stop` | 412 Precondition Failed | launch_scan.py stop |
| Modify scan | `PUT /scans/{id}` | 412 Precondition Failed | edit_scan.py |
| Delete scan | `DELETE /scans/{id}` | 412 Precondition Failed | manage_scans.py delete |

### Key Insight

The `scan_api: false` license flag only restricts **API endpoints**. The **Web UI routes** use the same backend but with different authentication (session tokens instead of API keys), allowing full automation by simulating browser requests.

---

## Configuration

### API Configuration (Hardcoded)
```python
NESSUS_URL = 'https://localhost:8834'
ACCESS_KEY = 'abc04cab03684de788ba0c4614eaba6302d3fe26852da06040eac3879547e405'
SECRET_KEY = '06332ecfd4bc633667be4e20e139c9451a848c580da988c69679fde16ce9c837'
```

### Web UI Configuration (Hardcoded)
```python
NESSUS_URL = 'https://localhost:8834'
USERNAME = 'nessus'
PASSWORD = 'nessus'
STATIC_API_TOKEN = 'af824aba-e642-4e63-a49b-0810542ad8a5'
# Session token obtained dynamically via POST /session
```

---

## Security Notes

- Passwords in scan configurations are masked as `***REDACTED***`
- Nessus API does not expose stored credentials in plaintext
- SSL verification disabled for localhost (self-signed certificates)
- DO NOT use these settings in production without proper SSL setup
- API keys and passwords are hardcoded (not production-ready)
- Session tokens expire and are regenerated per script execution

---

## System Requirements

### Host System
- **OS**: Linux (Ubuntu 24.04+) with Docker support
- **User**: Must be in docker group
- **Python**: 3.12+
- **Docker**: For running Nessus container (see [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md))

### Python Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Required packages**:
- pytenable >= 1.4.0
- requests >= 2.31.0
- urllib3 >= 2.0.0

### Nessus Instance

Nessus runs in Docker at `/home/nessus/docker/nessus/` with:
- Web UI: https://localhost:8834
- VPN Gateway: WireGuard (Gluetun)
- Network: 172.32.0.0/24

See [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) for Docker configuration details.

---

## Troubleshooting

### Error: "API is not available" (412)
This confirms you're hitting the `scan_api: false` restriction. Use Web UI simulation scripts instead:
- Use `manage_scans.py` instead of API create
- Use `launch_scan.py` instead of API launch
- Use `edit_scan.py` instead of API modify

### Error: Connection refused
- Ensure Nessus service is running
- Verify URL is `https://localhost:8834`

### Error: Authentication failed
- Verify username/password for Web UI scripts
- Verify access_key/secret_key for API scripts
- Check if user account is locked

### Error: SSL Certificate warnings
Expected with self-signed certificates. Suppressed with `urllib3.disable_warnings()`.

---

## For LLM (Claude Code) Usage

### Chaining Scripts for Complex Tasks

**Pattern 1: Create, Configure, Launch, Export**
```bash
nessusAPIWrapper/manage_scans.py create --name "X" --targets "Y"
  → Returns scan_id
nessusAPIWrapper/manage_credentials.py export <scan_id>
  → Edit JSON manually
nessusAPIWrapper/manage_credentials.py import <scan_id> <json>
nessusAPIWrapper/launch_scan.py launch <scan_id>
  → Wait for completion (check with list_scans.py)
nessusAPIWrapper/export_vulnerabilities_detailed.py <scan_id>
```

**Pattern 2: Bulk Operations**
```bash
nessusAPIWrapper/list_scans.py
  → Parse output for scan IDs matching criteria
For each scan_id:
  nessusAPIWrapper/launch_scan.py stop <scan_id>  # or delete, or export
```

**Pattern 3: Update and Relaunch**
```bash
nessusAPIWrapper/edit_scan.py <scan_id> --targets "new_targets"
nessusAPIWrapper/launch_scan.py launch <scan_id>
```

### Script Selection Guide

- **View scans**: `nessusAPIWrapper/list_scans.py`
- **View configuration**: `nessusAPIWrapper/scan_config.py`
- **Create scan**: `nessusAPIWrapper/manage_scans.py create`
- **Delete scan**: `nessusAPIWrapper/manage_scans.py delete`
- **Launch scan**: `nessusAPIWrapper/launch_scan.py launch`
- **Stop scan**: `nessusAPIWrapper/launch_scan.py stop`
- **Edit basic params**: `nessusAPIWrapper/edit_scan.py`
- **Edit credentials**: `nessusAPIWrapper/manage_credentials.py`
- **Export results**: `nessusAPIWrapper/export_vulnerabilities_detailed.py` (recommended) or `nessusAPIWrapper/export_vulnerabilities.py`
- **Check server**: `nessusAPIWrapper/check_status.py`

---

## Nessus Essentials License Features

From `GET /server/properties`:
```json
{
  "license": {
    "type": "home",
    "name": "Nessus Essentials",
    "restricted": true,
    "ips": 16,
    "features": {
      "api": true,           // General API access (read-only)
      "scan_api": false,     // Scan control API DISABLED
      "policies": true,
      "report": true,
      "users": false,
      "vpr": false
    }
  }
}
```

**With this project, all scan control operations are automated despite `scan_api: false`.**

---

## Project Status

**Status**: PRODUCTION READY

**Capabilities**:
- Full scan lifecycle automation (create, launch, stop, edit, delete)
- Credential management via JSON templates
- Comprehensive vulnerability exporting
- Works with Nessus Essentials (free tier)

**Limitations**:
- Credentials hardcoded (not production-ready for security)
- No retry logic for failed operations
- No logging to files
- No parallel execution for bulk operations

---

## Additional Resources

### Documentation
- [PROJECT_SETUP.md](PROJECT_SETUP.md) - Project conventions, directory structure, Claude Code guidelines
- [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) - Docker setup, networking, maintenance, troubleshooting
- [nessusAPIWrapper/CODEBASE_INDEX.md](nessusAPIWrapper/CODEBASE_INDEX.md) - Complete script inventory and details
- [mcp-server/](mcp-server/) - MCP server architecture and requirements (planning phase)
- [NESSUS_ESSENTIALS_LIMITATIONS.md](NESSUS_ESSENTIALS_LIMITATIONS.md) - API restrictions and workarounds
- [nessus_automation_prompt.md](nessus_automation_prompt.md) - LLM usage template

### External Resources
- **Tenable pyTenable Documentation**: https://pytenable.readthedocs.io
- **Nessus API Reference**: https://developer.tenable.com/reference/navigate
- **GitHub Repository**: https://github.com/eafonin/nessus-api

### Local Resources
- Python venv: `/home/nessus/projects/nessus-api/venv/`
- Docker setup: `/home/nessus/docker/nessus/`
- Credentials: `credentials.md` (git-ignored)

---

**Project Status**: Production Ready
**Last Updated**: 2025-10-31
**License**: Nessus Essentials 10.x with successful Web UI simulation bypass
**Environment**: Linux (Ubuntu 24.04) | Docker | Python 3.12
