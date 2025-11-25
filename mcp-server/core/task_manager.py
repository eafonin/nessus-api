"""Task manager with file-based storage."""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from .types import Task, ScanState, VALID_TRANSITIONS, StateTransitionError


def generate_task_id(scanner_type: str, instance_id: str) -> str:
    """Generate unique task ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_suffix = uuid.uuid4().hex[:8]
    type_prefix = scanner_type[:2].lower()
    instance_prefix = instance_id[:4].lower()
    return f"{type_prefix}_{instance_prefix}_{timestamp}_{random_suffix}"


class TaskManager:
    """Manages task lifecycle with file-based storage."""

    def __init__(self, data_dir: str = "/app/data/tasks"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def create_task(self, task: Task) -> None:
        """Create new task directory and metadata file."""
        task_dir = self.data_dir / task.task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        task_file = task_dir / "task.json"
        with open(task_file, "w") as f:
            json.dump(self._task_to_dict(task), f, indent=2)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task metadata."""
        task_file = self.data_dir / task_id / "task.json"
        if not task_file.exists():
            return None

        with open(task_file) as f:
            data = json.load(f)

        return Task(**data)

    def update_status(
        self,
        task_id: str,
        new_state: ScanState,
        **metadata
    ) -> None:
        """Update task status with state machine validation."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        current_state = ScanState(task.status)

        # Validate transition
        if new_state not in VALID_TRANSITIONS.get(current_state, set()):
            raise StateTransitionError(
                f"Invalid transition: {current_state.value} → {new_state.value}"
            )

        # Update timestamps
        if new_state == ScanState.RUNNING:
            task.started_at = datetime.utcnow().isoformat()
        elif new_state in {ScanState.COMPLETED, ScanState.FAILED, ScanState.TIMEOUT}:
            task.completed_at = datetime.utcnow().isoformat()

        task.status = new_state.value

        # Update additional metadata
        for key, value in metadata.items():
            if hasattr(task, key):
                setattr(task, key, value)

        # Write back
        task_file = self.data_dir / task_id / "task.json"
        with open(task_file, "w") as f:
            json.dump(self._task_to_dict(task), f, indent=2)

    @staticmethod
    def _task_to_dict(task: Task) -> dict:
        """Convert Task to dict for JSON serialization."""
        return {
            "task_id": task.task_id,
            "trace_id": task.trace_id,
            "scan_type": task.scan_type,
            "scanner_type": task.scanner_type,
            "scanner_instance_id": task.scanner_instance_id,
            "status": task.status,
            "payload": task.payload,
            "created_at": task.created_at,
            "scanner_pool": task.scanner_pool,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "nessus_scan_id": task.nessus_scan_id,
            "error_message": task.error_message,
            # Phase 4: Validation fields
            "validation_stats": task.validation_stats,
            "validation_warnings": task.validation_warnings,
            "authentication_status": task.authentication_status,
        }

    def mark_completed_with_validation(
        self,
        task_id: str,
        validation_stats: dict = None,
        validation_warnings: list = None,
        authentication_status: str = None
    ) -> None:
        """
        Mark task as completed with validation results.

        Args:
            task_id: Task ID
            validation_stats: Dict with hosts_scanned, vuln_counts, etc.
            validation_warnings: List of warning messages
            authentication_status: "success"|"failed"|"partial"|"not_applicable"
        """
        self.update_status(
            task_id,
            ScanState.COMPLETED,
            validation_stats=validation_stats,
            validation_warnings=validation_warnings,
            authentication_status=authentication_status
        )

    def mark_failed_with_validation(
        self,
        task_id: str,
        error_message: str,
        validation_stats: dict = None,
        authentication_status: str = None
    ) -> None:
        """
        Mark task as failed with validation context.

        Useful for auth failures where we have partial results.

        Args:
            task_id: Task ID
            error_message: Error description
            validation_stats: Dict with partial results info
            authentication_status: "success"|"failed"|"partial"|"not_applicable"
        """
        self.update_status(
            task_id,
            ScanState.FAILED,
            error_message=error_message,
            validation_stats=validation_stats,
            authentication_status=authentication_status
        )
