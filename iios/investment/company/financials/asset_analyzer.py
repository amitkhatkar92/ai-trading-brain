"""iios/investment/company/financials/asset_analyzer.py
Analyzes asset composition and structure from a BalanceSheet.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.company.financials.balance_sheet import BalanceSheet


@dataclass
class AssetMetrics:
    # Asset structure (% of total assets)
    current_asset_ratio:      Optional[float] = None   # %
    non_current_asset_ratio:  Optional[float] = None   # %
    cash_ratio_to_assets:     Optional[float] = None   # %
    inventory_ratio:          Optional[float] = None   # %
    receivables_ratio:        Optional[float] = None   # %
    ppe_ratio:                Optional[float] = None   # %
    goodwill_ratio:           Optional[float] = None   # %
    intangibles_ratio:        Optional[float] = None   # %

    # Absolute values (mirrors bs fields for convenience)
    total_assets:             Optional[float] = None
    total_current_assets:     Optional[float] = None
    cash_and_equivalents:     Optional[float] = None
    inventory:                Optional[float] = None
    accounts_receivable:      Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_asset_ratio":     self.current_asset_ratio,
            "non_current_asset_ratio": self.non_current_asset_ratio,
            "cash_ratio_to_assets":    self.cash_ratio_to_assets,
            "inventory_ratio":         self.inventory_ratio,
            "receivables_ratio":       self.receivables_ratio,
            "ppe_ratio":               self.ppe_ratio,
            "goodwill_ratio":          self.goodwill_ratio,
            "intangibles_ratio":       self.intangibles_ratio,
            "total_assets":            self.total_assets,
            "total_current_assets":    self.total_current_assets,
            "cash_and_equivalents":    self.cash_and_equivalents,
            "inventory":               self.inventory,
            "accounts_receivable":     self.accounts_receivable,
        }


def _pct(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return 100.0 * numerator / denominator


class AssetAnalyzer:
    """Extracts asset structure metrics from a BalanceSheet."""

    def analyze(self, bs: BalanceSheet) -> AssetMetrics:
        ta = bs.total_assets
        m  = AssetMetrics(
            total_assets=ta,
            total_current_assets=bs.total_current_assets,
            cash_and_equivalents=bs.cash_and_equivalents,
            inventory=bs.inventory,
            accounts_receivable=bs.accounts_receivable,
        )

        m.current_asset_ratio     = _pct(bs.total_current_assets, ta)
        m.non_current_asset_ratio = _pct(bs.total_non_current_assets, ta)
        m.cash_ratio_to_assets    = _pct(bs.cash_and_equivalents, ta)
        m.inventory_ratio         = _pct(bs.inventory, ta)
        m.receivables_ratio       = _pct(bs.accounts_receivable, ta)
        m.ppe_ratio               = _pct(bs.property_plant_equipment, ta)
        m.goodwill_ratio          = _pct(bs.goodwill, ta)
        m.intangibles_ratio       = _pct(bs.intangible_assets, ta)

        return m
