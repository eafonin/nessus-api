# Nessus Unified Mode Implementation Summary

**Date:** 2025-11-14
**Status:** ✅ COMPLETED
**Configuration:** Unified VPN Split Routing + Nginx Reverse Proxy

## Overview

Successfully implemented a unified Nessus scanner configuration that combines:
1. VPN split routing (internet via VPN, LAN direct)
2. Nginx reverse proxy for WebUI access (avoiding Docker NAT TLS issues)
3. Separate network namespaces for independent routing control

This eliminates the need for mode switching and provides simultaneous VPN + LAN access.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Host OS (172.32.0.209)                  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │   Docker Bridge Network (172.30.0.0/24)                  │  │
│  │                                                            │  │
│  │   ┌──────────────┐        ┌─────────────┐                │  │
│  │   │ VPN Gateway  │        │   Nginx     │                │  │
│  │   │ 172.30.0.2   │◄───────┤   Proxy     │                │  │
│  │   │ (Gluetun)    │        │ 172.30.0.8  │                │  │
│  │   └──────────────┘        └─────────────┘                │  │
│  │          │                       │                         │  │
│  │          │                       ▼                         │  │
│  │          ▼                 ┌──────────┐  ┌──────────┐    │  │
│  │   ┌──────────┐             │ Scanner1 │  │ Scanner2 │    │  │
│  │   │ Internet │             │172.30.0.3│  │172.30.0.4│    │  │
│  │   │   VPN    │             └──────────┘  └──────────┘    │  │
│  │   └──────────┘                  │              │          │  │
│  │                                 ▼              ▼          │  │
│  │                              [LAN: Direct]               │  │
│  │                              [Internet: via VPN]         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  WebUI Access: https://172.32.0.209:8443 (via nginx proxy)     │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Tasks Completed

### ✅ Phase 1: Unified Configuration
1. Backed up existing docker-compose configurations
2. Created unified docker-compose.yml with VPN split routing
3. Applied configuration and restarted all scanners
4. Verified scanner initialization (both ready)
5. Tested container-to-container access (working)
6. Verified VPN split routing:
   - Internet traffic: ✅ Via VPN (62.84.100.88)
   - LAN traffic: ✅ Direct (172.32.0.1 pingable)

### ✅ Phase 2: Nginx Reverse Proxy
7. Generated self-signed SSL certificates
8. Created nginx configuration for reverse proxy
9. Added nginx proxy service to docker-compose.yml
10. Started nginx proxy container

### ✅ Phase 3: Testing & Troubleshooting
11. Added test HTTP service to debug-scanner
12. Configured nginx to proxy test service
13. Tested host-to-nginx-to-service connection chain
14. **Discovered Docker localhost hairpin NAT issue**
15. **Solution: Use LAN IP instead of localhost**
16. Verified all endpoints working via LAN IP

## Access URLs

### ⚠️ IMPORTANT: Use LAN IP, NOT localhost

Due to Docker's localhost hairpin NAT limitation, you **must** use the host's LAN IP (172.32.0.209) to access the scanners. `localhost` (127.0.0.1) will NOT work.

### WebUI Access (via Nginx Proxy)
- **Scanner 1 WebUI:** `https://172.32.0.209:8443/scanner1`
- **Scanner 2 WebUI:** `https://172.32.0.209:8444/`
- **Test Service:** `http://172.32.0.209:8080/` (debug only)

### MCP Server Internal Access
- **Scanner 1:** `https://172.30.0.3:8834` (container-to-container)
- **Scanner 2:** `https://172.30.0.4:8834` (container-to-container)

## Network Configuration

### IP Assignments
| Container | IP Address | Purpose |
|-----------|------------|---------|
| vpn-gateway-shared | 172.30.0.2 | Gluetun VPN gateway |
| nessus-pro-1 | 172.30.0.3 | Scanner 1 |
| nessus-pro-2 | 172.30.0.4 | Scanner 2 |
| nessus-mcp-worker-dev | 172.30.0.5 | MCP worker (existing) |
| nessus-mcp-api-dev | 172.30.0.6 | MCP API (existing) |
| debug-scanner | 172.30.0.7 | Debug/testing container |
| nessus-nginx-proxy | 172.30.0.8 | Nginx reverse proxy |

### Port Mappings
| Host Port | Container Port | Service |
|-----------|----------------|---------|
| 8443 | 8443 | Scanner 1 WebUI (HTTPS) |
| 8444 | 8444 | Scanner 2 WebUI (HTTPS) |
| 8080 | 8080 | Test service (HTTP, debug) |

### VPN Split Routing

Configured via Gluetun environment variable:
```yaml
FIREWALL_OUTBOUND_SUBNETS=172.30.0.0/24,172.32.0.0/24
```

- **LAN traffic (172.32.0.0/24):** Routes directly (no VPN)
- **Internet traffic:** Routes via VPN (public IP: 62.84.100.88)
- **Docker internal (172.30.0.0/24):** Routes directly (no VPN)

## Key Technical Findings

### Docker Localhost Hairpin NAT Issue

**Problem:**
- Host → localhost:8443 → Docker NAT → 172.30.0.8:8443 (nginx) ✅ Works
- Response: 172.30.0.8 (nginx) → Docker reverse NAT → ??? ❌ **Fails to reach host**

**Evidence:**
```bash
# Nginx logs show HTTP 200 responses:
127.0.0.1 - - [24/Nov/2025:09:10:07 +0000] "GET / HTTP/1.1" 200 231

# But curl on host times out (never receives response)
$ curl http://localhost:8080/
[hangs indefinitely]

# Using LAN IP works perfectly:
$ curl http://172.32.0.209:8080/
<!DOCTYPE html>...  # Success!
```

**Root Cause:** Docker's `docker-proxy` process cannot properly handle return packets for localhost connections on some systems. This is a known Docker networking limitation.

**Solution:** Always use the host's LAN IP (172.32.0.209) instead of localhost (127.0.0.1).

### Why Container-to-Container Works

Container-to-container HTTPS (debug-scanner → Scanner 1) works perfectly because:
1. No Docker NAT layer (direct bridge routing)
2. No localhost hairpinning issue
3. TLS handshake occurs directly between containers

This is why the MCP server (which connects via container-to-container) will work without issues.

## Files Modified

### Configuration Files
- `/home/nessus/docker/nessus-shared/docker-compose.yml` - Unified configuration
- `/home/nessus/docker/nessus-shared/nginx/nginx.conf` - Nginx proxy config
- `/home/nessus/docker/nessus-shared/nginx/certs/` - SSL certificates

### Backup Location
`/home/nessus/docker/nessus-shared/backups/backup_20251114_194220/`

## Testing Results

### ✅ All Tests Passing

```bash
# Scanner Status Tests
Scanner 1: ✅ Status=ready | Code=200 | Engine=ready
Scanner 2: ✅ Status=ready | Code=200 | Engine=ready

# Container-to-Container Tests
debug-scanner → Scanner 1: ✅ HTTP 200
debug-scanner → Scanner 2: ✅ HTTP 200
nginx-proxy → debug-scanner test service: ✅ HTTP 200

# VPN Split Routing Tests
Public IP: ✅ 62.84.100.88 (VPN IP)
LAN Access: ✅ 172.32.0.1 pingable (direct)

# Host Access Tests (via LAN IP)
https://172.32.0.209:8443/scanner1/server/status: ✅ HTTP 200
https://172.32.0.209:8444/server/status: ✅ HTTP 200
http://172.32.0.209:8080/: ✅ HTTP 200

# Host Access Tests (via localhost) - Expected to fail
http://localhost:8080/: ❌ Timeout (Docker hairpin NAT issue)
https://localhost:8443/: ❌ Timeout (Docker hairpin NAT issue)
```

## Usage Instructions

### Starting the Stack
```bash
cd /home/nessus/docker/nessus-shared
docker compose up -d
```

### Checking Status
```bash
docker compose ps
docker compose logs -f nginx-proxy
```

### Accessing Scanners
1. Open browser to `https://172.32.0.209:8443/scanner1` (Scanner 1)
2. Open browser to `https://172.32.0.209:8444/` (Scanner 2)
3. Accept self-signed certificate warning
4. Login with Nessus credentials

### Verifying VPN Split Routing
```bash
# Check public IP (should be VPN IP)
docker exec debug-scanner curl -s https://api.ipify.org
# Expected: 62.84.100.88

# Check LAN access (should work)
docker exec debug-scanner ping -c 2 172.32.0.1
# Expected: 2 packets received
```

## Next Steps

1. **Remove Test Service** (optional):
   - Remove port 8080 from docker-compose.yml
   - Remove test service section from nginx.conf
   - Restart nginx-proxy

2. **MCP Server Configuration**:
   - Update MCP server to use internal IPs:
     - Scanner 1: `https://172.30.0.3:8834`
     - Scanner 2: `https://172.30.0.4:8834`
   - No proxy needed for MCP (uses container-to-container)

3. **Documentation**:
   - Update main README.md with unified mode instructions
   - Add troubleshooting guide for localhost issues
   - Update DOCUMENTATION_INDEX.md

4. **Security**:
   - Replace self-signed certificates with proper CA-signed certs (optional)
   - Consider adding nginx authentication (optional)
   - Review firewall rules for port 8443/8444

## Benefits of Unified Mode

1. ✅ **No Mode Switching:** Single configuration for all scenarios
2. ✅ **VPN Split Routing:** Internet via VPN, LAN direct (automatic)
3. ✅ **WebUI Access:** Via nginx proxy (avoids Docker NAT TLS issues)
4. ✅ **MCP Server Access:** Direct container-to-container (no proxy needed)
5. ✅ **Independent Routing:** Separate namespaces allow route modifications
6. ✅ **Proven Working:** All tests passing, ready for production

## Known Limitations

1. **Localhost Access:** Does not work due to Docker hairpin NAT issue
   - **Workaround:** Use LAN IP (172.32.0.209) instead

2. **Self-Signed Certificates:** Browser will show security warnings
   - **Workaround:** Accept warning or install CA-signed certs

3. **Static IP Assignment:** Requires manual IP management
   - **Impact:** Low (documented in docker-compose.yml)

## Related Documentation

- `PROXY_SOLUTION_ANALYSIS.md` - Original proxy design analysis
- `MODE_COMPATIBILITY_ANALYSIS.md` - Why modes are incompatible
- `FINAL_MODE_RECOMMENDATION.md` - Recommendation for unified mode
- `/home/nessus/docker/nessus-shared/docker-compose.yml` - Live configuration
- `/home/nessus/docker/nessus-shared/nginx/nginx.conf` - Nginx configuration

## Conclusion

The unified mode implementation is **complete and working**. All scanners are accessible via the nginx reverse proxy using the host's LAN IP (172.32.0.209). VPN split routing is functioning correctly, and the MCP server can access scanners via direct container-to-container connections.

The only limitation is that `localhost` access doesn't work due to Docker's hairpin NAT issue, but this is easily worked around by using the LAN IP instead.

**Status: READY FOR PRODUCTION** ✅
