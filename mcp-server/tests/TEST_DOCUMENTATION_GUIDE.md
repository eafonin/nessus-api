# Test Documentation Guide

[← Test Suite](README.MD)

---

## Overview

This guide defines the format and scope for test documentation in this project. Follow this guide when creating or updating test catalogs for any layer.

**Key Principle**: Each layer directory has its own `TESTS.md` file containing only tests from that directory. This keeps documentation modular and context-efficient.

---

## File Structure

```text
tests/
├── README.MD                          # Main test suite overview
├── TEST_DOCUMENTATION_GUIDE.md        # This file - format/scope guide
├── layer01_infrastructure/
│   ├── README.MD                      # Layer overview, purpose, troubleshooting
│   └── TESTS.md                       # Test catalog for layer01 only
├── layer02_internal/
│   ├── README.MD
│   └── TESTS.md
├── layer03_external_basic/
│   ├── README.MD
│   └── TESTS.md
└── layer04_full_workflow/
    ├── README.MD
    └── TESTS.md
```

---

## TESTS.md Format

Each `TESTS.md` file follows this structure:

```markdown
# Layer NN: [Layer Name] Tests

[← Test Suite](../README.MD) | [Layer README](README.MD)

---

## Overview

Brief description of what this layer tests.
- **Test Count**: NN tests
- **Duration**: ~XX seconds/minutes
- **Marker**: `@pytest.mark.layerNN`

---

## [test_file_name.py] (N tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_function_name` | `param=value` | `expected: type` | What is tested. Pass: condition. |

---

## See Also

- Links to related documentation
```

---

## Table Format

### Column Definitions

| Column | Purpose | Format |
|--------|---------|--------|
| **Test** | Function name | `` `test_function_name` `` |
| **Arguments** | Key parameters passed | `param=value`, `fixture_name` |
| **Returns** | Expected return value/type | `expected: type` or `{"key": value}` |
| **Description** | What is tested + pass criteria | "What is tested. Pass: condition." |

### Examples

**Good**:
```markdown
| `test_dns_resolution` | `hostname` from NESSUS_URL | `ip_address: str` | Verifies hostname resolves. Pass: non-empty IP. |
| `test_opens_after_threshold` | `failure_threshold=3`, 3 failures | `state == OPEN` | Opens after threshold. Pass: state becomes OPEN. |
```

**Avoid**:
```markdown
| test_dns_resolution | hostname | ip | Tests DNS |  <!-- Missing backticks, vague description -->
```

---

## Creating a New Layer

When adding a new test layer (e.g., `layer05_performance/`):

### Step 1: Create Directory Structure

```bash
mkdir tests/layer05_performance
touch tests/layer05_performance/__init__.py
touch tests/layer05_performance/conftest.py
```

### Step 2: Create README.MD

```markdown
# Layer 05: Performance Tests

[← Test Suite](../README.MD)

---

## Purpose

[Describe what this layer tests]

**Duration**: ~XX minutes
**Marker**: `@pytest.mark.layer05`

---

## Tests

| Test File | What it checks |
|-----------|----------------|
| `test_file.py` | Brief description |

---

## Running

```bash
pytest tests/layer05_performance/ -v
pytest -m layer05 -v
```

---

## If Tests Fail

[Troubleshooting guidance]

---

## See Also

- [Layer 04: Full Workflow](../layer04_full_workflow/README.MD)
```

### Step 3: Create TESTS.md

Follow the format in [TESTS.md Format](#testsmd-format) above.

### Step 4: Update Root README.MD

Add the new layer to:
- Layer diagram in tests/README.MD
- Quick Reference table
- Directory structure listing

### Step 5: Register Pytest Marker

Add to `conftest.py`:

```python
pytest.mark.layer05 = pytest.mark.mark(
    "layer05",
    description="Performance tests"
)
```

---

## Agent Lookup Patterns

TESTS.md files are optimized for grep-based lookup. **Do NOT load full files into context.**

### Search by Test Name

```bash
# Find test by name - returns args, returns, description
grep "test_scanner_reachable" tests/layer01_infrastructure/TESTS.md
```

### Search by Functionality

```bash
# Find DLQ-related tests
grep -ri "DLQ" tests/*/TESTS.md

# Find authentication tests
grep -ri "auth\|credential\|ssh" tests/*/TESTS.md

# Find error-handling tests
grep "raises.*Error\|ValueError\|Exception" tests/*/TESTS.md
```

### Search Across All Layers

```bash
# Find all tests matching pattern
grep -rh "test_" tests/*/TESTS.md | grep "circuit"
```

---

## Generating Test Run Reports

After running tests, generate a consolidated report using the **same format as TESTS.md** plus status/duration/error columns.

### Report Format

The generated `TEST_RUN_REPORT.md` uses a **single flat table** with full file paths for grep-friendly layer extraction:

```markdown
# Test Run Report

> Generated: 2024-01-15T10:30:45
> Duration: 245.32s
> Results: 485 passed, 2 failed, 2 skipped (489 total)

---

## All Tests

| Test | File | Arguments | Returns | Description | Status | Duration | Error |
|------|------|-----------|---------|-------------|--------|----------|-------|
| `test_dns_resolution` | `layer01_infrastructure/test_nessus_connectivity.py` | `hostname` from NESSUS_URL | `ip_address: str` | Verifies hostname resolves. Pass: non-empty IP. | passed | 0.012s | |
| `test_opens_after_threshold` | `layer02_internal/test_circuit_breaker.py` | `failure_threshold=3`, 3 failures | `state == OPEN` | Opens after threshold. Pass: state becomes OPEN. | passed | 0.003s | |
| `test_timeout_handling` | `layer02_internal/test_queue.py` | `timeout=0.1` | `None` | Timeout returns None. Pass: returns None. | failed | 5.001s | AssertionError: Expected None |
```

### Agent Lookup Patterns

```bash
# Find test and its layer from report
grep "test_opens_after_threshold" tests/TEST_RUN_REPORT.md
# Output: | `test_opens_after_threshold` | `layer02_internal/test_circuit_breaker.py` | ... | passed | ...

# Extract layer from file path
grep "test_opens_after_threshold" tests/TEST_RUN_REPORT.md | grep -oE "layer[0-9]+_[a-z_]+"
# Output: layer02_internal

# Find all failed tests
grep "| failed |" tests/TEST_RUN_REPORT.md

# Find failed tests in specific layer
grep "layer02_internal.*failed" tests/TEST_RUN_REPORT.md

# Find source file for a test
grep "test_circuit_breaker" tests/TEST_RUN_REPORT.md | cut -d'|' -f3
# Output: layer02_internal/test_circuit_breaker.py
```

### Generate Report Script

Create `tests/generate_test_report.py`:

```python
#!/usr/bin/env python3
"""
Generate TEST_RUN_REPORT.md after pytest run.

Format matches TESTS.md with additional Status/Duration/Error columns.
Single flat table for grep-friendly lookup.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


def load_tests_md_data(tests_dir: Path) -> dict:
    """Load test documentation from all TESTS.md files."""
    test_docs = {}
    for tests_md in tests_dir.glob("*/TESTS.md"):
        layer = tests_md.parent.name
        content = tests_md.read_text()

        # Parse table rows: | `test_name` | args | returns | description |
        pattern = r"\| `(test_\w+)` \| ([^|]*) \| ([^|]*) \| ([^|]*) \|"
        for match in re.finditer(pattern, content):
            test_name = match.group(1)
            test_docs[test_name] = {
                "arguments": match.group(2).strip(),
                "returns": match.group(3).strip(),
                "description": match.group(4).strip(),
            }
    return test_docs


def generate_report(json_path: str, output_path: str = "TEST_RUN_REPORT.md"):
    """Generate markdown report from pytest JSON output."""
    with open(json_path) as f:
        data = json.load(f)

    # Load test documentation for Arguments/Returns/Description
    tests_dir = Path(__file__).parent
    test_docs = load_tests_md_data(tests_dir)

    summary = data.get("summary", {})
    duration = data.get("duration", 0)

    lines = [
        "# Test Run Report",
        "",
        f"> Generated: {datetime.now().isoformat()}",
        f"> Duration: {duration:.2f}s",
        f"> Results: {summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed, "
        f"{summary.get('skipped', 0)} skipped ({summary.get('total', 0)} total)",
        "",
        "---",
        "",
        "## All Tests",
        "",
        "| Test | File | Arguments | Returns | Description | Status | Duration | Error |",
        "|------|------|-----------|---------|-------------|--------|----------|-------|",
    ]

    # Sort tests by nodeid for consistent ordering
    tests = sorted(data.get("tests", []), key=lambda t: t.get("nodeid", ""))

    for test in tests:
        nodeid = test.get("nodeid", "")
        outcome = test.get("outcome", "unknown")
        test_duration = test.get("duration", 0)

        # Extract test name and file path
        # nodeid format: layer01_infrastructure/test_nessus.py::TestClass::test_name
        parts = nodeid.split("::")
        file_path = parts[0] if parts else ""
        test_name = parts[-1] if parts else nodeid

        # Get documentation from TESTS.md
        doc = test_docs.get(test_name, {})
        arguments = doc.get("arguments", "-")
        returns = doc.get("returns", "-")
        description = doc.get("description", "-")

        # Extract error for failed tests
        error = ""
        if outcome == "failed":
            longrepr = test.get("longrepr", "")
            if isinstance(longrepr, str):
                # Get first line of error, truncate
                error = longrepr.split("\n")[-1][:60].replace("|", "\\|")
            elif isinstance(longrepr, dict):
                error = str(longrepr.get("reprcrash", {}).get("message", ""))[:60]

        lines.append(
            f"| `{test_name}` | `{file_path}` | {arguments} | {returns} | "
            f"{description} | {outcome} | {test_duration:.3f}s | {error} |"
        )

    # Add summary section at end
    lines.extend([
        "",
        "---",
        "",
        "## Summary by Layer",
        "",
        "| Layer | Passed | Failed | Skipped | Total |",
        "|-------|--------|--------|---------|-------|",
    ])

    # Group by layer for summary
    layer_stats = {}
    for test in data.get("tests", []):
        nodeid = test.get("nodeid", "")
        layer = nodeid.split("/")[0] if "/" in nodeid else "unknown"
        if layer not in layer_stats:
            layer_stats[layer] = {"passed": 0, "failed": 0, "skipped": 0}
        layer_stats[layer][test.get("outcome", "unknown")] = (
            layer_stats[layer].get(test.get("outcome", "unknown"), 0) + 1
        )

    for layer in sorted(layer_stats.keys()):
        stats = layer_stats[layer]
        total = stats["passed"] + stats["failed"] + stats["skipped"]
        lines.append(
            f"| {layer} | {stats['passed']} | {stats['failed']} | {stats['skipped']} | {total} |"
        )

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Report generated: {output_path}")
    print(f"  {summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed, "
          f"{summary.get('skipped', 0)} skipped")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_test_report.py <pytest_json_output>")
        print("Example: pytest tests/ --json-report --json-report-file=results.json")
        print("         python tests/generate_test_report.py results.json")
        sys.exit(1)
    generate_report(sys.argv[1])
```

### Run Tests with JSON Output

```bash
# Run all tests and generate JSON
pytest tests/ --json-report --json-report-file=test_results.json

# Generate markdown report
python tests/generate_test_report.py test_results.json

# View report
cat TEST_RUN_REPORT.md
```

### Key Features

1. **Same format as TESTS.md** - Arguments, Returns, Description columns preserved
2. **Full file path** - `layer02_internal/test_queue.py` enables layer extraction via grep
3. **Single flat table** - All tests in one table for easy grep across entire report
4. **Status/Duration/Error** - Additional columns for test run results
5. **Summary by layer** - Aggregated pass/fail counts per layer at end

### Example Output

```markdown
# Test Run Report

> Generated: 2024-01-15T10:30:45
> Duration: 245.32s
> Results: 485 passed, 2 failed, 2 skipped (489 total)

---

## All Tests

| Test | File | Arguments | Returns | Description | Status | Duration | Error |
|------|------|-----------|---------|-------------|--------|----------|-------|
| `test_dns_resolution` | `layer01_infrastructure/test_nessus_connectivity.py` | `hostname` from NESSUS_URL | `ip_address: str` | Verifies hostname resolves. Pass: non-empty IP. | passed | 0.012s | |
| `test_opens_after_threshold` | `layer02_internal/test_circuit_breaker.py` | `failure_threshold=3`, 3 failures | `state == OPEN` | Opens after threshold. | passed | 0.003s | |
| `test_timeout_handling` | `layer02_internal/test_queue.py` | `timeout=0.1` | `None` | Timeout returns None. | failed | 5.001s | AssertionError: Expected None |

---

## Summary by Layer

| Layer | Passed | Failed | Skipped | Total |
|-------|--------|--------|---------|-------|
| layer01_infrastructure | 23 | 0 | 0 | 23 |
| layer02_internal | 340 | 2 | 1 | 343 |
| layer03_external_basic | 79 | 0 | 0 | 79 |
| layer04_full_workflow | 40 | 0 | 2 | 42 |
```

---

## Maintenance

### When to Update TESTS.md

- **Add tests**: Add new rows to the appropriate file's table
- **Modify tests**: Update the corresponding row
- **Remove tests**: Remove the row
- **Rename tests**: Update the test name in the row

### Reconciliation

Use the reconciliation script to verify documentation completeness:

```bash
python3 tests/reconcile_tests.py           # Full report
python3 tests/reconcile_tests.py --summary # Summary only
python3 tests/reconcile_tests.py --stubs   # Generate missing entries
```

---

## See Also

- [Test Suite README](README.MD) - Main test documentation
- [Testing Guide](../docs/TESTING.md) - Comprehensive testing guide
