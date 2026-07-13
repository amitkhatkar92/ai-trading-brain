"""iios/investment/strategy/learning/strategy_maturity.py
StrategyMaturity — assesses how mature a strategy's learning is.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from iios.investment.strategy.learning.learning_input import LearningObservation
from iios.investment.strategy.learning.learning_profile import StrategyLearningProfile
from iios.investment.strategy.learning.learning_statistics import clamp, consistency_score


class MaturityLevel(str, Enum):
    NASCENT     = "nascent"       # < 10 observations
    DEVELOPING  = "developing"    # 10-49
    ESTABLISHED = "established"   # 50-199
    MATURE      = "mature"        # 200-999
    VETERAN     = "veteran"       # 1000+


@dataclass(frozen=True)
class StrategyMaturity:
    """
    Maturity assessment for a strategy's learning history.
    Higher maturity = more confidence in learning outputs.
    """
    strategy_id:        str
    assessed_at:        datetime
    level:              MaturityLevel
    observation_count:  int
    learning_age_days:  int
    regime_breadth:     float       # 0-100 (unique regimes / 3)
    consistency_score_val: float    # 0-100
    maturity_score:     float       # 0-100 composite
    next_milestone:     str         # human-readable next goal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":       self.strategy_id,
            "assessed_at":       self.assessed_at.isoformat(),
            "level":             self.level.value,
            "observation_count": self.observation_count,
            "learning_age_days": self.learning_age_days,
            "regime_breadth":    round(self.regime_breadth, 2),
            "consistency_score": round(self.consistency_score_val, 2),
            "maturity_score":    round(self.maturity_score, 2),
            "next_milestone":    self.next_milestone,
        }


class MaturityAssessor:
    """Derives strategy maturity from observation count and learning history."""

    def assess(
        self,
        profile:      StrategyLearningProfile,
        observations: List[LearningObservation],
    ) -> StrategyMaturity:
        n_obs = len(observations)
        sid   = profile.strategy_id

        # Determine level
        level = self._level(n_obs)

        # Learning age in days
        if len(observations) >= 2:
            age_days = max((observations[-1].observed_at - observations[0].observed_at).days, 0)
        else:
            age_days = 0

        # Regime breadth
        unique_regimes = len(set(
            o.current_regime for o in observations
            if o.current_regime and o.current_regime != "unknown"
        ))
        regime_breadth = clamp(min(unique_regimes / 3.0, 1.0) * 100.0)

        # Score consistency
        recent_scores = [o.evaluation_score for o in observations[-50:]]
        cons_score    = consistency_score(recent_scores) if len(recent_scores) >= 5 else 0.0

        # Composite maturity score
        obs_component   = clamp(min(n_obs / 200.0, 1.0) * 100.0)   # caps at 200+
        age_component   = clamp(min(age_days / 90.0, 1.0) * 100.0) # caps at 90 days
        maturity_score  = clamp(
            0.40 * obs_component
            + 0.25 * age_component
            + 0.20 * regime_breadth
            + 0.15 * cons_score
        )

        milestone = self._next_milestone(n_obs, level)

        return StrategyMaturity(
            strategy_id=sid,
            assessed_at=datetime.now(timezone.utc),
            level=level,
            observation_count=n_obs,
            learning_age_days=age_days,
            regime_breadth=regime_breadth,
            consistency_score_val=cons_score,
            maturity_score=maturity_score,
            next_milestone=milestone,
        )

    @staticmethod
    def _level(n_obs: int) -> MaturityLevel:
        if n_obs < 10:   return MaturityLevel.NASCENT
        if n_obs < 50:   return MaturityLevel.DEVELOPING
        if n_obs < 200:  return MaturityLevel.ESTABLISHED
        if n_obs < 1000: return MaturityLevel.MATURE
        return MaturityLevel.VETERAN

    @staticmethod
    def _next_milestone(n_obs: int, level: MaturityLevel) -> str:
        thresholds = {
            MaturityLevel.NASCENT:     (10,   "developing"),
            MaturityLevel.DEVELOPING:  (50,   "established"),
            MaturityLevel.ESTABLISHED: (200,  "mature"),
            MaturityLevel.MATURE:      (1000, "veteran"),
        }
        if level == MaturityLevel.VETERAN:
            return "Veteran status achieved"
        needed_total, next_name = thresholds[level]
        remaining = needed_total - n_obs
        return f"{remaining} more observation(s) to reach {next_name}"
