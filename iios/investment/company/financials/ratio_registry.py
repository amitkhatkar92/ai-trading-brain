"""iios/investment/company/financials/ratio_registry.py
Catalog of all standard financial ratios — pluggable and extensible.
Ratios are registered by name; callers add custom ratios via register().
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.company.financials.balance_sheet import BalanceSheet
from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.cash_flow_statement import CashFlowStatement
from iios.investment.company.financials.financial_ratios import (
    RatioCategory,
    RatioDefinition,
    RatioFn,
)


def _safe(fn: RatioFn) -> RatioFn:
    """Wrap a ratio function so division-by-zero returns None."""
    def wrapper(bs, is_, cf):
        try:
            return fn(bs, is_, cf)
        except (TypeError, ZeroDivisionError, AttributeError):
            return None
    return wrapper


def _div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _mul(a: Optional[float], b: float) -> Optional[float]:
    return None if a is None else a * b


# ─────────────────────────── Liquidity ───────────────────────────────────────

def _current_ratio(bs, is_, cf):
    return _div(bs.total_current_assets if bs else None,
                bs.total_current_liabilities if bs else None)


def _quick_ratio(bs, is_, cf):
    if not bs:
        return None
    numer = (bs.total_current_assets or 0) - (bs.inventory or 0)
    return _div(numer, bs.total_current_liabilities)


def _cash_ratio(bs, is_, cf):
    if not bs:
        return None
    numer = (bs.cash_and_equivalents or 0) + (bs.short_term_investments or 0)
    return _div(numer, bs.total_current_liabilities)


# ─────────────────────────── Profitability ───────────────────────────────────

def _gross_margin(bs, is_, cf):
    return is_.gross_margin if is_ else None


def _ebitda_margin(bs, is_, cf):
    return is_.ebitda_margin if is_ else None


def _ebit_margin(bs, is_, cf):
    return is_.ebit_margin if is_ else None


def _net_margin(bs, is_, cf):
    return is_.net_margin if is_ else None


def _roa(bs, is_, cf):
    ni = (is_.net_income_to_common or is_.net_income) if is_ else None
    return _mul(_div(ni, bs.total_assets if bs else None), 100.0)


def _roe(bs, is_, cf):
    ni = (is_.net_income_to_common or is_.net_income) if is_ else None
    return _mul(_div(ni, bs.total_equity if bs else None), 100.0)


def _roce(bs, is_, cf):
    if not bs or not is_:
        return None
    ebit = is_.ebit
    ce   = (bs.total_equity or 0) + (bs.long_term_debt or 0)
    return _mul(_div(ebit, ce), 100.0)


# ─────────────────────────── Leverage ────────────────────────────────────────

def _debt_to_equity(bs, is_, cf):
    if not bs:
        return None
    return _div(bs.total_debt, bs.total_equity)


def _debt_to_assets(bs, is_, cf):
    if not bs:
        return None
    return _div(bs.total_debt, bs.total_assets)


def _equity_ratio(bs, is_, cf):
    if not bs:
        return None
    return _mul(_div(bs.total_equity, bs.total_assets), 100.0)


def _net_debt_to_equity(bs, is_, cf):
    if not bs:
        return None
    net_debt = (bs.total_debt or 0) - (bs.cash_and_equivalents or 0)
    return _div(net_debt, bs.total_equity)


def _debt_to_ebitda(bs, is_, cf):
    if not bs or not is_:
        return None
    return _div(bs.total_debt, is_.ebitda)


# ─────────────────────────── Efficiency ──────────────────────────────────────

def _asset_turnover(bs, is_, cf):
    return _div(is_.revenue if is_ else None, bs.total_assets if bs else None)


def _inventory_turnover(bs, is_, cf):
    return _div(is_.cost_of_revenue if is_ else None, bs.inventory if bs else None)


def _receivables_turnover(bs, is_, cf):
    return _div(is_.revenue if is_ else None, bs.accounts_receivable if bs else None)


def _payables_turnover(bs, is_, cf):
    return _div(is_.cost_of_revenue if is_ else None, bs.accounts_payable if bs else None)


def _days_inventory(bs, is_, cf):
    it = _inventory_turnover(bs, is_, cf)
    return _div(365.0, it)


def _days_receivables(bs, is_, cf):
    rt = _receivables_turnover(bs, is_, cf)
    return _div(365.0, rt)


def _days_payables(bs, is_, cf):
    pt = _payables_turnover(bs, is_, cf)
    return _div(365.0, pt)


def _cash_conversion_cycle(bs, is_, cf):
    di  = _days_inventory(bs, is_, cf)
    dr  = _days_receivables(bs, is_, cf)
    dp  = _days_payables(bs, is_, cf)
    if None in (di, dr, dp):
        return None
    return di + dr - dp


# ─────────────────────────── Cash Flow ───────────────────────────────────────

def _ocf_to_revenue(bs, is_, cf):
    return _mul(_div(cf.operating_cash_flow if cf else None,
                     is_.revenue if is_ else None), 100.0)


def _ocf_to_net_income(bs, is_, cf):
    ni = (is_.net_income_to_common or is_.net_income) if is_ else None
    return _div(cf.operating_cash_flow if cf else None, ni)


def _fcf_to_revenue(bs, is_, cf):
    fcf = cf.free_cash_flow if cf else None
    return _mul(_div(fcf, is_.revenue if is_ else None), 100.0)


def _capex_to_revenue(bs, is_, cf):
    if not cf or not is_:
        return None
    return _mul(_div(abs(cf.capital_expenditure or 0), is_.revenue), 100.0)


def _fcf_yield_on_assets(bs, is_, cf):
    fcf = cf.free_cash_flow if cf else None
    return _mul(_div(fcf, bs.total_assets if bs else None), 100.0)


# ─────────────────────────── Coverage ────────────────────────────────────────

def _interest_coverage(bs, is_, cf):
    return _div(is_.ebit if is_ else None, is_.interest_expense if is_ else None)


def _debt_service_coverage(bs, is_, cf):
    ocf    = cf.operating_cash_flow if cf else None
    debt_r = is_.interest_expense if is_ else None   # proxy
    return _div(ocf, debt_r)


# ─────────────────────────── Per Share ───────────────────────────────────────

def _basic_eps(bs, is_, cf):
    return is_.basic_eps if is_ else None


def _diluted_eps(bs, is_, cf):
    return is_.diluted_eps if is_ else None


def _book_value_per_share(bs, is_, cf):
    if not bs or not is_:
        return None
    shares = is_.shares_outstanding_basic
    return _div(bs.total_equity, shares)


def _fcf_per_share(bs, is_, cf):
    fcf    = cf.free_cash_flow if cf else None
    shares = is_.shares_outstanding_diluted if is_ else None
    return _div(fcf, shares)


# ─────────────────────────── Returns ─────────────────────────────────────────

def _return_on_invested_capital(bs, is_, cf):
    if not bs or not is_:
        return None
    nopat = (is_.ebit or 0) * (1 - (is_.effective_tax_rate or 25) / 100)
    ic    = (bs.total_equity or 0) + (bs.total_debt or 0)
    return _mul(_div(nopat, ic), 100.0)


# ─────────────────────────── Registry class ──────────────────────────────────

class RatioRegistry:
    """Thread-safe catalog of RatioDefinitions keyed by name."""

    _instance: Optional["RatioRegistry"] = None
    _lock:     threading.Lock            = threading.Lock()

    def __init__(self) -> None:
        self._ratios: Dict[str, RatioDefinition] = {}
        self._load_standard_ratios()

    # ── Singleton ─────────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "RatioRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, defn: RatioDefinition) -> None:
        self._ratios[defn.name] = defn

    def get(self, name: str) -> Optional[RatioDefinition]:
        return self._ratios.get(name)

    def list_all(self) -> List[RatioDefinition]:
        return list(self._ratios.values())

    def list_by_category(self, category: RatioCategory) -> List[RatioDefinition]:
        return [r for r in self._ratios.values() if r.category == category]

    def names(self) -> List[str]:
        return list(self._ratios.keys())

    def _load_standard_ratios(self) -> None:
        specs = [
            # Liquidity
            ("current_ratio",         RatioCategory.LIQUIDITY,         "Current Assets / Current Liabilities",          "x",    True,  _current_ratio),
            ("quick_ratio",           RatioCategory.LIQUIDITY,         "(Current Assets - Inventory) / Current Liab.",  "x",    True,  _quick_ratio),
            ("cash_ratio",            RatioCategory.LIQUIDITY,         "(Cash + ST Investments) / Current Liab.",        "x",    True,  _cash_ratio),
            # Profitability
            ("gross_margin",          RatioCategory.PROFITABILITY,     "Gross Profit / Revenue × 100",                  "%",    True,  _gross_margin),
            ("ebitda_margin",         RatioCategory.PROFITABILITY,     "EBITDA / Revenue × 100",                        "%",    True,  _ebitda_margin),
            ("ebit_margin",           RatioCategory.PROFITABILITY,     "EBIT / Revenue × 100",                          "%",    True,  _ebit_margin),
            ("net_margin",            RatioCategory.PROFITABILITY,     "Net Income / Revenue × 100",                    "%",    True,  _net_margin),
            ("roa",                   RatioCategory.RETURNS,           "Net Income / Total Assets × 100",               "%",    True,  _roa),
            ("roe",                   RatioCategory.RETURNS,           "Net Income / Total Equity × 100",               "%",    True,  _roe),
            ("roce",                  RatioCategory.RETURNS,           "EBIT / Capital Employed × 100",                 "%",    True,  _roce),
            ("roic",                  RatioCategory.RETURNS,           "NOPAT / Invested Capital × 100",                "%",    True,  _return_on_invested_capital),
            # Leverage
            ("debt_to_equity",        RatioCategory.LEVERAGE,          "Total Debt / Total Equity",                     "x",    False, _debt_to_equity),
            ("debt_to_assets",        RatioCategory.LEVERAGE,          "Total Debt / Total Assets",                     "x",    False, _debt_to_assets),
            ("equity_ratio",          RatioCategory.CAPITAL_STRUCTURE, "Total Equity / Total Assets × 100",             "%",    True,  _equity_ratio),
            ("net_debt_to_equity",    RatioCategory.LEVERAGE,          "Net Debt / Total Equity",                       "x",    False, _net_debt_to_equity),
            ("debt_to_ebitda",        RatioCategory.LEVERAGE,          "Total Debt / EBITDA",                           "x",    False, _debt_to_ebitda),
            # Efficiency
            ("asset_turnover",        RatioCategory.EFFICIENCY,        "Revenue / Total Assets",                        "x",    True,  _asset_turnover),
            ("inventory_turnover",    RatioCategory.EFFICIENCY,        "COGS / Inventory",                              "x",    True,  _inventory_turnover),
            ("receivables_turnover",  RatioCategory.EFFICIENCY,        "Revenue / Accounts Receivable",                 "x",    True,  _receivables_turnover),
            ("payables_turnover",     RatioCategory.EFFICIENCY,        "COGS / Accounts Payable",                       "x",    None,  _payables_turnover),
            ("days_inventory",        RatioCategory.EFFICIENCY,        "365 / Inventory Turnover",                      "days", False, _days_inventory),
            ("days_receivables",      RatioCategory.EFFICIENCY,        "365 / Receivables Turnover",                    "days", False, _days_receivables),
            ("days_payables",         RatioCategory.EFFICIENCY,        "365 / Payables Turnover",                       "days", True,  _days_payables),
            ("cash_conversion_cycle", RatioCategory.EFFICIENCY,        "DIO + DSO - DPO",                               "days", False, _cash_conversion_cycle),
            # Cash Flow
            ("ocf_to_revenue",        RatioCategory.CASHFLOW,          "Operating CF / Revenue × 100",                  "%",    True,  _ocf_to_revenue),
            ("ocf_to_net_income",     RatioCategory.CASHFLOW,          "Operating CF / Net Income",                     "x",    True,  _ocf_to_net_income),
            ("fcf_to_revenue",        RatioCategory.CASHFLOW,          "Free CF / Revenue × 100",                       "%",    True,  _fcf_to_revenue),
            ("capex_to_revenue",      RatioCategory.CASHFLOW,          "|CapEx| / Revenue × 100",                       "%",    None,  _capex_to_revenue),
            ("fcf_yield_on_assets",   RatioCategory.CASHFLOW,          "Free CF / Total Assets × 100",                  "%",    True,  _fcf_yield_on_assets),
            # Coverage
            ("interest_coverage",     RatioCategory.COVERAGE,          "EBIT / Interest Expense",                       "x",    True,  _interest_coverage),
            ("debt_service_coverage", RatioCategory.COVERAGE,          "Operating CF / Interest Expense",               "x",    True,  _debt_service_coverage),
            # Per share
            ("basic_eps",             RatioCategory.PER_SHARE,         "Net Income / Basic Shares",                     "",     True,  _basic_eps),
            ("diluted_eps",           RatioCategory.PER_SHARE,         "Net Income / Diluted Shares",                   "",     True,  _diluted_eps),
            ("book_value_per_share",  RatioCategory.PER_SHARE,         "Total Equity / Basic Shares",                   "",     True,  _book_value_per_share),
            ("fcf_per_share",         RatioCategory.PER_SHARE,         "Free CF / Diluted Shares",                      "",     True,  _fcf_per_share),
        ]
        for name, cat, desc, unit, hib, fn in specs:
            self.register(RatioDefinition(
                name=name,
                category=cat,
                formula_description=desc,
                unit=unit,
                higher_is_better=hib,
                calculator=_safe(fn),
            ))
