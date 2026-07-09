"""iios/investment/company/financials/balance_sheet_analyzer.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import FinancialHealth


@dataclass
class BalanceSheetAnalysis:
    total_assets:    float         = 0.0
    total_debt:      float         = 0.0
    equity:          float         = 0.0
    debt_to_equity:  float         = 0.0
    current_ratio:   float         = 0.0
    net_cash:        float         = 0.0
    goodwill_pct:    float         = 0.0   # goodwill as % of total assets
    leverage_health: FinancialHealth = FinancialHealth.UNKNOWN
    health_score:    float         = 50.0   # 0–100
    metadata:        dict[str, Any] = field(default_factory=dict)

    @property
    def is_net_cash(self) -> bool:
        return self.net_cash > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_assets":    self.total_assets,
            "total_debt":      self.total_debt,
            "equity":          self.equity,
            "debt_to_equity":  self.debt_to_equity,
            "current_ratio":   self.current_ratio,
            "net_cash":        self.net_cash,
            "goodwill_pct":    self.goodwill_pct,
            "is_net_cash":     self.is_net_cash,
            "leverage_health": self.leverage_health.value,
            "health_score":    self.health_score,
            "metadata":        self.metadata,
        }


class BalanceSheetAnalyzer:
    """
    Derives solvency and leverage metrics from a balance sheet dict.

    Expected keys (all optional, default 0):
      total_assets, total_debt, equity, current_assets, current_liabilities,
      cash, goodwill
    """

    def analyze(self, data: dict[str, Any]) -> BalanceSheetAnalysis:
        if not data:
            return BalanceSheetAnalysis()

        assets     = float(data.get("total_assets", 0) or 0)
        debt       = float(data.get("total_debt", 0) or 0)
        equity     = float(data.get("equity", 0) or 0)
        curr_a     = float(data.get("current_assets", 0) or 0)
        curr_l     = float(data.get("current_liabilities", 0) or 0)
        cash       = float(data.get("cash", 0) or 0)
        goodwill   = float(data.get("goodwill", 0) or 0)

        de_ratio   = debt    / equity if equity   > 0 else 0.0
        curr_ratio = curr_a  / curr_l if curr_l   > 0 else (float("inf") if curr_a > 0 else 0.0)
        net_cash   = cash    - debt
        gw_pct     = goodwill / assets if assets  > 0 else 0.0

        leverage_health = self._classify_leverage(de_ratio, curr_ratio)
        health_score    = self._health_score(de_ratio, curr_ratio, net_cash)

        return BalanceSheetAnalysis(
            total_assets    = assets,
            total_debt      = debt,
            equity          = equity,
            debt_to_equity  = round(de_ratio, 4),
            current_ratio   = round(min(curr_ratio, 999.0), 4),
            net_cash        = round(net_cash, 2),
            goodwill_pct    = round(gw_pct, 4),
            leverage_health = leverage_health,
            health_score    = round(health_score, 2),
            metadata        = {"n_items": len(data)},
        )

    @staticmethod
    def _classify_leverage(de: float, cr: float) -> FinancialHealth:
        if de <= 0.30 and cr >= 2.0:
            return FinancialHealth.VERY_STRONG
        elif de <= 0.50 and cr >= 1.5:
            return FinancialHealth.STRONG
        elif de <= 1.00 and cr >= 1.2:
            return FinancialHealth.MODERATE
        elif de <= 2.00 and cr >= 1.0:
            return FinancialHealth.WEAK
        elif de <= 3.00:
            return FinancialHealth.VERY_WEAK
        else:
            return FinancialHealth.DISTRESSED

    @staticmethod
    def _health_score(de: float, cr: float, net_cash: float) -> float:
        # D/E component (50%)
        if de <= 0.30:
            de_score = 100.0
        elif de <= 0.60:
            de_score = 80.0
        elif de <= 1.00:
            de_score = 60.0
        elif de <= 2.00:
            de_score = 40.0
        elif de <= 3.00:
            de_score = 20.0
        else:
            de_score = 0.0

        # Current ratio component (30%)
        if cr == float("inf") or cr >= 3.0:
            cr_score = 100.0
        elif cr >= 2.0:
            cr_score = 80.0
        elif cr >= 1.5:
            cr_score = 60.0
        elif cr >= 1.0:
            cr_score = 40.0
        else:
            cr_score = 10.0

        # Net cash component (20%)
        nc_score = 80.0 if net_cash > 0 else 40.0

        return de_score * 0.50 + cr_score * 0.30 + nc_score * 0.20
