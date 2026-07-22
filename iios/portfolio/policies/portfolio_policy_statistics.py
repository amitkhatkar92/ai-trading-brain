"""
portfolio_policy_statistics.py — iios.portfolio.policies
=========================================================
Thread-safe statistics for the Portfolio Policy Engine.

All counters are cumulative and safe to read concurrently.
Averages use an exact running mean (not EMA) for precision.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from .constants import PolicyAction, PolicyType


class PortfolioPolicyStatistics:
    """
    Thread-safe cumulative statistics for the Portfolio Policy Engine.

    Tracks:
    - Evaluation counts (total, approved, rejected, blocked, escalated,
      deferred, manual-review, conditional)
    - Per-policy-type request counts
    - Average evaluation time
    - Policy registration counts
    """

    def __init__(self) -> None:
        self._lock              = threading.Lock()
        self._started_at: float = time.time()

        # Evaluation counters
        self._evaluations_total:        int   = 0
        self._evaluations_approved:     int   = 0
        self._evaluations_conditional:  int   = 0
        self._evaluations_rejected:     int   = 0
        self._evaluations_blocked:      int   = 0
        self._evaluations_escalated:    int   = 0
        self._evaluations_deferred:     int   = 0
        self._evaluations_manual:       int   = 0
        self._evaluations_error:        int   = 0

        # Timing
        self._total_elapsed_s: float = 0.0

        # Policy counts
        self._policies_registered: int = 0
        self._policies_active:     int = 0

        # Throughput
        self._policies_evaluated: int = 0  # individual policy evaluations

        # Per-type counters
        self._by_type: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Record methods
    # ------------------------------------------------------------------

    def record_evaluation_completed(
        self,
        final_action: PolicyAction,
        elapsed_s:    float,
        policy_types: Optional[list] = None,
    ) -> None:
        """Record a completed evaluation run and its outcome."""
        with self._lock:
            self._evaluations_total += 1
            self._total_elapsed_s   += elapsed_s

            if final_action == PolicyAction.APPROVE:
                self._evaluations_approved += 1
            elif final_action == PolicyAction.APPROVE_WITH_CONDITIONS:
                self._evaluations_conditional += 1
            elif final_action == PolicyAction.REJECT:
                self._evaluations_rejected += 1
            elif final_action == PolicyAction.BLOCK:
                self._evaluations_blocked += 1
            elif final_action == PolicyAction.ESCALATE:
                self._evaluations_escalated += 1
            elif final_action == PolicyAction.DEFER:
                self._evaluations_deferred += 1
            elif final_action == PolicyAction.REQUIRE_MANUAL_REVIEW:
                self._evaluations_manual += 1

            for pt in (policy_types or []):
                key = pt.value if hasattr(pt, "value") else str(pt)
                self._by_type[key] = self._by_type.get(key, 0) + 1

    def record_evaluation_error(self) -> None:
        """Record an evaluation run that failed with an engine error."""
        with self._lock:
            self._evaluations_error += 1

    def record_policy_evaluated(self, count: int = 1) -> None:
        """Record that N individual policies were evaluated in a run."""
        with self._lock:
            self._policies_evaluated += count

    def record_policy_registered(self) -> None:
        """Record a newly registered policy."""
        with self._lock:
            self._policies_registered += 1
            self._policies_active     += 1

    def record_policy_deactivated(self) -> None:
        """Record a policy deactivation."""
        with self._lock:
            if self._policies_active > 0:
                self._policies_active -= 1

    def reset(self) -> None:
        """Reset all counters (preserves uptime start time)."""
        with self._lock:
            self._evaluations_total       = 0
            self._evaluations_approved    = 0
            self._evaluations_conditional = 0
            self._evaluations_rejected    = 0
            self._evaluations_blocked     = 0
            self._evaluations_escalated   = 0
            self._evaluations_deferred    = 0
            self._evaluations_manual      = 0
            self._evaluations_error       = 0
            self._total_elapsed_s         = 0.0
            self._policies_registered     = 0
            self._policies_active         = 0
            self._policies_evaluated      = 0
            self._by_type.clear()

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return a thread-safe snapshot of all statistics."""
        with self._lock:
            total = self._evaluations_total
            avg   = (self._total_elapsed_s / total) if total > 0 else 0.0

            return {
                # Core counters
                "evaluations_total":       total,
                "evaluations_approved":    self._evaluations_approved,
                "evaluations_conditional": self._evaluations_conditional,
                "evaluations_rejected":    self._evaluations_rejected,
                "evaluations_blocked":     self._evaluations_blocked,
                "evaluations_escalated":   self._evaluations_escalated,
                "evaluations_deferred":    self._evaluations_deferred,
                "evaluations_manual":      self._evaluations_manual,
                "evaluations_error":       self._evaluations_error,
                # Timing
                "average_evaluation_time_s": avg,
                # Policy counts
                "policies_registered":     self._policies_registered,
                "policies_active":         self._policies_active,
                "policies_evaluated":      self._policies_evaluated,
                # Per-type breakdown
                "evaluations_by_type":     dict(self._by_type),
                # Uptime
                "uptime_s":                time.time() - self._started_at,
            }
