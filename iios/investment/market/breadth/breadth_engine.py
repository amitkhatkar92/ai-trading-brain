"""iios/investment/market/breadth/breadth_engine.py
Core breadth engine: runs all registered metrics on a UniverseSnapshot
and accumulates the A/D line + rolling stats via BreadthStateTracker.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from iios.investment.market.breadth.models import BreadthData, BreadthMetricValue
from iios.investment.market.breadth.metric_registry import MetricRegistry
from iios.investment.market.breadth.breadth_state import BreadthStateTracker

if TYPE_CHECKING:
    from iios.investment.market.breadth.models import UniverseSnapshot


class BreadthEngine:
    """
    Runs all registered BreadthMetric objects on each UniverseSnapshot
    and returns a fully-populated BreadthData.

    Parameters
    ----------
    registry:  MetricRegistry supplying active metrics.
    window:    Rolling window for statistics (default 50).
    """

    def __init__(
        self,
        registry: MetricRegistry,
        window: int = 50,
        state_tracker: Optional[BreadthStateTracker] = None,
    ) -> None:
        self._registry = registry
        self._state = state_tracker or BreadthStateTracker(window=window)

    # ── Public API ─────────────────────────────────────────────────────────

    def update(
        self,
        universe: "UniverseSnapshot",
        above_ma20_pct: float,
        health_score: float,
    ) -> BreadthData:
        """Process one universe snapshot and return BreadthData."""
        obs = universe.observations
        advancing = sum(1 for o in obs if o.is_advancing)
        declining = sum(1 for o in obs if o.is_declining)
        unchanged = sum(1 for o in obs if o.is_unchanged)
        total     = len(obs)

        metric_values = self._run_metrics(obs)

        return self._state.update(
            advancing=advancing,
            declining=declining,
            unchanged=unchanged,
            total=total,
            above_ma20_pct=above_ma20_pct,
            health_score=health_score,
            metric_values=metric_values,
        )

    @property
    def state_tracker(self) -> BreadthStateTracker:
        return self._state

    def register_metric(self, metric) -> None:
        self._registry.register(metric)

    def unregister_metric(self, name: str) -> None:
        self._registry.unregister(name)

    # ── Internal ──────────────────────────────────────────────────────────

    def _run_metrics(
        self, observations: list
    ) -> Dict[str, BreadthMetricValue]:
        results: Dict[str, BreadthMetricValue] = {}
        for metric in self._registry.all():
            if len(observations) >= metric.required_observations:
                out = metric.compute(observations)
                if out is not None:
                    results[metric.name] = out
        return results
