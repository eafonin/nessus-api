# Nginx Reverse Proxy

> TLS termination and WebSocket proxy for Nessus scanner WebUIs

## Purpose

Solves Docker NAT TLS handshake failures by providing container-to-container HTTPS proxying. Browsers connect to nginx, which forwards requests directly to scanner containers without NAT traversal.

## Architecture

```
Browser (LAN: 172.32.0.209:8443)
    ↓ HTTPS (TLS termination)
Nginx Proxy (172.30.0.8)
    ↓ HTTPS (container-to-container, no NAT)
Scanner 1 (172.30.0.3:8834)
```

## Directory Contents

| File | Purpose |
|------|---------|
| `nginx.conf` | Reverse proxy configuration |
| `certs/nessus-proxy.crt` | Self-signed TLS certificate |
| `certs/nessus-proxy.key` | TLS private key |

## Access URLs

| Service | URL | Backend |
|---------|-----|---------|
| Scanner 1 WebUI | `https://172.32.0.209:8443/` | `172.30.0.3:8834` |
| Scanner 2 WebUI | `https://172.32.0.209:8444/` | `172.30.0.4:8834` |
| Documentation | `http://172.32.0.209:8080/` | `172.30.0.7:8080` |

**Critical**: Use LAN IP (`172.32.0.209`), NOT `localhost` - Docker hairpin NAT prevents localhost access.

## Configuration Details

### nginx.conf Structure

```
http {
    # TLS settings (TLSv1.2+, strong ciphers)
    # Proxy settings (SSL verify off for self-signed scanner certs)
    # WebSocket upgrade mapping

    server { listen 8443 ssl; }  # Scanner 1
    server { listen 8444 ssl; }  # Scanner 2
    server { listen 8080; }      # Documentation
}
```

### Key Settings

| Setting | Value | Reason |
|---------|-------|--------|
| `proxy_ssl_verify` | `off` | Scanner uses self-signed cert |
| `proxy_buffering` | `off` | Required for SSE streams |
| `proxy_read_timeout` | `300s` | Long-running scan operations |

### WebSocket Support

Nessus WebUI uses WebSockets for real-time scan updates:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
```

## Certificate Management

Self-signed certificates in `certs/`:

```bash
# Generate new certificate (1 year validity)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/nessus-proxy.key \
  -out certs/nessus-proxy.crt \
  -subj "/CN=nessus-proxy"
```

Browser will show certificate warning - this is expected for self-signed certificates.

## Troubleshooting

### Connection Timeout

- Verify using LAN IP, not localhost
- Check nginx container is running: `docker compose ps nginx-proxy`
- Check nginx logs: `docker compose logs nginx-proxy`

### 502 Bad Gateway

- Scanner container not ready (wait 60s after startup)
- Scanner unhealthy: `docker compose ps nessus-pro-1`
- Network connectivity: `docker exec nginx-proxy ping 172.30.0.3`

### Certificate Warnings

Expected behavior for self-signed certificates. Click "Advanced" → "Accept Risk" in browser.

## See Also

- [Parent: scanners-infra/](../README.md) - Scanner infrastructure overview
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Full network architecture
- [docker-compose.yml](../docker-compose.yml) - Service definitions
