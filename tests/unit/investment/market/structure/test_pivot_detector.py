"""tests/unit/investment/market/structure/test_pivot_detector.py"""
from __future__ import annotations

from typing import List

import pytest

from iios.investment.market.structure.models import Bar
from iios.investment.market.structure.pivot_detector import (
    detect_pivots,
    is_pivot_high,
    is_pivot_low,
)
from tests.unit.investment.market.structure.conftest import (
    make_downtrend_bars,
    make_range_bars,
    make_uptrend_bars,
)


def _make_bars(prices: List[float]) -> List[Bar]:
    return [
        Bar(
            index=i,
            timestamp=float(i),
            open=p,
            high=p + 0.5,
            low=p - 0.5,
            close=p,
            volume=1000.0,
        )
        for i, p in enumerate(prices)
    ]


def _make_bars_hl(highs: List[float], lows: List[float]) -> List[Bar]:
    assert len(highs) == len(lows)
    return [
        Bar(
            index=i,
            timestamp=float(i),
            open=(highs[i] + lows[i]) / 2,
            high=highs[i],
            low=lows[i],
            close=(highs[i] + lows[i]) / 2,
            volume=1000.0,
        )
        for i in range(len(highs))
    ]


class TestIsPivotHigh:
    def test_clear_peak(self):
        # Index 3 is highest
        bars = _make_bars([1, 2, 3, 5, 3, 2, 1])
        assert is_pivot_high(bars, 3, 2, 2) is True

    def test_not_peak_left(self):
        bars = _make_bars([1, 6, 3, 5, 3, 2, 1])
        assert is_pivot_high(bars, 3, 2, 2) is False

    def test_not_peak_right(self):
        bars = _make_bars([1, 2, 3, 5, 3, 6, 1])
        assert is_pivot_high(bars, 3, 2, 2) is False

    def test_equal_not_strict(self):
        bars = _make_bars([1, 2, 5, 5, 3, 2, 1])
        # index 2 has neighbour at same value (index 3)
        assert is_pivot_high(bars, 2, 1, 1) is False

    def test_insufficient_left(self):
        bars = _make_bars([5, 3, 2, 1])
        assert is_pivot_high(bars, 0, 2, 1) is False

    def test_insufficient_right(self):
        bars = _make_bars([1, 2, 3, 5])
        assert is_pivot_high(bars, 3, 1, 2) is False


class TestIsPivotLow:
    def test_clear_trough(self):
        bars = _make_bars([5, 4, 3, 1, 3, 4, 5])
        # Adjust lows: use make_bars_hl for more precise control
        bars2 = _make_bars_hl(
            highs=[5.5, 4.5, 3.5, 1.5, 3.5, 4.5, 5.5],
            lows=[4.5, 3.5, 2.5, 0.5, 2.5, 3.5, 4.5],
        )
        assert is_pivot_low(bars2, 3, 2, 2) is True

    def test_not_trough_right(self):
        # idx=3, left=2 checks [1,2], right=2 checks [4,5]
        # bars[4].low = -0.5 is LOWER than bars[3].low = 0.5 → not a pivot
        bars = _make_bars_hl(
            highs=[5.5, 4.5, 3.5, 1.5, 0.0, 4.5, 5.5],
            lows=[4.5, 3.5, 2.5, 0.5, -0.5, 3.5, 4.5],
        )
        assert is_pivot_low(bars, 3, 2, 2) is False


class TestDetectPivots:
    def test_uptrend_has_pivots(self):
        # Zigzag uptrend: clear local peaks and troughs
        # Pattern: rise to peak, pull back, rise higher, pull back, rise higher
        # idx:  0    1    2    3    4    5    6    7    8    9    10   11   12
        highs = [100, 105, 108, 105, 101, 110, 115, 112, 108, 116, 120, 117, 113]
        lows  = [ 97, 102, 105, 102,  98, 107, 112, 109, 105, 113, 117, 114, 110]
        bars = _make_bars_hl(highs, lows)
        highs_idx, lows_idx = detect_pivots(bars, left=2, right=2)
        # idx=2 (h=108) is strictly > idx 0,1,3,4 → pivot high
        # idx=4 (l=98) is strictly < idx 2,3,5,6 → pivot low
        assert len(highs_idx) > 0 or len(lows_idx) > 0

    def test_downtrend_has_pivots(self):
        # Zigzag downtrend: explicit V-shapes going lower.
        # idx:   0    1    2    3    4    5    6    7    8    9    10   11   12   13   14
        # highs: decline, bounce (peak at 8), decline further
        highs = [120, 117, 114, 111, 108, 100, 103, 107, 110, 107, 103,  99,  97,  95,  93]
        lows  = [117, 114, 111, 108, 105,  97, 100, 104, 107, 104, 100,  96,  94,  92,  90]
        bars = _make_bars_hl(highs, lows)
        highs_idx, lows_idx = detect_pivots(bars, left=2, right=2)
        # idx=8 (h=110): bars[6]=103, bars[7]=107 < 110; bars[9]=107, bars[10]=103 < 110 → PH
        # idx=5 (l=97):  bars[3]=108, bars[4]=105 > 97;  bars[6]=100, bars[7]=104 > 97 → PL
        assert len(highs_idx) > 0 or len(lows_idx) > 0

    def test_insufficient_bars_returns_empty(self):
        bars = make_uptrend_bars(n=3)
        highs, lows = detect_pivots(bars, left=3, right=3)
        assert highs == []
        assert lows == []

    def test_pivot_indices_in_range(self):
        bars = make_range_bars(n=30)
        highs, lows = detect_pivots(bars, left=2, right=2)
        n = len(bars)
        for idx in highs:
            assert 0 <= idx < n
        for idx in lows:
            assert 0 <= idx < n

    def test_no_duplicate_indices(self):
        bars = make_uptrend_bars(n=50)
        highs, lows = detect_pivots(bars, left=3, right=3)
        assert len(highs) == len(set(highs))
        assert len(lows) == len(set(lows))

    def test_right_side_confirmation_lag(self):
        """Confirmed pivot indices are at least 'right' bars before the last bar."""
        bars = make_uptrend_bars(n=20)
        right = 3
        highs, lows = detect_pivots(bars, left=2, right=right)
        last_valid = len(bars) - 1 - right
        for idx in highs:
            assert idx <= last_valid
        for idx in lows:
            assert idx <= last_valid
