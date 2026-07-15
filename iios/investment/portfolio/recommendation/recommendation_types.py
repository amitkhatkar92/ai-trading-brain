"""iios/investment/portfolio/recommendation/recommendation_types.py

Shared types, enumerations, constants, and PortfolioIntelligence for the
Institutional Portfolio Recommendation Engine.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants — all configurable via PolicyParameters; these are defaults
# ---------------------------------------------------------------------------

# Risk budget thresholds
RISK_BUDGET_HIGH_THRESHOLD     = 0.85  # > 85% utilization → defensive action
RISK_BUDGET_LOW_THRESHOLD      = 0.40  # < 40% → can increase exposure
VAR_CRITICAL_THRESHOLD         = 0.90  # VaR > 90% utilization → hedge/defend

# Drawdown
DRAWDOWN_SEVERE_THRESHOLD      = 0.15  # > 15% drawdown → defensive/hedge

# Allocation thresholds (deviation from target)
EQUITY_OVERWEIGHT_THRESHOLD    = 0.10  # +10% vs target → reduce equity
EQUITY_UNDERWEIGHT_THRESHOLD   = 0.10  # -10% vs target → increase equity
CASH_HIGH_THRESHOLD            = 0.20  # > 20% cash → deploy cash
CASH_LOW_THRESHOLD             = 0.02  # < 2% cash → potential concern
INTERNATIONAL_LOW_THRESHOLD    = 0.10  # < 10% international → consider adding

# Diversification thresholds
HHI_CONCENTRATED_THRESHOLD     = 0.25  # HHI > 0.25 → concentration concern
HHI_VERY_CONCENTRATED          = 0.40  # HHI > 0.40 → strong concentration
MIN_EFFECTIVE_POSITIONS        = 5.0   # < 5 effective positions → diversify
MAX_SECTOR_CONCENTRATION       = 0.40  # single sector > 40% → reduce

# Performance thresholds
SHARPE_POOR_THRESHOLD          = 0.30  # Sharpe < 0.30 → research required
IR_POOR_THRESHOLD              = 0.00  # Negative IR → review
CALMAR_POOR_THRESHOLD          = 0.50  # Calmar < 0.50 → concern

# Quality thresholds
CONSTRUCTION_QUALITY_MIN       = 0.40  # < 0.40 → research required
OPTIMIZATION_QUALITY_MIN       = 0.40  # < 0.40 → not at efficient frontier

# Governance
MIN_CONFIDENCE_TO_PUBLISH      = 0.50  # Minimum confidence to publish
MAX_ACTIVE_RECOMMENDATIONS     = 10    # per portfolio
REC_COOLDOWN_HOURS             = 4.0   # minimum hours between same-type recs

# Expiry (hours)
DEFAULT_EXPIRY_HOURS           = 24.0
CRITICAL_EXPIRY_HOURS          = 4.0
HIGH_EXPIRY_HOURS              = 8.0
LOW_EXPIRY_HOURS               = 48.0
NO_ACTION_EXPIRY_HOURS         = 48.0

# Quality scoring
REC_SCORE_EXCELLENT            = 0.80
REC_SCORE_GOOD                 = 0.65
REC_SCORE_AVERAGE              = 0.50
REC_SCORE_BELOW_AVERAGE        = 0.35


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RecommendationAction(str, Enum):
    INCREASE_EQUITY_EXPOSURE       = "increase_equity_exposure"
    REDUCE_EQUITY_EXPOSURE         = "reduce_equity_exposure"
    INCREASE_CASH                  = "increase_cash"
    REDUCE_CASH                    = "reduce_cash"
    INCREASE_SECTOR_EXPOSURE       = "increase_sector_exposure"
    REDUCE_SECTOR_EXPOSURE         = "reduce_sector_exposure"
    INCREASE_INTERNATIONAL         = "increase_international_exposure"
    REDUCE_INTERNATIONAL           = "reduce_international_exposure"
    INCREASE_DIVERSIFICATION       = "increase_diversification"
    REDUCE_CONCENTRATION           = "reduce_concentration"
    REBALANCE_PORTFOLIO            = "rebalance_portfolio"
    DEFENSIVE_POSITIONING          = "defensive_positioning"
    AGGRESSIVE_POSITIONING         = "aggressive_positioning"
    HEDGE_PORTFOLIO                = "hedge_portfolio"
    RESEARCH_REQUIRED              = "research_required"
    NO_ACTION                      = "no_action"


class RecommendationPriority(str, Enum):
    IMMEDIATE     = "immediate"
    HIGH          = "high"
    MEDIUM        = "medium"
    LOW           = "low"
    INFORMATIONAL = "informational"


class RecommendationRisk(str, Enum):
    HIGH    = "high"
    MEDIUM  = "medium"
    LOW     = "low"
    MINIMAL = "minimal"


class RecommendationStatus(str, Enum):
    DRAFT      = "draft"
    PUBLISHED  = "published"
    ACTIVE     = "active"
    MONITORING = "monitoring"
    UPDATED    = "updated"
    EXPIRED    = "expired"
    WITHDRAWN  = "withdrawn"
    ARCHIVED   = "archived"


class LifecycleState(str, Enum):
    CREATED    = "created"
    PUBLISHED  = "published"
    ACTIVE     = "active"
    MONITORING = "monitoring"
    UPDATED    = "updated"
    EXPIRED    = "expired"
    WITHDRAWN  = "withdrawn"
    ARCHIVED   = "archived"


class RecommendationGrade(str, Enum):
    A = "A"   # excellent ≥ 0.80
    B = "B"   # good      0.65–0.80
    C = "C"   # average   0.50–0.65
    D = "D"   # below avg 0.35–0.50
    F = "F"   # poor      < 0.35


class RecommendationLevel(str, Enum):
    EXCELLENT     = "excellent"
    GOOD          = "good"
    AVERAGE       = "average"
    BELOW_AVERAGE = "below_average"
    POOR          = "poor"


class ValidationStatus(str, Enum):
    PASSED  = "passed"
    WARNING = "warning"
    FAILED  = "failed"


class PolicyType(str, Enum):
    CONSERVATIVE   = "conservative"
    BALANCED       = "balanced"
    AGGRESSIVE     = "aggressive"
    INCOME         = "income"
    GROWTH         = "growth"
    RISK_FIRST     = "risk_first"
    QUALITY_DRIVEN = "quality_driven"
    CUSTOM         = "custom"


# ---------------------------------------------------------------------------
# Portfolio Intelligence — aggregated signals from all upstream engines
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioIntelligence:
    """
    Aggregated intelligence from all upstream portfolio engines.
    Primary input to the Portfolio Recommendation Engine.

    NEVER passed back to upstream engines — one-way data flow only.
    """

    portfolio_id:   str   = ""
    captured_at:    str   = field(default_factory=lambda: now_utc())
    intelligence_id:str   = field(default_factory=lambda: str(uuid.uuid4()))

    # ---- Portfolio Framework Core ----
    portfolio_name: str   = ""
    portfolio_type: str   = ""      # equity / balanced / income / growth
    benchmark:      str   = ""
    currency:       str   = "INR"
    portfolio_value:float = 0.0

    # ---- Construction Engine ----
    n_positions:             int   = 0
    construction_quality:    float = 0.5   # [0, 1]
    min_positions_target:    int   = 5
    max_positions_target:    int   = 50

    # ---- Allocation Engine ----
    equity_weight:           float = 0.60
    bond_weight:             float = 0.30
    cash_weight:             float = 0.10
    alternative_weight:      float = 0.0
    international_weight:    float = 0.0
    target_equity_weight:    float = 0.60
    target_bond_weight:      float = 0.30
    target_cash_weight:      float = 0.10
    equity_drift:            float = 0.0   # equity_weight - target_equity_weight

    # ---- Optimization Engine ----
    optimization_quality:    float = 0.5
    is_at_efficient_frontier:bool  = False
    optimization_score:      float = 0.5

    # ---- Diversification Engine ----
    hhi:                     float = 0.10  # 0=fully diversified, 1=single position
    effective_positions:     float = 10.0  # HHI-adjusted position count
    sector_concentration:    float = 0.30  # max single-sector weight
    country_concentration:   float = 0.90  # max single-country weight
    n_sectors:               int   = 5

    # ---- Risk Engine ----
    portfolio_risk_score:    float = 0.50  # [0, 1] overall risk
    risk_budget_utilization: float = 0.50  # [0, 1]
    var_utilization:         float = 0.50  # Value-at-Risk utilization
    cvar_utilization:        float = 0.50  # CVaR utilization
    is_risk_within_budget:   bool  = True
    max_position_risk:       float = 0.50  # highest single-position risk

    # ---- Performance Engine ----
    sharpe_ratio:            float = 0.50
    alpha:                   float = 0.0
    information_ratio:       float = 0.0
    max_drawdown:            float = 0.05
    ytd_return:              float = 0.0
    tracking_error:          float = 0.02
    calmar_ratio:            float = 1.0

    # ---- Rebalancing Engine ----
    drift_level:             str   = "none"
    rebalance_recommended:   bool  = False
    rebalance_score:         float = 0.50
    days_since_rebalance:    float = 90.0

    # ---- Decision Intelligence ----
    market_regime:           str   = ""    # bull / bear / sideways / volatile
    macro_signal:            float = 0.0   # [-1, 1] bearish … bullish
    signal_confidence:       float = 0.5   # [0, 1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id":           self.portfolio_id,
            "n_positions":            self.n_positions,
            "equity_weight":          round(self.equity_weight, 4),
            "cash_weight":            round(self.cash_weight, 4),
            "risk_budget_utilization":round(self.risk_budget_utilization, 4),
            "sharpe_ratio":           round(self.sharpe_ratio, 4),
            "hhi":                    round(self.hhi, 4),
            "drift_level":            self.drift_level,
            "rebalance_recommended":  self.rebalance_recommended,
            "market_regime":          self.market_regime,
        }


def intelligence_from_any(source: Any) -> PortfolioIntelligence:
    """
    Construct PortfolioIntelligence from a plain instance, dict,
    or duck-typed object.  Plain instances are returned as-is.
    """
    if isinstance(source, PortfolioIntelligence):
        return source
    if isinstance(source, dict):
        return PortfolioIntelligence(**{
            k: v for k, v in source.items()
            if k in PortfolioIntelligence.__dataclass_fields__
        })
    # duck-typed object
    fields = PortfolioIntelligence.__dataclass_fields__
    return PortfolioIntelligence(**{
        k: getattr(source, k)
        for k in fields
        if hasattr(source, k)
    })


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def now_utc() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def recommendation_score_to_grade(score: float) -> RecommendationGrade:
    if score >= REC_SCORE_EXCELLENT:
        return RecommendationGrade.A
    if score >= REC_SCORE_GOOD:
        return RecommendationGrade.B
    if score >= REC_SCORE_AVERAGE:
        return RecommendationGrade.C
    if score >= REC_SCORE_BELOW_AVERAGE:
        return RecommendationGrade.D
    return RecommendationGrade.F


def recommendation_score_to_level(score: float) -> RecommendationLevel:
    if score >= REC_SCORE_EXCELLENT:
        return RecommendationLevel.EXCELLENT
    if score >= REC_SCORE_GOOD:
        return RecommendationLevel.GOOD
    if score >= REC_SCORE_AVERAGE:
        return RecommendationLevel.AVERAGE
    if score >= REC_SCORE_BELOW_AVERAGE:
        return RecommendationLevel.BELOW_AVERAGE
    return RecommendationLevel.POOR


def action_to_category(action: RecommendationAction) -> str:
    """Map a recommendation action to a high-level category."""
    _MAP = {
        RecommendationAction.INCREASE_EQUITY_EXPOSURE:  "allocation",
        RecommendationAction.REDUCE_EQUITY_EXPOSURE:    "allocation",
        RecommendationAction.INCREASE_CASH:             "allocation",
        RecommendationAction.REDUCE_CASH:               "allocation",
        RecommendationAction.INCREASE_SECTOR_EXPOSURE:  "allocation",
        RecommendationAction.REDUCE_SECTOR_EXPOSURE:    "allocation",
        RecommendationAction.INCREASE_INTERNATIONAL:    "allocation",
        RecommendationAction.REDUCE_INTERNATIONAL:      "allocation",
        RecommendationAction.INCREASE_DIVERSIFICATION:  "diversification",
        RecommendationAction.REDUCE_CONCENTRATION:      "diversification",
        RecommendationAction.REBALANCE_PORTFOLIO:       "rebalancing",
        RecommendationAction.DEFENSIVE_POSITIONING:     "risk",
        RecommendationAction.AGGRESSIVE_POSITIONING:    "risk",
        RecommendationAction.HEDGE_PORTFOLIO:           "risk",
        RecommendationAction.RESEARCH_REQUIRED:         "quality",
        RecommendationAction.NO_ACTION:                 "governance",
    }
    return _MAP.get(action, "other")


def priority_to_expiry_hours(
    priority:        RecommendationPriority,
    critical_hours:  float = CRITICAL_EXPIRY_HOURS,
    high_hours:      float = HIGH_EXPIRY_HOURS,
    default_hours:   float = DEFAULT_EXPIRY_HOURS,
    low_hours:       float = LOW_EXPIRY_HOURS,
    no_action_hours: float = NO_ACTION_EXPIRY_HOURS,
) -> float:
    if priority == RecommendationPriority.IMMEDIATE:
        return critical_hours
    if priority == RecommendationPriority.HIGH:
        return high_hours
    if priority == RecommendationPriority.LOW:
        return low_hours
    if priority == RecommendationPriority.INFORMATIONAL:
        return no_action_hours
    return default_hours  # MEDIUM
