# Dual-Mode Implementation Summary

> Why dual-mode architecture exists and how it solves VPN routing interference

## Problem Statement

Docker port forwarding creates NAT rules that interfere with VPN routing, preventing Nessus scanners from successfully downloading plugin updates while port forwarding is active.

**Observed Behavior:**
- Plugin updates **fail** when ports `8834:8834` and `8835:8834` are published to host
- LAN scanning works normally in both modes
- WebUI access requires port forwarding

**Root Cause:** Docker's iptables DNAT rules for port forwarding cause asymmetric routing that bypasses the VPN tunnel for return traffic.

## Solution: Dual-Mode Operation

Two operational modes toggle port forwarding on/off using Docker Compose override files:

| Mode | Port Forwarding | Purpose | WebUI Access | Plugin Updates |
|------|----------------|---------|--------------|----------------|
| **NORMAL** | Enabled | Daily operations | ✓ Via localhost | May fail (NAT interference) |
| **UPDATE** | Disabled | Plugin maintenance | ✗ Not from host | ✓ Works (clean VPN) |

### Mode Switching Mechanism

**NORMAL Mode** (base configuration):
```bash
docker compose up -d --force-recreate nessus-pro-1 nessus-pro-2
```
Containers start with port mappings defined in `docker-compose.yml`.

**UPDATE Mode** (with override):
```bash
docker compose -f docker-compose.yml -f docker-compose.update-mode.yml \
  up -d --force-recreate nessus-pro-1 nessus-pro-2
```
Override file uses `!reset` directive to clear inherited port mappings.

## How Modes Are Organized

### File Structure

```
/home/nessus/docker/nessus-shared/
├── docker-compose.yml               # Base config (NORMAL mode)
├── docker-compose.update-mode.yml   # Override (UPDATE mode)
├── switch-mode.sh                   # Interactive mode switcher
└── .current_mode                    # Tracks active mode (auto-generated)
```

### Base Configuration (docker-compose.yml)

Defines all services with port forwarding:

```yaml
services:
  nessus-pro-1:
    ports:
      - "8834:8834"  # Host access enabled
    networks:
      - vpn_net
    # ... other config

  nessus-pro-2:
    ports:
      - "8835:8834"  # Host access enabled
    networks:
      - vpn_net
    # ... other config
```

### Override Configuration (docker-compose.update-mode.yml)

Removes port forwarding using `!reset` directive:

```yaml
services:
  nessus-pro-1:
    ports: !reset []  # Clears inherited ports
    labels:
      - "nessus.mode=update"

  nessus-pro-2:
    ports: !reset []  # Clears inherited ports
    labels:
      - "nessus.mode=update"
```

## Why This Approach Works

### NAT Rule Behavior

**NORMAL Mode** (with port forwarding):
```
# iptables -t nat -L DOCKER -n
DNAT tcp dpt:8834 to:172.30.0.3:8834  ← Creates NAT interference
DNAT tcp dpt:8835 to:172.30.0.4:8834  ← Creates NAT interference
```

**UPDATE Mode** (without port forwarding):
```
# iptables -t nat -L DOCKER -n
(no entries for ports 8834/8835)  ← Clean VPN routing enabled
```

### Network Configuration Unchanged

Both modes use **identical split routing** inside containers:

```
Routing Table (inside scanners):
  default via 172.30.0.2          # Internet → VPN gateway
  172.30.0.0/24 dev eth0          # Container network
  172.32.0.0/24 via 172.30.0.1   # LAN → Direct routing
```

The only difference between modes is the presence/absence of Docker's port forwarding NAT rules on the host.

## Architecture Rationale

### Why Split Routing?

**Requirement:** Scanners need both VPN access (for plugin updates) and LAN access (for scanning local networks).

**Solution:** Two default routes with specific destination routing:
- **Default route**: Via VPN gateway (172.30.0.2) for internet traffic
- **Specific route**: Via bridge gateway (172.30.0.1) for LAN subnet (172.32.0.0/24)

### Why Docker Compose Override?

**Alternatives Considered:**
1. **Two separate compose files** - Requires duplicating all configuration
2. **Environment variables** - Cannot conditionally remove port mappings
3. **Multiple container definitions** - Confusing and error-prone

**Selected Approach:** Compose override with `!reset`
- Minimal duplication (only port changes)
- Standard Docker Compose feature
- Clear separation of concerns
- Easy to understand and maintain

### Why Container Recreation?

**Question:** Why not just toggle iptables rules?

**Answer:** Docker's port forwarding is set at container creation time. The DNAT rules are created when containers start with port mappings. Changing port configuration requires container recreation.

**Impact:** Running scans will be interrupted during mode switch. This is acceptable because:
- Mode switching is infrequent (only for plugin updates)
- Plugin updates are scheduled maintenance operations
- Users can plan switches during downtime

### Why VPN Gateway NAT?

**Requirement:** Scanner traffic must be masqueraded to appear from VPN tunnel IP.

**Solution:** Gluetun VPN gateway manages MASQUERADE rules automatically:

```
MASQUERADE  all  --  *  tun0  172.30.0.0/24  0.0.0.0/0
MASQUERADE  all  --  *  tun0  172.32.0.0/24  0.0.0.0/0
```

This ensures all scanner outbound traffic is NATted to VPN IP (10.0.0.26), which exits via Netherlands (62.84.100.88).

## Operational Workflow

### Standard Operations (NORMAL Mode)

```
1. Scanners run in NORMAL mode (default state)
2. WebUI accessible from host (localhost:8834, localhost:8835)
3. MCP worker manages scans via internal IPs
4. LAN scanning works (direct routing via 172.30.0.1)
5. Plugin updates MAY fail (Docker NAT interference)
```

### Plugin Update Workflow (UPDATE Mode)

```
1. Check current mode: ./switch-mode.sh status
2. Switch to UPDATE mode: ./switch-mode.sh update
   → Containers recreated without port forwarding
   → WebUI no longer accessible from host
3. Trigger plugin updates via MCP API (internal IPs still work)
4. Wait for updates to complete
5. Switch back to NORMAL: ./switch-mode.sh normal
   → Containers recreated with port forwarding restored
   → WebUI accessible again
```

### Mode Switch Script (`switch-mode.sh`)

Interactive script provides:
- **Safety confirmations** before mode changes
- **Status detection** shows current mode and capabilities
- **Mode history** tracks when switches occurred
- **Container recreation** handles Docker Compose commands

## Design Tradeoffs

### Tradeoff 1: Convenience vs. Functionality

**Sacrifice:** WebUI access from host during UPDATE mode
**Gain:** Plugin updates work reliably via VPN

**Rationale:** Plugin updates are infrequent operations. Sacrificing temporary WebUI convenience is acceptable for reliable plugin update functionality.

### Tradeoff 2: Simplicity vs. Automation

**Sacrifice:** Manual mode switching (not automatic)
**Gain:** Clear control and no unexpected behavior

**Rationale:** Automatic mode detection/switching could cause unexpected interruptions. Manual control gives operators clear visibility and decision-making power.

### Tradeoff 3: Container Restart vs. Live Reconfiguration

**Sacrifice:** Must restart containers to switch modes
**Gain:** Clean state and reliable mode switching

**Rationale:** Docker's port forwarding is set at container creation. Attempting live reconfiguration would be fragile and error-prone. Container recreation ensures clean state.

## Configuration Details

### VPN Gateway Configuration

**Container:** `vpn-gateway-shared`
**Image:** `qmcgaw/gluetun:latest`
**Function:** Shared WireGuard VPN for all scanners

**Key Settings:**
- `FIREWALL=on` - Enables kill switch and automatic NAT management
- `FIREWALL_OUTBOUND_SUBNETS=172.30.0.0/24,192.168.100.0/24` - Allows Docker networks
- `VPN_TYPE=wireguard` - WireGuard protocol
- `VPN_ENDPOINT_IP=62.84.100.88` - Netherlands server

### Scanner Configuration

**Containers:** `nessus-pro-1`, `nessus-pro-2`
**Image:** `tenable/nessus:latest-ubuntu`
**Networks:** Bridge network (vpn_net)

**Startup Commands:**
```bash
# Force VPN routing (applied at container start)
route del default gw 192.168.100.1 2>/dev/null || true
route add default gw 172.30.0.2 eth0

# Add LAN direct routing
ip route add 172.32.0.0/24 via 172.30.0.1 dev eth0
```

**Persistent Volumes:**
- `nessus_data_1` - Scanner 1 data (activation, plugins, scans)
- `nessus_data_2` - Scanner 2 data (activation, plugins, scans)

**Why External Volumes:** Scanner data persists across container recreation during mode switches and system reboots.

## Verification

### Test 1: Port Configuration

**NORMAL Mode:**
```bash
docker compose config | grep -A 3 "nessus-pro-1:" | grep "ports:"
# Expected: ports defined (8834:8834, 8835:8834)
```

**UPDATE Mode:**
```bash
docker compose -f docker-compose.yml -f docker-compose.update-mode.yml config | \
  python3 -c "import sys, yaml; c=yaml.safe_load(sys.stdin); \
  print('Ports:', c['services']['nessus-pro-1'].get('ports', 'NOT DEFINED'))"
# Expected: Ports: NOT DEFINED
```

### Test 2: Docker NAT Rules

**NORMAL Mode:**
```bash
sudo iptables -t nat -L DOCKER -n | grep 8834
# Expected: DNAT rules present
```

**UPDATE Mode:**
```bash
sudo iptables -t nat -L DOCKER -n | grep 8834
# Expected: No output (no DNAT rules)
```

### Test 3: VPN Routing

**Both Modes:**
```bash
docker exec nessus-pro-1 ip route show
# Expected:
#   default via 172.30.0.2 dev eth0
#   172.30.0.0/24 dev eth0 scope link
#   172.32.0.0/24 via 172.30.0.1 dev eth0
```

Routing configuration is identical in both modes.

## Future Enhancements

### Optional: Scheduled Updates

Automate mode switching for scheduled plugin updates using systemd timers:

```bash
# /etc/systemd/system/nessus-update-plugins.timer
[Timer]
OnCalendar=Sun 02:00
Persistent=true
```

### Optional: Pre-Switch Validation

Add scan status check to prevent interrupting active scans:

```bash
# Check for running scans via API before switching modes
# Delay mode switch if scans are active
```

### Optional: Plugin Update Monitoring

Monitor plugin update progress and auto-switch back to NORMAL when complete:

```bash
# Poll scanner API for plugin update status
# Automatically switch to NORMAL mode when updates finish
```

## Summary

**Implementation Status:** ✓ Complete and operational

**Key Decisions:**
- Dual-mode operation via Docker Compose override files
- Manual mode switching with interactive script
- Container recreation required for mode changes
- Split routing preserved across both modes
- VPN gateway handles NAT automatically

**Benefits:**
- Reliable plugin updates in UPDATE mode
- Convenient WebUI access in NORMAL mode
- Clear operational workflow
- Minimal configuration duplication
- Standard Docker Compose features

**Tradeoffs:**
- Manual mode switching (vs. automatic)
- Container recreation (vs. live reconfiguration)
- Temporary WebUI loss during UPDATE mode

See [MODE_SWITCHING_GUIDE.md](./MODE_SWITCHING_GUIDE.md) for operational procedures.
