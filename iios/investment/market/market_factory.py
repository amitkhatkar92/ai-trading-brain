"""iios/investment/market/market_factory.py
Static factory for Market Intelligence objects.
"""
from __future__ import annotations

from typing import Any, Callable

from iios.investment.market.market_constants import MarketRegime, MarketStatus
from iios.investment.market.market_state.market_snapshot import MarketSnapshot
from iios.investment.market.market_state.market_state import MarketState
from iios.investment.market.models.market_signal import MarketSignal, SignalStrength, SignalType
from iios.investment.market.models.market_summary import MarketSummary
from iios.investment.market.regime.regime_classifier import RegimeClassifier
from iios.investment.market.regime.regime_transition import RegimeTransition


class MarketFactory:
    """Static factory — no instances needed."""

    @staticmethod
    def make_snapshot(
        market_id: str,
        prices:    dict[str, float] | None = None,
        volumes:   dict[str, float] | None = None,
        changes:   dict[str, float] | None = None,
        spreads:   dict[str, float] | None = None,
        status:    MarketStatus            = MarketStatus.UNKNOWN,
        advances:  int                     = 0,
        declines:  int                     = 0,
        unchanged: int                     = 0,
        **metadata: Any,
    ) -> MarketSnapshot:
        p = prices  or {}
        v = volumes or {}
        return MarketSnapshot(
            market_id    = market_id,
            status       = status,
            prices       = p,
            volumes      = v,
            changes      = changes or {},
            spreads      = spreads or {},
            advances     = advances,
            declines     = declines,
            unchanged    = unchanged,
            symbols      = list(p.keys()),
            total_volume = sum(v.values()),
            metadata     = dict(metadata),
        )

    @staticmethod
    def make_market_state(market_id: str, name: str = "") -> MarketState:
        return MarketState(market_id=market_id, name=name or market_id)

    @staticmethod
    def make_signal(
        market_id:   str,
        label:       str,
        signal_type: str   = SignalType.CUSTOM,
        confidence:  float = 0.5,
        direction:   str   = "neutral",
        description: str   = "",
        strength:    str   = SignalStrength.MODERATE,
        value:       float | None = None,
    ) -> MarketSignal:
        return MarketSignal(
            market_id   = market_id,
            label       = label,
            signal_type = signal_type,
            confidence  = confidence,
            direction   = direction,
            description = description,
            strength    = strength,
            value       = value,
        )

    @staticmethod
    def make_function_classifier(
        classifier_id: str,
        name:          str,
        fn: Callable[
            [MarketSnapshot, list[MarketSnapshot]],
            tuple[MarketRegime, float],
        ],
    ) -> RegimeClassifier:
        """Creates an inline RegimeClassifier from a callable."""
        _id   = classifier_id
        _name = name
        _fn   = fn

        class _FunctionClassifier(RegimeClassifier):
            @property
            def classifier_id(self) -> str:
                return _id

            @property
            def name(self) -> str:
                return _name

            def classify(
                self,
                snapshot: MarketSnapshot,
                history:  list[MarketSnapshot],
            ) -> tuple[MarketRegime, float]:
                return _fn(snapshot, history)

        return _FunctionClassifier()
