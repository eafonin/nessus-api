"""Core type definitions."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ScanState(Enum):
    """Valid scan states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Valid state transitions
VALID_TRANSITIONS: dict[ScanState, set[ScanState]] = {
    ScanState.QUEUED: {ScanState.RUNNING, ScanState.FAILED},
    ScanState.RUNNING: {
        ScanState.RUNNING,
        ScanState.COMPLETED,
        ScanState.FAILED,
        ScanState.TIMEOUT,
    },  # Allow RUNNING→RUNNING for metadata updates
    ScanState.COMPLETED: set(),  # Terminal state
    ScanState.FAILED: set(),  # Terminal state
    ScanState.TIMEOUT: set(),  # Terminal state
}


class StateTransitionError(Exception):
    """Raised when invalid state transition is attempted."""

    pass


@dataclass
class Task:
    """Task representation."""

    task_id: str
    trace_id: str
    scan_type: str
    scanner_type: str
    scanner_instance_id: str
    status: str
    payload: dict[str, Any]
    created_at: str
    scanner_pool: str | None = None  # Pool name (e.g., "nessus", "nessus_dmz")
    started_at: str | None = None
    completed_at: str | None = None
    nessus_scan_id: int | None = None
    error_message: str | None = None
    # Phase 4: Validation results
    validation_stats: dict[str, Any] | None = None
    validation_warnings: list[str] | None = None
    authentication_status: str | None = (
        None  # "success"|"failed"|"partial"|"not_applicable"
    )
