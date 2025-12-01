<!-- README Navigation -->
<!-- L3: mcp-server/scanners/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Scanner abstraction, Nessus client, pool registry -->

# Scanner Module

> Scanner abstraction, Nessus client, and pool registry

**↑ Parent**: [MCP Server](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `base.py` | ~70 | Abstract scanner interface and ScanRequest dataclass |
| `registry.py` | ~670 | Pool-based scanner registry with load balancing |
| `nessus_scanner.py` | ~835 | High-level Nessus scanner (main implementation) |
| `nessus_validator.py` | ~235 | Scan result validation and auth status detection |
| `api_token_fetcher.py` | ~145 | Dynamic X-API-Token fetching from Nessus Web UI |
| `mock_scanner.py` | ~110 | Mock scanner for testing |
| `nessus.py` | ~80 | Low-level Nessus client stub (minimal) |

## Architecture

```
ScannerRegistry
    │
    ├── Pool: nessus
    │   ├── nessus:scanner1 → NessusScanner → Nessus API
    │   └── nessus:scanner2 → NessusScanner → Nessus API
    │
    └── Pool: nessus_dmz
        └── nessus_dmz:dmz1 → NessusScanner → Nessus API
```

## Key Classes

### ScannerInterface (base.py)

Abstract interface for scanner backends:

```python
class ScannerInterface(ABC):
    async def create_scan(request: ScanRequest) -> int
    async def launch_scan(scan_id: int) -> str
    async def get_status(scan_id: int) -> Dict
    async def export_results(scan_id: int) -> bytes
    async def stop_scan(scan_id: int) -> bool
    async def delete_scan(scan_id: int) -> bool
    async def close() -> None  # Cleanup HTTP sessions
```

### ScanRequest (base.py)

```python
@dataclass
class ScanRequest:
    targets: str          # "192.168.1.0/24"
    name: str             # Scan name
    scan_type: str        # "untrusted" | "authenticated" | "authenticated_privileged"
    description: str
    credentials: Dict     # SSH credentials for auth scans
    schema_profile: str   # "minimal" | "summary" | "brief" | "full"
```

### ScannerRegistry (registry.py)

Pool-based scanner management:

```python
registry = ScannerRegistry(config_file="config/scanners.yaml")

# List pools
pools = registry.list_pools()  # ["nessus", "nessus_dmz"]

# Get least loaded scanner
scanner, key = registry.get_available_scanner(pool="nessus")

# Acquire/release for tracking
scanner, key = await registry.acquire_scanner(pool="nessus")
await registry.release_scanner(key)

# Pool capacity
capacity = registry.get_pool_capacity(pool="nessus")  # 4
```

**Features**:
- Pool-based grouping
- Load-based selection (least active scans)
- Hot-reload on SIGHUP
- Environment variable substitution in config

**Configuration Example** (`config/scanners.yaml`):
```yaml
nessus:
  - instance_id: local
    name: "Local Nessus Scanner"
    url: ${NESSUS_URL:-https://vpn-gateway:8834}
    username: ${NESSUS_USERNAME:-nessus}
    password: ${NESSUS_PASSWORD:-nessus}
    enabled: true
    max_concurrent_scans: 10
```

### NessusScanner (nessus_scanner.py)

High-level scanner wrapper with Web UI simulation:

```python
scanner = NessusScanner(url, username, password, verify_ssl=False)

# Create and launch scan
scan_id = await scanner.create_scan(ScanRequest(...))
uuid = await scanner.launch_scan(scan_id)

# Monitor
status = await scanner.get_status(scan_id)
# {"status": "running", "progress": 45}

# Export results
nessus_xml = await scanner.export_results(scan_id)

await scanner.close()  # Always cleanup
```

**Key Implementation Details**:
- **Dynamic X-API-Token**: Fetched from `/nessus6.js` at runtime (adapts to Nessus rebuilds)
- **Web UI Marker**: `X-KL-kfa-Ajax-Request: Ajax_Request` required for launch/stop operations
- **Bypasses `scan_api: false`**: Uses Web UI simulation for Nessus Essentials
- **Session-based auth**: Token cookies with auto-refresh on 401
- **Three-step export**: Request → Poll status → Download
- **Two-step delete**: Move to trash → Delete from trash
- **Error handling**: 412/403/404/409 with appropriate retry logic

### NessusValidator (nessus_validator.py)

Result validation:

```python
from scanners.nessus_validator import validate_scan_results

result = validate_scan_results(
    nessus_file=Path("scan.nessus"),
    scan_type="authenticated"
)

# result.is_valid: bool
# result.error: Optional[str]
# result.stats: {"hosts_scanned": 1, "total_vulnerabilities": 42}
# result.authentication_status: "success" | "failed" | "partial" | "not_applicable"
```

**Validates**:
- XML well-formed
- Hosts found
- Authentication success (for auth scans)
- Plugin 141118 - "Valid Credentials Provided"
- Plugin 110385 - "Insufficient Privilege"

## Scan Types

| Type | Credentials | Use Case |
|------|-------------|----------|
| `untrusted` | None | Network-only scan |
| `authenticated` | SSH | Login to target |
| `authenticated_privileged` | SSH + sudo | Root-level scan |

## Authentication Flow

```
Authenticated scan:
1. Create scan with SSH credentials
2. Nessus logs into target
3. Plugin 141118 confirms success
4. Plugin 110385 indicates privilege level
5. Validator checks auth status
```

## Dependencies

```
scanners/
├── base.py              # No dependencies
├── registry.py          # → yaml, nessus_scanner, mock_scanner
├── nessus_scanner.py    # → httpx, api_token_fetcher, base
├── nessus_validator.py  # → xml.etree
├── api_token_fetcher.py # → httpx
└── mock_scanner.py      # → base.py
```

## Network Configuration

Network topology is environment-specific. To discover current configuration:

```bash
# List running containers and networks
docker compose ps
docker network ls

# Get container IPs
docker inspect <container_name> | grep IPAddress

# Check Nessus connectivity from MCP container
docker exec mcp-server curl -k https://<nessus_ip>:8834/server/status
```

**Docker Compose files**:
- `dev1/docker-compose.yml` - Development environment
- `mcp-server/prod/docker-compose.yml` - Production
- `scanners-infra/docker-compose.yml` - Scanner infrastructure

## Testing

See [../docs/TESTING.md](../docs/TESTING.md) for comprehensive test documentation.

**Quick test commands**:
```bash
cd mcp-server

# Integration tests with real Nessus
pytest tests/integration/test_nessus_scanner.py -v
pytest tests/integration/test_connectivity.py -v

# Unit tests
pytest tests/unit/test_nessus_validator.py -v
pytest tests/unit/test_pool_registry.py -v
```

## Adding New Scanner Types

1. Create new scanner class implementing `ScannerInterface`:

```python
from scanners.base import ScannerInterface, ScanRequest

class OpenVASScanner(ScannerInterface):
    async def create_scan(self, request: ScanRequest) -> int:
        # Implementation...
        pass

    async def launch_scan(self, scan_id: int) -> str:
        pass

    async def get_status(self, scan_id: int) -> Dict[str, Any]:
        pass

    async def export_results(self, scan_id: int) -> bytes:
        pass

    async def stop_scan(self, scan_id: int) -> bool:
        pass

    async def delete_scan(self, scan_id: int) -> bool:
        pass

    async def close(self) -> None:
        pass
```

2. Add configuration section to `config/scanners.yaml`
3. Update `registry.py` to handle new scanner type
4. Add integration tests

## Troubleshooting

### Connection Issues

**Problem**: Scanner can't reach Nessus

**Solution**: Verify URL matches your context:
```bash
# Check Nessus is reachable
curl -k https://<NESSUS_URL>:8834/server/status

# From container
docker exec mcp-server curl -k https://vpn-gateway:8834/server/status
```

### Authentication Failures

**Problem**: HTTP 401 or 403 errors

**Solution**:
- Verify credentials are correct
- For launch/stop operations, ensure `X-KL-kfa-Ajax-Request` header is present (handled by NessusScanner automatically)
- Check if session expired (NessusScanner auto-refreshes on 401)

### HTTP 412 Errors

**Problem**: Precondition Failed during scan operations

**Cause**: Nessus Essentials has `scan_api: false` restriction

**Solution**: NessusScanner uses Web UI simulation to bypass this. Ensure you're using `NessusScanner` class, not direct API calls.

### Export Timeout

**Problem**: Export takes too long or times out

**Solution**:
- Default timeout is 5 minutes (150 × 2s polls)
- Large scans may need longer - check scan completed before export
- Verify Nessus isn't under heavy load

## Related Documentation

- [NESSUS_HTTP_PATTERNS.md](./NESSUS_HTTP_PATTERNS.md) - Low-level HTTP reference (note: X-API-Token is now dynamic)
- [../docs/ARCHITECTURE_v2.2.md](../docs/ARCHITECTURE_v2.2.md) - Overall system architecture
- [../docs/TESTING.md](../docs/TESTING.md) - Test documentation
- [../docs/SCANNER_POOLS.md](../docs/SCANNER_POOLS.md) - Pool configuration details
