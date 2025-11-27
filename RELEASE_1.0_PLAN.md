# Nessus MCP Server 1.0 Release Plan

**Created:** 2025-11-27
**Status:** DRAFT - Iterating
**Pre-release Commit:** `b45c016297cb9e4b611343155a9e0a74170560c1`

## Design Decisions

| Question | Decision |
|----------|----------|
| VPN Requirement | Required - for scanner plugin/signature updates (not scanning) |
| Nessus Licensing | Hardcoded, document "replace with your code" |
| Integration | `scanners-infra/` at top level |
| Clone-and-Run Scope | Full stack (scanners + MCP) |
| Scanner Count | Dual scanner (demonstrates pools) |
| Secrets | Bundle now, sanitize in future |

---

## Rollback Instructions

If anything goes wrong, rollback to pre-release state:

```bash
cd /home/nessus/projects/nessus-api
git reset --hard b45c016297cb9e4b611343155a9e0a74170560c1
```

To undo only the archive operations (if committed separately):

```bash
git revert HEAD  # Reverts last commit
# OR
git log --oneline -10  # Find the commit to revert
git revert <commit-hash>
```

---

## 1.0 Release Scope

### KEEP (Core 1.0 Components)

| Component | Location | Description |
|-----------|----------|-------------|
| MCP Server Core | `mcp-server/core/` | Task manager, state machine, Redis client |
| Scanner Abstraction | `mcp-server/scanners/` | Nessus client, scanner registry |
| MCP Tools | `mcp-server/tools/` | Tool implementations, server entry point |
| Worker | `mcp-server/worker/` | Background scan processor |
| Schema | `mcp-server/schema/` | Results conversion, filtering |
| Client | `mcp-server/client/` | MCP client implementation |
| Tests | `mcp-server/tests/` | Unit, integration, e2e tests |
| Dockerfiles | `mcp-server/docker/` | Build instructions |
| Config | `mcp-server/config/` | Scanner configuration |
| Prod Environment | `mcp-server/prod/` | Production deployment files |
| Dev Environment | `dev1/` | docker-compose deployment |
| FastMCP Docs | `docs/fastMCPServer/` | Framework reference |
| Skills | `.claude/skills/nessus-scanner/` | Claude Code skill |
| Skills | `.claude/skills/markdown-writer/` | Markdown skill |
| Scanner Infra | `scanners-infra/` | **NEW** - Nessus scanners + VPN (from nessus-shared) |

### KEEP (MCP Server Docs - Cleaned)

| File | Keep/Archive |
|------|--------------|
| `mcp-server/docs/API.md` | KEEP |
| `mcp-server/docs/ARCHITECTURE_v2.2.md` | KEEP |
| `mcp-server/docs/SCANNER_POOLS.md` | KEEP |
| `mcp-server/docs/HOUSEKEEPING.md` | KEEP |
| `mcp-server/docs/MONITORING.md` | KEEP |
| `mcp-server/docs/TESTING.md` | KEEP |
| `mcp-server/docs/README.md` | KEEP |
| `mcp-server/docs/DOCKER_NETWORK_CONFIG.md` | ARCHIVE (infrastructure-specific) |
| `mcp-server/docs/HTTPX_READERROR_INVESTIGATION.md` | ARCHIVE (debug) |
| `mcp-server/docs/FASTMCP_CLIENT_ARCHITECTURE.md` | ARCHIVE (design doc) |
| `mcp-server/docs/FASTMCP_CLIENT_REQUIREMENT.md` | ARCHIVE (design doc) |
| `mcp-server/docs/SCAN_LIFECYCLE_TEST_ACTIONS.md` | ARCHIVE (testing notes) |
| `mcp-server/docs/STRUCTURED_LOGGING_EXAMPLES.md` | ARCHIVE (examples) |
| `mcp-server/docs/NESSUS_MCP_SERVER_REQUIREMENTS.md` | ARCHIVE (planning) |

### ARCHIVE (Move to `archive/2025-11-27/`)

| Source | Archive Destination |
|--------|---------------------|
| `nessusAPIWrapper/` | `archive/2025-11-27/nessusAPIWrapper/` |
| `mcp-server/phases/` | `archive/2025-11-27/mcp-server/phases/` |
| `mcp-server/docs/archive/` | `archive/2025-11-27/mcp-server/docs/archive/` |
| Selected docs (see above) | `archive/2025-11-27/mcp-server/docs/` |
| `mcp-server/scripts/debug/` | `archive/2025-11-27/mcp-server/scripts/debug/` |
| `README.md` (current) | `archive/2025-11-27/README_nessusAPIWrapper.md` |

### ARCHIVE (Root-level debris)

| Files | Reason |
|-------|--------|
| `test_*.py`, `test_*.sh` | Test/debug scripts |
| `scanner*_status.json`, `scanner*_webui.html` | Debug output |
| `test_results_*.json` | Test output |
| `vulns_*.json` | Export output |
| `scan_config_debug.json` | Debug output |
| `*.sh` (check_*, reset_*, access_*) | Debug scripts |
| `create_scan_*.py` | One-off scripts |
| `FINAL_ROOT_CAUSE_ANALYSIS.md` | Debug doc |
| `FIXES_SUMMARY.md` | Debug doc |
| `TEST_STATUS.md` | Debug doc |
| `UNIFIED_MODE_IMPLEMENTATION_SUMMARY.md` | Implementation notes |
| `DOCUMENTATION_INDEX.md` | Index (rebuild for 1.0) |
| `PROJECT_SETUP.md` | Old setup guide |
| `QUICK_ACCESS_GUIDE.md` | Infrastructure-specific |
| `docker-compose-webui-working.yml` | Debug config |
| `=0.20.0` | Artifact |
| `monitor_and_export.py` (root) | Duplicate |
| `mcp-server/venv/` |  |
| `venv/` (root) | l |

### DELETE (Not Archive)

| Item | Reason |
|------|--------|
| `temp/` | Git-ignored anyway |
| `.pytest_cache/` | Regenerated |

---

## Execution Steps

### Phase 1: Commit Untracked Files

```bash
# Commit Phase 5/6 work before archiving
git add mcp-server/phases/PHASE_6_RESILIENCE_TESTING.md
git add mcp-server/phases/phase5/
git add mcp-server/tests/integration/test_authenticated_scan_workflow.py
git add mcp-server/tests/integration/test_mcp_client_e2e.py
git add mcp-server/tests/unit/test_authenticated_scans.py
git add mcp-server/docker/Dockerfile.scan-target
git add dev1/.env.dev

git commit -m "feat: Add Phase 5/6 authenticated scan tests and docs"
```

### Phase 2: Integrate Scanner Infrastructure

```bash
# Copy scanner infrastructure from external location
cp -r /home/nessus/docker/nessus-shared scanners-infra

# Remove nessus-shared archive (we have our own archive structure)
rm -rf scanners-infra/archive

# Note: Contains sensitive data (VPN keys, SSL certs)
# TODO: Sanitize in future release
```

**Contents of `scanners-infra/`:**
- `docker-compose.yml` - Dual Nessus scanners + VPN + nginx proxy
- `nginx/` - Reverse proxy config + SSL certs
- `wg/` - WireGuard VPN config
- `README.md` - Quick start
- `ARCHITECTURE.md` - Technical docs
- `CONFIGURATION.md` - Configuration guide

### Phase 3: Create Archive Structure

```bash
mkdir -p archive/2025-11-27/mcp-server/docs
mkdir -p archive/2025-11-27/root-debris
```

### Phase 4: Archive nessusAPIWrapper

```bash
mv nessusAPIWrapper archive/2025-11-27/
```

### Phase 5: Archive mcp-server/phases

```bash
mv mcp-server/phases archive/2025-11-27/mcp-server/
```

### Phase 6: Archive Selected MCP Docs

```bash
# Move debug/planning docs
mv mcp-server/docs/DOCKER_NETWORK_CONFIG.md archive/2025-11-27/mcp-server/docs/
mv mcp-server/docs/HTTPX_READERROR_INVESTIGATION.md archive/2025-11-27/mcp-server/docs/
mv mcp-server/docs/FASTMCP_CLIENT_ARCHITECTURE.md archive/2025-11-27/mcp-server/docs/
mv mcp-server/docs/FASTMCP_CLIENT_REQUIREMENT.md archive/2025-11-27/mcp-server/docs/
mv mcp-server/docs/SCAN_LIFECYCLE_TEST_ACTIONS.md archive/2025-11-27/mcp-server/docs/
mv mcp-server/docs/STRUCTURED_LOGGING_EXAMPLES.md archive/2025-11-27/mcp-server/docs/
mv mcp-server/docs/NESSUS_MCP_SERVER_REQUIREMENTS.md archive/2025-11-27/mcp-server/docs/
mv mcp-server/docs/archive archive/2025-11-27/mcp-server/docs/

# Move debug scripts
mkdir -p archive/2025-11-27/mcp-server/scripts
mv mcp-server/scripts/debug archive/2025-11-27/mcp-server/scripts/
```

### Phase 7: Archive Root-Level Debris

```bash
# Test files
mv test_both_scanners.py archive/2025-11-27/root-debris/
mv test_dual_mode_comprehensive.py archive/2025-11-27/root-debris/
mv test_results_*.json archive/2025-11-27/root-debris/

# Debug scripts
mv check_routing.sh archive/2025-11-27/root-debris/
mv check_scanners.sh archive/2025-11-27/root-debris/
mv reset_scanner2.sh archive/2025-11-27/root-debris/
mv test_debug_scanner.sh archive/2025-11-27/root-debris/
mv test_target.sh archive/2025-11-27/root-debris/
mv test_vpn_gateway.sh archive/2025-11-27/root-debris/
mv access-scanner-webui.sh archive/2025-11-27/root-debris/

# Debug output
mv scanner1_status.json archive/2025-11-27/root-debris/
mv scanner2_status.json archive/2025-11-27/root-debris/
mv scanner1_webui.html archive/2025-11-27/root-debris/
mv scanner2_webui.html archive/2025-11-27/root-debris/
mv scan_config_debug.json archive/2025-11-27/root-debris/
mv vulns_*.json archive/2025-11-27/root-debris/
mv test-scanner-access.html archive/2025-11-27/root-debris/

# One-off scripts
mv create_scan_direct.py archive/2025-11-27/root-debris/
mv create_scan_scanner2.py archive/2025-11-27/root-debris/
mv scanner2_scan.py archive/2025-11-27/root-debris/
mv scanner2_scan_httpx.py archive/2025-11-27/root-debris/
mv monitor_and_export.py archive/2025-11-27/root-debris/

# Docs to archive
mv FINAL_ROOT_CAUSE_ANALYSIS.md archive/2025-11-27/root-debris/
mv FIXES_SUMMARY.md archive/2025-11-27/root-debris/
mv TEST_STATUS.md archive/2025-11-27/root-debris/
mv UNIFIED_MODE_IMPLEMENTATION_SUMMARY.md archive/2025-11-27/root-debris/
mv DOCUMENTATION_INDEX.md archive/2025-11-27/root-debris/
mv PROJECT_SETUP.md archive/2025-11-27/root-debris/
mv QUICK_ACCESS_GUIDE.md archive/2025-11-27/root-debris/
mv docker-compose-webui-working.yml archive/2025-11-27/root-debris/

# Artifacts
mv "=0.20.0" archive/2025-11-27/root-debris/
```

### Phase 8: Archive Old README

```bash
mv README.md archive/2025-11-27/README_nessusAPIWrapper.md
```

### Phase 9: Clean Up

```bash
# Remove regeneratable directories (if they exist in git)
rm -rf mcp-server/venv
rm -rf venv
rm -rf temp
rm -rf mcp-server/.pytest_cache

# Remove empty directories
rm -rf claudeScripts  # Empty directory
rm -rf prod           # Empty root prod/ (real prod is in mcp-server/prod/)
find . -type d -empty -delete 2>/dev/null || true
```

### Phase 10: Create New README.md

Create new `README.md` focused on MCP Server 1.0 (content TBD - will iterate).

### Phase 11: Commit Archive

```bash
git add -A
git commit -m "chore: Prepare 1.0 release - integrate scanners, archive legacy

Added:
- scanners-infra/ (Nessus scanners + VPN from nessus-shared)

Archived to archive/2025-11-27/:
- nessusAPIWrapper/ (original Python scripts)
- mcp-server/phases/ (implementation planning)
- Debug scripts and output files
- Old README and documentation

1.0 Release: Full-stack MCP Server with integrated scanner infrastructure."
```

### Phase 12: Push

```bash
git push origin main
```

---

## Final 1.0 Structure (Expected)

```
nessus-api/
├── .claude/
│   └── skills/
│       ├── markdown-writer/      # Markdown skill
│       └── nessus-scanner/       # Nessus skill
│
├── scanners-infra/               # NEW: Scanner infrastructure
│   ├── docker-compose.yml        # Dual scanners + VPN + nginx
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── certs/
│   ├── wg/
│   │   └── wg0.conf              # WireGuard config
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── CONFIGURATION.md
│   └── *.md                      # Other docs
│
├── mcp-server/
│   ├── core/                     # Task manager, state machine
│   ├── scanners/                 # Nessus client, registry
│   ├── tools/                    # MCP tools, server entry
│   ├── worker/                   # Background processor
│   ├── schema/                   # Results conversion
│   ├── client/                   # MCP client
│   ├── tests/                    # All tests
│   ├── docker/                   # Dockerfiles
│   ├── config/                   # Scanner config
│   ├── scripts/                  # Utility scripts
│   ├── docs/                     # Cleaned documentation
│   │   ├── API.md
│   │   ├── ARCHITECTURE_v2.2.md
│   │   ├── SCANNER_POOLS.md
│   │   ├── HOUSEKEEPING.md
│   │   ├── MONITORING.md
│   │   ├── TESTING.md
│   │   └── README.md
│   ├── prod/                     # Production deployment
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.worker
│   │   └── .env.prod.example
│   ├── README.md                 # MCP Server README
│   ├── requirements*.txt
│   ├── pyproject.toml
│   └── pytest.ini
│
├── dev1/
│   ├── docker-compose.yml        # MCP deployment
│   └── README_MIGRATION.md
│
├── docs/
│   ├── fastMCPServer/            # FastMCP reference
│   └── credentials.md            # (git-ignored)
│
├── archive/
│   └── 2025-11-27/               # Pre-1.0 archive
│       ├── nessusAPIWrapper/
│       ├── mcp-server/
│       │   ├── phases/
│       │   └── docs/
│       ├── root-debris/
│       └── README_nessusAPIWrapper.md
│
├── README.md                     # NEW: MCP Server 1.0 focused
└── .gitignore
```

---

## Open Questions - RESOLVED

1. **mcp-server/scripts/** - Archive `scripts/debug/` (8 debug scripts), keep `scripts/` dir
2. **mcp-server/prod/** - KEEP (has production docker-compose, Dockerfiles, .env.prod.example)
3. **claudeScripts/** - DELETE (empty directory)
4. **Root archive/** - Already has content from Nov 24. Add `2025-11-27/` subdirectory
5. **New README content** - TBD after archive complete

---

## Checklist

- [ ] Review this plan
- [ ] Resolve open questions
- [ ] Commit untracked files (Phase 1)
- [ ] Integrate scanner infrastructure (Phase 2)
- [ ] Execute archive operations (Phases 3-9)
- [ ] Create new README (Phase 10)
- [ ] Final commit and push (Phases 11-12)
- [ ] Verify 1.0 structure
- [ ] Tag release: `git tag -a v1.0.0 -m "Nessus MCP Server 1.0"`
