"""iios/investment/portfolio/performance/performance_profile.py

PerformanceProfile: the primary output of the Portfolio Performance Engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.investment.portfolio.performance.performance_types import (
    PerformanceGrade, PerformanceLevel, PerformanceTrend,
)


@dataclass(frozen=True)
class PerformanceProfile:
    """
    Full performance evaluation output for a single portfolio run.

    This is the canonical output of PortfolioPerformanceEngine.evaluate().
    All monetary/ratio values are floats. Timestamps are ISO-8601 UTC strings.
    """

    profile_id:            str = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:          str = ""
    plan_id:               str = ""
    version:               str = "1.0.0"
    created_at:            str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Position metadata
    n_positions:           int   = 0
    period_years:          float = 1.0
    currency:              str   = "INR"

    # ------- Return analysis -------
    total_period_return:   float = 0.0   # actual or estimated
    annualized_return:     float = 0.0
    excess_return:         float = 0.0   # over risk-free
    expected_return:       float = 0.0   # conviction-based

    # ------- Benchmark -------
    benchmark_id:          str   = "nifty50"
    benchmark_return:      float = 0.0
    active_return:         float = 0.0   # over benchmark
    alpha:                 float = 0.0   # Jensen's alpha
    beta:                  float = 0.0
    tracking_error:        float = 0.0
    information_ratio:     float = 0.0
    outperforms_benchmark: bool  = False

    # ------- Attribution -------
    allocation_effect:     float = 0.0
    selection_effect:      float = 0.0
    interaction_effect:    float = 0.0
    top_sector:            str   = ""
    dominant_factor:       str   = ""
    best_strategy:         str   = ""

    # ------- Risk-adjusted -------
    annual_vol:            float = 0.0
    sharpe_ratio:          float = 0.0
    sortino_ratio:         float = 0.0
    treynor_ratio:         float = 0.0
    calmar_ratio:          float = 0.0
    omega_ratio:           float = 0.0
    max_drawdown_proxy:    float = 0.0

    # ------- Extended ratios -------
    modigliani_ratio:      float = 0.0
    upside_potential_ratio:float = 0.0

    # ------- Scoring -------
    overall_performance_score: float             = 0.0   # [0, 1]
    performance_grade:         PerformanceGrade  = PerformanceGrade.F
    performance_level:         PerformanceLevel  = PerformanceLevel.POOR
    performance_trend:         PerformanceTrend  = PerformanceTrend.INSUFFICIENT
    is_acceptable:             bool              = False
    primary_weakness:          str               = ""
    recommendation:            str               = ""

    # ------- Forecasts -------
    expected_return_1y:        float = 0.0
    prob_positive_1y:          float = 0.0

    # ------- Confidence -------
    confidence_score:          float = 0.0
    n_alerts:                  int   = 0

    # ------- Metadata -------
    metadata:                  Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id":             self.profile_id,
            "portfolio_id":           self.portfolio_id,
            "created_at":             self.created_at,
            "n_positions":            self.n_positions,
            "period_years":           self.period_years,

            "total_period_return":    round(self.total_period_return, 4),
            "annualized_return":      round(self.annualized_return, 4),
            "excess_return":          round(self.excess_return, 4),
            "alpha":                  round(self.alpha, 4),
            "beta":                   round(self.beta, 4),
            "tracking_error":         round(self.tracking_error, 4),
            "information_ratio":      round(self.information_ratio, 4),
            "outperforms_benchmark":  self.outperforms_benchmark,

            "sharpe_ratio":           round(self.sharpe_ratio, 4),
            "sortino_ratio":          round(self.sortino_ratio, 4),
            "calmar_ratio":           round(self.calmar_ratio, 4),
            "annual_vol":             round(self.annual_vol, 4),

            "overall_performance_score": round(self.overall_performance_score, 4),
            "performance_grade":      self.performance_grade.value,
            "performance_level":      self.performance_level.value,
            "is_acceptable":          self.is_acceptable,
            "confidence_score":       round(self.confidence_score, 4),
            "recommendation":         self.recommendation,
        }
