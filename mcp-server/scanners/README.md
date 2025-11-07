# Scanner Implementations

This directory contains scanner implementations that conform to the `ScannerInterface` defined in `base.py`.

## Available Scanners

### NessusScanner (nessus_scanner.py)

Production-ready async Nessus scanner using proven HTTP patterns from nessusAPIWrapper/.

**Status**: ✅ Production Ready (Phase 1A Completed)

**Features**:
- Web UI authentication with session tokens
- Bypasses Nessus Essentials `scan_api: false` restriction
- Native async/await using httpx (no subprocess calls)
- Comprehensive error handling (412/403/404/409)
- Proper HTTP session cleanup

**Key Implementation Details**:
- Static API Token: `af824aba-e642-4e63-a49b-0810542ad8a5` (required for all requests)
- Web UI Marker: `X-KL-kfa-Ajax-Request: Ajax_Request` (required for launch/stop operations)
- Session-based authentication with token cookies
- Three-step export process (request → poll → download)
- Two-step delete process (move to trash → delete)

**Documentation**:
- **[Nessus HTTP Patterns](./NESSUS_HTTP_PATTERNS.md)** ⭐ - Complete HTTP pattern reference extracted from wrapper
- **[Docker Network Config](../docs/DOCKER_NETWORK_CONFIG.md)** - Network topology and URL configuration
- **[Phase 1A Completion Report](../phases/PHASE_1A_COMPLETION_REPORT.md)** - Implementation summary

### MockNessusScanner (mock_scanner.py)

Mock scanner for testing and development.

**Status**: ✅ Stable

**Features**:
- Returns mock .nessus XML from fixtures
- Simulates scan progression over configurable duration
- Supports all ScannerInterface operations
- No external dependencies (ideal for unit tests)

## Scanner Interface (base.py)

Abstract base class defining the scanner contract:

```python
class ScannerInterface(ABC):
    async def create_scan(request: ScanRequest) -> int
    async def launch_scan(scan_id: int) -> str
    async def get_status(scan_id: int) -> Dict[str, Any]
    async def export_results(scan_id: int) -> bytes
    async def stop_scan(scan_id: int) -> bool
    async def delete_scan(scan_id: int) -> bool
    async def close() -> None  # Cleanup resources
```

## Scanner Registry (registry.py)

Manages multiple scanner instances with:
- YAML-based configuration
- Environment variable substitution
- Round-robin load balancing
- Hot-reload on SIGHUP
- Automatic fallback to mock scanner

**Configuration Example**:
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

## Network Configuration

**Critical**: URL configuration differs between host and containers:

| Context | Nessus URL | Notes |
|---------|-----------|-------|
| Host | `https://localhost:8834` | Port forwarded from vpn-gateway |
| Containers | `https://172.18.0.2:8834` or `https://vpn-gateway:8834` | Direct to VPN gateway |

See [Docker Network Configuration](../docs/DOCKER_NETWORK_CONFIG.md) for complete details.

## Usage Examples

### Direct Scanner Usage

```python
from scanners.nessus_scanner import NessusScanner
from scanners.base import ScanRequest

scanner = NessusScanner(
    url="https://172.18.0.2:8834",  # Use container URL
    username="nessus",
    password="nessus",
    verify_ssl=False
)

try:
    # Create scan
    request = ScanRequest(
        targets="192.168.1.1",
        name="Security Scan",
        scan_type="untrusted"
    )
    scan_id = await scanner.create_scan(request)

    # Launch scan
    scan_uuid = await scanner.launch_scan(scan_id)

    # Check status
    status = await scanner.get_status(scan_id)
    print(f"Status: {status['status']}, Progress: {status['progress']}%")

finally:
    await scanner.close()  # Always cleanup
```

### Via Scanner Registry

```python
from scanners.registry import ScannerRegistry

registry = ScannerRegistry(config_file="config/scanners.yaml")

# Get scanner instance (round-robin)
scanner = registry.get_instance(scanner_type="nessus")

# Use scanner...
```

## Testing

### Integration Tests

```bash
# Test scanner with real Nessus
cd mcp-server
pytest tests/integration/test_scanner_wrapper_comparison.py -v

# Test connectivity
pytest tests/integration/test_connectivity.py -v
```

### Unit Tests

```bash
# Test with mock scanner
pytest tests/unit/test_scanner_interface.py -v
```

## Adding New Scanner Types

1. Create new scanner class implementing `ScannerInterface`
2. Add configuration section to `scanners.yaml`
3. Update `registry.py` to handle new scanner type
4. Add integration tests

Example:
```python
from scanners.base import ScannerInterface, ScanRequest

class OpenVASScanner(ScannerInterface):
    async def create_scan(self, request: ScanRequest) -> int:
        # Implementation...
        pass

    # Implement other interface methods...
```

## Troubleshooting

### Connection Issues

**Problem**: Scanner can't reach Nessus

**Solution**: Check you're using the correct URL for your context:
- From host: `https://localhost:8834`
- From container: `https://172.18.0.2:8834` or `https://vpn-gateway:8834`

### Authentication Failures

**Problem**: HTTP 401 or 403 errors

**Solution**:
- Verify credentials are correct
- For launch/stop operations, ensure `X-KL-kfa-Ajax-Request` header is present
- Check Nessus server status: `curl -k https://NESSUS_URL/server/status`

### HTTP 412 Errors

**Problem**: Precondition Failed during scan operations

**Cause**: Nessus Essentials has `scan_api: false` restriction

**Solution**: NessusScanner uses Web UI simulation to bypass this - ensure you're using the latest version

## Related Documentation

- [Phase 1A Completion Report](../phases/PHASE_1A_COMPLETION_REPORT.md) - Scanner rewrite summary
- [Nessus HTTP Patterns](./NESSUS_HTTP_PATTERNS.md) - Complete HTTP reference
- [Docker Network Config](../docs/DOCKER_NETWORK_CONFIG.md) - Network setup guide
- [Architecture v2.2](../ARCHITECTURE_v2.2.md) - Overall system design
