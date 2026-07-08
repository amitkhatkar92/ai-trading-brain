"""
iios/intelligence/governance/monitoring/drift_detector.py
==========================================================
DriftDetector — tracks quality/confidence samples and fires alerts when
rolling variance exceeds configured thresholds.
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from ..quality_constants import (
    CONFIDENCE_DRIFT_THRESHOLD,
    DRIFT_WINDOW_N,
    QUALITY_DRIFT_THRESHOLD,
    DriftType,
)
from ..quality_exceptions import DriftAlertError


@dataclass
class DriftAlert:
    """Fired when a rolling metric diverges beyond its threshold."""

    alert_id:   str       = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:  str       = ""
    drift_type: DriftType = DriftType.QUALITY
    baseline:   float     = 0.0
    current:    float     = 0.0
    delta:      float     = 0.0
    severity:   str       = "warning"       # warning | critical
    triggered_at: float   = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id":     self.alert_id,
            "source_id":    self.source_id,
            "drift_type":   self.drift_type.value,
            "baseline":     round(self.baseline, 4),
            "current":      round(self.current, 4),
            "delta":        round(self.delta, 4),
            "severity":     self.severity,
            "triggered_at": self.triggered_at,
        }


class DriftDetector:
    """
    Per-source sliding window drift detector.
    Call ``record_sample()`` after every evaluation; it returns any alerts.
    """

    def __init__(
        self,
        window_n:           int   = DRIFT_WINDOW_N,
        quality_threshold:  float = QUALITY_DRIFT_THRESHOLD,
        confidence_threshold: float = CONFIDENCE_DRIFT_THRESHOLD,
    ) -> None:
        self._window:           int   = window_n
        self._quality_thr:      float = quality_threshold
        self._confidence_thr:   float = confidence_threshold

        # source_id → deque of (quality_score, confidence_score)
        self._quality_buf:     dict[str, deque[float]] = {}
        self._confidence_buf:  dict[str, deque[float]] = {}
        self._alerts:          dict[str, list[DriftAlert]] = {}
        self._lock:            threading.RLock = threading.RLock()

    def record_sample(
        self,
        source_id:        str,
        quality_score:    float,
        confidence_score: float,
    ) -> list[DriftAlert]:
        fired: list[DriftAlert] = []

        with self._lock:
            if source_id not in self._quality_buf:
                self._quality_buf[source_id]    = deque(maxlen=self._window * 2)
                self._confidence_buf[source_id] = deque(maxlen=self._window * 2)
                self._alerts[source_id]         = []

            qbuf = self._quality_buf[source_id]
            cbuf = self._confidence_buf[source_id]
            qbuf.append(quality_score)
            cbuf.append(confidence_score)

            # Need at least window_n * 2 samples to split into baseline vs current
            n = self._window
            if len(qbuf) >= n * 2:
                q_list = list(qbuf)
                c_list = list(cbuf)
                q_base    = sum(q_list[:n]) / n
                q_current = sum(q_list[n:]) / max(len(q_list) - n, 1)
                c_base    = sum(c_list[:n]) / n
                c_current = sum(c_list[n:]) / max(len(c_list) - n, 1)

                q_delta = abs(q_base - q_current)
                c_delta = abs(c_base - c_current)

                if q_delta >= self._quality_thr:
                    alert = DriftAlert(
                        source_id  = source_id,
                        drift_type = DriftType.QUALITY,
                        baseline   = q_base,
                        current    = q_current,
                        delta      = q_delta,
                        severity   = "critical" if q_delta >= self._quality_thr * 2 else "warning",
                    )
                    self._alerts[source_id].append(alert)
                    fired.append(alert)

                if c_delta >= self._confidence_thr:
                    alert = DriftAlert(
                        source_id  = source_id,
                        drift_type = DriftType.CONFIDENCE,
                        baseline   = c_base,
                        current    = c_current,
                        delta      = c_delta,
                        severity   = "critical" if c_delta >= self._confidence_thr * 2 else "warning",
                    )
                    self._alerts[source_id].append(alert)
                    fired.append(alert)

        return fired

    def get_alerts(self, source_id: str) -> list[DriftAlert]:
        with self._lock:
            return list(self._alerts.get(source_id, []))

    def all_alerts(self) -> list[DriftAlert]:
        with self._lock:
            out: list[DriftAlert] = []
            for alerts in self._alerts.values():
                out.extend(alerts)
            return out

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "monitored_sources": len(self._quality_buf),
                "total_alerts":      sum(len(v) for v in self._alerts.values()),
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:     threading.Lock           = threading.Lock()
_DETECTOR: DriftDetector | None    = None


def get_drift_detector() -> DriftDetector:
    global _DETECTOR
    if _DETECTOR is None:
        with _LOCK:
            if _DETECTOR is None:
                _DETECTOR = DriftDetector()
    return _DETECTOR


def reset_drift_detector() -> None:
    global _DETECTOR
    with _LOCK:
        _DETECTOR = None
