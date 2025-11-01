# Nessus MCP Server - Architecture Plan

## 1. Overall Architecture

### System Components
```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Multi-Agent System              │
│                    (with OpenRouter LLM Backend)            │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP + Bearer Token Auth
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastMCP HTTP Server                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          MCP Tools Layer (Simple Interface)          │  │
│  └──────────────────┬───────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │         Task Manager & Queue System                  │  │
│  │  (Async ops, Status tracking, Polling interface)     │  │
│  └──────────────────┬───────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │    Scanner Abstraction Layer (Pluggable Interface)   │  │
│  └──────────────────┬───────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │         Nessus Scanner Implementation                │  │
│  │      (wraps existing Python scripts)                 │  │
│  └──────────────────┬───────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │   Storage Layer (File system, JSON-NL, NESSUS)      │  │
│  │   + Housekeeping (TTL, last-access tracking)         │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTPS API (port 8834)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│          Nessus Scanner Container (External Service)         │
│                  (tenable/nessus:latest-ubuntu)              │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles
- **Simplicity First**: Clean, maintainable code over premature optimization
- **Pluggable Scanner**: Scanner interface abstracted for future extensibility
- **Shared State**: All agents see all scans (collaborative environment)
- **Async by Design**: Long-running scans don't block MCP calls
- **Stateless MCP Tools**: Task state persisted to filesystem, not in memory

---

## 2. Scanner Abstraction Layer (Pluggable Interface)

### Base Scanner Protocol
```python
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class ScanType(Enum):
    UNTRUSTED = "untrusted"           # No credentials
    TRUSTED_BASIC = "trusted_basic"   # SSH, no privilege escalation
    TRUSTED_PRIVILEGED = "trusted_privileged"  # SSH + sudo/root

@dataclass
class ScanRequest:
    scan_type: ScanType
    targets: List[str]
    name: str
    description: str
    credentials: Dict[str, Any] | None  # Template-based credentials

@dataclass
class ScanTask:
    task_id: str
    scan_id: int | None  # Nessus scan ID
    status: str  # "queued", "running", "completed", "failed", "timeout"
    created_at: str
    started_at: str | None
    completed_at: str | None
    last_accessed_at: str
    scan_request: ScanRequest
    error_message: str | None

class ScannerBackend(Protocol):
    """Pluggable scanner interface for different vulnerability scanners"""

    @abstractmethod
    async def create_scan(self, request: ScanRequest) -> str:
        """Create scan, return scanner-specific scan ID"""
        pass

    @abstractmethod
    async def launch_scan(self, scan_id: str) -> None:
        """Launch the scan"""
        pass

    @abstractmethod
    async def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """Get current scan status"""
        pass

    @abstractmethod
    async def export_scan(self, scan_id: str, format: str) -> bytes:
        """Export scan in native format (e.g., .nessus)"""
        pass

    @abstractmethod
    async def delete_scan(self, scan_id: str) -> None:
        """Delete scan from scanner"""
        pass
```

### Scanner Instance Management

```python
from hashlib import sha256
import random

@dataclass
class ScannerInstance:
    """Represents a specific scanner instance in a pool"""
    scanner_type: str      # "nessus", "openvas", etc.
    instance_id: str       # 4-char hex hash (auto-generated)
    name: str              # "Production Nessus", "Dev Nessus"
    url: str               # "http://nessus-prod:8834"
    credentials: Dict[str, Any]  # API keys, username/password
    enabled: bool = True

    def __post_init__(self):
        """Auto-generate instance_id if not provided"""
        if not self.instance_id:
            hash_input = f"{self.url}:{self.name}"
            self.instance_id = sha256(hash_input.encode()).hexdigest()[:4]

class ScannerRegistry:
    """Registry of scanner instances with pool management"""

    def __init__(self):
        self._instances: Dict[str, ScannerInstance] = {}

    def register_instance(self, instance: ScannerInstance) -> None:
        """Register a scanner instance"""
        key = f"{instance.scanner_type}_{instance.instance_id}"
        self._instances[key] = instance

    def get_instance(
        self,
        scanner_type: str,
        instance_id: str | None = None
    ) -> ScannerInstance:
        """
        Get scanner instance by type and optional instance ID.
        If instance_id is None, returns random enabled instance of that type.
        """
        if instance_id:
            # Specific instance requested
            key = f"{scanner_type}_{instance_id}"
            if key not in self._instances:
                raise ValueError(f"Scanner instance not found: {key}")
            instance = self._instances[key]
            if not instance.enabled:
                raise ValueError(f"Scanner instance disabled: {key}")
            return instance
        else:
            # Pick random enabled instance from pool
            candidates = [
                inst for inst in self._instances.values()
                if inst.scanner_type == scanner_type and inst.enabled
            ]
            if not candidates:
                raise ValueError(f"No enabled scanners of type: {scanner_type}")
            return random.choice(candidates)

    def list_instances(
        self,
        scanner_type: str | None = None,
        enabled_only: bool = True
    ) -> List[ScannerInstance]:
        """List all instances, optionally filtered by type and enabled status"""
        instances = self._instances.values()

        if scanner_type:
            instances = [i for i in instances if i.scanner_type == scanner_type]

        if enabled_only:
            instances = [i for i in instances if i.enabled]

        return list(instances)

    def disable_instance(self, scanner_type: str, instance_id: str) -> None:
        """Disable a scanner instance (e.g., for maintenance)"""
        key = f"{scanner_type}_{instance_id}"
        if key in self._instances:
            self._instances[key].enabled = False

    def enable_instance(self, scanner_type: str, instance_id: str) -> None:
        """Enable a scanner instance"""
        key = f"{scanner_type}_{instance_id}"
        if key in self._instances:
            self._instances[key].enabled = True
```

**Configuration Example**:
```python
# Initialize registry at startup
registry = ScannerRegistry()

# Register multiple Nessus instances (pool)
registry.register_instance(ScannerInstance(
    scanner_type="nessus",
    instance_id="",  # Auto-generated
    name="Production Nessus",
    url="http://nessus-prod:8834",
    credentials={
        "access_key": "...",
        "secret_key": "...",
        "username": "nessus",
        "password": "nessus"
    }
))

registry.register_instance(ScannerInstance(
    scanner_type="nessus",
    instance_id="",
    name="Dev Nessus",
    url="http://nessus-dev:8834",
    credentials={...}
))

# Future: Register OpenVAS instances
registry.register_instance(ScannerInstance(
    scanner_type="openvas",
    instance_id="",
    name="Main OpenVAS",
    url="http://openvas:9392",
    credentials={...}
))

# Get specific instance
prod_nessus = registry.get_instance("nessus", "a3f2")

# Get random instance from pool
random_nessus = registry.get_instance("nessus")  # Random selection
```

**Justification**:
- Separates MCP logic from scanner-specific implementation
- Easy to add OpenVAS, Qualys, Tenable.io, or custom scanners
- Each scanner implementation wraps its own API/CLI
- Nessus implementation wraps existing Python scripts
- **Pool management**: Multiple instances of same scanner type
- **Load balancing**: Random selection when instance not specified
- **Maintenance**: Can disable instances without removing them
- **Unique task IDs**: Instance ID embedded in task ID for traceability

---

## 3. Core Workflow Types

### Workflow Implementation Strategy

Each workflow type uses different credential templates:

#### 3.1 Untrusted Scan
```python
# No credentials, network-only
# - Port scanning
# - Banner grabbing
# - Service detection
# - CVE matching based on versions
# - No authenticated checks

scan_request = ScanRequest(
    scan_type=ScanType.UNTRUSTED,
    targets=["192.168.1.0/24"],
    name="Network Discovery",
    description="Unauthenticated network scan",
    credentials=None
)
```

#### 3.2 Trusted Non-Privileged Scan
```python
# SSH with regular user, no sudo
# - Software inventory
# - Configuration checks
# - Non-privileged file access
# - Process enumeration
# - User-level vulnerability checks

credentials_template = {
    "username": "scanuser",
    "password": "scanpass",
    "auth_method": "password",
    "elevate_privileges_with": "Nothing",  # No privilege escalation
    "escalation_password": None,
    "escalation_account": None
}

scan_request = ScanRequest(
    scan_type=ScanType.TRUSTED_BASIC,
    targets=["192.168.1.10"],
    credentials=credentials_template,
    ...
)
```

#### 3.3 Trusted Privileged Scan
```python
# SSH with sudo/root access
# - Full system inventory
# - Kernel vulnerability checks
# - System configuration audits
# - Installed package enumeration
# - Deep compliance checks

credentials_template = {
    "username": "scanadmin",
    "password": "adminpass",
    "auth_method": "password",
    "elevate_privileges_with": "sudo",  # or "su", "pbrun", etc.
    "escalation_password": "sudopass",
    "escalation_account": "root"
}

scan_request = ScanRequest(
    scan_type=ScanType.TRUSTED_PRIVILEGED,
    targets=["192.168.1.10"],
    credentials=credentials_template,
    ...
)
```

---

## 4. Data Formats & Schema Negotiation

### 4.1 Schema Definition System

```python
from dataclasses import dataclass
from typing import List, Literal

@dataclass
class SchemaProfile:
    """Predefined schema profiles (Option A - Required)"""
    name: str
    fields: List[str]
    description: str

# Predefined profiles
SCHEMA_PROFILES = {
    "minimal": SchemaProfile(
        name="minimal",
        fields=["host", "plugin_id", "severity", "cve", "cvss_score", "exploit_available"],
        description="Essential vulnerability identifiers only"
    ),
    "summary": SchemaProfile(
        name="summary",
        fields=["host", "plugin_id", "plugin_name", "severity", "cve", "cvss_base_score",
                "cvss3_base_score", "exploit_available", "synopsis"],
        description="Key vulnerability information with synopsis"
    ),
    "brief": SchemaProfile(
        name="brief",
        fields=["host", "plugin_id", "plugin_name", "severity", "cve", "cvss_base_score",
                "cvss3_base_score", "exploit_available", "description", "solution"],
        description="Actionable vulnerability details"
    ),
    "full": SchemaProfile(
        name="full",
        fields=["*"],  # All fields from detailed export
        description="Complete vulnerability data including metadata"
    )
}

@dataclass
class SchemaRequest:
    """Client schema negotiation"""
    profile: Literal["minimal", "summary", "brief", "full", "custom"] = "brief"
    custom_fields: List[str] | None = None  # Option C: JSON schema definition
    natural_language_desc: str | None = None  # Option D: Placeholder for future
    page_size: int = 40  # Lines per page (30-50 default)
```

### 4.2 JSON-NL Output Format

```python
# Paginated JSON-NL structure
# Each line is a complete JSON object

# Line 1: Schema definition
{"type": "schema", "profile": "brief", "fields": ["host", "plugin_id", ...], "total_vulnerabilities": 1523, "total_pages": 39}

# Line 2: Scan metadata (always included)
{"type": "scan_metadata", "task_id": "ns_20250101_120345_a1b2c3", "scan_name": "Production Servers", "scan_type": "trusted_privileged", "started_at": "2025-01-01T12:03:45Z", "completed_at": "2025-01-01T14:25:12Z", "targets": ["192.168.1.10", "192.168.1.11"], "credentials_used": {"username": "scanadmin", "auth_method": "password", "privilege_escalation": "sudo"}}

# Lines 3-42: Vulnerability data (40 items, configurable page_size)
{"type": "vulnerability", "host": "192.168.1.10", "plugin_id": 12345, "plugin_name": "Apache CVE-2023-XXXX", "severity": "Critical", "cve": ["CVE-2023-XXXX"], "cvss_base_score": 9.8, "cvss3_base_score": 9.8, "exploit_available": true, "description": "...", "solution": "..."}
{"type": "vulnerability", "host": "192.168.1.10", "plugin_id": 12346, ...}
...

# Line 43: Pagination marker
{"type": "pagination", "page": 1, "total_pages": 39, "next_page_token": "page_2"}

# Optional: Scan settings on demand
{"type": "scan_settings", "folder_id": 3, "scanner_id": 1, "policy_template": "advanced", "scan_duration_seconds": 8487, "ports_scanned": "1-65535", ...}
```

**Key Features**:
- Each JSON-NL line is independently parseable
- Schema negotiation prevents context clutter
- Pagination with configurable page size (30-50 lines default)
- Scan metadata included once at the top
- Settings included only when requested

---

## 5. Task Management & Async Operations

### 5.1 Task ID Format
```python
# Format: {scanner_type}_{instance_id}_{date}_{time}_{random_suffix}
# Examples:
#   ns_a3f2_20250101_120345_b1c2d3e4  (nessus instance a3f2)
#   ov_8d4c_20250101_130512_c2d3e4f5  (openvas instance 8d4c)
#   ns_b7e1_20250101_140612_d3e4f5a6  (different nessus instance)
#
# Where:
#   scanner_type = "ns" (nessus), "ov" (openvas), etc.
#   instance_id = 4-char hex hash of scanner URL + name (identifies specific scanner)
#   date = YYYYMMDD
#   time = HHMMSS
#   random_suffix = 8-char hex for uniqueness

import secrets
from datetime import datetime
from hashlib import sha256

def generate_instance_id(scanner_url: str, scanner_name: str) -> str:
    """Generate 4-char instance ID from scanner URL and name"""
    hash_input = f"{scanner_url}:{scanner_name}"
    return sha256(hash_input.encode()).hexdigest()[:4]

def generate_task_id(scanner_type: str, instance_id: str) -> str:
    """Generate unique task ID for a scanner instance"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(4)
    return f"{scanner_type}_{instance_id}_{timestamp}_{suffix}"
```

### 5.2 Task State Machine

```
queued → running → completed
                 → failed
                 → timeout (>24h)
```

### 5.3 Task Storage Structure

```
data/
├── tasks/
│   ├── ns_a3f2_20250101_120345_b1c2d3e4/
│   │   ├── task.json              # Task metadata & status
│   │   ├── scan_request.json      # Original scan request
│   │   ├── scan_native.nessus     # Native Nessus format (stored here!)
│   │   ├── scan_schema_brief.jsonl   # Pre-generated JSON-NL (brief profile)
│   │   ├── scan_schema_full.jsonl    # Pre-generated JSON-NL (full profile)
│   │   ├── logs.txt               # MCP execution logs
│   │   └── scanner_logs/          # Internal scanner debug logs (if enabled)
│   │       ├── nessus_api.log
│   │       ├── scan_progress.log
│   │       └── export.log
│   └── ns_a3f2_20250101_140512_c2d3e4f5/
│       └── ...
├── queue/
│   └── queue.json                 # Simple FIFO queue of task_ids
└── schemas/
    └── custom_schema_hash.json    # Custom schema definitions (reusable)
```

**File: task.json**
```json
{
  "task_id": "ns_a3f2_20250101_120345_b1c2d3e4",
  "status": "completed",
  "scan_id": 42,
  "scanner_type": "nessus",
  "scanner_instance_id": "a3f2",
  "scanner_instance_name": "Production Nessus",
  "created_at": "2025-01-01T12:03:45Z",
  "started_at": "2025-01-01T12:04:12Z",
  "completed_at": "2025-01-01T14:25:38Z",
  "last_accessed_at": "2025-01-01T14:30:00Z",
  "error_message": null,
  "scan_type": "trusted_privileged",
  "ttl_hours": 24,
  "debug_mode": true,
  "scanner_logs_available": true
}
```

### 5.4 Queue System

```python
class SimpleTaskQueue:
    """FIFO queue for scan tasks"""

    def __init__(self, queue_file: str):
        self.queue_file = queue_file

    async def enqueue(self, task_id: str) -> None:
        """Add task to queue"""
        pass

    async def dequeue(self) -> str | None:
        """Get next task, return None if empty"""
        pass

    async def get_position(self, task_id: str) -> int:
        """Get queue position (1-indexed)"""
        pass

    async def list_queue(self) -> List[str]:
        """List all queued task IDs"""
        pass
```

**Concurrency Consideration**:
- Single worker process consumes queue (simple, no race conditions)
- Multiple agents can submit → queue handles serialization
- Queue prevents scanner overload

---

## 6. MCP Tools Layer - API Surface

### Option A: Separate Tools per Workflow (Recommended)

**Justification**:
- ✅ **Simpler for LLM agents** - Clear tool names indicate purpose
- ✅ **Type safety** - Each tool has specific credential requirements
- ✅ **Better tool descriptions** - Focused documentation per scan type
- ✅ **Easier to extend** - Add new scan types without breaking existing tools
- ⚠️ **More tools** - But only 3 core scan tools (manageable)

```python
from fastmcp import FastMCP

mcp = FastMCP("Nessus Scanner")

@mcp.tool()
async def run_untrusted_scan(
    targets: str,
    name: str,
    description: str = "",
    schema_profile: str = "brief",
    scanner_type: str = "nessus",
    scanner_instance: str | None = None,
    debug_mode: bool = False
) -> dict:
    """
    Run untrusted network scan (no credentials).

    Performs network-only vulnerability scanning:
    - Port scanning and service detection
    - Banner grabbing and version identification
    - CVE matching based on detected versions
    - No authenticated checks

    Args:
        targets: IP addresses or ranges (e.g., "192.168.1.0/24, 10.0.0.1")
        name: Scan name for identification
        description: Optional scan description
        schema_profile: Output schema (minimal|summary|brief|full)
        scanner_type: Scanner type to use (nessus|openvas|qualys)
        scanner_instance: Specific scanner instance ID, or None for random selection
        debug_mode: Enable detailed scanner logging

    Returns:
        {"task_id": "ns_a3f2_...", "status": "queued", "queue_position": 2, "scanner_instance": "a3f2"}
    """
    pass

@mcp.tool()
async def run_trusted_scan(
    targets: str,
    name: str,
    username: str,
    password: str,
    auth_method: str = "password",
    description: str = "",
    schema_profile: str = "brief",
    scanner_type: str = "nessus",
    scanner_instance: str | None = None,
    debug_mode: bool = False
) -> dict:
    """
    Run trusted scan with non-privileged SSH access.

    Performs authenticated scanning with regular user credentials:
    - Software inventory and version detection
    - Configuration file analysis (user-accessible)
    - Process enumeration
    - User-level vulnerability checks
    - No privilege escalation

    Args:
        targets: IP addresses or ranges
        name: Scan name
        username: SSH username
        password: SSH password
        auth_method: Authentication method (password|certificate|publickey|kerberos)
        description: Optional description
        schema_profile: Output schema (minimal|summary|brief|full)
        scanner_type: Scanner type to use (nessus|openvas|qualys)
        scanner_instance: Specific scanner instance ID, or None for random selection
        debug_mode: Enable detailed scanner logging

    Returns:
        {"task_id": "ns_a3f2_...", "status": "queued", "queue_position": 1, "scanner_instance": "a3f2"}
    """
    pass

@mcp.tool()
async def run_privileged_scan(
    targets: str,
    name: str,
    username: str,
    password: str,
    escalation_method: str,
    escalation_password: str,
    escalation_account: str = "root",
    auth_method: str = "password",
    description: str = "",
    schema_profile: str = "brief",
    scanner_type: str = "nessus",
    scanner_instance: str | None = None,
    debug_mode: bool = False
) -> dict:
    """
    Run trusted scan with privileged access (sudo/root).

    Performs deep authenticated scanning with privilege escalation:
    - Complete system inventory
    - Kernel vulnerability detection
    - System-wide configuration audits
    - All installed packages and services
    - Compliance policy checks
    - Full filesystem access

    Args:
        targets: IP addresses or ranges
        name: Scan name
        username: SSH username
        password: SSH password
        escalation_method: Privilege escalation (sudo|su|pbrun|dzdo|cisco_enable)
        escalation_password: Password for privilege escalation
        escalation_account: Target privileged account (default: root)
        auth_method: Authentication method (password|certificate|publickey|kerberos)
        description: Optional description
        schema_profile: Output schema (minimal|summary|brief|full)
        scanner_type: Scanner type to use (nessus|openvas|qualys)
        scanner_instance: Specific scanner instance ID, or None for random selection
        debug_mode: Enable detailed scanner logging

    Returns:
        {"task_id": "ns_a3f2_...", "status": "queued", "queue_position": 0, "scanner_instance": "a3f2"}
    """
    pass

@mcp.tool()
async def get_scan_status(task_id: str) -> dict:
    """
    Poll scan task status.

    Returns current status of a scan task. Use this to monitor long-running scans.

    Args:
        task_id: Task ID returned from run_*_scan()

    Returns:
        {
            "task_id": "ns_...",
            "status": "running|completed|failed|timeout|queued",
            "progress": 45,  # percentage (0-100), null if not available
            "created_at": "2025-01-01T12:03:45Z",
            "started_at": "2025-01-01T12:04:12Z",
            "completed_at": null,
            "queue_position": null,  # set if status=queued
            "error_message": null
        }
    """
    pass

@mcp.tool()
async def get_scan_results(
    task_id: str,
    page: int = 1,
    page_size: int = 40,
    custom_schema: dict | None = None,
    filters: dict | None = None
) -> str:
    """
    Retrieve scan results in paginated JSON-NL format with optional filtering.

    Returns vulnerability data in JSON Lines format (one JSON object per line).
    Only available when scan status is "completed".

    Args:
        task_id: Task ID from run_*_scan()
        page: Page number (1-indexed), or 0 for ALL data (no pagination, client's responsibility)
        page_size: Lines per page (default: 40, range: 10-100), ignored if page=0
        custom_schema: Optional custom field list (overrides profile)
        filters: Optional dict of field filters. All filters are ANDed together.
                 Works on ANY attribute available in the schema.

                 Filter syntax by data type:
                 - Strings: Substring match (case-insensitive)
                   Example: {"plugin_name": "SSH", "severity": "Critical"}
                 - Numbers: Comparison operators as string prefix
                   Example: {"cvss3_base_score": ">7.0", "cvss_base_score": ">=6.5"}
                   Operators: ">", ">=", "<", "<=", "=", or plain number for exact match
                 - Booleans: Exact match
                   Example: {"exploit_available": true}
                 - Lists (e.g., CVE): Any element contains substring
                   Example: {"cve": "CVE-2023"}

    Returns:
        Multi-line JSON-NL string with:
        - Line 1: Schema definition (includes applied filters)
        - Line 2: Scan metadata
        - Lines 3-N: Filtered vulnerability data
        - Last line: Pagination info (includes filtered_count and total_count)

    Examples:
        # Only Critical vulnerabilities
        get_scan_results(task_id, filters={"severity": "Critical"})

        # CVSS > 7.0 with exploits available
        get_scan_results(task_id, filters={"cvss3_base_score": ">7.0", "exploit_available": true})

        # SSH vulnerabilities on specific host
        get_scan_results(task_id, filters={"plugin_name": "SSH", "host": "192.168.1.10"})

        # All data without pagination (client manages size)
        get_scan_results(task_id, page=0)

    Note: Client's LLM backend generates filters based on schema attributes.
          MCP server applies filters generically to any schema field.
    """
    pass

@mcp.tool()
async def get_scan_settings(task_id: str) -> dict:
    """
    Get detailed scan settings and configuration.

    Returns comprehensive scan metadata including:
    - Original scan request parameters
    - Nessus configuration (policy, plugins, ports)
    - Execution timeline
    - Credential information (passwords masked)

    Args:
        task_id: Task ID from run_*_scan()

    Returns:
        Full scan configuration dictionary
    """
    pass

@mcp.tool()
async def list_scans(
    status: str | None = None,
    scan_type: str | None = None,
    limit: int = 50
) -> list:
    """
    List all scans visible to this MCP server (shared state).

    All agents see all scans for collaboration. Filter by status or type.

    Args:
        status: Filter by status (queued|running|completed|failed|timeout)
        scan_type: Filter by type (untrusted|trusted_basic|trusted_privileged)
        limit: Maximum results (default: 50)

    Returns:
        List of scan summaries with task_id, name, status, created_at, last_accessed_at
    """
    pass

@mcp.tool()
async def delete_scan(task_id: str, force: bool = False) -> dict:
    """
    Delete a scan task and all associated data.

    Permanently removes scan from filesystem. No recovery possible.
    If scan is running, must set force=True.

    Args:
        task_id: Task ID to delete
        force: Allow deletion of running scans

    Returns:
        {"deleted": true, "task_id": "ns_..."}
    """
    pass

@mcp.tool()
async def download_native_scan(task_id: str) -> str:
    """
    Get path/URL to native .nessus scan file.

    Returns location of native Nessus format file for external analysis tools
    or semantic search indexing.

    Args:
        task_id: Task ID from completed scan

    Returns:
        {"file_path": "/data/tasks/ns_.../scan_native.nessus", "size_bytes": 2458624}
    """
    pass

@mcp.tool()
async def list_scanners(
    scanner_type: str | None = None,
    enabled_only: bool = True
) -> list:
    """
    List available scanner instances.

    Returns all registered scanner instances with their details.
    Useful for clients to see available scanners before submitting scans.

    Args:
        scanner_type: Filter by scanner type (nessus|openvas|qualys), or None for all
        enabled_only: Only show enabled scanners (default: True)

    Returns:
        List of scanner instances:
        [
            {
                "scanner_type": "nessus",
                "instance_id": "a3f2",
                "name": "Production Nessus",
                "url": "http://nessus-prod:8834",
                "enabled": true
            },
            {
                "scanner_type": "nessus",
                "instance_id": "b7e1",
                "name": "Dev Nessus",
                "url": "http://nessus-dev:8834",
                "enabled": true
            },
            {
                "scanner_type": "openvas",
                "instance_id": "8d4c",
                "name": "Main OpenVAS",
                "url": "http://openvas:9392",
                "enabled": false
            }
        ]

    Note: Credentials are not included in the response for security.
    """
    pass
```

### Option B: Single Tool with Parameters (Alternative)

**Justification**:
- ✅ **Fewer tools** - Single entry point
- ⚠️ **More complex parameters** - Credential parameters optional/required based on scan_type
- ⚠️ **Harder for LLM** - Needs to understand conditional parameter requirements
- ❌ **Less type safety** - Can't enforce credential requirements at tool signature level

```python
@mcp.tool()
async def run_scan(
    scan_type: str,  # "untrusted|trusted_basic|trusted_privileged"
    targets: str,
    name: str,
    credentials: dict | None = None,  # Required for trusted scans
    description: str = "",
    schema_profile: str = "brief"
) -> dict:
    """
    Run vulnerability scan with specified credential level.

    Scan types:
    - untrusted: No credentials, network-only scanning
    - trusted_basic: SSH credentials, no privilege escalation
    - trusted_privileged: SSH credentials with sudo/root access

    Args:
        scan_type: Type of scan to run
        targets: IP addresses or ranges
        name: Scan name
        credentials: SSH credentials dict (required for trusted scans)
        description: Optional description
        schema_profile: Output schema (minimal|summary|brief|full)

    Returns:
        {"task_id": "ns_...", "status": "queued"}
    """
    pass
```

**Recommendation**: **Option A (Separate Tools)** for better LLM usability and type safety.

---

## 7. Storage & Housekeeping

### 7.1 Retention & Cleanup

```python
class HousekeepingService:
    """Background service for scan cleanup"""

    def __init__(self, data_dir: str, default_ttl_hours: int = 24):
        self.data_dir = data_dir
        self.default_ttl_hours = default_ttl_hours

    async def cleanup_expired_scans(self) -> int:
        """
        Delete scans based on last_accessed_at + TTL.

        Runs periodically (e.g., every hour).
        Returns number of scans deleted.
        """
        pass

    async def update_last_accessed(self, task_id: str) -> None:
        """Update last_accessed_at timestamp when scan is read"""
        pass

    async def set_custom_ttl(self, task_id: str, ttl_hours: int) -> None:
        """Override default TTL for specific scan"""
        pass
```

**Cleanup Logic**:
```python
# Scan is deleted if:
current_time - last_accessed_at > ttl_hours

# Default TTL: 24 hours (configurable)
# TTL is extended each time scan results are accessed
# No recovery after deletion (hard delete)
```

### 7.2 Last Access Tracking

```python
# Every time get_scan_results() or download_native_scan() is called:
await housekeeping.update_last_accessed(task_id)

# Updates task.json:
{
    ...
    "last_accessed_at": "2025-01-01T15:42:18Z"  # Reset TTL timer
}
```

---

## 8. Multi-Agent Considerations

### 8.1 Shared State Design

```python
# All agents see all scans via list_scans()
# No agent-specific isolation

# Collaboration pattern:
# Agent A: Runs privileged scan, gets task_id
# Agent A: Shares task_id in multiagent system chat/context
# Agent B: Calls get_scan_status(task_id) to monitor
# Agent B: Calls get_scan_results(task_id) to analyze different aspects
# Agent C: Calls download_native_scan(task_id) for semantic search indexing
```

### 8.2 Concurrent Access Handling

```python
# Queue System prevents scanner overload:
# - Multiple agents can submit scans → queued in FIFO order
# - Single worker processes queue sequentially
# - No parallel scans (Nessus limitation, prevent resource exhaustion)

# File-based locking for shared resources:
import fcntl

class FileLock:
    """Simple file-based lock for queue operations"""
    def __init__(self, lockfile: str):
        self.lockfile = lockfile

    def __enter__(self):
        self.fd = open(self.lockfile, 'w')
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *args):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        self.fd.close()
```

### 8.3 Download Pattern for Large Results

```python
# Instead of returning megabytes in MCP response:

# 1. Agent calls get_scan_results() with pagination
#    Returns 30-50 lines at a time

# 2. Agent calls download_native_scan() for full data
#    Returns file path on shared filesystem

# 3. Agent can stream file directly or index it externally

# Benefit: MCP responses stay small, full data accessible on demand
```

---

## 9. Deployment Architecture

### 9.1 Docker Compose Setup

```yaml
# docker-compose.yml for MCP Server

networks:
  nessus_mcp_net:
    driver: bridge
    external: false

services:
  nessus-mcp-server:
    build: ./nessus-mcp-server
    container_name: nessus-mcp-server
    ports:
      - "8835:8000"  # Different port from Nessus (8834)
    environment:
      - NESSUS_URL=http://vpn-gateway:8834  # Connect to existing Nessus
      - NESSUS_ACCESS_KEY=${NESSUS_ACCESS_KEY}
      - NESSUS_SECRET_KEY=${NESSUS_SECRET_KEY}
      - NESSUS_USERNAME=nessus
      - NESSUS_PASSWORD=nessus
      - MCP_BEARER_TOKEN=${MCP_BEARER_TOKEN}
      - DATA_DIR=/data
      - DEFAULT_TTL_HOURS=24
    volumes:
      - ./data:/data  # Persistent scan storage
      - ./logs:/logs  # Application logs
    networks:
      - nessus_mcp_net
      - nessus_net  # Connect to existing Nessus network
    restart: unless-stopped
    depends_on:
      - nessus-mcp-worker

  nessus-mcp-worker:
    build: ./nessus-mcp-server
    container_name: nessus-mcp-worker
    command: ["python", "worker.py"]  # Queue worker process
    environment:
      - NESSUS_URL=http://vpn-gateway:8834
      - NESSUS_ACCESS_KEY=${NESSUS_ACCESS_KEY}
      - NESSUS_SECRET_KEY=${NESSUS_SECRET_KEY}
      - NESSUS_USERNAME=nessus
      - NESSUS_PASSWORD=nessus
      - DATA_DIR=/data
      - SCAN_TIMEOUT_HOURS=24
    volumes:
      - ./data:/data
      - ./logs:/logs
    networks:
      - nessus_mcp_net
      - nessus_net
    restart: unless-stopped

networks:
  nessus_net:
    external: true  # Connect to existing Nessus network
```

### 9.2 Container Architecture

```
┌─────────────────────────────────────────────┐
│  nessus-mcp-server (FastMCP HTTP Server)    │
│  - Handles MCP tool calls                   │
│  - Bearer token authentication              │
│  - Enqueues scan tasks                      │
│  - Serves scan results                      │
│  Port: 8835 → 8000                          │
└─────────────┬───────────────────────────────┘
              │ Shared /data volume
┌─────────────▼───────────────────────────────┐
│  nessus-mcp-worker (Background Worker)      │
│  - Processes scan queue                     │
│  - Communicates with Nessus scanner         │
│  - Exports results to filesystem            │
│  - Monitors scan progress                   │
└─────────────┬───────────────────────────────┘
              │ HTTP API (port 8834)
┌─────────────▼───────────────────────────────┐
│  Existing Nessus Container                  │
│  (Already running in your docker-compose)   │
└─────────────────────────────────────────────┘
```

### 9.3 Pluggable Scanner Interface

```python
# scanner_registry.py
from typing import Dict, Type
from .scanners.base import ScannerBackend
from .scanners.nessus import NessusScanner
# Future: from .scanners.openvas import OpenVASScanner

class ScannerRegistry:
    """Registry of available scanner implementations"""

    _scanners: Dict[str, Type[ScannerBackend]] = {
        "nessus": NessusScanner,
        # "openvas": OpenVASScanner,  # Future
        # "qualys": QualysScanner,    # Future
    }

    @classmethod
    def get_scanner(cls, scanner_type: str) -> ScannerBackend:
        """Get scanner instance by type"""
        if scanner_type not in cls._scanners:
            raise ValueError(f"Unknown scanner type: {scanner_type}")
        return cls._scanners[scanner_type]()

    @classmethod
    def register_scanner(cls, name: str, scanner_class: Type[ScannerBackend]):
        """Register custom scanner implementation"""
        cls._scanners[name] = scanner_class
```

**Directory Structure**:
```
nessus-api/                          # Root project directory
├── scripts/                         # Existing Python scripts (unchanged)
│   ├── manage_scans.py
│   ├── manage_credentials.py
│   ├── launch_scan.py
│   ├── export_vulnerabilities_detailed.py
│   └── ...
├── docs/                            # Documentation
│   ├── CODEBASE_INDEX.md
│   ├── NESSUS_MCP_SERVER_ARCHITECTURE.md
│   └── fastMCPServer/
└── mcp-server/                      # NEW: MCP server implementation
    ├── README.md
    ├── requirements.txt
    ├── Dockerfile
    ├── docker-compose.yml
    ├── .env.example
    ├── server.py                    # FastMCP HTTP server entrypoint
    ├── worker.py                    # Background queue worker
    ├── config.py                    # Configuration management
    ├── admin_cli.py                 # Administrative CLI (not via MCP)
    ├── scanners/                    # Scanner abstraction layer
    │   ├── __init__.py
    │   ├── base.py                  # ScannerBackend protocol
    │   ├── registry.py              # ScannerRegistry + ScannerInstance
    │   └── nessus.py                # Nessus implementation (wraps ../scripts/)
    ├── core/                        # Core task management
    │   ├── __init__.py
    │   ├── task_manager.py          # Task state management
    │   ├── queue.py                 # Simple FIFO queue
    │   └── housekeeping.py          # TTL cleanup service
    ├── schema/                      # Schema and data conversion
    │   ├── __init__.py
    │   ├── profiles.py              # Schema profiles (minimal/summary/brief/full)
    │   ├── converter.py             # Nessus → JSON-NL conversion
    │   └── filters.py               # Generic filtering logic
    ├── tools/                       # MCP tools implementation
    │   ├── __init__.py
    │   ├── scan_tools.py            # run_*_scan tools
    │   ├── status_tools.py          # get_scan_status, list_scans
    │   ├── results_tools.py         # get_scan_results, download_native
    │   └── scanner_tools.py         # list_scanners
    ├── tests/                       # Unit and integration tests
    │   ├── __init__.py
    │   ├── test_scanner.py
    │   ├── test_queue.py
    │   ├── test_filters.py
    │   └── test_tools.py
    └── data/                        # Runtime data (gitignored)
        ├── tasks/
        │   └── ns_a3f2_20250101_120345_b1c2d3e4/
        │       ├── task.json
        │       ├── scan_request.json
        │       ├── scan_native.nessus
        │       ├── scan_schema_brief.jsonl
        │       ├── scan_schema_full.jsonl
        │       ├── logs.txt
        │       └── scanner_logs/    # Debug logs directory
        ├── queue/
        │   └── queue.json
        └── schemas/
            └── custom_schema_*.json
```

---

## 10. Security & Authentication

### 10.1 Bearer Token Authentication

```python
# Using FastMCP HTTP deployment with Bearer auth

from fastmcp import FastMCP
from fastmcp.server.http import BearerAuth
import os

mcp = FastMCP("Nessus Scanner")

# ... define tools ...

if __name__ == "__main__":
    bearer_token = os.getenv("MCP_BEARER_TOKEN")

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000,
        auth=BearerAuth(token=bearer_token)
    )
```

**Client Usage**:
```python
# From FastAPI multiagent system
from fastmcp import FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server.http import BearerAuth

client = FastMCP(
    transport=StreamableHttpTransport(
        url="http://nessus-mcp-server:8000",
        auth=BearerAuth(token=MCP_BEARER_TOKEN)
    )
)

result = await client.call_tool("run_privileged_scan", {...})
```

### 10.2 Administrative CLI (Not via MCP)

```python
# admin_cli.py - Separate CLI tool, not exposed via MCP

import typer
from typing import Optional

app = typer.Typer()

@app.command()
def cleanup_all():
    """Force cleanup of all expired scans (admin only)"""
    pass

@app.command()
def reset_queue():
    """Clear scan queue (admin only)"""
    pass

@app.command()
def show_stats():
    """Show system statistics"""
    pass

@app.command()
def set_ttl(task_id: str, hours: int):
    """Override TTL for specific scan"""
    pass

@app.command()
def export_audit_log():
    """Export all scan activity logs"""
    pass

if __name__ == "__main__":
    app()
```

**Usage**:
```bash
# Inside container or with mounted volume
docker exec nessus-mcp-server python admin_cli.py cleanup_all
docker exec nessus-mcp-server python admin_cli.py show_stats
```

---

## 11. Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Scanner abstraction layer (`ScannerBackend` protocol)
- [ ] Nessus scanner implementation (wrap existing scripts)
- [ ] Task management system (task IDs, state machine, filesystem storage)
- [ ] Simple FIFO queue
- [ ] Basic FastMCP server with authentication

### Phase 2: Scan Workflows (Week 2)
- [ ] Implement three scan type tools (untrusted, trusted, privileged)
- [ ] Credential template handling
- [ ] Scan creation and launch logic
- [ ] Status polling tool
- [ ] Background worker process

### Phase 3: Results & Schema (Week 3)
- [ ] Schema negotiation system (predefined profiles)
- [ ] JSON-NL export from Nessus native format
- [ ] Pagination logic
- [ ] `get_scan_results()` tool
- [ ] `get_scan_settings()` tool
- [ ] Native scan file access

### Phase 4: Management & Housekeeping (Week 4)
- [ ] `list_scans()` tool with filtering
- [ ] `delete_scan()` tool
- [ ] Housekeeping service (TTL cleanup)
- [ ] Last-access tracking
- [ ] Administrative CLI

### Phase 5: Deployment & Testing (Week 5)
- [ ] Docker containerization
- [ ] Docker Compose integration with existing Nessus
- [ ] Integration tests with real Nessus scanner
- [ ] Multi-agent access testing
- [ ] Documentation

### Phase 6: Advanced Features (Future)
- [ ] Custom schema support (JSON schema definition)
- [ ] Natural language schema description (LLM-based)
- [ ] Semantic search integration placeholder
- [ ] Additional scanner backends (OpenVAS, etc.)
- [ ] Database backend option (if performance needed)

---

## 12. Key Design Decisions Summary

| Decision | Choice | Justification |
|----------|--------|---------------|
| **Scanner Interface** | Pluggable protocol with instance registry | Multiple scanners, pool management, easy extension |
| **Scanner Instances** | 4-char hash in task ID | Identifies specific scanner, enables load balancing |
| **MCP Tools** | Separate tools per scan type + list_scanners() | Better LLM usability, type safety, scanner discovery |
| **Storage** | Filesystem (JSON-NL) | Simple, no premature DB optimization |
| **Scanner Logs** | Directory per task (debug mode) | Organized debug logs, optional overhead |
| **Queue** | Simple FIFO | Single worker, prevents overload |
| **Task IDs** | {type}_{instance}_{timestamp}_{random} | Unique, scanner-traceable, chronologically sortable |
| **Result Format** | Paginated JSON-NL | Prevents context clutter, LLM-friendly |
| **Pagination** | page=0 for all data | Client responsibility for size management |
| **Schema** | Negotiated (profiles + custom) | Flexible, client controls verbosity |
| **Filtering** | Generic AND filters on any attribute | LLM-generated, substring matching, simple operators |
| **Scan Storage** | Native .nessus format | Minimal scanner engagement, semantic search ready |
| **Async Model** | Task ID + polling | Long-running scans, non-blocking |
| **Multi-Agent** | Shared state, no isolation | Collaboration, concurrent submissions |
| **Authentication** | Bearer token only | Simple, no complex access levels |
| **Admin Tasks** | Separate CLI, not MCP | Security boundary |
| **Deployment** | Docker Compose, HTTP | Integrates with existing Nessus setup |
| **Directory Structure** | mcp-server/ separate from scripts/ | Clean separation, organized modules |
| **Retention** | Last-access + TTL | Automatic cleanup, no manual intervention needed |
| **Concurrency** | File locks, single worker | Simple, avoids race conditions |

---

## 13. Example Usage Workflow

```python
# Agent in multiagent system using MCP client

# 0. List available scanners (optional, for discovery)
scanners = await mcp_client.call_tool("list_scanners", {"scanner_type": "nessus"})
print(f"Available Nessus scanners: {len(scanners)}")
# [{"scanner_type": "nessus", "instance_id": "a3f2", "name": "Production Nessus", ...}]

# 1. Submit privileged scan (let MCP pick random scanner instance)
result = await mcp_client.call_tool("run_privileged_scan", {
    "targets": "192.168.1.10,192.168.1.11",
    "name": "Production Server Audit",
    "username": "scanadmin",
    "password": "adminpass",
    "escalation_method": "sudo",
    "escalation_password": "sudopass",
    "description": "Monthly compliance scan",
    "schema_profile": "brief",
    "scanner_type": "nessus",      # Optional, defaults to nessus
    "scanner_instance": None,       # None = random selection from pool
    "debug_mode": True              # Enable detailed scanner logs
})

task_id = result["task_id"]  # "ns_a3f2_20250101_120345_b1c2d3e4"
scanner_instance = result["scanner_instance"]  # "a3f2"
print(f"Scan queued: {task_id} on scanner {scanner_instance}, position: {result['queue_position']}")

# 2. Poll status (agent checks periodically)
status = await mcp_client.call_tool("get_scan_status", {"task_id": task_id})
print(f"Status: {status['status']}, Progress: {status['progress']}%")

# 3. When completed, get filtered results (only Critical with exploits)
results = await mcp_client.call_tool("get_scan_results", {
    "task_id": task_id,
    "page": 1,
    "page_size": 40,
    "filters": {
        "severity": "Critical",
        "exploit_available": True,
        "cvss3_base_score": ">7.0"
    }
})

# Parse JSON-NL results
for line in results.split('\n'):
    vuln = json.loads(line)
    if vuln['type'] == 'vulnerability':
        print(f"CRITICAL: {vuln['plugin_name']} on {vuln['host']} (CVSS: {vuln['cvss3_base_score']})")

# 4. Another agent filters for SSH vulnerabilities with custom schema
agent2_results = await mcp_client.call_tool("get_scan_results", {
    "task_id": task_id,
    "page": 1,
    "custom_schema": {"fields": ["host", "plugin_name", "cve", "cvss3_base_score", "solution"]},
    "filters": {
        "plugin_name": "SSH",  # Substring match, case-insensitive
        "cvss_base_score": ">=6.0"
    }
})

# 5. Get all data at once (no pagination, client's responsibility)
all_results = await mcp_client.call_tool("get_scan_results", {
    "task_id": task_id,
    "page": 0,  # Returns ALL data
    "filters": {"severity": "High"}
})
# Warning: Can be large! Client must handle size.

# 6. Download full native scan for semantic search indexing
native_file = await mcp_client.call_tool("download_native_scan", {"task_id": task_id})
# Index native_file['file_path'] into vector database for RAG queries

# 7. Review debug logs if enabled
if result.get("debug_mode"):
    # Scanner logs available at: data/tasks/{task_id}/scanner_logs/

# 8. Scan auto-deletes after 24h of no access (last_accessed_at + TTL)
```

---

## 14. Architecture Summary

This architecture provides a **simple, maintainable, and extensible foundation** for MCP-based vulnerability scanning optimized for multiagent systems.

### Key Highlights:

**✅ Three Scan Workflows** - Separate, clearly-defined workflows for untrusted (no creds), trusted non-privileged (SSH only), and trusted privileged (SSH + sudo/root)

**✅ Pluggable Scanner Interface** - Abstract `ScannerBackend` protocol allows adding OpenVAS, Qualys, or other scanners without touching MCP code

**✅ Scanner Instance Registry** - Pool management with automatic load balancing. 4-char instance hash in task IDs enables scanner traceability. `list_scanners()` tool for discovery.

**✅ Async Task Model** - Submit scan → get task_id → poll status → retrieve paginated/filtered results when complete

**✅ JSON-NL Pagination** - Schema negotiation (minimal/summary/brief/full/custom) with configurable page size. `page=0` returns all data (client's responsibility).

**✅ Generic Filtering** - LLM-friendly filtering on ANY schema attribute. AND logic, substring matching, comparison operators. Client LLM generates filters based on schema.

**✅ Shared State for Multi-Agent** - All agents see all scans, can collaborate by sharing task_ids. FIFO queue handles concurrent submissions.

**✅ Simple Storage** - Filesystem-based with unique task IDs. Native .nessus files stored locally for semantic search readiness. Scanner logs in dedicated directory (debug mode).

**✅ TTL Housekeeping** - Automatic cleanup based on `last_accessed_at + TTL` (default 24h). Hard delete, no recovery.

**✅ Separate Tools** - `run_untrusted_scan()`, `run_trusted_scan()`, `run_privileged_scan()`, `list_scanners()` for better LLM usability and type safety

**✅ Clean Code Organization** - `mcp-server/` directory separate from existing `scripts/`. Organized modules: scanners/, core/, schema/, tools/, tests/.

**✅ Docker Deployment** - HTTP server + background worker containers, integrates with existing Nessus docker-compose setup

**✅ Security** - Bearer token auth for MCP access, separate admin CLI for management tasks

The pluggable scanner interface with instance registry, generic filtering system, clear workflow separation, and flexible pagination design ensure the system remains performant, maintainable, and LLM-friendly while allowing future enhancements.
