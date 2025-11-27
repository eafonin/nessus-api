# Scan Type Selection Guide

> When to use which scan type

## Overview

| Scan Type | Tool | Credentials | Depth | Use Case |
|-----------|------|-------------|-------|----------|
| Untrusted | `run_untrusted_scan` | None | Network-only | External assessment |
| Authenticated | `run_authenticated_scan` | SSH user | Medium | Internal audit |
| Authenticated Privileged | `run_authenticated_scan` | SSH + sudo | Deep | Full system audit |

## Decision Tree

```
Can you provide SSH credentials?
│
├─ NO → Use run_untrusted_scan
│       (Network-only scan, ~100 checks)
│
└─ YES → What access level do you have?
         │
         ├─ Regular user (no sudo) → run_authenticated_scan
         │                          scan_type="authenticated"
         │                          (~500 checks)
         │
         └─ Root or sudo access → run_authenticated_scan
                                 scan_type="authenticated_privileged"
                                 elevate_privileges_with="sudo"
                                 (~1000+ checks)
```

## Scan Type Details

### Untrusted Scan

**What it checks:**
- Open ports and services
- Service versions (banners)
- Known network vulnerabilities
- SSL/TLS configuration
- Default credentials (network level)

**Detection capability:** ~100 vulnerability checks

**Best for:**
- External penetration testing
- Perimeter security assessment
- Systems where you can't get credentials
- Quick network discovery

**Example:**
```python
run_untrusted_scan(
    targets="192.168.1.0/24",
    name="External Assessment"
)
```

### Authenticated Scan

**What it checks:**
- Everything from untrusted +
- Installed packages and versions
- Configuration files (readable by user)
- User account enumeration
- Local privilege escalation paths
- Application vulnerabilities

**Detection capability:** ~500 vulnerability checks (5x untrusted)

**Best for:**
- Internal vulnerability assessment
- Patch compliance checking
- Application server audits
- Regular security monitoring

**Requirements:**
- SSH access to target
- Username and password

**Example:**
```python
run_authenticated_scan(
    targets="192.168.1.100",
    name="Server Audit",
    scan_type="authenticated",
    ssh_username="scanuser",
    ssh_password="password123"
)
```

### Authenticated Privileged Scan

**What it checks:**
- Everything from authenticated +
- Root-only configuration files
- System-level security settings
- Kernel parameters
- Full filesystem checks
- Privileged service configurations
- Complete compliance assessment

**Detection capability:** ~1000+ vulnerability checks (10x untrusted)

**Best for:**
- Compliance audits (PCI, HIPAA, SOC2)
- Full system security assessment
- Pre-deployment security validation
- Incident response preparation

**Requirements:**
- SSH access to target
- Username and password
- sudo or root access

**Escalation Methods:**
| Method | When to Use |
|--------|-------------|
| `sudo` | Most common - user can sudo to root |
| `su` | Switch user to root directly |
| `su+sudo` | First su to intermediate user, then sudo |
| `pbrun` | PowerBroker environments |
| `dzdo` | Centrify DirectAuthorize |

**Example (sudo with password):**
```python
run_authenticated_scan(
    targets="192.168.1.100",
    name="Compliance Audit",
    scan_type="authenticated_privileged",
    ssh_username="scanuser",
    ssh_password="password123",
    elevate_privileges_with="sudo",
    escalation_password="password123"
)
```

**Example (sudo NOPASSWD):**
```python
run_authenticated_scan(
    targets="192.168.1.100",
    name="Full Audit",
    scan_type="authenticated_privileged",
    ssh_username="scanuser",
    ssh_password="password123",
    elevate_privileges_with="sudo"
    # No escalation_password needed
)
```

## Detection Comparison

| Vulnerability Type | Untrusted | Authenticated | Privileged |
|-------------------|-----------|---------------|------------|
| Open ports | Yes | Yes | Yes |
| Service versions | Partial | Yes | Yes |
| Missing patches | No | Yes | Yes |
| Config issues | No | Partial | Yes |
| Local privesc | No | Yes | Yes |
| Kernel vulns | No | Partial | Yes |
| Compliance | No | Partial | Yes |

## Common Scenarios

### Scenario 1: External Web Server

**Situation:** Public-facing web server, no SSH access
**Choice:** `run_untrusted_scan`
**Why:** Can only assess from network perspective

### Scenario 2: Internal Application Server

**Situation:** Internal server, have SSH as app user
**Choice:** `run_authenticated_scan` (authenticated)
**Why:** Can check packages and configs, but not root-level

### Scenario 3: PCI Compliance Audit

**Situation:** Need full compliance report, have sudo access
**Choice:** `run_authenticated_scan` (authenticated_privileged)
**Why:** PCI requires checking root-level security controls

### Scenario 4: Quick Network Inventory

**Situation:** Want to discover what's on the network
**Choice:** `run_untrusted_scan`
**Why:** Fast, doesn't require credentials

### Scenario 5: Patch Tuesday Verification

**Situation:** Need to verify patches applied, have credentials
**Choice:** `run_authenticated_scan` (authenticated)
**Why:** Can check installed package versions

## Questions to Ask User

When helping select scan type, ask:

1. "Do you have SSH credentials for the target systems?"
2. "Do you need to check installed packages and local configurations?"
3. "Do you have sudo or root access?"
4. "Is this for compliance (PCI, HIPAA, etc.)?"

Based on answers, select appropriate scan type.
