<!-- README Navigation -->
<!-- L3: mcp-server/config/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Scanner pool configuration files -->

# Configuration

> Scanner pool configuration files

**↑ Parent**: [MCP Server](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

## Files

| File | Purpose |
|------|---------|
| `scanners.yaml` | Scanner pool and instance definitions |

## scanners.yaml Structure

```yaml
# Pool name becomes queue name: {pool}:queue
nessus:
  - instance_id: scanner1       # Unique within pool
    name: "Nessus Scanner 1"    # Human-readable name
    url: https://172.30.0.3:8834
    username: nessus
    password: nessus
    enabled: true
    max_concurrent_scans: 2     # Capacity for backpressure
```

## Pool Configuration

### Pool Naming Convention

| Pattern | Example | Use Case |
|---------|---------|----------|
| `{vendor}` | `nessus` | Single-zone setup |
| `{vendor}_{zone}` | `nessus_dmz` | Multi-zone setup |

### Instance Fields

| Field | Required | Description |
|-------|----------|-------------|
| `instance_id` | Yes | Unique ID within pool |
| `name` | Yes | Display name |
| `url` | Yes | Scanner API endpoint |
| `username` | Yes | API username |
| `password` | Yes | API password |
| `enabled` | No | Enable/disable (default: true) |
| `max_concurrent_scans` | No | Capacity limit (default: 5) |

## Environment Variable Substitution

Config supports `${VAR}` and `${VAR:-default}`:

```yaml
url: ${NESSUS_URL:-https://172.30.0.3:8834}
password: ${NESSUS_PASSWORD}
```

## Queue Mapping

Each pool gets its own Redis queue:

| Pool | Queue Key | DLQ Key |
|------|-----------|---------|
| `nessus` | `nessus:queue` | `nessus:queue:dead` |
| `nessus_dmz` | `nessus_dmz:queue` | `nessus_dmz:queue:dead` |

## Capacity Calculation

Per-pool capacity = sum of `max_concurrent_scans` for all instances:

```
nessus pool:
  scanner1: max_concurrent_scans=2
  scanner2: max_concurrent_scans=2
  → Total capacity: 4 concurrent scans
```

## Adding a Scanner

1. Add instance to pool in `scanners.yaml`:
   ```yaml
   nessus:
     # ... existing scanners ...
     - instance_id: scanner3
       name: "Nessus Scanner 3"
       url: https://new-scanner:8834
       username: admin
       password: ${NESSUS_PASSWORD_3}
       enabled: true
       max_concurrent_scans: 3
   ```

2. Restart MCP server and worker

## Adding a Pool

1. Add pool section to `scanners.yaml`:
   ```yaml
   nessus_dmz:
     - instance_id: dmz-scanner1
       name: "DMZ Scanner"
       url: ${NESSUS_DMZ_URL}
       username: ${NESSUS_DMZ_USER}
       password: ${NESSUS_DMZ_PASS}
       max_concurrent_scans: 2
   ```

2. Update worker `WORKER_POOLS` to include new pool (or leave empty for all)

3. Restart services

## Validation

Config is validated on startup by `ScannerRegistry`:
- All required fields present
- URLs are valid
- Environment variables resolved
- At least one scanner enabled per pool

Validation errors logged and service won't start if critical.
