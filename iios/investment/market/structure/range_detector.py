"""iios/investment/market/structure/range_detector.py
Detect trading ranges and rectangles from bar series.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from iios.investment.market.structure.models import Bar, ConsolidationState, ConsolidationType

logger = logging.getLogger(__name__)


class RangeDetector:
    """Detect trading ranges and rectangle patterns from OHLCV bars."""

    def __init__(
        self,
        min_bars: int = 5,
        max_width_pct: float = 0.06,
        touch_threshold: int = 2,
    ) -> None:
        self._min_bars = min_bars
        self._max_width_pct = max_width_pct
        self._touch_threshold = touch_threshold

    def detect(self, bars: List[Bar]) -> Optional[ConsolidationState]:
        """Return ConsolidationState if bars form a range, else None."""
        if len(bars) < self._min_bars:
            return None

        recent = bars[-max(self._min_bars, len(bars)) :]
        high = max(b.high for b in recent)
        low = min(b.low for b in recent)
        mid = (high + low) / 2.0
        if mid == 0:
            return None

        width_pct = (high - low) / mid
        if width_pct > self._max_width_pct:
            return None

        # Check top and bottom are both touched multiple times
        tolerance = (high - low) * 0.15
        top_touches = self._count_touches(recent, high, tolerance)
        bot_touches = self._count_touches(recent, low, tolerance)

        if top_touches < self._touch_threshold and bot_touches < self._touch_threshold:
            return None

        avg_range = sum(b.range for b in recent) / len(recent)
        initial_range = recent[0].range if recent else avg_range
        tightest = min(b.range for b in recent)
        vol_trend = self._volume_trend(recent)

        ctype = (
            ConsolidationType.RECTANGLE
            if top_touches >= self._touch_threshold and bot_touches >= self._touch_threshold
            else ConsolidationType.RANGE
        )

        return ConsolidationState(
            consolidation_type=ctype,
            start_index=recent[0].index,
            high_bound=high,
            low_bound=low,
            bar_count=len(recent),
            avg_range=avg_range,
            initial_range=initial_range,
            tightest_range=tightest,
            volume_trend=vol_trend,
            active=True,
        )

    def update_range(
        self,
        state: ConsolidationState,
        new_bar: Bar,
    ) -> Optional[ConsolidationState]:
        """Extend existing range or return None if price broke out."""
        # Check if price has left the range
        margin = state.range_width * 0.15
        if new_bar.close > state.high_bound + margin:
            return None
        if new_bar.close < state.low_bound - margin:
            return None

        new_high = max(state.high_bound, new_bar.high)
        new_low = min(state.low_bound, new_bar.low)
        new_avg = (state.avg_range * state.bar_count + new_bar.range) / (state.bar_count + 1)
        new_tightest = min(state.tightest_range, new_bar.range)
        from dataclasses import replace
        return replace(
            state,
            high_bound=new_high,
            low_bound=new_low,
            bar_count=state.bar_count + 1,
            avg_range=new_avg,
            tightest_range=new_tightest,
        )

    def _count_touches(
        self, bars: List[Bar], level: float, tolerance: float
    ) -> int:
        """Count how many bars have high or low within tolerance of level."""
        count = 0
        for b in bars:
            if abs(b.high - level) <= tolerance or abs(b.low - level) <= tolerance:
                count += 1
        return count

    def _volume_trend(self, bars: List[Bar]) -> str:
        if len(bars) < 4:
            return "neutral"
        n = len(bars)
        first_avg = sum(b.volume for b in bars[: n // 2]) / (n // 2)
        second_avg = sum(b.volume for b in bars[n // 2 :]) / (n - n // 2)
        if second_avg > first_avg * 1.2:
            return "increasing"
        if second_avg < first_avg * 0.8:
            return "decreasing"
        return "neutral"
