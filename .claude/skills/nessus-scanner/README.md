# Nessus Scanner Skill

> Claude Code skill for vulnerability scanning with the Nessus MCP Server

## Overview

This skill enables Claude to effectively use the Nessus MCP Server for vulnerability scanning. It provides guidance on scan type selection, result filtering, and vulnerability analysis.

## Features

- **Scan Type Selection** - Guidance on untrusted vs authenticated vs privileged scans
- **Result Filtering** - Filter by severity, CVSS, host, custom criteria
- **Top 5 Analysis** - Extract and explain most critical vulnerabilities
- **Attack Vector Explanations** - Brief descriptions of exploitation potential

## Prerequisites

### 1. MCP Server Running

The Nessus MCP Server must be running:

```bash
cd /home/nessus/projects/nessus-api/dev1
docker compose up -d
```

### 2. Register with Claude Code

```bash
claude mcp add --transport http nessus-mcp http://localhost:8836/mcp
```

Verify tools are available:
```bash
claude /tools
```

## Usage

### Explicit Activation

```
User: "Use the nessus skill to scan 192.168.1.0/24"
```

### Automatic Activation

The skill may activate when you mention:
- Vulnerability scanning
- Security assessment
- Nessus scan
- Network security scan

## Available Tools

After MCP registration, these tools are available:

| Tool | Purpose |
|------|---------|
| `run_untrusted_scan` | Network-only vulnerability scan |
| `run_authenticated_scan` | SSH authenticated scan |
| `get_scan_status` | Check scan progress |
| `get_scan_results` | Get paginated results |
| `list_scanners` | List scanner instances |
| `list_pools` | List scanner pools |
| `get_pool_status` | Pool capacity info |
| `get_queue_status` | Queue metrics |
| `list_tasks` | Recent task history |

## File Structure

```
nessus-scanner/
├── SKILL.md              # Main skill file (Claude reads this)
├── README.md             # This file
└── references/
    ├── QUICK-REF.md      # Tool syntax cheat sheet
    ├── SCAN-SELECTION.md # Scan type decision guide
    └── FILTERING.md      # Result filtering strategies
```

## Quick Examples

### Network Scan

```
User: "Scan 192.168.1.0/24 for vulnerabilities"
Claude: [Uses run_untrusted_scan, waits, returns top 5 vulns]
```

### Authenticated Scan

```
User: "Run an authenticated scan on 192.168.1.100 with user 'admin'"
Claude: [Asks for password, uses run_authenticated_scan]
```

### Filter Results

```
User: "Show me only critical vulnerabilities from that scan"
Claude: [Uses get_scan_results with filters={"severity": "4"}]
```

## Related Documentation

- [MCP Server README](../../../mcp-server/README.md)
- [API Reference](../../../mcp-server/docs/API.md)
- [Scanner Pools](../../../mcp-server/docs/SCANNER_POOLS.md)

## Version

**1.0.0** - Initial release (2025-11-26)
