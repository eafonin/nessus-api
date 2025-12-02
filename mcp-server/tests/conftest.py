"""
Root pytest configuration for the Nessus MCP Server test suite.

This conftest.py provides:
- Layer-based marker registration (layer01, layer02, layer03, layer04)
- Dependency markers (requires_nessus, requires_redis, requires_mcp)
- Legacy phase markers (deprecated, kept for backwards compatibility)

Test Layer Architecture:
    layer01: Infrastructure     [<1s]    Connectivity, access checks
    layer02: Internal           [~30s]   Core modules (mocked deps)
    layer03: External Basic     [~1min]  Single tool calls with real services
    layer04: Full Workflow      [5-10m]  Complete E2E workflows
"""

import pytest


def pytest_configure(config):
    """Register all custom markers."""

    # ==========================================================================
    # Layer Markers (Primary)
    # ==========================================================================
    config.addinivalue_line(
        "markers",
        "layer01: Layer 01 tests - Infrastructure checks (connectivity, access)",
    )
    config.addinivalue_line(
        "markers", "layer02: Layer 02 tests - Internal modules (mocked dependencies)"
    )
    config.addinivalue_line(
        "markers", "layer03: Layer 03 tests - External basic (single tool calls)"
    )
    config.addinivalue_line(
        "markers", "layer04: Layer 04 tests - Full workflow E2E (complete scans)"
    )

    # ==========================================================================
    # Dependency Markers
    # ==========================================================================
    config.addinivalue_line(
        "markers", "requires_nessus: Test requires Nessus scanner access"
    )
    config.addinivalue_line("markers", "requires_redis: Test requires Redis connection")
    config.addinivalue_line("markers", "requires_mcp: Test requires MCP server running")
    config.addinivalue_line(
        "markers", "requires_docker_network: Test must run inside Docker network"
    )

    # ==========================================================================
    # Behavior Markers
    # ==========================================================================
    config.addinivalue_line("markers", "slow: Test takes > 1 minute to complete")
    config.addinivalue_line("markers", "e2e: End-to-end test covering full workflow")
    config.addinivalue_line("markers", "authenticated: Test uses SSH credentials")
    config.addinivalue_line(
        "markers", "real_nessus: Test uses real Nessus scanner (NOT mocks)"
    )
    config.addinivalue_line("markers", "mcp: Test exercises MCP protocol layer")
    config.addinivalue_line(
        "markers", "timeout: Test timeout in seconds (requires pytest-timeout plugin)"
    )

    # ==========================================================================
    # Legacy Phase Markers (Deprecated - kept for backwards compatibility)
    # ==========================================================================
    config.addinivalue_line(
        "markers", "phase0: [DEPRECATED] Use layer01/layer02 instead"
    )
    config.addinivalue_line("markers", "phase1: [DEPRECATED] Use layer03 instead")
    config.addinivalue_line("markers", "phase2: [DEPRECATED] Use layer03 instead")
    config.addinivalue_line("markers", "phase3: [DEPRECATED] Use layer02 instead")
    config.addinivalue_line("markers", "phase4: [DEPRECATED] Use layer04 instead")
    config.addinivalue_line(
        "markers", "integration: Integration tests (use layer03 or layer04 instead)"
    )


def pytest_collection_modifyitems(config, items):
    """
    Auto-apply markers based on test location.

    Tests in layer directories automatically get the corresponding marker.
    """
    for item in items:
        # Get the test file path
        test_path = str(item.fspath)

        # Auto-apply layer markers based on directory
        if "layer01_infrastructure" in test_path:
            item.add_marker(pytest.mark.layer01)
        elif "layer02_internal" in test_path:
            item.add_marker(pytest.mark.layer02)
        elif "layer03_external_basic" in test_path:
            item.add_marker(pytest.mark.layer03)
        elif "layer04_full_workflow" in test_path:
            item.add_marker(pytest.mark.layer04)
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.e2e)
