# Final Root Cause Analysis - Scanner 2 Activation Failure

## Executive Summary

**Scanner 2 HAS correct routing** (via VPN gateway 172.30.0.2) **BUT still cannot reach plugins.nessus.org**

This rules out routing misconfiguration and points to one of three possible causes:
1. **VPN Gateway firewall** blocking Scanner 2's traffic
2. **Activation code already used** (code was used on old Scanner 2 instance)
3. **Tenable rate limiting** from VPN IP address

---

## Detailed Findings

### Routing Analysis

| Container | Default Gateway | Status | Internet Access |
|-----------|----------------|--------|-----------------|
| Scanner 1 (nessus-pro-1) | 172.30.0.2 (VPN) | ✓ Correct | ✓ **Working** |
| Scanner 2 (nessus-pro-2) | 172.30.0.2 (VPN) | ✓ Correct | ✗ **Failing** |
| Debug Scanner | 192.168.100.1 (LAN) | ✗ Wrong | ✗ Failing |

**Key Insight:** Scanner 2 routing is **IDENTICAL** to Scanner 1 routing, yet Scanner 2 cannot connect to Tenable servers.

### Error Evidence

From Scanner 2 logs (`/opt/nessus/var/nessus/logs/backend.log`):
```
[error] Could not connect to plugins.nessus.org
[error] Nessus Plugins: Failed to send HTTP request to plugins.nessus.org
[error] Failed to register plugin feed
```

### Network Configuration Comparison

#### Scanner 1 (Working) ✓
```
VPN Network: 172.30.0.3/24 (eth0)
LAN Network: 192.168.100.9/24 (eth1)
Default Route: 172.30.0.2 via eth0
DNS: 172.30.0.2
Activation Code: 8WVN-N99G-LHTF-TQ4D-LTAX
Status: ready, fully functional
Plugin Set: 202511060226 (up to date)
```

#### Scanner 2 (Not Working) ✗
```
VPN Network: 172.30.0.4/24 (eth0)
LAN Network: 192.168.100.10/24 (eth1)
Default Route: 172.30.0.2 via eth0 (SAME AS SCANNER 1)
DNS: 172.30.0.2
Activation Code: YGHZ-GELQ-RNZX-QSSH-4XD5
Status: register (stuck, waiting for activation)
Plugin Set: None
Error: Cannot connect to plugins.nessus.org
```

---

## Possible Root Causes (Ranked by Likelihood)

### 1. Activation Code Already Used ⭐ **MOST LIKELY**

**Evidence:**
- We deleted and recreated Scanner 2 with fresh volume
- Activation code `YGHZ-GELQ-RNZX-QSSH-4XD5` was used in previous Scanner 2 instance
- Tenable only allows one scanner per activation code
- Scanner 1's code works fine

**Solution:**
- Get a new activation code from https://www.tenable.com/products/nessus/nessus-essentials
- Use new code to activate Scanner 2

**Test:**
```bash
# Try activating Scanner 2 with Scanner 1's code temporarily
docker exec nessus-pro-2 /opt/nessus/sbin/nessuscli fetch --register 8WVN-N99G-LHTF-TQ4D-LTAX
# If this works, it confirms the old code was the issue
```

### 2. VPN Gateway Firewall Rules

**Evidence:**
- Scanner 1 works, Scanner 2 doesn't (same routing)
- VPN gateway may have connection tracking or NAT rules that remember Scanner 1's IP
- Scanner 2 was created AFTER initial VPN setup

**Solution:**
```bash
cd /home/nessus/docker/nessus-shared
docker compose restart vpn-gateway
sleep 30
docker compose restart nessus-pro-2
# Wait 2 minutes, then retry activation
```

### 3. Tenable Rate Limiting / IP Block

**Evidence:**
- Multiple failed activation attempts from same VPN IP
- Both scanners share same public IP (62.84.100.88 via VPN)
- Tenable may rate-limit or block multiple activations from same IP

**Solution:**
- Wait 24 hours before retrying
- Or temporarily disconnect VPN and activate directly

---

## Debug Scanner Issue (Separate Problem)

The debug scanner has **incorrect routing** because the startup script had a chicken-and-egg problem:

1. Container starts without `net-tools` installed
2. Tries to run `route` command → fails (command not found)
3. Tries to `apt-get install net-tools` → needs internet
4. Internet doesn't work because routing wasn't fixed
5. Gets stuck in loop

**Fix:** Pre-install routing tools in Docker image before trying to modify routes.

---

## Recommended Action Plan

### Option A: Get New Activation Code (Recommended)
1. Visit https://www.tenable.com/products/nessus/nessus-essentials
2. Register for new free activation code
3. Use new code in Scanner 2 web UI
4. Wait 5-10 minutes for plugin download

### Option B: Copy Plugins from Scanner 1 (Workaround)
```bash
cd /home/nessus/docker/nessus-shared
docker compose stop nessus-pro-1 nessus-pro-2

# Copy plugins
docker run --rm \
  -v nessus_data:/source \
  -v nessus_data_2:/dest \
  alpine sh -c "cp -r /source/var/nessus/plugins /dest/var/nessus/"

docker compose start nessus-pro-1 nessus-pro-2
```

**Note:** Scanner 2 will work for scanning but won't receive plugin updates.

### Option C: Test with Scanner 1's Code (Diagnostic)
```bash
# This will deactivate Scanner 1, so only do this for testing
docker exec nessus-pro-2 /opt/nessus/sbin/nessuscli fetch --register 8WVN-N99G-LHTF-TQ4D-LTAX
```

If this works, it confirms Scanner 2's activation code is the issue.

---

## Why Scanner 1 Works But Scanner 2 Doesn't

Despite **identical** network configuration, Scanner 1 works because:
1. ✓ It was activated when first created (before volume was ever deleted)
2. ✓ Its activation code is valid and registered with Tenable
3. ✓ Plugins are already downloaded (202511060226)
4. ✓ It can access update servers for future updates

Scanner 2 fails because:
1. ✗ Volume was deleted, losing activation data
2. ✗ Activation code may have been "consumed" by previous instance
3. ✗ No plugins downloaded
4. ✗ Cannot reach Tenable servers to activate/download

---

## Files Created During Investigation

- `/home/nessus/projects/nessus-api/SCANNER2_ACTIVATION_FAILURE_ANALYSIS.md` - Initial analysis
- `/home/nessus/projects/nessus-api/check_routing.sh` - Routing comparison script
- `/home/nessus/projects/nessus-api/FINAL_ROOT_CAUSE_ANALYSIS.md` - This file
- `/home/nessus/docker/nessus-shared/docker-compose.yml` - Updated with debug-scanner

## Logs for Reference

```bash
# Scanner 2 activation attempts
docker exec nessus-pro-2 tail -100 /opt/nessus/var/nessus/logs/backend.log | grep -i "error\|fail"

# VPN gateway status
docker logs vpn-gateway-shared | tail -50

# Routing tables
./check_routing.sh
```
