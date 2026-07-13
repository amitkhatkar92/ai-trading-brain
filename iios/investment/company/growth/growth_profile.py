"""iios/investment/company/growth/growth_profile.py
Core data types and enumerations for the Growth Intelligence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GrowthTrend(Enum):
    ACCELERATING      = "accelerating"
    STABLE            = "stable"
    DECELERATING      = "decelerating"
    DECLINING         = "declining"
    RECOVERING        = "recovering"
    VOLATILE          = "volatile"
    INSUFFICIENT_DATA = "insufficient_data"


class GrowthLabel(Enum):
    EXCEPTIONAL        = "exceptional"   # CAGR >= 25%
    STRONG             = "strong"        # 15-25%
    MODERATE           = "moderate"      # 8-15%
    WEAK               = "weak"          # 0-8%
    NEGATIVE           = "negative"      # < 0%
    INSUFFICIENT_DATA  = "insufficient_data"


@dataclass
class CAGRProfile:
    """Compound Annual Growth Rate across multiple time horizons."""
    cagr_1y:          Optional[float] = None
    cagr_3y:          Optional[float] = None
    cagr_5y:          Optional[float] = None
    cagr_10y:         Optional[float] = None
    best_available:   Optional[float] = None   # Most reliable CAGR given data depth
    trend:            GrowthTrend     = GrowthTrend.INSUFFICIENT_DATA
    periods_used:     int             = 0
    label:            GrowthLabel     = GrowthLabel.INSUFFICIENT_DATA

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cagr_1y":        round(self.cagr_1y, 4)        if self.cagr_1y    is not None else None,
            "cagr_3y":        round(self.cagr_3y, 4)        if self.cagr_3y    is not None else None,
            "cagr_5y":        round(self.cagr_5y, 4)        if self.cagr_5y    is not None else None,
            "cagr_10y":       round(self.cagr_10y, 4)       if self.cagr_10y   is not None else None,
            "best_available": round(self.best_available, 4)  if self.best_available is not None else None,
            "trend":          self.trend.value,
            "periods_used":   self.periods_used,
            "label":          self.label.value,
        }


@dataclass
class RevenueGrowthProfile:
    """Revenue growth intelligence."""
    cagr:                CAGRProfile   = field(default_factory=CAGRProfile)
    yoy:                 Optional[float] = None   # Year-over-year growth
    qoq:                 Optional[float] = None   # Quarter-over-quarter growth
    organic_estimate:    Optional[float] = None   # Organic growth estimate
    trend:               GrowthTrend   = GrowthTrend.INSUFFICIENT_DATA
    explanation:         List[str]     = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cagr":             self.cagr.to_dict(),
            "yoy":              round(self.yoy, 4)             if self.yoy             is not None else None,
            "qoq":              round(self.qoq, 4)             if self.qoq             is not None else None,
            "organic_estimate": round(self.organic_estimate, 4) if self.organic_estimate is not None else None,
            "trend":            self.trend.value,
            "explanation":      self.explanation,
        }


@dataclass
class EarningsGrowthProfile:
    """Earnings and EPS growth intelligence."""
    eps_cagr:                 CAGRProfile = field(default_factory=CAGRProfile)
    net_income_cagr:          CAGRProfile = field(default_factory=CAGRProfile)
    ebitda_growth:            Optional[float] = None
    operating_profit_growth:  Optional[float] = None
    yoy_eps:                  Optional[float] = None
    trend:                    GrowthTrend = GrowthTrend.INSUFFICIENT_DATA
    explanation:              List[str]   = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eps_cagr":               self.eps_cagr.to_dict(),
            "net_income_cagr":        self.net_income_cagr.to_dict(),
            "ebitda_growth":          self.ebitda_growth,
            "operating_profit_growth": self.operating_profit_growth,
            "yoy_eps":                self.yoy_eps,
            "trend":                  self.trend.value,
            "explanation":            self.explanation,
        }


@dataclass
class MarginGrowthProfile:
    """Margin expansion / contraction intelligence."""
    gross_margin_expansion_bps:  Optional[float] = None   # basis points per year; + = expanding
    ebitda_margin_expansion_bps: Optional[float] = None
    net_margin_expansion_bps:    Optional[float] = None
    is_expanding:                Optional[bool]  = None
    is_contracting:              Optional[bool]  = None
    current_net_margin:          Optional[float] = None
    avg_net_margin:              Optional[float] = None
    current_gross_margin:        Optional[float] = None
    avg_gross_margin:            Optional[float] = None
    trend:                       GrowthTrend     = GrowthTrend.INSUFFICIENT_DATA
    explanation:                 List[str]       = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross_margin_expansion_bps":  self.gross_margin_expansion_bps,
            "ebitda_margin_expansion_bps": self.ebitda_margin_expansion_bps,
            "net_margin_expansion_bps":    self.net_margin_expansion_bps,
            "is_expanding":                self.is_expanding,
            "is_contracting":              self.is_contracting,
            "current_net_margin":          self.current_net_margin,
            "avg_net_margin":              self.avg_net_margin,
            "trend":                       self.trend.value,
            "explanation":                 self.explanation,
        }


@dataclass
class CashflowGrowthProfile:
    """Free cash flow and operating cash flow growth intelligence."""
    fcf_cagr:           CAGRProfile = field(default_factory=CAGRProfile)
    ocf_cagr:           CAGRProfile = field(default_factory=CAGRProfile)
    current_fcf_margin: Optional[float] = None
    avg_fcf_margin:     Optional[float] = None
    fcf_margin_trend:   GrowthTrend = GrowthTrend.INSUFFICIENT_DATA
    explanation:        List[str]   = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fcf_cagr":           self.fcf_cagr.to_dict(),
            "ocf_cagr":           self.ocf_cagr.to_dict(),
            "current_fcf_margin": self.current_fcf_margin,
            "avg_fcf_margin":     self.avg_fcf_margin,
            "fcf_margin_trend":   self.fcf_margin_trend.value,
            "explanation":        self.explanation,
        }


@dataclass
class GrowthDriverProfile:
    """Identified growth drivers and their strength."""
    detected_drivers:         List[str] = field(default_factory=list)
    primary_driver:           Optional[str] = None
    operational_leverage_score: float = 0.0   # 0-100
    pricing_power_score:      float = 0.0
    market_expansion_score:   float = 0.0
    innovation_score:         float = 0.0
    driver_confidence:        float = 0.0
    explanation:              List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected_drivers":           self.detected_drivers,
            "primary_driver":             self.primary_driver,
            "operational_leverage_score": round(self.operational_leverage_score, 1),
            "pricing_power_score":        round(self.pricing_power_score, 1),
            "market_expansion_score":     round(self.market_expansion_score, 1),
            "innovation_score":           round(self.innovation_score, 1),
            "driver_confidence":          round(self.driver_confidence, 2),
            "explanation":                self.explanation,
        }


@dataclass
class GrowthSustainabilityProfile:
    """Growth sustainability, consistency and risk assessment."""
    sustainability_score: float = 0.0   # 0-100
    consistency_score:    float = 0.0
    resilience_score:     float = 0.0
    cyclicality:          float = 0.0   # 0-100; higher = more cyclical
    predictability:       float = 0.0   # 0-100
    is_sustainable:       bool  = False
    risk_factors:         List[str] = field(default_factory=list)
    explanation:          List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sustainability_score": round(self.sustainability_score, 1),
            "consistency_score":    round(self.consistency_score, 1),
            "resilience_score":     round(self.resilience_score, 1),
            "cyclicality":          round(self.cyclicality, 1),
            "predictability":       round(self.predictability, 1),
            "is_sustainable":       self.is_sustainable,
            "risk_factors":         self.risk_factors,
            "explanation":          self.explanation,
        }


@dataclass
class GrowthForecastProfile:
    """Forward-looking growth estimates across scenarios."""
    base_revenue_growth:    Optional[float] = None
    bull_revenue_growth:    Optional[float] = None
    bear_revenue_growth:    Optional[float] = None
    base_eps_growth:        Optional[float] = None
    bull_eps_growth:        Optional[float] = None
    bear_eps_growth:        Optional[float] = None
    forecast_horizon_years: int   = 3
    forecast_confidence:    float = 0.0
    forecast_basis:         str   = "historical_extrapolation"  # | "mean_reversion" | "trend_adjusted"
    explanation:            List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_revenue_growth": self.base_revenue_growth,
            "bull_revenue_growth": self.bull_revenue_growth,
            "bear_revenue_growth": self.bear_revenue_growth,
            "base_eps_growth":     self.base_eps_growth,
            "bull_eps_growth":     self.bull_eps_growth,
            "bear_eps_growth":     self.bear_eps_growth,
            "horizon_years":       self.forecast_horizon_years,
            "confidence":          round(self.forecast_confidence, 2),
            "basis":               self.forecast_basis,
            "explanation":         self.explanation,
        }


@dataclass
class GrowthQuality:
    """Quality assessment of the growth data and estimates."""
    quality_label:      str   = "insufficient"   # exceptional/strong/moderate/weak/poor
    data_completeness:  float = 0.0              # 0-1
    is_high_quality:    bool  = False
    issues:             List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality_label":     self.quality_label,
            "data_completeness": round(self.data_completeness, 2),
            "is_high_quality":   self.is_high_quality,
            "issues":            self.issues,
        }


@dataclass
class GrowthIntelligenceScore:
    """Overall Growth Intelligence Score (0-100)."""
    overall_score:              float = 0.0
    revenue_growth_score:       float = 0.0
    profit_growth_score:        float = 0.0
    cashflow_growth_score:      float = 0.0
    sustainability_score:       float = 0.0
    forecast_confidence_score:  float = 0.0
    label:                      str   = "insufficient"
    explanation:                List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":             round(self.overall_score, 1),
            "label":                     self.label,
            "revenue_growth_score":      round(self.revenue_growth_score, 1),
            "profit_growth_score":       round(self.profit_growth_score, 1),
            "cashflow_growth_score":     round(self.cashflow_growth_score, 1),
            "sustainability_score":      round(self.sustainability_score, 1),
            "forecast_confidence_score": round(self.forecast_confidence_score, 1),
            "explanation":               self.explanation,
        }


def classify_growth(rate: Optional[float]) -> GrowthLabel:
    """Classify a growth rate into a label."""
    if rate is None:
        return GrowthLabel.INSUFFICIENT_DATA
    if rate >= 0.25:
        return GrowthLabel.EXCEPTIONAL
    if rate >= 0.15:
        return GrowthLabel.STRONG
    if rate >= 0.08:
        return GrowthLabel.MODERATE
    if rate >= 0.0:
        return GrowthLabel.WEAK
    return GrowthLabel.NEGATIVE
