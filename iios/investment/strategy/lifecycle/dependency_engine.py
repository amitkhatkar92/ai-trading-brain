"""iios/investment/strategy/lifecycle/dependency_engine.py
Dependency resolution engine — combines registry + graph for runtime use.

Converts declared dependencies into execution batches and tracks
satisfaction at runtime so downstream strategies only run when all
their required upstream strategies have completed.
"""
from __future__ import annotations

import logging
import threading
from typing import Dict, FrozenSet, List, Optional, Set

from iios.investment.strategy.lifecycle.dependency_graph import (
    CyclicDependencyError,
    DependencyGraph,
)
from iios.investment.strategy.lifecycle.dependency_registry import (
    DependencyDeclaration,
    DependencyRegistry,
    DependencyType,
)
from iios.investment.strategy.lifecycle.dependency_validator import (
    DependencyValidationResult,
    DependencyValidator,
)

logger = logging.getLogger(__name__)


class DependencyResolutionError(Exception):
    """Raised when dependencies cannot be resolved for execution."""


class DependencyEngine:
    """
    Resolves strategy execution order from declared dependencies.

    Ordering API:
        engine.topological_order()   → List[str]  (dependency-first order)
        engine.parallel_batches()    → List[List[str]]  (concurrent groups)

    Runtime tracking (call once per cycle):
        engine.reset_cycle()
        engine.mark_completed("strat-a")
        engine.is_ready("strat-b")   → True when strat-a done
        engine.ready_to_run(candidates) → filtered list
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._registry = DependencyRegistry()
        self._graph = DependencyGraph()
        self._validator = DependencyValidator()
        self._completed: Set[str] = set()

    # ── Declaration API ───────────────────────────────────────────────────────

    def declare(self, declaration: DependencyDeclaration) -> None:
        """
        Add a dependency declaration and update the execution graph.

        Raises CyclicDependencyError if the dependency would form a cycle.
        On cycle detection the registry entry is rolled back.
        """
        with self._lock:
            self._registry.declare(declaration)
            try:
                self._graph.add_dependency(
                    declaration.strategy_id, declaration.depends_on
                )
            except CyclicDependencyError:
                # Roll back — remove the declaration just added
                decls = self._registry.get_dependencies(declaration.strategy_id)
                self._registry._declarations[declaration.strategy_id] = [
                    d
                    for d in decls
                    if d.depends_on != declaration.depends_on
                ]
                raise

    def declare_many(self, declarations: List[DependencyDeclaration]) -> None:
        for decl in declarations:
            self.declare(decl)

    def remove_strategy(self, strategy_id: str) -> None:
        """Remove a strategy and all its dependency edges from the engine."""
        with self._lock:
            self._registry.remove_strategy(strategy_id)
            self._graph.remove_strategy(strategy_id)
            self._completed.discard(strategy_id)

    # ── Ordering API ──────────────────────────────────────────────────────────

    def topological_order(self) -> List[str]:
        """Return all strategies in dependency-first execution order."""
        with self._lock:
            return self._graph.topological_sort()

    def parallel_batches(self) -> List[List[str]]:
        """
        Return groups of strategies that can execute concurrently.

        Strategies in the same batch share no inter-dependencies.
        Returns an empty list when no strategies have declared dependencies.
        """
        with self._lock:
            return self._graph.independent_sets()

    def get_dependencies(self, strategy_id: str) -> FrozenSet[str]:
        return self._graph.get_dependencies(strategy_id)

    def get_dependents(self, strategy_id: str) -> FrozenSet[str]:
        return self._graph.get_dependents(strategy_id)

    # ── Runtime tracking ──────────────────────────────────────────────────────

    def reset_cycle(self) -> None:
        """Clear completion tracking — call at the start of each new cycle."""
        with self._lock:
            self._completed.clear()

    def mark_completed(self, strategy_id: str) -> None:
        """Signal that strategy_id has successfully completed this cycle."""
        with self._lock:
            self._completed.add(strategy_id)

    def is_ready(self, strategy_id: str) -> bool:
        """True if all *required* dependencies of strategy_id are completed."""
        with self._lock:
            required = self._registry.get_required_dependency_ids(strategy_id)
            return required.issubset(self._completed)

    def ready_to_run(self, candidate_ids: Set[str]) -> List[str]:
        """
        Filter candidate_ids to those whose required dependencies are satisfied.

        Args:
            candidate_ids: Strategy IDs under consideration for the next batch.

        Returns:
            Subset that is ready to execute.
        """
        with self._lock:
            return [sid for sid in candidate_ids if self.is_ready(sid)]

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(
        self, registered_ids: Optional[Set[str]] = None
    ) -> DependencyValidationResult:
        """Validate the full dependency graph."""
        with self._lock:
            return self._validator.validate_graph(self._graph, registered_ids)

    # ── Convenience constructors ──────────────────────────────────────────────

    @staticmethod
    def market_dependency(strategy_id: str) -> DependencyDeclaration:
        return DependencyDeclaration(
            strategy_id=strategy_id,
            depends_on="__market_intelligence__",
            dependency_type=DependencyType.MARKET_INTELLIGENCE,
            required=True,
            description="Requires market intelligence snapshot",
        )

    @staticmethod
    def company_dependency(strategy_id: str) -> DependencyDeclaration:
        return DependencyDeclaration(
            strategy_id=strategy_id,
            depends_on="__company_intelligence__",
            dependency_type=DependencyType.COMPANY_INTELLIGENCE,
            required=True,
            description="Requires company intelligence snapshot",
        )

    @staticmethod
    def risk_dependency(strategy_id: str) -> DependencyDeclaration:
        return DependencyDeclaration(
            strategy_id=strategy_id,
            depends_on="__risk_engine__",
            dependency_type=DependencyType.RISK,
            required=True,
            description="Requires risk validation to pass",
        )

    def __len__(self) -> int:
        return len(self._graph)
