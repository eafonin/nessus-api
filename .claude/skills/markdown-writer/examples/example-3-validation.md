# Example 3: Validation Workflow

This example demonstrates running validation on a real project's documentation.

## Context

You're working on the Nessus MCP Server project which has multiple markdown documentation files including:
- `README.md` - Main project documentation
- `PHASE_0_FOUNDATION.md` - Phase 0 plan
- `ARCHITECTURE_v2.2.md` - Architecture documentation
- Various other phase and technical documents

You want to ensure all documentation meets LLM-optimized standards.

## Step 1: Activate the Markdown Writer Skill

When working with markdown, the skill is automatically considered. State your intent:

> "I want to validate all markdown documentation in this project to ensure it meets LLM-optimized standards."

## Step 2: Determine Operation Mode

Based on the decision tree:
- Task: Validation of existing documents
- Mode: **Mode 1 (Light Operations)** - Use Quick Reference
- Tool: Validation script

## Step 3: Run Validation

```bash
python .claude/skills/markdown-writer/scripts/validate_markdown.py .
```

## Step 4: Review Results

Example output:

```
================================================================================
MARKDOWN VALIDATION REPORT
================================================================================

Scanned 15 file(s)
Found 8 issue(s) and 12 warning(s)

================================================================================
ISSUES (Must Fix)
================================================================================

📄 ./ALTERNATIVE_FIX_ANALYSIS.md
   ❌ Multiple H1 headings found (3). Only ONE allowed.
   ❌ Skipped heading level: H1 → H3 (around line 45)

📄 ./DEBUGGING.md
   ❌ Found 5 code block(s) without language identifier
   ❌ Vague link text found ('[here](') Use descriptive text instead.

📄 ./docs/api-guide.md
   ❌ Missing H1 heading (document title)

================================================================================
WARNINGS (Should Fix)
================================================================================

📄 ./PHASE_1_REAL_NESSUS.md
   ⚠️  Document too long (1243 lines). Consider splitting (ideal: 200-1000 lines)
   ⚠️  Line 67: Missing blank line before heading

📄 ./README.md
   ⚠️  Line 145: Possible command without backticks: npm install

================================================================================
CLEAN FILES (8)
================================================================================
   ✅ ./ARCHITECTURE_v2.2.md
   ✅ ./MINIMAL_FIX_SUMMARY.md
   ✅ ./PHASE_0_FOUNDATION.md
   ✅ ./PHASE0_STATUS.md
   ✅ ./PHASE_2_SCHEMA_RESULTS.md
   ✅ ./PHASE_3_OBSERVABILITY.md
   ✅ ./PHASE_4_PRODUCTION.md
   ✅ ./NESSUS_MCP_SERVER_REQUIREMENTS.md

================================================================================
SUMMARY
================================================================================
Total files: 15
Clean files: 8
Files with issues: 3
Files with warnings: 2
Total issues: 8
Total warnings: 12

❌ 8 issue(s) need attention
```

## Step 5: Prioritize Fixes

Based on results, prioritize:

### Critical (Fix Immediately)
1. **ALTERNATIVE_FIX_ANALYSIS.md** - Multiple H1 headings, skipped levels
2. **DEBUGGING.md** - Missing code block languages, vague links
3. **docs/api-guide.md** - Missing H1 heading

### High Priority
1. **PHASE_1_REAL_NESSUS.md** - Oversized (1243 lines), should split

### Medium Priority
1. Various files with missing blank lines
2. Commands without backticks

## Step 6: Fix Issues

For each issue, use the quick reference guide:

### Fixing Multiple H1 Headings

**Before** (ALTERNATIVE_FIX_ANALYSIS.md):
```markdown
# Alternative Fix Analysis

Some content...

# Option 1: Minimal Changes

More content...

# Option 2: Full Refactor
```

**After**:
```markdown
# Alternative Fix Analysis

Some content...

## Option 1: Minimal Changes

More content...

## Option 2: Full Refactor
```

### Fixing Code Blocks Without Languages

**Before** (DEBUGGING.md):
```markdown
Run the following:

```
npm test
```
```

**After**:
```markdown
Run the following:

```bash
npm test
```
```

### Fixing Vague Link Text

**Before** (DEBUGGING.md):
```markdown
See [here](./PHASE_0_FOUNDATION.md) for details.
```

**After**:
```markdown
See [Phase 0 Foundation documentation](./PHASE_0_FOUNDATION.md) for details.
```

### Fixing Missing H1

**Before** (docs/api-guide.md):
```markdown
## Overview

This guide covers the API...
```

**After**:
```markdown
# API Guide

> Complete guide to using the Nessus MCP Server API

## Overview

This guide covers the API...
```

## Step 7: Re-validate

After fixes:

```bash
python .claude/skills/markdown-writer/scripts/validate_markdown.py .
```

Expected result:
```
================================================================================
MARKDOWN VALIDATION REPORT
================================================================================

Scanned 15 file(s)
Found 0 issue(s) and 2 warning(s)

✅ No critical issues found!
```

## Step 8: Address Remaining Warnings

For the oversized document (PHASE_1_REAL_NESSUS.md at 1243 lines), consider:
1. Splitting into multiple focused documents
2. Moving detailed sections to separate files
3. Creating a navigation hub

This would transition to **Mode 2** (Heavy Refactoring) and require reading the full generation guide.

## Key Takeaways

1. **Validation is quick** - Run script, get immediate feedback
2. **Prioritize by severity** - Fix issues before warnings
3. **Use quick reference** - For fixing common problems
4. **Re-validate** - Ensure fixes are correct
5. **Escalate when needed** - Large refactoring needs full guide

## Result

- All critical issues fixed
- Documentation is LLM-optimized
- Knowledge integrity maintained
- Project documentation is healthy
