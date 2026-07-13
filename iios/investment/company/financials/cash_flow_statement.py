"""iios/investment/company/financials/cash_flow_statement.py
Raw cash flow statement data model — no analysis, no scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.financial_period import FinancialPeriod, FinancialUnit


@dataclass
class CashFlowStatement:
    """Raw cash flow statement for one financial period."""
    period:   FinancialPeriod
    currency: str           = "INR"
    unit:     FinancialUnit = FinancialUnit.CRORES
    restated: bool          = False

    # ── Operating activities ───────────────────────────────────────────────────
    net_income_cf:                Optional[float] = None   # net income as starting point
    depreciation_amortization_cf: Optional[float] = None
    changes_in_working_capital:   Optional[float] = None
    changes_in_receivables:       Optional[float] = None
    changes_in_inventory:         Optional[float] = None
    changes_in_payables:          Optional[float] = None
    deferred_tax_cf:              Optional[float] = None
    other_operating_adjustments:  Optional[float] = None
    operating_cash_flow:          Optional[float] = None   # net CFO

    # ── Investing activities ───────────────────────────────────────────────────
    capital_expenditure:          Optional[float] = None   # negative = outflow
    acquisitions:                 Optional[float] = None   # negative = paid
    proceeds_from_disposals:      Optional[float] = None
    purchases_of_investments:     Optional[float] = None
    proceeds_from_investments:    Optional[float] = None
    other_investing:              Optional[float] = None
    investing_cash_flow:          Optional[float] = None   # net CFI

    # ── Financing activities ───────────────────────────────────────────────────
    debt_issued:                  Optional[float] = None
    debt_repaid:                  Optional[float] = None
    equity_issued:                Optional[float] = None
    equity_repurchased:           Optional[float] = None   # buybacks (negative)
    dividends_paid:               Optional[float] = None   # negative
    other_financing:              Optional[float] = None
    financing_cash_flow:          Optional[float] = None   # net CFF

    # ── Reconciliation ────────────────────────────────────────────────────────
    forex_effect_on_cash:         Optional[float] = None
    net_change_in_cash:           Optional[float] = None
    beginning_cash:               Optional[float] = None
    ending_cash:                  Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def free_cash_flow(self) -> Optional[float]:
        """FCF = OCF - CapEx (using absolute CapEx value)."""
        ocf   = self.operating_cash_flow
        capex = self.capital_expenditure
        if ocf is None:
            return None
        if capex is None:
            return ocf
        # CapEx stored as negative outflow conventionally; take abs
        return ocf - abs(capex)

    @property
    def maintenance_capex_proxy(self) -> Optional[float]:
        """Proxy for maintenance CapEx using D&A (rough)."""
        return self.depreciation_amortization_cf

    def completeness_pct(self) -> float:
        key_fields = [
            self.operating_cash_flow, self.capital_expenditure,
            self.investing_cash_flow, self.financing_cash_flow,
            self.net_change_in_cash,
        ]
        filled = sum(1 for f in key_fields if f is not None)
        return 100.0 * filled / len(key_fields)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period":   self.period.to_dict(),
            "currency": self.currency,
            "unit":     self.unit.value,
            "restated": self.restated,
            "net_income_cf":                self.net_income_cf,
            "depreciation_amortization_cf": self.depreciation_amortization_cf,
            "changes_in_working_capital":   self.changes_in_working_capital,
            "other_operating_adjustments":  self.other_operating_adjustments,
            "operating_cash_flow":          self.operating_cash_flow,
            "capital_expenditure":          self.capital_expenditure,
            "acquisitions":                 self.acquisitions,
            "other_investing":              self.other_investing,
            "investing_cash_flow":          self.investing_cash_flow,
            "debt_issued":                  self.debt_issued,
            "debt_repaid":                  self.debt_repaid,
            "dividends_paid":               self.dividends_paid,
            "equity_repurchased":           self.equity_repurchased,
            "financing_cash_flow":          self.financing_cash_flow,
            "net_change_in_cash":           self.net_change_in_cash,
            "beginning_cash":               self.beginning_cash,
            "ending_cash":                  self.ending_cash,
            # computed
            "free_cash_flow": self.free_cash_flow,
            "completeness_pct": round(self.completeness_pct(), 1),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any], period: FinancialPeriod) -> "CashFlowStatement":
        cf = CashFlowStatement(period=period)
        for field_name in (
            "net_income_cf", "depreciation_amortization_cf",
            "changes_in_working_capital", "changes_in_receivables",
            "changes_in_inventory", "changes_in_payables", "deferred_tax_cf",
            "other_operating_adjustments", "operating_cash_flow",
            "capital_expenditure", "acquisitions", "proceeds_from_disposals",
            "purchases_of_investments", "proceeds_from_investments",
            "other_investing", "investing_cash_flow", "debt_issued", "debt_repaid",
            "equity_issued", "equity_repurchased", "dividends_paid",
            "other_financing", "financing_cash_flow", "forex_effect_on_cash",
            "net_change_in_cash", "beginning_cash", "ending_cash",
        ):
            val = data.get(field_name)
            if val is not None:
                try:
                    setattr(cf, field_name, float(val))
                except (TypeError, ValueError):
                    pass
        cf.currency = str(data.get("currency", "INR"))
        cf.restated  = bool(data.get("restated", False))
        return cf
