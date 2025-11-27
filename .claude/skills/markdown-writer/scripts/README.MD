# Validation Scripts

> Automated tools for markdown quality checking and documentation analysis

## Scripts

| Script | Purpose |
|--------|---------|
| [validate_markdown.py](validate_markdown.py) | Quality validation checks |
| [analyze_docs.py](analyze_docs.py) | Documentation structure analysis |

## validate_markdown.py

Checks markdown files for common quality issues.

### Usage

```bash
python scripts/validate_markdown.py <path>
```

### Checks Performed

| Check | Description |
|-------|-------------|
| Multiple H1 | Flags documents with more than one `#` heading |
| Skipped levels | Detects heading hierarchy jumps (e.g., `##` to `####`) |
| Code block languages | Finds `` ``` `` blocks without language identifiers |
| Document length | Warns about oversized documents (>1000 lines) |

### Example Output

```
Checking: docs/API.md
  WARNING: Code block without language at line 45
  WARNING: Code block without language at line 89

Checking: docs/GUIDE.md
  ERROR: Multiple H1 headings found
  WARNING: Skipped heading level at line 67 (## to ####)

Summary: 2 files checked, 1 error, 3 warnings
```

## analyze_docs.py

Analyzes documentation structure and link integrity.

### Usage

```bash
python scripts/analyze_docs.py <path>
```

### Analysis Performed

| Analysis | Description |
|----------|-------------|
| Orphaned documents | Files with no incoming links |
| Broken links | Internal links to non-existent files |
| Broken anchors | Links to non-existent headings |
| Oversized documents | Files exceeding 1000 lines |

### Example Output

```
Documentation Analysis Report
=============================

Orphaned Documents (no incoming links):
  - docs/old-guide.md
  - docs/draft-feature.md

Broken Links:
  - README.md:45 -> docs/missing.md (file not found)
  - docs/API.md:123 -> #non-existent-section (anchor not found)

Oversized Documents:
  - docs/COMPLETE_GUIDE.md (1450 lines)

Summary:
  Total files: 25
  Orphaned: 2
  Broken links: 2
  Oversized: 1
```

## Excluded Directories

Both scripts automatically exclude:
- `node_modules/` - Package dependencies
- `.git/` - Git internals
- `venv/` - Python virtual environments
- `vendor/` - Third-party code
- `__pycache__/` - Python cache
- `.claude/skills/` - Skill templates (avoids self-validation)

## Integration

### Pre-commit Hook

```bash
#!/bin/bash
python .claude/skills/markdown-writer/scripts/validate_markdown.py . || exit 1
```

### CI Pipeline

```yaml
- name: Validate Documentation
  run: |
    python .claude/skills/markdown-writer/scripts/validate_markdown.py .
    python .claude/skills/markdown-writer/scripts/analyze_docs.py .
```

## See Also

- [Skill README](../README.md) - Main skill documentation
- [Reference Materials](../references/README.MD) - Standards and templates
- [Examples](../examples/README.md) - Usage demonstrations
