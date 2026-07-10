"""market/market_simulator.py — Multi-symbol price bar store for paper trading."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_exceptions import MarketSimulatorError


@dataclass
class PriceBar:
    """
    OHLCV bar for a single symbol and time period.

    All prices are in the instrument's native currency.
    """
    timestamp: float
    symbol:    str
    open:      float
    high:      float
    low:       float
    close:     float
    volume:    float
    interval:  str            = "1d"
    bar_index: int            = 0
    is_last:   bool           = False
    extra:     dict[str, Any] = field(default_factory=dict)

    @property
    def vwap(self) -> float:
        """Estimated VWAP = (O + H + L + C) / 4."""
        return (self.open + self.high + self.low + self.close) / 4.0

    @property
    def typical_price(self) -> float:
        """Typical price = (H + L + C) / 3."""
        return (self.high + self.low + self.close) / 3.0

    @property
    def mid(self) -> float:
        """Mid = (H + L) / 2."""
        return (self.high + self.low) / 2.0


class MarketSimulator:
    """
    Stores pre-loaded price bars and serves them to the simulation loop.

    Supports corporate-action adjustments (splits, dividends) applied
    retroactively to all historical bars for a symbol.
    """

    def __init__(self) -> None:
        self._bars: dict[str, list[PriceBar]] = {}

    # ── Loading ───────────────────────────────────────────────────────────────

    def load(self, bars_data: dict[str, list[PriceBar]]) -> None:
        """Load bar data keyed by symbol.  Replaces any existing data."""
        self._bars = {sym: list(bars) for sym, bars in bars_data.items()}
        for sym, bars in self._bars.items():
            for idx, bar in enumerate(bars):
                bar.bar_index = idx
            if bars:
                bars[-1].is_last = True

    # ── Queries ───────────────────────────────────────────────────────────────

    def symbols(self) -> list[str]:
        return list(self._bars.keys())

    def bar_count(self, symbol: str) -> int:
        self._assert_symbol(symbol)
        return len(self._bars[symbol])

    def get_bar(self, symbol: str, index: int) -> PriceBar:
        self._assert_symbol(symbol)
        bars = self._bars[symbol]
        if index < 0 or index >= len(bars):
            raise MarketSimulatorError(
                f"Bar index {index} out of range for symbol {symbol!r} (0–{len(bars) - 1})"
            )
        return bars[index]

    def all_bars(self, symbol: str) -> list[PriceBar]:
        self._assert_symbol(symbol)
        return list(self._bars[symbol])

    def sorted_timeline(self) -> list[tuple[float, str, PriceBar]]:
        """Return all (timestamp, symbol, bar) triples sorted by (timestamp, symbol)."""
        events: list[tuple[float, str, PriceBar]] = []
        for sym, bars in self._bars.items():
            for bar in bars:
                events.append((bar.timestamp, sym, bar))
        events.sort(key=lambda x: (x[0], x[1]))
        return events

    def latest_prices(self) -> dict[str, float]:
        """Return the close price of the last bar for each symbol."""
        return {
            sym: bars[-1].close
            for sym, bars in self._bars.items()
            if bars
        }

    # ── Corporate actions ─────────────────────────────────────────────────────

    def apply_split(
        self,
        symbol:    str,
        ratio:     float,
        before_ts: float,
    ) -> None:
        """Adjust all bars before *before_ts* for a forward split of *ratio*.

        E.g. ratio=2 means a 2-for-1 split: prices halved, volumes doubled.
        """
        self._assert_symbol(symbol)
        if ratio <= 0.0:
            raise MarketSimulatorError("Split ratio must be positive")
        for bar in self._bars[symbol]:
            if bar.timestamp < before_ts:
                bar.open   /= ratio
                bar.high   /= ratio
                bar.low    /= ratio
                bar.close  /= ratio
                bar.volume *= ratio

    def apply_dividend(
        self,
        symbol:   str,
        dividend: float,
        ex_ts:    float,
    ) -> None:
        """Adjust all bars before *ex_ts* for a cash dividend.

        Reduces historical prices by the dividend / last_close_before_ex factor.
        """
        self._assert_symbol(symbol)
        # Find the close just before ex date
        last_close: Optional[float] = None
        for bar in self._bars[symbol]:
            if bar.timestamp < ex_ts:
                last_close = bar.close
        if last_close is None or last_close <= 0.0:
            return
        factor = (last_close - dividend) / last_close
        for bar in self._bars[symbol]:
            if bar.timestamp < ex_ts:
                bar.open  *= factor
                bar.high  *= factor
                bar.low   *= factor
                bar.close *= factor

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        total = sum(len(b) for b in self._bars.values())
        return {
            "symbols":    self.symbols(),
            "total_bars": total,
            "per_symbol": {sym: len(bars) for sym, bars in self._bars.items()},
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _assert_symbol(self, symbol: str) -> None:
        if symbol not in self._bars:
            raise MarketSimulatorError(f"Symbol {symbol!r} not loaded")
