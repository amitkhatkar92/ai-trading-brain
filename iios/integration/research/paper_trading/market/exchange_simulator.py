"""market/exchange_simulator.py — Simulated exchange state and trading halts."""
from __future__ import annotations

from typing import Any

from iios.integration.research.paper_trading.paper_trading_constants import (
    ExchangeStatus,
    MarketPhase,
)
from iios.integration.research.paper_trading.paper_trading_exceptions import ExchangeError


class ExchangeSimulator:
    """
    Simulates the operational state of a generic exchange.

    Tracks overall exchange status, the active market phase, and per-symbol
    trading halts.  Does NOT impose calendar restrictions — use
    ``TradingSessionManager`` for calendar-aware logic.
    """

    def __init__(self, exchange_id: str = "SIMEX") -> None:
        self._exchange_id = exchange_id
        self._status:  ExchangeStatus          = ExchangeStatus.CLOSED
        self._phase:   MarketPhase             = MarketPhase.CLOSED
        self._halted:  dict[str, str]          = {}   # symbol → reason
        self._history: list[dict[str, Any]]    = []

    # ── Session control ───────────────────────────────────────────────────────

    def initialize(self) -> None:
        self._status = ExchangeStatus.CLOSED
        self._phase  = MarketPhase.CLOSED
        self._halted.clear()

    def open_session(self, timestamp: float) -> None:
        self._status = ExchangeStatus.OPEN
        self._phase  = MarketPhase.CONTINUOUS
        self._log("session_open", timestamp)

    def close_session(self, timestamp: float) -> None:
        self._status = ExchangeStatus.CLOSED
        self._phase  = MarketPhase.CLOSED
        self._log("session_close", timestamp)

    def set_phase(self, phase: MarketPhase, timestamp: float) -> None:
        self._phase = phase
        self._log(f"phase_{phase.value}", timestamp)

    # ── Halt management ───────────────────────────────────────────────────────

    def halt_trading(self, symbol: str, reason: str, timestamp: float) -> None:
        self._halted[symbol] = reason
        self._log(f"halt_{symbol}", timestamp, {"reason": reason})

    def resume_trading(self, symbol: str, timestamp: float) -> None:
        self._halted.pop(symbol, None)
        self._log(f"resume_{symbol}", timestamp)

    def is_halted(self, symbol: str) -> bool:
        return symbol in self._halted

    def halt_reason(self, symbol: str) -> str:
        return self._halted.get(symbol, "")

    # ── State queries ─────────────────────────────────────────────────────────

    def status(self) -> ExchangeStatus:
        return self._status

    def phase(self) -> MarketPhase:
        return self._phase

    def can_trade(self, symbol: str) -> bool:
        """Returns True when the exchange is open and the symbol is not halted."""
        if self._status not in (ExchangeStatus.OPEN, ExchangeStatus.PRE_MARKET, ExchangeStatus.POST_MARKET):
            return False
        return symbol not in self._halted

    @property
    def exchange_id(self) -> str:
        return self._exchange_id

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "exchange_id":    self._exchange_id,
            "status":         self._status.value,
            "phase":          self._phase.value,
            "halted_symbols": list(self._halted.keys()),
            "total_events":   len(self._history),
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _log(self, event: str, timestamp: float, extra: dict | None = None) -> None:
        entry: dict[str, Any] = {"event": event, "timestamp": timestamp}
        if extra:
            entry.update(extra)
        self._history.append(entry)
