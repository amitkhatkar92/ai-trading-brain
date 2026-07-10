"""iios/investment/market/structure/trend_classifier.py
Classify trend direction from swing sequences using pure swing-based logic.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.structure.models import (
    Bar,
    SwingPoint,
    SwingRelation,
    SwingSequence,
    SwingType,
    TrendTransition,
)

logger = logging.getLogger(__name__)


class TrendClassifier:
    """Classify trend direction and detect structure transitions."""

    def classify(self, sequence: SwingSequence) -> Tuple[TrendDirection, int]:
        """Return (direction, leg_count).

        Uptrend:   last 2 swing highs: SH2 > SH1 (HH), last 2 lows: SL2 > SL1 (HL)
        Downtrend: last 2 swing highs: SH2 < SH1 (LH), last 2 lows: SL2 < SL1 (LL)
        Sideways:  mixed or insufficient swings.
        leg_count = consecutive confirming swing pairs.
        """
        highs = sequence.highs  # newest first
        lows = sequence.lows    # newest first

        if len(highs) < 2 or len(lows) < 2:
            return TrendDirection.SIDEWAYS, 0

        # Check the most recent pair
        hh = highs[0].price > highs[1].price  # higher high
        hl = lows[0].price > lows[1].price    # higher low
        lh = highs[0].price < highs[1].price  # lower high
        ll = lows[0].price < lows[1].price    # lower low

        if hh and hl:
            direction = TrendDirection.UP
            leg_count = self._count_consecutive_uptrend(highs, lows)
        elif lh and ll:
            direction = TrendDirection.DOWN
            leg_count = self._count_consecutive_downtrend(highs, lows)
        else:
            direction = TrendDirection.SIDEWAYS
            leg_count = 0

        return direction, leg_count

    def detect_break_of_structure(
        self,
        sequence: SwingSequence,
        current_price: float,
    ) -> Optional[TrendTransition]:
        """Break of structure: price closes beyond the most recent significant swing."""
        highs = sequence.highs
        lows = sequence.lows

        if not highs or not lows:
            return None

        direction, _ = self.classify(sequence)

        if direction == TrendDirection.UP:
            # BOS bearish: price closes below most recent swing low
            last_low = lows[0]
            if current_price < last_low.price:
                return TrendTransition(
                    from_direction=TrendDirection.UP,
                    to_direction=TrendDirection.DOWN,
                    trigger_index=last_low.index,
                    trigger_price=last_low.price,
                    trigger_swing=last_low,
                    transition_type="break_of_structure",
                    confirmed=False,
                )

        elif direction == TrendDirection.DOWN:
            # BOS bullish: price closes above most recent swing high
            last_high = highs[0]
            if current_price > last_high.price:
                return TrendTransition(
                    from_direction=TrendDirection.DOWN,
                    to_direction=TrendDirection.UP,
                    trigger_index=last_high.index,
                    trigger_price=last_high.price,
                    trigger_swing=last_high,
                    transition_type="break_of_structure",
                    confirmed=False,
                )

        return None

    def detect_change_of_character(
        self,
        sequence: SwingSequence,
        current_bar: Bar,
    ) -> Optional[TrendTransition]:
        """Change of character: first opposite swing after extended trend (3+ legs)."""
        direction, leg_count = self.classify(sequence)
        if leg_count < 3:
            return None

        highs = sequence.highs
        lows = sequence.lows

        if direction == TrendDirection.UP and len(highs) >= 2:
            # CHOCH: most recent high is lower than previous high
            if highs[0].price < highs[1].price:
                return TrendTransition(
                    from_direction=TrendDirection.UP,
                    to_direction=TrendDirection.DOWN,
                    trigger_index=highs[0].index,
                    trigger_price=highs[0].price,
                    trigger_swing=highs[0],
                    transition_type="change_of_character",
                    confirmed=False,
                )

        elif direction == TrendDirection.DOWN and len(lows) >= 2:
            # CHOCH: most recent low is higher than previous low
            if lows[0].price > lows[1].price:
                return TrendTransition(
                    from_direction=TrendDirection.DOWN,
                    to_direction=TrendDirection.UP,
                    trigger_index=lows[0].index,
                    trigger_price=lows[0].price,
                    trigger_swing=lows[0],
                    transition_type="change_of_character",
                    confirmed=False,
                )

        return None

    # ── Helpers ───────────────────────────────────────────────────────────

    def _count_consecutive_uptrend(
        self, highs: List[SwingPoint], lows: List[SwingPoint]
    ) -> int:
        """Count consecutive HH+HL pairs (newest-first lists)."""
        count = 0
        # Reverse to chronological order for counting
        h = list(reversed(highs))
        l = list(reversed(lows))
        for i in range(1, min(len(h), len(l))):
            if h[i].price > h[i - 1].price and l[i].price > l[i - 1].price:
                count += 1
            else:
                break
        return max(count, 1)

    def _count_consecutive_downtrend(
        self, highs: List[SwingPoint], lows: List[SwingPoint]
    ) -> int:
        """Count consecutive LH+LL pairs (newest-first lists)."""
        count = 0
        h = list(reversed(highs))
        l = list(reversed(lows))
        for i in range(1, min(len(h), len(l))):
            if h[i].price < h[i - 1].price and l[i].price < l[i - 1].price:
                count += 1
            else:
                break
        return max(count, 1)
