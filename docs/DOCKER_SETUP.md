# Nessus Docker Setup

## Overview

Nessus Essentials runs in a Docker container with a VPN gateway (WireGuard) for secure scanning operations. The setup uses docker-compose for orchestration and includes autoheal for container monitoring.

## System Information

- **Host**: nessus@37.18.107.123 (Ubuntu 24.04 LTS)
- **User**: uid=1001(nessus) gid=1001(nessus)
- **Groups**: nessus, sudo, docker
- **Docker Location**: `/home/nessus/docker/nessus/`
- **Kernel**: Linux 6.14.0-33-generic #33~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC

## Architecture

```
┌─────────────────────────────────────────┐
│  Host: 37.18.107.123                    │
│  ┌───────────────────────────────────┐  │
│  │  VPN Gateway (Gluetun)            │  │
│  │  - WireGuard VPN Connection       │  │
│  │  - Network: 172.32.0.0/24         │  │
│  │  - Exposed Port: 8834             │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │  Nessus Pro/Essentials      │  │  │
│  │  │  - Runs via VPN gateway     │  │  │
│  │  │  - Web UI: localhost:8834   │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Autoheal (Monitoring)            │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Docker Compose Configuration

Location: `/home/nessus/docker/nessus/docker-compose.yml`

### Services

#### 1. vpn-gateway (Gluetun)
- **Image**: `qmcgaw/gluetun:latest`
- **Purpose**: Provides VPN connectivity via WireGuard
- **Capabilities**: NET_ADMIN
- **Network**: nessus_net (bridge, IPv6 disabled)
- **Exposed Port**: 8834 (Nessus Web UI accessible LAN-wide)
- **Environment**:
  - VPN Provider: Custom WireGuard configuration
  - Timezone: Europe/Amsterdam
  - Firewall: Outbound traffic restricted to 172.32.0.0/24
  - Local network: 172.32.0.0/24
- **Volume**: WireGuard config mounted at `/gluetun/wireguard/wg0.conf`
- **Auto-restart**: Disabled (manual control)
- **Autoheal**: Enabled

#### 2. nessus-pro
- **Image**: `tenable/nessus:latest-ubuntu`
- **Purpose**: Nessus vulnerability scanner
- **Network Mode**: Shares network stack with vpn-gateway
- **Dependencies**: Starts after vpn-gateway
- **Credentials**:
  - Username: `nessus`
  - Password: `nessus`
- **Activation**: Nessus Essentials license code configured
- **Auto-restart**: Disabled (manual control)

#### 3. autoheal
- **Image**: `willfarrell/autoheal:latest`
- **Purpose**: Monitors and auto-restarts containers labeled with `autoheal=true`
- **Network**: None (isolated)
- **Access**: Docker socket mounted for container management

### WireGuard Configuration

Location: `/home/nessus/docker/nessus/wg/`

- `wg0.conf` → symlink to `wg0.conf.new`
- Contains VPN endpoint, keys, and routing configuration
- **Security**: Files are mode 600 (read/write owner only)

## Docker Commands

### Start Services
```bash
cd /home/nessus/docker/nessus
docker compose up -d
```

### Stop Services
```bash
docker compose down
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f nessus-pro
docker compose logs -f vpn-gateway
```

### Check Status
```bash
docker compose ps
```

### Restart Nessus
```bash
docker compose restart nessus-pro
```

### Rebuild and Restart
```bash
docker compose down
docker compose pull
docker compose up -d
```

## Network Configuration

### Docker Network
- **Name**: `nessus_net`
- **Type**: Bridge
- **IPv6**: Disabled
- **Subnet**: 172.32.0.0/24 (internal VPN network)

### Port Mapping
- **Host Port**: 8834
- **Container Port**: 8834 (via vpn-gateway)
- **Access**: LAN-wide (0.0.0.0:8834)
- **Protocol**: HTTPS

### Firewall Rules
- Outbound traffic restricted to 172.32.0.0/24 via Gluetun firewall
- Local network access: 172.32.0.0/24

## Accessing Nessus

### Local Access
```
https://localhost:8834
```

### LAN Access
```
https://37.18.107.123:8834
```

### Credentials
- **Username**: `nessus`
- **Password**: `nessus`

## License Information

- **Type**: Nessus Essentials (Home License)
- **Activation Code**: Configured in docker-compose.yml
- **IP Limit**: 16 IPs
- **Features**:
  - `api: true` (Read-only API operations)
  - `scan_api: false` (Scan control requires Web UI simulation)
  - `policies: true`
  - `report: true`

## Integration with nessus-api Project

The Python automation scripts in `/home/nessus/projects/nessus-api/` connect to the Nessus instance via:

1. **API Authentication** (Read-only operations):
   - URL: `https://localhost:8834`
   - Access Key & Secret Key (hardcoded in scripts)

2. **Web UI Authentication** (Scan control operations):
   - URL: `https://localhost:8834`
   - Username/Password: nessus/nessus
   - Session token generated per script execution

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker compose logs vpn-gateway
docker compose logs nessus-pro

# Verify WireGuard config
ls -la wg/
cat wg/wg0.conf  # Check syntax
```

### VPN Connection Issues
```bash
# Check VPN gateway status
docker exec vpn-gateway ip addr
docker exec vpn-gateway ip route

# Restart VPN gateway
docker compose restart vpn-gateway
```

### Nessus UI Not Accessible
```bash
# Verify port mapping
docker compose ps
netstat -tlnp | grep 8834

# Check if Nessus is ready
curl -k https://localhost:8834/server/status
```

### Autoheal Not Working
```bash
# Check autoheal logs
docker logs autoheal

# Verify autoheal label on vpn-gateway
docker inspect vpn-gateway | grep autoheal
```

### Permission Issues
```bash
# Verify user is in docker group
groups nessus

# If not, add user to docker group
sudo usermod -aG docker nessus
# Then logout and login again
```

## Security Considerations

1. **VPN Configuration**: WireGuard configs contain sensitive credentials
   - Stored with 600 permissions
   - Not tracked in git
   - Keep backup of `wg0.conf` in secure location

2. **Nessus Credentials**: Default credentials are hardcoded
   - Change default password in production
   - Use strong authentication

3. **API Keys**: Hardcoded in Python scripts
   - Consider using environment variables
   - Rotate keys periodically

4. **Network Isolation**: Nessus traffic routed through VPN
   - Prevents direct exposure
   - All scanning traffic encrypted

5. **SSL Certificates**: Self-signed certificates in use
   - SSL verification disabled in scripts
   - Consider proper certificates for production

## Maintenance

### Update Nessus
```bash
cd /home/nessus/docker/nessus
docker compose pull nessus-pro
docker compose up -d nessus-pro
```

### Update Plugin Feed
Automatic via Nessus (requires internet/VPN connectivity)

### Backup Configuration
```bash
# Backup Nessus data
docker exec nessus-pro tar -czf /opt/nessus/backup.tar.gz /opt/nessus/var/nessus

# Copy backup out of container
docker cp nessus-pro:/opt/nessus/backup.tar.gz ~/backups/

# Backup WireGuard config
cp -a wg/ ~/backups/nessus-wg-$(date +%Y%m%d)/
```

### Monitor Disk Space
```bash
# Check Docker disk usage
docker system df

# Clean up old images
docker system prune -a
```

## Notes

- **Restart Policy**: Set to `"no"` for manual control (prevents automatic restarts)
- **IPv6**: Disabled via sysctls and network configuration
- **Time Zone**: Europe/Amsterdam (configured in vpn-gateway)
- **Autoheal Label**: Only vpn-gateway is monitored for auto-restart

---

**Last Updated**: 2025-10-31
**Docker Compose Version**: 3.9
**Location**: `/home/nessus/docker/nessus/`
