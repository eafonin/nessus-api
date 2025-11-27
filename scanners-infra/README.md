# Nessus Unified Mode - Quick Start

**Version:** 4.0
**Status:** Production
**Architecture:** [See ARCHITECTURE.md](./ARCHITECTURE.md) for technical deep-dive

---

## Quick Access URLs

⚠️ **IMPORTANT:** Use LAN IP (172.32.0.209), NOT localhost!

- **Scanner 1 Web UI:** https://172.32.0.209:8443/
- **Scanner 2 Web UI:** https://172.32.0.209:8444/
- **Documentation:** http://172.32.0.209:8080/

---

## Quick Start

### Start All Services
```bash
docker compose up -d
```

### Check Status
```bash
docker compose ps
```

### View Logs
```bash
docker compose logs -f
docker compose logs nginx-proxy
docker compose logs nessus-pro-1
```

### Stop All Services
```bash
docker compose down
```

---

## What's Running

| Service | Container | IP | Purpose |
|---------|-----------|----|---------|
| VPN Gateway | vpn-gateway-shared | 172.30.0.2 | WireGuard VPN + split routing |
| Scanner 1 | nessus-pro-1 | 172.30.0.3 | Nessus Pro scanner |
| Scanner 2 | nessus-pro-2 | 172.30.0.4 | Nessus Pro scanner |
| MCP Worker | nessus-mcp-worker-dev | 172.30.0.5 | MCP server worker |
| MCP API | nessus-mcp-api-dev | 172.30.0.6 | MCP API server |
| Debug/Docs | debug-scanner | 172.30.0.7 | Testing + documentation |
| Proxy | nginx-proxy | 172.30.0.8 | Reverse proxy for Web UIs |
| Autoheal | autoheal-shared | (none) | Auto-restart unhealthy containers |

---

## File Structure

```
/home/nessus/docker/nessus-shared/
├── docker-compose.yml    # Main configuration
├── ARCHITECTURE.md       # Technical architecture (READ THIS!)
├── README.md            # This file
└── nginx/
    ├── nginx.conf       # Nginx reverse proxy config
    └── certs/
        ├── nessus-proxy.crt
        └── nessus-proxy.key
```

---

## Common Tasks

### Restart a Single Service
```bash
docker compose restart nessus-pro-1
docker compose restart nginx-proxy
```

### Update Scanner Images
```bash
docker compose pull nessus-pro-1 nessus-pro-2
docker compose up -d nessus-pro-1 nessus-pro-2
```

### View Scanner Logs
```bash
docker compose logs -f nessus-pro-1
```

### Test VPN Routing
```bash
# Check public IP (should be VPN IP: 62.84.100.88)
docker exec debug-scanner curl -s https://api.ipify.org

# Check LAN access (should work)
docker exec debug-scanner ping -c 2 172.32.0.1
```

### Test Scanner Access
```bash
# Scanner 1
curl -k -s https://172.32.0.209:8443/server/status | jq

# Scanner 2
curl -k -s https://172.32.0.209:8444/server/status | jq
```

---

## Architecture Overview

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

**Key Features:**
- ✅ VPN split routing (automatic)
- ✅ Web UI access via nginx proxy
- ✅ MCP server integration
- ✅ Independent scanner routing
- ✅ Auto-healing unhealthy containers

---

## Troubleshooting

### "Connection Timeout" in Browser
- ✅ Use `https://172.32.0.209:8443/` (LAN IP)
- ❌ Don't use `https://localhost:8443/` (won't work)

### "Certificate Warning" in Browser
- Expected (self-signed certificate)
- Click "Advanced" → "Accept Risk and Continue"

### Scanner Not Ready
- Wait 30-60 seconds after startup
- Check logs: `docker compose logs nessus-pro-1`
- Check health: `docker compose ps`

### VPN Not Working
```bash
# Check VPN status
docker logs vpn-gateway-shared | tail -50

# Verify public IP
docker exec debug-scanner curl -s https://api.ipify.org
# Expected: 62.84.100.88
```

---

## Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Complete technical architecture (START HERE!)
- **[Quick Access Guide](../../projects/nessus-api/QUICK_ACCESS_GUIDE.md)** - URLs and commands
- **[Implementation Summary](../../projects/nessus-api/UNIFIED_MODE_IMPLEMENTATION_SUMMARY.md)** - Build history

---

## Support

For detailed technical information, architectural decisions, and troubleshooting, see **[ARCHITECTURE.md](./ARCHITECTURE.md)**.

For quick commands and access URLs, see **[QUICK_ACCESS_GUIDE.md](../../projects/nessus-api/QUICK_ACCESS_GUIDE.md)**.
