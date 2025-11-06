# Markdown Generation Guide for Claude Agents

**Version**: 2.0
**Purpose**: Comprehensive guide for Claude agents generating high-quality markdown documentation
**Scope**: Generic for any Claude agent in any project
**Quick Reference**: See [MARKDOWN-QUICK-REF.md](./MARKDOWN-QUICK-REF.md) for fast lookup

**Key Characteristics**: LLM-Focused • Modular • Hierarchical • Context-Efficient

---

## Table of Contents

1. [Document Structure](#document-structure)
2. [Heading Hierarchy](#heading-hierarchy)
3. [Links and Cross-References](#links-and-cross-references)
4. [Text Formatting](#text-formatting)
5. [Lists and Enumerations](#lists-and-enumerations)
6. [Code Blocks](#code-blocks)
7. [Tables](#tables)
8. [Images and Media](#images-and-media)
9. [Blockquotes and Callouts](#blockquotes-and-callouts)
10. [Task Lists](#task-lists)
11. [Special Elements](#special-elements)
12. [Document Front Matter](#document-front-matter)
13. [Best Practices](#best-practices)
14. [Common Pitfalls](#common-pitfalls)
15. [Template Library](#template-library)

---

## Document Structure

### Primary Heading

**Rule**: Every markdown document MUST start with exactly ONE level-1 heading (`#`).

```markdown
# Document Title

> Brief tagline or description (optional but recommended)

Opening paragraph introducing the document's purpose.
```

**Key Points**:
- No text before the first `#` heading
- Only ONE `#` heading per document
- Title case for the heading text
- Optional subtitle using `>` blockquote

### Standard Document Flow

```
# Main Title
> Optional tagline

Introduction paragraph(s)

## First Major Section
### Subsection 1
#### Detail Level 1

### Subsection 2

## Second Major Section

## See Also / Next Steps
```

### Progressive Disclosure Pattern

Organize content from simple to complex:

1. **Overview** - What is it?
2. **Quick Start** - Get running fast
3. **Core Concepts** - Understanding fundamentals
4. **Detailed Usage** - Deep dive
5. **Advanced Topics** - Expert usage
6. **Reference** - Complete specifications
7. **Troubleshooting** - Common issues

---

## Heading Hierarchy

### Heading Levels

| Level | Syntax | Purpose | Example |
|-------|--------|---------|---------|
| H1 | `#` | Document title (ONE per doc) | `# Quickstart Guide` |
| H2 | `##` | Major sections | `## Installation` |
| H3 | `###` | Subsections | `### Prerequisites` |
| H4 | `####` | Detail sections | `#### Configuration Options` |
| H5 | `#####` | Fine details | `##### Advanced Settings` |
| H6 | `######` | Rarely used | Avoid if possible |

### Critical Rules

1. **No Skipping Levels**: Don't jump from `##` to `####`
   ```markdown
   <!-- WRONG -->
   ## Section
   #### Subsection

   <!-- CORRECT -->
   ## Section
   ### Subsection
   ```

2. **Blank Lines**: Always before and after headings
   ```markdown
   ## Heading

   Content here

   ### Subheading

   More content
   ```

3. **Capitalization**: Title case for H1-H3, sentence case for H4-H6
4. **No Punctuation**: Don't end headings with periods or colons

---

## Links and Cross-References

> **MOST IMPORTANT SECTION** - Links enable modular, hierarchical documentation

### Link Priority Hierarchy

**For LLM Agents**: Follow this priority when creating links:

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

### Local File Links (Primary Method)

**Syntax**:
```markdown
<!-- Same directory -->
[Configuration Guide](configuration.md)
[Setup Instructions](setup.md)

<!-- Subdirectory -->
[API Reference](docs/api-reference.md)
[CLI Commands](reference/cli-commands.md)

<!-- Parent directory -->
[Project README](../README.md)
[Main Documentation](../../docs/main.md)

<!-- With section anchor -->
[Installation Steps](setup.md#installation)
[Database Config](config.md#database-configuration)
```

**Best Practices**:
```markdown
<!-- EXCELLENT - Local, descriptive -->
See [Agent Configuration](../agents/configuration.md) for details
Review the [CLI Command Reference](./cli-reference.md)
Configure [environment variables](./env-setup.md)

<!-- AVOID - External when local copy exists -->
See [Python Docs](https://docs.python.org) for syntax
Check [GitHub Docs](https://docs.github.com) for help
```

**Modular Structure Example**:
```
docs/
├── README.md                    # Navigation hub
├── getting-started/
│   ├── installation.md
│   └── quickstart.md
├── guides/
│   ├── configuration.md
│   └── troubleshooting.md
└── reference/
    ├── api.md
    └── cli.md
```

### Internal Anchors (Same Document)

**Heading anchors auto-generate** from heading text:

```markdown
## Installation Guide              → #installation-guide
### Step 1: Install                → #step-1-install
#### API Configuration             → #api-configuration
### Getting Started                → #getting-started
```

**Anchor generation rules**:
- Lowercase all letters
- Replace spaces with hyphens
- Remove special characters
- `## Section: Advanced Setup` → `#section-advanced-setup`
- `### C++ Build Options` → `#c-build-options`

**Usage**:
```markdown
Jump to [Installation Guide](#installation-guide)
See [API Configuration](#api-configuration) for setup
Return to [Table of Contents](#table-of-contents)
```

### Cross-Document Links with Sections

```markdown
<!-- Link to specific heading in another file -->
[Database Configuration](./setup.md#database-configuration)
[Authentication Methods](../api/auth.md#authentication-methods)
[Troubleshooting Network](./troubleshooting.md#network-issues)
```

**Verify anchors exist**:
```markdown
<!-- File: setup.md must have this heading -->
## Database Configuration

<!-- Then this link will work -->
[DB Setup](./setup.md#database-configuration)
```

### Link Text Best Practices

**DO**:
```markdown
[Internal link](#section-anchor)
[Relative link](./other-file.md)
See the [CLI reference](./cli-ref.md)
Configure [environment variables](./env-setup.md)
Learn more about [subagent configuration](./agents.md)
Review the [troubleshooting guide](./troubleshooting.md)
```

**DON'T**:
```markdown
Click [here](./guide.md) for details       # Avoid "here", "click here"
See [this document](./doc.md)              # Avoid "this document"
[https://example.com](https://example.com) # Avoid naked URLs as text
Read [this](./guide.md) for more info      # "this" is unclear
```

**Rules for link text**:
- Descriptive and action-oriented
- Explains what user will find
- 2-6 words typically
- Standalone meaningful (not "here" or "this")

### Reference Links (Repeated URLs)

**When to use**: Same URL appears 3+ times in document

**Syntax**:
```markdown
<!-- Document content -->
See the [API guide][api] for endpoints.
Check the [API guide][api] for examples.
Review the [API guide][api] for authentication.

<!-- Link definitions at document end -->
[api]: ./api-reference.md
[config]: ./configuration.md
[cli]: ./cli-reference.md
```

**Advantages**:
- Define URL once, reference many times
- Easy to update (change in one place)
- Cleaner source text

**Best Practices**:
1. Place definitions at document end
2. Use descriptive reference names (`[api-docs]`, not `[1]`)
3. Sort alphabetically

### External Links (Use Sparingly)

**When external links ARE appropriate**:
- Official tool documentation (frequently updated)
- Live services (GitHub, cloud providers)
- Standards/regulatory documents
- Open source project homepages

**When to AVOID external links**:
- External docs that should be copied locally
- Tutorial content (copy and adapt instead)
- Reference material that could be archived
- Anything that might disappear

**Strategy**:
```markdown
<!-- ACCEPTABLE - Official, maintained -->
See [Python Official Docs](https://docs.python.org/3/)
View on [GitHub](https://github.com/user/repo)

<!-- BETTER - Copy to local and link -->
See our [Python Guide](./reference/python-guide.md)
See [Development Setup](./dev-setup.md)
```

**For large projects**: Consider hosting external references locally:
```
docs/
├── external-references/
│   ├── python-style-guide.md  (copied from external)
│   ├── docker-best-practices.md
│   └── api-design-patterns.md
└── project-docs/
    └── architecture.md  (links to ../external-references/)
```

> **Note**: Consider copying external documentation to local GitLab for offline access and version control. This keeps documentation self-contained and under your control.

### Link Organization Patterns

**Navigation Hub Pattern** (for main README/index):
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

**"See Also" Pattern** (for document end):
```markdown
## See Also

- [Quick Start Guide](./quickstart.md) - Get started in 5 minutes
- [Configuration Reference](./config.md) - All configuration options
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
```

### LLM Link Generation Guidelines

**Decision Tree**:
```
Need to link to information?
├─ Is it in this document?
│  └─ Use internal anchor: [Section](#section-anchor)
├─ Is it in this repository?
│  └─ Use local file link: [Doc](./doc.md)
├─ Should it be in this repository?
│  └─ Create local file first, then link to it
└─ Must be external?
   ├─ Can we copy to local? → Copy, then link locally
   └─ Must stay external? → Use external link with caution
```

**When creating links**:
1. **Always prefer local files** over external URLs
2. **Use descriptive link text** that explains destination
3. **Check if target file exists** in project
4. **Use reference links** if URL appears 3+ times
5. **Group related links** under headings
6. **Verify anchors** when linking to sections

---

## Text Formatting

### Emphasis Styles

| Style | Syntax | When to Use | Example |
|-------|--------|-------------|---------|
| **Bold** | `**text**` | Important terms, labels | `**Required**: Install Node.js` |
| *Italic* | `*text*` | Subtle emphasis, variables | `Replace *username* with yours` |
| `Code` | `` `text` `` | Commands, files, variables | ``Use the `npm install` command`` |

### When to Use Bold

- First mention of important terms
- Key requirements or prerequisites
- Section lead-ins within lists
- Important warnings (with context)

```markdown
**Prerequisites**:
- Node.js 18 or newer
- A valid API key

**Note**: The API key must be active.
```

### When to Use Inline Code

```markdown
Commands: `npm install`, `git clone`
File paths: `.claude/settings.json`, `/etc/config`
Variables: `API_KEY`, `DATABASE_URL`
Functions: `calculateTotal()`, `getUserData()`
Configuration keys: `permissions.allow`, `server.port`
```

### Line Breaks and Spacing

**Rule**: Use blank lines to separate blocks, never manual `<br>` tags.

```markdown
<!-- CORRECT -->
Paragraph one has content.

Paragraph two starts after a blank line.

## New Section

Content continues.
```

---

## Lists and Enumerations

### Unordered Lists

**Syntax**: Use `*`, `-`, or `+` (be consistent)

```markdown
* First item
* Second item
  * Nested item (2 spaces indent)
  * Another nested item
* Third item
```

**Best Practice**: Use `*` for main lists, `-` for nested emphasis

```markdown
* Main feature
  - Sub-detail
  - Another sub-detail
* Another main feature
```

### Ordered Lists

```markdown
1. First step
2. Second step
3. Third step
```

**Nested Lists**:
```markdown
1. Step one
   * Detail point
   * Another detail
2. Step two
   1. Sub-step one
   2. Sub-step two
```

### Multi-Paragraph List Items

```markdown
* **Item one**: Brief description.

  Continuation paragraph for item one.
  Must be indented to align with list content.

* **Item two**: Brief description.

  ```bash
  # Code blocks can also be nested
  command --option
  ```

  More content for item two.
```

---

## Code Blocks

### Fenced Code Blocks

**Syntax**: Triple backticks with language identifier

````markdown
```bash
npm install package-name
```

```python
def example():
    return "Hello, World!"
```

```javascript
function example() {
  return "Hello, World!";
}
```
````

### Common Language Identifiers

| Language | Identifier | Alternative |
|----------|-----------|-------------|
| Bash/Shell | `bash` | `sh`, `shell` |
| Python | `python` | `py` |
| JavaScript | `javascript` | `js` |
| TypeScript | `typescript` | `ts` |
| JSON | `json` | - |
| YAML | `yaml` | `yml` |
| Markdown | `markdown` | `md` |
| Plain Text | `text` | `txt` |
| SQL | `sql` | - |
| Go | `go` | `golang` |
| Rust | `rust` | `rs` |
| C/C++ | `c`, `cpp` | `c++` |

### Code Block Best Practices

1. **Always specify language** (enables syntax highlighting)
2. **Keep examples concise** (under 50 lines)
3. **Add context** before code blocks
4. **Include comments** for complex code

````markdown
To start the server, run:

```bash
# Start the development server on port 3000
npm run dev
```

This will launch the application in development mode.
````

### Command vs Output

**Distinguish commands from output**:

````markdown
Run the following command:

```bash
npm --version
```

Expected output:

```text
9.6.0
```
````

### Multi-Line Commands

```bash
docker run \
  --name my-container \
  --port 8080:8080 \
  --env API_KEY=secret \
  my-image:latest
```

### Configuration Files

**Show complete, valid examples**:

````markdown
Create a `.env` file:

```bash
# .env
API_KEY=your_api_key_here
DATABASE_URL=postgresql://localhost/mydb
NODE_ENV=development
```
````

---

## Tables

### Basic Table Syntax

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |
```

### Table Alignment

```markdown
| Left Aligned | Center Aligned | Right Aligned |
|:-------------|:--------------:|--------------:|
| Left         | Center         | Right         |
| Text         | Text           | Text          |
```

**Alignment syntax**:
- Left: `:---` or `---` (default)
- Center: `:---:`
- Right: `---:`

### Descriptive Headers

```markdown
<!-- GOOD -->
| Command | Description | Example |
|---------|-------------|---------|

<!-- AVOID -->
| Col1 | Col2 | Col3 |
|------|------|------|
```

### Tables with Formatting

```markdown
| Setting | Type | Description |
|---------|------|-------------|
| `apiKey` | **Required** | Your API key |
| `timeout` | *Optional* | Timeout in ms |
| `debug` | `boolean` | Enable debug mode |
```

### Configuration Tables

```markdown
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `port` | `number` | `3000` | Server port |
| `host` | `string` | `localhost` | Server host |
| `debug` | `boolean` | `false` | Debug mode |
```

### When to Avoid Tables

**Don't use for**:
- Very wide content (wrapping issues)
- Long paragraphs (use lists)
- Complex nested data (use sections)

---

## Images and Media

### Basic Image Syntax

```markdown
![Alt text](image.png)
![Alt text](path/to/image.png "Optional title")
```

**Components**:
- `!` - Indicates image
- `[Alt text]` - Descriptive text (required)
- `(path)` - Image file path or URL
- `"Title"` - Optional hover text

### When to Use Images (LLM Decision Guide)

**USE images for**:
- Architecture diagrams
- System topology/network maps
- Process flowcharts
- UI mockups/screenshots
- State machines/sequence diagrams

**DON'T use images for**:
- Code (use code blocks)
- Text content (use markdown)
- Simple lists or tables
- Command output (use code blocks)
- Searchable content

### Decision Tree

```
Need to show information?
├─ Is it text/code? → Use code block or markdown
├─ Is it tabular data? → Use markdown table
├─ Is it relationship/flow/structure?
│  ├─ Simple (2-3 items)? → Use text/lists
│  └─ Complex? → Use diagram image
└─ Is it UI/visual example?
   ├─ Can describe in text? → Use text
   └─ Must show visually? → Use image
```

### Alt Text (Critical for LLMs)

**Purpose**: Allows LLM agents to understand image content

**Good alt text rules**:
1. Be descriptive and specific
2. Keep under 125 characters
3. Skip "image of" or "diagram of"
4. Describe what matters

**Examples**:
```markdown
<!-- EXCELLENT -->
![Three-tier architecture: client, application server, database](architecture.png)
![Login form with username, password fields](login-ui.png)
![Data flow from API through validator to database](dataflow.png)

<!-- POOR -->
![diagram](architecture.png)
![screenshot](login-ui.png)
```

### Image File Paths

**Local images** (preferred):
```markdown
<!-- Same directory -->
![Network diagram](network-topology.png)

<!-- Images subdirectory -->
![API flow](images/api-flow-diagram.png)

<!-- Organized by type -->
![Architecture](diagrams/system-architecture.png)
![Login UI](screenshots/login-page.png)
```

**Project structure**:
```
docs/
├── README.md
├── architecture.md
└── images/
    ├── diagrams/
    │   ├── system-architecture.png
    │   └── data-flow.png
    └── screenshots/
        ├── login-ui.png
        └── dashboard.png
```

### Clickable Images

```markdown
<!-- Thumbnail → full-size -->
[![Diagram thumbnail](thumb.png)](full-diagram.png)

<!-- Logo → homepage -->
[![Project logo](logo.png)](https://project.example.com "Visit homepage")
```

### LLM Image Guidelines

**When LLM should suggest an image**:

1. **Complex relationships** → Architecture diagram
   ```markdown
   System has client, API gateway, microservices, database cluster
   → Suggest: ![System architecture](images/architecture.png)
   ```

2. **Multi-step process** → Flowchart
   ```markdown
   Form submit → validation → DB save → email notification
   → Suggest: ![Registration flow](images/registration-flow.png)
   ```

3. **UI elements** → Screenshot
   ```markdown
   Click hamburger menu (top-right) → Settings → Preferences
   → Suggest: ![Settings menu](images/settings-menu.png)
   ```

**LLMs CANNOT create images**, but CAN:
- Suggest where images would help
- Write descriptive alt text
- Recommend diagram types
- Create placeholder references

**Placeholder pattern**:
```markdown
![Network topology with router, switches, VLANs](_TODO_network-topology.png)

> **TODO**: Create diagram showing:
> - SKS8300 router (192.168.10.13)
> - Two L2 switches
> - VLANs 10, 20, 30
```

### Image Format Recommendations

- **PNG**: Diagrams, screenshots, UI elements
- **JPG/JPEG**: Photos, complex images
- **SVG**: Vector diagrams (scalable, small files)
- **Avoid GIF**: No animations

**Size recommendations**:
- Diagrams: 800-1200px wide
- Screenshots: 1920px wide max
- Icons/logos: 200-400px
- Keep under 1MB when possible

---

## Blockquotes and Callouts

### Standard Blockquotes

```markdown
> This is a blockquote for notes or callouts.
> It can span multiple lines.

> Single line blockquote
```

**Common uses**:
- Document taglines/summaries
- Important notes
- Quoted content

```markdown
# Installation Guide

> A comprehensive guide to installing and configuring the application.

This guide covers...
```

### Callout Patterns

**Standard pattern** (works everywhere):
```markdown
> **Note**: This is important information.

> **Warning**: This action cannot be undone.

> **Tip**: Here's a helpful hint.
```

**Platform-specific** (if supported):
```markdown
<Note>
  This is a note callout with special formatting.
</Note>

<Warning>
  This is a warning callout.
</Warning>
```

---

## Task Lists

### Syntax

```markdown
- [ ] Unchecked item (incomplete)
- [x] Checked item (complete)
- [X] Also checked (uppercase works)
```

### When to Use Task Lists

**DO use for**:
- Setup/installation checklists
- Project roadmaps
- TODO items with binary status
- Verification steps

**DON'T use for**:
- Static feature lists (use regular lists)
- Published documentation
- Content without completion tracking

### Examples

**Setup checklist**:
```markdown
## Setup Checklist

- [x] Install dependencies
- [x] Configure environment
- [ ] Run tests
- [ ] Deploy to production
```

**Grouped tasks**:
```markdown
## Backend Setup

- [ ] Install Python 3.11
- [ ] Create virtual environment
- [ ] Install requirements

## Frontend Setup

- [ ] Install Node.js
- [ ] Install npm packages
- [ ] Build production assets
```

### Best Practices

1. **Keep descriptions concise** (one line)
2. **Group related tasks** under headings
3. **Limit nesting** (max 2 levels)
4. **Use with code blocks**:
   ```markdown
   - [x] Install dependencies:
     ```bash
     npm install
     ```

   - [ ] Run tests:
     ```bash
     npm test
     ```
   ```

### Platform Compatibility

**Supported**: GitHub, GitLab, VS Code, Obsidian, Notion
**Limited**: CommonMark parsers (renders as plain list)
**Fallback**: Degrades gracefully to regular lists

---

## Special Elements

### Horizontal Rules

**Syntax**: `---`, `***`, or `___` on own line

```markdown
Section one content.

---

Section two content.
```

**Best Practice**: Use `---` for consistency

### Escaping Special Characters

Use backslash `\` to escape markdown syntax:

```markdown
\# This is not a heading
\* This is not a list item
\` This is not code
```

### HTML in Markdown

**Avoid when possible**, but allowed for special cases:

```markdown
<!-- Rare exception: complex layouts -->
<div class="custom">
  Content here
</div>
```

**Best Practice**: Use pure markdown unless absolutely necessary

---

## Document Front Matter

### YAML Front Matter

For systems that support it:

```markdown
---
title: Document Title
description: Brief description
author: Author Name
date: 2025-11-03
tags: [tag1, tag2, tag3]
---

# Document Title

Content starts here.
```

### Common Fields

| Field | Purpose | Example |
|-------|---------|---------|
| `title` | Document title | `"Installation Guide"` |
| `description` | Brief summary | `"How to install"` |
| `author` | Author name | `"Engineering Team"` |
| `date` | Creation date | `"2025-11-03"` |
| `tags` | Category tags | `["tutorial", "setup"]` |
| `version` | Doc version | `"1.2"` |

### Agent Definitions

```markdown
---
name: code-reviewer
description: Expert code reviewer
tools: Read, Grep, Glob, Bash
model: sonnet
---

# Code Reviewer Agent

You are a senior code reviewer...
```

---

## Best Practices

### 1. Clarity Over Cleverness

- Use simple, direct language
- Define technical terms on first use
- Break complex concepts into steps

### 2. Consistent Terminology and Formatting

**Terminology**:
- Use same term throughout (don't switch between "configuration file" and "config file")
- Create glossary for complex docs

**Formatting**:
- Choose one pattern and stick to it **throughout the project**
- Avoid mixed styles in the same document and across documents
- Examples: list markers (`*` not mixed with `-`), link paths (relative vs absolute)

### 3. Active Voice

```markdown
<!-- BETTER -->
Run the following command to install:

<!-- WORSE -->
The following command should be run for installation:
```

### 4. Imperative Mood for Instructions

```markdown
<!-- GOOD -->
1. Open the terminal
2. Navigate to project directory
3. Run `npm install`

<!-- AVOID -->
1. You should open the terminal
2. You will navigate to project directory
```

### 5. Examples Are Essential

Always provide examples for:
- Commands
- Configuration
- Code usage
- Expected output

### 6. Progressive Enhancement

Layer information:
1. Basic usage first
2. Common variations next
3. Advanced options last
4. Edge cases in separate section

### 7. Scannable Content

Make documents scannable:
- Descriptive headings
- Short paragraphs (3-5 lines)
- Bullet points for lists
- Bold for key terms
- Tables for structured data

### 8. Document Size Guidelines

**Recommended lengths**:
- Quick starts: 150-300 lines
- Reference docs: 300-600 lines
- Comprehensive guides: 600-1000 lines
- Over 1000 lines? Split into multiple documents

### 9. Modular Documentation

**Benefits**:
- LLM agents load only relevant content
- Easier to maintain
- Better navigation
- Parallel editing

**Pattern**:
```
docs/
├── README.md (overview + navigation)
├── getting-started/
├── guides/
└── reference/
```

### 10. Cross-Linking

Build navigation between related docs:
- Link to prerequisites
- Reference related guides
- Add "See Also" sections
- Create navigation hubs

---

## Common Pitfalls

### 1. Multiple H1 Headings

**WRONG**: Multiple `#` headings
```markdown
# First Title
...
# Second Title
```

**CORRECT**: Only one `#` per document
```markdown
# Document Title
...
## Major Section
```

### 2. Skipping Heading Levels

**WRONG**: Jumping levels
```markdown
## Section
#### Subsection
```

**CORRECT**: Sequential levels
```markdown
## Section
### Subsection
```

### 3. Missing Code Block Languages

**WRONG**: No language specified
````markdown
```
npm install package
```
````

**CORRECT**: Language specified
````markdown
```bash
npm install package
```
````

### 4. Vague Link Text

**WRONG**:
```markdown
Click [here](./guide.md) for details
See [this document](./doc.md)
[https://example.com](https://example.com)
```

**CORRECT**:
```markdown
See the [installation guide](./guide.md) for setup instructions
Review the [API reference](./doc.md) for complete documentation
Visit the [project homepage](https://example.com)
```

### 5. External Links Instead of Local

**WRONG**: External when local should exist
```markdown
See [Python docs](https://docs.python.org/3/tutorial/)
```

**CORRECT**: Local documentation
```markdown
See [Python Guide](./reference/python-guide.md)
```

### 6. Missing or Poor Alt Text

**WRONG**:
```markdown
![](diagram.png)
![diagram.png](diagram.png)
![image](architecture.png)
```

**CORRECT**:
```markdown
![Three-tier architecture with client, API, database](architecture.png)
![Login form with username and password fields](login-screen.png)
```

### 7. Inconsistent Formatting

**Avoid mixed styles in the same document and across the project.**

Choose one pattern and stick to it **throughout the project**:
- List markers (`*` vs `-` vs `+`)
- Heading capitalization
- Code block styles
- Link formats (relative vs absolute paths)

**Example of inconsistency**:
```markdown
<!-- Document A uses * for lists -->
* Item 1
* Item 2

<!-- Document B uses - for lists -->
- Item 1
- Item 2

<!-- This creates confusion across the project -->
```

**Consistent approach**:
```markdown
<!-- All documents in project use * for lists -->
* Item 1
* Item 2
```

### 8. Using Task Lists for Static Content

**WRONG**: Task lists for feature lists
```markdown
## Features
- [ ] Authentication system
- [ ] User dashboard
```

**CORRECT**: Regular lists for features
```markdown
## Features
* Authentication system
* User dashboard
```

### 9. Massive Single Files

**WRONG**: One 5000-line file with everything

**CORRECT**: Modular structure
```
docs/
├── README.md (200 lines)
├── getting-started/
│   ├── installation.md (300 lines)
│   └── quickstart.md (250 lines)
└── guides/
    └── configuration.md (400 lines)
```

### 10. No Table of Contents for Long Docs

**Rule**: Add TOC for documents over 200 lines or 3+ major sections

```markdown
# Long Guide

## Table of Contents

1. [Section 1](#section-1)
2. [Section 2](#section-2)
3. [Section 3](#section-3)

## Section 1
...
```

---

## Template Library

### Quick Start Template

```markdown
# Quick Start: [Feature Name]

> Get started with [feature] in under 5 minutes

## Prerequisites

Before you begin, ensure you have:
* Requirement 1
* Requirement 2

## Step 1: [First Action]

Description of the step.

```bash
command --example
```

## Step 2: [Second Action]

Description of the step.

```bash
another-command --option
```

## Verify Installation

Confirm everything works:

```bash
verification-command
```

Expected output:

```text
Success message
```

## Next Steps

- [Advanced Configuration](./advanced.md)
- [API Reference](./api-reference.md)
```

### Configuration Reference Template

```markdown
# [Feature] Configuration

> Complete configuration reference for [feature]

## Configuration File

**Location**: `~/.config/app/config.json`

## Configuration Format

```json
{
  "option1": "value",
  "option2": 123,
  "option3": true
}
```

## Available Options

### option1

* **Type**: `string`
* **Default**: `"default-value"`
* **Required**: Yes

Description of what this option controls.

**Example**:

```json
{
  "option1": "custom-value"
}
```

## Complete Example

```json
{
  "option1": "production",
  "option2": 500,
  "option3": true
}
```

## See Also

- [Quick Start Guide](./quickstart.md)
- [Troubleshooting](./troubleshooting.md)
```

### API Reference Template

```markdown
# API Reference: [Module Name]

> Complete API documentation for [module]

## Methods

### methodName()

Description of what the method does.

**Syntax**:

```javascript
methodName(param1, param2, options)
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `param1` | `string` | Yes | Description |
| `param2` | `number` | No | Description |
| `options` | `Object` | No | Config options |

**Returns**: `Promise<Result>`

**Example**:

```javascript
const result = await methodName('value', 42, {
  timeout: 10000
});
```

**Errors**:

| Error | Cause | Resolution |
|-------|-------|------------|
| `InvalidParamError` | Invalid param1 | Check format |
| `TimeoutError` | Timeout | Increase timeout |
```

### Troubleshooting Template

```markdown
# Troubleshooting

> Solutions to common issues

## Common Issues

### Issue: [Problem Description]

**Symptoms**:
* Symptom 1
* Symptom 2

**Cause**: Explanation

**Solution**:

1. Step one to resolve
2. Step two to resolve

```bash
fix-command --option
```

**Prevention**: How to avoid this

---

### Issue: [Another Problem]

**Symptoms**:
* Different symptom

**Solution**:

Try solution A:

```bash
solution-a-command
```

If that doesn't work, try solution B:

```bash
solution-b-command
```

## Getting More Help

- [Documentation](./docs.md)
- [GitHub Issues](https://github.com/user/repo/issues)
```

---

## Summary

### Key Principles for LLM-Generated Docs

1. **Structure first** - Use appropriate templates
2. **Local links always** - Prefer local files over external
3. **Descriptive link text** - Explain destination clearly
4. **Modular design** - One topic per file, cross-link extensively
5. **Code blocks with language** - Always specify syntax highlighting
6. **Scannable content** - Short paragraphs, clear headings
7. **Progressive disclosure** - Simple to complex
8. **Examples everywhere** - Show, don't just tell
9. **Consistent formatting** - Follow established patterns
10. **Context-efficient** - Keep documents focused and appropriately sized

### Documentation Quality Checklist

**Good documentation is**:
- ✅ **Clear** - Easy to understand
- ✅ **Complete** - Covers necessary information
- ✅ **Concise** - No unnecessary verbosity
- ✅ **Consistent** - Follows established patterns
- ✅ **Connected** - Well-linked and navigable
- ✅ **Current** - Up to date with reality

---

**Version History**:
- **2.0** (2025-11-03): Optimized for context efficiency, enhanced links section, modular design focus
- **1.1** (2025-11-03): Added task lists, enhanced links, expanded images section
- **1.0** (2025-11-03): Initial release

**Related Documentation**:
- [Quick Reference](./MARKDOWN-QUICK-REF.md) - Fast lookup cheat sheet
- [CommonMark Specification](https://commonmark.org/)
- [GitHub Flavored Markdown](https://github.github.com/gfm/)
