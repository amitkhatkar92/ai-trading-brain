"""iios/investment/company/financials/financial_snapshot.py
FinancialSnapshot — the current best view of a company's financials.
Consumers query this; not individual statements.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.financials.financial_period import FinancialPeriod, PeriodType
from iios.investment.company.financials.balance_sheet import BalanceSheet
from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.cash_flow_statement import CashFlowStatement


@dataclass
class FinancialTimeline:
    """Ordered list of period labels with availability flags."""
    entries: List[Dict[str, Any]] = field(default_factory=list)

    def add(self, period: FinancialPeriod, has_bs: bool, has_is: bool, has_cf: bool) -> None:
        self.entries.append({
            "label":    period.label,
            "end_date": period.end_date,
            "has_bs":   has_bs,
            "has_is":   has_is,
            "has_cf":   has_cf,
        })

    def to_dict(self) -> List[Dict[str, Any]]:
        return list(self.entries)


@dataclass
class FinancialSnapshot:
    """
    Point-in-time snapshot of a company's financial intelligence.
    This is the primary object consumed by downstream engines.
    """
    ticker:        str
    generated_at:  float = field(default_factory=time.time)

    # ── Latest statements (best available period) ─────────────────────────────
    latest_annual_bs:   Optional[BalanceSheet]      = None
    latest_annual_is:   Optional[IncomeStatement]   = None
    latest_annual_cf:   Optional[CashFlowStatement] = None

    latest_quarterly_bs:  Optional[BalanceSheet]      = None
    latest_quarterly_is:  Optional[IncomeStatement]   = None
    latest_quarterly_cf:  Optional[CashFlowStatement] = None

    ttm_is:  Optional[IncomeStatement]   = None   # trailing twelve months IS
    ttm_cf:  Optional[CashFlowStatement] = None   # trailing twelve months CF

    # ── Computed ratios (from ratio_calculator) ────────────────────────────────
    ratios: Dict[str, Optional[float]] = field(default_factory=dict)

    # ── Derived balance sheet metrics ─────────────────────────────────────────
    balance_sheet_metrics: Dict[str, Optional[float]] = field(default_factory=dict)

    # ── Derived income statement metrics ──────────────────────────────────────
    income_metrics: Dict[str, Optional[float]] = field(default_factory=dict)

    # ── Derived cash flow metrics ─────────────────────────────────────────────
    cashflow_metrics: Dict[str, Optional[float]] = field(default_factory=dict)

    # ── Quality ───────────────────────────────────────────────────────────────
    quality_score: float = 0.0           # 0–100
    quality_flags: List[str] = field(default_factory=list)

    # ── Timeline ──────────────────────────────────────────────────────────────
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    periods_available: int = 0

    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_annual(self) -> bool:
        return self.latest_annual_is is not None or self.latest_annual_bs is not None

    @property
    def has_ttm(self) -> bool:
        return self.ttm_is is not None

    @property
    def revenue(self) -> Optional[float]:
        if self.ttm_is and self.ttm_is.revenue is not None:
            return self.ttm_is.revenue
        if self.latest_annual_is:
            return self.latest_annual_is.revenue
        return None

    @property
    def net_income(self) -> Optional[float]:
        if self.ttm_is and self.ttm_is.net_income is not None:
            return self.ttm_is.net_income
        if self.latest_annual_is:
            return self.latest_annual_is.net_income
        return None

    @property
    def total_assets(self) -> Optional[float]:
        bs = self.latest_quarterly_bs or self.latest_annual_bs
        return bs.total_assets if bs else None

    @property
    def total_equity(self) -> Optional[float]:
        bs = self.latest_quarterly_bs or self.latest_annual_bs
        return bs.total_equity if bs else None

    @property
    def total_debt(self) -> Optional[float]:
        bs = self.latest_quarterly_bs or self.latest_annual_bs
        return bs.total_debt if bs else None

    @property
    def free_cash_flow(self) -> Optional[float]:
        if self.ttm_cf:
            return self.ttm_cf.free_cash_flow
        if self.latest_annual_cf:
            return self.latest_annual_cf.free_cash_flow
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":         self.ticker,
            "generated_at":   self.generated_at,
            "has_annual":     self.has_annual,
            "has_ttm":        self.has_ttm,
            "periods_available": self.periods_available,
            "latest_annual_bs":  self.latest_annual_bs.to_dict() if self.latest_annual_bs else None,
            "latest_annual_is":  self.latest_annual_is.to_dict() if self.latest_annual_is else None,
            "latest_annual_cf":  self.latest_annual_cf.to_dict() if self.latest_annual_cf else None,
            "latest_quarterly_bs": self.latest_quarterly_bs.to_dict() if self.latest_quarterly_bs else None,
            "latest_quarterly_is": self.latest_quarterly_is.to_dict() if self.latest_quarterly_is else None,
            "latest_quarterly_cf": self.latest_quarterly_cf.to_dict() if self.latest_quarterly_cf else None,
            "ttm_is":         self.ttm_is.to_dict() if self.ttm_is else None,
            "ttm_cf":         self.ttm_cf.to_dict() if self.ttm_cf else None,
            "ratios":         self.ratios,
            "balance_sheet_metrics": self.balance_sheet_metrics,
            "income_metrics": self.income_metrics,
            "cashflow_metrics": self.cashflow_metrics,
            "quality_score":  self.quality_score,
            "quality_flags":  self.quality_flags,
            "timeline":       self.timeline,
            "revenue":        self.revenue,
            "net_income":     self.net_income,
            "total_assets":   self.total_assets,
            "total_equity":   self.total_equity,
            "total_debt":     self.total_debt,
            "free_cash_flow": self.free_cash_flow,
        }
