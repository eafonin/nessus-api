# Documentation Hierarchy Requirements

> Organizational rules for 4-level hierarchical documentation optimized for LLM agent consumption

**Version:** 1.0.0 | **Scope:** Structure and organization | **Companion:** markdown-writer skill (formatting)

---

## Purpose

This document defines the hierarchical structure, navigation patterns, and organizational rules for project documentation. It ensures:

1. **Predictable navigation** - Every directory has a README.MD entry point
2. **Progressive disclosure** - Abstracts enable selective document loading
3. **Context efficiency** - Documents sized for LLM context windows
4. **No scattered information** - Each topic consolidated in one authoritative location

**Separation of concerns:**
- This document: Scope, hierarchy, organization
- markdown-writer skill: Content formatting, linking, validation

---

## Hierarchy Levels

### Level Definition

| Level | Location | Role | Example |
|-------|----------|------|---------|
| L1 | `/README.MD` | Project root, navigation hub | Project entry point |
| L2 | `/*/README.MD` | Major component entry | `mcp-server/`, `docs/`, `dev1/` |
| L3 | `/*/*/README.MD` | Subcomponent entry | `mcp-server/core/`, `mcp-server/docs/` |
| L4 | `/*/*/*/README.MD` | Leaf module entry | `mcp-server/tests/unit/` |

### Depth Rules

- **Target depth:** 4 levels (L1-L4)
- **Deeper nesting:** Acceptable when necessary, but discouraged
- **Every directory:** Must have a README.MD without exception

### Navigation Pattern

```
L1: /README.MD
 ├── L2: mcp-server/README.MD
 │    ├── L3: mcp-server/core/README.MD
 │    │    └── L4: mcp-server/core/utils/README.MD (if exists)
 │    ├── L3: mcp-server/docs/README.MD
 │    │    └── Leaf docs: API.md, ARCHITECTURE.md (no children)
 │    └── L3: mcp-server/tests/README.MD
 │         └── L4: mcp-server/tests/unit/README.MD
 ├── L2: docs/README.MD
 ├── L2: dev1/README.MD
 └── L2: scanners-infra/README.MD
```

---

## README.MD Requirements

### Mandatory Header

Every README.MD must begin with navigation metadata as HTML comments:

```html
<!-- README Navigation -->
<!-- L{N}: {relative-path}/ -->
<!-- Parent: {path-to-parent-README} -->
<!-- Purpose: {one-line description} -->
```

**Example (L3 document):**
```html
<!-- README Navigation -->
<!-- L3: mcp-server/core/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Task management, queuing, and observability -->
```

**L1 Root Exception:**
```html
<!-- README Navigation -->
<!-- L1: / (Project Root) -->
<!-- Purpose: Project entry point and navigation hub -->
```

### Required Sections

#### All README.MD Files

1. **Title** - Single H1 with module/component name
2. **Tagline** - Blockquote with one-line description (abstract)
3. **Parent Link** - Navigation back to parent README
4. **Quick Navigation** - Table linking to child directories/documents

#### L1 Root README.MD (Additional)

- Project overview and status
- Quick start instructions
- Architecture diagram (high-level)
- MCP tools summary table
- Configuration overview

#### L2-L4 README.MD (Additional)

- Directory structure (if contains subdirectories)
- Module/file overview table
- Key workflows or concepts
- Usage examples (brief)
- Links to detailed documentation

### README.MD Structure Template

```markdown
<!-- README Navigation -->
<!-- L{N}: {path}/ -->
<!-- Parent: {parent-path} -->
<!-- Purpose: {one-line} -->

# {Component Name}

> {One-line description serving as abstract}

**↑ Parent**: [{Parent Name}]({parent-path}) | **↑↑ Root**: [Project Root](/{root-path})

## Quick Navigation

| Directory/Document | Purpose |
|--------------------|---------|
| [child/](child/README.MD) | Brief description |
| [DOC.md](DOC.md) | Brief description |

## {Content Sections}

{Appropriate content for this level}

## See Also

- [Related Doc](path/to/doc.md) - Description
```

---

## Non-README Documents (Leaf Documents)

### Definition

Leaf documents are standalone documents that:
- Do not have child documents
- Are linked from a parent README.MD
- Consolidate all information on a specific topic

**Examples:** `API.md`, `ARCHITECTURE_v2.2.md`, `MONITORING.md`, `TESTING.md`

### Header Requirements

Simplified header with purpose and parent only:

```html
<!-- Purpose: {one-line description} -->
<!-- Parent: ./README.MD -->
```

**Example:**
```html
<!-- Purpose: MCP tool API reference with parameters and examples -->
<!-- Parent: ./README.MD -->
```

### Leaf Document Rules

1. **No children** - Leaf documents do not link to child documents (exceptions: INDEX.md, generated reference docs)
2. **Single topic** - Each document covers one consolidated topic
3. **Self-contained** - All information on that topic in one place
4. **Cross-references** - May link to sibling documents for related topics

---

## Progressive Disclosure

### Abstract Pattern

Every document provides a scannable abstract so agents can decide whether to load the full content:

| Location | Abstract Format |
|----------|-----------------|
| README.MD | Blockquote after H1: `> One-line description` |
| Parent README | Quick Navigation table with brief descriptions |
| Complex parents | Document Summaries section with expanded abstracts |

### Quick Navigation Table

Used in every README.MD to provide brief link descriptions:

```markdown
## Quick Navigation

| Directory | README | Purpose |
|-----------|--------|---------|
| [core/](core/) | [README.MD](core/README.MD) | Task management, queue, health checks |
| [schema/](schema/) | [README.MD](schema/README.MD) | Result parsing and filtering |
```

### Document Summaries Section

Add when child documents are complex (hierarchy of headings, many sections, or approaching size limits):

```markdown
## Document Summaries

### API.md

MCP tool reference covering:
- `run_untrusted_scan` - Parameters, response format
- `run_authenticated_scan` - SSH credential handling
- `get_scan_status` - Status codes, progress tracking
- `get_scan_results` - Filtering, pagination, JSON-NL format

### ARCHITECTURE_v2.2.md

System components and data flow:
- MCP server (FastMCP framework)
- Redis queue architecture
- Scanner worker lifecycle
- Task state machine
```

### When to Include Document Summaries

Include Document Summaries section when:
- Documents have complex internal structure (multiple heading levels)
- Documents have many sections (>5 major headings)
- Documents approach the 1000-line size limit
- Agent discretion based on complexity

---

## Document Sizing

### Target Line Counts

| Document Type | Target | Maximum |
|---------------|--------|---------|
| README.MD | 100-300 lines | 500 lines |
| Leaf documents | 200-800 lines | 1000 lines |

### Sizing Guidelines

1. **README.MD files** - Concise navigation hubs, not comprehensive documentation
2. **Leaf documents** - Consolidated topic coverage within context window limits
3. **Oversized documents** - Split into focused sub-documents, update parent README
4. **Coordinate with markdown-writer** - Use skill for detailed sizing validation

### When to Split Documents

Split a document when:
- Exceeds 1000 lines
- Covers multiple distinct topics
- Has sections that could stand alone
- Agent frequently needs only part of the content

---

## Naming Conventions

### File Names

| Type | Convention | Example |
|------|------------|---------|
| Directory README | `README.MD` (uppercase extension) | `core/README.MD` |
| Leaf documents | `SCREAMING_SNAKE.md` or `Title_Case.md` | `API.md`, `ARCHITECTURE_v2.2.md` |
| Generated/index | `INDEX.md`, `KEYWORDS.md` | Reference documents |

### Consistency Rules

1. **README files** - Always `README.MD` with uppercase `.MD` extension
2. **Within directory** - Consistent naming style for all documents
3. **Versioned documents** - Include version in filename: `ARCHITECTURE_v2.2.md`

---

## Directory Types

All directory types follow the same README.MD requirements:

| Type | Examples | README Content Focus |
|------|----------|---------------------|
| Code modules | `core/`, `schema/`, `tools/` | Module overview, file purposes, usage |
| Documentation | `docs/`, `mcp-server/docs/` | Document index, summaries, quick links |
| Infrastructure | `dev1/`, `scanners-infra/` | Setup instructions, configuration |
| Data/Logs | `dev1/data/`, `dev1/logs/` | Purpose, retention, access patterns |
| Tests | `tests/`, `tests/unit/` | Test organization, running instructions |
| Config | `config/` | Configuration options, examples |

---

## Information Organization

### No Scattered Information

Each topic must have one authoritative location:

```
✓ CORRECT: All API documentation in docs/API.md
✗ WRONG: API info split across README, API.md, and USAGE.md
```

### Topic Consolidation Rules

1. **One source of truth** - Each topic documented in exactly one place
2. **Cross-reference, don't duplicate** - Link to authoritative source
3. **README summarizes, docs detail** - README provides overview, links to full docs
4. **Update together** - When topic changes, update authoritative doc only

### Link Hierarchy

```
README.MD (overview + links)
    ↓
Leaf Document (full details)
    ↓
Code Comments (implementation notes)
```

---

## Validation Checklist

### For README.MD Files

- [ ] Has navigation header (`<!-- README Navigation -->` block)
- [ ] Level matches directory depth (L1-L4)
- [ ] Parent path is correct and relative
- [ ] Single H1 heading
- [ ] Blockquote abstract after H1
- [ ] Parent link in document body
- [ ] Quick Navigation table present
- [ ] Within 500-line limit
- [ ] All child directories linked
- [ ] All sibling documents linked

### For Leaf Documents

- [ ] Has simplified header (Purpose + Parent)
- [ ] Single consolidated topic
- [ ] Within 1000-line limit
- [ ] Linked from parent README.MD
- [ ] No orphaned content

### For Directory Structure

- [ ] Every directory has README.MD
- [ ] No deeper than L4 (unless necessary)
- [ ] Consistent naming convention
- [ ] No duplicate topic coverage

---

## Examples

### L1 Root README.MD Header

```html
<!-- README Navigation -->
<!-- L1: / (Project Root) -->
<!-- Purpose: Project entry point and navigation hub -->

# Nessus MCP Server

> Model Context Protocol server for Nessus vulnerability scanning with Claude Code

**Version:** 1.0.0 | **Status:** Production Ready

## Quick Navigation

| Directory | README | Purpose |
|-----------|--------|---------|
| [mcp-server/](mcp-server/) | [README.MD](mcp-server/README.MD) | MCP server code |
| [dev1/](dev1/) | [README.MD](dev1/README.MD) | Development deployment |
```

### L3 Module README.MD Header

```html
<!-- README Navigation -->
<!-- L3: mcp-server/core/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Task management, queuing, and observability -->

# Core Infrastructure

> Foundation modules for task management, queuing, and observability

**↑ Parent**: [MCP Server](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)
```

### Leaf Document Header

```html
<!-- Purpose: MCP tool API reference with parameters and examples -->
<!-- Parent: ./README.MD -->

# API Reference

> Complete MCP tool signatures, parameters, and response formats
```

---

## Integration with markdown-writer

This document defines **what** to organize. The markdown-writer skill defines **how** to format:

| Concern | This Document | markdown-writer |
|---------|---------------|-----------------|
| Hierarchy levels | ✓ | |
| README requirements | ✓ | |
| Document sizing | ✓ | ✓ (detailed validation) |
| Header metadata | ✓ | |
| Content formatting | | ✓ |
| Link syntax | | ✓ |
| Code block formatting | | ✓ |
| Heading structure | | ✓ |

**Workflow:**
1. Use this document for structural decisions
2. Use markdown-writer skill for content creation
3. Validate with both checklists

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-01 | Initial requirements document |
