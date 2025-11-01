# Nessus API Automation - Codebase Index

## Project Overview
This project provides Python automation scripts for managing Nessus vulnerability scans. It bypasses API license restrictions by using direct HTTP requests that simulate web UI interactions, enabling full scan management capabilities with Nessus Essentials.

**Technology Stack:** Python 3.12, tenable.nessus SDK, requests, urllib3
**Primary Use Case:** Automated vulnerability scanning and credential management for Nessus Essentials

---

## Configuration Constants
All scripts share common configuration:
- **NESSUS_URL:** `https://localhost:8834`
- **ACCESS_KEY:** API access key for Nessus authentication
- **SECRET_KEY:** API secret key for Nessus authentication
- **STATIC_API_TOKEN:** Static token for web UI simulation
- **USERNAME/PASSWORD:** Nessus login credentials (`nessus`/`nessus`)

---

## Core Scripts

### 1. manage_scans.py
**Purpose:** Create and delete Nessus scans via web UI simulation, bypassing API license restrictions

**Main Functions:**
- `authenticate(username, password)` - Authenticates with Nessus web UI and returns API token + session token
- `get_template_config(template_uuid, api_token, session_token)` - Retrieves template configuration from Nessus
- `create_scan(api_token, session_token, name, targets, description, template_uuid)` - Creates new scan with specified parameters and dummy SSH credentials
- `delete_scan(scan_id, api_token, session_token)` - Moves scan to trash and permanently deletes it
- `move_to_trash(scan_id, api_token, session_token)` - Moves scan to trash folder (folder_id=2)
- `empty_trash(api_token, session_token)` - Permanently deletes all scans in trash folder
- `init_ssh_credentials(scan_id, api_token, session_token)` - Initializes scan with placeholder SSH credentials

**Key Classes/Arguments:**
- Template UUID for Advanced Scan: `ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66`
- Default folder_id: 3 (My Scans), Trash folder_id: 2

**CLI Usage:**
- Create: `python manage_scans.py create <name> <targets> [description]`
- Delete: `python manage_scans.py delete <scan_id>`
- Empty trash: `python manage_scans.py empty-trash`

---

### 2. manage_credentials.py
**Purpose:** Manage SSH credentials for Nessus scans using JSON template import/export system

**Main Functions:**
- `export_credentials_template(scan_id, output_file)` - Exports SSH credential structure to JSON template file
- `import_credentials_from_template(scan_id, api_token, session_token, template_file)` - Imports SSH credentials from filled JSON template
- `extract_ssh_credential_template(credentials)` - Extracts SSH credential structure and creates template with available options
- `build_ssh_credential_instance(template_data, existing_instance)` - Builds or updates SSH credential instance from template data
- `get_scan_status(scan_id)` - Returns scan status to prevent editing running scans

**Key Classes/Arguments:**
- Credential categories: Host credentials with SSH type
- Auth methods: password, certificate, Kerberos, public key
- Privilege escalation: Nothing, sudo, su, pbrun, dzdo, Cisco 'enable'
- Template fields: username, password, auth_method, elevate_privileges_with, escalation_password, escalation_account

**CLI Usage:**
- Export template: `python manage_credentials.py <scan_id>`
- Import credentials: `python manage_credentials.py <scan_id> <json_file>`

---

### 3. list_scans.py
**Purpose:** Simple utility to list all scans from Nessus Essentials with their details

**Main Functions:**
- Uses `nessus.scans.list()` to retrieve all scans and folders

**Output Information:**
- Scan ID, Name, Status, Folder ID, Enabled status, Last modification date, UUID
- Folder list with IDs and names

**CLI Usage:**
- Run: `python list_scans.py`

---

### 4. launch_scan.py
**Purpose:** Launch, stop, and manage Nessus scan execution via web UI simulation

**Main Functions:**
- `launch_scan(scan_id, api_token, cookie_token)` - Launches scan by simulating web UI button press
- `stop_scan(scan_id, api_token, cookie_token)` - Stops running scan
- `stop_all_scans()` - Stops all currently running scans
- `list_scans()` - Lists all available scans with status

**Key Features:**
- Auto-login support (no need to manually provide tokens)
- Manual token support for advanced use cases
- Bulk operations (stop all running scans)

**CLI Usage:**
- List scans: `python launch_scan.py` or `python launch_scan.py list`
- Launch: `python launch_scan.py launch <scan_id>`
- Stop: `python launch_scan.py stop <scan_id>`
- Stop all: `python launch_scan.py stop-all`

---

### 5. export_vulnerabilities_detailed.py
**Purpose:** Export comprehensive vulnerability data with full plugin information including CVE, CVSS, exploit data

**Main Functions:**
- `export_detailed_json(scan_id, scan_name, output_file)` - Exports vulnerabilities with complete plugin details for each host
- `get_detailed_plugin_info(scan_id, host_id, plugin_id)` - Fetches full plugin details for specific vulnerability
- `display_summary(scan_id, scan_name)` - Shows vulnerability summary by severity

**Exported Data Fields:**
- Risk information: risk_factor, cvss_base_score, cvss_vector, cvss3_base_score, cvss3_vector, cvss3_impact_score
- Vulnerability info: exploit_available, exploitability_ease, exploit_code_maturity, patch_publication_date, vuln_publication_date, cpe, age_of_vuln
- Plugin info: plugin_publication_date, plugin_modification_date, plugin_type, plugin_version
- References: CVE list, BID list, external references (XREF), USN references
- Descriptive text: description, solution, synopsis, see_also links

**CLI Usage:**
- Export: `python export_vulnerabilities_detailed.py <scan_id_or_name>`

---

### 6. export_vulnerabilities.py
**Purpose:** Export vulnerability data in multiple formats (JSON, CSV, HTML, PDF, Nessus native)

**Main Functions:**
- `export_to_json(scan_id, scan_name, output_file)` - Exports vulnerability data to JSON format
- `export_to_csv(scan_id, scan_name, output_file)` - Exports vulnerability summary to CSV
- `export_scan_file(scan_id, scan_name, format, output_file)` - Exports full scan in native Nessus formats
- `display_vulnerability_summary(scan_id, scan_name)` - Displays comprehensive vulnerability summary with top critical/high findings

**Supported Export Formats:**
- json - Vulnerability list with scan metadata
- csv - Tabular vulnerability data
- nessus - Native .nessus file format
- html - HTML report
- pdf - PDF report
- all - Exports in all formats simultaneously

**CLI Usage:**
- `python export_vulnerabilities.py <scan_id_or_name> [format]`
- Example: `python export_vulnerabilities.py 12 csv`

---

### 7. edit_scan.py
**Purpose:** Edit Nessus scan parameters (name, description, targets) and optionally launch

**Main Functions:**
- `update_scan(scan_id, api_token, session_token, name, description, targets)` - Updates scan configuration parameters
- `extract_settings_from_editor_config(editor_config)` - Extracts flat settings dict from nested editor configuration
- `launch_scan(scan_id, api_token, session_token)` - Launches scan after updating
- `get_scan_details(scan_id)` - Retrieves full scan configuration using API

**Key Features:**
- Prevents editing running scans (checks status first)
- Preserves existing credentials and plugin configurations
- Optional auto-launch after update

**CLI Usage:**
- `python edit_scan.py <scan_id> --name <name> --description <desc> --targets <targets> [--launch]`
- Example: `python edit_scan.py 12 --targets "192.168.1.1,192.168.1.2" --launch`

---

### 8. check_status.py
**Purpose:** Simple diagnostic script to check Nessus server status

**Main Functions:**
- Uses `nessus.server.status()` to retrieve and display server status

**Output:**
- Status, Progress, Session information

**CLI Usage:**
- Run: `python check_status.py`

---

### 9. check_dropdown_options.py
**Purpose:** Debug utility to examine SSH credential field structure and available options

**Main Functions:**
- Loads scan configuration from `scan_config_debug.json`
- Extracts and displays authentication method options
- Shows privilege escalation options

**Usage:**
- Requires `scan_config_debug.json` file from scan_config.py output
- Run: `python check_dropdown_options.py`

---

### 10. scan_config.py
**Purpose:** Display comprehensive scan configuration including credentials, targets, settings, and plugins

**Main Functions:**
- `display_scan_config(scan_id, scan_name)` - Shows complete scan configuration from editor API
- `display_credentials(credentials_data)` - Parses and displays configured credentials with masked sensitive data
- `extract_input_values(inputs_list, prefix)` - Recursively extracts values from nested credential input structures
- `mask_sensitive(key, value)` - Masks passwords and sensitive fields

**Output Sections:**
- Basic Information: ID, name, UUID, owner, policy template
- Scan Settings: folder, scanner, enabled status, launch settings
- Targets: IP/hostname targets and file targets
- Schedule: Frequency, interval, start time, timezone
- Advanced Settings: Max scan time, port ranges, network discovery
- Credentials: All configured credentials with masked passwords
- Plugins: Summary of enabled plugin families

**CLI Usage:**
- `python scan_config.py [scan_name_or_id]`
- Saves full config to `scan_config_debug.json` for debugging

---

## Common Patterns

### Authentication Flow
1. Call `authenticate(username, password)` to get session tokens
2. Use `api_token` for X-API-Token header
3. Use `session_token` for X-Cookie header as `token={session_token}`

### HTTP Request Headers (Web UI Simulation)
All scripts use consistent headers to simulate browser requests:
- User-Agent: Chrome browser signature
- Accept-Encoding: gzip, deflate, br, zstd
- X-API-Token: Static or dynamic API token
- X-Cookie: Session token
- Content-Type: application/json

### Error Handling
- Scripts validate scan status before modifications
- SSL warnings disabled for localhost/self-signed certificates
- Detailed error messages with status codes and response text
- Traceback printing for debugging

### Data Structures
- **Scan Settings:** Flat dictionary with key-value pairs extracted from nested editor structure
- **Credentials:** Nested structure with categories > types > instances > inputs
- **SSH Credentials:** Hierarchical structure with auth_method containing nested options for password/certificate/Kerberos

---

## File Dependencies

### Import Dependencies
- `urllib3` - HTTP client library, used to disable SSL warnings
- `requests` - HTTP requests for web UI simulation
- `tenable.nessus` - Official Nessus Python SDK
- `json` - JSON parsing and generation
- `csv` - CSV export functionality
- `datetime` - Timestamp handling
- `sys` - Command-line argument parsing

### Internal Dependencies
- Scripts are independent but share configuration constants
- `manage_credentials.py` references output of `manage_scans.py` (scan IDs)
- `check_dropdown_options.py` requires `scan_config_debug.json` from `scan_config.py`

---

## Development Notes

### API License Bypass Strategy
The project bypasses Nessus Essentials API license restrictions by:
1. Using direct HTTP requests to simulate web UI interactions
2. Authenticating via `/session` endpoint to obtain session tokens
3. Sending requests with browser-like headers (User-Agent, Sec-Fetch headers)
4. Using X-API-Token and X-Cookie headers for authentication

### Credential Management Architecture
Credentials use a complex nested structure:
- Top level: Categories (e.g., "Host")
- Second level: Types (e.g., "SSH")
- Third level: Instances (individual credential sets)
- Fourth level: Inputs (nested fields with ui_radio options)
- The `auth_method` field uses `ui_radio` type with nested options for different auth types
- Each auth type (password/certificate) has its own nested input fields

### Template System
The credential template system:
1. Extracts field definitions from scan configuration
2. Dynamically discovers available options (auth methods, escalation options)
3. Creates JSON template with hints and current values
4. Supports partial updates (only specified fields are changed)
5. Uses add/delete pattern for credential updates

---

## Quick Reference

### Scan Lifecycle
1. Create: `manage_scans.py create`
2. Configure credentials: `manage_credentials.py`
3. Edit if needed: `edit_scan.py`
4. Launch: `launch_scan.py launch`
5. Monitor: `list_scans.py` or `check_status.py`
6. Export results: `export_vulnerabilities.py` or `export_vulnerabilities_detailed.py`
7. View config: `scan_config.py`
8. Delete: `manage_scans.py delete`

### Common Scan IDs
- Folder IDs: 2 (Trash), 3 (My Scans)
- Scanner ID: 1 (Local scanner)
- Template UUID: Advanced Scan template hardcoded in manage_scans.py

### File Outputs
- Credential templates: `scan_{scan_id}_ssh_credentials.json`
- Vulnerability exports: `vulns_{scan_name}_{timestamp}.{format}`
- Detailed exports: `vulns_detailed_{scan_name}_{timestamp}.json`
- Config debug: `scan_config_debug.json`

---

## Security Considerations

### Hardcoded Credentials
All scripts contain hardcoded Nessus credentials and API keys. For production use:
- Move credentials to environment variables or configuration file
- Add to `.gitignore` (credentials.md is already ignored)
- Use secure credential storage

### SSL Verification
SSL verification is disabled for localhost/self-signed certificates. This is acceptable for local Nessus instances but should be reconsidered for remote/production deployments.

### Credential Masking
`scan_config.py` masks sensitive fields (passwords, keys) when displaying configuration. However, credentials are transmitted in plaintext over HTTPS to Nessus server.
