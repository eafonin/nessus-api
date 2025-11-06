---
name: markdown-writer
description: Use this skill when creating, editing, or reviewing markdown (.md) files. Ensures documents are LLM-optimized, properly structured, semantically organized, with correct hierarchy and knowledge integrity. Automatically applies best practices for agent-readable documentation.
---

# Markdown Writer Skill

## Mission

Your mission when handling ANY markdown file operation:

1. **LLM-Optimized Structure** - Documents structured for agent consumption, not just human readers
2. **Semantic Grouping** - Related information clustered together, not scattered across files
3. **Proper Hierarchy** - Clear document organization with correct heading levels (no skips, single H1)
4. **Context-Aware Length** - Documents sized for agent context windows (200-1000 lines ideal)
5. **Knowledge Integrity** - No orphaned documents, no broken links, no lost knowledge

This skill ensures ALL markdown in a project is properly structured for LLM agent effectiveness.

## When to Use This Skill

Use this skill for **ANY markdown file operation**:
- Creating new documentation from scratch
- Editing existing markdown files (minor or major changes)
- Reviewing documentation structure and quality
- Refactoring scattered information into coherent documents
- Fixing broken links or orphaned documents
- Validating markdown quality standards
- Project-wide documentation audits

**Automatic activation**: Whenever you work with .md files, apply this skill's principles.

## How This Skill Applies

### For Single File Operations (Modes 1 & 2)
- Applied **manually** when you edit/create a specific markdown file
- Use guidelines from quick reference or full guide
- Check against Top 8 Pitfalls
- Validate links to ensure they work
- **Scope**: Only the file(s) you're actively editing

### For Project-Wide Analysis (Mode 3)
- Run validation scripts to scan **entire project**
- Automatically excludes:
  - Dependencies (`node_modules/`, `venv/`, `vendor/`)
  - Build artifacts (`__pycache__/`)
  - Git internals (`.git/`)
  - **Skill templates** (`.claude/skills/`) - avoids self-validation
  - External docs (`docs/fastMCPServer/`) - if not project-owned
- **Scope**: All project markdown files
- **When to use**: Documentation audits, quarterly reviews, before releases

**Important**: Mode 3 scans ALL project files, but Mode 1/2 apply only to files you're working on.

## Operation Modes

### Mode 1: Light Operations (Use Quick Reference)

**When to use**: Minor edits, quick fixes, validation checks, reviews

**Process**:
1. Read `references/markdown-quick-ref.md` (478 lines) completely
2. Apply top 8 pitfalls checklist
3. Verify link structure and hierarchy
4. Make targeted changes

**Examples**: Fixing typos, adding links, minor formatting, quick validation

### Mode 2: Heavy Operations (Use Full Guide)

**When to use**: New documents, major refactoring, structural changes

**Process**:
1. Read `references/markdown-generation-guide.md` (1559 lines) completely
2. Select appropriate template from guide
3. Follow progressive disclosure pattern
4. Implement modular documentation structure
5. Create comprehensive cross-linking

**Examples**: New feature docs, major rewrites, consolidating scattered content

### Mode 3: Documentation Health Analysis

**When to use**: Project-wide quality assessment, finding issues

**Process**:
1. Read quick reference for checklist
2. Use `scripts/validate_markdown.py` to scan all docs
3. Use `scripts/analyze_docs.py` to find orphans and broken links
4. Generate recommendations for improvements

**Examples**: Quarterly doc reviews, new project onboarding, quality audits

**How it works**:
- Scans **ALL markdown files** in project recursively
- Automatically excludes these directories:
  - `node_modules/` - Package dependencies
  - `.git/` - Git internals
  - `venv/` - Python virtual environments
  - `vendor/` - Third-party code
  - `__pycache__/` - Python cache
  - `.claude/skills/` - **Skill templates/examples (avoids self-validation)**
- Focuses on **project-owned documentation** only
- Use for project-wide audits, not single file validation

## Decision Tree: Which Mode to Use?

```
Working with markdown?
│
├─ Creating new document from scratch?
│  └─ MODE 2: Read FULL GUIDE (markdown-generation-guide.md)
│     Use template, follow progressive disclosure
│
├─ Major refactoring (restructure, content reorganization)?
│  └─ MODE 2: Read FULL GUIDE (markdown-generation-guide.md)
│     Treat as new document creation
│
├─ Minor edits (typos, small additions, formatting)?
│  └─ MODE 1: Read QUICK REF (markdown-quick-ref.md)
│     Apply checklist, make targeted changes
│
├─ Reviewing/validating existing document?
│  └─ MODE 1: Read QUICK REF (markdown-quick-ref.md)
│     Check against top 8 pitfalls
│
└─ Project-wide documentation audit?
   └─ MODE 3: Use QUICK REF + validation scripts
      Generate health report, recommend fixes
```

## Critical Rules (Always Apply)

### The Top 8 Pitfalls to Avoid

1. **Multiple H1 headings** - Only ONE `#` per document
2. **No language on code blocks** - Always use `` ```bash ``, `` ```python ``, etc.
3. **Vague link text** - Avoid "here", "this"; use descriptive text
4. **External links when local exists** - Prefer local files for documentation
5. **Missing alt text on images** - Always describe images for LLM agents
6. **Skipping heading levels** - Don't jump from `##` to `####`
7. **No blank lines around blocks** - Always separate headings, code, lists
8. **Inconsistent formatting** - Choose one pattern and stick to it throughout project

### Link Priority Hierarchy (CRITICAL)

```
1. Local file links    (same repository)    ← ALWAYS PREFER
2. Internal anchors    (same document)      ← For navigation
3. External links      (other sites)        ← ONLY when necessary
```

**Why local links matter**:
- Keep documentation self-contained
- Work offline
- Version controlled together
- No broken external links
- Faster for agents to navigate
- LLM-friendly context loading

### Document Length Guidelines

| Type | Lines | Action if Exceeded |
|------|-------|-------------------|
| Cheat sheets | 100-200 | Keep concise |
| Quick starts | 150-300 | Split into steps |
| Reference docs | 300-600 | Create sub-docs |
| Comprehensive guides | 600-1000 | Modularize |
| **Over 1000 lines** | — | **MUST split into multiple documents** |

### Heading Hierarchy Rules

```markdown
# Document Title                    # ONE per document, no text before
> Optional tagline

## Major Section                    # H2 for main sections
### Subsection                      # H3 for subsections
#### Detail Level                   # H4 for details
##### Fine Details                  # H5 rarely needed
###### Avoid                        # H6 almost never used
```

**Critical**: Never skip levels (e.g., `##` → `####` is WRONG)

## Automatic Link Validation

**MANDATORY**: Validate links automatically for operations involving links.

### When to Auto-Validate Links

**Always validate** when:
1. **Adding new links** to any markdown file
2. **Modifying existing links** (changing paths or anchors)
3. **Creating new markdown documents** (validate all links on completion)
4. **Moving or renaming files** (check for references that will break)
5. **User explicitly requests** validation or review

### Link Validation Command

Run this command to validate link integrity:

```bash
python scripts/analyze_docs.py .
```

**What it validates** (all automatic):
- ✅ **Local .md files** - Checks file exists
- ✅ **Local project files** - Checks any file type exists (yaml, json, etc.)
- ✅ **Internal anchors** (#same-doc) - Validates heading exists in same file
- ✅ **Cross-doc anchors** (file.md#section) - Validates both file AND heading exist

**What it does NOT validate**:
- ❌ **External links** (http/https) - Intentionally skipped (no network requests)

### Validation Workflow

1. **Before completing task**: Run link validation
   ```bash
   python scripts/analyze_docs.py .
   ```

2. **If broken links found**:
   - Report them to user with file and line info
   - Offer to fix them (update paths, create missing files, fix anchors)
   - Ask if user wants to proceed or fix first

3. **Common fixes**:
   - Update relative paths (`../` vs `./`)
   - Create missing anchor by adding heading
   - Update links after file moves/renames
   - Remove dead links to deleted files

### Example Automatic Validation

**Scenario**: User adds link to another document

```markdown
See [Configuration Guide](./config/setup.md#database) for details.
```

**Your process**:
1. Add the link
2. Run validation: `python scripts/analyze_docs.py .`
3. Check output for this specific link
4. If broken:
   - Report: "Link validation failed: ./config/setup.md doesn't exist" OR
   - Report: "Link validation failed: anchor 'database' not found in ./config/setup.md"
5. Offer fix or ask user preference

### Performance Note

Link validation scans all markdown files but is fast (Python-based):
- Small projects (<50 files): < 1 second
- Medium projects (50-200 files): 1-3 seconds
- Large projects (200+ files): 3-10 seconds

**Don't worry about resources** - validation is quick and catches critical issues.

## Workflows

### Workflow 1: Creating New Markdown Document

1. **Determine document type**
   - Quick start guide
   - Configuration reference
   - API reference
   - Troubleshooting guide
   - Architecture document
   - Other

2. **Read full generation guide completely**
   - Read `references/markdown-generation-guide.md` from start to finish
   - Pay special attention to template library section
   - Review examples for your document type

3. **Select appropriate template**
   - Use template from guide's template library
   - Adapt for your specific needs
   - See `references/templates/` for extracted templates

4. **Create document following these principles**:
   - Single H1 heading (document title)
   - Optional tagline using `>` blockquote
   - Progressive disclosure (overview → quickstart → details → advanced)
   - Local file links preferred over external
   - Code blocks with language identifiers
   - Descriptive link text (not "here" or "this")
   - Proper heading hierarchy (no skips)
   - Tables with descriptive headers
   - Images with descriptive alt text

5. **Add cross-links to related documents**
   - Link to prerequisites
   - Reference related guides
   - Add "See Also" section at end
   - Create bidirectional links when possible

6. **Validate links automatically**:
   - Run: `python scripts/analyze_docs.py .`
   - Check for broken links to new document
   - Verify all outgoing links work (files exist, anchors exist)
   - Fix any broken links before proceeding

7. **Verify document meets standards**:
   - Single H1 heading ✓
   - No skipped heading levels ✓
   - All code blocks have languages ✓
   - All links are descriptive ✓
   - All links are valid (not broken) ✓
   - Document length appropriate (200-1000 lines) ✓
   - Proper cross-linking ✓

### Workflow 2: Editing Existing Markdown (Light)

**When**: Minor changes, quick fixes, small additions

1. **Read quick reference**
   - Read `references/markdown-quick-ref.md` completely
   - Focus on top 8 pitfalls section

2. **Scan document for common issues**:
   - Multiple H1 headings?
   - Skipped heading levels?
   - Code blocks without languages?
   - Vague link text ("here", "this")?
   - External links that could be local?
   - Missing alt text on images?

3. **Make targeted edits**
   - Fix identified issues
   - Apply quick ref rules
   - Preserve existing structure if sound

4. **Validate links if modified**:
   - If you added or changed links, run: `python scripts/analyze_docs.py .`
   - Check that modified links work (files exist, anchors exist)
   - Fix any broken links introduced by edits

5. **Validate changes**
   - Run through top 8 pitfalls checklist
   - Verify links still work
   - Check heading hierarchy

### Workflow 3: Editing Existing Markdown (Heavy Refactoring)

**When**: Major structural changes, consolidation, content reorganization

1. **Read full generation guide**
   - Read `references/markdown-generation-guide.md` completely
   - Treat this as creating a new document

2. **Analyze current state**:
   - What's the document's purpose?
   - Is information scattered?
   - Are there multiple H1 headings?
   - Is the hierarchy logical?
   - Is it too long (>1000 lines)?
   - Are there orphaned sections?

3. **Plan restructure**:
   - Define clear document purpose
   - Group related information
   - Design proper hierarchy
   - Identify content to split off
   - Plan cross-linking strategy

4. **Implement refactoring**:
   - Create new structure
   - Consolidate scattered information
   - Fix heading hierarchy
   - Split oversized documents
   - Update all links
   - Add cross-references

5. **Validate links automatically**:
   - Run: `python scripts/analyze_docs.py .`
   - Check all refactored documents for broken links
   - Verify updated links point to correct files and anchors
   - Fix any broken links from restructuring

6. **Validate result**:
   - Single H1 heading ✓
   - Proper hierarchy ✓
   - Semantic grouping ✓
   - Appropriate length ✓
   - Strong cross-linking ✓
   - All links valid (not broken) ✓

### Workflow 4: Documentation Review

**When**: Validating quality of existing documentation

1. **Read quick reference**
   - Read `references/markdown-quick-ref.md` completely

2. **Check against top 8 pitfalls**:
   - [ ] Only one H1 heading
   - [ ] No skipped heading levels
   - [ ] All code blocks have languages
   - [ ] Link text is descriptive
   - [ ] Local links preferred
   - [ ] Images have alt text
   - [ ] Blank lines around blocks
   - [ ] Consistent formatting

3. **Validate links automatically**:
   - Run: `python scripts/analyze_docs.py .`
   - Review output for broken links in this document
   - [ ] Local links work (files exist)
   - [ ] Internal anchors work (headings exist)
   - [ ] No broken links
   - [ ] Link text is descriptive
   - [ ] Cross-links to related docs

4. **Check semantic grouping**:
   - [ ] Related information is together
   - [ ] No scattered content
   - [ ] Logical flow (progressive disclosure)

5. **Verify heading hierarchy**:
   - [ ] Single H1
   - [ ] Proper nesting (no skips)
   - [ ] Descriptive headings

6. **Check document length**:
   - [ ] Within appropriate range for type
   - [ ] Not oversized (>1000 lines)
   - [ ] Not too sparse (<100 lines for main docs)

### Workflow 5: Project Documentation Audit

**When**: Assessing documentation health across entire project

1. **Discover all markdown files**:
   ```bash
   find . -name "*.md" -type f | grep -v node_modules
   ```

2. **Run validation script**:
   ```bash
   python scripts/validate_markdown.py .
   ```
   This checks:
   - Multiple H1 headings
   - Skipped heading levels
   - Code blocks without languages
   - Document lengths
   - Common pitfalls

3. **Run analysis script**:
   ```bash
   python scripts/analyze_docs.py .
   ```
   This identifies:
   - Orphaned documents (no incoming links)
   - Broken internal links
   - Oversized documents (>1000 lines)
   - Documents with scattered related content
   - Missing cross-links

4. **Generate recommendations**:
   - List orphaned docs to integrate
   - Identify broken links to fix
   - Suggest document splits for oversized files
   - Recommend consolidation opportunities
   - Propose cross-linking improvements

5. **Prioritize fixes**:
   - Critical: Broken links, orphaned docs
   - High: Oversized docs, missing H1s
   - Medium: Formatting issues, weak cross-links
   - Low: Style inconsistencies

## Reference Materials

### Quick Reference (478 lines)
**File**: `references/markdown-quick-ref.md`

**Use for**:
- Quick checks and validation
- Minor edits and fixes
- Top 8 pitfalls checklist
- Fast syntax lookup

**Key sections**:
- Link priority hierarchy
- Text formatting rules
- Code block syntax
- Top 8 pitfalls
- Decision trees

### Full Generation Guide (1559 lines)
**File**: `references/markdown-generation-guide.md`

**Use for**:
- Creating new documents
- Major refactoring
- Understanding best practices
- Template selection

**Key sections**:
- Document structure patterns
- Comprehensive link guidance
- Template library (quickstart, config, API, troubleshooting)
- Progressive disclosure
- Best practices

### Templates
**Directory**: `references/templates/`

Pre-extracted templates from the guide:
- `quickstart.md` - Quick start template
- `configuration.md` - Configuration reference template
- `api-reference.md` - API documentation template
- `troubleshooting.md` - Troubleshooting guide template

### Validation Scripts
**Directory**: `scripts/`

- `validate_markdown.py` - Automated quality checking
- `analyze_docs.py` - Find orphans, broken links, structural issues

## Examples

See `examples/` directory for real-world demonstrations:
- Creating new documentation
- Refactoring existing docs
- Fixing common pitfalls
- Project-wide audits

## Quality Checklist

Before completing any markdown operation, verify:

- [ ] **Single H1 heading** - Only one `#` in the document
- [ ] **No skipped levels** - Heading hierarchy is sequential
- [ ] **Code blocks have languages** - All `` ``` `` blocks specify language
- [ ] **Internal links work** - All local file links and anchors are valid
- [ ] **Link text is descriptive** - No "here", "this", naked URLs
- [ ] **Document length appropriate** - 200-1000 lines for main docs
- [ ] **Proper cross-linking** - Related docs are linked
- [ ] **Semantic grouping** - Related content is together
- [ ] **Consistent formatting** - Same patterns throughout project
- [ ] **No orphaned sections** - All content has clear purpose and connection

## Common Patterns

### Navigation Hub Pattern

For main README or index files:

```markdown
# Project Documentation

## Getting Started

- [Installation](./getting-started/installation.md) - Install and setup
- [Quick Start](./getting-started/quickstart.md) - Get running in 5 minutes

## Guides

- [Configuration](./guides/configuration.md) - Configure the application
- [Deployment](./guides/deployment.md) - Deploy to production

## Reference

- [API Reference](./reference/api.md) - Complete API documentation
- [CLI Commands](./reference/cli.md) - Command-line interface
```

### "See Also" Pattern

For document endings:

```markdown
## See Also

- [Quick Start Guide](./quickstart.md) - Get started in 5 minutes
- [Configuration Reference](./config.md) - All configuration options
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
```

### Progressive Disclosure Pattern

Order content from simple to complex:

1. **Overview** - What is it?
2. **Quick Start** - Get running fast
3. **Core Concepts** - Understanding fundamentals
4. **Detailed Usage** - Deep dive
5. **Advanced Topics** - Expert usage
6. **Reference** - Complete specifications
7. **Troubleshooting** - Common issues

## Troubleshooting

### Issue: Document is too long (>1000 lines)

**Solution**: Split into modular documents
1. Identify logical sections
2. Create separate files for each
3. Create navigation hub document
4. Add cross-links between documents

### Issue: Found orphaned document

**Solution**: Integrate into documentation structure
1. Determine document's purpose
2. Find related documents
3. Add links from related docs
4. Add to navigation hub
5. Consider consolidating if very small

### Issue: Broken internal links

**Solution**: Fix systematically
1. Use validation script to find all broken links
2. Check if target file was moved/renamed
3. Update link or remove if target obsolete
4. Consider using reference links for repeated URLs

### Issue: Scattered related information

**Solution**: Consolidate
1. Identify all documents with related content
2. Determine best structure (single doc or related group)
3. Create consolidated document with clear hierarchy
4. Move content and update cross-links
5. Archive or redirect old documents

## Advanced: Modular Documentation Architecture

For large projects, organize documentation modularly:

```
docs/
├── README.md                    # Navigation hub
├── getting-started/
│   ├── installation.md         # 250 lines
│   └── quickstart.md           # 200 lines
├── guides/
│   ├── configuration.md        # 400 lines
│   ├── deployment.md           # 350 lines
│   └── troubleshooting.md      # 300 lines
├── reference/
│   ├── api.md                  # 600 lines
│   └── cli.md                  # 400 lines
└── architecture/
    ├── overview.md             # 300 lines
    ├── components.md           # 500 lines
    └── data-flow.md            # 400 lines
```

**Benefits**:
- LLM agents load only relevant content
- Easier to maintain
- Better navigation
- Parallel editing
- Context-window friendly

## Summary: Key Principles

When handling ANY markdown file, remember:

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

**Mission Success**: All markdown in the project is LLM-optimized, semantically grouped, properly hierarchical, context-appropriate in length, with zero orphaned or broken documents.
