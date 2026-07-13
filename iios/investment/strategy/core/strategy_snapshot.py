"""iios/investment/strategy/core/strategy_snapshot.py
Point-in-time metric capture for a strategy.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.strategy.strategy_constants import (
    DEFAULT_SNAPSHOT_TTL_SEC,
    MarketRegime,
    StrategyGrade,
    StrategyRecommendation,
    StrategyStatus,
)


@dataclass
class StrategySnapshot:
    """
    Immutable point-in-time record of a strategy's key metrics.
    Created after each evaluation cycle and stored in StrategyHistory.
    """

    snapshot_id:      str                   = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id:      str                   = ""
    timestamp:        float                 = field(default_factory=time.time)

    # Lifecycle state at snapshot time
    status:           StrategyStatus        = StrategyStatus.UNKNOWN

    # Performance metrics (None = not yet computed)
    win_rate:         float | None          = None
    sharpe_ratio:     float | None          = None
    max_drawdown:     float | None          = None
    avg_return:       float | None          = None
    profit_factor:    float | None          = None
    total_trades:     int                   = 0

    # Evaluation
    overall_score:    float | None          = None
    grade:            StrategyGrade         = StrategyGrade.UNKNOWN
    recommendation:   StrategyRecommendation = StrategyRecommendation.UNKNOWN

    # Market context at snapshot time
    active_regime:    MarketRegime          = MarketRegime.UNKNOWN

    # Current parameters (possibly adapted from original)
    active_params:    dict[str, Any]        = field(default_factory=dict)

    metadata:         dict[str, Any]        = field(default_factory=dict)
    created_at:       float                 = field(default_factory=time.time)

    @property
    def age_sec(self) -> float:
        return time.time() - self.created_at

    def is_stale(self, ttl_sec: float = DEFAULT_SNAPSHOT_TTL_SEC) -> bool:
        return self.age_sec > ttl_sec

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":   self.snapshot_id,
            "strategy_id":   self.strategy_id,
            "timestamp":     self.timestamp,
            "status":        self.status.value,
            "win_rate":      self.win_rate,
            "sharpe_ratio":  self.sharpe_ratio,
            "max_drawdown":  self.max_drawdown,
            "avg_return":    self.avg_return,
            "profit_factor": self.profit_factor,
            "total_trades":  self.total_trades,
            "overall_score": self.overall_score,
            "grade":         self.grade.value,
            "recommendation": self.recommendation.value,
            "active_regime": self.active_regime.value,
            "active_params": self.active_params,
            "metadata":      self.metadata,
            "created_at":    self.created_at,
        }
