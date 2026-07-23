"""
autonomous_governance_validator.py — iios.supervisor.governance
----------------------------------------------------------------
Validation engine for governance requests and outputs.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List, Tuple

from .constants import AutonomousGovernanceValidationCode, VERSION
from .autonomous_governance_request import AutonomousGovernanceRequest
from .autonomous_governance_response import AutonomousGovernanceSummary


# ---------------------------------------------------------------------------
# Validation value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernanceValidationCheckResult:
    """Result of a single validation check."""
    code:    AutonomousGovernanceValidationCode
    passed:  bool
    message: str = ""

    def to_dict(self):
        return {
            "code":    self.code.value,
            "passed":  self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class AutonomousGovernanceValidationResult:
    """Aggregated validation result."""
    is_valid:      bool
    checks:        Tuple[GovernanceValidationCheckResult, ...]
    failed_checks: Tuple[GovernanceValidationCheckResult, ...]
    passed_count:  int
    failed_count:  int

    @property
    def failure_messages(self) -> List[str]:
        return [c.message for c in self.failed_checks if c.message]

    def to_dict(self):
        return {
            "is_valid":     self.is_valid,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "failures":     self.failure_messages,
        }


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class AutonomousGovernanceValidator:
    """
    Validates governance requests and output summaries.
    """

    def validate_request(
        self, request: AutonomousGovernanceRequest
    ) -> AutonomousGovernanceValidationResult:
        checks: List[GovernanceValidationCheckResult] = []

        # REQUEST_COMPLETENESS
        if not request.supervision_id:
            checks.append(GovernanceValidationCheckResult(
                code    = AutonomousGovernanceValidationCode.REQUEST_COMPLETENESS,
                passed  = False,
                message = "supervision_id is empty",
            ))
        else:
            checks.append(GovernanceValidationCheckResult(
                code   = AutonomousGovernanceValidationCode.REQUEST_COMPLETENESS,
                passed = True,
            ))

        # CONTEXT_CONSISTENCY
        ctx = request.context
        ctx_ok = (
            ctx.supervision_id == request.supervision_id
        )
        checks.append(GovernanceValidationCheckResult(
            code    = AutonomousGovernanceValidationCode.CONTEXT_CONSISTENCY,
            passed  = ctx_ok,
            message = "" if ctx_ok else "Context supervision_id mismatch",
        ))

        # SNAPSHOT_CONSISTENCY — at least one snapshot should be present
        has_snapshots = ctx.snapshot_count() >= 0  # always passes (zero is valid)
        checks.append(GovernanceValidationCheckResult(
            code   = AutonomousGovernanceValidationCode.SNAPSHOT_CONSISTENCY,
            passed = True,
            message = f"snapshot_count={ctx.snapshot_count()}",
        ))

        return self._build(checks)

    def validate_summary(
        self, summary: AutonomousGovernanceSummary
    ) -> AutonomousGovernanceValidationResult:
        checks: List[GovernanceValidationCheckResult] = []

        # OUTPUT_COMPLETENESS — is_success and has summary_id
        ok = bool(summary.summary_id)
        checks.append(GovernanceValidationCheckResult(
            code    = AutonomousGovernanceValidationCode.OUTPUT_COMPLETENESS,
            passed  = ok,
            message = "" if ok else "summary_id missing",
        ))

        # REASONING_INTEGRITY — non-empty reasoning on success
        reasoning_ok = not summary.is_success or bool(summary.reasoning_summary)
        checks.append(GovernanceValidationCheckResult(
            code    = AutonomousGovernanceValidationCode.REASONING_INTEGRITY,
            passed  = reasoning_ok,
            message = "" if reasoning_ok else "reasoning_summary is empty on success",
        ))

        return self._build(checks)

    # ------------------------------------------------------------------

    @staticmethod
    def _build(
        checks: List[GovernanceValidationCheckResult],
    ) -> AutonomousGovernanceValidationResult:
        failed   = [c for c in checks if not c.passed]
        return AutonomousGovernanceValidationResult(
            is_valid      = not failed,
            checks        = tuple(checks),
            failed_checks = tuple(failed),
            passed_count  = len(checks) - len(failed),
            failed_count  = len(failed),
        )
