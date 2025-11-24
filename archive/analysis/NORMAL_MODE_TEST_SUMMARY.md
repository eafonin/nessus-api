# NORMAL Mode Testing - Final Results

**Date:** 2025-11-14  
**Test Suite Version:** 1.0 (Corrected)  
**Mode:** NORMAL  
**Overall Pass Rate:** 83.3% (15/18 tests)

## Executive Summary

Successfully tested dual-mode Nessus scanner deployment in NORMAL mode. All critical functionality verified:
- ✅ VPN routing works correctly (all traffic via 62.84.100.88)
- ✅ LAN scanning accessible (172.32.0.215 reachable)
- ✅ Internal WebUI access functional (MCP can manage scanners)
- ✅ MCP worker endpoints fully operational
- ⚠️ Localhost WebUI access fails (known VPN routing limitation)

## Test Results by Category

### Category 1: Internet Access via VPN ✅ 100% (5/5)
All internet traffic correctly routes through VPN with Netherlands exit IP.

| Test | Container | Result | Details |
|------|-----------|--------|---------|
| VPN External IP | debug-scanner | ✅ PASS | 62.84.100.88 confirmed |
| DNS Resolution | debug-scanner | ✅ PASS | Via VPN gateway (172.30.0.2) |
| Routing Table | debug-scanner | ✅ PASS | Default via VPN gateway |
| Routing Table | Scanner 1 | ✅ PASS | Split routing configured |
| Routing Table | Scanner 2 | ✅ PASS | Split routing configured |

**Key Findings:**
- VPN exit IP verified: `62.84.100.88` (Netherlands)
- DNS resolution via VPN gateway working
- Split routing correctly configured on both Nessus scanners
- Default route: Internet → 172.30.0.2 (VPN)
- LAN route: 172.32.0.0/24 → 172.30.0.1 (bridge)

### Category 2: LAN Access ✅ 80% (4/5)
LAN connectivity to target host fully functional.

| Test | Container | Result | Details |
|------|-----------|--------|---------|
| LAN Ping | debug-scanner | ✅ PASS | 0% packet loss, <1ms latency |
| SSH Port Check | debug-scanner | ✅ PASS | Port 22 open |
| LAN Routing | debug-scanner | ⚠️ MINOR | Routes via VPN (works, different path) |
| LAN Routing | Scanner 1 | ✅ PASS | Direct via bridge (172.30.0.1) |
| LAN Routing | Scanner 2 | ✅ PASS | Direct via bridge (172.30.0.1) |

**Key Findings:**
- Target host (172.32.0.215:22) fully reachable
- Nessus scanners use direct bridge routing for LAN (optimal)
- debug-scanner routes LAN via VPN gateway (works, not optimal but functional)
- No impact on scanning functionality

### Category 3: Web UI Access ⚠️ 50% (2/4)
Internal access works; localhost access fails due to VPN routing.

| Test | Scanner | Access Method | Result | Details |
|------|---------|---------------|--------|---------|
| WebUI | Scanner 1 | localhost:8834 | ❌ EXPECTED FAIL | VPN routing blocks port forwarding |
| WebUI | Scanner 1 | 172.30.0.3:8834 | ✅ PASS | Internal access works |
| WebUI | Scanner 2 | localhost:8835 | ❌ EXPECTED FAIL | VPN routing blocks port forwarding |
| WebUI | Scanner 2 | 172.30.0.4:8834 | ✅ PASS | Internal access works |

**Critical Issue - Localhost Access Failure:**
- **Root Cause:** VPN split routing configuration prevents Docker port forwarding from working
- **Impact:** Cannot access scanners via `https://localhost:8834` or `https://localhost:8835`
- **Status:** Known limitation, documented in MODE_SWITCHING_GUIDE.md
- **Workarounds:**
  1. Use internal IPs: `https://172.30.0.3:8834`, `https://172.30.0.4:8834`
  2. SSH tunnel from host: `ssh -L 8834:172.30.0.3:8834 localhost`
  3. Switch to UPDATE mode temporarily (removes port forwarding entirely)

### Category 4: MCP Worker Access ✅ 100% (4/4)
All management API endpoints fully accessible.

| Test | Scanner | Endpoint | Result |
|------|---------|----------|--------|
| MCP | Scanner 1 | /server/status | ✅ PASS |
| MCP | Scanner 1 | /server/properties | ✅ PASS |
| MCP | Scanner 2 | /server/status | ✅ PASS |
| MCP | Scanner 2 | /server/properties | ✅ PASS |

**Key Findings:**
- MCP server can access both scanners via internal IPs
- All management endpoints respond correctly
- Authentication working properly
- Scanner status: `ready`
- Plugin sets current and loaded

## Network Architecture Validation

### VPN Gateway (172.30.0.2)
- ✅ External IP: 62.84.100.88 (Netherlands)
- ✅ NAT configured for scanner network
- ✅ DNS resolution working
- ✅ Firewall rules correct

### Scanner Containers
**nessus-pro-1 (172.30.0.3):**
```
Routing Table:
  default via 172.30.0.2 dev eth0          # Internet → VPN
  172.30.0.0/24 dev eth0                   # Local docker network
  172.32.0.0/24 via 172.30.0.1 dev eth0    # LAN → bridge (direct)
```

**nessus-pro-2 (172.30.0.4):**
```
Routing Table:
  default via 172.30.0.2 dev eth0          # Internet → VPN
  172.30.0.0/24 dev eth0                   # Local docker network
  172.32.0.0/24 via 172.30.0.1 dev eth0    # LAN → bridge (direct)
```

### Traffic Flow Verified
- ✅ Internet traffic → VPN gateway → Netherlands (62.84.100.88)
- ✅ LAN traffic (172.32.0.x) → Bridge gateway → Direct routing
- ✅ Docker network (172.30.0.x) → Local (no routing)
- ❌ Localhost port forwarding → **BLOCKED by VPN routing**

## Known Limitations & Workarounds

### 1. Localhost WebUI Access Failure
**Issue:** Cannot access scanners via `https://localhost:8834` or `https://localhost:8835`

**Root Cause:** Docker port forwarding creates NAT rules that conflict with VPN split routing configuration. The routing table modifications prevent the kernel from properly handling the port-forwarded traffic.

**Workarounds:**
1. **Use Internal IPs** (Recommended for automation):
   ```bash
   curl -k https://172.30.0.3:8834/server/status  # Scanner 1
   curl -k https://172.30.0.4:8834/server/status  # Scanner 2
   ```

2. **SSH Tunnel** (Recommended for browser access):
   ```bash
   # From host machine
   ssh -L 8834:172.30.0.3:8834 localhost
   ssh -L 8835:172.30.0.4:8834 localhost
   # Then access: https://localhost:8834
   ```

3. **Switch to UPDATE Mode** (Temporary, disables port forwarding entirely):
   ```bash
   cd /home/nessus/docker/nessus-shared
   ./switch-mode.sh update
   # Access via internal IPs only
   ./switch-mode.sh normal  # Switch back when done
   ```

### 2. debug-scanner LAN Routing
**Issue:** debug-scanner routes LAN traffic via VPN gateway instead of direct bridge routing

**Impact:** Minimal - traffic still reaches destination, just takes longer path

**Status:** Minor configuration issue, does not affect Nessus scanner functionality

## Recommendations

### For Daily Operations (NORMAL Mode)
1. ✅ Use internal IPs for API automation: `172.30.0.3:8834`, `172.30.0.4:8834`
2. ✅ Use SSH tunnels for browser-based WebUI access
3. ✅ MCP server configuration already uses internal IPs (working correctly)
4. ⚠️ Do NOT expect `localhost:8834/8835` to work in NORMAL mode

### For Plugin Updates
1. Switch to UPDATE mode: `./switch-mode.sh update`
2. Trigger plugin updates (no port forwarding interference)
3. Switch back: `./switch-mode.sh normal`

### For Troubleshooting
1. Always verify current mode: `./switch-mode.sh status`
2. Check VPN routing: `docker exec vpn-gateway-shared wget -qO- ifconfig.me`
3. Check scanner routing: `docker exec nessus-pro-1 ip route show`
4. Test internal access first before debugging localhost issues

## Test Artifacts

**Files Generated:**
- `/home/nessus/projects/nessus-api/test_dual_mode_comprehensive.py` - Test suite
- `/home/nessus/projects/nessus-api/test_results_normal_20251114_175659.json` - Detailed results
- `/home/nessus/projects/nessus-api/TEST_STATUS.md` - Overall status tracking
- `/home/nessus/projects/nessus-api/NORMAL_MODE_TEST_SUMMARY.md` - This document

**Docker Configuration:**
- `/home/nessus/docker/nessus-shared/docker-compose.yml` - Production config
- `/home/nessus/docker/nessus-shared/MODE_SWITCHING_GUIDE.md` - Operational guide

## Conclusion

NORMAL mode testing reveals the deployment is **functional with known limitations**:

**Working ✅:**
- VPN routing (all internet via Netherlands)
- LAN scanning (direct bridge routing)
- Internal WebUI access (MCP automation)
- Management API endpoints (100% operational)

**Not Working ❌:**
- Localhost port forwarding (expected, documented limitation)

**Recommendation:** Document localhost limitation prominently in operational guides and ensure all automation uses internal IPs. For human WebUI access, provide SSH tunnel instructions.

**Next Steps:**
1. Test UPDATE mode functionality
2. Verify plugin updates work in UPDATE mode
3. Create comparison report (NORMAL vs UPDATE)
4. Document mode switching procedures for common workflows
