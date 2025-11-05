"""Idempotency key management for preventing duplicate scans."""

import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime


class ConflictError(Exception):
    """Raised when idempotency key exists with different request parameters."""
    pass


def extract_idempotency_key(request_headers: Dict, tool_args: Dict) -> Optional[str]:
    """
    Extract and validate idempotency key from header or tool argument.

    Accepts key from either X-Idempotency-Key header OR idempotency_key argument.
    If both provided, validates they match.
    """
    header_key = request_headers.get("X-Idempotency-Key")
    arg_key = tool_args.get("idempotency_key")

    if header_key and arg_key:
        if header_key != arg_key:
            raise ValueError("Idempotency key mismatch between header and argument")
        return header_key

    return header_key or arg_key


class IdempotencyManager:
    """Manages idempotency keys in Redis with 48h TTL."""

    def __init__(self, redis_client):
        self.redis = redis_client

    def _hash_request(self, params: Dict[str, Any]) -> str:
        """Generate SHA256 hash of normalized request parameters."""
        # TODO: Implement request hashing
        # 1. Sort keys
        # 2. Normalize values (handle None, bool, numbers consistently)
        # 3. SHA256 hash
        pass

    async def check(self, idemp_key: str, request_params: Dict[str, Any]) -> Optional[str]:
        """
        Check if idempotency key exists.

        Returns existing task_id if found with matching hash.
        Raises ConflictError (409) if hash differs.
        Returns None if key not found.
        """
        # TODO: Implement idempotency check
        # key = f"idemp:{idemp_key}"
        # stored_data = self.redis.get(key)
        # if stored_data:
        #     stored = json.loads(stored_data)
        #     current_hash = self._hash_request(request_params)
        #     if stored["request_hash"] != current_hash:
        #         raise ConflictError("Idempotency key exists with different parameters")
        #     return stored["task_id"]
        # return None
        pass

    async def store(self, idemp_key: str, task_id: str, request_params: Dict) -> bool:
        """
        Store idempotency key using SETNX (atomic).

        Returns True if newly stored, False if already existed.
        TTL: 48 hours.
        """
        # TODO: Implement idempotency storage
        # key = f"idemp:{idemp_key}"
        # data = json.dumps({
        #     "task_id": task_id,
        #     "request_hash": self._hash_request(request_params),
        #     "created_at": datetime.utcnow().isoformat()
        # })
        # return bool(self.redis.set(key, data, nx=True, ex=48*3600))
        pass
