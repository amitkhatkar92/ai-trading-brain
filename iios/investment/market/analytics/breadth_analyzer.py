"""iios/investment/market/analytics/breadth_analyzer.py
Market breadth computation from advance/decline/unchanged counts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.market.market_constants import BreadthCondition


@dataclass
class BreadthAnalysis:
    condition:             BreadthCondition = BreadthCondition.MODERATE
    advance_decline_ratio: float            = 1.0
    pct_advancing:         float            = 0.0
    pct_declining:         float            = 0.0
    score:                 float            = 50.0   # 0–100
    metadata:              dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition":             self.condition.value,
            "advance_decline_ratio": self.advance_decline_ratio,
            "pct_advancing":         self.pct_advancing,
            "pct_declining":         self.pct_declining,
            "score":                 self.score,
            "metadata":              self.metadata,
        }


class BreadthAnalyzer:
    """
    Produces a BreadthAnalysis from advance/decline/unchanged counts.

    Score 0–100:  0 = all declining, 50 = neutral, 100 = all advancing.
    """

    def analyze(
        self,
        advances:  int,
        declines:  int,
        unchanged: int = 0,
    ) -> BreadthAnalysis:
        total = advances + declines + unchanged
        if total == 0:
            return BreadthAnalysis()

        pct_adv = advances / total
        pct_dec = declines / total
        adr     = (
            advances / declines if declines > 0
            else float(advances if advances > 0 else 1)
        )

        score = min(100.0, max(0.0, 50.0 + (pct_adv - pct_dec) * 100))

        if pct_adv >= 0.70:
            condition = BreadthCondition.VERY_BROAD
        elif pct_adv >= 0.55:
            condition = BreadthCondition.BROAD
        elif pct_adv >= 0.45:
            condition = BreadthCondition.MODERATE
        elif pct_adv >= 0.30:
            condition = BreadthCondition.NARROW
        else:
            condition = BreadthCondition.VERY_NARROW

        return BreadthAnalysis(
            condition             = condition,
            advance_decline_ratio = round(adr, 4),
            pct_advancing         = round(pct_adv, 4),
            pct_declining         = round(pct_dec, 4),
            score                 = round(score, 2),
            metadata              = {"total_issues": total},
        )
