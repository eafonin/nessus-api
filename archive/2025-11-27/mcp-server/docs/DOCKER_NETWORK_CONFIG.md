# Docker Network Configuration for Phase 1A

> **Critical**: MCP containers must use different URLs than host to reach Nessus
> **Status**: Validated and Working
> **Date**: 2025-01-07

---

## Network Architecture

### Container Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Host (Ubuntu)                      │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           nessus_nessus_net (172.18.0.0/16)           │  │
│  │                                                         │  │
│  │  ┌──────────────────┐  ┌──────────────────┐          │  │
│  │  │  vpn-gateway     │  │  nessus-pro      │          │  │
│  │  │  172.18.0.2      │──│  (via VPN)       │          │  │
│  │  │  Port: 8834      │  │                  │          │  │
│  │  └──────────────────┘  └──────────────────┘          │  │
│  │          │                                             │  │
│  │          │                                             │  │
│  │  ┌───────┴────────────────────────────────────────┐  │  │
│  │  │  nessus-mcp-api-dev    172.18.0.4             │  │  │
│  │  │  nessus-mcp-worker-dev 172.18.0.3             │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           dev1_default (172.19.0.0/16)                │  │
│  │                                                         │  │
│  │  ┌──────────────────┐  ┌──────────────────┐          │  │
│  │  │  redis           │  │  mcp-api         │          │  │
│  │  │  172.19.0.2      │  │  172.19.0.3      │          │  │
│  │  └──────────────────┘  └──────────────────┘          │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  Host Loopback: localhost (127.0.0.1)                      │
│  Port 8834: Forwarded from vpn-gateway                     │
└─────────────────────────────────────────────────────────────┘
```

---

## URL Configuration

### From Different Contexts

| Context | Nessus URL | Status | Notes |
|---------|-----------|--------|-------|
| **Host machine** | `https://localhost:8834` | ✅ Working | Port forwarded from vpn-gateway |
| **MCP API container** | `https://172.18.0.2:8834` | ✅ Working | Direct to vpn-gateway |
| **MCP Worker container** | `https://172.18.0.2:8834` | ✅ Working | Direct to vpn-gateway |
| **Host using container IP** | `https://172.18.0.2:8834` | ❌ Not routable | 172.18.x.x not accessible from host |

---

## Container Network Details

### MCP API Container

```bash
docker inspect nessus-mcp-api-dev | grep -A 10 "Gateway"
```

**Networks**:
- `dev1_default`: 172.19.0.3/16 (Gateway: 172.19.0.1)
- `nessus_nessus_net`: 172.18.0.4/16 (Gateway: 172.18.0.1)

**DNS Names**:
- `nessus-mcp-api-dev`
- `mcp-api`

### MCP Worker Container

**Networks**:
- `dev1_default`: 172.19.0.4/16
- `nessus_nessus_net`: 172.18.0.3/16

**DNS Names**:
- `nessus-mcp-worker-dev`
- `scanner-worker`

### VPN Gateway Container

**Networks**:
- `nessus_nessus_net`: 172.18.0.2/16

**Exposed Ports**:
- `8834/tcp` → Host `0.0.0.0:8834`

**Purpose**: Provides VPN tunnel to Nessus Pro scanner, forwards Nessus API on port 8834

---

## Configuration in Code

### Environment Variables

**For Host Testing** (nessusAPIWrapper/):
```bash
NESSUS_URL=https://localhost:8834
```

**For MCP Containers** (mcp-server/):
```bash
NESSUS_URL=https://172.18.0.2:8834
```

### Docker Compose Configuration

**File**: `dev1/docker-compose.yml`

```yaml
services:
  mcp-api:
    networks:
      - default
      - nessus_nessus_net
    environment:
      - NESSUS_URL=https://172.18.0.2:8834

  scanner-worker:
    networks:
      - default
      - nessus_nessus_net
    environment:
      - NESSUS_URL=https://172.18.0.2:8834

networks:
  default:
    name: dev1_default
  nessus_nessus_net:
    external: true
    name: nessus_nessus_net
```

---

## Verification Commands

### From Host

```bash
# Test connectivity from host
curl -k https://localhost:8834/server/status

# Expected output:
# {"status": "ready", ...}
```

### From MCP API Container

```bash
# Test connectivity from container
docker exec nessus-mcp-api-dev python -c "
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        response = await client.get('https://172.18.0.2:8834/server/status')
        print(f'Status: {response.status_code}')
        print(response.json())

asyncio.run(test())
"

# Expected output:
# Status: 200
# {'status': 'ready', 'pluginSet': True, ...}
```

### From MCP Worker Container

```bash
# Same test from worker
docker exec nessus-mcp-worker-dev python -c "
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        response = await client.get('https://172.18.0.2:8834/server/status')
        print(f'Status: {response.status_code}')

asyncio.run(test())
"
```

---

## Troubleshooting

### Issue: "Connection refused" from container

**Symptom**: `httpx.ConnectError: All connection attempts failed`

**Cause**: Using `localhost` or `127.0.0.1` from inside container

**Solution**: Use `172.18.0.2` (VPN gateway IP) instead

**Verification**:
```bash
docker exec nessus-mcp-api-dev python -c "
import socket
print('Trying localhost:', socket.gethostbyname('localhost'))
print('Trying vpn-gateway:', socket.gethostbyname('vpn-gateway'))
"
```

### Issue: "Name or service not known"

**Symptom**: DNS resolution fails for hostname

**Cause**: Container not on correct network

**Solution**: Add container to `nessus_nessus_net` network:

```bash
docker network connect nessus_nessus_net <container_name>
```

### Issue: "SSL: CERTIFICATE_VERIFY_FAILED"

**Symptom**: TLS handshake fails

**Cause**: Self-signed certificate on Nessus

**Solution**: Disable SSL verification in httpx:
```python
httpx.AsyncClient(verify=False)
```

---

## Why This Architecture?

### VPN Gateway Pattern

Nessus Pro scanner is accessed through a VPN tunnel managed by the `vpn-gateway` container:

1. **nessus-pro** container runs Nessus scanner
2. **vpn-gateway** container establishes VPN connection
3. Nessus API is exposed on vpn-gateway port 8834
4. Host can access via `localhost:8834` (port forwarding)
5. Other containers access via `172.18.0.2:8834` (direct)

### Multi-Network Topology

MCP containers are on **two networks**:

1. **dev1_default**: For inter-MCP communication (API ↔ Worker ↔ Redis)
2. **nessus_nessus_net**: For accessing Nessus via VPN gateway

This isolation provides:
- ✅ Security: MCP services isolated from Nessus network
- ✅ Flexibility: Can scale MCP independently
- ✅ Simplicity: Clean separation of concerns

---

## Testing Matrix

### Connectivity Test Results

| Source | Destination | Protocol | Result | Notes |
|--------|------------|----------|--------|-------|
| Host | localhost:8834 | HTTPS | ✅ Pass | Via port forwarding |
| Host | 172.18.0.2:8834 | HTTPS | ❌ Fail | Container IP not routable |
| mcp-api | localhost:8834 | HTTPS | ❌ Fail | localhost = container itself |
| mcp-api | 172.18.0.2:8834 | HTTPS | ✅ Pass | Direct to VPN gateway |
| mcp-api | vpn-gateway:8834 | HTTPS | ✅ Pass | DNS name (alternative) |
| mcp-worker | 172.18.0.2:8834 | HTTPS | ✅ Pass | Direct to VPN gateway |

---

## Production Considerations

### URL Configuration Strategy

**Option 1: Environment Variable** (Recommended)
```yaml
environment:
  - NESSUS_URL=${NESSUS_URL:-https://172.18.0.2:8834}
```

**Option 2: Auto-Detection**
```python
import socket
import os

def get_nessus_url():
    # Try to detect if we're in container
    if os.path.exists('/.dockerenv'):
        return "https://172.18.0.2:8834"
    else:
        return "https://localhost:8834"
```

**Option 3: DNS Name**
```python
# Use DNS name instead of IP (more resilient)
NESSUS_URL = "https://vpn-gateway:8834"
```

### Network Security

**Current**: No network isolation, all containers can access Nessus

**Future Enhancements**:
- Firewall rules limiting access to MCP containers only
- mTLS between MCP and Nessus
- Secrets management for Nessus credentials

---

## Related Documentation

- **Phase 1A Plan**: `mcp-server/phases/PHASE_1A_SCANNER_REWRITE.md`
- **HTTP Patterns**: `mcp-server/scanners/NESSUS_HTTP_PATTERNS.md`
- **Connectivity Test**: `mcp-server/tests/integration/test_connectivity.py`
- **Docker Compose**: `dev1/docker-compose.yml`

---

**Document Version**: 1.0
**Created**: 2025-01-07
**Validated**: Nessus ready, all connectivity tests passing
**Status**: Production-Ready Configuration
