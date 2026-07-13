"""iios/investment/strategy/learning/failure_pattern.py
FailurePattern — structural conditions observed during poor performance periods.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_statistics import clamp


@dataclass(frozen=True)
class FailurePattern:
    """An identified pattern associated with below-threshold performance."""
    pattern_id:        str
    strategy_id:       str
    name:              str
    description:       str
    conditions:        Dict[str, Any]
    failure_rate:      float          # fraction of failures among matching obs
    observation_count: int
    confidence:        float          # 0-1
    severity:          str            # mild / moderate / severe
    suggested_remedy:  str
    characteristic_regimes: List[str]
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id":       self.pattern_id,
            "name":             self.name,
            "description":      self.description,
            "failure_rate":     round(self.failure_rate, 3),
            "observation_count": self.observation_count,
            "confidence":       round(self.confidence, 3),
            "severity":         self.severity,
            "suggested_remedy": self.suggested_remedy,
            "conditions":       self.conditions,
            "regimes":          self.characteristic_regimes,
        }


class FailurePatternExtractor:
    """Identifies recurring conditions that correlate with poor evaluation scores."""

    def __init__(
        self,
        failure_threshold: float = 45.0,
        min_support:       int   = 3,
        min_confidence:    float = 0.60,
    ) -> None:
        self._threshold   = failure_threshold
        self._min_support = min_support
        self._min_conf    = min_confidence

    def extract(self, observations: List[LearningObservation]) -> List[FailurePattern]:
        failures = [o for o in observations if o.evaluation_score < self._threshold]
        if len(failures) < self._min_support:
            return []

        patterns: List[FailurePattern] = []
        patterns += self._regime_mismatch_patterns(observations, failures)
        patterns += self._high_drawdown_patterns(observations, failures)
        patterns += self._low_win_rate_patterns(observations, failures)
        patterns += self._volatility_patterns(observations, failures)
        return patterns

    def _regime_mismatch_patterns(
        self,
        all_obs: List[LearningObservation],
        failures: List[LearningObservation],
    ) -> List[FailurePattern]:
        mismatched = [o for o in failures if o.regime_mismatch]
        if len(mismatched) < self._min_support:
            return []
        all_mismatched = [o for o in all_obs if o.regime_mismatch]
        failure_rate = len(mismatched) / max(len(all_mismatched), 1)
        if failure_rate < self._min_conf:
            return []
        regimes = list(set(o.current_regime for o in mismatched))
        return [FailurePattern(
            pattern_id=str(uuid.uuid4()),
            strategy_id=failures[0].strategy_id,
            name="regime_mismatch_failure",
            description="Strategy underperforms when deployed in unsupported market regimes",
            conditions={"regime_mismatch": True},
            failure_rate=failure_rate,
            observation_count=len(mismatched),
            confidence=min(failure_rate, 1.0),
            severity="moderate",
            suggested_remedy="Restrict deployment to supported regimes or extend regime support",
            characteristic_regimes=regimes,
        )]

    def _high_drawdown_patterns(
        self,
        all_obs: List[LearningObservation],
        failures: List[LearningObservation],
    ) -> List[FailurePattern]:
        high_dd = [o for o in failures if o.max_drawdown > 0.25]
        if len(high_dd) < self._min_support:
            return []
        all_high = [o for o in all_obs if o.max_drawdown > 0.25]
        failure_rate = len(high_dd) / max(len(all_high), 1)
        if failure_rate < self._min_conf:
            return []
        return [FailurePattern(
            pattern_id=str(uuid.uuid4()),
            strategy_id=failures[0].strategy_id,
            name="excessive_drawdown",
            description="Max drawdown >25% consistently associated with poor performance",
            conditions={"max_drawdown_gt": 0.25},
            failure_rate=failure_rate,
            observation_count=len(high_dd),
            confidence=min(failure_rate, 1.0),
            severity="severe",
            suggested_remedy="Review stop-loss logic and position sizing; consider tighter risk limits",
            characteristic_regimes=list(set(o.current_regime for o in high_dd)),
        )]

    def _low_win_rate_patterns(
        self,
        all_obs: List[LearningObservation],
        failures: List[LearningObservation],
    ) -> List[FailurePattern]:
        low_wr = [o for o in failures if o.win_rate < 0.40]
        if len(low_wr) < self._min_support:
            return []
        all_low = [o for o in all_obs if o.win_rate < 0.40]
        failure_rate = len(low_wr) / max(len(all_low), 1)
        if failure_rate < self._min_conf:
            return []
        return [FailurePattern(
            pattern_id=str(uuid.uuid4()),
            strategy_id=failures[0].strategy_id,
            name="low_win_rate",
            description="Win rate <40% strongly correlated with below-threshold performance",
            conditions={"win_rate_lt": 0.40},
            failure_rate=failure_rate,
            observation_count=len(low_wr),
            confidence=min(failure_rate, 1.0),
            severity="moderate",
            suggested_remedy="Review entry signal quality; consider tightening entry filters",
            characteristic_regimes=list(set(o.current_regime for o in low_wr)),
        )]

    def _volatility_patterns(
        self,
        all_obs: List[LearningObservation],
        failures: List[LearningObservation],
    ) -> List[FailurePattern]:
        high_vol = [o for o in failures if o.current_volatility_level in ("high", "extreme")]
        if len(high_vol) < self._min_support:
            return []
        all_high_vol = [o for o in all_obs if o.current_volatility_level in ("high", "extreme")]
        failure_rate = len(high_vol) / max(len(all_high_vol), 1)
        if failure_rate < self._min_conf:
            return []
        return [FailurePattern(
            pattern_id=str(uuid.uuid4()),
            strategy_id=failures[0].strategy_id,
            name="high_volatility_failure",
            description="Strategy underperforms in high or extreme volatility environments",
            conditions={"volatility_level": ["high", "extreme"]},
            failure_rate=failure_rate,
            observation_count=len(high_vol),
            confidence=min(failure_rate, 1.0),
            severity="mild",
            suggested_remedy="Reduce position sizes during elevated volatility periods",
            characteristic_regimes=list(set(o.current_regime for o in high_vol)),
        )]
