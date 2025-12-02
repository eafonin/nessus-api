"""Redis-based task queue for Nessus scan job management.

Phase 4: Supports per-pool queues for scanner pool isolation.
"""

import json
import logging
from datetime import datetime
from typing import Any

import redis

logger = logging.getLogger(__name__)

# Default pool for backward compatibility
DEFAULT_POOL = "nessus"


class TaskQueue:
    """
    Pool-aware FIFO queue using Redis.

    Queue Architecture (per pool):
    - {pool}:queue       - Main FIFO task queue (LPUSH/BRPOP)
    - {pool}:queue:dead  - Dead Letter Queue for failed tasks (sorted set by timestamp)

    Example pools:
    - nessus:queue, nessus:queue:dead
    - nessus_dmz:queue, nessus_dmz:queue:dead
    - nuclei:queue, nuclei:queue:dead

    Features:
    - Per-pool queue isolation
    - Blocking dequeue with timeout (prevents busy waiting)
    - Dead Letter Queue for error tracking
    - Queue depth metrics per pool
    - JSON serialization for complex task objects
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_pool: str = DEFAULT_POOL,
    ) -> None:
        """
        Initialize TaskQueue with Redis connection.

        Args:
            redis_url: Redis connection URL (redis://host:port/db)
            default_pool: Default pool name for backward compatibility
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.default_pool = default_pool

        # Verify connection
        try:
            self.redis_client.ping()
            logger.info(f"TaskQueue connected to Redis at {redis_url}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _queue_key(self, pool: str) -> str:
        """Get queue key for a pool."""
        return f"{pool}:queue"

    def _dlq_key(self, pool: str) -> str:
        """Get DLQ key for a pool."""
        return f"{pool}:queue:dead"

    # Backward compatibility properties
    @property
    def queue_key(self) -> str:
        """Default queue key (backward compatibility)."""
        return self._queue_key(self.default_pool)

    @property
    def dlq_key(self) -> str:
        """Default DLQ key (backward compatibility)."""
        return self._dlq_key(self.default_pool)

    def enqueue(self, task: dict[str, Any], pool: str | None = None) -> int:
        """
        Enqueue task for processing in specified pool.

        Uses LPUSH to add to the left (head) of the list.
        Worker uses BRPOP to pop from the right (tail) - FIFO behavior.

        Args:
            task: Task dictionary (must be JSON-serializable)
                  Expected keys: task_id, trace_id, payload, scanner_pool, etc.
            pool: Pool name (e.g., "nessus", "nessus_dmz").
                  If None, uses task's scanner_pool or default_pool.

        Returns:
            New queue depth after enqueue

        Raises:
            TypeError: If task is not JSON-serializable
            redis.RedisError: If Redis operation fails
        """
        # Determine pool from argument, task, or default
        target_pool = pool or task.get("scanner_pool") or self.default_pool
        queue_key = self._queue_key(target_pool)

        try:
            task_json = json.dumps(task)
            queue_depth = self.redis_client.lpush(queue_key, task_json)
            logger.info(
                f"Enqueued task: {task.get('task_id', 'unknown')}, "
                f"pool: {target_pool}, "
                f"trace_id: {task.get('trace_id', 'unknown')}, "
                f"queue_depth: {queue_depth}"
            )
            return queue_depth
        except (TypeError, json.JSONDecodeError) as e:
            logger.error(f"Failed to serialize task: {e}")
            raise TypeError(f"Task must be JSON-serializable: {e}")
        except redis.RedisError as e:
            logger.error(f"Redis error during enqueue: {e}")
            raise

    def dequeue(
        self, pool: str | None = None, timeout: int = 5
    ) -> dict[str, Any] | None:
        """
        Dequeue task from pool (blocking with timeout).

        Uses BRPOP to block until task available or timeout.
        This prevents busy-waiting and reduces CPU usage.

        Args:
            pool: Pool to dequeue from. If None, uses default_pool.
            timeout: Block timeout in seconds (0 = block forever)

        Returns:
            Task dictionary if available, None if timeout

        Raises:
            json.JSONDecodeError: If stored task is not valid JSON
            redis.RedisError: If Redis operation fails
        """
        target_pool = pool or self.default_pool
        queue_key = self._queue_key(target_pool)

        try:
            result = self.redis_client.brpop(queue_key, timeout=timeout)

            if not result:
                # Timeout - no tasks available
                return None

            # BRPOP returns tuple: (key, value)
            _, task_json = result
            task = json.loads(task_json)

            logger.info(
                f"Dequeued task: {task.get('task_id', 'unknown')}, "
                f"pool: {target_pool}, "
                f"trace_id: {task.get('trace_id', 'unknown')}"
            )
            return task

        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize task from queue: {e}")
            # Move corrupted task to DLQ
            self.move_to_dlq(
                {"error": "corrupted_json", "raw_data": task_json},
                f"JSON decode error: {e}",
                pool=target_pool,
            )
            return None
        except redis.RedisError as e:
            logger.error(f"Redis error during dequeue: {e}")
            raise

    def dequeue_any(
        self, pools: list[str], timeout: int = 5
    ) -> dict[str, Any] | None:
        """
        Dequeue task from any of the specified pools (blocking with timeout).

        Uses BRPOP with multiple keys to wait on any pool.

        Args:
            pools: List of pool names to dequeue from
            timeout: Block timeout in seconds (0 = block forever)

        Returns:
            Task dictionary if available, None if timeout
        """
        if not pools:
            pools = [self.default_pool]

        queue_keys = [self._queue_key(pool) for pool in pools]

        try:
            result = self.redis_client.brpop(queue_keys, timeout=timeout)

            if not result:
                return None

            # BRPOP returns tuple: (key, value)
            dequeued_key, task_json = result
            task = json.loads(task_json)

            # Extract pool from key (e.g., "nessus:queue" -> "nessus")
            dequeued_pool = dequeued_key.rsplit(":queue", 1)[0]

            logger.info(
                f"Dequeued task: {task.get('task_id', 'unknown')}, "
                f"pool: {dequeued_pool}, "
                f"trace_id: {task.get('trace_id', 'unknown')}"
            )
            return task

        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize task from queue: {e}")
            return None
        except redis.RedisError as e:
            logger.error(f"Redis error during dequeue: {e}")
            raise

    def move_to_dlq(
        self, task: dict[str, Any], error: str, pool: str | None = None
    ) -> None:
        """
        Move failed task to Dead Letter Queue.

        DLQ uses Redis sorted set (ZADD) with timestamp as score.
        This allows:
        - Chronological ordering of failures
        - Range queries by time
        - Easy cleanup of old entries

        Args:
            task: Failed task dictionary
            error: Error message describing failure
            pool: Pool name. If None, uses task's scanner_pool or default_pool.
        """
        target_pool = pool or task.get("scanner_pool") or self.default_pool
        dlq_key = self._dlq_key(target_pool)

        try:
            # Enrich task with failure metadata
            task["error"] = error
            task["failed_at"] = datetime.utcnow().isoformat()
            task["scanner_pool"] = target_pool

            # Use timestamp as score for chronological ordering
            score = datetime.utcnow().timestamp()
            task_json = json.dumps(task)

            self.redis_client.zadd(dlq_key, {task_json: score})

            logger.warning(
                f"Moved task to DLQ: {task.get('task_id', 'unknown')}, "
                f"pool: {target_pool}, "
                f"error: {error}"
            )
        except Exception as e:
            # Last resort: log error but don't fail
            logger.error(f"Failed to move task to DLQ: {e}", exc_info=True)

    def get_queue_depth(self, pool: str | None = None) -> int:
        """
        Get number of tasks waiting in queue.

        Args:
            pool: Pool name. If None, uses default_pool.

        Returns:
            Queue depth (number of pending tasks)
        """
        target_pool = pool or self.default_pool
        queue_key = self._queue_key(target_pool)

        try:
            depth = self.redis_client.llen(queue_key)
            return depth
        except redis.RedisError as e:
            logger.error(f"Failed to get queue depth for pool {target_pool}: {e}")
            return -1

    def get_dlq_size(self, pool: str | None = None) -> int:
        """
        Get number of tasks in Dead Letter Queue.

        Args:
            pool: Pool name. If None, uses default_pool.

        Returns:
            DLQ size (number of failed tasks)
        """
        target_pool = pool or self.default_pool
        dlq_key = self._dlq_key(target_pool)

        try:
            size = self.redis_client.zcard(dlq_key)
            return size
        except redis.RedisError as e:
            logger.error(f"Failed to get DLQ size for pool {target_pool}: {e}")
            return -1

    def peek(self, count: int = 1, pool: str | None = None) -> list[dict[str, Any]]:
        """
        Peek at next tasks in queue without removing them.

        Useful for monitoring and debugging.

        Args:
            count: Number of tasks to peek at (default: 1)
            pool: Pool name. If None, uses default_pool.

        Returns:
            List of task dictionaries in FIFO order (next to be dequeued first)
        """
        target_pool = pool or self.default_pool
        queue_key = self._queue_key(target_pool)

        try:
            # LRANGE -count -1 gets last 'count' items (next to be dequeued)
            # Reverse to get FIFO order (BRPOP pops from right, so rightmost is next)
            task_jsons = self.redis_client.lrange(queue_key, -count, -1)
            tasks = [json.loads(tj) for tj in reversed(task_jsons)]
            return tasks
        except Exception as e:
            logger.error(f"Failed to peek queue for pool {target_pool}: {e}")
            return []

    def get_dlq_tasks(
        self, start: int = 0, end: int = 9, pool: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get tasks from Dead Letter Queue (most recent first).

        Args:
            start: Start index (0-based)
            end: End index (inclusive)
            pool: Pool name. If None, uses default_pool.

        Returns:
            List of failed task dictionaries with error metadata
        """
        target_pool = pool or self.default_pool
        dlq_key = self._dlq_key(target_pool)

        try:
            # ZREVRANGE returns newest (highest score) first
            task_jsons = self.redis_client.zrevrange(dlq_key, start, end)
            tasks = [json.loads(tj) for tj in task_jsons]
            return tasks
        except Exception as e:
            logger.error(f"Failed to get DLQ tasks for pool {target_pool}: {e}")
            return []

    def get_dlq_task(
        self, task_id: str, pool: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get a specific task from DLQ by task_id.

        Args:
            task_id: Task ID to find
            pool: Pool name. If None, uses default_pool.

        Returns:
            Task dictionary if found, None otherwise
        """
        target_pool = pool or self.default_pool
        dlq_key = self._dlq_key(target_pool)

        try:
            # Scan all DLQ entries to find matching task_id
            task_jsons = self.redis_client.zrange(dlq_key, 0, -1)
            for tj in task_jsons:
                task = json.loads(tj)
                if task.get("task_id") == task_id:
                    return task
            return None
        except Exception as e:
            logger.error(
                f"Failed to get DLQ task {task_id} for pool {target_pool}: {e}"
            )
            return None

    def retry_dlq_task(self, task_id: str, pool: str | None = None) -> bool:
        """
        Move a task from DLQ back to main queue for retry.

        Args:
            task_id: Task ID to retry
            pool: Pool name. If None, uses default_pool.

        Returns:
            True if task was found and moved, False otherwise
        """
        target_pool = pool or self.default_pool
        dlq_key = self._dlq_key(target_pool)

        try:
            # Find the task in DLQ
            task_jsons = self.redis_client.zrange(dlq_key, 0, -1, withscores=True)
            for tj, _score in task_jsons:
                task = json.loads(tj)
                if task.get("task_id") == task_id:
                    # Remove from DLQ
                    self.redis_client.zrem(dlq_key, tj)

                    # Clear error metadata and re-queue
                    task.pop("error", None)
                    task.pop("failed_at", None)
                    self.enqueue(task, pool=target_pool)

                    logger.info(
                        f"Retried task {task_id} from DLQ for pool {target_pool}"
                    )
                    return True

            logger.warning(f"Task {task_id} not found in DLQ for pool {target_pool}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to retry DLQ task {task_id} for pool {target_pool}: {e}"
            )
            return False

    def clear_dlq(
        self, before_timestamp: float | None = None, pool: str | None = None
    ) -> int:
        """
        Clear Dead Letter Queue entries.

        Args:
            before_timestamp: If provided, only clear entries before this timestamp
                            If None, clear all entries
            pool: Pool name. If None, uses default_pool.

        Returns:
            Number of entries removed
        """
        target_pool = pool or self.default_pool
        dlq_key = self._dlq_key(target_pool)

        try:
            if before_timestamp:
                # Remove entries with score < before_timestamp
                removed = self.redis_client.zremrangebyscore(
                    dlq_key, "-inf", before_timestamp
                )
            else:
                # Remove all entries
                removed = self.redis_client.delete(dlq_key)

            logger.info(f"Cleared {removed} entries from DLQ for pool {target_pool}")
            return removed
        except redis.RedisError as e:
            logger.error(f"Failed to clear DLQ for pool {target_pool}: {e}")
            return 0

    def close(self) -> None:
        """Close Redis connection."""
        try:
            self.redis_client.close()
            logger.info("TaskQueue Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Queue statistics helper
def get_queue_stats(queue: TaskQueue, pool: str | None = None) -> dict[str, Any]:
    """
    Get comprehensive queue statistics for a pool.

    Args:
        queue: TaskQueue instance
        pool: Pool name. If None, uses default_pool.

    Returns:
        Dictionary with queue metrics
    """
    target_pool = pool or queue.default_pool
    return {
        "pool": target_pool,
        "queue_depth": queue.get_queue_depth(pool=target_pool),
        "dlq_size": queue.get_dlq_size(pool=target_pool),
        "next_tasks": queue.peek(count=3, pool=target_pool),
        "timestamp": datetime.utcnow().isoformat(),
    }


def get_all_pool_stats(queue: TaskQueue, pools: list[str]) -> dict[str, Any]:
    """
    Get queue statistics across all specified pools.

    Args:
        queue: TaskQueue instance
        pools: List of pool names

    Returns:
        Dictionary with aggregate and per-pool metrics
    """
    total_depth = 0
    total_dlq = 0
    pool_stats = []

    for pool in pools:
        depth = queue.get_queue_depth(pool=pool)
        dlq = queue.get_dlq_size(pool=pool)
        total_depth += depth
        total_dlq += dlq
        pool_stats.append(
            {
                "pool": pool,
                "queue_depth": depth,
                "dlq_size": dlq,
            }
        )

    return {
        "total_queue_depth": total_depth,
        "total_dlq_size": total_dlq,
        "pools": pool_stats,
        "timestamp": datetime.utcnow().isoformat(),
    }
