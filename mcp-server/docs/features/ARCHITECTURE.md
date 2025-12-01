# Nessus MCP Server - Architecture

> **[↑ Documentation Index](/mcp-server/docs/README.md)** | **[← Features](FEATURES.md)** | **[Requirements →](REQUIREMENTS.md)**

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MCP Clients                                    │
│              (Claude Code, LLM Applications, CI/CD)                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ SSE Transport (HTTP)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        MCP Server (FastMCP)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  MCP Tools   │  │   Health     │  │   Metrics    │                  │
│  │  /mcp        │  │   /health    │  │   /metrics   │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
         │                                           │
         │ Task Creation                             │ Status Queries
         ▼                                           ▼
┌─────────────────────┐                    ┌──────────────────────┐
│    Task Manager     │                    │   Scanner Registry   │
│  (File-based JSON)  │                    │   (YAML Config)      │
└─────────────────────┘                    └──────────────────────┘
         │                                           │
         │ Enqueue                                   │ Scanner Selection
         ▼                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Redis Queue                                     │
│  ┌──────────────────────────┐  ┌──────────────────────────┐            │
│  │    {pool}:queue          │  │    {pool}:queue:dead     │            │
│  │    (FIFO - LPUSH/BRPOP)  │  │    (Dead Letter Queue)   │            │
│  └──────────────────────────┘  └──────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ BRPOP (blocking dequeue)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Scanner Worker                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  Task Loop   │  │  Validator   │  │  Semaphore   │                  │
│  │  (async)     │  │  (XML parse) │  │  (concurrency)│                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/REST API
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Nessus Scanner Pool                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  Scanner 1   │  │  Scanner 2   │  │  Scanner N   │                  │
│  │  (Primary)   │  │  (Secondary) │  │  (...)       │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. MCP Server Layer

**Technology**: FastMCP 2.13.0.2 + Starlette SSE

**Endpoints**:
| Endpoint | Protocol | Purpose |
|----------|----------|---------|
| `/mcp` | SSE | MCP protocol (JSON-RPC over SSE) |
| `/health` | HTTP GET | Health check |
| `/metrics` | HTTP GET | Prometheus metrics |

**MCP Tools** (9 total):
- `run_untrusted_scan` - Network scanning
- `run_authenticated_scan` - SSH authenticated scanning
- `get_scan_status` - Task status with progress
- `get_scan_results` - Filtered result retrieval
- `list_tasks` - Task listing with filters
- `list_scanners` - Scanner instances
- `list_pools` - Scanner pools
- `get_pool_status` - Pool utilization
- `get_queue_status` - Queue metrics

### 2. Task Management Layer

**Storage**: File-based JSON in `/app/data/tasks/{task_id}/`

**Files per task**:
```
/app/data/tasks/{task_id}/
├── task.json           # Task metadata, state, validation
└── scan_native.nessus  # Nessus XML results
```

**Task State Machine**:
```
           ┌─────────┐
           │ QUEUED  │
           └────┬────┘
                │ Worker picks up
                ▼
           ┌─────────┐
           │ RUNNING │
           └────┬────┘
                │
    ┌───────────┼───────────┐
    │           │           │
    ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│COMPLETED│ │ FAILED  │ │ TIMEOUT │
└─────────┘ └─────────┘ └─────────┘
```

**Task ID Format**: `{scanner_type}_{instance}_{timestamp}_{random}`

### 3. Queue Layer

**Technology**: Redis 7+ with FIFO lists

**Queue Structure**:
```
Redis Keys:
├── {pool}:queue         # Main FIFO queue (LPUSH/BRPOP)
├── {pool}:queue:dead    # Dead Letter Queue (ZADD with timestamp)
└── idempotency:{key}    # Idempotency key storage (TTL)
```

**Operations**:
| Operation | Redis Command | Blocking |
|-----------|---------------|----------|
| Enqueue | LPUSH | No |
| Dequeue | BRPOP | Yes (timeout) |
| Queue depth | LLEN | No |
| DLQ add | ZADD | No |

### 4. Worker Layer

**Technology**: Async Python with asyncio

**Concurrency Model**:
```python
MAX_CONCURRENT_SCANS = 2  # Per scanner instance
semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCANS)
```

**Worker Loop**:
1. BRPOP from queue (30s timeout)
2. Acquire semaphore
3. Update task → RUNNING
4. Create scan on Nessus
5. Poll until complete (30s intervals)
6. Export results to .nessus file
7. Validate results (XML, auth detection)
8. Update task → COMPLETED/FAILED
9. Release semaphore

**Validation Step**:
- Parse .nessus XML
- Check host count
- Detect authentication status via Plugin 19506
- Count severity breakdown
- Store validation_stats in task.json

### 5. Scanner Layer

**Technology**: httpx async HTTP client

**Scanner Interface**:
```python
class ScannerInterface:
    async def create_scan(request: ScanRequest) -> int
    async def launch_scan(scan_id: int) -> None
    async def get_status(scan_id: int) -> dict
    async def export_results(scan_id: int) -> bytes
    async def stop_scan(scan_id: int) -> None
    async def delete_scan(scan_id: int) -> None
```

**Nessus API Authentication**:
1. Fetch X-API-Token from `/nessus6.js`
2. POST `/session` for session token
3. Use both tokens for all requests

---

## Data Flow

### Scan Submission Flow

```
Client                MCP Server           Redis            Worker           Nessus
  │                       │                  │                 │                │
  │── run_untrusted_scan ─▶│                  │                 │                │
  │                       │── create task ───▶│                 │                │
  │                       │◀─ task_id ────────│                 │                │
  │                       │── LPUSH task ────▶│                 │                │
  │◀── {task_id, queued} ─│                  │                 │                │
  │                       │                  │── BRPOP ───────▶│                │
  │                       │                  │◀─ task ─────────│                │
  │                       │                  │                 │── POST /scans ─▶│
  │                       │                  │                 │◀─ scan_id ─────│
  │                       │                  │                 │── poll ────────▶│
  │                       │                  │                 │◀─ status ──────│
  │                       │                  │                 │── export ──────▶│
  │                       │                  │                 │◀─ .nessus ─────│
  │                       │                  │                 │── validate ────│
  │                       │                  │◀─ complete ─────│                │
```

### Result Retrieval Flow

```
Client                MCP Server           Task Manager        Parser
  │                       │                    │                  │
  │── get_scan_results ──▶│                    │                  │
  │                       │── get_task ───────▶│                  │
  │                       │◀─ task.json ───────│                  │
  │                       │── read .nessus ───▶│                  │
  │                       │                    │── parse XML ────▶│
  │                       │                    │◀─ vulns[] ───────│
  │                       │── apply filters ──▶│                  │
  │                       │── apply schema ───▶│                  │
  │                       │── paginate ───────▶│                  │
  │◀── JSON-NL response ──│                    │                  │
```

---

## Configuration

### Scanner Configuration

**File**: `config/scanners.yaml`

```yaml
scanners:
  nessus:  # Pool name
    - instance_id: scanner1
      url: https://nessus1.local:8834
      username: ${NESSUS_USER:-admin}
      password: ${NESSUS_PASS}
      max_concurrent_scans: 2
      enabled: true
    - instance_id: scanner2
      url: https://nessus2.local:8834
      username: ${NESSUS_USER:-admin}
      password: ${NESSUS_PASS}
      max_concurrent_scans: 2
      enabled: true
```

**Environment Variable Substitution**:
- `${VAR}` - Required variable
- `${VAR:-default}` - Variable with default

**Hot Reload**: SIGHUP triggers config reload

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| REDIS_URL | redis://localhost:6379 | Redis connection |
| DATA_DIR | /app/data/tasks | Task storage path |
| SCANNER_CONFIG | /app/config/scanners.yaml | Scanner config path |
| LOG_LEVEL | INFO | Logging level |
| MCP_PORT | 8000 | Server port |

---

## Docker Architecture

### Development Setup

```yaml
services:
  redis:
    image: redis:7-alpine
    networks: [mcp-network]

  mcp-api:
    build: .
    ports: ["8836:8000"]
    depends_on: [redis]
    networks: [mcp-network, nessus-shared_vpn_net]

  worker:
    build: .
    command: python -m worker.scanner_worker
    depends_on: [redis]
    networks: [mcp-network, nessus-shared_vpn_net]
```

### Network Topology

```
┌──────────────────────────────────────────────────────────────┐
│                     Docker Host                               │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │               mcp-network (172.30.0.0/24)               │ │
│  │                                                          │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────┐  │ │
│  │  │  Redis  │  │ MCP API │  │ Worker  │  │scan-target│  │ │
│  │  │ .2:6379 │  │ .5:8000 │  │   .6    │  │    .9     │  │ │
│  │  └─────────┘  └─────────┘  └─────────┘  └───────────┘  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                            │                                  │
│                            │ Bridge                           │
│                            ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │          nessus-shared_vpn_net (172.32.0.0/24)         │ │
│  │                                                          │ │
│  │  ┌───────────┐                                          │ │
│  │  │  Nessus   │                                          │ │
│  │  │  .3:8834  │                                          │ │
│  │  └───────────┘                                          │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### Credential Handling

| Stage | Security |
|-------|----------|
| MCP Request | HTTPS recommended |
| Redis Queue | Internal network only |
| Task Storage | Credentials NOT persisted |
| Nessus API | SSL (self-signed allowed) |
| Logs | Credentials sanitized |

### Network Security

- Redis not exposed externally
- Nessus on isolated network
- Scanner credentials in env vars
- No credential logging

### Future Enhancements

- Credential encryption in transit
- HashiCorp Vault integration
- mTLS for scanner communication

---

## Performance Characteristics

### Timing

| Operation | Typical Duration |
|-----------|------------------|
| Queue enqueue | < 1ms |
| Queue dequeue | 0-30s (blocking) |
| Scan creation | 1-2s |
| Network scan | 5-15 min |
| Auth scan | 8-20 min |
| Result export | 2-5s |
| XML parsing | 10-80ms |

### Throughput

| Configuration | Scans/Hour |
|--------------|------------|
| 1 scanner, concurrent=2 | 8-12 |
| 2 scanners, concurrent=2 | 16-24 |
| 2 scanners, concurrent=5 | 40-60 |

### Resource Usage

| Component | CPU | Memory |
|-----------|-----|--------|
| MCP Server | 0.1-0.5 core | 256-512 MB |
| Worker | 0.2-1 core | 512 MB-1 GB |
| Redis | 0.1 core | 128-256 MB |

---

*Generated: 2025-12-01*
*Source: Consolidated from Phase 0-6 documentation*
