"""
integration_policy_statistics.py — iios.integration.policies
-------------------------------------------------------------
Statistics counters for the Integration Governance Policy Framework.

Tracks all 9 metrics defined in the specification:
  Policies Evaluated, Policies Approved, Policies Rejected,
  Policies Blocked, Security Reviews, Escalations,
  Emergency Stops, Average Evaluation Time, Governance Coverage.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass(frozen=True)
class IntegrationPolicyStatisticsReport:
    """Snapshot of all 9 governance statistics."""

    policies_evaluated:    int
    policies_approved:     int
    policies_rejected:     int
    policies_blocked:      int
    security_reviews:      int
    escalations:           int
    emergency_stops:       int
    average_evaluation_ms: float
    governance_coverage:   float    # approved / evaluated (1.0 when zero evaluations)
    captured_at:           str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policies_evaluated":    self.policies_evaluated,
            "policies_approved":     self.policies_approved,
            "policies_rejected":     self.policies_rejected,
            "policies_blocked":      self.policies_blocked,
            "security_reviews":      self.security_reviews,
            "escalations":           self.escalations,
            "emergency_stops":       self.emergency_stops,
            "average_evaluation_ms": self.average_evaluation_ms,
            "governance_coverage":   self.governance_coverage,
            "captured_at":           self.captured_at,
        }


class IntegrationPolicyStatistics:
    """
    Thread-safe statistics counters for governance evaluations.
    """

    def __init__(self) -> None:
        self._lock              = threading.Lock()
        self._evaluated         = 0
        self._approved          = 0
        self._rejected          = 0
        self._blocked           = 0
        self._security_reviews  = 0
        self._escalations       = 0
        self._emergency_stops   = 0
        self._eval_times: List[float] = []

    # ── increment methods ─────────────────────────────────────────────

    def record_evaluated(self)       -> None:
        with self._lock: self._evaluated        += 1

    def record_approved(self)        -> None:
        with self._lock: self._approved         += 1

    def record_rejected(self)        -> None:
        with self._lock: self._rejected         += 1

    def record_blocked(self)         -> None:
        with self._lock: self._blocked          += 1

    def record_security_review(self) -> None:
        with self._lock: self._security_reviews += 1

    def record_escalation(self)      -> None:
        with self._lock: self._escalations      += 1

    def record_emergency_stop(self)  -> None:
        with self._lock: self._emergency_stops  += 1

    def record_evaluation_time(self, ms: float) -> None:
        with self._lock:
            self._eval_times.append(ms)
            # Keep the ring bounded to avoid unbounded memory growth
            if len(self._eval_times) > 10_000:
                self._eval_times = self._eval_times[-10_000:]

    # ── report ────────────────────────────────────────────────────────

    def report(self) -> IntegrationPolicyStatisticsReport:
        with self._lock:
            evaluated = self._evaluated
            approved  = self._approved
            rejected  = self._rejected
            blocked   = self._blocked
            security  = self._security_reviews
            escalated = self._escalations
            emergency = self._emergency_stops
            times     = list(self._eval_times)

        avg_ms   = sum(times) / len(times) if times else 0.0
        coverage = approved / evaluated if evaluated else 1.0

        return IntegrationPolicyStatisticsReport(
            policies_evaluated    = evaluated,
            policies_approved     = approved,
            policies_rejected     = rejected,
            policies_blocked      = blocked,
            security_reviews      = security,
            escalations           = escalated,
            emergency_stops       = emergency,
            average_evaluation_ms = avg_ms,
            governance_coverage   = coverage,
            captured_at           = datetime.now(timezone.utc).isoformat(),
        )

    def reset(self) -> None:
        with self._lock:
            self._evaluated        = 0
            self._approved         = 0
            self._rejected         = 0
            self._blocked          = 0
            self._security_reviews = 0
            self._escalations      = 0
            self._emergency_stops  = 0
            self._eval_times       = []
