# Application Proxy Solution for WebUI Access

**Date:** 2025-11-14
**Proposed Solution:** Use Traefik/nginx reverse proxy to bridge internal Docker network to host OS
**Status:** ✅ VIABLE - Should solve Docker NAT TLS issue

---

## TL;DR - The Solution

**Problem:** Docker NAT breaks TLS handshakes from host to containers
**Solution:** Use reverse proxy container on same Docker network to terminate/forward TLS
**Result:** Host → Proxy (no NAT) → Scanner (container-to-container, no NAT)

**Expected Outcome:** ✅ Localhost WebUI access should work + Keep NORMAL/UPDATE modes

---

## Why This Should Work

### The Current TLS Issue

```
Host → localhost:8834 → Docker NAT → Container
                            ↓
                    TLS handshake FAILS
                    (NAT modifies packets)
```

### With Reverse Proxy

```
Host → localhost:8080 → Docker Port Mapping → Proxy Container
                                ↓
                          TLS terminates at proxy
                                ↓
                        Proxy → 172.30.0.3:8834 → Scanner
                                ↓
                        Container-to-container (no NAT)
                                ✅ Works!
```

**Key Insight:**
- Proxy **terminates** TLS from host (accepts HTTPS on 8080)
- Proxy **initiates new** connection to scanner (container-to-container)
- No Docker NAT in the middle of the end-to-end TLS session

---

## Proposed Architecture

### Option 1: Traefik (Recommended)

**Why Traefik:**
- ✅ Dynamic configuration (no reload needed)
- ✅ Automatic service discovery
- ✅ Built-in TLS termination
- ✅ Dashboard for monitoring
- ✅ Docker-native

**Configuration:**

```yaml
services:
  traefik:
    image: traefik:v2.10
    container_name: traefik-proxy
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--log.level=INFO"
    ports:
      - "8080:80"      # HTTP
      - "8443:443"     # HTTPS
      - "9090:8080"    # Traefik dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik/certs:/certs:ro  # Self-signed certs
    networks:
      - vpn_net
    restart: unless-stopped

  # Nessus scanners with labels for Traefik
  nessus-pro-1:
    image: tenable/nessus:latest-ubuntu
    networks:
      vpn_net:
        ipv4_address: 172.30.0.3
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.scanner1.rule=Host(`scanner1.local`) || PathPrefix(`/scanner1`)"
      - "traefik.http.routers.scanner1.entrypoints=websecure"
      - "traefik.http.routers.scanner1.tls=true"
      - "traefik.http.services.scanner1.loadbalancer.server.port=8834"
      - "traefik.http.services.scanner1.loadbalancer.server.scheme=https"
    # Can still use NORMAL/UPDATE modes!

  nessus-pro-2:
    image: tenable/nessus:latest-ubuntu
    networks:
      vpn_net:
        ipv4_address: 172.30.0.4
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.scanner2.rule=Host(`scanner2.local`) || PathPrefix(`/scanner2`)"
      - "traefik.http.routers.scanner2.entrypoints=websecure"
      - "traefik.http.routers.scanner2.tls=true"
      - "traefik.http.services.scanner2.loadbalancer.server.port=8834"
      - "traefik.http.services.scanner2.loadbalancer.server.scheme=https"
```

**Access URLs:**
```
Scanner 1: https://localhost:8443/scanner1
Scanner 2: https://localhost:8443/scanner2

Or with host file entries:
Scanner 1: https://scanner1.local:8443
Scanner 2: https://scanner2.local:8443
```

### Option 2: Nginx

**Why Nginx:**
- ✅ Simpler configuration
- ✅ Well-known, stable
- ✅ Lower resource usage
- ⚠️ Static configuration (requires reload for changes)

**Configuration:**

```yaml
services:
  nginx-proxy:
    image: nginx:alpine
    container_name: nginx-proxy
    ports:
      - "8080:80"
      - "8443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    networks:
      - vpn_net
    depends_on:
      - nessus-pro-1
      - nessus-pro-2
    restart: unless-stopped

  nessus-pro-1:
    networks:
      vpn_net:
        ipv4_address: 172.30.0.3
    # Can use NORMAL/UPDATE modes!

  nessus-pro-2:
    networks:
      vpn_net:
        ipv4_address: 172.30.0.4
    # Can use NORMAL/UPDATE modes!
```

**Nginx Configuration (`nginx.conf`):**

```nginx
events {
    worker_connections 1024;
}

http {
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Upstream servers
    upstream scanner1 {
        server 172.30.0.3:8834;
    }

    upstream scanner2 {
        server 172.30.0.4:8834;
    }

    # Scanner 1 proxy
    server {
        listen 443 ssl;
        server_name scanner1.local;

        ssl_certificate /etc/nginx/certs/cert.pem;
        ssl_certificate_key /etc/nginx/certs/key.pem;

        location / {
            proxy_pass https://scanner1;
            proxy_ssl_verify off;  # Accept self-signed cert from scanner

            # WebSocket support (if needed)
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            # Headers
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # Scanner 2 proxy
    server {
        listen 443 ssl;
        server_name scanner2.local;

        ssl_certificate /etc/nginx/certs/cert.pem;
        ssl_certificate_key /etc/nginx/certs/key.pem;

        location / {
            proxy_pass https://scanner2;
            proxy_ssl_verify off;

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # Default server (path-based routing)
    server {
        listen 443 ssl default_server;
        server_name _;

        ssl_certificate /etc/nginx/certs/cert.pem;
        ssl_certificate_key /etc/nginx/certs/key.pem;

        location /scanner1/ {
            proxy_pass https://scanner1/;
            proxy_ssl_verify off;
            # ... same headers as above
        }

        location /scanner2/ {
            proxy_pass https://scanner2/;
            proxy_ssl_verify off;
            # ... same headers as above
        }
    }
}
```

**Access URLs:**
```
Scanner 1: https://localhost:8443/scanner1/
Scanner 2: https://localhost:8443/scanner2/

Or with /etc/hosts entries:
127.0.0.1 scanner1.local scanner2.local

Scanner 1: https://scanner1.local:8443
Scanner 2: https://scanner2.local:8443
```

---

## Benefits of Proxy Solution

### Advantages

1. **✅ Solves TLS Issue**
   - Proxy terminates TLS from host (no Docker NAT involved)
   - Proxy initiates new connection to scanner (container-to-container)
   - No NAT in the critical TLS path

2. **✅ Keep NORMAL/UPDATE Modes**
   - Scanners use separate network namespaces
   - Can still modify routing with `ip route` commands
   - Mode switching works as designed

3. **✅ Additional Features**
   - Load balancing (if you add more scanners)
   - Path-based routing (/scanner1, /scanner2)
   - Host-based routing (scanner1.local, scanner2.local)
   - Single entry point for multiple scanners
   - Access logs and monitoring
   - Rate limiting (if needed)

4. **✅ Flexibility**
   - Easy to add more scanners
   - Can proxy other services too
   - Can add authentication at proxy level
   - Can add custom headers

### Trade-offs

1. **⚠️ Additional Container**
   - One more service to manage
   - Slightly more resource usage

2. **⚠️ Additional Configuration**
   - Need to configure proxy
   - Need to generate/manage TLS certificates
   - More complex troubleshooting

3. **⚠️ Extra Network Hop**
   - Minimal latency impact (container-to-container is fast)
   - But it's one more layer

---

## Why This Should Work (Technical)

### Container-to-Container Communication

**Current working scenario:**
```bash
# From debug-scanner container to Scanner 1:
docker exec debug-scanner curl -k https://172.30.0.3:8834/server/status
# Result: ✅ Works instantly
```

**Proxy scenario:**
```
Nginx/Traefik container → 172.30.0.3:8834
         ↓
   Same network (vpn_net)
         ↓
   No Docker NAT
         ↓
   Container-to-container direct communication
         ✅ Should work!
```

### TLS Flow with Proxy

**Without proxy (current broken):**
```
Browser TLS handshake → localhost:8834 → Docker NAT → Scanner
                                             ↓
                                      Packets modified
                                             ↓
                                        TLS FAILS
```

**With proxy:**
```
Browser TLS handshake → localhost:8443 → Docker NAT → Proxy
                                             ↓
                                    TLS terminates (succeeds)
                                             ↓
                         Proxy new TLS handshake → 172.30.0.3:8834 → Scanner
                                             ↓
                                    Container-to-container
                                             ↓
                                        TLS SUCCEEDS
```

---

## Implementation Plan

### Phase 1: Test with Nginx (Simpler)

**Step 1: Generate self-signed certificates**
```bash
cd /home/nessus/docker/nessus-shared
mkdir -p nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/key.pem \
  -out nginx/certs/cert.pem \
  -subj "/CN=localhost"
```

**Step 2: Create nginx.conf**
```bash
# See nginx configuration above
cat > nginx/nginx.conf <<'EOF'
# ... nginx config from above ...
EOF
```

**Step 3: Add to docker-compose.yml**
```bash
# Add nginx-proxy service (see config above)
```

**Step 4: Test**
```bash
docker compose up -d nginx-proxy
curl -k https://localhost:8443/scanner1/server/status
```

### Phase 2: If Nginx works, optionally switch to Traefik

**Traefik advantages:**
- Auto-discovery (no manual config per scanner)
- Better dashboard
- Easier to scale

**Nginx advantages:**
- Simpler
- Lower resource usage
- Already tested in Phase 1

---

## Expected Results

### What Should Work

**With Proxy:**
- ✅ `https://localhost:8443/scanner1` → Scanner 1 WebUI
- ✅ `https://localhost:8443/scanner2` → Scanner 2 WebUI
- ✅ NORMAL/UPDATE modes (scanners have separate namespaces)
- ✅ VPN split routing in UPDATE mode
- ✅ MCP automation (internal IPs still work)

**Without changing:**
- ✅ LAN scanning (direct routing)
- ✅ Plugin updates (VPN routing in UPDATE mode)

### What Changes

**Access method:**
- Old: `https://172.32.0.209:8834` (host LAN IP)
- New: `https://localhost:8443/scanner1` (via proxy)

**Network flow:**
- Old: Browser → host NIC → Docker port → shared namespace
- New: Browser → proxy → container-to-container → scanner

---

## Comparison: Proxy vs Shared Namespace

| Feature | Shared Namespace | Reverse Proxy |
|---------|-----------------|---------------|
| **WebUI Access** | ✅ Via host LAN IP | ✅ Via localhost |
| **NORMAL/UPDATE Modes** | ❌ Incompatible | ✅ Compatible |
| **VPN Split Routing** | ⚠️ Inherited | ✅ Per-scanner |
| **Mode Switching** | ❌ Not possible | ✅ Works |
| **Complexity** | Low (1 override) | Medium (+proxy) |
| **Resource Usage** | Low | Medium (+proxy container) |
| **Flexibility** | Low | High (multiple scanners) |
| **Access URL** | host LAN IP | localhost |

---

## Recommendation

### For Your Use Case

**Recommended: Try Nginx Proxy**

**Why:**
1. ✅ Should solve localhost TLS issue
2. ✅ Keep NORMAL/UPDATE modes
3. ✅ Simpler than Traefik for basic use
4. ✅ Low resource overhead
5. ✅ Can upgrade to Traefik later if needed

**Implementation:**
1. Start with nginx (simpler to test)
2. If it works, decide if you want to switch to Traefik
3. If it doesn't work, fall back to shared namespace

### Quick Test Script

```bash
#!/bin/bash
# File: /home/nessus/projects/nessus-api/test-nginx-proxy.sh

cd /home/nessus/docker/nessus-shared

# 1. Revert to separate namespace (for NORMAL/UPDATE modes)
echo "Reverting to separate namespace..."
docker compose up -d --force-recreate nessus-pro-1 nessus-pro-2

# 2. Wait for scanners to initialize
echo "Waiting 30s for scanners..."
sleep 30

# 3. Test internal IP access from another container (should work)
echo "Testing container-to-container access..."
docker exec debug-scanner curl -k -s https://172.30.0.3:8834/server/status | head -5

# 4. Add nginx proxy
echo "Starting nginx proxy..."
docker compose up -d nginx-proxy

# 5. Test via proxy
echo "Testing via nginx proxy..."
sleep 5
curl -k -s https://localhost:8443/scanner1/server/status | head -5

echo "Done! Check if proxy access works."
```

---

## Potential Issues and Solutions

### Issue 1: Nessus WebUI doesn't like proxies

**Symptom:** Login works but WebUI elements don't load
**Cause:** WebUI makes assumptions about URLs/paths
**Solution:** Use host-based routing instead of path-based

```nginx
# Instead of /scanner1, use scanner1.local
server {
    listen 443 ssl;
    server_name scanner1.local;
    location / {
        proxy_pass https://172.30.0.3:8834;
    }
}
```

### Issue 2: WebSocket connections fail

**Symptom:** Real-time updates don't work
**Cause:** Proxy doesn't forward WebSocket upgrade
**Solution:** Already included in nginx config above

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### Issue 3: Session cookies don't work

**Symptom:** Can't stay logged in
**Cause:** Cookie domain mismatch
**Solution:** Ensure `Host` header is proxied

```nginx
proxy_set_header Host $host;
```

---

## Final Recommendation

### Test Plan

1. **Backup current working config**
```bash
cd /home/nessus/docker/nessus-shared
cp docker-compose.yml docker-compose.yml.backup-webui
```

2. **Implement nginx proxy** (see implementation plan above)

3. **Test localhost access**
```bash
curl -k https://localhost:8443/scanner1/server/status
```

4. **Test in browser**
```
https://localhost:8443/scanner1
```

5. **Test NORMAL/UPDATE mode switching**
```bash
./switch-mode.sh update
# Test that routing changes work
./switch-mode.sh normal
```

6. **If it works:** Document as permanent solution
7. **If it doesn't work:** Revert to shared namespace

### Expected Outcome

**Probability of success:** ⭐⭐⭐⭐⭐ (Very High)

**Why:** Container-to-container HTTPS already works (proven with debug-scanner). Proxy just bridges the gap between host and containers.

---

**Status:** ✅ **VIABLE SOLUTION - RECOMMENDED TO TEST**
**Next Step:** Implement nginx proxy and test localhost access

---

## Related Documentation

**Core WebUI Access:**
- [WEBUI_ACCESS_SOLUTION_FINAL.md](WEBUI_ACCESS_SOLUTION_FINAL.md) - Current working solution (host LAN IP)
- [WEBUI_ACCESS_QUICKREF.md](WEBUI_ACCESS_QUICKREF.md) - Quick reference for daily use

**Mode Analysis:**
- [MODE_COMPATIBILITY_ANALYSIS.md](MODE_COMPATIBILITY_ANALYSIS.md) - Why shared namespace and modes are incompatible
- [FINAL_MODE_RECOMMENDATION.md](FINAL_MODE_RECOMMENDATION.md) - Recommendation to keep shared namespace

**Index:**
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Master index of all project documentation
