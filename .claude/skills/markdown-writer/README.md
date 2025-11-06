# Markdown Writer Skill

> Production-ready skill for creating and maintaining LLM-optimized markdown documentation

## Overview

The `markdown-writer` skill ensures all markdown files in a project are properly structured for LLM agent effectiveness. It provides comprehensive guidance, validation tools, and templates to maintain high-quality, agent-readable documentation.

## Mission

Ensure ALL markdown in a project is:

1. **LLM-Optimized** - Structured for agent consumption
2. **Semantically Grouped** - Related information clustered, not scattered
3. **Properly Hierarchical** - Correct heading levels and organization
4. **Context-Efficient** - Appropriately sized for agent context windows (200-1000 lines)
5. **Knowledge-Preserving** - No orphaned documents, broken links, or lost information

## Features

### Comprehensive Guidance

- **Quick Reference** (478 lines) - For light edits, validation, quick checks
- **Full Generation Guide** (1559 lines) - For new documents, major refactoring
- **Decision Trees** - Clear workflows for different operations
- **Templates** - Pre-built templates for common document types

### Validation Tools

- **validate_markdown.py** - Automated quality checking
  - Single H1 heading verification
  - Heading hierarchy validation
  - Code block language checking
  - Document length analysis
  - Link text quality checks

- **analyze_docs.py** - Documentation structure analysis
  - Find orphaned documents
  - Identify broken links
  - Detect oversized files
  - Generate connectivity reports

### Templates

Pre-built templates for common documentation:
- Quick Start Guide
- Configuration Reference
- API Reference
- Troubleshooting Guide

## Installation

### For Claude Code

1. Copy the skill to your project's `.claude/skills/` directory:

```bash
cp -r markdown-writer ~/.claude/skills/
```

2. Or copy to project-local skills directory:

```bash
mkdir -p .claude/skills
cp -r markdown-writer .claude/skills/
```

3. The skill will be automatically available when working with markdown files

### Standalone Usage

You can use the validation scripts independently:

```bash
# Validate all markdown in current directory
python markdown-writer/scripts/validate_markdown.py .

# Analyze documentation structure
python markdown-writer/scripts/analyze_docs.py .
```

## Usage

### Quick Start

When working with markdown files, the skill activates automatically. You can explicitly invoke it:

> "Use the markdown-writer skill to create a new troubleshooting guide"

> "Validate all markdown documentation using the markdown-writer skill"

### Operation Modes

#### Mode 1: Light Operations
For minor edits, quick fixes, validation:
- Uses Quick Reference (478 lines)
- Fast, targeted changes
- Example: Fixing typos, adding links, quick validation

#### Mode 2: Heavy Operations
For new documents, major refactoring:
- Uses Full Generation Guide (1559 lines)
- Comprehensive guidance
- Example: New features docs, major rewrites

#### Mode 3: Documentation Health
For project-wide quality assessment:
- Uses validation scripts
- Identifies systemic issues
- Example: Quarterly reviews, new project onboarding

### Decision Tree

```
Working with markdown?
│
├─ Creating new document from scratch?
│  └─ MODE 2: Read FULL GUIDE
│
├─ Major refactoring (restructure, content reorganization)?
│  └─ MODE 2: Read FULL GUIDE
│
├─ Minor edits (typos, small additions, formatting)?
│  └─ MODE 1: Read QUICK REF
│
├─ Reviewing/validating existing document?
│  └─ MODE 1: Read QUICK REF
│
└─ Project-wide documentation audit?
   └─ MODE 3: Use QUICK REF + validation scripts
```

## Examples

See the [examples/](./examples/) directory for detailed demonstrations:

- **Example 1**: Creating new documentation from scratch
- **Example 2**: Fixing common markdown issues
- **Example 3**: Running validation workflow
- **Example 4**: Performing documentation health audit
- **Example 5**: Refactoring large documents

## File Structure

```
markdown-writer/
├── SKILL.md                            # Main skill file (Claude reads this)
├── README.md                           # This file
├── scripts/
│   ├── validate_markdown.py           # Validation script
│   └── analyze_docs.py                # Structure analysis script
├── references/
│   ├── markdown-quick-ref.md          # Quick reference guide (478 lines)
│   ├── markdown-generation-guide.md   # Full guide (1559 lines)
│   └── templates/
│       ├── quickstart.md              # Quick start template
│       ├── configuration.md           # Configuration reference template
│       ├── api-reference.md           # API documentation template
│       └── troubleshooting.md         # Troubleshooting guide template
└── examples/
    ├── README.md                       # Examples overview
    ├── example-1-create-new-doc.md    # Creating new docs
    ├── example-2-fix-existing-doc.md  # Fixing existing docs
    ├── example-3-validation.md        # Validation workflow
    ├── example-4-health-audit.md      # Health audit workflow
    └── example-5-refactor-large-doc.md # Refactoring workflow
```

## Key Principles

1. **Structure First** - Use appropriate templates and patterns
2. **Local Links Always** - Prefer local files over external URLs
3. **Descriptive Link Text** - Explain destination clearly
4. **Modular Design** - One topic per file, cross-link extensively
5. **Language Tags** - Always specify syntax highlighting on code blocks
6. **Scannable Content** - Short paragraphs, clear headings, examples
7. **Progressive Disclosure** - Simple to complex
8. **Examples Everywhere** - Show, don't just tell
9. **Consistent Formatting** - Follow established patterns throughout project
10. **Context Efficiency** - Keep documents focused and appropriately sized

## Top 8 Pitfalls Prevented

1. Multiple H1 headings (only one allowed)
2. No language on code blocks
3. Vague link text ("here", "this")
4. External links when local should exist
5. Missing alt text on images
6. Skipping heading levels
7. No blank lines around blocks
8. Inconsistent formatting

## Requirements

- Python 3.6+ (for validation scripts)
- Claude Code (for skill activation)

## Contributing

This skill is designed to be generic and reusable across any project. To customize for your specific needs:

1. Fork the skill directory
2. Modify templates in `references/templates/`
3. Add project-specific examples in `examples/`
4. Keep the core principles intact

## License

This skill follows Anthropic's skills repository patterns and is provided as a reference implementation.

## Version

**1.0.0** - Initial release

## Related Documentation

- [Quick Reference](./references/markdown-quick-ref.md) - Fast lookup
- [Full Generation Guide](./references/markdown-generation-guide.md) - Complete reference
- [Examples](./examples/README.md) - Real-world demonstrations
- [CommonMark Specification](https://commonmark.org/)
- [GitHub Flavored Markdown](https://github.github.com/gfm/)

## Support

For issues or questions:
1. Check the [examples](./examples/) directory
2. Review the [Quick Reference](./references/markdown-quick-ref.md)
3. Read the [Full Guide](./references/markdown-generation-guide.md)
4. Run validation scripts for automated checking
