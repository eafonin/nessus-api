"""
Phase 1 Tests: Nessus Scanner Integration (READ + WRITE operations)

Run with: pytest tests/integration/test_phase1.py -v

This consolidates all Phase 1 functionality tests:
- Dynamic X-API-Token fetching
- Authentication
- READ operations (list scans, get status, etc.)
- WRITE operations (create, launch, stop, delete)
- Complete scan workflow with vulnerability export
- Error handling
- Session management
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import all Phase 1 tests
from tests.integration.test_nessus_read_write_operations import (
    TestReadOperations,
    TestWriteOperations,
    TestErrorHandling,
    TestSessionManagement,
    test_complete_authenticated_scan_workflow
)

from tests.integration.test_complete_scan_with_results import (
    test_complete_scan_workflow_with_export
)


# Mark all tests as phase1
pytestmark = pytest.mark.phase1


@pytest.mark.phase1
class TestPhase1Suite:
    """
    Phase 1 complete test suite.

    Usage:
        # Run all Phase 1 tests
        pytest tests/integration/test_phase1.py -v

        # Run just READ operations
        pytest tests/integration/test_phase1.py::TestReadOperations -v

        # Run just WRITE operations
        pytest tests/integration/test_phase1.py::TestWriteOperations -v

        # Run complete scan workflow
        pytest tests/integration/test_phase1.py::test_complete_scan_workflow_with_export -v -s
    """
    pass


# Export all test classes for easy import
__all__ = [
    'TestReadOperations',
    'TestWriteOperations',
    'TestErrorHandling',
    'TestSessionManagement',
    'test_complete_authenticated_scan_workflow',
    'test_complete_scan_workflow_with_export',
]


if __name__ == "__main__":
    import sys

    print("\n" + "="*70)
    print("PHASE 1 TEST SUITE: Nessus Scanner Integration")
    print("="*70)
    print("\nTests included:")
    print("  1. Dynamic X-API-Token Fetching")
    print("  2. Authentication")
    print("  3. READ Operations (server status, list scans, scan details)")
    print("  4. WRITE Operations (create, launch, stop, delete)")
    print("  5. Complete Scan Workflow with Vulnerability Export")
    print("  6. Error Handling (401/403/404/409)")
    print("  7. Session Management")
    print("\n" + "="*70 + "\n")

    # Run all Phase 1 tests
    sys.exit(pytest.main([__file__, "-v", "-m", "phase1"]))
