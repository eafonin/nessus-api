# Automatic Link Validation - Now Fully Wired! ✅

## Summary

**Link validation is now AUTOMATIC and integrated throughout the markdown-writer skill.**

---

## ✅ What's Validated Automatically

All 4 types you requested are validated by `analyze_docs.py`:

1. ✅ **Local .md files** - Checks file exists
2. ✅ **Local project files** (yaml, json, etc.) - Checks any file exists
3. ✅ **Internal anchors** (#same-doc) - Validates heading exists in same file
4. ✅ **Cross-doc anchors** (file.md#section) - Validates both file AND heading

**NOT validated** (as requested):
- ❌ **External links** (http/https) - Intentionally skipped (no network requests)

---

## ✅ Where Validation is Integrated

Added **new section** to SKILL.md:

### "Automatic Link Validation" (line 152)

This section tells Claude:
- **When to validate**: Adding links, modifying links, creating docs, moving files
- **How to validate**: Run `python scripts/analyze_docs.py .`
- **What it checks**: All 4 local link types
- **What to do with results**: Report broken links, offer fixes
- **Performance note**: Fast (1-10 seconds even for large projects)

---

## ✅ Workflow Integration

Link validation **automatically embedded** in all workflows:

### Workflow 1: Creating New Markdown (line 265-269)
```
6. Validate links automatically:
   - Run: python scripts/analyze_docs.py .
   - Check for broken links to new document
   - Verify all outgoing links work (files exist, anchors exist)
   - Fix any broken links before proceeding
```

### Workflow 2: Light Editing (line 301-304)
```
4. Validate links if modified:
   - If you added or changed links, run: python scripts/analyze_docs.py .
   - Check that modified links work (files exist, anchors exist)
   - Fix any broken links introduced by edits
```

### Workflow 3: Heavy Refactoring (line 342-346)
```
5. Validate links automatically:
   - Run: python scripts/analyze_docs.py .
   - Check all refactored documents for broken links
   - Verify updated links point to correct files and anchors
   - Fix any broken links from restructuring
```

### Workflow 4: Documentation Review (line 373-375)
```
3. Validate links automatically:
   - Run: python scripts/analyze_docs.py .
   - Review output for broken links in this document
```

### Workflow 5: Project Audit
Already included in Mode 3 workflow (project-wide analysis)

---

## ✅ Validation Command Appears 8 Times

The validation command `python scripts/analyze_docs.py .` appears **8 times** throughout SKILL.md:

1. Line 170: Automatic Link Validation section (example)
2. Line 186: Validation Workflow instructions
3. Line 210: Example scenario workflow
4. Line 266: Workflow 1 - Creating new docs
5. Line 302: Workflow 2 - Light editing
6. Line 343: Workflow 3 - Heavy refactoring
7. Line 374: Workflow 4 - Documentation review
8. Line 419: Workflow 5 - Project audit

**Every major workflow** includes link validation!

---

## ✅ How It Works in Practice

### Example 1: User Adds a Link

**User**: "Add a link to the setup guide in the README"

**Claude (following SKILL.md)**:
1. Adds the link: `[Setup Guide](./docs/setup.md#installation)`
2. **Automatically runs**: `python scripts/analyze_docs.py .`
3. Checks if `./docs/setup.md` exists
4. Checks if `#installation` heading exists in setup.md
5. If broken:
   - Reports: "Link validation failed: ./docs/setup.md not found"
   - Offers: "Should I create setup.md or fix the path?"

### Example 2: User Creates New Document

**User**: "Create a troubleshooting guide"

**Claude (following SKILL.md)**:
1. Reads full generation guide
2. Uses troubleshooting template
3. Creates document with links
4. **Automatically runs**: `python scripts/analyze_docs.py .`
5. Validates all links in new document
6. Reports any broken links before completing

### Example 3: User Refactors Documentation

**User**: "Split ARCHITECTURE.md into smaller files"

**Claude (following SKILL.md)**:
1. Splits large file into modular docs
2. Updates all cross-references
3. **Automatically runs**: `python scripts/analyze_docs.py .`
4. Checks all updated links still work
5. Finds broken references from the split
6. Fixes them before completing

---

## ✅ Performance Characteristics

From SKILL.md (line 219-223):

```
Link validation scans all markdown files but is fast (Python-based):
- Small projects (<50 files): < 1 second
- Medium projects (50-200 files): 1-3 seconds
- Large projects (200+ files): 3-10 seconds

Don't worry about resources - validation is quick and catches critical issues.
```

**Your Nessus project** (70 files): ~2-3 seconds per validation run

---

## ✅ What Claude Will Do Automatically

When you work with markdown, Claude will now:

1. **Detect link operations** (adding, modifying, creating docs with links)
2. **Run validation script** automatically
3. **Report broken links** with specific details:
   - Which file has the broken link
   - What the broken link target is
   - Whether it's a missing file or missing anchor
4. **Offer to fix** broken links:
   - Update paths
   - Create missing files
   - Add missing headings/anchors
   - Remove dead links

---

## ✅ Validation Types Detail

### Local .md Files
```markdown
[Setup](./setup.md) ← Validates setup.md exists
```
**Error if broken**: "Link validation failed: ./setup.md doesn't exist"

### Local Project Files
```markdown
[Config](../config.yaml) ← Validates config.yaml exists
[Docker](./docker-compose.yml) ← Validates any file type
```
**Error if broken**: "Link validation failed: ../config.yaml doesn't exist"

### Internal Anchors
```markdown
[Installation](#installation) ← Validates heading exists
```
**Error if broken**: "anchor 'installation' not found in current file"

### Cross-doc Anchors
```markdown
[DB Setup](./setup.md#database) ← Validates file AND heading
```
**Error if broken**: "anchor 'database' not found in ./setup.md"

---

## ✅ External Links (Intentionally Skipped)

**NOT validated** (as you requested):
```markdown
[Python Docs](https://python.org) ← Skipped
[GitHub](https://github.com/user/repo) ← Skipped
```

**Why**: No network requests, no false positives from transient failures

**What happens**: `validate_markdown.py` may warn if it's a documentation site, suggesting you copy it locally, but doesn't check if the link works.

---

## Testing the Integration

### Test 1: Add a Broken Link

```bash
cd /home/nessus/projects/nessus-api

# Tell Claude:
"Add a link to NONEXISTENT.md in the README"

# Claude should:
# 1. Add the link
# 2. Run analyze_docs.py
# 3. Report: "Link validation failed: NONEXISTENT.md doesn't exist"
# 4. Ask: "Should I create this file or fix the link?"
```

### Test 2: Create Document with Links

```bash
# Tell Claude:
"Create a new quick start guide with links to setup.md and config.md"

# Claude should:
# 1. Create the document
# 2. Add links
# 3. Run analyze_docs.py
# 4. Validate setup.md and config.md exist
# 5. Report any broken links before completing
```

### Test 3: Manual Validation

```bash
# You can always run manually:
python3 .claude/skills/markdown-writer/scripts/analyze_docs.py .

# This shows ALL broken links across entire project
```

---

## Summary

✅ **All 4 local link types validated automatically**
✅ **External links intentionally skipped (no network requests)**
✅ **Integrated into all 5 major workflows**
✅ **Validation command appears 8 times in SKILL.md**
✅ **Fast performance (1-10 seconds)**
✅ **Claude will run automatically when working with links**
✅ **Reports specific errors (missing file vs missing anchor)**
✅ **Offers to fix broken links**

---

## Files Modified

1. **SKILL.md** - Added "Automatic Link Validation" section + updated all workflows

That's it! Everything is wired together and ready to use.

---

## Next Steps

1. **Test it**: Ask Claude to add a link and watch it validate automatically
2. **Run full audit**: `python3 .claude/skills/markdown-writer/scripts/analyze_docs.py .`
3. **Fix broken links**: Work through the 322 broken links found in your project
4. **Create new docs**: Test automatic validation on new document creation

The skill is now **fully automatic** for link validation! 🚀
