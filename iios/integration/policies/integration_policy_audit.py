"""
integration_policy_audit.py — iios.integration.policies
---------------------------------------------------------
Audit trail for every governance evaluation.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

from .constants import DEFAULT_MAX_AUDIT, PolicyAction
from .integration_policy_result import GovernanceDecision, IntegrationPolicyResult


@dataclass(frozen=True)
class IntegrationAuditEntry:
    """
    Immutable record of a single governance evaluation.
    """

    audit_id:           str
    request_id:         str
    context_id:         str
    final_action:       PolicyAction
    policies_evaluated: int
    policy_results:     Tuple[IntegrationPolicyResult, ...]
    decision_id:        str
    evaluation_time_ms: float
    audit_timestamp:    str
    metadata:           Dict[str, Any]

    @classmethod
    def create(
        cls,
        request_id:         str,
        context_id:         str,
        decision:           GovernanceDecision,
        policy_results:     List[IntegrationPolicyResult],
        evaluation_time_ms: float                    = 0.0,
        metadata:           Optional[Dict[str, Any]] = None,
    ) -> "IntegrationAuditEntry":
        return cls(
            audit_id           = f"audit-{uuid.uuid4().hex[:12]}",
            request_id         = request_id,
            context_id         = context_id,
            final_action       = decision.final_action,
            policies_evaluated = len(policy_results),
            policy_results     = tuple(policy_results),
            decision_id        = decision.decision_id,
            evaluation_time_ms = evaluation_time_ms,
            audit_timestamp    = datetime.now(timezone.utc).isoformat(),
            metadata           = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id":           self.audit_id,
            "request_id":         self.request_id,
            "context_id":         self.context_id,
            "final_action":       self.final_action.value,
            "policies_evaluated": self.policies_evaluated,
            "policy_results":     [r.to_dict() for r in self.policy_results],
            "decision_id":        self.decision_id,
            "evaluation_time_ms": self.evaluation_time_ms,
            "audit_timestamp":    self.audit_timestamp,
            "metadata":           self.metadata,
        }


@dataclass(frozen=True)
class IntegrationAuditReport:
    """Aggregated audit report across a batch of evaluations."""

    report_id:          str
    total_evaluations:  int
    total_approved:     int
    total_rejected:     int
    total_blocked:      int
    total_emergency:    int
    avg_evaluation_ms:  float
    entries:            Tuple[IntegrationAuditEntry, ...]
    generated_at:       str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":         self.report_id,
            "total_evaluations": self.total_evaluations,
            "total_approved":    self.total_approved,
            "total_rejected":    self.total_rejected,
            "total_blocked":     self.total_blocked,
            "total_emergency":   self.total_emergency,
            "avg_evaluation_ms": self.avg_evaluation_ms,
            "entries":           [e.to_dict() for e in self.entries],
            "generated_at":      self.generated_at,
        }


class IntegrationPolicyAudit:
    """
    Thread-safe bounded ring-buffer of governance audit entries.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_AUDIT) -> None:
        self._max     = max_entries
        self._entries: Deque[IntegrationAuditEntry] = deque(maxlen=max_entries)
        self._lock    = threading.Lock()

    def record(self, entry: IntegrationAuditEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    def get(self, audit_id: str) -> Optional[IntegrationAuditEntry]:
        with self._lock:
            for e in self._entries:
                if e.audit_id == audit_id:
                    return e
        return None

    def by_request(self, request_id: str) -> List[IntegrationAuditEntry]:
        with self._lock:
            return [e for e in self._entries if e.request_id == request_id]

    def recent(self, n: int = 20) -> List[IntegrationAuditEntry]:
        with self._lock:
            entries = list(self._entries)
        return entries[-n:]

    def report(self) -> IntegrationAuditReport:
        with self._lock:
            entries = list(self._entries)

        total     = len(entries)
        approved  = sum(
            1 for e in entries
            if e.final_action in (PolicyAction.APPROVE, PolicyAction.APPROVE_WITH_CONDITIONS)
        )
        rejected  = sum(1 for e in entries if e.final_action == PolicyAction.REJECT)
        blocked   = sum(1 for e in entries if e.final_action == PolicyAction.BLOCK)
        emergency = sum(1 for e in entries if e.final_action == PolicyAction.EMERGENCY_STOP)
        avg_ms    = (
            sum(e.evaluation_time_ms for e in entries) / total
            if total else 0.0
        )

        return IntegrationAuditReport(
            report_id         = f"arpt-{uuid.uuid4().hex[:8]}",
            total_evaluations = total,
            total_approved    = approved,
            total_rejected    = rejected,
            total_blocked     = blocked,
            total_emergency   = emergency,
            avg_evaluation_ms = avg_ms,
            entries           = tuple(entries),
            generated_at      = datetime.now(timezone.utc).isoformat(),
        )

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
