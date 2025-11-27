# Markdown Writer Skill

> LLM-optimized documentation standards and validation tools

## Quick Navigation

| Directory | README | Description |
|-----------|--------|-------------|
| [references/](references/) | [README.MD](references/README.MD) | Standards and templates |
| [scripts/](scripts/) | [README.MD](scripts/README.MD) | Validation tools |
| [examples/](examples/) | [README_NEW.MD](examples/README_NEW.MD) | Usage demonstrations |

## Key Files

| File | Purpose |
|------|---------|
| [SKILL.md](SKILL.md) | Main skill file (Claude reads this) |
| [README.md](README.md) | Comprehensive skill documentation |
| [DEMONSTRATION.md](DEMONSTRATION.md) | Skill demonstration |
| [AUTOMATIC_LINK_VALIDATION.md](AUTOMATIC_LINK_VALIDATION.md) | Link validation guide |

## Quick Start

### For Light Edits
Read [references/MARKDOWN-QUICK-REF.md](references/MARKDOWN-QUICK-REF.md) (478 lines)

### For New Documents
Read [references/MARKDOWN-GENERATION-GUIDE.md](references/MARKDOWN-GENERATION-GUIDE.md) (1559 lines)

### For Validation
```bash
python scripts/validate_markdown.py .
python scripts/analyze_docs.py .
```

## Mission

Ensure all markdown is:
1. **LLM-Optimized** - Structured for agent consumption
2. **Semantically Grouped** - Related information clustered
3. **Properly Hierarchical** - Correct heading levels
4. **Context-Efficient** - 200-1000 lines per document
5. **Knowledge-Preserving** - No orphans or broken links

## Top 8 Pitfalls

1. Multiple H1 headings (only one allowed)
2. No language on code blocks
3. Vague link text ("here", "this")
4. External links when local should exist
5. Missing alt text on images
6. Skipping heading levels
7. No blank lines around blocks
8. Inconsistent formatting

## Directory Structure

```
markdown-writer/
├── SKILL.md                  # Main skill file
├── README.md                 # Full documentation
├── README_NEW.MD             # This navigation file
├── DEMONSTRATION.md          # Skill demo
├── AUTOMATIC_LINK_VALIDATION.md
├── references/               # Standards and templates
│   ├── README.MD
│   ├── MARKDOWN-GENERATION-GUIDE.md
│   ├── MARKDOWN-QUICK-REF.md
│   └── templates/
├── scripts/                  # Validation tools
│   ├── README.MD
│   ├── validate_markdown.py
│   └── analyze_docs.py
└── examples/                 # Usage demonstrations
    ├── README.md
    ├── README_NEW.MD
    └── example-3-validation.md
```

## See Also

- [README.md](README.md) - Full skill documentation
- [SKILL.md](SKILL.md) - Main skill definition
