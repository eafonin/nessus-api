#!/bin/bash
# =============================================================================
# lint.sh - Static analysis check (CI/pre-push)
# =============================================================================
# Usage: ./scripts/lint.sh
# Exit codes:
#   0 - All checks passed
#   1 - Linting errors found
#   2 - Formatting issues found
#   3 - Type errors found
#
# Performance targets:
#   - Ruff check: <1 second
#   - Ruff format check: <0.5 seconds
#   - MyPy (warm cache): 1-2 seconds
# =============================================================================

set -e  # Exit on first error

# Change to mcp-server directory (script location parent)
cd "$(dirname "$0")/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Static Analysis ===${NC}"
echo ""

# -----------------------------------------------------------------------------
# Step 1: Ruff Lint Check
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[1/3] Ruff lint check...${NC}"
START=$(date +%s.%N)

if ! ruff check .; then
    echo -e "${RED}✗ Ruff found linting errors${NC}"
    echo ""
    echo "Run './scripts/fix.sh' to auto-fix, or fix manually"
    exit 1
fi

END=$(date +%s.%N)
DURATION=$(echo "$END - $START" | bc)
echo -e "${GREEN}✓ Ruff lint passed${NC} (${DURATION}s)"
echo ""

# -----------------------------------------------------------------------------
# Step 2: Ruff Format Check
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[2/3] Ruff format check...${NC}"
START=$(date +%s.%N)

if ! ruff format --check .; then
    echo -e "${RED}✗ Formatting issues found${NC}"
    echo ""
    echo "Run 'ruff format .' to fix"
    exit 2
fi

END=$(date +%s.%N)
DURATION=$(echo "$END - $START" | bc)
echo -e "${GREEN}✓ Formatting OK${NC} (${DURATION}s)"
echo ""

# -----------------------------------------------------------------------------
# Step 3: MyPy Type Check
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[3/3] MyPy type check...${NC}"
START=$(date +%s.%N)

if ! mypy .; then
    echo -e "${RED}✗ Type errors found${NC}"
    echo ""
    echo "Fix type annotations or add targeted '# type: ignore[error-code]'"
    exit 3
fi

END=$(date +%s.%N)
DURATION=$(echo "$END - $START" | bc)
echo -e "${GREEN}✓ Type check passed${NC} (${DURATION}s)"
echo ""

# -----------------------------------------------------------------------------
# Success
# -----------------------------------------------------------------------------
echo -e "${GREEN}=== All checks passed ✓ ===${NC}"
