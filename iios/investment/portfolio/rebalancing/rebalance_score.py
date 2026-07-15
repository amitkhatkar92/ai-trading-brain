"""iios/investment/portfolio/rebalancing/rebalance_score.py

Composite quality scoring for rebalancing plans.

Weights: drift_reduction=0.35, cost_efficiency=0.25, risk_improvement=0.20,
         diversification=0.10, tax_efficiency=0.10
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.rebalancing.allocation_drift import AllocationDrift
from iios.investment.portfolio.rebalancing.execution_estimator import ExecutionEstimate
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    DRIFT_THRESHOLD_CRITICAL, DRIFT_THRESHOLD_MODERATE,
    RebalanceGrade, RebalanceLevel,
    rebalance_score_to_grade, rebalance_score_to_level, TradeSide,
)
from iios.investment.portfolio.rebalancing.risk_drift import RiskDrift
from iios.investment.portfolio.rebalancing.trade_planner import TradePlan

_WEIGHTS = {
    "drift_reduction":   0.35,
    "cost_efficiency":   0.25,
    "risk_improvement":  0.20,
    "diversification":   0.10,
    "tax_efficiency":    0.10,
}


@dataclass(frozen=True)
class RebalanceDimensionScore:
    """Score for one quality dimension."""

    dimension:    str
    raw_value:    float = 0.0
    score:        float = 0.0    # [0, 1]
    weight:       float = 0.0
    contribution: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension":    self.dimension,
            "raw_value":    round(self.raw_value, 4),
            "score":        round(self.score, 4),
            "contribution": round(self.contribution, 4),
        }


@dataclass(frozen=True)
class RebalanceScore:
    """Composite quality score for a rebalancing plan."""

    result_id:         str           = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str           = ""

    overall:           float         = 0.0   # [0, 1]
    drift_red_score:   float         = 0.0
    cost_eff_score:    float         = 0.0
    risk_imp_score:    float         = 0.0
    div_score:         float         = 0.0
    tax_eff_score:     float         = 0.0

    grade:             RebalanceGrade = RebalanceGrade.F
    level:             RebalanceLevel = RebalanceLevel.POOR
    is_recommended:    bool           = False
    dimensions:        tuple          = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":       round(self.overall, 4),
            "grade":         self.grade.value,
            "level":         self.level.value,
            "is_recommended":self.is_recommended,
            "dimensions":    [d.to_dict() for d in self.dimensions],
        }


class RebalanceScoreCalculator:
    """Calculates composite quality score for a rebalancing plan."""

    def __init__(self, recommendation_threshold: float = 0.50) -> None:
        self.threshold = recommendation_threshold

    def calculate(
        self,
        alloc_drift:   AllocationDrift,
        risk_drift:    RiskDrift,
        trade_plan:    TradePlan,
        execution_est: Optional[ExecutionEstimate] = None,
        portfolio_id:  str = "",
    ) -> RebalanceScore:

        if execution_est is None:
            execution_est = trade_plan.execution_estimate

        # 1. Drift reduction score: how much drift will we eliminate?
        pre_drift  = alloc_drift.total_abs_drift
        post_drift = _estimate_post_rebalance_drift(alloc_drift, trade_plan)
        reduction  = (pre_drift - post_drift) / max(pre_drift, 1e-10)
        dr_score   = min(1.0, max(0.0, reduction))

        # 2. Cost efficiency score: cost / turnover (lower = better)
        if execution_est and execution_est.total_cost_pct > 0:
            # Good: cost < 0.25% per 10% turnover = 0.0025 / 0.10 = 0.025 ratio
            cost_ratio = execution_est.total_cost_pct / max(trade_plan.total_turnover, 0.01)
            # cost_ratio ≈ 0.025 → excellent; 0.10 → poor
            ce_score = max(0.0, 1.0 - cost_ratio / 0.10)
        else:
            ce_score = 1.0   # free rebalancing

        # 3. Risk improvement score
        ri_score = min(1.0, max(0.0, risk_drift.abs_risk_drift * 5.0)) if risk_drift.abs_risk_drift > 0 else 0.2

        # 4. Diversification improvement: new positions improve diversification
        n_new = len(trade_plan.new_positions)
        n_total = max(alloc_drift.n_positions_current, 1)
        div_score = min(1.0, n_new / n_total + 0.3 if n_total > 0 else 0.3)
        div_score = max(0.0, min(1.0, div_score))

        # 5. Tax efficiency score: fraction of sells that are LTCG
        sells = [c for c in trade_plan.changes if c.trade_side == TradeSide.SELL]
        if sells:
            ltcg_pct = sum(1 for s in sells if s.is_ltcg_eligible) / len(sells)
            te_score = ltcg_pct
        else:
            te_score = 1.0   # no sells = no tax cost

        # Composite
        overall = (
            dr_score  * _WEIGHTS["drift_reduction"]
          + ce_score  * _WEIGHTS["cost_efficiency"]
          + ri_score  * _WEIGHTS["risk_improvement"]
          + div_score * _WEIGHTS["diversification"]
          + te_score  * _WEIGHTS["tax_efficiency"]
        )
        overall = max(0.0, min(1.0, overall))

        dimensions = tuple(
            RebalanceDimensionScore(
                dimension    = k,
                raw_value    = round(rv, 4),
                score        = round(sc, 4),
                weight       = _WEIGHTS[k],
                contribution = round(sc * _WEIGHTS[k], 4),
            )
            for k, rv, sc in [
                ("drift_reduction",  reduction, dr_score),
                ("cost_efficiency",  ce_score,  ce_score),
                ("risk_improvement", risk_drift.abs_risk_drift, ri_score),
                ("diversification",  float(n_new), div_score),
                ("tax_efficiency",   te_score, te_score),
            ]
        )

        return RebalanceScore(
            portfolio_id     = portfolio_id,
            overall          = round(overall, 4),
            drift_red_score  = round(dr_score, 4),
            cost_eff_score   = round(ce_score, 4),
            risk_imp_score   = round(ri_score, 4),
            div_score        = round(div_score, 4),
            tax_eff_score    = round(te_score, 4),
            grade            = rebalance_score_to_grade(overall),
            level            = rebalance_score_to_level(overall),
            is_recommended   = overall >= self.threshold,
            dimensions       = dimensions,
        )


class RebalanceScoreHistory:
    """Thread-safe bounded history of scores per portfolio."""

    def __init__(self, portfolio_id: str, max_size: int = 100) -> None:
        self.portfolio_id = portfolio_id
        self._max  = max_size
        self._lock = threading.RLock()
        self._data: List[RebalanceScore] = []

    def add(self, score: RebalanceScore) -> None:
        with self._lock:
            self._data.append(score)
            if len(self._data) > self._max:
                self._data = self._data[-self._max:]

    def latest(self) -> Optional[RebalanceScore]:
        with self._lock:
            return self._data[-1] if self._data else None

    def best(self) -> Optional[RebalanceScore]:
        with self._lock:
            return max(self._data, key=lambda s: s.overall) if self._data else None


def _estimate_post_rebalance_drift(
    drift: AllocationDrift,
    plan:  TradePlan,
) -> float:
    """Estimate residual drift after the trades are executed."""
    # Each trade reduces the drift of the affected position
    change_map = {c.symbol: c.abs_change for c in plan.changes}
    residual = 0.0
    for pd in drift.position_drifts:
        applied = change_map.get(pd.symbol, 0.0)
        remaining = max(0.0, pd.abs_drift - applied)
        residual += remaining
    return residual
