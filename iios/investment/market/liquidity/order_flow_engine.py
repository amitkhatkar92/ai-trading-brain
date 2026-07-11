"""iios/investment/market/liquidity/order_flow_engine.py
Stateful order flow engine.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from iios.investment.market.liquidity.models import VolumeBar, OrderFlowSnapshot
from iios.investment.market.liquidity.order_flow_snapshot import OrderFlowSnapshotBuilder
from iios.investment.market.liquidity.imbalance_detector import ImbalanceDetector
from iios.investment.market.liquidity.flow_statistics import FlowStatistics, FlowStats

logger = logging.getLogger(__name__)


class OrderFlowEngine:
    """
    Stateful order flow engine.
    Extensible for Level-2 data integration without changing the interface.
    """

    def __init__(
        self,
        window: int = 20,
        snapshot_builder: Optional[OrderFlowSnapshotBuilder] = None,
        imbalance_detector: Optional[ImbalanceDetector] = None,
        flow_statistics: Optional[FlowStatistics] = None,
    ) -> None:
        self._window = window
        self._snapshot_builder = snapshot_builder or OrderFlowSnapshotBuilder()
        self._imbalance_detector = imbalance_detector or ImbalanceDetector(window=window)
        self._flow_statistics = flow_statistics or FlowStatistics()
        self._cumulative_delta: float = 0.0
        self._current: Optional[OrderFlowSnapshot] = None

    def update(self, vbar: VolumeBar, relative_volume: float) -> OrderFlowSnapshot:
        snap = self._snapshot_builder.build(vbar, self._cumulative_delta, relative_volume)
        self._cumulative_delta = snap.cumulative_delta
        self._imbalance_detector.update(snap)
        self._flow_statistics.record(snap)
        self._current = snap
        return snap

    def initialize(self, vbars: List[VolumeBar]) -> OrderFlowSnapshot:
        last: Optional[OrderFlowSnapshot] = None
        for vbar in vbars:
            last = self.update(vbar, vbar.relative_volume)
        if last is None:
            raise ValueError("initialize() requires at least one bar")
        return last

    def current(self) -> Optional[OrderFlowSnapshot]:
        return self._current

    def cumulative_delta(self) -> float:
        return self._cumulative_delta

    def imbalance(self) -> float:
        return self._imbalance_detector.current_imbalance()

    def has_buy_pressure(self) -> bool:
        return self._imbalance_detector.has_persistent_buy_pressure()

    def has_sell_pressure(self) -> bool:
        return self._imbalance_detector.has_persistent_sell_pressure()

    def stats(self) -> FlowStats:
        return self._flow_statistics.stats()

    def reset_cumulative_delta(self) -> None:
        """Reset cumulative delta (e.g., at session start)."""
        self._cumulative_delta = 0.0

    # L2 extension point — override in subclass
    def connect_l2_feed(self, feed: Any) -> None:
        """Future: connect a Level-2 market depth feed. No-op in base implementation."""
        logger.info("L2 feed integration not yet connected. Using OHLCV heuristics.")
