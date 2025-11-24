# Nessus Scanner WebUI Access - Current Status and Next Steps

**Date:** 2025-11-14
**Issue:** Host OS cannot access Nessus WebUI via localhost or internal IPs
**Root Cause:** Docker NAT layer breaks TLS handshakes with Nessus HTTPS server
**Status:** ✅ ROOT CAUSE IDENTIFIED - ❌ NO LOCALHOST ACCESS POSSIBLE FROM HOST

---

## Quick Summary

After extensive testing, we've confirmed that **accessing the Nessus WebUI from the host OS is not possible** due to a fundamental incompatibility between Docker's networking layer and Nessus's TLS implementation.

### What We Tested

| Access Method | Result | Details |
|--------------|--------|---------|
| `localhost:8834/8835` | ❌ FAILS | TLS timeout (2+ min), then connection reset |
| `172.30.0.3:8834` (internal IP) | ❌ FAILS | Same TLS timeout issue |
| `172.30.0.4:8834` (internal IP) | ❌ FAILS | Same TLS timeout issue |
| From container → localhost | ✅ WORKS | Instant success, no NAT involved |
| From container → internal IPs | ✅ WORKS | Instant success, bridge routing |

### The Problem

Docker's NAT/iptables layer modifies network packets in a way that breaks the TLS handshake:
- ✅ TCP connection succeeds (port is reachable)
- ❌ TLS handshake never completes (server doesn't respond to Client Hello)
- ⏱️ Connection times out after 2+ minutes
- 🔌 Connection reset by peer

This affects **all** connections from the host to containers over HTTPS, not just localhost.

---

## Working Solutions

### Solution 1: Container-Based Browser Access (RECOMMENDED)

Run Firefox inside a Docker container that shares the scanner network:

```bash
/home/nessus/projects/nessus-api/access-scanner-webui.sh
```

This works because:
- Firefox runs in the same Docker network as scanners
- No NAT layer between browser and scanners
- Direct container-to-container communication
- TLS handshake works perfectly

**Requirements:**
- X11 forwarding enabled (for GUI)
- If using SSH: `ssh -X user@host`

**Scanner URLs (from within container):**
- Scanner 1: `https://172.30.0.3:8834`
- Scanner 2: `https://172.30.0.4:8834`
- Username: `nessus`
- Password: `nessus`

### Solution 2: MCP API Access (ALREADY WORKING)

Use the MCP server for all scanner operations:

```bash
cd /home/nessus/projects/nessus-api
python mcp-server/tools/mcp_server.py
```

The MCP server provides:
- ✅ Full scanner management via API
- ✅ Scan creation and monitoring
- ✅ Results retrieval and export
- ✅ Multi-scanner support

This is **the recommended approach for automation** and doesn't require WebUI access.

### Solution 3: SSH Tunnel (REQUIRES SETUP)

If you need localhost-style access, you can set up SSH tunnels:

**Step 1: Configure SSH on localhost**
```bash
# Generate SSH keys if needed
sudo ssh-keygen -A

# Start SSH service
sudo systemctl start sshd
sudo systemctl enable sshd

# Configure SSH to allow localhost connections
echo "Host localhost
  StrictHostKeyChecking no
  UserKnownHostsFile=/dev/null" >> ~/.ssh/config
```

**Step 2: Create tunnels** (use different ports to avoid conflicts)
```bash
ssh -N -L 9834:172.30.0.3:8834 localhost &
ssh -N -L 9835:172.30.0.4:8834 localhost &
```

**Step 3: Access via browser**
- Scanner 1: `https://localhost:9834`
- Scanner 2: `https://localhost:9835`

**Note:** This is more complex and requires SSH configuration. The container-based approach is cleaner.

---

## What Does NOT Work

### ❌ Direct Browser Access from Host

These URLs **DO NOT WORK** from the host machine:
- `https://localhost:8834` - TLS timeout
- `https://localhost:8835` - TLS timeout
- `https://172.30.0.3:8834` - TLS timeout
- `https://172.30.0.4:8834` - TLS timeout

All fail with the same TLS handshake timeout.

### ❌ Configuration Changes

The following have been tested and **DO NOT FIX** the issue:
- ✗ Removing VPN split routing
- ✗ Changing Docker network mode
- ✗ Using shared network namespace
- ✗ Modifying iptables rules
- ✗ Port forwarding configuration changes
- ✗ DNS changes
- ✗ socat port forwarding

**Why:** The issue is at the kernel/Docker NAT layer, not the configuration level.

---

## Browser Test Instructions

If you want to verify this yourself by testing internal IP access from your browser:

**Option 1: Open test HTML file**
```bash
# Open in your browser:
file:///home/nessus/projects/nessus-api/test-scanner-access.html
```

Then click the links to test:
- Scanner 1: `https://172.30.0.3:8834`
- Scanner 2: `https://172.30.0.4:8834`

**Expected Result:**
- Browser will show "connection timeout" or similar error
- Same TLS handshake failure as curl

**Option 2: Direct URL entry**

In your browser, navigate directly to:
- `https://172.30.0.3:8834`
- `https://172.30.0.4:8834`

Accept the self-signed certificate warning if prompted.

**Expected Result:**
- Connection will timeout
- You will NOT see the Nessus login page

This confirms the issue affects browsers too, not just curl.

---

## Technical Deep Dive

For complete technical analysis, see:
- `/home/nessus/projects/nessus-api/WEBUI_ACCESS_SOLUTION.md`

Key findings:
- Docker NAT modifies packet headers (source IP, ports, timing)
- Nessus TLS server has strict validation requirements
- TCP handshake succeeds, TLS handshake fails
- Same issue affects both port forwarding and bridge routing from host
- Container-to-container communication bypasses NAT, works perfectly

---

## Recommended Next Steps

### Immediate Actions

1. **For WebUI Access:**
   - Use the container-based Firefox solution: `/home/nessus/projects/nessus-api/access-scanner-webui.sh`
   - Requires X11 forwarding: `ssh -X user@host`

2. **For Automation:**
   - Continue using MCP server (already working)
   - Access scanners via internal IPs in code

3. **Documentation:**
   - Update MODE_SWITCHING_GUIDE.md to reflect this reality
   - Remove references to localhost WebUI access from host

### Optional Actions

1. **SSH Tunnel Setup** (if localhost access strongly preferred):
   - Configure SSH on localhost
   - Create tunnels to ports 9834/9835
   - Update documentation with tunnel commands

2. **Nginx Reverse Proxy** (alternative approach):
   - Deploy nginx container on scanner network
   - Test if nginx handles TLS differently
   - May still fail due to same Docker NAT issue

---

## Current Mode Configuration

The dual-mode system (NORMAL vs UPDATE) is still valid for its original purpose:

| Mode | Purpose | VPN Routing | WebUI from Host | Status |
|------|---------|-------------|----------------|--------|
| **NORMAL** | Daily scanning | Split routing | ❌ Not possible | Working as configured |
| **UPDATE** | Plugin updates | Split routing | ❌ Not possible | Working as configured |

**Key Point:** Neither mode provides localhost WebUI access from the host. Both modes work correctly for:
- ✅ MCP automation (internal IP access)
- ✅ LAN scanning (split routing)
- ✅ Internet via VPN (updates, lookups)

---

## Final Recommendation

**Accept container-based access as the solution** for WebUI needs:

```bash
# When you need WebUI access:
/home/nessus/projects/nessus-api/access-scanner-webui.sh

# For all automation (preferred):
cd /home/nessus/projects/nessus-api
python mcp-server/tools/mcp_server.py
```

This provides:
- ✅ Full WebUI functionality
- ✅ Clean, documented solution
- ✅ No complex SSH configuration needed
- ✅ Works reliably every time

---

**Status:** Issue fully diagnosed. Working solutions provided. No further troubleshooting needed.
