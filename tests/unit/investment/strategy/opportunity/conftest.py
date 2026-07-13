"""tests/unit/investment/strategy/opportunity/conftest.py
Shared fixtures for all opportunity engine tests.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pytest

from iios.investment.strategy.opportunity.market_opportunity import (
    MarketOpportunity, OpportunityType, MarketRegime, VolatilityRegime, Timeframe
)
from iios.investment.strategy.opportunity.company_opportunity import CompanyOpportunity
from iios.investment.strategy.opportunity.strategy_candidate import StrategyCandidate
from iios.investment.strategy.opportunity.matching_profile import DEFAULT_PROFILE


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_market_opp(
    opp_id: str = "mkt-001",
    opp_type: OpportunityType = OpportunityType.TREND_FOLLOWING,
    symbol: str = "RELIANCE",
    sector: str = "energy",
    regime: MarketRegime = MarketRegime.BULL,
    direction: str = "long",
    confidence: float = 0.75,
    strength: float = 0.70,
    timeframe: Timeframe = Timeframe.SWING,
    vol_regime: VolatilityRegime = VolatilityRegime.MODERATE,
    liquidity: float = 0.75,
    momentum: float = 0.50,
    trend: float = 0.60,
    expires_in_hours: Optional[int] = 48,
) -> MarketOpportunity:
    expires = _now() + timedelta(hours=expires_in_hours) if expires_in_hours else None
    return MarketOpportunity(
        opportunity_id=opp_id,
        opportunity_type=opp_type,
        symbol=symbol,
        sector=sector,
        regime=regime,
        direction=direction,
        confidence=confidence,
        strength=strength,
        timeframe=timeframe,
        volatility_regime=vol_regime,
        liquidity_score=liquidity,
        momentum_score=momentum,
        trend_score=trend,
        detected_at=_now(),
        expires_at=expires,
    )


def make_company_opp(
    opp_id: str = "co-001",
    symbol: str = "HDFC",
    sector: str = "finance",
    opp_type: str = "fundamental_value",
    catalyst: str = "Strong earnings beat",
    direction: str = "long",
    fundamental: float = 0.80,
    technical: float = 0.65,
    sentiment: float = 0.40,
    quality: float = 0.75,
    risk_level: str = "moderate",
    market_cap: str = "large",
    confidence: float = 0.70,
    timeframe: str = "swing",
    expires_in_hours: Optional[int] = 72,
) -> CompanyOpportunity:
    expires = _now() + timedelta(hours=expires_in_hours) if expires_in_hours else None
    return CompanyOpportunity(
        opportunity_id=opp_id,
        company_id=f"comp-{symbol.lower()}",
        symbol=symbol,
        sector=sector,
        opportunity_type=opp_type,
        catalyst=catalyst,
        direction=direction,
        fundamental_score=fundamental,
        technical_score=technical,
        sentiment_score=sentiment,
        quality_score=quality,
        risk_level=risk_level,
        market_cap_category=market_cap,
        confidence=confidence,
        timeframe=timeframe,
        detected_at=_now(),
        expires_at=expires,
    )


def make_candidate(
    strategy_id: str = "s1",
    strategy_name: str = "Momentum Long",
    asset_types: Optional[List[str]] = None,
    timeframes: Optional[List[str]] = None,
    regimes: Optional[List[str]] = None,
    directions: Optional[List[str]] = None,
    sectors: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    min_capital: float = 100_000.0,
    eval_score: float = 75.0,
    sharpe: float = 1.2,
    max_dd: float = 0.12,
    win_rate: float = 0.58,
    pf: float = 1.6,
    robustness: float = 0.72,
    confidence: float = 68.0,
    approval: str = "approved",
    min_vol: Optional[str] = None,
    max_vol: Optional[str] = None,
) -> StrategyCandidate:
    return StrategyCandidate(
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        asset_types=asset_types or ["equity"],
        supported_timeframes=timeframes or ["swing", "positional"],
        supported_regimes=regimes or ["bull", "sideways"],
        supported_directions=directions or ["long"],
        sectors=sectors or [],
        tags=tags or ["momentum", "trend"],
        min_capital=min_capital,
        max_position_size=0.05,
        max_drawdown_tolerance=0.20,
        min_liquidity_score=0.30,
        evaluation_score=eval_score,
        sharpe_ratio=sharpe,
        max_drawdown=max_dd,
        win_rate=win_rate,
        profit_factor=pf,
        robustness_score=robustness,
        confidence_score=confidence,
        approval_status=approval,
        min_volatility_regime=min_vol,
        max_volatility_regime=max_vol,
    )


def make_engine():
    """Fresh StrategyOpportunityEngine with default settings."""
    from iios.investment.strategy.opportunity.strategy_opportunity_engine import (
        StrategyOpportunityEngine
    )
    return StrategyOpportunityEngine(max_workers=4)
