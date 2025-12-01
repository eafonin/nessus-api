# Nessus MCP Server - Architecture v2.3

> Production-grade MCP server with pool-based scanning, authenticated scans, and comprehensive observability
> Updated: 2025-12-01 | Status: Production-Ready (Phases 0-6 Complete)

---

## Quick Navigation

- [1. System Overview](#1-system-overview)
- [2. Container Architecture](#2-container-architecture)
- [3. Data Flow](#3-data-flow)
- [4. Component Details](#4-component-details)
- [5. Configuration](#5-configuration)

---

## 1. System Overview

### 1.1 Key Capabilities

| Capability | Description |
|------------|-------------|
| **Pool-Based Scanning** | Isolated scanner groups with load-based routing |
| **Authenticated Scans** | SSH credentials with privilege escalation |
| **Async Queue Processing** | Redis-backed FIFO with dead letter queue |
| **Result Transformation** | XML to JSON-NL with schema profiles |
| **Production Observability** | Prometheus metrics, structured logging |
| **Resilience** | Circuit breaker, TTL housekeeping, DLQ CLI |

### 1.2 Architecture Principles

1. **Queue Everything** - Accept all valid requests, process asynchronously
2. **Single Writer** - TaskManager owns all state transitions
3. **Pool Isolation** - Scanner pools enable network segmentation
4. **Fail Gracefully** - Circuit breakers prevent cascading failures
5. **Observable by Default** - Metrics and logs at every layer

---

## 2. Container Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Docker Host                                      │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Docker Compose Network                           │ │
│  │                                                                     │ │
│  │  ┌─────────────────┐     ┌──────────────────┐                      │ │
│  │  │   MCP API       │     │     Redis        │                      │ │
│  │  │   Port: 8836    │────▶│   Port: 6379     │                      │ │
│  │  │                 │     │                  │                      │ │
│  │  │  Endpoints:     │     │  Keys:           │                      │ │
│  │  │  • /sse (MCP)   │     │  • {pool}:queue  │                      │ │
│  │  │  • /health      │     │  • {pool}:dead   │                      │ │
│  │  │  • /metrics     │     │  • idemp:*       │                      │ │
│  │  └─────────────────┘     └──────────────────┘                      │ │
│  │           │                       │                                 │ │
│  │           │    ┌──────────────────┴───────────────┐                │ │
│  │           │    │      Shared Volume: /app/data    │                │ │
│  │           │    │                                  │                │ │
│  │           │    │  tasks/{task_id}/                │                │ │
│  │           │    │  ├── task.json                   │                │ │
│  │           │    │  ├── scan_native.nessus          │                │ │
│  │           │    │  └── scanner_logs/               │                │ │
│  │           │    └──────────────────┬───────────────┘                │ │
│  │           │                       │                                 │ │
│  │  ┌────────▼───────────────────────▼───────────────────────────┐   │ │
│  │  │                   Scanner Worker                            │   │ │
│  │  │                                                             │   │ │
│  │  │  Features:                                                  │   │ │
│  │  │  • Multi-pool subscription (WORKER_POOLS)                   │   │ │
│  │  │  • Concurrent task processing                               │   │ │
│  │  │  • Result validation with auth detection                    │   │ │
│  │  │  • Circuit breaker protection                               │   │ │
│  │  │  • TTL housekeeping (background task)                       │   │ │
│  │  └────────────────────────┬────────────────────────────────────┘   │ │
│  │                           │                                         │ │
│  │                           ▼                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────┐   │ │
│  │  │                    Scanner Pool: nessus                      │   │ │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │   │ │
│  │  │  │  scanner1   │  │  scanner2   │  │  scanner3   │          │   │ │
│  │  │  │  2/2 active │  │  1/2 active │  │  0/2 active │          │   │ │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘          │   │ │
│  │  └─────────────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Services

| Service | Purpose | Health Check |
|---------|---------|--------------|
| `redis` | Task queue, idempotency, scanner state | `redis-cli ping` |
| `mcp-api` | MCP protocol server, HTTP endpoints | `curl /health` |
| `scanner-worker` | Async task processing, Nessus integration | Redis ping |

### 2.2 Volumes

| Volume | Path | Purpose |
|--------|------|---------|
| `redis-data` | `/data` | Queue persistence |
| `task-data` | `/app/data` | Task metadata and results |
| `config` | `/app/config` | Scanner configuration (read-only) |

---

## 3. Data Flow

### 3.1 Scan Submission Flow

```
Client                    MCP API                   Redis                   Worker
  │                          │                        │                        │
  │  run_untrusted_scan()    │                        │                        │
  ├─────────────────────────▶│                        │                        │
  │                          │                        │                        │
  │                          │  Check idempotency     │                        │
  │                          ├───────────────────────▶│                        │
  │                          │◀───────────────────────┤                        │
  │                          │                        │                        │
  │                          │  Select scanner        │                        │
  │                          │  (lowest utilization)  │                        │
  │                          │                        │                        │
  │                          │  Create task.json      │                        │
  │                          │  Enqueue task          │                        │
  │                          ├───────────────────────▶│                        │
  │                          │                        │                        │
  │  {task_id, status:queued}│                        │                        │
  │◀─────────────────────────┤                        │                        │
  │                          │                        │  BRPOP task            │
  │                          │                        │◀───────────────────────┤
  │                          │                        │                        │
  │                          │                        │                        │  ┌─────────────┐
  │                          │                        │                        │─▶│   Nessus    │
  │                          │                        │                        │  │   Scanner   │
  │                          │                        │                        │◀─│             │
  │                          │                        │                        │  └─────────────┘
  │                          │                        │                        │
  │                          │                        │                        │  Validate results
  │                          │                        │                        │  Update task.json
  │                          │                        │                        │
```

### 3.2 State Machine

```
                    ┌──────────────────┐
                    │      QUEUED      │
                    │   (API enqueues) │
                    └────────┬─────────┘
                             │
                             │ Worker dequeues (BRPOP)
                             ▼
                    ┌──────────────────┐
                    │     RUNNING      │
                    │ (Worker polling) │
                    └────────┬─────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
  │    COMPLETED    │ │     FAILED      │ │    TIMEOUT      │
  │  (results OK)   │ │  (error/auth)   │ │  (24h limit)    │
  └─────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                    │
         │                   └──────────┬─────────┘
         │                              │
         │                              ▼
         │                    ┌─────────────────┐
         │                    │   Dead Letter   │
         │                    │     Queue       │
         │                    └─────────────────┘
         │
         ▼
  ┌─────────────────┐
  │  TTL Cleanup    │
  │  (7 days)       │
  └─────────────────┘
```

---

## 4. Component Details

### 4.1 MCP API Server

**Technology:** FastMCP with SSE transport

**MCP Tools:**
| Tool | Purpose |
|------|---------|
| `run_untrusted_scan` | Network-only scan |
| `run_authenticated_scan` | SSH-authenticated scan |
| `get_scan_status` | Task status with validation data |
| `get_scan_results` | Paginated JSON-NL results |
| `list_tasks` | Task listing with filters |
| `list_scanners` | Scanner instances with load info |
| `list_pools` | Available scanner pools |
| `get_pool_status` | Pool capacity and utilization |
| `get_queue_status` | Redis queue metrics |

**HTTP Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sse` | GET | MCP protocol (Server-Sent Events) |
| `/health` | GET | Health check (200/503) |
| `/metrics` | GET | Prometheus metrics |

---

### 4.2 Scanner Worker

**Technology:** Python asyncio with httpx

**Processing Loop:**
1. BRPOP from pool queue(s) with 5s timeout
2. Parse task, acquire scanner
3. Create scan in Nessus with credentials
4. Launch scan, poll status every 30s
5. Export results on completion
6. Validate results (auth detection)
7. Update task.json with validation metadata
8. Move to DLQ on failure

**Background Tasks:**
- TTL housekeeping (hourly)
- Metrics update (30s)

---

### 4.3 Scanner Registry

**Technology:** YAML configuration with env var substitution

**Pool Architecture:**
```yaml
# config/scanners.yaml
nessus:                    # Pool name
  scanner1:                # Instance ID
    name: "Primary"
    url: "https://..."
    username: "${NESSUS_USERNAME}"
    password: "${NESSUS_PASSWORD}"
    enabled: true
    max_concurrent_scans: 2

nessus_dmz:               # Separate pool
  dmz_scanner:
    name: "DMZ Scanner"
    url: "https://..."
```

**Load Balancing:**
- Calculate utilization: `active / max_concurrent`
- Select scanner with lowest utilization
- Tie-breaker: first available

---

### 4.4 Result Transformation

**Pipeline:**
```
.nessus (XML)
    │
    ├── XML Parser (parser.py)
    │   └── Extract hosts, vulnerabilities, metadata
    │
    ├── Schema Profile (profiles.py)
    │   └── Field selection (minimal|summary|brief|full)
    │
    ├── Filter Engine (filters.py)
    │   └── Type-aware filtering (AND logic)
    │
    └── JSON-NL Converter (converter.py)
        └── Paginated output with schema header
```

**JSON-NL Format:**
```
{"type":"schema","profile":"brief","total_vulnerabilities":42,...}
{"type":"scan_metadata","scan_name":"Test",...}
{"type":"vulnerability","host":"192.168.1.1",...}
{"type":"pagination","page":1,"has_next":true,...}
```

---

### 4.5 Observability Stack

**Metrics (Prometheus):**
```
# Core metrics
nessus_scans_total{scan_type,status}
nessus_active_scans
nessus_task_duration_seconds

# Pool metrics
nessus_pool_queue_depth{pool}
nessus_validation_failures_total{pool,reason}
nessus_auth_failures_total{pool,scan_type}
```

**Logging (structlog):**
```json
{
  "timestamp": "2025-12-01T12:00:00.000000Z",
  "level": "info",
  "trace_id": "abc123",
  "task_id": "ne_prod_...",
  "event": "scan_completed",
  "authentication_status": "success"
}
```

---

### 4.6 Resilience Patterns

**Circuit Breaker:**
```
CLOSED ──(5 failures)──▶ OPEN ──(300s cooldown)──▶ HALF_OPEN
   ▲                                                    │
   │                                                    │
   └────────────(2 successes)───────────────────────────┘
```

**DLQ Handling:**
- Failed tasks moved to sorted set with timestamp
- Admin CLI for inspection and retry
- Configurable retention (30 days default)

**TTL Housekeeping:**
- Completed tasks: 7 days
- Failed tasks: 30 days
- Running/queued: never deleted

---

## 5. Configuration

### 5.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `DATA_DIR` | `/app/data/tasks` | Task storage |
| `SCANNER_CONFIG` | `/app/config/scanners.yaml` | Scanner registry |
| `LOG_LEVEL` | `INFO` | Log verbosity |
| `MAX_CONCURRENT_SCANS` | `2` | Per-scanner limit |
| `WORKER_POOLS` | `nessus` | Pools to subscribe |

### 5.2 Docker Compose

**Development:**
```bash
cd mcp-server
docker compose up -d
docker compose logs -f worker
```

**Production:**
```bash
cd mcp-server/prod
docker compose -f docker-compose.yml up -d
```

### 5.3 Quick Commands

```bash
# Health check
curl http://localhost:8836/health

# Prometheus metrics
curl http://localhost:8836/metrics

# Queue status
docker exec nessus-mcp-redis redis-cli LLEN nessus:queue

# DLQ inspection
python -m tools.admin_cli list-dlq --pool nessus

# Hot reload config
kill -SIGHUP $(pgrep -f scanner_worker)
```

---

## Appendix: Version History

| Version | Date | Changes |
|---------|------|---------|
| v2.3 | 2025-12-01 | Phases 4-6 complete: pools, auth scans, resilience |
| v2.2 | 2025-11-08 | Phases 0-3: foundation, queue, observability |
| v2.1 | 2025-11-01 | Initial architecture design |
