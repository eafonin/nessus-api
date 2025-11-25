"""Core type definitions."""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional


class ScanState(Enum):
    """Valid scan states."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Valid state transitions
VALID_TRANSITIONS: Dict[ScanState, set[ScanState]] = {
    ScanState.QUEUED: {ScanState.RUNNING, ScanState.FAILED},
    ScanState.RUNNING: {ScanState.RUNNING, ScanState.COMPLETED, ScanState.FAILED, ScanState.TIMEOUT},  # Allow RUNNING→RUNNING for metadata updates
    ScanState.COMPLETED: set(),  # Terminal state
    ScanState.FAILED: set(),     # Terminal state
    ScanState.TIMEOUT: set(),    # Terminal state
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
    payload: Dict[str, Any]
    created_at: str
    scanner_pool: Optional[str] = None  # Pool name (e.g., "nessus", "nessus_dmz")
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    nessus_scan_id: Optional[int] = None
    error_message: Optional[str] = None
