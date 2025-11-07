"""Redis-based task queue for Nessus scan job management."""

import json
import redis
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TaskQueue:
    """
    Simple FIFO queue using Redis.

    Queue Architecture:
    - nessus:queue       - Main FIFO task queue (LPUSH/BRPOP)
    - nessus:queue:dead  - Dead Letter Queue for failed tasks (sorted set by timestamp)

    Features:
    - Blocking dequeue with timeout (prevents busy waiting)
    - Dead Letter Queue for error tracking
    - Queue depth metrics
    - JSON serialization for complex task objects
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        queue_key: str = "nessus:queue",
        dlq_key: str = "nessus:queue:dead"
    ):
        """
        Initialize TaskQueue with Redis connection.

        Args:
            redis_url: Redis connection URL (redis://host:port/db)
            queue_key: Redis key for main queue
            dlq_key: Redis key for dead letter queue
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.queue_key = queue_key
        self.dlq_key = dlq_key

        # Verify connection
        try:
            self.redis_client.ping()
            logger.info(f"TaskQueue connected to Redis at {redis_url}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def enqueue(self, task: Dict[str, Any]) -> int:
        """
        Enqueue task for processing.

        Uses LPUSH to add to the left (head) of the list.
        Worker uses BRPOP to pop from the right (tail) - FIFO behavior.

        Args:
            task: Task dictionary (must be JSON-serializable)
                  Expected keys: task_id, trace_id, payload, scanner_type, etc.

        Returns:
            New queue depth after enqueue

        Raises:
            TypeError: If task is not JSON-serializable
            redis.RedisError: If Redis operation fails
        """
        try:
            task_json = json.dumps(task)
            queue_depth = self.redis_client.lpush(self.queue_key, task_json)
            logger.info(
                f"Enqueued task: {task.get('task_id', 'unknown')}, "
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

    def dequeue(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Dequeue task (blocking with timeout).

        Uses BRPOP to block until task available or timeout.
        This prevents busy-waiting and reduces CPU usage.

        Args:
            timeout: Block timeout in seconds (0 = block forever)

        Returns:
            Task dictionary if available, None if timeout

        Raises:
            json.JSONDecodeError: If stored task is not valid JSON
            redis.RedisError: If Redis operation fails
        """
        try:
            result = self.redis_client.brpop(self.queue_key, timeout=timeout)

            if not result:
                # Timeout - no tasks available
                return None

            # BRPOP returns tuple: (key, value)
            _, task_json = result
            task = json.loads(task_json)

            logger.info(
                f"Dequeued task: {task.get('task_id', 'unknown')}, "
                f"trace_id: {task.get('trace_id', 'unknown')}"
            )
            return task

        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize task from queue: {e}")
            # Move corrupted task to DLQ
            self.move_to_dlq(
                {"error": "corrupted_json", "raw_data": task_json},
                f"JSON decode error: {e}"
            )
            return None
        except redis.RedisError as e:
            logger.error(f"Redis error during dequeue: {e}")
            raise

    def move_to_dlq(self, task: Dict[str, Any], error: str) -> None:
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
        """
        try:
            # Enrich task with failure metadata
            task["error"] = error
            task["failed_at"] = datetime.utcnow().isoformat()

            # Use timestamp as score for chronological ordering
            score = datetime.utcnow().timestamp()
            task_json = json.dumps(task)

            self.redis_client.zadd(self.dlq_key, {task_json: score})

            logger.warning(
                f"Moved task to DLQ: {task.get('task_id', 'unknown')}, "
                f"error: {error}"
            )
        except Exception as e:
            # Last resort: log error but don't fail
            logger.error(f"Failed to move task to DLQ: {e}", exc_info=True)

    def get_queue_depth(self) -> int:
        """
        Get number of tasks waiting in queue.

        Returns:
            Queue depth (number of pending tasks)
        """
        try:
            depth = self.redis_client.llen(self.queue_key)
            return depth
        except redis.RedisError as e:
            logger.error(f"Failed to get queue depth: {e}")
            return -1

    def get_dlq_size(self) -> int:
        """
        Get number of tasks in Dead Letter Queue.

        Returns:
            DLQ size (number of failed tasks)
        """
        try:
            size = self.redis_client.zcard(self.dlq_key)
            return size
        except redis.RedisError as e:
            logger.error(f"Failed to get DLQ size: {e}")
            return -1

    def peek(self, count: int = 1) -> list[Dict[str, Any]]:
        """
        Peek at next tasks in queue without removing them.

        Useful for monitoring and debugging.

        Args:
            count: Number of tasks to peek at (default: 1)

        Returns:
            List of task dictionaries in FIFO order (next to be dequeued first)
        """
        try:
            # LRANGE -count -1 gets last 'count' items (next to be dequeued)
            # Reverse to get FIFO order (BRPOP pops from right, so rightmost is next)
            task_jsons = self.redis_client.lrange(self.queue_key, -count, -1)
            tasks = [json.loads(tj) for tj in reversed(task_jsons)]
            return tasks
        except Exception as e:
            logger.error(f"Failed to peek queue: {e}")
            return []

    def get_dlq_tasks(
        self,
        start: int = 0,
        end: int = 9
    ) -> list[Dict[str, Any]]:
        """
        Get tasks from Dead Letter Queue (most recent first).

        Args:
            start: Start index (0-based)
            end: End index (inclusive)

        Returns:
            List of failed task dictionaries with error metadata
        """
        try:
            # ZREVRANGE returns newest (highest score) first
            task_jsons = self.redis_client.zrevrange(self.dlq_key, start, end)
            tasks = [json.loads(tj) for tj in task_jsons]
            return tasks
        except Exception as e:
            logger.error(f"Failed to get DLQ tasks: {e}")
            return []

    def clear_dlq(self, before_timestamp: Optional[float] = None) -> int:
        """
        Clear Dead Letter Queue entries.

        Args:
            before_timestamp: If provided, only clear entries before this timestamp
                            If None, clear all entries

        Returns:
            Number of entries removed
        """
        try:
            if before_timestamp:
                # Remove entries with score < before_timestamp
                removed = self.redis_client.zremrangebyscore(
                    self.dlq_key,
                    '-inf',
                    before_timestamp
                )
            else:
                # Remove all entries
                removed = self.redis_client.delete(self.dlq_key)

            logger.info(f"Cleared {removed} entries from DLQ")
            return removed
        except redis.RedisError as e:
            logger.error(f"Failed to clear DLQ: {e}")
            return 0

    def close(self) -> None:
        """Close Redis connection."""
        try:
            self.redis_client.close()
            logger.info("TaskQueue Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Queue statistics helper
def get_queue_stats(queue: TaskQueue) -> Dict[str, Any]:
    """
    Get comprehensive queue statistics.

    Args:
        queue: TaskQueue instance

    Returns:
        Dictionary with queue metrics
    """
    return {
        "queue_depth": queue.get_queue_depth(),
        "dlq_size": queue.get_dlq_size(),
        "next_tasks": queue.peek(count=3),
        "timestamp": datetime.utcnow().isoformat()
    }
