"""iios/investment/portfolio/risk/risk_types.py

Core types, enumerations, constants, and utilities for the
Institutional Portfolio Risk Engine.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RiskGrade(str, Enum):
    A = "A"   # Very low  ≤ 0.20
    B = "B"   # Low       0.20-0.35
    C = "C"   # Moderate  0.35-0.55
    D = "D"   # High      0.55-0.70
    F = "F"   # Very high > 0.70


class RiskLevel(str, Enum):
    VERY_LOW    = "very_low"
    LOW         = "low"
    MODERATE    = "moderate"
    HIGH        = "high"
    VERY_HIGH   = "very_high"
    CRITICAL    = "critical"


class RiskStatus(str, Enum):
    HEALTHY     = "healthy"
    ELEVATED    = "elevated"
    WARNING     = "warning"
    CRITICAL    = "critical"
    UNKNOWN     = "unknown"


class RiskCategory(str, Enum):
    MARKET        = "market"
    CREDIT        = "credit"
    LIQUIDITY     = "liquidity"
    CURRENCY      = "currency"
    INTEREST_RATE = "interest_rate"
    CONCENTRATION = "concentration"
    TAIL          = "tail"
    SYSTEMIC      = "systemic"


class DrawdownLevel(str, Enum):
    NONE       = "none"       # < 1%
    MINIMAL    = "minimal"    # 1-5%
    MODERATE   = "moderate"   # 5-15%
    SEVERE     = "severe"     # 15-30%
    EXTREME    = "extreme"    # > 30%


class StressTestSeverity(str, Enum):
    MILD       = "mild"
    MODERATE   = "moderate"
    SEVERE     = "severe"
    EXTREME    = "extreme"
    BLACK_SWAN = "black_swan"


class ExposureType(str, Enum):
    ASSET_CLASS = "asset_class"
    SECTOR      = "sector"
    INDUSTRY    = "industry"
    COUNTRY     = "country"
    CURRENCY    = "currency"
    STYLE       = "style"
    FACTOR      = "factor"
    THEME       = "theme"


class AlertSeverity(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    CRITICAL = "critical"


class TrendDirection(str, Enum):
    IMPROVING         = "improving"
    STABLE            = "stable"
    DETERIORATING     = "deteriorating"
    INSUFFICIENT_DATA = "insufficient_data"


class RunStatus(str, Enum):
    SUCCESS = "success"
    FAILED  = "failed"
    PARTIAL = "partial"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Standard normal quantiles  (scipy.stats.norm.ppf equivalents)
NORMAL_Z_90   = 1.2816
NORMAL_Z_95   = 1.6449
NORMAL_Z_99   = 2.3263
NORMAL_Z_999  = 3.0902

# Risk score → annual vol mapping (linear interpolation)
MIN_ANNUAL_VOL = 0.05     # risk_score = 0.0  → 5% p.a.
MAX_ANNUAL_VOL = 0.60     # risk_score = 1.0  → 60% p.a.
TRADING_DAYS   = 252

# Correlation proxies (same as diversification engine)
CORR_SAME_SYMBOL      = 1.00
CORR_SAME_INDUSTRY    = 0.80
CORR_SAME_SECTOR      = 0.55
CORR_SAME_ASSET_CLASS = 0.30
CORR_DIFFERENT        = 0.10

# VaR warning / critical levels (daily, as fraction of portfolio)
VAR_95_1D_WARNING  = 0.020
VAR_95_1D_CRITICAL = 0.035
VAR_99_1D_WARNING  = 0.030
VAR_99_1D_CRITICAL = 0.050

# Annual volatility bands
VOL_LOW       = 0.10
VOL_MODERATE  = 0.20
VOL_HIGH      = 0.30
VOL_VERY_HIGH = 0.50

# Drawdown thresholds
DD_NONE     = 0.01
DD_MINIMAL  = 0.05
DD_MODERATE = 0.15
DD_SEVERE   = 0.30

# Liquidity thresholds
LIQUIDITY_LOW_THRESHOLD       = 0.30   # avg liquidity < 30% → elevated
LIQUIDITY_CRITICAL_THRESHOLD  = 0.15   # avg liquidity < 15% → critical
ILLIQUID_WEIGHT_WARNING       = 0.20   # >20% of portfolio in illiquid assets
ILLIQUID_WEIGHT_CRITICAL      = 0.40

# Credit thresholds
CREDIT_LOW_THRESHOLD  = 0.40
CREDIT_HIGH_THRESHOLD = 0.70

# Concentration risk thresholds (HHI)
HHI_LOW_RISK      = 0.15
HHI_MODERATE_RISK = 0.25
HHI_HIGH_RISK     = 0.40

# Currency exposure thresholds
FOREIGN_CURRENCY_WARNING  = 0.30
FOREIGN_CURRENCY_CRITICAL = 0.60

# Dimension weights for composite risk score
WEIGHT_MARKET        = 0.30
WEIGHT_CONCENTRATION = 0.20
WEIGHT_LIQUIDITY     = 0.15
WEIGHT_TAIL          = 0.15
WEIGHT_CREDIT        = 0.10
WEIGHT_CURRENCY      = 0.05
WEIGHT_INTEREST_RATE = 0.05

# Quality gate: risk score <= threshold is "acceptable"
DEFAULT_RISK_QUALITY_GATE = 0.55   # lower is better for risk

# Schema versions
RISK_PROFILE_SCHEMA_VERSION  = "1.0.0"
RISK_SNAPSHOT_SCHEMA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# RiskPosition — unified position model for the risk engine
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskPosition:
    """Normalised position for institutional risk analysis."""

    symbol:        str   = ""
    weight:        float = 0.0        # portfolio weight [0, 1]
    sector:        str   = ""
    industry:      str   = ""
    asset_class:   str   = "equity"
    country:       str   = "IN"
    currency:      str   = "INR"

    # Risk inputs (0–1 normalised)
    risk_score:    float = 0.25       # 0=very low risk, 1=very high
    conviction:    float = 0.60       # 0=low, 1=high expected return proxy
    confidence:    float = 0.70       # signal confidence
    liquidity:     float = 0.70       # 0=illiquid, 1=very liquid
    credit_quality: float = 0.70      # 0=junk, 1=investment-grade/AAA

    @property
    def annual_volatility(self) -> float:
        """Estimated annual volatility from risk_score (5%–60% linear)."""
        return MIN_ANNUAL_VOL + self.risk_score * (MAX_ANNUAL_VOL - MIN_ANNUAL_VOL)

    @property
    def daily_volatility(self) -> float:
        return self.annual_volatility / math.sqrt(TRADING_DAYS)

    @property
    def is_foreign_currency(self) -> bool:
        return self.currency not in ("INR", "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":         self.symbol,
            "weight":         round(self.weight, 6),
            "sector":         self.sector,
            "industry":       self.industry,
            "asset_class":    self.asset_class,
            "country":        self.country,
            "currency":       self.currency,
            "risk_score":     round(self.risk_score, 4),
            "conviction":     round(self.conviction, 4),
            "confidence":     round(self.confidence, 4),
            "liquidity":      round(self.liquidity, 4),
            "credit_quality": round(self.credit_quality, 4),
        }


# ---------------------------------------------------------------------------
# positions_from_plan factory
# ---------------------------------------------------------------------------

def positions_from_plan(plan: Any) -> List[RiskPosition]:
    """
    Extract a list of RiskPosition from an OptimizationPlan, AllocationPlan,
    DiversificationProfile, any duck-typed plan object, or a plain list.
    """
    # If already a list of RiskPosition, pass through as-is
    if isinstance(plan, list):
        if not plan:
            return []
        if all(isinstance(p, RiskPosition) for p in plan):
            return list(plan)
        raw = list(plan)
        return _build_risk_positions(raw)

    raw: List[Any] = []
    if hasattr(plan, "positions"):
        raw = list(plan.positions)
    elif hasattr(plan, "allocations"):
        raw = list(plan.allocations)
    else:
        return []

    return _build_risk_positions(raw)


def _build_risk_positions(raw: List[Any]) -> List["RiskPosition"]:
    """Build RiskPosition list from raw duck-typed items."""
    out: List[RiskPosition] = []
    for p in raw:
        w = float(
            getattr(p, "optimized_weight", None)
            or getattr(p, "final_weight", None)
            or getattr(p, "weight", 0.0)
        )
        out.append(RiskPosition(
            symbol         = str(getattr(p, "symbol", "")),
            weight         = w,
            sector         = str(getattr(p, "sector", "")),
            industry       = str(getattr(p, "industry", "")),
            asset_class    = str(getattr(p, "asset_class", "equity")),
            country        = str(getattr(p, "country", "IN")),
            currency       = str(getattr(p, "currency", "INR")),
            risk_score     = float(
                getattr(p, "risk_proxy", None) or getattr(p, "risk_score", 0.25)
            ),
            conviction     = float(
                getattr(p, "expected_return_proxy", None) or getattr(p, "conviction", 0.60)
            ),
            confidence     = float(
                getattr(p, "confidence_proxy", None) or getattr(p, "confidence", 0.70)
            ),
            liquidity      = float(getattr(p, "liquidity", 0.70)),
            credit_quality = float(getattr(p, "credit_quality", 0.70)),
        ))

    total = sum(r.weight for r in out)
    if total > 1e-8 and abs(total - 1.0) > 1e-4:
        return [RiskPosition(
            symbol=r.symbol, weight=r.weight / total,
            sector=r.sector, industry=r.industry,
            asset_class=r.asset_class, country=r.country, currency=r.currency,
            risk_score=r.risk_score, conviction=r.conviction, confidence=r.confidence,
            liquidity=r.liquidity, credit_quality=r.credit_quality,
        ) for r in out]
    return out


# ---------------------------------------------------------------------------
# Mathematical utilities
# ---------------------------------------------------------------------------

def _corr(a: RiskPosition, b: RiskPosition) -> float:
    """Pairwise correlation proxy based on shared attributes."""
    if a.symbol == b.symbol:
        return CORR_SAME_SYMBOL
    if a.industry and a.industry == b.industry:
        return CORR_SAME_INDUSTRY
    if a.sector and a.sector == b.sector:
        return CORR_SAME_SECTOR
    if a.asset_class and a.asset_class == b.asset_class:
        return CORR_SAME_ASSET_CLASS
    return CORR_DIFFERENT


def portfolio_variance(positions: List[RiskPosition]) -> float:
    """Full covariance portfolio variance using pairwise correlation proxies."""
    if not positions:
        return 0.0
    var = 0.0
    for pi in positions:
        for pj in positions:
            var += (pi.weight * pj.weight
                    * _corr(pi, pj)
                    * pi.annual_volatility
                    * pj.annual_volatility)
    return max(0.0, var)


def portfolio_volatility(positions: List[RiskPosition]) -> float:
    """Annual portfolio volatility (sigma_p)."""
    return math.sqrt(portfolio_variance(positions))


def var_parametric(vol_annual: float, z: float, horizon_days: int = 1) -> float:
    """Parametric VaR: annual vol → VaR over horizon_days."""
    daily_vol = vol_annual / math.sqrt(TRADING_DAYS)
    return z * daily_vol * math.sqrt(horizon_days)


def cvar_parametric(vol_annual: float, z: float, horizon_days: int = 1) -> float:
    """Parametric CVaR (Expected Shortfall) for normal distribution.
    ES_alpha = phi(z_alpha) / (1-alpha) * sigma_daily * sqrt(horizon)
    """
    phi_z  = math.exp(-z * z / 2.0) / math.sqrt(2.0 * math.pi)
    alpha  = 0.95 if abs(z - NORMAL_Z_95) < 0.1 else 0.99
    daily  = vol_annual / math.sqrt(TRADING_DAYS)
    return (phi_z / (1.0 - alpha)) * daily * math.sqrt(horizon_days)


def weighted_average(positions: List[RiskPosition], attr: str) -> float:
    """Weight-adjusted average of a RiskPosition attribute."""
    if not positions:
        return 0.0
    total = sum(p.weight * getattr(p, attr, 0.0) for p in positions)
    wsum  = sum(p.weight for p in positions)
    return total / wsum if wsum > 1e-10 else 0.0


def bucket_weights(positions: List[RiskPosition], attr: str) -> Dict[str, float]:
    """Aggregate portfolio weight by attribute bucket (sector, industry, etc.)."""
    result: Dict[str, float] = {}
    for p in positions:
        key = str(getattr(p, attr, "unknown"))
        result[key] = result.get(key, 0.0) + p.weight
    return result


def hhi(weights: List[float]) -> float:
    """Herfindahl-Hirschman Index."""
    return sum(w * w for w in weights)


def risk_score_to_level(score: float) -> RiskLevel:
    if score <= 0.20:
        return RiskLevel.VERY_LOW
    if score <= 0.35:
        return RiskLevel.LOW
    if score <= 0.55:
        return RiskLevel.MODERATE
    if score <= 0.70:
        return RiskLevel.HIGH
    if score <= 0.85:
        return RiskLevel.VERY_HIGH
    return RiskLevel.CRITICAL


def risk_score_to_grade(score: float) -> RiskGrade:
    """Lower score = better (less risky) grade."""
    if score <= 0.20:
        return RiskGrade.A
    if score <= 0.35:
        return RiskGrade.B
    if score <= 0.55:
        return RiskGrade.C
    if score <= 0.70:
        return RiskGrade.D
    return RiskGrade.F


def drawdown_to_level(dd: float) -> DrawdownLevel:
    dd = abs(dd)
    if dd < DD_NONE:
        return DrawdownLevel.NONE
    if dd < DD_MINIMAL:
        return DrawdownLevel.MINIMAL
    if dd < DD_MODERATE:
        return DrawdownLevel.MODERATE
    if dd < DD_SEVERE:
        return DrawdownLevel.SEVERE
    return DrawdownLevel.EXTREME
