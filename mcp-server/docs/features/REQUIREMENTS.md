# Nessus MCP Server - Requirements

> **[↑ Features Index](README.md)** | **[← Architecture](ARCHITECTURE.md)** | **[Features →](FEATURES.md)**

## Functional Requirements

### FR1: Vulnerability Scanning

| ID | Requirement | Status |
|----|-------------|--------|
| FR1.1 | Submit network-only (untrusted) scans via MCP | ✅ Implemented |
| FR1.2 | Submit SSH-authenticated scans via MCP | ✅ Implemented |
| FR1.3 | Submit privileged scans with sudo escalation | ✅ Implemented |
| FR1.4 | Track scan progress in real-time | ✅ Implemented |
| FR1.5 | Detect authentication success/failure | ✅ Implemented |
| FR1.6 | Support multiple escalation methods (sudo, su, pbrun, dzdo) | ✅ Implemented |

### FR2: Queue Management

| ID | Requirement | Status |
|----|-------------|--------|
| FR2.1 | Async FIFO queue for scan tasks | ✅ Implemented |
| FR2.2 | Dead Letter Queue for failed tasks | ✅ Implemented |
| FR2.3 | Idempotency support for duplicate prevention | ✅ Implemented |
| FR2.4 | Queue position reporting | ✅ Implemented |
| FR2.5 | Estimated wait time calculation | ✅ Implemented |
| FR2.6 | Task filtering by status, target, pool | ✅ Implemented |

### FR3: Results Retrieval

| ID | Requirement | Status |
|----|-------------|--------|
| FR3.1 | Parse Nessus XML results | ✅ Implemented |
| FR3.2 | Schema profiles for field selection | ✅ Implemented |
| FR3.3 | Custom field selection | ✅ Implemented |
| FR3.4 | Generic filtering (string, number, boolean) | ✅ Implemented |
| FR3.5 | Pagination support | ✅ Implemented |
| FR3.6 | JSON-NL output format | ✅ Implemented |

### FR4: Multi-Scanner Support

| ID | Requirement | Status |
|----|-------------|--------|
| FR4.1 | Multi-instance scanner configuration | ✅ Implemented |
| FR4.2 | Scanner pool management | ✅ Implemented |
| FR4.3 | Load-based scanner selection | ✅ Implemented |
| FR4.4 | Per-scanner concurrent scan limits | ✅ Implemented |
| FR4.5 | Hot-reload scanner configuration | ✅ Implemented |
| FR4.6 | Scanner enable/disable without restart | ✅ Implemented |

### FR5: Observability

| ID | Requirement | Status |
|----|-------------|--------|
| FR5.1 | Structured JSON logging | ✅ Implemented |
| FR5.2 | Trace ID propagation | ✅ Implemented |
| FR5.3 | Prometheus metrics endpoint | ✅ Implemented |
| FR5.4 | Health check endpoint | ✅ Implemented |
| FR5.5 | Per-task validation statistics | ✅ Implemented |
| FR5.6 | Authentication status tracking | ✅ Implemented |

---

## Non-Functional Requirements

### NFR1: Performance

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR1.1 | Queue enqueue latency | < 10ms | ✅ Met (<1ms) |
| NFR1.2 | API response latency | < 100ms | ✅ Met (<50ms) |
| NFR1.3 | XML parsing time | < 100ms for 200 vulns | ✅ Met (~80ms) |
| NFR1.4 | Observability overhead | < 1% latency | ✅ Met (<1ms) |
| NFR1.5 | Concurrent scan handling | ≥2 per scanner | ✅ Met (configurable) |

### NFR2: Reliability

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR2.1 | Graceful shutdown | Clean worker stop | ✅ Implemented |
| NFR2.2 | Task timeout protection | 24 hours max | ✅ Implemented |
| NFR2.3 | DLQ for failed tasks | No task loss | ✅ Implemented |
| NFR2.4 | State transition validation | No invalid states | ✅ Implemented |
| NFR2.5 | Health monitoring | Redis + filesystem | ✅ Implemented |

### NFR3: Scalability

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR3.1 | Multiple scanner instances | ≥2 per pool | ✅ Supported |
| NFR3.2 | Multiple scanner pools | ≥2 pools | ✅ Supported |
| NFR3.3 | Queue capacity | Unlimited | ✅ Implemented |
| NFR3.4 | Horizontal worker scaling | Future | 🔮 Planned |

### NFR4: Security

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR4.1 | Credential sanitization in logs | No passwords | ✅ Implemented |
| NFR4.2 | Credentials not persisted | Ephemeral only | ✅ Implemented |
| NFR4.3 | Internal Redis network | Not exposed | ✅ Implemented |
| NFR4.4 | Environment variable secrets | No hardcoding | ✅ Implemented |

### NFR5: Maintainability

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR5.1 | Unit test coverage | ≥70% | ✅ Met (121+ tests) |
| NFR5.2 | Integration test coverage | Key workflows | ✅ Met (26+ tests) |
| NFR5.3 | Structured code organization | Module separation | ✅ Implemented |
| NFR5.4 | Configuration externalization | YAML + env vars | ✅ Implemented |

---

## MCP Tool Requirements

### TR1: run_untrusted_scan

| ID | Requirement | Status |
|----|-------------|--------|
| TR1.1 | Accept target IPs/CIDRs | ✅ |
| TR1.2 | Return task_id and trace_id | ✅ |
| TR1.3 | Report queue position | ✅ |
| TR1.4 | Support scanner pool selection | ✅ |
| TR1.5 | Support idempotency key | ✅ |

### TR2: run_authenticated_scan

| ID | Requirement | Status |
|----|-------------|--------|
| TR2.1 | Accept SSH credentials | ✅ |
| TR2.2 | Validate scan_type parameter | ✅ |
| TR2.3 | Support privilege escalation | ✅ |
| TR2.4 | Detect auth success/failure | ✅ |
| TR2.5 | Include troubleshooting on failure | ✅ |

### TR3: get_scan_status

| ID | Requirement | Status |
|----|-------------|--------|
| TR3.1 | Return current task state | ✅ |
| TR3.2 | Include live progress if running | ✅ |
| TR3.3 | Include results_summary if completed | ✅ |
| TR3.4 | Include authentication_status | ✅ |
| TR3.5 | Include troubleshooting hints | ✅ |

### TR4: get_scan_results

| ID | Requirement | Status |
|----|-------------|--------|
| TR4.1 | Support schema profiles | ✅ |
| TR4.2 | Support custom field selection | ✅ |
| TR4.3 | Support filtering | ✅ |
| TR4.4 | Support pagination | ✅ |
| TR4.5 | Return JSON-NL format | ✅ |

### TR5: list_tasks

| ID | Requirement | Status |
|----|-------------|--------|
| TR5.1 | Filter by status | ✅ |
| TR5.2 | Filter by scanner pool | ✅ |
| TR5.3 | Filter by target (CIDR-aware) | ✅ |
| TR5.4 | Configurable limit | ✅ |

### TR6: Scanner Management Tools

| ID | Requirement | Status |
|----|-------------|--------|
| TR6.1 | list_scanners with load info | ✅ |
| TR6.2 | list_pools | ✅ |
| TR6.3 | get_pool_status with utilization | ✅ |
| TR6.4 | get_queue_status | ✅ |

---

## Integration Requirements

### IR1: Nessus Integration

| ID | Requirement | Status |
|----|-------------|--------|
| IR1.1 | X-API-Token authentication | ✅ Implemented |
| IR1.2 | Session token management | ✅ Implemented |
| IR1.3 | SSL support (self-signed) | ✅ Implemented |
| IR1.4 | Scan create/launch/poll/export | ✅ Implemented |
| IR1.5 | Status mapping to MCP states | ✅ Implemented |

### IR2: Redis Integration

| ID | Requirement | Status |
|----|-------------|--------|
| IR2.1 | FIFO queue with LPUSH/BRPOP | ✅ Implemented |
| IR2.2 | DLQ with sorted set | ✅ Implemented |
| IR2.3 | Health check via PING | ✅ Implemented |
| IR2.4 | Connection pooling | ✅ Implemented |

### IR3: Docker Integration

| ID | Requirement | Status |
|----|-------------|--------|
| IR3.1 | Multi-service compose | ✅ Implemented |
| IR3.2 | Health checks | ✅ Implemented |
| IR3.3 | Network isolation | ✅ Implemented |
| IR3.4 | Volume persistence | ✅ Implemented |

---

## Test Requirements

### TestR1: Unit Tests

| ID | Requirement | Count | Status |
|----|-------------|-------|--------|
| TestR1.1 | Task Manager tests | 16 | ✅ |
| TestR1.2 | Nessus Validator tests | 18 | ✅ |
| TestR1.3 | Authenticated Scan tests | 18 | ✅ |
| TestR1.4 | Schema/Parser tests | 20+ | ✅ |
| TestR1.5 | Logging/Metrics tests | 55+ | ✅ |

### TestR2: Integration Tests

| ID | Requirement | Count | Status |
|----|-------------|-------|--------|
| TestR2.1 | MCP E2E tests | 15 | ✅ |
| TestR2.2 | Authenticated scan workflow | 8 | ✅ |
| TestR2.3 | Queue accuracy tests | 4 | ✅ |
| TestR2.4 | Failure mode tests | 3 | ✅ |

### TestR3: Test Infrastructure

| ID | Requirement | Status |
|----|-------------|--------|
| TestR3.1 | Scan target container | ✅ Implemented |
| TestR3.2 | Test users with varied sudo | ✅ Implemented |
| TestR3.3 | Network connectivity tests | ✅ Implemented |

---

## Dependency Requirements

### Core Dependencies

| Package | Version | Required |
|---------|---------|----------|
| Python | ≥3.12 | Yes |
| fastmcp | 2.13.0.2 | Yes |
| mcp | ≥1.18.0 | Yes |
| starlette | 0.49.1 (PINNED) | Yes |
| anyio | 4.6.2.post1 (PINNED) | Yes |
| uvicorn | 0.38.0 | Yes |
| httpx | ≥0.27.0 | Yes |
| redis | ≥5.0.0 | Yes |
| structlog | 24.1.0 | Yes |
| prometheus-client | ≥0.20.0 | Yes |
| pyyaml | ≥6.0.1 | Yes |

### Infrastructure Dependencies

| Component | Version | Required |
|-----------|---------|----------|
| Redis | ≥7.0 | Yes |
| Nessus | ≥10.0 | Yes |
| Docker | ≥24.0 | Recommended |
| Docker Compose | ≥2.0 | Recommended |

---

## Future Requirements (Not Implemented)

### Phase 7 (Planned)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR7.1 | Scan cancellation | Medium |
| FR7.2 | Batch scan submission | Medium |

### Phase 8 (Planned)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR8.1 | Webhook notifications | Low |
| FR8.2 | Scheduled scans | Low |

### Phase 9 (Planned)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR9.1 | Multi-worker scaling | Medium |
| FR9.2 | Horizontal autoscaling | Low |

---

*Generated: 2025-12-01*
*Source: Consolidated from Phase 0-6 documentation*
