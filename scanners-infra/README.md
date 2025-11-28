# Nessus Scanner Infrastructure

> Docker deployment for Nessus Pro scanners with VPN split-routing and reverse proxy

**Version:** 4.0 | **Status:** Production

## Overview

Self-contained infrastructure for running multiple Nessus Professional scanners with:

- **VPN Split Routing** - Internet traffic via VPN, LAN scans direct
- **Reverse Proxy** - TLS termination for WebUI access (solves Docker NAT issues)
- **Auto-healing** - Automatic restart of unhealthy containers
- **MCP Integration** - Direct container-to-container API access

## Quick Start

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## Access URLs

| Service | URL | Notes |
|---------|-----|-------|
| Scanner 1 WebUI | `https://172.32.0.209:8443/` | Via nginx proxy |
| Scanner 2 WebUI | `https://172.32.0.209:8444/` | Via nginx proxy |
| Documentation | `http://172.32.0.209:8080/` | Architecture docs |

**Critical**: Use LAN IP (`172.32.0.209`), NOT `localhost` - Docker hairpin NAT prevents localhost access.

### MCP Server Access

| Scanner | Container Name | Static IP | Port |
|---------|---------------|-----------|------|
| Scanner 1 | `nessus-pro-1` | `172.30.0.3` | 8834 |
| Scanner 2 | `nessus-pro-2` | `172.30.0.4` | 8834 |

**Preferred**: Use container names (`https://nessus-pro-1:8834`) for resilience.

## Network Topology

```
vpn_net (172.30.0.0/24)
├── 172.30.0.1  Docker bridge gateway
├── 172.30.0.2  VPN Gateway (Gluetun)
├── 172.30.0.3  Scanner 1 (Nessus Pro)
├── 172.30.0.4  Scanner 2 (Nessus Pro)
├── 172.30.0.5  MCP Worker (dev1/)
├── 172.30.0.6  MCP API (dev1/)
├── 172.30.0.7  Debug Scanner + Docs
└── 172.30.0.8  Nginx Proxy
```

> **Note**: MCP services (172.30.0.5-6) are defined in `dev1/docker-compose.yml`, not this file.

## Directory Structure

```
scanners-infra/
├── docker-compose.yml      # Service definitions
├── ARCHITECTURE.md         # Technical deep-dive
├── CONFIGURATION.md        # Configuration reference
├── nginx/                  # Reverse proxy
│   ├── README.MD          # Nginx documentation
│   ├── nginx.conf         # Proxy configuration
│   └── certs/             # TLS certificates
└── wg/                     # WireGuard VPN
    ├── README.MD          # VPN documentation
    └── wg0.conf           # VPN credentials
```

## Services

| Service | Container | Purpose |
|---------|-----------|---------|
| `vpn-gateway` | `vpn-gateway-shared` | WireGuard VPN with split routing |
| `nessus-pro-1` | `nessus-pro-1` | Nessus Professional scanner |
| `nessus-pro-2` | `nessus-pro-2` | Nessus Professional scanner |
| `nginx-proxy` | `nessus-nginx-proxy` | TLS termination, WebUI proxy |
| `debug-scanner` | `debug-scanner` | Troubleshooting + documentation server |
| `autoheal` | `autoheal-shared` | Auto-restart unhealthy containers |

## Architecture Highlights

### Traffic Flow

```
Browser (172.32.0.209:8443)
  ↓ HTTPS
Nginx Proxy (172.30.0.8)
  ↓ Container-to-Container HTTPS
Scanner 1 (172.30.0.3)
  ↓ Scan traffic
VPN Gateway (172.30.0.2)
  ↓ Split routing decision
  ├─→ LAN (172.32.0.x): Direct
  └─→ Internet: Via VPN (62.84.100.88)
```

### VPN Split Routing

```
Scanner Traffic:
├── 172.30.0.0/24 → Direct (container network)
├── 172.32.0.0/24 → Direct (LAN targets)
└── Everything else → VPN tunnel
```

### Key Features

- ✅ VPN split routing (automatic via Gluetun)
- ✅ Web UI access via nginx proxy
- ✅ MCP server integration (container names)
- ✅ Independent scanner routing
- ✅ Auto-healing unhealthy containers
- ✅ Static IPs prevent conflicts

## Common Operations

### Service Management

```bash
# Restart single service
docker compose restart nessus-pro-1

# Update scanner images
docker compose pull nessus-pro-1 nessus-pro-2
docker compose up -d nessus-pro-1 nessus-pro-2

# View service logs
docker compose logs -f nessus-pro-1
```

### Health Verification

```bash
# Check all services
docker compose ps

# Test VPN routing (should return VPN IP: 62.84.100.88)
docker exec debug-scanner curl -s https://api.ipify.org

# Test LAN access
docker exec debug-scanner ping -c 2 172.32.0.1

# Test scanner API
curl -k -s https://172.32.0.209:8443/server/status | jq
```

### Network Diagnostics

```bash
# View IP allocations
docker network inspect nessus-shared_vpn_net \
  --format '{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{"\n"}}{{end}}' | sort

# Test container-to-container access
docker exec debug-scanner curl -k https://nessus-pro-1:8834/server/status
```

## Troubleshooting

### Scanner Not Accessible

1. Check container status: `docker compose ps`
2. Verify nginx proxy: `docker compose logs nginx-proxy`
3. Test direct access: `docker exec nginx-proxy curl -k https://172.30.0.3:8834/server/status`

### VPN Issues

1. Check VPN logs: `docker logs vpn-gateway-shared`
2. Verify public IP: `docker exec debug-scanner curl -s https://api.ipify.org`
3. Expected VPN IP: `62.84.100.88`

### Browser Certificate Warning

Expected for self-signed certificates. Click "Advanced" → "Accept Risk".

### Connection Timeout in Browser

- ✅ Use `https://172.32.0.209:8443/` (LAN IP)
- ❌ Don't use `https://localhost:8443/` (won't work)

### IP Conflict After Restart

If services fail to start due to IP conflicts:
1. Stop all stacks: `docker compose down` (in both scanners-infra and dev1)
2. Start scanners-infra first: `docker compose up -d`
3. Then start dev1: `docker compose up -d`

All services have static IPs to prevent this, but order matters if network was recreated.

## Subdirectory Documentation

| Directory | Purpose | Link |
|-----------|---------|------|
| `nginx/` | Reverse proxy for WebUI access | [nginx/README.MD](nginx/README.MD) |
| `wg/` | WireGuard VPN split-routing | [wg/README.MD](wg/README.MD) |

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - Complete technical architecture
- [mcp-server/](../mcp-server/README.md) - MCP server that uses these scanners
- [dev1/](../dev1/) - MCP development compose file
