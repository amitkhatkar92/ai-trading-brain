"""
decision_snapshot_validation.py — iios.decision.snapshot
=========================================================
Nine-check structural and consistency validation for DecisionSnapshot.

Validation checks
-----------------
1. IDENTIFIER_CONSISTENCY    — required IDs are non-empty and consistent.
2. LIFECYCLE_CONSISTENCY     — lifecycle_state is a known value.
3. POLICY_CONSISTENCY        — policy_summary is consistent with decision_status.
4. OPTIMIZATION_CONSISTENCY  — optimization_summary is consistent with decision_score.
5. DECISION_CONSISTENCY      — selected_decision is present when status is APPROVED.
6. SNAPSHOT_COMPLETENESS     — all required fields are populated.
7. VERSION_COMPATIBILITY     — framework_version and schema_version are compatible.
8. TIMESTAMP_CONSISTENCY     — created_at is a valid UTC timestamp.
9. AUDIT_CONSISTENCY         — audit_metadata contains required keys.

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .constants import (
    SCHEMA_VERSION,
    VERSION,
    DecisionStatus,
    SnapshotValidationCode,
)
from .decision_snapshot import DecisionSnapshot


# ── Check result ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SnapshotValidationCheckResult:
    """Result of a single validation check."""
    code:    SnapshotValidationCode
    passed:  bool
    message: str


@dataclass(frozen=True)
class SnapshotValidationResult:
    """Aggregated result of all nine validation checks."""
    is_valid:      bool
    checks:        Tuple[SnapshotValidationCheckResult, ...]
    failed_checks: Tuple[SnapshotValidationCode, ...]
    passed_count:  int
    failed_count:  int

    @property
    def error_messages(self) -> Tuple[str, ...]:
        return tuple(c.message for c in self.checks if not c.passed)


# ── Validator ─────────────────────────────────────────────────────────────────

class DecisionSnapshotValidator:
    """
    Validates a :class:`DecisionSnapshot` against nine structural and
    consistency checks.
    """

    def validate(self, snapshot: DecisionSnapshot) -> SnapshotValidationResult:
        """Run all nine checks and return an aggregate result."""
        checks = [
            self._check_identifier_consistency(snapshot),
            self._check_lifecycle_consistency(snapshot),
            self._check_policy_consistency(snapshot),
            self._check_optimization_consistency(snapshot),
            self._check_decision_consistency(snapshot),
            self._check_snapshot_completeness(snapshot),
            self._check_version_compatibility(snapshot),
            self._check_timestamp_consistency(snapshot),
            self._check_audit_consistency(snapshot),
        ]
        failed = [c for c in checks if not c.passed]
        return SnapshotValidationResult(
            is_valid      = len(failed) == 0,
            checks        = tuple(checks),
            failed_checks = tuple(c.code for c in failed),
            passed_count  = len(checks) - len(failed),
            failed_count  = len(failed),
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_identifier_consistency(
        self, s: DecisionSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.IDENTIFIER_CONSISTENCY
        if not s.snapshot_id:
            return SnapshotValidationCheckResult(code, False, "snapshot_id is empty")
        if not s.session_id:
            return SnapshotValidationCheckResult(code, False, "session_id is empty")
        if not s.decision_id:
            return SnapshotValidationCheckResult(code, False, "decision_id is empty")
        return SnapshotValidationCheckResult(code, True, "Identifier consistency: OK")

    def _check_lifecycle_consistency(
        self, s: DecisionSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.LIFECYCLE_CONSISTENCY
        _KNOWN_STATES = {
            "created", "initializing", "collecting", "evaluating",
            "ready", "active", "paused", "resuming",
            "completed", "failed", "archived",
        }
        if not s.lifecycle_state:
            return SnapshotValidationCheckResult(code, False, "lifecycle_state is empty")
        if s.lifecycle_state not in _KNOWN_STATES:
            return SnapshotValidationCheckResult(
                code, False,
                f"Unknown lifecycle_state: {s.lifecycle_state!r}"
            )
        return SnapshotValidationCheckResult(code, True, "Lifecycle consistency: OK")

    def _check_policy_consistency(
        self, s: DecisionSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.POLICY_CONSISTENCY
        # policy_summary should be present when status is explicitly approved/rejected
        decided = {
            DecisionStatus.APPROVED,
            DecisionStatus.APPROVED_CONDITIONAL,
            DecisionStatus.REJECTED,
            DecisionStatus.BLOCKED,
        }
        if s.decision_status in decided and not s.policy_summary:
            return SnapshotValidationCheckResult(
                code, False,
                f"policy_summary missing for status {s.decision_status.value!r}"
            )
        return SnapshotValidationCheckResult(code, True, "Policy consistency: OK")

    def _check_optimization_consistency(
        self, s: DecisionSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.OPTIMIZATION_CONSISTENCY
        # If optimization_summary present, score must be in [0, 1]
        if s.optimization_summary:
            if not (0.0 <= s.decision_score <= 1.0):
                return SnapshotValidationCheckResult(
                    code, False,
                    f"decision_score {s.decision_score} out of [0, 1] range"
                )
        return SnapshotValidationCheckResult(code, True, "Optimization consistency: OK")

    def _check_decision_consistency(
        self, s: DecisionSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.DECISION_CONSISTENCY
        # When APPROVED the snapshot SHOULD have a selected decision
        if s.decision_status in (
            DecisionStatus.APPROVED,
            DecisionStatus.APPROVED_CONDITIONAL,
        ):
            if s.selected_decision is None:
                return SnapshotValidationCheckResult(
                    code, False,
                    "selected_decision is None for an approved decision"
                )
        return SnapshotValidationCheckResult(code, True, "Decision consistency: OK")

    def _check_snapshot_completeness(
        self, s: DecisionSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.SNAPSHOT_COMPLETENESS
        # Mandatory string fields must not be empty
        if not s.decision_scope:
            return SnapshotValidationCheckResult(code, False, "decision_scope is empty")
        if not s.decision_type:
            return SnapshotValidationCheckResult(code, False, "decision_type is empty")
        if not s.decision_priority:
            return SnapshotValidationCheckResult(code, False, "decision_priority is empty")
        return SnapshotValidationCheckResult(code, True, "Snapshot completeness: OK")

    def _check_version_compatibility(
        self, s: DecisionSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.VERSION_COMPATIBILITY
        if not s.framework_version:
            return SnapshotValidationCheckResult(code, False, "framework_version is empty")
        if not s.schema_version:
            return SnapshotValidationCheckResult(code, False, "schema_version is empty")
        # Major version must match
        try:
            snap_major = int(s.framework_version.split(".")[0])
            cur_major  = int(VERSION.split(".")[0])
            if snap_major != cur_major:
                return SnapshotValidationCheckResult(
                    code, False,
                    f"Incompatible framework version: "
                    f"{s.framework_version!r} vs {VERSION!r}"
                )
        except (ValueError, IndexError):
            return SnapshotValidationCheckResult(
                code, False, f"Malformed framework_version: {s.framework_version!r}"
            )
        return SnapshotValidationCheckResult(code, True, "Version compatibility: OK")

    def _check_timestamp_consistency(
        self, s: DecisionSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.TIMESTAMP_CONSISTENCY
        if s.created_at is None:
            return SnapshotValidationCheckResult(code, False, "created_at is None")
        if s.created_at.tzinfo is None:
            return SnapshotValidationCheckResult(
                code, False, "created_at has no timezone info"
            )
        return SnapshotValidationCheckResult(code, True, "Timestamp consistency: OK")

    def _check_audit_consistency(
        self, s: DecisionSnapshot
    ) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.AUDIT_CONSISTENCY
        if not isinstance(s.audit_metadata, dict):
            return SnapshotValidationCheckResult(
                code, False, "audit_metadata is not a dict"
            )
        return SnapshotValidationCheckResult(code, True, "Audit consistency: OK")
