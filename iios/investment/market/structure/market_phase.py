"""iios/investment/market/structure/market_phase.py
Detect Wyckoff-inspired market phases from pure price action.
"""
from __future__ import annotations

import logging
from typing import List

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.structure.models import (
    Bar,
    StructurePhase,
    SwingSequence,
    SwingType,
    TrendState,
)

logger = logging.getLogger(__name__)


class MarketPhaseDetector:
    """Detect Wyckoff-inspired structural phases without any indicators."""

    def __init__(self, lookback: int = 20) -> None:
        self._lookback = lookback

    def detect(
        self,
        bars: List[Bar],
        trend: TrendState,
        sequence: SwingSequence,
    ) -> StructurePhase:
        """Determine the current structural phase."""
        if len(bars) < self._lookback:
            return StructurePhase.ACCUMULATION

        recent = bars[-self._lookback:]

        # Trending phases take priority over range phases
        if trend.direction == TrendDirection.UP and trend.confirmed:
            if self._is_expanding(recent):
                return StructurePhase.EXPANSION
            return StructurePhase.MARKUP

        if trend.direction == TrendDirection.DOWN and trend.confirmed:
            if self._is_expanding(recent):
                return StructurePhase.EXPANSION
            return StructurePhase.MARKDOWN

        # Range/compression detection
        if self._is_compressing(recent):
            return StructurePhase.COMPRESSION

        if self._is_ranging(recent):
            if self._detect_accumulation(recent, trend, sequence):
                return StructurePhase.ACCUMULATION
            if self._detect_distribution(recent, trend, sequence):
                return StructurePhase.DISTRIBUTION
            return StructurePhase.CONTRACTION

        return StructurePhase.ACCUMULATION

    # ── Sub-detectors ─────────────────────────────────────────────────────

    def _is_ranging(self, bars: List[Bar]) -> bool:
        """Price has stayed within a bounded range for lookback bars."""
        if len(bars) < 5:
            return False
        high = max(b.high for b in bars)
        low = min(b.low for b in bars)
        mid = (high + low) / 2.0
        if mid == 0:
            return False
        width_pct = (high - low) / mid
        return width_pct < 0.06

    def _is_expanding(self, bars: List[Bar]) -> bool:
        """Bar ranges are systematically increasing."""
        if len(bars) < 6:
            return False
        n = len(bars)
        first_half_avg = sum(b.range for b in bars[: n // 2]) / (n // 2)
        second_half_avg = sum(b.range for b in bars[n // 2 :]) / (n - n // 2)
        return second_half_avg > first_half_avg * 1.3

    def _is_compressing(self, bars: List[Bar]) -> bool:
        """Bar ranges are systematically decreasing."""
        if len(bars) < 6:
            return False
        n = len(bars)
        first_half_avg = sum(b.range for b in bars[: n // 2]) / (n // 2)
        second_half_avg = sum(b.range for b in bars[n // 2 :]) / (n - n // 2)
        return second_half_avg < first_half_avg * 0.6

    def _detect_accumulation(
        self,
        bars: List[Bar],
        trend: TrendState,
        sequence: SwingSequence,
    ) -> bool:
        """Ranging after a downtrend with volume on bounces (higher lows on bounces)."""
        if trend.direction != TrendDirection.DOWN and trend.direction != TrendDirection.SIDEWAYS:
            return False

        lows = sequence.lows
        if len(lows) < 2:
            return False

        # Higher lows within the range = accumulation characteristic
        recent_lows = lows[:3]  # newest first
        if len(recent_lows) >= 2:
            hl_pattern = all(
                recent_lows[i].price > recent_lows[i + 1].price
                for i in range(len(recent_lows) - 1)
            )
            if hl_pattern:
                return True

        # Volume proxy: bounces (bullish bars) have higher avg volume than dips
        bullish_vol = [b.volume for b in bars if b.is_bullish and b.volume > 0]
        bearish_vol = [b.volume for b in bars if b.is_bearish and b.volume > 0]
        if bullish_vol and bearish_vol:
            avg_bull = sum(bullish_vol) / len(bullish_vol)
            avg_bear = sum(bearish_vol) / len(bearish_vol)
            return avg_bull > avg_bear

        return False

    def _detect_distribution(
        self,
        bars: List[Bar],
        trend: TrendState,
        sequence: SwingSequence,
    ) -> bool:
        """Ranging after an uptrend with volume on dips (lower highs pattern)."""
        if trend.direction != TrendDirection.UP and trend.direction != TrendDirection.SIDEWAYS:
            return False

        highs = sequence.highs
        if len(highs) < 2:
            return False

        # Lower highs within the range = distribution characteristic
        recent_highs = highs[:3]  # newest first
        if len(recent_highs) >= 2:
            lh_pattern = all(
                recent_highs[i].price < recent_highs[i + 1].price
                for i in range(len(recent_highs) - 1)
            )
            if lh_pattern:
                return True

        # Volume proxy: dips (bearish bars) have higher avg volume than bounces
        bullish_vol = [b.volume for b in bars if b.is_bullish and b.volume > 0]
        bearish_vol = [b.volume for b in bars if b.is_bearish and b.volume > 0]
        if bullish_vol and bearish_vol:
            avg_bull = sum(bullish_vol) / len(bullish_vol)
            avg_bear = sum(bearish_vol) / len(bearish_vol)
            return avg_bear > avg_bull

        return False
