"""iios/investment/market/regime/market_regime_engine.py
Coordinates regime detection and tracks transitions per market.
"""
from __future__ import annotations

import threading
import time

from iios.investment.market.market_constants import MarketRegime
from iios.investment.market.market_state.market_snapshot import MarketSnapshot
from iios.investment.market.regime.regime_classifier import (
    DefaultRegimeClassifier,
    RegimeClassifier,
)
from iios.investment.market.regime.regime_history import RegimeHistory
from iios.investment.market.regime.regime_transition import RegimeTransition


class MarketRegimeEngine:
    """Stateful engine that classifies and tracks market regimes."""

    def __init__(
        self,
        classifier: RegimeClassifier | None = None,
        history:    RegimeHistory    | None = None,
    ) -> None:
        self._lock:       threading.RLock      = threading.RLock()
        self._classifier: RegimeClassifier     = classifier or DefaultRegimeClassifier()
        self._history:    RegimeHistory        = history    or RegimeHistory()
        self._current:    dict[str, MarketRegime] = {}
        self._confidence: dict[str, float]        = {}
        self._bars:       dict[str, int]           = {}  # consecutive bars in current regime

    def classify(
        self,
        market_id: str,
        snapshot:  MarketSnapshot,
        history:   list[MarketSnapshot] | None = None,
    ) -> tuple[MarketRegime, float]:
        """Classify regime and record any transition."""
        regime, confidence = self._classifier.classify(snapshot, history or [])

        with self._lock:
            prev = self._current.get(market_id, MarketRegime.UNKNOWN)

            if prev != regime:
                # Record transition
                bars = self._bars.get(market_id, 0)
                transition = RegimeTransition(
                    market_id    = market_id,
                    from_regime  = prev,
                    to_regime    = regime,
                    confidence   = confidence,
                    trigger      = f"classifier:{self._classifier.classifier_id}",
                    duration_bars = bars,
                    timestamp    = time.time(),
                )
                self._history.record(transition)
                self._bars[market_id]    = 0
            else:
                self._bars[market_id] = self._bars.get(market_id, 0) + 1

            self._current[market_id]    = regime
            self._confidence[market_id] = confidence

        return regime, confidence

    def current_regime(self, market_id: str) -> MarketRegime:
        with self._lock:
            return self._current.get(market_id, MarketRegime.UNKNOWN)

    def confidence(self, market_id: str) -> float:
        with self._lock:
            return self._confidence.get(market_id, 0.0)

    def regime_history(self) -> RegimeHistory:
        return self._history

    def set_classifier(self, classifier: RegimeClassifier) -> None:
        with self._lock:
            self._classifier = classifier

    def known_markets(self) -> list[str]:
        with self._lock:
            return list(self._current.keys())

    def bars_in_current_regime(self, market_id: str) -> int:
        with self._lock:
            return self._bars.get(market_id, 0)
