"""TTL-based task cleanup for automatic disk management.

Phase 4.10: Automatic cleanup of old completed/failed tasks to prevent disk exhaustion.
"""

import json
import shutil
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from core.metrics import ttl_deletions_total

logger = logging.getLogger(__name__)


class Housekeeper:
    """
    Cleans up old task directories based on TTL.

    Default retention:
    - Completed tasks: 7 days
    - Failed/Timeout tasks: 30 days
    - Running tasks: Never (still in progress)

    Features:
    - Configurable retention periods
    - Safe deletion (only removes known status types)
    - Metrics tracking via ttl_deletions_total
    - Detailed logging of cleanup operations
    """

    def __init__(
        self,
        data_dir: str = "/app/data/tasks",
        completed_ttl_days: int = 7,
        failed_ttl_days: int = 30
    ):
        """
        Initialize Housekeeper.

        Args:
            data_dir: Directory containing task subdirectories
            completed_ttl_days: Days to retain completed tasks (default: 7)
            failed_ttl_days: Days to retain failed/timeout tasks (default: 30)
        """
        self.data_dir = Path(data_dir)
        self.completed_ttl = timedelta(days=completed_ttl_days)
        self.failed_ttl = timedelta(days=failed_ttl_days)

    def cleanup(self) -> dict:
        """
        Run cleanup cycle - delete expired task directories.

        Returns:
            Dict with:
                - deleted_count: Number of tasks deleted
                - freed_bytes: Total bytes freed
                - freed_mb: Total MB freed (rounded)
                - errors: List of error messages
                - skipped: Count of tasks skipped (still active)
        """
        now = datetime.utcnow()
        deleted = 0
        freed = 0
        errors = []
        skipped = 0

        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {self.data_dir}")
            return {
                "deleted_count": 0,
                "freed_bytes": 0,
                "freed_mb": 0,
                "errors": ["Data directory does not exist"],
                "skipped": 0
            }

        for task_dir in self.data_dir.iterdir():
            if not task_dir.is_dir():
                continue

            task_file = task_dir / "task.json"
            if not task_file.exists():
                # Skip directories without task.json (might be temp or incomplete)
                continue

            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(task_file.stat().st_mtime)
                age = now - mtime

                # Read task status
                with open(task_file) as f:
                    task = json.load(f)

                status = task.get("status", "unknown")
                task_id = task.get("task_id", task_dir.name)

                # Determine if should delete based on status and age
                should_delete = False
                if status == "completed" and age > self.completed_ttl:
                    should_delete = True
                    reason = f"completed task older than {self.completed_ttl.days} days"
                elif status in ("failed", "timeout") and age > self.failed_ttl:
                    should_delete = True
                    reason = f"{status} task older than {self.failed_ttl.days} days"
                elif status in ("queued", "running"):
                    # Never delete active tasks
                    skipped += 1
                    continue

                if should_delete:
                    # Calculate size before deletion
                    dir_size = self._get_dir_size(task_dir)

                    # Delete the directory
                    shutil.rmtree(task_dir)

                    deleted += 1
                    freed += dir_size
                    ttl_deletions_total.inc()

                    logger.info(
                        f"Deleted task {task_id}: {reason} "
                        f"(age={age.days}d, size={dir_size / 1024:.1f}KB)"
                    )

            except json.JSONDecodeError as e:
                errors.append(f"{task_dir.name}: Invalid JSON - {e}")
                logger.warning(f"Skipping {task_dir.name}: Invalid task.json - {e}")
            except PermissionError as e:
                errors.append(f"{task_dir.name}: Permission denied - {e}")
                logger.error(f"Cannot delete {task_dir.name}: Permission denied")
            except Exception as e:
                errors.append(f"{task_dir.name}: {e}")
                logger.error(f"Error cleaning {task_dir.name}: {e}")

        result = {
            "deleted_count": deleted,
            "freed_bytes": freed,
            "freed_mb": round(freed / 1024 / 1024, 2),
            "errors": errors,
            "skipped": skipped
        }

        if deleted > 0:
            logger.info(
                f"Housekeeping complete: deleted {deleted} tasks, "
                f"freed {result['freed_mb']} MB, {len(errors)} errors"
            )

        return result

    def _get_dir_size(self, path: Path) -> int:
        """Calculate total size of directory contents."""
        total = 0
        try:
            for f in path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
        except Exception:
            pass
        return total

    def get_stats(self) -> dict:
        """
        Get statistics about task directories without deleting.

        Returns:
            Dict with task counts by status and size
        """
        stats = {
            "total_tasks": 0,
            "total_size_mb": 0,
            "by_status": {},
            "expired": {"completed": 0, "failed": 0}
        }

        if not self.data_dir.exists():
            return stats

        now = datetime.utcnow()
        total_size = 0

        for task_dir in self.data_dir.iterdir():
            if not task_dir.is_dir():
                continue

            task_file = task_dir / "task.json"
            if not task_file.exists():
                continue

            try:
                with open(task_file) as f:
                    task = json.load(f)

                status = task.get("status", "unknown")
                stats["total_tasks"] += 1
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                # Check if expired
                mtime = datetime.fromtimestamp(task_file.stat().st_mtime)
                age = now - mtime

                if status == "completed" and age > self.completed_ttl:
                    stats["expired"]["completed"] += 1
                elif status in ("failed", "timeout") and age > self.failed_ttl:
                    stats["expired"]["failed"] += 1

                total_size += self._get_dir_size(task_dir)

            except Exception:
                pass

        stats["total_size_mb"] = round(total_size / 1024 / 1024, 2)
        return stats


async def run_periodic_cleanup(
    data_dir: str = "/app/data/tasks",
    interval_hours: int = 1,
    completed_ttl_days: int = 7,
    failed_ttl_days: int = 30
):
    """
    Run cleanup periodically as background task.

    Designed to be integrated into worker startup.

    Args:
        data_dir: Task data directory
        interval_hours: Hours between cleanup runs (default: 1)
        completed_ttl_days: Days to retain completed tasks (default: 7)
        failed_ttl_days: Days to retain failed tasks (default: 30)
    """
    housekeeper = Housekeeper(
        data_dir=data_dir,
        completed_ttl_days=completed_ttl_days,
        failed_ttl_days=failed_ttl_days
    )

    logger.info(
        f"Housekeeping started: interval={interval_hours}h, "
        f"completed_ttl={completed_ttl_days}d, failed_ttl={failed_ttl_days}d"
    )

    while True:
        try:
            result = housekeeper.cleanup()
            if result["deleted_count"] > 0 or result["errors"]:
                logger.info(
                    f"Housekeeping cycle: deleted {result['deleted_count']} tasks, "
                    f"freed {result['freed_mb']} MB, {len(result['errors'])} errors"
                )
        except Exception as e:
            logger.error(f"Housekeeping error: {e}", exc_info=True)

        await asyncio.sleep(interval_hours * 3600)
