"""iios/investment/portfolio/rebalancing/risk_drift.py

Risk-level drift analysis: current portfolio risk vs target risk.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.rebalancing.rebalancing_types import (
    DRIFT_THRESHOLD_MODERATE, CurrentPosition, DriftLevel,
    TargetPosition, classify_drift_level, now_utc,
    portfolio_weighted_risk,
)


@dataclass(frozen=True)
class RiskDrift:
    """Portfolio-level risk drift."""

    result_id:           str        = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str        = ""
    created_at:          str        = field(default_factory=now_utc)

    current_risk:        float      = 0.0
    target_risk:         float      = 0.0
    risk_drift:          float      = 0.0    # current - target (signed)
    abs_risk_drift:      float      = 0.0
    drift_level:         DriftLevel = DriftLevel.NONE

    current_liquidity:   float      = 0.0
    target_liquidity:    float      = 0.0
    liquidity_drift:     float      = 0.0    # current - target

    requires_rebalance:  bool       = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_risk":    round(self.current_risk, 4),
            "target_risk":     round(self.target_risk, 4),
            "risk_drift":      round(self.risk_drift, 4),
            "drift_level":     self.drift_level.value,
            "liquidity_drift": round(self.liquidity_drift, 4),
        }


def compute_risk_drift(
    current:      List[CurrentPosition],
    target:       List[TargetPosition],
    portfolio_id: str = "",
) -> RiskDrift:
    """
    Compute risk and liquidity drift between current and target portfolios.
    """
    if not current and not target:
        return RiskDrift(portfolio_id=portfolio_id)

    cur_risk = _weighted_risk_current(current)
    tgt_risk = _weighted_risk_target(target)
    r_drift  = cur_risk - tgt_risk
    abs_r    = abs(r_drift)

    cur_liq  = _weighted_liquidity_current(current)
    tgt_liq  = _weighted_liquidity_target(target)
    l_drift  = cur_liq - tgt_liq

    # Risk drift maps to [0, 1] scale first, then classify
    # A 0.10 change in risk_score proxy maps to ~2% allocation drift equivalent
    risk_abs_drift_equiv = abs_r * 0.5   # scale factor for classification
    level = classify_drift_level(risk_abs_drift_equiv)

    return RiskDrift(
        portfolio_id        = portfolio_id,
        current_risk        = round(cur_risk, 4),
        target_risk         = round(tgt_risk, 4),
        risk_drift          = round(r_drift, 4),
        abs_risk_drift      = round(abs_r, 4),
        drift_level         = level,
        current_liquidity   = round(cur_liq, 4),
        target_liquidity    = round(tgt_liq, 4),
        liquidity_drift     = round(l_drift, 4),
        requires_rebalance  = abs_r >= DRIFT_THRESHOLD_MODERATE * 2,
    )


def _weighted_risk_current(positions: List[CurrentPosition]) -> float:
    total_w = sum(p.current_weight for p in positions)
    if total_w <= 1e-10:
        return 0.5
    return sum(p.current_weight * p.risk_score for p in positions) / total_w


def _weighted_risk_target(positions: List[TargetPosition]) -> float:
    total_w = sum(p.target_weight for p in positions)
    if total_w <= 1e-10:
        return 0.5
    return sum(p.target_weight * p.risk_score for p in positions) / total_w


def _weighted_liquidity_current(positions: List[CurrentPosition]) -> float:
    total_w = sum(p.current_weight for p in positions)
    if total_w <= 1e-10:
        return 0.7
    return sum(p.current_weight * p.liquidity for p in positions) / total_w


def _weighted_liquidity_target(positions: List[TargetPosition]) -> float:
    total_w = sum(p.target_weight for p in positions)
    if total_w <= 1e-10:
        return 0.7
    return sum(p.target_weight * p.liquidity for p in positions) / total_w
