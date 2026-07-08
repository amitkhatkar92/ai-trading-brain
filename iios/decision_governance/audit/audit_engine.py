"""iios/decision_governance/audit/audit_engine.py

AuditEngine: records events and generates reports.
"""
from __future__ import annotations

from iios.decision_governance.governance_constants import AuditEventType
from iios.decision_governance.governance_context import GovernanceSubject
from iios.decision_governance.audit.audit_event import AuditEvent
from iios.decision_governance.audit.audit_history import AuditHistory
from iios.decision_governance.audit.audit_registry import AuditRegistry
from iios.decision_governance.audit.audit_report import AuditReport, build_audit_report


class AuditEngine:
    """
    Records audit events to the history + registry and produces reports.
    """

    def __init__(
        self,
        history:  AuditHistory  | None = None,
        registry: AuditRegistry | None = None,
    ) -> None:
        self._history  = history  or AuditHistory()
        self._registry = registry or AuditRegistry()

    # ── recording ─────────────────────────────────────────────────────────────

    def record(self, event: AuditEvent) -> None:
        self._history.record(event)
        self._registry.register(event)

    def record_submission(
        self,
        subject:    GovernanceSubject,
        session_id: str = "",
        details:    dict | None = None,
    ) -> AuditEvent:
        ev = AuditEvent(
            decision_id=subject.decision_id,
            event_type=AuditEventType.SUBMITTED,
            actor="system",
            action="subject_submitted",
            details=details or {},
            session_id=session_id,
        )
        self.record(ev)
        return ev

    def record_event(
        self,
        decision_id: str,
        event_type:  AuditEventType,
        actor:       str   = "system",
        action:      str   = "",
        details:     dict  | None = None,
        evidence:    dict  | None = None,
        session_id:  str   = "",
    ) -> AuditEvent:
        ev = AuditEvent(
            decision_id=decision_id,
            event_type=event_type,
            actor=actor,
            action=action or event_type.value,
            details=details or {},
            evidence=evidence or {},
            session_id=session_id,
        )
        self.record(ev)
        return ev

    # ── reporting ─────────────────────────────────────────────────────────────

    def build_report(self, decision_id: str) -> AuditReport:
        events = self._history.by_decision(decision_id)
        return build_audit_report(decision_id, events)

    def replay(self, decision_id: str) -> list[AuditEvent]:
        return self._history.replay(decision_id)

    def compare(self, decision_id_a: str, decision_id_b: str) -> dict:
        return self._history.compare(decision_id_a, decision_id_b)
