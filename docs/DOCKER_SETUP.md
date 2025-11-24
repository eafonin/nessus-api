# Nessus Docker Setup

**Version:** 4.0
**Status:** Production
**Last Updated:** 2025-11-24

---

## Overview

Dual-scanner Nessus deployment with unified VPN split routing and nginx reverse proxy. All scanners share a VPN gateway (Gluetun) with automatic split routing: LAN traffic direct, internet via VPN.

**Key Features:**
- ✅ Dual Nessus Pro scanners (independent routing)
- ✅ VPN split routing (automatic via Gluetun)
- ✅ Web UI access via nginx reverse proxy
- ✅ MCP server integration (container-to-container)
- ✅ Auto-healing unhealthy containers

---

## System Information

- **Host**: nessus@37.18.107.123 (Ubuntu 24.04 LTS)
- **Docker Location**: `/home/nessus/docker/nessus-shared/`
- **Deployment Mode**: Unified (single configuration, no mode switching)

---

## Quick Access URLs

⚠️ **IMPORTANT:** Use LAN IP (172.32.0.209), NOT localhost (Docker hairpin NAT issue)

- **Scanner 1 Web UI:** https://172.32.0.209:8443/
- **Scanner 2 Web UI:** https://172.32.0.209:8444/
- **Documentation Server:** http://172.32.0.209:8080/

**MCP Server Access (Internal):**
- Scanner 1 API: `https://172.30.0.3:8834` (container-to-container)
- Scanner 2 API: `https://172.30.0.4:8834` (container-to-container)

**Credentials:**
- Username: `nessus`
- Password: `nessus`

---

## Architecture

```
Browser (172.32.0.209:8443)
  ↓ HTTPS (TLS terminated by nginx)
Nginx Proxy (172.30.0.8:8443)
  ↓ Container-to-Container HTTPS (no Docker NAT)
Scanner 1 (172.30.0.3:8834)
  ↓ Scan traffic routing decision
VPN Gateway (172.30.0.2)
  ↓ Automatic split routing
  ├─→ LAN (172.30.0.x, 172.32.0.x): Direct
  └─→ Internet: Via VPN (62.84.100.88)
```

**Network:** Single Docker bridge `vpn_net (172.30.0.0/24)`

**Key Design Decisions:**
- **No direct port forwarding on scanners**: Avoids Docker NAT breaking TLS handshakes
- **Nginx reverse proxy**: Terminates TLS, proxies to scanners via container-to-container HTTPS
- **Separate network namespaces**: Each scanner has independent routing (essential for VPN split routing)
- **Static IP assignments**: Predictable addressing for proxy/MCP configuration

📖 **For complete technical architecture, see**: [/home/nessus/docker/nessus-shared/ARCHITECTURE.md](../../../docker/nessus-shared/ARCHITECTURE.md)

---

## Services

| Service | Container | IP | Purpose |
|---------|-----------|----| --------|
| VPN Gateway | vpn-gateway-shared | 172.30.0.2 | WireGuard VPN + split routing |
| Scanner 1 | nessus-pro-1 | 172.30.0.3 | Nessus Pro scanner |
| Scanner 2 | nessus-pro-2 | 172.30.0.4 | Nessus Pro scanner |
| Nginx Proxy | nessus-nginx-proxy | 172.30.0.8 | Reverse proxy for Web UIs |
| Debug/Docs | debug-scanner | 172.30.0.7 | Testing + documentation server |
| Autoheal | autoheal-shared | (none) | Auto-restart unhealthy containers |

---

## Docker Commands

### Start Services
```bash
cd /home/nessus/docker/nessus-shared
docker compose up -d
```

### Stop Services
```bash
docker compose down
```

### Check Status
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f nessus-pro-1
docker compose logs -f nginx-proxy
docker compose logs -f vpn-gateway
```

### Restart Services
```bash
# Restart single service
docker compose restart nessus-pro-1

# Restart all services
docker compose restart
```

### Update Scanner Images
```bash
docker compose pull nessus-pro-1 nessus-pro-2
docker compose up -d nessus-pro-1 nessus-pro-2
```

---

## Network Configuration

### Docker Bridge Network
- **Name**: `vpn_net`
- **Type**: Bridge
- **Subnet**: 172.30.0.0/24
- **Gateway**: 172.30.0.1

### VPN Split Routing
**Gluetun Configuration:**
```yaml
FIREWALL_OUTBOUND_SUBNETS=172.30.0.0/24,172.32.0.0/24
```

**Routing Behavior:**
- **172.30.0.0/24** (Docker bridge) → Direct (no VPN)
- **172.32.0.0/24** (Host LAN) → Direct (no VPN)
- **All other traffic** (Internet) → Via VPN tunnel

**Why this works:**
- Gluetun automatically routes specified subnets via bridge gateway (no VPN)
- Everything else goes through VPN interface (tun0)
- No manual iptables rules needed

### Port Mappings
Nginx exposes these ports to the host:
- **8443** → Scanner 1 Web UI
- **8444** → Scanner 2 Web UI
- **8080** → Documentation Server

Scanners have **NO** direct port forwarding (access via nginx only).

---

## Troubleshooting

### "Connection Timeout" in Browser
**Symptom:** Can't access https://172.32.0.209:8443/

**Solution:**
1. ✅ Use LAN IP `https://172.32.0.209:8443/` (NOT `https://localhost:8443/`)
2. Check nginx status: `docker compose ps nginx-proxy`
3. Check scanner status: `docker compose ps nessus-pro-1`
4. View nginx logs: `docker compose logs nginx-proxy`

### "Certificate Warning" in Browser
**Symptom:** Browser warns about untrusted certificate

**Solution:**
- This is expected (self-signed certificate)
- Click "Advanced" → "Accept Risk and Continue"

### Scanner Not Ready
**Symptom:** Scanner web UI shows "Scanner Not Ready"

**Solution:**
- Wait 30-60 seconds after startup for Nessus to initialize
- Check health: `docker compose ps`
- View logs: `docker compose logs nessus-pro-1`

### VPN Not Working
**Symptom:** Scanners can't reach internet

**Check VPN status:**
```bash
# Check VPN logs
docker compose logs vpn-gateway

# Verify public IP (should be 62.84.100.88)
docker exec debug-scanner curl -s https://api.ipify.org

# Verify LAN access (should work)
docker exec debug-scanner ping -c 2 172.32.0.1
```

### Container Health Check Failed
**Symptom:** `docker compose ps` shows "(unhealthy)"

**Solution:**
- Autoheal will automatically restart unhealthy containers
- Check autoheal logs: `docker logs autoheal-shared`
- Manually restart if needed: `docker compose restart <service>`

---

## Verification Commands

### Test Web UI Access
```bash
# Scanner 1
curl -k -s https://172.32.0.209:8443/server/status | jq

# Scanner 2
curl -k -s https://172.32.0.209:8444/server/status | jq
```

### Test VPN Routing
```bash
# Should show VPN IP: 62.84.100.88
docker exec debug-scanner curl -s https://api.ipify.org

# Should work (LAN access)
docker exec debug-scanner ping -c 2 172.32.0.1
```

### Test Container-to-Container Access
```bash
# Scanner 1 direct access (from host)
curl -k -s https://172.30.0.3:8834/server/status | jq

# Scanner 2 direct access (from host)
curl -k -s https://172.30.0.4:8834/server/status | jq
```

---

## Integration with nessus-api Project

The MCP server and Python scripts in `/home/nessus/projects/nessus-api/` connect to scanners via:

**Container-to-Container (Preferred for MCP):**
- Scanner 1: `https://172.30.0.3:8834`
- Scanner 2: `https://172.30.0.4:8834`
- No Docker NAT, no TLS issues
- Direct bridge routing

**Via Nginx Proxy (Alternative):**
- Scanner 1: `https://172.32.0.209:8443`
- Scanner 2: `https://172.32.0.209:8444`
- For external access or browser-based tools

**Authentication:**
- Username/Password: `nessus/nessus`
- API Keys: Generated via Nessus Web UI

---

## Security Considerations

1. **VPN Configuration**
   - WireGuard configs contain sensitive credentials
   - Stored with 600 permissions in `/home/nessus/docker/nessus-shared/wg/`
   - Not tracked in git

2. **Default Credentials**
   - Hardcoded username/password: `nessus/nessus`
   - Change for production use

3. **Self-Signed Certificates**
   - Nginx uses self-signed certificates
   - SSL verification disabled in MCP server
   - Acceptable for internal use

4. **Network Isolation**
   - Scanners isolated on dedicated bridge network
   - All scan traffic routed through VPN
   - Kill-switch enabled (if VPN drops, scanners lose internet)

5. **Container Security**
   - VPN gateway requires NET_ADMIN capability
   - All containers run as non-root (where possible)
   - Autoheal has Docker socket access (required for monitoring)

---

## Documentation

**Quick Start:**
- **[README.md](../../../docker/nessus-shared/README.md)** - Quick start guide, common operations

**Technical Deep-Dive:**
- **[ARCHITECTURE.md](../../../docker/nessus-shared/ARCHITECTURE.md)** - Complete architecture, network diagrams, traffic flows

**System Index:**
- **[DOCUMENTATION_INDEX.md](../../../DOCUMENTATION_INDEX.md)** - Complete system documentation index

---

**Docker Compose Location:** `/home/nessus/docker/nessus-shared/docker-compose.yml`
**Nginx Config:** `/home/nessus/docker/nessus-shared/nginx/nginx.conf`
**WireGuard Config:** `/home/nessus/docker/nessus-shared/wg/wg0.conf`
