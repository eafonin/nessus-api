# Phase 5: Authenticated Scan Types

> Implement SSH-based authenticated and privileged vulnerability scanning

---

## Overview

Phase 5 extends the MCP server to support authenticated vulnerability scans. Authenticated scans use SSH credentials to log into target systems, enabling deeper vulnerability detection that unauthenticated scans cannot achieve.

### Scan Type Definitions

| Scan Type | Description | Credentials | Use Case |
|-----------|-------------|-------------|----------|
| `untrusted` | Network-only scan, no auth | None | External attack surface |
| `authenticated` | SSH login to target | username/password | Internal vulnerability assessment |
| `authenticated_privileged` | SSH + sudo/root escalation | username/password + escalation | Full system audit, compliance |

### Why Authenticated Scans Matter

- **10x more vulnerabilities detected**: Auth scans check installed packages, configs, permissions
- **Accurate patch status**: Verify actual installed versions vs advertised
- **Compliance requirements**: PCI-DSS, HIPAA, SOC2 require authenticated scanning
- **Reduced false positives**: Confirm vulnerabilities vs guessing from banners

---

## Validated Workflow (Tested 2025-11-25)

### Wrapper Scripts Used

The following `nessusAPIWrapper` scripts were validated for authenticated scan workflow:

| Script | Function | Command |
|--------|----------|---------|
| `manage_scans.py` | Create scan with placeholder creds | `python manage_scans.py create "ScanName" "target_ip" "description"` |
| `manage_credentials.py` | Export credential template | `python manage_credentials.py <scan_id>` |
| `manage_credentials.py` | Import filled credentials | `python manage_credentials.py <scan_id> <json_file>` |
| `launch_scan.py` | Launch scan | `python launch_scan.py launch <scan_id>` |
| `list_scans.py` | Monitor status | `python list_scans.py` |
| `export_vulnerabilities.py` | Export summary | `python export_vulnerabilities.py <scan_id>` |
| `export_vulnerabilities_detailed.py` | Export full details | `python export_vulnerabilities_detailed.py <scan_id>` |
| `scan_config.py` | Verify credentials saved | `python scan_config.py <scan_id>` |

### Complete Test Workflow Executed

```bash
# 1. Create scan with placeholder credentials
python manage_scans.py create "Auth_Test" "172.32.0.215" "Test authenticated scan"
# Output: Scan ID: 120

# 2. Create credential JSON
cat > scan_120_creds.json << 'EOF'
{
  "auth_method": "password",
  "username": "randy",
  "password": "randylovesgoldfish1998",
  "elevate_privileges_with": "Nothing"
}
EOF

# 3. Import credentials
python manage_credentials.py 120 scan_120_creds.json
# Output: [SUCCESS] SSH credentials updated for scan 120

# 4. Launch scan
python launch_scan.py launch 120
# Output: [SUCCESS] Scan 120 launched successfully!

# 5. Monitor until completion (~8 minutes)
# Status: running → completed

# 6. Export results
python export_vulnerabilities.py 120
```

### Test Results Summary

```
Target: 172.32.0.215
Authentication: SUCCESS (credentials worked)
Scan Duration: ~8 minutes

Vulnerabilities Found:
  Critical: 0
  High: 1 (Ubuntu 21.04 Perl vulnerability USN-5033-1)
  Medium: 2 (SSH Terrapin, mDNS Detection)
  Low: 2 (ICMP Timestamp, Ubuntu SEoL)
  Info: 59 (authentication-enabled enumeration)
```

---

## Detecting Authentication Success/Failure

### Key Indicators in Scan Results

#### 1. Host Summary - `credential` Field

In the JSON export, each host has a `credential` field:

```json
"hosts_summary": [
  {
    "hostname": "172.32.0.215",
    "credential": "true",  // "true" = auth success, "false" = auth failed
    "critical": 0,
    "high": 1,
    ...
  }
]
```

#### 2. Plugin 141118 - Valid Credentials Confirmation

**Plugin Name**: "Target Credential Status by Authentication Protocol - Valid Credentials Provided"

This plugin explicitly confirms successful authentication:
```
Plugin ID: 141118
Severity: Info
Presence indicates: Authentication SUCCESS
```

#### 3. Plugin 110385 - Insufficient Privilege Warning

**Plugin Name**: "Target Credential Issues by Authentication Protocol - Insufficient Privilege"

This plugin indicates partial authentication (logged in but limited access):
```
Plugin ID: 110385
Severity: Info
Presence indicates: Need privilege escalation (sudo/su)
```

#### 4. Plugin 19506 - Nessus Scan Information

Contains the definitive authentication status:
```
Plugin output includes:
"Credentialed checks : yes"   → Full auth success
"Credentialed checks : no"    → Auth failed or not attempted
"Credentialed checks : partial" → Some hosts authenticated
```

#### 5. SSH-Based Enumeration Plugins

Presence of these plugins confirms authentication worked:

| Plugin ID | Name | Indicates |
|-----------|------|-----------|
| 22869 | Software Enumeration (SSH) | Auth success - can list packages |
| 97993 | OS Identification over SSH v2 | Auth success - can identify OS |
| 95928 | Linux User List Enumeration | Auth success - can list users |
| 66334 | Patch Report | Auth success - can check patches |
| 179139 | Package Manager Packages Report | Auth success - full package list |
| 39520 | Backported Security Patch Detection (SSH) | Auth success - patch analysis |

### Authentication Status Logic

```python
def determine_auth_status(scan_results):
    """Determine authentication status from scan results."""

    # Check hosts_summary credential field
    for host in scan_results.get('hosts_summary', []):
        if host.get('credential') == 'true':
            return 'success'

    # Check for Plugin 141118 (explicit success)
    for vuln in scan_results.get('vulnerabilities', []):
        if vuln['plugin_id'] == 141118:
            return 'success'
        if vuln['plugin_id'] == 110385:
            return 'partial'  # Logged in but insufficient privilege

    # Check for SSH enumeration plugins (indirect confirmation)
    auth_plugins = {22869, 97993, 95928, 66334, 179139, 39520}
    found_plugins = {v['plugin_id'] for v in scan_results.get('vulnerabilities', [])}
    if auth_plugins & found_plugins:
        return 'success'

    return 'failed'
```

---

## Current State Analysis

### Already Implemented (Ready to Use)

| Component | Location | Status |
|-----------|----------|--------|
| `ScanRequest.credentials` field | `scanners/base.py:15` | Defined but unused |
| Worker credential passing | `worker/scanner_worker.py:229` | Passes to scanner |
| Auth status in Task | `core/types.py:50` | `authentication_status` field |
| Auth validation | `scanners/nessus_validator.py:51-202` | Detects success/failure |
| Auth troubleshooting API | `tools/mcp_server.py:281-292` | Status includes auth info |
| Metrics for auth | `core/metrics.py` | Labels for scan_type |

### Needs Implementation

| Component | Location | Work Required |
|-----------|----------|---------------|
| Credential insertion | `scanners/nessus_scanner.py` | Add to `create_scan()` payload |
| MCP tools | `tools/mcp_server.py` | New `run_authenticated_scan()` tool |
| Tests | `tests/` | Unit + integration tests |
| Documentation | `docs/` | API docs, usage examples |

---

## Architecture

### Credential Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   MCP Client    │────▶│   MCP Server    │────▶│  Redis Queue    │
│                 │     │                 │     │                 │
│ run_auth_scan() │     │ Create Task     │     │ {pool}:queue    │
│ + credentials   │     │ + credentials   │     │ + credentials   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Nessus API     │◀────│    Scanner      │◀────│     Worker      │
│                 │     │                 │     │                 │
│ POST /scans     │     │ create_scan()   │     │ _process_task() │
│ + credentials   │     │ + credentials   │     │ + credentials   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │   Validator     │
                        │                 │
                        │ Plugin 141118:  │
                        │ "Valid Creds"   │
                        │                 │
                        │ Plugin 19506:   │
                        │ "Credentialed   │
                        │  checks: yes"   │
                        └─────────────────┘
```

### Credential Structure

Based on `nessusAPIWrapper/manage_credentials.py` patterns:

```python
# SSH Password Authentication (authenticated scan)
credentials = {
    "type": "ssh",
    "auth_method": "password",
    "username": "randy",
    "password": "randylovesgoldfish1998",
    "elevate_privileges_with": "Nothing"
}

# SSH with Privilege Escalation - sudo with password (authenticated_privileged scan)
credentials = {
    "type": "ssh",
    "auth_method": "password",
    "username": "nessus",
    "password": "nessus",
    "elevate_privileges_with": "sudo",
    "escalation_account": "root",      # optional, defaults to root
    "escalation_password": "nessus"    # sudo password
}

# SSH with Privilege Escalation - sudo NOPASSWD (authenticated_privileged scan)
credentials = {
    "type": "ssh",
    "auth_method": "password",
    "username": "testauth_sudo_nopass",
    "password": "testpassword",
    "elevate_privileges_with": "sudo",
    "escalation_account": "root"
    # No escalation_password needed for NOPASSWD
}
```

### Nessus API Payload Format

Reference: `nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md` - Workflow Stage 3

```python
# Credentials section in scan creation payload
payload = {
    "uuid": TEMPLATE_UUID,
    "settings": {
        "name": scan_name,
        "text_targets": targets,
        # ... other settings
    },
    "credentials": {
        "add": {
            "Host": {
                "SSH": [{
                    "auth_method": "password",
                    "username": "randy",
                    "password": "randylovesgoldfish1998",
                    "elevate_privileges_with": "Nothing",  # or "sudo", "su"
                    "custom_password_prompt": "",
                    "target_priority_list": ""
                }]
            }
        },
        "edit": {},
        "delete": []
    }
}
```

### Available Escalation Methods

From `manage_credentials.py` template extraction:

```python
ESCALATION_METHODS = [
    "Nothing",           # No privilege escalation
    "sudo",              # Most common - sudo to root
    "su",                # Switch user
    "su+sudo",           # Combined su then sudo
    "pbrun",             # PowerBroker
    "dzdo",              # Centrify DirectAuthorize
    ".k5login",          # Kerberos
    "Cisco 'enable'",    # Network devices
    "Checkpoint Gaia 'expert'"  # Checkpoint firewalls
]
```

---

## Security Considerations

### Credential Handling in Redis Queue

**Current Design**: Credentials pass through Redis queue in plaintext within task payload.

**Risk Assessment**:
- Redis is internal (Docker network only)
- No external exposure
- Credentials are ephemeral (per-scan, not stored)

**Future Enhancement** (Not Phase 5):
- Encrypt credentials before queue insertion
- Decrypt in worker before scanner use
- Consider HashiCorp Vault integration for credential management

**Mitigation for Phase 5**:
- Document the security consideration
- Ensure Redis is not exposed externally
- Sanitize credentials from all logs (already implemented in validator)

---

## Test User Setup

### Test Target: 172.32.0.209 (Docker Host - READY)

Test users have been created on the Docker host (172.32.0.209) for authenticated scan testing.

**Status: CREATED AND VERIFIED (2025-11-25)**

#### Users Created

| Username | Password | Sudo Config | UID |
|----------|----------|-------------|-----|
| `testauth_sudo_pass` | `TestPass123!` | sudo with password | 1002 |
| `testauth_sudo_nopass` | `TestPass123!` | sudo NOPASSWD | 1003 |
| `testauth_nosudo` | `TestPass123!` | No sudo | 1004 |

#### Sudoers Configuration

File: `/etc/sudoers.d/testauth`
```
# Test users for Nessus authenticated scan testing
testauth_sudo_pass ALL=(ALL) ALL
testauth_sudo_nopass ALL=(ALL) NOPASSWD: ALL
# testauth_nosudo - intentionally NO sudo access
```

#### Verification Results

```bash
# NOPASSWD sudo works:
$ sudo -u testauth_sudo_nopass sudo -n whoami
root

# No sudo access (password required = effectively no access for Nessus):
$ sudo -u testauth_nosudo sudo -n whoami
sudo: a password is required
```

### Test Target: 172.32.0.215 (External Host)

Existing user for basic authenticated scan testing:

| Username | Password | Access |
|----------|----------|--------|
| `randy` | `randylovesgoldfish1998` | Full root SSH access |

### Complete Test Matrix

| Target | Username | Password | Sudo Config | Scan Type | Expected Result |
|--------|----------|----------|-------------|-----------|-----------------|
| 172.32.0.209 | `testauth_sudo_pass` | `TestPass123!` | sudo + password | `authenticated_privileged` | Success with escalation_password |
| 172.32.0.209 | `testauth_sudo_nopass` | `TestPass123!` | sudo NOPASSWD | `authenticated_privileged` | Success without escalation_password |
| 172.32.0.209 | `testauth_nosudo` | `TestPass123!` | No sudo | `authenticated` | Success, Plugin 110385 warning |
| 172.32.0.209 | `nessus` | `nessus` | sudo + password | `authenticated_privileged` | Success (existing) |
| 172.32.0.215 | `randy` | `randylovesgoldfish1998` | Full root | `authenticated` | Success |

### Test Scan Examples

```bash
# 1. Authenticated scan (SSH only, no escalation)
python manage_scans.py create "Test_Auth" "172.32.0.209" "Test"
# Configure with testauth_nosudo credentials
# Expected: Plugin 110385 (insufficient privilege)

# 2. Privileged scan with sudo + password
python manage_scans.py create "Test_Priv_Pass" "172.32.0.209" "Test"
# Configure with testauth_sudo_pass + escalation_password
# Expected: Full privileged scan

# 3. Privileged scan with sudo NOPASSWD
python manage_scans.py create "Test_Priv_NoPass" "172.32.0.209" "Test"
# Configure with testauth_sudo_nopass (no escalation_password needed)
# Expected: Full privileged scan
```

---

## Implementation Plan

### Step 1: Scanner Credential Support

**File:** `scanners/nessus_scanner.py`

**Reference:** `nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md` - Workflow Stage 2 & 3

**Changes:**

1. Modify `create_scan()` to include credentials in payload:

```python
async def create_scan(self, request: ScanRequest) -> int:
    """Create scan with optional credentials."""

    payload = {
        "uuid": self.TEMPLATE_ADVANCED_SCAN,
        "settings": {
            "name": request.name,
            "text_targets": request.targets,
            "description": request.description,
            "enabled": True,
            "folder_id": self.FOLDER_MY_SCANS,
            "scanner_id": self.SCANNER_LOCAL,
            "launch_now": False
        }
    }

    # Add credentials if provided
    if request.credentials:
        self._validate_credentials(request.credentials)
        payload["credentials"] = self._build_credentials_payload(
            request.credentials
        )

    # ... rest of create_scan
```

2. Add credential payload builder:

```python
def _build_credentials_payload(
    self,
    credentials: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build Nessus credentials payload from request credentials.

    Based on patterns from nessusAPIWrapper/manage_credentials.py
    """
    cred_type = credentials.get("type", "ssh")

    if cred_type == "ssh":
        ssh_cred = {
            "auth_method": credentials.get("auth_method", "password"),
            "username": credentials["username"],
            "password": credentials["password"],
            "elevate_privileges_with": credentials.get(
                "elevate_privileges_with", "Nothing"
            ),
            "custom_password_prompt": "",
            "target_priority_list": ""
        }

        # Add escalation fields if using sudo/su
        escalation = credentials.get("elevate_privileges_with", "Nothing")
        if escalation not in ("Nothing", ""):
            if credentials.get("escalation_password"):
                ssh_cred["escalation_password"] = credentials["escalation_password"]
            if credentials.get("escalation_account"):
                ssh_cred["escalation_account"] = credentials["escalation_account"]

        return {
            "add": {
                "Host": {
                    "SSH": [ssh_cred]
                }
            },
            "edit": {},
            "delete": []
        }

    raise ValueError(f"Unsupported credential type: {cred_type}")
```

3. Add credential validation:

```python
VALID_ESCALATION_METHODS = {
    "Nothing", "sudo", "su", "su+sudo", "pbrun", "dzdo",
    ".k5login", "Cisco 'enable'", "Checkpoint Gaia 'expert'"
}

def _validate_credentials(self, credentials: Dict[str, Any]) -> None:
    """Validate credential structure before use."""
    if not credentials:
        return

    cred_type = credentials.get("type", "ssh")

    if cred_type == "ssh":
        # Required fields
        required = ["username", "password"]
        for field in required:
            if not credentials.get(field):
                raise ValueError(f"SSH credential missing required field: {field}")

        # Validate escalation config
        escalation = credentials.get("elevate_privileges_with", "Nothing")
        if escalation not in self.VALID_ESCALATION_METHODS:
            raise ValueError(
                f"Invalid escalation method: {escalation}. "
                f"Valid options: {', '.join(self.VALID_ESCALATION_METHODS)}"
            )
    else:
        raise ValueError(f"Unsupported credential type: {cred_type}")
```

---

### Step 2: MCP Tool Implementation

**File:** `tools/mcp_server.py`

**Reference:** `nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md` - MCP Tool Mapping Recommendations

**New Tool:** `run_authenticated_scan()`

```python
@mcp.tool()
async def run_authenticated_scan(
    targets: str,
    name: str,
    scan_type: str,
    ssh_username: str,
    ssh_password: str,
    description: str = "",
    schema_profile: str = "brief",
    elevate_privileges_with: str = "Nothing",
    escalation_account: str = "",
    escalation_password: str = "",
    idempotency_key: str | None = None,
    scanner_pool: str | None = None,
    scanner_instance: str | None = None,
) -> dict:
    """
    Run an authenticated vulnerability scan with SSH credentials.

    Authenticated scans log into target systems to perform deeper
    vulnerability assessment than unauthenticated network scans.

    Args:
        targets: IP addresses or hostnames to scan (comma-separated)
        name: Human-readable scan name
        scan_type: "authenticated" (SSH only) or "authenticated_privileged" (SSH + sudo)
        ssh_username: SSH username for target authentication
        ssh_password: SSH password for target authentication
        description: Optional scan description
        schema_profile: Result detail level ("minimal", "brief", "full")
        elevate_privileges_with: "Nothing", "sudo", "su" (for authenticated_privileged)
        escalation_account: Account to escalate to (default: root)
        escalation_password: Password for privilege escalation (if required)
        idempotency_key: Optional key for duplicate prevention
        scanner_pool: Optional pool name for scanner selection
        scanner_instance: Optional specific scanner instance

    Returns:
        dict with task_id, trace_id, status, queue_position

    Authentication Detection:
        After scan completion, check these indicators:
        - authentication_status: "success" | "partial" | "failed"
        - Plugin 141118: "Valid Credentials Provided" (confirms success)
        - Plugin 110385: "Insufficient Privilege" (need sudo escalation)
        - hosts_summary.credential: "true" | "false"

    Example (authenticated scan - SSH only):
        run_authenticated_scan(
            targets="172.32.0.215",
            name="Internal Server Audit",
            scan_type="authenticated",
            ssh_username="randy",
            ssh_password="randylovesgoldfish1998"
        )

    Example (authenticated_privileged scan - SSH + sudo with password):
        run_authenticated_scan(
            targets="172.32.0.215",
            name="Full System Audit",
            scan_type="authenticated_privileged",
            ssh_username="testauth_sudo_pass",
            ssh_password="TestPass123!",
            elevate_privileges_with="sudo",
            escalation_password="TestPass123!"
        )

    Example (authenticated_privileged scan - SSH + sudo NOPASSWD):
        run_authenticated_scan(
            targets="172.32.0.215",
            name="Full System Audit",
            scan_type="authenticated_privileged",
            ssh_username="testauth_sudo_nopass",
            ssh_password="TestPass123!",
            elevate_privileges_with="sudo"
            # No escalation_password needed for NOPASSWD
        )
    """
    trace_id = generate_trace_id()

    # Validate scan_type
    valid_types = ("authenticated", "authenticated_privileged")
    if scan_type not in valid_types:
        return {
            "error": f"Invalid scan_type: {scan_type}. Must be one of: {valid_types}",
            "trace_id": trace_id
        }

    # Validate privileged scan has escalation configured
    if scan_type == "authenticated_privileged" and elevate_privileges_with == "Nothing":
        return {
            "error": "authenticated_privileged scan requires elevate_privileges_with (sudo/su)",
            "trace_id": trace_id
        }

    # Build credentials
    credentials = {
        "type": "ssh",
        "auth_method": "password",
        "username": ssh_username,
        "password": ssh_password,
        "elevate_privileges_with": elevate_privileges_with,
    }

    if elevate_privileges_with != "Nothing":
        if escalation_password:
            credentials["escalation_password"] = escalation_password
        if escalation_account:
            credentials["escalation_account"] = escalation_account

    # Pool selection (same logic as untrusted scan)
    pool = scanner_pool or "nessus"

    # ... rest follows run_untrusted_scan() pattern:
    # - Check idempotency
    # - Create Task with scan_type and credentials in payload
    # - Enqueue to pool
    # - Return task info
```

---

### Step 3: Test Implementation

**New Test File:** `tests/unit/test_authenticated_scans.py`

```python
"""Unit tests for authenticated scan functionality."""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest


class TestCredentialPayloadBuilder:
    """Test credential payload generation."""

    def test_ssh_password_credentials(self):
        """Test basic SSH password credential payload."""
        scanner = NessusScanner(config={})

        credentials = {
            "type": "ssh",
            "username": "testuser",
            "password": "testpass"
        }

        payload = scanner._build_credentials_payload(credentials)

        assert payload["add"]["Host"]["SSH"][0]["username"] == "testuser"
        assert payload["add"]["Host"]["SSH"][0]["password"] == "testpass"
        assert payload["add"]["Host"]["SSH"][0]["auth_method"] == "password"
        assert payload["add"]["Host"]["SSH"][0]["elevate_privileges_with"] == "Nothing"

    def test_ssh_sudo_with_password(self):
        """Test SSH with sudo escalation requiring password."""
        scanner = NessusScanner(config={})

        credentials = {
            "type": "ssh",
            "username": "testauth_sudo_pass",
            "password": "TestPass123!",
            "elevate_privileges_with": "sudo",
            "escalation_password": "TestPass123!"
        }

        payload = scanner._build_credentials_payload(credentials)

        ssh_cred = payload["add"]["Host"]["SSH"][0]
        assert ssh_cred["elevate_privileges_with"] == "sudo"
        assert ssh_cred["escalation_password"] == "TestPass123!"

    def test_ssh_sudo_nopasswd(self):
        """Test SSH with sudo NOPASSWD (no escalation_password)."""
        scanner = NessusScanner(config={})

        credentials = {
            "type": "ssh",
            "username": "testauth_sudo_nopass",
            "password": "TestPass123!",
            "elevate_privileges_with": "sudo"
            # No escalation_password
        }

        payload = scanner._build_credentials_payload(credentials)

        ssh_cred = payload["add"]["Host"]["SSH"][0]
        assert ssh_cred["elevate_privileges_with"] == "sudo"
        assert "escalation_password" not in ssh_cred or ssh_cred.get("escalation_password") == ""


class TestCredentialValidation:
    """Test credential validation."""

    def test_missing_username_raises(self):
        """Test missing username raises validation error."""
        scanner = NessusScanner(config={})

        credentials = {"type": "ssh", "password": "pass"}

        with pytest.raises(ValueError, match="missing required field: username"):
            scanner._validate_credentials(credentials)

    def test_invalid_escalation_method_raises(self):
        """Test invalid escalation method raises error."""
        scanner = NessusScanner(config={})

        credentials = {
            "type": "ssh",
            "username": "user",
            "password": "pass",
            "elevate_privileges_with": "invalid_method"
        }

        with pytest.raises(ValueError, match="Invalid escalation method"):
            scanner._validate_credentials(credentials)
```

**Integration Test:** `tests/integration/test_authenticated_scan_workflow.py`

```python
"""Integration tests for authenticated scan workflow."""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.slow]


class TestAuthenticatedScanE2E:
    """End-to-end authenticated scan tests."""

    async def test_authenticated_scan_workflow(self, mcp_client):
        """Test authenticated scan (SSH only, no sudo)."""
        result = await mcp_client.call_tool(
            "run_authenticated_scan",
            {
                "targets": "172.32.0.215",
                "name": "Test Authenticated Scan",
                "scan_type": "authenticated",
                "ssh_username": "randy",
                "ssh_password": "randylovesgoldfish1998"
            }
        )

        assert "task_id" in result
        task_id = result["task_id"]

        status = await wait_for_completion(mcp_client, task_id, timeout=600)

        assert status["status"] == "completed"
        assert status["authentication_status"] == "success"

    async def test_privileged_scan_sudo_password(self, mcp_client):
        """Test authenticated_privileged scan with sudo password."""
        result = await mcp_client.call_tool(
            "run_authenticated_scan",
            {
                "targets": "172.32.0.215",
                "name": "Test Privileged Scan (sudo+pass)",
                "scan_type": "authenticated_privileged",
                "ssh_username": "testauth_sudo_pass",
                "ssh_password": "TestPass123!",
                "elevate_privileges_with": "sudo",
                "escalation_password": "TestPass123!"
            }
        )

        assert "task_id" in result
        status = await wait_for_completion(mcp_client, result["task_id"], timeout=600)

        assert status["status"] == "completed"
        assert status["authentication_status"] == "success"

    async def test_privileged_scan_sudo_nopasswd(self, mcp_client):
        """Test authenticated_privileged scan with sudo NOPASSWD."""
        result = await mcp_client.call_tool(
            "run_authenticated_scan",
            {
                "targets": "172.32.0.215",
                "name": "Test Privileged Scan (sudo nopasswd)",
                "scan_type": "authenticated_privileged",
                "ssh_username": "testauth_sudo_nopass",
                "ssh_password": "TestPass123!",
                "elevate_privileges_with": "sudo"
                # No escalation_password
            }
        )

        assert "task_id" in result
        status = await wait_for_completion(mcp_client, result["task_id"], timeout=600)

        assert status["status"] == "completed"
        assert status["authentication_status"] == "success"

    async def test_authenticated_scan_insufficient_privilege(self, mcp_client):
        """Test authenticated scan shows insufficient privilege warning."""
        result = await mcp_client.call_tool(
            "run_authenticated_scan",
            {
                "targets": "172.32.0.215",
                "name": "Test No Sudo User",
                "scan_type": "authenticated",
                "ssh_username": "testauth_nosudo",
                "ssh_password": "TestPass123!"
            }
        )

        assert "task_id" in result
        status = await wait_for_completion(mcp_client, result["task_id"], timeout=600)

        assert status["status"] == "completed"
        # Should have Plugin 110385 warning about insufficient privilege
        # But still authentication_status == "success" (SSH worked)
        assert status["authentication_status"] in ("success", "partial")

    async def test_auth_failure_detected(self, mcp_client):
        """Test that failed auth is properly detected."""
        result = await mcp_client.call_tool(
            "run_authenticated_scan",
            {
                "targets": "172.32.0.215",
                "name": "Test Bad Credentials",
                "scan_type": "authenticated",
                "ssh_username": "nonexistent_user",
                "ssh_password": "wrong_password"
            }
        )

        task_id = result["task_id"]
        status = await wait_for_completion(mcp_client, task_id, timeout=600)

        # Scan completes but auth failed
        assert status["status"] == "completed"
        assert status["authentication_status"] == "failed"
```

---

## Test Targets Reference

### Approved Scan Targets

| IP | Host | Users | Notes |
|----|------|-------|-------|
| `172.32.0.209` | Docker host | `nessus`, `testauth_*` | Primary test target for escalation testing |
| `172.32.0.215` | External host | `randy` | Basic authenticated scan testing |

### Test Users (CREATED on 172.32.0.209)

| Username | Password | Sudo Config | Purpose | Status |
|----------|----------|-------------|---------|--------|
| `testauth_sudo_pass` | `TestPass123!` | sudo with password | Test privileged with escalation_password | READY |
| `testauth_sudo_nopass` | `TestPass123!` | sudo NOPASSWD | Test privileged without escalation_password | READY |
| `testauth_nosudo` | `TestPass123!` | No sudo | Test authenticated (non-privileged) | READY |
| `nessus` | `nessus` | sudo with password | Existing user | READY |
| `randy` (172.32.0.215) | `randylovesgoldfish1998` | Full root | Existing user | READY |

---

## Implementation Checklist

### Phase 5.1: Core Implementation

- [ ] Modify `scanners/nessus_scanner.py`
  - [ ] Add `_build_credentials_payload()` method
  - [ ] Add `_validate_credentials()` method
  - [ ] Add `VALID_ESCALATION_METHODS` constant
  - [ ] Update `create_scan()` to include credentials
  - [ ] Add credential logging (sanitized - no passwords in logs)

- [ ] Modify `tools/mcp_server.py`
  - [ ] Add `run_authenticated_scan()` tool
  - [ ] Add input validation for scan_type
  - [ ] Add credential validation
  - [ ] Update metrics labels for new scan types

### Phase 5.2: Test Infrastructure

- [x] Create test users on 172.32.0.209 (Docker host)
  - [x] `testauth_sudo_pass` (sudo with password) - UID 1002
  - [x] `testauth_sudo_nopass` (sudo NOPASSWD) - UID 1003
  - [x] `testauth_nosudo` (no sudo access) - UID 1004
  - [x] Sudoers file: `/etc/sudoers.d/testauth`

- [ ] Create `tests/unit/test_authenticated_scans.py`
  - [ ] Test credential payload building
  - [ ] Test credential validation
  - [ ] Test error cases

- [ ] Create `tests/integration/test_authenticated_scan_workflow.py`
  - [ ] Test authenticated scan E2E
  - [ ] Test authenticated_privileged scan (sudo + password)
  - [ ] Test authenticated_privileged scan (sudo NOPASSWD)
  - [ ] Test auth failure detection
  - [ ] Test insufficient privilege detection

### Phase 5.3: Documentation

- [ ] Update `docs/API.md` with auth scan documentation
- [ ] Update `README.md` with auth scan examples
- [ ] Update `nessusAPIWrapper/CODEBASE_INDEX.md`
- [ ] Update `nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md`

---

## Validation Criteria

### Success Metrics

1. **Functional**: Authenticated scans complete with credential injection
2. **Detection**: Validator correctly identifies auth success/failure/partial
3. **Plugin Verification**: Plugin 141118 present for successful auth
4. **Metrics**: Prometheus metrics include scan_type labels
5. **Tests**: All new tests pass
6. **Documentation**: API docs complete

### Acceptance Test

```bash
# 1. Submit authenticated scan via MCP
curl -X POST http://localhost:8835/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "run_authenticated_scan",
    "params": {
      "targets": "172.32.0.215",
      "name": "Acceptance Test",
      "scan_type": "authenticated",
      "ssh_username": "randy",
      "ssh_password": "randylovesgoldfish1998"
    }
  }'

# 2. Wait for completion
# 3. Verify authentication_status == "success"
# 4. Verify Plugin 141118 present in results
# 5. Verify hosts_summary.credential == "true"
```

---

## Future Phases

### Phase 6: SSH Key Authentication

**Scope**: Support SSH public key authentication instead of passwords

**Key Tasks**:
1. Generate test SSH keypairs
2. Deploy public keys to test targets
3. Update credential structure for `auth_method: "public key"`
4. Add `private_key` and `passphrase` fields
5. Update MCP tool parameters
6. Create tests

**Credential Structure**:
```python
credentials = {
    "type": "ssh",
    "auth_method": "public key",
    "username": "scanuser",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...",
    "passphrase": "optional_key_passphrase",
    "elevate_privileges_with": "sudo"
}
```

---

## References

- `nessusAPIWrapper/manage_credentials.py` - Credential structure patterns
- `nessusAPIWrapper/manage_scans.py` - Scan creation with credentials
- `nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md` - Complete workflow documentation
- `nessusAPIWrapper/CODEBASE_INDEX.md` - Script function reference
- `scanners/nessus_validator.py` - Auth detection logic (Plugin 141118, 110385, 19506)
- `tests/README.md` - Test targets and credentials
