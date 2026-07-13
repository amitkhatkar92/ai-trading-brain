"""iios/investment/strategy/learning/degradation_detector.py
DegradationDetector — detects and classifies performance degradation.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.drift_detector import DriftDetector, DriftSignal
from iios.investment.strategy.learning.degradation_statistics import (
    degradation_score, max_drawdown_from_scores, is_statistically_significant
)
from iios.investment.strategy.learning.learning_statistics import clamp


class DegradationLevel(str, Enum):
    NONE     = "none"
    MILD     = "mild"
    MODERATE = "moderate"
    SEVERE   = "severe"
    CRITICAL = "critical"


@dataclass(frozen=True)
class DegradationReport:
    """
    Point-in-time degradation assessment.
    Combines drift signals into an overall degradation level.
    """
    strategy_id:        str
    assessed_at:        datetime

    level:              DegradationLevel
    degradation_score:  float        # 0-100; 0 = no degradation
    drift_signals:      List[DriftSignal]
    significant_drifts: List[str]    # DriftType values that are significant

    # Detailed per-dimension scores
    performance_degradation: float
    risk_degradation:        float
    signal_degradation:      float

    is_actionable:    bool           # true if degradation requires attention
    recovery_possible: bool          # heuristic: can it self-recover?

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":             self.strategy_id,
            "assessed_at":             self.assessed_at.isoformat(),
            "level":                   self.level.value,
            "degradation_score":       round(self.degradation_score, 2),
            "significant_drifts":      self.significant_drifts,
            "performance_degradation": round(self.performance_degradation, 2),
            "risk_degradation":        round(self.risk_degradation, 2),
            "signal_degradation":      round(self.signal_degradation, 2),
            "is_actionable":           self.is_actionable,
            "recovery_possible":       self.recovery_possible,
        }


class DegradationDetector:
    """
    Detects performance degradation by comparing baseline vs recent windows.
    Severity thresholds are configurable via constructor.
    """

    def __init__(
        self,
        mild_threshold:     float = 0.05,
        moderate_threshold: float = 0.15,
        severe_threshold:   float = 0.25,
        critical_threshold: float = 0.40,
        drift_window:       int   = 10,
        baseline_window:    int   = 10,
    ) -> None:
        self._mild     = mild_threshold
        self._moderate = moderate_threshold
        self._severe   = severe_threshold
        self._critical = critical_threshold
        self._drift_window    = drift_window
        self._baseline_window = baseline_window
        self._drift_detector  = DriftDetector(mild_threshold=mild_threshold)

    def detect(
        self, observations: List[LearningObservation]
    ) -> Optional[DegradationReport]:
        if len(observations) < self._baseline_window + 1:
            return None

        sid       = observations[0].strategy_id
        baseline  = observations[:self._baseline_window]
        recent    = observations[-self._drift_window:]

        b_scores = [o.evaluation_score for o in baseline]
        r_scores = [o.evaluation_score for o in recent]
        b_risks  = [o.risk_score       for o in baseline]
        r_risks  = [o.risk_score       for o in recent]
        b_sharpe = [o.sharpe_ratio     for o in baseline]
        r_sharpe = [o.sharpe_ratio     for o in recent]

        b_mean_score  = statistics.mean(b_scores)
        r_mean_score  = statistics.mean(r_scores)
        b_mean_risk   = statistics.mean(b_risks)
        r_mean_risk   = statistics.mean(r_risks)
        b_mean_sharpe = statistics.mean(b_sharpe) if b_sharpe else 0.0
        r_mean_sharpe = statistics.mean(r_sharpe) if r_sharpe else 0.0

        perf_deg = degradation_score(b_mean_score, r_mean_score, self._critical)
        risk_deg = degradation_score(b_mean_risk,  r_mean_risk,  self._critical * 1.5) \
                   if r_mean_risk > b_mean_risk else 0.0
        sig_deg  = degradation_score(b_mean_sharpe, r_mean_sharpe, self._critical) \
                   if b_mean_sharpe > 0 else 0.0

        composite = clamp(
            0.55 * perf_deg
            + 0.25 * risk_deg
            + 0.20 * sig_deg
        )

        # Drift signals
        drift_signals = self._drift_detector.detect(baseline, recent)
        significant = [s.drift_type.value for s in drift_signals if s.is_significant]

        # Level from composite score
        level = self._classify(composite)

        recovery_possible = (
            level in (DegradationLevel.MILD, DegradationLevel.MODERATE)
            and statistics.mean(r_scores[-3:]) > r_mean_score   # last 3 trending up
            if len(r_scores) >= 3 else True
        )

        return DegradationReport(
            strategy_id=sid,
            assessed_at=datetime.now(timezone.utc),
            level=level,
            degradation_score=composite,
            drift_signals=drift_signals,
            significant_drifts=significant,
            performance_degradation=perf_deg,
            risk_degradation=risk_deg,
            signal_degradation=sig_deg,
            is_actionable=level != DegradationLevel.NONE,
            recovery_possible=recovery_possible,
        )

    def _classify(self, score: float) -> DegradationLevel:
        pct = score / 100.0
        if pct < self._mild:       return DegradationLevel.NONE
        if pct < self._moderate:   return DegradationLevel.MILD
        if pct < self._severe:     return DegradationLevel.MODERATE
        if pct < self._critical:   return DegradationLevel.SEVERE
        return DegradationLevel.CRITICAL
