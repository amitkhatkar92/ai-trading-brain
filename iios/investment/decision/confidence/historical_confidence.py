"""iios/investment/decision/confidence/historical_confidence.py
HistoricalConfidenceAnalyzer — combines trend, evolution, and drift analyses.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from iios.investment.decision.confidence.confidence_drift import (
    ConfidenceDriftDetector,
    DriftResult,
)
from iios.investment.decision.confidence.confidence_evolution import (
    ConfidenceEvolutionTracker,
    EvolutionResult,
)
from iios.investment.decision.confidence.confidence_trends import (
    ConfidenceTrendAnalyzer,
    TrendResult,
)
from iios.investment.decision.confidence.confidence_constants import TrendDirection


@dataclass(frozen=True)
class HistoricalConfidenceResult:
    subject_id:        str
    sample_count:      int
    trend:             TrendResult
    drift:             DriftResult
    evolution:         Optional[EvolutionResult]
    stability_score:   float   # 0–100 (100 = perfectly stable)
    historical_conf:   float   # 0–100 contribution to overall confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_id":      self.subject_id,
            "sample_count":    self.sample_count,
            "stability_score": round(self.stability_score, 2),
            "historical_conf": round(self.historical_conf, 2),
            "trend":           self.trend.to_dict(),
            "drift":           self.drift.to_dict(),
            "evolution":       self.evolution.to_dict() if self.evolution else None,
        }


class HistoricalConfidenceAnalyzer:
    """
    Aggregates trend, drift, and evolution into a single historical confidence score.
    """

    def __init__(
        self,
        trend_analyzer:   Optional[ConfidenceTrendAnalyzer]    = None,
        drift_detector:   Optional[ConfidenceDriftDetector]    = None,
        evolution_tracker: Optional[ConfidenceEvolutionTracker] = None,
    ) -> None:
        self._trend  = trend_analyzer    or ConfidenceTrendAnalyzer()
        self._drift  = drift_detector    or ConfidenceDriftDetector()
        self._evol   = evolution_tracker or ConfidenceEvolutionTracker()

    def analyze(
        self,
        subject_id: str,
        series:     List[float],
        version:    int,
        current:    float,
    ) -> HistoricalConfidenceResult:
        # Record latest point in evolution
        self._evol.record(subject_id, version, current)

        n = len(series)

        if n == 0:
            # No history — neutral score
            from iios.investment.decision.confidence.confidence_constants import (
                DriftSeverity, DRIFT_THRESHOLD_MODERATE,
            )
            neutral_trend = self._trend.analyze([current])
            neutral_drift = self._drift.detect([current])
            return HistoricalConfidenceResult(
                subject_id=subject_id,
                sample_count=0,
                trend=neutral_trend,
                drift=neutral_drift,
                evolution=self._evol.evolution(subject_id),
                stability_score=50.0,
                historical_conf=50.0,
            )

        trend  = self._trend.analyze(series)
        drift  = self._drift.detect(series)
        evol   = self._evol.evolution(subject_id)

        # Stability: penalise high std_dev, volatile trend, severe drift
        stability = 100.0
        stability -= min(40.0, trend.std_dev * 2.0)
        if trend.direction == TrendDirection.VOLATILE:
            stability -= 20.0
        stability -= drift.drift_score * 0.30
        stability = max(0.0, stability)

        # Historical confidence
        # Stable + improving = high; declining or drifting = low
        direction_bonus = {
            TrendDirection.IMPROVING: 10.0,
            TrendDirection.STABLE:     5.0,
            TrendDirection.DECLINING: -10.0,
            TrendDirection.VOLATILE:  -20.0,
        }.get(trend.direction, 0.0)

        historical_conf = min(100.0, max(0.0,
            stability * 0.70
            + min(100.0, current) * 0.20
            + direction_bonus
            + 10.0 * (1.0 if n >= 10 else n / 10)
        ))

        return HistoricalConfidenceResult(
            subject_id=subject_id,
            sample_count=n,
            trend=trend,
            drift=drift,
            evolution=evol,
            stability_score=round(stability, 4),
            historical_conf=round(historical_conf, 4),
        )
