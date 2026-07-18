"""
iios/execution/recovery/failover/failover_response.py
=====================================================
FailoverResponse, FailoverResult, VerificationReport, VerificationCheck,
and FailoverExecutionStep — outputs from the Failover Framework.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    VERSION,
    FailoverAction,
    FailoverPhase,
    FailoverStatus,
    FailoverType,
    NON_OPERATIONAL_ACTIONS,
    VerificationStatus,
)


# ── Verification types ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class VerificationCheck:
    """Single post-failover verification check."""

    check_name:  str
    status:      VerificationStatus
    message:     str
    checked_at:  float = field(default_factory=time.time)

    @property
    def passed(self) -> bool:
        return self.status == VerificationStatus.PASSED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_name": self.check_name,
            "status":     self.status.value,
            "message":    self.message,
            "checked_at": self.checked_at,
        }


@dataclass(frozen=True)
class VerificationReport:
    """Complete post-failover verification report."""

    report_id:           str
    failover_session_id: str
    checks:              Tuple[VerificationCheck, ...]
    overall_status:      VerificationStatus
    passed_checks:       int
    failed_checks:       int
    skipped_checks:      int
    verified_at:         float
    version:             str  = VERSION

    @property
    def is_verified(self) -> bool:
        return self.overall_status == VerificationStatus.PASSED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":           self.report_id,
            "failover_session_id": self.failover_session_id,
            "checks":              [c.to_dict() for c in self.checks],
            "overall_status":      self.overall_status.value,
            "passed_checks":       self.passed_checks,
            "failed_checks":       self.failed_checks,
            "skipped_checks":      self.skipped_checks,
            "verified_at":         self.verified_at,
        }


# ── Execution step ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FailoverExecutionStep:
    """Record of a single phase/action during failover execution."""

    step_id:     str
    phase:       FailoverPhase
    action:      FailoverAction
    status:      FailoverStatus
    message:     str
    started_at:  float
    completed_at: float
    duration_ms:  float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id":     self.step_id,
            "phase":       self.phase.value,
            "action":      self.action.value,
            "status":      self.status.value,
            "message":     self.message,
            "duration_ms": self.duration_ms,
        }


# ── Failover result ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FailoverResult:
    """Outcome of the failover execution (produced by FailoverExecutor)."""

    result_id:           str
    request_id:          str
    failover_session_id: str
    failover_type:       FailoverType
    action_executed:     FailoverAction
    status:              FailoverStatus
    is_successful:       bool
    phases_completed:    Tuple[FailoverPhase, ...]
    execution_steps:     Tuple[FailoverExecutionStep, ...]
    recovery_time_ms:    float
    started_at:          float
    completed_at:        float
    error_message:       str           = ""
    fallback_used:       bool          = False
    fallback_action:     Optional[FailoverAction] = None
    version:             str           = VERSION
    metadata:            Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":           self.result_id,
            "request_id":          self.request_id,
            "failover_session_id": self.failover_session_id,
            "failover_type":       self.failover_type.value,
            "action_executed":     self.action_executed.value,
            "status":              self.status.value,
            "is_successful":       self.is_successful,
            "phases_completed":    [p.value for p in self.phases_completed],
            "recovery_time_ms":    self.recovery_time_ms,
            "started_at":          self.started_at,
            "completed_at":        self.completed_at,
            "error_message":       self.error_message,
            "fallback_used":       self.fallback_used,
        }


# ── Failover response ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FailoverResponse:
    """
    Top-level response from the Failover Engine.

    Combines the FailoverResult with the VerificationReport and
    operational state assessment.
    """

    response_id:                  str
    request_id:                   str
    failover_session_id:          str
    source_decision_id:           str
    result:                       FailoverResult
    verification_report:          Optional[VerificationReport]
    is_operational:               bool
    requires_manual_intervention: bool
    next_recommended_action:      str
    response_time_ms:             float
    responded_at:                 float
    version:                      str           = VERSION
    metadata:                     Dict[str, Any] = field(default_factory=dict)

    @property
    def is_successful(self) -> bool:
        return self.result.is_successful

    @property
    def is_verified(self) -> bool:
        if self.verification_report is None:
            return True   # verification not required
        return self.verification_report.is_verified

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":                  self.response_id,
            "request_id":                   self.request_id,
            "failover_session_id":          self.failover_session_id,
            "source_decision_id":           self.source_decision_id,
            "is_successful":                self.is_successful,
            "is_operational":               self.is_operational,
            "is_verified":                  self.is_verified,
            "requires_manual_intervention": self.requires_manual_intervention,
            "next_recommended_action":      self.next_recommended_action,
            "response_time_ms":             self.response_time_ms,
            "responded_at":                 self.responded_at,
        }


# ── Factories ─────────────────────────────────────────────────────────────────

def make_verification_report(
    failover_session_id: str,
    checks: Tuple[VerificationCheck, ...],
    *,
    report_id: Optional[str] = None,
) -> VerificationReport:
    passed  = sum(1 for c in checks if c.status == VerificationStatus.PASSED)
    failed  = sum(1 for c in checks if c.status == VerificationStatus.FAILED)
    skipped = sum(1 for c in checks if c.status == VerificationStatus.SKIPPED)
    overall = VerificationStatus.PASSED if failed == 0 else VerificationStatus.FAILED
    return VerificationReport(
        report_id           = report_id or str(uuid.uuid4()),
        failover_session_id = failover_session_id,
        checks              = checks,
        overall_status      = overall,
        passed_checks       = passed,
        failed_checks       = failed,
        skipped_checks      = skipped,
        verified_at         = time.time(),
    )


def make_failover_result(
    request_id: str,
    failover_session_id: str,
    failover_type: FailoverType,
    action_executed: FailoverAction,
    status: FailoverStatus,
    is_successful: bool,
    phases_completed: Tuple[FailoverPhase, ...],
    execution_steps: Tuple[FailoverExecutionStep, ...],
    recovery_time_ms: float,
    started_at: float,
    *,
    error_message: str = "",
    fallback_used: bool = False,
    fallback_action: Optional[FailoverAction] = None,
    metadata: Optional[Dict[str, Any]] = None,
    result_id: Optional[str] = None,
) -> FailoverResult:
    return FailoverResult(
        result_id           = result_id or str(uuid.uuid4()),
        request_id          = request_id,
        failover_session_id = failover_session_id,
        failover_type       = failover_type,
        action_executed     = action_executed,
        status              = status,
        is_successful       = is_successful,
        phases_completed    = phases_completed,
        execution_steps     = execution_steps,
        recovery_time_ms    = recovery_time_ms,
        started_at          = started_at,
        completed_at        = time.time(),
        error_message       = error_message,
        fallback_used       = fallback_used,
        fallback_action     = fallback_action,
        metadata            = dict(metadata) if metadata else {},
    )


def make_failover_response(
    request_id: str,
    failover_session_id: str,
    source_decision_id: str,
    result: FailoverResult,
    verification_report: Optional[VerificationReport],
    response_time_ms: float,
    *,
    next_recommended_action: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    response_id: Optional[str] = None,
) -> FailoverResponse:
    is_operational = (
        result.is_successful
        and result.action_executed not in NON_OPERATIONAL_ACTIONS
    )
    requires_manual = result.action_executed in (
        FailoverAction.MANUAL_ESCALATION, FailoverAction.GRACEFUL_SHUTDOWN
    )
    return FailoverResponse(
        response_id                  = response_id or str(uuid.uuid4()),
        request_id                   = request_id,
        failover_session_id          = failover_session_id,
        source_decision_id           = source_decision_id,
        result                       = result,
        verification_report          = verification_report,
        is_operational               = is_operational,
        requires_manual_intervention = requires_manual,
        next_recommended_action      = next_recommended_action,
        response_time_ms             = response_time_ms,
        responded_at                 = time.time(),
        metadata                     = dict(metadata) if metadata else {},
    )
