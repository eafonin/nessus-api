# Nessus API Workflow Guide for MCP Server Development

> Concise reference for implementing automated Nessus vulnerability scanning via MCP server

## Purpose

This guide provides workflow-based documentation for Python developers building an MCP (Model Context Protocol) server that automates Nessus vulnerability scanning. It focuses on **Web UI simulation methods** that bypass Nessus Essentials API restrictions, enabling full scan lifecycle automation.

**Target Audience**: Python developers implementing MCP server tools
**Focus**: Web UI simulation approach (works with Nessus Essentials)
**Source Code**: [`nessusAPIWrapper/`](./README.md)

---

## API vs Web UI Endpoints: Critical Distinction

**Understanding what the wrapper scripts actually use**:

> **📖 Detailed Explanation**: See [README.md - Authentication Methods](./README.md#authentication-methods) for comprehensive documentation on when to use API vs Web UI endpoints, including setup requirements and use cases.

### Nessus REST API (Official, Documented) - READ Operations
- **What**: Official Tenable-documented API
- **Authentication**: Requires API keys (access_key/secret_key) - must be manually generated in Nessus Web UI
- **Limitation**: Disabled for WRITE operations in Nessus Essentials (`scan_api: false`)
- **Used For**: ✅ List scans, view configurations, check status, export results
- **Status**: ✅ **Used for READ operations only**

### Nessus Web UI Endpoints (Internal, Undocumented) - CHANGE Operations
- **What**: Internal endpoints used by the web browser interface
- **Authentication**: Username/password + X-API-Token (dynamically fetched from nessus6.js)
- **Advantage**: Works with Nessus Essentials (bypasses `scan_api` restriction)
- **Used For**: ✅ Create/launch/stop/edit/delete scans, manage credentials
- **Status**: ✅ **Used for WRITE operations**

### Why "Wrapper"?

These scripts are called "wrappers" because they **wrap Nessus Web UI endpoints** to provide programmatic access. They simulate browser behavior to bypass Nessus Essentials API limitations.

**Authentication Flow (Web UI Endpoints)**:
```python
# 0. Fetch X-API-Token dynamically (once per session)
GET /nessus6.js
→ Extract token via regex: getApiToken[^}]+return["']([A-F0-9-]+)["']
→ Example: '778F4A9C-D797-4817-B110-EC427B724486'

# 1. Authenticate via Web UI endpoint
POST /session
  Headers: {'X-API-Token': '{dynamically_fetched_token}'}
  Body: {'username': 'nessus', 'password': 'nessus'}
→ Returns session token

# 2. Make authenticated requests
GET /scans/11
  Headers: {
    'X-API-Token': '{dynamically_fetched_token}',
    'X-Cookie': 'token={session_token}'
  }
→ Returns scan data
```

**Key Headers (Web UI Simulation)**:
- `X-API-Token`: Installation-specific token (dynamically fetched from nessus6.js at runtime)
- `X-Cookie`: Dynamic session token from authentication
- `X-KL-kfa-Ajax-Request`: Web UI marker for launch/stop operations

**All operations in this guide use Web UI endpoints**, not the official REST API.

---

## Prerequisites

- Python 3.12+ with virtual environment
- Nessus instance at `https://localhost:8834`
- Valid Nessus credentials (username/password)
- Dependencies: `requests`, `urllib3`, `pytenable`

See [`requirements.txt`](./requirements.txt) for complete dependency list.

---

## Workflow Overview

The complete scan lifecycle follows this sequence:

```
1. Authentication     → Get session tokens
2. Create Scan        → Initialize scan with targets
3. Configure Creds    → Add SSH credentials (optional)
4. Launch Scan        → Start vulnerability scanning
5. Monitor Status     → Track scan progress
6. Export Results     → Retrieve vulnerability data
7. Cleanup            → Delete/archive scans
```

Each workflow stage is detailed below with function references and key parameters.

---

## Workflow Stage 1: Authentication

**Purpose**: Obtain authentication tokens for Web UI simulation

### Primary Function

**Location**: [`manage_scans.py:27-84`](./manage_scans.py)

```python
authenticate(username: str, password: str) -> tuple[str, str]
```

**Inputs**:
- `username` - Nessus username (default: `"nessus"`)
- `password` - Nessus password (default: `"nessus"`)

**Outputs**:
- `api_token` - Installation-specific X-API-Token (dynamically fetched from nessus6.js)
- `session_token` - Dynamic session token from `/session` endpoint
- Returns `(None, None)` on failure

**Usage Pattern**:
```python
# Token is fetched automatically within authenticate()
api_token, session_token = authenticate("nessus", "nessus")
if not api_token:
    # Handle authentication failure (includes token fetch failure)
```

**Headers Required**:
- `X-API-Token: {api_token}` - Fetched from nessus6.js at runtime
- `X-Cookie: token={session_token}` - From authentication response

**Session Lifecycle**:
- Session tokens expire after inactivity; re-authenticate as needed
- X-API-Token remains constant per Nessus installation (changes only after rebuild/reinstall)

### Alternative: API Keys (Read-Only Operations)

**Location**: Used in [`list_scans.py:11-16`](./list_scans.py), [`check_status.py:7-12`](./check_status.py)

```python
nessus = Nessus(
    url='https://172.32.0.209:8834',
    access_key='27f46c28...',  # API access key (manually generated)
    secret_key='11a99860...',  # API secret key (manually generated)
    ssl_verify=False
)
```

**Setup Required**: Generate keys manually in Nessus Web UI → Settings → API Keys → Generate

**Limitation**: API keys work for **read-only** operations (list scans, export results) but fail for write operations (create, launch, delete) on Nessus Essentials.

---

## Workflow Stage 2: Create Scan

**Purpose**: Create new vulnerability scan with specified targets

### Primary Function

**Location**: [`manage_scans.py:312-424`](./manage_scans.py)

```python
create_scan(
    api_token: str,
    session_token: str,
    name: str,
    targets: str,
    description: str = "",
    template_uuid: str = None
) -> dict
```

**Inputs**:
- `api_token`, `session_token` - From authentication
- `name` - Scan display name (e.g., `"Production Server Scan"`)
- `targets` - Comma-separated IPs/hostnames (e.g., `"192.168.1.1,192.168.1.2"`)
- `description` - Optional scan description
- `template_uuid` - Scan template (defaults to Advanced Scan: `ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66`)

**Outputs**:
- Success: Returns scan metadata dict with `scan.id`
- Failure: Returns `None`

**Automatic Behaviors**:
- Creates scan in "My Scans" folder (`folder_id=3`)
- Assigns to local scanner (`scanner_id='1'`)
- Adds placeholder SSH credentials (`username: PLACEHOLDER, password: PLACEHOLDER`)
- Sets `launch_now=False` (requires explicit launch)

**Example Response**:
```json
{
  "scan": {
    "id": 30,
    "name": "Production Server Scan",
    "enabled": false
  }
}
```

### Helper Functions

**Get Template Config**: [`manage_scans.py:87-133`](./manage_scans.py)
**Extract Settings**: [`manage_scans.py:136-176`](./manage_scans.py)

---

## Workflow Stage 3: Configure Credentials (Optional)

**Purpose**: Add or update SSH credentials for authenticated scanning

### Credential Management Workflow

**Location**: [`manage_credentials.py`](./manage_credentials.py)

#### Step 3.1: Export Credential Template

```python
export_credentials_template(scan_id: int, output_file: str) -> bool
```

**Location**: [`manage_credentials.py:319-348`](./manage_credentials.py)

**Inputs**:
- `scan_id` - Target scan ID
- `output_file` - JSON template filename (e.g., `scan_30_ssh_credentials.json`)

**Outputs**:
- Creates JSON template with current credential structure
- Returns `True` on success

**Template Structure**:
```json
{
  "_info": "Fill in the fields you want to set...",
  "auth_method": "password",
  "username": "PLACEHOLDER",
  "password": "",
  "elevate_privileges_with": "Nothing",
  "_elevate_options": ["Nothing", "sudo", "su", "pbrun", "dzdo", "..."]
}
```

#### Step 3.2: Import Filled Credentials

```python
import_credentials_from_template(
    scan_id: int,
    api_token: str,
    session_token: str,
    template_file: str
) -> bool
```

**Location**: [`manage_credentials.py:519-673`](./manage_credentials.py)

**Inputs**:
- `scan_id` - Target scan ID
- `api_token`, `session_token` - From authentication
- `template_file` - Filled JSON template

**Credential Fields**:
- `username` - SSH username (e.g., `"admin"`)
- `password` - SSH password
- `auth_method` - `"password"`, `"certificate"`, `"Kerberos"`, or `"public key"`
- `elevate_privileges_with` - Privilege escalation method
  - Options: `"Nothing"`, `"sudo"`, `"su"`, `"pbrun"`, `"dzdo"`, `"Cisco 'enable'"`
- `escalation_account` - Target user for escalation (optional)
- `escalation_password` - Password for escalation (optional)

**Important**: Scan must **not be running** when updating credentials

### Alternative: Edit Other Scan Parameters

**Location**: [`edit_scan.py:186-282`](./edit_scan.py)

```python
update_scan(
    scan_id: int,
    api_token: str,
    session_token: str,
    name: str = None,
    description: str = None,
    targets: str = None
) -> bool
```

Updates scan name, description, or targets without modifying credentials.

---

## Workflow Stage 4: Launch Scan

**Purpose**: Start scan execution

### Primary Function

**Location**: [`launch_scan.py:117-163`](./launch_scan.py)

```python
launch_scan(scan_id: int, api_token: str, cookie_token: str) -> None
```

**Inputs**:
- `scan_id` - Scan to launch
- `api_token`, `cookie_token` - From authentication (`cookie_token` = `session_token`)

**HTTP Endpoint**: `POST /scans/{scan_id}/launch`

**Key Headers**:
- `X-API-Token: {api_token}`
- `X-Cookie: token={cookie_token}`
- `X-KL-kfa-Ajax-Request: Ajax_Request` (Web UI simulation marker)

**Status Codes**:
- `200 OK` - Scan launched successfully
- `403 Forbidden` - License restriction (if using API keys)
- `404 Not Found` - Invalid scan ID

**Response**:
```json
{
  "scan_uuid": "template-uuid-here"
}
```

### Scan Control Functions

**Stop Scan**: [`launch_scan.py:166-213`](./launch_scan.py)
```python
stop_scan(scan_id: int, api_token: str, cookie_token: str) -> None
```

**Stop All Running Scans**: [`launch_scan.py:215-252`](./launch_scan.py)
```python
stop_all_scans() -> None
```

---

## Workflow Stage 5: Monitor Status

**Purpose**: Track scan progress and completion

### List All Scans

**Location**: [`list_scans.py:18-50`](./list_scans.py) or [`launch_scan.py:87-114`](./launch_scan.py)

```python
nessus.scans.list() -> dict
```

**Returns**:
```json
{
  "scans": [
    {
      "id": 30,
      "name": "Production Server Scan",
      "status": "running",  // "completed", "canceled", "paused"
      "enabled": false,
      "last_modification_date": 1699564800,
      "folder_id": 3
    }
  ],
  "folders": [...]
}
```

**Scan Status Values**:
- `running` - Actively scanning
- `completed` - Finished successfully
- `canceled` - User stopped
- `paused` - Temporarily halted
- `empty` - Never run

### Check Server Health

**Location**: [`check_status.py:14-24`](./check_status.py)

```python
nessus.server.status() -> dict
```

**Returns**:
```json
{
  "status": "ready",
  "progress": null,
  "must_destroy_session": false
}
```

### Get Scan Details

**Location**: [`manage_credentials.py:115-138`](./manage_credentials.py), [`scan_config.py:120-246`](./scan_config.py)

```python
nessus.editor.details('scan', scan_id) -> dict
```

Returns complete scan configuration including credentials, settings, plugins.

---

## Workflow Stage 6: Export Results

**Purpose**: Retrieve vulnerability data in various formats

### Quick Export (Summary Data)

**Location**: [`export_vulnerabilities.py`](./export_vulnerabilities.py)

#### Export to JSON

```python
export_to_json(scan_id: int, scan_name: str, output_file: str = None) -> str
```

**Location**: [`export_vulnerabilities.py:55-85`](./export_vulnerabilities.py)

**Returns**: Filename of exported JSON
**Contents**: Vulnerability list, scan metadata, host summary

#### Export to CSV

```python
export_to_csv(scan_id: int, scan_name: str, output_file: str = None) -> str
```

**Location**: [`export_vulnerabilities.py:88-139`](./export_vulnerabilities.py)

**CSV Columns**:
- `plugin_id`, `plugin_name`, `plugin_family`, `severity`, `severity_name`, `count`, `cvss_score`, `vpr_score`, `epss_score`, `cpe`

#### Export Native Formats

```python
export_scan_file(scan_id: int, scan_name: str, format: str, output_file: str = None) -> str
```

**Location**: [`export_vulnerabilities.py:142-171`](./export_vulnerabilities.py)

**Supported Formats**:
- `nessus` - Native .nessus XML format
- `csv` - Nessus CSV export
- `html` - HTML report
- `pdf` - PDF report

### Detailed Export (Full Plugin Data)

**Location**: [`export_vulnerabilities_detailed.py:50-225`](./export_vulnerabilities_detailed.py)

```python
export_detailed_json(scan_id: int, scan_name: str, output_file: str = None) -> str
```

**What's Included**:
- Complete plugin descriptions
- CVE references (`cve` list)
- CVSS v2/v3 scores and vectors
- Exploit availability (`exploit_available`, `exploitability_ease`, `exploit_code_maturity`)
- Patch/vulnerability publication dates
- Solution/remediation steps
- Per-host plugin output
- Risk factors and age of vulnerabilities

**Use Case**: Comprehensive vulnerability analysis and reporting

### Vulnerability Summary Display

**Location**: [`export_vulnerabilities.py:174-231`](./export_vulnerabilities.py)

```python
display_vulnerability_summary(scan_id: int, scan_name: str) -> None
```

Prints formatted console output with:
- Scan info (status, targets, policy, timestamps)
- Host summary (critical/high/medium/low/info counts per host)
- Vulnerability counts by severity
- Top 10 critical/high vulnerabilities

---

## Workflow Stage 7: Cleanup

**Purpose**: Delete or archive completed scans

### Delete Scan (Complete)

**Location**: [`manage_scans.py:612-629`](./manage_scans.py)

```python
delete_scan(scan_id: int, api_token: str, session_token: str) -> bool
```

**Process**:
1. Moves scan to trash folder (`folder_id=2`)
2. Permanently deletes from trash

**Alternative**: Two-step process

**Move to Trash**: [`manage_scans.py:427-476`](./manage_scans.py)
```python
move_to_trash(scan_id: int, api_token: str, session_token: str) -> bool
```

**Empty Trash**: [`manage_scans.py:479-550`](./manage_scans.py)
```python
empty_trash(api_token: str, session_token: str) -> bool
```

Permanently deletes all scans in trash folder.

---

## State Management for MCP Server

### Authentication State

**Session Tokens**:
- Expire after inactivity period
- Store `api_token` (constant) and `session_token` (dynamic)
- Re-authenticate when receiving `401 Unauthorized`

**Recommended Pattern**:
```python
class NessusClient:
    def __init__(self):
        self.api_token = None
        self.session_token = None
        self.last_auth_time = None

    def ensure_authenticated(self):
        if not self.session_token or self._is_token_expired():
            self.api_token, self.session_token = authenticate(username, password)
```

### Scan State Tracking

**Key States**:
- `empty` - Scan created, never run
- `running` - Currently scanning
- `paused` - Temporarily stopped
- `completed` - Finished successfully
- `canceled` - User stopped

**Polling Strategy**:
```python
# Poll scan status every 30-60 seconds
while True:
    scans = nessus.scans.list()
    scan = next(s for s in scans['scans'] if s['id'] == scan_id)

    if scan['status'] in ['completed', 'canceled']:
        break

    time.sleep(30)
```

### Error Handling Patterns

**Common Errors**:

1. **412 Precondition Failed** - API restriction on Nessus Essentials
   - Solution: Use Web UI simulation methods

2. **403 Forbidden** - Invalid authentication
   - Solution: Re-authenticate and retry

3. **404 Not Found** - Invalid scan ID
   - Solution: Verify scan exists with `scans.list()`

4. **409 Conflict** - Scan already running
   - Solution: Wait for completion or stop scan first

5. **Connection errors** - Nessus server unreachable
   - Solution: Verify server status with `server.status()`

**Retry Pattern**:
```python
def with_retry(func, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return func()
        except requests.exceptions.ConnectionError:
            if attempt == max_attempts - 1:
                raise
            time.sleep(5 * (attempt + 1))  # Exponential backoff
```

---

## MCP Tool Mapping Recommendations

### Suggested MCP Tools

Based on workflow stages, implement these MCP tools:

1. **`nessus_create_scan`**
   - Maps to: `create_scan()`
   - Input params: `name`, `targets`, `description`
   - Returns: `scan_id`

2. **`nessus_configure_credentials`**
   - Maps to: `export_credentials_template()` + `import_credentials_from_template()`
   - Input params: `scan_id`, `username`, `password`, `escalation_method`
   - Returns: Success status

3. **`nessus_launch_scan`**
   - Maps to: `launch_scan()`
   - Input params: `scan_id`
   - Returns: `scan_uuid`

4. **`nessus_get_scan_status`**
   - Maps to: `nessus.scans.list()` + filter by ID
   - Input params: `scan_id`
   - Returns: `status`, `progress_percentage`

5. **`nessus_export_results`**
   - Maps to: `export_detailed_json()`
   - Input params: `scan_id`, `format`
   - Returns: Vulnerability data structure

6. **`nessus_delete_scan`**
   - Maps to: `delete_scan()`
   - Input params: `scan_id`
   - Returns: Success status

### Async Considerations

Nessus operations are inherently **synchronous HTTP requests**. For MCP server:

- Use `asyncio.to_thread()` to run blocking calls
- Implement background polling for scan status
- Consider websocket notifications for scan completion (if implementing real-time updates)

---

## Configuration Reference

### Connection Settings

**Default Values** (hardcoded in wrapper scripts):
```python
NESSUS_URL = 'https://172.32.0.209:8834'
USERNAME = 'nessus'
PASSWORD = 'nessus'
# STATIC_API_TOKEN - Dynamically fetched from nessus6.js (not hardcoded)
```

**API Keys** (for read-only operations - manually generated in Nessus Web UI):
```python
ACCESS_KEY = '27f46c288d1b5d229f152128ed219cec3962a811a9090da0a3e8375c53389298'
SECRET_KEY = '11a99860b2355d1dc1a91999c096853d1e2ff20a88e30fc5866de82c97005329'
```

**X-API-Token** (for Web UI operations - automatically fetched):
- Dynamically extracted from `/nessus6.js` at runtime
- Installation-specific (changes after Nessus rebuild)
- No manual configuration needed
- See [X-API-TOKEN_EXPLAINED.md](./X-API-TOKEN_EXPLAINED.md) for details

**Security Note**: For production MCP server, move credentials to:
- Environment variables
- Secure credential store (e.g., HashiCorp Vault)
- Configuration file (excluded from version control)

### Template UUIDs

**Advanced Scan Template**: `ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66`

Other templates discoverable via:
```python
nessus.editor.list('scan')
```

### Folder IDs

- `2` - Trash folder
- `3` - My Scans folder (default)

### Scanner IDs

- `1` - Local scanner (default)

---

## Complete Example: Full Scan Lifecycle

```python
# 1. Authenticate
api_token, session_token = authenticate("nessus", "nessus")

# 2. Create scan
scan_result = create_scan(
    api_token=api_token,
    session_token=session_token,
    name="Production Web Servers",
    targets="192.168.1.10,192.168.1.11",
    description="Weekly vulnerability scan"
)
scan_id = scan_result['scan']['id']

# 3. Configure credentials (optional)
export_credentials_template(scan_id, f"scan_{scan_id}_creds.json")
# [User fills in JSON template with real credentials]
import_credentials_from_template(scan_id, api_token, session_token, f"scan_{scan_id}_creds.json")

# 4. Launch scan
launch_scan(scan_id, api_token, session_token)

# 5. Monitor status
while True:
    scans_data = nessus.scans.list()
    scan = next(s for s in scans_data['scans'] if s['id'] == scan_id)

    if scan['status'] == 'completed':
        break
    elif scan['status'] == 'canceled':
        raise Exception("Scan was canceled")

    time.sleep(60)  # Check every minute

# 6. Export results
results_file = export_detailed_json(scan_id, "Production Web Servers")
print(f"Results saved to: {results_file}")

# 7. Cleanup (optional)
# delete_scan(scan_id, api_token, session_token)
```

---

## See Also

- **[README.md](./README.md)** - Overview and quick start guide
- **[CODEBASE_INDEX.md](./CODEBASE_INDEX.md)** - Complete script inventory with technical details
- **[requirements.txt](./requirements.txt)** - Python dependencies

**External Resources**:
- [Tenable pyTenable Documentation](https://pytenable.readthedocs.io)
- [Nessus API Reference](https://developer.tenable.com/reference/navigate)

---

**Document Version**: 1.0
**Last Updated**: 2025-01-07
**Maintained By**: Nessus API Wrapper Project
