# Nessus Unified Mode - Quick Access Guide

## ⚠️ IMPORTANT: Use LAN IP, NOT localhost!

Due to Docker networking limitations, you **must** use the host's LAN IP:
**`172.32.0.209`**

`localhost` (127.0.0.1) will **NOT** work.

## WebUI Access URLs

### Scanner 1
```
https://172.32.0.209:8443/
```

### Scanner 2
```
https://172.32.0.209:8444/
```

### Test Service (Debug Only)
```
http://172.32.0.209:8080/
```

## MCP Server Internal Access

For MCP server configuration, use these internal IPs:

### Scanner 1
```
https://172.30.0.3:8834
```

### Scanner 2
```
https://172.30.0.4:8834
```

## Quick Commands

### Start Stack
```bash
cd /home/nessus/docker/nessus-shared
docker compose up -d
```

### Check Status
```bash
docker compose ps
docker compose logs -f nginx-proxy
```

### Stop Stack
```bash
docker compose down
```

### Verify VPN Routing
```bash
# Check public IP (should be VPN IP: 62.84.100.88)
docker exec debug-scanner curl -s https://api.ipify.org

# Check LAN access (should succeed)
docker exec debug-scanner ping -c 2 172.32.0.1
```

### Test Scanner Access
```bash
# Scanner 1
curl -k -s https://172.32.0.209:8443/server/status | jq

# Scanner 2
curl -k -s https://172.32.0.209:8444/server/status | jq
```

## Troubleshooting

### "Connection Timeout" when accessing via browser
✅ **Solution:** Make sure you're using `https://172.32.0.209:8443/` (LAN IP)
❌ **Don't use:** `https://localhost:8443/` (won't work)

### "Certificate Warning" in browser
This is expected (self-signed certificate). Click "Advanced" → "Accept Risk and Continue"

### Scanner not responding
Check scanner status:
```bash
docker compose ps
docker compose logs nessus-pro-1
docker compose logs nessus-pro-2
```

Wait 30-60 seconds for scanners to fully initialize.

### VPN not working
Check Gluetun status:
```bash
docker compose logs vpn-gateway-shared
```

Verify public IP is VPN IP:
```bash
docker exec debug-scanner curl -s https://api.ipify.org
# Expected: 62.84.100.88
```

## File Locations

- **Docker Compose:** `/home/nessus/docker/nessus-shared/docker-compose.yml`
- **Nginx Config:** `/home/nessus/docker/nessus-shared/nginx/nginx.conf`
- **SSL Certs:** `/home/nessus/docker/nessus-shared/nginx/certs/`
- **Backups:** `/home/nessus/docker/nessus-shared/backups/backup_20251114_194220/`

## Network Architecture

```
Host: 172.32.0.209
  ↓
  Nginx Proxy (172.30.0.8) on ports 8443/8444
  ↓
  Scanner 1 (172.30.0.3:8834) or Scanner 2 (172.30.0.4:8834)
  ↓
  VPN Gateway (172.30.0.2)
  ↓
  Internet via VPN (62.84.100.88) OR LAN direct (172.32.0.x)
```

## Quick Reference

| What | URL | Notes |
|------|-----|-------|
| Scanner 1 WebUI | `https://172.32.0.209:8443/` | Accept cert warning |
| Scanner 2 WebUI | `https://172.32.0.209:8444/` | Accept cert warning |
| Scanner 1 Internal | `https://172.30.0.3:8834` | For MCP only |
| Scanner 2 Internal | `https://172.30.0.4:8834` | For MCP only |
| Host LAN IP | `172.32.0.209` | Required for access |
| VPN Public IP | `62.84.100.88` | Verify VPN working |

## Complete Documentation

See `UNIFIED_MODE_IMPLEMENTATION_SUMMARY.md` for full implementation details, architecture diagrams, and technical analysis.
