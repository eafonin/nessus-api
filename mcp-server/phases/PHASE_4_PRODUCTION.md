# Phase 4: Production Hardening

> **Duration**: Week 4
> **Goal**: Production deployment, TTL housekeeping, error recovery, documentation
> **Status**: 🔴 Not Started
> **Prerequisites**: Phase 3 complete, all tests passing

---

## Overview

Phase 4 prepares the system for production use:
- **Production Docker Config**: Optimized images, resource limits
- **TTL Housekeeping**: Automatic cleanup of old tasks
- **Dead Letter Queue Handler**: Manual DLQ inspection and retry
- **Import Linting**: Enforce layer boundaries
- **Error Recovery**: Comprehensive error handling
- **Load Testing**: Verify concurrent scan handling
- **Documentation**: Complete user and admin guides
- **Deployment Guide**: Step-by-step production setup

---

## Phase 4 Task List

### 4.1: Production Docker Configuration
- [ ] Create `prod/docker-compose.yml`
- [ ] Optimize Dockerfiles for production:
  - [ ] Multi-stage builds
  - [ ] Minimal base images
  - [ ] No hot reload
  - [ ] Log to stdout only
- [ ] Add resource limits (CPU, memory)
- [ ] Configure restart policies
- [ ] Set production environment variables
- [ ] Test production build

### 4.2: TTL Housekeeping
- [ ] Create `core/housekeeping.py`
- [ ] Implement `cleanup_expired_tasks()`:
  - [ ] Check last_accessed_at timestamp
  - [ ] Delete tasks older than TTL (default 24h)
  - [ ] Remove task directories
  - [ ] Update metrics (ttl_deletions_total)
- [ ] Add periodic scheduler (APScheduler)
- [ ] Run cleanup every hour
- [ ] Test TTL cleanup

### 4.3: Dead Letter Queue Handler
- [ ] Create `tools/admin_cli.py`
- [ ] Commands:
  - [ ] `list-dlq` - show failed tasks
  - [ ] `inspect-dlq <task_id>` - view task details
  - [ ] `retry-dlq <task_id>` - move back to main queue
  - [ ] `purge-dlq` - clear all DLQ tasks
- [ ] Test DLQ operations

### 4.4: Import Linting
- [ ] Verify pyproject.toml has all rules
- [ ] Run `import-linter` locally
- [ ] Add pre-commit hook
- [ ] Add to CI/CD pipeline
- [ ] Fix any violations

### 4.5: Error Recovery
- [ ] Add retry logic in worker (3 attempts)
- [ ] Exponential backoff on transient errors
- [ ] Circuit breaker for scanner failures
- [ ] Graceful degradation strategies
- [ ] Test error scenarios

### 4.6: Load Testing
- [ ] Create `tests/load/test_concurrent_scans.py`
- [ ] Submit 10+ scans concurrently
- [ ] Verify FIFO order
- [ ] Check no race conditions
- [ ] Monitor metrics during load
- [ ] Verify cleanup works under load

### 4.7: Documentation
- [ ] User guide (how to use MCP tools)
- [ ] Admin guide (deployment, monitoring)
- [ ] API reference (all tools documented)
- [ ] Troubleshooting guide
- [ ] Update README.md

### 4.8: Deployment Guide
- [ ] Step-by-step production setup
- [ ] Environment variable checklist
- [ ] Scanner configuration guide
- [ ] Backup and recovery procedures
- [ ] Upgrade procedures
- [ ] Rollback procedures

---

## Key Implementation Details

### Production Docker Compose

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

  mcp-api:
    image: nessus-mcp:prod
    container_name: nessus-mcp-api-prod
    ports:
      - "8836:8000"  # Different port from dev
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/app/data/tasks
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
      - BEARER_TOKEN=${BEARER_TOKEN}
      - NESSUS_USERNAME_1=${NESSUS_USERNAME_1}
      - NESSUS_PASSWORD_1=${NESSUS_PASSWORD_1}
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

  scanner-worker:
    image: nessus-mcp-worker:prod
    container_name: nessus-mcp-worker-prod
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/app/data/tasks
      - SCANNER_CONFIG=/app/config/scanners.yaml
      - LOG_LEVEL=INFO
      - NESSUS_USERNAME_1=${NESSUS_USERNAME_1}
      - NESSUS_PASSWORD_1=${NESSUS_PASSWORD_1}
      - MAX_CONCURRENT_SCANS=10
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

volumes:
  redis_data_prod:
    driver: local
```

**File: `prod/.env.prod`**
```bash
# Production Environment

ENVIRONMENT=production
LOG_LEVEL=INFO

# Redis
REDIS_URL=redis://redis:6379

# Storage
DATA_DIR=/app/data/tasks

# Scanner Configuration
SCANNER_CONFIG=/app/config/scanners.yaml

# Nessus Credentials
NESSUS_USERNAME_1=nessus
NESSUS_PASSWORD_1=<SET_THIS>

# Security
BEARER_TOKEN=<SET_THIS>

# Housekeeping
TTL_HOURS=24
CLEANUP_INTERVAL_SECONDS=3600
```

### TTL Housekeeping

**File: `core/housekeeping.py`**
```python
"""Automatic task cleanup based on TTL."""
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import logging
import shutil
from core.metrics import ttl_deletions_total

logger = logging.getLogger(__name__)


class HousekeepingService:
    """Periodic cleanup of expired tasks."""

    def __init__(
        self,
        data_dir: str,
        ttl_hours: int = 24,
        cleanup_interval: int = 3600
    ):
        self.data_dir = Path(data_dir)
        self.ttl_hours = ttl_hours
        self.cleanup_interval = cleanup_interval
        self.running = False

    async def start(self):
        """Start housekeeping service."""
        self.running = True
        logger.info(f"Housekeeping service started (TTL: {self.ttl_hours}h)")

        while self.running:
            try:
                deleted = await self.cleanup_expired_tasks()
                if deleted > 0:
                    logger.info(f"Cleanup: deleted {deleted} expired tasks")
            except Exception as e:
                logger.error(f"Housekeeping error: {e}", exc_info=True)

            await asyncio.sleep(self.cleanup_interval)

    async def cleanup_expired_tasks(self) -> int:
        """Delete tasks older than TTL."""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=self.ttl_hours)
        deleted = 0

        for task_dir in self.data_dir.iterdir():
            if not task_dir.is_dir():
                continue

            # Check last_accessed_at in task.json
            task_file = task_dir / "task.json"
            if not task_file.exists():
                continue

            import json
            with open(task_file) as f:
                task = json.load(f)

            last_accessed = task.get("last_accessed_at") or task.get("created_at")
            if not last_accessed:
                continue

            last_accessed_dt = datetime.fromisoformat(last_accessed)

            if last_accessed_dt < cutoff:
                # Delete task
                try:
                    shutil.rmtree(task_dir)
                    deleted += 1
                    ttl_deletions_total.inc()
                    logger.info(f"Deleted expired task: {task_dir.name}")
                except Exception as e:
                    logger.error(f"Failed to delete task {task_dir.name}: {e}")

        return deleted

    def stop(self):
        """Stop housekeeping service."""
        self.running = False
```

**Add to worker:**
```python
# In worker/scanner_worker.py
from core.housekeeping import HousekeepingService

async def main():
    # ... existing setup ...

    # Start housekeeping
    housekeeping = HousekeepingService(
        data_dir=os.getenv("DATA_DIR", "/app/data/tasks"),
        ttl_hours=int(os.getenv("TTL_HOURS", "24")),
        cleanup_interval=int(os.getenv("CLEANUP_INTERVAL_SECONDS", "3600"))
    )
    asyncio.create_task(housekeeping.start())

    # Start worker
    worker = ScannerWorker(...)
    await worker.run()
```

### Admin CLI

**File: `tools/admin_cli.py`**
```python
"""Admin CLI for DLQ management."""
import click
import redis
import json
from tabulate import tabulate


@click.group()
@click.option('--redis-url', default='redis://localhost:6379', help='Redis URL')
@click.pass_context
def cli(ctx, redis_url):
    """Nessus MCP Admin CLI."""
    ctx.obj = redis.from_url(redis_url, decode_responses=True)


@cli.command()
@click.pass_obj
def list_dlq(r):
    """List all tasks in dead letter queue."""
    dlq_key = "nessus:queue:dead"
    tasks = r.zrange(dlq_key, 0, -1, withscores=True)

    if not tasks:
        click.echo("DLQ is empty")
        return

    table = []
    for task_json, score in tasks:
        task = json.loads(task_json)
        table.append([
            task.get("task_id"),
            task.get("scan_type"),
            task.get("error", "N/A")[:50],
            datetime.fromtimestamp(score).isoformat()
        ])

    click.echo(tabulate(table, headers=["Task ID", "Type", "Error", "Failed At"]))


@cli.command()
@click.argument('task_id')
@click.pass_obj
def inspect_dlq(r, task_id):
    """Inspect specific DLQ task."""
    dlq_key = "nessus:queue:dead"
    tasks = r.zrange(dlq_key, 0, -1)

    for task_json in tasks:
        task = json.loads(task_json)
        if task.get("task_id") == task_id:
            click.echo(json.dumps(task, indent=2))
            return

    click.echo(f"Task {task_id} not found in DLQ")


@cli.command()
@click.argument('task_id')
@click.pass_obj
def retry_dlq(r, task_id):
    """Retry task from DLQ (move back to main queue)."""
    dlq_key = "nessus:queue:dead"
    queue_key = "nessus:queue"

    tasks = r.zrange(dlq_key, 0, -1)

    for task_json in tasks:
        task = json.loads(task_json)
        if task.get("task_id") == task_id:
            # Remove from DLQ
            r.zrem(dlq_key, task_json)

            # Remove error fields
            task.pop("error", None)
            task.pop("failed_at", None)

            # Add back to main queue
            r.lpush(queue_key, json.dumps(task))

            click.echo(f"✓ Task {task_id} moved back to main queue")
            return

    click.echo(f"✗ Task {task_id} not found in DLQ")


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to purge entire DLQ?')
@click.pass_obj
def purge_dlq(r):
    """Clear entire DLQ."""
    dlq_key = "nessus:queue:dead"
    count = r.zcard(dlq_key)
    r.delete(dlq_key)
    click.echo(f"✓ Purged {count} tasks from DLQ")


if __name__ == '__main__':
    cli()
```

**Usage:**
```bash
# List DLQ
python tools/admin_cli.py list-dlq

# Inspect task
python tools/admin_cli.py inspect-dlq ns_prod_20250105_120000_abcd1234

# Retry task
python tools/admin_cli.py retry-dlq ns_prod_20250105_120000_abcd1234

# Purge DLQ
python tools/admin_cli.py purge-dlq
```

---

## Phase 4 Completion Checklist

### Deliverables
- [ ] Production Docker config optimized
- [ ] TTL housekeeping running
- [ ] DLQ admin CLI functional
- [ ] Import linting passing
- [ ] Error recovery implemented
- [ ] Load tests passing (10+ concurrent)
- [ ] Complete documentation
- [ ] Deployment guide ready

### Production Deployment Steps
```bash
# 1. Build production images
cd mcp-server-source
docker build -t nessus-mcp:prod -f Dockerfile.api .
docker build -t nessus-mcp-worker:prod -f Dockerfile.worker .

# 2. Configure production environment
cd ../prod
cp .env.prod.example .env.prod
# Edit .env.prod with real credentials

# 3. Deploy
docker compose up -d

# 4. Verify health
curl http://localhost:8836/health
curl http://localhost:8836/metrics

# 5. Monitor logs
docker compose logs -f
```

### Success Criteria
✅ Phase 4 complete when:
1. Production environment running stable
2. Housekeeping deletes old tasks
3. DLQ CLI can inspect/retry tasks
4. Import linting passes
5. Load tests handle 10+ scans
6. Documentation complete
7. Deployment tested

---

## Post-Phase 4: Project Complete

### Final Verification
- [ ] All 4 phases marked complete in README.md
- [ ] All tests passing (unit + integration + load)
- [ ] Production deployment documented
- [ ] Commit final code
- [ ] Tag release: `git tag v1.0.0`
- [ ] Update project status: 🟢 Production Ready

### Handoff Checklist
- [ ] User guide delivered
- [ ] Admin guide delivered
- [ ] API reference complete
- [ ] Deployment guide tested
- [ ] Troubleshooting guide written
- [ ] Code repository clean
- [ ] Documentation up-to-date

---

**Congratulations! The Nessus MCP Server is production-ready! 🚀**
