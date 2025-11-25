# Scanner Pool Configuration Guide

> **Phase 4 Feature**: Pool-based scanner grouping with queue isolation

## Overview

Scanner pools group scanners by purpose, network zone, or vendor. Each pool has:
- Its own Redis queue for task isolation
- Independent load balancing within the pool
- Separate Dead Letter Queue for failed tasks

## Pool Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Client                                │
│   run_untrusted_scan(scanner_pool="nessus_dmz", ...)            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Redis Queues                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ nessus:queue │  │nessus_dmz:   │  │nessus_lan:   │          │
│  │              │  │    queue     │  │    queue     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐          │
│  │nessus:queue: │  │nessus_dmz:   │  │nessus_lan:   │          │
│  │    dead      │  │  queue:dead  │  │  queue:dead  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Scanner Workers                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Worker (WORKER_POOLS=nessus,nessus_dmz)                 │    │
│  │   └─► dequeue_any([nessus:queue, nessus_dmz:queue])     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Scanner Instances                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Pool:     │  │   Pool:     │  │   Pool:     │              │
│  │   nessus    │  │ nessus_dmz  │  │ nessus_lan  │              │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │              │
│  │ │scanner1 │ │  │ │dmz-scan1│ │  │ │lan-scan1│ │              │
│  │ │scanner2 │ │  │ └─────────┘ │  │ │lan-scan2│ │              │
│  │ └─────────┘ │  │             │  │ └─────────┘ │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Using Pools from MCP Client

### Submitting Scans to a Pool

```python
from client.nessus_fastmcp_client import NessusFastMCPClient

async with NessusFastMCPClient() as client:
    # Default pool (nessus)
    result = await client.call_tool("run_untrusted_scan", {
        "targets": "192.168.1.0/24",
        "name": "Default Pool Scan"
    })

    # Specific pool - routes to DMZ queue
    result = await client.call_tool("run_untrusted_scan", {
        "targets": "10.0.0.0/24",
        "name": "DMZ Scan",
        "scanner_pool": "nessus_dmz"
    })
```

### Querying Pool Information

```python
# List all available pools
pools = await client.call_tool("list_pools", {})
# Returns: {"pools": ["nessus", "nessus_dmz"], "default_pool": "nessus"}

# List scanners in a specific pool
scanners = await client.call_tool("list_scanners", {"scanner_pool": "nessus_dmz"})

# Get pool capacity/utilization
status = await client.call_tool("get_pool_status", {"scanner_pool": "nessus_dmz"})
# Returns: {"pool": "nessus_dmz", "total_scanners": 1, "total_capacity": 3,
#           "total_active": 1, "utilization_pct": 33.3, ...}

# Get queue depth for a pool
queue = await client.call_tool("get_queue_status", {"scanner_pool": "nessus_dmz"})
# Returns: {"pool": "nessus_dmz", "queue_depth": 5, "dlq_size": 0, ...}

# List tasks filtered by pool
tasks = await client.call_tool("list_tasks", {"scanner_pool": "nessus_dmz"})
```

## Pool Configuration

Pools are defined in `config/scanners.yaml`. Each top-level key is a pool name.

### Configuration File Structure

```yaml
# config/scanners.yaml

# Pool: nessus (default general-purpose pool)
nessus:
  - instance_id: scanner1
    name: "Nessus Scanner 1"
    url: ${NESSUS_URL:-https://172.30.0.3:8834}
    username: ${NESSUS_USERNAME:-nessus}
    password: ${NESSUS_PASSWORD:-nessus}
    enabled: true
    max_concurrent_scans: 5

  - instance_id: scanner2
    name: "Nessus Scanner 2"
    url: ${NESSUS_URL_2:-https://172.30.0.4:8834}
    username: ${NESSUS_USERNAME_2:-nessus}
    password: ${NESSUS_PASSWORD_2:-nessus}
    enabled: true
    max_concurrent_scans: 5

# Pool: nessus_dmz (DMZ network scanning)
nessus_dmz:
  - instance_id: dmz-scanner1
    name: "DMZ Nessus Scanner"
    url: ${NESSUS_DMZ_URL:-https://dmz-scanner:8834}
    username: ${NESSUS_DMZ_USERNAME:-admin}
    password: ${NESSUS_DMZ_PASSWORD}
    enabled: true
    max_concurrent_scans: 3

# Pool: nessus_lan (Internal LAN scanning)
nessus_lan:
  - instance_id: lan-scanner1
    name: "LAN Scanner 1"
    url: ${NESSUS_LAN_URL:-https://lan-scanner1:8834}
    username: ${NESSUS_LAN_USERNAME:-admin}
    password: ${NESSUS_LAN_PASSWORD}
    enabled: true
    max_concurrent_scans: 5

  - instance_id: lan-scanner2
    name: "LAN Scanner 2"
    url: ${NESSUS_LAN_URL_2:-https://lan-scanner2:8834}
    username: ${NESSUS_LAN_USERNAME:-admin}
    password: ${NESSUS_LAN_PASSWORD}
    enabled: true
    max_concurrent_scans: 5
```

### Adding a Scanner to an Existing Pool

Add another entry under the pool:

```yaml
nessus:
  - instance_id: scanner1
    # ... existing config

  - instance_id: scanner2
    # ... existing config

  # NEW SCANNER
  - instance_id: scanner3
    name: "Nessus Scanner 3"
    url: ${NESSUS_URL_3:-https://172.30.0.5:8834}
    username: ${NESSUS_USERNAME_3:-nessus}
    password: ${NESSUS_PASSWORD_3:-nessus}
    enabled: true
    max_concurrent_scans: 5
```

### Creating a New Pool

Add a new top-level key with scanners:

```yaml
# NEW POOL: Cloud infrastructure scanning
nessus_cloud:
  - instance_id: cloud-scanner1
    name: "Cloud Scanner"
    url: ${NESSUS_CLOUD_URL}
    username: ${NESSUS_CLOUD_USERNAME}
    password: ${NESSUS_CLOUD_PASSWORD}
    enabled: true
    max_concurrent_scans: 10
```

### Applying Configuration Changes

**Option 1: Restart the MCP server**
```bash
docker compose restart mcp-api
```

**Option 2: Hot-reload via SIGHUP** (no downtime)
```bash
docker compose exec mcp-api kill -HUP 1
```

## Pool Naming Convention

| Pool Name | Use Case | Scanner Type |
|-----------|----------|--------------|
| `nessus` | Default general-purpose pool | Nessus |
| `nessus_dmz` | DMZ/perimeter network scanning | Nessus |
| `nessus_lan` | Internal LAN scanning | Nessus |
| `nessus_cloud` | Cloud infrastructure scanning | Nessus |
| `nuclei` | Web vulnerability scanning (future) | Nuclei |
| `openvas` | Open-source scanning (future) | OpenVAS |

**Note**: The pool name prefix determines the scanner type:
- `nessus*` → NessusScanner
- `nuclei*` → NucleiScanner (future)
- `openvas*` → OpenVASScanner (future)

## Worker Pool Configuration

Workers can be configured to consume from specific pools:

### Docker Compose Configuration

```yaml
# docker-compose.yml
services:
  # Worker for main pool only
  worker-main:
    image: nessus-mcp:worker
    environment:
      - WORKER_POOLS=nessus
      - MAX_CONCURRENT_SCANS=5

  # Worker for DMZ pool only (isolated)
  worker-dmz:
    image: nessus-mcp:worker
    environment:
      - WORKER_POOLS=nessus_dmz
      - MAX_CONCURRENT_SCANS=3

  # Worker for all pools (general purpose)
  worker-all:
    image: nessus-mcp:worker
    environment:
      - WORKER_POOLS=  # Empty = consume from ALL pools
      - MAX_CONCURRENT_SCANS=10
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WORKER_POOLS` | Comma-separated list of pools to consume from | All pools |
| `MAX_CONCURRENT_SCANS` | Maximum parallel scans per worker | 5 |
| `SCANNER_CONFIG` | Path to scanners.yaml | /app/config/scanners.yaml |

## Load Balancing Within Pools

Within each pool, the scanner registry performs load-based selection:

1. **Capacity Check**: Only scanners with `active_scans < max_concurrent_scans`
2. **Utilization Sort**: Prefer lowest utilization percentage
3. **Tie-breaker**: Least recently used scanner

```python
# Example: Pool with 2 scanners
# scanner1: active_scans=3, max_concurrent=5 (60% utilization)
# scanner2: active_scans=1, max_concurrent=5 (20% utilization)
#
# Next task goes to scanner2 (lower utilization)
```

## Redis Queue Keys

| Key Pattern | Description |
|-------------|-------------|
| `{pool}:queue` | Main task queue (FIFO via LPUSH/BRPOP) |
| `{pool}:queue:dead` | Dead Letter Queue (sorted set by timestamp) |

Examples:
- `nessus:queue` - Default pool main queue
- `nessus_dmz:queue` - DMZ pool main queue
- `nessus:queue:dead` - Default pool DLQ
- `nessus_dmz:queue:dead` - DMZ pool DLQ

## Backward Compatibility

- **Default Pool**: When `scanner_pool` is not specified, the default pool (`nessus`) is used
- **scanner_type Parameter**: Still works for backward compatibility (maps to pool name)
- **Existing Tasks**: Tasks without `scanner_pool` field work correctly (fall back to `scanner_type`)

## Related Documentation

- [Architecture v2.2](./ARCHITECTURE_v2.2.md) - Overall system design
- [scanners/registry.py](../scanners/registry.py) - Pool-aware scanner registry
- [core/queue.py](../core/queue.py) - Pool-aware task queue
- [worker/scanner_worker.py](../worker/scanner_worker.py) - Pool-aware worker
