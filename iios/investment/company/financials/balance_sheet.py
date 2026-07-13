"""iios/investment/company/financials/balance_sheet.py
Raw balance sheet data model — no analysis, no scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.financial_period import FinancialPeriod, FinancialUnit


@dataclass
class BalanceSheet:
    """Raw balance sheet for one financial period."""
    period:   FinancialPeriod
    currency: str          = "INR"
    unit:     FinancialUnit = FinancialUnit.CRORES
    restated: bool         = False

    # ── Assets ────────────────────────────────────────────────────────────────
    cash_and_equivalents:       Optional[float] = None
    short_term_investments:     Optional[float] = None
    accounts_receivable:        Optional[float] = None
    inventory:                  Optional[float] = None
    other_current_assets:       Optional[float] = None
    total_current_assets:       Optional[float] = None

    property_plant_equipment:   Optional[float] = None
    goodwill:                   Optional[float] = None
    intangible_assets:          Optional[float] = None
    long_term_investments:      Optional[float] = None
    other_non_current_assets:   Optional[float] = None
    total_non_current_assets:   Optional[float] = None

    total_assets:               Optional[float] = None

    # ── Liabilities ───────────────────────────────────────────────────────────
    accounts_payable:               Optional[float] = None
    short_term_debt:                Optional[float] = None
    current_portion_long_term_debt: Optional[float] = None
    other_current_liabilities:      Optional[float] = None
    total_current_liabilities:      Optional[float] = None

    long_term_debt:                 Optional[float] = None
    deferred_tax_liabilities:       Optional[float] = None
    other_non_current_liabilities:  Optional[float] = None
    total_non_current_liabilities:  Optional[float] = None

    total_liabilities:              Optional[float] = None

    # ── Equity ────────────────────────────────────────────────────────────────
    common_stock:                   Optional[float] = None
    retained_earnings:              Optional[float] = None
    additional_paid_in_capital:     Optional[float] = None
    other_equity:                   Optional[float] = None
    total_equity:                   Optional[float] = None
    minority_interest:              Optional[float] = None
    total_liabilities_and_equity:   Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── computed helpers ──────────────────────────────────────────────────────

    @property
    def total_debt(self) -> Optional[float]:
        sd  = self.short_term_debt or 0.0
        cp  = self.current_portion_long_term_debt or 0.0
        ltd = self.long_term_debt or 0.0
        if sd == 0.0 and cp == 0.0 and ltd == 0.0:
            return None
        return sd + cp + ltd

    @property
    def net_cash(self) -> Optional[float]:
        cash = self.cash_and_equivalents
        debt = self.total_debt
        if cash is None and debt is None:
            return None
        return (cash or 0.0) - (debt or 0.0)

    @property
    def working_capital(self) -> Optional[float]:
        ca  = self.total_current_assets
        cl  = self.total_current_liabilities
        if ca is None or cl is None:
            return None
        return ca - cl

    def completeness_pct(self) -> float:
        """Fraction of key fields populated (0-100)."""
        key_fields = [
            self.cash_and_equivalents, self.accounts_receivable, self.inventory,
            self.total_current_assets, self.property_plant_equipment,
            self.total_assets, self.accounts_payable, self.short_term_debt,
            self.long_term_debt, self.total_current_liabilities,
            self.total_liabilities, self.total_equity,
        ]
        filled = sum(1 for f in key_fields if f is not None)
        return 100.0 * filled / len(key_fields)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period":   self.period.to_dict(),
            "currency": self.currency,
            "unit":     self.unit.value,
            "restated": self.restated,
            # Assets
            "cash_and_equivalents":       self.cash_and_equivalents,
            "short_term_investments":     self.short_term_investments,
            "accounts_receivable":        self.accounts_receivable,
            "inventory":                  self.inventory,
            "total_current_assets":       self.total_current_assets,
            "property_plant_equipment":   self.property_plant_equipment,
            "goodwill":                   self.goodwill,
            "intangible_assets":          self.intangible_assets,
            "total_non_current_assets":   self.total_non_current_assets,
            "total_assets":               self.total_assets,
            # Liabilities
            "accounts_payable":           self.accounts_payable,
            "short_term_debt":            self.short_term_debt,
            "long_term_debt":             self.long_term_debt,
            "total_current_liabilities":  self.total_current_liabilities,
            "total_liabilities":          self.total_liabilities,
            # Equity
            "total_equity":               self.total_equity,
            "retained_earnings":          self.retained_earnings,
            "total_liabilities_and_equity": self.total_liabilities_and_equity,
            # Computed
            "total_debt":    self.total_debt,
            "net_cash":      self.net_cash,
            "working_capital": self.working_capital,
            "completeness_pct": round(self.completeness_pct(), 1),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any], period: FinancialPeriod) -> "BalanceSheet":
        bs = BalanceSheet(period=period)
        for field_name in (
            "cash_and_equivalents", "short_term_investments", "accounts_receivable",
            "inventory", "other_current_assets", "total_current_assets",
            "property_plant_equipment", "goodwill", "intangible_assets",
            "long_term_investments", "other_non_current_assets", "total_non_current_assets",
            "total_assets", "accounts_payable", "short_term_debt",
            "current_portion_long_term_debt", "other_current_liabilities",
            "total_current_liabilities", "long_term_debt", "deferred_tax_liabilities",
            "other_non_current_liabilities", "total_non_current_liabilities",
            "total_liabilities", "common_stock", "retained_earnings",
            "additional_paid_in_capital", "other_equity", "total_equity",
            "minority_interest", "total_liabilities_and_equity",
        ):
            val = data.get(field_name)
            if val is not None:
                try:
                    setattr(bs, field_name, float(val))
                except (TypeError, ValueError):
                    pass
        bs.currency = str(data.get("currency", "INR"))
        bs.restated  = bool(data.get("restated", False))
        return bs
