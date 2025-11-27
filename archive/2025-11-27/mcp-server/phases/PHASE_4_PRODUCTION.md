# Phase 4: Production Hardening (Enhanced)

> **Duration**: Week 4 (extended to Week 4-5)
> **Goal**: Production deployment with scanner pool management, result validation, observability
> **Status**: 🔴 Not Started
> **Prerequisites**: Phase 3 complete, all tests passing

---

## Overview

Phase 4 prepares the system for production use with enhanced capabilities:
- **Scanner Pool Management**: Multi-scanner support with per-instance concurrency limits
- **Advanced Queue Routing**: Per-scanner queues with intelligent load balancing
- **Result Validation**: Post-export validation with authentication failure detection
- **Production Docker Config**: Optimized images, container resource limits
- **Per-Scanner Observability**: Prometheus metrics for pool monitoring
- **TTL Housekeeping**: Automatic cleanup of old tasks
- **Dead Letter Queue Handler**: Manual DLQ inspection and retry
- **Error Recovery**: Comprehensive error handling
- **Load Testing**: Verify concurrent scan handling across scanner pool
- **Documentation**: Complete user and admin guides

---

## Phase 4 Task List

### 4.1: Scanner Pool Management & Registry

**Goal**: Support multiple Nessus scanner instances with configurable concurrency limits

- [ ] Create `core/scanner_registry.py`
  - [ ] `ScannerInstance` dataclass (url, credentials, max_concurrent_scans)
  - [ ] `ScannerRegistry` class with YAML config loading
  - [ ] `get_available_instance()` - find scanner with capacity
  - [ ] `increment_running()` / `decrement_running()` - Redis-based tracking
  - [ ] `get_instances_by_type()` - filter by scanner type
- [ ] Create `config/scanners.yaml` format specification
  - [ ] Document scanner configuration structure
  - [ ] Environment variable substitution (e.g., `${NESSUS_USERNAME_1}`)
  - [ ] Per-instance `max_concurrent_scans` setting (default: 2)
- [ ] Create `config/scanners.yaml.example` template
- [ ] Update `.env.example` with scanner credentials pattern
- [ ] Add `SCANNER_CONFIG` environment variable to docker-compose
- [ ] Test scanner registry loading and instance selection

### 4.2: Multi-Queue System

**Goal**: Route tasks to specific scanners or global queue for load balancing

- [ ] Enhance `core/queue.py` with multi-queue support
  - [ ] Keep existing methods for backward compatibility
  - [ ] Add `enqueue_for_scanner(task, scanner_instance_id)` - specific queue
  - [ ] Add `enqueue_global(task)` - any available scanner
  - [ ] Update `dequeue_for_scanner(scanner_instance_id)` - checks [scanner_queue, global_queue]
  - [ ] Add `get_queue_depth_for_scanner(scanner_instance_id)`
  - [ ] Add `get_global_queue_depth()`
  - [ ] Add `get_all_queue_stats()` - comprehensive queue metrics
- [ ] Update Redis key structure documentation
  - [ ] `nessus:queue:nessus:{instance_id}` - per-scanner queues
  - [ ] `nessus:queue:global` - global overflow queue
  - [ ] `nessus:scanners:{instance_id}:running` - running task tracking (SET)
- [ ] Test queue routing logic with multiple scanners

### 4.3: Enhanced MCP Tools with Scanner Selection

**Goal**: Allow users to specify scanner instance, handle capacity routing

- [ ] Update `tools/mcp_server.py` scan tools
  - [ ] Add `scanner_instance: Optional[str]` parameter to all scan tools
  - [ ] Integrate `scanner_registry.get_available_instance()`
  - [ ] Implement 3-way routing logic:
    - **Case A**: Capacity available → route to scanner
    - **Case B**: Specific scanner requested but at capacity → queue for that scanner
    - **Case C**: No specific scanner + all at capacity → global queue
  - [ ] Return enhanced response with scanner info and queue position
- [ ] Update tool return format with new fields:
  - [ ] `scanner_instance`: Which scanner will process this
  - [ ] `scanner_url`: Scanner URL for transparency
  - [ ] `queue_position`: Position in queue
  - [ ] `estimated_wait_time`: Optional wait estimate
- [ ] Test tool calls with scanner selection

### 4.4: Result Validation with Authentication Detection

**Goal**: Validate exported .nessus files and detect authentication failures

- [ ] Create `scanners/nessus_validator.py`
  - [ ] `ValidationResult` dataclass (is_valid, error, warnings, stats, authentication_status)
  - [ ] `NessusValidator` class with validation logic
  - [ ] **Critical**: Parse plugin 19506 output for "Credentialed checks : yes/no"
  - [ ] Count authenticated vs unauthenticated plugin results
  - [ ] Define `AUTH_SUCCESS_PLUGINS` dict (20811, 21643, 97833, etc.)
  - [ ] Define `UNAUTH_ONLY_PLUGINS` dict (10335, 11219, 14272, etc.)
  - [ ] `_parse_credentialed_status()` - extract from plugin 19506
  - [ ] `_validate_authentication()` - verify auth based on scan_type
  - [ ] Validation checks:
    - [ ] File exists and has reasonable size (>500 bytes)
    - [ ] Valid XML structure with required elements
    - [ ] Host count vs expected targets
    - [ ] Authentication success for trusted/privileged scans
    - [ ] Plugin count thresholds (min 5 auth plugins for trusted scans)
    - [ ] Scan error detection in plugin outputs
- [ ] Create `validate_nessus_results()` convenience function
- [ ] Test validator with:
  - [ ] Successful authenticated scan
  - [ ] Failed authentication (only port scan results)
  - [ ] Untrusted scan (no auth expected)
  - [ ] Corrupted/empty .nessus file
  - [ ] Partial authentication failure

### 4.5: Worker Enhancement for Scanner Pool

**Goal**: Workers enforce per-scanner concurrency and perform validation

- [ ] Update `worker/scanner_worker.py`
  - [ ] Add `SCANNER_INSTANCE_ID` environment variable (required)
  - [ ] Each worker subscribes to ONE scanner instance
  - [ ] Check scanner capacity before dequeuing
  - [ ] Use `scanner_registry.increment_running()` before processing
  - [ ] Use `scanner_registry.decrement_running()` in finally block
  - [ ] Call `validate_nessus_results()` after export
  - [ ] Handle validation result:
    - **Valid**: Mark completed with validation_stats
    - **Invalid**: Mark failed, move to DLQ
  - [ ] Pass `scan_type` to validator for auth detection
  - [ ] Log authentication status for all scans
- [ ] Update `process_scan_task()` function
  - [ ] Add validation step between export and mark_completed
  - [ ] Enhanced logging with authentication status
- [ ] Test worker with scanner concurrency limits

### 4.6: Enhanced Task Metadata

**Goal**: Store validation results and authentication status in task.json

- [ ] Update `core/task_manager.py`
  - [ ] Add `validation_stats: Optional[Dict]` to `mark_completed()`
  - [ ] Add `validation_warnings: Optional[List[str]]` to `mark_completed()`
  - [ ] Add `authentication_status: Optional[str]` to `mark_completed()` and `mark_failed()`
  - [ ] Store in task.json for status API
- [ ] Update task.json schema with new fields:
  - [ ] `validation_stats`: Host counts, vuln counts, plugin stats, file size
  - [ ] `validation_warnings`: List of warning messages
  - [ ] `authentication_status`: "success", "failed", "partial", "not_applicable"
- [ ] Test task metadata persistence

### 4.7: Enhanced Status API

**Goal**: Expose validation results and scanner info in status responses

- [ ] Update `get_scan_status()` tool
  - [ ] Add `scanner_instance` field
  - [ ] Add `results_summary` section (if completed):
    - hosts_scanned
    - total_vulnerabilities
    - severity_breakdown
    - file_size_mb
  - [ ] Add `warnings` field for validation warnings
  - [ ] Add `authentication_status` field
  - [ ] Add `troubleshooting` section (if failed with auth error):
    - likely_cause
    - next_steps (list of actions)
- [ ] Test status API with various scan states

### 4.8: Per-Scanner Prometheus Metrics

**Goal**: Monitor scanner pool health and utilization

- [ ] Update `core/metrics.py` with per-scanner metrics
  - [ ] `nessus_scanner_active_scans{scanner_instance="..."}` - running scans
  - [ ] `nessus_scanner_capacity{scanner_instance="..."}` - max concurrent
  - [ ] `nessus_scanner_utilization_pct{scanner_instance="..."}` - % utilized
  - [ ] `nessus_scanner_queue_depth{scanner_instance="..."}` - queued tasks
  - [ ] `nessus_scanner_enabled{scanner_instance="..."}` - 0 or 1
  - [ ] `nessus_global_queue_depth` - global queue size
  - [ ] `nessus_validation_failures_total{reason="..."}` - validation failure counts
  - [ ] `nessus_auth_failures_total{scanner_instance="..."}` - auth failure counts
- [ ] Add metrics collection in:
  - [ ] Scanner registry (capacity, utilization)
  - [ ] Queue manager (queue depths)
  - [ ] Worker (increment/decrement active scans)
  - [ ] Validator (failure counts)
- [ ] Create Grafana dashboard template (optional)
- [ ] Test metrics endpoint

### 4.9: Production Docker Configuration

**Goal**: Optimized Docker setup with resource limits and multi-worker support

- [ ] Create `prod/docker-compose.yml`
  - [ ] Optimize Dockerfiles for production:
    - [ ] Multi-stage builds
    - [ ] Minimal base images (python:3.12-slim)
    - [ ] No hot reload
    - [ ] Log to stdout only
  - [ ] Add container resource limits (CPU, memory):
    - [ ] Redis: 0.5 CPU, 512M memory
    - [ ] MCP API: 1.0 CPU, 1G memory
    - [ ] Scanner worker: 2.0 CPU, 2G memory per worker
  - [ ] Configure restart policies (always)
  - [ ] Deploy one worker per scanner instance:
    - [ ] `worker-nessus-prod-1` with `SCANNER_INSTANCE_ID=nessus_prod_1`
    - [ ] `worker-nessus-prod-2` with `SCANNER_INSTANCE_ID=nessus_prod_2`
  - [ ] Mount config volumes read-only
- [ ] Create `prod/.env.prod.example`
- [ ] Set production environment variables
- [ ] Test production build and deployment

### 4.10: TTL Housekeeping

- [ ] Create `core/housekeeping.py`
- [ ] Implement `HousekeepingService` class
  - [ ] `cleanup_expired_tasks()` - delete tasks older than TTL
  - [ ] Check `last_accessed_at` timestamp
  - [ ] Remove task directories (scan results, logs)
  - [ ] Update metrics (`ttl_deletions_total`)
- [ ] Add periodic scheduler (APScheduler or asyncio loop)
- [ ] Run cleanup every hour (configurable)
- [ ] Integrate into worker startup
- [ ] Test TTL cleanup with old tasks

### 4.11: Dead Letter Queue Handler

- [ ] Create `tools/admin_cli.py`
- [ ] Implement CLI commands:
  - [ ] `list-dlq` - show failed tasks with error summaries
  - [ ] `inspect-dlq <task_id>` - view full task details and error
  - [ ] `retry-dlq <task_id>` - move task back to main queue
    - [ ] Clear error fields
    - [ ] Reset to "queued" status
    - [ ] Re-enqueue to appropriate scanner queue
  - [ ] `purge-dlq` - clear all DLQ tasks (with confirmation)
  - [ ] `stats` - queue statistics (main queue, DLQ, per-scanner queues)
- [ ] Add tabular output using `tabulate` library
- [ ] Test DLQ operations with failed scans

### 4.12: Error Recovery & Circuit Breaker

- [ ] Add retry logic in worker (3 attempts for transient errors)
- [ ] Implement exponential backoff (1s, 2s, 4s)
- [ ] Add circuit breaker for scanner failures
  - [ ] Track consecutive failures per scanner
  - [ ] Disable scanner after 5 consecutive failures
  - [ ] Auto-re-enable after cooldown period (5 minutes)
  - [ ] Emit metric: `nessus_scanner_circuit_breaker_open{scanner_instance="..."}`
- [ ] Distinguish transient vs permanent errors:
  - **Transient**: Network timeouts, temporary scanner overload
  - **Permanent**: Authentication failures, invalid targets, scanner offline
- [ ] Test error scenarios and recovery

### 4.13: Load Testing

- [ ] Create `tests/load/test_concurrent_scans.py`
- [ ] Test scenarios:
  - [ ] Submit 10+ scans concurrently (more than total capacity)
  - [ ] Verify FIFO order within each scanner queue
  - [ ] Check no race conditions in concurrency tracking
  - [ ] Verify tasks distributed across scanners
  - [ ] Monitor metrics during load
  - [ ] Verify cleanup works under load
  - [ ] Test scanner failure during load
- [ ] Create `tests/load/test_scanner_pool.py`
  - [ ] Test specific scanner selection
  - [ ] Test global queue fallback
  - [ ] Test scanner at capacity behavior
  - [ ] Verify proper task routing
- [ ] Test validation under load (multiple concurrent exports)
- [ ] Generate load test report

### 4.14: Documentation

- [ ] Create `docs/USER_GUIDE.md`
  - [ ] How to use MCP tools
  - [ ] Understanding scan types (untrusted, trusted_basic, trusted_privileged)
  - [ ] Specifying scanner instances
  - [ ] Interpreting status responses
  - [ ] Understanding validation results
  - [ ] Troubleshooting authentication failures
- [ ] Create `docs/ADMIN_GUIDE.md`
  - [ ] Deployment procedures
  - [ ] Scanner configuration (scanners.yaml)
  - [ ] Monitoring with Prometheus/Grafana
  - [ ] DLQ management
  - [ ] Credential management
  - [ ] Scaling worker pool
- [ ] Create `docs/TROUBLESHOOTING.md`
  - [ ] Common errors and solutions
  - [ ] Authentication failure debugging
  - [ ] Scanner connectivity issues
  - [ ] Queue stuck scenarios
  - [ ] Performance tuning
- [ ] Create `docs/API_REFERENCE.md`
  - [ ] All MCP tools documented
  - [ ] Request/response examples
  - [ ] Error codes and messages
- [ ] Update main `README.md`
  - [ ] Architecture overview with scanner pool
  - [ ] Quick start guide
  - [ ] Configuration examples

### 4.15: Deployment Guide

- [ ] Create `docs/DEPLOYMENT.md`
  - [ ] Step-by-step production setup
  - [ ] Environment variable checklist
  - [ ] Scanner configuration guide
  - [ ] Multi-scanner setup
  - [ ] SSL/TLS configuration for scanners
  - [ ] Backup and recovery procedures
  - [ ] Upgrade procedures
  - [ ] Rollback procedures
  - [ ] Monitoring setup (Prometheus + Grafana)

---

## Critical Implementation Details

### 1. Scanner Configuration Format

**File: `config/scanners.yaml`**

```yaml
# Scanner Pool Configuration
# Each scanner can have independent concurrency limits
scanners:
  - instance_id: "nessus_prod_1"
    scanner_type: "nessus"
    url: "https://nessus1.corp.local:8834"
    max_concurrent_scans: 2  # Max 2 scans at once
    credentials:
      username: "${NESSUS_USERNAME_1}"  # From environment
      password: "${NESSUS_PASSWORD_1}"
    enabled: true

  - instance_id: "nessus_prod_2"
    scanner_type: "nessus"
    url: "https://nessus2.corp.local:8834"
    max_concurrent_scans: 3  # This scanner can handle 3
    credentials:
      username: "${NESSUS_USERNAME_2}"
      password: "${NESSUS_PASSWORD_2}"
    enabled: true

  - instance_id: "nessus_dev"
    scanner_type: "nessus"
    url: "https://localhost:8834"
    max_concurrent_scans: 1  # Dev scanner, limit to 1
    credentials:
      username: "${NESSUS_USERNAME_DEV}"
      password: "${NESSUS_PASSWORD_DEV}"
    enabled: false  # Disabled in production
```

**Environment Variables (`.env`)**:
```bash
# Scanner 1 Credentials
NESSUS_USERNAME_1=admin
NESSUS_PASSWORD_1=SecurePass123!

# Scanner 2 Credentials
NESSUS_USERNAME_2=admin
NESSUS_PASSWORD_2=AnotherSecurePass!

# Dev Scanner (disabled in prod)
NESSUS_USERNAME_DEV=dev_user
NESSUS_PASSWORD_DEV=DevPass!
```

### 2. Authentication Detection Logic (CRITICAL)

**File: `scanners/nessus_validator.py`**

```python
class NessusValidator:
    """
    Validates Nessus results with authentication detection.

    CRITICAL: Authentication validation based on plugin analysis, NOT statistics.
    """

    # Plugin 19506: Nessus Scan Information (contains credentialed status)
    SCAN_INFO_PLUGIN = 19506

    # Plugins that ONLY work with authentication
    AUTH_SUCCESS_PLUGINS = {
        # Windows
        20811: "Windows Compliance Checks",
        21643: "Windows Local Security Checks",
        97833: "Windows Security Update Check",
        66334: "MS Windows Patch Enumeration",

        # Linux
        12634: "Unix/Linux Local Security Checks",
        51192: "Debian Local Security Checks",
        33851: "Red Hat Local Security Checks",

        # Package enumeration (strong indicator)
        22869: "Installed Software Enumeration",
    }

    # Plugins that work WITHOUT authentication (port scanning)
    UNAUTH_ONLY_PLUGINS = {
        10335: "TCP/IP Timestamps Supported",
        11219: "Nessus SYN scanner",
        14272: "netstat portscanner (SSH)",
        10863: "Web Server Detection",
        10107: "HTTP Server Type and Version"
    }

    def _parse_credentialed_status(self, plugin_output: str) -> Optional[str]:
        """
        Parse plugin 19506 output for explicit credential status.

        Example plugin output:
        ```
        Information about this scan :

        Nessus version : 10.6.4
        Nessus build : 20009
        Plugin feed version : 202501091839
        Scanner IP : 192.168.1.100
        Port scanner(s) : nessus_syn_scanner
        Credentialed checks : yes    <-- CRITICAL LINE
        Patch management checks : None
        ```

        Returns:
            "success" if "Credentialed checks : yes"
            "failed" if "Credentialed checks : no"
            "partial" if "Credentialed checks : partial"
            None if not found
        """
        lines = plugin_output.split('\n')
        for line in lines:
            if 'credentialed checks' in line.lower():
                line_lower = line.lower()
                if 'yes' in line_lower or 'successful' in line_lower:
                    return "success"
                elif 'no' in line_lower or 'failed' in line_lower:
                    return "failed"
                elif 'partial' in line_lower:
                    return "partial"
        return None

    def _validate_authentication(
        self,
        scan_type: str,
        plugin_counts: Dict[str, Any],
        credentialed_checks_status: Optional[str],
        num_hosts: int
    ) -> Dict[str, Any]:
        """
        Validate authentication based on scan type.

        Logic:
        1. For untrusted scans: Auth not required, pass
        2. For trusted/privileged scans:
           a. Check plugin 19506 explicit status (most reliable)
           b. Check authenticated plugin count threshold (>= 5)
           c. Check ratio of auth vs unauth plugins

        Returns validation result with is_error flag.
        """
        if scan_type == "untrusted":
            return {
                "status": "not_applicable",
                "is_error": False,
                "is_warning": False,
                "message": "Authentication not required for untrusted scan"
            }

        # Trusted/privileged scans REQUIRE authentication
        auth_plugin_count = plugin_counts["auth_required"]

        # PRIMARY CHECK: Plugin 19506 explicit status
        if credentialed_checks_status == "failed":
            return {
                "status": "failed",
                "is_error": True,  # FAIL THE SCAN
                "is_warning": False,
                "message": (
                    f"Authentication FAILED: Plugin 19506 reports 'Credentialed checks : no'. "
                    f"Scan type '{scan_type}' requires valid credentials. "
                    f"Only {auth_plugin_count} authenticated plugins executed. "
                    f"Results only contain port scan data."
                )
            }

        # SECONDARY CHECK: Plugin count threshold
        if auth_plugin_count < 5:  # Hardcoded threshold
            return {
                "status": "failed",
                "is_error": True,  # FAIL THE SCAN
                "is_warning": False,
                "message": (
                    f"Authentication appears to have FAILED: "
                    f"Only {auth_plugin_count} authenticated plugin results found (threshold: 5). "
                    f"Scan type '{scan_type}' requires valid credentials."
                )
            }

        # SUCCESS: Sufficient authenticated results
        return {
            "status": "success",
            "is_error": False,
            "is_warning": False,
            "message": f"Authentication successful (confirmed by plugin analysis)"
        }
```

### 3. Multi-Queue Routing Logic

**File: `core/queue.py` (enhanced)**

```python
class TaskQueue:
    """
    Multi-queue system for scanner pool management.

    Queue Structure:
    - nessus:queue:nessus:{instance_id}  - Per-scanner queues (FIFO lists)
    - nessus:queue:global                 - Global overflow queue
    - nessus:scanners:{instance_id}:running  - Running scans (SET of task_ids)
    """

    def enqueue_for_scanner(
        self,
        task: Dict[str, Any],
        scanner_instance_id: str
    ) -> int:
        """Enqueue task for specific scanner instance."""
        queue_key = f"nessus:queue:nessus:{scanner_instance_id}"
        task_json = json.dumps(task)
        queue_depth = self.redis_client.lpush(queue_key, task_json)

        logger.info(
            f"Enqueued {task['task_id']} for scanner {scanner_instance_id}, "
            f"queue_depth: {queue_depth}"
        )
        return queue_depth

    def enqueue_global(self, task: Dict[str, Any]) -> int:
        """Enqueue to global queue (any available scanner)."""
        queue_key = "nessus:queue:global"
        task_json = json.dumps(task)
        global_depth = self.redis_client.lpush(queue_key, task_json)

        logger.info(
            f"Enqueued {task['task_id']} to global queue, depth: {global_depth}"
        )
        return global_depth

    def dequeue_for_scanner(
        self,
        scanner_instance_id: str,
        timeout: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Dequeue next task for this scanner.

        Priority order:
        1. Scanner-specific queue (tasks explicitly routed to this scanner)
        2. Global queue (tasks waiting for any available scanner)

        Uses BRPOP for atomic blocking dequeue.
        """
        scanner_queue = f"nessus:queue:nessus:{scanner_instance_id}"
        global_queue = "nessus:queue:global"

        # BRPOP checks keys in order
        result = self.redis_client.brpop(
            [scanner_queue, global_queue],
            timeout=timeout
        )

        if not result:
            return None

        queue_key, task_json = result
        task = json.loads(task_json)

        # If from global queue, assign to this scanner
        if queue_key == global_queue:
            task["scanner_instance_id"] = scanner_instance_id
            logger.info(
                f"Assigned task {task['task_id']} from global queue "
                f"to scanner {scanner_instance_id}"
            )

        return task
```

### 4. Worker Concurrency Enforcement

**File: `worker/scanner_worker.py`**

```python
async def worker_main():
    """
    Worker process for one scanner instance.

    Environment Variables:
    - SCANNER_INSTANCE_ID (required): Which scanner this worker manages
    - REDIS_URL: Redis connection string
    """
    scanner_instance_id = os.getenv("SCANNER_INSTANCE_ID")
    if not scanner_instance_id:
        raise ValueError("SCANNER_INSTANCE_ID environment variable required")

    # Initialize
    redis_client = redis.from_url(os.getenv("REDIS_URL"))
    scanner_registry = ScannerRegistry(redis_client)
    task_queue = TaskQueue(redis_client)

    scanner_instance = scanner_registry.get_instance(scanner_instance_id)

    logger.info(
        f"Worker started for scanner: {scanner_instance_id}",
        extra={
            "url": scanner_instance.url,
            "max_concurrent": scanner_instance.max_concurrent_scans
        }
    )

    while True:
        try:
            # 1. Check scanner capacity
            running_count = scanner_registry._get_running_count(scanner_instance)

            if running_count >= scanner_instance.max_concurrent_scans:
                # At capacity - wait
                logger.debug(
                    f"Scanner {scanner_instance_id} at capacity "
                    f"({running_count}/{scanner_instance.max_concurrent_scans})"
                )
                await asyncio.sleep(5)
                continue

            # 2. Dequeue task
            task = task_queue.dequeue_for_scanner(scanner_instance_id, timeout=5)
            if not task:
                continue

            # 3. Claim slot BEFORE starting (prevents race condition)
            scanner_registry.increment_running(scanner_instance_id, task["task_id"])

            logger.info(
                f"Starting scan {task['task_id']} on {scanner_instance_id} "
                f"(now running: {running_count + 1}/{scanner_instance.max_concurrent_scans})"
            )

            # 4. Process async (doesn't block other tasks)
            asyncio.create_task(
                process_scan_task(task, scanner_instance, scanner_registry, task["task_id"])
            )

        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            await asyncio.sleep(10)


async def process_scan_task(
    task: Dict[str, Any],
    scanner_instance: ScannerInstance,
    scanner_registry: ScannerRegistry,
    task_id: str
):
    """Process scan with validation."""
    try:
        # ... scan execution (create, launch, poll, export) ...

        # VALIDATION STEP (NEW)
        scan_type = task.get("scan_type", "untrusted")
        validation = await validate_nessus_results(
            nessus_file_path=nessus_file_path,
            task=task,
            scan_id=scan_id,
            scan_type=scan_type
        )

        if validation.is_valid:
            # Success
            await task_manager.mark_completed(
                task_id,
                task["trace_id"],
                validation_stats=validation.stats,
                validation_warnings=validation.warnings,
                authentication_status=validation.authentication_status
            )
            logger.info(
                f"Scan {task_id} completed successfully",
                extra={
                    "authentication_status": validation.authentication_status,
                    "hosts_scanned": validation.stats.get("hosts_scanned", 0)
                }
            )
        else:
            # Validation failed (e.g., auth failure)
            await task_manager.mark_failed(
                task_id,
                task["trace_id"],
                error=validation.error,
                validation_stats=validation.stats,
                authentication_status=validation.authentication_status
            )
            task_queue.move_to_dlq(task, error=validation.error)

    finally:
        # CRITICAL: Always release slot
        scanner_registry.decrement_running(scanner_instance.instance_id, task_id)
```

### 5. Production Docker Compose with Multi-Worker

**File: `prod/docker-compose.yml`**

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: nessus-mcp-redis-prod
    volumes:
      - redis_data_prod:/data
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: always
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    networks:
      - mcp-network

  mcp-api:
    image: nessus-mcp:prod
    container_name: nessus-mcp-api-prod
    ports:
      - "8836:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/app/data/tasks
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
      - SCANNER_CONFIG=/app/config/scanners.yaml
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    networks:
      - mcp-network

  # Worker for Scanner 1
  worker-nessus-prod-1:
    image: nessus-mcp-worker:prod
    container_name: nessus-mcp-worker-prod-1
    environment:
      - REDIS_URL=redis://redis:6379
      - SCANNER_INSTANCE_ID=nessus_prod_1  # Dedicated to prod_1
      - DATA_DIR=/app/data/tasks
      - SCANNER_CONFIG=/app/config/scanners.yaml
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      redis:
        condition: service_healthy
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    networks:
      - mcp-network

  # Worker for Scanner 2
  worker-nessus-prod-2:
    image: nessus-mcp-worker:prod
    container_name: nessus-mcp-worker-prod-2
    environment:
      - REDIS_URL=redis://redis:6379
      - SCANNER_INSTANCE_ID=nessus_prod_2  # Dedicated to prod_2
      - DATA_DIR=/app/data/tasks
      - SCANNER_CONFIG=/app/config/scanners.yaml
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      redis:
        condition: service_healthy
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    networks:
      - mcp-network

networks:
  mcp-network:
    driver: bridge

volumes:
  redis_data_prod:
    driver: local
```

### 6. Per-Scanner Prometheus Metrics

**File: `core/metrics.py` (additions)**

```python
from prometheus_client import Counter, Gauge, Histogram

# Scanner pool metrics
scanner_active_scans = Gauge(
    "nessus_scanner_active_scans",
    "Currently running scans on this scanner",
    ["scanner_instance"]
)

scanner_capacity = Gauge(
    "nessus_scanner_capacity",
    "Maximum concurrent scans for this scanner",
    ["scanner_instance"]
)

scanner_utilization_pct = Gauge(
    "nessus_scanner_utilization_pct",
    "Scanner utilization percentage (0-100)",
    ["scanner_instance"]
)

scanner_queue_depth = Gauge(
    "nessus_scanner_queue_depth",
    "Tasks queued for this scanner",
    ["scanner_instance"]
)

global_queue_depth = Gauge(
    "nessus_global_queue_depth",
    "Tasks in global queue (any available scanner)"
)

# Validation metrics
validation_failures_total = Counter(
    "nessus_validation_failures_total",
    "Total validation failures",
    ["reason"]  # "auth_failed", "corrupted_xml", "empty_scan", etc.
)

auth_failures_total = Counter(
    "nessus_auth_failures_total",
    "Total authentication failures",
    ["scanner_instance", "scan_type"]
)

# Usage in code:
def update_scanner_metrics(scanner_registry, task_queue):
    """Update all scanner metrics (call periodically)."""
    for instance in scanner_registry.scanners.values():
        running = scanner_registry._get_running_count(instance)
        capacity = instance.max_concurrent_scans

        scanner_active_scans.labels(
            scanner_instance=instance.instance_id
        ).set(running)

        scanner_capacity.labels(
            scanner_instance=instance.instance_id
        ).set(capacity)

        scanner_utilization_pct.labels(
            scanner_instance=instance.instance_id
        ).set((running / capacity * 100) if capacity > 0 else 0)

        scanner_queue_depth.labels(
            scanner_instance=instance.instance_id
        ).set(task_queue.get_queue_depth_for_scanner(instance.instance_id))

    global_queue_depth.set(task_queue.get_global_queue_depth())
```

---

## Phase 4 Completion Checklist

### Core Deliverables
- [ ] Scanner registry with multi-scanner support
- [ ] Multi-queue system (per-scanner + global)
- [ ] Enhanced MCP tools with scanner selection
- [ ] Result validation with authentication detection
- [ ] Multi-worker deployment (one per scanner)
- [ ] Per-scanner Prometheus metrics
- [ ] Production Docker configuration with resource limits
- [ ] TTL housekeeping running
- [ ] DLQ admin CLI functional
- [ ] Error recovery with circuit breaker
- [ ] Load tests passing (10+ concurrent scans)
- [ ] Complete documentation (user, admin, troubleshooting)

### Verification Tests
```bash
# 1. Test scanner pool loading
python -c "from core.scanner_registry import ScannerRegistry; \
           import redis; r = redis.from_url('redis://localhost:6379'); \
           reg = ScannerRegistry(r); print(reg.scanners)"

# 2. Submit scan with specific scanner
curl -X POST http://localhost:8836/tools/run_untrusted_scan \
  -d '{"targets":"192.168.1.1","name":"Test","scanner_instance":"nessus_prod_2"}'

# 3. Check per-scanner metrics
curl http://localhost:8836/metrics | grep scanner_active_scans

# 4. Test authentication failure detection
# Submit trusted scan with bad credentials, verify it fails with auth error

# 5. Check queue routing
redis-cli LLEN nessus:queue:nessus:nessus_prod_1
redis-cli LLEN nessus:queue:global
redis-cli SMEMBERS nessus:scanners:nessus_prod_1:running

# 6. Run load tests
pytest tests/load/ -v
```

### Success Criteria
✅ Phase 4 complete when:
1. Multiple scanners configured and operational
2. Per-scanner concurrency limits enforced (no scanner exceeds limit)
3. Tasks route correctly to specific scanners or global queue
4. Authentication failures detected and scans marked as failed
5. Validation stats visible in status API
6. Per-scanner metrics exposed and accurate
7. Load tests pass (10+ concurrent scans across pool)
8. DLQ CLI can inspect and retry failed tasks
9. Production Docker deployment stable
10. All documentation complete

---

## Future Enhancements (Post-Phase 4)

These features are deferred to later phases:

1. **Troubleshooting Process** (Phase 5)
   - Automated failed scan analysis
   - Credential testing tool
   - Network connectivity checker
   - Plugin analysis tool

2. **Dynamic Scanner Registration** (Phase 5)
   - Admin API to add/remove scanners without restart
   - Hot-reload scanner configuration
   - Scanner health monitoring

3. **Advanced Retry Logic** (Phase 5)
   - Credential override on retry
   - Automatic retry with different scanner
   - Exponential backoff for auth failures

4. **Validation Override** (Phase 5)
   - Admin CLI to force-accept partial results
   - Audit log for overrides
   - Configurable validation thresholds

5. **Enhanced Load Balancing** (Phase 6)
   - Weighted load balancing (prefer faster scanners)
   - Geographic routing (prefer closer scanners)
   - Scanner capability matching (credential types)

---

**Phase 4 Duration**: 2 weeks (extended from 1 week due to added features)
**Estimated Effort**: 80-100 hours
**Team Size**: 1-2 developers

**Next Phase**: [PHASE_5_ADVANCED_FEATURES.md](./PHASE_5_ADVANCED_FEATURES.md) (TBD)
