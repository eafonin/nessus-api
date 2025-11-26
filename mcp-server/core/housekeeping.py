"""TTL-based task cleanup and stale scan management.

Phase 4.10: Automatic cleanup of old completed/failed tasks to prevent disk exhaustion.
Phase 7.1: Stale scan cleanup - stop and delete scans running longer than threshold.
"""

import json
import shutil
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from core.metrics import ttl_deletions_total

if TYPE_CHECKING:
    from scanners.registry import ScannerRegistry

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


class StaleScanCleaner:
    """
    Cleans up stale running/queued scans older than threshold.

    Phase 7.1: Stops scans on Nessus and updates task status to 'timeout'.

    Features:
    - Configurable stale threshold (default: 24 hours)
    - Stops scan on Nessus scanner before cleanup
    - Optionally deletes scan from Nessus
    - Updates task status to 'timeout'
    """

    def __init__(
        self,
        data_dir: str = "/app/data/tasks",
        stale_hours: int = 24,
        delete_from_nessus: bool = True
    ):
        """
        Initialize StaleScanCleaner.

        Args:
            data_dir: Directory containing task subdirectories
            stale_hours: Hours after which running scan is considered stale
            delete_from_nessus: Whether to delete scan from Nessus after stopping
        """
        self.data_dir = Path(data_dir)
        self.stale_threshold = timedelta(hours=stale_hours)
        self.delete_from_nessus = delete_from_nessus

    async def cleanup_stale_scans(
        self,
        scanner_registry: "ScannerRegistry"
    ) -> dict:
        """
        Find and stop stale running scans.

        Args:
            scanner_registry: Registry to get scanner instances

        Returns:
            Dict with:
                - stopped_count: Number of scans stopped
                - deleted_count: Number of scans deleted from Nessus
                - errors: List of error messages
        """
        now = datetime.utcnow()
        stopped = 0
        deleted = 0
        errors = []

        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {self.data_dir}")
            return {"stopped_count": 0, "deleted_count": 0, "errors": ["Data directory missing"]}

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
                task_id = task.get("task_id", task_dir.name)

                # Only process running/queued scans
                if status not in ("running", "queued"):
                    continue

                # Check age using started_at or created_at
                started_at = task.get("started_at") or task.get("created_at")
                if not started_at:
                    continue

                try:
                    start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00").replace("+00:00", ""))
                except (ValueError, AttributeError):
                    # Fallback to file mtime
                    start_time = datetime.fromtimestamp(task_file.stat().st_mtime)

                age = now - start_time

                if age <= self.stale_threshold:
                    continue  # Not stale yet

                # Stale scan found - stop and clean up
                nessus_scan_id = task.get("nessus_scan_id")
                scanner_pool = task.get("scanner_pool", "nessus")
                scanner_instance_id = task.get("scanner_instance_id")

                logger.warning(
                    f"Stale scan detected: {task_id} (age={age}, "
                    f"nessus_id={nessus_scan_id}, pool={scanner_pool})"
                )

                # Stop scan on Nessus if we have scan ID
                if nessus_scan_id and scanner_instance_id:
                    try:
                        scanner = await scanner_registry.get_scanner(
                            pool=scanner_pool,
                            instance_id=scanner_instance_id
                        )

                        if scanner:
                            # Stop the scan
                            try:
                                await scanner.stop_scan(nessus_scan_id)
                                stopped += 1
                                logger.info(f"Stopped stale scan {nessus_scan_id} on {scanner_instance_id}")
                            except Exception as e:
                                # Scan may already be stopped
                                logger.warning(f"Could not stop scan {nessus_scan_id}: {e}")

                            # Delete from Nessus if configured
                            if self.delete_from_nessus:
                                try:
                                    await scanner.delete_scan(nessus_scan_id)
                                    deleted += 1
                                    logger.info(f"Deleted stale scan {nessus_scan_id} from Nessus")
                                except Exception as e:
                                    logger.warning(f"Could not delete scan {nessus_scan_id}: {e}")
                            # Note: Don't close scanner - registry manages lifetime
                    except Exception as e:
                        errors.append(f"{task_id}: Scanner error - {e}")
                        logger.error(f"Scanner error for {task_id}: {e}")

                # Update task status to timeout
                task["status"] = "timeout"
                task["completed_at"] = datetime.utcnow().isoformat()
                task["error_message"] = f"Scan exceeded {self.stale_threshold.total_seconds() / 3600:.0f}h timeout and was automatically stopped"

                with open(task_file, "w") as f:
                    json.dump(task, f, indent=2)

                logger.info(f"Marked stale task {task_id} as timeout")

            except json.JSONDecodeError as e:
                errors.append(f"{task_dir.name}: Invalid JSON - {e}")
            except Exception as e:
                errors.append(f"{task_dir.name}: {e}")
                logger.error(f"Error processing stale scan {task_dir.name}: {e}")

        result = {
            "stopped_count": stopped,
            "deleted_count": deleted,
            "errors": errors
        }

        if stopped > 0 or deleted > 0:
            logger.info(
                f"Stale scan cleanup: stopped {stopped}, deleted {deleted}, "
                f"{len(errors)} errors"
            )

        return result

    def get_stale_scan_stats(self) -> dict:
        """
        Get statistics about potentially stale scans without stopping them.

        Returns:
            Dict with counts of stale running/queued scans
        """
        now = datetime.utcnow()
        stats = {
            "stale_running": 0,
            "stale_queued": 0,
            "active_running": 0,
            "active_queued": 0,
            "threshold_hours": self.stale_threshold.total_seconds() / 3600
        }

        if not self.data_dir.exists():
            return stats

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
                if status not in ("running", "queued"):
                    continue

                started_at = task.get("started_at") or task.get("created_at")
                if started_at:
                    try:
                        start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00").replace("+00:00", ""))
                    except (ValueError, AttributeError):
                        start_time = datetime.fromtimestamp(task_file.stat().st_mtime)
                else:
                    start_time = datetime.fromtimestamp(task_file.stat().st_mtime)

                age = now - start_time
                is_stale = age > self.stale_threshold

                if status == "running":
                    if is_stale:
                        stats["stale_running"] += 1
                    else:
                        stats["active_running"] += 1
                elif status == "queued":
                    if is_stale:
                        stats["stale_queued"] += 1
                    else:
                        stats["active_queued"] += 1

            except Exception:
                pass

        return stats


class NessusScanCleaner:
    """
    Scanner-centric cleanup: deletes old scans directly from each Nessus instance.

    Phase 7.2 (simplified): Instead of tracking task → scanner relationships,
    directly query each scanner for old scans and delete them.

    Features:
    - Scanner-centric: iterates over all configured scanners
    - No task tracking needed: queries Nessus API directly
    - Handles orphaned scans: scans without task records get cleaned up
    - Stops running scans if they exceed stale threshold
    """

    # Nessus scan statuses
    RUNNING_STATUSES = {"running", "pending", "pausing", "resuming"}
    COMPLETED_STATUSES = {"completed", "canceled", "imported"}

    def __init__(
        self,
        retention_hours: int = 24,
        stale_running_hours: int = 24
    ):
        """
        Initialize NessusScanCleaner.

        Args:
            retention_hours: Hours to keep finished scans on Nessus (default: 24)
            stale_running_hours: Hours after which running scans are stopped (default: 24)
        """
        self.retention_seconds = retention_hours * 3600
        self.stale_running_seconds = stale_running_hours * 3600

    async def cleanup_all_scanners(
        self,
        scanner_registry: "ScannerRegistry"
    ) -> dict:
        """
        Clean up old scans from all registered scanners.

        For each scanner:
        1. List all scans via Nessus API
        2. Delete finished scans older than retention_hours
        3. Stop and delete running scans older than stale_running_hours

        Args:
            scanner_registry: Registry containing all scanner instances

        Returns:
            Dict with:
                - scanners_processed: Number of scanners checked
                - deleted_count: Number of scans deleted
                - stopped_count: Number of running scans stopped
                - errors: List of error messages
        """
        import time
        now = time.time()
        deleted = 0
        stopped = 0
        errors = []
        scanners_processed = 0

        all_scanners = scanner_registry.get_all_scanners()
        if not all_scanners:
            logger.warning("No scanners registered for cleanup")
            return {
                "scanners_processed": 0,
                "deleted_count": 0,
                "stopped_count": 0,
                "errors": ["No scanners registered"]
            }

        for instance_key, scanner in all_scanners:
            scanners_processed += 1

            try:
                # List all scans from this scanner
                scans = await scanner.list_scans()
                logger.debug(f"[{instance_key}] Found {len(scans)} scans")

                for scan in scans:
                    scan_id = scan.get("id")
                    scan_name = scan.get("name", "unnamed")
                    status = scan.get("status", "unknown")
                    last_mod = scan.get("last_modification_date", 0)

                    if not scan_id or not last_mod:
                        continue

                    age_seconds = now - last_mod
                    age_hours = age_seconds / 3600

                    try:
                        # Handle running scans that are stale
                        if status in self.RUNNING_STATUSES:
                            if age_seconds > self.stale_running_seconds:
                                logger.info(
                                    f"[{instance_key}] Stopping stale scan {scan_id} "
                                    f"'{scan_name}' (age={age_hours:.1f}h, status={status})"
                                )
                                try:
                                    await scanner.stop_scan(scan_id)
                                    stopped += 1
                                except Exception as e:
                                    logger.warning(f"Could not stop scan {scan_id}: {e}")

                                # Delete after stopping
                                await scanner.delete_scan(scan_id)
                                deleted += 1
                                logger.info(f"[{instance_key}] Deleted stale scan {scan_id}")

                        # Handle finished scans that are old
                        elif status in self.COMPLETED_STATUSES:
                            if age_seconds > self.retention_seconds:
                                await scanner.delete_scan(scan_id)
                                deleted += 1
                                logger.info(
                                    f"[{instance_key}] Deleted old scan {scan_id} "
                                    f"'{scan_name}' (age={age_hours:.1f}h)"
                                )

                    except Exception as e:
                        error_msg = f"[{instance_key}] scan {scan_id}: {e}"
                        if "404" not in str(e) and "not found" not in str(e).lower():
                            errors.append(error_msg)
                            logger.warning(error_msg)
                        # 404 = already deleted, silently ignore

            except Exception as e:
                error_msg = f"[{instance_key}] Failed to list scans: {e}"
                errors.append(error_msg)
                logger.error(error_msg)

        result = {
            "scanners_processed": scanners_processed,
            "deleted_count": deleted,
            "stopped_count": stopped,
            "errors": errors
        }

        if deleted > 0 or stopped > 0:
            logger.info(
                f"Nessus cleanup: {scanners_processed} scanners, "
                f"deleted {deleted}, stopped {stopped}, {len(errors)} errors"
            )

        return result


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


async def run_stale_scan_cleanup(
    scanner_registry: "ScannerRegistry",
    data_dir: str = "/app/data/tasks",
    interval_hours: int = 1,
    stale_hours: int = 24,
    delete_from_nessus: bool = True
):
    """
    Run stale scan cleanup periodically as background task.

    Designed to be integrated into worker startup alongside TTL cleanup.

    Args:
        scanner_registry: Registry to get scanner instances
        data_dir: Task data directory
        interval_hours: Hours between cleanup runs (default: 1)
        stale_hours: Hours after which running scan is considered stale (default: 24)
        delete_from_nessus: Whether to delete stale scans from Nessus (default: True)
    """
    cleaner = StaleScanCleaner(
        data_dir=data_dir,
        stale_hours=stale_hours,
        delete_from_nessus=delete_from_nessus
    )

    logger.info(
        f"Stale scan cleanup started: interval={interval_hours}h, "
        f"stale_threshold={stale_hours}h, delete_from_nessus={delete_from_nessus}"
    )

    while True:
        try:
            result = await cleaner.cleanup_stale_scans(scanner_registry)
            if result["stopped_count"] > 0 or result["deleted_count"] > 0 or result["errors"]:
                logger.info(
                    f"Stale scan cleanup cycle: stopped {result['stopped_count']}, "
                    f"deleted {result['deleted_count']}, {len(result['errors'])} errors"
                )
        except Exception as e:
            logger.error(f"Stale scan cleanup error: {e}", exc_info=True)

        await asyncio.sleep(interval_hours * 3600)


async def run_nessus_scan_cleanup(
    scanner_registry: "ScannerRegistry",
    interval_hours: int = 1,
    retention_hours: int = 24,
    stale_running_hours: int = 24
):
    """
    Run scanner-centric cleanup periodically as background task.

    For each configured scanner:
    - Deletes finished scans older than retention_hours
    - Stops and deletes running scans older than stale_running_hours

    This is scanner-centric: no task tracking needed, queries Nessus API directly.

    Args:
        scanner_registry: Registry containing all scanner instances
        interval_hours: Hours between cleanup runs (default: 1)
        retention_hours: Hours to keep finished scans on Nessus (default: 24)
        stale_running_hours: Hours after which running scans are stopped (default: 24)
    """
    cleaner = NessusScanCleaner(
        retention_hours=retention_hours,
        stale_running_hours=stale_running_hours
    )

    logger.info(
        f"Nessus scan cleanup started: interval={interval_hours}h, "
        f"retention={retention_hours}h, stale_running={stale_running_hours}h"
    )

    while True:
        try:
            result = await cleaner.cleanup_all_scanners(scanner_registry)
            if result["deleted_count"] > 0 or result["stopped_count"] > 0 or result["errors"]:
                logger.info(
                    f"Nessus scan cleanup cycle: {result['scanners_processed']} scanners, "
                    f"deleted {result['deleted_count']}, stopped {result['stopped_count']}, "
                    f"{len(result['errors'])} errors"
                )
        except Exception as e:
            logger.error(f"Nessus scan cleanup error: {e}", exc_info=True)

        await asyncio.sleep(interval_hours * 3600)
