"""iios/investment/company/financials/financial_statement.py
Composite statement: BalanceSheet + IncomeStatement + CashFlowStatement
for one reporting period, with version tracking.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.financial_period import FinancialPeriod
from iios.investment.company.financials.balance_sheet import BalanceSheet
from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.cash_flow_statement import CashFlowStatement


@dataclass
class StatementVersion:
    """Immutable record of one version of a filed statement."""
    version:       int           # monotonically increasing
    filed_at:      float         # Unix timestamp
    source:        str           # e.g. "bse", "nse", "mca", "provider"
    is_restated:   bool
    notes:         str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version":     self.version,
            "filed_at":    self.filed_at,
            "source":      self.source,
            "is_restated": self.is_restated,
            "notes":       self.notes,
        }


@dataclass
class FinancialStatement:
    """
    Composite financial statement for one period.
    All three component statements share the same FinancialPeriod.
    """
    period:          FinancialPeriod
    balance_sheet:   Optional[BalanceSheet]       = None
    income_statement: Optional[IncomeStatement]   = None
    cash_flow:       Optional[CashFlowStatement]  = None

    # Versioning
    current_version: int   = 1
    source:          str   = "unknown"
    created_at:      float = field(default_factory=time.time)
    updated_at:      float = field(default_factory=time.time)
    versions:        list  = field(default_factory=list)  # List[StatementVersion]

    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return (
            self.balance_sheet is not None
            and self.income_statement is not None
            and self.cash_flow is not None
        )

    @property
    def has_balance_sheet(self) -> bool:
        return self.balance_sheet is not None

    @property
    def has_income_statement(self) -> bool:
        return self.income_statement is not None

    @property
    def has_cash_flow(self) -> bool:
        return self.cash_flow is not None

    def completeness_pct(self) -> float:
        scores = []
        if self.balance_sheet is not None:
            scores.append(self.balance_sheet.completeness_pct())
        if self.income_statement is not None:
            scores.append(self.income_statement.completeness_pct())
        if self.cash_flow is not None:
            scores.append(self.cash_flow.completeness_pct())
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def stamp_version(self, source: str, restated: bool = False, notes: str = "") -> None:
        v = StatementVersion(
            version=self.current_version,
            filed_at=time.time(),
            source=source,
            is_restated=restated,
            notes=notes,
        )
        self.versions.append(v)
        self.current_version += 1
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period":           self.period.to_dict(),
            "balance_sheet":    self.balance_sheet.to_dict() if self.balance_sheet else None,
            "income_statement": self.income_statement.to_dict() if self.income_statement else None,
            "cash_flow":        self.cash_flow.to_dict() if self.cash_flow else None,
            "current_version":  self.current_version,
            "source":           self.source,
            "created_at":       self.created_at,
            "updated_at":       self.updated_at,
            "is_complete":      self.is_complete,
            "completeness_pct": round(self.completeness_pct(), 1),
            "versions":         [v.to_dict() for v in self.versions],
        }
