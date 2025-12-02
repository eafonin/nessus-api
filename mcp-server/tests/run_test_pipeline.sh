#!/bin/bash
##############################################################################
# Nessus MCP Server - Layered Test Pipeline
##############################################################################
#
# This script runs the test suite using a layered architecture:
#
#   Layer 01: Infrastructure     [<1s]    Connectivity checks (Nessus, Redis)
#   Layer 02: Internal           [~30s]   Core modules with mocked dependencies
#   Layer 03: External Basic     [~1min]  Single MCP tool calls with real services
#   Layer 04: Full Workflow      [5-10m]  Complete E2E scan workflows
#
# Usage:
#   ./run_test_pipeline.sh [OPTIONS]
#
# Options:
#   --quick     Run only layer01 and layer02 (fastest)
#   --standard  Run layer01, layer02, layer03 (default)
#   --full      Run all layers including layer04 E2E tests
#   --layer N   Run only specified layer (1-4)
#
# Run from inside Docker container:
#   cd /app && tests/run_test_pipeline.sh
#
# Run from host:
#   docker compose exec mcp-api tests/run_test_pipeline.sh
#
##############################################################################

# Note: We don't use 'set -e' because we need to handle test failures gracefully

# Parse arguments
RUN_MODE="standard"
SPECIFIC_LAYER=""
for arg in "$@"; do
    case $arg in
        --quick)
            RUN_MODE="quick"
            ;;
        --standard)
            RUN_MODE="standard"
            ;;
        --full)
            RUN_MODE="full"
            ;;
        --layer)
            # Next arg is the layer number
            ;;
        1|2|3|4)
            if [[ "$SPECIFIC_LAYER" == "" ]]; then
                SPECIFIC_LAYER=$arg
            fi
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo
    echo "=============================================================================="
    echo -e "${BLUE}$1${NC}"
    echo "=============================================================================="
    echo
}

print_layer() {
    echo
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Track results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

run_layer() {
    local layer_num="$1"
    local layer_name="$2"
    local layer_dir="$3"
    local optional="${4:-false}"

    print_layer "Layer $layer_num: $layer_name"
    echo "Running: pytest tests/$layer_dir/ -v --tb=short"
    echo

    if pytest tests/$layer_dir/ -v --tb=short; then
        print_success "Layer $layer_num: $layer_name - PASSED"
        ((TESTS_PASSED++))
        return 0
    else
        if [[ "$optional" == "true" ]]; then
            print_warning "Layer $layer_num: $layer_name - SKIPPED (optional)"
            ((TESTS_SKIPPED++))
            return 0
        else
            print_error "Layer $layer_num: $layer_name - FAILED"
            ((TESTS_FAILED++))
            return 1
        fi
    fi
}

##############################################################################
# Start Test Pipeline
##############################################################################

print_header "Nessus MCP Server - Layered Test Pipeline"

echo "Configuration:"
echo "  Mode: $RUN_MODE"
if [[ -n "$SPECIFIC_LAYER" ]]; then
    echo "  Specific Layer: $SPECIFIC_LAYER"
fi
echo "  Date: $(date)"
echo "  Working Dir: $(pwd)"
echo

# Show what will run based on mode
case $RUN_MODE in
    quick)
        echo "Running: Layer 01 (Infrastructure) + Layer 02 (Internal)"
        ;;
    standard)
        echo "Running: Layer 01-03 (Infrastructure → External Basic)"
        ;;
    full)
        echo "Running: All Layers (01-04) including E2E workflows"
        ;;
esac
echo

##############################################################################
# Run Layers Based on Mode
##############################################################################

if [[ -n "$SPECIFIC_LAYER" ]]; then
    # Run specific layer only
    case $SPECIFIC_LAYER in
        1)
            run_layer "01" "Infrastructure" "layer01_infrastructure"
            ;;
        2)
            run_layer "02" "Internal" "layer02_internal"
            ;;
        3)
            run_layer "03" "External Basic" "layer03_external_basic"
            ;;
        4)
            run_layer "04" "Full Workflow" "layer04_full_workflow" "true"
            ;;
    esac
else
    # Run based on mode

    # Layer 01: Infrastructure (always runs)
    run_layer "01" "Infrastructure" "layer01_infrastructure"

    # Layer 02: Internal (always runs)
    run_layer "02" "Internal" "layer02_internal"

    # Layer 03: External Basic (standard and full modes)
    if [[ "$RUN_MODE" == "standard" || "$RUN_MODE" == "full" ]]; then
        run_layer "03" "External Basic" "layer03_external_basic"
    else
        print_warning "Layer 03: External Basic - SKIPPED (quick mode)"
        ((TESTS_SKIPPED++))
    fi

    # Layer 04: Full Workflow (full mode only)
    if [[ "$RUN_MODE" == "full" ]]; then
        print_warning "Layer 04 tests take 5-10 minutes to complete..."
        run_layer "04" "Full Workflow" "layer04_full_workflow" "true"
    else
        print_warning "Layer 04: Full Workflow - SKIPPED (use --full)"
        ((TESTS_SKIPPED++))
    fi
fi

##############################################################################
# Summary
##############################################################################

print_header "Test Pipeline Summary"

echo "Results:"
echo "  ✓ Passed:  $TESTS_PASSED"
echo "  ✗ Failed:  $TESTS_FAILED"
echo "  ⚠ Skipped: $TESTS_SKIPPED"
echo

if [[ $TESTS_FAILED -eq 0 ]]; then
    print_success "ALL TESTS PASSED!"
    echo
    echo "Layer Status:"
    echo "  Layer 01: Infrastructure     ✓"
    echo "  Layer 02: Internal           ✓"
    if [[ "$RUN_MODE" != "quick" ]]; then
        echo "  Layer 03: External Basic     ✓"
    else
        echo "  Layer 03: External Basic     ⊘ (quick mode)"
    fi
    if [[ "$RUN_MODE" == "full" ]]; then
        echo "  Layer 04: Full Workflow      ✓"
    else
        echo "  Layer 04: Full Workflow      ⊘ (use --full)"
    fi
    echo
    echo "Next steps:"
    if [[ "$RUN_MODE" == "quick" ]]; then
        echo "  - Run with --standard to include external tests"
    elif [[ "$RUN_MODE" == "standard" ]]; then
        echo "  - Run with --full to include E2E scan workflows"
    fi
    echo
    exit 0
else
    print_error "SOME TESTS FAILED"
    echo
    echo "Troubleshooting:"
    echo "  - Layer 01 failures: Check Docker containers (Nessus, Redis)"
    echo "  - Layer 02 failures: Check for code/import issues"
    echo "  - Layer 03 failures: Check MCP server and worker status"
    echo "  - Layer 04 failures: Check scanner connectivity and timeouts"
    echo
    exit 1
fi
