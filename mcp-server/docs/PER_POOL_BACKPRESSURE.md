# Per-Pool Backpressure Implementation

**Status:** PLANNING
**Created:** 2025-11-27

## Problem

Current worker has a single global `MAX_CONCURRENT_SCANS` limit that:
- Is hardcoded in docker-compose.yml
- Doesn't reflect actual scanner capacity from scanners.yaml
- Applies globally across all pools

## Solution

Per-pool backpressure where each pool's limit is derived from its scanner configuration.

## Design

### Capacity Calculation

```
Pool capacity = sum(max_concurrent_scans for all scanners in pool)

Example:
  nessus pool:
    scanner1: max_concurrent_scans=2
    scanner2: max_concurrent_scans=2
    → pool capacity = 4

  nessus_dmz pool:
    dmz-scanner1: max_concurrent_scans=3
    → pool capacity = 3
```

### Data Flow

```
scanners.yaml
    ↓
ScannerRegistry.get_pool_capacity(pool) → int
    ↓
ScannerWorker.active_tasks_per_pool[pool] → set
    ↓
Worker loop: only dequeue from pools with available capacity
```

## Changes Required

### 1. ScannerRegistry (scanners/registry.py)

Add method:
```python
def get_pool_capacity(self, pool: str) -> int:
    """
    Get total capacity for a pool (sum of all scanner max_concurrent_scans).

    Args:
        pool: Pool name (e.g., "nessus")

    Returns:
        Total max_concurrent_scans across all scanners in pool
    """
    total = 0
    for key, data in self._instances.items():
        if key.startswith(f"{pool}:"):
            total += data.get("max_concurrent_scans", 1)
    return total
```

### 2. ScannerWorker (worker/scanner_worker.py)

**Remove:**
- `max_concurrent_scans` parameter from `__init__`
- Global `self.active_tasks` set

**Add:**
```python
# Per-pool active task tracking
self.active_tasks_per_pool: Dict[str, Set[asyncio.Task]] = {
    pool: set() for pool in self.pools
}

def _get_pool_capacity(self, pool: str) -> int:
    """Get capacity for pool from scanner registry."""
    return self.scanner_registry.get_pool_capacity(pool)

def _get_pools_with_capacity(self) -> List[str]:
    """Return pools that have available capacity."""
    available = []
    for pool in self.pools:
        active = len(self.active_tasks_per_pool[pool])
        capacity = self._get_pool_capacity(pool)
        if active < capacity:
            available.append(pool)
    return available
```

**Modify worker loop:**
```python
# Before
if len(self.active_tasks) >= self.max_concurrent_scans:
    logger.debug(f"At capacity ({len(self.active_tasks)}/{self.max_concurrent_scans}), waiting...")
    await asyncio.sleep(1)
    continue

# After
pools_with_capacity = self._get_pools_with_capacity()
if not pools_with_capacity:
    # Log per-pool status
    status = {p: f"{len(self.active_tasks_per_pool[p])}/{self._get_pool_capacity(p)}"
              for p in self.pools}
    logger.debug(f"All pools at capacity: {status}, waiting...")
    await asyncio.sleep(1)
    continue

# Only dequeue from pools with capacity
task_data = await asyncio.to_thread(
    self.queue.dequeue_any,
    pools=pools_with_capacity,  # Changed from self.pools
    timeout=5
)
```

**Track tasks per pool:**
```python
# When spawning task
pool = task_data.get("scanner_pool", "nessus")
task = asyncio.create_task(self._process_scan(task_data))
self.active_tasks_per_pool[pool].add(task)

# Cleanup completed tasks (in loop)
for pool in self.pools:
    self.active_tasks_per_pool[pool] = {
        t for t in self.active_tasks_per_pool[pool] if not t.done()
    }
```

### 3. Worker Entry Point (worker/__main__.py)

**Remove:**
```python
max_concurrent = int(os.getenv("MAX_CONCURRENT_SCANS", "5"))
```

**Change worker instantiation:**
```python
# Before
worker = ScannerWorker(queue, task_manager, registry, max_concurrent_scans=max_concurrent)

# After
worker = ScannerWorker(queue, task_manager, registry)
# Capacity derived from registry automatically
```

### 4. Docker Compose (dev1/docker-compose.yml)

**Remove:**
```yaml
- MAX_CONCURRENT_SCANS=3
```

### 5. Add Future Work Comments

In `scanner_worker.py` near capacity check:
```python
# TODO: Future enhancement - Target network limits
# Different target networks may have different scan capacity based on:
# - Target infrastructure resources (CPU/RAM consumption during scans)
# - Network bandwidth constraints
# - Compliance requirements (e.g., production vs lab)
#
# Potential implementation:
# target_limits:
#   - cidr: "172.32.0.0/24"
#     max_concurrent_scans: 2
#   - cidr: "10.0.0.0/8"
#     max_concurrent_scans: 10
#   - default: 5
#
# Would require checking target CIDR against limits before allowing scan.
```

## Testing

1. Unit tests for `get_pool_capacity()`
2. Unit tests for per-pool task tracking
3. Integration test: submit more scans than capacity, verify queueing
4. Verify logs show per-pool capacity status

## Migration

1. Deploy new code
2. Restart worker (picks up new logic)
3. Remove `MAX_CONCURRENT_SCANS` from docker-compose.yml
4. Restart again (env var removal)

Or combine: update docker-compose.yml and deploy together.

## Rollback

If issues, add back `MAX_CONCURRENT_SCANS` env var with fallback logic:
```python
# Fallback if env var set (for emergency override)
override = os.getenv("MAX_CONCURRENT_SCANS")
if override:
    return int(override) // len(self.pools)  # Distribute across pools
```
