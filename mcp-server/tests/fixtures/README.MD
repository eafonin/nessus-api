# Test Fixtures

> Sample data files for test suite

## Files

| File | Size | Purpose |
|------|------|---------|
| `sample_scan.nessus` | ~2MB | Real Nessus scan output XML for parser and schema tests |

## Usage

Fixtures are loaded by tests via relative paths:

```python
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
sample_scan = FIXTURES_DIR / "sample_scan.nessus"
```

## Data Format

The `.nessus` file is XML containing:
- Scan metadata (policy, targets, timestamps)
- Host information (IPs, OS detection)
- Vulnerability findings (plugin output, severity, CVSS)

Used by:
- `schema/parser.py` tests - XML parsing validation
- `schema/converter.py` tests - Schema transformation
- `schema/profiles.py` tests - Field filtering
