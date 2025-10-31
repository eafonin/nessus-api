# Nessus Essentials Automation Scripts

## Overview

Python automation scripts for managing Nessus Essentials scans. This project includes **FULL SCAN AUTOMATION** via Web UI simulation, bypassing the `scan_api: false` API restrictions.

## Key Innovation

While Nessus Essentials restricts scan control via API (`scan_api: false`), this project **bypasses these restrictions** by simulating Web UI interactions using HTTP requests with proper authentication headers.

### What This Means

- Create, launch, stop, edit, and delete scans programmatically
- Manage SSH credentials via JSON templates
- Full automation capabilities without Nessus Professional license
- Read-only API operations for viewing and exporting results

## Project Structure

```
c:\nessus\
├── API-Based Scripts (Read-Only Operations)
│   ├── list_scans.py                       # List all scans
│   ├── scan_config.py                      # View scan configuration
│   ├── check_status.py                     # Check server status
│   ├── export_vulnerabilities.py           # Export vulnerability summaries
│   └── export_vulnerabilities_detailed.py  # Export FULL details
│
├── Web UI Simulation Scripts (Full Control)
│   ├── launch_scan.py                      # Launch/stop scans
│   ├── edit_scan.py                        # Edit scan parameters
│   ├── manage_credentials.py               # SSH credential management
│   ├── manage_scans.py                     # Create/delete scans
│   └── check_dropdown_options.py           # Extract field options
│
└── Documentation
    ├── README.md                           # This file
    ├── NESSUS_ESSENTIALS_LIMITATIONS.md    # API restrictions (now with workarounds)
    └── nessus_automation_prompt.md         # LLM usage template
```

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
python list_scans.py
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
python scan_config.py [scan_id_or_name]
```

**Examples**:
```bash
python scan_config.py                # Default scan
python scan_config.py 12             # By ID
python scan_config.py "172.32.0.209" # By partial name
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
python check_status.py
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
python export_vulnerabilities.py <scan_id_or_name> [format]
```

**Formats**: `json`, `csv`, `nessus`, `html`, `pdf`, `all`

**Examples**:
```bash
python export_vulnerabilities.py 12 csv
python export_vulnerabilities.py "172.32.0.215" all
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
python export_vulnerabilities_detailed.py <scan_id_or_name>
```

**Examples**:
```bash
python export_vulnerabilities_detailed.py 24
python export_vulnerabilities_detailed.py "corrosion"
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
python launch_scan.py list                  # List scans
python launch_scan.py launch <scan_id>      # Launch specific scan
python launch_scan.py stop <scan_id>        # Stop specific scan
python launch_scan.py stop-all              # Stop all running scans
```

**Examples**:
```bash
python launch_scan.py list
python launch_scan.py launch 24
python launch_scan.py stop 12
python launch_scan.py stop-all
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
python edit_scan.py <scan_id> [--name NAME] [--description DESC] [--targets TARGETS]
```

**Examples**:
```bash
python edit_scan.py 24 --name "Updated Scan"
python edit_scan.py 24 --targets "172.32.0.1-254"
python edit_scan.py 24 --name "Web Server Scan" --description "Weekly scan" --targets "192.168.1.10"
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
python manage_credentials.py <scan_id>                     # Export template
python manage_credentials.py <scan_id> <json_file>         # Import credentials
```

**Workflow**:
1. **Export template**: `python manage_credentials.py 24`
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

3. **Import credentials**: `python manage_credentials.py 24 scan_24_ssh_credentials.json`
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
python manage_scans.py create "Scan Name" "IP/CIDR" ["Description"]
python manage_scans.py delete <scan_id>
```

**Examples**:
```bash
python manage_scans.py create "Web Server Scan" "192.168.1.0/24"
python manage_scans.py create "Host Scan" "172.32.0.215" "Production server"
python manage_scans.py delete 25
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
python check_dropdown_options.py <scan_id>
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
python manage_scans.py create "New Server Scan" "172.32.0.100"
# Output: [SUCCESS] New scan ID: 30
#         [INFO] Dummy SSH credentials added (username/password: PLACEHOLDER)

# 2. Configure SSH credentials
python manage_credentials.py 30
# Creates scan_30_ssh_credentials.json

# Edit the JSON file:
# {
#   "username": "admin",
#   "password": "yourpassword",
#   "elevate_privileges_with": "Nothing"
# }

python manage_credentials.py 30 scan_30_ssh_credentials.json
# Output: [SUCCESS] SSH credentials updated for scan 30

# 3. Launch scan
python launch_scan.py launch 30

# 4. Monitor progress
python list_scans.py

# 5. Export results (once completed)
python export_vulnerabilities_detailed.py 30
```

### Example 2: Bulk Delete Scans
```bash
# List scans to find IDs
python list_scans.py

# Delete scans with "test" in name (manually)
python manage_scans.py delete 15
python manage_scans.py delete 18
python manage_scans.py delete 22
```

### Example 3: Edit Existing Scan
```bash
# Update scan targets
python edit_scan.py 24 --targets "172.32.0.1-50"

# Launch updated scan
python launch_scan.py launch 24

# Stop if needed
python launch_scan.py stop 24
```

### Example 4: Daily Reporting
```bash
# Export all completed scans
python list_scans.py  # Get scan IDs
python export_vulnerabilities_detailed.py 12
python export_vulnerabilities_detailed.py 24
python export_vulnerabilities_detailed.py 30
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

## Dependencies

```bash
pip install pytenable requests
```

Or activate the virtual environment:
```bash
.\env\Scripts\activate
```

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
manage_scans.py create --name "X" --targets "Y"
  → Returns scan_id
manage_credentials.py export <scan_id>
  → Edit JSON manually
manage_credentials.py import <scan_id> <json>
launch_scan.py launch <scan_id>
  → Wait for completion (check with list_scans.py)
export_vulnerabilities_detailed.py <scan_id>
```

**Pattern 2: Bulk Operations**
```bash
list_scans.py
  → Parse output for scan IDs matching criteria
For each scan_id:
  launch_scan.py stop <scan_id>  # or delete, or export
```

**Pattern 3: Update and Relaunch**
```bash
edit_scan.py <scan_id> --targets "new_targets"
launch_scan.py launch <scan_id>
```

### Script Selection Guide

- **View scans**: `list_scans.py`
- **View configuration**: `scan_config.py`
- **Create scan**: `manage_scans.py create`
- **Delete scan**: `manage_scans.py delete`
- **Launch scan**: `launch_scan.py launch`
- **Stop scan**: `launch_scan.py stop`
- **Edit basic params**: `edit_scan.py`
- **Edit credentials**: `manage_credentials.py`
- **Export results**: `export_vulnerabilities_detailed.py` (recommended) or `export_vulnerabilities.py`
- **Check server**: `check_status.py`

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

- **Tenable pyTenable Documentation**: https://pytenable.readthedocs.io
- **Nessus API Reference**: https://developer.tenable.com/reference/navigate
- **Local pytenable source**: `.\env\Lib\site-packages\tenable\nessus\`

---

Last Updated: Based on Nessus Essentials 10.x with successful Web UI simulation bypass.
