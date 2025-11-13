# Nessus MCP Server - Requirements Document

> **Version:** 2.2 (aligned with ARCHITECTURE_v2.2.md)
> **Date:** 2025-11-01
> **Status:** Approved for Implementation

---

## 1. Project Overview

### 1.1 Purpose
Build an MCP (Model Context Protocol) server that provides vulnerability scanning capabilities to a multi-agent system, wrapping the existing Nessus scanner infrastructure with an LLM-friendly API.

### 1.2 Goals
- Enable autonomous agents to request and manage vulnerability scans
- Provide flexible, paginated, filterable scan results optimized for LLM consumption
- Support multiple scanning privilege levels (untrusted, trusted, privileged)
- Abstract scanner implementation to support multiple scanner types (Nessus, OpenVAS, etc.)
- Maintain simple, maintainable code architecture

### 1.3 Related Documents
- **Architecture Design**: [`ARCHITECTURE_v2.2.md`](./ARCHITECTURE_v2.2.md) (same directory)
- **Implementation Guide**: [`archive/IMPLEMENTATION_GUIDE.md`](./archive/IMPLEMENTATION_GUIDE.md)
- **Existing Codebase Index**: [`../nessusAPIWrapper/CODEBASE_INDEX.md`](../nessusAPIWrapper/CODEBASE_INDEX.md)
- **FastMCP Documentation**: [`../docs/fastMCPServer/INDEX.md`](../docs/fastMCPServer/INDEX.md)
- **Existing Scripts directory**: [`../nessusAPIWrapper/`](../nessusAPIWrapper/)

---

## 2. System Context

### 2.1 Deployment Environment
- **Client**: FastAPI-based multi-agent system with OpenRouter LLM backend
- **Scanner**: Existing Nessus Docker container (VPN gateway + Nessus Pro)
- **Docker Compose**: See `/home/nessus/docker/nessus/docker-compose.yml` (external to project)
- **Network**: Containerized services on `nessus_net` bridge network
- **MCP Server**: New HTTP service deployed alongside existing Nessus infrastructure

### 2.2 Existing Infrastructure
The MCP server wraps existing Python automation scripts:
- `nessusAPIWrapper/manage_scans.py` - Scan creation/deletion
- `nessusAPIWrapper/manage_credentials.py` - SSH credential management
- `nessusAPIWrapper/launch_scan.py` - Scan execution control
- `nessusAPIWrapper/export_vulnerabilities_detailed.py` - Result export
- See [`../nessusAPIWrapper/CODEBASE_INDEX.md`](../nessusAPIWrapper/CODEBASE_INDEX.md) for complete script inventory

---

## 3. Core Functional Requirements

### 3.1 Three Scan Workflows

#### FR-1.1: Untrusted Scan (Network-Only)
**Description**: Perform unauthenticated vulnerability scanning
**Capabilities**:
- Port scanning and service detection
- Banner grabbing and version identification
- CVE matching based on detected versions
- No authenticated checks, no credentials required

**Acceptance Criteria**:
- Agent can submit scan with only targets and name
- Results include network-level vulnerabilities only
- Scan completes without SSH/authentication attempts

#### FR-1.2: Trusted Non-Privileged Scan
**Description**: Authenticated scanning with regular user SSH access
**Capabilities**:
- Software inventory and version detection
- Configuration file analysis (user-accessible files only)
- Process enumeration
- User-level vulnerability checks
- No privilege escalation

**Acceptance Criteria**:
- Agent provides SSH credentials (username/password)
- Scanner authenticates but does not attempt privilege escalation
- Results include authenticated checks without root-level findings

#### FR-1.3: Trusted Privileged Scan
**Description**: Deep authenticated scanning with root/sudo access
**Capabilities**:
- Complete system inventory
- Kernel vulnerability detection
- System-wide configuration audits
- All installed packages and services
- Compliance policy checks
- Full filesystem access

**Acceptance Criteria**:
- Agent provides SSH credentials + escalation method (sudo/su/pbrun)
- Scanner successfully escalates to root or specified privileged account
- Results include complete system vulnerability assessment

**Special Case**: Sometimes root user directly (sudo as option), no separate user account

---

### 3.2 Scanner Management

#### FR-2.1: Pluggable Scanner Architecture
**Description**: Support multiple scanner types and instances
**Requirements**:
- Abstract scanner interface (`ScannerBackend` protocol)
- Scanner registry with instance management
- 4-character hash instance IDs (derived from URL + name)
- Support for scanner pools (multiple instances of same type)
- Random load balancing when no specific instance requested

**Acceptance Criteria**:
- Can register multiple Nessus instances (e.g., "Production Nessus", "Dev Nessus")
- Future: Can add OpenVAS, Qualys, or custom scanner implementations
- Task IDs include scanner type and instance ID for traceability
- Format: `{type}_{instance}_{timestamp}_{random}` (e.g., `ns_a3f2_20250101_120345_b1c2d3e4`)

#### FR-2.2: Scanner Discovery
**Description**: Agents can list available scanner instances
**Tool**: `list_scanners(scanner_type, enabled_only)`
**Returns**:
- Scanner type, instance ID, name, URL, enabled status
- Does NOT return credentials (security)

**Acceptance Criteria**:
- Agent can discover all registered scanners before submitting scan
- Can filter by scanner type
- Can see only enabled scanners

---

### 3.3 Async Task Management

#### FR-3.1: Task Submission
**Description**: Non-blocking scan submission with task ID
**Workflow**:
1. Agent calls `run_*_scan()` tool
2. MCP server enqueues scan task
3. Returns immediately with: `{"task_id": "...", "status": "queued", "queue_position": N, "scanner_instance": "..."}`

**Acceptance Criteria**:
- Scan submission completes in <1 second regardless of scan duration
- Task ID is unique and includes scanner instance information
- Queue position indicates number of scans ahead
- Scan creation is async by default (like "async with httpx.AsyncClient() as client: \response = await client.post") so MCP server can perform several tasks concurrently

#### FR-3.2: Task Status Polling
**Description**: Monitor long-running scans
**Tool**: `get_scan_status(task_id)`
**Returns**: Status (queued|running|completed|failed|timeout), progress %, timestamps, queue position (if queued), error message (if failed)

**Acceptance Criteria**:
- Agent can poll at any time without affecting scan
- Progress percentage available when scanner provides it
- Status reflects actual Nessus scan state

#### FR-3.3: Task Queue (FIFO)
**Description**: Serialize scan execution to prevent scanner overload
**Requirements**:
- Simple FIFO queue (Redis-based, key: `nessus:queue`)
- Single background worker processes queue sequentially
- Multiple agents can submit concurrently (queue handles serialization)
- Redis LPUSH/BRPOP for atomic queue operations
- Dead Letter Queue (DLQ) for failed tasks (Redis sorted set: `nessus:queue:dead`)

**Acceptance Criteria**:
- Multiple agents can submit scans simultaneously
- Queue persists across MCP server restarts
- Failed tasks moved to DLQ for manual inspection

#### FR-3.4: Scan Timeout
**Description**: Automatically fail scans exceeding maximum duration
**Limit**: 24 hours
**Action**: Mark scan as "timeout" status, stop scanner, clean up

**Acceptance Criteria**:
- Scans running >24 hours automatically marked as failed
- Nessus scan stopped via API
- Agent receives timeout status on next poll

---

### 3.4 Result Retrieval & Schema Negotiation

#### FR-4.1: Schema Profiles (Predefined)
**Description**: Four standard output schemas plus custom mode
**Profiles**:
- **minimal**: 6 core fields: `host, plugin_id, severity, cve, cvss_score, exploit_available`
- **summary**: minimal + 3 additional fields: `plugin_name, cvss3_base_score, synopsis`
- **brief** (default): summary + 2 more fields: `description, solution`
- **full**: All fields from Nessus detailed export (no field filtering)

**Custom Mode**:
- **custom**: Agent provides explicit field list via `custom_fields` parameter
- Mutually exclusive with `schema_profile` (cannot specify both)
- Allows arbitrary field selection from Nessus export

**Acceptance Criteria**:
- Agent specifies profile in scan request: `schema_profile="minimal"` | `"summary"` | `"brief"` | `"full"`
- Agent can use custom mode: `custom_fields=["host", "cve", "cvss3_base_score"]`
- **API rejects with 400 error if both `schema_profile` and `custom_fields` are provided**
- Results include only requested fields
- Scan configuration settings included as a JSON object
- Vulnerability schema definition included in first line of JSON-NL output
- Schema line echoes applied filters for LLM reasoning: `"filters_applied": {...}`

#### FR-4.2: Custom Schema Definition
**Description**: Agent provides custom field list
**Format**: `custom_fields=["host", "cve", "cvss3_base_score", ...]`
**Exclusivity**: Mutually exclusive with `schema_profile` - API rejects if both provided

**Acceptance Criteria**:
- Agent can specify arbitrary field list
- Only requested fields returned
- Works with any field available in Nessus export

#### FR-4.3: Natural Language Schema (Placeholder)
**Description**: Future capability for LLM-generated schema
**Format**: `natural_language_desc="Give me only critical CVEs with exploit availability"`
**Status**: Placeholder in API, not implemented in Phase 1

**Acceptance Criteria** (Future):
- Accept natural language string
- Use LLM to generate field list
- Translate to standard schema format

---

### 3.5 Pagination & Data Delivery

#### FR-5.1: Paginated Results
**Description**: Return results in configurable page sizes
**Default**: 40 lines per page
**Range**: 10-100 lines per page
**Format**: JSON-NL (one JSON object per line)

**JSON-NL Structure**:
```
Line 1: {"type": "schema", "profile": "...", "fields": [...], "total_vulnerabilities": N, "total_pages": M}
Line 2: {"type": "scan_metadata", "task_id": "...", "scan_name": "...", "started_at": "...", ...}
Lines 3+: {"type": "vulnerability", "host": "...", "plugin_id": 123, ...}
Last line: {"type": "pagination", "page": 1, "total_pages": M, "next_page_token": "..."}
```

**Acceptance Criteria**:
- Each line is valid, standalone JSON
- Page size configurable by agent
- Pagination info includes total counts

#### FR-5.2: Complete Data Retrieval (page=0)
**Description**: Return ALL scan data in single response
**Trigger**: `page=0` parameter
**Behavior**: No pagination, return complete dataset

**Important**:
- **No size limit** - Client's responsibility to handle large responses
- May be megabytes in size
- Use only when agent explicitly needs complete dataset

**Acceptance Criteria**:
- `page=0` returns all vulnerabilities in one response
- No pagination marker in output
- Agent warned in documentation about potential size

#### FR-5.3: Scan Metadata Access
**Description**: Retrieve detailed scan configuration
**Tool**: `get_scan_settings(task_id)`
**Returns**: Original scan request, Nessus config, execution timeline, credentials (passwords masked)

**Acceptance Criteria**:
- Available at any time after scan creation
- Includes all scan parameters
- Sensitive data (passwords) masked with `***`

---

### 3.6 Generic Filtering

#### FR-6.1: Filter on Any Attribute
**Description**: Client-specified filters applied BEFORE pagination
**Filter Parameter**: `filters={"field_name": "value_or_operator", ...}`
**Logic**: All filters ANDed together

**Filter Syntax by Type**:
- **Strings**: Case-insensitive substring match
  - `{"plugin_name": "SSH"}` - matches "SSH Key", "OpenSSH", etc.
- **Numbers**: Comparison operators (as string prefix)
  - `{"cvss3_base_score": ">7.0"}` - greater than 7.0
  - `{"cvss_base_score": ">=6.5"}` - greater or equal
  - Operators: `>`, `>=`, `<`, `<=`, `=`, or plain number for exact
- **Booleans**: Exact match
  - `{"exploit_available": true}`
- **Lists** (e.g., CVE): Any element contains substring
  - `{"cve": "CVE-2023"}` - matches if any CVE contains "CVE-2023"

**Key Requirement**: Filters work on **ANY attribute** available in chosen schema. No hardcoded filter fields. Client's LLM backend generates filters based on schema definition.

**Acceptance Criteria**:
- Agent receives schema definition (line 1 of results)
- Agent's LLM generates appropriate filters based on schema
- MCP server applies filters generically to any field
- Pagination counts reflect filtered results (not total)
- Schema line includes applied filters for transparency

**Examples**:
```python
# Only Critical vulnerabilities with exploits
filters={"severity": "Critical", "exploit_available": True}

# SSH vulnerabilities with CVSS > 6.0
filters={"plugin_name": "SSH", "cvss3_base_score": ">6.0"}

# Specific host, specific CVE year
filters={"host": "192.168.1.10", "cve": "CVE-2023"}
```

---

### 3.7 Housekeeping & Data Retention

#### FR-7.1: Time-to-Live (TTL)
**Description**: Automatic scan cleanup based on last access time
**Default TTL**: 24 hours (configurable)
**Trigger**: `current_time - last_accessed_at > ttl_hours`

**Acceptance Criteria**:
- Background service runs periodically (e.g., every hour)
- Scans not accessed for TTL duration are deleted
- Hard delete - no recovery mechanism
- `last_accessed_at` updated on every `get_scan_results()` or `download_native_scan()` call

#### FR-7.2: Manual Deletion
**Description**: Agent can explicitly delete scans
**Tool**: `delete_scan(task_id, force=False)`
**Behavior**:
- Permanently deletes scan and all associated data
- If scan is running, must set `force=True`
- Returns confirmation with task_id

**Acceptance Criteria**:
- Cannot delete running scan without force flag
- Deletion is immediate and permanent
- All files removed from filesystem

#### FR-7.3: Scan Listing (Shared State)
**Description**: All agents see all scans (collaborative environment)
**Tool**: `list_scans(status, scan_type, limit)`
**Returns**: List of all scans with summary info

**Acceptance Criteria**:
- Agent A's scans visible to Agent B (no isolation)
- Can filter by status (queued, running, completed, failed, timeout)
- Can filter by scan type (untrusted, trusted_basic, trusted_privileged)
- Default limit: 50 scans

---

### 3.8 Storage & Data Formats

#### FR-8.1: Native Scan Storage
**Description**: Store scan results in native Nessus `.nessus` format
**Reason**: Minimize scanner engagement, enable semantic search indexing later

**Acceptance Criteria**:
- Completed scans exported to `.nessus` file
- Stored in task directory: `data/tasks/{task_id}/scan_native.nessus`
- Available via `download_native_scan()` tool
- Pre-generated JSON-NL files for each hardcoded schema profile (brief, full)

#### FR-8.2: File System Layout
**Description**: Task-based directory structure
**Location**: `mcp-server/data/tasks/{task_id}/`

**Contents**:
```
{task_id}/
├── task.json              # Task metadata & status
├── scan_request.json      # Original scan request parameters
├── scan_native.nessus     # Native scanner format
├── scan_schema_brief.jsonl   # Pre-generated brief schema
├── scan_schema_full.jsonl    # Pre-generated full schema
├── logs.txt               # MCP execution logs
└── scanner_logs/          # Debug logs (if debug_mode=true)
    ├── nessus_api.log
    ├── scan_progress.log
    └── export.log
```

**Acceptance Criteria**:
- Each task has isolated directory
- Directory name is task_id
- All files persisted to disk
- Debug logs only created when `debug_mode=True`

#### FR-8.3: Scanner Debug Logs
**Description**: Capture internal scanner API logs for troubleshooting (future, stub at the moment)
**Trigger**: `debug_mode=True` parameter in scan request
**Storage**: `scanner_logs/` directory (not single file)

**Acceptance Criteria**:
- Debug logs OFF by default (performance)
- When enabled, populates `scanner_logs/` directory
- Captures API requests/responses, scan progress, export operations
- `task.json` includes `scanner_logs_available: true` when present
- Admin CLI can access logs

---

## 4. MCP Tool Specifications

### 4.1 Scan Execution Tools

#### Tool: `run_untrusted_scan()`
**Parameters**:
- `targets` (required): IP addresses or ranges (e.g., "192.168.1.0/24, 10.0.0.1")
- `name` (required): Scan name for identification
- `description` (optional): Scan description
- `schema_profile` (optional, default="brief"): Output schema profile
- `scanner_type` (optional, default="nessus"): Scanner type to use
- `scanner_instance` (optional): Specific scanner instance ID, or None for random
- `debug_mode` (optional, default=False): Enable detailed scanner logging

**Returns**: `{"task_id": "...", "status": "queued", "queue_position": N, "scanner_instance": "..."}`

#### Tool: `run_trusted_scan()`
**Parameters**: All from `run_untrusted_scan()` PLUS:
- `username` (required): SSH username
- `password` (required): SSH password
- `auth_method` (optional, default="password"): Authentication method (password|certificate|publickey|kerberos)

**Returns**: Same as `run_untrusted_scan()`

#### Tool: `run_privileged_scan()`
**Parameters**: All from `run_trusted_scan()` PLUS:
- `escalation_method` (required): Privilege escalation method (sudo|su|pbrun|dzdo|cisco_enable)
- `escalation_password` (required): Password for privilege escalation
- `escalation_account` (optional, default="root"): Target privileged account

**Returns**: Same as `run_untrusted_scan()`

### 4.2 Status & Results Tools

#### Tool: `get_scan_status(task_id)`
**Returns**:
```json
{
  "task_id": "...",
  "status": "running|completed|failed|timeout|queued",
  "progress": 45,
  "created_at": "...",
  "started_at": "...",
  "completed_at": null,
  "queue_position": null,
  "error_message": null
}
```

#### Tool: `get_scan_results(task_id, page, page_size, custom_schema, filters)`
**Parameters**:
- `task_id` (required): Task ID from run_*_scan()
- `page` (optional, default=1): Page number (1-indexed), or 0 for ALL data
- `page_size` (optional, default=40): Lines per page (10-100), ignored if page=0
- `custom_schema` (optional): Custom field list, overrides profile
- `filters` (optional): Filter dict, see FR-6.1 for syntax

**Returns**: Multi-line JSON-NL string (see FR-5.1)

**Availability**: Only when `status="completed"`

#### Tool: `get_scan_settings(task_id)`
**Returns**: Complete scan configuration dict (passwords masked)

#### Tool: `list_scans(status, scan_type, limit)`
**Parameters**:
- `status` (optional): Filter by status
- `scan_type` (optional): Filter by scan type
- `limit` (optional, default=50): Maximum results

**Returns**: List of scan summary objects

#### Tool: `delete_scan(task_id, force)`
**Parameters**:
- `task_id` (required): Task ID to delete
- `force` (optional, default=False): Allow deletion of running scans

**Returns**: `{"deleted": true, "task_id": "..."}`

#### Tool: `download_native_scan(task_id)`
**Returns**: `{"file_path": "/data/tasks/.../scan_native.nessus", "size_bytes": N}`

### 4.3 Scanner Management Tools

#### Tool: `list_scanners(scanner_type, enabled_only)`
**Parameters**:
- `scanner_type` (optional): Filter by type (nessus|openvas|qualys)
- `enabled_only` (optional, default=True): Only show enabled scanners

**Returns**: List of scanner instance objects (without credentials)

---

## 5. Non-Functional Requirements

### 5.1 Simplicity & Maintainability
- **Requirement**: Code must be simple and maintainable
- **Rationale**: Performance is NOT a concern for Phase 1
- **Implications**:
  - Use file system storage for task data and results
  - Redis for queue, scanner registry, idempotency keys, and task metadata
  - Simple FIFO queue via Redis LPUSH/BRPOP (no complex job system)
  - File-based locking (fcntl) for atomic task.json updates
  - Clear separation of concerns (scanners/, core/, schema/, tools/)

### 5.2 Multi-Agent Concurrency
- **Shared State**: All agents see all scans (no tenant isolation)
- **Concurrent Submissions**: Queue handles multiple simultaneous scan requests
- **Collaboration Pattern**: Agents share task_ids, access each other's results

### 5.3 Security
- **Authentication**: Bearer token for HTTP access (all clients same privilege level)
- **Authorization**: No per-user/per-agent access control (trusted system)
- **Administrative Tasks**: Separate CLI tool (not via MCP), direct filesystem/container access
- **Credential Storage**: Scanner credentials in environment variables
- **Credential Transmission**: SSH passwords in scan requests (HTTPS encrypted)

### 5.4 Performance
- **Scan Submission**: <1 second response time
- **Status Polling**: <500ms response time
- **Result Retrieval**: Pagination ensures bounded response size
- **page=0 Exception**: No size limit, client's responsibility
- **Storage**: File system adequate for expected load

### 5.5 Availability
- **Uptime Target**: 99% (best effort, not critical infrastructure)
- **Scan Timeout**: 24 hours maximum
- **Queue Processing**: Continuous (background worker always running)
- **Housekeeping**: Hourly cleanup runs

---

## 6. Technical Constraints

### 6.1 Technology Stack
- **MCP Framework**: FastMCP (Python)
- **Transport**: HTTP with Bearer authentication
- **Deployment**: Docker Compose (redis, mcp-api, scanner-worker services)
- **Python Version**: 3.11+ (async/await support)
- **Queue & Registry**: Redis (FIFO queue, scanner registry, idempotency, task metadata)
- **Scanner API**: Nessus REST API (native async with httpx.AsyncClient)
- **Storage**: File system for task data (JSON, JSON-NL, .nessus), Redis for ephemeral state
- **Observability**: Prometheus metrics (/metrics endpoint), JSON structured logs

### 6.2 Code Organization
- **Location**: `mcp-server/` directory
- **Structure**:
  ```
  mcp-server/
  ├── scanners/     # Scanner abstraction
  ├── core/         # Task management, queue, housekeeping
  ├── schema/       # Schema profiles, converters, filters
  ├── tools/        # MCP tool implementations
  └── tests/        # Unit & integration tests
  ```

### 6.3 Dependencies
- **Existing Scripts**: Reuse `nessusAPIWrapper/` via imports (do not duplicate)
- **FastMCP Docs**: Reference [`../docs/fastMCPServer/`](../docs/fastMCPServer/)
- **Scanner Independence**: Abstract interface allows adding non-Nessus scanners

---

## 7. Out of Scope (Phase 1)

### 7.1 Future Features
- Natural language schema description (placeholder only)
- Database backend (if file system proves inadequate)
- Semantic search integration (native .nessus files stored for future use)
- Additional scanner backends (OpenVAS, Qualys) - architecture supports, not implemented
- OR filter logic (only AND supported in Phase 1)
- Regular expression filtering (only substring matching)

### 7.2 Not Required
- Per-agent/per-user access control
- Scan result encryption at rest
- Real-time scan progress streaming (polling sufficient)
- Scan scheduling (agents manage their own timing)
- Scan result caching beyond native file storage
- Scan result aggregation/analytics
- Webhook notifications (agents poll)

---

## 8. Acceptance Criteria (Overall)

### 8.1 Core Functionality
- [ ] Agent can submit all three scan types successfully
- [ ] Agent can list available scanners
- [ ] Scans queue and execute in order (FIFO)
- [ ] Agent can poll status and receive accurate progress
- [ ] Completed scans return paginated JSON-NL results
- [ ] Filters work on any schema attribute
- [ ] page=0 returns complete dataset
- [ ] Agent can download native .nessus file
- [ ] Debug logs captured when enabled
- [ ] Scans auto-delete after TTL expires
- [ ] Multiple agents can access same scan

### 8.2 Quality
- [ ] Code passes linting (black, mypy)
- [ ] Unit tests for core logic (>80% coverage)
- [ ] Integration tests with real Nessus scanner
- [ ] Documentation complete (README, API reference)
- [ ] Docker deployment works out-of-box

### 8.3 Performance
- [ ] Scan submission completes in <1s
- [ ] Status polling completes in <500ms
- [ ] Paginated results return in <2s
- [ ] System handles 10 concurrent scan submissions
- [ ] System maintains 100+ task directories without degradation

---

## 9. Implementation Phases

See [`ARCHITECTURE_v2.2.md`](./ARCHITECTURE_v2.2.md) for architectural details and [`archive/IMPLEMENTATION_GUIDE.md`](./archive/IMPLEMENTATION_GUIDE.md) for the comprehensive implementation checklist.

**Summary** (10 phases):
1. **Phase 1**: Core infrastructure setup (directories, Docker, Redis config)
2. **Phase 2**: State management & idempotency (TaskManager, trace IDs)
3. **Phase 3**: Scanner abstraction layer (interface, native async Nessus)
4. **Phase 4**: MCP tools implementation (10 tools)
5. **Phase 5**: Worker implementation (queue consumer, task execution)
6. **Phase 6**: JSON-NL converter & schema system
7. **Phase 7**: Observability & monitoring (logs, metrics, health checks)
8. **Phase 8**: Testing infrastructure (unit, integration, comparison tests)
9. **Phase 9**: Deployment & configuration (Docker, env vars, scanner config)
10. **Phase 10**: Documentation & future enhancements

---

## 10. References

### 10.1 Project Documents
- **Architecture**: [`ARCHITECTURE_v2.2.md`](./ARCHITECTURE_v2.2.md) (same directory)
- **Implementation Guide**: [`archive/IMPLEMENTATION_GUIDE.md`](./archive/IMPLEMENTATION_GUIDE.md)
- **Archived Architectures**: [`archive/`](./archive/) (v1.0, v2.0, v2.1)
- **Codebase Index (nessusAPIWrapper)**: [`../nessusAPIWrapper/CODEBASE_INDEX.md`](../nessusAPIWrapper/CODEBASE_INDEX.md)
- **FastMCP Docs**: [`../docs/fastMCPServer/INDEX.md`](../docs/fastMCPServer/INDEX.md)

### 10.2 External Resources
- **FastMCP GitHub**: https://github.com/jlowin/fastmcp
- **Nessus API Documentation**: https://developer.tenable.com/reference/navigate
- **MCP Protocol Spec**: https://spec.modelcontextprotocol.io/

### 10.3 Docker Environment
- **Nessus Compose**: `/home/nessus/docker/nessus/docker-compose.yml` (external to project)
- **Nessus URL**: `https://localhost:8834` (via VPN gateway)
- **MCP Server URL**: `http://localhost:8835` (to be deployed)

---

## 11. Glossary

- **MCP**: Model Context Protocol - Standard for LLM-tool communication
- **FastMCP**: Python framework for building MCP servers
- **JSON-NL**: JSON Lines format - one JSON object per line
- **Task ID**: Unique identifier for scan, format: `{type}_{instance}_{timestamp}_{random}`
- **Scanner Instance**: Specific scanner deployment (e.g., "Production Nessus")
- **Schema Profile**: Predefined field set for results (minimal/summary/brief/full)
- **TTL**: Time-to-Live - Duration before automatic deletion
- **FIFO**: First In First Out - Queue processing order
- **Privilege Escalation**: Gaining root/admin access (sudo, su, etc.)

---

## 12. Approval

**Requirements Approved By**: User
**Date**: 2025-11-01 (updated for v2.2)
**Architecture Approved**: Yes ([`ARCHITECTURE_v2.2.md`](./ARCHITECTURE_v2.2.md))
**Implementation Guide**: Available ([`archive/IMPLEMENTATION_GUIDE.md`](./archive/IMPLEMENTATION_GUIDE.md))
**Ready for Implementation**: Yes

**Next Step**: Begin Phase 1 implementation per archive/IMPLEMENTATION_GUIDE.md
