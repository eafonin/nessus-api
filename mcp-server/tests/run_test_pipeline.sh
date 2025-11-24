#!/bin/bash
##############################################################################
# Nessus MCP Server - Integrated Test Pipeline
##############################################################################
#
# This script runs the complete test pipeline in the recommended order:
#   1. Basic unit tests (quick validation)
#   2. Integration tests using direct Python API (no FastMCP)
#   3. FastMCP client smoke test (quick connectivity check)
#   4. Optional: Full E2E test with FastMCP client (5-10 min scan)
#
# Usage:
#   ./run_test_pipeline.sh [--full]
#
# Options:
#   --full    Include full E2E test with scan completion (takes 5-10 minutes)
#
# Run from host:
#   docker compose -f dev1/docker-compose.yml exec mcp-api tests/run_test_pipeline.sh
#
##############################################################################

set -e  # Exit on error

# Parse arguments
FULL_TEST=false
if [[ "$1" == "--full" ]]; then
    FULL_TEST=true
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo
    echo "=============================================================================="
    echo -e "${BLUE}$1${NC}"
    echo "=============================================================================="
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

run_test() {
    local name="$1"
    local command="$2"
    local optional="${3:-false}"

    echo
    echo "Running: $name"
    echo "Command: $command"
    echo

    if eval "$command"; then
        print_success "$name PASSED"
        ((TESTS_PASSED++))
        return 0
    else
        if [[ "$optional" == "true" ]]; then
            print_warning "$name SKIPPED (optional test failed)"
            ((TESTS_SKIPPED++))
            return 0
        else
            print_error "$name FAILED"
            ((TESTS_FAILED++))
            return 1
        fi
    fi
}

##############################################################################
# Start Test Pipeline
##############################################################################

print_header "Nessus MCP Server - Test Pipeline"

echo "Configuration:"
echo "  Full E2E Test: $FULL_TEST"
echo "  Date: $(date)"
echo "  Working Dir: $(pwd)"
echo

##############################################################################
# Phase 1: Unit Tests (Quick)
##############################################################################

print_header "Phase 1: Unit Tests"

run_test \
    "Logging Configuration Tests" \
    "pytest tests/unit/test_logging_config.py -v --tb=short"

run_test \
    "Prometheus Metrics Tests" \
    "pytest tests/unit/test_metrics.py -v --tb=short"

run_test \
    "Health Check Tests" \
    "pytest tests/unit/test_health.py -v --tb=short"

##############################################################################
# Phase 2: Integration Tests (Python API)
##############################################################################

print_header "Phase 2: Integration Tests (Direct Python API)"

run_test \
    "Phase 0: Queue and Task Management" \
    "pytest tests/integration/test_phase0.py -v --tb=short"

run_test \
    "Phase 1: Scanner Integration" \
    "pytest tests/integration/test_phase1.py -v --tb=short"

run_test \
    "Phase 2: Schema and Results" \
    "pytest tests/integration/test_phase2.py -v --tb=short"

run_test \
    "Idempotency Tests" \
    "pytest tests/integration/test_idempotency.py -v --tb=short"

##############################################################################
# Phase 3: FastMCP Client Tests
##############################################################################

print_header "Phase 3: FastMCP Client Tests"

run_test \
    "FastMCP Client Smoke Test" \
    "pytest tests/integration/test_fastmcp_client_smoke.py -v -s --tb=short"

run_test \
    "FastMCP Client Connection Tests" \
    "pytest tests/integration/test_fastmcp_client.py::TestClientConnection -v --tb=short"

run_test \
    "FastMCP Client Scan Submission Tests" \
    "pytest tests/integration/test_fastmcp_client.py::TestScanSubmission -v --tb=short"

run_test \
    "FastMCP Client Queue Operations" \
    "pytest tests/integration/test_fastmcp_client.py::TestQueueOperations -v --tb=short"

##############################################################################
# Phase 4: Full E2E Test (Optional, Long-Running)
##############################################################################

if [[ "$FULL_TEST" == "true" ]]; then
    print_header "Phase 4: Full E2E Test (5-10 minutes)"

    print_warning "This test will:"
    print_warning "  - Submit a complete vulnerability scan"
    print_warning "  - Wait for scan completion (5-10 minutes)"
    print_warning "  - Validate results and filtering"
    print_warning "  - Test all MCP client operations end-to-end"
    echo

    run_test \
        "Full E2E Workflow Test" \
        "pytest tests/integration/test_fastmcp_client_e2e.py::test_complete_e2e_workflow_untrusted_scan -v -s --tb=short" \
        "true"

    run_test \
        "E2E Result Filtering Test" \
        "pytest tests/integration/test_fastmcp_client_e2e.py::test_e2e_with_result_filtering -v -s --tb=short" \
        "true"
else
    print_header "Phase 4: Full E2E Test (SKIPPED)"
    echo "Run with --full flag to include long-running E2E tests"
    echo "Example: ./run_test_pipeline.sh --full"
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
    echo "Testing Pipeline Complete:"
    echo "  1. ✓ Unit tests validated"
    echo "  2. ✓ Integration tests validated"
    echo "  3. ✓ FastMCP client validated"
    if [[ "$FULL_TEST" == "true" ]]; then
        echo "  4. ✓ Full E2E workflow validated"
    else
        echo "  4. ⊘ Full E2E test skipped (use --full)"
    fi
    echo
    exit 0
else
    print_error "SOME TESTS FAILED"
    echo
    echo "Failed tests: $TESTS_FAILED"
    echo "Please review the output above for details."
    echo
    exit 1
fi
