"""iios/investment/market/liquidity/order_flow_snapshot.py
Builds OrderFlowSnapshot from VolumeBar + running cumulative delta.
"""
from __future__ import annotations

import logging

from iios.investment.market.liquidity.models import VolumeBar, OrderFlowSnapshot

logger = logging.getLogger(__name__)


class OrderFlowSnapshotBuilder:
    """
    Builds OrderFlowSnapshot from VolumeBar + running cumulative delta.
    Stateless — inject cumulative_delta from caller.
    """

    def build(
        self,
        vbar: VolumeBar,
        cumulative_delta: float,
        relative_volume: float,
    ) -> OrderFlowSnapshot:
        estimated_buy_volume = vbar.volume * vbar.close_position
        estimated_sell_volume = vbar.volume * (1.0 - vbar.close_position)
        estimated_delta = estimated_buy_volume - estimated_sell_volume
        new_cumulative = cumulative_delta + estimated_delta

        safe_volume = max(vbar.volume, 1e-9)
        buy_imbalance = estimated_buy_volume / safe_volume
        sell_imbalance = 1.0 - buy_imbalance
        net_imbalance = buy_imbalance - sell_imbalance  # -1 to 1

        aggressive_buying = buy_imbalance > 0.65 and relative_volume >= 1.2
        aggressive_selling = buy_imbalance < 0.35 and relative_volume >= 1.2

        return OrderFlowSnapshot(
            estimated_buy_volume=estimated_buy_volume,
            estimated_sell_volume=estimated_sell_volume,
            estimated_delta=estimated_delta,
            cumulative_delta=new_cumulative,
            buy_imbalance=buy_imbalance,
            sell_imbalance=sell_imbalance,
            net_imbalance=net_imbalance,
            aggressive_buying=aggressive_buying,
            aggressive_selling=aggressive_selling,
        )
