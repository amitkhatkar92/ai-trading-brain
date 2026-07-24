"""
knowledge_policy_statistics.py — iios.knowledge.policies
----------------------------------------------------------
KnowledgeGovernanceStatistics — thread-safe 8-counter governance metrics.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict


class KnowledgeGovernanceStatistics:
    """
    Thread-safe statistics for the governance policy framework.

    Counters (8)
    ------------
    policies_evaluated          Total evaluation runs
    policies_approved           Approved (incl. approved_with_conditions)
    policies_rejected           Rejected decisions
    policies_blocked            Blocked decisions
    manual_reviews              Manual review decisions
    escalations                 Escalation decisions
    average_evaluation_time_ms  Rolling average evaluation time
    governance_coverage         Source coverage ratio [0.0 – 1.0]
    """

    def __init__(self) -> None:
        self._lock                          = threading.Lock()
        self._policies_evaluated:       int   = 0
        self._policies_approved:        int   = 0
        self._policies_rejected:        int   = 0
        self._policies_blocked:         int   = 0
        self._manual_reviews:           int   = 0
        self._escalations:              int   = 0
        self._total_evaluation_ms:      float = 0.0
        self._coverage_sources_total:   int   = 0
        self._coverage_sources_covered: int   = 0
        self._start_time:               float = time.time()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_evaluation(self, decision: str, evaluation_ms: float) -> None:
        """Record one policy evaluation by decision string value."""
        from .constants import GovernanceDecision
        with self._lock:
            self._policies_evaluated += 1
            self._total_evaluation_ms += evaluation_ms
            if decision in (
                GovernanceDecision.APPROVED.value,
                GovernanceDecision.APPROVED_WITH_CONDITIONS.value,
            ):
                self._policies_approved += 1
            elif decision == GovernanceDecision.REJECTED.value:
                self._policies_rejected += 1
            elif decision == GovernanceDecision.BLOCKED.value:
                self._policies_blocked += 1
            elif decision == GovernanceDecision.MANUAL_REVIEW.value:
                self._manual_reviews += 1
            elif decision == GovernanceDecision.ESCALATED.value:
                self._escalations += 1

    def update_coverage(self, total_sources: int, covered_sources: int) -> None:
        with self._lock:
            self._coverage_sources_total   = total_sources
            self._coverage_sources_covered = covered_sources

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg = (
                self._total_evaluation_ms / self._policies_evaluated
                if self._policies_evaluated > 0
                else 0.0
            )
            coverage = (
                self._coverage_sources_covered / self._coverage_sources_total
                if self._coverage_sources_total > 0
                else 0.0
            )
            return {
                "policies_evaluated":         self._policies_evaluated,
                "policies_approved":          self._policies_approved,
                "policies_rejected":          self._policies_rejected,
                "policies_blocked":           self._policies_blocked,
                "manual_reviews":             self._manual_reviews,
                "escalations":                self._escalations,
                "average_evaluation_time_ms": round(avg, 3),
                "governance_coverage":        round(coverage, 4),
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._policies_evaluated       = 0
            self._policies_approved        = 0
            self._policies_rejected        = 0
            self._policies_blocked         = 0
            self._manual_reviews           = 0
            self._escalations              = 0
            self._total_evaluation_ms      = 0.0
            self._coverage_sources_total   = 0
            self._coverage_sources_covered = 0
            self._start_time               = time.time()
