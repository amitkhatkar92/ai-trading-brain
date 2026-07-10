"""execution/slippage_model.py — Simulated market slippage."""
from __future__ import annotations

from iios.integration.research.paper_trading.paper_trading_constants import (
    DEFAULT_SLIPPAGE_PCT,
    OrderSide,
)
from iios.integration.research.paper_trading.market.market_simulator import PriceBar


class SlippageModel:
    """
    Computes a deterministic slippage cost for a fill.

    *slippage_pct* is applied as a fraction of the fill price in the
    direction that disadvantages the trader (buys get slipped up, sells down).

    *impact_factor* adds a volume-proportional component
    ``impact_factor * (quantity / bar.volume) * price``.
    """

    def __init__(
        self,
        slippage_pct:  float = DEFAULT_SLIPPAGE_PCT,
        impact_factor: float = 0.0,
    ) -> None:
        self._pct    = max(0.0, slippage_pct)
        self._impact = max(0.0, impact_factor)

    def compute(
        self,
        price:    float,
        quantity: float,
        side:     OrderSide,
        bar:      PriceBar,
    ) -> float:
        """
        Return the total slippage cost (always non-negative).

        For buys, slippage pushes the fill price up.
        For sells, it pushes it down.
        Both represent a cost to the trader.
        """
        base = self._pct * price
        if self._impact > 0.0 and bar.volume > 0.0:
            base += self._impact * (quantity / bar.volume) * price
        return base * quantity

    @property
    def slippage_pct(self) -> float:
        return self._pct

    @property
    def impact_factor(self) -> float:
        return self._impact
