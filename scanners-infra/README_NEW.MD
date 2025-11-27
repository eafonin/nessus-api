# Nessus Scanner Infrastructure

> Docker deployment for Nessus Pro scanners with VPN split-routing and reverse proxy

## Overview

Self-contained infrastructure for running multiple Nessus Professional scanners with:

- **VPN Split Routing** - Internet traffic via VPN, LAN scans direct
- **Reverse Proxy** - TLS termination for WebUI access
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

**Critical**: Use LAN IP (`172.32.0.209`), NOT `localhost`.

### MCP Server Internal Access

| Scanner | URL | Network |
|---------|-----|---------|
| Scanner 1 API | `https://172.30.0.3:8834` | Container-to-container |
| Scanner 2 API | `https://172.30.0.4:8834` | Container-to-container |

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

## Network Topology

```
vpn_net (172.30.0.0/24)
├── 172.30.0.1  Docker bridge gateway
├── 172.30.0.2  VPN Gateway (Gluetun)
├── 172.30.0.3  Scanner 1 (Nessus Pro)
├── 172.30.0.4  Scanner 2 (Nessus Pro)
├── 172.30.0.5  MCP Worker
├── 172.30.0.6  MCP API
├── 172.30.0.7  Debug Scanner + Docs
└── 172.30.0.8  Nginx Proxy
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

## Subdirectory Documentation

| Directory | Purpose | Link |
|-----------|---------|------|
| `nginx/` | Reverse proxy for WebUI access | [nginx/README.MD](nginx/README.MD) |
| `wg/` | WireGuard VPN split-routing | [wg/README.MD](wg/README.MD) |

## Architecture Highlights

### VPN Split Routing

```
Scanner Traffic:
├── 172.30.0.0/24 → Direct (container network)
├── 172.32.0.0/24 → Direct (LAN targets)
└── Everything else → VPN tunnel
```

### TLS Proxy Chain

```
Browser → Nginx (TLS termination) → Scanner (container HTTPS)
```

Solves Docker NAT TLS handshake failures.

### Health Monitoring

- Scanners have Python-based health checks (60s interval)
- Autoheal container restarts unhealthy services
- 180s start period allows for scanner initialization

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

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - Complete technical architecture
- [CONFIGURATION.md](CONFIGURATION.md) - Detailed configuration reference
- [mcp-server/](../mcp-server/README_NEW.MD) - MCP server that uses these scanners
