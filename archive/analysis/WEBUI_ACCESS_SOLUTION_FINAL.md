# Nessus Scanner WebUI Access - Final Working Solution

**Date:** 2025-11-14
**Status:** ✅ WORKING - Tested and Verified
**Access Method:** Host LAN IP (not localhost)

---

## Quick Access Guide

### Working URLs

**Scanner 1 WebUI:**
```
https://172.32.0.209:8834
```

**Credentials:**
- Username: `nessus`
- Password: `nessus`

**Browser Warning:** You'll see a certificate warning (self-signed cert). Click "Advanced" → "Proceed" to continue.

---

## Why Localhost Doesn't Work

### The TLS Handshake Problem

Docker's NAT layer breaks TLS handshakes when traffic goes from host → container:

```
Host Machine → Docker NAT → Container
     ↓              ↓           ↓
  TLS Client   Packet Mod   TLS Server

TCP Connection:  ✅ Works
TLS Handshake:   ❌ Fails (timeout after 2+ min)
```

### Test Results

| Access Method | From | Result | Details |
|--------------|------|--------|---------|
| `localhost:8834` | Host OS | ❌ FAILS | TLS timeout |
| `172.30.0.3:8834` (internal IP) | Host OS | ❌ FAILS | TLS timeout |
| `172.32.0.209:8834` (host LAN IP) | Host OS | ✅ **WORKS** | Instant |
| `localhost:8834` | Inside VPN gateway | ✅ WORKS | No NAT |
| `172.30.0.3:8834` | Inside containers | ✅ WORKS | No NAT |

**Key Insight:** The issue is Docker's NAT layer, not the network configuration.

---

## Working Configuration

### Architecture: Shared Network Namespace

The scanner container shares the VPN gateway's network stack:

```
┌─────────────────────────────────────┐
│   VPN Gateway Container             │
│   IP: 172.30.0.2 (on vpn_net)      │
│   Port: 8834 exposed to host       │
│                                     │
│   ┌─────────────────────────────┐  │
│   │  Nessus Scanner Process     │  │
│   │  Listening on: 0.0.0.0:8834 │  │
│   └─────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
         ↓
    Host Port 8834
         ↓
    Accessible via Host LAN IP
    (172.32.0.209:8834)
```

### Docker Compose Configuration

**File:** `/home/nessus/docker/nessus-shared/docker-compose.yml`

```yaml
version: '3.8'

networks:
  vpn_net:
    driver: bridge
    enable_ipv6: false
    ipam:
      config:
        - subnet: 172.30.0.0/24
          gateway: 172.30.0.1

volumes:
  nessus_data_1:
    external: true
    name: nessus_data

services:
  # VPN Gateway - Handles routing and port exposure
  vpn-gateway:
    image: qmcgaw/gluetun:latest
    container_name: vpn-gateway-shared
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun:/dev/net/tun
    environment:
      - VPN_SERVICE_PROVIDER=custom
      - VPN_TYPE=wireguard
      - TZ=Europe/Amsterdam
      - FIREWALL_OUTBOUND_SUBNETS=172.30.0.0/24,172.32.0.0/24
      - FIREWALL=on
      - HTTPPROXY=on
      - HTTPPROXY_LOG=on
    volumes:
      - ./wg/wg0.conf:/gluetun/wireguard/wg0.conf:ro
    ports:
      - "8834:8834"  # Expose scanner port via VPN gateway
    networks:
      vpn_net:
        ipv4_address: 172.30.0.2
    sysctls:
      - net.ipv6.conf.all.disable_ipv6=1
      - net.ipv4.conf.all.src_valid_mark=1
      - net.ipv4.ip_forward=1
    labels:
      - autoheal=true
    restart: unless-stopped

  # Nessus Scanner - Shares VPN gateway's network
  nessus-pro-1:
    image: tenable/nessus:latest-ubuntu
    container_name: nessus-pro-1
    network_mode: "service:vpn-gateway"  # KEY: Share network with VPN gateway
    depends_on:
      vpn-gateway:
        condition: service_started
    volumes:
      - nessus_data_1:/opt/nessus
    environment:
      - ACTIVATION_CODE=8WVN-N99G-LHTF-TQ4D-LTAX
      - USERNAME=nessus
      - PASSWORD=nessus
    restart: unless-stopped

  # Additional services (nessus-pro-2, debug-scanner, autoheal)...
```

### Override File for Testing

**File:** `/home/nessus/docker/nessus-shared/docker-compose.old-working-test.yml`

```yaml
# Test: Exact replication of old WORKING configuration
version: '3.8'

services:
  vpn-gateway:
    # Add port forwarding to VPN gateway (like the old config)
    ports:
      - "8834:8834"

  nessus-pro-1:
    # Use shared network mode (like old config)
    network_mode: "service:vpn-gateway"
    # Remove separate network config
    networks: !reset {}
    # Remove individual port forwarding
    ports: !reset []
```

**Apply:**
```bash
cd /home/nessus/docker/nessus-shared
docker compose -f docker-compose.yml -f docker-compose.old-working-test.yml up -d --force-recreate nessus-pro-1 vpn-gateway
```

---

## Access Methods Comparison

### Method 1: Host LAN IP (WORKING - RECOMMENDED)

**URL:** `https://172.32.0.209:8834`

**Pros:**
- ✅ Works immediately
- ✅ No special configuration needed
- ✅ Same as original working setup
- ✅ Accessible from any device on LAN

**Cons:**
- ⚠️ Requires knowing/using host IP instead of localhost
- ⚠️ Only accessible on local network (but that's usually desired)

**When to use:** Daily WebUI access, the standard method

### Method 2: Internal Docker IPs (NOT WORKING from host)

**URL:** `https://172.30.0.3:8834` (Scanner 1), `https://172.30.0.4:8834` (Scanner 2)

**Status:** ❌ Fails from host OS with TLS timeout
**Status:** ✅ Works from inside containers

**Why it fails:** Docker bridge NAT breaks TLS handshakes from host

### Method 3: Localhost (NOT WORKING from host)

**URL:** `https://localhost:8834`

**Status:** ❌ Never worked, even in old configuration
**Why:** Docker NAT layer breaks TLS handshakes

**Old documentation warned:**
```
- **Host Access**: Use host IP `172.32.0.209:8834` (NOT `localhost:8834`)
- **Why**: Nessus uses VPN gateway network stack; localhost doesn't route correctly
```

### Method 4: Container-Based Browser (ALTERNATIVE)

Run Firefox inside a Docker container:

```bash
/home/nessus/projects/nessus-api/access-scanner-webui.sh
```

Then access: `https://172.30.0.3:8834`

**Pros:**
- ✅ Bypasses host NAT issues
- ✅ Can access internal IPs directly

**Cons:**
- ⚠️ Requires X11 forwarding (`ssh -X`)
- ⚠️ More complex than using host LAN IP

---

## Network Flow Diagrams

### Working: Host LAN IP Access

```
Browser on Host/LAN Device
    ↓
https://172.32.0.209:8834
    ↓
Host Network Interface (172.32.0.209)
    ↓
Docker Port Mapping (8834:8834 on vpn-gateway)
    ↓
VPN Gateway Container Network Stack
    ↓
Nessus Process (shares same network)
    ↓
✅ TLS Handshake Succeeds
```

### Broken: Localhost Access

```
Browser on Host
    ↓
https://localhost:8834
    ↓
Loopback Interface (127.0.0.1)
    ↓
Docker NAT/iptables Rules
    ↓
❌ TLS Handshake Fails (packet modification breaks TLS)
```

### Working: Container-to-Container

```
Container A (debug-scanner)
    ↓
https://172.30.0.3:8834
    ↓
Docker Bridge (172.30.0.0/24)
    ↓
Container B (nessus-pro-1)
    ↓
✅ TLS Handshake Succeeds (no NAT)
```

---

## Troubleshooting

### WebUI Not Accessible

**Problem:** Cannot access `https://172.32.0.209:8834`

**Diagnostic Steps:**

1. **Verify containers are running:**
```bash
docker ps --filter "name=vpn-gateway\|nessus-pro-1"
```

Expected output:
```
NAMES                STATUS                        PORTS
vpn-gateway-shared   Up X minutes (healthy)        0.0.0.0:8834->8834/tcp
nessus-pro-1         Up X minutes
```

2. **Check network mode:**
```bash
docker inspect nessus-pro-1 | grep NetworkMode
```

Expected: `"NetworkMode": "container:vpn-gateway-shared"`

3. **Verify port is listening inside VPN gateway:**
```bash
docker exec vpn-gateway-shared netstat -tlnp | grep 8834
```

Expected:
```
tcp        0      0 0.0.0.0:8834            0.0.0.0:*               LISTEN
```

4. **Test from inside VPN gateway (should work):**
```bash
docker exec vpn-gateway-shared sh -c "apk add --no-cache curl && curl -k -s https://localhost:8834/server/status"
```

Expected: JSON response with `"status": "ready"`

5. **Test from host via LAN IP (should work):**
```bash
curl -k -s https://172.32.0.209:8834/server/status
```

Expected: JSON response with `"status": "ready"`

6. **Verify host IP hasn't changed:**
```bash
ip addr show | grep "inet 172.32"
```

Expected: `172.32.0.209/24` (if different, use new IP in browser)

### Certificate Warning in Browser

**Problem:** Browser shows "Your connection is not private"

**Solution:** This is expected (self-signed certificate).
1. Click "Advanced"
2. Click "Proceed to 172.32.0.209" (or similar)
3. Accept the risk

### Slow Loading

**Problem:** WebUI takes a long time to load

**Causes:**
- Nessus still initializing (wait 30-60 seconds after container start)
- Plugin updates in progress (check `/server/status` endpoint)
- Database rebuilding

**Check status:**
```bash
curl -k -s https://172.32.0.209:8834/server/status | python3 -m json.tool
```

Look for:
- `"status": "ready"` - Fully operational
- `"status": "loading"` - Still initializing
- `"engine_status": {"status": "ready"}` - Scan engine ready

---

## MCP Server Access

The MCP server uses internal Docker IPs and works independently of WebUI access:

**Configuration:** `/home/nessus/projects/nessus-api/mcp-server/tools/mcp_server.py`

```python
SCANNERS = {
    'scanner1': {
        'url': 'https://172.30.0.3:8834',  # Internal IP
        'access_key': '...',
        'secret_key': '...'
    },
    'scanner2': {
        'url': 'https://172.30.0.4:8834',  # Internal IP
        'access_key': '...',
        'secret_key': '...'
    }
}
```

**Run MCP server:**
```bash
cd /home/nessus/projects/nessus-api
python mcp-server/tools/mcp_server.py
```

**Why MCP works:** The MCP server runs in a Python environment that uses internal Docker IPs and doesn't go through the host NAT layer.

---

## Configuration Files Reference

### Main Configuration
- **Base:** `/home/nessus/docker/nessus-shared/docker-compose.yml`
- **Current working override:** `/home/nessus/docker/nessus-shared/docker-compose.old-working-test.yml`
- **UPDATE mode override:** `/home/nessus/docker/nessus-shared/docker-compose.update-mode.yml`

### Documentation
- **This file:** `/home/nessus/projects/nessus-api/WEBUI_ACCESS_SOLUTION_FINAL.md`
- **Old working config backup:** `/home/nessus/docker/backups/20251111_135253/nessus-old/docker-compose.yml`
- **Old README:** `/home/nessus/docker/backups/20251111_135253/nessus-old/README.md`

### Helper Scripts
- **Container-based browser:** `/home/nessus/projects/nessus-api/access-scanner-webui.sh`
- **Browser test page:** `/home/nessus/projects/nessus-api/test-scanner-access.html`

---

## Summary

### What Works

✅ **WebUI Access via Host LAN IP:**
- URL: `https://172.32.0.209:8834`
- Works from host browser
- Works from any device on LAN (172.32.0.0/24)
- Same method as original working configuration

✅ **MCP API Access:**
- Uses internal IPs (172.30.0.3:8834, 172.30.0.4:8834)
- Works from Python/automation
- Independent of WebUI access method

### What Doesn't Work

❌ **Localhost Access from Host:**
- `https://localhost:8834` - TLS timeout
- Never worked, even in old configuration
- Docker NAT breaks TLS handshakes

❌ **Internal IP Access from Host:**
- `https://172.30.0.3:8834` - TLS timeout
- `https://172.30.0.4:8834` - TLS timeout
- Same Docker NAT issue

### Key Configuration

**Network mode:** `service:vpn-gateway` (shared network namespace)
**Port mapping:** `8834:8834` on vpn-gateway container
**Access URL:** `https://172.32.0.209:8834` (host LAN IP)

---

**Last Updated:** 2025-11-14
**Tested and Verified:** ✅ Working
**Status:** Production Ready

---

## See Also

**Quick Reference:**
- [WEBUI_ACCESS_QUICKREF.md](WEBUI_ACCESS_QUICKREF.md) - Quick reference card for daily use
- [docker-compose-webui-working.yml](docker-compose-webui-working.yml) - Working Docker configuration

**Advanced Analysis:**
- [MODE_COMPATIBILITY_ANALYSIS.md](MODE_COMPATIBILITY_ANALYSIS.md) - Why shared namespace and modes are incompatible
- [FINAL_MODE_RECOMMENDATION.md](FINAL_MODE_RECOMMENDATION.md) - Recommendation to keep shared namespace
- [PROXY_SOLUTION_ANALYSIS.md](PROXY_SOLUTION_ANALYSIS.md) - Alternative solution using reverse proxy

**Project Documentation:**
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Master index of all project documentation
