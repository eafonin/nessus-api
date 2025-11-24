# Mode Compatibility Analysis - Shared Network Namespace vs NORMAL/UPDATE Modes

**Date:** 2025-11-14
**Issue:** Are NORMAL/UPDATE modes compatible with shared network namespace WebUI access?

---

## TL;DR - Compatibility Matrix

| Configuration | NORMAL Mode | UPDATE Mode | WebUI Access | VPN Routing | Status |
|--------------|-------------|-------------|--------------|-------------|---------|
| **Separate Network** | ✅ Compatible | ✅ Compatible | ❌ Fails (TLS) | ✅ Works | Current dual-mode |
| **Shared Network** | ⚠️ **INCOMPATIBLE** | ⚠️ **INCOMPATIBLE** | ✅ Works | ✅ Works | Current WebUI config |

**Conclusion:** Shared network namespace and NORMAL/UPDATE modes are **MUTUALLY EXCLUSIVE**.

---

## The Fundamental Conflict

### Shared Network Namespace Configuration

**How it works:**
```yaml
nessus-pro-1:
  network_mode: "service:vpn-gateway"  # Shares VPN gateway's network stack
```

**Network Stack:**
- Scanner container has **NO separate network namespace**
- Scanner uses **VPN gateway's network interfaces**
- Scanner uses **VPN gateway's routing table**
- Scanner **cannot modify routes independently**

### UPDATE Mode Requirements

**What UPDATE mode tries to do:**
```yaml
nessus-pro-1:
  cap_add:
    - NET_ADMIN  # Requires ability to modify routes
  command: >
    ip route del default &&      # Delete default route
    ip route add 172.32.0.0/24 via 172.30.0.1 dev eth0 &&  # Add LAN route
    ip route add default via 172.30.0.2 dev eth0            # Add VPN route
```

**The Problem:**
- When `network_mode: "service:vpn-gateway"`, scanner shares VPN gateway's network
- Scanner **cannot have separate routes** - it uses VPN gateway's routes
- `ip route` commands would modify **VPN gateway's routing**, breaking VPN gateway itself!
- UPDATE mode's routing commands are **impossible** in shared namespace

---

## Detailed Compatibility Analysis

### Configuration 1: Separate Network Namespace (Current Dual-Mode)

**Docker Config:**
```yaml
nessus-pro-1:
  networks:
    vpn_net:
      ipv4_address: 172.30.0.3
  ports:
    - "8834:8834"  # Port forwarding on scanner
```

**NORMAL Mode Compatibility:** ✅ **WORKS**
- Scanner has separate network namespace
- Can modify own routing table
- No VPN split routing configured (uses Docker default)
- Port forwarding configured
- **Issue:** WebUI TLS fails due to Docker NAT

**UPDATE Mode Compatibility:** ✅ **WORKS**
- Scanner has separate network namespace
- Can modify own routing table with `ip route` commands
- VPN split routing applied successfully
- Port forwarding removed
- **Issue:** WebUI TLS still fails (internal IPs also fail)

**VPN Routing:** ✅ Works in UPDATE mode
**WebUI Access:** ❌ Fails in both modes (Docker NAT breaks TLS)

### Configuration 2: Shared Network Namespace (Current WebUI Access)

**Docker Config:**
```yaml
vpn-gateway:
  ports:
    - "8834:8834"  # Port forwarding on VPN gateway

nessus-pro-1:
  network_mode: "service:vpn-gateway"  # Share VPN gateway's network
```

**NORMAL Mode Compatibility:** ⚠️ **INCOMPATIBLE**
- Scanner shares VPN gateway's network namespace
- **Cannot modify routes** - would affect VPN gateway
- No separate routing table to configure
- NORMAL mode expects **no VPN split routing**, but VPN gateway **already has** split routing!

**UPDATE Mode Compatibility:** ⚠️ **INCOMPATIBLE**
- Scanner shares VPN gateway's network namespace
- **Cannot execute `ip route` commands** independently
- Attempting to modify routes would **break VPN gateway**
- UPDATE mode's `command:` with routing changes would fail or corrupt VPN routing

**VPN Routing:** ⚠️ Inherited from VPN gateway (cannot be modified)
**WebUI Access:** ✅ Works (via host LAN IP)

---

## Why They Can't Coexist

### Technical Reasons

**1. Network Namespace Conflict**
```
Shared Namespace:
  Scanner and VPN gateway share ONE routing table
  ↓
  UPDATE mode tries to modify routing
  ↓
  Would break VPN gateway's routing
  ↓
  ❌ INCOMPATIBLE
```

**2. Capability Conflict**
```
Shared Namespace:
  Scanner has no separate network interfaces
  ↓
  UPDATE mode requires NET_ADMIN to modify routes
  ↓
  Would grant scanner control over VPN gateway's network
  ↓
  ⚠️ Security risk + Operational conflict
```

**3. Routing Inheritance**
```
VPN Gateway has routing:
  default via 172.30.0.2 (VPN)
  172.32.0.0/24 via 172.30.0.1 (LAN)
  ↓
  Scanner inherits these routes
  ↓
  NORMAL mode expects default Docker routing
  ↓
  ❌ Routes don't match mode expectations
```

---

## What This Means for Your Setup

### Current Reality

You **cannot have both**:
1. ✅ WebUI access via host LAN IP (requires shared namespace)
2. ✅ NORMAL/UPDATE mode switching (requires separate namespace)

**You must choose ONE:**

### Option A: Keep WebUI Access (Shared Namespace)

**Configuration:** Current setup
```bash
cd /home/nessus/docker/nessus-shared
docker compose -f docker-compose.yml -f docker-compose.old-working-test.yml up -d
```

**What You Get:**
- ✅ WebUI via `https://172.32.0.209:8834`
- ✅ VPN routing (inherited from VPN gateway)
- ✅ LAN scanning (inherited from VPN gateway)
- ❌ Cannot switch modes
- ❌ Cannot modify routing per scanner
- ❌ No separate scanner configurations

**When to use:** You primarily need WebUI access and don't need mode switching

### Option B: Keep NORMAL/UPDATE Modes (Separate Namespace)

**Configuration:** Original dual-mode setup
```bash
cd /home/nessus/docker/nessus-shared
docker compose up -d  # NORMAL mode
./switch-mode.sh update  # UPDATE mode
```

**What You Get:**
- ✅ Mode switching (NORMAL ↔ UPDATE)
- ✅ Independent routing per scanner
- ✅ VPN split routing in UPDATE mode
- ✅ MCP automation works
- ❌ No WebUI access via host LAN IP
- ❌ No WebUI access via localhost
- ⚠️ WebUI access only via container-based browser

**When to use:** You need mode switching for plugin updates, don't need host WebUI access

---

## Recommended Solution

### Hybrid Approach: Add Scanner 2 with Dual-Mode

**Keep Scanner 1 in shared namespace for WebUI:**
```yaml
nessus-pro-1:
  network_mode: "service:vpn-gateway"
  # No mode switching, always accessible via WebUI
```

**Keep Scanner 2 with dual-mode capability:**
```yaml
nessus-pro-2:
  networks:
    vpn_net:
      ipv4_address: 172.30.0.4
  ports:
    - "8835:8834"  # NORMAL mode (port forwarding)
  # Can switch to UPDATE mode when needed
```

**Benefits:**
- ✅ Scanner 1: WebUI access via `https://172.32.0.209:8834`
- ✅ Scanner 2: Mode switching capability
- ✅ Scanner 2: Plugin updates in UPDATE mode
- ✅ Both: LAN scanning
- ✅ Both: MCP automation

**Trade-offs:**
- Scanner 1 cannot switch modes (always has VPN routing)
- Scanner 2 has no WebUI access from host (use Scanner 1's WebUI)
- More complex configuration

---

## Technical Deep Dive: Why VPN Gateway Has Split Routing

### VPN Gateway Routing Table

The VPN gateway **already has** split routing configured:

```bash
# Check VPN gateway routing:
docker exec vpn-gateway-shared ip route show
```

**Expected output:**
```
default via [VPN tunnel IP] dev tun0       # Internet → VPN
172.30.0.0/24 dev eth0                     # Docker network
172.32.0.0/24 via 172.30.0.1 dev eth0      # LAN → bridge
```

**Why it has this:**
- Gluetun VPN client configures VPN routing automatically
- `FIREWALL_OUTBOUND_SUBNETS=172.30.0.0/24,172.32.0.0/24` tells Gluetun to route these LANs via bridge
- Everything else goes via VPN tunnel

### What Scanner Inherits (Shared Namespace)

When scanner uses `network_mode: "service:vpn-gateway"`:

```
Scanner's routing table = VPN gateway's routing table
  ↓
Scanner automatically has:
  - Internet → VPN ✅
  - LAN → bridge ✅
  - Docker network → bridge ✅
```

**This is why it works for LAN scanning and plugin updates!**

### Conflict with UPDATE Mode

UPDATE mode tries to configure these exact same routes:

```yaml
command: >
  ip route del default &&
  ip route add 172.32.0.0/24 via 172.30.0.1 dev eth0 &&
  ip route add default via 172.30.0.2 dev eth0
```

**Problem:** These routes **already exist** (inherited from VPN gateway)!

**If we ran this:**
1. `ip route del default` → Deletes VPN gateway's VPN route
2. VPN gateway loses internet access
3. All containers using VPN gateway lose internet
4. ❌ **Complete failure**

---

## Conclusion

### The Incompatibility is Fundamental

**Shared network namespace** and **independent routing per scanner** are mutually exclusive at the Docker/kernel level.

### Recommendation: Choose Based on Priority

**Priority #1: WebUI Access**
→ Use shared namespace (current working config)
→ Sacrifice mode switching
→ VPN routing inherited from gateway (works fine)

**Priority #2: Mode Switching**
→ Use separate namespace (original dual-mode)
→ Sacrifice WebUI access from host
→ Independent routing per scanner

**Priority #3: Both**
→ Use hybrid approach (Scanner 1 shared, Scanner 2 separate)
→ Scanner 1 for WebUI, Scanner 2 for mode switching
→ Most complex but most capable

---

## Next Steps

### If You Want to Keep WebUI Access

**No action needed** - current config works!

**Update documentation:**
- NORMAL/UPDATE modes not applicable with shared namespace
- VPN routing is always enabled (inherited from VPN gateway)
- Cannot switch modes with this configuration

### If You Want to Keep Mode Switching

**Revert to separate namespace:**
```bash
cd /home/nessus/docker/nessus-shared
docker compose up -d --force-recreate nessus-pro-1
```

**Accept limitation:**
- WebUI access only via container-based browser
- Use internal IPs from within containers

### If You Want Both

**Implement hybrid approach:**
- Keep Scanner 1 in shared namespace (WebUI access)
- Keep Scanner 2 in separate namespace (mode switching)
- Document which scanner to use for which purpose

---

**Last Updated:** 2025-11-14
**Status:** Analysis Complete
**Recommendation:** Choose based on priority - cannot have both WebUI access and mode switching on same scanner

---

## Related Documentation

**WebUI Access:**
- [WEBUI_ACCESS_SOLUTION_FINAL.md](WEBUI_ACCESS_SOLUTION_FINAL.md) - Current working solution (host LAN IP)
- [WEBUI_ACCESS_QUICKREF.md](WEBUI_ACCESS_QUICKREF.md) - Quick reference for daily use

**Recommendations:**
- [FINAL_MODE_RECOMMENDATION.md](FINAL_MODE_RECOMMENDATION.md) - Recommendation to keep shared namespace
- [PROXY_SOLUTION_ANALYSIS.md](PROXY_SOLUTION_ANALYSIS.md) - Alternative solution using reverse proxy

**Index:**
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Master index of all project documentation
