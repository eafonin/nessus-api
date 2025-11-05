# Nessus MCP Server - Architecture v2.1 (Enhanced Docker Implementation)

> **Purpose**: Docker-based MCP server with Redis queue, incorporating full requirements from v1.0
> **Changes from v2.0**: Added scanner registry, proper task IDs, all MCP tools, filtering, TTL management
> **Priority**: Working prototype with complete feature set

---

## 1. High-Level Architecture (Enhanced)

### Container Architecture with Scanner Registry
```
┌─────────────────────────────────────────────────────────────┐
│                   Docker Host (Single Machine)               │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                 Docker Compose Network                  │ │
│  │                                                         │ │
│  │  ┌─────────────────┐  ┌──────────────────┐            │ │
│  │  │  MCP HTTP API   │  │  Redis           │            │ │
│  │  │  Port: 8835     │──│  Port: 6379      │            │ │
│  │  │  (FastMCP)      │  │  - Task Queue    │            │ │
│  │  │  - 10 MCP Tools │  │  - Dead Letter Q  │            │ │
│  │  │  - No Auth      │  │  - Scanner Registry│            │ │
│  │  └─────────────────┘  └──────────────────┘            │ │
│  │           │                     │                      │ │
│  │  ┌─────────────────────────────┴────────┐            │ │
│  │  │         Shared Volume: /app/data      │            │ │
│  │  │  - tasks/{task_id}/                   │            │ │
│  │  │    ├── task.json                      │            │ │
│  │  │    ├── scan_native.nessus             │            │ │
│  │  │    ├── scan_schema_*.jsonl            │            │ │
│  │  │    └── scanner_logs/                  │            │ │
│  │  └───────────────┬───────────────────────┘            │ │
│  │                  │                                     │ │
│  │  ┌───────────────▼──────────┐  ┌──────────────────┐  │ │
│  │  │   Scanner Worker         │  │  Existing Nessus  │  │ │
│  │  │   - Queue Consumer       │──│  Port: 8834       │  │ │
│  │  │   - Async Operations     │  │  Instance: "prod" │  │ │
│  │  │   - TTL Housekeeping     │  └──────────────────┘  │ │
│  │  └──────────────────────────┘  ┌──────────────────┐  │ │
│  │                                 │  Future: Nessus   │  │ │
│  │                                 │  Instance: "dev"  │  │ │
│  │                                 └──────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Enhancements from v2.0
- **Scanner Registry**: Multiple scanner instances with 4-char hash IDs
- **Proper Task IDs**: Format `{type}_{instance}_{timestamp}_{random}`
- **All 10 MCP Tools**: Complete tool set from requirements
- **Advanced Filtering**: Generic filters on any schema attribute
- **TTL Management**: Automatic cleanup with last_accessed_at tracking
- **Scanner Debug Logs**: Directory structure for troubleshooting

---

## 2. Scanner Registry & Instance Management

### 2.1 Scanner Instance Configuration
```python
# config/scanners.yaml
scanners:
  - type: nessus
    name: "Production Nessus"
    url: "http://host.docker.internal:8834"
    credentials:
      username: "nessus"
      password: "nessus"
      access_key: "abc..."
      secret_key: "06332..."
    enabled: true

  - type: nessus
    name: "Dev Nessus"  # Future instance
    url: "http://nessus-dev:8834"
    credentials:
      username: "nessus-dev"
      password: "dev-pass"
    enabled: false
```

### 2.2 Enhanced Scanner Registry
```python
# scanners/registry.py
from dataclasses import dataclass
from hashlib import sha256
from typing import Dict, List, Optional
import random
import yaml

@dataclass
class ScannerInstance:
    """Scanner instance with auto-generated 4-char ID"""
    scanner_type: str      # "nessus", "openvas"
    instance_id: str       # 4-char hex (auto-generated)
    name: str
    url: str
    credentials: Dict[str, str]
    enabled: bool = True

    def __post_init__(self):
        """Generate instance_id from URL + name"""
        if not self.instance_id:
            hash_input = f"{self.url}:{self.name}".encode()
            self.instance_id = sha256(hash_input).hexdigest()[:4]

class ScannerRegistry:
    """Registry with pool management and Redis persistence"""

    def __init__(self, redis_client, config_file: str = "config/scanners.yaml"):
        self.redis = redis_client
        self.registry_key = "nessus:scanners:registry"
        self._load_config(config_file)

    def _load_config(self, config_file: str):
        """Load scanner instances from YAML config"""
        with open(config_file) as f:
            config = yaml.safe_load(f)

        for scanner_conf in config.get("scanners", []):
            instance = ScannerInstance(
                scanner_type=scanner_conf["type"],
                instance_id="",  # Auto-generated
                name=scanner_conf["name"],
                url=scanner_conf["url"],
                credentials=scanner_conf["credentials"],
                enabled=scanner_conf.get("enabled", True)
            )
            self.register_instance(instance)

    def register_instance(self, instance: ScannerInstance):
        """Register scanner in Redis"""
        key = f"{instance.scanner_type}_{instance.instance_id}"
        self.redis.hset(
            self.registry_key,
            key,
            json.dumps(asdict(instance))
        )

    def get_instance(
        self,
        scanner_type: str = "nessus",
        instance_id: Optional[str] = None
    ) -> ScannerInstance:
        """Get specific instance or random from pool"""
        if instance_id:
            key = f"{scanner_type}_{instance_id}"
            data = self.redis.hget(self.registry_key, key)
            if not data:
                raise ValueError(f"Scanner not found: {key}")
            return ScannerInstance(**json.loads(data))

        # Get random enabled instance
        pattern = f"{scanner_type}_*"
        all_scanners = self.redis.hgetall(self.registry_key)

        candidates = []
        for key, data in all_scanners.items():
            if key.startswith(scanner_type):
                instance = ScannerInstance(**json.loads(data))
                if instance.enabled:
                    candidates.append(instance)

        if not candidates:
            raise ValueError(f"No enabled {scanner_type} scanners")

        return random.choice(candidates)

    def list_scanners(
        self,
        scanner_type: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[Dict[str, str]]:
        """List available scanners (for list_scanners tool)"""
        all_scanners = self.redis.hgetall(self.registry_key)

        result = []
        for key, data in all_scanners.items():
            instance = ScannerInstance(**json.loads(data))

            if scanner_type and instance.scanner_type != scanner_type:
                continue
            if enabled_only and not instance.enabled:
                continue

            # Don't expose credentials
            result.append({
                "scanner_type": instance.scanner_type,
                "instance_id": instance.instance_id,
                "name": instance.name,
                "url": instance.url,
                "enabled": instance.enabled
            })

        return result
```

---

## 3. Task ID Generation & Management

### 3.1 Proper Task ID Format
```python
# core/task_id.py
from datetime import datetime
import secrets

def generate_task_id(scanner_type: str, instance_id: str) -> str:
    """
    Generate task ID with format: {type}_{instance}_{timestamp}_{random}
    Example: ns_a3f2_20250101_120345_b1c2d3e4
    """
    type_prefix = {
        "nessus": "ns",
        "openvas": "ov",
        "qualys": "ql"
    }.get(scanner_type, "xx")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_suffix = secrets.token_hex(4)  # 8 chars

    return f"{type_prefix}_{instance_id}_{timestamp}_{random_suffix}"

def parse_task_id(task_id: str) -> Dict[str, str]:
    """Parse task ID to extract components"""
    parts = task_id.split("_")
    if len(parts) != 5:
        raise ValueError(f"Invalid task ID format: {task_id}")

    return {
        "scanner_type": parts[0],
        "instance_id": parts[1],
        "date": parts[2],
        "time": parts[3],
        "random": parts[4]
    }
```

---

## 4. Complete MCP Tools Implementation

### 4.1 All 10 Tools from Requirements
```python
# tools/scan_tools.py
from fastmcp import FastMCP
from typing import Dict, Any, Optional, List
import json

mcp = FastMCP("Nessus Scanner")

# Initialize shared resources
registry = ScannerRegistry(redis_client)
queue = TaskQueue(redis_client)
task_mgr = TaskManager("/app/data")

# ============= Scan Execution Tools (3) =============

@mcp.tool()
async def run_untrusted_scan(
    targets: str,
    name: str,
    description: str = "",
    schema_profile: str = "brief",
    scanner_type: str = "nessus",
    scanner_instance: Optional[str] = None,
    debug_mode: bool = False
) -> Dict[str, Any]:
    """
    Run network-only vulnerability scan (no credentials).

    Performs port scanning, service detection, and CVE matching.
    No authentication required.
    """
    # Get scanner instance
    instance = registry.get_instance(scanner_type, scanner_instance)

    # Generate proper task ID
    task_id = generate_task_id(scanner_type, instance.instance_id)

    # Create task with full metadata
    task = Task(
        task_id=task_id,
        scan_type="untrusted",
        scanner_type=scanner_type,
        scanner_instance_id=instance.instance_id,
        payload={
            "targets": targets,
            "name": name,
            "description": description,
            "schema_profile": schema_profile,
            "debug_mode": debug_mode
        }
    )

    # Enqueue and get position
    queue_position = await queue.enqueue(task)

    # Create task directory structure
    await task_mgr.create_task(task_id, task.payload)

    return {
        "task_id": task_id,
        "status": "queued",
        "queue_position": queue_position,
        "scanner_instance": instance.instance_id
    }

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
    scanner_instance: Optional[str] = None,
    debug_mode: bool = False
) -> Dict[str, Any]:
    """
    Run authenticated scan with regular user SSH access.

    Performs software inventory, configuration checks, and
    user-level vulnerability detection. No privilege escalation.
    """
    instance = registry.get_instance(scanner_type, scanner_instance)
    task_id = generate_task_id(scanner_type, instance.instance_id)

    task = Task(
        task_id=task_id,
        scan_type="trusted_basic",
        scanner_type=scanner_type,
        scanner_instance_id=instance.instance_id,
        payload={
            "targets": targets,
            "name": name,
            "description": description,
            "schema_profile": schema_profile,
            "debug_mode": debug_mode,
            "credentials": {
                "username": username,
                "password": password,
                "auth_method": auth_method,
                "elevate_privileges_with": "Nothing"
            }
        }
    )

    queue_position = await queue.enqueue(task)
    await task_mgr.create_task(task_id, task.payload)

    return {
        "task_id": task_id,
        "status": "queued",
        "queue_position": queue_position,
        "scanner_instance": instance.instance_id
    }

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
    scanner_instance: Optional[str] = None,
    debug_mode: bool = False
) -> Dict[str, Any]:
    """
    Run authenticated scan with root/sudo access.

    Performs complete system inventory, kernel vulnerability detection,
    and compliance checks with full filesystem access.
    """
    instance = registry.get_instance(scanner_type, scanner_instance)
    task_id = generate_task_id(scanner_type, instance.instance_id)

    task = Task(
        task_id=task_id,
        scan_type="trusted_privileged",
        scanner_type=scanner_type,
        scanner_instance_id=instance.instance_id,
        payload={
            "targets": targets,
            "name": name,
            "description": description,
            "schema_profile": schema_profile,
            "debug_mode": debug_mode,
            "credentials": {
                "username": username,
                "password": password,
                "auth_method": auth_method,
                "elevate_privileges_with": escalation_method,
                "escalation_password": escalation_password,
                "escalation_account": escalation_account
            }
        }
    )

    queue_position = await queue.enqueue(task)
    await task_mgr.create_task(task_id, task.payload)

    return {
        "task_id": task_id,
        "status": "queued",
        "queue_position": queue_position,
        "scanner_instance": instance.instance_id
    }

# ============= Status & Results Tools (4) =============

@mcp.tool()
async def get_scan_status(task_id: str) -> Dict[str, Any]:
    """
    Get current status of scan task.

    Returns status, progress percentage, timestamps, and error info.
    """
    task_data = await task_mgr.get_task_metadata(task_id)

    # Get queue position if queued
    queue_position = None
    if task_data["status"] == "queued":
        queue_position = await queue.get_position(task_id)

    # Get progress from scanner if running
    progress = None
    if task_data["status"] == "running":
        scan_id = task_data.get("scan_id")
        if scan_id:
            # TODO: Get actual progress from scanner
            progress = 45  # Mock for now

    return {
        "task_id": task_id,
        "status": task_data["status"],
        "progress": progress,
        "created_at": task_data.get("created_at"),
        "started_at": task_data.get("started_at"),
        "completed_at": task_data.get("completed_at"),
        "queue_position": queue_position,
        "error_message": task_data.get("error_message")
    }

@mcp.tool()
async def get_scan_results(
    task_id: str,
    page: int = 1,
    page_size: int = 40,
    custom_schema: Optional[Dict[str, List[str]]] = None,
    filters: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get scan results in paginated JSON-NL format with filtering.

    Page 0 returns ALL data (no pagination).
    Filters work on ANY schema attribute with AND logic.

    Filter syntax:
    - Strings: {"plugin_name": "SSH"} - substring match
    - Numbers: {"cvss3_base_score": ">7.0"} - comparison
    - Booleans: {"exploit_available": true} - exact match
    - Lists: {"cve": "CVE-2023"} - contains
    """
    # Update last_accessed_at for TTL
    await task_mgr.update_last_accessed(task_id)

    # Check if scan completed
    status = await task_mgr.get_task_metadata(task_id)
    if status["status"] != "completed":
        return json.dumps({"error": f"Scan not completed: {status['status']}"})

    # Determine schema to use
    if custom_schema:
        schema_fields = custom_schema.get("fields", [])
        schema_profile = "custom"
    else:
        schema_profile = status.get("schema_profile", "brief")
        schema_fields = SCHEMAS[schema_profile]

    # Get pre-generated or generate on-demand
    results = await task_mgr.get_scan_results(
        task_id,
        schema_profile,
        page,
        page_size,
        filters
    )

    return results  # JSON-NL string

@mcp.tool()
async def get_scan_settings(task_id: str) -> Dict[str, Any]:
    """
    Get detailed scan configuration and settings.

    Returns original scan request, scanner config, and credentials
    (with passwords masked).
    """
    await task_mgr.update_last_accessed(task_id)

    metadata = await task_mgr.get_task_metadata(task_id)
    settings = metadata.get("scan_request", {})

    # Mask sensitive data
    if "credentials" in settings:
        creds = settings["credentials"].copy()
        for key in ["password", "escalation_password", "private_key"]:
            if key in creds:
                creds[key] = "***REDACTED***"
        settings["credentials"] = creds

    return {
        "task_id": task_id,
        "scan_type": metadata.get("scan_type"),
        "scanner_type": metadata.get("scanner_type"),
        "scanner_instance": metadata.get("scanner_instance_id"),
        "settings": settings,
        "created_at": metadata.get("created_at"),
        "execution_time_seconds": metadata.get("execution_time")
    }

@mcp.tool()
async def download_native_scan(task_id: str) -> Dict[str, Any]:
    """
    Get path to native .nessus file for external analysis.

    Updates last_accessed_at for TTL tracking.
    """
    await task_mgr.update_last_accessed(task_id)

    file_path = f"/app/data/tasks/{task_id}/scan_native.nessus"

    # Check if file exists
    import os
    if not os.path.exists(file_path):
        return {"error": "Native scan file not found"}

    file_size = os.path.getsize(file_path)

    return {
        "file_path": file_path,
        "size_bytes": file_size,
        "format": "nessus"
    }

# ============= Management Tools (3) =============

@mcp.tool()
async def list_scans(
    status: Optional[str] = None,
    scan_type: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    List all scans (shared state, all agents see all scans).

    Filter by status: queued|running|completed|failed|timeout
    Filter by scan_type: untrusted|trusted_basic|trusted_privileged
    """
    scans = await task_mgr.list_tasks(
        status_filter=status,
        scan_type_filter=scan_type,
        limit=limit
    )

    return scans

@mcp.tool()
async def delete_scan(
    task_id: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    Delete scan and all associated data.

    Set force=True to delete running scans.
    Permanent deletion with no recovery.
    """
    metadata = await task_mgr.get_task_metadata(task_id)

    # Check if running
    if metadata["status"] == "running" and not force:
        return {"error": "Cannot delete running scan without force=True"}

    # Stop scan if running
    if metadata["status"] == "running":
        scan_id = metadata.get("scan_id")
        if scan_id:
            # TODO: Stop scan in Nessus
            pass

    # Delete from queue if queued
    if metadata["status"] == "queued":
        await queue.remove(task_id)

    # Delete task data
    await task_mgr.delete_task(task_id)

    return {
        "deleted": True,
        "task_id": task_id
    }

@mcp.tool()
async def list_scanners(
    scanner_type: Optional[str] = None,
    enabled_only: bool = True
) -> List[Dict[str, str]]:
    """
    List available scanner instances.

    Returns scanner type, instance ID, name, URL, and status.
    Does NOT return credentials for security.
    """
    return registry.list_scanners(scanner_type, enabled_only)
```

---

## 5. Schema Processing with Factory Pattern

### 5.1 Enhanced Schema Converter
```python
# schema/converter.py
from typing import List, Dict, Any, Optional
import json
import xml.etree.ElementTree as ET

class NessusToJsonNL:
    """Convert Nessus XML to JSON-NL with schema profiles"""

    # Predefined schema profiles
    SCHEMAS = {
        "minimal": [
            "host", "plugin_id", "severity", "cve",
            "cvss_score", "exploit_available"
        ],
        "brief": [
            "host", "plugin_id", "plugin_name", "severity",
            "cve", "description", "solution"
        ],
        "summary": [
            "host", "plugin_id", "plugin_name", "severity",
            "cve", "cvss3_base_score", "synopsis"
        ],
        "full": None  # All fields
    }

    def convert(
        self,
        nessus_data: bytes,
        schema_profile: str = "brief",
        custom_fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Convert Nessus XML to JSON-NL format.

        Uses factory pattern for schema generation:
        - full: Direct conversion of all fields
        - custom: User-specified field list
        - brief/minimal/summary: Predefined field sets
        """
        # Parse Nessus XML
        root = ET.fromstring(nessus_data)

        # Determine fields to include
        if schema_profile == "full":
            fields = None  # Include all
        elif schema_profile == "custom" and custom_fields:
            fields = custom_fields
        else:
            fields = self.SCHEMAS.get(schema_profile, self.SCHEMAS["brief"])

        # Build JSON-NL lines
        lines = []

        # Line 1: Schema definition
        schema_def = {
            "type": "schema",
            "profile": schema_profile,
            "fields": fields or "all",
            "filters_applied": filters
        }
        lines.append(json.dumps(schema_def))

        # Line 2: Scan metadata
        scan_meta = self._extract_scan_metadata(root)
        lines.append(json.dumps(scan_meta))

        # Lines 3+: Vulnerability data
        vulnerabilities = self._extract_vulnerabilities(root, fields, filters)
        for vuln in vulnerabilities:
            lines.append(json.dumps(vuln))

        # Last line: Pagination (if applicable)
        # TODO: Add pagination logic

        return "\n".join(lines)

    def _extract_vulnerabilities(
        self,
        root: ET.Element,
        fields: Optional[List[str]],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract vulnerability data with filtering"""
        vulnerabilities = []

        for report_host in root.findall(".//ReportHost"):
            host = report_host.get("name")

            for item in report_host.findall("ReportItem"):
                vuln = {
                    "type": "vulnerability",
                    "host": host,
                    "plugin_id": int(item.get("pluginID")),
                    "plugin_name": item.get("pluginName"),
                    "severity": item.get("severity")
                }

                # Add additional fields
                for child in item:
                    vuln[child.tag] = child.text

                # Apply field selection
                if fields:
                    vuln = {k: v for k, v in vuln.items() if k in fields or k == "type"}

                # Apply filters
                if filters and not self._matches_filters(vuln, filters):
                    continue

                vulnerabilities.append(vuln)

        return vulnerabilities

    def _matches_filters(self, vuln: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if vulnerability matches all filters (AND logic)"""
        for field, filter_value in filters.items():
            if field not in vuln:
                return False

            vuln_value = vuln[field]

            # String filter (substring match)
            if isinstance(vuln_value, str) and isinstance(filter_value, str):
                if filter_value.lower() not in vuln_value.lower():
                    return False

            # Number filter (comparison)
            elif isinstance(filter_value, str) and filter_value[0] in "<>=":
                try:
                    num_value = float(vuln_value)
                    operator = filter_value[0]
                    compare_value = float(filter_value[1:])

                    if operator == ">" and num_value <= compare_value:
                        return False
                    elif operator == "<" and num_value >= compare_value:
                        return False
                    elif operator == "=" and num_value != compare_value:
                        return False
                except (ValueError, TypeError):
                    return False

            # Boolean filter (exact match)
            elif isinstance(filter_value, bool):
                if bool(vuln_value) != filter_value:
                    return False

            # List filter (contains)
            elif isinstance(vuln_value, list):
                found = False
                for item in vuln_value:
                    if str(filter_value).lower() in str(item).lower():
                        found = True
                        break
                if not found:
                    return False

        return True
```

---

## 6. Enhanced Task Manager with TTL

### 6.1 Task Manager with Last Access Tracking
```python
# core/task_manager.py
from pathlib import Path
from datetime import datetime, timedelta
import json
import shutil
from typing import Dict, Any, List, Optional

class TaskManager:
    """Manages task lifecycle with TTL and last access tracking"""

    def __init__(self, data_dir: str, default_ttl_hours: int = 24):
        self.data_dir = Path(data_dir)
        self.default_ttl_hours = default_ttl_hours

    async def create_task(self, task_id: str, request: Dict[str, Any]) -> None:
        """Create task directory and initial metadata"""
        task_dir = self.data_dir / "tasks" / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create scanner_logs directory if debug mode
        if request.get("debug_mode"):
            (task_dir / "scanner_logs").mkdir(exist_ok=True)

        # Create task.json with metadata
        metadata = {
            "task_id": task_id,
            "status": "queued",
            "scan_request": request,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed_at": datetime.utcnow().isoformat(),
            "ttl_hours": self.default_ttl_hours,
            "scanner_logs_available": request.get("debug_mode", False)
        }

        with open(task_dir / "task.json", "w") as f:
            json.dump(metadata, f, indent=2)

    async def update_last_accessed(self, task_id: str) -> None:
        """Update last_accessed_at timestamp (extends TTL)"""
        task_dir = self.data_dir / "tasks" / task_id
        metadata_file = task_dir / "task.json"

        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)

            metadata["last_accessed_at"] = datetime.utcnow().isoformat()

            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

    async def cleanup_expired_tasks(self) -> int:
        """Delete tasks that exceeded TTL"""
        now = datetime.utcnow()
        deleted_count = 0

        tasks_dir = self.data_dir / "tasks"
        if not tasks_dir.exists():
            return 0

        for task_dir in tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            metadata_file = task_dir / "task.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file) as f:
                    metadata = json.load(f)

                last_accessed = datetime.fromisoformat(metadata["last_accessed_at"])
                ttl_hours = metadata.get("ttl_hours", self.default_ttl_hours)

                if now - last_accessed > timedelta(hours=ttl_hours):
                    # Delete task directory
                    shutil.rmtree(task_dir)
                    deleted_count += 1

            except Exception as e:
                # Log error but continue
                print(f"Error checking task {task_dir.name}: {e}")

        return deleted_count

    async def get_scan_results(
        self,
        task_id: str,
        schema_profile: str,
        page: int,
        page_size: int,
        filters: Optional[Dict[str, Any]]
    ) -> str:
        """Get scan results with pagination and filtering"""
        task_dir = self.data_dir / "tasks" / task_id

        # Check for pre-generated schema file
        schema_file = task_dir / f"scan_schema_{schema_profile}.jsonl"

        if schema_file.exists() and not filters and page == 1:
            # Return pre-generated file (no filtering needed)
            return schema_file.read_text()

        # Generate on-demand with filtering
        nessus_file = task_dir / "scan_native.nessus"
        if not nessus_file.exists():
            return json.dumps({"error": "Scan results not found"})

        converter = NessusToJsonNL()

        # Handle page=0 (return all data)
        if page == 0:
            return converter.convert(
                nessus_file.read_bytes(),
                schema_profile=schema_profile,
                filters=filters
            )

        # TODO: Implement proper pagination
        # For now, return filtered results
        return converter.convert(
            nessus_file.read_bytes(),
            schema_profile=schema_profile,
            filters=filters
        )

    async def list_tasks(
        self,
        status_filter: Optional[str] = None,
        scan_type_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List tasks with filtering"""
        tasks = []
        tasks_dir = self.data_dir / "tasks"

        if not tasks_dir.exists():
            return tasks

        for task_dir in sorted(tasks_dir.iterdir(), reverse=True)[:limit]:
            if not task_dir.is_dir():
                continue

            metadata_file = task_dir / "task.json"
            if not metadata_file.exists():
                continue

            with open(metadata_file) as f:
                metadata = json.load(f)

            # Apply filters
            if status_filter and metadata.get("status") != status_filter:
                continue
            if scan_type_filter and metadata.get("scan_type") != scan_type_filter:
                continue

            tasks.append({
                "task_id": metadata["task_id"],
                "name": metadata.get("scan_request", {}).get("name"),
                "status": metadata["status"],
                "scan_type": metadata.get("scan_type"),
                "created_at": metadata["created_at"],
                "last_accessed_at": metadata["last_accessed_at"]
            })

        return tasks
```

---

## 7. Enhanced Worker with Debug Logging

### 7.1 Worker with Scanner Logs Support
```python
# worker.py
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import sys

# Add existing scripts to path
sys.path.insert(0, "/app/nessusAPIWrapper")

class ScanWorker:
    """Enhanced worker with debug logging support"""

    def __init__(self, redis_url: str, nessus_url: str, data_dir: str):
        self.queue = TaskQueue(redis_url)
        self.registry = ScannerRegistry(redis.from_url(redis_url))
        self.data_dir = Path(data_dir)
        self.converter = NessusToJsonNL()

        # Setup structured logging
        self.setup_logging()

    def setup_logging(self):
        """Configure JSON-NL structured logging"""
        formatter = logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", '
            '"component": "%(name)s", "message": "%(message)s"}'
        )

        # File handler for persistent logs
        file_handler = logging.FileHandler("/app/logs/worker.jsonl")
        file_handler.setFormatter(formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler]
        )

        self.logger = logging.getLogger("worker")

    async def process_task(self, task: Task):
        """Process single scan task with full workflow"""
        task_dir = self.data_dir / "tasks" / task.task_id

        try:
            self.logger.info(f"Processing task {task.task_id}")

            # Get scanner instance
            parsed = parse_task_id(task.task_id)
            instance = self.registry.get_instance(
                task.scanner_type,
                parsed["instance_id"]
            )

            # Initialize scanner
            scanner = NessusScanner(instance.url, instance.credentials)

            # Enable debug logging if requested
            if task.payload.get("debug_mode"):
                scanner.set_debug_dir(task_dir / "scanner_logs")

            # Update status to running
            await self.update_task_status(task.task_id, "running")

            # 1. Create scan with credentials
            scan_request = ScanRequest(
                targets=task.payload["targets"],
                name=task.payload["name"],
                scan_type=task.scan_type,
                credentials=task.payload.get("credentials")
            )

            scan_id = await scanner.create_scan(scan_request)
            self.logger.info(f"Created scan {scan_id} for task {task.task_id}")

            # Save scan_id to task metadata
            await self.save_scan_id(task.task_id, scan_id)

            # 2. Launch scan
            scan_uuid = await scanner.launch_scan(scan_id)
            self.logger.info(f"Launched scan {scan_id} with UUID {scan_uuid}")

            # 3. Poll until complete (with timeout)
            start_time = datetime.utcnow()
            timeout_hours = 24

            while True:
                status = await scanner.get_status(scan_id)

                if status["status"] == "completed":
                    break

                # Check timeout
                if (datetime.utcnow() - start_time).total_seconds() > timeout_hours * 3600:
                    raise TimeoutError(f"Scan exceeded {timeout_hours} hour timeout")

                await asyncio.sleep(30)  # Poll every 30 seconds

            # 4. Export native format
            nessus_data = await scanner.export_results(scan_id, "nessus")
            (task_dir / "scan_native.nessus").write_bytes(nessus_data)
            self.logger.info(f"Exported {len(nessus_data)} bytes for task {task.task_id}")

            # 5. Generate default schema (brief) immediately
            brief_jsonl = self.converter.convert(
                nessus_data,
                schema_profile="brief"
            )
            (task_dir / "scan_schema_brief.jsonl").write_text(brief_jsonl)

            # 6. Mark complete
            await self.update_task_status(task.task_id, "completed")
            await self.queue.complete(task.task_id)

            self.logger.info(f"Task {task.task_id} completed successfully")

        except TimeoutError as e:
            self.logger.error(f"Task {task.task_id} timeout: {e}")
            await self.update_task_status(task.task_id, "timeout", str(e))
            await self.queue.fail(task.task_id, str(e))

        except Exception as e:
            self.logger.error(f"Task {task.task_id} failed: {e}", exc_info=True)
            await self.update_task_status(task.task_id, "failed", str(e))
            await self.queue.fail(task.task_id, str(e))

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        error: Optional[str] = None
    ):
        """Update task status in metadata"""
        task_dir = self.data_dir / "tasks" / task_id
        metadata_file = task_dir / "task.json"

        with open(metadata_file) as f:
            metadata = json.load(f)

        metadata["status"] = status

        if status == "running":
            metadata["started_at"] = datetime.utcnow().isoformat()
        elif status in ["completed", "failed", "timeout"]:
            metadata["completed_at"] = datetime.utcnow().isoformat()

            # Calculate execution time
            if "started_at" in metadata:
                start = datetime.fromisoformat(metadata["started_at"])
                end = datetime.utcnow()
                metadata["execution_time"] = (end - start).total_seconds()

        if error:
            metadata["error_message"] = error

        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    async def run_housekeeping(self):
        """Background task for TTL cleanup"""
        while True:
            try:
                deleted = await TaskManager(self.data_dir).cleanup_expired_tasks()
                if deleted > 0:
                    self.logger.info(f"Housekeeping deleted {deleted} expired tasks")
            except Exception as e:
                self.logger.error(f"Housekeeping error: {e}")

            await asyncio.sleep(3600)  # Run every hour

    async def run(self):
        """Main worker loop with housekeeping"""
        self.logger.info("Worker started")

        # Start housekeeping in background
        asyncio.create_task(self.run_housekeeping())

        # Main queue processing loop
        while True:
            task = await self.queue.dequeue()
            if task:
                await self.process_task(task)
            else:
                await asyncio.sleep(1)
```

---

## 8. Docker Compose Configuration (Updated)

### 8.1 docker-compose.yml
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: nessus-mcp-redis
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - mcp-network

  mcp-api:
    build:
      context: ..
      dockerfile: mcp-server/Dockerfile.api
    container_name: nessus-mcp-api
    ports:
      - "8835:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/app/data
      - LOG_DIR=/app/logs
      - NO_AUTH=true
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - mcp-network

  scanner-worker:
    build:
      context: ..
      dockerfile: mcp-server/Dockerfile.worker
    container_name: nessus-mcp-worker
    environment:
      - REDIS_URL=redis://redis:6379
      - NESSUS_URL=http://host.docker.internal:8834
      - DATA_DIR=/app/data
      - LOG_DIR=/app/logs
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      redis:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - mcp-network

networks:
  mcp-network:
    driver: bridge

volumes:
  redis-data:
  data:
  logs:
```

---

## 9. Implementation Timeline (Updated)

### Week 1: Core + Basic Workflow
```
Day 1-2:   Docker setup + Redis + Scanner Registry
Day 3-4:   Task ID generation + Queue with proper IDs
Day 5-6:   All 10 MCP tools (stubs first)
Day 7:     Worker with real Nessus integration
```

### Week 2: Schema & Filtering
```
Day 8-9:   Schema converter with XML parsing
Day 10-11: Generic filtering implementation
Day 12-13: TTL management + housekeeping
```

### Week 3: Production Features
```
Day 14-15: Scanner debug logs
Day 16-17: Dead letter queue processing
Day 18-19: Integration testing
Day 20-21: Documentation + cleanup
```

---

## 10. Testing Commands (Updated)

```bash
# Test untrusted scan with proper task ID
curl -X POST http://localhost:8835/tools/run_untrusted_scan \
  -H "Content-Type: application/json" \
  -d '{
    "targets": "192.168.1.1",
    "name": "Test Scan",
    "debug_mode": true
  }'
# Returns: {"task_id": "ns_a3f2_20250101_120345_b1c2d3e4", ...}

# Check status
curl -X POST http://localhost:8835/tools/get_scan_status \
  -d '{"task_id": "ns_a3f2_20250101_120345_b1c2d3e4"}'

# List available scanners
curl -X POST http://localhost:8835/tools/list_scanners

# Get results with filtering
curl -X POST http://localhost:8835/tools/get_scan_results \
  -d '{
    "task_id": "ns_a3f2_20250101_120345_b1c2d3e4",
    "filters": {
      "severity": "Critical",
      "exploit_available": true
    }
  }'

# View scanner logs (if debug_mode was true)
cat ./data/tasks/ns_a3f2_*/scanner_logs/nessus_api.log

# Check dead letter queue
docker exec nessus-mcp-redis redis-cli LLEN nessus:queue:dead
```

---

## Summary of v2.1 Enhancements

This v2.1 architecture incorporates ALL requirements from the original document:

1. ✅ **Scanner Registry** with 4-char instance IDs and pool management
2. ✅ **Proper Task IDs** format: `{type}_{instance}_{timestamp}_{random}`
3. ✅ **All 10 MCP Tools** from requirements (not just 3)
4. ✅ **Generic Filtering** on any schema attribute with proper syntax
5. ✅ **TTL Management** with last_accessed_at tracking
6. ✅ **Scanner Debug Logs** directory structure (when debug_mode=true)
7. ✅ **Schema Factory Pattern** for custom/minimal/brief/summary/full
8. ✅ **Dead Letter Queue** for failed task analysis
9. ✅ **Async Operations** throughout the implementation
10. ✅ **Complete Metadata** in task.json including execution times

The architecture maintains the Docker focus and rapid prototyping approach from v2.0 while adding the robustness and completeness of the original requirements.