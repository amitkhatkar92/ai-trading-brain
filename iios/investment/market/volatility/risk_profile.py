"""iios/investment/market/volatility/risk_profile.py
Stateless builder for RiskProfile from component scores.
"""
from __future__ import annotations

from iios.investment.market.volatility.models import (
    BehaviourSnapshot,
    RiskLevel,
    RiskProfile,
    VolatilityRegimeType,
    VolatilityState,
)
from iios.investment.market.volatility import risk_score as rs


# ── Component weights in overall risk ────────────────────────────────────────

_WEIGHTS = {
    "execution": 0.20,
    "gap":       0.15,
    "overnight": 0.15,
    "portfolio": 0.25,
    "market":    0.25,
}


def _risk_level(overall: float) -> RiskLevel:
    if overall < 0.15:
        return RiskLevel.VERY_LOW
    if overall < 0.30:
        return RiskLevel.LOW
    if overall < 0.50:
        return RiskLevel.MODERATE
    if overall < 0.70:
        return RiskLevel.HIGH
    if overall < 0.85:
        return RiskLevel.VERY_HIGH
    return RiskLevel.EXTREME


class RiskProfileBuilder:
    """Builds a RiskProfile from VolatilityState, regime, and behaviour."""

    def build(
        self,
        state: VolatilityState,
        regime: VolatilityRegimeType,
        behaviour: BehaviourSnapshot,
    ) -> RiskProfile:
        exec_r    = rs.execution_risk_score(state, behaviour, regime)
        gap_r     = rs.gap_risk_score(state, behaviour)
        overnight = rs.overnight_risk_score(state, regime)
        portfolio = rs.portfolio_risk_score(state, regime)
        strategy  = rs.strategy_risk_score(state, regime, behaviour)
        market    = rs.market_risk_score(state, behaviour)

        overall = (
            exec_r    * _WEIGHTS["execution"]
            + gap_r   * _WEIGHTS["gap"]
            + overnight * _WEIGHTS["overnight"]
            + portfolio * _WEIGHTS["portfolio"]
            + market    * _WEIGHTS["market"]
        )
        # strategy risk influences the score too
        overall = overall * 0.85 + strategy * 0.15
        overall = max(0.0, min(1.0, overall))

        return RiskProfile(
            execution_risk=round(exec_r, 4),
            gap_risk=round(gap_r, 4),
            overnight_risk=round(overnight, 4),
            portfolio_risk=round(portfolio, 4),
            strategy_risk=round(strategy, 4),
            market_risk=round(market, 4),
            overall_risk=round(overall, 4),
            risk_level=_risk_level(overall),
            risk_score=round(overall * 100, 2),
        )
