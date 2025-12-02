#!/bin/bash
# =============================================================================
# fix.sh - Auto-fix linting and formatting issues
# =============================================================================
# Usage: ./scripts/fix.sh
#
# This script will:
#   1. Auto-fix all safe Ruff lint issues (~80% of findings)
#   2. Format all Python files
#   3. Show remaining issues that need manual attention
#
# After running:
#   - Review changes with: git diff
#   - Run tests: pytest
#   - Commit if everything looks good
# =============================================================================

# Change to mcp-server directory (script location parent)
cd "$(dirname "$0")/.."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Auto-Fix Mode ===${NC}"
echo ""

# -----------------------------------------------------------------------------
# Step 1: Ruff Auto-Fix
# -----------------------------------------------------------------------------
echo -e "${CYAN}[1/3] Running Ruff auto-fix...${NC}"
ruff check . --fix
echo ""

# -----------------------------------------------------------------------------
# Step 2: Ruff Format
# -----------------------------------------------------------------------------
echo -e "${CYAN}[2/3] Running Ruff formatter...${NC}"
ruff format .
echo ""

# -----------------------------------------------------------------------------
# Step 3: Show Remaining Issues
# -----------------------------------------------------------------------------
echo -e "${CYAN}[3/3] Checking for remaining issues...${NC}"
echo ""

# Count remaining Ruff issues
RUFF_ISSUES=$(ruff check . 2>/dev/null | grep -c "^" || echo "0")

if [ "$RUFF_ISSUES" -gt 0 ]; then
    echo -e "${YELLOW}Remaining Ruff issues (need manual fix):${NC}"
    ruff check . --statistics
    echo ""
else
    echo -e "${GREEN}✓ No remaining Ruff issues${NC}"
fi

# Count MyPy issues (don't fail, just report)
echo ""
echo -e "${CYAN}MyPy status:${NC}"
MYPY_OUTPUT=$(mypy . 2>&1)
MYPY_ERRORS=$(echo "$MYPY_OUTPUT" | grep -c "error:" || echo "0")

if [ "$MYPY_ERRORS" -gt 0 ]; then
    echo -e "${YELLOW}MyPy errors: $MYPY_ERRORS${NC}"
    echo ""
    echo "Top error types:"
    echo "$MYPY_OUTPUT" | grep -oP '\[\K[^\]]+' | sort | uniq -c | sort -rn | head -10
    echo ""
    echo "Run 'mypy .' for full output"
else
    echo -e "${GREEN}✓ No MyPy errors${NC}"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}=== Auto-fix complete ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Review changes:  git diff"
echo "  2. Run tests:       pytest"
echo "  3. Full check:      ./scripts/lint.sh"
