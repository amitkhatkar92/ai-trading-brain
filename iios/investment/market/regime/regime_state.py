"""iios/investment/market/regime/regime_state.py
Thread-safe mutable state container per market.
"""
from __future__ import annotations

import threading
from typing import Any, Dict

from iios.investment.market.regime.models import RegimeType


class RegimeState:
    """Thread-safe per-market regime state tracker."""

    def __init__(self, market_id: str, symbol: str) -> None:
        self._lock:         threading.RLock = threading.RLock()
        self._market_id:    str             = market_id
        self._symbol:       str             = symbol
        self._current:      RegimeType      = RegimeType.UNKNOWN
        self._bars:         int             = 0

    def set_current(self, regime: RegimeType, confidence: float = 0.0) -> bool:
        """Thread-safe update. Returns True if regime changed."""
        with self._lock:
            if regime == self._current:
                self._bars += 1
                return False
            self._current = regime
            self._bars = 1
            return True

    def current_regime(self) -> RegimeType:
        with self._lock:
            return self._current

    def bars_in_current(self) -> int:
        with self._lock:
            return self._bars

    def reset(self) -> None:
        with self._lock:
            self._current = RegimeType.UNKNOWN
            self._bars = 0

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "market_id": self._market_id,
                "symbol":    self._symbol,
                "current":   self._current.value,
                "bars":      self._bars,
            }
