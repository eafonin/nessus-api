# Phase 4: Implementation Guide

> **Living Document** - Update checkboxes as tasks are completed
> **Last Updated**: 2025-11-25
> **Status**: In Progress (~40% complete)

---

## Quick Status

| Task | Description | Status | Blocked By |
|------|-------------|--------|------------|
| 4.1 | Pool Architecture | ✅ DONE | - |
| 4.3 | Enhanced MCP Tools | ⚠️ 70% | - |
| 4.5 | Worker Enhancement | ⚠️ 50% | 4.6 |
| 4.6 | Enhanced Task Metadata | 🔴 TODO | - |
| 4.7 | Enhanced Status API | 🔴 TODO | 4.6 |
| 4.8 | Per-Scanner Metrics | 🔴 TODO | - |
| 4.9 | Production Docker | 🔴 TODO | - |
| 4.10 | TTL Housekeeping | 🔴 TODO | - |
| 4.11 | DLQ Handler CLI | 🔴 TODO | - |
| 4.12 | Circuit Breaker | 🔴 TODO | 4.5 |

---

## Implementation Order

```
START
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4A: Core Enhancement (Foundation)                     │
├─────────────────────────────────────────────────────────────┤
│ 4.6 Enhanced Task Metadata ──► 4.5 Worker Enhancement       │
│         │                              │                    │
│         └──────────────┬───────────────┘                    │
│                        ▼                                    │
│              4.3 Enhanced MCP Tools (finish)                │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4B: Observability                                     │
├─────────────────────────────────────────────────────────────┤
│ 4.7 Enhanced Status API ◄── uses validation data            │
│ 4.8 Per-Scanner Metrics ◄── can parallel with 4.7           │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4C: Production                                        │
├─────────────────────────────────────────────────────────────┤
│ 4.9 Production Docker Configuration                         │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4D: Operations                                        │
├─────────────────────────────────────────────────────────────┤
│ 4.10 TTL Housekeeping (independent)                         │
│ 4.11 DLQ Handler CLI (independent)                          │
│ 4.12 Circuit Breaker (needs 4.5)                            │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
 DONE
```

---

## Task 4.6: Enhanced Task Metadata

**Status**: 🔴 NOT STARTED
**Priority**: HIGH (blocks 4.5, 4.7)
**Effort**: ~2 hours

### Goal

Store validation results and authentication status in task.json for later retrieval via status API.

### Current State

**File**: `core/types.py` (lines 31-46)

```python
@dataclass
class Task:
    task_id: str
    trace_id: str
    scan_type: str
    scanner_type: str
    scanner_instance_id: str
    status: str
    payload: Dict[str, Any]
    created_at: str
    scanner_pool: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    nessus_scan_id: Optional[int] = None
    error_message: Optional[str] = None
    # MISSING: validation_stats, validation_warnings, authentication_status
```

### Implementation Checklist

#### 4.6.1: Update Task dataclass

- [ ] **File**: `core/types.py`
- [ ] Add to `Task` dataclass:

```python
@dataclass
class Task:
    # ... existing fields ...

    # Phase 4: Validation results
    validation_stats: Optional[Dict[str, Any]] = None
    validation_warnings: Optional[List[str]] = None
    authentication_status: Optional[str] = None  # "success"|"failed"|"partial"|"not_applicable"
```

#### 4.6.2: Update TaskManager._task_to_dict()

- [ ] **File**: `core/task_manager.py` (lines 83-99)
- [ ] Add new fields to serialization:

```python
@staticmethod
def _task_to_dict(task: Task) -> dict:
    return {
        # ... existing fields ...
        "error_message": task.error_message,
        # Phase 4: Validation fields
        "validation_stats": task.validation_stats,
        "validation_warnings": task.validation_warnings,
        "authentication_status": task.authentication_status,
    }
```

#### 4.6.3: Add mark_completed_with_validation() helper

- [ ] **File**: `core/task_manager.py`
- [ ] Add convenience method:

```python
def mark_completed_with_validation(
    self,
    task_id: str,
    validation_stats: Optional[Dict[str, Any]] = None,
    validation_warnings: Optional[List[str]] = None,
    authentication_status: Optional[str] = None
) -> None:
    """
    Mark task as completed with validation results.

    Args:
        task_id: Task ID
        validation_stats: Dict with hosts_scanned, vuln_counts, etc.
        validation_warnings: List of warning messages
        authentication_status: "success"|"failed"|"partial"|"not_applicable"
    """
    self.update_status(
        task_id,
        ScanState.COMPLETED,
        validation_stats=validation_stats,
        validation_warnings=validation_warnings,
        authentication_status=authentication_status
    )
```

#### 4.6.4: Add mark_failed_with_validation() helper

- [ ] **File**: `core/task_manager.py`
- [ ] Add convenience method:

```python
def mark_failed_with_validation(
    self,
    task_id: str,
    error_message: str,
    validation_stats: Optional[Dict[str, Any]] = None,
    authentication_status: Optional[str] = None
) -> None:
    """
    Mark task as failed with validation context.

    Useful for auth failures where we have partial results.
    """
    self.update_status(
        task_id,
        ScanState.FAILED,
        error_message=error_message,
        validation_stats=validation_stats,
        authentication_status=authentication_status
    )
```

### Acceptance Criteria

- [ ] Task dataclass has 3 new optional fields
- [ ] task.json includes validation fields when present
- [ ] Existing tasks without validation fields load correctly (backward compat)
- [ ] Helper methods work correctly

### Test Commands

```bash
# Unit test
docker compose exec mcp-api python -c "
from core.types import Task
from core.task_manager import TaskManager
import tempfile
import os

with tempfile.TemporaryDirectory() as tmpdir:
    tm = TaskManager(data_dir=tmpdir)

    # Create task with validation
    task = Task(
        task_id='test123',
        trace_id='trace123',
        scan_type='untrusted',
        scanner_type='nessus',
        scanner_instance_id='scanner1',
        status='completed',
        payload={'targets': '192.168.1.1'},
        created_at='2025-01-01T00:00:00',
        validation_stats={'hosts_scanned': 1, 'vuln_count': 5},
        validation_warnings=['Low host count'],
        authentication_status='not_applicable'
    )
    tm.create_task(task)

    # Verify
    loaded = tm.get_task('test123')
    assert loaded.validation_stats == {'hosts_scanned': 1, 'vuln_count': 5}
    assert loaded.authentication_status == 'not_applicable'
    print('✅ Task 4.6 validation passed')
"
```

---

## Task 4.5: Worker Enhancement for Scanner Pool

**Status**: ⚠️ 50% DONE
**Priority**: HIGH
**Effort**: ~3 hours
**Depends On**: Task 4.6

### Goal

Add result validation after export, detect authentication failures, and store validation results.

### Current State

**File**: `worker/scanner_worker.py`

Current `_poll_until_complete()` (lines 278-301):
- ✅ Exports results to `scan_native.nessus`
- ✅ Marks task as COMPLETED
- ❌ NO validation step
- ❌ NO authentication detection

### Implementation Checklist

#### 4.5.1: Create NessusValidator class

- [ ] **File**: `scanners/nessus_validator.py` (NEW)
- [ ] Create validation logic:

```python
"""Nessus scan result validator with authentication detection."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a Nessus scan."""
    is_valid: bool
    error: Optional[str] = None
    warnings: List[str] = None
    stats: Dict[str, Any] = None
    authentication_status: str = "unknown"  # success|failed|partial|not_applicable

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.stats is None:
            self.stats = {}


class NessusValidator:
    """
    Validates Nessus scan results with authentication detection.

    Key Features:
    - XML structure validation
    - Host count verification
    - Authentication status from plugin 19506
    - Authenticated plugin count analysis
    """

    # Plugin 19506: Nessus Scan Information (contains credential status)
    SCAN_INFO_PLUGIN_ID = "19506"

    # Plugins that ONLY work with authentication
    AUTH_REQUIRED_PLUGINS = {
        "20811": "Windows Compliance Checks",
        "21643": "Windows Local Security Checks",
        "97833": "Windows Security Update Check",
        "66334": "MS Windows Patch Enumeration",
        "12634": "Unix/Linux Local Security Checks",
        "51192": "Debian Local Security Checks",
        "33851": "Red Hat Local Security Checks",
        "22869": "Installed Software Enumeration",
    }

    # Minimum authenticated plugins for trusted scan validation
    MIN_AUTH_PLUGINS = 5

    def validate(
        self,
        nessus_file: Path,
        scan_type: str = "untrusted",
        expected_hosts: int = 0
    ) -> ValidationResult:
        """
        Validate Nessus scan results.

        Args:
            nessus_file: Path to .nessus file
            scan_type: "untrusted"|"trusted_basic"|"trusted_privileged"
            expected_hosts: Expected host count (0 = don't check)

        Returns:
            ValidationResult with is_valid, stats, authentication_status
        """
        warnings = []
        stats = {}

        # 1. File existence check
        if not nessus_file.exists():
            return ValidationResult(
                is_valid=False,
                error=f"Results file not found: {nessus_file}",
                authentication_status="unknown"
            )

        # 2. File size check
        file_size = nessus_file.stat().st_size
        stats["file_size_bytes"] = file_size

        if file_size < 500:
            return ValidationResult(
                is_valid=False,
                error=f"Results file too small ({file_size} bytes)",
                stats=stats,
                authentication_status="unknown"
            )

        # 3. XML parsing
        try:
            tree = ET.parse(nessus_file)
            root = tree.getroot()
        except ET.ParseError as e:
            return ValidationResult(
                is_valid=False,
                error=f"Invalid XML: {e}",
                stats=stats,
                authentication_status="unknown"
            )

        # 4. Host analysis
        hosts = root.findall(".//ReportHost")
        stats["hosts_scanned"] = len(hosts)

        if len(hosts) == 0:
            return ValidationResult(
                is_valid=False,
                error="No hosts in scan results",
                stats=stats,
                authentication_status="unknown"
            )

        if expected_hosts > 0 and len(hosts) < expected_hosts:
            warnings.append(
                f"Host count ({len(hosts)}) less than expected ({expected_hosts})"
            )

        # 5. Plugin analysis
        all_plugins = root.findall(".//ReportItem")
        stats["total_plugins"] = len(all_plugins)

        # Count authenticated plugins
        auth_plugin_count = 0
        for item in all_plugins:
            plugin_id = item.get("pluginID", "")
            if plugin_id in self.AUTH_REQUIRED_PLUGINS:
                auth_plugin_count += 1

        stats["auth_plugins_found"] = auth_plugin_count

        # 6. Authentication status detection
        cred_status = self._parse_credentialed_status(root)
        stats["credentialed_status_raw"] = cred_status

        # Determine authentication status
        if scan_type == "untrusted":
            auth_status = "not_applicable"
        elif cred_status == "yes":
            auth_status = "success"
        elif cred_status == "no":
            auth_status = "failed"
        elif cred_status == "partial":
            auth_status = "partial"
        elif auth_plugin_count >= self.MIN_AUTH_PLUGINS:
            # Fallback: infer from plugin count
            auth_status = "success"
        elif scan_type in ("trusted_basic", "trusted_privileged"):
            # Trusted scan but no auth evidence
            auth_status = "failed"
        else:
            auth_status = "unknown"

        # 7. Validation based on scan type
        if scan_type in ("trusted_basic", "trusted_privileged"):
            if auth_status == "failed":
                return ValidationResult(
                    is_valid=False,
                    error=(
                        f"Authentication FAILED for {scan_type} scan. "
                        f"Plugin 19506 reports: Credentialed checks = {cred_status or 'not found'}. "
                        f"Only {auth_plugin_count} authenticated plugins found (minimum: {self.MIN_AUTH_PLUGINS}). "
                        f"Results contain only network-level data."
                    ),
                    warnings=warnings,
                    stats=stats,
                    authentication_status=auth_status
                )
            elif auth_status == "partial":
                warnings.append(
                    f"Partial authentication: some hosts authenticated, some failed"
                )

        # 8. Vulnerability counts
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for item in all_plugins:
            severity = int(item.get("severity", "0"))
            if severity == 4:
                severity_counts["critical"] += 1
            elif severity == 3:
                severity_counts["high"] += 1
            elif severity == 2:
                severity_counts["medium"] += 1
            elif severity == 1:
                severity_counts["low"] += 1
            else:
                severity_counts["info"] += 1

        stats["severity_counts"] = severity_counts
        stats["total_vulnerabilities"] = sum(
            v for k, v in severity_counts.items() if k != "info"
        )

        return ValidationResult(
            is_valid=True,
            warnings=warnings,
            stats=stats,
            authentication_status=auth_status
        )

    def _parse_credentialed_status(self, root: ET.Element) -> Optional[str]:
        """
        Parse plugin 19506 output for credential status.

        Looks for: "Credentialed checks : yes|no|partial"

        Returns:
            "yes", "no", "partial", or None if not found
        """
        for item in root.findall(".//ReportItem"):
            if item.get("pluginID") == self.SCAN_INFO_PLUGIN_ID:
                output = item.findtext("plugin_output", "")
                for line in output.split("\n"):
                    line_lower = line.lower()
                    if "credentialed checks" in line_lower:
                        if "yes" in line_lower:
                            return "yes"
                        elif "no" in line_lower:
                            return "no"
                        elif "partial" in line_lower:
                            return "partial"
        return None


def validate_scan_results(
    nessus_file: Path,
    scan_type: str = "untrusted",
    expected_hosts: int = 0
) -> ValidationResult:
    """Convenience function for validation."""
    validator = NessusValidator()
    return validator.validate(nessus_file, scan_type, expected_hosts)
```

#### 4.5.2: Integrate validator into worker

- [ ] **File**: `worker/scanner_worker.py`
- [ ] Add import at top:

```python
from scanners.nessus_validator import validate_scan_results
```

- [ ] Modify `_poll_until_complete()` after export (around line 290):

```python
# Save results to task directory
task_dir = self.task_manager.data_dir / task_id
task_dir.mkdir(parents=True, exist_ok=True)
results_file = task_dir / "scan_native.nessus"
results_file.write_bytes(results)

logger.info(
    f"[{task_id}] Results saved: {results_file} "
    f"({len(results)} bytes)"
)

# === NEW: Validation step ===
scan_type = self._get_scan_type_from_task(task_id)
validation = validate_scan_results(
    nessus_file=results_file,
    scan_type=scan_type
)

if validation.is_valid:
    # Success - mark completed with validation data
    self.task_manager.mark_completed_with_validation(
        task_id,
        validation_stats=validation.stats,
        validation_warnings=validation.warnings,
        authentication_status=validation.authentication_status
    )
    logger.info(
        f"[{task_id}] Task completed successfully",
        extra={
            "authentication_status": validation.authentication_status,
            "hosts_scanned": validation.stats.get("hosts_scanned", 0),
            "total_vulnerabilities": validation.stats.get("total_vulnerabilities", 0)
        }
    )
else:
    # Validation failed (e.g., auth failure)
    self.task_manager.mark_failed_with_validation(
        task_id,
        error_message=validation.error,
        validation_stats=validation.stats,
        authentication_status=validation.authentication_status
    )
    logger.warning(
        f"[{task_id}] Scan validation failed: {validation.error}",
        extra={"authentication_status": validation.authentication_status}
    )
    # Don't return - let finally block clean up
    raise ValueError(validation.error)

return  # Success path
```

#### 4.5.3: Add helper to get scan_type from task

- [ ] **File**: `worker/scanner_worker.py`
- [ ] Add method to `ScannerWorker` class:

```python
def _get_scan_type_from_task(self, task_id: str) -> str:
    """Get scan_type from task metadata."""
    task = self.task_manager.get_task(task_id)
    if task:
        return task.scan_type
    return "untrusted"
```

### Acceptance Criteria

- [ ] `scanners/nessus_validator.py` exists and is importable
- [ ] Validator correctly parses plugin 19506 for credential status
- [ ] Trusted scans fail validation if authentication failed
- [ ] Validation stats stored in task.json
- [ ] Worker logs authentication status

### Test Commands

```bash
# Test validator standalone
docker compose exec mcp-api python -c "
from pathlib import Path
from scanners.nessus_validator import NessusValidator

validator = NessusValidator()

# Test with existing scan result (if available)
test_file = Path('/app/data/tasks').glob('*/scan_native.nessus')
for f in list(test_file)[:1]:
    result = validator.validate(f, scan_type='untrusted')
    print(f'File: {f}')
    print(f'Valid: {result.is_valid}')
    print(f'Auth Status: {result.authentication_status}')
    print(f'Stats: {result.stats}')
    print(f'Warnings: {result.warnings}')
"
```

---

## Task 4.3: Enhanced MCP Tools (Finish)

**Status**: ⚠️ 70% DONE
**Priority**: MEDIUM
**Effort**: ~2 hours

### Current State

**File**: `tools/mcp_server.py`

Already implemented:
- ✅ `scanner_pool` parameter on all scan tools
- ✅ Pool validation and routing
- ✅ Load-based scanner selection

Missing:
- ❌ `scanner_instance` returned in response (currently only selected, not returned)
- ❌ Scanner URL in response
- ❌ Estimated wait time

### Implementation Checklist

#### 4.3.1: Enhance run_untrusted_scan response

- [ ] **File**: `tools/mcp_server.py`
- [ ] Add scanner URL to response (around line 200):

```python
# Get scanner URL for transparency
scanner_info = scanner_registry.get_instance(pool=target_pool, instance_id=selected_instance)
scanner_url = scanner_info.url if hasattr(scanner_info, 'url') else "unknown"

return {
    "task_id": task_id,
    "trace_id": trace_id,
    "status": "queued",
    "scanner_pool": target_pool,
    "scanner_instance": selected_instance,
    "scanner_url": scanner_url,  # NEW
    "queue_position": queue_depth,
    "estimated_wait_minutes": queue_depth * 15,  # NEW: rough estimate
    "message": "Scan enqueued successfully. Worker will process asynchronously."
}
```

#### 4.3.2: Add get_estimated_wait_time() helper

- [ ] **File**: `tools/mcp_server.py`
- [ ] Add function:

```python
def get_estimated_wait_time(queue_depth: int, avg_scan_minutes: int = 15) -> int:
    """
    Estimate wait time based on queue position.

    Simple model: queue_position * average_scan_duration

    Args:
        queue_depth: Position in queue
        avg_scan_minutes: Average scan duration (default: 15 min)

    Returns:
        Estimated wait time in minutes
    """
    return queue_depth * avg_scan_minutes
```

### Acceptance Criteria

- [ ] Response includes `scanner_url`
- [ ] Response includes `estimated_wait_minutes`
- [ ] All scan tools return consistent response format

---

## Task 4.7: Enhanced Status API

**Status**: 🔴 NOT STARTED
**Priority**: MEDIUM
**Effort**: ~2 hours
**Depends On**: Task 4.6

### Goal

Expose validation results, authentication status, and troubleshooting hints in status responses.

### Implementation Checklist

#### 4.7.1: Enhance get_scan_status response

- [ ] **File**: `tools/mcp_server.py` (lines 211-272)
- [ ] Add validation fields to response:

```python
@mcp.tool()
async def get_scan_status(task_id: str) -> dict:
    """Get current status of scan task."""
    task = task_manager.get_task(task_id)

    if not task:
        return {"error": f"Task {task_id} not found"}

    response = {
        "task_id": task.task_id,
        "trace_id": task.trace_id,
        "status": task.status,
        "scanner_pool": task.scanner_pool or task.scanner_type,
        "scanner_type": task.scanner_type,
        "scanner_instance": task.scanner_instance_id,
        "nessus_scan_id": task.nessus_scan_id,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error_message": task.error_message,

        # Phase 4: Validation fields
        "authentication_status": task.authentication_status,
        "validation_warnings": task.validation_warnings,
    }

    # Add results_summary for completed tasks
    if task.status == "completed" and task.validation_stats:
        response["results_summary"] = {
            "hosts_scanned": task.validation_stats.get("hosts_scanned", 0),
            "total_vulnerabilities": task.validation_stats.get("total_vulnerabilities", 0),
            "severity_breakdown": task.validation_stats.get("severity_counts", {}),
            "file_size_kb": round(task.validation_stats.get("file_size_bytes", 0) / 1024, 1),
            "auth_plugins_found": task.validation_stats.get("auth_plugins_found", 0),
        }

    # Add troubleshooting for failed auth
    if task.authentication_status == "failed":
        response["troubleshooting"] = {
            "likely_cause": "Credentials rejected or inaccessible target",
            "next_steps": [
                "Verify credentials in scanner configuration",
                "Check target allows SSH/WinRM from scanner IP",
                "Verify target firewall rules",
                "Check credential permissions on target",
                "Review scan logs for specific error"
            ]
        }

    # Get live progress if running
    if task.status == "running" and task.nessus_scan_id:
        try:
            pool = task.scanner_pool or task.scanner_type
            scanner = scanner_registry.get_instance(
                pool=pool,
                instance_id=task.scanner_instance_id
            )
            status_info = await scanner.get_status(task.nessus_scan_id)
            response["progress"] = status_info.get("progress", 0)
            response["scanner_status"] = status_info.get("status")
        except Exception as e:
            response["scanner_error"] = str(e)

    return response
```

### Acceptance Criteria

- [ ] Completed tasks show `results_summary`
- [ ] Failed auth tasks show `troubleshooting` section
- [ ] `authentication_status` always present (or null)
- [ ] `validation_warnings` included when present

---

## Task 4.8: Per-Scanner Prometheus Metrics

**Status**: 🔴 NOT STARTED
**Priority**: MEDIUM
**Effort**: ~3 hours

### Goal

Add pool-level metrics for monitoring scanner utilization and validation failures.

### Current State

**File**: `core/metrics.py`

Already has:
- ✅ `nessus_scanner_active_scans{scanner_instance}`
- ✅ `nessus_scanner_capacity{scanner_instance}`
- ✅ `nessus_scanner_utilization_pct{scanner_instance}`
- ✅ `nessus_pool_total_capacity`
- ✅ `nessus_pool_total_active`

Missing:
- ❌ Pool-level queue depth
- ❌ Validation failure counters
- ❌ Authentication failure counters

### Implementation Checklist

#### 4.8.1: Add missing metrics

- [ ] **File**: `core/metrics.py`
- [ ] Add new metrics:

```python
# Pool-level queue metrics
pool_queue_depth = Gauge(
    "nessus_pool_queue_depth",
    "Number of tasks queued for pool",
    ["pool"]
)

# Validation metrics
validation_total = Counter(
    "nessus_validation_total",
    "Total validations performed",
    ["pool", "result"]  # result: success, failed
)

validation_failures = Counter(
    "nessus_validation_failures_total",
    "Validation failures by reason",
    ["pool", "reason"]  # reason: auth_failed, xml_invalid, empty_scan, etc.
)

auth_failures = Counter(
    "nessus_auth_failures_total",
    "Authentication failures",
    ["pool", "scan_type"]
)
```

#### 4.8.2: Add metric recording helpers

- [ ] **File**: `core/metrics.py`
- [ ] Add helper functions:

```python
def record_validation_result(pool: str, is_valid: bool):
    """Record validation result."""
    result = "success" if is_valid else "failed"
    validation_total.labels(pool=pool, result=result).inc()


def record_validation_failure(pool: str, reason: str):
    """Record validation failure with reason."""
    validation_failures.labels(pool=pool, reason=reason).inc()


def record_auth_failure(pool: str, scan_type: str):
    """Record authentication failure."""
    auth_failures.labels(pool=pool, scan_type=scan_type).inc()


def update_pool_queue_depth(pool: str, depth: int):
    """Update queue depth for a pool."""
    pool_queue_depth.labels(pool=pool).set(depth)
```

#### 4.8.3: Integrate metrics in worker

- [ ] **File**: `worker/scanner_worker.py`
- [ ] Add import and calls in validation section:

```python
from core.metrics import (
    record_validation_result,
    record_validation_failure,
    record_auth_failure
)

# In validation section of _poll_until_complete:
if validation.is_valid:
    record_validation_result(scanner_pool, True)
else:
    record_validation_result(scanner_pool, False)

    # Categorize failure reason
    if validation.authentication_status == "failed":
        record_validation_failure(scanner_pool, "auth_failed")
        record_auth_failure(scanner_pool, scan_type)
    elif "XML" in str(validation.error):
        record_validation_failure(scanner_pool, "xml_invalid")
    elif "empty" in str(validation.error).lower():
        record_validation_failure(scanner_pool, "empty_scan")
    else:
        record_validation_failure(scanner_pool, "other")
```

### Acceptance Criteria

- [ ] `/metrics` shows `nessus_pool_queue_depth{pool="nessus"}`
- [ ] `/metrics` shows `nessus_validation_failures_total{pool, reason}`
- [ ] `/metrics` shows `nessus_auth_failures_total{pool, scan_type}`
- [ ] Metrics increment correctly during scan lifecycle

### Test Commands

```bash
# Check metrics endpoint
curl -s http://localhost:8836/metrics | grep nessus_pool
curl -s http://localhost:8836/metrics | grep nessus_validation
curl -s http://localhost:8836/metrics | grep nessus_auth
```

---

## Task 4.9: Production Docker Configuration

**Status**: 🔴 NOT STARTED
**Priority**: MEDIUM
**Effort**: ~4 hours

### Goal

Create production-ready Docker Compose with resource limits, multi-worker support, and proper restart policies.

### Implementation Checklist

#### 4.9.1: Create prod directory structure

- [ ] Create `prod/` directory
- [ ] Create `prod/docker-compose.yml`
- [ ] Create `prod/Dockerfile.api`
- [ ] Create `prod/Dockerfile.worker`
- [ ] Create `prod/.env.prod.example`

#### 4.9.2: Production docker-compose.yml

- [ ] **File**: `prod/docker-compose.yml`

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: nessus-mcp-redis-prod
    volumes:
      - redis_data:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: always
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    networks:
      - mcp-network

  mcp-api:
    build:
      context: ..
      dockerfile: prod/Dockerfile.api
    image: nessus-mcp-api:prod
    container_name: nessus-mcp-api-prod
    ports:
      - "${MCP_PORT:-8836}:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/app/data/tasks
      - SCANNER_CONFIG=/app/config/scanners.yaml
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ../data:/app/data
      - ../config:/app/config:ro
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
    networks:
      - mcp-network

  worker-main:
    build:
      context: ..
      dockerfile: prod/Dockerfile.worker
    image: nessus-mcp-worker:prod
    container_name: nessus-mcp-worker-main
    environment:
      - REDIS_URL=redis://redis:6379
      - DATA_DIR=/app/data/tasks
      - SCANNER_CONFIG=/app/config/scanners.yaml
      - WORKER_POOLS=nessus
      - MAX_CONCURRENT_SCANS=${MAX_CONCURRENT_SCANS:-5}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ../data:/app/data
      - ../config:/app/config:ro
    depends_on:
      redis:
        condition: service_healthy
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
    networks:
      - mcp-network

networks:
  mcp-network:
    driver: bridge

volumes:
  redis_data:
```

#### 4.9.3: Production API Dockerfile

- [ ] **File**: `prod/Dockerfile.api`

```dockerfile
# Multi-stage build for minimal production image
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements-api.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements-api.txt

# Production image
FROM python:3.12-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY core/ ./core/
COPY scanners/ ./scanners/
COPY schema/ ./schema/
COPY tools/ ./tools/
COPY run_server.py .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "tools.mcp_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 4.9.4: Production Worker Dockerfile

- [ ] **File**: `prod/Dockerfile.worker`

```dockerfile
# Multi-stage build for minimal production image
FROM python:3.12-slim as builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements-api.txt

# Production image
FROM python:3.12-slim

WORKDIR /app

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY core/ ./core/
COPY scanners/ ./scanners/
COPY worker/ ./worker/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run worker
CMD ["python", "-m", "worker.scanner_worker"]
```

#### 4.9.5: Environment template

- [ ] **File**: `prod/.env.prod.example`

```bash
# Production Environment Configuration

# MCP Server
MCP_PORT=8836
LOG_LEVEL=INFO

# Worker
MAX_CONCURRENT_SCANS=5

# Scanner credentials (set in production)
NESSUS_URL=https://nessus.example.com:8834
NESSUS_USERNAME=admin
NESSUS_PASSWORD=changeme
```

### Acceptance Criteria

- [ ] `docker compose -f prod/docker-compose.yml up -d` starts all services
- [ ] Health check passes: `curl http://localhost:8836/health`
- [ ] Worker processes scans correctly
- [ ] Containers restart automatically after failure

---

## Task 4.10: TTL Housekeeping

**Status**: 🔴 NOT STARTED
**Priority**: LOW
**Effort**: ~2 hours

### Goal

Automatic cleanup of old completed/failed tasks to prevent disk exhaustion.

### Implementation Checklist

#### 4.10.1: Create housekeeping module

- [ ] **File**: `core/housekeeping.py` (NEW)

```python
"""TTL-based task cleanup."""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from core.metrics import ttl_deletions_total

logger = logging.getLogger(__name__)


class Housekeeper:
    """
    Cleans up old task directories based on TTL.

    Default retention:
    - Completed tasks: 7 days
    - Failed tasks: 30 days
    """

    def __init__(
        self,
        data_dir: str = "/app/data/tasks",
        completed_ttl_days: int = 7,
        failed_ttl_days: int = 30
    ):
        self.data_dir = Path(data_dir)
        self.completed_ttl = timedelta(days=completed_ttl_days)
        self.failed_ttl = timedelta(days=failed_ttl_days)

    def cleanup(self) -> dict:
        """
        Run cleanup cycle.

        Returns:
            Dict with deleted_count, freed_bytes, errors
        """
        now = datetime.utcnow()
        deleted = 0
        freed = 0
        errors = []

        for task_dir in self.data_dir.iterdir():
            if not task_dir.is_dir():
                continue

            task_file = task_dir / "task.json"
            if not task_file.exists():
                continue

            try:
                # Check modification time
                mtime = datetime.fromtimestamp(task_file.stat().st_mtime)
                age = now - mtime

                # Read status
                import json
                with open(task_file) as f:
                    task = json.load(f)

                status = task.get("status", "unknown")

                # Determine if should delete
                should_delete = False
                if status == "completed" and age > self.completed_ttl:
                    should_delete = True
                elif status in ("failed", "timeout") and age > self.failed_ttl:
                    should_delete = True

                if should_delete:
                    # Calculate size before deletion
                    dir_size = sum(f.stat().st_size for f in task_dir.rglob("*") if f.is_file())

                    # Delete
                    shutil.rmtree(task_dir)

                    deleted += 1
                    freed += dir_size
                    ttl_deletions_total.inc()

                    logger.info(
                        f"Deleted task {task_dir.name} (status={status}, age={age.days}d)"
                    )

            except Exception as e:
                errors.append(f"{task_dir.name}: {e}")
                logger.error(f"Error cleaning {task_dir.name}: {e}")

        return {
            "deleted_count": deleted,
            "freed_bytes": freed,
            "freed_mb": round(freed / 1024 / 1024, 2),
            "errors": errors
        }


async def run_periodic_cleanup(
    data_dir: str = "/app/data/tasks",
    interval_hours: int = 1
):
    """
    Run cleanup periodically (for integration into worker).

    Args:
        data_dir: Task data directory
        interval_hours: Hours between cleanup runs
    """
    import asyncio

    housekeeper = Housekeeper(data_dir=data_dir)

    while True:
        try:
            result = housekeeper.cleanup()
            if result["deleted_count"] > 0:
                logger.info(
                    f"Housekeeping: deleted {result['deleted_count']} tasks, "
                    f"freed {result['freed_mb']} MB"
                )
        except Exception as e:
            logger.error(f"Housekeeping error: {e}")

        await asyncio.sleep(interval_hours * 3600)
```

#### 4.10.2: Integrate into worker startup

- [ ] **File**: `worker/scanner_worker.py`
- [ ] Add to `main()`:

```python
from core.housekeeping import run_periodic_cleanup

# In main(), after worker.start():
asyncio.create_task(run_periodic_cleanup(data_dir=data_dir))
```

### Acceptance Criteria

- [ ] Old completed tasks deleted after 7 days
- [ ] Old failed tasks deleted after 30 days
- [ ] `nessus_ttl_deletions_total` metric increments
- [ ] Cleanup runs hourly

---

## Task 4.11: DLQ Handler CLI

**Status**: 🔴 NOT STARTED
**Priority**: LOW
**Effort**: ~3 hours

### Goal

Admin CLI for inspecting and managing Dead Letter Queue tasks.

### Implementation Checklist

#### 4.11.1: Create admin CLI

- [ ] **File**: `tools/admin_cli.py` (NEW)

```python
#!/usr/bin/env python3
"""Admin CLI for DLQ management."""

import argparse
import json
import os
import sys
from datetime import datetime
from tabulate import tabulate

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.queue import TaskQueue


def list_dlq(queue: TaskQueue, pool: str, limit: int = 20):
    """List tasks in Dead Letter Queue."""
    dlq_tasks = queue.list_dlq(pool=pool, limit=limit)

    if not dlq_tasks:
        print(f"No tasks in DLQ for pool: {pool}")
        return

    rows = []
    for task in dlq_tasks:
        rows.append([
            task.get("task_id", "?")[:20],
            task.get("scan_type", "?"),
            task.get("error", "?")[:50],
            task.get("failed_at", "?")[:19],
        ])

    print(f"\nDead Letter Queue: {pool}")
    print(tabulate(rows, headers=["Task ID", "Type", "Error", "Failed At"]))
    print(f"\nTotal: {len(dlq_tasks)}")


def inspect_dlq(queue: TaskQueue, pool: str, task_id: str):
    """Show detailed info for a DLQ task."""
    task = queue.get_dlq_task(pool=pool, task_id=task_id)

    if not task:
        print(f"Task {task_id} not found in DLQ")
        return

    print(json.dumps(task, indent=2))


def retry_dlq(queue: TaskQueue, pool: str, task_id: str):
    """Move task from DLQ back to main queue."""
    success = queue.retry_dlq_task(pool=pool, task_id=task_id)

    if success:
        print(f"✅ Task {task_id} moved to main queue")
    else:
        print(f"❌ Failed to retry task {task_id}")


def purge_dlq(queue: TaskQueue, pool: str):
    """Clear all tasks from DLQ."""
    count = queue.purge_dlq(pool=pool)
    print(f"✅ Purged {count} tasks from DLQ")


def stats(queue: TaskQueue, pool: str):
    """Show queue statistics."""
    main_depth = queue.get_queue_depth(pool=pool)
    dlq_depth = queue.get_dlq_depth(pool=pool)

    print(f"\nQueue Statistics: {pool}")
    print(f"  Main queue depth: {main_depth}")
    print(f"  DLQ depth: {dlq_depth}")


def main():
    parser = argparse.ArgumentParser(description="Nessus MCP Admin CLI")
    parser.add_argument("--redis-url", default=os.getenv("REDIS_URL", "redis://localhost:6379"))
    parser.add_argument("--pool", default="nessus", help="Scanner pool name")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-dlq
    list_parser = subparsers.add_parser("list-dlq", help="List DLQ tasks")
    list_parser.add_argument("--limit", type=int, default=20)

    # inspect-dlq
    inspect_parser = subparsers.add_parser("inspect-dlq", help="Inspect DLQ task")
    inspect_parser.add_argument("task_id", help="Task ID to inspect")

    # retry-dlq
    retry_parser = subparsers.add_parser("retry-dlq", help="Retry DLQ task")
    retry_parser.add_argument("task_id", help="Task ID to retry")

    # purge-dlq
    purge_parser = subparsers.add_parser("purge-dlq", help="Purge all DLQ tasks")
    purge_parser.add_argument("--confirm", action="store_true", required=True)

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show queue stats")

    args = parser.parse_args()

    queue = TaskQueue(redis_url=args.redis_url)

    if args.command == "list-dlq":
        list_dlq(queue, args.pool, args.limit)
    elif args.command == "inspect-dlq":
        inspect_dlq(queue, args.pool, args.task_id)
    elif args.command == "retry-dlq":
        retry_dlq(queue, args.pool, args.task_id)
    elif args.command == "purge-dlq":
        purge_dlq(queue, args.pool)
    elif args.command == "stats":
        stats(queue, args.pool)


if __name__ == "__main__":
    main()
```

#### 4.11.2: Add queue DLQ methods

- [ ] **File**: `core/queue.py`
- [ ] Add methods to `TaskQueue` class:

```python
def list_dlq(self, pool: str, limit: int = 20) -> list:
    """List tasks in DLQ."""
    dlq_key = self._dlq_key(pool)
    items = self.redis_client.zrange(dlq_key, 0, limit - 1, withscores=True)

    tasks = []
    for item, score in items:
        task = json.loads(item)
        task["failed_at"] = datetime.fromtimestamp(score).isoformat()
        tasks.append(task)

    return tasks


def get_dlq_task(self, pool: str, task_id: str) -> Optional[dict]:
    """Get specific task from DLQ."""
    dlq_key = self._dlq_key(pool)
    items = self.redis_client.zrange(dlq_key, 0, -1)

    for item in items:
        task = json.loads(item)
        if task.get("task_id") == task_id:
            return task

    return None


def retry_dlq_task(self, pool: str, task_id: str) -> bool:
    """Move task from DLQ to main queue."""
    task = self.get_dlq_task(pool, task_id)
    if not task:
        return False

    # Remove from DLQ
    dlq_key = self._dlq_key(pool)
    self.redis_client.zrem(dlq_key, json.dumps(task))

    # Clear error and re-queue
    task.pop("error", None)
    task.pop("failed_at", None)
    self.enqueue(task, pool=pool)

    return True


def purge_dlq(self, pool: str) -> int:
    """Clear all tasks from DLQ."""
    dlq_key = self._dlq_key(pool)
    count = self.redis_client.zcard(dlq_key)
    self.redis_client.delete(dlq_key)
    return count


def get_dlq_depth(self, pool: str) -> int:
    """Get DLQ depth for pool."""
    dlq_key = self._dlq_key(pool)
    return self.redis_client.zcard(dlq_key)
```

### Acceptance Criteria

- [ ] `python -m tools.admin_cli stats` shows queue depths
- [ ] `python -m tools.admin_cli list-dlq` shows failed tasks
- [ ] `python -m tools.admin_cli retry-dlq <task_id>` re-queues task
- [ ] `python -m tools.admin_cli purge-dlq --confirm` clears DLQ

---

## Task 4.12: Circuit Breaker

**Status**: 🔴 NOT STARTED
**Priority**: LOW
**Effort**: ~4 hours
**Depends On**: Task 4.5

### Goal

Protect system from cascading failures when scanners become unhealthy.

### Implementation Checklist

#### 4.12.1: Create circuit breaker module

- [ ] **File**: `core/circuit_breaker.py` (NEW)

```python
"""Circuit breaker for scanner failure protection."""

import time
import logging
from typing import Dict
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """
    Circuit breaker per scanner instance.

    States:
    - CLOSED: Normal operation, track failures
    - OPEN: Too many failures, reject all requests
    - HALF_OPEN: After cooldown, allow one test request

    Configuration:
    - failure_threshold: Failures before opening (default: 5)
    - cooldown_seconds: Time before half-open (default: 300)
    - success_threshold: Successes to close (default: 2)
    """
    instance_key: str
    failure_threshold: int = 5
    cooldown_seconds: int = 300
    success_threshold: int = 2

    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    success_count: int = field(default=0)
    last_failure_time: float = field(default=0)

    def record_success(self):
        """Record successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._close()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def record_failure(self):
        """Record failed operation."""
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failure during test, reopen
            self._open()
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self._open()

    def is_available(self) -> bool:
        """Check if requests should be allowed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if cooldown elapsed
            if time.time() - self.last_failure_time >= self.cooldown_seconds:
                self._half_open()
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow test request
            return True

        return False

    def _open(self):
        """Open circuit (reject requests)."""
        self.state = CircuitState.OPEN
        self.success_count = 0
        logger.warning(f"Circuit OPEN for {self.instance_key}")

    def _half_open(self):
        """Half-open circuit (allow test)."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        logger.info(f"Circuit HALF-OPEN for {self.instance_key}")

    def _close(self):
        """Close circuit (normal operation)."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info(f"Circuit CLOSED for {self.instance_key}")


class CircuitBreakerRegistry:
    """Manages circuit breakers for all scanner instances."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, instance_key: str) -> CircuitBreaker:
        """Get or create circuit breaker for instance."""
        if instance_key not in self._breakers:
            self._breakers[instance_key] = CircuitBreaker(instance_key=instance_key)
        return self._breakers[instance_key]

    def is_available(self, instance_key: str) -> bool:
        """Check if instance is available."""
        return self.get_breaker(instance_key).is_available()

    def record_success(self, instance_key: str):
        """Record successful operation."""
        self.get_breaker(instance_key).record_success()

    def record_failure(self, instance_key: str):
        """Record failed operation."""
        self.get_breaker(instance_key).record_failure()

    def get_status(self) -> dict:
        """Get status of all breakers."""
        return {
            key: {
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "available": breaker.is_available()
            }
            for key, breaker in self._breakers.items()
        }
```

#### 4.12.2: Integrate into worker

- [ ] **File**: `worker/scanner_worker.py`
- [ ] Add circuit breaker checks:

```python
from core.circuit_breaker import CircuitBreakerRegistry

# In __init__:
self.circuit_breakers = CircuitBreakerRegistry()

# In _process_task, before acquiring scanner:
if not self.circuit_breakers.is_available(instance_key):
    logger.warning(f"[{task_id}] Scanner {instance_key} circuit open, requeuing")
    self.queue.enqueue(task_data, pool=scanner_pool)
    return

# After successful completion:
self.circuit_breakers.record_success(instance_key)

# In exception handler:
self.circuit_breakers.record_failure(instance_key)
```

### Acceptance Criteria

- [ ] Scanner disabled after 5 consecutive failures
- [ ] Scanner re-enabled after 5 minute cooldown
- [ ] Tasks re-queued when scanner unavailable
- [ ] Circuit state visible in logs

---

## Session Handoff Checklist

When ending a session, update this section:

### Current Session Status

**Date**: 2025-11-25
**Session Focus**: Planning and documentation
**Completed This Session**:
- [x] Committed pool architecture (b9e1ef9)
- [x] Created detailed implementation plan
- [x] Documented all remaining tasks

### Next Session Should

1. Start with Task 4.6 (Enhanced Task Metadata)
2. Then Task 4.5 (Worker Enhancement)
3. Run tests after each task

### Quick Start Commands

```bash
# Start services
cd /home/nessus/projects/nessus-api/mcp-server
docker compose up -d

# Run tests
docker compose exec mcp-api pytest tests/unit/ -v

# Check health
curl http://localhost:8836/health

# View logs
docker compose logs -f worker
```

### Files to Edit (Next Session)

1. `core/types.py` - Add validation fields to Task
2. `core/task_manager.py` - Add validation helper methods
3. `scanners/nessus_validator.py` - Create (NEW)
4. `worker/scanner_worker.py` - Integrate validator

---

## Version History

| Date | Changes | Commit |
|------|---------|--------|
| 2025-11-25 | Created implementation guide | 403429c |
| 2025-11-25 | Pool architecture complete | b9e1ef9 |
