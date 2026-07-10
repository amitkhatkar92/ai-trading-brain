"""execution/commission_model.py — Simulated transaction commissions."""
from __future__ import annotations

from iios.integration.research.paper_trading.paper_trading_constants import DEFAULT_COMMISSION_PCT


class CommissionModel:
    """
    Computes a deterministic commission for a fill.

    Commission = max(min_commission, min(max_commission, commission_pct * price * quantity))
    """

    def __init__(
        self,
        commission_pct:  float = DEFAULT_COMMISSION_PCT,
        min_commission:  float = 0.0,
        max_commission:  float = float("inf"),
    ) -> None:
        self._pct = max(0.0, commission_pct)
        self._min = max(0.0, min_commission)
        self._max = max_commission

    def compute(self, price: float, quantity: float) -> float:
        """Return commission amount for a fill of *quantity* at *price*."""
        raw = self._pct * price * quantity
        return min(self._max, max(self._min, raw))

    @property
    def commission_pct(self) -> float:
        return self._pct

    @property
    def min_commission(self) -> float:
        return self._min

    @property
    def max_commission(self) -> float:
        return self._max
