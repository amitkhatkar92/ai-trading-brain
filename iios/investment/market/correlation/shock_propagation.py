"""iios/investment/market/correlation/shock_propagation.py
Analyzes how a shock in one asset propagates through the correlation network.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

from iios.investment.market.correlation.models import (
    ContagionPath,
    CorrelationEvent,
    CorrelationEventType,
    CorrelationMatrix,
    DependencyGraph,
)


class ShockPropagationAnalyzer:
    """
    Given a shocked asset (large return move), traces how the shock
    propagates through correlated and dependent assets.
    """

    def __init__(
        self,
        min_propagation_corr: float = 0.40,
        propagation_depth: int = 3,
        shock_threshold_pct: float = 0.03,
    ) -> None:
        self._min_corr       = min_propagation_corr
        self._depth          = propagation_depth
        self._shock_threshold = shock_threshold_pct

    def analyze(
        self,
        matrix: CorrelationMatrix,
        dep_graph: DependencyGraph,
        current_returns: Dict[str, float],
        bar_index: int,
    ) -> tuple[List[ContagionPath], List[CorrelationEvent]]:
        """
        Detect shocked assets and compute propagation paths.

        Returns (paths, events).
        """
        shocked = [
            (sym, ret) for sym, ret in current_returns.items()
            if abs(ret) >= self._shock_threshold
        ]

        all_paths: List[ContagionPath] = []
        events: List[CorrelationEvent] = []

        for sym, magnitude in shocked:
            paths = self._trace_propagation(sym, magnitude, matrix, dep_graph)
            if paths:
                all_paths.extend(paths)
                affected = list({p.target for p in paths[:5]})
                events.append(CorrelationEvent(
                    event_type=CorrelationEventType.SHOCK_PROPAGATION,
                    bar_index=bar_index,
                    severity=min(1.0, abs(magnitude) / 0.10),
                    affected_assets=[sym] + affected,
                    description=(
                        f"Shock in {sym} ({magnitude*100:.1f}%) "
                        f"propagates to {len(paths)} assets"
                    ),
                ))

        return all_paths, events

    # ── Internal ──────────────────────────────────────────────────────────

    def _trace_propagation(
        self,
        source: str,
        magnitude: float,
        matrix: CorrelationMatrix,
        dep_graph: DependencyGraph,
    ) -> List[ContagionPath]:
        paths: List[ContagionPath] = []
        visited: Set[str] = {source}
        queue = [(source, abs(magnitude), 0, [source])]

        # Also build adjacency from dependency graph for faster lookup
        followers: Dict[str, List[str]] = {}
        for edge in dep_graph.edges:
            followers.setdefault(edge.source, []).append(edge.target)

        while queue:
            asset, mag, depth, path = queue.pop(0)
            if depth >= self._depth:
                continue

            # Propagate via correlation
            for sym in matrix.symbols:
                if sym in visited:
                    continue
                corr = matrix.get(asset, sym)
                if corr is None or abs(corr) < self._min_corr:
                    continue

                prop_mag = mag * abs(corr)
                new_path = path + [sym]
                paths.append(ContagionPath(
                    source=source,
                    target=sym,
                    path=new_path,
                    correlation_product=abs(corr),
                    estimated_impact=prop_mag,
                    propagation_steps=depth + 1,
                ))
                visited.add(sym)
                if prop_mag > 0.005:  # only continue if impact still meaningful
                    queue.append((sym, prop_mag, depth + 1, new_path))

        return sorted(paths, key=lambda p: -p.estimated_impact)
