"""iios/investment/portfolio/performance/performance_types.py

Core types, enumerations, constants, and utilities for the
Institutional Portfolio Performance Engine.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RISK_FREE_RATE_ANNUAL   = 0.065   # 6.5% — Indian 10Y Gsec proxy
EQUITY_PREMIUM_PROXY    = 0.065   # India equity risk premium proxy
TRADING_DAYS            = 252
MONTHS_PER_YEAR         = 12
QUARTERS_PER_YEAR       = 4

# Vol proxy constants (mirrors risk_types.py)
MIN_ANNUAL_VOL          = 0.05
MAX_ANNUAL_VOL          = 0.60
VOL_RANGE               = MAX_ANNUAL_VOL - MIN_ANNUAL_VOL

# Performance score thresholds
SCORE_EXCELLENT         = 0.75
SCORE_GOOD              = 0.55
SCORE_AVERAGE           = 0.40
SCORE_BELOW_AVERAGE     = 0.25

# Sharpe normalization cap
SHARPE_EXCELLENT        = 2.0
SHARPE_GOOD             = 1.0
SHARPE_ACCEPTABLE       = 0.5

# Alpha normalization (annual)
ALPHA_EXCELLENT         = 0.05    # 5% annual alpha
ALPHA_GOOD              = 0.02

# Benchmark return proxies (annual, for estimation without live data)
BENCHMARK_NIFTY50_RETURN    = 0.12
BENCHMARK_NIFTY500_RETURN   = 0.13
BENCHMARK_SENSEX_RETURN     = 0.11
BENCHMARK_NIFTY_IT_RETURN   = 0.15
BENCHMARK_NIFTY_BANK_RETURN = 0.11
BENCHMARK_NIFTY_MIDCAP_RETURN = 0.14
BENCHMARK_GLOBAL_RETURN     = 0.10


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class PerformanceGrade(str, Enum):
    A = "A"   # excellent  ≥ 0.75
    B = "B"   # good       0.55-0.75
    C = "C"   # average    0.40-0.55
    D = "D"   # below avg  0.25-0.40
    F = "F"   # poor       < 0.25


class PerformanceLevel(str, Enum):
    EXCELLENT    = "excellent"
    GOOD         = "good"
    AVERAGE      = "average"
    BELOW_AVERAGE = "below_average"
    POOR         = "poor"


class PerformanceTrend(str, Enum):
    IMPROVING    = "improving"
    STABLE       = "stable"
    DETERIORATING = "deteriorating"
    INSUFFICIENT = "insufficient_data"


class ReturnPeriod(str, Enum):
    DAILY       = "daily"
    WEEKLY      = "weekly"
    MONTHLY     = "monthly"
    QUARTERLY   = "quarterly"
    ANNUAL      = "annual"
    INCEPTION   = "inception"


class AttributionMethod(str, Enum):
    BRINSON     = "brinson"      # BHB: allocation + selection + interaction
    ARITHMETIC  = "arithmetic"   # simple arithmetic
    GEOMETRIC   = "geometric"    # geometric linking


class BenchmarkType(str, Enum):
    BROAD_MARKET    = "broad_market"
    SECTOR          = "sector"
    CUSTOM          = "custom"
    GLOBAL          = "global"
    RISK_FREE       = "risk_free"


class RunStatus(str, Enum):
    SUCCESS  = "success"
    FAILED   = "failed"
    PARTIAL  = "partial"


# ---------------------------------------------------------------------------
# Core position type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PerformancePosition:
    """A portfolio position as seen by the Performance Engine."""

    symbol:                 str
    weight:                 float    # portfolio weight [0, 1]
    sector:                 str      = ""
    industry:               str      = ""
    asset_class:            str      = "equity"
    country:                str      = "IN"
    currency:               str      = "INR"
    strategy_id:            str      = ""

    # Return data — actual if available, estimated if not
    period_return:          float    = 0.0     # realised return this evaluation period
    expected_return_annual: float    = 0.0     # forward-looking annual expected return

    # Risk & conviction from upstream engines
    risk_score:             float    = 0.25    # 0=low risk, 1=high risk
    conviction:             float    = 0.60    # 0=low conviction, 1=high conviction
    confidence:             float    = 0.70
    liquidity:              float    = 0.70

    # Optional benchmark return for active return attribution
    benchmark_period_return: float   = 0.0

    @property
    def annual_vol_proxy(self) -> float:
        """Annual vol proxy: MIN + risk_score * (MAX - MIN)."""
        return MIN_ANNUAL_VOL + self.risk_score * VOL_RANGE

    @property
    def contribution(self) -> float:
        """Absolute return contribution = weight × period_return."""
        return self.weight * self.period_return

    @property
    def active_return(self) -> float:
        """Active return vs benchmark."""
        return self.period_return - self.benchmark_period_return

    @property
    def active_contribution(self) -> float:
        return self.weight * self.active_return

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":                  self.symbol,
            "weight":                  round(self.weight, 4),
            "sector":                  self.sector,
            "period_return":           round(self.period_return, 4),
            "expected_return_annual":  round(self.expected_return_annual, 4),
            "contribution":            round(self.contribution, 4),
        }


# ---------------------------------------------------------------------------
# Factory: positions_from_plan
# ---------------------------------------------------------------------------

def positions_from_plan(
    plan:              Any,
    period_return_map: Optional[Dict[str, float]] = None,
) -> List[PerformancePosition]:
    """
    Convert any upstream plan object or list of positions into a list of
    PerformancePosition.

    Accepts:
      - List[PerformancePosition]  → pass-through
      - List[Any]                  → duck-type each item
      - Plan with .positions attr  → extract and duck-type
      - Plan with .allocations attr
    """
    period_return_map = period_return_map or {}

    if isinstance(plan, list):
        if not plan:
            return []
        if all(isinstance(p, PerformancePosition) for p in plan):
            return list(plan)
        return _build_performance_positions(plan, period_return_map)

    raw: List[Any] = []
    if hasattr(plan, "positions"):
        raw = list(plan.positions)
    elif hasattr(plan, "allocations"):
        raw = list(plan.allocations)
    else:
        return []

    return _build_performance_positions(raw, period_return_map)


def _build_performance_positions(
    raw: List[Any],
    period_return_map: Dict[str, float],
) -> List[PerformancePosition]:
    out: List[PerformancePosition] = []
    for p in raw:
        symbol = str(getattr(p, "symbol", ""))
        w = float(
            getattr(p, "optimized_weight", None)
            or getattr(p, "final_weight", None)
            or getattr(p, "weight", 0.0)
        )
        risk_score = float(
            getattr(p, "risk_proxy", None)
            or getattr(p, "risk_score", 0.25)
        )
        conviction  = float(
            getattr(p, "expected_return_proxy", None)
            or getattr(p, "conviction", 0.60)
        )
        confidence  = float(getattr(p, "confidence_proxy", None) or getattr(p, "confidence", 0.70))
        exp_ret     = float(getattr(p, "expected_return_annual", None)
                           or _estimate_expected_return(conviction, risk_score))
        period_ret  = period_return_map.get(symbol,
                        float(getattr(p, "period_return", 0.0)))
        bmk_ret     = float(getattr(p, "benchmark_period_return", 0.0))
        out.append(PerformancePosition(
            symbol                  = symbol,
            weight                  = w,
            sector                  = str(getattr(p, "sector", "")),
            industry                = str(getattr(p, "industry", "")),
            asset_class             = str(getattr(p, "asset_class", "equity")),
            country                 = str(getattr(p, "country", "IN")),
            currency                = str(getattr(p, "currency", "INR")),
            strategy_id             = str(getattr(p, "strategy_id", "")),
            period_return           = period_ret,
            expected_return_annual  = exp_ret,
            risk_score              = risk_score,
            conviction              = conviction,
            confidence              = confidence,
            liquidity               = float(getattr(p, "liquidity", 0.70)),
            benchmark_period_return = bmk_ret,
        ))

    total = sum(r.weight for r in out)
    if total > 1e-8 and abs(total - 1.0) > 1e-4:
        out = [PerformancePosition(
            symbol=p.symbol, weight=p.weight / total,
            sector=p.sector, industry=p.industry, asset_class=p.asset_class,
            country=p.country, currency=p.currency, strategy_id=p.strategy_id,
            period_return=p.period_return,
            expected_return_annual=p.expected_return_annual,
            risk_score=p.risk_score, conviction=p.conviction,
            confidence=p.confidence, liquidity=p.liquidity,
            benchmark_period_return=p.benchmark_period_return,
        ) for p in out]
    return out


def _estimate_expected_return(conviction: float, risk_score: float) -> float:
    """Estimate annual expected return from conviction signal and risk score."""
    conviction_signal = (conviction - 0.5) * 2.0          # [-1, +1]
    return RISK_FREE_RATE_ANNUAL + conviction_signal * EQUITY_PREMIUM_PROXY


# ---------------------------------------------------------------------------
# Mathematical utilities
# ---------------------------------------------------------------------------

def portfolio_return(positions: List[PerformancePosition]) -> float:
    """Total portfolio return = Σ w_i × r_i."""
    return sum(p.contribution for p in positions)


def portfolio_expected_return(positions: List[PerformancePosition]) -> float:
    """Expected portfolio return = Σ w_i × E[r_i]."""
    return sum(p.weight * p.expected_return_annual for p in positions)


def portfolio_vol_proxy(positions: List[PerformancePosition]) -> float:
    """Annual vol proxy from position risk scores (uses CORR_SAME_SECTOR proxy)."""
    if not positions:
        return 0.0
    n = len(positions)
    var = 0.0
    for pi in positions:
        for pj in positions:
            if pi.symbol == pj.symbol:
                corr = 1.00
            elif pi.industry and pi.industry == pj.industry:
                corr = 0.80
            elif pi.sector and pi.sector == pj.sector:
                corr = 0.55
            elif pi.asset_class and pi.asset_class == pj.asset_class:
                corr = 0.30
            else:
                corr = 0.10
            var += pi.weight * pj.weight * corr * pi.annual_vol_proxy * pj.annual_vol_proxy
    return math.sqrt(max(0.0, var))


def downside_deviation(returns: List[float], target: float = 0.0) -> float:
    """Semi-deviation below target for Sortino ratio."""
    if not returns:
        return 0.0
    neg_sq = [(r - target) ** 2 for r in returns if r < target]
    if not neg_sq:
        return 0.0
    return math.sqrt(sum(neg_sq) / len(returns))


def sharpe_from_positions(positions: List[PerformancePosition], realized_return: float) -> float:
    """Compute Sharpe ratio using position-based vol proxy."""
    vol = portfolio_vol_proxy(positions)
    if vol <= 1e-10:
        return 0.0
    return (realized_return - RISK_FREE_RATE_ANNUAL) / vol


def performance_score_to_grade(score: float) -> PerformanceGrade:
    if score >= SCORE_EXCELLENT:    return PerformanceGrade.A
    if score >= SCORE_GOOD:         return PerformanceGrade.B
    if score >= SCORE_AVERAGE:      return PerformanceGrade.C
    if score >= SCORE_BELOW_AVERAGE:return PerformanceGrade.D
    return PerformanceGrade.F


def performance_score_to_level(score: float) -> PerformanceLevel:
    if score >= SCORE_EXCELLENT:    return PerformanceLevel.EXCELLENT
    if score >= SCORE_GOOD:         return PerformanceLevel.GOOD
    if score >= SCORE_AVERAGE:      return PerformanceLevel.AVERAGE
    if score >= SCORE_BELOW_AVERAGE:return PerformanceLevel.BELOW_AVERAGE
    return PerformanceLevel.POOR


def normalize_sharpe(sharpe: float) -> float:
    """Map Sharpe ratio to [0, 1] score."""
    if sharpe <= 0:          return 0.0
    if sharpe >= SHARPE_EXCELLENT: return 1.0
    return sharpe / SHARPE_EXCELLENT


def normalize_alpha(alpha_annual: float) -> float:
    """Map annual alpha to [0, 1] score."""
    if alpha_annual <= 0:           return 0.0
    if alpha_annual >= ALPHA_EXCELLENT: return 1.0
    return alpha_annual / ALPHA_EXCELLENT


def bucket_weights(positions: List[PerformancePosition], attr: str) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for p in positions:
        key = str(getattr(p, attr, "unknown"))
        result[key] = result.get(key, 0.0) + p.weight
    return result


def bucket_returns(positions: List[PerformancePosition], attr: str) -> Dict[str, float]:
    """Weighted average return per bucket (sector/industry/etc.)."""
    weights = bucket_weights(positions, attr)
    contrib: Dict[str, float] = {}
    for p in positions:
        key = str(getattr(p, attr, "unknown"))
        contrib[key] = contrib.get(key, 0.0) + p.weight * p.period_return
    return {k: contrib.get(k, 0.0) / w if w > 1e-10 else 0.0
            for k, w in weights.items()}
