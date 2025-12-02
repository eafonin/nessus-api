"""Integration tests for idempotency system."""

import pytest
import redis
from core.idempotency import IdempotencyManager, ConflictError


@pytest.fixture
def redis_client():
    """Redis client for testing."""
    client = redis.from_url("redis://redis:6379", decode_responses=True)
    yield client
    # Cleanup test keys
    for key in client.scan_iter("idemp:test-*"):
        client.delete(key)
    client.close()


@pytest.fixture
def idempotency_manager(redis_client):
    """IdempotencyManager instance for testing."""
    return IdempotencyManager(redis_client)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hash_request_consistent(idempotency_manager):
    """Test that same parameters produce same hash."""
    params1 = {
        "targets": "192.168.1.100",
        "name": "Test Scan",
        "description": "Test",
    }

    params2 = {
        "targets": "192.168.1.100",
        "name": "Test Scan",
        "description": "Test",
    }

    hash1 = idempotency_manager._hash_request(params1)
    hash2 = idempotency_manager._hash_request(params2)

    assert hash1 == hash2, "Identical parameters should produce same hash"
    assert len(hash1) == 64, "SHA256 hash should be 64 characters"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hash_request_key_order_independent(idempotency_manager):
    """Test that key order doesn't affect hash."""
    params1 = {
        "targets": "192.168.1.100",
        "name": "Test Scan",
        "description": "Test",
    }

    params2 = {
        "description": "Test",
        "targets": "192.168.1.100",
        "name": "Test Scan",
    }

    hash1 = idempotency_manager._hash_request(params1)
    hash2 = idempotency_manager._hash_request(params2)

    assert hash1 == hash2, "Key order should not affect hash"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hash_request_different_params(idempotency_manager):
    """Test that different parameters produce different hashes."""
    params1 = {
        "targets": "192.168.1.100",
        "name": "Test Scan 1",
    }

    params2 = {
        "targets": "192.168.1.100",
        "name": "Test Scan 2",
    }

    hash1 = idempotency_manager._hash_request(params1)
    hash2 = idempotency_manager._hash_request(params2)

    assert hash1 != hash2, "Different parameters should produce different hashes"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hash_request_none_normalization(idempotency_manager):
    """Test that None values are normalized consistently."""
    params1 = {"targets": "192.168.1.100", "description": None}
    params2 = {"targets": "192.168.1.100", "description": None}

    hash1 = idempotency_manager._hash_request(params1)
    hash2 = idempotency_manager._hash_request(params2)

    assert hash1 == hash2, "None values should be normalized consistently"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hash_request_bool_normalization(idempotency_manager):
    """Test that boolean values are normalized consistently."""
    params1 = {"targets": "192.168.1.100", "enabled": True}
    params2 = {"targets": "192.168.1.100", "enabled": True}

    hash1 = idempotency_manager._hash_request(params1)
    hash2 = idempotency_manager._hash_request(params2)

    assert hash1 == hash2, "Boolean values should be normalized consistently"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_store_new_key(idempotency_manager):
    """Test storing a new idempotency key."""
    idemp_key = "test-idemp-001"
    task_id = "task-001"
    params = {"targets": "192.168.1.100", "name": "Test"}

    result = await idempotency_manager.store(idemp_key, task_id, params)

    assert result is True, "Should return True for new key"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_store_existing_key(idempotency_manager):
    """Test storing an already existing key returns False."""
    idemp_key = "test-idemp-002"
    task_id = "task-002"
    params = {"targets": "192.168.1.100", "name": "Test"}

    # Store first time
    result1 = await idempotency_manager.store(idemp_key, task_id, params)
    assert result1 is True

    # Store second time (should fail)
    result2 = await idempotency_manager.store(idemp_key, task_id, params)
    assert result2 is False, "Should return False for existing key"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_check_nonexistent_key(idempotency_manager):
    """Test checking a key that doesn't exist."""
    idemp_key = "test-idemp-nonexistent"
    params = {"targets": "192.168.1.100"}

    result = await idempotency_manager.check(idemp_key, params)

    assert result is None, "Should return None for nonexistent key"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_check_matching_key(idempotency_manager):
    """Test checking a key with matching parameters."""
    idemp_key = "test-idemp-003"
    task_id = "task-003"
    params = {"targets": "192.168.1.100", "name": "Test Scan"}

    # Store key
    await idempotency_manager.store(idemp_key, task_id, params)

    # Check with same params
    result = await idempotency_manager.check(idemp_key, params)

    assert result == task_id, "Should return task_id for matching key"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_check_conflicting_params(idempotency_manager):
    """Test checking a key with different parameters raises ConflictError."""
    idemp_key = "test-idemp-004"
    task_id = "task-004"
    params1 = {"targets": "192.168.1.100", "name": "Test Scan 1"}
    params2 = {"targets": "192.168.1.100", "name": "Test Scan 2"}

    # Store with first params
    await idempotency_manager.store(idemp_key, task_id, params1)

    # Check with different params should raise ConflictError
    with pytest.raises(ConflictError) as exc_info:
        await idempotency_manager.check(idemp_key, params2)

    assert "different request parameters" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_store_ttl_set(idempotency_manager, redis_client):
    """Test that stored keys have 48h TTL."""
    idemp_key = "test-idemp-005"
    task_id = "task-005"
    params = {"targets": "192.168.1.100"}

    await idempotency_manager.store(idemp_key, task_id, params)

    # Check TTL
    key = f"idemp:{idemp_key}"
    ttl = redis_client.ttl(key)

    # TTL should be close to 48 hours (172800 seconds)
    assert ttl > 172700, "TTL should be approximately 48 hours"
    assert ttl <= 172800, "TTL should not exceed 48 hours"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_workflow_with_retry(idempotency_manager):
    """Test full idempotency workflow with retry."""
    idemp_key = "test-idemp-006"
    task_id = "task-006"
    params = {
        "targets": "192.168.1.100",
        "name": "Full Workflow Test",
        "description": "Testing idempotency",
    }

    # Step 1: Check key (should not exist)
    result = await idempotency_manager.check(idemp_key, params)
    assert result is None

    # Step 2: Store key
    stored = await idempotency_manager.store(idemp_key, task_id, params)
    assert stored is True

    # Step 3: Retry with same params (should return existing task_id)
    result = await idempotency_manager.check(idemp_key, params)
    assert result == task_id

    # Step 4: Retry with different params (should raise ConflictError)
    params_changed = params.copy()
    params_changed["name"] = "Different Name"

    with pytest.raises(ConflictError):
        await idempotency_manager.check(idemp_key, params_changed)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_store_operations(idempotency_manager):
    """Test that concurrent store operations are atomic (SETNX behavior)."""
    import asyncio

    idemp_key = "test-idemp-007"
    params = {"targets": "192.168.1.100"}

    async def try_store(task_num):
        task_id = f"task-{task_num:03d}"
        return await idempotency_manager.store(idemp_key, task_id, params)

    # Try to store same key concurrently
    results = await asyncio.gather(*[try_store(i) for i in range(10)])

    # Only one should succeed
    successful = sum(1 for r in results if r)
    assert successful == 1, "Only one concurrent store should succeed"


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_idempotency.py -v
    pytest.main([__file__, "-v", "-s"])
