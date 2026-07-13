"""iios/investment/company/valuation/valuation_gap.py
Compute the absolute fair value gap: fair_value - market_price.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValuationGap:
    """
    Absolute gap between estimated fair value and current market price.
    Positive gap = undervalued; negative gap = overvalued.
    """
    fair_value:         Optional[float] = None
    market_price:       Optional[float] = None
    gap_absolute:       Optional[float] = None   # FV - MP
    gap_pct:            Optional[float] = None   # (FV - MP) / MP * 100
    currency:           str             = "INR"
    explanation:        List[str]       = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fair_value":    round(self.fair_value, 2)   if self.fair_value   else None,
            "market_price":  round(self.market_price, 2) if self.market_price else None,
            "gap_absolute":  round(self.gap_absolute, 2) if self.gap_absolute is not None else None,
            "gap_pct":       round(self.gap_pct, 1)      if self.gap_pct      is not None else None,
            "currency":      self.currency,
            "explanation":   self.explanation,
        }


def compute_valuation_gap(
    fair_value:    Optional[float],
    market_price:  Optional[float],
    currency:      str = "INR",
) -> ValuationGap:
    gap = ValuationGap(
        fair_value   = fair_value,
        market_price = market_price,
        currency     = currency,
    )

    if fair_value is None or market_price is None or market_price <= 0:
        gap.explanation.append("Insufficient data to compute gap")
        return gap

    gap.gap_absolute = fair_value - market_price
    gap.gap_pct      = (fair_value - market_price) / market_price * 100.0

    if gap.gap_pct >= 20:
        gap.explanation.append(
            f"Fair value exceeds market price by {gap.gap_pct:.1f}% "
            f"({currency} {gap.gap_absolute:.2f}/share)"
        )
    elif gap.gap_pct <= -20:
        gap.explanation.append(
            f"Market price exceeds fair value by {abs(gap.gap_pct):.1f}% "
            f"({currency} {abs(gap.gap_absolute):.2f}/share)"
        )
    else:
        gap.explanation.append(
            f"Gap of {gap.gap_pct:.1f}% ({currency} {gap.gap_absolute:.2f}/share)"
        )

    return gap
