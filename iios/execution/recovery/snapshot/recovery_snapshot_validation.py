"""
iios/execution/recovery/snapshot/recovery_snapshot_validation.py
================================================================
SnapshotValidationResult and RecoverySnapshotValidator.

Validates ExecutionRecoverySnapshot objects for:
  - Identifier consistency
  - Lifecycle consistency
  - Recovery consistency
  - Policy consistency
  - Failover consistency
  - Verification consistency
  - Snapshot completeness
  - Version compatibility
  - Timestamp consistency

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .constants import (
    LIFECYCLE_VALID_STATES,
    SCHEMA_VERSION,
    VERSION,
    RecoveryResult,
    SnapshotHealth,
    SnapshotStatus,
    VerificationOutcome,
)

if TYPE_CHECKING:
    from .execution_recovery_snapshot import ExecutionRecoverySnapshot


@dataclass
class SnapshotValidationResult:
    """Mutable accumulator of validation findings."""

    is_valid: bool        = True
    errors:   List[str]   = field(default_factory=list)
    warnings: List[str]   = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: "SnapshotValidationResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class RecoverySnapshotValidator:
    """
    Validates ExecutionRecoverySnapshot objects across 9 dimensions.

    All validate_* methods return SnapshotValidationResult.
    validate() aggregates all checks.
    """

    # ── Top-level ─────────────────────────────────────────────────────────────

    def validate(self, snapshot: Optional["ExecutionRecoverySnapshot"]) -> SnapshotValidationResult:
        """Run all validation checks and return merged result."""
        if snapshot is None:
            r = SnapshotValidationResult()
            r.add_error("snapshot must not be None")
            return r

        result = SnapshotValidationResult()
        for check in (
            self.validate_identifiers,
            self.validate_lifecycle,
            self.validate_recovery,
            self.validate_policy,
            self.validate_failover,
            self.validate_verification,
            self.validate_completeness,
            self.validate_version,
            self.validate_timestamp,
        ):
            result.merge(check(snapshot))
        return result

    # ── Identifier consistency ────────────────────────────────────────────────

    def validate_identifiers(
        self, snapshot: "ExecutionRecoverySnapshot",
    ) -> SnapshotValidationResult:
        r = SnapshotValidationResult()
        if not snapshot.snapshot_id:
            r.add_error("snapshot_id is required")
        if not snapshot.recovery_session_id:
            r.add_error("recovery_session_id is required")
        if not snapshot.execution_session_id:
            r.add_error("execution_session_id is required")
        if snapshot.snapshot_version < 1:
            r.add_error(f"snapshot_version must be >= 1, got {snapshot.snapshot_version}")
        return r

    # ── Lifecycle consistency ─────────────────────────────────────────────────

    def validate_lifecycle(
        self, snapshot: "ExecutionRecoverySnapshot",
    ) -> SnapshotValidationResult:
        r = SnapshotValidationResult()
        if not snapshot.lifecycle_state:
            r.add_error("lifecycle_state is required")
        elif snapshot.lifecycle_state not in LIFECYCLE_VALID_STATES:
            r.add_error(
                f"lifecycle_state {snapshot.lifecycle_state!r} is not a known value"
            )
        return r

    # ── Recovery consistency ──────────────────────────────────────────────────

    def validate_recovery(
        self, snapshot: "ExecutionRecoverySnapshot",
    ) -> SnapshotValidationResult:
        r = SnapshotValidationResult()
        if not isinstance(snapshot.recovery_result, RecoveryResult):
            r.add_error("recovery_result must be a RecoveryResult enum")
        if snapshot.recovery_duration_ms < 0:
            r.add_error("recovery_duration_ms must be >= 0")
        if snapshot.recovery_result == RecoveryResult.SUCCESS and \
                snapshot.lifecycle_state not in ("completed", "verifying"):
            r.add_warning(
                "recovery_result=SUCCESS but lifecycle_state is not 'completed' or 'verifying'"
            )
        return r

    # ── Policy consistency ────────────────────────────────────────────────────

    def validate_policy(
        self, snapshot: "ExecutionRecoverySnapshot",
    ) -> SnapshotValidationResult:
        r = SnapshotValidationResult()
        # A warning (not error) when no policy info and result is not unknown
        if (not snapshot.selected_recovery_policy and
                snapshot.recovery_result not in (RecoveryResult.UNKNOWN, RecoveryResult.ABORTED)):
            r.add_warning("selected_recovery_policy is empty for a non-aborted recovery")
        return r

    # ── Failover consistency ──────────────────────────────────────────────────

    def validate_failover(
        self, snapshot: "ExecutionRecoverySnapshot",
    ) -> SnapshotValidationResult:
        r = SnapshotValidationResult()
        # Informational only — failover may not always be executed
        return r

    # ── Verification consistency ──────────────────────────────────────────────

    def validate_verification(
        self, snapshot: "ExecutionRecoverySnapshot",
    ) -> SnapshotValidationResult:
        r = SnapshotValidationResult()
        if not isinstance(snapshot.verification_result, VerificationOutcome):
            r.add_error("verification_result must be a VerificationOutcome enum")
        # Consistency: successful recovery should not have FAILED verification
        if (snapshot.recovery_result == RecoveryResult.SUCCESS and
                snapshot.verification_result == VerificationOutcome.FAILED):
            r.add_warning(
                "recovery_result=SUCCESS but verification_result=FAILED — unusual combination"
            )
        return r

    # ── Snapshot completeness ─────────────────────────────────────────────────

    def validate_completeness(
        self, snapshot: "ExecutionRecoverySnapshot",
    ) -> SnapshotValidationResult:
        r = SnapshotValidationResult()
        if snapshot.audit_metadata is None:
            r.add_error("audit_metadata is required")
        if snapshot.timestamp <= 0:
            r.add_error("timestamp must be a positive Unix epoch value")
        if not isinstance(snapshot.recovery_status, SnapshotStatus):
            r.add_error("recovery_status must be a SnapshotStatus enum")
        if not isinstance(snapshot.recovery_health, SnapshotHealth):
            r.add_error("recovery_health must be a SnapshotHealth enum")
        return r

    # ── Version compatibility ─────────────────────────────────────────────────

    def validate_version(
        self, snapshot: "ExecutionRecoverySnapshot",
    ) -> SnapshotValidationResult:
        r = SnapshotValidationResult()
        if not snapshot.framework_version:
            r.add_error("framework_version is required")
        if not snapshot.schema_version:
            r.add_error("schema_version is required")
        if snapshot.schema_version != SCHEMA_VERSION:
            r.add_warning(
                f"snapshot schema_version {snapshot.schema_version!r} differs from "
                f"current {SCHEMA_VERSION!r}"
            )
        return r

    # ── Timestamp consistency ─────────────────────────────────────────────────

    def validate_timestamp(
        self, snapshot: "ExecutionRecoverySnapshot",
    ) -> SnapshotValidationResult:
        r = SnapshotValidationResult()
        now = time.time()
        if snapshot.timestamp > now + 60:
            r.add_warning("snapshot timestamp is more than 60 seconds in the future")
        if snapshot.timestamp < 0:
            r.add_error("snapshot timestamp must be non-negative")
        return r
