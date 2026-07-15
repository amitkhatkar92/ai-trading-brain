"""iios/investment/portfolio/integration/aggregation_state.py

Per-portfolio mutable aggregation state: stores engine contributions and
computes completeness/freshness/status.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.integration.integration_types import (
    AggregationStatus, EngineId, IntegrationParameters,
    REQUIRED_ENGINES, hours_since, now_utc,
)


@dataclass(frozen=True)
class EngineContribution:
    """Immutable record of one engine's intelligence contribution."""
    engine_id:       EngineId
    portfolio_id:    str
    contributed_at:  str
    data:            Dict[str, Any]
    contribution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_valid:        bool = True
    error:           Optional[str] = None

    def age_hours(self) -> float:
        return hours_since(self.contributed_at)


class AggregationState:
    """Thread-safe mutable state for per-portfolio aggregation."""

    def __init__(self, portfolio_id: str, params: IntegrationParameters) -> None:
        self.portfolio_id = portfolio_id
        self._params      = params
        self._lock        = threading.RLock()
        self._contributions: Dict[EngineId, EngineContribution] = {}

    def update(self, contribution: EngineContribution) -> None:
        with self._lock:
            self._contributions[contribution.engine_id] = contribution

    def get(self, engine_id: EngineId) -> Optional[EngineContribution]:
        with self._lock:
            return self._contributions.get(engine_id)

    def snapshot(self) -> Dict[EngineId, EngineContribution]:
        with self._lock:
            return dict(self._contributions)

    def present_engines(self) -> List[EngineId]:
        with self._lock:
            return [eid for eid, c in self._contributions.items() if c.is_valid]

    def missing_required(self) -> List[EngineId]:
        with self._lock:
            present = {eid for eid, c in self._contributions.items() if c.is_valid}
            return [eid for eid in REQUIRED_ENGINES if eid not in present]

    def completeness(self) -> float:
        with self._lock:
            n_required = len(REQUIRED_ENGINES)
            if n_required == 0:
                return 1.0
            n_present = sum(
                1 for eid in REQUIRED_ENGINES
                if eid in self._contributions and self._contributions[eid].is_valid
            )
            return n_present / n_required

    def freshness(self) -> float:
        """Fraction of contributions within the freshness window."""
        with self._lock:
            if not self._contributions:
                return 0.0
            fresh = sum(
                1 for c in self._contributions.values()
                if c.age_hours() <= self._params.freshness_hours
            )
            return fresh / len(self._contributions)

    def status(self) -> AggregationStatus:
        completeness = self.completeness()
        if completeness < self._params.min_completeness:
            return AggregationStatus.PARTIAL
        if self.freshness() < 0.80:
            return AggregationStatus.STALE
        return AggregationStatus.COMPLETE
