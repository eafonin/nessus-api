"""Prometheus metrics definitions for Nessus MCP Server."""
from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY


# =============================================================================
# Counters (monotonically increasing)
# =============================================================================

scans_total = Counter(
    "nessus_scans_total",
    "Total number of scans submitted",
    ["scan_type", "status"]
)

api_requests_total = Counter(
    "nessus_api_requests_total",
    "Total number of MCP tool invocations",
    ["tool", "status"]
)

ttl_deletions_total = Counter(
    "nessus_ttl_deletions_total",
    "Total number of tasks deleted by TTL cleanup"
)


# =============================================================================
# Gauges (can go up and down)
# =============================================================================

active_scans = Gauge(
    "nessus_active_scans",
    "Number of currently running scans"
)

scanner_instances = Gauge(
    "nessus_scanner_instances",
    "Number of registered scanner instances",
    ["scanner_type", "enabled"]
)

queue_depth = Gauge(
    "nessus_queue_depth",
    "Number of tasks in queue",
    ["queue"]  # main, dead
)

dlq_size = Gauge(
    "nessus_dlq_size",
    "Number of tasks in dead letter queue"
)


# =============================================================================
# Histograms (distribution of values)
# =============================================================================

task_duration_seconds = Histogram(
    "nessus_task_duration_seconds",
    "Task execution duration in seconds",
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400]  # 1m, 5m, 10m, 30m, 1h, 2h, 4h
)


# =============================================================================
# Metric Helpers
# =============================================================================

def metrics_response() -> bytes:
    """
    Generate Prometheus metrics response.

    Returns:
        Prometheus text format metrics
    """
    return generate_latest(REGISTRY)


def record_tool_call(tool_name: str, status: str = "success"):
    """
    Record MCP tool invocation.

    Args:
        tool_name: Name of the tool (run_untrusted_scan, get_scan_status, etc.)
        status: Status (success, error)
    """
    api_requests_total.labels(tool=tool_name, status=status).inc()


def record_scan_submission(scan_type: str, status: str = "queued"):
    """
    Record scan submission.

    Args:
        scan_type: Type of scan (untrusted, trusted)
        status: Status (queued, failed)
    """
    scans_total.labels(scan_type=scan_type, status=status).inc()


def record_scan_completion(scan_type: str, status: str):
    """
    Record scan completion.

    Args:
        scan_type: Type of scan (untrusted, trusted)
        status: Final status (completed, failed, timeout)
    """
    scans_total.labels(scan_type=scan_type, status=status).inc()


def update_active_scans_count(count: int):
    """
    Update active scans gauge.

    Args:
        count: Current number of active scans
    """
    active_scans.set(count)


def update_queue_metrics(main_depth: int, dlq_depth: int):
    """
    Update queue-related metrics.

    Args:
        main_depth: Main queue depth
        dlq_depth: Dead letter queue depth
    """
    queue_depth.labels(queue="main").set(main_depth)
    queue_depth.labels(queue="dead").set(dlq_depth)
    dlq_size.set(dlq_depth)


def update_scanner_instances_metric(scanner_type: str, enabled_count: int, disabled_count: int):
    """
    Update scanner instances gauge.

    Args:
        scanner_type: Type of scanner (nessus, openvas, etc.)
        enabled_count: Number of enabled instances
        disabled_count: Number of disabled instances
    """
    scanner_instances.labels(scanner_type=scanner_type, enabled="true").set(enabled_count)
    scanner_instances.labels(scanner_type=scanner_type, enabled="false").set(disabled_count)
