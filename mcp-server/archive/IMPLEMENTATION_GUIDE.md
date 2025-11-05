# Nessus MCP Server - Implementation Guide

> **Version**: 2.2
> **Last Updated**: 2025-11-01
> **Status**: Implementation Checklist

This guide provides a structured checklist for implementing the Nessus MCP Server based on ARCHITECTURE_v2.2.md.

---

## Phase 1: Core Infrastructure Setup

### 1.1 Project Structure
- [ ] Create directory structure (scanners/, core/, schema/, tools/, tests/)
- [ ] Add __init__.py files to all packages
- [ ] Create requirements-api.txt with FastMCP, httpx, redis, prometheus_client
- [ ] Create requirements-worker.txt with httpx, redis, asyncio
- [ ] Create requirements-dev.txt with pytest, pytest-asyncio, inline-snapshot
- [ ] Create Dockerfile.api for MCP API service
- [ ] Create Dockerfile.worker for scanner worker service
- [ ] Create docker-compose.yml with redis, mcp-api, scanner-worker services

### 1.2 Redis Configuration
- [ ] Define Redis key schemas in documentation
  - [ ] Queue: `nessus:queue` (FIFO list)
  - [ ] Dead Letter Queue: `nessus:queue:dead` (sorted set)
  - [ ] Scanner Registry: `nessus:scanners:{scanner_type}:{instance_id}` (hash)
  - [ ] Idempotency Keys: `idemp:{key}` (string, 48h TTL)
  - [ ] Task Metadata: `task:{task_id}:metadata` (hash)
- [ ] Configure Redis connection pooling in core/redis.py
- [ ] Add Redis health checks to docker-compose.yml
- [ ] Implement Redis reconnection logic with exponential backoff

### 1.3 Configuration System
- [ ] Create config/scanners.yaml for scanner instance definitions
- [ ] Implement environment variable overrides (REDIS_URL, LOG_LEVEL, etc.)
- [ ] Add configuration validation at startup
- [ ] Create config loader in core/config.py

---

## Phase 2: State Management & Idempotency

### 2.1 Task Manager (Single Writer Pattern)
- [ ] Implement `core/task_manager.py` with TaskManager class
- [ ] Add state transition validation with VALID_TRANSITIONS dict
- [ ] Implement file locking (fcntl) for atomic task.json updates
- [ ] Define ScanState enum (QUEUED, RUNNING, COMPLETED, FAILED, TIMEOUT)
- [ ] Add StateTransitionError exception class
- [ ] Implement transition_state() method with trace_id logging
- [ ] Add task creation method (create_task)
- [ ] Add task retrieval method (get_task)
- [ ] Implement task deletion with TTL support

### 2.2 Idempotency System
- [ ] Implement `core/idempotency.py` with IdempotencyManager class
- [ ] Add extract_idempotency_key() function (header OR tool arg)
- [ ] Implement check() method to verify existing idempotency keys
- [ ] Implement store() method using Redis SETNX (atomic)
- [ ] Add request hash calculation (_hash_request using SHA256)
- [ ] Implement ConflictError for hash mismatches (409 response)
- [ ] Add 48-hour TTL for idempotency keys
- [ ] Write unit tests for idempotency key validation

### 2.3 Trace ID System
- [ ] Implement `core/middleware.py` with TraceMiddleware class
- [ ] Generate trace_id per HTTP request (UUID4)
- [ ] Propagate trace_id via request.state
- [ ] Add trace_id to all log messages
- [ ] Include trace_id in Task dataclass
- [ ] Add trace_id to queue messages
- [ ] Return trace_id in all tool responses
- [ ] Add X-Trace-Id response header

---

## Phase 3: Scanner Abstraction Layer

### 3.1 Scanner Interface
- [ ] Define `scanners/base.py` with ScannerInterface ABC
  - [ ] create_scan(request: ScanRequest) -> int
  - [ ] launch_scan(scan_id: int) -> bool
  - [ ] get_status(scan_id: int) -> Dict
  - [ ] get_results(scan_id: int, filters: Dict) -> Dict
  - [ ] pause_scan(scan_id: int) -> bool
  - [ ] resume_scan(scan_id: int) -> bool
  - [ ] stop_scan(scan_id: int) -> bool
  - [ ] delete_scan(scan_id: int) -> bool
- [ ] Define ScanRequest dataclass
- [ ] Add scanner type detection logic

### 3.2 Native Async Nessus Scanner
- [ ] Implement `scanners/nessus.py` with NessusScanner class
- [ ] Use httpx.AsyncClient for all API calls (no subprocess)
- [ ] Implement async _authenticate() method
- [ ] Implement async _get_session() with connection pooling
- [ ] Add template UUID mapping for scan types
  - [ ] UNTRUSTED: "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66"
  - [ ] TRUSTED: TBD
  - [ ] WEB_APP: "e9cfb74f-947b-8fa7-f0c7-f3fbbe1c520a878248c99a5ba89c"
- [ ] Implement create_scan() with policy/target configuration
- [ ] Implement launch_scan() wrapper
- [ ] Implement get_status() with progress calculation
- [ ] Implement get_results() with result fetching
- [ ] Add _map_nessus_status() for state mapping:
  - [ ] pending → queued
  - [ ] running → running
  - [ ] paused → running
  - [ ] completed → completed
  - [ ] canceled/stopped/aborted → failed
- [ ] Implement pause_scan(), resume_scan(), stop_scan(), delete_scan()
- [ ] Add error handling for 401, 403, 404, 500 responses
- [ ] Implement session cleanup in __del__ or context manager

### 3.3 Scanner Registry
- [ ] Implement `scanners/registry.py` with ScannerRegistry class
- [ ] Load scanner instances from config/scanners.yaml at startup
- [ ] Register scanners in Redis with heartbeat mechanism
- [ ] Implement get_available_scanner() for round-robin selection
- [ ] Add scanner health checks (ping endpoint)
- [ ] Implement scanner disable/enable logic
- [ ] Track last_used_at timestamp for each scanner

---

## Phase 4: MCP Tools Implementation

### 4.1 Tool Registration
- [ ] Create `tools/__init__.py` with FastMCP instance
- [ ] Configure FastMCP with server name "nessus-mcp-server"
- [ ] Add TraceMiddleware to FastAPI app
- [ ] Mount /metrics endpoint for Prometheus

### 4.2 Core Scan Tools
- [ ] Implement run_untrusted_scan() tool
  - [ ] Add all parameters (targets, name, description, schema_profile, scanner_type, scanner_instance, debug_mode, idempotency_key)
  - [ ] Extract trace_id from request.state
  - [ ] Extract and validate idempotency_key
  - [ ] Check idempotency and return existing task if found
  - [ ] Select scanner instance via ScannerRegistry
  - [ ] Create Task with TaskManager
  - [ ] Enqueue task to Redis `nessus:queue`
  - [ ] Store idempotency key if provided
  - [ ] Return task_id, trace_id, status, scanner_instance
- [ ] Implement run_trusted_scan() tool (similar to untrusted)
- [ ] Implement run_web_app_scan() tool
- [ ] Add input validation for targets (CIDR, IP, hostname)
- [ ] Add schema_profile validation (minimal, summary, brief, full, custom)

### 4.3 Status & Control Tools
- [ ] Implement get_scan_status() tool
  - [ ] Fetch task metadata from TaskManager
  - [ ] Call scanner.get_status() for live progress
  - [ ] Return task_id, trace_id, status, progress, scanner_instance, nessus_scan_id, timestamps
- [ ] Implement pause_scan() tool
- [ ] Implement resume_scan() tool
- [ ] Implement stop_scan() tool
- [ ] Implement delete_scan() tool

### 4.4 Results & Data Tools
- [ ] Implement get_scan_results() tool
  - [ ] Accept filters (severity, plugin_id, cve, host, port, exploit_available)
  - [ ] Accept pagination (page, page_size)
  - [ ] Accept schema_profile (minimal|summary|brief|full) OR custom_fields (mutually exclusive)
  - [ ] Validate mutual exclusivity: raise ValueError if both schema_profile and custom_fields provided
  - [ ] Call NessusToJsonNL.convert() for formatting
  - [ ] Return JSON-NL string with schema line containing filters_applied
- [ ] Implement export_scan() tool
  - [ ] Support formats: nessus (native), pdf, html, csv
  - [ ] Use scanner.export_scan() or local generation
  - [ ] Return file_path or download_url
- [ ] Implement list_scans() tool
  - [ ] Support filtering by status, scanner_type, date_range
  - [ ] Return array of task summaries

### 4.5 Scanner Management Tools
- [ ] Implement list_scanners() tool
  - [ ] Query ScannerRegistry
  - [ ] Return scanner_type, instance_id, enabled, last_heartbeat
- [ ] Implement get_scanner_health() tool
  - [ ] Check Redis connectivity
  - [ ] Check scanner API endpoints
  - [ ] Return overall health status

---

## Phase 5: Worker Implementation

### 5.1 Queue Consumer
- [ ] Create `worker/scanner_worker.py` with main worker loop
- [ ] Implement async queue polling (BRPOP on `nessus:queue`)
- [ ] Add graceful shutdown on SIGTERM/SIGINT
- [ ] Implement max_concurrent_scans limit (default 5)
- [ ] Add worker heartbeat to Redis

### 5.2 Task Execution
- [ ] Implement process_task(task: Task) async function
- [ ] Transition state to RUNNING via TaskManager
- [ ] Instantiate scanner from ScannerRegistry
- [ ] Call scanner.create_scan() with task payload
- [ ] Store nessus_scan_id in task metadata
- [ ] Call scanner.launch_scan()
- [ ] Poll scanner.get_status() until terminal state
- [ ] Transition to COMPLETED or FAILED based on result
- [ ] Add timeout handling (default 24h, transition to TIMEOUT)

### 5.3 Error Handling & DLQ
- [ ] Implement retry logic with exponential backoff (3 retries)
- [ ] Move failed tasks to `nessus:queue:dead` after max retries
- [ ] Log all errors with trace_id
- [ ] Increment prometheus counter for DLQ additions
- [ ] Add manual DLQ inspection tool (admin)

---

## Phase 6: JSON-NL Converter & Schema System

### 6.1 Schema Definitions
- [ ] Create `schema/profiles.py` with SCHEMAS dict
  - [ ] minimal: 6 fields (host, plugin_id, severity, cve, cvss_score, exploit_available)
  - [ ] summary: +3 fields (plugin_name, cvss3_base_score, synopsis)
  - [ ] brief: +2 fields (description, solution)
  - [ ] full: None (all fields)
- [ ] Add schema validation logic
- [ ] Support custom field lists

### 6.2 JSON-NL Converter
- [ ] Implement `schema/jsonl_converter.py` with NessusToJsonNL class
- [ ] Implement convert() method
  - [ ] Line 1: Schema definition with filters_applied echo
  - [ ] Line 2: Scan metadata (scan_id, name, targets, timestamps)
  - [ ] Lines 3+: Vulnerability objects (one per line)
  - [ ] Last line: Pagination metadata (page, total_pages, total_vulns)
- [ ] Add severity mapping (Critical=4, High=3, Medium=2, Low=1, Info=0)
- [ ] Implement filtering logic (severity, plugin_id, cve, host, port, exploit_available)
- [ ] Implement pagination (page, page_size)
- [ ] Add field projection based on schema_profile

### 6.3 Filter Echo Implementation
- [ ] Include filters_applied in first JSON-NL line
- [ ] Normalize filter values for consistent echoing
- [ ] Add comment explaining rationale for LLM reasoning

---

## Phase 7: Observability & Monitoring

### 7.1 Structured Logging
- [ ] Configure JSON logging with trace_id in all messages
- [ ] Add log levels (DEBUG, INFO, WARNING, ERROR)
- [ ] Log key events:
  - [ ] Tool invocations (with trace_id, tool_name, args)
  - [ ] State transitions (with trace_id, task_id, old_state, new_state)
  - [ ] Scanner API calls (with trace_id, endpoint, status_code)
  - [ ] Errors (with trace_id, exception, stack_trace)
- [ ] Use structured logging library (e.g., structlog)

### 7.2 Prometheus Metrics
- [ ] Implement `core/metrics.py` with metrics definitions
  - [ ] scans_total (Counter, labels: scan_type, status)
  - [ ] api_requests_total (Counter, labels: tool, status)
  - [ ] active_scans (Gauge)
  - [ ] scanner_instances (Gauge, labels: scanner_type, enabled)
  - [ ] queue_depth (Gauge, labels: queue=[main|dead])
  - [ ] task_duration_seconds (Histogram)
  - [ ] ttl_deletions_total (Counter)
  - [ ] dlq_size (Gauge)
- [ ] Instrument all tools with api_requests_total
- [ ] Update active_scans on state transitions
- [ ] Update queue_depth on enqueue/dequeue
- [ ] Record task_duration_seconds on completion
- [ ] Mount /metrics endpoint with generate_latest()

### 7.3 Health Checks
- [ ] Implement /health endpoint for API service
  - [ ] Check Redis connectivity (PING)
  - [ ] Check filesystem writability (touch test file)
  - [ ] Return 200 OK if healthy, 503 if unhealthy
- [ ] Implement worker health check script
  - [ ] Check Redis connectivity
  - [ ] Check last heartbeat timestamp
  - [ ] Exit 0 if healthy, 1 if unhealthy
- [ ] Add healthchecks to docker-compose.yml

---

## Phase 8: Testing Infrastructure

### 8.1 Unit Tests
- [ ] Create `tests/test_idempotency.py`
  - [ ] Test header-only idempotency
  - [ ] Test tool-arg-only idempotency
  - [ ] Test header+arg match (success)
  - [ ] Test header+arg mismatch (409 error)
  - [ ] Test hash mismatch (409 error)
- [ ] Create `tests/test_state_machine.py`
  - [ ] Test valid transitions
  - [ ] Test invalid transitions (StateTransitionError)
  - [ ] Test concurrent updates (file locking)
- [ ] Create `tests/test_scanner_nessus.py`
  - [ ] Mock httpx.AsyncClient
  - [ ] Test authentication flow
  - [ ] Test scan creation
  - [ ] Test status mapping
  - [ ] Test error handling (401, 404, 500)

### 8.2 Integration Tests
- [ ] Create `tests/test_full_workflow.py`
  - [ ] Test end-to-end untrusted scan
  - [ ] Test idempotent retry (same task_id returned)
  - [ ] Test status polling until completion
  - [ ] Test result retrieval with filters
  - [ ] Test pagination
- [ ] Use pytest fixtures for Redis/FastMCP setup
- [ ] Use inline-snapshot for response validation

### 8.3 Comparison Tests with Old Scripts
- [ ] Create `tests/test_legacy_comparison.py`
  - [ ] Run old bash scripts via subprocess
  - [ ] Run new async implementation
  - [ ] Compare Nessus API calls (sequence, payloads)
  - [ ] Compare final results (vulnerability counts, severities)
  - [ ] Assert equivalence within tolerance
- [ ] Document any intentional differences

### 8.4 Python Test Client
- [ ] Create `tests/client/nessus_client.py` with NessusMCPClient class
- [ ] Implement submit_scan() method with idempotency_key support
- [ ] Implement get_status() method
- [ ] Implement poll_until_complete() helper
- [ ] Implement get_results() method
- [ ] Implement pause/resume/stop/delete wrappers
- [ ] Add example usage script in tests/client/example.py

---

## Phase 9: Deployment & Configuration

### 9.1 Docker Configuration
- [ ] Finalize Dockerfile.api
  - [ ] Use python:3.11-slim base
  - [ ] Install requirements-api.txt
  - [ ] Copy tools/, core/, schema/, scanners/ modules
  - [ ] Expose port 8000
  - [ ] Set CMD to run uvicorn
- [ ] Finalize Dockerfile.worker
  - [ ] Use python:3.11-slim base
  - [ ] Install requirements-worker.txt
  - [ ] Copy worker/, core/, scanners/, schema/ modules
  - [ ] Set CMD to run scanner_worker.py
- [ ] Finalize docker-compose.yml
  - [ ] Add environment variables (REDIS_URL, NESSUS_URL, NESSUS_ACCESS_KEY, NESSUS_SECRET_KEY)
  - [ ] Add volumes for persistent task storage
  - [ ] Add healthcheck dependencies
  - [ ] Add resource limits (mem_limit, cpus)

### 9.2 Environment Configuration
- [ ] Create .env.example with all required variables
- [ ] Document environment variables in README.md
- [ ] Add validation for required env vars at startup
- [ ] Implement secret management (consider vault/secrets manager)

### 9.3 Scanner Configuration
- [ ] Finalize config/scanners.yaml format
  ```yaml
  nessus:
    - instance_id: nessus-scanner-1
      url: https://nessus1.example.com:8834
      access_key: ${NESSUS_ACCESS_KEY_1}
      secret_key: ${NESSUS_SECRET_KEY_1}
      enabled: true
      max_concurrent_scans: 10
  ```
- [ ] Add configuration reload mechanism (SIGHUP or API endpoint)

---

## Phase 10: Documentation & Future Enhancements

### 10.1 Documentation
- [ ] Update README.md with quickstart guide
- [ ] Document all MCP tools with examples
- [ ] Add API reference (OpenAPI/Swagger)
- [ ] Create developer setup guide
- [ ] Document troubleshooting procedures
- [ ] Add runbook for common issues

### 10.2 Future Enhancements (Deferred to Post-v2.2)
- [ ] Add Pydantic validation for all tool inputs
- [ ] Generate OpenAPI schema from FastMCP tools
- [ ] Implement webhook notifications on scan completion
- [ ] Add scan scheduling (cron-like)
- [ ] Implement scan templates
- [ ] Add multi-tenancy support
- [ ] Implement RBAC for scanner access
- [ ] Add audit logging
- [ ] Implement result caching
- [ ] Add graphical dashboard (Grafana)

---

## Validation Checklist

Before marking implementation complete, verify:

- [ ] All unit tests pass (pytest tests/ -v)
- [ ] Integration tests pass
- [ ] Comparison tests with old scripts show equivalence
- [ ] Docker compose stack starts successfully
- [ ] Health checks pass for all services
- [ ] Prometheus metrics endpoint returns data
- [ ] Full workflow test (submit → poll → get_results) succeeds
- [ ] Idempotent retry returns same task_id
- [ ] State machine rejects invalid transitions
- [ ] DLQ receives failed tasks after max retries
- [ ] Trace IDs propagate through entire workflow
- [ ] Logs are structured JSON with trace_id
- [ ] Scanner registry loads from config
- [ ] Round-robin scanner selection works
- [ ] JSON-NL output includes filter echo
- [ ] All 10 MCP tools are functional
- [ ] Documentation is up-to-date

---

## Notes

- **Implementation Order**: Follow phases sequentially for dependency resolution
- **Testing**: Write tests alongside implementation, not after
- **Error Handling**: Add TODOs for comprehensive error handling during Phase 1-6, implement fully in Phase 7
- **Performance**: Defer optimization until functional correctness is verified
- **Security**: Use environment variables for all secrets, never hardcode credentials
