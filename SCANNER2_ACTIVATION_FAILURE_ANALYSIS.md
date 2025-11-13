# Scanner 2 Activation Failure - Root Cause Analysis

## Summary
Scanner 2 activation failed because it **cannot establish network connectivity** to `plugins.nessus.org` to download the plugin feed and complete registration.

## Error Evidence from Logs

From `/opt/nessus/var/nessus/logs/backend.log`:

```
[12/Nov/2025:07:59:23 -0500] [error] [http] [username=nessus_ms_agent, request_id=mug/1762952353:0:53] Could not connect to plugins.nessus.org
[12/Nov/2025:07:59:23 -0500] [error] [http] [username=nessus_ms_agent, request_id=mug/1762952353:0:53] Nessus Plugins: Failed to send HTTP request to plugins.nessus.org
[12/Nov/2025:07:59:23 -0500] [error] [http] [username=nessus_ms_agent, request_id=mug/1762952353:0:53] Failed to register plugin feed
[12/Nov/2025:07:59:41 -0500] [error] [http] [username=nessus_ms_agent, request_id=mug/1762952371:0:55] Could not connect to plugins.nessus.org
```

## What Happened During Activation

1. **User entered activation code** `YGHZ-GELQ-RNZX-QSSH-4XD5` in Scanner 2 web UI
2. **Nessus attempted to connect** to `plugins.nessus.org` to:
   - Validate the activation code
   - Download the plugin feed (~200MB)
   - Register the scanner
3. **Connection failed** - Scanner could not reach Tenable's servers
4. **Result:** "Activation failed" error message

## Network Configuration Analysis

### Routing Table (Identical for Both Scanners)
```
Default Gateway: 172.30.0.2 (VPN gateway)
Local Network: 172.30.0.0/24 (VPN network)
Local Network: 192.168.100.0/24 (macvlan)
```

### DNS Configuration (Identical for Both Scanners)
```
nameserver 127.0.0.11 (Docker DNS)
ExtServers: [172.30.0.2] (VPN gateway as DNS forwarder)
```

### VPN Gateway Status
- Container: `vpn-gateway-shared` - Running and HEALTHY
- VPN Connection: Connected to WireGuard endpoint
- Public IP: 62.84.100.88 (Netherlands)
- Routing: Configured for subnets 172.30.0.0/24, 192.168.100.0/24, 172.32.0.0/24

## Scanner Comparison

### Scanner 1 (172.30.0.3:8834) ✓ WORKING
- Status: `ready`
- License Type: `home` (Nessus Essentials)
- Plugin Set: `202511060226`
- Feed Status: `ready (100%)`
- **Successfully registered and operational**

### Scanner 2 (172.30.0.4:8834) ❌ NOT WORKING
- Status: `register` (stuck waiting for registration)
- License Type: `unknown`
- Plugin Set: `None`
- Feed Status: `ready (100%)` but no plugins downloaded
- **Cannot connect to plugins.nessus.org**

## Possible Root Causes

### 1. **VPN Gateway Not Routing for Scanner 2** (Most Likely)
- Scanner 2 was created AFTER initial VPN gateway setup
- VPN gateway may need restart to recognize new container
- Firewall rules may not include Scanner 2's traffic

### 2. **Activation Code Already Used**
- Activation code `YGHZ-GELQ-RNZX-QSSH-4XD5` may have been used on previous Scanner 2 instance
- Tenable only allows one scanner per activation code
- Scanner 1's code `8WVN-N99G-LHTF-TQ4D-LTAX` is working

### 3. **DNS Resolution Failure**
- Scanner 2 cannot resolve `plugins.nessus.org` hostname
- VPN gateway DNS forwarding not working for Scanner 2

### 4. **Tenable Server Block**
- Multiple failed activation attempts may have triggered rate limiting
- Same IP (via VPN) trying to activate multiple scanners

## Recommended Solutions (in order)

### Solution 1: Restart VPN Gateway (Quick Fix)
```bash
cd /home/nessus/docker/nessus-shared
docker compose restart vpn-gateway
# Wait 30 seconds for VPN to reconnect
docker compose restart nessus-pro-2
# Wait 2 minutes, then try activation again in web UI
```

### Solution 2: Use Scanner 1's Plugins (Workaround)
Since Scanner 1 is fully registered with plugins, copy its data:
```bash
# Stop both scanners
docker compose stop nessus-pro-1 nessus-pro-2

# Copy plugins from Scanner 1 to Scanner 2
docker run --rm \
  -v nessus_data:/source \
  -v nessus_data_2:/dest \
  alpine sh -c "cp -r /source/var/nessus/plugins /dest/var/nessus/"

# Restart scanners
docker compose start nessus-pro-1 nessus-pro-2
```

**Note:** This gives Scanner 2 offline scanning capability but it won't receive updates.

### Solution 3: Try Different Activation Method
Register via command line instead of web UI:
```bash
docker exec nessus-pro-2 /opt/nessus/sbin/nessuscli fetch --register YGHZ-GELQ-RNZX-QSSH-4XD5
docker exec nessus-pro-2 /opt/nessus/sbin/nessuscli update --all
```

### Solution 4: Use Scanner Without Registration (Testing Only)
Scanner 2 can still perform scans using cached plugins (if copied from Scanner 1), but:
- No plugin updates
- Limited license features
- Not recommended for production

### Solution 5: Get New Activation Code
If `YGHZ-GELQ-RNZX-QSSH-4XD5` is invalid/used:
- Visit https://www.tenable.com/products/nessus/nessus-essentials
- Register for a new free activation code
- Use new code to activate Scanner 2

## Next Steps

1. **Try Solution 1 first** (restart VPN gateway)
2. **Monitor logs** during next activation attempt
3. **If still fails**, proceed to Solution 2 (copy plugins)
4. **Report findings** back for further troubleshooting

## Log Monitoring Commands

```bash
# Watch Scanner 2 logs in real-time
docker logs -f nessus-pro-2

# Check backend log for errors
docker exec nessus-pro-2 tail -f /opt/nessus/var/nessus/logs/backend.log | grep -i "error\|fail"

# Check VPN gateway logs
docker logs -f vpn-gateway-shared
```
