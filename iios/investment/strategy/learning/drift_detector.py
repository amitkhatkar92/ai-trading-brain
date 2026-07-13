"""iios/investment/strategy/learning/drift_detector.py
DriftDetector — detects and classifies performance drift across multiple dimensions.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_statistics import (
    clamp, z_score, drift_magnitude
)
from iios.investment.strategy.learning.degradation_statistics import is_statistically_significant


class DriftType(str, Enum):
    PERFORMANCE  = "performance"
    RISK         = "risk"
    EXECUTION    = "execution"
    SIGNAL       = "signal"
    REGIME       = "regime"
    CONFIDENCE   = "confidence"


@dataclass(frozen=True)
class DriftSignal:
    """A detected drift signal in a single dimension."""
    drift_type:    DriftType
    magnitude:     float    # 0-100; severity of drift
    direction:     str      # "degrading" | "improving" | "volatile"
    z_score_val:   float    # standardised deviation
    is_significant: bool    # statistically significant?
    description:   str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_type":   self.drift_type.value,
            "magnitude":    round(self.magnitude, 2),
            "direction":    self.direction,
            "z_score":      round(self.z_score_val, 3),
            "is_significant": self.is_significant,
            "description":  self.description,
        }


class DriftDetector:
    """
    Compares baseline and recent observation windows to produce typed drift signals.
    Stateless — call detect() with windows each time.
    """

    def __init__(
        self,
        mild_threshold:     float = 0.05,
        z_score_threshold:  float = 1.65,
    ) -> None:
        self._mild_thr = mild_threshold
        self._z_thr    = z_score_threshold

    def detect(
        self,
        baseline_obs: List[LearningObservation],
        recent_obs:   List[LearningObservation],
    ) -> List[DriftSignal]:
        if not baseline_obs or not recent_obs:
            return []

        signals: List[DriftSignal] = []

        signals += self._performance_drift(baseline_obs, recent_obs)
        signals += self._risk_drift(baseline_obs, recent_obs)
        signals += self._signal_drift(baseline_obs, recent_obs)
        signals += self._confidence_drift(baseline_obs, recent_obs)
        signals += self._regime_drift(baseline_obs, recent_obs)

        return signals

    # ── dimension detectors ───────────────────────────────────────────────────

    def _performance_drift(
        self,
        baseline: List[LearningObservation],
        recent: List[LearningObservation],
    ) -> List[DriftSignal]:
        b_scores = [o.evaluation_score for o in baseline]
        r_scores = [o.evaluation_score for o in recent]
        return self._make_signals(
            DriftType.PERFORMANCE, b_scores, r_scores,
            lambda drifted: "evaluation_score" if drifted else "stable",
            desc_template="Evaluation score has {dir} by {pct:.1%} from baseline",
            higher_is_better=True,
        )

    def _risk_drift(
        self,
        baseline: List[LearningObservation],
        recent: List[LearningObservation],
    ) -> List[DriftSignal]:
        b_risk = [o.risk_score for o in baseline]
        r_risk = [o.risk_score for o in recent]
        return self._make_signals(
            DriftType.RISK, b_risk, r_risk,
            lambda d: "risk_score",
            desc_template="Risk score has {dir} by {pct:.1%} from baseline",
            higher_is_better=False,    # lower risk = better
        )

    def _signal_drift(
        self,
        baseline: List[LearningObservation],
        recent: List[LearningObservation],
    ) -> List[DriftSignal]:
        b_sharpe = [o.sharpe_ratio for o in baseline]
        r_sharpe = [o.sharpe_ratio for o in recent]
        return self._make_signals(
            DriftType.SIGNAL, b_sharpe, r_sharpe,
            lambda d: "sharpe_ratio",
            desc_template="Sharpe ratio has {dir} by {pct:.1%} from baseline (signal quality proxy)",
            higher_is_better=True,
        )

    def _confidence_drift(
        self,
        baseline: List[LearningObservation],
        recent: List[LearningObservation],
    ) -> List[DriftSignal]:
        b_conf = [o.confidence_score for o in baseline]
        r_conf = [o.confidence_score for o in recent]
        return self._make_signals(
            DriftType.CONFIDENCE, b_conf, r_conf,
            lambda d: "confidence_score",
            desc_template="Confidence score has {dir} by {pct:.1%} from baseline",
            higher_is_better=True,
        )

    def _regime_drift(
        self,
        baseline: List[LearningObservation],
        recent: List[LearningObservation],
    ) -> List[DriftSignal]:
        b_mismatch = sum(1 for o in baseline if o.regime_mismatch) / len(baseline)
        r_mismatch = sum(1 for o in recent   if o.regime_mismatch) / len(recent)
        delta = r_mismatch - b_mismatch
        if abs(delta) < self._mild_thr:
            return []
        magnitude = clamp(abs(delta) * 200.0)   # 50% change → 100 magnitude
        direction = "degrading" if delta > 0 else "improving"
        sig = is_statistically_significant(
            [float(o.regime_mismatch) for o in baseline],
            [float(o.regime_mismatch) for o in recent],
            self._z_thr,
        )
        return [DriftSignal(
            drift_type=DriftType.REGIME,
            magnitude=magnitude,
            direction=direction,
            z_score_val=delta * 10.0,
            is_significant=sig,
            description=(
                f"Regime mismatch rate has {direction}: "
                f"{b_mismatch:.1%} (baseline) → {r_mismatch:.1%} (recent)"
            ),
        )]

    # ── helper ────────────────────────────────────────────────────────────────

    def _make_signals(
        self,
        drift_type: DriftType,
        baseline_vals: List[float],
        recent_vals:   List[float],
        namer,
        desc_template: str,
        higher_is_better: bool,
    ) -> List[DriftSignal]:
        if not baseline_vals or not recent_vals:
            return []
        b_mean = statistics.mean(baseline_vals)
        r_mean = statistics.mean(recent_vals)
        if abs(b_mean) < 1e-9:
            return []
        pct_change = (r_mean - b_mean) / abs(b_mean)
        if abs(pct_change) < self._mild_thr:
            return []

        magnitude = clamp(abs(pct_change) / 0.40 * 100.0)  # normalised to 40% = 100
        if higher_is_better:
            direction = "degrading" if pct_change < 0 else "improving"
        else:
            direction = "degrading" if pct_change > 0 else "improving"

        sig = is_statistically_significant(baseline_vals, recent_vals, self._z_thr)
        b_std = statistics.stdev(baseline_vals) if len(baseline_vals) >= 2 else 1.0
        z = z_score(r_mean, b_mean, b_std)

        return [DriftSignal(
            drift_type=drift_type,
            magnitude=magnitude,
            direction=direction,
            z_score_val=z,
            is_significant=sig,
            description=desc_template.format(dir=direction, pct=abs(pct_change)),
        )]
