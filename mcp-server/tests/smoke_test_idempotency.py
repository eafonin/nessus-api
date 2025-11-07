#!/usr/bin/env python3
"""Idempotency system smoke test - Quick verification without pytest."""

import sys
import asyncio
sys.path.insert(0, '/app')

import redis
from core.idempotency import IdempotencyManager, ConflictError


async def main():
    print("=" * 70)
    print("Idempotency System Smoke Test")
    print("=" * 70)

    # Initialize Redis client
    print("\n1. Initializing Redis client...")
    try:
        redis_client = redis.from_url("redis://redis:6379", decode_responses=True)
        redis_client.ping()
        print("   ✅ Redis connection successful")
    except Exception as e:
        print(f"   ❌ Redis connection failed: {e}")
        return 1

    # Initialize IdempotencyManager
    print("\n2. Initializing IdempotencyManager...")
    try:
        idempotency_manager = IdempotencyManager(redis_client)
        print("   ✅ IdempotencyManager initialized")
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return 1

    # Cleanup test keys
    for key in redis_client.scan_iter("idemp:smoke-*"):
        redis_client.delete(key)

    try:
        # Test 1: Hash consistency
        print("\n3. Testing request hashing...")
        params1 = {"targets": "192.168.1.100", "name": "Test Scan", "description": "Test"}
        params2 = {"targets": "192.168.1.100", "name": "Test Scan", "description": "Test"}

        hash1 = idempotency_manager._hash_request(params1)
        hash2 = idempotency_manager._hash_request(params2)

        if hash1 == hash2 and len(hash1) == 64:
            print(f"   ✅ Consistent hash: {hash1[:16]}...")
        else:
            print(f"   ❌ Hash mismatch or invalid length")
            return 1

        # Test 2: Key order independence
        print("\n4. Testing key order independence...")
        params_ordered = {"a": "1", "b": "2", "c": "3"}
        params_reversed = {"c": "3", "b": "2", "a": "1"}

        hash_ordered = idempotency_manager._hash_request(params_ordered)
        hash_reversed = idempotency_manager._hash_request(params_reversed)

        if hash_ordered == hash_reversed:
            print("   ✅ Key order doesn't affect hash")
        else:
            print("   ❌ Key order affects hash (should be independent)")
            return 1

        # Test 3: Store new key
        print("\n5. Testing store new idempotency key...")
        idemp_key = "smoke-test-001"
        task_id = "task-smoke-001"
        params = {"targets": "192.168.1.100", "name": "Smoke Test"}

        result = await idempotency_manager.store(idemp_key, task_id, params)
        if result:
            print(f"   ✅ Stored key: {idemp_key} → {task_id}")
        else:
            print("   ❌ Failed to store new key")
            return 1

        # Test 4: Store duplicate key (should fail)
        print("\n6. Testing duplicate key storage...")
        result = await idempotency_manager.store(idemp_key, "task-duplicate", params)
        if not result:
            print("   ✅ Duplicate key rejected (SETNX behavior)")
        else:
            print("   ❌ Duplicate key accepted (should be rejected)")
            return 1

        # Test 5: Check existing key with matching params
        print("\n7. Testing check with matching params...")
        retrieved_task_id = await idempotency_manager.check(idemp_key, params)
        if retrieved_task_id == task_id:
            print(f"   ✅ Retrieved task_id: {retrieved_task_id}")
        else:
            print(f"   ❌ Task ID mismatch: expected {task_id}, got {retrieved_task_id}")
            return 1

        # Test 6: Check nonexistent key
        print("\n8. Testing check nonexistent key...")
        result = await idempotency_manager.check("smoke-nonexistent", params)
        if result is None:
            print("   ✅ Nonexistent key returns None")
        else:
            print(f"   ❌ Unexpected result: {result}")
            return 1

        # Test 7: Check with conflicting params (should raise error)
        print("\n9. Testing conflict detection...")
        conflicting_params = {"targets": "192.168.1.100", "name": "Different Name"}
        try:
            await idempotency_manager.check(idemp_key, conflicting_params)
            print("   ❌ ConflictError not raised")
            return 1
        except ConflictError as e:
            print(f"   ✅ ConflictError raised: {str(e)[:60]}...")

        # Test 8: Verify TTL
        print("\n10. Testing TTL (48 hours)...")
        key = f"idemp:{idemp_key}"
        ttl = redis_client.ttl(key)
        if 172700 < ttl <= 172800:
            print(f"   ✅ TTL set correctly: {ttl}s (~48 hours)")
        else:
            print(f"   ❌ TTL incorrect: {ttl}s (expected ~172800s)")
            return 1

        # Test 9: Full workflow
        print("\n11. Testing full idempotency workflow...")
        workflow_key = "smoke-workflow-001"
        workflow_task_id = "task-workflow-001"
        workflow_params = {
            "targets": "192.168.1.200",
            "name": "Workflow Test",
            "description": "Full idempotency test"
        }

        # Check (should not exist)
        result = await idempotency_manager.check(workflow_key, workflow_params)
        if result is not None:
            print(f"   ❌ Expected None, got {result}")
            return 1

        # Store
        stored = await idempotency_manager.store(workflow_key, workflow_task_id, workflow_params)
        if not stored:
            print("   ❌ Store failed")
            return 1

        # Retry (should return existing task_id)
        result = await idempotency_manager.check(workflow_key, workflow_params)
        if result == workflow_task_id:
            print(f"   ✅ Full workflow: check → store → retry successful")
        else:
            print(f"   ❌ Workflow failed: expected {workflow_task_id}, got {result}")
            return 1

        # Test 10: Concurrent operations
        print("\n12. Testing concurrent store operations...")
        concurrent_key = "smoke-concurrent-001"
        concurrent_params = {"targets": "192.168.1.250"}

        async def try_store(i):
            return await idempotency_manager.store(
                concurrent_key,
                f"task-concurrent-{i:03d}",
                concurrent_params
            )

        results = await asyncio.gather(*[try_store(i) for i in range(10)])
        successful = sum(1 for r in results if r)

        if successful == 1:
            print(f"   ✅ Only 1 of 10 concurrent stores succeeded (atomic)")
        else:
            print(f"   ❌ {successful} stores succeeded (expected 1)")
            return 1

        print("\n" + "=" * 70)
        print("✅ ALL IDEMPOTENCY SMOKE TESTS PASSED!")
        print("=" * 70)
        print("\nIdempotency System Components Verified:")
        print("  ✅ Request hashing (SHA256)")
        print("  ✅ Key order independence")
        print("  ✅ Store new key (SETNX)")
        print("  ✅ Duplicate key rejection")
        print("  ✅ Check with matching params")
        print("  ✅ Check nonexistent key")
        print("  ✅ Conflict detection")
        print("  ✅ 48-hour TTL")
        print("  ✅ Full workflow (check → store → retry)")
        print("  ✅ Concurrent operations (atomic)")
        print("\nIdempotency System: Ready for production")
        print("=" * 70)

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Cleanup
        for key in redis_client.scan_iter("idemp:smoke-*"):
            redis_client.delete(key)
        redis_client.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
