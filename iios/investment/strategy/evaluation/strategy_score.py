"""iios/investment/strategy/evaluation/strategy_score.py
Evaluation score model produced by StrategyEvaluator.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.strategy.strategy_constants import (
    StrategyGrade,
    StrategyRecommendation,
)


@dataclass
class StrategyScore:
    """
    Evaluation score for a single strategy at a single point in time.

    Sub-scores are 0–100 (higher = better).
    confidence_score reflects data sufficiency (0–100).
    """

    score_id:            str                  = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id:         str                  = ""
    strategy_name:       str                  = ""

    # Composite score (weighted sum of sub-scores)
    overall_score:       float                = 50.0

    # Sub-dimension scores (0–100)
    performance_score:   float                = 50.0
    risk_score:          float                = 50.0
    stability_score:     float                = 50.0
    regime_score:        float                = 50.0
    confidence_score:    float                = 0.0      # 0 = no data

    # Key metrics (raw)
    win_rate:            float                = 0.0
    sharpe_ratio:        float                = 0.0
    max_drawdown:        float                = 0.0
    avg_return:          float                = 0.0
    profit_factor:       float                = 0.0
    total_trades:        int                  = 0
    winning_trades:      int                  = 0

    # Evaluation outcome
    grade:               StrategyGrade        = StrategyGrade.UNKNOWN
    recommendation:      StrategyRecommendation = StrategyRecommendation.UNKNOWN

    metadata:            dict[str, Any]       = field(default_factory=dict)
    evaluated_at:        float                = field(default_factory=time.time)

    @property
    def is_above_threshold(self) -> bool:
        from iios.investment.strategy.strategy_constants import (
            MIN_WIN_RATE, MIN_SHARPE, MAX_DRAWDOWN
        )
        return (
            self.win_rate     >= MIN_WIN_RATE
            and self.sharpe_ratio >= MIN_SHARPE
            and self.max_drawdown <= MAX_DRAWDOWN
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_id":          self.score_id,
            "strategy_id":       self.strategy_id,
            "strategy_name":     self.strategy_name,
            "overall_score":     self.overall_score,
            "performance_score": self.performance_score,
            "risk_score":        self.risk_score,
            "stability_score":   self.stability_score,
            "regime_score":      self.regime_score,
            "confidence_score":  self.confidence_score,
            "win_rate":          self.win_rate,
            "sharpe_ratio":      self.sharpe_ratio,
            "max_drawdown":      self.max_drawdown,
            "avg_return":        self.avg_return,
            "profit_factor":     self.profit_factor,
            "total_trades":      self.total_trades,
            "winning_trades":    self.winning_trades,
            "grade":             self.grade.value,
            "recommendation":    self.recommendation.value,
            "is_above_threshold": self.is_above_threshold,
            "metadata":          self.metadata,
            "evaluated_at":      self.evaluated_at,
        }
