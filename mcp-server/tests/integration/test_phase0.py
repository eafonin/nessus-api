"""
Phase 0 Tests: Task Management and Queue Infrastructure

Run with: pytest tests/integration/test_phase0.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import existing Phase 0 tests
from tests.integration.test_queue import *
from tests.integration.test_idempotency import *
from tests.integration.test_phase0_integration import *


@pytest.mark.phase0
class TestPhase0Suite:
    """Phase 0 test suite marker for easy execution."""
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "phase0"])
