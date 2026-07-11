"""iios/investment/market/integration/dependency_monitor.py
Tracks inter-engine dependencies and detects cascade failures.

A cascade failure occurs when a dependency-critical engine fails/goes stale
and downstream engines that depend on it would produce unreliable signals.
"""
from __future__ import annotations

from typing import Dict, List, Set

from iios.investment.market.integration.models import HealthStatus

# Dependency graph: engine → engines it depends on (conceptually)
# If the upstream engine is unhealthy, downstream confidence is reduced.
_DEPENDENCIES: Dict[str, List[str]] = {
    "trend":          ["market_regime"],
    "sector_rotation": ["breadth", "market_regime"],
    "opportunity":    ["trend", "volatility", "sector_rotation"],
    "breadth":        ["market_regime"],
    "correlation":    ["volatility"],
}


class DependencyMonitor:
    """Detects cascade failure paths given current engine health."""

    def __init__(
        self, dependency_graph: Dict[str, List[str]] = None
    ) -> None:
        self._graph = dependency_graph or _DEPENDENCIES

    def cascade_affected(
        self, unhealthy_engines: Set[str]
    ) -> Dict[str, List[str]]:
        """Return {downstream_engine: [failed_upstreams]} for all affected engines."""
        affected: Dict[str, List[str]] = {}
        for engine, deps in self._graph.items():
            failed_deps = [d for d in deps if d in unhealthy_engines]
            if failed_deps:
                affected[engine] = failed_deps
        return affected

    def reliability_factor(
        self,
        engine_name: str,
        health_records: Dict,   # engine_name → EngineHealthRecord
    ) -> float:
        """Return 0-1 reliability factor for engine given dependency health."""
        deps = self._graph.get(engine_name, [])
        if not deps:
            return 1.0
        scores = []
        for dep in deps:
            rec = health_records.get(dep)
            if rec is None:
                scores.append(0.5)
            elif rec.status is HealthStatus.HEALTHY:
                scores.append(1.0)
            elif rec.status is HealthStatus.DEGRADED:
                scores.append(0.7)
            elif rec.status is HealthStatus.STALE:
                scores.append(0.3)
            else:   # FAILED / MISSING
                scores.append(0.0)
        return sum(scores) / len(scores)
