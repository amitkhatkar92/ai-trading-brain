"""iios/investment/market/structure/breakout_classifier.py
Classify breakout types from zone breaks. Pure price action.
"""
from __future__ import annotations

import logging
from typing import Optional

from iios.investment.market.structure.models import (
    Bar,
    BreakoutType,
    ConsolidationState,
    SwingSequence,
    Zone,
    ZoneType,
)

logger = logging.getLogger(__name__)


class BreakoutClassifier:
    """Classify the type of breakout from a zone break event."""

    def classify(
        self,
        zone: Zone,
        bar: Bar,
        sequence: SwingSequence,
        avg_volume_20: float,
    ) -> BreakoutType:
        """Classify what kind of breakout this bar represents."""
        is_resistance = zone.zone_type in (ZoneType.RESISTANCE, ZoneType.SUPPLY, ZoneType.BROKEN_SUPPORT)
        is_support = zone.zone_type in (ZoneType.SUPPORT, ZoneType.DEMAND, ZoneType.BROKEN_RESISTANCE)

        vol_break = self._is_volume_breakout(bar, avg_volume_20)
        volatility_break = self._is_volatility_breakout(bar, zone.width if zone.width > 0 else 1.0)

        if volatility_break:
            return BreakoutType.VOLATILITY
        if vol_break:
            return BreakoutType.VOLUME

        if is_resistance and bar.close > zone.upper:
            return BreakoutType.BULLISH
        if is_support and bar.close < zone.lower:
            return BreakoutType.BEARISH

        # Check if price came back inside (failed breakout pattern inferred from context)
        if is_resistance and bar.close < zone.upper and bar.high > zone.upper:
            return BreakoutType.FAILED_BULLISH
        if is_support and bar.close > zone.lower and bar.low < zone.lower:
            return BreakoutType.FAILED_BEARISH

        return BreakoutType.RANGE

    def _is_volume_breakout(self, bar: Bar, avg_volume: float) -> bool:
        """Volume 1.5× above recent average."""
        if avg_volume <= 0:
            return False
        return bar.volume > avg_volume * 1.5

    def _is_range_breakout(
        self,
        bar: Bar,
        consolidation: Optional[ConsolidationState],
    ) -> bool:
        if consolidation is None:
            return False
        return bar.high > consolidation.high_bound or bar.low < consolidation.low_bound

    def _is_volatility_breakout(self, bar: Bar, avg_range: float) -> bool:
        """Bar range 2× recent average range."""
        if avg_range <= 0:
            return False
        return bar.range > avg_range * 2.0
