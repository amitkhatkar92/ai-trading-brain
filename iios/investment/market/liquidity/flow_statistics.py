"""iios/investment/market/liquidity/flow_statistics.py
Accumulates order flow statistics over engine lifetime.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from iios.investment.market.liquidity.models import OrderFlowSnapshot

logger = logging.getLogger(__name__)


@dataclass
class FlowStats:
    total_bars: int
    avg_buy_imbalance: float
    avg_sell_imbalance: float
    avg_delta: float
    cumulative_delta: float
    buy_dominant_bars: int      # bars where buy_imbalance > 0.60
    sell_dominant_bars: int
    aggressive_buy_events: int
    aggressive_sell_events: int


class FlowStatistics:
    """Accumulates order flow statistics over engine lifetime."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._total_bars: int = 0
        self._sum_buy_imbalance: float = 0.0
        self._sum_sell_imbalance: float = 0.0
        self._sum_delta: float = 0.0
        self._last_cumulative_delta: float = 0.0
        self._buy_dominant_bars: int = 0
        self._sell_dominant_bars: int = 0
        self._aggressive_buy_events: int = 0
        self._aggressive_sell_events: int = 0

    def record(self, snapshot: OrderFlowSnapshot) -> None:
        self._total_bars += 1
        self._sum_buy_imbalance += snapshot.buy_imbalance
        self._sum_sell_imbalance += snapshot.sell_imbalance
        self._sum_delta += snapshot.estimated_delta
        self._last_cumulative_delta = snapshot.cumulative_delta
        if snapshot.buy_imbalance > 0.60:
            self._buy_dominant_bars += 1
        if snapshot.sell_imbalance > 0.60:
            self._sell_dominant_bars += 1
        if snapshot.aggressive_buying:
            self._aggressive_buy_events += 1
        if snapshot.aggressive_selling:
            self._aggressive_sell_events += 1

    def stats(self) -> FlowStats:
        n = max(self._total_bars, 1)
        return FlowStats(
            total_bars=self._total_bars,
            avg_buy_imbalance=self._sum_buy_imbalance / n,
            avg_sell_imbalance=self._sum_sell_imbalance / n,
            avg_delta=self._sum_delta / n,
            cumulative_delta=self._last_cumulative_delta,
            buy_dominant_bars=self._buy_dominant_bars,
            sell_dominant_bars=self._sell_dominant_bars,
            aggressive_buy_events=self._aggressive_buy_events,
            aggressive_sell_events=self._aggressive_sell_events,
        )
