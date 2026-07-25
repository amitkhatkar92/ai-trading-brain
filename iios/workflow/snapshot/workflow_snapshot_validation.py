"""
workflow_snapshot_validation.py — iios.workflow.snapshot
---------------------------------------------------------
WorkflowSnapshotValidation — validates snapshot integrity and completeness.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from iios.common.logging.logging_manager import get_logger

from .exceptions import WorkflowSnapshotValidationError
from .workflow_snapshot import WorkflowSnapshot

_log = get_logger(__name__)


@dataclass(frozen=True)
class SnapshotValidationResult:
    """Result of validating a single snapshot."""
    snapshot_id: str
    valid:       bool
    issues:      tuple    # Tuple[str, ...]

    @property
    def issue_list(self) -> List[str]:
        return list(self.issues)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "valid":       self.valid,
            "issues":      self.issue_list,
        }


class WorkflowSnapshotValidation:
    """
    Validates WorkflowSnapshot objects for completeness and consistency.

    Thread-safe — stateless.
    """

    def validate(self, snapshot: WorkflowSnapshot) -> SnapshotValidationResult:
        """
        Validate a snapshot.

        Returns:
            SnapshotValidationResult with outcome and issues list.
        """
        issues: List[str] = []

        # 1. Required identifiers
        if not snapshot.snapshot_id:
            issues.append("snapshot_id is empty")
        if not snapshot.workflow_id:
            issues.append("workflow_id is empty")
        if not snapshot.workflow_name:
            issues.append("workflow_name is empty")
        if not snapshot.snapshot_version:
            issues.append("snapshot_version is empty")

        # 2. Timestamp consistency
        if not snapshot.snapshot_timestamp:
            issues.append("snapshot_timestamp is missing")
        if not snapshot.created_at:
            issues.append("created_at is missing")

        # 3. Progress consistency
        if not (0.0 <= snapshot.execution_progress <= 1.0):
            issues.append(
                f"execution_progress={snapshot.execution_progress} out of range [0, 1]"
            )
        if snapshot.total_steps > 0 and snapshot.completed_steps > snapshot.total_steps:
            issues.append(
                f"completed_steps={snapshot.completed_steps} > total_steps={snapshot.total_steps}"
            )

        # 4. Counter non-negativity
        for field_name in ("retry_count", "timeout_count", "compensation_count", "checkpoint_count"):
            val = getattr(snapshot, field_name)
            if val < 0:
                issues.append(f"{field_name}={val} must be >= 0")

        # 5. Metadata present
        if snapshot.metadata is None:
            issues.append("metadata is missing")

        valid = len(issues) == 0
        result = SnapshotValidationResult(
            snapshot_id = snapshot.snapshot_id,
            valid       = valid,
            issues      = tuple(issues),
        )
        if not valid:
            _log.warning(
                f"Validation: snapshot={snapshot.snapshot_id!r} "
                f"failed with {len(issues)} issue(s)"
            )
        return result

    def validate_or_raise(self, snapshot: WorkflowSnapshot) -> None:
        """Validate and raise WorkflowSnapshotValidationError if invalid."""
        result = self.validate(snapshot)
        if not result.valid:
            raise WorkflowSnapshotValidationError(
                f"Snapshot {snapshot.snapshot_id!r} is invalid",
                issues=result.issue_list,
            )
