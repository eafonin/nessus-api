# Nessus MCP Project - Documentation Index

**Last Updated:** 2025-11-14
**Status:** Production Ready

---

## Quick Start

### Access Nessus WebUI
**URL:** https://172.32.0.209:8834
**Quick Ref:** [WEBUI_ACCESS_QUICKREF.md](WEBUI_ACCESS_QUICKREF.md)

### Run MCP Server
```bash
cd /home/nessus/projects/nessus-api
python mcp-server/tools/mcp_server.py
```

---

## Documentation Structure

### WebUI Access (NEW - 2025-11-14)

**Problem Solved:** Host-to-container WebUI access with Docker + VPN

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [WEBUI_ACCESS_SUMMARY.md](WEBUI_ACCESS_SUMMARY.md) | **Executive summary** | Quick overview, investigation timeline |
| [WEBUI_ACCESS_QUICKREF.md](WEBUI_ACCESS_QUICKREF.md) | Quick reference card | Daily WebUI access |
| [WEBUI_ACCESS_SOLUTION_FINAL.md](WEBUI_ACCESS_SOLUTION_FINAL.md) | Complete guide | Troubleshooting, understanding architecture |
| [docker-compose-webui-working.yml](docker-compose-webui-working.yml) | Working config override | Applying configuration |

**Key Finding:**
- ❌ `localhost:8834` doesn't work (Docker NAT breaks TLS)
- ✅ `https://172.32.0.209:8834` works (host LAN IP)
- Same access method as original working configuration

### Advanced Analysis (NEW - 2025-11-14)

**In-Depth Technical Analysis:**

| Document | Purpose | Key Insights |
|----------|---------|--------------|
| [MODE_COMPATIBILITY_ANALYSIS.md](MODE_COMPATIBILITY_ANALYSIS.md) | Shared namespace vs NORMAL/UPDATE modes | Mutual exclusivity explained |
| [FINAL_MODE_RECOMMENDATION.md](FINAL_MODE_RECOMMENDATION.md) | Recommended simplified architecture | Keep shared namespace, eliminate mode complexity |
| [PROXY_SOLUTION_ANALYSIS.md](PROXY_SOLUTION_ANALYSIS.md) | Reverse proxy solution design | Get localhost access + keep modes (not yet tested) |

**Key Findings:**
- Shared network namespace and NORMAL/UPDATE modes are fundamentally incompatible
- Cannot modify routing in shared namespace (would break VPN gateway)
- Reverse proxy solution could enable both WebUI + modes simultaneously
- Current recommendation: Keep shared namespace (simpler, works perfectly)

### Phase Documentation

| Phase | Document | Status |
|-------|----------|--------|
| Phase 0 | [PHASE_0_FOUNDATION.md](PHASE_0_FOUNDATION.md) | ✅ Complete |
| Phase 0 Status | [PHASE0_STATUS.md](PHASE0_STATUS.md) | ✅ Complete |
| Phase 1 | [PHASE_1_REAL_NESSUS.md](PHASE_1_REAL_NESSUS.md) | ✅ Complete |
| Phase 1A Status | [phases/phase1/PHASE_1A_STATUS.md](phases/phase1/PHASE_1A_STATUS.md) | ✅ Complete |
| Phase 2 | [PHASE_2_SCHEMA_RESULTS.md](PHASE_2_SCHEMA_RESULTS.md) | 📝 Planned |
| Phase 3 | [PHASE_3_OBSERVABILITY.md](PHASE_3_OBSERVABILITY.md) | 📝 Planned |
| Phase 4 | [PHASE_4_PRODUCTION.md](PHASE_4_PRODUCTION.md) | 📝 Planned |

### Architecture & Requirements

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Project overview |
| [ARCHITECTURE_v2.2.md](ARCHITECTURE_v2.2.md) | System architecture |
| [NESSUS_MCP_SERVER_REQUIREMENTS.md](NESSUS_MCP_SERVER_REQUIREMENTS.md) | Requirements specification |

### Testing & Validation

| Document | Purpose |
|----------|---------|
| [DUAL_MODE_COMPARISON_FINAL_REPORT.md](DUAL_MODE_COMPARISON_FINAL_REPORT.md) | Dual-mode testing results |
| [NORMAL_MODE_TEST_SUMMARY_FINAL.md](NORMAL_MODE_TEST_SUMMARY_FINAL_REPORT.md) | NORMAL mode analysis |
| [TEST_STATUS.md](TEST_STATUS.md) | Testing status tracker |

**Test Results:**
- `test_results_normal_20251114_181321.json` - NORMAL mode results
- `test_results_update_20251114_182113.json` - UPDATE mode results

### Implementation Guides

| Document | Purpose |
|----------|---------|
| [FINAL_MINIMAL_CHANGES.md](FINAL_MINIMAL_CHANGES.md) | Minimal fix implementation |
| [MINIMAL_FIX_SUMMARY.md](MINIMAL_FIX_SUMMARY.md) | Quick fix reference |

---

## Configuration Files

### Docker Compose

**Location:** `/home/nessus/docker/nessus-shared/`

| File | Purpose | Usage |
|------|---------|-------|
| `docker-compose.yml` | Base configuration | Always required |
| `docker-compose.update-mode.yml` | UPDATE mode override | Plugin updates |
| `docker-compose.old-working-test.yml` | WebUI access override | Human WebUI access |

**Backup:** `/home/nessus/docker/backups/20251111_135253/nessus-old/`

### Apply Configurations

**Normal mode (default):**
```bash
cd /home/nessus/docker/nessus-shared
docker compose up -d
```

**UPDATE mode (plugin updates):**
```bash
cd /home/nessus/docker/nessus-shared
./switch-mode.sh update
```

**WebUI access mode (current):**
```bash
cd /home/nessus/docker/nessus-shared
docker compose -f docker-compose.yml -f docker-compose.old-working-test.yml up -d
```

### MCP Server Configuration

**Location:** `/home/nessus/projects/nessus-api/mcp-server/tools/mcp_server.py`

**Scanner URLs:**
- Scanner 1: `https://172.30.0.3:8834` (internal Docker IP)
- Scanner 2: `https://172.30.0.4:8834` (internal Docker IP)

---

## Helper Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `switch-mode.sh` | `/home/nessus/docker/nessus-shared/` | Switch NORMAL/UPDATE modes |
| `access-scanner-webui.sh` | `/home/nessus/projects/nessus-api/` | Container-based Firefox browser |
| `test-scanner-access.html` | `/home/nessus/projects/nessus-api/` | Browser test page |

---

## Common Tasks

### Access WebUI
```bash
# Open browser to:
https://172.32.0.209:8834

# Or use container-based browser:
/home/nessus/projects/nessus-api/access-scanner-webui.sh
```

### Run MCP Server
```bash
cd /home/nessus/projects/nessus-api
python mcp-server/tools/mcp_server.py
```

### Switch to UPDATE Mode
```bash
cd /home/nessus/docker/nessus-shared
./switch-mode.sh update
```

### Check Scanner Status
```bash
# Via host LAN IP:
curl -k -s https://172.32.0.209:8834/server/status | python3 -m json.tool

# Via MCP automation:
cd /home/nessus/projects/nessus-api
python -c "import httpx; print(httpx.get('https://172.30.0.3:8834/server/status', verify=False).json())"
```

### Verify Configuration
```bash
# Check containers:
docker ps --filter "name=vpn-gateway\|nessus-pro"

# Check network mode:
docker inspect nessus-pro-1 | grep NetworkMode

# Check port mapping:
docker port vpn-gateway-shared 8834
```

---

## Troubleshooting Guides

### WebUI Access Issues
**Guide:** [WEBUI_ACCESS_SOLUTION_FINAL.md](WEBUI_ACCESS_SOLUTION_FINAL.md) - Section "Troubleshooting"

**Quick checks:**
```bash
# Verify host IP (use this in browser):
ip addr show | grep "inet 172.32"

# Test connectivity:
curl -k -s https://172.32.0.209:8834/server/status

# Check Nessus status:
docker exec vpn-gateway-shared curl -k -s https://localhost:8834/server/status
```

### Mode Switching
**Guide:** [DUAL_MODE_COMPARISON_FINAL_REPORT.md](DUAL_MODE_COMPARISON_FINAL_REPORT.md) - Section "Mode Switching Procedure"

```bash
cd /home/nessus/docker/nessus-shared
./switch-mode.sh status  # Check current mode
```

### MCP Server Issues
**Guide:** [PHASE_1_REAL_NESSUS.md](PHASE_1_REAL_NESSUS.md)

**Test scanner connectivity:**
```bash
cd /home/nessus/projects/nessus-api
python mcp-server/test_both_scanners.py
```

---

## Network Architecture

### Dual-Mode System

**NORMAL Mode:**
- Purpose: Daily scanning operations
- VPN: Split routing (internet via VPN, LAN direct)
- WebUI: Via host LAN IP (172.32.0.209:8834)
- MCP: Via internal IPs (172.30.0.3:8834, 172.30.0.4:8834)

**UPDATE Mode:**
- Purpose: Plugin updates and maintenance
- VPN: Split routing (same as NORMAL)
- WebUI: Via host LAN IP (same as NORMAL)
- Port Forwarding: Removed to avoid NAT conflicts

**Current Mode:** WebUI access (shared network namespace)

### Network Topology

```
Host Machine (172.32.0.209)
    ↓
Docker Bridge (172.30.0.0/24)
    ↓
    ├── VPN Gateway (172.30.0.2) [Port 8834 exposed]
    │   └── Nessus Scanner 1 (shares VPN gateway network)
    │
    ├── Nessus Scanner 2 (172.30.0.4)
    │
    └── Debug Scanner (172.30.0.7)
```

**WebUI Access Flow:**
```
Browser → https://172.32.0.209:8834
         ↓
      Host NIC (172.32.0.209)
         ↓
      Docker Port Mapping (8834:8834)
         ↓
      VPN Gateway Network Stack
         ↓
      Nessus Process (shared namespace)
         ↓
      ✅ Success
```

---

## Key Insights & Lessons Learned

### Docker NAT + TLS Issue
**Problem:** Docker NAT breaks TLS handshakes for host-to-container connections
**Solution:** Use host LAN IP instead of localhost
**Documentation:** [WEBUI_ACCESS_SOLUTION_FINAL.md](WEBUI_ACCESS_SOLUTION_FINAL.md)

### VPN Split Routing
**Problem:** Plugin updates fail when port forwarding interferes with VPN routing
**Solution:** Dual-mode system (NORMAL vs UPDATE)
**Documentation:** [DUAL_MODE_COMPARISON_FINAL_REPORT.md](DUAL_MODE_COMPARISON_FINAL_REPORT.md)

### Shared Network Namespace
**Problem:** Need scanner to use VPN but expose port on host
**Solution:** `network_mode: "service:vpn-gateway"` + port on gateway
**Documentation:** [WEBUI_ACCESS_SOLUTION_FINAL.md](WEBUI_ACCESS_SOLUTION_FINAL.md) - "Working Configuration"

---

## Current Status Summary

### Working Features
✅ WebUI access via host LAN IP (https://172.32.0.209:8834)
✅ MCP automation via internal IPs
✅ VPN split routing (internet via VPN, LAN direct)
✅ Dual-scanner setup (Scanner 1 + Scanner 2)
✅ Mode switching (NORMAL ↔ UPDATE)
✅ LAN scanning capability
✅ Plugin updates (in UPDATE mode)

### Known Limitations
❌ Localhost WebUI access (Docker NAT breaks TLS)
❌ Host-to-internal-IP HTTPS (same TLS issue)

### Recommended Access Methods
1. **WebUI (Human):** `https://172.32.0.209:8834` (host LAN IP)
2. **API (Automation):** `https://172.30.0.3:8834` (internal IP via MCP)
3. **Alternative:** Container-based browser for internal IP access

---

## Project Milestones

- ✅ **2025-11-06:** Phase 0 - Mock Nessus implementation
- ✅ **2025-11-13:** Phase 1A - Real Nessus integration
- ✅ **2025-11-14:** WebUI access solution finalized
- 📝 **Next:** Phase 2 - Schema-driven result handling

---

## Quick Reference Card

**WebUI:** https://172.32.0.209:8834 (user: nessus / pass: nessus)
**MCP:** `cd /home/nessus/projects/nessus-api && python mcp-server/tools/mcp_server.py`
**Mode:** `cd /home/nessus/docker/nessus-shared && ./switch-mode.sh status`
**Docs:** `/home/nessus/projects/nessus-api/WEBUI_ACCESS_QUICKREF.md`

---

**For detailed information on any topic, refer to the specific documentation file listed above.**
