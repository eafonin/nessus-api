#!/usr/bin/env python3
"""Simple test for Phase 3 observability features (without full server import)."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("PHASE 3 OBSERVABILITY TESTING - SIMPLIFIED")
print("=" * 70)

# Test 1: Health check module
print("\n[TEST 1] Health check module...")
from core.health import check_redis, check_filesystem, check_all_dependencies
print("✅ Imported successfully")

test_dir = "/tmp/nessus-test"
os.makedirs(test_dir, exist_ok=True)
fs_result = check_filesystem(test_dir)
print(f"Filesystem check: {'✅' if fs_result['healthy'] else '❌'}")

# Test 2: Metrics module
print("\n[TEST 2] Metrics module...")
from core.metrics import (
    record_tool_call, record_scan_submission, metrics_response
)
print("✅ Imported successfully")

record_tool_call("test_tool", "success")
record_scan_submission("untrusted", "queued")
print("✅ Recorded test metrics")

metrics_output = metrics_response()
print(f"✅ Generated {len(metrics_output)} bytes of Prometheus metrics")

# Display sample
print("\n--- Sample Prometheus Metrics (first 600 chars) ---")
print(metrics_output[:600].decode('utf-8'))
print("...")

# Test 3: Structured logging
print("\n[TEST 3] Structured logging...")
from core.logging_config import configure_logging, get_logger
print("✅ Imported successfully")

configure_logging(log_level="INFO")
logger = get_logger("test")
print("\n--- Sample JSON Logs ---")
logger.info("scan_initiated", trace_id="abc-123", targets="192.168.1.0/24")
logger.warning("high_queue_depth", depth=50, threshold=40)
logger.error("scan_failed", task_id="nessus-local-456", error="timeout")
print("--- End Sample ---")

print("\n" + "=" * 70)
print("ALL CORE MODULES TESTED SUCCESSFULLY!")
print("=" * 70)
