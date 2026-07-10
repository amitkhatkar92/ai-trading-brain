"""iios/investment/market/structure/pivot_detector.py
Pivot point detection from raw OHLCV bars.

A pivot high = bar whose high is strictly greater than N bars on each side.
A pivot low  = bar whose low  is strictly less    than N bars on each side.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from iios.investment.market.structure.models import Bar

logger = logging.getLogger(__name__)


def is_pivot_high(bars: List[Bar], idx: int, left: int, right: int) -> bool:
    """Return True if bars[idx].high is strictly greater than all neighbours."""
    if idx < left or idx + right >= len(bars):
        return False
    pivot_high = bars[idx].high
    for i in range(idx - left, idx):
        if bars[i].high >= pivot_high:
            return False
    for i in range(idx + 1, idx + right + 1):
        if bars[i].high >= pivot_high:
            return False
    return True


def is_pivot_low(bars: List[Bar], idx: int, left: int, right: int) -> bool:
    """Return True if bars[idx].low is strictly less than all neighbours."""
    if idx < left or idx + right >= len(bars):
        return False
    pivot_low = bars[idx].low
    for i in range(idx - left, idx):
        if bars[i].low <= pivot_low:
            return False
    for i in range(idx + 1, idx + right + 1):
        if bars[i].low <= pivot_low:
            return False
    return True


def detect_pivots(
    bars: List[Bar],
    left: int = 3,
    right: int = 3,
) -> Tuple[List[int], List[int]]:
    """Detect pivot highs and lows in a bar series.

    Returns
    -------
    (high_indices, low_indices)
        Lists of bar indices (0-based) where confirmed pivots occur.
        These indices are `right` bars old by the time they are confirmed.
    """
    if len(bars) < left + right + 1:
        logger.debug("Insufficient bars for pivot detection: %d", len(bars))
        return [], []

    high_indices: List[int] = []
    low_indices: List[int] = []

    # Only check bars that have enough right-side confirmation.
    # The last valid index to check is len(bars) - 1 - right.
    max_check = len(bars) - 1 - right

    for idx in range(left, max_check + 1):
        if is_pivot_high(bars, idx, left, right):
            high_indices.append(idx)
        if is_pivot_low(bars, idx, left, right):
            low_indices.append(idx)

    return high_indices, low_indices
