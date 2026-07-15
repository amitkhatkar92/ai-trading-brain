"""iios/investment/portfolio/rebalancing/rebalancing_types.py

Shared types, enumerations, constants, and utilities for the
Institutional Portfolio Rebalancing Engine.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Drift thresholds (absolute weight deviation)
DRIFT_THRESHOLD_MINOR        = 0.02   # 2%  — monitor
DRIFT_THRESHOLD_MODERATE     = 0.05   # 5%  — consider rebalancing
DRIFT_THRESHOLD_SIGNIFICANT  = 0.08   # 8%  — strong trigger
DRIFT_THRESHOLD_CRITICAL     = 0.10   # 10% — immediate action required

# Trade sizing
MIN_TRADE_SIZE_PCT           = 0.005  # 0.5% — ignore smaller adjustments
MAX_TURNOVER_SINGLE_REBAL    = 0.30   # 30% max single-rebalance turnover
MAX_TURNOVER_ANNUAL          = 0.50   # 50% annual turnover institutional limit

# Transaction costs (Indian equity market, per leg)
TRANSACTION_COST_EQUITY      = 0.0025  # 25 bps per leg (buy or sell)
TRANSACTION_COST_BOND        = 0.0010  # 10 bps for bonds/fixed income
TRANSACTION_COST_FIXED_INR   = 50.0   # Fixed INR cost per trade
MARKET_IMPACT_FACTOR         = 0.003   # 30 bps base market impact
MARKET_IMPACT_THRESHOLD      = 0.05   # Orders > 5% portfolio → impact applies

# Indian tax (equity)
TAX_RATE_STCG                = 0.20    # Short-term capital gains (< 1 year)
TAX_RATE_LTCG                = 0.125   # Long-term capital gains (≥ 1 year)
LTCG_HOLDING_DAYS            = 365

# Benefit thresholds
MIN_BENEFIT_COST_RATIO       = 1.5    # Benefit must be ≥ 1.5× cost to proceed
MIN_DRIFT_REDUCTION_PCT      = 0.30   # Need ≥ 30% drift reduction to justify cost

# Calendar policy defaults
CALENDAR_MONTHLY_DAYS        = 30
CALENDAR_QUARTERLY_DAYS      = 91
CALENDAR_ANNUAL_DAYS         = 365

# Quality scoring (same structure as Performance Engine)
REBAL_SCORE_EXCELLENT        = 0.75
REBAL_SCORE_GOOD             = 0.55
REBAL_SCORE_AVERAGE          = 0.40
REBAL_SCORE_BELOW_AVERAGE    = 0.25


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RebalanceTrigger(str, Enum):
    CALENDAR      = "calendar"
    THRESHOLD     = "threshold"
    RISK_BASED    = "risk_based"
    DRIFT_BASED   = "drift_based"
    VOLATILITY    = "volatility"
    TAX_AWARE     = "tax_aware"
    CASH_FLOW     = "cash_flow"
    HYBRID        = "hybrid"
    MANUAL        = "manual"
    NONE          = "none"


class RebalanceStatus(str, Enum):
    DRAFT         = "draft"
    PENDING       = "pending"
    APPROVED      = "approved"
    RECOMMENDED   = "recommended"
    NOT_REQUIRED  = "not_required"
    REJECTED      = "rejected"
    EXECUTING     = "executing"
    COMPLETED     = "completed"
    CANCELLED     = "cancelled"
    FAILED        = "failed"


class DriftLevel(str, Enum):
    NONE          = "none"         # < 2%
    MINOR         = "minor"        # 2–5%
    MODERATE      = "moderate"     # 5–8%
    SIGNIFICANT   = "significant"  # 8–10%
    CRITICAL      = "critical"     # ≥ 10%


class TradeSide(str, Enum):
    BUY           = "buy"
    SELL          = "sell"
    HOLD          = "hold"


class TradePriority(str, Enum):
    LOW           = "low"
    MEDIUM        = "medium"
    HIGH          = "high"
    URGENT        = "urgent"
    IMMEDIATE     = "immediate"


class PolicyType(str, Enum):
    CALENDAR      = "calendar"
    THRESHOLD     = "threshold"
    RISK_BASED    = "risk_based"
    DRIFT_BASED   = "drift_based"
    VOLATILITY    = "volatility_based"
    TAX_AWARE     = "tax_aware"
    CASH_FLOW     = "cash_flow"
    HYBRID        = "hybrid"
    CUSTOM        = "custom"


class ValidationStatus(str, Enum):
    PASSED        = "passed"
    WARNING       = "warning"
    FAILED        = "failed"


class RebalanceGrade(str, Enum):
    A = "A"   # excellent  ≥ 0.75
    B = "B"   # good       0.55–0.75
    C = "C"   # average    0.40–0.55
    D = "D"   # below avg  0.25–0.40
    F = "F"   # poor       < 0.25


class RebalanceLevel(str, Enum):
    EXCELLENT     = "excellent"
    GOOD          = "good"
    AVERAGE       = "average"
    BELOW_AVERAGE = "below_average"
    POOR          = "poor"


# ---------------------------------------------------------------------------
# Core position types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CurrentPosition:
    """A position the portfolio currently holds."""

    symbol:            str
    current_weight:    float       # current portfolio weight [0, 1]
    sector:            str   = ""
    industry:          str   = ""
    asset_class:       str   = "equity"
    country:           str   = "IN"
    currency:          str   = "INR"
    strategy_id:       str   = ""
    risk_score:        float = 0.50   # 0=low risk, 1=high risk
    liquidity:         float = 0.70   # 0=illiquid, 1=highly liquid
    cost_basis:        float = 0.0    # cost as fraction of portfolio value
    holding_days:      int   = 365    # days held (for tax determination)
    unrealized_gain:   float = 0.0    # unrealized P&L as fraction

    @property
    def is_ltcg_eligible(self) -> bool:
        return self.holding_days >= LTCG_HOLDING_DAYS

    @property
    def applicable_tax_rate(self) -> float:
        return TAX_RATE_LTCG if self.is_ltcg_eligible else TAX_RATE_STCG

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":         self.symbol,
            "current_weight": round(self.current_weight, 4),
            "sector":         self.sector,
            "asset_class":    self.asset_class,
            "holding_days":   self.holding_days,
            "is_ltcg":        self.is_ltcg_eligible,
        }


@dataclass(frozen=True)
class TargetPosition:
    """A target position from the allocation/optimization engine."""

    symbol:        str
    target_weight: float     # target portfolio weight [0, 1]
    sector:        str   = ""
    industry:      str   = ""
    asset_class:   str   = "equity"
    country:       str   = "IN"
    currency:      str   = "INR"
    strategy_id:   str   = ""
    risk_score:    float = 0.50
    conviction:    float = 0.60
    liquidity:     float = 0.70

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":        self.symbol,
            "target_weight": round(self.target_weight, 4),
            "sector":        self.sector,
            "asset_class":   self.asset_class,
            "conviction":    round(self.conviction, 4),
        }


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def current_positions_from_any(source: Any) -> List[CurrentPosition]:
    """
    Extract CurrentPosition list from various upstream sources.

    Accepts:
      - List[CurrentPosition]  → pass-through
      - Duck-typed plan with .positions / .allocations
      - Object with .current_positions
    """
    if isinstance(source, list):
        if not source:
            return []
        if all(isinstance(p, CurrentPosition) for p in source):
            return list(source)
        return [_duck_current(p) for p in source]

    for attr in ("current_positions", "positions", "allocations", "holdings"):
        raw = getattr(source, attr, None)
        if raw is not None:
            lst = list(raw)
            if all(isinstance(p, CurrentPosition) for p in lst):
                return lst
            return [_duck_current(p) for p in lst]
    return []


def target_positions_from_any(source: Any) -> List[TargetPosition]:
    """
    Extract TargetPosition list from various upstream plan objects.

    Accepts:
      - List[TargetPosition]
      - Duck-typed allocation plan with .positions / .allocations
    """
    if isinstance(source, list):
        if not source:
            return []
        if all(isinstance(p, TargetPosition) for p in source):
            return list(source)
        return [_duck_target(p) for p in source]

    for attr in ("target_positions", "positions", "allocations", "targets"):
        raw = getattr(source, attr, None)
        if raw is not None:
            lst = list(raw)
            if all(isinstance(p, TargetPosition) for p in lst):
                return lst
            return [_duck_target(p) for p in lst]
    return []


def _duck_current(p: Any) -> CurrentPosition:
    w = float(
        getattr(p, "current_weight", None)
        or getattr(p, "weight", None)
        or getattr(p, "final_weight", 0.0)
    )
    return CurrentPosition(
        symbol          = str(getattr(p, "symbol", "")),
        current_weight  = w,
        sector          = str(getattr(p, "sector", "")),
        industry        = str(getattr(p, "industry", "")),
        asset_class     = str(getattr(p, "asset_class", "equity")),
        country         = str(getattr(p, "country", "IN")),
        currency        = str(getattr(p, "currency", "INR")),
        strategy_id     = str(getattr(p, "strategy_id", "")),
        risk_score      = float(getattr(p, "risk_score", 0.50)),
        liquidity       = float(getattr(p, "liquidity", 0.70)),
        cost_basis      = float(getattr(p, "cost_basis", 0.0)),
        holding_days    = int(getattr(p, "holding_days", 365)),
        unrealized_gain = float(getattr(p, "unrealized_gain", 0.0)),
    )


def _duck_target(p: Any) -> TargetPosition:
    w = float(
        getattr(p, "target_weight", None)
        or getattr(p, "optimized_weight", None)
        or getattr(p, "weight", None)
        or getattr(p, "final_weight", 0.0)
    )
    return TargetPosition(
        symbol        = str(getattr(p, "symbol", "")),
        target_weight = w,
        sector        = str(getattr(p, "sector", "")),
        industry      = str(getattr(p, "industry", "")),
        asset_class   = str(getattr(p, "asset_class", "equity")),
        country       = str(getattr(p, "country", "IN")),
        currency      = str(getattr(p, "currency", "INR")),
        strategy_id   = str(getattr(p, "strategy_id", "")),
        risk_score    = float(getattr(p, "risk_score", 0.50)),
        conviction    = float(getattr(p, "conviction", 0.60)),
        liquidity     = float(getattr(p, "liquidity", 0.70)),
    )


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def classify_drift_level(abs_drift: float) -> DriftLevel:
    """Map absolute weight drift to DriftLevel enum."""
    if abs_drift < DRIFT_THRESHOLD_MINOR:
        return DriftLevel.NONE
    if abs_drift < DRIFT_THRESHOLD_MODERATE:
        return DriftLevel.MINOR
    if abs_drift < DRIFT_THRESHOLD_SIGNIFICANT:
        return DriftLevel.MODERATE
    if abs_drift < DRIFT_THRESHOLD_CRITICAL:
        return DriftLevel.SIGNIFICANT
    return DriftLevel.CRITICAL


def rebalance_score_to_grade(score: float) -> RebalanceGrade:
    if score >= REBAL_SCORE_EXCELLENT:     return RebalanceGrade.A
    if score >= REBAL_SCORE_GOOD:          return RebalanceGrade.B
    if score >= REBAL_SCORE_AVERAGE:       return RebalanceGrade.C
    if score >= REBAL_SCORE_BELOW_AVERAGE: return RebalanceGrade.D
    return RebalanceGrade.F


def rebalance_score_to_level(score: float) -> RebalanceLevel:
    if score >= REBAL_SCORE_EXCELLENT:     return RebalanceLevel.EXCELLENT
    if score >= REBAL_SCORE_GOOD:          return RebalanceLevel.GOOD
    if score >= REBAL_SCORE_AVERAGE:       return RebalanceLevel.AVERAGE
    if score >= REBAL_SCORE_BELOW_AVERAGE: return RebalanceLevel.BELOW_AVERAGE
    return RebalanceLevel.POOR


def aggregate_drift_level(position_levels: List[DriftLevel]) -> DriftLevel:
    """Return highest drift level from a list."""
    if not position_levels:
        return DriftLevel.NONE
    order = [DriftLevel.NONE, DriftLevel.MINOR, DriftLevel.MODERATE,
             DriftLevel.SIGNIFICANT, DriftLevel.CRITICAL]
    return max(position_levels, key=lambda l: order.index(l))


def portfolio_weighted_risk(positions: List[CurrentPosition]) -> float:
    """Weighted average risk score of a portfolio."""
    total_w = sum(p.current_weight for p in positions)
    if total_w <= 1e-10:
        return 0.5
    return sum(p.current_weight * p.risk_score for p in positions) / total_w


def portfolio_weighted_liquidity(positions: List[CurrentPosition]) -> float:
    """Weighted average liquidity of a portfolio."""
    total_w = sum(p.current_weight for p in positions)
    if total_w <= 1e-10:
        return 0.7
    return sum(p.current_weight * p.liquidity for p in positions) / total_w


def now_utc() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()
