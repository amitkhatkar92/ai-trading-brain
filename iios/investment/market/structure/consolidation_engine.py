"""iios/investment/market/structure/consolidation_engine.py
Main consolidation detection combining range and compression detectors.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from iios.investment.market.structure.compression_detector import CompressionDetector
from iios.investment.market.structure.models import Bar, ConsolidationState, ConsolidationType
from iios.investment.market.structure.range_detector import RangeDetector

logger = logging.getLogger(__name__)


class ConsolidationEngine:
    """Combine range and compression detection into a single consolidation state."""

    def __init__(
        self,
        range_detector: RangeDetector,
        compression_detector: CompressionDetector,
    ) -> None:
        self._range = range_detector
        self._compression = compression_detector
        self._active: Optional[ConsolidationState] = None

    def update(self, bars: List[Bar]) -> Optional[ConsolidationState]:
        """Detect or update consolidation state."""
        if not bars:
            return self._active

        # If already in active consolidation, try to extend it
        if self._active is not None and self._active.active:
            updated = self._range.update_range(self._active, bars[-1])
            if updated is not None:
                self._active = updated
                return self._active
            else:
                # Range broken — deactivate
                from dataclasses import replace
                self._active = replace(self._active, active=False)

        # Try to detect a new consolidation
        range_state = self._range.detect(bars)
        comp_state = self._compression.detect(bars)
        self._active = self._resolve_type(range_state, comp_state)
        return self._active

    def get_active(self) -> Optional[ConsolidationState]:
        return self._active if (self._active and self._active.active) else None

    def is_consolidating(self) -> bool:
        return self._active is not None and self._active.active

    def bars_in_consolidation(self) -> int:
        if self._active is None or not self._active.active:
            return 0
        return self._active.bar_count

    def _resolve_type(
        self,
        range_state: Optional[ConsolidationState],
        comp_state: Optional[ConsolidationState],
    ) -> Optional[ConsolidationState]:
        """Choose the most specific consolidation type detected."""
        if comp_state is not None:
            # Compression is more specific than a plain range
            return comp_state
        if range_state is not None:
            return range_state
        return None
