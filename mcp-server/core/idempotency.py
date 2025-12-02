"""Idempotency key management for preventing duplicate scans."""

import hashlib
import json
from datetime import datetime
from typing import Any


class ConflictError(Exception):
    """Raised when idempotency key exists with different request parameters."""

    pass


def extract_idempotency_key(request_headers: dict, tool_args: dict) -> str | None:
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

    def __init__(self, redis_client) -> None:
        self.redis = redis_client

    def _hash_request(self, params: dict[str, Any]) -> str:
        """
        Generate SHA256 hash of normalized request parameters.

        Normalization ensures consistent hashing:
        - Keys sorted alphabetically
        - None values handled explicitly
        - Booleans converted to lowercase strings
        - Numbers preserved as-is
        """
        # Sort keys for consistent ordering
        sorted_params = {}
        for key in sorted(params.keys()):
            value = params[key]

            # Normalize value for consistent hashing
            if value is None:
                sorted_params[key] = "null"
            elif isinstance(value, bool):
                sorted_params[key] = str(value).lower()
            else:
                sorted_params[key] = value

        # Create deterministic JSON string (sorted keys)
        normalized_json = json.dumps(
            sorted_params, sort_keys=True, separators=(",", ":")
        )

        # Generate SHA256 hash
        return hashlib.sha256(normalized_json.encode("utf-8")).hexdigest()

    async def check(
        self, idemp_key: str, request_params: dict[str, Any]
    ) -> str | None:
        """
        Check if idempotency key exists.

        Returns existing task_id if found with matching hash.
        Raises ConflictError (409) if hash differs.
        Returns None if key not found.
        """
        key = f"idemp:{idemp_key}"
        stored_data = self.redis.get(key)

        if not stored_data:
            return None

        # Parse stored data
        stored = json.loads(stored_data)
        stored_hash = stored.get("request_hash")
        stored_task_id = stored.get("task_id")

        # Compute hash of current request
        current_hash = self._hash_request(request_params)

        # Compare hashes
        if stored_hash != current_hash:
            raise ConflictError(
                f"Idempotency key '{idemp_key}' exists with different request parameters. "
                f"Use a different key or match the original request."
            )

        return stored_task_id

    async def store(self, idemp_key: str, task_id: str, request_params: dict) -> bool:
        """
        Store idempotency key using SETNX (atomic).

        Returns True if newly stored, False if already existed.
        TTL: 48 hours.
        """
        key = f"idemp:{idemp_key}"

        # Compute request hash
        request_hash = self._hash_request(request_params)

        # Prepare data to store
        data = json.dumps(
            {
                "task_id": task_id,
                "request_hash": request_hash,
                "created_at": datetime.utcnow().isoformat(),
            }
        )

        # SETNX with TTL (atomic operation)
        # Returns True if key was set, False if already existed
        result = self.redis.set(key, data, nx=True, ex=48 * 3600)
        return bool(result)
