"""engine/market_simulator.py — Historical bar data access layer for simulations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BarEvent:
    """
    A single OHLCV bar for one symbol at one timestamp.

    Passed to the strategy's on_bar() callback.
    """
    timestamp:  float = 0.0        # unix epoch (seconds)
    symbol:     str   = ""
    open:       float = 0.0
    high:       float = 0.0
    low:        float = 0.0
    close:      float = 0.0
    volume:     float = 0.0
    interval:   str   = "1d"
    bar_index:  int   = 0          # 0-based index in this symbol's bar series
    is_last:    bool  = False      # True for the final bar in the series
    extra:      dict[str, Any] = field(default_factory=dict)

    @property
    def vwap(self) -> float:
        return (self.open + self.high + self.low + self.close) / 4.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "symbol":    self.symbol,
            "open":      self.open,
            "high":      self.high,
            "low":       self.low,
            "close":     self.close,
            "volume":    self.volume,
            "interval":  self.interval,
            "bar_index": self.bar_index,
            "is_last":   self.is_last,
        }


class MarketSimulator:
    """
    Provides ordered, multi-symbol bar access during simulation.

    Bars must be pre-loaded as a dict[symbol, list[BarEvent]] sorted
    by ascending timestamp before calling get_bars_at().
    """

    def __init__(self) -> None:
        self._data:  dict[str, list[BarEvent]] = {}
        self._index: dict[str, int]            = {}    # next unread index per symbol

    # ── Data loading ──────────────────────────────────────────────────────────

    def load(self, bars_data: dict[str, list[BarEvent]]) -> None:
        """Replace entire dataset. bars_data must be sorted by timestamp."""
        self._data  = {s: list(bars) for s, bars in bars_data.items()}
        self._index = {s: 0 for s in self._data}

    def symbols(self) -> list[str]:
        return list(self._data.keys())

    def bar_count(self, symbol: str) -> int:
        return len(self._data.get(symbol, []))

    def all_bars(self, symbol: str) -> list[BarEvent]:
        return list(self._data.get(symbol, []))

    # ── Sorted unified timeline ────────────────────────────────────────────────

    def sorted_timeline(self) -> list[tuple[float, str, BarEvent]]:
        """Return all (timestamp, symbol, bar) sorted by timestamp then symbol."""
        entries: list[tuple[float, str, BarEvent]] = []
        for symbol, bars in self._data.items():
            for bar in bars:
                entries.append((bar.timestamp, symbol, bar))
        entries.sort(key=lambda x: (x[0], x[1]))
        return entries

    # ── Corporate-action adjustment ───────────────────────────────────────────

    def apply_split_adjustment(self, symbol: str, ratio: float, before_ts: float) -> None:
        """Adjust all bars before before_ts by split ratio (price / ratio, volume * ratio)."""
        if symbol not in self._data:
            return
        for bar in self._data[symbol]:
            if bar.timestamp < before_ts:
                bar.open   /= ratio
                bar.high   /= ratio
                bar.low    /= ratio
                bar.close  /= ratio
                bar.volume *= ratio

    def apply_dividend_adjustment(self, symbol: str, dividend: float, ex_ts: float) -> None:
        """Apply dividend adjustment factor to all bars before ex_ts."""
        if symbol not in self._data:
            return
        ref_bar = next(
            (b for b in self._data[symbol] if b.timestamp >= ex_ts),
            None,
        )
        if ref_bar is None or ref_bar.close <= 0:
            return
        factor = (ref_bar.close - dividend) / ref_bar.close
        for bar in self._data[symbol]:
            if bar.timestamp < ex_ts:
                bar.open  *= factor
                bar.high  *= factor
                bar.low   *= factor
                bar.close *= factor

    # ── Statistics ────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "symbols":    list(self._data.keys()),
            "total_bars": sum(len(b) for b in self._data.values()),
        }
