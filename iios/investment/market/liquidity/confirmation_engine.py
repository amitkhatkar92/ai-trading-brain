"""iios/investment/market/liquidity/confirmation_engine.py
Determines whether volume confirms a price move.
"""
from __future__ import annotations

import logging

from iios.investment.market.liquidity.models import VolumeBar

logger = logging.getLogger(__name__)


class ConfirmationEngine:
    """
    Determines whether volume confirms a price move.
    Stateless — pure computation.
    """

    def is_price_confirmed_by_volume(
        self,
        vbar: VolumeBar,
        relative_volume: float,
        min_relative_volume: float = 1.1,
    ) -> bool:
        """
        Returns True if:
        - Up bar: relative_volume >= min_relative_volume AND close_position > 0.5
        - Down bar: relative_volume >= min_relative_volume AND close_position < 0.5
        """
        if relative_volume < min_relative_volume:
            return False
        if vbar.is_up:
            return vbar.close_position > 0.5
        else:
            return vbar.close_position < 0.5

    def is_breakout_confirmed(
        self,
        vbar: VolumeBar,
        relative_volume: float,
        breakout_direction: str,
        min_relative_volume: float = 1.5,
    ) -> bool:
        """Breakout requires higher relative volume threshold."""
        if relative_volume < min_relative_volume:
            return False
        if breakout_direction == "up":
            return vbar.is_up and vbar.close_position > 0.5
        elif breakout_direction == "down":
            return (not vbar.is_up) and vbar.close_position < 0.5
        return False

    def confirmation_strength(self, vbar: VolumeBar, relative_volume: float) -> float:
        """0-1 strength of volume confirmation."""
        return min(1.0, relative_volume / 2.0) * (vbar.body_pct * 0.5 + 0.5)
