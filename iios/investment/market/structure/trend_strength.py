"""iios/investment/market/structure/trend_strength.py
Measure trend strength from impulse vs correction ratios. Pure price action.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from iios.investment.market.market_constants import MarketStrength, TrendDirection
from iios.investment.market.structure.models import SwingPoint, SwingSequence, SwingType

logger = logging.getLogger(__name__)


class TrendStrengthAnalyzer:
    """Measure trend strength from price action structure."""

    def measure(
        self,
        sequence: SwingSequence,
        direction: TrendDirection,
    ) -> Tuple[MarketStrength, float]:
        """Return (strength_enum, score 0-100)."""
        if direction == TrendDirection.SIDEWAYS:
            return MarketStrength.NEUTRAL, 50.0

        impulses, corrections = self._extract_legs(sequence, direction)
        if not impulses:
            return MarketStrength.NEUTRAL, 50.0

        avg_impulse = sum(impulses) / len(impulses)
        avg_correction = sum(corrections) / len(corrections) if corrections else 0.0
        total = avg_impulse + avg_correction
        if total == 0:
            return MarketStrength.NEUTRAL, 50.0

        ratio = avg_impulse / total  # 0-1; higher = stronger trend
        score = ratio * 100.0

        if score >= 80:
            strength = MarketStrength.VERY_STRONG
        elif score >= 65:
            strength = MarketStrength.STRONG
        elif score >= 50:
            strength = MarketStrength.MODERATE
        elif score >= 35:
            strength = MarketStrength.WEAK
        else:
            strength = MarketStrength.VERY_WEAK

        return strength, score

    def is_accelerating(
        self,
        sequence: SwingSequence,
        direction: TrendDirection,
    ) -> bool:
        """True if each successive impulse is larger than the previous."""
        impulses, _ = self._extract_legs(sequence, direction)
        if len(impulses) < 2:
            return False
        # Check last 3 impulses (or all available)
        recent = impulses[-3:] if len(impulses) >= 3 else impulses
        return all(recent[i] > recent[i - 1] for i in range(1, len(recent)))

    def is_exhausting(
        self,
        sequence: SwingSequence,
        direction: TrendDirection,
    ) -> bool:
        """True if impulses getting shorter AND corrections getting deeper."""
        impulses, corrections = self._extract_legs(sequence, direction)
        if len(impulses) < 2 or len(corrections) < 2:
            return False

        impulse_shrinking = all(
            impulses[i] < impulses[i - 1] for i in range(1, min(3, len(impulses)))
        )
        correction_deepening = all(
            corrections[i] > corrections[i - 1]
            for i in range(1, min(3, len(corrections)))
        )
        return impulse_shrinking and correction_deepening

    def correction_depth(
        self,
        sequence: SwingSequence,
        direction: TrendDirection,
    ) -> float:
        """Average correction depth as fraction of preceding impulse (0-1)."""
        impulses, corrections = self._extract_legs(sequence, direction)
        if not impulses or not corrections:
            return 0.0
        pairs = min(len(impulses), len(corrections))
        ratios = []
        for i in range(pairs):
            if impulses[i] > 0:
                ratios.append(corrections[i] / impulses[i])
        return sum(ratios) / len(ratios) if ratios else 0.0

    # ── Helpers ───────────────────────────────────────────────────────────

    def _extract_legs(
        self,
        sequence: SwingSequence,
        direction: TrendDirection,
    ) -> Tuple[List[float], List[float]]:
        """Extract impulse and correction magnitudes from the swing sequence."""
        # Combine and sort chronologically
        all_swings: List[SwingPoint] = sorted(
            sequence.highs + sequence.lows, key=lambda s: s.index
        )

        if len(all_swings) < 2:
            return [], []

        impulses: List[float] = []
        corrections: List[float] = []

        for i in range(1, len(all_swings)):
            prev = all_swings[i - 1]
            curr = all_swings[i]
            move = abs(curr.price - prev.price)

            if direction == TrendDirection.UP:
                # Impulse = move up (low → high), correction = move down (high → low)
                if (
                    prev.swing_type == SwingType.LOW
                    and curr.swing_type == SwingType.HIGH
                    and curr.price > prev.price
                ):
                    impulses.append(move)
                elif (
                    prev.swing_type == SwingType.HIGH
                    and curr.swing_type == SwingType.LOW
                ):
                    corrections.append(move)
            else:  # DOWN
                # Impulse = move down (high → low), correction = move up (low → high)
                if (
                    prev.swing_type == SwingType.HIGH
                    and curr.swing_type == SwingType.LOW
                    and curr.price < prev.price
                ):
                    impulses.append(move)
                elif (
                    prev.swing_type == SwingType.LOW
                    and curr.swing_type == SwingType.HIGH
                ):
                    corrections.append(move)

        return impulses, corrections
