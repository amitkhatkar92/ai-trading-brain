"""iios/investment/strategy/learning/learning_confidence.py
LearningConfidence — quantifies how much trust to place in learning outputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_profile import StrategyLearningProfile
from iios.investment.strategy.learning.learning_policy import LearningPolicy, DEFAULT_POLICY
from iios.investment.strategy.learning.learning_statistics import clamp


@dataclass(frozen=True)
class LearningConfidence:
    """Confidence in the learning outputs for a strategy."""
    strategy_id:      str
    assessed_at:      datetime

    data_sufficiency:  float   # enough observations? (0-100)
    pattern_stability: float   # patterns consistent? (0-100)
    regime_coverage:   float   # all regimes tested? (0-100)
    temporal_coverage: float   # history long enough? (0-100)
    overall_confidence: float  # weighted composite (0-100)
    grade:             str     # HIGH / MEDIUM / LOW

    @property
    def is_reliable(self) -> bool:
        return self.overall_confidence >= 70.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":       self.strategy_id,
            "assessed_at":       self.assessed_at.isoformat(),
            "data_sufficiency":  round(self.data_sufficiency, 2),
            "pattern_stability": round(self.pattern_stability, 2),
            "regime_coverage":   round(self.regime_coverage, 2),
            "temporal_coverage": round(self.temporal_coverage, 2),
            "overall_confidence": round(self.overall_confidence, 2),
            "grade":             self.grade,
        }

    @classmethod
    def compute(
        cls,
        profile:      StrategyLearningProfile,
        observations: List[LearningObservation],
        policy:       LearningPolicy = DEFAULT_POLICY,
    ) -> "LearningConfidence":
        n_obs = len(observations)
        sid   = profile.strategy_id

        # Data sufficiency: reaches 100 when we have 2× baseline_window observations
        data_suf = clamp(
            min(n_obs / (2 * policy.baseline_window), 1.0) * 100.0
        )

        # Pattern stability: based on score consistency in the profile
        from iios.investment.strategy.learning.learning_statistics import consistency_score
        pattern_stability = clamp(
            consistency_score(profile.recent_scores)
            if profile.observation_count >= 5 else 0.0
        )

        # Regime coverage: unique regimes seen vs expected diversity
        unique_regimes = len(set(
            o.current_regime for o in observations
            if o.current_regime and o.current_regime != "unknown"
        ))
        # Expect at least 3 distinct regimes for good coverage
        regime_cov = clamp(min(unique_regimes / 3.0, 1.0) * 100.0)

        # Temporal coverage: observations spread over time
        if len(observations) >= 2:
            t_first = observations[0].observed_at
            t_last  = observations[-1].observed_at
            age_days = max((t_last - t_first).days, 0)
            # 30 days = 50%, 90 days = 100%
            temporal_cov = clamp(min(age_days / 90.0, 1.0) * 100.0)
        else:
            temporal_cov = 0.0

        overall = clamp(
            0.40 * data_suf
            + 0.25 * pattern_stability
            + 0.20 * regime_cov
            + 0.15 * temporal_cov
        )

        grade = (
            "HIGH"   if overall >= 70.0 else
            "MEDIUM" if overall >= 40.0 else
            "LOW"
        )

        return cls(
            strategy_id=sid,
            assessed_at=datetime.now(timezone.utc),
            data_sufficiency=data_suf,
            pattern_stability=pattern_stability,
            regime_coverage=regime_cov,
            temporal_coverage=temporal_cov,
            overall_confidence=overall,
            grade=grade,
        )
