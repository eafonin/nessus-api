# Examples

> Real-world demonstrations of the markdown-writer skill

## Available Examples

| Example | File | Description |
|---------|------|-------------|
| Validation Workflow | [example-3-validation.md](example-3-validation.md) | Running validation scripts and interpreting results |

## Planned Examples

The following examples are referenced in documentation but not yet created:

| Example | Purpose |
|---------|---------|
| example-1-create-new-doc.md | Creating new documentation from scratch |
| example-2-fix-existing-doc.md | Fixing common markdown issues |
| example-4-health-audit.md | Performing documentation health audit |
| example-5-refactor-large-doc.md | Refactoring oversized documents |

## Example 3: Validation Workflow

The available example demonstrates:
- Running `validate_markdown.py` on project documentation
- Interpreting validation output
- Prioritizing fixes by severity
- Common issue patterns and solutions

### Quick Usage

```bash
# Run validation on current directory
python scripts/validate_markdown.py .

# Analyze documentation structure
python scripts/analyze_docs.py .
```

## See Also

- [Skill README](../README.md) - Main skill documentation
- [Scripts README](../scripts/README.MD) - Validation tool details
- [Reference Materials](../references/README.MD) - Standards and templates
