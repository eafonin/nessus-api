# Mode Switching Guide

> How to switch between NORMAL and UPDATE modes

## Overview

Two operational modes control port forwarding to solve VPN routing interference:

| Mode | Port Forwarding | WebUI Access (Host) | Plugin Updates | When to Use |
|------|----------------|---------------------|----------------|-------------|
| **NORMAL** | Enabled | ✓ localhost:8834/8835 | May fail | Daily operations |
| **UPDATE** | Disabled | ✗ Not accessible | ✓ Works | Plugin updates |

**Why modes exist:** Docker port forwarding creates NAT rules that interfere with VPN routing, breaking plugin updates. UPDATE mode removes port forwarding to enable clean VPN routing.

## Quick Start

```bash
cd /home/nessus/docker/nessus-shared

# Check current mode
./switch-mode.sh status

# Switch to UPDATE mode (for plugin updates)
./switch-mode.sh update

# Switch back to NORMAL mode
./switch-mode.sh normal
```

## Mode Switching Commands

### Check Current Mode

```bash
./switch-mode.sh status
```

Shows:
- Current operational mode
- Access URLs and capabilities
- Container status

### Switch to NORMAL Mode

```bash
./switch-mode.sh normal
```

**Enables:**
- WebUI access from host OS (https://localhost:8834, https://localhost:8835)
- LAN scanning via direct routing
- MCP API access via internal IPs

**Limitations:**
- Plugin updates may fail (Docker port forwarding interference)

**Use for:**
- Daily scanner operations
- Manual scanner configuration via WebUI
- LAN vulnerability scanning

### Switch to UPDATE Mode

```bash
./switch-mode.sh update
```

**Enables:**
- Plugin updates via VPN (clean routing, no NAT interference)
- LAN scanning via direct routing
- MCP API access via internal IPs

**Limitations:**
- WebUI NOT accessible from host OS

**Use for:**
- Updating vulnerability plugins
- Scheduled maintenance windows

## Plugin Update Workflow

### Complete Update Procedure

```bash
# 1. Check current mode
cd /home/nessus/docker/nessus-shared
./switch-mode.sh status

# 2. Switch to UPDATE mode
./switch-mode.sh update
# Containers will be recreated (takes ~30 seconds)

# 3. Trigger plugin updates via MCP API
# Scanner 1: https://172.30.0.3:8834
# Scanner 2: https://172.30.0.4:8834
# (Use MCP worker or SSH tunnel to access)

# 4. Wait for updates to complete
# Monitor via API polling or logs

# 5. Switch back to NORMAL mode
./switch-mode.sh normal
```

### Accessing Scanners in UPDATE Mode

Since WebUI is not accessible from host in UPDATE mode, use these methods:

**Method 1: Via MCP Worker** (recommended)
```bash
docker exec -it nessus-mcp-worker-dev bash
# Use Python/httpx to trigger updates via internal IPs
```

**Method 2: Via SSH Tunnel**
```bash
# From remote workstation
ssh -L 8834:172.30.0.3:8834 user@scanner-host -N -f
ssh -L 8835:172.30.0.4:8834 user@scanner-host -N -f

# Access via localhost:8834, localhost:8835
```

**Method 3: Via API Directly**
```bash
# From scanner host
curl -k -X POST https://172.30.0.3:8834/plugins/families \
  -H "X-API-Token: YOUR_TOKEN"
```

## Manual Mode Switching

If you prefer not to use the helper script:

### Switch to UPDATE Mode Manually

```bash
cd /home/nessus/docker/nessus-shared

# Stop scanners
docker compose stop nessus-pro-1 nessus-pro-2

# Restart with update mode override
docker compose -f docker-compose.yml -f docker-compose.update-mode.yml \
  up -d --force-recreate nessus-pro-1 nessus-pro-2
```

### Switch to NORMAL Mode Manually

```bash
cd /home/nessus/docker/nessus-shared

# Stop scanners
docker compose stop nessus-pro-1 nessus-pro-2

# Restart with base config only
docker compose up -d --force-recreate nessus-pro-1 nessus-pro-2
```

## Important Notes

### Container Restart Warning

Mode switching **always restarts** scanner containers:
- Running scans **will be interrupted**
- Scanner services unavailable for ~30 seconds
- Plan mode switches during maintenance windows

### Network Configuration Unchanged

Both modes use **identical split routing**:
- **LAN traffic** (172.32.0.0/24) → Direct via bridge gateway
- **Internet traffic** → Via VPN gateway (172.30.0.2)

The routing table inside containers is **identical** in both modes. Only host-level port forwarding changes.

### VPN Routing Unaffected

VPN routing works in both modes:
```bash
# VPN exit verification (works in both modes)
docker exec vpn-gateway-shared wget -qO- https://api.ipify.org
# Expected: 62.84.100.88 (Netherlands)
```

## Verification

### Verify NORMAL Mode

```bash
# 1. Check port forwarding exists
sudo iptables -t nat -L DOCKER -n | grep 8834
# Expected: DNAT rules for ports 8834 and 8835

# 2. Test WebUI access from host
curl -k https://localhost:8834/server/status
curl -k https://localhost:8835/server/status
# Expected: HTTP 200 responses
```

### Verify UPDATE Mode

```bash
# 1. Check port forwarding removed
sudo iptables -t nat -L DOCKER -n | grep 8834
# Expected: No output (no DNAT rules)

# 2. Test WebUI NOT accessible from host
curl -k -m 3 https://localhost:8834/server/status
# Expected: Connection timeout or refused

# 3. Test internal access still works
curl -k https://172.30.0.3:8834/server/status
curl -k https://172.30.0.4:8834/server/status
# Expected: HTTP 200 responses
```

### Verify VPN Routing (Both Modes)

```bash
# Check scanner routing
docker exec nessus-pro-1 ip route show
# Expected:
#   default via 172.30.0.2 dev eth0          # Internet → VPN
#   172.30.0.0/24 dev eth0 scope link        # Container network
#   172.32.0.0/24 via 172.30.0.1 dev eth0   # LAN → Direct

# Verify VPN NAT rules
docker exec vpn-gateway-shared iptables -t nat -L POSTROUTING -n | grep MASQUERADE
# Expected: MASQUERADE rules for 172.30.0.0/24
```

## Troubleshooting

### Mode Switch Fails

```bash
# Check docker-compose files exist
ls -la /home/nessus/docker/nessus-shared/docker-compose*.yml

# Check for syntax errors
docker compose config
docker compose -f docker-compose.yml -f docker-compose.update-mode.yml config

# Check container status
docker compose ps
```

### WebUI Not Accessible in NORMAL Mode

```bash
# Verify port forwarding
sudo iptables -t nat -L DOCKER -n | grep 8834

# Check containers are running
docker compose ps nessus-pro-1 nessus-pro-2

# Check scanner service is ready
docker logs nessus-pro-1 --tail 50
```

### Plugin Updates Still Fail in UPDATE Mode

```bash
# 1. Verify no port forwarding
sudo iptables -t nat -L DOCKER -n | grep 8834
# Expected: No output

# 2. Check VPN connectivity
docker exec vpn-gateway-shared wget -qO- https://api.ipify.org
# Expected: 62.84.100.88

# 3. Check VPN NAT rules
docker exec vpn-gateway-shared iptables -t nat -L POSTROUTING -n

# 4. Check scanner routing
docker exec nessus-pro-1 ip route show
```

### Containers Won't Start After Mode Switch

```bash
# Check logs
docker compose logs nessus-pro-1
docker compose logs nessus-pro-2

# Verify VPN gateway is healthy
docker compose ps vpn-gateway-shared
docker logs vpn-gateway-shared --tail 50

# Restart VPN gateway if needed
docker compose restart vpn-gateway-shared
sleep 5
docker compose restart nessus-pro-1 nessus-pro-2
```

## Best Practices

### Scheduled Plugin Updates

**Recommended workflow:**
1. Schedule updates during low-activity periods (weekends, nights)
2. Switch to UPDATE mode before triggering updates
3. Monitor update progress via API polling
4. Switch back to NORMAL mode after completion
5. Verify scanners are accessible via WebUI

### Pre-Switch Checks

**Before switching modes, verify:**
```bash
# No active scans (check via API or WebUI)
# VPN gateway is healthy
docker logs vpn-gateway-shared --tail 20

# Containers are running
docker compose ps
```

### Post-Switch Validation

**After switching modes, verify:**
```bash
# Containers restarted successfully
docker compose ps

# VPN routing still works
docker exec vpn-gateway-shared wget -qO- https://api.ipify.org

# Scanner internal IPs accessible
curl -k https://172.30.0.3:8834/server/status
curl -k https://172.30.0.4:8834/server/status
```

## See Also

- **[README.md](./README.md)** - Main documentation and quick reference
- **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** - Why dual-mode architecture exists and design rationale
- **[docker-compose.yml](./docker-compose.yml)** - Base configuration (NORMAL mode)
- **[docker-compose.update-mode.yml](./docker-compose.update-mode.yml)** - Override configuration (UPDATE mode)
