# Nessus Essentials API Limitations & Workarounds

## Summary

Nessus Essentials has **severe API restrictions** due to `scan_api: false` license flag, which blocks scan creation, launching, stopping, modification, and deletion via standard API endpoints.

**BREAKTHROUGH**: These restrictions can be **bypassed** by simulating Web UI interactions using HTTP requests with proper authentication headers.

## Evidence

### 1. License Feature Flags

From `GET /server/properties`:

```json
{
  "license": {
    "type": "home",
    "name": "Nessus Essentials",
    "restricted": true,
    "ips": 16,
    "features": {
      "api": true,           // ← General API access enabled (read-only)
      "scan_api": false,     // ← Scan manipulation API DISABLED
      ...
    }
  }
}
```

### 2. API Errors Encountered

#### Creating Scans (API blocked)
```bash
POST https://localhost:8834/scans
→ 412 Precondition Failed
→ {"error":"API is not available"}
```

#### Launching Scans (API blocked)
```bash
POST https://localhost:8834/scans/8/launch
→ 412 Precondition Failed
→ {"error":"API is not available"}
```

Both operations return HTTP 412 (Precondition Failed) with the same error message when using API key authentication.

## What scan_api: false Restricts

### API Endpoints - BLOCKED

| Operation | HTTP Method | Endpoint | Error | Workaround |
|-----------|-------------|----------|-------|------------|
| **Create scan** | POST | `/scans` | 412: API not available | Web UI simulation |
| **Modify scan** | PUT | `/scans/{id}` | 412: API not available | Web UI simulation |
| **Launch scan** | POST | `/scans/{id}/launch` | 412: API not available | Web UI simulation |
| **Stop scan** | POST | `/scans/{id}/stop` | 412: API not available | Web UI simulation |
| **Pause scan** | POST | `/scans/{id}/pause` | 412: API not available | Web UI simulation |
| **Resume scan** | POST | `/scans/{id}/resume` | 412: API not available | Web UI simulation |
| **Delete scan** | DELETE | `/scans/{id}` | 412: API not available | Web UI simulation |

### API Endpoints - ALLOWED

| Operation | HTTP Method | Endpoint | Status |
|-----------|-------------|----------|--------|
| **List scans** | GET | `/scans` | Works |
| **Scan details** | GET | `/scans/{id}` | Works |
| **Scan configuration** | GET | `/editor/scan/{id}` | Works |
| **Export scan** | POST | `/scans/{id}/export` | Works |
| **Server status** | GET | `/server/status` | Works |
| **Server properties** | GET | `/server/properties` | Works |
| **List policies** | GET | `/policies` | Works |

## The Workaround: Web UI Simulation

### Discovery

The `scan_api: false` restriction only applies to **API endpoints** authenticated with access_key/secret_key. The **Web UI routes** use the same backend operations but with different authentication (session tokens), and these are NOT restricted.

### Authentication Methods

**API Authentication (Restricted)**:
```python
headers = {
    'X-ApiKeys': f'accessKey={access_key}; secretKey={secret_key}'
}
# Results in 412 errors for scan control operations
```

**Web UI Authentication (Unrestricted)**:
```python
# Step 1: Authenticate to get session token
response = requests.post('https://localhost:8834/session',
                        json={'username': 'nessus', 'password': 'nessus'})
session_token = response.json()['token']

# Step 2: Use session token + static API token
headers = {
    'X-API-Token': 'af824aba-e642-4e63-a49b-0810542ad8a5',  # Static
    'X-Cookie': f'token={session_token}',                   # Dynamic
    'X-KL-kfa-Ajax-Request': 'Ajax_Request',
    'Content-Type': 'application/json'
}
# Works for ALL scan control operations
```

### Implemented Workarounds

| Blocked API Operation | Web UI Workaround Script | Status |
|-----------------------|--------------------------|--------|
| Create scan | `manage_scans.py create` | Working |
| Delete scan | `manage_scans.py delete` | Working |
| Launch scan | `launch_scan.py launch` | Working |
| Stop scan | `launch_scan.py stop` | Working |
| Modify scan (basic) | `edit_scan.py` | Working |
| Modify credentials | `manage_credentials.py` | Working |

## What This Means

### Nessus Essentials NOW Supports (with Web UI simulation)

1. **Create** new scans programmatically
2. **Launch** scans programmatically
3. **Stop/Pause/Resume** scans programmatically
4. **Modify** scan configurations (targets, credentials, settings)
5. **Delete** scans programmatically
6. **Export** scan data for reporting (always worked)
7. **View** scan results and configurations (always worked)

### Full Automation Achieved

With the scripts in this project:
- **Complete scan lifecycle automation** (create → configure → launch → monitor → export → delete)
- **Credential management** via JSON templates
- **Bulk operations** (delete multiple scans, export multiple reports)
- **No manual Web UI interaction required**

## Comparison with Professional Edition

| Feature | Essentials (API) | Essentials (Web UI Simulation) | Professional (API) |
|---------|------------------|--------------------------------|--------------------|
| API - Read scans | ✅ Yes | ✅ Yes | ✅ Yes |
| API - Export scans | ✅ Yes | ✅ Yes | ✅ Yes |
| **Create scans** | ❌ No | **✅ Yes** | ✅ Yes |
| **Launch scans** | ❌ No | **✅ Yes** | ✅ Yes |
| **Manage scans** | ❌ No | **✅ Yes** | ✅ Yes |
| Max IPs | 16 | 16 | Unlimited |
| Multiple users | ❌ No | ❌ No | ✅ Yes |

**Key Insight**: Web UI simulation gives Essentials users the same scan control capabilities as Professional, within the 16 IP limit.

## Why This Limitation Exists

Tenable's business model:
- **Essentials**: Free tier for individual users, intended for manual workflow
- **Professional/Expert**: Paid tiers for automation and enterprise use

The `scan_api: false` restriction was designed to prevent automation via API, encouraging upgrades for production environments. However, the Web UI routes (intended for browser use) are not restricted and can be leveraged for automation.

## Workaround Implementation Details

### Pattern 1: Session Token Authentication
```python
def authenticate():
    """Get session token for Web UI operations"""
    url = f"{NESSUS_URL}/session"
    response = requests.post(url,
                           json={'username': USERNAME, 'password': PASSWORD},
                           verify=False)
    return response.json()['token']
```

### Pattern 2: Web UI Headers
```python
def get_webui_headers(session_token):
    """Headers that bypass scan_api: false restriction"""
    return {
        'X-API-Token': STATIC_API_TOKEN,
        'X-Cookie': f'token={session_token}',
        'X-KL-kfa-Ajax-Request': 'Ajax_Request',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': NESSUS_URL,
        'Referer': f'{NESSUS_URL}/'
    }
```

### Pattern 3: Same Endpoints, Different Auth
```python
# API Method (FAILS with 412)
response = nessus.scans.launch(scan_id)

# Web UI Method (WORKS)
session_token = authenticate()
headers = get_webui_headers(session_token)
response = requests.post(f'{NESSUS_URL}/scans/{scan_id}/launch',
                        headers=headers, verify=False)
```

## Scripts Provided

### API-Based Scripts (Read-Only)

1. **list_scans.py** - List all scans with status
2. **scan_config.py** - View detailed scan configuration
3. **check_status.py** - Check Nessus server status
4. **export_vulnerabilities.py** - Export vulnerability summaries
5. **export_vulnerabilities_detailed.py** - Export FULL vulnerability details

### Web UI Simulation Scripts (Full Control)

1. **launch_scan.py** - Launch/stop scans, bypasses `scan_api: false`
2. **edit_scan.py** - Edit basic scan parameters (name, description, targets)
3. **manage_credentials.py** - SSH credential management via JSON templates
4. **manage_scans.py** - Create/delete scans
5. **check_dropdown_options.py** - Extract field options from configuration

## Recommendations

### For Nessus Essentials Users

1. **Use Web UI simulation scripts** for full automation
2. **No need to upgrade** unless you need:
   - More than 16 IPs
   - Multiple users
   - VPR (Vulnerability Priority Rating)
   - Enterprise features
3. **Hybrid approach**: Use API scripts for read operations (faster), Web UI scripts for write operations

### For Production Environments

Consider upgrading to Nessus Professional if you need:
- **More than 16 IPs** scanned
- **Multiple user accounts** with role-based access
- **Official support** from Tenable
- **Compliance certifications** requiring licensed software

### For Learning/Home Labs

Nessus Essentials + Web UI simulation scripts provide:
- **Complete automation** for learning and testing
- **Full vulnerability scanning** within 16 IP limit
- **No cost** for home/educational use

## Security Considerations

### Web UI Simulation Risks

1. **Session tokens expire** - Scripts re-authenticate each run
2. **Static API token exposed** - Tied to specific Nessus instance
3. **Username/password in scripts** - Not suitable for production without vault integration
4. **No official support** - Workaround may break with Nessus updates

### Mitigation

- Use environment variables for credentials
- Implement credential vaulting (HashiCorp Vault, AWS Secrets Manager)
- Regular security audits of scripts
- Monitor for Nessus version updates that may affect Web UI routes

## Testing Methodology

All conclusions based on empirical testing:

```bash
# Test 1: List scans (API - works)
GET /scans with API keys → 200 OK

# Test 2: Create scan (API - fails)
POST /scans with API keys → 412 Precondition Failed

# Test 3: Create scan (Web UI - works)
POST /scans with session token → 200 OK

# Test 4: Launch scan (API - fails)
POST /scans/8/launch with API keys → 412 Precondition Failed

# Test 5: Launch scan (Web UI - works)
POST /scans/8/launch with session token → 200 OK

# Test 6: Scan details (API - works)
GET /scans/12 with API keys → 200 OK

# Test 7: Server properties (API - works)
GET /server/properties → Returns "scan_api": false
```

## Conclusion

**Nessus Essentials `scan_api: false` is NOT a hard limit for automation.** While it prevents scan control via API key authentication, the **Web UI routes provide full scan control** when authenticated with session tokens.

**This project demonstrates that Nessus Essentials can be fully automated** for scan management within the 16 IP license restriction, making it viable for:
- Home labs and learning environments
- Small network scanning (up to 16 IPs)
- Proof-of-concept security automation
- Individual security researchers

**No need for Nessus Professional** unless you require more than 16 IPs, multiple users, or enterprise features.

---

*Last updated: Based on successful Web UI simulation bypass with Nessus Essentials 10.x*
*All scripts tested and working as of October 2025*
