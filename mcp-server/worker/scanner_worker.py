"""Background worker for processing scan tasks from Redis queue."""

import asyncio
import signal
import os
import logging
from typing import Optional
from pathlib import Path

from core.queue import TaskQueue
from core.task_manager import TaskManager
from core.types import ScanState
from scanners.registry import ScannerRegistry
from scanners.base import ScanRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScannerWorker:
    """
    Background worker that processes scan tasks from Redis queue.

    Features:
    - Consumes tasks from Redis queue (BRPOP)
    - Executes scans via scanner registry
    - Updates task state machine
    - Error handling with Dead Letter Queue
    - Graceful shutdown on SIGTERM/SIGINT
    - 24-hour scan timeout protection
    """

    def __init__(
        self,
        queue: TaskQueue,
        task_manager: TaskManager,
        scanner_registry: ScannerRegistry,
        max_concurrent_scans: int = 5
    ):
        """
        Initialize scanner worker.

        Args:
            queue: TaskQueue instance for consuming tasks
            task_manager: TaskManager for updating task state
            scanner_registry: ScannerRegistry for getting scanner instances
            max_concurrent_scans: Maximum parallel scans (default: 5)
        """
        self.queue = queue
        self.task_manager = task_manager
        self.scanner_registry = scanner_registry
        self.max_concurrent_scans = max_concurrent_scans
        self.running = False
        self.active_tasks: set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
        self._shutdown_event.set()

    async def start(self) -> None:
        """
        Start worker loop with graceful shutdown handling.

        Continuously polls queue and spawns task processors.
        """
        self.running = True
        logger.info(f"Worker started (max_concurrent_scans={self.max_concurrent_scans})")

        try:
            await self._worker_loop()
        finally:
            await self._cleanup()

    async def _worker_loop(self) -> None:
        """Main worker loop - poll queue and process tasks."""
        while self.running:
            try:
                # Check if at capacity
                if len(self.active_tasks) >= self.max_concurrent_scans:
                    logger.debug(f"At capacity ({len(self.active_tasks)}/{self.max_concurrent_scans}), waiting...")
                    await asyncio.sleep(1)
                    # Clean up completed tasks
                    self.active_tasks = {t for t in self.active_tasks if not t.done()}
                    continue

                # Dequeue task (blocking with 5s timeout)
                task_data = self.queue.dequeue(timeout=5)

                if not task_data:
                    # Timeout - no tasks available
                    continue

                # Spawn task processor (non-blocking)
                task = asyncio.create_task(self._process_task(task_data))
                self.active_tasks.add(task)

                # Remove from active set when done
                task.add_done_callback(self.active_tasks.discard)

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Back off on error

        logger.info("Worker loop exited")

    async def _process_task(self, task_data: dict) -> None:
        """
        Process single scan task through full lifecycle.

        Workflow:
        1. Transition to RUNNING
        2. Get scanner instance
        3. Create scan
        4. Launch scan
        5. Poll until completion (with timeout)
        6. Export results
        7. Transition to COMPLETED/FAILED/TIMEOUT

        Args:
            task_data: Task dictionary from queue
        """
        task_id = task_data.get("task_id", "unknown")
        trace_id = task_data.get("trace_id", "unknown")

        logger.info(f"Processing task: {task_id}, trace_id: {trace_id}")

        scanner = None
        try:
            # Transition to RUNNING
            self.task_manager.update_status(
                task_id,
                ScanState.RUNNING
            )

            # Get scanner instance
            scanner = self.scanner_registry.get_instance(
                scanner_type=task_data.get("scanner_type", "nessus"),
                instance_id=task_data.get("scanner_instance_id")
            )

            # Create scan request
            payload = task_data["payload"]
            scan_request = ScanRequest(
                targets=payload["targets"],
                name=payload["name"],
                scan_type=task_data.get("scan_type", "untrusted"),
                description=payload.get("description", ""),
                credentials=payload.get("credentials"),
                schema_profile=payload.get("schema_profile", "brief")
            )

            # Create scan in Nessus
            logger.info(f"[{task_id}] Creating scan: {scan_request.name}")
            scan_id = await scanner.create_scan(scan_request)
            logger.info(f"[{task_id}] Created scan_id: {scan_id}")

            # Update task with scan_id
            self.task_manager.update_status(
                task_id,
                ScanState.RUNNING,
                nessus_scan_id=scan_id
            )

            # Launch scan
            logger.info(f"[{task_id}] Launching scan {scan_id}...")
            scan_uuid = await scanner.launch_scan(scan_id)
            logger.info(f"[{task_id}] Scan launched, UUID: {scan_uuid}")

            # Poll until completion (with timeout)
            await self._poll_until_complete(
                task_id=task_id,
                scanner=scanner,
                scan_id=scan_id,
                timeout_seconds=24 * 3600  # 24 hours
            )

        except Exception as e:
            logger.error(f"[{task_id}] Task failed: {e}", exc_info=True)
            await self._handle_error(task_data, e)

        finally:
            # Cleanup scanner resources
            if scanner:
                try:
                    await scanner.close()
                    logger.debug(f"[{task_id}] Scanner connection closed")
                except Exception as e:
                    logger.error(f"[{task_id}] Error closing scanner: {e}")

    async def _poll_until_complete(
        self,
        task_id: str,
        scanner,
        scan_id: int,
        timeout_seconds: int = 86400  # 24 hours
    ) -> None:
        """
        Poll scan status until completion or timeout.

        Args:
            task_id: Task ID for logging
            scanner: Scanner instance
            scan_id: Nessus scan ID
            timeout_seconds: Maximum time to wait (default: 24h)

        Raises:
            TimeoutError: If scan exceeds timeout
        """
        poll_interval = 30  # 30 seconds
        elapsed = 0

        logger.info(f"[{task_id}] Polling scan {scan_id} (timeout: {timeout_seconds}s)...")

        while elapsed < timeout_seconds:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            try:
                status = await scanner.get_status(scan_id)
                scanner_status = status["status"]
                progress = status.get("progress", 0)

                logger.info(
                    f"[{task_id}] Scan {scan_id} status: {scanner_status}, "
                    f"progress: {progress}%, elapsed: {elapsed}s"
                )

                if scanner_status == "completed":
                    # Success - export results
                    logger.info(f"[{task_id}] Scan completed, exporting results...")
                    results = await scanner.export_results(scan_id)

                    # Save results to task directory
                    task_dir = self.task_manager.data_dir / task_id
                    task_dir.mkdir(parents=True, exist_ok=True)
                    results_file = task_dir / "scan_native.nessus"
                    results_file.write_bytes(results)

                    logger.info(
                        f"[{task_id}] Results saved: {results_file} "
                        f"({len(results)} bytes)"
                    )

                    # Transition to COMPLETED
                    self.task_manager.update_status(
                        task_id,
                        ScanState.COMPLETED
                    )

                    logger.info(f"[{task_id}] Task completed successfully")
                    return

                elif scanner_status == "failed":
                    # Scanner reported failure
                    error_msg = "Scanner reported failure"
                    logger.warning(f"[{task_id}] {error_msg}")

                    self.task_manager.update_status(
                        task_id,
                        ScanState.FAILED,
                        error_message=error_msg
                    )
                    return

            except Exception as e:
                logger.error(f"[{task_id}] Error polling status: {e}")
                # Continue polling - transient errors are OK

        # Timeout reached
        logger.warning(f"[{task_id}] Scan timeout after {elapsed}s, stopping scan...")

        try:
            await scanner.stop_scan(scan_id)
        except Exception as e:
            logger.error(f"[{task_id}] Error stopping scan: {e}")

        self.task_manager.update_status(
            task_id,
            ScanState.TIMEOUT,
            error_message=f"Scan timeout after {timeout_seconds}s"
        )

    async def _handle_error(self, task_data: dict, error: Exception) -> None:
        """
        Handle task error by moving to Dead Letter Queue.

        Args:
            task_data: Task dictionary
            error: Exception that occurred
        """
        task_id = task_data.get("task_id", "unknown")
        error_msg = f"{error.__class__.__name__}: {str(error)}"

        logger.error(f"[{task_id}] Moving to DLQ: {error_msg}")

        # Update task state to FAILED
        try:
            self.task_manager.update_status(
                task_id,
                ScanState.FAILED,
                error_message=error_msg
            )
        except Exception as e:
            logger.error(f"[{task_id}] Failed to update task state: {e}")

        # Move to Dead Letter Queue
        self.queue.move_to_dlq(task_data, error_msg)

    async def _cleanup(self) -> None:
        """Clean up resources and wait for active tasks."""
        logger.info(f"Cleanup: waiting for {len(self.active_tasks)} active tasks...")

        if self.active_tasks:
            # Wait for active tasks with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.active_tasks, return_exceptions=True),
                    timeout=60  # 1 minute timeout for cleanup
                )
            except asyncio.TimeoutError:
                logger.warning("Cleanup timeout - some tasks may not have finished")

        logger.info("Worker shutdown complete")


async def main():
    """Worker entry point."""
    # Load configuration from environment
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    data_dir = os.getenv("DATA_DIR", "/app/data/tasks")
    scanner_config = os.getenv("SCANNER_CONFIG", "/app/config/scanners.yaml")
    max_concurrent = int(os.getenv("MAX_CONCURRENT_SCANS", "5"))
    log_level = os.getenv("LOG_LEVEL", "INFO")

    # Configure logging
    logging.getLogger().setLevel(log_level)

    logger.info("=" * 60)
    logger.info("Nessus Scanner Worker Starting")
    logger.info("=" * 60)
    logger.info(f"Redis URL: {redis_url}")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Scanner config: {scanner_config}")
    logger.info(f"Max concurrent scans: {max_concurrent}")
    logger.info(f"Log level: {log_level}")
    logger.info("=" * 60)

    # Initialize components
    try:
        queue = TaskQueue(redis_url=redis_url)
        task_manager = TaskManager(data_dir=data_dir)
        scanner_registry = ScannerRegistry(config_file=scanner_config)

        logger.info("✅ Components initialized")

    except Exception as e:
        logger.error(f"Failed to initialize components: {e}", exc_info=True)
        return 1

    # Create and start worker
    worker = ScannerWorker(
        queue=queue,
        task_manager=task_manager,
        scanner_registry=scanner_registry,
        max_concurrent_scans=max_concurrent
    )

    try:
        await worker.start()
        return 0
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        return 1
    finally:
        queue.close()
        logger.info("Worker stopped")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
