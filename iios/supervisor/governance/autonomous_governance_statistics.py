"""
autonomous_governance_statistics.py — iios.supervisor.governance
-----------------------------------------------------------------
Thread-safe statistics accumulator for the Autonomous Governance Framework.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict

_EMA_ALPHA = 0.1


class AutonomousGovernanceStatistics:
    """
    Thread-safe accumulator for autonomous governance assessment statistics.

    Tracks:
    - Supervision sessions (total, success, failure)
    - Enterprise assessments
    - Anomalies detected
    - Incidents correlated
    - Root causes identified
    - Recommendations generated
    - Self-healing plans generated
    - Average / EMA assessment time
    - Platform stability score (EMA)
    """

    def __init__(self) -> None:
        self._lock                     = threading.Lock()
        self._sessions:          int   = 0
        self._successes:         int   = 0
        self._failures:          int   = 0
        self._enterprise_assessments: int = 0
        self._anomalies_detected:int   = 0
        self._incidents_correlated: int = 0
        self._root_causes_identified: int = 0
        self._recommendations_generated: int = 0
        self._self_healing_plans: int  = 0
        self._total_elapsed_s:   float = 0.0
        self._ema_elapsed_s:     float = 0.0
        self._platform_stability_ema: float = 1.0
        self._started_at:        float = time.time()

    # ------------------------------------------------------------------
    # Recorders
    # ------------------------------------------------------------------

    def record_session(self) -> None:
        with self._lock:
            self._sessions += 1

    def record_success(self, elapsed_s: float = 0.0) -> None:
        with self._lock:
            self._successes += 1
            self._total_elapsed_s += elapsed_s
            if self._ema_elapsed_s == 0.0:
                self._ema_elapsed_s = elapsed_s
            else:
                self._ema_elapsed_s = (
                    _EMA_ALPHA * elapsed_s
                    + (1 - _EMA_ALPHA) * self._ema_elapsed_s
                )

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1

    def record_enterprise_assessment(self) -> None:
        with self._lock:
            self._enterprise_assessments += 1

    def record_anomalies(self, count: int) -> None:
        with self._lock:
            self._anomalies_detected += count

    def record_incidents(self, count: int) -> None:
        with self._lock:
            self._incidents_correlated += count

    def record_root_causes(self, count: int) -> None:
        with self._lock:
            self._root_causes_identified += count

    def record_recommendations(self, count: int) -> None:
        with self._lock:
            self._recommendations_generated += count

    def record_self_healing_plan(self) -> None:
        with self._lock:
            self._self_healing_plans += 1

    def record_stability(self, score: float) -> None:
        with self._lock:
            self._platform_stability_ema = (
                _EMA_ALPHA * score
                + (1 - _EMA_ALPHA) * self._platform_stability_ema
            )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            sessions = self._sessions or 1
            return {
                "sessions":                   self._sessions,
                "successes":                  self._successes,
                "failures":                   self._failures,
                "enterprise_assessments":     self._enterprise_assessments,
                "anomalies_detected":         self._anomalies_detected,
                "incidents_correlated":       self._incidents_correlated,
                "root_causes_identified":     self._root_causes_identified,
                "recommendations_generated":  self._recommendations_generated,
                "self_healing_plans":         self._self_healing_plans,
                "success_rate":               self._successes / sessions,
                "average_elapsed_s":          self._total_elapsed_s / max(1, self._successes),
                "ema_elapsed_s":              self._ema_elapsed_s,
                "platform_stability_score":   self._platform_stability_ema,
                "uptime_s":                   time.time() - self._started_at,
            }

    def reset(self) -> None:
        with self._lock:
            self._sessions                 = 0
            self._successes                = 0
            self._failures                 = 0
            self._enterprise_assessments   = 0
            self._anomalies_detected       = 0
            self._incidents_correlated     = 0
            self._root_causes_identified   = 0
            self._recommendations_generated = 0
            self._self_healing_plans       = 0
            self._total_elapsed_s          = 0.0
            self._ema_elapsed_s            = 0.0
            self._platform_stability_ema   = 1.0
            self._started_at               = time.time()
