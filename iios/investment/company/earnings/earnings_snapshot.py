"""iios/investment/company/earnings/earnings_snapshot.py
EarningsSnapshot — the primary output of EarningsIntelligenceEngine.
Consumed by all downstream engines (Valuation, Growth, Risk, Decision).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import (
    EarningsQualityLabel, TrendDirection, ProfitCyclePhase, MomentumLabel,
)


@dataclass
class EarningsQualityScore:
    """Earnings quality from 0 (poor) to 100 (excellent)."""
    label:              EarningsQualityLabel = EarningsQualityLabel.INSUFFICIENT
    overall_score:      float = 0.0

    # Components (0-100 each)
    cash_quality_score:    float = 0.0   # OCF vs reported earnings
    accruals_score:        float = 0.0   # accruals ratio quality
    consistency_score:     float = 0.0   # margin consistency over periods
    persistence_score:     float = 0.0   # recurring earnings proportion
    reliability_score:     float = 0.0   # no restatements, stable reporting

    # Raw inputs
    avg_ocf_to_ni:         Optional[float] = None
    avg_accruals_ratio:    Optional[float] = None
    margin_cv:             Optional[float] = None   # coefficient of variation

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label":               self.label.value,
            "overall_score":       round(self.overall_score, 1),
            "cash_quality_score":  round(self.cash_quality_score, 1),
            "accruals_score":      round(self.accruals_score, 1),
            "consistency_score":   round(self.consistency_score, 1),
            "persistence_score":   round(self.persistence_score, 1),
            "reliability_score":   round(self.reliability_score, 1),
            "avg_ocf_to_ni":       self.avg_ocf_to_ni,
            "avg_accruals_ratio":  self.avg_accruals_ratio,
            "margin_cv":           self.margin_cv,
            "flags":               self.flags,
        }


@dataclass
class ProfitabilityProfile:
    """Profitability metrics from the latest period."""
    # Current period margins
    gross_margin:   Optional[float] = None
    ebitda_margin:  Optional[float] = None
    ebit_margin:    Optional[float] = None
    net_margin:     Optional[float] = None
    fcf_margin:     Optional[float] = None

    # Returns
    roe:   Optional[float] = None
    roa:   Optional[float] = None
    roic:  Optional[float] = None
    roce:  Optional[float] = None

    # Historical averages (from all stored periods)
    avg_gross_margin:  Optional[float] = None
    avg_ebitda_margin: Optional[float] = None
    avg_net_margin:    Optional[float] = None
    avg_roe:           Optional[float] = None
    avg_roic:          Optional[float] = None

    # vs. history
    gross_margin_vs_avg:  Optional[float] = None   # current - avg
    net_margin_vs_avg:    Optional[float] = None
    roe_vs_avg:           Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross_margin":        self.gross_margin,
            "ebitda_margin":       self.ebitda_margin,
            "ebit_margin":         self.ebit_margin,
            "net_margin":          self.net_margin,
            "fcf_margin":          self.fcf_margin,
            "roe":                 self.roe,
            "roa":                 self.roa,
            "roic":                self.roic,
            "roce":                self.roce,
            "avg_gross_margin":    self.avg_gross_margin,
            "avg_ebitda_margin":   self.avg_ebitda_margin,
            "avg_net_margin":      self.avg_net_margin,
            "avg_roe":             self.avg_roe,
            "avg_roic":            self.avg_roic,
            "gross_margin_vs_avg": self.gross_margin_vs_avg,
            "net_margin_vs_avg":   self.net_margin_vs_avg,
            "roe_vs_avg":          self.roe_vs_avg,
        }


@dataclass
class TrendProfile:
    """Earnings and margin trend signals."""
    eps_direction:        TrendDirection = TrendDirection.INSUFFICIENT
    revenue_direction:    TrendDirection = TrendDirection.INSUFFICIENT
    margin_direction:     TrendDirection = TrendDirection.INSUFFICIENT

    eps_growth_rates:     List[Optional[float]] = field(default_factory=list)
    revenue_growth_rates: List[Optional[float]] = field(default_factory=list)
    latest_eps_growth:    Optional[float] = None
    cagr_eps:             Optional[float] = None
    cagr_revenue:         Optional[float] = None

    margin_slope:         Optional[float] = None   # normalised slope of net margin
    margin_acceleration:  Optional[float] = None

    profit_cycle_phase:   ProfitCyclePhase = ProfitCyclePhase.UNKNOWN

    periods_analyzed:     int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eps_direction":        self.eps_direction.value,
            "revenue_direction":    self.revenue_direction.value,
            "margin_direction":     self.margin_direction.value,
            "latest_eps_growth":    self.latest_eps_growth,
            "cagr_eps":             self.cagr_eps,
            "cagr_revenue":         self.cagr_revenue,
            "margin_slope":         self.margin_slope,
            "margin_acceleration":  self.margin_acceleration,
            "profit_cycle_phase":   self.profit_cycle_phase.value,
            "periods_analyzed":     self.periods_analyzed,
            "eps_growth_rates":     self.eps_growth_rates,
        }


@dataclass
class EarningsMomentumProfile:
    """Short-term earnings momentum."""
    label:              MomentumLabel = MomentumLabel.INSUFFICIENT
    score:              float = 50.0   # 0–100

    eps_momentum:       Optional[float] = None   # latest EPS vs trailing avg
    margin_momentum:    Optional[float] = None   # latest margin vs trailing avg
    revenue_momentum:   Optional[float] = None

    periods_used:       int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label":           self.label.value,
            "score":           round(self.score, 1),
            "eps_momentum":    self.eps_momentum,
            "margin_momentum": self.margin_momentum,
            "revenue_momentum": self.revenue_momentum,
            "periods_used":    self.periods_used,
        }


@dataclass
class EarningsRiskProfile:
    """Earnings risk and stability metrics."""
    eps_volatility:        Optional[float] = None   # stdev of EPS growth rates
    margin_volatility:     Optional[float] = None   # stdev of net margin
    revenue_volatility:    Optional[float] = None   # stdev of revenue growth
    ocf_volatility:        Optional[float] = None

    earnings_stability_score: float = 0.0   # 0-100; 100 = perfectly stable
    revision_count:           int   = 0
    revision_bias:            Optional[float] = None   # -1 to +1

    is_cyclical:              bool = False
    consecutive_profit_years: int  = 0

    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eps_volatility":          self.eps_volatility,
            "margin_volatility":       self.margin_volatility,
            "revenue_volatility":      self.revenue_volatility,
            "earnings_stability_score": round(self.earnings_stability_score, 1),
            "revision_count":          self.revision_count,
            "revision_bias":           self.revision_bias,
            "is_cyclical":             self.is_cyclical,
            "consecutive_profit_years": self.consecutive_profit_years,
            "flags":                   self.flags,
        }


@dataclass
class EarningsConfidenceScore:
    """Overall earnings intelligence confidence."""
    score:           float = 0.0   # 0-100
    data_sufficiency: float = 0.0   # how many periods available vs expected
    consistency_confidence: float = 0.0
    quality_confidence: float = 0.0
    label:           str   = "insufficient"   # "high"|"medium"|"low"|"insufficient"

    factors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score":                   round(self.score, 1),
            "label":                   self.label,
            "data_sufficiency":        round(self.data_sufficiency, 1),
            "consistency_confidence":  round(self.consistency_confidence, 1),
            "quality_confidence":      round(self.quality_confidence, 1),
            "factors":                 self.factors,
        }


@dataclass
class EarningsSnapshot:
    """
    Primary earnings intelligence object — consumed by downstream engines.
    Generated by EarningsIntelligenceEngine.
    """
    ticker:       str
    generated_at: float = field(default_factory=time.time)

    # Latest earnings data
    latest_report:  Optional[Any] = None   # EarningsReport (typed as Any to avoid circular)
    history_depth:  int            = 0

    # Intelligence profiles
    quality:       EarningsQualityScore     = field(default_factory=EarningsQualityScore)
    profitability: ProfitabilityProfile     = field(default_factory=ProfitabilityProfile)
    trend:         TrendProfile             = field(default_factory=TrendProfile)
    momentum:      EarningsMomentumProfile  = field(default_factory=EarningsMomentumProfile)
    risk:          EarningsRiskProfile      = field(default_factory=EarningsRiskProfile)
    confidence:    EarningsConfidenceScore  = field(default_factory=EarningsConfidenceScore)

    # Overall score (composite of quality + confidence)
    overall_score: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Convenience properties ─────────────────────────────────────────────────

    @property
    def current_eps(self) -> Optional[float]:
        return self.latest_report.effective_eps() if self.latest_report else None

    @property
    def current_net_margin(self) -> Optional[float]:
        return self.latest_report.net_margin if self.latest_report else None

    @property
    def is_profitable(self) -> bool:
        return self.latest_report.is_profitable() if self.latest_report else False

    @property
    def roe(self) -> Optional[float]:
        return self.latest_report.roe if self.latest_report else None

    @property
    def roic(self) -> Optional[float]:
        return self.latest_report.roic if self.latest_report else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":           self.ticker,
            "generated_at":     self.generated_at,
            "history_depth":    self.history_depth,
            "overall_score":    round(self.overall_score, 1),
            "is_profitable":    self.is_profitable,
            "current_eps":      self.current_eps,
            "current_net_margin": self.current_net_margin,
            "roe":              self.roe,
            "roic":             self.roic,
            "latest_report":    self.latest_report.to_dict() if self.latest_report else None,
            "quality":          self.quality.to_dict(),
            "profitability":    self.profitability.to_dict(),
            "trend":            self.trend.to_dict(),
            "momentum":         self.momentum.to_dict(),
            "risk":             self.risk.to_dict(),
            "confidence":       self.confidence.to_dict(),
        }
