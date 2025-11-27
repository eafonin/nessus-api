# FastMCP Client Architecture

> Comprehensive guide to the Nessus MCP Server client architecture, data flow, and integration patterns

## Overview

The FastMCP Client provides a type-safe, Pythonic interface for interacting with the Nessus MCP Server. This document explains the complete architecture, from user code to backend services, with detailed data flow diagrams and integration patterns.

**Key Components**:
- **NessusFastMCPClient** - High-level wrapper for Nessus-specific operations
- **FastMCP Client Library** - Protocol implementation and transport layer
- **Nessus MCP Server** - FastMCP-based HTTP/SSE server
- **Backend Services** - Task management, queue, scanner, schema conversion

**Reference Documentation**:
- FastMCP Client Basics: `@docs/fastMCPServer/clients/client.md`
- Tool Operations: `@docs/fastMCPServer/clients/tools.md`
- HTTP Transport: `@docs/fastMCPServer/clients/transports.md`

---

## Architecture Layers

### Layer 1: User Application

```
┌─────────────────────────────────────────────────────────────┐
│  User Code                                                  │
│  - Test suites                                              │
│  - CLI tools                                                │
│  - Debugging scripts                                        │
│  - Production automation                                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ async with NessusFastMCPClient(url) as client
                  │     task = await client.submit_scan(...)
                  │     status = await client.get_status(...)
                  │
                  ▼
```

**Responsibilities**:
- Define scan parameters (targets, scan names)
- Handle scan lifecycle (submit, monitor, retrieve results)
- Process vulnerability data
- Implement business logic

**Code Location**: User-defined scripts, `tests/`, `examples/`

---

### Layer 2: NessusFastMCPClient (High-Level Wrapper)

```
┌─────────────────────────────────────────────────────────────┐
│  NessusFastMCPClient                                        │
│  📁 client/nessus_fastmcp_client.py (740 lines)             │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  CORE OPERATIONS (Base MCP Protocol)                 │  │
│  │                                                       │  │
│  │  • ping() → bool                                     │  │
│  │  • list_tools() → List[Dict]                        │  │
│  │  • call_tool(name, args) → Any                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  HIGH-LEVEL METHODS (Nessus-Specific)               │  │
│  │                                                       │  │
│  │  • submit_scan(targets, name, ...) → Dict           │  │
│  │  • get_status(task_id) → Dict                       │  │
│  │  • get_results(task_id, schema, ...) → str          │  │
│  │  • list_scanners() → Dict                           │  │
│  │  • get_queue_status() → Dict                        │  │
│  │  • list_tasks(status, limit) → Dict                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  HELPER METHODS (Workflows)                          │  │
│  │                                                       │  │
│  │  • wait_for_completion(task_id, ...) → Dict         │  │
│  │  • scan_and_wait(targets, ...) → Dict               │  │
│  │  • get_critical_vulnerabilities(task_id) → List     │  │
│  │  • get_vulnerability_summary(task_id) → Dict        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Connection Management:                                    │
│  - async with context manager                              │
│  - Automatic connect/disconnect                            │
│  - Connection state tracking                               │
│                                                             │
│  Error Handling:                                           │
│  - TimeoutError for long operations                        │
│  - Exception propagation from FastMCP                      │
│  - Debug logging (optional)                                │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ FastMCP Client API
                  │ - client.call_tool(tool_name, arguments)
                  │ - client.ping()
                  │
                  ▼
```

**Responsibilities**:
- Provide type-safe, Pythonic API
- Map Nessus operations to MCP tool calls
- Handle connection lifecycle
- Implement helper workflows (wait, poll, parse)
- Progress monitoring and logging

**Key Features**:
- 6 wrapper methods for MCP tools
- 4 helper methods for common patterns
- Built-in timeout handling
- Progress callbacks
- Debug logging support

---

### Layer 3: FastMCP Client Library

```
┌─────────────────────────────────────────────────────────────┐
│  FastMCP Client                                             │
│  📦 from fastmcp import Client                              │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Protocol Operations                                  │  │
│  │                                                       │  │
│  │  • call_tool(name, args) → CallToolResult           │  │
│  │  • list_tools() → List[Tool]                        │  │
│  │  • read_resource(uri) → ResourceContent             │  │
│  │  • get_prompt(name, args) → PromptMessages          │  │
│  │  • ping() → None                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Connection Lifecycle                                 │  │
│  │                                                       │  │
│  │  • __aenter__() - Establish connection               │  │
│  │  • __aexit__() - Close connection                    │  │
│  │  • is_connected() → bool                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Callback Handlers                                    │  │
│  │                                                       │  │
│  │  • log_handler(message) - Server logs                │  │
│  │  • progress_handler(p, t, msg) - Progress updates    │  │
│  │  • sampling_handler(messages) - LLM requests         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Transport Management:                                     │
│  - Automatic transport inference (HTTP, SSE, stdio)        │
│  - Connection pooling                                      │
│  - Request serialization (MCP protocol)                    │
│  - Response deserialization                                │
│                                                             │
│  Reference: @docs/fastMCPServer/clients/*                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ HTTP POST with SSE
                  │ Endpoint: http://localhost:8835/mcp
                  │
                  ▼
```

**Responsibilities**:
- Implement MCP protocol specification
- Manage HTTP/SSE transport
- Serialize/deserialize messages
- Handle callbacks (log, progress, sampling)
- Connection pooling and keepalive

**Key Features**:
- Protocol-compliant implementation
- Multiple transport support (HTTP, stdio, WebSocket)
- Automatic transport inference
- Timeout management
- Callback system

---

### Layer 4: HTTP/SSE Transport

```
┌─────────────────────────────────────────────────────────────┐
│  HTTP/SSE Transport Layer                                   │
│                                                             │
│  Request Format (HTTP POST):                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  POST http://localhost:8835/mcp                      │  │
│  │  Content-Type: application/json                      │  │
│  │                                                       │  │
│  │  {                                                    │  │
│  │    "jsonrpc": "2.0",                                 │  │
│  │    "id": 1,                                          │  │
│  │    "method": "tools/call",                           │  │
│  │    "params": {                                       │  │
│  │      "name": "run_untrusted_scan",                   │  │
│  │      "arguments": {                                  │  │
│  │        "targets": "192.168.1.1",                     │  │
│  │        "scan_name": "Test Scan"                      │  │
│  │      }                                               │  │
│  │    }                                                 │  │
│  │  }                                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Response Format (SSE Stream):                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  data: {"jsonrpc": "2.0", "id": 1, "result": {       │  │
│  │    "content": [{                                     │  │
│  │      "type": "text",                                 │  │
│  │      "text": "{\"task_id\": \"...\", ...}"          │  │
│  │    }],                                               │  │
│  │    "isError": false                                  │  │
│  │  }}                                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Transport Features:                                       │
│  - Connection pooling (reuse connections)                  │
│  - Request/response correlation (via id field)             │
│  - Streaming responses (Server-Sent Events)                │
│  - Timeout enforcement                                     │
│  - Error propagation                                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
```

**Responsibilities**:
- HTTP connection management
- SSE stream parsing
- Request/response correlation
- Error handling and propagation

---

### Layer 5: Nessus MCP Server

```
┌─────────────────────────────────────────────────────────────┐
│  Nessus MCP Server (FastMCP)                               │
│  📁 tools/mcp_server.py (426 lines)                         │
│                                                             │
│  HTTP Endpoints:                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  GET  /health  → {redis_healthy, filesystem, ...}   │  │
│  │  GET  /metrics → Prometheus metrics (text format)    │  │
│  │  POST /mcp     → MCP protocol (SSE transport)        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  MCP Tools (6):                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  @mcp.tool()                                         │  │
│  │  async def run_untrusted_scan(                       │  │
│  │      targets: str,                                   │  │
│  │      scan_name: str,                                 │  │
│  │      description: Optional[str] = None               │  │
│  │  ) -> Dict[str, Any]:                                │  │
│  │      # Creates task, enqueues to Redis              │  │
│  │      # Returns {"task_id": "...", "status": "..."}  │  │
│  │                                                       │  │
│  │  @mcp.tool()                                         │  │
│  │  async def get_scan_status(                          │  │
│  │      task_id: str                                    │  │
│  │  ) -> Dict[str, Any]:                                │  │
│  │      # Returns current task status                   │  │
│  │                                                       │  │
│  │  @mcp.tool()                                         │  │
│  │  async def get_scan_results(                         │  │
│  │      task_id: str,                                   │  │
│  │      schema_profile: str = "brief",                  │  │
│  │      filters: Optional[Dict] = None,                 │  │
│  │      page: int = 1,                                  │  │
│  │      page_size: int = 40                             │  │
│  │  ) -> str:                                           │  │
│  │      # Returns JSON-NL formatted results            │  │
│  │                                                       │  │
│  │  @mcp.tool()                                         │  │
│  │  async def list_scanners() -> Dict[str, Any]:       │  │
│  │      # Returns scanner registry                     │  │
│  │                                                       │  │
│  │  @mcp.tool()                                         │  │
│  │  async def get_queue_status() -> Dict[str, Any]:    │  │
│  │      # Returns queue depth stats                    │  │
│  │                                                       │  │
│  │  @mcp.tool()                                         │  │
│  │  async def list_tasks(                               │  │
│  │      status: Optional[str] = None,                   │  │
│  │      limit: int = 100                                │  │
│  │  ) -> Dict[str, Any]:                                │  │
│  │      # Returns task list                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Observability:                                            │
│  - Structured logging (JSON) via structlog                 │
│  - Prometheus metrics (8 metrics defined)                  │
│  - Health check endpoints                                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
```

**Responsibilities**:
- Expose MCP tools via HTTP/SSE
- Route requests to backend services
- Return formatted responses
- Provide health and metrics endpoints

---

### Layer 6: Backend Services

```
┌─────────────────────────────────────────────────────────────┐
│  Backend Services                                           │
│                                                             │
│  ┌────────────────┬────────────────┬───────────────────┐   │
│  │ TaskManager    │ Redis Queue    │ Scanner Worker    │   │
│  │                │                │                   │   │
│  │ core/task_     │ core/queue.py  │ worker/scanner_   │   │
│  │  manager.py    │                │  worker.py        │   │
│  │                │                │                   │   │
│  │ • create_task  │ • enqueue      │ • dequeue         │   │
│  │ • get_task     │ • dequeue      │ • execute_scan    │   │
│  │ • update_task  │ • dlq_push     │ • monitor         │   │
│  │ • delete_task  │ • get_depth    │ • handle_errors   │   │
│  │                │                │                   │   │
│  │ Storage:       │ Storage:       │ Execution:        │   │
│  │ Filesystem     │ Redis 7.4.7    │ Async loop        │   │
│  │ data/tasks/    │ :6379          │ Real Nessus       │   │
│  └────────────────┴────────────────┴───────────────────┘   │
│                                                             │
│  ┌────────────────┬────────────────────────────────────┐   │
│  │ Schema System  │ Idempotency Manager                │   │
│  │                │                                    │   │
│  │ schema/        │ core/idempotency_manager.py        │   │
│  │  parser.py     │                                    │   │
│  │  profiles.py   │ • check(key, params) → task_id    │   │
│  │  converter.py  │ • SHA256 request hashing          │   │
│  │  filters.py    │ • Redis SETNX (atomic)            │   │
│  │                │ • 48-hour TTL                     │   │
│  │ • parse_xml    │ • Conflict detection              │   │
│  │ • apply_schema │                                    │   │
│  │ • filter       │                                    │   │
│  │ • paginate     │                                    │   │
│  └────────────────┴────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Responsibilities**:
- **TaskManager**: CRUD operations for scan tasks
- **Queue**: FIFO queue with DLQ for failed tasks
- **Scanner Worker**: Async scan execution with real Nessus
- **Schema System**: Parse, filter, paginate vulnerability data
- **Idempotency**: Prevent duplicate scan submissions

---

## Complete Request/Response Flow

### Flow 1: Submit Scan

```
┌──────────────────────────────────────────────────────────────────┐
│ USER CODE                                                        │
│                                                                  │
│ async with NessusFastMCPClient("http://localhost:8835/mcp") as client:
│     task = await client.submit_scan(                            │
│         targets="192.168.1.1",                                  │
│         scan_name="Network Scan"                                │
│     )                                                            │
│     # task = {"task_id": "nessus-local-...", "status": "queued"}│
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: NessusFastMCPClient.submit_scan()                       │
│                                                                  │
│ def submit_scan(self, targets, scan_name, ...):                 │
│     arguments = {                                               │
│         "targets": "192.168.1.1",                               │
│         "scan_name": "Network Scan"                             │
│     }                                                            │
│     return await self.call_tool("run_untrusted_scan", arguments)│
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: FastMCP Client.call_tool()                              │
│                                                                  │
│ Serializes to MCP protocol:                                     │
│ {                                                                │
│   "jsonrpc": "2.0",                                             │
│   "id": 1,                                                      │
│   "method": "tools/call",                                       │
│   "params": {                                                   │
│     "name": "run_untrusted_scan",                               │
│     "arguments": {                                              │
│       "targets": "192.168.1.1",                                 │
│       "scan_name": "Network Scan"                               │
│     }                                                            │
│   }                                                              │
│ }                                                                │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │ HTTP POST http://localhost:8835/mcp
                       │ Content-Type: application/json
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: MCP Server receives request                             │
│                                                                  │
│ FastMCP framework routes to:                                    │
│   @mcp.tool()                                                   │
│   async def run_untrusted_scan(targets, scan_name):             │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 4: run_untrusted_scan() executes                           │
│                                                                  │
│ 1. Check idempotency (SHA256 hash of params)                    │
│    existing = idempotency_manager.check(key, params)            │
│    if existing: return {"task_id": existing, "idempotent": True}│
│                                                                  │
│ 2. Create task (TaskManager)                                    │
│    task = task_manager.create_task(                             │
│        task_id="nessus-local-20251108-143022",                  │
│        scan_type="untrusted",                                   │
│        targets="192.168.1.1",                                   │
│        scan_name="Network Scan",                                │
│        status="queued"                                          │
│    )                                                             │
│                                                                  │
│ 3. Enqueue to Redis                                             │
│    queue.enqueue(task_id="nessus-local-20251108-143022")        │
│                                                                  │
│ 4. Store idempotency key (48h TTL)                              │
│    redis.set(key, task_id, nx=True, ex=48*3600)                 │
│                                                                  │
│ 5. Record metrics                                               │
│    nessus_scans_total{scan_type="untrusted",status="queued"}++  │
│    nessus_queue_depth{queue="main"} = queue.depth()             │
│                                                                  │
│ 6. Log event                                                    │
│    logger.info("scan_enqueued", task_id="...", targets="...")   │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │ Return value
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 5: MCP Server serializes response                          │
│                                                                  │
│ Response (SSE format):                                          │
│ data: {                                                          │
│   "jsonrpc": "2.0",                                             │
│   "id": 1,                                                      │
│   "result": {                                                   │
│     "content": [{                                               │
│       "type": "text",                                           │
│       "text": "{\"task_id\": \"nessus-local-...\", ...}"       │
│     }],                                                          │
│     "isError": false                                            │
│   }                                                              │
│ }                                                                │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │ HTTP 200 OK (SSE stream)
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 6: FastMCP Client deserializes response                    │
│                                                                  │
│ Extracts result.content[0].text, parses JSON:                   │
│ {                                                                │
│   "task_id": "nessus-local-20251108-143022",                    │
│   "status": "queued",                                           │
│   "scan_type": "untrusted",                                     │
│   "targets": "192.168.1.1",                                     │
│   "scan_name": "Network Scan",                                  │
│   "created_at": "2025-11-08T14:30:22Z",                         │
│   "idempotent": false                                           │
│ }                                                                │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 7: NessusFastMCPClient returns Dict to user                │
│                                                                  │
│ User receives:                                                   │
│ {                                                                │
│   "task_id": "nessus-local-20251108-143022",                    │
│   "status": "queued",                                           │
│   ...                                                            │
│ }                                                                │
└──────────────────────────────────────────────────────────────────┘
```

**Key Points**:
- **Idempotency check** prevents duplicate submissions
- **Task creation** persists to filesystem (`data/tasks/{task_id}/`)
- **Queue enqueue** uses Redis LPUSH
- **Metrics recorded** for observability
- **Structured logging** captures all events

---

### Flow 2: Background Scan Execution

```
┌──────────────────────────────────────────────────────────────────┐
│ SCANNER WORKER (Running in background)                          │
│ worker/scanner_worker.py                                         │
│                                                                  │
│ while True:                                                      │
│     # Poll Redis queue                                          │
│     task_id = queue.dequeue(timeout=5)                          │
│     if not task_id:                                             │
│         continue                                                 │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │ Task dequeued: "nessus-local-20251108-143022"
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Load task from TaskManager                              │
│                                                                  │
│ task = task_manager.get_task("nessus-local-20251108-143022")    │
│ # Returns Task object with targets, scan_name, etc.             │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Initialize Nessus scanner                               │
│                                                                  │
│ scanner = NessusAsyncScanner(                                    │
│     url="https://vpn-gateway:8834",                             │
│     username="nessus",                                          │
│     password="nessus"                                           │
│ )                                                                │
│ await scanner.authenticate()                                    │
│ # Fetches X-API-Token from nessus6.js dynamically               │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: Create scan in Nessus                                   │
│                                                                  │
│ nessus_scan_id = await scanner.create_scan(                     │
│     name="Network Scan",                                        │
│     targets="192.168.1.1",                                      │
│     policy_id="untrusted_network_scan_policy_id"                │
│ )                                                                │
│ # Returns: 42 (Nessus internal scan ID)                         │
│                                                                  │
│ # Update task                                                   │
│ task.nessus_scan_id = 42                                        │
│ task_manager.update_task(task)                                  │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 4: Launch scan                                             │
│                                                                  │
│ await scanner.launch_scan(nessus_scan_id=42)                    │
│                                                                  │
│ # Update task status                                            │
│ task.status = "running"                                         │
│ task_manager.update_task(task)                                  │
│                                                                  │
│ # Log event                                                     │
│ logger.info("scan_state_transition",                            │
│     from_state="queued", to_state="running",                    │
│     nessus_scan_id=42)                                          │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 5: Monitor scan progress (polling loop)                    │
│                                                                  │
│ while True:                                                      │
│     status = await scanner.get_scan_status(nessus_scan_id=42)   │
│                                                                  │
│     if status["status"] == "completed":                         │
│         break                                                    │
│                                                                  │
│     # Update progress                                           │
│     task.progress = status.get("progress", 0)                   │
│     task_manager.update_task(task)                              │
│                                                                  │
│     # Log progress                                              │
│     logger.info("scan_progress",                                │
│         progress=status["progress"],                            │
│         scanner_status=status["status"])                        │
│                                                                  │
│     await asyncio.sleep(10)  # Poll every 10 seconds            │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │ Scan completes
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 6: Export results from Nessus                              │
│                                                                  │
│ # Request export                                                │
│ file_id = await scanner.export_scan(                            │
│     nessus_scan_id=42,                                          │
│     format="nessus"  # .nessus XML format                       │
│ )                                                                │
│                                                                  │
│ # Wait for export to be ready                                   │
│ while not await scanner.is_export_ready(file_id):               │
│     await asyncio.sleep(5)                                      │
│                                                                  │
│ # Download .nessus file                                         │
│ nessus_data = await scanner.download_export(file_id)            │
│ # Returns: bytes (XML content)                                  │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 7: Save results to filesystem                              │
│                                                                  │
│ results_path = task_manager.data_dir / task.task_id / "scan_native.nessus"
│ results_path.write_bytes(nessus_data)                           │
│                                                                  │
│ # Update task                                                   │
│ task.status = "completed"                                       │
│ task.progress = 100                                             │
│ task.completed_at = datetime.utcnow()                           │
│ task_manager.update_task(task)                                  │
│                                                                  │
│ # Log completion                                                │
│ logger.info("scan_completed",                                   │
│     task_id=task.task_id,                                       │
│     duration_seconds=...,                                       │
│     vulnerabilities_found=...)                                  │
│                                                                  │
│ # Record metrics                                                │
│ nessus_scans_total{scan_type="untrusted",status="completed"}++  │
│ nessus_task_duration_seconds.observe(duration)                  │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 8: Cleanup Nessus scan                                     │
│                                                                  │
│ await scanner.delete_scan(nessus_scan_id=42)                    │
│ # Removes scan from Nessus (keeps .nessus file locally)         │
└──────────────────────────────────────────────────────────────────┘
```

**Key Points**:
- **Async execution** - Worker runs independently of API
- **Dynamic token fetching** - X-API-Token extracted from nessus6.js
- **Progress monitoring** - 10-second polling interval
- **Structured logging** - 39 log events throughout workflow
- **Metrics collection** - Duration, completion rate tracked

---

### Flow 3: Retrieve Results

```
┌──────────────────────────────────────────────────────────────────┐
│ USER CODE                                                        │
│                                                                  │
│ # Wait for completion                                           │
│ await client.wait_for_completion(task_id, timeout=600)          │
│                                                                  │
│ # Get results                                                   │
│ results = await client.get_results(                             │
│     task_id="nessus-local-20251108-143022",                     │
│     schema_profile="brief",                                     │
│     filters={"severity": "4"},  # Critical only                 │
│     page=0  # Get all data                                      │
│ )                                                                │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: NessusFastMCPClient.get_results()                       │
│                                                                  │
│ arguments = {                                                    │
│     "task_id": "nessus-local-20251108-143022",                  │
│     "schema_profile": "brief",                                  │
│     "filters": {"severity": "4"},                               │
│     "page": 0                                                    │
│ }                                                                │
│ return await self.call_tool("get_scan_results", arguments)      │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │ HTTP POST /mcp (MCP protocol)
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: MCP Server - get_scan_results() executes                │
│                                                                  │
│ 1. Validate task exists and is completed                        │
│    task = task_manager.get_task(task_id)                        │
│    if task.status != "completed":                               │
│        return {"error": "Scan not completed yet"}               │
│                                                                  │
│ 2. Load .nessus file                                            │
│    nessus_file = data_dir / task_id / "scan_native.nessus"      │
│    nessus_data = nessus_file.read_bytes()                       │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: Schema System - Convert to JSON-NL                      │
│                                                                  │
│ converter = NessusToJsonNL()                                     │
│ json_nl = converter.convert(                                    │
│     nessus_data=nessus_data,                                    │
│     schema_profile="brief",                                     │
│     filters={"severity": "4"},                                  │
│     page=0                                                       │
│ )                                                                │
│                                                                  │
│ Internally:                                                      │
│ 1. Parse XML (schema/parser.py)                                 │
│    parsed = parse_nessus_file(nessus_data)                      │
│    # Returns: {vulnerabilities: [...], scan_metadata: {...}}    │
│                                                                  │
│ 2. Get schema fields (schema/profiles.py)                       │
│    fields = get_schema_fields("brief")                          │
│    # Returns: ["host", "plugin_id", "severity", ...]            │
│                                                                  │
│ 3. Apply filters (schema/filters.py)                            │
│    filtered = apply_filters(parsed["vulnerabilities"], filters) │
│    # Filters for severity=="4" only                             │
│                                                                  │
│ 4. Project fields (schema/converter.py)                         │
│    projected = [_project_fields(v, fields) for v in filtered]   │
│    # Keeps only "brief" schema fields                           │
│                                                                  │
│ 5. Format as JSON-NL                                            │
│    lines = [                                                     │
│        json.dumps({"type": "schema", "profile": "brief", ...}), │
│        json.dumps({"type": "scan_metadata", ...}),              │
│        *[json.dumps(vuln) for vuln in projected],               │
│        # No pagination line for page=0                          │
│    ]                                                             │
│    return "\n".join(lines)                                      │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │ Returns JSON-NL string
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 4: MCP Server returns JSON-NL via SSE                      │
│                                                                  │
│ Response:                                                        │
│ data: {"jsonrpc": "2.0", "id": 2, "result": {                   │
│   "content": [{"type": "text", "text": "<JSON-NL string>"}]     │
│ }}                                                               │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 5: User parses JSON-NL                                     │
│                                                                  │
│ for line in results.strip().split("\n"):                        │
│     data = json.loads(line)                                     │
│     if data["type"] == "schema":                                │
│         print(f"Total: {data['total_vulnerabilities']}")        │
│     elif data["type"] == "vulnerability":                       │
│         print(f"CVE: {data.get('cve')}, CVSS: {data['cvss_score']}")
└──────────────────────────────────────────────────────────────────┘
```

**Key Points**:
- **Phase 2 schema system** handles parsing and filtering
- **JSON-NL format** - One JSON object per line for streaming
- **Page=0** returns all data without pagination
- **Filter application** happens before field projection

---

## Component Interactions

### Idempotency Flow

```
┌──────────────────────────────────────────────────────────────────┐
│ CLIENT                                                           │
│                                                                  │
│ # Submit same scan twice                                        │
│ task1 = await client.submit_scan(targets="192.168.1.1", ...)    │
│ task2 = await client.submit_scan(targets="192.168.1.1", ...)    │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ FIRST REQUEST                                                    │
│                                                                  │
│ 1. Generate idempotency key                                     │
│    key_data = {                                                  │
│        "scan_type": "untrusted",                                │
│        "targets": "192.168.1.1",                                │
│        "scan_name": "...",                                      │
│        "description": "..."                                     │
│    }                                                             │
│    key = SHA256(json.dumps(key_data, sort_keys=True))           │
│    # Returns: "idem:c3ef11a1c4a1a8f8..."                        │
│                                                                  │
│ 2. Check Redis for existing task                                │
│    existing = redis.get(key)                                    │
│    # Returns: None (first submission)                           │
│                                                                  │
│ 3. Create new task                                              │
│    task_id = "nessus-local-20251108-143022"                     │
│    task_manager.create_task(...)                                │
│                                                                  │
│ 4. Store idempotency key with 48h TTL                           │
│    redis.set(key, task_id, nx=True, ex=48*3600)                 │
│                                                                  │
│ 5. Return new task                                              │
│    return {"task_id": "...", "idempotent": False}               │
└──────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ SECOND REQUEST (Duplicate)                                      │
│                                                                  │
│ 1. Generate same idempotency key                                │
│    key = SHA256(json.dumps(key_data, sort_keys=True))           │
│    # Returns: "idem:c3ef11a1c4a1a8f8..." (SAME as first)        │
│                                                                  │
│ 2. Check Redis for existing task                                │
│    existing = redis.get(key)                                    │
│    # Returns: "nessus-local-20251108-143022" (EXISTS!)          │
│                                                                  │
│ 3. Return existing task (NO NEW TASK CREATED)                   │
│    return {                                                      │
│        "task_id": "nessus-local-20251108-143022",               │
│        "idempotent": True,  # Flag indicates duplicate          │
│        "original_task": task_manager.get_task(existing)         │
│    }                                                             │
└──────────────────────────────────────────────────────────────────┘
```

**Benefits**:
- Prevents duplicate scan submissions
- 48-hour deduplication window
- Atomic Redis SETNX operation
- SHA256 hash ensures parameter matching

---

## Development Requirement

### Mandatory for All Future Work

**Requirement**: All future development iterations MUST use the FastMCP client for testing and integration.

**Rationale**:
1. **Type safety** - Catches errors at development time
2. **Consistency** - Standardized API across all code
3. **Testability** - Easy to write integration tests
4. **Debugging** - Built-in debug logging
5. **Maintainability** - Single source of truth for API calls

**Examples**:

**Do**:
```python
async with NessusFastMCPClient() as client:
    task = await client.submit_scan(targets="192.168.1.1", scan_name="Test")
    assert task["status"] == "queued"
```

**Don't**:
```bash
curl -X POST http://localhost:8835/mcp -d '{"method": "tools/call", ...}'
```

**Documentation Reference**:
- Client implementation: [`client/nessus_fastmcp_client.py`](./client/nessus_fastmcp_client.py)
- Example usage: [`client/examples/`](./client/examples/)
- FastMCP docs: `@docs/fastMCPServer/`

---

## Performance Characteristics

### Latency Breakdown

**Total request latency**: ~50-200ms (typical)

1. **Client serialization**: ~1ms
   - Python dict → JSON
   - MCP protocol wrapping

2. **HTTP transport**: ~5-20ms
   - Network latency (localhost: 1-5ms, remote: 10-50ms)
   - TLS handshake (first request only)
   - Connection pooling (reuse)

3. **Server processing**: ~10-50ms
   - MCP protocol parsing
   - Tool routing
   - Business logic (TaskManager, Redis)

4. **Response serialization**: ~1-5ms
   - JSON encoding
   - SSE formatting

5. **Client deserialization**: ~1ms
   - SSE parsing
   - JSON decoding

**Optimization Opportunities**:
- Connection pooling (already implemented)
- Request batching (future enhancement)
- Caching for read-heavy operations (future enhancement)

---

## Error Handling

### Error Propagation Chain

```
User Code
    ↓ Exception raised
NessusFastMCPClient
    ↓ Catches specific errors, adds context
FastMCP Client
    ↓ HTTP/protocol errors
MCP Server
    ↓ Business logic errors
Backend Services
    ↓ Infrastructure errors
```

**Common Errors**:

1. **TimeoutError**
   - Source: NessusFastMCPClient.wait_for_completion()
   - Cause: Task doesn't complete within timeout
   - Handling: Catch and retry, or extend timeout

2. **ConnectionError**
   - Source: FastMCP Client (HTTP transport)
   - Cause: Server unreachable
   - Handling: Check server status, verify network

3. **ValueError**
   - Source: Schema system (invalid parameters)
   - Cause: Invalid schema profile or custom fields
   - Handling: Validate parameters before submission

4. **TaskNotFoundError**
   - Source: TaskManager
   - Cause: Invalid task_id
   - Handling: Verify task_id from submit_scan()

---

## Observability

### Logging

**Structured JSON logging** throughout the stack:

```json
{
  "timestamp": "2025-11-08T14:30:22.123456Z",
  "level": "info",
  "event": "scan_state_transition",
  "task_id": "nessus-local-20251108-143022",
  "from_state": "queued",
  "to_state": "running",
  "nessus_scan_id": 42,
  "component": "scanner_worker"
}
```

**39 log events** defined across worker lifecycle.

### Metrics

**8 Prometheus metrics**:
- `nessus_scans_total{scan_type, status}`
- `nessus_api_requests_total{tool, status}`
- `nessus_active_scans`
- `nessus_scanner_instances{scanner_type, enabled}`
- `nessus_queue_depth{queue}`
- `nessus_task_duration_seconds`
- `nessus_ttl_deletions_total`
- `nessus_dlq_size`

**Endpoint**: `GET http://localhost:8835/metrics`

### Health Checks

**Endpoint**: `GET http://localhost:8835/health`

**Checks**:
- Redis connectivity (PING)
- Filesystem writability (touch test)

**Response**:
```json
{
  "redis_healthy": true,
  "filesystem_healthy": true,
  "overall_status": "healthy",
  "response_code": 200
}
```

---

## Summary

The FastMCP Client architecture provides:

1. **3 Layers** - User code → NessusFastMCPClient → FastMCP Client → MCP Server
2. **Type Safety** - Python type hints throughout
3. **Observability** - Structured logging, metrics, health checks
4. **Reliability** - Idempotency, error handling, retries
5. **Performance** - Sub-200ms latency for most operations
6. **Testability** - Clean API for integration tests

**Next Steps**:
- Review example usage scripts: [`client/examples/`](./client/examples/)
- Read client implementation: [`client/nessus_fastmcp_client.py`](./client/nessus_fastmcp_client.py)
- Explore FastMCP documentation: `@docs/fastMCPServer/`

---

**Last Updated**: 2025-11-08
**Version**: 1.0
**Status**: Complete and production-ready
