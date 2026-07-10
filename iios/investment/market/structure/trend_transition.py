"""iios/investment/market/structure/trend_transition.py
Detect and manage trend transitions (Break of Structure / Change of Character).
"""
from __future__ import annotations

import logging
from typing import Optional

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.structure.models import Bar, SwingSequence, TrendTransition
from iios.investment.market.structure.trend_classifier import TrendClassifier

logger = logging.getLogger(__name__)


class TrendTransitionDetector:
    """Monitor the swing sequence for BOS and CHOCH events."""

    def __init__(self, min_legs_for_trend: int = 2) -> None:
        self._min_legs = min_legs_for_trend
        self._pending_transition: Optional[TrendTransition] = None
        self._last_confirmed_direction: TrendDirection = TrendDirection.SIDEWAYS
        self._last_transition: Optional[TrendTransition] = None
        self._classifier = TrendClassifier()

    def update(
        self,
        sequence: SwingSequence,
        current_bar: Bar,
    ) -> Optional[TrendTransition]:
        """Check for Break of Structure or Change of Character.

        Returns a newly detected transition or None.
        """
        direction, leg_count = self._classifier.classify(sequence)

        # ── 1. Try Break of Structure first ──────────────────────────────
        bos = self._classifier.detect_break_of_structure(
            sequence, current_bar.close
        )
        if bos is not None:
            bos.confirmed = True
            self._pending_transition = None
            self._last_confirmed_direction = bos.to_direction
            self._last_transition = bos
            return bos

        # ── 2. Change of Character (requires extended trend) ─────────────
        if leg_count >= self._min_legs:
            choch = self._classifier.detect_change_of_character(sequence, current_bar)
            if choch is not None and choch != self._pending_transition:
                self._pending_transition = choch
                self._last_transition = choch
                return choch

        # ── 3. Confirm pending CHOCH if now supported by new swings ──────
        if self._pending_transition is not None and not self._pending_transition.confirmed:
            new_dir, _ = self._classifier.classify(sequence)
            if new_dir == self._pending_transition.to_direction:
                self._pending_transition.confirmed = True
                self._last_confirmed_direction = self._pending_transition.to_direction
                return self._pending_transition

        return None

    def get_pending(self) -> Optional[TrendTransition]:
        return self._pending_transition

    def get_last_transition(self) -> Optional[TrendTransition]:
        return self._last_transition
