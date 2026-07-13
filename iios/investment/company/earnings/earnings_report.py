"""iios/investment/company/earnings/earnings_report.py
EarningsReport — atomic unit of per-period earnings data extracted
from FinancialSnapshot. Contains no raw statement parsing.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ─────────────────────────── Domain enums ─────────────────────────────────────

class TrendDirection(str, Enum):
    ACCELERATING   = "accelerating"
    DECELERATING   = "decelerating"
    STABLE         = "stable"
    RECOVERING     = "recovering"
    DETERIORATING  = "deteriorating"
    REVERSAL_UP    = "reversal_up"
    REVERSAL_DOWN  = "reversal_down"
    INSUFFICIENT   = "insufficient_data"


class EarningsQualityLabel(str, Enum):
    HIGH           = "high"
    ABOVE_AVERAGE  = "above_average"
    AVERAGE        = "average"
    BELOW_AVERAGE  = "below_average"
    LOW            = "low"
    INSUFFICIENT   = "insufficient_data"


class ProfitCyclePhase(str, Enum):
    EXPANSION      = "expansion"    # margins rising above historical avg
    PEAK           = "peak"         # margins near high, growth slowing
    CONTRACTION    = "contraction"  # margins falling from peak
    TROUGH         = "trough"       # margins at low, decline slowing
    RECOVERY       = "recovery"     # margins rising from trough
    UNKNOWN        = "unknown"


class EarningsType(str, Enum):
    REPORTED   = "reported"    # as filed
    ADJUSTED   = "adjusted"    # non-recurring stripped
    OPERATING  = "operating"   # EBIT-based
    CORE       = "core"        # management-adjusted
    CASH       = "cash"        # OCF-based


class MomentumLabel(str, Enum):
    STRONG_POSITIVE = "strong_positive"
    POSITIVE        = "positive"
    NEUTRAL         = "neutral"
    NEGATIVE        = "negative"
    STRONG_NEGATIVE = "strong_negative"
    INSUFFICIENT    = "insufficient_data"


# ─────────────────────────── Core model ───────────────────────────────────────

@dataclass
class EarningsReport:
    """
    Per-period earnings intelligence extracted from FinancialSnapshot.
    This is the atomic unit stored in EarningsHistory.
    """
    period_label:  str
    end_date:      str
    period_type:   str           # "annual" | "quarterly" | "ttm"
    fiscal_year:   int
    quarter:       Optional[int]  # 1-4 for quarterly; None for annual/TTM

    # ── Core earnings ─────────────────────────────────────────────────────────
    revenue:              Optional[float] = None
    gross_profit:         Optional[float] = None
    ebitda:               Optional[float] = None
    ebit:                 Optional[float] = None
    net_income:           Optional[float] = None
    net_income_to_common: Optional[float] = None
    basic_eps:            Optional[float] = None
    diluted_eps:          Optional[float] = None

    # ── Margins (%) ───────────────────────────────────────────────────────────
    gross_margin:   Optional[float] = None
    ebitda_margin:  Optional[float] = None
    ebit_margin:    Optional[float] = None
    net_margin:     Optional[float] = None

    # ── Returns (%) ───────────────────────────────────────────────────────────
    roe:   Optional[float] = None
    roa:   Optional[float] = None
    roic:  Optional[float] = None
    roce:  Optional[float] = None

    # ── Cash earnings quality ─────────────────────────────────────────────────
    operating_cash_flow:  Optional[float] = None
    free_cash_flow:       Optional[float] = None
    ocf_to_net_income:    Optional[float] = None   # ratio >1 = strong
    fcf_margin:           Optional[float] = None   # %

    # ── Accruals ──────────────────────────────────────────────────────────────
    accruals_ratio:       Optional[float] = None   # (NI-OCF)/Assets; <0.05 ideal
    sloan_ratio:          Optional[float] = None   # (NI-OCF-ICF)/avg_assets

    # ── Cost structure (% of revenue) ─────────────────────────────────────────
    cost_of_revenue_pct:  Optional[float] = None
    sga_pct:              Optional[float] = None
    rd_pct:               Optional[float] = None
    da_pct:               Optional[float] = None
    interest_pct:         Optional[float] = None
    effective_tax_rate:   Optional[float] = None

    # ── Quality flags ─────────────────────────────────────────────────────────
    is_restated:          bool = False
    has_high_accruals:    bool = False   # accruals_ratio > 0.10
    is_cash_backed:       bool = False   # ocf_to_net_income >= 0.8

    source:     str   = "financial_statement_engine"
    created_at: float = field(default_factory=time.time)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def effective_earnings(self) -> Optional[float]:
        return self.net_income_to_common if self.net_income_to_common is not None else self.net_income

    def effective_eps(self) -> Optional[float]:
        return self.diluted_eps if self.diluted_eps is not None else self.basic_eps

    def is_profitable(self) -> bool:
        ni = self.effective_earnings()
        return ni is not None and ni > 0

    def cash_quality(self) -> Optional[float]:
        """Cash earnings quality: 0–1 (1 = perfectly cash-backed)."""
        ratio = self.ocf_to_net_income
        if ratio is None:
            return None
        return min(1.0, max(0.0, ratio))   # clamp to [0,1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_label":        self.period_label,
            "end_date":            self.end_date,
            "period_type":         self.period_type,
            "fiscal_year":         self.fiscal_year,
            "quarter":             self.quarter,
            "revenue":             self.revenue,
            "gross_profit":        self.gross_profit,
            "ebitda":              self.ebitda,
            "ebit":                self.ebit,
            "net_income":          self.net_income,
            "net_income_to_common": self.net_income_to_common,
            "basic_eps":           self.basic_eps,
            "diluted_eps":         self.diluted_eps,
            "gross_margin":        self.gross_margin,
            "ebitda_margin":       self.ebitda_margin,
            "ebit_margin":         self.ebit_margin,
            "net_margin":          self.net_margin,
            "roe":                 self.roe,
            "roa":                 self.roa,
            "roic":                self.roic,
            "roce":                self.roce,
            "operating_cash_flow": self.operating_cash_flow,
            "free_cash_flow":      self.free_cash_flow,
            "ocf_to_net_income":   self.ocf_to_net_income,
            "fcf_margin":          self.fcf_margin,
            "accruals_ratio":      self.accruals_ratio,
            "sloan_ratio":         self.sloan_ratio,
            "cost_of_revenue_pct": self.cost_of_revenue_pct,
            "sga_pct":             self.sga_pct,
            "da_pct":              self.da_pct,
            "effective_tax_rate":  self.effective_tax_rate,
            "is_restated":         self.is_restated,
            "has_high_accruals":   self.has_high_accruals,
            "is_cash_backed":      self.is_cash_backed,
            "is_profitable":       self.is_profitable(),
            "effective_eps":       self.effective_eps(),
            "effective_earnings":  self.effective_earnings(),
        }

    @staticmethod
    def from_snapshot(snapshot: Any, period_type: str = "annual") -> Optional["EarningsReport"]:
        """
        Build EarningsReport from a FinancialSnapshot.
        Import FinancialSnapshot lazily to avoid circular imports.
        """
        try:
            is_ = snapshot.ttm_is if period_type == "ttm" else snapshot.latest_annual_is
            if is_ is None:
                return None

            p   = is_.period
            bs  = snapshot.latest_quarterly_bs or snapshot.latest_annual_bs
            cf  = snapshot.ttm_cf if period_type == "ttm" else snapshot.latest_annual_cf

            r = EarningsReport(
                period_label=p.label,
                end_date=p.end_date,
                period_type=period_type,
                fiscal_year=p.fiscal_year,
                quarter=p.quarter,
            )

            # Core earnings from IS
            r.revenue              = is_.revenue
            r.gross_profit         = is_.gross_profit
            r.ebitda               = is_.ebitda
            r.ebit                 = is_.ebit
            r.net_income           = is_.net_income
            r.net_income_to_common = is_.net_income_to_common
            r.basic_eps            = is_.basic_eps
            r.diluted_eps          = is_.diluted_eps
            r.effective_tax_rate   = is_.effective_tax_rate

            # Margins
            r.gross_margin   = is_.gross_margin
            r.ebitda_margin  = is_.ebitda_margin
            r.ebit_margin    = is_.ebit_margin
            r.net_margin     = is_.net_margin

            # Returns from computed ratios
            ratios = snapshot.ratios or {}
            r.roe  = ratios.get("roe")
            r.roa  = ratios.get("roa")
            r.roic = ratios.get("roic")
            r.roce = ratios.get("roce")

            # Cash metrics from cashflow_metrics
            cfm = snapshot.cashflow_metrics or {}
            r.operating_cash_flow = cfm.get("operating_cash_flow")
            r.free_cash_flow      = cfm.get("free_cash_flow")
            r.ocf_to_net_income   = cfm.get("ocf_to_net_income")
            r.fcf_margin          = cfm.get("fcf_margin")

            # Income metrics for cost structure
            im = snapshot.income_metrics or {}
            r.da_pct = im.get("da_pct")
            r.effective_tax_rate = r.effective_tax_rate or im.get("tax_rate")

            if cf is not None:
                r.cost_of_revenue_pct = (
                    100.0 * (is_.cost_of_revenue or 0) / is_.revenue
                    if is_.revenue and is_.revenue > 0 and is_.cost_of_revenue else None
                )
                r.interest_pct = (
                    100.0 * (is_.interest_expense or 0) / is_.revenue
                    if is_.revenue and is_.revenue > 0 and is_.interest_expense else None
                )

            # Accruals ratio: (NI - OCF) / Total Assets
            ni       = r.net_income
            ocf      = r.operating_cash_flow
            ta       = snapshot.total_assets
            if ni is not None and ocf is not None and ta and ta != 0:
                r.accruals_ratio = (ni - ocf) / ta

            # Sloan ratio: (NI - OCF - ICF) / avg_assets (proxy: use same TA)
            if cf is not None and ni is not None and ocf is not None and ta and ta != 0:
                icf = cf.investing_cash_flow or 0.0
                r.sloan_ratio = (ni - ocf - icf) / ta

            # Quality flags
            if r.accruals_ratio is not None:
                r.has_high_accruals = r.accruals_ratio > 0.10
            if r.ocf_to_net_income is not None:
                r.is_cash_backed = r.ocf_to_net_income >= 0.8

            return r
        except Exception:
            return None
