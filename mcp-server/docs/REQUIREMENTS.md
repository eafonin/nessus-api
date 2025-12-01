# Nessus MCP Server - Requirements

> **Last Updated**: 2025-12-01
> **Purpose**: Living traceability matrix linking requirements to implementation

---

## Functional Requirements (FR)

### Scan Operations

| ID | Requirement | Status | Implementation |
|----|-------------|--------|----------------|
| FR-01 | Submit untrusted (network-only) scans | DONE | `run_untrusted_scan` tool |
| FR-02 | Submit authenticated scans (SSH) | DONE | `run_authenticated_scan` tool |
| FR-03 | Submit privileged scans (SSH + sudo/su) | DONE | `run_authenticated_scan` with `elevate_privileges_with` |
| FR-04 | Cancel running scans | PARTIAL | Housekeeping stops stale scans |
| FR-05 | Retry failed scans | DONE | Admin CLI `retry-dlq` command |

### Status & Results

| ID | Requirement | Status | Implementation |
|----|-------------|--------|----------------|
| FR-10 | Get scan status | DONE | `get_scan_status` tool |
| FR-11 | Get queue position | DONE | Returned in scan submission response |
| FR-12 | Get paginated results | DONE | `get_scan_results` with `page`/`page_size` |
| FR-13 | Filter results by severity | DONE | `filters={"severity": "4"}` |
| FR-14 | Filter results by CVSS | DONE | `filters={"cvss_score": ">=7.0"}` |
| FR-15 | Filter results by CVE | DONE | `filters={"cve": "CVE-2021"}` |
| FR-16 | Custom field selection | DONE | `custom_fields` parameter |
| FR-17 | Schema profiles (minimal/summary/brief/full) | DONE | `schema_profile` parameter |

### Infrastructure

| ID | Requirement | Status | Implementation |
|----|-------------|--------|----------------|
| FR-20 | List available scanners | DONE | `list_scanners` tool |
| FR-21 | List scanner pools | DONE | `list_pools` tool |
| FR-22 | Get pool status/capacity | DONE | `get_pool_status` tool |
| FR-23 | Get queue status | DONE | `get_queue_status` tool |
| FR-24 | List recent tasks | DONE | `list_tasks` tool |

---

## Non-Functional Requirements (NFR)

### Performance

| ID | Requirement | Target | Actual | Status |
|----|-------------|--------|--------|--------|
| NFR-01 | Scan submission latency | < 500ms | ~200ms | PASS |
| NFR-02 | Status query latency | < 100ms | ~50ms | PASS |
| NFR-03 | Concurrent scans per scanner | 2-5 | Configurable | PASS |
| NFR-04 | Queue throughput | 100 tasks/min | Untested | - |

### Reliability

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-10 | Task persistence | Survive restart | DONE (file-based) |
| NFR-11 | Dead Letter Queue | Capture failed tasks | DONE |
| NFR-12 | Idempotency | Prevent duplicate scans | DONE (48h TTL) |
| NFR-13 | Stale scan cleanup | Auto-stop after 24h | DONE |
| NFR-14 | TTL housekeeping | Delete old tasks | DONE (7d/30d) |

### Observability

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-20 | Prometheus metrics | /metrics endpoint | DONE |
| NFR-21 | Structured logging | JSON format | DONE |
| NFR-22 | Trace ID propagation | All operations | DONE |
| NFR-23 | Health check | /health endpoint | DONE |

### Security

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-30 | Credential handling | No plaintext logging | DONE |
| NFR-31 | Scanner TLS | HTTPS with self-signed | DONE |
| NFR-32 | Network isolation | Docker network | DONE |

---

## MCP Tool Requirements (TR)

### run_untrusted_scan

| ID | Requirement | Status |
|----|-------------|--------|
| TR-01.1 | Accept targets parameter | DONE |
| TR-01.2 | Accept name parameter | DONE |
| TR-01.3 | Accept schema_profile parameter | DONE |
| TR-01.4 | Accept idempotency_key parameter | DONE |
| TR-01.5 | Accept scanner_pool parameter | DONE |
| TR-01.6 | Return task_id and trace_id | DONE |
| TR-01.7 | Return queue_position | DONE |

### run_authenticated_scan

| ID | Requirement | Status |
|----|-------------|--------|
| TR-02.1 | Accept SSH credentials | DONE |
| TR-02.2 | Support sudo escalation | DONE |
| TR-02.3 | Support su escalation | DONE |
| TR-02.4 | Detect authentication success | DONE |

### get_scan_results

| ID | Requirement | Status |
|----|-------------|--------|
| TR-03.1 | Return JSON-NL format | DONE |
| TR-03.2 | Support pagination | DONE |
| TR-03.3 | Support page=0 (all data) | DONE |
| TR-03.4 | Echo applied filters | DONE |
| TR-03.5 | Include scan metadata | DONE |

---

## Integration Requirements (IR)

### Nessus Integration

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| IR-01 | Native async Nessus API | DONE | `scanners/nessus_scanner.py` |
| IR-02 | Create scans | DONE | POST /scans |
| IR-03 | Launch scans | DONE | POST /scans/{id}/launch |
| IR-04 | Poll scan status | DONE | GET /scans/{id} |
| IR-05 | Export results (.nessus) | DONE | POST /scans/{id}/export |
| IR-06 | Stop scans | DONE | POST /scans/{id}/stop |
| IR-07 | Delete scans | DONE | DELETE /scans/{id} |
| IR-08 | Multi-scanner support | DONE | Pool-based registry |

### Redis Integration

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| IR-10 | Task queue (FIFO) | DONE | LPUSH/BRPOP |
| IR-11 | Dead Letter Queue | DONE | ZADD with timestamp |
| IR-12 | Idempotency storage | DONE | SET with NX and TTL |
| IR-13 | Blocking dequeue | DONE | BRPOP with timeout |
| IR-14 | Multi-pool support | DONE | `{pool}:queue` keys |

### Docker Integration

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| IR-20 | Multi-container deployment | DONE | redis, mcp-api, worker |
| IR-21 | Shared volume for tasks | DONE | /app/data/tasks |
| IR-22 | Health checks | DONE | Redis ping, HTTP /health |
| IR-23 | Auto-restart | DONE | `restart: unless-stopped` |
| IR-24 | External scanner network | DONE | `scanner_bridge` network |

---

## Test Requirements (TestR)

| ID | Requirement | Status | Coverage |
|----|-------------|--------|----------|
| TestR-01 | Unit tests | PARTIAL | ~40% |
| TestR-02 | Integration tests (real Nessus) | DONE | Phase 0+1 tests |
| TestR-03 | Schema profile tests | DONE | All 4 profiles |
| TestR-04 | Filter tests | DONE | All filter types |
| TestR-05 | Queue operation tests | DONE | Enqueue/dequeue/DLQ |

---

## Dependency Requirements

### Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| fastmcp | 2.2.7 | MCP server framework |
| httpx | >=0.27 | Async HTTP client |
| redis | >=5.0 | Redis client |
| prometheus-client | >=0.21 | Metrics |
| pyyaml | >=6.0 | Scanner config parsing |
| uvicorn | >=0.34 | ASGI server |

### Infrastructure

| Component | Version | Purpose |
|-----------|---------|---------|
| Redis | 7.x | Task queue, state |
| Docker | 24+ | Container runtime |
| Nessus | 10.x | Vulnerability scanner |

---

## Future Roadmap

### Planned (Not Implemented)

| ID | Feature | Priority |
|----|---------|----------|
| FUTURE-01 | Webhook notifications on completion | Medium |
| FUTURE-02 | Scheduled scans (cron-like) | Medium |
| FUTURE-03 | OR filter logic | Low |
| FUTURE-04 | Regex filtering | Low |
| FUTURE-05 | OpenVAS scanner support | Low |
| FUTURE-06 | WinRM authentication | Medium |
| FUTURE-07 | Result aggregation dashboard | Medium |
| FUTURE-08 | API rate limiting | Medium |

---

## Cross-References

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: System design
- **[FEATURES.md](FEATURES.md)**: Feature documentation
- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Operational guidance

---

*Requirements document generated from source code analysis*
