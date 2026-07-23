"""
governance_policy_statistics.py — iios.supervisor.policy
----------------------------------------------------------
Thread-safe statistics for the AI Governance Policy Framework.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict

_EMA_ALPHA = 0.1


class GovernancePolicyStatistics:
    """
    Thread-safe accumulator for governance policy evaluation statistics.
    """

    def __init__(self) -> None:
        self._lock                    = threading.Lock()
        self._evaluations:      int   = 0
        self._successes:        int   = 0
        self._failures:         int   = 0
        self._approved:         int   = 0
        self._denied:           int   = 0
        self._escalated:        int   = 0
        self._deferred:         int   = 0
        self._policies_evaluated: int = 0
        self._total_elapsed_s:  float = 0.0
        self._ema_elapsed_s:    float = 0.0
        self._started_at:       float = time.time()

    # ------------------------------------------------------------------
    # Recorders
    # ------------------------------------------------------------------

    def record_evaluation(self) -> None:
        with self._lock:
            self._evaluations += 1

    def record_success(self, elapsed_s: float = 0.0) -> None:
        with self._lock:
            self._successes += 1
            self._total_elapsed_s += elapsed_s
            if elapsed_s > 0:
                if self._ema_elapsed_s == 0.0:
                    self._ema_elapsed_s = elapsed_s
                else:
                    self._ema_elapsed_s = (
                        _EMA_ALPHA * elapsed_s
                        + (1.0 - _EMA_ALPHA) * self._ema_elapsed_s
                    )

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1

    def record_approved(self) -> None:
        with self._lock:
            self._approved += 1

    def record_denied(self) -> None:
        with self._lock:
            self._denied += 1

    def record_escalated(self) -> None:
        with self._lock:
            self._escalated += 1

    def record_deferred(self) -> None:
        with self._lock:
            self._deferred += 1

    def record_policies_evaluated(self, count: int) -> None:
        with self._lock:
            self._policies_evaluated += count

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg = (
                self._total_elapsed_s / self._successes
                if self._successes > 0 else 0.0
            )
            return {
                "evaluations":             self._evaluations,
                "successes":               self._successes,
                "failures":                self._failures,
                "approved":                self._approved,
                "denied":                  self._denied,
                "escalated":               self._escalated,
                "deferred":                self._deferred,
                "policies_evaluated":      self._policies_evaluated,
                "average_evaluation_s":    avg,
                "ema_evaluation_s":        self._ema_elapsed_s,
                "uptime_s":                time.time() - self._started_at,
            }

    def reset(self) -> None:
        with self._lock:
            self._evaluations        = 0
            self._successes          = 0
            self._failures           = 0
            self._approved           = 0
            self._denied             = 0
            self._escalated          = 0
            self._deferred           = 0
            self._policies_evaluated = 0
            self._total_elapsed_s    = 0.0
            self._ema_elapsed_s      = 0.0
            self._started_at         = time.time()
