"""iios/investment/portfolio/integration/aggregation_engine.py

Low-level merger of EngineContribution data into a canonical namespaced dict.
"""
from __future__ import annotations

from typing import Any, Dict

from iios.investment.portfolio.integration.aggregation_state import AggregationState
from iios.investment.portfolio.integration.integration_types import EngineId


class AggregationEngine:
    """
    Merges per-engine contributions into a single namespaced dict.
    Each engine's payload is stored under its engine_id.value key.
    """

    def merge(self, state: AggregationState) -> Dict[str, Any]:
        """Produce a namespaced dict from all valid contributions."""
        contributions = state.snapshot()
        merged: Dict[str, Any] = {}
        for engine_id, contribution in contributions.items():
            if contribution.is_valid:
                merged[engine_id.value] = dict(contribution.data)
        merged["_meta"] = {
            "portfolio_id": state.portfolio_id,
            "n_engines":    len(contributions),
            "completeness": state.completeness(),
            "freshness":    state.freshness(),
        }
        return merged

    def extract(
        self,
        merged:    Dict[str, Any],
        engine_id: EngineId,
        key:       str,
        default:   Any = None,
    ) -> Any:
        """Safely extract a keyed value from one engine's contribution."""
        return merged.get(engine_id.value, {}).get(key, default)
