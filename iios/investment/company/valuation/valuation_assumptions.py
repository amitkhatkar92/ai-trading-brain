"""iios/investment/company/valuation/valuation_assumptions.py
Configurable assumption sets for all valuation models.
No assumptions are hardcoded — all are parameterised and explainable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WACCAssumptions:
    """Weighted Average Cost of Capital parameters."""

    # Cost of equity components
    risk_free_rate:    float = 0.065   # 10-yr govt bond yield (localise per market)
    equity_risk_premium: float = 0.055  # ERP (Damodaran market-specific)
    beta:              float = 1.0     # Can be provided or computed from sector

    # Cost of debt
    cost_of_debt:      float = 0.08   # Pre-tax cost of debt
    tax_rate:          float = 0.25   # Effective corporate tax rate

    # Capital structure
    debt_weight:       float = 0.30   # D / (D + E)
    equity_weight:     float = 0.70   # E / (D + E)

    # Direct override (used by scenario engine to shift WACC without changing components)
    wacc_override:     Optional[float] = None

    def cost_of_equity(self) -> float:
        return self.risk_free_rate + self.beta * self.equity_risk_premium

    def cost_of_debt_after_tax(self) -> float:
        return self.cost_of_debt * (1.0 - self.tax_rate)

    def wacc(self) -> float:
        if self.wacc_override is not None:
            return self.wacc_override
        return (
            self.cost_of_equity() * self.equity_weight
            + self.cost_of_debt_after_tax() * self.debt_weight
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_free_rate":    self.risk_free_rate,
            "equity_risk_premium": self.equity_risk_premium,
            "beta":              self.beta,
            "cost_of_debt":      self.cost_of_debt,
            "tax_rate":          self.tax_rate,
            "debt_weight":       self.debt_weight,
            "equity_weight":     self.equity_weight,
            "computed_wacc":     round(self.wacc(), 4),
            "cost_of_equity":    round(self.cost_of_equity(), 4),
        }


@dataclass
class DCFAssumptions:
    """DCF model parameters — two-stage projection + terminal value."""

    wacc:               WACCAssumptions = field(default_factory=WACCAssumptions)
    projection_years:   int             = 10
    near_term_years:    int             = 5     # phase-1 growth period

    # Growth rates
    near_term_growth:   float = 0.12   # FCF CAGR in years 1-5
    mid_term_growth:    float = 0.08   # FCF CAGR in years 6-10
    terminal_growth:    float = 0.04   # Perpetuity growth (GDP proxy)

    # Terminal value method
    terminal_method:    str   = "gordon"   # "gordon" | "multiple"
    terminal_fcf_multiple: float = 15.0   # EV/FCF multiple at terminal (only if method=="multiple")

    # FCF override: if None, derived from financial/earnings data
    fcf_base_override:  Optional[float] = None

    def terminal_discount_check(self) -> bool:
        """WACC must exceed terminal growth for Gordon Growth to be valid."""
        return self.wacc.wacc() > self.terminal_growth

    def to_dict(self) -> Dict[str, Any]:
        return {
            "projection_years": self.projection_years,
            "near_term_growth": self.near_term_growth,
            "mid_term_growth":  self.mid_term_growth,
            "terminal_growth":  self.terminal_growth,
            "terminal_method":  self.terminal_method,
            "wacc":             self.wacc.to_dict(),
        }


@dataclass
class DDMAssumptions:
    """Dividend Discount Model parameters."""

    cost_of_equity:    WACCAssumptions = field(default_factory=WACCAssumptions)
    dividend_growth:   float = 0.06    # Sustainable dividend growth rate
    payout_ratio:      Optional[float] = None  # if None, derived from data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cost_of_equity": self.cost_of_equity.to_dict(),
            "dividend_growth": self.dividend_growth,
            "payout_ratio":   self.payout_ratio,
        }


@dataclass
class RIMAssumptions:
    """Residual Income Model parameters."""

    cost_of_equity:    WACCAssumptions = field(default_factory=WACCAssumptions)
    roe_fade_years:    int   = 10      # Years until ROE fades to cost of equity
    roe_mean_reversion: float = 0.12  # Long-run ROE target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cost_of_equity": round(self.cost_of_equity.cost_of_equity(), 4),
            "roe_fade_years": self.roe_fade_years,
            "roe_mean_reversion": self.roe_mean_reversion,
        }


@dataclass
class RelativeValuationAssumptions:
    """Relative valuation parameters."""

    # Target multiples (None = use historical median or peer median)
    target_pe:         Optional[float] = None
    target_ev_ebitda:  Optional[float] = None
    target_pb:         Optional[float] = None
    target_ev_sales:   Optional[float] = None
    target_pfcf:       Optional[float] = None

    # Historical lookback for own-history median
    historical_periods: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_pe":        self.target_pe,
            "target_ev_ebitda": self.target_ev_ebitda,
            "target_pb":        self.target_pb,
            "target_ev_sales":  self.target_ev_sales,
            "target_pfcf":      self.target_pfcf,
        }


@dataclass
class ValuationAssumptions:
    """
    Master assumption set passed to ValuationIntelligenceEngine.
    All fields have sensible defaults; override for company-specific calibration.
    """
    dcf:         DCFAssumptions               = field(default_factory=DCFAssumptions)
    ddm:         DDMAssumptions               = field(default_factory=DDMAssumptions)
    rim:         RIMAssumptions               = field(default_factory=RIMAssumptions)
    relative:    RelativeValuationAssumptions  = field(default_factory=RelativeValuationAssumptions)

    # Company / market context
    currency:            str            = "INR"
    shares_outstanding:  Optional[float] = None   # override; else derived from financial data
    net_debt_override:   Optional[float] = None   # override for net debt (total debt - cash)

    # Model weights for blending (0 = exclude model)
    model_weights: Dict[str, float] = field(default_factory=lambda: {
        "dcf":            0.40,
        "relative":       0.35,
        "residual_income": 0.15,
        "asset_based":    0.05,
        "ddm":            0.05,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dcf":              self.dcf.to_dict(),
            "ddm":              self.ddm.to_dict(),
            "rim":              self.rim.to_dict(),
            "relative":         self.relative.to_dict(),
            "currency":         self.currency,
            "model_weights":    self.model_weights,
        }
