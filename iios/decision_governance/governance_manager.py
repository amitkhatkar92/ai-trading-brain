"""iios/decision_governance/governance_manager.py

GovernanceManager: the main governance pipeline orchestrator.

Pipeline:
  1.  Create/validate GovernanceSubject
  2.  Record SUBMITTED audit event
  3.  Execute governance policies  → PolicyExecutionResult
  4.  If STRICT mode + blocking violations → reject immediately
  5.  Run approval workflow / ad-hoc approval policies → ApprovalResult
  6.  Record APPROVED / REJECTED / ESCALATED audit event
  7.  If approved → issue CertificationRecord
  8.  Publish metrics + alerts
  9.  Return GovernanceResult
"""
from __future__ import annotations

import time
import threading
import uuid
from dataclasses import dataclass, field

from iios.decision_governance.governance_constants import (
    AuditEventType,
    GovernanceMode,
    GovernanceStatus,
    AlertSeverity,
    DEFAULT_GOVERNANCE_MODE,
)
from iios.decision_governance.governance_exceptions import GovernanceNotFoundError
from iios.decision_governance.governance_context import GovernanceSubject
from iios.decision_governance.policies.governance_policy import GovernancePolicy
from iios.decision_governance.policies.policy_executor import (
    PolicyExecutionResult,
    PolicyExecutor,
)
from iios.decision_governance.approval.approval_policy import ApprovalPolicy
from iios.decision_governance.approval.approval_result import ApprovalResult
from iios.decision_governance.approval.approval_workflow import ApprovalWorkflow
from iios.decision_governance.approval.approval_engine import ApprovalEngine
from iios.decision_governance.audit.audit_engine import AuditEngine
from iios.decision_governance.audit.audit_history import AuditHistory
from iios.decision_governance.audit.audit_report import AuditReport
from iios.decision_governance.certification.certification_record import CertificationRecord
from iios.decision_governance.certification.certification_engine import CertificationEngine
from iios.decision_governance.monitoring.governance_metrics import GovernanceMetrics
from iios.decision_governance.monitoring.governance_alerts import GovernanceAlerts
from iios.decision_governance.history.governance_history import GovernanceHistory


# ─────────────────────────────────────────────────────────────────────────────
# Request / Result dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GovernanceRequest:
    """Input to the governance pipeline."""

    request_id:          str              = field(default_factory=lambda: str(uuid.uuid4()))
    subject:             GovernanceSubject | None = None
    governance_policies: list[GovernancePolicy]   = field(default_factory=list)
    approval_policies:   list[ApprovalPolicy]     = field(default_factory=list)
    workflow:            ApprovalWorkflow | None   = None
    mode:                GovernanceMode            = DEFAULT_GOVERNANCE_MODE
    metadata:            dict                     = field(default_factory=dict)
    created_at:          float                    = field(default_factory=time.time)


@dataclass
class GovernanceResult:
    """Output of the governance pipeline."""

    result_id:        str                        = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:       str                        = ""
    subject:          GovernanceSubject | None   = None
    status:           GovernanceStatus           = GovernanceStatus.PENDING
    approved:         bool                       = False
    mode:             GovernanceMode             = DEFAULT_GOVERNANCE_MODE
    policy_result:    PolicyExecutionResult | None = None
    approval_result:  ApprovalResult | None      = None
    audit_report:     AuditReport | None         = None
    certification:    CertificationRecord | None = None
    succeeded:        bool                       = True
    errors:           list[str]                  = field(default_factory=list)
    warnings:         list[str]                  = field(default_factory=list)
    duration_ms:      float                      = 0.0
    created_at:       float                      = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "result_id":       self.result_id,
            "request_id":      self.request_id,
            "status":          self.status.value,
            "approved":        self.approved,
            "mode":            self.mode.value,
            "succeeded":       self.succeeded,
            "errors":          self.errors,
            "warnings":        self.warnings,
            "duration_ms":     self.duration_ms,
            "created_at":      self.created_at,
        }


# ─────────────────────────────────────────────────────────────────────────────
# GovernanceManager
# ─────────────────────────────────────────────────────────────────────────────

class GovernanceManager:

    def __init__(self) -> None:
        self._lock:           threading.RLock        = threading.RLock()
        self._policy_executor = PolicyExecutor()
        self._approval_engine = ApprovalEngine()
        self._audit_history   = AuditHistory()
        self._audit_engine    = AuditEngine(history=self._audit_history)
        self._cert_engine     = CertificationEngine()
        self._alerts          = GovernanceAlerts()
        self._history         = GovernanceHistory()
        self._metrics         = GovernanceMetrics()

    # ── public API ────────────────────────────────────────────────────────────

    def govern(self, request: GovernanceRequest) -> GovernanceResult:
        """Run the full governance pipeline and return a GovernanceResult."""
        t0 = time.time()
        subject = request.subject or GovernanceSubject()

        result = GovernanceResult(
            request_id=request.request_id,
            subject=subject,
            mode=request.mode,
        )

        try:
            self._run_pipeline(request, subject, result)
        except Exception as exc:  # noqa: BLE001
            result.succeeded = False
            result.errors.append(str(exc))
            result.status    = GovernanceStatus.REJECTED

        result.duration_ms = (time.time() - t0) * 1_000
        self._update_metrics(result)
        self._history.store(result)
        return result

    def get(self, result_id: str) -> GovernanceResult:
        return self._history.get(result_id)  # type: ignore[return-value]

    def recent(self, n: int = 10) -> list[GovernanceResult]:
        return self._history.recent(n)  # type: ignore[return-value]

    def statistics(self) -> dict:
        with self._lock:
            m = self._metrics
        return {
            "total":           m.total_submitted,
            "approved":        m.approved,
            "rejected":        m.rejected,
            "escalated":       m.escalated,
            "policy_violations": m.policy_violations,
            "alerts":          m.alerts_raised,
            "avg_latency_ms":  m.avg_latency_ms,
        }

    def metrics(self) -> GovernanceMetrics:
        with self._lock:
            return self._metrics

    def alerts(self) -> GovernanceAlerts:
        return self._alerts

    def audit_engine(self) -> AuditEngine:
        return self._audit_engine

    def cert_engine(self) -> CertificationEngine:
        return self._cert_engine

    # ── pipeline stages ───────────────────────────────────────────────────────

    def _run_pipeline(
        self,
        request: GovernanceRequest,
        subject: GovernanceSubject,
        result:  GovernanceResult,
    ) -> None:
        # Stage 1: audit submission
        self._audit_engine.record_submission(subject, details={"mode": request.mode.value})

        # Stage 2: bypass mode
        if request.mode == GovernanceMode.BYPASS:
            result.approved = True
            result.status   = GovernanceStatus.APPROVED
            self._audit_engine.record_event(
                subject.decision_id, AuditEventType.APPROVED,
                action="bypass_approved",
            )
            result.certification = self._cert_engine.issue(
                subject.decision_id, subject.subject_id, basis="bypass"
            )
            return

        # Stage 3: governance policy evaluation
        policy_result = self._policy_executor.execute(
            subject, request.governance_policies
        )
        result.policy_result = policy_result

        if policy_result.violations:
            with self._lock:
                self._metrics.policy_violations += len(
                    [v for v in policy_result.violations if v.is_blocking]
                )

        # Stage 4: STRICT mode hard rejection on blocking violations
        if request.mode == GovernanceMode.STRICT and not policy_result.passed:
            result.approved = False
            result.status   = GovernanceStatus.REJECTED
            msgs = [v.message for v in policy_result.violations if v.is_blocking]
            result.errors.extend(msgs)
            self._audit_engine.record_event(
                subject.decision_id, AuditEventType.REJECTED,
                action="policy_rejected",
                details={"violations": len(policy_result.violations)},
            )
            self._alerts.raise_alert(
                AlertSeverity.WARNING,
                f"Decision {subject.decision_id!r} rejected by policy (STRICT)",
                source="policy_executor",
                decision_id=subject.decision_id,
            )
            with self._lock:
                self._metrics.alerts_raised += 1
            return

        # Stage 5: AUDIT_ONLY — record but never block
        if request.mode == GovernanceMode.AUDIT_ONLY:
            result.approved = True
            result.status   = GovernanceStatus.APPROVED
            self._audit_engine.record_event(
                subject.decision_id, AuditEventType.APPROVED,
                action="audit_only_approved",
            )
            result.certification = self._cert_engine.issue(
                subject.decision_id, subject.subject_id, basis="audit_only"
            )
            return

        # Stage 6: approval
        if not policy_result.passed:
            result.warnings.extend(
                [v.message for v in policy_result.violations if not v.is_blocking]
            )

        if request.workflow is not None:
            approval = self._approval_engine.run_workflow(subject, request.workflow)
        elif request.approval_policies:
            approval = self._approval_engine.evaluate(subject, request.approval_policies)
        else:
            # No approval policy configured → auto-approve
            from iios.decision_governance.approval.approval_policy import AutoApprovalPolicy  # noqa: PLC0415
            auto = AutoApprovalPolicy("_auto", "Auto Approve")
            approval = self._approval_engine.evaluate(subject, [auto])

        result.approval_result = approval

        from iios.decision_governance.governance_constants import ApprovalStatus  # noqa: PLC0415
        if approval.status == ApprovalStatus.APPROVED:
            result.approved = True
            result.status   = GovernanceStatus.APPROVED
            self._audit_engine.record_event(
                subject.decision_id, AuditEventType.APPROVED,
                action="approval_granted",
                details={"approval_result_id": approval.result_id},
            )
            result.certification = self._cert_engine.issue(
                subject.decision_id, subject.subject_id, basis="approval_granted"
            )

        elif approval.status == ApprovalStatus.ESCALATED:
            result.approved = False
            result.status   = GovernanceStatus.ESCALATED
            self._audit_engine.record_event(
                subject.decision_id, AuditEventType.ESCALATED,
                action="approval_escalated",
            )
            self._alerts.raise_alert(
                AlertSeverity.WARNING,
                f"Decision {subject.decision_id!r} escalated for manual review",
                source="approval_engine",
                decision_id=subject.decision_id,
            )
            with self._lock:
                self._metrics.alerts_raised += 1

        else:
            result.approved = False
            result.status   = GovernanceStatus.REJECTED
            self._audit_engine.record_event(
                subject.decision_id, AuditEventType.REJECTED,
                action="approval_denied",
                details={"records": len(approval.records)},
            )

        # Stage 7: build audit report
        result.audit_report = self._audit_engine.build_report(subject.decision_id)

    # ── metrics ───────────────────────────────────────────────────────────────

    def _update_metrics(self, result: GovernanceResult) -> None:
        with self._lock:
            m = self._metrics
            m.total_submitted  += 1
            m.total_latency_ms += result.duration_ms
            if result.status == GovernanceStatus.APPROVED:
                m.approved  += 1
            elif result.status == GovernanceStatus.REJECTED:
                m.rejected  += 1
            elif result.status == GovernanceStatus.ESCALATED:
                m.escalated += 1
            if result.certification:
                m.certified += 1


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock        = threading.Lock()
_instance:       GovernanceManager | None = None


def get_governance_manager() -> GovernanceManager:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = GovernanceManager()
    return _instance


def reset_governance_manager() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        _instance = None
