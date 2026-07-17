"""iios/execution/monitoring/alerts/alert_statistics.py
==================================================
AlertStatistics — mutable accumulator for alert framework operational stats.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AlertStatistics:
    """Mutable accumulator for framework-wide alert statistics."""

    alerts_generated:    int   = 0
    alerts_acknowledged: int   = 0
    alerts_resolved:     int   = 0
    alerts_escalated:    int   = 0
    alerts_expired:      int   = 0
    alerts_suppressed:   int   = 0
    critical_alerts:     int   = 0
    emergency_alerts:    int   = 0
    evaluation_count:    int   = 0
    evaluation_failures: int   = 0
    # Running sums for averages
    _total_evaluation_ms: float = 0.0
    _total_detection_ms:  float = 0.0
    _detection_count:     int   = 0
    last_updated_at:      float = 0.0

    def __post_init__(self) -> None:
        self._lock = threading.RLock()

    # ── Record helpers ────────────────────────────────────────────────────────

    def record_generated(self, severity_value: str = "") -> None:
        with self._lock:
            self.alerts_generated += 1
            if severity_value == "critical":
                self.critical_alerts += 1
            elif severity_value == "emergency":
                self.emergency_alerts += 1
            self.last_updated_at = time.time()

    def record_acknowledged(self) -> None:
        with self._lock:
            self.alerts_acknowledged += 1
            self.last_updated_at = time.time()

    def record_resolved(self) -> None:
        with self._lock:
            self.alerts_resolved += 1
            self.last_updated_at = time.time()

    def record_escalated(self) -> None:
        with self._lock:
            self.alerts_escalated += 1
            self.last_updated_at = time.time()

    def record_expired(self) -> None:
        with self._lock:
            self.alerts_expired += 1
            self.last_updated_at = time.time()

    def record_suppressed(self) -> None:
        with self._lock:
            self.alerts_suppressed += 1
            self.last_updated_at = time.time()

    def record_evaluation(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self.evaluation_count    += 1
            self._total_evaluation_ms += duration_ms
            self.last_updated_at = time.time()

    def record_evaluation_failure(self) -> None:
        with self._lock:
            self.evaluation_failures += 1
            self.last_updated_at = time.time()

    def record_detection_time(self, detection_ms: float) -> None:
        with self._lock:
            self._total_detection_ms += detection_ms
            self._detection_count    += 1
            self.last_updated_at      = time.time()

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def average_evaluation_time_ms(self) -> float:
        with self._lock:
            if self.evaluation_count == 0:
                return 0.0
            return self._total_evaluation_ms / self.evaluation_count

    @property
    def average_detection_time_ms(self) -> float:
        with self._lock:
            if self._detection_count == 0:
                return 0.0
            return self._total_detection_ms / self._detection_count

    @property
    def resolution_rate(self) -> float:
        with self._lock:
            if self.alerts_generated == 0:
                return 0.0
            return min(1.0, self.alerts_resolved / self.alerts_generated)

    @property
    def escalation_rate(self) -> float:
        with self._lock:
            if self.alerts_generated == 0:
                return 0.0
            return min(1.0, self.alerts_escalated / self.alerts_generated)

    @property
    def suppression_rate(self) -> float:
        with self._lock:
            total = self.alerts_generated + self.alerts_suppressed
            if total == 0:
                return 0.0
            return min(1.0, self.alerts_suppressed / total)

    # ── Utilities ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        with self._lock:
            self.alerts_generated     = 0
            self.alerts_acknowledged  = 0
            self.alerts_resolved      = 0
            self.alerts_escalated     = 0
            self.alerts_expired       = 0
            self.alerts_suppressed    = 0
            self.critical_alerts      = 0
            self.emergency_alerts     = 0
            self.evaluation_count     = 0
            self.evaluation_failures  = 0
            self._total_evaluation_ms = 0.0
            self._total_detection_ms  = 0.0
            self._detection_count     = 0
            self.last_updated_at      = 0.0

    def copy(self) -> "AlertStatistics":
        with self._lock:
            s = AlertStatistics(
                alerts_generated     = self.alerts_generated,
                alerts_acknowledged  = self.alerts_acknowledged,
                alerts_resolved      = self.alerts_resolved,
                alerts_escalated     = self.alerts_escalated,
                alerts_expired       = self.alerts_expired,
                alerts_suppressed    = self.alerts_suppressed,
                critical_alerts      = self.critical_alerts,
                emergency_alerts     = self.emergency_alerts,
                evaluation_count     = self.evaluation_count,
                evaluation_failures  = self.evaluation_failures,
                _total_evaluation_ms = self._total_evaluation_ms,
                _total_detection_ms  = self._total_detection_ms,
                _detection_count     = self._detection_count,
                last_updated_at      = self.last_updated_at,
            )
        return s

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "alerts_generated":          self.alerts_generated,
                "alerts_acknowledged":        self.alerts_acknowledged,
                "alerts_resolved":            self.alerts_resolved,
                "alerts_escalated":           self.alerts_escalated,
                "alerts_expired":             self.alerts_expired,
                "alerts_suppressed":          self.alerts_suppressed,
                "critical_alerts":            self.critical_alerts,
                "emergency_alerts":           self.emergency_alerts,
                "evaluation_count":           self.evaluation_count,
                "evaluation_failures":        self.evaluation_failures,
                "average_evaluation_time_ms": self.average_evaluation_time_ms,
                "average_detection_time_ms":  self.average_detection_time_ms,
                "resolution_rate":            self.resolution_rate,
                "escalation_rate":            self.escalation_rate,
                "suppression_rate":           self.suppression_rate,
                "last_updated_at":            self.last_updated_at,
            }
