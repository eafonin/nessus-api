"""Task manager with state machine enforcement (single writer pattern)."""

import fcntl
import json
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional, Set


class ScanState(Enum):
    """Valid scan states."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Valid state transitions
VALID_TRANSITIONS: Dict[ScanState, Set[ScanState]] = {
    ScanState.QUEUED: {ScanState.RUNNING, ScanState.FAILED},
    ScanState.RUNNING: {ScanState.COMPLETED, ScanState.FAILED, ScanState.TIMEOUT},
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
    payload: Dict[str, Any]


class TaskManager:
    """Manages task state with file locking for atomic updates."""

    def __init__(self, data_dir: str = "data/tasks"):
        self.data_dir = data_dir

    async def create_task(self, task: Task) -> str:
        """Create new task and persist to disk."""
        # TODO: Implement task creation
        pass

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task metadata."""
        # TODO: Implement task retrieval
        pass

    async def transition_state(
        self,
        task_id: str,
        new_state: ScanState,
        trace_id: str,
        **metadata
    ) -> None:
        """Transition task to new state with validation and file locking."""
        # TODO: Implement state transition with fcntl locking
        # 1. Open task.json
        # 2. Acquire exclusive lock (fcntl.LOCK_EX)
        # 3. Read current state
        # 4. Validate transition
        # 5. Update state and metadata
        # 6. Write back to file
        # 7. Release lock
        pass

    async def delete_task(self, task_id: str) -> bool:
        """Delete task and all associated data."""
        # TODO: Implement task deletion
        pass
