# Nessus MCP Server - Configuration Status

**Last Updated**: 2025-11-13
**Current Status**: PLANNING PHASE - New configuration ready for review

---

## Configuration Files Overview

### CURRENT (Active)

```
docker-compose.yml              ← Active configuration ⚠️ HAS ISSUES
├── External network: nessus_nessus_net     ← WRONG network name ❌
├── Scanner URLs: https://vpn-gateway:8834  ← WRONG URL (not accessible) ❌
└── Issue: Cannot connect to scanners ❌
```

### PROPOSED (Ready to Deploy)

```
docker-compose.yml.new          ← New configuration ✅ FIXES ISSUES
├── External network: nessus-shared_vpn_net ← CORRECT network ✓
├── Scanner URLs:
│   ├── Scanner 1: https://172.30.0.3:8834  ← Internal bridge IP ✓
│   └── Scanner 2: https://172.30.0.5:8834  ← Internal bridge IP ✓
└── Connects to scanners via internal bridge ✅
```

### OBSOLETE (After Migration)

```
docker-compose.yml.obsolete     ← Will be created during migration
└── Previous configuration with wrong network (archived for reference)
```

---

## Quick Status Check

### Is Migration Needed?

**Run this test to check if MCP can connect to scanners:**

```bash
# Test: Can MCP container reach Scanner 1?
docker exec nessus-mcp-api-dev curl -k https://172.30.0.3:8834/server/status 2>&1

# If this returns {"code":200} → Already working (or fix applied)
# If this fails with "Connection refused" or timeout → Migration needed ✅
```

### Current Network Architecture

```
┌──────────────────────────────────────────────────────────┐
│ MCP Server Containers                                    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ default network (dev1_default)                    │ │
│  │   ├── redis                                       │ │
│  │   ├── mcp-api ──────┐                            │ │
│  │   └── scanner-worker ┘                           │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ nessus_nessus_net (external) ⚠️ WRONG NETWORK    │ │
│  │   ├── mcp-api (trying to connect)                │ │
│  │   └── scanner-worker (trying to connect)         │ │
│  │                                                   │ │
│  │   Issue: This network doesn't have scanners! ❌  │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘

Scanners are actually on: nessus-shared_vpn_net (different network!)
```

---

## Key Differences: Current vs Proposed

### Network Configuration

| Aspect | Current | Proposed |
|--------|---------|----------|
| **External Network** | `nessus_nessus_net` ❌ | `nessus-shared_vpn_net` ✅ |
| **Scanner 1 URL** | `https://vpn-gateway:8834` ❌ | `https://172.30.0.3:8834` ✅ |
| **Scanner 2 URL** | Not configured ❌ | `https://172.30.0.5:8834` ✅ |
| **Connectivity** | Broken ❌ | Working ✅ |

### Environment Variables

| Variable | Current | Proposed |
|----------|---------|----------|
| `NESSUS_URL` | `https://vpn-gateway:8834` ❌ | Removed (use per-scanner URLs) |
| `SCANNER_1_URL` | Not set | `https://172.30.0.3:8834` ✅ |
| `SCANNER_2_URL` | Not set | `https://172.30.0.5:8834` ✅ |
| `NESSUS_USERNAME` | `nessus` ✅ | `nessus` ✅ (preserved) |
| `NESSUS_PASSWORD` | `nessus` ✅ | `nessus` ✅ (preserved) |

---

## Migration Dependencies

### Scanner Stack Must Be Migrated First

```
1. Migrate scanner stack (/home/nessus/docker/nessus-shared/)
   ├── Deploy new docker-compose.yml with split routing
   ├── Verify scanners are on nessus-shared_vpn_net
   └── Verify scanner internal IPs (172.30.0.3, 172.30.0.5)

2. Then migrate MCP stack (this directory)
   ├── Update docker-compose.yml to use correct network
   ├── Update scanner URLs to internal bridge IPs
   └── Verify MCP can connect to both scanners
```

**Do not migrate MCP before scanner stack!** Network connectivity depends on scanner configuration.

---

## Pre-Migration Checklist

Before running migration, verify:

- [ ] Scanner stack migrated first (see `/home/nessus/docker/nessus-shared/README_MIGRATION.md`)
- [ ] Scanners are running on `nessus-shared_vpn_net` network
- [ ] Scanner 1 accessible at `172.30.0.3:8834`
- [ ] Scanner 2 accessible at `172.30.0.5:8834`
- [ ] Created backup of current docker-compose.yml
- [ ] Redis data volume exists (scan history preserved)

---

## Quick Migration Commands

**For admins who read the scanner migration docs:**

```bash
cd /home/nessus/projects/nessus-api/dev1

# 1. Backup
cp docker-compose.yml docker-compose.yml.backup-$(date +%Y%m%d)

# 2. Stop MCP stack
docker compose down

# 3. Replace config
mv docker-compose.yml docker-compose.yml.obsolete
mv docker-compose.yml.new docker-compose.yml

# 4. Start with new config
docker compose up -d

# 5. Verify connectivity to scanners
docker exec nessus-mcp-api-dev curl -k https://172.30.0.3:8834/server/status
# Expected: {"code":200}

docker exec nessus-mcp-api-dev curl -k https://172.30.0.5:8834/server/status
# Expected: {"code":200}

# 6. Check MCP logs
docker compose logs -f mcp-api
```

**If something breaks:** See rollback procedure in scanner deployment guide.

---

## Verification Tests

### Test 1: Network Connectivity

```bash
# MCP should be on correct network
docker inspect nessus-mcp-api-dev | grep -A 5 "Networks"

# Expected to see: "nessus-shared_vpn_net"

# Ping test to scanners
docker run --rm --network nessus-shared_vpn_net alpine ping -c 1 172.30.0.3
docker run --rm --network nessus-shared_vpn_net alpine ping -c 1 172.30.0.5

# Both should work (0% packet loss)
```

### Test 2: Scanner API Access

```bash
# From MCP API container
docker exec nessus-mcp-api-dev curl -k https://172.30.0.3:8834/server/status

# Expected: {"code":200}

docker exec nessus-mcp-api-dev curl -k https://172.30.0.5:8834/server/status

# Expected: {"code":200}
```

### Test 3: MCP Functionality

```bash
# Run full integration test
cd /home/nessus/projects/nessus-api

docker run --rm --network nessus-shared_vpn_net \
  -v $(pwd):/app -w /app python:3.12-slim \
  sh -c "pip install --quiet httpx && python test_both_scanners.py"

# Expected:
# ✓ Both scanners authenticated
# ✓ Scans created on both scanners
# ✓ Scans launched successfully
```

---

## Rollback Procedure

If migration fails:

```bash
cd /home/nessus/projects/nessus-api/dev1

# Stop new configuration
docker compose down

# Restore previous configuration
cp docker-compose.yml.obsolete docker-compose.yml

# Start old configuration
docker compose up -d

# Verify MCP is back online
docker compose ps
docker compose logs mcp-api
```

**Note**: If scanner stack was also rolled back, you may need to update scanner URLs to old IPs (192.168.100.9, 192.168.100.10).

---

## Documentation Files

### This Directory (MCP Configuration)

| File | Purpose | Status |
|------|---------|--------|
| `docker-compose.yml` | Current active configuration | ⚠️ Has connectivity issues |
| `docker-compose.yml.new` | Proposed configuration | ✅ Ready to deploy |
| `docker-compose.yml.obsolete` | Will be created during migration | Pending |
| `README_MIGRATION.md` | This file - Quick migration reference | ✅ Complete |

### Scanner Stack Documentation

| File | Purpose | Status |
|------|---------|--------|
| `/home/nessus/docker/nessus-shared/NETWORK_ARCHITECTURE.md` | Complete design | ✅ Complete |
| `/home/nessus/docker/nessus-shared/DEPLOYMENT_GUIDE.md` | Migration guide | ✅ Complete |
| `/home/nessus/docker/nessus-shared/README_MIGRATION.md` | Scanner migration status | ✅ Complete |

---

## Related Components

### What This MCP Server Does

```
MCP Server Stack (this directory)
├── redis: Task queue and state management
├── mcp-api: HTTP API for Claude Desktop integration
│   └── Connects to scanners via internal bridge
└── scanner-worker: Background scan job processor
    └── Connects to scanners via internal bridge
```

### How MCP Connects to Scanners

**Before Migration:**
```
mcp-api → nessus_nessus_net → ??? (scanners not on this network) ❌
```

**After Migration:**
```
mcp-api → nessus-shared_vpn_net → Scanner 1 (172.30.0.3:8834) ✅
                                  → Scanner 2 (172.30.0.5:8834) ✅
```

---

## Common Issues & Solutions

### Issue 1: Cannot connect after migration

**Symptoms:**
```bash
docker exec nessus-mcp-api-dev curl -k https://172.30.0.3:8834/server/status
# Connection timeout or "Could not resolve host"
```

**Solution:**
```bash
# Check network configuration
docker inspect nessus-mcp-api-dev | grep -A 10 "Networks"

# Should show nessus-shared_vpn_net
# If not, recreate containers:
docker compose down
docker compose up -d
```

### Issue 2: Old network still referenced

**Symptoms:**
```bash
docker network ls | grep nessus
# Shows: nessus_nessus_net (still exists)
```

**Solution:**
This is OK. The old network can coexist. Just ensure MCP is using `nessus-shared_vpn_net`:
```bash
docker inspect nessus-mcp-api-dev | grep -A 10 "Networks"
```

### Issue 3: Scanner URLs wrong in code

**Symptoms:**
MCP connects to old URLs (`vpn-gateway:8834`)

**Solution:**
Check that new environment variables are set:
```bash
docker exec nessus-mcp-api-dev env | grep SCANNER

# Should show:
# SCANNER_1_URL=https://172.30.0.3:8834
# SCANNER_2_URL=https://172.30.0.5:8834
```

---

## Post-Migration Configuration

### Configure Scanner Discovery (Optional)

After migration, you can configure scanner discovery:

```bash
cd /home/nessus/projects/nessus-api/mcp-server/config

# Create scanners.yaml
cat > scanners.yaml <<EOF
scanners:
  - name: scanner-1
    url: https://172.30.0.3:8834
    username: nessus
    password: nessus
    enabled: true
    max_concurrent_scans: 5

  - name: scanner-2
    url: https://172.30.0.5:8834
    username: nessus
    password: nessus
    enabled: true
    max_concurrent_scans: 5
EOF

# Restart MCP to apply
cd /home/nessus/projects/nessus-api/dev1
docker compose restart
```

---

## Status Log

| Date | Action | Status | Notes |
|------|--------|--------|-------|
| 2025-11-13 | Planning phase complete | ✅ Done | Configuration ready |
| TBD | Scanner migration complete | Pending | Dependency |
| TBD | MCP migration executed | Pending | Awaiting scanner migration |
| TBD | Verification complete | Pending | All tests passed |
| TBD | Old configs archived | Pending | Marked obsolete |

---

## Next Steps

1. **Complete scanner stack migration first**
   - See: `/home/nessus/docker/nessus-shared/DEPLOYMENT_GUIDE.md`

2. **Verify scanner connectivity**
   - Ensure scanners are on `nessus-shared_vpn_net`
   - Verify internal IPs (172.30.0.3, 172.30.0.5)

3. **Migrate MCP stack**
   - Follow quick migration commands above
   - Verify connectivity tests

4. **Run integration tests**
   - Test full scan workflow
   - Verify both scanners working

---

**Document Status**: ✅ Complete - Ready for Review
**Next Action**: Wait for scanner migration, then migrate MCP
**Estimated Downtime**: 1-2 minutes (MCP restart only)
