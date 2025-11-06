# Markdown Quick Reference for Claude Agents

**Version**: 2.0
**Purpose**: Fast reference for generating LLM-friendly, modular markdown documentation
**For comprehensive details**: See [MARKDOWN-GENERATION-GUIDE.md](./MARKDOWN-GENERATION-GUIDE.md)

---

## Document Structure

### Heading Rules

```markdown
# Document Title                    # ONE per document, no text before
> Optional tagline

## Major Section                    # H2 for main sections
### Subsection                      # H3 for subsections
#### Detail Level                   # H4 for details
```

**Rules**:
- Only ONE `#` (H1) per document
- Don't skip levels (`##` → `####` is wrong)
- Blank lines before and after headings
- Title case for H1-H3, sentence case for H4-H6

---

## Links (MOST IMPORTANT)

### Link Priority Hierarchy

```
1. Local file links    (same repository)    ← ALWAYS PREFER
2. Internal anchors    (same document)      ← For navigation
3. External links      (other sites)        ← ONLY when necessary
```

### Local File Links

```markdown
<!-- Same directory -->
[Configuration Guide](configuration.md)
[Setup Instructions](setup.md)

<!-- Subdirectory -->
[API Reference](docs/api-reference.md)
[CLI Commands](reference/cli-commands.md)

<!-- Parent directory -->
[Project README](../README.md)
[Main Guide](../../guides/main.md)

<!-- With section anchor -->
[Installation Steps](setup.md#installation)
[Database Config](config.md#database-configuration)
```

### Internal Anchors

**Auto-generated from headings**:
```markdown
## Installation Guide              → #installation-guide
### Step 1: Install                → #step-1-install
#### API Configuration             → #api-configuration
### Getting Started                → #getting-started
```

**Usage**:
```markdown
Jump to [Installation Guide](#installation-guide)
See [API Configuration](#api-configuration) for details
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
```

### Cross-Document Linking

```markdown
<!-- Link to section in another file -->
[Database Setup](./setup.md#database-configuration)
[Authentication Flow](../api/auth.md#oauth2-flow)

<!-- Organized link sections -->
## See Also

- [Quick Start Guide](./quickstart.md) - Get started in 5 minutes
- [Configuration Reference](./config.md) - All configuration options
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
```

### External Links (Use Sparingly)

**When appropriate**:
- Official tool documentation (frequently updated)
- Live services (GitHub, cloud providers)
- Standards documents

**When to avoid**:
- External docs that should be copied locally
- Tutorial content (copy and adapt)
- Anything that might disappear

> **Note**: Consider copying external documentation to local GitLab for offline access and version control.

---

## Text Formatting

| Style | Syntax | When to Use |
|-------|--------|-------------|
| **Bold** | `**text**` | Important terms, emphasis, labels |
| *Italic* | `*text*` | Subtle emphasis, variables |
| `Code` | `` `text` `` | Commands, files, variables, functions |

**Examples**:
```markdown
**Required**: Install Node.js 18 or newer
Replace *username* with your actual username
Run the `npm install` command
Edit the `.env` file in your project root
```

---

## Lists

### Unordered Lists

```markdown
* First item
* Second item
  * Nested item (2 spaces indent)
  * Another nested item
* Third item
```

### Ordered Lists

```markdown
1. First step
2. Second step
3. Third step
```

### Lists with Multiple Paragraphs

```markdown
* **Item one**: Brief description.

  Continuation paragraph for item one.
  Must be indented to align with list content.

* **Item two**: Brief description.

  ```bash
  # Code blocks can be nested
  command --option
  ```
```

---

## Code Blocks

### Basic Syntax

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

| Language | Identifier | Example |
|----------|-----------|---------|
| Bash/Shell | `bash`, `sh` | `` ```bash `` |
| Python | `python`, `py` | `` ```python `` |
| JavaScript | `javascript`, `js` | `` ```js `` |
| JSON | `json` | `` ```json `` |
| YAML | `yaml`, `yml` | `` ```yaml `` |
| Plain Text | `text`, `txt` | `` ```text `` |

**Always specify language** for syntax highlighting.

---

## Tables

### Basic Table

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |
```

### Alignment

```markdown
| Left Aligned | Center Aligned | Right Aligned |
|:-------------|:--------------:|--------------:|
| Left         | Center         | Right         |
```

### Tables with Code

```markdown
| Command | Description |
|---------|-------------|
| `npm install` | Install dependencies |
| `npm test` | Run test suite |
```

---

## Blockquotes

```markdown
> This is a blockquote for notes or callouts.

> **Note**: Important information here.

> **Warning**: This action cannot be undone.

> **Tip**: Helpful hint for users.
```

---

## Images

```markdown
<!-- Basic syntax -->
![Alt text describing image](image.png)

<!-- With path -->
![Network topology diagram](images/network-topology.png)

<!-- Good alt text - descriptive and specific -->
![Three-tier architecture with client, API gateway, and database](architecture.png)
```

**Alt text rules**:
- Be descriptive and specific
- Keep under 125 characters
- Skip "image of" or "diagram of"

---

## Task Lists

```markdown
- [ ] Incomplete task
- [x] Completed task
- [ ] Another incomplete task
```

**When to use**: Setup checklists, roadmaps, TODO items
**When NOT to use**: Static feature lists, published docs

---

## Horizontal Rules

```markdown
Content above.

---

Content below.
```

---

## Top 8 Pitfalls to Avoid

1. **Multiple H1 headings** - Only ONE `#` per document
2. **No language on code blocks** - Always use `` ```bash ``, `` ```python ``, etc.
3. **Vague link text** - Avoid "here", "this", use descriptive text
4. **External links when local exists** - Prefer local files for documentation
5. **Missing alt text on images** - Always describe images for LLM agents
6. **Skipping heading levels** - Don't jump from `##` to `####`
7. **No blank lines around blocks** - Always separate headings, code, lists
8. **Inconsistent formatting** - Choose one pattern (list markers, link styles) and stick to it **throughout the project**

---

## Modular Documentation Pattern

### Recommended Structure

```
docs/
├── README.md                    # Overview + navigation hub
├── getting-started/
│   ├── installation.md         # Installation guide
│   └── quickstart.md           # Quick start tutorial
├── guides/
│   ├── configuration.md        # Configuration reference
│   ├── deployment.md           # Deployment guide
│   └── troubleshooting.md      # Troubleshooting tips
└── reference/
    ├── api.md                  # API reference
    └── cli.md                  # CLI commands reference
```

### Navigation Hub Pattern

```markdown
# Project Documentation

## Getting Started

- [Installation](./getting-started/installation.md) - Install and setup
- [Quick Start](./getting-started/quickstart.md) - Get running in 5 minutes

## Guides

- [Configuration](./guides/configuration.md) - Configure the application
- [Deployment](./guides/deployment.md) - Deploy to production
- [Troubleshooting](./guides/troubleshooting.md) - Solve common issues

## Reference

- [API Reference](./reference/api.md) - Complete API documentation
- [CLI Commands](./reference/cli.md) - Command-line interface
```

---

## Document Templates

### Quick Start Template

```markdown
# Quick Start: [Feature Name]

> Get started with [feature] in under 5 minutes

## Prerequisites

Before you begin, ensure you have:
* Requirement 1
* Requirement 2

## Step 1: [First Action]

Description.

```bash
command --example
```

## Step 2: [Second Action]

Description.

## Next Steps

- [Advanced Configuration](./advanced.md)
- [API Reference](./api-reference.md)
```

### Configuration Reference Template

```markdown
# [Feature] Configuration

> Complete configuration reference for [feature]

## Configuration File

Location: `~/.config/app/config.json`

## Available Options

### option_name

* **Type**: `string`
* **Default**: `"default-value"`
* **Required**: Yes

Description of what this option controls.

**Example**:

```json
{
  "option_name": "custom-value"
}
```

## See Also

- [Quick Start Guide](./quickstart.md)
- [Troubleshooting](./troubleshooting.md)
```

---

## LLM Agent Guidelines

### When Generating Documentation

1. **Start with structure** - Choose appropriate template
2. **Prefer local links** - Keep documentation self-contained
3. **Use descriptive link text** - Explain destination clearly
4. **Always specify code block language** - Enable syntax highlighting
5. **Keep documents focused** - One topic per file, 200-500 lines ideal
6. **Cross-link extensively** - Build navigation between related docs
7. **Write for scanning** - Short paragraphs, clear headings, examples

### Decision Tree: Link Type

```
Need to link to information?
├─ Is it in this document?
│  └─ Use internal anchor: [Section](#section-anchor)
├─ Is it in this repository?
│  └─ Use local file link: [Doc](./doc.md)
├─ Should it be in this repository?
│  └─ Create local file first, then link to it
└─ Must be external?
   └─ Use external link with descriptive text
```

### Document Size Recommendations

- **Cheat sheets**: 100-200 lines
- **Quick start guides**: 150-300 lines
- **Reference docs**: 300-600 lines
- **Comprehensive guides**: 600-1000 lines
- **Over 1000 lines?** → Split into multiple documents

---

## Version History

- **2.0** (2025-11-03): Quick reference created, focus on links and modularity
- **1.1** (2025-11-03): Full guide enhanced with task lists, images, links
- **1.0** (2025-11-03): Initial comprehensive guide

---

**For detailed information, edge cases, and advanced topics**: See [MARKDOWN-GENERATION-GUIDE.md](./MARKDOWN-GENERATION-GUIDE.md)
