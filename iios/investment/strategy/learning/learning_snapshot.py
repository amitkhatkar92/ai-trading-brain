"""iios/investment/strategy/learning/learning_snapshot.py
LearningSnapshot — immutable point-in-time capture of a strategy's learning state.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.strategy.learning.learning_profile import StrategyLearningProfile


@dataclass(frozen=True)
class LearningSnapshot:
    """Immutable learning-state snapshot. Used for history and auditing."""
    snapshot_id:       str
    strategy_id:       str
    strategy_name:     str
    captured_at:       datetime

    # Core state
    observation_count: int
    maturity_level:    str
    baseline_established: bool
    baseline_score:    float
    smoothed_score:    float
    score_trend:       float
    risk_trend:        float
    best_regime:       str
    worst_regime:      str
    degradation_level: str
    learning_version:  int

    # Computed at snapshot time (injected by caller)
    learning_score:     float = 0.0
    degradation_score:  float = 0.0
    adaptability_score: float = 0.0

    @classmethod
    def from_profile(
        cls,
        profile:           StrategyLearningProfile,
        learning_score:    float = 0.0,
        degradation_score: float = 0.0,
        adaptability_score: float = 0.0,
    ) -> "LearningSnapshot":
        return cls(
            snapshot_id=str(uuid.uuid4()),
            strategy_id=profile.strategy_id,
            strategy_name=profile.strategy_name,
            captured_at=datetime.now(timezone.utc),
            observation_count=profile.observation_count,
            maturity_level=profile.maturity_level,
            baseline_established=profile.baseline_established,
            baseline_score=profile.baseline_score,
            smoothed_score=profile.smoothed_score,
            score_trend=profile.score_trend,
            risk_trend=profile.risk_trend,
            best_regime=profile.best_regime,
            worst_regime=profile.worst_regime,
            degradation_level=profile.degradation_level,
            learning_version=profile.learning_version,
            learning_score=learning_score,
            degradation_score=degradation_score,
            adaptability_score=adaptability_score,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":         self.snapshot_id,
            "strategy_id":         self.strategy_id,
            "captured_at":         self.captured_at.isoformat(),
            "observation_count":   self.observation_count,
            "maturity_level":      self.maturity_level,
            "baseline_established": self.baseline_established,
            "baseline_score":      round(self.baseline_score, 2),
            "smoothed_score":      round(self.smoothed_score, 2),
            "score_trend":         round(self.score_trend, 4),
            "risk_trend":          round(self.risk_trend, 4),
            "best_regime":         self.best_regime,
            "worst_regime":        self.worst_regime,
            "degradation_level":   self.degradation_level,
            "learning_version":    self.learning_version,
            "learning_score":      round(self.learning_score, 2),
            "degradation_score":   round(self.degradation_score, 2),
            "adaptability_score":  round(self.adaptability_score, 2),
        }
