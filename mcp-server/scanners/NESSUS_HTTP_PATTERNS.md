# Nessus HTTP Patterns - Extracted from Proven Wrappers

> **Purpose**: Exact HTTP patterns from nessusAPIWrapper for Phase 1A scanner implementation
> **Status**: Reference Document
> **Source**: nessusAPIWrapper/manage_scans.py, launch_scan.py, export_vulnerabilities.py

---

> **IMPORTANT - Dynamic Token Update**
>
> This document references a static `X-API-Token`. The current `nessus_scanner.py` implementation
> now **dynamically fetches** the token from `/nessus6.js` via `api_token_fetcher.py`. This ensures
> compatibility when Nessus is rebuilt/reinstalled (token changes). The HTTP patterns below remain
> valid, but use the dynamically fetched token instead of the hardcoded value shown.

---

## Overview

This document contains **byte-for-byte exact** HTTP patterns extracted from the proven `nessusAPIWrapper/` code. These patterns have been validated to work with Nessus Essentials and bypass the `scan_api: false` restriction through Web UI simulation.

---

## Pattern 1: Authentication

**Source**: `nessusAPIWrapper/manage_scans.py:27-84`

### HTTP Request

```http
POST /session HTTP/1.1
Host: localhost:8834
Content-Type: application/json
X-API-Token: af824aba-e642-4e63-a49b-0810542ad8a5
```

### Request Headers (Full Set)

```python
headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Host': 'localhost:8834',
    'Origin': 'https://localhost:8834',
    'Referer': 'https://localhost:8834/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'X-API-Token': 'af824aba-e642-4e63-a49b-0810542ad8a5',  # Static token
    'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}
```

### Request Payload

```json
{
  "username": "nessus",
  "password": "nessus"
}
```

### Response (Success - 200 OK)

```json
{
  "token": "2a84cbd24f8d7f4c8e0a94c5e1f69b3a4d8c7e9f0b1a2c3d4e5f6a7b8c9d0e1f"
}
```

### Implementation Notes

1. **Static API Token**: Always use `af824aba-e642-4e63-a49b-0810542ad8a5`
2. **Session Token**: Extract `token` field from response, expires after inactivity
3. **SSL Verification**: Must be disabled (`verify=False`) for self-signed certs
4. **Retry on 401**: Re-authenticate if subsequent requests return 401

---

## Pattern 2: Create Scan (Untrusted)

**Source**: `nessusAPIWrapper/manage_scans.py:312-424`

### HTTP Request

```http
POST /scans HTTP/1.1
Host: localhost:8834
Content-Type: application/json
X-API-Token: af824aba-e642-4e63-a49b-0810542ad8a5
X-Cookie: token={session_token}
```

### Request Headers (Authenticated)

```python
headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Host': 'localhost:8834',
    'Origin': 'https://localhost:8834',
    'Referer': 'https://localhost:8834/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'X-API-Token': 'af824aba-e642-4e63-a49b-0810542ad8a5',
    'X-Cookie': f'token={session_token}',  # Dynamic session token
    'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}
```

### Request Payload (Untrusted Scan)

```json
{
  "uuid": "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66",
  "settings": {
    "name": "My Untrusted Scan",
    "text_targets": "172.32.0.215",
    "description": "Network-only vulnerability scan",
    "enabled": true,
    "folder_id": 3,
    "scanner_id": 1,
    "launch_now": false
  }
}
```

### Response (Success - 200 OK)

```json
{
  "scan": {
    "id": 30,
    "uuid": "template-uuid-here",
    "name": "My Untrusted Scan",
    "enabled": true,
    "owner": "nessus",
    "permissions": 128,
    "type": "remote",
    "read": true,
    "status": "empty",
    "shared": false,
    "user_permissions": 128,
    "creation_date": 1699564800,
    "last_modification_date": 1699564800,
    "folder_id": 3
  }
}
```

### Implementation Notes

1. **Template UUID**: Use Advanced Scan template `ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66`
2. **Folder ID**: `3` = "My Scans" folder
3. **Scanner ID**: `1` = Local scanner
4. **Launch Now**: Always `false` (explicit launch required)
5. **Extract Scan ID**: `response['scan']['id']` → integer

---

## Pattern 3: Launch Scan

**Source**: `nessusAPIWrapper/launch_scan.py:117-163`

### HTTP Request

```http
POST /scans/{scan_id}/launch HTTP/1.1
Host: localhost:8834
Content-Type: application/json
X-API-Token: af824aba-e642-4e63-a49b-0810542ad8a5
X-Cookie: token={session_token}
X-KL-kfa-Ajax-Request: Ajax_Request
```

### Request Headers (Critical: Web UI Marker)

```python
headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Host': 'localhost:8834',
    'Origin': 'https://localhost:8834',
    'Referer': f'https://localhost:8834/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'X-API-Token': 'af824aba-e642-4e63-a49b-0810542ad8a5',
    'X-Cookie': f'token={session_token}',
    'X-KL-kfa-Ajax-Request': 'Ajax_Request',  # CRITICAL: Web UI simulation marker
    'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}
```

### Request Payload

```json
{}
```

*Note: Empty payload, scan_id in URL path*

### Response (Success - 200 OK)

```json
{
  "scan_uuid": "template-uuid-here"
}
```

### Error Responses

| Status | Meaning | Action |
|--------|---------|--------|
| 403 Forbidden | API restriction (scan_api: false) | Use Web UI headers (X-KL-kfa-Ajax-Request) |
| 404 Not Found | Invalid scan_id | Verify scan exists |
| 409 Conflict | Scan already running | Stop first or wait for completion |

### Implementation Notes

1. **Web UI Marker**: `X-KL-kfa-Ajax-Request: Ajax_Request` is **CRITICAL** - without it, you get 403
2. **Scan UUID**: Extract from response for tracking
3. **Non-blocking**: Returns immediately, scan runs asynchronously

---

## Pattern 4: Get Scan Status

**Source**: `nessusAPIWrapper/list_scans.py:18-50` + inline GET /scans/{id}

### HTTP Request

```http
GET /scans/{scan_id} HTTP/1.1
Host: localhost:8834
X-API-Token: af824aba-e642-4e63-a49b-0810542ad8a5
X-Cookie: token={session_token}
```

### Request Headers

```python
headers = {
    'Accept': 'application/json',
    'X-API-Token': 'af824aba-e642-4e63-a49b-0810542ad8a5',
    'X-Cookie': f'token={session_token}'
}
```

### Response (Success - 200 OK)

```json
{
  "info": {
    "uuid": "scan-uuid",
    "status": "running",
    "name": "My Untrusted Scan",
    "enabled": true,
    "folder_id": 3,
    "scanner_name": "Local Scanner",
    "targets": "172.32.0.215",
    "timestamp": 1699564800,
    "object_id": 30,
    "progress": 45,
    "scan_start": 1699564900,
    "scan_end": null,
    "policy": "Advanced Scan"
  },
  "hosts": [
    {
      "host_id": 1,
      "hostname": "172.32.0.215",
      "progress": 45,
      "critical": 0,
      "high": 2,
      "medium": 5,
      "low": 10,
      "info": 50,
      "score": 350
    }
  ],
  "vulnerabilities": [
    {
      "plugin_id": 12345,
      "plugin_name": "Sample Vulnerability",
      "severity": 2,
      "count": 1
    }
  ]
}
```

### Status Values

| Nessus Status | MCP Status | Description |
|--------------|------------|-------------|
| `pending` | `queued` | Scan queued but not started |
| `running` | `running` | Scan actively running |
| `paused` | `running` | Scan paused (treat as still running) |
| `completed` | `completed` | Scan finished successfully |
| `canceled` | `failed` | User canceled scan |
| `stopped` | `failed` | Scan stopped due to error |
| `aborted` | `failed` | Scan aborted |
| `empty` | N/A | Scan never launched |

### Implementation Notes

1. **Progress Field**: `info.progress` → 0-100 integer
2. **Status Mapping**: Use table above to map Nessus → MCP states
3. **Polling Interval**: 30 seconds recommended
4. **Poll Endpoint**: Use GET `/scans/{id}` for live progress

---

## Pattern 5: Export Scan Results

**Source**: `nessusAPIWrapper/export_vulnerabilities.py:142-171`

### Step 5.1: Request Export

#### HTTP Request

```http
POST /scans/{scan_id}/export HTTP/1.1
Host: localhost:8834
Content-Type: application/json
X-API-Token: af824aba-e642-4e63-a49b-0810542ad8a5
X-Cookie: token={session_token}
```

#### Request Payload

```json
{
  "format": "nessus"
}
```

#### Response (Success - 200 OK)

```json
{
  "file": 12345,
  "temp_token": "optional-temp-token"
}
```

### Step 5.2: Poll Export Status

#### HTTP Request

```http
GET /scans/{scan_id}/export/{file_id}/status HTTP/1.1
Host: localhost:8834
X-API-Token: af824aba-e642-4e63-a49b-0810542ad8a5
X-Cookie: token={session_token}
```

#### Response (In Progress)

```json
{
  "status": "loading"
}
```

#### Response (Ready)

```json
{
  "status": "ready"
}
```

### Step 5.3: Download Export

#### HTTP Request

```http
GET /scans/{scan_id}/export/{file_id}/download HTTP/1.1
Host: localhost:8834
X-API-Token: af824aba-e642-4e63-a49b-0810542ad8a5
X-Cookie: token={session_token}
```

#### Response (Success - 200 OK)

```
Content-Type: application/xml
Content-Disposition: attachment; filename="scan_results.nessus"

<?xml version="1.0" ?>
<NessusClientData_v2>
  <Report name="My Untrusted Scan">
    <ReportHost name="172.32.0.215">
      <ReportItem pluginID="10267" pluginName="SSH Server Version" severity="0">
        <description>It is possible to obtain information about the remote SSH server.</description>
        <plugin_output>SSH version : SSH-2.0-OpenSSH_8.2p1</plugin_output>
        <solution>n/a</solution>
      </ReportItem>
      ...
    </ReportHost>
  </Report>
</NessusClientData_v2>
```

### Implementation Notes

1. **Format**: Always use `"nessus"` for raw XML export
2. **File ID**: Extract from step 5.1 response
3. **Polling**: Check status every 2 seconds
4. **Max Wait**: 5 minutes (150 iterations × 2 seconds)
5. **Content Type**: Expect `application/xml` in response
6. **Return**: Raw bytes (XML content)

---

## Pattern 6: Stop Scan

**Source**: `nessusAPIWrapper/launch_scan.py:166-213`

### HTTP Request

```http
POST /scans/{scan_id}/stop HTTP/1.1
Host: localhost:8834
Content-Type: application/json
X-API-Token: af824aba-e642-4e63-a49b-0810542ad8a5
X-Cookie: token={session_token}
X-KL-kfa-Ajax-Request: Ajax_Request
```

### Request Headers

Same as Launch Scan (includes Web UI marker)

### Request Payload

```json
{}
```

### Response (Success - 200 OK)

```json
{
  "scan_uuid": "template-uuid-here"
}
```

### Implementation Notes

1. **Web UI Marker**: Required (`X-KL-kfa-Ajax-Request: Ajax_Request`)
2. **Non-blocking**: Returns immediately
3. **Status Check**: Verify stopped with GET `/scans/{id}`

---

## Pattern 7: Delete Scan

**Source**: `nessusAPIWrapper/manage_scans.py:612-629`

### Two-Step Process

#### Step 7.1: Move to Trash

##### HTTP Request

```http
PUT /scans/{scan_id} HTTP/1.1
Host: localhost:8834
Content-Type: application/json
X-API-Token: af824aba-e642-4e63-a49b-0810542ad8a5
X-Cookie: token={session_token}
```

##### Request Payload

```json
{
  "folder_id": 2
}
```

*Note: folder_id=2 is the Trash folder*

#### Step 7.2: Delete from Trash

##### HTTP Request

```http
DELETE /scans/{scan_id} HTTP/1.1
Host: localhost:8834
X-API-Token: af824aba-e642-4e63-a49b-0810542ad8a5
X-Cookie: token={session_token}
```

##### Response (Success - 200 OK)

```json
{}
```

### Implementation Notes

1. **Two Steps**: Must move to trash first, then delete
2. **Folder IDs**: 2=Trash, 3=My Scans
3. **Alternative**: Single-step DELETE works in some Nessus versions

---

## Error Handling Patterns

### HTTP Status Codes

| Status | Error | Cause | Solution |
|--------|-------|-------|----------|
| 400 Bad Request | Invalid parameters | Malformed payload | Check JSON structure |
| 401 Unauthorized | Authentication failed | Session expired | Re-authenticate |
| 403 Forbidden | API restriction | `scan_api: false` | Use Web UI headers |
| 404 Not Found | Resource not found | Invalid scan_id | Verify scan exists |
| 409 Conflict | Resource conflict | Scan already running | Stop first or wait |
| 412 Precondition Failed | API unavailable | Nessus Essentials limitation | Cannot fix, use Web UI |
| 500 Internal Server Error | Nessus error | Backend issue | Retry with backoff |
| 503 Service Unavailable | Nessus busy | Too many requests | Wait and retry |

### Retry Strategy

```python
def with_retry(func, max_attempts=3):
    """Retry with exponential backoff."""
    for attempt in range(max_attempts):
        try:
            return func()
        except (ConnectionError, Timeout) as e:
            if attempt == max_attempts - 1:
                raise
            wait_time = 5 * (2 ** attempt)  # 5s, 10s, 20s
            time.sleep(wait_time)
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [401, 403]:
                # Re-authenticate and retry once
                if attempt == 0:
                    await scanner._authenticate()
                    return func()
            raise
```

---

## Template UUIDs

### Advanced Scan (Default)

```
ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66
```

**Use Case**: Comprehensive vulnerability scan with all plugins

### Other Templates

To discover available templates:

```http
GET /editor/scan/templates HTTP/1.1
X-API-Token: {api_token}
X-Cookie: token={session_token}
```

---

## Constants

### Static Values

```python
# Static API Token (never changes)
STATIC_API_TOKEN = "af824aba-e642-4e63-a49b-0810542ad8a5"

# Folder IDs
FOLDER_MY_SCANS = 3
FOLDER_TRASH = 2

# Scanner IDs
SCANNER_LOCAL = 1

# Template UUIDs
TEMPLATE_ADVANCED_SCAN = "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66"

# Polling Intervals
STATUS_POLL_INTERVAL = 30  # seconds
EXPORT_POLL_INTERVAL = 2   # seconds

# Timeouts
SCAN_TIMEOUT = 24 * 3600   # 24 hours
EXPORT_TIMEOUT = 300       # 5 minutes
```

---

## Minimal Working Headers

For async scanner implementation, these are the **minimum required headers**:

### Authentication

```python
{
    'Content-Type': 'application/json',
    'X-API-Token': STATIC_API_TOKEN
}
```

### Authenticated Requests (Create/Status/Export)

```python
{
    'Content-Type': 'application/json',
    'X-API-Token': STATIC_API_TOKEN,
    'X-Cookie': f'token={session_token}'
}
```

### Launch/Stop Scan (Web UI Simulation)

```python
{
    'Content-Type': 'application/json',
    'X-API-Token': STATIC_API_TOKEN,
    'X-Cookie': f'token={session_token}',
    'X-KL-kfa-Ajax-Request': 'Ajax_Request'  # CRITICAL!
}
```

---

## Async Implementation Notes

### Converting from `requests` to `httpx`

The wrapper uses `requests` (sync), scanner must use `httpx` (async):

```python
# Wrapper (sync)
response = requests.post(url, json=payload, headers=headers, verify=False)

# Scanner (async)
async with httpx.AsyncClient(verify=False) as client:
    response = await client.post(url, json=payload, headers=headers)
```

### Session Management

```python
class NessusScanner:
    def __init__(self, url, username, password):
        self._session: Optional[httpx.AsyncClient] = None
        self._session_token: Optional[str] = None
        self._static_token = STATIC_API_TOKEN

    async def _get_session(self) -> httpx.AsyncClient:
        if not self._session:
            self._session = httpx.AsyncClient(
                verify=False,
                timeout=30.0,
                follow_redirects=True
            )
        return self._session

    async def _authenticate(self) -> None:
        if self._session_token:
            return  # Already authenticated

        client = await self._get_session()
        response = await client.post(
            f"{self.url}/session",
            json={"username": self.username, "password": self.password},
            headers={'Content-Type': 'application/json', 'X-API-Token': self._static_token}
        )
        response.raise_for_status()
        self._session_token = response.json()["token"]

    async def close(self):
        if self._session:
            await self._session.aclose()
```

---

## Testing Checklist

When implementing the new scanner, verify these exact behaviors:

- [ ] Authentication returns session token matching wrapper
- [ ] Create scan payload structure byte-for-byte identical
- [ ] Launch scan includes `X-KL-kfa-Ajax-Request` header
- [ ] Status mapping matches wrapper (pending→queued, etc.)
- [ ] Export follows 3-step process (request→poll→download)
- [ ] Error handling matches wrapper (retry on 401, fail on 403, etc.)
- [ ] SSL verification disabled (`verify=False`)
- [ ] All headers match minimal working set

---

## Related Documents

- **MCP Workflow Guide**: `nessusAPIWrapper/MCP_WORKFLOW_GUIDE.md`
- **Phase 1A Plan**: `mcp-server/phases/PHASE_1A_SCANNER_REWRITE.md`
- **Wrapper Source**: `nessusAPIWrapper/manage_scans.py`, `launch_scan.py`

---

**Document Version**: 1.0
**Created**: 2025-01-07
**Extracted From**: nessusAPIWrapper/ (proven working code)
**Purpose**: Reference for Phase 1A scanner implementation
