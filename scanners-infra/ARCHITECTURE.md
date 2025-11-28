# Nessus Unified Mode Architecture

**Version:** 4.1
**Date:** 2025-11-28
**Status:** Production
**Purpose:** Technical deep-dive architecture reference for Claude agents managing Nessus scanner infrastructure

> **Related Documentation:**
> - [MCP Server Architecture](../mcp-server/docs/ARCHITECTURE_v2.2.md) - Application architecture (API, workers, Redis queue)
> - [MCP Development Compose](../dev1/docker-compose.yml) - MCP service definitions

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Network Architecture](#network-architecture)
3. [Component Details](#component-details) (7 components)
4. [Traffic Flow Diagrams](#traffic-flow-diagrams)
5. [Directory Structure](#directory-structure)
6. [Configuration Reference](#configuration-reference)
7. [Technical Decisions & Justifications](#technical-decisions--justifications)
8. [Access Summary](#access-summary)
9. [Critical Constraints](#critical-constraints)
10. [Maintenance Notes](#maintenance-notes)
11. [Troubleshooting Reference](#troubleshooting-reference)

---

## System Overview

### What This System Does

This infrastructure provides:
1. **Dual Nessus Pro Scanners** with independent network routing
2. **VPN Split Routing** (internet via WireGuard VPN, LAN direct)
3. **Web UI Access** via nginx reverse proxy (avoids Docker NAT TLS issues)
4. **MCP Server Integration** via direct container-to-container communication

### Key Design Principle

**Unified Mode:** Single configuration that handles all scenarios simultaneously. No mode switching required. VPN and LAN routing coexist automatically via split routing.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Physical Host (172.32.0.209)                    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │          Docker Bridge Network: vpn_net (172.30.0.0/24)        │   │
│  │                                                                  │   │
│  │   ┌──────────────────┐         ┌─────────────────────┐        │   │
│  │   │  VPN Gateway     │         │   Nginx Proxy       │        │   │
│  │   │  172.30.0.2      │◄────────┤   172.30.0.8        │        │   │
│  │   │  (Gluetun)       │         │   Ports: 8443/8444  │        │   │
│  │   │  WireGuard VPN   │         └─────────────────────┘        │   │
│  │   └──────────────────┘                    │                     │   │
│  │          │ │ │                             │                     │   │
│  │          │ │ └─────────┐                  │                     │   │
│  │          │ └────┐      │                  │                     │   │
│  │          ▼      ▼      ▼                  ▼                     │   │
│  │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │   │
│  │   │Scanner 1 │ │Scanner 2 │ │ Debug    │ │MCP Server│        │   │
│  │   │172.30.0.3│ │172.30.0.4│ │172.30.0.7│ │172.30.0.6│        │   │
│  │   │:8834     │ │:8834     │ │:8080     │ │:8000     │        │   │
│  │   └──────────┘ └──────────┘ └──────────┘ └──────────┘        │   │
│  │          │            │            │                            │   │
│  │          └────────────┴────────────┴──► Scan Targets           │   │
│  │                                          ┌──────────┐          │   │
│  │                                          │scan-target│          │   │
│  │           (LAN: direct, Internet: VPN)   │172.30.0.9│          │   │
│  │                                          │:22 (SSH) │          │   │
│  │                                          └──────────┘          │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌────────────────────────────────────────┐                            │
│  │  gluetun-host (host network mode)      │ ◄── Required for VPN      │
│  │  Ensures VPN gateway can reach WG server│                            │
│  └────────────────────────────────────────┘                            │
│                                                                          │
│  External Access:                                                       │
│    - Web Browser → https://172.32.0.209:8443 (Scanner 1)              │
│    - Web Browser → https://172.32.0.209:8444 (Scanner 2)              │
│    - MCP API → http://172.32.0.209:8836                                │
│    - Documentation → http://172.32.0.209:8080                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Network Architecture

### Network Topology

**Single Docker Bridge Network:** `vpn_net (172.30.0.0/24)`

All containers exist on the same bridge network but have **separate network namespaces**, allowing independent routing configuration per scanner.

### IP Address Assignments

**Full Network Allocation (172.30.0.0/24):**

| IP Address | Container | Compose File | Purpose |
|------------|-----------|--------------|---------|
| 172.30.0.1 | (gateway) | Docker | Bridge gateway |
| 172.30.0.2 | vpn-gateway-shared | scanners-infra | VPN gateway (Gluetun) |
| 172.30.0.3 | nessus-pro-1 | scanners-infra | Scanner 1 |
| 172.30.0.4 | nessus-pro-2 | scanners-infra | Scanner 2 |
| 172.30.0.5 | nessus-mcp-worker-dev | dev1 | MCP worker |
| 172.30.0.6 | nessus-mcp-api-dev | dev1 | MCP API server |
| 172.30.0.7 | debug-scanner | scanners-infra | Debug/testing + docs |
| 172.30.0.8 | nessus-nginx-proxy | scanners-infra | Reverse proxy |
| 172.30.0.9 | scan-target | scanners-infra | SSH test target for authenticated scans |
| 172.30.0.10+ | (available) | - | Future expansion |

**Port Mappings (Host → Container):**

| Host Port | Container | Service |
|-----------|-----------|---------|
| 8443 | nginx-proxy:8443 | Scanner 1 Web UI (HTTPS) |
| 8444 | nginx-proxy:8444 | Scanner 2 Web UI (HTTPS) |
| 8080 | nginx-proxy:8080 | Documentation Server (HTTP) |
| 8836 | mcp-api:8000 | MCP API (HTTP) |
| 6379 | redis:6379 | Redis (MCP internal) |

> **Important**: MCP services (worker, api, redis) are defined in `dev1/docker-compose.yml`, not this file. They connect to `nessus-shared_vpn_net` as an external network with static IPs to prevent conflicts.

### VPN Split Routing Configuration

**Gluetun Environment Variable:**
```yaml
FIREWALL_OUTBOUND_SUBNETS=172.30.0.0/24,172.32.0.0/24
```

**Routing Behavior:**
- **172.30.0.0/24** (Docker bridge) → Direct (no VPN)
- **172.32.0.0/24** (Host LAN) → Direct (no VPN)
- **All other traffic** (Internet) → Via VPN tunnel (tun0)

**Why This Works:**
- Each scanner has its own network namespace
- Scanner's default gateway is 172.30.0.1 (bridge gateway)
- DNS points to VPN gateway (172.30.0.2)
- Gluetun intercepts traffic and applies split routing rules
- LAN destinations bypass VPN, internet goes through tunnel

### DNS Configuration

All scanners use VPN gateway as DNS:
```yaml
dns:
  - 172.30.0.2  # Routes DNS through Gluetun
```

**Justification:** Ensures DNS queries go through VPN for privacy, while split routing still allows direct LAN access.

---

## Component Details

### 1. VPN Gateway (Gluetun)

**Container:** `vpn-gateway-shared`
**Image:** `qmcgaw/gluetun:latest`
**Network:** `vpn_net` (172.30.0.2)

**Purpose:**
- Provides WireGuard VPN tunnel for internet-bound traffic
- Implements split routing via iptables rules
- Acts as DNS server for all scanners

**Key Configuration:**
- `VPN_SERVICE_PROVIDER=custom` - Uses custom WireGuard config
- `VPN_TYPE=wireguard` - WireGuard protocol
- `FIREWALL_OUTBOUND_SUBNETS` - Split routing configuration
- WireGuard config mounted from `./wg/wg0.conf:/gluetun/wireguard/wg0.conf:ro`

> **Host-Specific Note:** A separate `gluetun-host` container runs on host network mode to ensure the VPN gateway can connect to the WireGuard server. This container is not part of the compose file but must remain running. Do not remove it.

**Network Interfaces:**
- `eth0` - Docker bridge (172.30.0.2)
- `tun0` - VPN tunnel interface

**Justification for Gluetun:**
- Battle-tested split routing implementation
- Automatic iptables firewall management
- Health monitoring and auto-reconnect
- No manual iptables rule management needed

### 2. Nessus Pro Scanners

**Containers:** `nessus-pro-1`, `nessus-pro-2`
**Image:** `tenable/nessus:latest-ubuntu`
**Network:** `vpn_net` (172.30.0.3, 172.30.0.4)

**Purpose:**
- Run vulnerability scans against targets
- Provide Web UI for scan management
- Expose API for MCP server integration

> **Image Limitations:** Nessus images are vendor-supplied by Tenable. They lack most standard binaries (no `curl`, `wget`, `bash` utilities) and additional packages cannot be installed. This is why health checks use Python urllib instead of curl. For debugging network issues, use the `debug-scanner` container which has full tooling.

**Key Configuration:**
- **Separate network namespaces** - Each scanner has independent routing
- **No port forwarding** - Prevents Docker NAT TLS issues
- **Static IPs** - Ensures predictable addressing for proxy/MCP
- **Persistent volumes** - Scanner data survives container restarts

**Network Access:**
- LAN targets: Direct access (no VPN)
- Internet targets: Via VPN (62.84.100.88)
- Web UI: Via nginx proxy (HTTPS)
- API: Via nginx proxy (Web UI) or direct (MCP server)

**Justification for Separate Namespaces:**
- Independent routing allows per-scanner configuration
- Can modify routes without affecting other containers
- Essential for VPN split routing to work correctly

### 3. Nginx Reverse Proxy

**Container:** `nessus-nginx-proxy`
**Image:** `nginx:alpine`
**Network:** `vpn_net` (172.30.0.8)

**Purpose:**
- Provide HTTPS Web UI access without Docker NAT TLS issues
- Terminate TLS connections from external browsers
- Proxy to backend scanners via container-to-container HTTPS

**Key Configuration:**
- **Direct proxying** (no path prefixes) - Avoids SPA routing issues
- **Separate ports per scanner** - 8443 (Scanner 1), 8444 (Scanner 2)
- **Self-signed certificates** - `/etc/nginx/certs/`
- **WebSocket support** - For real-time scan updates

**Traffic Flow:**
```
Browser (172.32.0.209:8443)
  → nginx TLS termination
  → proxy_pass https://172.30.0.3:8834
  → Scanner 1 (container-to-container HTTPS)
```

**Why This Architecture:**

1. **Docker NAT TLS Issue:**
   - Host → Docker NAT → Container breaks TLS handshakes
   - Solution: nginx terminates TLS, then container-to-container HTTPS

2. **Localhost Hairpin NAT Issue:**
   - localhost (127.0.0.1) connections hang (Docker limitation)
   - Solution: Use host LAN IP (172.32.0.209) instead

3. **Direct Proxy (No Path Prefix):**
   - Nessus SPA makes API calls to absolute paths (e.g., `/server/status`)
   - Path-based routing (`/scanner1/`) causes 404 errors
   - Solution: Separate ports with direct proxying

### 4. Debug Scanner

**Container:** `debug-scanner`
**Image:** `alpine:latest`
**Network:** `vpn_net` (172.30.0.7)

**Purpose:**
- Network troubleshooting and testing
- Documentation server (Python HTTP server on port 8080)
- Verify VPN split routing functionality
- **Test proxy for Nessus scanners** - behaves identically to Nessus on the network

**Services Running:**
- Python HTTP server serving `/docs` directory
- Debug tools: curl, wget, bind-tools, nmap, tcpdump, iproute2

> **Why This Container Exists:** Since Nessus images are vendor-supplied with no installable packages, this Alpine container provides full network tooling. It sits on the same network with the same routing rules as the Nessus scanners, making it ideal for testing connectivity, VPN routing, and debugging network issues before running actual scans.

**Justification:**
- Essential for debugging network issues (Nessus containers lack tools)
- Provides visibility into VPN routing behavior
- Dual-purpose: debugging + documentation hosting
- Same network behavior as scanners for accurate testing

### 5. MCP Server (Separate Compose)

**Compose File:** `dev1/docker-compose.yml`
**Containers:** `nessus-mcp-api-dev`, `nessus-mcp-worker-dev`, `nessus-mcp-redis-dev`
**Network:** Joins `vpn_net` via external network reference

**Purpose:**
- Model Context Protocol server for Claude integration
- Provides Nessus API access to Claude agents

**Scanner Access (using container names):**
- Primary: `https://nessus-pro-1:8834`, `https://nessus-pro-2:8834`
- Fallback: `https://172.30.0.3:8834`, `https://172.30.0.4:8834`

**Why Container Names:**
- DNS-based resolution is more resilient than hardcoded IPs
- Self-documenting (name indicates the service)
- Survives network reconfiguration

**Why Direct Access (no nginx):**
- Container-to-container = no Docker NAT = TLS works
- No need for nginx proxy layer
- Lower latency

### 6. Autoheal

**Container:** `autoheal-shared`
**Image:** `willfarrell/autoheal:latest`
**Network Mode:** `none`

**Purpose:**
- Automatically restart unhealthy containers
- Monitors containers with `autoheal` label

**Justification:**
- Ensures high availability
- Automatic recovery from transient failures
- No manual intervention needed

### 7. Scan Target (Test Container)

**Container:** `scan-target`
**Image:** `scan-target:test` (built from `mcp-server/docker/Dockerfile.scan-target`)
**Network:** `vpn_net` (172.30.0.9)

**Purpose:**
- Provides SSH test target for authenticated scan testing
- Used by MCP server integration tests (Phase 5)
- Contains test users with various privilege levels

**Test Users Available:**
| Username | Password | Sudo Access | Use Case |
|----------|----------|-------------|----------|
| `testauth_sudo_pass` | `TestPass123!` | Yes (with password) | Authenticated privileged scan |
| `testauth_sudo_nopass` | `TestPass123!` | Yes (NOPASSWD) | Authenticated privileged scan |
| `testauth_nosudo` | `TestPass123!` | No | Authenticated scan, insufficient privilege testing |

**Usage:**
```bash
# Start the scan target (if not running)
docker run -d --name scan-target \
  --network nessus-shared_vpn_net \
  --ip 172.30.0.9 \
  scan-target:test

# Or build and run from mcp-server/
docker build -t scan-target:test -f docker/Dockerfile.scan-target .
```

> **Note:** This container is started manually or via test scripts, not by docker-compose.yml. It provides a real SSH target within the scanner network for integration testing.

---

## Traffic Flow Diagrams

### 1. Web Browser → Scanner Web UI

```
┌─────────────┐
│   Browser   │
│  (External) │
└──────┬──────┘
       │ HTTPS (TLS 1.2/1.3)
       │ Host: 172.32.0.209:8443
       ▼
┌──────────────────┐
│  Host Firewall   │
│  Port Forward    │
└──────┬───────────┘
       │ Docker Port Mapping
       │ 8443 → nginx-proxy:8443
       ▼
┌──────────────────┐
│   Nginx Proxy    │
│   172.30.0.8     │
│  TLS Termination │
└──────┬───────────┘
       │ Container-to-Container HTTPS
       │ proxy_pass https://172.30.0.3:8834/
       ▼
┌──────────────────┐
│   Scanner 1      │
│   172.30.0.3     │
│   :8834          │
└──────────────────┘
```

**Why This Path:**
- TLS terminates at nginx (avoids Docker NAT TLS issue)
- Container-to-container = direct bridge routing (no NAT)
- Browser never touches Docker NAT directly

### 2. MCP Server → Scanner API

```
┌─────────────────┐
│   MCP Server    │
│   172.30.0.6    │
└──────┬──────────┘
       │ Container-to-Container HTTPS
       │ https://172.30.0.3:8834/
       │ (Direct bridge routing, no NAT)
       ▼
┌──────────────────┐
│   Scanner 1      │
│   172.30.0.3     │
│   :8834          │
└──────────────────┘
```

**Why This Path:**
- No nginx proxy needed (container-to-container HTTPS works)
- Lower latency (one less hop)
- No Docker NAT involved

### 3. Scanner → Scan Target (LAN)

```
┌──────────────────┐
│   Scanner 1      │
│   172.30.0.3     │
└──────┬───────────┘
       │ Scan traffic
       │ Destination: 172.32.0.x (LAN)
       ▼
┌──────────────────┐
│  VPN Gateway     │
│  172.30.0.2      │
│  (Gluetun)       │
└──────┬───────────┘
       │ Checks FIREWALL_OUTBOUND_SUBNETS
       │ Match: 172.32.0.0/24 → ACCEPT
       │ (Bypass VPN, route directly)
       ▼
┌──────────────────┐
│  Docker Bridge   │
│  172.30.0.1      │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Host Network    │
│  172.32.0.209    │
└──────┬───────────┘
       │ Direct routing
       ▼
┌──────────────────┐
│   LAN Target     │
│   172.32.0.x     │
└──────────────────┘
```

**Why Split Routing:**
- LAN scans don't need VPN (faster, lower latency)
- VPN bandwidth reserved for internet scans
- Gluetun iptables rules handle routing automatically

### 4. Scanner → Scan Target (Internet)

```
┌──────────────────┐
│   Scanner 1      │
│   172.30.0.3     │
└──────┬───────────┘
       │ Scan traffic
       │ Destination: 8.8.8.8 (Internet)
       ▼
┌──────────────────┐
│  VPN Gateway     │
│  172.30.0.2      │
│  (Gluetun)       │
└──────┬───────────┘
       │ Checks FIREWALL_OUTBOUND_SUBNETS
       │ No match → Route via VPN
       │ SNAT to VPN IP
       ▼
┌──────────────────┐
│  tun0 Interface  │
│  VPN Tunnel      │
└──────┬───────────┘
       │ WireGuard encrypted tunnel
       │ Source IP: 62.84.100.88 (VPN IP)
       ▼
┌──────────────────┐
│  VPN Provider    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Internet Target  │
│   8.8.8.8        │
└──────────────────┘
```

**Why VPN for Internet:**
- Anonymity for internet scans
- Avoid IP-based rate limiting/blocking
- Consistent source IP for all scans

---

## Directory Structure

### Scanner Infrastructure Directory
```
/home/nessus/projects/nessus-api/scanners-infra/
├── docker-compose.yml          # Main orchestration file
├── ARCHITECTURE.md             # This file (architecture reference)
├── README.md                   # Quick start guide and overview
├── nginx/
│   ├── README.MD               # Nginx configuration docs
│   ├── nginx.conf              # Nginx reverse proxy configuration
│   └── certs/
│       ├── nessus-proxy.crt    # Self-signed SSL certificate
│       └── nessus-proxy.key    # SSL private key
└── wg/
    ├── README.MD               # WireGuard configuration docs
    └── wg0.conf                # WireGuard VPN credentials
```

### Related Project Directories
```
/home/nessus/projects/nessus-api/
├── scanners-infra/              # This infrastructure (you are here)
├── dev1/                        # MCP development compose
│   └── docker-compose.yml       # MCP API, Worker, Redis
├── mcp-server/                  # MCP server code
│   ├── docs/
│   │   └── ARCHITECTURE_v2.2.md # Application architecture
│   └── docker/
│       └── Dockerfile.scan-target  # SSH test target
└── archive/                     # Historical documentation
```

### Container Filesystem Locations

**Scanner Data (Persistent Volumes):**
```
nessus-pro-1: /opt/nessus/ → nessus_data (Docker volume)
nessus-pro-2: /opt/nessus/ → nessus_data_2 (Docker volume)
```

**Nginx Configuration (Read-Only Mounts):**
```
nginx-proxy: /etc/nginx/nginx.conf → ./nginx/nginx.conf:ro
nginx-proxy: /etc/nginx/certs/ → ./nginx/certs/:ro
```

**Debug Scanner Documentation:**
```
debug-scanner: /docs/ → ./  (scanners-infra directory, read-only)
```

**WireGuard VPN Configuration:**
```
vpn-gateway: /gluetun/wireguard/wg0.conf → ./wg/wg0.conf:ro
```

---

## Configuration Reference

### Docker Compose Structure

**Networks:**
```yaml
networks:
  vpn_net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/24
          gateway: 172.30.0.1
```

**Volumes:**
```yaml
volumes:
  nessus_data:      # Scanner 1 persistent data
    external: true
  nessus_data_2:    # Scanner 2 persistent data
    external: true
```

**Service Dependencies:**
```
vpn-gateway (independent)
  └── nessus-pro-1 (depends on vpn-gateway)
  └── nessus-pro-2 (depends on vpn-gateway)
  └── debug-scanner (depends on vpn-gateway)
      └── nginx-proxy (depends on scanners)
```

### Nginx Proxy Configuration

**Server Blocks:**
- Port 8443: Scanner 1 (`proxy_pass https://172.30.0.3:8834/`)
- Port 8444: Scanner 2 (`proxy_pass https://172.30.0.4:8834/`)
- Port 8080: Documentation (`proxy_pass http://172.30.0.7:8080/`)

**Key Settings:**
```nginx
proxy_ssl_verify off;           # Scanner uses self-signed cert
proxy_buffering off;            # Required for SSE/streaming
proxy_read_timeout 300s;        # Long-running scan operations
proxy_http_version 1.1;         # WebSocket support
```

### Health Check Configuration

**Scanner Health Checks (using Python - curl not available):**
```yaml
healthcheck:
  test: ["CMD-SHELL", "python3 -c \"import urllib.request,ssl;c=ssl.create_default_context();c.check_hostname=False;c.verify_mode=ssl.CERT_NONE;exit(0 if urllib.request.urlopen('https://localhost:8834/server/status',timeout=5,context=c).status==200 else 1)\""]
  interval: 60s
  timeout: 15s
  retries: 5
  start_period: 180s
```

> **Why Python?** Nessus containers are vendor-supplied and lack curl/wget. Python is the only available tool for HTTP requests.

**Nginx Health Check:**
```yaml
healthcheck:
  test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8080/"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

## Technical Decisions & Justifications

### 1. Why Unified Mode (No Mode Switching)?

**Problem:**
- Previous setup required switching between NORMAL mode (routing via host) and UPDATE mode (VPN for everything)
- Mode switching = manual intervention, complexity, potential for errors

**Solution:**
- VPN split routing via Gluetun's `FIREWALL_OUTBOUND_SUBNETS`
- LAN and internet routing coexist automatically
- No manual route modifications needed

**Trade-offs:**
- ✅ Pros: Simple, automatic, always works
- ❌ Cons: Cannot disable VPN for internet scans (always on)

### 2. Why Separate Network Namespaces?

**Problem:**
- Shared namespace = one routing table for all containers
- Cannot have per-scanner custom routes

**Solution:**
- Each scanner has its own network namespace
- Independent routing tables
- Can modify routes without affecting others

**Trade-offs:**
- ✅ Pros: Flexibility, independence, essential for split routing
- ❌ Cons: Slightly more complex (but worth it)

### 3. Why Nginx Reverse Proxy (Not Direct Port Forwarding)?

**Problem:**
- Docker NAT breaks TLS handshakes for direct port forwarding
- Host → Docker NAT → Scanner HTTPS = TLS errors

**Solution:**
- Nginx terminates TLS from external browsers
- Then uses container-to-container HTTPS (no NAT)

**Evidence:**
- Container-to-container HTTPS: ✅ Works perfectly
- Host → Docker NAT → Scanner HTTPS: ❌ Fails

**Trade-offs:**
- ✅ Pros: Works reliably, proven solution
- ❌ Cons: Extra hop (negligible latency)

### 4. Why LAN IP (Not Localhost)?

**Problem:**
- `localhost` (127.0.0.1) connections hang due to Docker hairpin NAT issue
- Requests reach nginx, responses never return

**Solution:**
- Use host LAN IP (172.32.0.209) instead

**Evidence:**
```
localhost:8443 → Hangs (hairpin NAT issue)
172.32.0.209:8443 → Works perfectly
```

**Trade-offs:**
- ✅ Pros: Works reliably
- ❌ Cons: Must use LAN IP (not localhost)

### 5. Why Direct Proxy (Not Path-Based)?

**Problem:**
- Path-based routing (`/scanner1/`) breaks Nessus SPA
- JavaScript makes API calls to absolute paths (`/server/status`)
- Results in 404 errors

**Solution:**
- Direct proxying on separate ports
- No path prefixes

**Trade-offs:**
- ✅ Pros: Works with SPA routing, simple
- ❌ Cons: Requires separate ports per scanner

### 6. Why Gluetun (Not Custom VPN Setup)?

**Problem:**
- Manual iptables rules are complex and error-prone
- Need automatic failover and health monitoring

**Solution:**
- Gluetun provides battle-tested split routing
- Automatic iptables management
- Built-in health checks

**Trade-offs:**
- ✅ Pros: Reliable, maintained, feature-rich
- ❌ Cons: Extra dependency (but worth it)

### 7. Why Self-Signed Certificates?

**Problem:**
- Need TLS for nginx proxy
- CA-signed certs require domain name and renewal

**Solution:**
- Self-signed certificates (valid 1 year)

**Trade-offs:**
- ✅ Pros: Simple, no external dependencies
- ❌ Cons: Browser warnings (acceptable for internal use)

### 8. Why Static IP Assignments?

**Problem:**
- Dynamic IPs = unpredictable addressing
- Proxy/MCP configs would break on IP changes

**Solution:**
- Static IP assignment in docker-compose.yml

**Trade-offs:**
- ✅ Pros: Predictable, reliable
- ❌ Cons: Manual IP management (documented)

### 9. Why Container Names + Static IPs (Hybrid)?

**Problem:**
- Multiple compose files share one network (`nessus-shared_vpn_net`)
- Without static IPs, Docker assigns next available IP
- If infrastructure container (e.g., VPN) is down, other containers steal its IP
- Results in IP conflict when infrastructure restarts

**Example of Conflict:**
```
1. VPN gateway (172.30.0.2) stops
2. MCP API starts without static IP
3. Docker assigns 172.30.0.2 to MCP API (first available)
4. VPN gateway tries to start → IP conflict → fails
```

**Solution:**
- **Static IPs**: All containers on shared network MUST have static IPs
- **Container Names**: Use DNS names for service-to-service communication
- MCP services use `https://nessus-pro-1:8834` (name) instead of `https://172.30.0.3:8834` (IP)

**Trade-offs:**
- ✅ Pros: No IP conflicts, self-documenting, resilient
- ❌ Cons: Must coordinate IPs across compose files (documented in IP allocation table)

---

## Access Summary

### External Access (From Host or LAN)

| Service | URL | Authentication |
|---------|-----|----------------|
| Scanner 1 Web UI | `https://172.32.0.209:8443/` | Nessus login |
| Scanner 2 Web UI | `https://172.32.0.209:8444/` | Nessus login |
| Documentation | `http://172.32.0.209:8080/` | None |
| MCP API | `http://172.32.0.209:8836/` | API token |

### Internal Access (Container-to-Container)

| Service | URL | Purpose |
|---------|-----|---------|
| Scanner 1 API | `https://172.30.0.3:8834` or `https://nessus-pro-1:8834` | MCP server |
| Scanner 2 API | `https://172.30.0.4:8834` or `https://nessus-pro-2:8834` | MCP server |
| VPN Gateway | `172.30.0.2` | DNS, routing |
| Scan Target | `172.30.0.9:22` | SSH test target for authenticated scans |
| Debug Scanner | `172.30.0.7` | Network debugging (curl, nmap, etc.) |

---

## Critical Constraints

1. **Must use LAN IP (172.32.0.209)** - Localhost doesn't work (Docker hairpin NAT)
2. **Cannot use path-based routing** - Breaks Nessus SPA
3. **Scanners must have separate namespaces** - Required for split routing
4. **VPN split routing is automatic** - No manual route modifications
5. **Health checks required** - Autoheal depends on them
6. **Static IPs required** - Proxy and MCP configs depend on them
7. **gluetun-host container must run** - Required for VPN gateway connectivity (host-specific)
8. **Nessus containers lack tools** - Use debug-scanner for network debugging

---

## Maintenance Notes

### Updating Scanner Images

```bash
cd /home/nessus/projects/nessus-api/scanners-infra
docker compose pull nessus-pro-1 nessus-pro-2
docker compose up -d nessus-pro-1 nessus-pro-2
```

Data persists in volumes (no data loss).

### Regenerating SSL Certificates

```bash
cd /home/nessus/projects/nessus-api/scanners-infra/nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nessus-proxy.key \
  -out nessus-proxy.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:172.32.0.209"
docker compose restart nginx-proxy
```

### Adding New Scanner

1. Add service to docker-compose.yml
2. Assign static IP (172.30.0.x) - next available is 172.30.0.10
3. Add nginx server block (new port)
4. Restart stack

### VPN Configuration Changes

WireGuard config located at: `./wg/wg0.conf`

To update:
1. Edit `wg/wg0.conf` with new credentials
2. Restart vpn-gateway container: `docker compose restart vpn-gateway`

> **Warning:** The `gluetun-host` container on host network must remain running for VPN connectivity. Do not remove it.

---

## Troubleshooting Reference

### Scanner Not Accessible

**Check nginx logs:**
```bash
docker logs nessus-nginx-proxy --tail 50
```

**Check scanner health (use debug-scanner, not Nessus container):**
```bash
# From debug-scanner (has curl)
docker exec debug-scanner curl -k https://172.30.0.3:8834/server/status

# Or check container health status
docker inspect nessus-pro-1 --format '{{.State.Health.Status}}'
```

### VPN Not Working

**Check public IP:**
```bash
docker exec debug-scanner curl -s https://api.ipify.org
# Expected: 62.84.100.88 (VPN IP)
```

**Check Gluetun status:**
```bash
docker logs vpn-gateway-shared --tail 100
```

### Container-to-Container Issues

**Test from debug-scanner:**
```bash
docker exec debug-scanner curl -k https://172.30.0.3:8834/server/status
```

**Check network connectivity:**
```bash
docker exec debug-scanner ping 172.30.0.3
```

---

**End of Architecture Documentation**
