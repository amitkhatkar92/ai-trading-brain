"""iios/decision_governance/audit/audit_report.py

AuditReport dataclass + builder function.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from iios.decision_governance.audit.audit_event import AuditEvent


@dataclass
class AuditReport:
    """Comprehensive audit report for a single decision."""

    report_id:       str             = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id:     str             = ""
    events:          list[AuditEvent] = field(default_factory=list)
    event_count:     int             = 0
    summary:         dict            = field(default_factory=dict)
    evidence_trace:  list[dict]      = field(default_factory=list)
    policy_trace:    list[dict]      = field(default_factory=list)
    reasoning_trace: list[str]       = field(default_factory=list)
    generated_at:    float           = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "report_id":       self.report_id,
            "decision_id":     self.decision_id,
            "event_count":     self.event_count,
            "summary":         self.summary,
            "evidence_trace":  self.evidence_trace,
            "policy_trace":    self.policy_trace,
            "reasoning_trace": self.reasoning_trace,
            "generated_at":    self.generated_at,
        }


def build_audit_report(
    decision_id: str,
    events:      list[AuditEvent],
) -> AuditReport:
    """Build a report from a chronologically-ordered list of audit events."""
    sorted_events = sorted(events, key=lambda e: e.timestamp)

    # Aggregate evidence + policy + reasoning traces
    evidence_trace:  list[dict] = []
    policy_trace:    list[dict] = []
    reasoning_trace: list[str]  = []
    type_counts:     dict[str, int] = {}

    for ev in sorted_events:
        type_counts[ev.event_type.value] = type_counts.get(ev.event_type.value, 0) + 1

        if ev.evidence:
            evidence_trace.append(
                {"event_id": ev.event_id, "event_type": ev.event_type.value, **ev.evidence}
            )
        if "policy" in ev.details:
            policy_trace.append(
                {"event_id": ev.event_id, "policy": ev.details["policy"]}
            )
        if "reasoning" in ev.details:
            reasoning_trace.append(ev.details["reasoning"])

    summary = {
        "total_events":  len(sorted_events),
        "actors":        sorted({e.actor for e in sorted_events}),
        "event_types":   type_counts,
        "first_event":   sorted_events[0].timestamp if sorted_events else None,
        "last_event":    sorted_events[-1].timestamp if sorted_events else None,
    }

    return AuditReport(
        decision_id=decision_id,
        events=sorted_events,
        event_count=len(sorted_events),
        summary=summary,
        evidence_trace=evidence_trace,
        policy_trace=policy_trace,
        reasoning_trace=reasoning_trace,
    )
