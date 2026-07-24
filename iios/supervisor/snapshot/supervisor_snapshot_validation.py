"""
supervisor_snapshot_validation.py — iios.supervisor.snapshot
-------------------------------------------------------------
Snapshot integrity validation.

Seven validation checks:
  1. IDENTIFIER_CONSISTENCY  — IDs are non-empty
  2. VERSION_CONSISTENCY     — version fields present
  3. GOVERNANCE_CONSISTENCY  — governance decision present
  4. ENTERPRISE_CONSISTENCY  — health in [0,1], valid enterprise state
  5. RECOMMENDATION_CONSISTENCY — self-healing counts non-negative
  6. SNAPSHOT_COMPLETENESS   — timestamps valid
  7. METADATA_INTEGRITY      — metadata_id and environment present

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .constants import SnapshotValidationCode
from .supervisor_snapshot import SupervisorSnapshot


@dataclass(frozen=True)
class SnapshotValidationCheckResult:
    """Result of a single validation check."""
    code:    SnapshotValidationCode
    passed:  bool
    message: str           = ""
    detail:  Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SupervisorSnapshotValidationResult:
    """Aggregated validation result for a snapshot."""
    is_valid:      bool
    checks:        Tuple[SnapshotValidationCheckResult, ...]
    failed_checks: Tuple[SnapshotValidationCheckResult, ...]
    passed_count:  int
    failed_count:  int

    @property
    def failure_messages(self) -> List[str]:
        return [c.message for c in self.failed_checks if c.message]


class SupervisorSnapshotValidator:
    """Validates SupervisorSnapshot integrity across seven dimensions."""

    def validate(self, snapshot: SupervisorSnapshot) -> SupervisorSnapshotValidationResult:
        """Run all validation checks against a snapshot."""
        checks: List[SnapshotValidationCheckResult] = [
            self._check_identifier_consistency(snapshot),
            self._check_version_consistency(snapshot),
            self._check_governance_consistency(snapshot),
            self._check_enterprise_consistency(snapshot),
            self._check_recommendation_consistency(snapshot),
            self._check_snapshot_completeness(snapshot),
            self._check_metadata_integrity(snapshot),
        ]
        failed = [c for c in checks if not c.passed]
        return SupervisorSnapshotValidationResult(
            is_valid      = len(failed) == 0,
            checks        = tuple(checks),
            failed_checks = tuple(failed),
            passed_count  = len(checks) - len(failed),
            failed_count  = len(failed),
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_identifier_consistency(self, s: SupervisorSnapshot) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.IDENTIFIER_CONSISTENCY
        if not s.snapshot_id:
            return SnapshotValidationCheckResult(code, False, "snapshot_id is empty")
        if not s.supervisor_session_id:
            return SnapshotValidationCheckResult(code, False, "supervisor_session_id is empty")
        if not s.supervisor_workflow_id:
            return SnapshotValidationCheckResult(code, False, "supervisor_workflow_id is empty")
        return SnapshotValidationCheckResult(code, True)

    def _check_version_consistency(self, s: SupervisorSnapshot) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.VERSION_CONSISTENCY
        if not s.framework_version:
            return SnapshotValidationCheckResult(code, False, "framework_version is empty")
        if not s.platform_version:
            return SnapshotValidationCheckResult(code, False, "platform_version is empty")
        if not s.metadata.schema_version:
            return SnapshotValidationCheckResult(code, False, "metadata.schema_version is empty")
        return SnapshotValidationCheckResult(code, True)

    def _check_governance_consistency(self, s: SupervisorSnapshot) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.GOVERNANCE_CONSISTENCY
        if not s.governance_summary.governance_decision:
            return SnapshotValidationCheckResult(code, False, "governance_decision is empty")
        return SnapshotValidationCheckResult(code, True)

    def _check_enterprise_consistency(self, s: SupervisorSnapshot) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.ENTERPRISE_CONSISTENCY
        h = s.enterprise_summary.enterprise_health
        if not (0.0 <= h <= 1.0):
            return SnapshotValidationCheckResult(
                code, False, f"enterprise_health out of [0,1]: {h}"
            )
        valid_states = {"optimal", "normal", "degraded", "critical", "emergency", "unknown"}
        if s.enterprise_state.value not in valid_states:
            return SnapshotValidationCheckResult(code, False, "invalid enterprise_state value")
        return SnapshotValidationCheckResult(code, True)

    def _check_recommendation_consistency(self, s: SupervisorSnapshot) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.RECOMMENDATION_CONSISTENCY
        sh = s.self_healing_summary
        if sh.recommended_actions < 0:
            return SnapshotValidationCheckResult(code, False, "recommended_actions is negative")
        if sh.recovery_plans < 0:
            return SnapshotValidationCheckResult(code, False, "recovery_plans is negative")
        return SnapshotValidationCheckResult(code, True)

    def _check_snapshot_completeness(self, s: SupervisorSnapshot) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.SNAPSHOT_COMPLETENESS
        if s.snapshot_timestamp <= 0.0:
            return SnapshotValidationCheckResult(code, False, "snapshot_timestamp is zero/negative")
        if s.created_at <= 0.0:
            return SnapshotValidationCheckResult(code, False, "created_at is zero/negative")
        return SnapshotValidationCheckResult(code, True)

    def _check_metadata_integrity(self, s: SupervisorSnapshot) -> SnapshotValidationCheckResult:
        code = SnapshotValidationCode.METADATA_INTEGRITY
        if not s.metadata.metadata_id:
            return SnapshotValidationCheckResult(code, False, "metadata_id is empty")
        if not s.metadata.environment:
            return SnapshotValidationCheckResult(code, False, "environment is empty")
        return SnapshotValidationCheckResult(code, True)
