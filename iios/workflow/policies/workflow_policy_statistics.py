"""
workflow_policy_statistics.py — iios.workflow.policies
-------------------------------------------------------
WorkflowPolicyStatisticsReport + WorkflowPolicyStatistics — governance
evaluation metrics aggregation and reporting.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import GovernanceDecision


@dataclass(frozen=True)
class WorkflowPolicyStatisticsReport:
    """Immutable snapshot of governance statistics."""
    policies_evaluated:       int
    policies_approved:        int
    policies_rejected:        int
    policies_blocked:         int
    manual_approvals:         int
    executive_approvals:      int
    emergency_stops:          int
    escalations:              int
    conditional_approvals:    int
    total_evaluation_time_ms: float
    average_evaluation_time_ms: float
    governance_coverage:      float    # fraction of evaluations with ≥1 applicable policy
    generated_at:             str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policies_evaluated":        self.policies_evaluated,
            "policies_approved":         self.policies_approved,
            "policies_rejected":         self.policies_rejected,
            "policies_blocked":          self.policies_blocked,
            "manual_approvals":          self.manual_approvals,
            "executive_approvals":       self.executive_approvals,
            "emergency_stops":           self.emergency_stops,
            "escalations":               self.escalations,
            "conditional_approvals":     self.conditional_approvals,
            "total_evaluation_time_ms":  self.total_evaluation_time_ms,
            "average_evaluation_time_ms": self.average_evaluation_time_ms,
            "governance_coverage":       self.governance_coverage,
            "generated_at":              self.generated_at,
        }


class WorkflowPolicyStatistics:
    """
    Thread-safe governance evaluation metrics tracker.
    """

    def __init__(self) -> None:
        self._lock               = threading.Lock()
        self._evaluated          = 0
        self._approved           = 0
        self._rejected           = 0
        self._blocked            = 0
        self._manual             = 0
        self._executive          = 0
        self._emergency          = 0
        self._escalated          = 0
        self._conditional        = 0
        self._total_time_ms      = 0.0
        self._with_policies      = 0   # evaluations that had ≥1 applicable policy

    # ----------------------------------------------------------------
    # Recording
    # ----------------------------------------------------------------

    def record_evaluation(
        self,
        decision:            GovernanceDecision,
        evaluation_time_ms:  float,
        had_applicable_policies: bool = True,
    ) -> None:
        """Record a single governance evaluation outcome."""
        with self._lock:
            self._evaluated      += 1
            self._total_time_ms  += evaluation_time_ms
            if had_applicable_policies:
                self._with_policies += 1

            if decision in (
                GovernanceDecision.APPROVED,
                GovernanceDecision.APPROVED_WITH_CONDITIONS,
            ):
                self._approved += 1
                if decision == GovernanceDecision.APPROVED_WITH_CONDITIONS:
                    self._conditional += 1
            elif decision == GovernanceDecision.REJECTED:
                self._rejected += 1
            elif decision == GovernanceDecision.BLOCKED:
                self._blocked += 1
            elif decision == GovernanceDecision.REQUIRES_MANUAL_APPROVAL:
                self._manual += 1
            elif decision == GovernanceDecision.REQUIRES_EXECUTIVE_APPROVAL:
                self._executive += 1
            elif decision == GovernanceDecision.EMERGENCY_STOPPED:
                self._emergency += 1
            elif decision == GovernanceDecision.ESCALATED:
                self._escalated += 1

    # ----------------------------------------------------------------
    # Report
    # ----------------------------------------------------------------

    def report(self) -> WorkflowPolicyStatisticsReport:
        with self._lock:
            evaluated   = self._evaluated
            approved    = self._approved
            rejected    = self._rejected
            blocked     = self._blocked
            manual      = self._manual
            executive   = self._executive
            emergency   = self._emergency
            escalated   = self._escalated
            conditional = self._conditional
            total_time  = self._total_time_ms
            with_pol    = self._with_policies

        avg = round(total_time / evaluated, 3) if evaluated else 0.0
        cov = round(with_pol / evaluated, 4)   if evaluated else 0.0

        return WorkflowPolicyStatisticsReport(
            policies_evaluated        = evaluated,
            policies_approved         = approved,
            policies_rejected         = rejected,
            policies_blocked          = blocked,
            manual_approvals          = manual,
            executive_approvals       = executive,
            emergency_stops           = emergency,
            escalations               = escalated,
            conditional_approvals     = conditional,
            total_evaluation_time_ms  = round(total_time, 3),
            average_evaluation_time_ms = avg,
            governance_coverage       = cov,
            generated_at              = datetime.now(tz=timezone.utc).isoformat(),
        )

    def reset(self) -> None:
        """Reset all counters."""
        with self._lock:
            self._evaluated     = 0
            self._approved      = 0
            self._rejected      = 0
            self._blocked       = 0
            self._manual        = 0
            self._executive     = 0
            self._emergency     = 0
            self._escalated     = 0
            self._conditional   = 0
            self._total_time_ms = 0.0
            self._with_policies = 0
