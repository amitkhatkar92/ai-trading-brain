"""market/market_clock.py — Simulated wall clock for paper trading sessions."""
from __future__ import annotations

from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_exceptions import MarketClockError


class MarketClock:
    """
    Deterministic simulation clock.

    Advances through time in fixed ``step_sec`` increments or by an explicit
    ``advance_to()`` call.  Raises ``StopIteration`` when ``advance()`` is
    called past the end timestamp.
    """

    def __init__(self) -> None:
        self._start:   Optional[float] = None
        self._end:     Optional[float] = None
        self._current: Optional[float] = None
        self._step:    float            = 86_400.0  # default: 1 day
        self._ticks:   int              = 0

    # ── Setup ─────────────────────────────────────────────────────────────────

    def initialize(
        self,
        start:    float,
        end:      float,
        step_sec: float = 86_400.0,
    ) -> None:
        if end <= start:
            raise MarketClockError(f"end ({end}) must be > start ({start})")
        if step_sec <= 0.0:
            raise MarketClockError("step_sec must be positive")
        self._start   = start
        self._end     = end
        self._current = start
        self._step    = step_sec
        self._ticks   = 0

    def reset(self) -> None:
        if self._start is None:
            raise MarketClockError("Clock has not been initialized")
        self._current = self._start
        self._ticks   = 0

    # ── Navigation ────────────────────────────────────────────────────────────

    def advance(self) -> float:
        """
        Advance by one step.

        Returns the new current timestamp.
        Raises ``StopIteration`` when past the end.
        """
        self._assert_init()
        next_ts = self._current + self._step  # type: ignore[operator]
        if next_ts > self._end:  # type: ignore[operator]
            raise StopIteration("Market clock has reached the end of the simulation range")
        self._current = next_ts
        self._ticks  += 1
        return self._current  # type: ignore[return-value]

    def advance_to(self, ts: float) -> None:
        """Jump the clock to an explicit timestamp (must not go backward)."""
        self._assert_init()
        if ts < self._current:  # type: ignore[operator]
            raise MarketClockError(
                f"Cannot advance clock backward: {ts} < {self._current}"
            )
        if ts > self._end:  # type: ignore[operator]
            raise MarketClockError(f"Timestamp {ts} is past end {self._end}")
        self._current = ts
        self._ticks  += 1

    def set_step(self, step_sec: float) -> None:
        if step_sec <= 0.0:
            raise MarketClockError("step_sec must be positive")
        self._step = step_sec

    # ── State ─────────────────────────────────────────────────────────────────

    def is_done(self) -> bool:
        if self._current is None or self._end is None:
            return False
        return self._current >= self._end

    def remaining(self) -> float:
        if self._current is None or self._end is None:
            return 0.0
        return max(0.0, self._end - self._current)

    def elapsed(self) -> float:
        if self._current is None or self._start is None:
            return 0.0
        return self._current - self._start

    @property
    def current(self) -> float:
        self._assert_init()
        return self._current  # type: ignore[return-value]

    @property
    def start(self) -> float:
        self._assert_init()
        return self._start  # type: ignore[return-value]

    @property
    def end(self) -> float:
        self._assert_init()
        return self._end  # type: ignore[return-value]

    @property
    def tick_count(self) -> int:
        return self._ticks

    @property
    def is_initialized(self) -> bool:
        return self._start is not None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _assert_init(self) -> None:
        if self._start is None:
            raise MarketClockError("MarketClock has not been initialized")

    def to_dict(self) -> dict[str, Any]:
        return {
            "start":        self._start,
            "end":          self._end,
            "current":      self._current,
            "step_sec":     self._step,
            "tick_count":   self._ticks,
            "is_done":      self.is_done(),
            "is_initialized": self.is_initialized,
        }
