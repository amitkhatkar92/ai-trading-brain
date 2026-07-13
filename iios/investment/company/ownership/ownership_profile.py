"""iios/investment/company/ownership/ownership_profile.py
Core enumerations and dataclass profiles for the Ownership Intelligence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enumerations ──────────────────────────────────────────────────────────────

class ConcentrationLevel(Enum):
    HIGHLY_CONCENTRATED = "highly_concentrated"   # top-10 > 80%
    CONCENTRATED        = "concentrated"          # top-10 60-80%
    MODERATE            = "moderate"              # top-10 40-60%
    DIVERSIFIED         = "diversified"           # top-10 20-40%
    WIDELY_HELD         = "widely_held"           # top-10 < 20%
    UNKNOWN             = "unknown"


class PromoterStabilityLabel(Enum):
    STRONG     = "strong"      # holding ≥50% and stable/increasing
    STABLE     = "stable"      # minimal change, adequate holding
    NEUTRAL    = "neutral"     # minor movement, moderate holding
    DECLINING  = "declining"   # consistent downtrend
    CONCERNING = "concerning"  # rapid selling or very high pledge
    UNKNOWN    = "unknown"


class InstitutionalParticipationLabel(Enum):
    EXCEPTIONAL = "exceptional"   # > 40% institutional
    HIGH        = "high"          # 25-40%
    MODERATE    = "moderate"      # 15-25%
    LOW         = "low"           # 5-15%
    NEGLIGIBLE  = "negligible"    # < 5%
    UNKNOWN     = "unknown"


class InsiderActivityLabel(Enum):
    ACCUMULATING  = "accumulating"    # net buying; strong positive signal
    STEADY        = "steady"          # minor net buying
    NEUTRAL       = "neutral"         # balanced buys/sells
    DISTRIBUTING  = "distributing"    # net selling
    LIQUIDATING   = "liquidating"     # heavy selling; caution signal
    UNKNOWN       = "unknown"


class CapitalAllocationQuality(Enum):
    EXCEPTIONAL  = "exceptional"
    DISCIPLINED  = "disciplined"
    ADEQUATE     = "adequate"
    QUESTIONABLE = "questionable"
    DESTRUCTIVE  = "destructive"
    INSUFFICIENT = "insufficient"


class ShareholderValueLabel(Enum):
    EXCEPTIONAL      = "exceptional"
    STRONG           = "strong"
    ADEQUATE         = "adequate"
    WEAK             = "weak"
    VALUE_DESTRUCTIVE = "value_destructive"
    INSUFFICIENT     = "insufficient"


class OwnershipRiskLabel(Enum):
    LOW      = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH     = "high"
    CRITICAL = "critical"


class OwnershipQualityLabel(Enum):
    EXCEPTIONAL  = "exceptional"
    STRONG       = "strong"
    ADEQUATE     = "adequate"
    WEAK         = "weak"
    POOR         = "poor"
    INSUFFICIENT = "insufficient"


# ── Ownership Structure Profile ───────────────────────────────────────────────

@dataclass
class OwnershipStructureProfile:
    """Current shareholder composition and structure assessment."""
    promoter_holding_pct:        Optional[float] = None   # 0-100
    institutional_holding_pct:   Optional[float] = None
    retail_holding_pct:          Optional[float] = None
    government_holding_pct:      Optional[float] = None
    foreign_holding_pct:         Optional[float] = None
    employee_holding_pct:        Optional[float] = None
    treasury_pct:                Optional[float] = None
    free_float_pct:              Optional[float] = None
    fii_holding_pct:             Optional[float] = None
    dii_holding_pct:             Optional[float] = None
    mutual_fund_holding_pct:     Optional[float] = None
    promoter_pledge_pct:         Optional[float] = None   # % of promoter holding pledged
    top10_holder_pct:            Optional[float] = None

    # Scores (0-100)
    promoter_stability_score:    float = 0.0
    institutional_quality_score: float = 0.0
    free_float_score:            float = 0.0
    distribution_quality_score:  float = 0.0
    overall_structure_score:     float = 0.0

    concentration_level:         ConcentrationLevel          = ConcentrationLevel.UNKNOWN
    promoter_stability:          PromoterStabilityLabel      = PromoterStabilityLabel.UNKNOWN
    institutional_participation: InstitutionalParticipationLabel = InstitutionalParticipationLabel.UNKNOWN

    explanation: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "promoter_holding_pct":        self.promoter_holding_pct,
            "institutional_holding_pct":   self.institutional_holding_pct,
            "retail_holding_pct":          self.retail_holding_pct,
            "free_float_pct":              self.free_float_pct,
            "promoter_pledge_pct":         self.promoter_pledge_pct,
            "promoter_stability_score":    round(self.promoter_stability_score, 1),
            "institutional_quality_score": round(self.institutional_quality_score, 1),
            "free_float_score":            round(self.free_float_score, 1),
            "overall_structure_score":     round(self.overall_structure_score, 1),
            "concentration_level":         self.concentration_level.value,
            "promoter_stability":          self.promoter_stability.value,
            "institutional_participation": self.institutional_participation.value,
        }


# ── Insider Activity Profile ──────────────────────────────────────────────────

@dataclass
class InsiderActivityProfile:
    """Aggregated insider trading and holdings intelligence."""
    insider_ownership_pct:     Optional[float] = None   # 0-100
    ceo_ownership_pct:         Optional[float] = None
    cfo_ownership_pct:         Optional[float] = None
    board_total_ownership_pct: Optional[float] = None
    esop_outstanding_pct:      Optional[float] = None
    net_insider_sentiment:     float = 0.0   # -100 to +100; positive = net buying
    insider_buy_count_6m:      int = 0
    insider_sell_count_6m:     int = 0
    insider_activity_label:    InsiderActivityLabel = InsiderActivityLabel.UNKNOWN

    # Scores (0-100)
    insider_holding_score:  float = 0.0
    insider_buying_score:   float = 0.0
    alignment_score:        float = 0.0   # management skin-in-game

    explanation: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insider_ownership_pct":     self.insider_ownership_pct,
            "ceo_ownership_pct":         self.ceo_ownership_pct,
            "net_insider_sentiment":     round(self.net_insider_sentiment, 1),
            "insider_buy_count_6m":      self.insider_buy_count_6m,
            "insider_sell_count_6m":     self.insider_sell_count_6m,
            "insider_activity_label":    self.insider_activity_label.value,
            "insider_holding_score":     round(self.insider_holding_score, 1),
            "insider_buying_score":      round(self.insider_buying_score, 1),
            "alignment_score":           round(self.alignment_score, 1),
        }


# ── Capital Allocation Profile (Ownership Perspective) ───────────────────────

@dataclass
class OwnershipCapitalAllocationProfile:
    """Capital allocation quality assessed from the shareholder perspective."""
    dividend_policy_score:      float = 0.0
    buyback_quality_score:      float = 0.0
    reinvestment_score:         float = 0.0
    debt_management_score:      float = 0.0
    capex_efficiency_score:     float = 0.0
    cash_utilization_score:     float = 0.0
    overall_capital_score:      float = 0.0
    capital_quality:            CapitalAllocationQuality = CapitalAllocationQuality.INSUFFICIENT
    explanation:                List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dividend_policy_score":   round(self.dividend_policy_score, 1),
            "buyback_quality_score":   round(self.buyback_quality_score, 1),
            "reinvestment_score":      round(self.reinvestment_score, 1),
            "debt_management_score":   round(self.debt_management_score, 1),
            "capex_efficiency_score":  round(self.capex_efficiency_score, 1),
            "cash_utilization_score":  round(self.cash_utilization_score, 1),
            "overall_capital_score":   round(self.overall_capital_score, 1),
            "capital_quality":         self.capital_quality.value,
        }


# ── Shareholder Value Profile ─────────────────────────────────────────────────

@dataclass
class ShareholderValueProfile:
    """Long-term shareholder value creation assessment."""
    economic_return_score:        float = 0.0   # ROIC vs cost of capital proxy
    capital_productivity_score:   float = 0.0   # FCF / invested capital
    dividend_sustainability_score: float = 0.0
    earnings_power_score:         float = 0.0
    growth_value_score:           float = 0.0
    overall_value_score:          float = 0.0
    value_label:                  ShareholderValueLabel = ShareholderValueLabel.INSUFFICIENT
    explanation:                  List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "economic_return_score":         round(self.economic_return_score, 1),
            "capital_productivity_score":    round(self.capital_productivity_score, 1),
            "dividend_sustainability_score": round(self.dividend_sustainability_score, 1),
            "earnings_power_score":          round(self.earnings_power_score, 1),
            "growth_value_score":            round(self.growth_value_score, 1),
            "overall_value_score":           round(self.overall_value_score, 1),
            "value_label":                   self.value_label.value,
        }


# ── Ownership Risk Profile ────────────────────────────────────────────────────

@dataclass
class OwnershipRiskProfile:
    """Ownership-specific risk assessment."""
    pledge_risk_score:        float = 0.0   # 0-100; higher = more risky
    concentration_risk_score: float = 0.0
    dilution_risk_score:      float = 0.0
    control_risk_score:       float = 0.0
    liquidity_risk_score:     float = 0.0   # based on free float
    overall_risk_score:       float = 0.0
    risk_label:               OwnershipRiskLabel = OwnershipRiskLabel.MODERATE
    alerts:                   List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pledge_risk_score":        round(self.pledge_risk_score, 1),
            "concentration_risk_score": round(self.concentration_risk_score, 1),
            "dilution_risk_score":      round(self.dilution_risk_score, 1),
            "control_risk_score":       round(self.control_risk_score, 1),
            "liquidity_risk_score":     round(self.liquidity_risk_score, 1),
            "overall_risk_score":       round(self.overall_risk_score, 1),
            "risk_label":               self.risk_label.value,
            "alerts":                   self.alerts,
        }


# ── Ownership Intelligence Score ──────────────────────────────────────────────

@dataclass
class OwnershipIntelligenceScore:
    """Composite ownership intelligence score."""
    overall_score:            float = 0.0   # 0-100
    ownership_quality_score:  float = 0.0
    capital_allocation_score: float = 0.0
    shareholder_value_score:  float = 0.0
    insider_alignment_score:  float = 0.0
    label:                    OwnershipQualityLabel = OwnershipQualityLabel.INSUFFICIENT
    explanation:              List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":            round(self.overall_score, 1),
            "ownership_quality_score":  round(self.ownership_quality_score, 1),
            "capital_allocation_score": round(self.capital_allocation_score, 1),
            "shareholder_value_score":  round(self.shareholder_value_score, 1),
            "insider_alignment_score":  round(self.insider_alignment_score, 1),
            "label":                    self.label.value,
        }
