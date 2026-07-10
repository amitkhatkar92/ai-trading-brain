"""iios/investment/market/structure/swing_detector.py
Detect major and minor swing points from OHLCV bars.
Classifies each swing relative to the previous swing of the same type
(HH / HL / LH / LL / EH / EL).
"""
from __future__ import annotations

import logging
from typing import List, Optional, Set

from iios.investment.market.structure.models import (
    Bar,
    SwingPoint,
    SwingRelation,
    SwingStrength,
    SwingType,
)
from iios.investment.market.structure.pivot_detector import (
    detect_pivots,
    is_pivot_high,
    is_pivot_low,
)

logger = logging.getLogger(__name__)


class SwingDetector:
    """Detect and classify swing points (pivots) from a bar series."""

    def __init__(
        self,
        major_left: int = 5,
        major_right: int = 5,
        minor_left: int = 2,
        minor_right: int = 2,
        equality_threshold_pct: float = 0.1,
    ) -> None:
        self._major_left = major_left
        self._major_right = major_right
        self._minor_left = minor_left
        self._minor_right = minor_right
        self._eq_pct = equality_threshold_pct / 100.0  # store as fraction
        self._seen_indices: Set[int] = set()

    # ── Public API ────────────────────────────────────────────────────────

    def detect_all(self, bars: List[Bar]) -> List[SwingPoint]:
        """Detect all swing points in the full bar series, sorted by index."""
        if not bars:
            return []

        swings: List[SwingPoint] = []

        # Detect major swings
        major_highs, major_lows = detect_pivots(bars, self._major_left, self._major_right)
        major_high_set = set(major_highs)
        major_low_set = set(major_lows)

        # Detect minor swings (those NOT already classified as major)
        minor_highs, minor_lows = detect_pivots(bars, self._minor_left, self._minor_right)

        # Build swing points
        for idx in major_highs:
            swings.append(self._make_swing(bars, idx, SwingType.HIGH, SwingStrength.MAJOR))
        for idx in major_lows:
            swings.append(self._make_swing(bars, idx, SwingType.LOW, SwingStrength.MAJOR))
        for idx in minor_highs:
            if idx not in major_high_set:
                swings.append(self._make_swing(bars, idx, SwingType.HIGH, SwingStrength.MINOR))
        for idx in minor_lows:
            if idx not in major_low_set:
                swings.append(self._make_swing(bars, idx, SwingType.LOW, SwingStrength.MINOR))

        swings.sort(key=lambda s: s.index)
        self._classify_relations(swings)
        return swings

    def process_bar(self, bars: List[Bar]) -> List[SwingPoint]:
        """Process the latest bar update and return any newly confirmed swings.

        Swings are confirmed only once enough right-side bars exist.
        """
        if not bars:
            return []

        new_swings: List[SwingPoint] = []
        last_idx = len(bars) - 1

        # The earliest candidate that could be newly confirmed is:
        #   last_idx - minor_right (for minor) or last_idx - major_right (for major)
        minor_candidate = last_idx - self._minor_right
        major_candidate = last_idx - self._major_right

        for candidate in {minor_candidate, major_candidate}:
            if candidate < 0 or candidate in self._seen_indices:
                continue
            # Check major
            if candidate >= self._major_left:
                if is_pivot_high(bars, candidate, self._major_left, self._major_right):
                    sp = self._make_swing(bars, candidate, SwingType.HIGH, SwingStrength.MAJOR)
                    new_swings.append(sp)
                    self._seen_indices.add(candidate)
                    continue
                if is_pivot_low(bars, candidate, self._major_left, self._major_right):
                    sp = self._make_swing(bars, candidate, SwingType.LOW, SwingStrength.MAJOR)
                    new_swings.append(sp)
                    self._seen_indices.add(candidate)
                    continue
            # Check minor
            if candidate >= self._minor_left:
                if is_pivot_high(bars, candidate, self._minor_left, self._minor_right):
                    sp = self._make_swing(bars, candidate, SwingType.HIGH, SwingStrength.MINOR)
                    new_swings.append(sp)
                    self._seen_indices.add(candidate)
                elif is_pivot_low(bars, candidate, self._minor_left, self._minor_right):
                    sp = self._make_swing(bars, candidate, SwingType.LOW, SwingStrength.MINOR)
                    new_swings.append(sp)
                    self._seen_indices.add(candidate)

        return new_swings

    # ── Private helpers ───────────────────────────────────────────────────

    def _make_swing(
        self,
        bars: List[Bar],
        idx: int,
        swing_type: SwingType,
        strength: SwingStrength,
    ) -> SwingPoint:
        bar = bars[idx]
        price = bar.high if swing_type == SwingType.HIGH else bar.low
        left = self._major_left if strength == SwingStrength.MAJOR else self._minor_left
        right = self._major_right if strength == SwingStrength.MAJOR else self._minor_right
        return SwingPoint(
            index=idx,
            timestamp=bar.timestamp,
            price=price,
            swing_type=swing_type,
            strength=strength,
            volume=bar.volume,
            bar_range=bar.range,
            left_bars=left,
            right_bars=right,
            relation=None,
        )

    def _classify_relations(self, swings: List[SwingPoint]) -> None:
        """Mutate swings in-place, setting the relation field."""
        last_high: Optional[SwingPoint] = None
        last_low: Optional[SwingPoint] = None
        for sw in swings:
            if sw.swing_type == SwingType.HIGH:
                sw.relation = self._classify_relation(sw, last_high)
                last_high = sw
            else:
                sw.relation = self._classify_relation(sw, last_low)
                last_low = sw

    def _classify_relation(
        self,
        point: SwingPoint,
        previous_of_same_type: Optional[SwingPoint],
    ) -> Optional[SwingRelation]:
        if previous_of_same_type is None:
            return None
        prev_price = previous_of_same_type.price
        curr_price = point.price
        threshold = prev_price * self._eq_pct

        if abs(curr_price - prev_price) <= threshold:
            return SwingRelation.EQUAL_HIGH if point.swing_type == SwingType.HIGH else SwingRelation.EQUAL_LOW

        if point.swing_type == SwingType.HIGH:
            return SwingRelation.HIGHER_HIGH if curr_price > prev_price else SwingRelation.LOWER_HIGH
        else:
            return SwingRelation.HIGHER_LOW if curr_price > prev_price else SwingRelation.LOWER_LOW
