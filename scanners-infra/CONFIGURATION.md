# Configuration Reference

> Docker Compose and WireGuard configuration details

## Docker Compose Files

### Base Configuration (docker-compose.yml)

**Purpose**: Defines NORMAL mode with port forwarding enabled

**Key Services:**

```yaml
services:
  vpn-gateway-shared:
    image: qmcgaw/gluetun:latest
    container_name: vpn-gateway-shared
    cap_add:
      - NET_ADMIN
    environment:
      - VPN_SERVICE_PROVIDER=custom
      - VPN_TYPE=wireguard
      - WIREGUARD_CONF_SECRETFILE=/gluetun/wg0.conf
      - FIREWALL=on
      - FIREWALL_OUTBOUND_SUBNETS=172.30.0.0/24,192.168.100.0/24
    volumes:
      - ./wg:/gluetun
    networks:
      vpn_net:
        ipv4_address: 172.30.0.2

  nessus-pro-1:
    image: tenable/nessus:latest-ubuntu
    container_name: nessus-pro-1
    ports:
      - "8834:8834"  # Port forwarding (NORMAL mode)
    environment:
      - ACTIVATION_CODE=${ACTIVATION_CODE_1}
    volumes:
      - nessus_data_1:/opt/nessus
    networks:
      - vpn_net
    cap_add:
      - NET_ADMIN
    command: >
      sh -c "route del default gw 192.168.100.1 2>/dev/null || true &&
             route add default gw 172.30.0.2 eth0 &&
             ip route add 172.32.0.0/24 via 172.30.0.1 dev eth0 &&
             /opt/nessus/sbin/nessusctl start"

  nessus-pro-2:
    image: tenable/nessus:latest-ubuntu
    container_name: nessus-pro-2
    ports:
      - "8835:8834"  # Port forwarding (NORMAL mode)
    environment:
      - ACTIVATION_CODE=${ACTIVATION_CODE_2}
    volumes:
      - nessus_data_2:/opt/nessus
    networks:
      - vpn_net
    cap_add:
      - NET_ADMIN
    command: >
      sh -c "route del default gw 192.168.100.1 2>/dev/null || true &&
             route add default gw 172.30.0.2 eth0 &&
             ip route add 172.32.0.0/24 via 172.30.0.1 dev eth0 &&
             /opt/nessus/sbin/nessusctl start"

networks:
  vpn_net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/24

volumes:
  nessus_data_1:
    external: true
  nessus_data_2:
    external: true
```

### Update Mode Override (docker-compose.update-mode.yml)

**Purpose**: Removes port forwarding for UPDATE mode using `!reset` directive

```yaml
services:
  nessus-pro-1:
    ports: !reset []  # Removes inherited port mappings
    labels:
      - "nessus.mode=update"

  nessus-pro-2:
    ports: !reset []  # Removes inherited port mappings
    labels:
      - "nessus.mode=update"
```

## Network Configuration

### Bridge Network (vpn_net)

**Subnet**: `172.30.0.0/24`
**Gateway**: `172.30.0.1` (Docker bridge)
**DNS**: Handled by VPN gateway

**IP Assignments:**
- `172.30.0.2` - VPN gateway
- `172.30.0.3` - Scanner 1 (nessus-pro-1)
- `172.30.0.4` - Scanner 2 (nessus-pro-2)

### Routing Configuration

**Inside Scanner Containers:**

```bash
# Default route → VPN gateway (for internet traffic)
default via 172.30.0.2 dev eth0

# Container network (local Docker communication)
172.30.0.0/24 dev eth0 scope link

# LAN subnet → Direct routing (bypasses VPN)
172.32.0.0/24 via 172.30.0.1 dev eth0
```

**Why Split Routing?**
- Internet traffic (plugin updates) → VPN (Netherlands)
- LAN scanning → Direct routing (no VPN overhead)

## WireGuard VPN Configuration

### Configuration File Location

`/home/nessus/docker/nessus-shared/wg/wg0.conf`

### Configuration Structure

```ini
[Interface]
PrivateKey = <REDACTED>
Address = 10.0.0.26/32
DNS = 10.0.0.1

[Peer]
PublicKey = <SERVER_PUBLIC_KEY>
AllowedIPs = <SPLIT_TUNNEL_CIDRS>
Endpoint = 62.84.100.88:51830
PersistentKeepalive = 15
```

### Key Settings

**Interface:**
- **Address**: `10.0.0.26/32` - VPN tunnel IP
- **DNS**: `10.0.0.1` - VPN DNS server

**Peer:**
- **Endpoint**: `62.84.100.88:51830` - Netherlands VPN server
- **PersistentKeepalive**: `15` seconds - Keeps connection alive
- **AllowedIPs**: Split-tunnel configuration (excludes `172.32.0.206/32`)

**Split-Tunnel Behavior:**
- Routes all traffic through VPN **except** LAN scanner IP
- Ensures plugin downloads use VPN
- Allows scanners to reach LAN targets directly

### VPN Gateway Environment Variables

**Required Variables:**

```bash
VPN_SERVICE_PROVIDER=custom          # Use custom WireGuard config
VPN_TYPE=wireguard                   # WireGuard protocol
WIREGUARD_CONF_SECRETFILE=/gluetun/wg0.conf  # Config file path
FIREWALL=on                          # Enable kill switch + NAT
FIREWALL_OUTBOUND_SUBNETS=172.30.0.0/24,192.168.100.0/24  # Allow Docker networks
```

**Firewall Behavior:**
- Blocks all traffic if VPN drops (kill switch)
- Automatically creates MASQUERADE rules for scanner subnets
- Allows outbound traffic from Docker networks

## Persistent Volumes

### Scanner Data Volumes

**Volume Names:**
- `nessus_data_1` - Scanner 1 persistent storage
- `nessus_data_2` - Scanner 2 persistent storage

**Volume Type:** External (created outside docker-compose)

**Contents:**
- Scanner activation license
- Plugin database
- Scan configurations
- Scan history and results
- User accounts and settings

### Creating Volumes (First-Time Setup)

```bash
# Create external volumes
docker volume create nessus_data_1
docker volume create nessus_data_2

# Verify volumes exist
docker volume ls | grep nessus_data
```

### Volume Backup

```bash
# Backup scanner data
docker run --rm \
  -v nessus_data_1:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/nessus-scanner1-$(date +%Y%m%d).tar.gz -C /data .

# Restore scanner data
docker run --rm \
  -v nessus_data_1:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/nessus-scanner1-YYYYMMDD.tar.gz -C /data
```

## Container Configuration

### Scanner Container Details

**Image**: `tenable/nessus:latest-ubuntu`
**Capabilities**: `NET_ADMIN` (required for routing manipulation)
**Restart Policy**: `unless-stopped`

**Startup Commands:**

```bash
# 1. Remove any macvlan default route (if present)
route del default gw 192.168.100.1 2>/dev/null || true

# 2. Set VPN gateway as default route
route add default gw 172.30.0.2 eth0

# 3. Add LAN subnet direct routing
ip route add 172.32.0.0/24 via 172.30.0.1 dev eth0

# 4. Start Nessus service
/opt/nessus/sbin/nessusctl start
```

**Why NET_ADMIN Capability?**
Scanner containers need `NET_ADMIN` to manipulate routing tables at startup. This allows forcing VPN routing while preserving LAN access.

### VPN Gateway Container Details

**Image**: `qmcgaw/gluetun:latest`
**Capabilities**: `NET_ADMIN` (required for VPN tunnel and NAT)
**Restart Policy**: `unless-stopped`

**Key Functions:**
1. Establishes WireGuard VPN tunnel
2. Creates NAT/MASQUERADE rules for scanners
3. Provides kill switch (blocks traffic if VPN fails)
4. DNS forwarding from VPN

## NAT/Firewall Rules

### VPN Gateway NAT (Automatic)

Gluetun automatically creates these iptables rules:

```bash
# MASQUERADE scanner traffic through VPN
iptables -t nat -A POSTROUTING -s 172.30.0.0/24 -o tun0 -j MASQUERADE
iptables -t nat -A POSTROUTING -s 192.168.100.0/24 -o tun0 -j MASQUERADE
```

### Docker Port Forwarding (NORMAL Mode)

Docker automatically creates these iptables rules when ports are published:

```bash
# Port forwarding (NORMAL mode only)
iptables -t nat -A DOCKER -p tcp --dport 8834 -j DNAT --to-destination 172.30.0.3:8834
iptables -t nat -A DOCKER -p tcp --dport 8835 -j DNAT --to-destination 172.30.0.4:8834
```

**UPDATE Mode:** These rules are **removed** (no port forwarding).

## Environment Variables

### Required Variables

**VPN Configuration:**
- `VPN_SERVICE_PROVIDER=custom`
- `VPN_TYPE=wireguard`
- `WIREGUARD_CONF_SECRETFILE=/gluetun/wg0.conf`

**Firewall Settings:**
- `FIREWALL=on`
- `FIREWALL_OUTBOUND_SUBNETS=172.30.0.0/24,192.168.100.0/24`

**Scanner Activation:**
- `ACTIVATION_CODE_1` - Scanner 1 license key
- `ACTIVATION_CODE_2` - Scanner 2 license key

### Setting Environment Variables

Create `.env` file in deployment directory:

```bash
# .env file
ACTIVATION_CODE_1=XXXX-XXXX-XXXX-XXXX
ACTIVATION_CODE_2=YYYY-YYYY-YYYY-YYYY
```

Docker Compose automatically loads `.env` file from the same directory.

## Verification Commands

### Check Container IPs

```bash
# Scanner 1 IP
docker inspect nessus-pro-1 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'

# Scanner 2 IP
docker inspect nessus-pro-2 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'

# VPN Gateway IP
docker inspect vpn-gateway-shared --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'
```

### Check Routing Tables

```bash
# Scanner 1 routing
docker exec nessus-pro-1 ip route show

# Expected output:
# default via 172.30.0.2 dev eth0
# 172.30.0.0/24 dev eth0 scope link
# 172.32.0.0/24 via 172.30.0.1 dev eth0
```

### Check VPN Connection

```bash
# VPN exit IP
docker exec vpn-gateway-shared wget -qO- https://api.ipify.org
# Expected: 62.84.100.88

# VPN tunnel status
docker exec vpn-gateway-shared wg show
```

### Check NAT Rules

```bash
# VPN gateway NAT rules
docker exec vpn-gateway-shared iptables -t nat -L POSTROUTING -n -v

# Expected: MASQUERADE rules for 172.30.0.0/24

# Host port forwarding (NORMAL mode only)
sudo iptables -t nat -L DOCKER -n | grep 8834
# Expected (NORMAL): DNAT rules for ports 8834/8835
# Expected (UPDATE): No output
```

## See Also

- **[README.md](./README.md)** - Main deployment documentation
- **[MODE_SWITCHING_GUIDE.md](./MODE_SWITCHING_GUIDE.md)** - Mode switching procedures
- **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** - Architecture rationale
