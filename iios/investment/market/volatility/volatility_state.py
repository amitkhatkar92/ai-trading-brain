"""iios/investment/market/volatility/volatility_state.py
Stateful tracker that produces VolatilityState from a stream of
annualised-volatility observations.
"""
from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Deque, List

from iios.investment.market.volatility.models import VolatilityState
from iios.investment.market.volatility.volatility_statistics import VolatilityStatistics

if TYPE_CHECKING:
    from iios.investment.market.structure.models import Bar


class VolatilityStateTracker:
    """
    Maintains rolling vol windows and produces VolatilityState snapshots.

    Parameters
    ----------
    short_window:   number of bars for the short-term vol average
    medium_window:  number of bars for the medium-term vol average (also the
                    initialisation threshold)
    long_window:    number of bars for the long-term vol average
    """

    def __init__(
        self,
        short_window: int = 5,
        medium_window: int = 20,
        long_window: int = 50,
    ) -> None:
        self._short_w  = short_window
        self._medium_w = medium_window
        self._long_w   = long_window

        self._stats = VolatilityStatistics(window=long_window)
        self._range_buf: Deque[float] = deque(maxlen=medium_window)
        self._bars_processed = 0

    # ── Public API ─────────────────────────────────────────────────────────

    def update(self, realized_vol: float, bar: "Bar") -> VolatilityState:
        """Ingest one vol estimate and the corresponding bar; return new state."""
        self._stats.update(realized_vol)
        bar_range = bar.high - bar.low
        self._range_buf.append(bar_range)
        self._bars_processed += 1

        short_vol, medium_vol, long_vol = self._stats.multi_window_means(
            self._short_w, self._medium_w, self._long_w
        )

        relative_vol = (
            short_vol / medium_vol if medium_vol > 1e-10 else 1.0
        )
        normalized = self._stats.normalized(realized_vol)
        persistence = self._stats.lag1_autocorrelation()

        vol_of_vol = self._stats.std
        stability = 1.0 / (1.0 + vol_of_vol / max(medium_vol, 1e-8))
        stability = max(0.0, min(1.0, stability))

        avg_range = (
            sum(self._range_buf) / len(self._range_buf)
            if self._range_buf
            else max(bar_range, 1e-8)
        )
        range_ratio = bar_range / avg_range if avg_range > 1e-10 else 1.0

        is_initialized = self._stats.count >= self._medium_w

        return VolatilityState(
            realized_volatility=realized_vol,
            short_term_vol=short_vol,
            medium_term_vol=medium_vol,
            long_term_vol=long_vol,
            relative_volatility=relative_vol,
            normalized_volatility=normalized,
            volatility_persistence=persistence,
            volatility_stability=stability,
            vol_of_vol=vol_of_vol,
            bar_range_ratio=range_ratio,
            bars_processed=self._bars_processed,
            is_initialized=is_initialized,
        )

    @property
    def bars_processed(self) -> int:
        return self._bars_processed

    @property
    def statistics(self) -> VolatilityStatistics:
        return self._stats
