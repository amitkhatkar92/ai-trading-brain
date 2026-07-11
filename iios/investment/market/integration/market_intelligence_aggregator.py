"""iios/investment/market/integration/market_intelligence_aggregator.py
Thin orchestrator: combines AggregationEngine + AggregationHistory.
"""
from __future__ import annotations

from iios.investment.market.integration.aggregation_engine import AggregationEngine
from iios.investment.market.integration.aggregation_history import AggregationHistory
from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.models import IntelligenceBundle


class MarketIntelligenceAggregator:
    """Aggregates intelligence bundles and maintains a history of states."""

    def __init__(self, history_len: int = 200) -> None:
        self._engine  = AggregationEngine()
        self._history = AggregationHistory(history_len)

    def aggregate(self, bundle: IntelligenceBundle) -> AggregationState:
        state = self._engine.aggregate(bundle)
        self._history.append(state)
        return state

    @property
    def history(self) -> AggregationHistory:
        return self._history

    def latest_state(self) -> AggregationState | None:
        return self._history.latest()
