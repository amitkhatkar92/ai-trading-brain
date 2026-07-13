"""iios/investment/company/financials/financial_period.py
Defines the FinancialPeriod — the atomic time unit for all statements.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PeriodType(str, Enum):
    QUARTERLY   = "quarterly"
    HALF_YEARLY = "half_yearly"
    ANNUAL      = "annual"
    TTM         = "ttm"    # trailing twelve months


class AccountingStandard(str, Enum):
    IFRS   = "ifrs"
    US_GAAP = "us_gaap"
    IND_AS  = "ind_as"
    GAAP_IN = "gaap_in"   # old Indian GAAP
    OTHER   = "other"


class ReportingCurrency(str, Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    OTHER = "OTHER"


# Standard unit multipliers (all stored values represent this currency unit)
class FinancialUnit(str, Enum):
    UNITS   = "units"       # raw rupees/dollars
    LAKHS   = "lakhs"       # 1L = 100,000
    CRORES  = "crores"      # 1Cr = 10,000,000
    MILLIONS = "millions"   # 1M = 1,000,000
    BILLIONS = "billions"   # 1B = 1,000,000,000


@dataclass(frozen=True)
class FinancialPeriod:
    """Immutable identifier for a financial reporting period."""
    period_type:          PeriodType
    fiscal_year:          int              # e.g., 2024
    quarter:              Optional[int]    # 1–4; None for annual/TTM
    start_date:           str              # ISO "YYYY-MM-DD"
    end_date:             str              # ISO "YYYY-MM-DD"
    accounting_standard:  AccountingStandard = AccountingStandard.IND_AS

    @property
    def label(self) -> str:
        if self.period_type is PeriodType.QUARTERLY and self.quarter:
            return f"Q{self.quarter}FY{self.fiscal_year % 100:02d}"
        if self.period_type is PeriodType.HALF_YEARLY and self.quarter:
            half = "H1" if self.quarter <= 2 else "H2"
            return f"{half}FY{self.fiscal_year % 100:02d}"
        if self.period_type is PeriodType.TTM:
            return f"TTM-{self.end_date}"
        return f"FY{self.fiscal_year % 100:02d}"

    @staticmethod
    def annual(
        fiscal_year: int,
        start_date:  str,
        end_date:    str,
        standard:    AccountingStandard = AccountingStandard.IND_AS,
    ) -> "FinancialPeriod":
        return FinancialPeriod(PeriodType.ANNUAL, fiscal_year, None, start_date, end_date, standard)

    @staticmethod
    def quarterly(
        fiscal_year: int,
        quarter:     int,
        start_date:  str,
        end_date:    str,
        standard:    AccountingStandard = AccountingStandard.IND_AS,
    ) -> "FinancialPeriod":
        return FinancialPeriod(PeriodType.QUARTERLY, fiscal_year, quarter, start_date, end_date, standard)

    def to_dict(self) -> dict:
        return {
            "period_type":         self.period_type.value,
            "fiscal_year":         self.fiscal_year,
            "quarter":             self.quarter,
            "start_date":          self.start_date,
            "end_date":            self.end_date,
            "accounting_standard": self.accounting_standard.value,
            "label":               self.label,
        }
