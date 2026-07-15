"""iios/investment/portfolio/integration/portfolio_intelligence_aggregator.py

Receives engine contributions and maintains per-portfolio aggregation state.
"""
from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.integration.aggregation_engine import AggregationEngine
from iios.investment.portfolio.integration.aggregation_history import (
    AggregationHistory, AggregationRecord,
)
from iios.investment.portfolio.integration.aggregation_state import (
    AggregationState, EngineContribution,
)
from iios.investment.portfolio.integration.integration_types import (
    AggregationStatus, EngineId, IntegrationParameters, now_utc,
)


class PortfolioIntelligenceAggregator:
    """
    Accepts intelligence contributions from each upstream portfolio engine
    and maintains per-portfolio aggregation state.
    """

    def __init__(self, params: Optional[IntegrationParameters] = None) -> None:
        self._params  = params or IntegrationParameters()
        self._engine  = AggregationEngine()
        self._history = AggregationHistory(self._params.snapshot_history_size)
        self._lock    = threading.RLock()
        self._states: Dict[str, AggregationState] = {}

    # ── Contributions ──────────────────────────────────────────────────────────

    def contribute(
        self,
        portfolio_id: str,
        engine_id:    EngineId,
        data:         Dict[str, Any],
        *,
        is_valid:     bool = True,
        error:        Optional[str] = None,
    ) -> EngineContribution:
        """Accept an intelligence payload from one upstream engine."""
        contribution = EngineContribution(
            engine_id      = engine_id,
            portfolio_id   = portfolio_id,
            contributed_at = now_utc(),
            data           = dict(data),
            is_valid       = is_valid,
            error          = error,
        )
        with self._lock:
            if portfolio_id not in self._states:
                self._states[portfolio_id] = AggregationState(portfolio_id, self._params)
            self._states[portfolio_id].update(contribution)
        return contribution

    # ── State access ───────────────────────────────────────────────────────────

    def get_state(self, portfolio_id: str) -> Optional[AggregationState]:
        with self._lock:
            return self._states.get(portfolio_id)

    def merge(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """Return the merged namespaced dict for a portfolio."""
        state = self.get_state(portfolio_id)
        return self._engine.merge(state) if state else None

    def aggregation_status(self, portfolio_id: str) -> AggregationStatus:
        state = self.get_state(portfolio_id)
        return state.status() if state else AggregationStatus.INVALID

    # ── History ────────────────────────────────────────────────────────────────

    def record_run(
        self,
        portfolio_id: str,
        duration_ms:  float,
        snapshot_id:  Optional[str] = None,
        error:        Optional[str] = None,
    ) -> AggregationRecord:
        state = self.get_state(portfolio_id)
        record = AggregationRecord(
            record_id    = str(uuid.uuid4()),
            portfolio_id = portfolio_id,
            aggregated_at = now_utc(),
            status       = state.status() if state else AggregationStatus.INVALID,
            n_engines    = len(state.present_engines()) if state else 0,
            completeness = state.completeness() if state else 0.0,
            freshness    = state.freshness() if state else 0.0,
            duration_ms  = duration_ms,
            snapshot_id  = snapshot_id,
            error        = error,
        )
        self._history.add(record)
        return record

    def aggregation_history(
        self,
        portfolio_id: str,
        n: int = 10,
    ) -> List[AggregationRecord]:
        return self._history.recent(portfolio_id, n)

    def all_portfolio_ids(self) -> List[str]:
        with self._lock:
            return list(self._states.keys())
