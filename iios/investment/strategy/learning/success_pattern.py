"""iios/investment/strategy/learning/success_pattern.py
SuccessPattern — structural conditions observed during high-performance periods.
"""
from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_statistics import (
    above_threshold_rate, clamp, percentile
)


@dataclass(frozen=True)
class SuccessPattern:
    """An identified pattern associated with above-average performance."""
    pattern_id:          str
    strategy_id:         str
    name:                str
    description:         str
    conditions:          Dict[str, Any]   # what was true when this pattern appeared
    success_rate:        float            # fraction of successes among matching obs
    observation_count:   int              # how many observations support this
    confidence:          float            # 0-1
    characteristic_regimes:  List[str]
    characteristic_tags:     List[str]
    detected_at:         datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id":         self.pattern_id,
            "name":               self.name,
            "description":        self.description,
            "success_rate":       round(self.success_rate, 3),
            "observation_count":  self.observation_count,
            "confidence":         round(self.confidence, 3),
            "conditions":         self.conditions,
            "regimes":            self.characteristic_regimes,
            "tags":               self.characteristic_tags,
        }


class SuccessPatternExtractor:
    """
    Identifies recurring conditions that correlate with high evaluation scores.
    Operates on a list of LearningObservation objects.
    """

    def __init__(
        self,
        success_threshold:  float = 70.0,
        min_support:        int   = 3,
        min_confidence:     float = 0.60,
    ) -> None:
        self._threshold    = success_threshold
        self._min_support  = min_support
        self._min_conf     = min_confidence

    def extract(self, observations: List[LearningObservation]) -> List[SuccessPattern]:
        successes = [o for o in observations if o.evaluation_score >= self._threshold]
        if len(successes) < self._min_support:
            return []

        patterns: List[SuccessPattern] = []

        # Pattern 1: Regime alignment
        patterns += self._regime_alignment_patterns(observations, successes)

        # Pattern 2: Low drawdown + high win rate
        patterns += self._drawdown_win_rate_patterns(observations, successes)

        # Pattern 3: High risk-adjusted performance (sharpe)
        patterns += self._sharpe_patterns(observations, successes)

        # Pattern 4: Tag-specific success
        patterns += self._tag_patterns(observations, successes)

        return patterns

    def _regime_alignment_patterns(
        self,
        all_obs: List[LearningObservation],
        successes: List[LearningObservation],
    ) -> List[SuccessPattern]:
        patterns = []
        regimes_in_success: Dict[str, int] = {}
        for o in successes:
            if not o.regime_mismatch and o.current_regime != "unknown":
                regimes_in_success[o.current_regime] = regimes_in_success.get(o.current_regime, 0) + 1

        for regime, count in regimes_in_success.items():
            if count < self._min_support:
                continue
            all_in_regime = [o for o in all_obs if o.current_regime == regime]
            if not all_in_regime:
                continue
            success_rate = count / len(all_in_regime)
            if success_rate < self._min_conf:
                continue
            confidence = clamp(success_rate * count / max(len(all_obs), 1) * 10, 0.0, 1.0)
            patterns.append(SuccessPattern(
                pattern_id=str(uuid.uuid4()),
                strategy_id=successes[0].strategy_id,
                name=f"regime_alignment_{regime}",
                description=f"Strategy performs well in aligned {regime} regime",
                conditions={"regime": regime, "regime_mismatch": False},
                success_rate=success_rate,
                observation_count=count,
                confidence=min(confidence, 1.0),
                characteristic_regimes=[regime],
                characteristic_tags=list(set(t for o in successes for t in o.tags)),
            ))
        return patterns

    def _drawdown_win_rate_patterns(
        self,
        all_obs: List[LearningObservation],
        successes: List[LearningObservation],
    ) -> List[SuccessPattern]:
        controlled = [
            o for o in successes
            if o.max_drawdown < 0.15 and o.win_rate >= 0.55
        ]
        if len(controlled) < self._min_support:
            return []
        total_with_condition = [
            o for o in all_obs
            if o.max_drawdown < 0.15 and o.win_rate >= 0.55
        ]
        success_rate = len(controlled) / max(len(total_with_condition), 1)
        if success_rate < self._min_conf:
            return []
        return [SuccessPattern(
            pattern_id=str(uuid.uuid4()),
            strategy_id=successes[0].strategy_id,
            name="controlled_drawdown_high_win",
            description="Low drawdown (<15%) combined with high win rate (>55%) predicts success",
            conditions={"max_drawdown_lt": 0.15, "win_rate_gte": 0.55},
            success_rate=success_rate,
            observation_count=len(controlled),
            confidence=min(success_rate, 1.0),
            characteristic_regimes=list(set(o.current_regime for o in controlled)),
            characteristic_tags=list(set(t for o in controlled for t in o.tags)),
        )]

    def _sharpe_patterns(
        self,
        all_obs: List[LearningObservation],
        successes: List[LearningObservation],
    ) -> List[SuccessPattern]:
        high_sharpe = [o for o in successes if o.sharpe_ratio >= 1.5]
        if len(high_sharpe) < self._min_support:
            return []
        total = [o for o in all_obs if o.sharpe_ratio >= 1.5]
        success_rate = len(high_sharpe) / max(len(total), 1)
        if success_rate < self._min_conf:
            return []
        return [SuccessPattern(
            pattern_id=str(uuid.uuid4()),
            strategy_id=successes[0].strategy_id,
            name="high_sharpe_ratio",
            description="Sharpe ratio ≥ 1.5 strongly correlates with above-threshold performance",
            conditions={"sharpe_ratio_gte": 1.5},
            success_rate=success_rate,
            observation_count=len(high_sharpe),
            confidence=min(success_rate, 1.0),
            characteristic_regimes=list(set(o.current_regime for o in high_sharpe)),
            characteristic_tags=list(set(t for o in high_sharpe for t in o.tags)),
        )]

    def _tag_patterns(
        self,
        all_obs: List[LearningObservation],
        successes: List[LearningObservation],
    ) -> List[SuccessPattern]:
        patterns = []
        tag_success: Dict[str, List[LearningObservation]] = {}
        for o in successes:
            for tag in o.tags:
                tag_success.setdefault(tag, []).append(o)

        for tag, obs in tag_success.items():
            if len(obs) < self._min_support:
                continue
            all_with_tag = [o for o in all_obs if tag in o.tags]
            success_rate = len(obs) / max(len(all_with_tag), 1)
            if success_rate < self._min_conf:
                continue
            patterns.append(SuccessPattern(
                pattern_id=str(uuid.uuid4()),
                strategy_id=successes[0].strategy_id,
                name=f"tag_success_{tag}",
                description=f"Strategy tag '{tag}' associated with high performance",
                conditions={"tag": tag},
                success_rate=success_rate,
                observation_count=len(obs),
                confidence=min(success_rate, 1.0),
                characteristic_regimes=list(set(o.current_regime for o in obs)),
                characteristic_tags=[tag],
            ))
        return patterns
