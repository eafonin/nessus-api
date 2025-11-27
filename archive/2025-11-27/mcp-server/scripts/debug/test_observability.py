#!/usr/bin/env python3
"""Test script for Phase 3 observability features."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("PHASE 3 OBSERVABILITY TESTING")
print("=" * 70)

# Test 1: Import health check module
print("\n[TEST 1] Testing health check module...")
try:
    from core.health import check_redis, check_filesystem, check_all_dependencies
    print("✅ Health check module imported successfully")

    # Test Redis connectivity
    redis_result = check_redis("redis://localhost:6379", timeout=2)
    print(f"\nRedis health check:")
    print(f"  Status: {'✅ HEALTHY' if redis_result['healthy'] else '❌ UNHEALTHY'}")
    if not redis_result['healthy']:
        print(f"  Error: {redis_result.get('error', 'Unknown')}")

    # Test filesystem writability
    test_dir = "/tmp/nessus-test"
    os.makedirs(test_dir, exist_ok=True)
    fs_result = check_filesystem(test_dir)
    print(f"\nFilesystem health check:")
    print(f"  Path: {test_dir}")
    print(f"  Status: {'✅ HEALTHY' if fs_result['healthy'] else '❌ UNHEALTHY'}")
    if not fs_result['healthy']:
        print(f"  Error: {fs_result.get('error', 'Unknown')}")

    # Test combined check
    all_deps = check_all_dependencies("redis://localhost:6379", test_dir)
    print(f"\nCombined health check:")
    print(f"  Overall Status: {'✅ HEALTHY' if all_deps['status'] == 'healthy' else '❌ UNHEALTHY'}")

except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Import metrics module
print("\n[TEST 2] Testing metrics module...")
try:
    from core.metrics import (
        scans_total, api_requests_total, active_scans,
        record_tool_call, record_scan_submission, metrics_response
    )
    print("✅ Metrics module imported successfully")

    # Test recording metrics
    print("\nRecording test metrics...")
    record_tool_call("test_tool", "success")
    record_scan_submission("untrusted", "queued")
    print("✅ Metrics recorded successfully")

    # Test metrics output
    print("\nGenerating Prometheus metrics output...")
    metrics_output = metrics_response()
    print(f"✅ Generated {len(metrics_output)} bytes of metrics")

    # Display sample metrics
    print("\nSample metrics (first 500 chars):")
    print("-" * 50)
    print(metrics_output[:500].decode('utf-8'))
    print("...")

except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Import and test structured logging
print("\n[TEST 3] Testing structured logging...")
try:
    from core.logging_config import configure_logging, get_logger
    print("✅ Logging module imported successfully")

    # Configure logging
    configure_logging(log_level="INFO")
    print("✅ Logging configured successfully")

    # Get logger and test output
    logger = get_logger("test_module")
    print("\nTesting structured log output:")
    print("-" * 50)
    logger.info("test_event", trace_id="test-123", action="testing", status="success")
    logger.warning("test_warning", message="This is a test warning")
    logger.error("test_error", error_code=500, details="Test error details")
    print("-" * 50)
    print("✅ Structured logging works! (Check JSON format above)")

except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Import main server to check for errors
print("\n[TEST 4] Testing main server import...")
try:
    # This will test if the server initializes without errors
    import tools.mcp_server as mcp_server
    print("✅ MCP server imported successfully")
    print(f"  Logger: {mcp_server.logger}")
    print(f"  Redis URL: {mcp_server.REDIS_URL}")
    print(f"  Data dir: {mcp_server.DATA_DIR}")

except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("OBSERVABILITY TESTING COMPLETE")
print("=" * 70)
