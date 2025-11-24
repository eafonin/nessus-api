# Nessus WebUI Access - Quick Reference

**Status:** ✅ WORKING
**Last Updated:** 2025-11-14

---

## Access the WebUI

### URL
```
https://172.32.0.209:8834
```

### Credentials
```
Username: nessus
Password: nessus
```

### Browser Warning
You'll see a certificate warning. Click "Advanced" → "Proceed".

---

## Why Not Localhost?

❌ `https://localhost:8834` - **DOESN'T WORK**
✅ `https://172.32.0.209:8834` - **WORKS**

**Reason:** Docker NAT breaks TLS handshakes for localhost connections.

---

## Docker Configuration

### Current Setup
- **Network mode:** `service:vpn-gateway` (shared namespace)
- **Port:** `8834:8834` on vpn-gateway container
- **Access:** Via host LAN IP only

### Apply Configuration
```bash
cd /home/nessus/docker/nessus-shared
docker compose -f docker-compose.yml -f docker-compose.old-working-test.yml up -d
```

### Verify
```bash
# Check containers
docker ps --filter "name=vpn-gateway\|nessus-pro-1"

# Test access
curl -k -s https://172.32.0.209:8834/server/status
```

---

## Troubleshooting

### If host IP changed:
```bash
ip addr show | grep "inet 172.32"
```
Use the new IP in your browser.

### If WebUI not loading:
```bash
# Check Nessus status
curl -k -s https://172.32.0.209:8834/server/status | python3 -m json.tool

# Look for "status": "ready"
```

---

## Documentation

**Full guide:** `/home/nessus/projects/nessus-api/WEBUI_ACCESS_SOLUTION_FINAL.md`
**Docker config:** `/home/nessus/docker/nessus-shared/docker-compose.old-working-test.yml`
**Old backup:** `/home/nessus/docker/backups/20251111_135253/nessus-old/`
