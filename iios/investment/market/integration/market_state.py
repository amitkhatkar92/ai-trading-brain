"""iios/investment/market/integration/market_state.py
Classifies the integrated AggregationState into a MarketStateLabel.
"""
from __future__ import annotations

from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.models import MarketStateLabel


class MarketStateClassifier:
    """Deterministic rule-based market state classifier.

    Priority: CRISIS → RISK_OFF → RECOVERY → RISK_ON → TRANSITION → NEUTRAL.
    """

    def classify(self, state: AggregationState) -> MarketStateLabel:
        if self._is_crisis(state):
            return MarketStateLabel.CRISIS
        if self._is_risk_off(state):
            return MarketStateLabel.RISK_OFF
        if self._is_recovery(state):
            return MarketStateLabel.RECOVERY
        if self._is_risk_on(state):
            return MarketStateLabel.RISK_ON
        if self._is_transition(state):
            return MarketStateLabel.TRANSITION
        if state.market_regime is None:
            return MarketStateLabel.UNKNOWN
        return MarketStateLabel.NEUTRAL

    # ── sub-classifiers ───────────────────────────────────────────────────────

    @staticmethod
    def _is_crisis(s: AggregationState) -> bool:
        return (
            s.market_regime == "crisis"
            or s.volatility_regime == "extreme"
            or s.correlation_regime == "crisis"
            or s.liquidity_regime == "crisis"
        )

    @staticmethod
    def _is_risk_off(s: AggregationState) -> bool:
        signals = []
        if s.market_regime in ("bear", "neutral"):
            signals.append(True)
        if s.trend_direction == "down":
            signals.append(True)
        if s.breadth_regime == "negative":
            signals.append(True)
        if s.volatility_regime in ("elevated", "extreme"):
            signals.append(True)
        # Need at least 3 corroborating signals
        return sum(signals) >= 3

    @staticmethod
    def _is_recovery(s: AggregationState) -> bool:
        return (
            s.market_regime in ("bear", "neutral")
            and s.trend_direction == "up"
            and s.breadth_regime in ("positive", "neutral")
            and s.trend_strength < 65.0
        )

    @staticmethod
    def _is_risk_on(s: AggregationState) -> bool:
        signals = []
        if s.market_regime == "bull":
            signals.append(True)
        if s.trend_direction == "up" and s.trend_strength > 55.0:
            signals.append(True)
        if s.breadth_regime == "positive":
            signals.append(True)
        if s.volatility_regime in ("low", "normal"):
            signals.append(True)
        if s.liquidity_regime in ("abundant", "normal"):
            signals.append(True)
        return sum(signals) >= 3

    @staticmethod
    def _is_transition(s: AggregationState) -> bool:
        # Transition: mixed signals across key dimensions
        signals_present = sum(
            1 for x in (
                s.market_regime, s.trend_direction,
                s.breadth_regime, s.volatility_regime,
            )
            if x is not None
        )
        if signals_present < 2:
            return False
        # Bull regime but downtrend, or bear regime but uptrend
        mixed = (
            (s.market_regime == "bull" and s.trend_direction == "down")
            or (s.market_regime == "bear" and s.trend_direction == "up")
            or (s.breadth_regime == "positive" and s.market_regime == "bear")
            or (s.breadth_regime == "negative" and s.market_regime == "bull")
        )
        return mixed
