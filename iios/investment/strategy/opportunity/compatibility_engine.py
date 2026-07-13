"""iios/investment/strategy/opportunity/compatibility_engine.py
CompatibilityEngine — computes multi-dimensional compatibility scores
between a strategy and an opportunity.  Returns soft scores (0–100) for
each dimension; no hard rejections.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

from iios.investment.strategy.opportunity.market_opportunity import MarketOpportunity
from iios.investment.strategy.opportunity.company_opportunity import CompanyOpportunity
from iios.investment.strategy.opportunity.strategy_candidate import StrategyCandidate
from iios.investment.strategy.opportunity.suitability_statistics import (
    clamp, score_bool, volatility_compat, capital_score,
    risk_compat, timeframe_score, linear_scale,
)


@dataclass(frozen=True)
class CompatibilityScores:
    """Per-dimension soft compatibility scores in [0, 100]."""
    market_compatibility:    float = 0.0
    company_compatibility:   float = 0.0
    risk_compatibility:      float = 0.0
    timeframe_compatibility: float = 0.0
    capital_compatibility:   float = 0.0
    execution_readiness:     float = 0.0
    overall:                 float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_compatibility":    self.market_compatibility,
            "company_compatibility":   self.company_compatibility,
            "risk_compatibility":      self.risk_compatibility,
            "timeframe_compatibility": self.timeframe_compatibility,
            "capital_compatibility":   self.capital_compatibility,
            "execution_readiness":     self.execution_readiness,
            "overall":                 self.overall,
        }


_RISK_LEVELS = {"low": 0.10, "moderate": 0.20, "high": 0.35, "very_high": 0.50}
_CAP_LEVELS  = {"large": 0.10, "mid": 0.25, "small": 0.45, "micro": 0.60}


class CompatibilityEngine:
    """
    Scores how compatible a strategy is with an opportunity across six
    dimensions.  All results are deterministic and auditable.
    """

    def __init__(self, available_capital: float = 0.0) -> None:
        self._capital = available_capital

    def score(
        self,
        candidate: StrategyCandidate,
        opportunity: Union[MarketOpportunity, CompanyOpportunity],
    ) -> CompatibilityScores:
        if isinstance(opportunity, MarketOpportunity):
            return self._score_market(candidate, opportunity)
        return self._score_company(candidate, opportunity)

    # ── market ────────────────────────────────────────────────────────────────

    def _score_market(
        self, c: StrategyCandidate, opp: MarketOpportunity
    ) -> CompatibilityScores:
        mkt = self._market_compat(c, opp)
        co  = 50.0  # no company-specific data
        risk = self._risk_compat_market(c, opp)
        tf   = timeframe_score(c.supported_timeframes, opp.timeframe.value)
        cap  = capital_score(c.min_capital, self._capital) if self._capital > 0 else 100.0
        exe  = self._exec_readiness(c)
        overall = (
            0.30 * mkt + 0.10 * co + 0.25 * risk
            + 0.15 * tf + 0.10 * cap + 0.10 * exe
        )
        return CompatibilityScores(
            market_compatibility=round(mkt, 2),
            company_compatibility=round(co, 2),
            risk_compatibility=round(risk, 2),
            timeframe_compatibility=round(tf, 2),
            capital_compatibility=round(cap, 2),
            execution_readiness=round(exe, 2),
            overall=round(clamp(overall), 2),
        )

    def _score_company(
        self, c: StrategyCandidate, opp: CompanyOpportunity
    ) -> CompatibilityScores:
        mkt  = 60.0  # proxy — no explicit market data
        co   = self._company_compat(c, opp)
        risk = risk_compat(
            c.max_drawdown_tolerance,
            _RISK_LEVELS.get(opp.risk_level, 0.20),
        )
        tf   = timeframe_score(c.supported_timeframes, opp.timeframe)
        cap  = capital_score(c.min_capital, self._capital) if self._capital > 0 else 100.0
        exe  = self._exec_readiness(c)
        overall = (
            0.15 * mkt + 0.30 * co + 0.25 * risk
            + 0.15 * tf + 0.10 * cap + 0.05 * exe
        )
        return CompatibilityScores(
            market_compatibility=round(mkt, 2),
            company_compatibility=round(co, 2),
            risk_compatibility=round(risk, 2),
            timeframe_compatibility=round(tf, 2),
            capital_compatibility=round(cap, 2),
            execution_readiness=round(exe, 2),
            overall=round(clamp(overall), 2),
        )

    # ── dimension helpers ────────────────────────────────────────────────────

    def _market_compat(self, c: StrategyCandidate, opp: MarketOpportunity) -> float:
        regime_ok  = c.supports_regime(opp.regime.value)
        dir_ok     = c.supports_direction(opp.direction)
        sector_ok  = c.supports_sector(opp.sector)
        vol        = volatility_compat(c.min_volatility_regime, c.max_volatility_regime, opp.volatility_regime.value)
        liq        = clamp(opp.liquidity_score / max(c.min_liquidity_score, 0.01) * 100.0)
        base = (
            score_bool(regime_ok) * 0.30
            + score_bool(dir_ok)  * 0.25
            + vol * 0.20
            + liq * 0.15
            + score_bool(sector_ok, 100.0, 60.0) * 0.10
        )
        return clamp(base)

    def _company_compat(self, c: StrategyCandidate, opp: CompanyOpportunity) -> float:
        dir_ok    = c.supports_direction(opp.direction)
        sector_ok = c.supports_sector(opp.sector)
        quality   = opp.quality_score * 100.0
        composite = opp.composite_score * 100.0
        cap_liq   = clamp(
            (1.0 - _CAP_LEVELS.get(opp.market_cap_category, 0.40))
            / max(c.min_liquidity_score, 0.01) * 100.0
        )
        return clamp(
            score_bool(dir_ok) * 0.20
            + score_bool(sector_ok, 100.0, 60.0) * 0.10
            + quality * 0.25
            + composite * 0.30
            + cap_liq * 0.15
        )

    def _risk_compat_market(self, c: StrategyCandidate, opp: MarketOpportunity) -> float:
        implied_risk = {
            "high_volatility": 0.35, "crisis": 0.50,
            "bear": 0.30, "bull": 0.15, "sideways": 0.15,
            "low_volatility": 0.10, "recovery": 0.20,
        }.get(opp.regime.value, 0.20)
        return risk_compat(c.max_drawdown_tolerance, implied_risk)

    @staticmethod
    def _exec_readiness(c: StrategyCandidate) -> float:
        from iios.investment.strategy.opportunity.suitability_statistics import execution_readiness_score
        return execution_readiness_score(c.approval_status, c.evaluation_score)
