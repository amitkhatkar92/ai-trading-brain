"""iios/investment/market/liquidity/imbalance_detector.py
Detects buy/sell imbalances from rolling order flow snapshots.
"""
from __future__ import annotations

import logging
from collections import deque

from iios.investment.market.liquidity.models import OrderFlowSnapshot

logger = logging.getLogger(__name__)


class ImbalanceDetector:
    """
    Detects buy/sell imbalances from rolling order flow snapshots.
    """

    def __init__(self, window: int = 10) -> None:
        self._window = window
        self._snapshots: deque[OrderFlowSnapshot] = deque(maxlen=window)

    def update(self, snapshot: OrderFlowSnapshot) -> None:
        self._snapshots.append(snapshot)

    def current_imbalance(self) -> float:
        """Weighted avg net_imbalance of recent N snapshots. Range [-1, 1]."""
        snaps = list(self._snapshots)
        if not snaps:
            return 0.0
        return sum(s.net_imbalance for s in snaps) / len(snaps)

    def has_persistent_buy_pressure(self, threshold: float = 0.3) -> bool:
        """last 3+ bars with net_imbalance >= threshold."""
        snaps = list(self._snapshots)[-3:]
        if len(snaps) < 3:
            return False
        return all(s.net_imbalance >= threshold for s in snaps)

    def has_persistent_sell_pressure(self, threshold: float = 0.3) -> bool:
        """last 3+ bars with net_imbalance <= -threshold."""
        snaps = list(self._snapshots)[-3:]
        if len(snaps) < 3:
            return False
        return all(s.net_imbalance <= -threshold for s in snaps)

    def imbalance_strength(self) -> float:
        """abs(current_imbalance), range [0, 1]."""
        return abs(self.current_imbalance())
