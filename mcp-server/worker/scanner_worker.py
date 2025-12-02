"""Background worker for processing scan tasks from Redis queue.

Phase 4: Supports pool-based queue consumption.
"""

import asyncio
import contextlib
import logging
import os
import signal
from types import FrameType

from core.housekeeping import (
    run_nessus_scan_cleanup,
    run_periodic_cleanup,
    run_stale_scan_cleanup,
)
from core.metrics import (
    record_auth_failure,
    record_validation_failure,
    record_validation_result,
    update_all_scanner_metrics,
    update_pool_dlq_depth,
    update_pool_queue_depth,
)
from core.queue import TaskQueue
from core.task_manager import TaskManager
from core.types import ScanState
from scanners.base import ScannerInterface, ScanRequest
from scanners.nessus_validator import validate_scan_results
from scanners.registry import ScannerRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ScannerWorker:
    """
    Background worker that processes scan tasks from Redis queue.

    Phase 4 Enhancements:
    - Pool-based queue consumption (consumes from specific pool queues)
    - Load-based scanner selection within pools
    - Per-scanner active scan tracking

    Features:
    - Consumes tasks from pool-specific Redis queues (BRPOP)
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
        pools: list[str] | None = None,
    ) -> None:
        """
        Initialize scanner worker.

        Per-pool backpressure: Each pool's capacity is derived from its scanner
        configuration (sum of max_concurrent_scans for all scanners in pool).

        Args:
            queue: TaskQueue instance for consuming tasks
            task_manager: TaskManager for updating task state
            scanner_registry: ScannerRegistry for getting scanner instances
            pools: List of pool names to consume from (e.g., ["nessus", "nessus_dmz"]).
                  If None, uses all registered pools from scanner_registry.
        """
        self.queue = queue
        self.task_manager = task_manager
        self.scanner_registry = scanner_registry
        self.running = False
        self._shutdown_event = asyncio.Event()

        # Determine pools to consume from
        if pools:
            self.pools = pools
        else:
            # Use all registered pools from scanner_registry
            self.pools = scanner_registry.list_pools()
            if not self.pools:
                # Fallback to default pool
                self.pools = [scanner_registry.get_default_pool()]

        # Per-pool active task tracking for backpressure control
        # Capacity for each pool is derived from scanner_registry.get_pool_capacity()
        self.active_tasks_per_pool: dict[str, set[asyncio.Task]] = {
            pool: set() for pool in self.pools
        }

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _get_pool_capacity(self, pool: str) -> int:
        """Get capacity for pool from scanner registry."""
        return self.scanner_registry.get_pool_capacity(pool)

    def _get_pools_with_capacity(self) -> list[str]:
        """Return pools that have available capacity for new scans."""
        available = []
        for pool in self.pools:
            active = len(self.active_tasks_per_pool.get(pool, set()))
            capacity = self._get_pool_capacity(pool)
            if active < capacity:
                available.append(pool)
        return available

    def _get_capacity_status(self) -> dict[str, str]:
        """Get human-readable capacity status for all pools."""
        result = {}
        for pool in self.pools:
            active = len(self.active_tasks_per_pool.get(pool, set()))
            cap = self._get_pool_capacity(pool)
            result[pool] = f"{active}/{cap}"
        return result

    def _cleanup_completed_tasks(self) -> None:
        """Remove completed tasks from per-pool tracking."""
        for pool in self.pools:
            self.active_tasks_per_pool[pool] = {
                t for t in self.active_tasks_per_pool[pool] if not t.done()
            }

    def _handle_shutdown(self, signum: int, frame: FrameType | None) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
        self._shutdown_event.set()

    async def start(self) -> None:
        """
        Start worker loop with graceful shutdown handling.

        Continuously polls pool queues and spawns task processors.
        """
        self.running = True
        # Log per-pool capacities derived from scanner configuration
        pool_capacities = {pool: self._get_pool_capacity(pool) for pool in self.pools}
        logger.info(
            f"Worker started with per-pool backpressure (pools={self.pools}, "
            f"capacities={pool_capacities})"
        )

        try:
            await self._worker_loop()
        finally:
            await self._cleanup()

    def _update_metrics(self) -> None:
        """Update Prometheus metrics for pools and scanners."""
        try:
            # Update queue metrics for each pool
            for pool in self.pools:
                depth = self.queue.get_queue_depth(pool=pool)
                dlq_depth = self.queue.get_dlq_size(pool=pool)
                update_pool_queue_depth(pool, depth)
                update_pool_dlq_depth(pool, dlq_depth)

            # Update scanner metrics
            scanner_list = self.scanner_registry.list_instances(include_load=True)
            update_all_scanner_metrics(scanner_list)
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    async def _worker_loop(self) -> None:
        """Main worker loop - poll pool queues and process tasks.

        Per-pool backpressure: Only dequeues from pools that have available
        capacity. Each pool's capacity is derived from scanner configuration.

        # TODO: Future enhancement - Target network limits
        # Different target networks may have different scan capacity based on:
        # - Target infrastructure resources (CPU/RAM consumption during scans)
        # - Network bandwidth constraints
        # - Compliance requirements (e.g., production vs lab)
        #
        # Potential implementation:
        # target_limits:
        #   - cidr: "172.32.0.0/24"
        #     max_concurrent_scans: 2
        #   - cidr: "10.0.0.0/8"
        #     max_concurrent_scans: 10
        #   - default: 5
        #
        # Would require checking target CIDR against limits before allowing scan.
        """
        import time

        metrics_interval = 30  # Update metrics every 30 seconds
        last_metrics_update = 0.0

        while self.running:
            try:
                # Periodic metrics update
                now = time.time()
                if now - last_metrics_update >= metrics_interval:
                    self._update_metrics()
                    last_metrics_update = now

                # Clean up completed tasks from all pools
                self._cleanup_completed_tasks()

                # Per-pool backpressure: only dequeue from pools with available capacity
                pools_with_capacity = self._get_pools_with_capacity()
                if not pools_with_capacity:
                    status = self._get_capacity_status()
                    logger.debug(f"All pools at capacity: {status}, waiting...")
                    await asyncio.sleep(1)
                    continue

                # Dequeue task from pools with available capacity (blocking with 5s timeout)
                # Run blocking Redis call in thread pool to avoid blocking event loop
                task_data = await asyncio.to_thread(
                    self.queue.dequeue_any, pools=pools_with_capacity, timeout=5
                )

                if not task_data:
                    # Timeout - no tasks available
                    continue

                # Determine which pool this task belongs to
                task_pool = task_data.get("scanner_pool", self.pools[0])

                # Ensure pool is tracked (in case of dynamic pool addition)
                if task_pool not in self.active_tasks_per_pool:
                    self.active_tasks_per_pool[task_pool] = set()

                # Spawn task processor (non-blocking)
                task = asyncio.create_task(self._process_task(task_data))
                self.active_tasks_per_pool[task_pool].add(task)

                # Log task assignment
                status = self._get_capacity_status()
                logger.debug(f"Task assigned to pool '{task_pool}': {status}")

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Back off on error

        logger.info("Worker loop exited")

    async def _process_task(self, task_data: dict) -> None:
        """
        Process single scan task through full lifecycle.

        Workflow:
        1. Acquire scanner from pool (increments active_scans)
        2. Transition to RUNNING
        3. Create scan
        4. Launch scan
        5. Poll until completion (with timeout)
        6. Export results
        7. Release scanner (decrements active_scans)
        8. Transition to COMPLETED/FAILED/TIMEOUT

        Args:
            task_data: Task dictionary from queue
        """
        task_id = task_data.get("task_id", "unknown")
        trace_id = task_data.get("trace_id", "unknown")
        scanner_pool = task_data.get("scanner_pool") or task_data.get(
            "scanner_type", "nessus"
        )
        scanner_instance_id = task_data.get("scanner_instance_id")

        logger.info(
            f"Processing task: {task_id}, trace_id: {trace_id}, pool: {scanner_pool}"
        )

        scanner = None
        instance_key = None
        try:
            # Acquire scanner from pool (increments active_scans)
            scanner, instance_key = await self.scanner_registry.acquire_scanner(
                pool=scanner_pool, instance_id=scanner_instance_id
            )
            logger.info(f"[{task_id}] Acquired scanner: {instance_key}")

            # Transition to RUNNING
            self.task_manager.update_status(task_id, ScanState.RUNNING)

            # Create scan request
            payload = task_data["payload"]
            scan_request = ScanRequest(
                targets=payload["targets"],
                name=payload["name"],
                scan_type=task_data.get("scan_type", "untrusted"),
                description=payload.get("description", ""),
                credentials=payload.get("credentials"),
                schema_profile=payload.get("schema_profile", "brief"),
            )

            # Create scan in Nessus
            logger.info(f"[{task_id}] Creating scan: {scan_request.name}")
            scan_id = await scanner.create_scan(scan_request)
            logger.info(f"[{task_id}] Created scan_id: {scan_id}")

            # Update task with scan_id
            self.task_manager.update_status(
                task_id, ScanState.RUNNING, nessus_scan_id=scan_id
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
                scanner_pool=scanner_pool,
                timeout_seconds=24 * 3600,  # 24 hours
            )

        except Exception as e:
            logger.error(f"[{task_id}] Task failed: {e}", exc_info=True)
            await self._handle_error(task_data, e)

        finally:
            # Release scanner (decrements active_scans)
            if instance_key:
                await self.scanner_registry.release_scanner(instance_key)
                logger.debug(f"[{task_id}] Released scanner: {instance_key}")

            # Cleanup scanner resources
            if scanner:
                try:
                    await scanner.close()
                    logger.debug(f"[{task_id}] Scanner connection closed")
                except Exception as e:
                    logger.error(f"[{task_id}] Error closing scanner: {e}")

    def _get_scan_type_from_task(self, task_id: str) -> str:
        """Get scan_type from task metadata."""
        task = self.task_manager.get_task(task_id)
        if task:
            return task.scan_type
        return "untrusted"

    async def _poll_until_complete(
        self,
        task_id: str,
        scanner: ScannerInterface,
        scan_id: int,
        scanner_pool: str = "nessus",
        timeout_seconds: int = 86400,  # 24 hours
    ) -> None:
        """
        Poll scan status until completion or timeout.

        Args:
            task_id: Task ID for logging
            scanner: Scanner instance
            scan_id: Nessus scan ID
            scanner_pool: Scanner pool name for metrics
            timeout_seconds: Maximum time to wait (default: 24h)

        Raises:
            TimeoutError: If scan exceeds timeout
        """
        poll_interval = 30  # 30 seconds
        elapsed = 0

        logger.info(
            f"[{task_id}] Polling scan {scan_id} (timeout: {timeout_seconds}s)..."
        )

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

                    # Phase 4: Validate scan results
                    scan_type = self._get_scan_type_from_task(task_id)
                    validation = validate_scan_results(
                        nessus_file=results_file, scan_type=scan_type
                    )

                    if validation.is_valid:
                        # Success - mark completed with validation data
                        self.task_manager.mark_completed_with_validation(
                            task_id,
                            validation_stats=validation.stats,
                            validation_warnings=validation.warnings,
                            authentication_status=validation.authentication_status,
                        )
                        # Record validation success metric
                        record_validation_result(scanner_pool, is_valid=True)
                        logger.info(
                            f"[{task_id}] Task completed successfully "
                            f"(auth_status={validation.authentication_status}, "
                            f"hosts={validation.stats.get('hosts_scanned', 0)}, "
                            f"vulns={validation.stats.get('total_vulnerabilities', 0)})"
                        )
                    else:
                        # Validation failed (e.g., auth failure)
                        self.task_manager.mark_failed_with_validation(
                            task_id,
                            error_message=validation.error or "Validation failed",
                            validation_stats=validation.stats,
                            authentication_status=validation.authentication_status,
                        )
                        # Record validation failure metrics
                        record_validation_result(scanner_pool, is_valid=False)

                        # Categorize and record failure reason
                        if validation.authentication_status == "failed":
                            record_validation_failure(scanner_pool, "auth_failed")
                            record_auth_failure(scanner_pool, scan_type)
                        elif "XML" in str(validation.error or ""):
                            record_validation_failure(scanner_pool, "xml_invalid")
                        elif "empty" in str(validation.error or "").lower():
                            record_validation_failure(scanner_pool, "empty_scan")
                        elif "not found" in str(validation.error or "").lower():
                            record_validation_failure(scanner_pool, "file_not_found")
                        else:
                            record_validation_failure(scanner_pool, "other")

                        logger.warning(
                            f"[{task_id}] Scan validation failed: {validation.error} "
                            f"(auth_status={validation.authentication_status})"
                        )

                    return

                elif scanner_status == "failed":
                    # Scanner reported failure
                    error_msg = "Scanner reported failure"
                    logger.warning(f"[{task_id}] {error_msg}")

                    self.task_manager.update_status(
                        task_id, ScanState.FAILED, error_message=error_msg
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
            error_message=f"Scan timeout after {timeout_seconds}s",
        )

    async def _handle_error(self, task_data: dict, error: Exception) -> None:
        """
        Handle task error by moving to Dead Letter Queue.

        Args:
            task_data: Task dictionary
            error: Exception that occurred
        """
        task_id = task_data.get("task_id", "unknown")
        scanner_pool = task_data.get("scanner_pool") or task_data.get(
            "scanner_type", "nessus"
        )
        error_msg = f"{error.__class__.__name__}: {error!s}"

        logger.error(f"[{task_id}] Moving to DLQ (pool={scanner_pool}): {error_msg}")

        # Update task state to FAILED
        try:
            self.task_manager.update_status(
                task_id, ScanState.FAILED, error_message=error_msg
            )
        except Exception as e:
            logger.error(f"[{task_id}] Failed to update task state: {e}")

        # Move to pool-specific Dead Letter Queue
        self.queue.move_to_dlq(task_data, error_msg, pool=scanner_pool)

    async def _cleanup(self) -> None:
        """Clean up resources and wait for active tasks across all pools."""
        # Gather all active tasks from all pools
        all_tasks = set()
        for pool_tasks in self.active_tasks_per_pool.values():
            all_tasks.update(pool_tasks)

        logger.info(
            f"Cleanup: waiting for {len(all_tasks)} active tasks across {len(self.pools)} pools..."
        )

        if all_tasks:
            # Wait for active tasks with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*all_tasks, return_exceptions=True),
                    timeout=60,  # 1 minute timeout for cleanup
                )
            except TimeoutError:
                logger.warning("Cleanup timeout - some tasks may not have finished")

        logger.info("Worker shutdown complete")


async def main() -> int:
    """Worker entry point."""
    # Load configuration from environment
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    data_dir = os.getenv("DATA_DIR", "/app/data/tasks")
    scanner_config = os.getenv("SCANNER_CONFIG", "/app/config/scanners.yaml")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    # Pool configuration (comma-separated list or empty for all pools)
    # Example: WORKER_POOLS=nessus,nessus_dmz
    pools_env = os.getenv("WORKER_POOLS", "")
    pools = (
        [p.strip() for p in pools_env.split(",") if p.strip()] if pools_env else None
    )

    # Housekeeping configuration
    housekeeping_enabled = os.getenv("HOUSEKEEPING_ENABLED", "true").lower() == "true"
    housekeeping_interval_hours = int(os.getenv("HOUSEKEEPING_INTERVAL_HOURS", "1"))
    completed_ttl_days = int(os.getenv("COMPLETED_TTL_DAYS", "7"))
    failed_ttl_days = int(os.getenv("FAILED_TTL_DAYS", "30"))

    # Stale scan cleanup configuration
    stale_scan_cleanup_enabled = (
        os.getenv("STALE_SCAN_CLEANUP_ENABLED", "true").lower() == "true"
    )
    stale_scan_hours = int(os.getenv("STALE_SCAN_HOURS", "24"))
    stale_scan_delete_from_nessus = (
        os.getenv("STALE_SCAN_DELETE_FROM_NESSUS", "true").lower() == "true"
    )

    # Nessus scan cleanup configuration (delete finished scans from Nessus)
    nessus_scan_cleanup_enabled = (
        os.getenv("NESSUS_SCAN_CLEANUP_ENABLED", "true").lower() == "true"
    )
    nessus_scan_retention_hours = int(os.getenv("NESSUS_SCAN_RETENTION_HOURS", "24"))

    # Configure logging
    logging.getLogger().setLevel(log_level)

    logger.info("=" * 60)
    logger.info("Nessus Scanner Worker Starting")
    logger.info("=" * 60)
    logger.info(f"Redis URL: {redis_url}")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Scanner config: {scanner_config}")
    logger.info(f"Pools: {pools or 'all'}")
    logger.info(f"Log level: {log_level}")
    logger.info("Per-pool backpressure: capacity derived from scanners.yaml")
    logger.info("=" * 60)

    # Initialize components
    try:
        queue = TaskQueue(redis_url=redis_url)
        task_manager = TaskManager(data_dir=data_dir)
        scanner_registry = ScannerRegistry(config_file=scanner_config)

        logger.info("✅ Components initialized")
        logger.info(f"Available pools: {scanner_registry.list_pools()}")

    except Exception as e:
        logger.error(f"Failed to initialize components: {e}", exc_info=True)
        return 1

    # Create and start worker
    # Per-pool backpressure: capacity is derived from scanners.yaml, not env var
    worker = ScannerWorker(
        queue=queue,
        task_manager=task_manager,
        scanner_registry=scanner_registry,
        pools=pools,
    )

    # Start housekeeping background task if enabled
    housekeeping_task = None
    if housekeeping_enabled:
        logger.info(
            f"Housekeeping enabled: interval={housekeeping_interval_hours}h, "
            f"completed_ttl={completed_ttl_days}d, failed_ttl={failed_ttl_days}d"
        )
        housekeeping_task = asyncio.create_task(
            run_periodic_cleanup(
                data_dir=data_dir,
                interval_hours=housekeeping_interval_hours,
                completed_ttl_days=completed_ttl_days,
                failed_ttl_days=failed_ttl_days,
            )
        )

    # Start stale scan cleanup background task if enabled
    stale_scan_task = None
    if stale_scan_cleanup_enabled:
        logger.info(
            f"Stale scan cleanup enabled: threshold={stale_scan_hours}h, "
            f"delete_from_nessus={stale_scan_delete_from_nessus}"
        )
        stale_scan_task = asyncio.create_task(
            run_stale_scan_cleanup(
                scanner_registry=scanner_registry,
                data_dir=data_dir,
                interval_hours=housekeeping_interval_hours,  # Run at same interval
                stale_hours=stale_scan_hours,
                delete_from_nessus=stale_scan_delete_from_nessus,
            )
        )

    # Start Nessus scan cleanup background task if enabled (scanner-centric cleanup)
    nessus_scan_task = None
    if nessus_scan_cleanup_enabled:
        logger.info(
            f"Nessus scan cleanup enabled: retention={nessus_scan_retention_hours}h"
        )
        nessus_scan_task = asyncio.create_task(
            run_nessus_scan_cleanup(
                scanner_registry=scanner_registry,
                interval_hours=housekeeping_interval_hours,  # Run at same interval
                retention_hours=nessus_scan_retention_hours,
                stale_running_hours=stale_scan_hours,  # Use same threshold for stale running scans
            )
        )

    try:
        await worker.start()
        return 0
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        return 1
    finally:
        # Cancel background tasks
        if housekeeping_task:
            housekeeping_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await housekeeping_task
        if stale_scan_task:
            stale_scan_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await stale_scan_task
        if nessus_scan_task:
            nessus_scan_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await nessus_scan_task

        queue.close()
        logger.info("Worker stopped")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
