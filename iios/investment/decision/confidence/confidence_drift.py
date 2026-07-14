"""iios/investment/decision/confidence/confidence_drift.py
ConfidenceDriftDetector — measures whether confidence has drifted from its baseline.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from iios.investment.decision.confidence.confidence_constants import (
    DriftSeverity,
    DRIFT_THRESHOLD_MINOR,
    DRIFT_THRESHOLD_MODERATE,
    DRIFT_THRESHOLD_SEVERE,
)


@dataclass(frozen=True)
class DriftResult:
    baseline_mean:   float
    current_mean:    float
    absolute_drift:  float    # current - baseline (signed)
    relative_drift:  float    # % change  (signed)
    severity:        DriftSeverity
    drift_score:     float    # 0–100 (0 = no drift, 100 = maximum drift)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_mean":  round(self.baseline_mean, 2),
            "current_mean":   round(self.current_mean, 2),
            "absolute_drift": round(self.absolute_drift, 2),
            "relative_drift": round(self.relative_drift, 4),
            "severity":       self.severity.value,
            "drift_score":    round(self.drift_score, 2),
        }


class ConfidenceDriftDetector:
    """
    Detects confidence drift by comparing a recent window against a baseline window.
    """

    def detect(
        self,
        series:          List[float],
        baseline_window: int = 30,
        recent_window:   int = 5,
    ) -> DriftResult:
        n = len(series)

        if n < 2:
            score = series[0] if n == 1 else 0.0
            return DriftResult(
                baseline_mean=score, current_mean=score,
                absolute_drift=0.0, relative_drift=0.0,
                severity=DriftSeverity.NONE, drift_score=0.0,
            )

        baseline_slice = series[:baseline_window]
        recent_slice   = series[-recent_window:]

        baseline_mean = statistics.mean(baseline_slice)
        current_mean  = statistics.mean(recent_slice)
        absolute_drift = current_mean - baseline_mean
        relative_drift = (
            absolute_drift / baseline_mean if baseline_mean != 0 else 0.0
        )

        abs_drift = abs(absolute_drift)

        if abs_drift < DRIFT_THRESHOLD_MINOR:
            severity = DriftSeverity.NONE
        elif abs_drift < DRIFT_THRESHOLD_MODERATE:
            severity = DriftSeverity.MINOR
        elif abs_drift < DRIFT_THRESHOLD_SEVERE:
            severity = DriftSeverity.MODERATE
        else:
            severity = DriftSeverity.SEVERE

        # Drift score: scales 0–100 linearly within SEVERE threshold
        drift_score = min(100.0, (abs_drift / DRIFT_THRESHOLD_SEVERE) * 100.0)

        return DriftResult(
            baseline_mean=round(baseline_mean, 4),
            current_mean=round(current_mean, 4),
            absolute_drift=round(absolute_drift, 4),
            relative_drift=round(relative_drift, 6),
            severity=severity,
            drift_score=round(drift_score, 4),
        )
