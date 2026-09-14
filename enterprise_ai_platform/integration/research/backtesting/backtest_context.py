"""backtest_context.py — Thread-local execution context for backtest operations."""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator, Optional


@dataclass
class BacktestContextState:
    operation:   str            = ""
    backtest_id: str            = ""
    strategy_id: str            = ""
    session_id:  str            = ""
    started_at:  float          = field(default_factory=time.time)

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1000.0


_tls = threading.local()


def _state() -> BacktestContextState:
    if not hasattr(_tls, "_bt_ctx"):
        _tls._bt_ctx = BacktestContextState()
    return _tls._bt_ctx


class BacktestContext:
    """Thread-local context carrier for backtest operations."""

    @staticmethod
    def set(
        operation:   str = "",
        backtest_id: str = "",
        strategy_id: str = "",
        session_id:  str = "",
    ) -> BacktestContextState:
        s = _state()
        s.operation   = operation
        s.backtest_id = backtest_id
        s.strategy_id = strategy_id
        s.session_id  = session_id
        s.started_at  = time.time()
        return s

    @staticmethod
    def get() -> BacktestContextState:
        return _state()

    @staticmethod
    def clear() -> None:
        _tls._bt_ctx = BacktestContextState()

    @staticmethod
    @contextmanager
    def scope(
        operation:   str = "",
        backtest_id: str = "",
        strategy_id: str = "",
        session_id:  str = "",
    ) -> Generator[BacktestContextState, None, None]:
        prev = BacktestContextState(
            operation   = _state().operation,
            backtest_id = _state().backtest_id,
            strategy_id = _state().strategy_id,
            session_id  = _state().session_id,
            started_at  = _state().started_at,
        )
        s = BacktestContext.set(operation, backtest_id, strategy_id, session_id)
        try:
            yield s
        finally:
            _tls._bt_ctx = prev
