"""iios/execution/snapshot/execution_snapshot_validator.py
==================================================
ExecutionSnapshotValidator — stateless validator for snapshot
completeness, consistency, and lifecycle rules.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from iios.execution.snapshot.constants import SnapshotLifecycle, SnapshotValidationCode
from iios.execution.snapshot.execution_snapshot import ExecutionSnapshot
from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__, engine_id="iios:execution:snapshot:validator")

# Terminal states accepted for succeeded=True check
_TERMINAL_STATES = frozenset({"COMPLETED", "FAILED", "CANCELLED"})


@dataclass(frozen=True)
class SnapshotValidationResult:
    """Outcome of a snapshot validation pass."""

    passed:   bool
    errors:   tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def ok(cls, *, warnings: tuple[str, ...] = ()) -> "SnapshotValidationResult":
        return cls(passed=True, errors=(), warnings=warnings)

    @classmethod
    def fail(cls, *errors: str) -> "SnapshotValidationResult":
        return cls(passed=False, errors=errors)

    def __bool__(self) -> bool:
        return self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed":   self.passed,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class ExecutionSnapshotValidator:
    """
    Stateless validator for ExecutionSnapshot objects.

    Thread-safe (no mutable state).
    """

    def validate(self, snap: ExecutionSnapshot) -> SnapshotValidationResult:
        """
        Full validation of a snapshot.

        Checks: required IDs, version, state consistency, result
        consistency, lifecycle consistency.
        """
        errors:   list[str] = []
        warnings: list[str] = []

        self._check_required_ids(snap, errors)
        self._check_version(snap, errors)
        self._check_state_consistency(snap, errors)
        self._check_result_consistency(snap, errors, warnings)
        self._check_lifecycle(snap, errors, warnings)

        if errors:
            return SnapshotValidationResult.fail(*errors)
        return SnapshotValidationResult.ok(warnings=tuple(warnings))

    # ── Per-field checks ──────────────────────────────────────────────────────

    def _check_required_ids(
        self,
        snap:   ExecutionSnapshot,
        errors: list[str],
    ) -> None:
        if not snap.snapshot_id:
            errors.append(
                f"[{SnapshotValidationCode.MISSING_SNAPSHOT_ID.value}] "
                "snapshot_id must not be empty"
            )
        if not snap.execution_id:
            errors.append(
                f"[{SnapshotValidationCode.MISSING_EXECUTION_ID.value}] "
                "execution_id must not be empty"
            )
        if not snap.workflow_id:
            errors.append(
                f"[{SnapshotValidationCode.MISSING_WORKFLOW_ID.value}] "
                "workflow_id must not be empty"
            )
        if not snap.order_id:
            errors.append(
                f"[{SnapshotValidationCode.MISSING_ORDER_ID.value}] "
                "order_id must not be empty"
            )
        if snap.captured_at <= 0.0:
            errors.append(
                f"[{SnapshotValidationCode.MISSING_TIMESTAMP.value}] "
                "captured_at must be a positive Unix timestamp"
            )

    def _check_version(
        self,
        snap:   ExecutionSnapshot,
        errors: list[str],
    ) -> None:
        if snap.version < 1:
            errors.append(
                f"[{SnapshotValidationCode.INVALID_VERSION.value}] "
                "version must be >= 1"
            )
        if not snap.schema_version:
            errors.append(
                f"[{SnapshotValidationCode.INVALID_VERSION.value}] "
                "schema_version must not be empty"
            )

    def _check_state_consistency(
        self,
        snap:   ExecutionSnapshot,
        errors: list[str],
    ) -> None:
        if not snap.execution_state:
            errors.append(
                f"[{SnapshotValidationCode.INVALID_STATE.value}] "
                "execution_state must not be empty"
            )
        # is_terminal must be consistent with execution_state
        if snap.execution_state in _TERMINAL_STATES and not snap.is_terminal:
            errors.append(
                f"[{SnapshotValidationCode.INVALID_STATE.value}] "
                f"execution_state '{snap.execution_state}' is terminal "
                "but is_terminal=False"
            )
        if snap.execution_state not in _TERMINAL_STATES and snap.is_terminal:
            errors.append(
                f"[{SnapshotValidationCode.INVALID_STATE.value}] "
                f"execution_state '{snap.execution_state}' is non-terminal "
                "but is_terminal=True"
            )

    def _check_result_consistency(
        self,
        snap:     ExecutionSnapshot,
        errors:   list[str],
        warnings: list[str],
    ) -> None:
        # succeeded=True implies COMPLETED and no error
        if snap.succeeded and snap.execution_state != "COMPLETED":
            errors.append(
                f"[{SnapshotValidationCode.RESULT_MISMATCH.value}] "
                "succeeded=True but execution_state is not COMPLETED"
            )
        if snap.succeeded and snap.error_message:
            errors.append(
                f"[{SnapshotValidationCode.RESULT_MISMATCH.value}] "
                "succeeded=True but error_message is non-empty"
            )
        # No result_id on terminal snapshots is a warning
        if snap.is_terminal and not snap.result_id:
            warnings.append(
                f"[{SnapshotValidationCode.INCOMPLETE_SNAPSHOT.value}] "
                "Terminal snapshot has no result_id"
            )

    def _check_lifecycle(
        self,
        snap:     ExecutionSnapshot,
        errors:   list[str],
        warnings: list[str],
    ) -> None:
        # PUBLISHED snapshots must have a valid trigger in audit_metadata
        if (
            snap.lifecycle in (SnapshotLifecycle.PUBLISHED, SnapshotLifecycle.STORED)
            and snap.audit_metadata is None
        ):
            warnings.append(
                f"[{SnapshotValidationCode.LIFECYCLE_INVALID.value}] "
                f"Snapshot with lifecycle={snap.lifecycle.value} has no audit_metadata"
            )
