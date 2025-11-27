# Scanner Module

> Scanner abstraction, Nessus client, and pool registry

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `base.py` | ~80 | Abstract scanner interface |
| `registry.py` | ~400 | Pool-based scanner registry |
| `nessus.py` | ~500 | Low-level Nessus REST API client |
| `nessus_scanner.py` | ~300 | High-level Nessus scanner wrapper |
| `nessus_validator.py` | ~250 | Scan result validation |
| `api_token_fetcher.py` | ~100 | Nessus API token management |
| `mock_scanner.py` | ~150 | Mock scanner for testing |

## Architecture

```
ScannerRegistry
    │
    ├── Pool: nessus
    │   ├── nessus:scanner1 → NessusScanner → NessusClient → Nessus API
    │   └── nessus:scanner2 → NessusScanner → NessusClient → Nessus API
    │
    └── Pool: nessus_dmz
        └── nessus_dmz:dmz1 → NessusScanner → NessusClient → Nessus API
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
- Environment variable substitution

### NessusScanner (nessus_scanner.py)

High-level scanner wrapper:

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

await scanner.close()
```

### NessusClient (nessus.py)

Low-level REST API client:

```python
client = NessusClient(url, username, password)
await client.login()

# Raw API calls
scans = await client.list_scans()
scan_id = await client.create_scan(name, targets, policy_template)
await client.launch_scan(scan_id)
status = await client.get_scan_status(scan_id)
xml_bytes = await client.export_scan(scan_id, format="nessus")

await client.logout()
```

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
├── nessus.py            # → httpx, ssl
├── nessus_scanner.py    # → nessus.py, base.py
├── nessus_validator.py  # → xml.etree
├── api_token_fetcher.py # → httpx
└── mock_scanner.py      # → base.py
```
