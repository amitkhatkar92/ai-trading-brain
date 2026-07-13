"""iios/investment/strategy/lifecycle/dependency_validator.py
Validation of strategy dependency graphs and individual declarations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set

from iios.investment.strategy.lifecycle.dependency_graph import (
    CyclicDependencyError,
    DependencyGraph,
)


@dataclass
class DependencyValidationResult:
    """Detailed result of a dependency validation pass."""

    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_strategies: List[str] = field(default_factory=list)
    cycles_detected: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


class DependencyValidator:
    """
    Validates strategy dependency declarations before execution.

    Graph-level checks:
      - No cycles (topological sort must succeed)
      - No self-dependencies
      - All dependency targets are registered (optional)

    Single-declaration checks:
      - No self-dependency
      - No duplicate declarations
      - All targets registered (optional)
    """

    def validate_graph(
        self,
        graph: DependencyGraph,
        registered_strategy_ids: Optional[Set[str]] = None,
    ) -> DependencyValidationResult:
        """
        Validate an entire dependency graph.

        Args:
            graph: Graph to validate.
            registered_strategy_ids: When provided, any dependency target not
                in this set is reported as a warning.
        """
        result = DependencyValidationResult()

        # Cycle detection via topological sort
        try:
            graph.topological_sort()
        except CyclicDependencyError as exc:
            result.add_error(f"Cyclic dependency: {exc}")
            result.cycles_detected.append(str(exc))

        # Self-dependency
        for sid in graph.all_strategy_ids():
            if sid in graph.get_dependencies(sid):
                result.add_error(f"Strategy {sid!r} depends on itself")

        # Unregistered dependencies
        if registered_strategy_ids is not None:
            for sid in graph.all_strategy_ids():
                for dep_id in graph.get_dependencies(sid):
                    if dep_id not in registered_strategy_ids:
                        result.missing_strategies.append(dep_id)
                        result.add_warning(
                            f"Strategy {sid!r} depends on unregistered "
                            f"strategy {dep_id!r}"
                        )

        return result

    def validate_single(
        self,
        strategy_id: str,
        dependencies: List[str],
        registered_strategy_ids: Optional[Set[str]] = None,
    ) -> DependencyValidationResult:
        """
        Validate a single strategy's dependency list without a full graph.
        """
        result = DependencyValidationResult()

        # Self-dependency
        if strategy_id in dependencies:
            result.add_error(
                f"Strategy {strategy_id!r} cannot depend on itself"
            )

        # Duplicate entries
        seen: Set[str] = set()
        for dep in dependencies:
            if dep in seen:
                result.add_warning(
                    f"Duplicate dependency {dep!r} for {strategy_id!r}"
                )
            seen.add(dep)

        # Unregistered targets
        if registered_strategy_ids is not None:
            for dep in dependencies:
                if dep not in registered_strategy_ids:
                    result.missing_strategies.append(dep)
                    result.add_warning(
                        f"Dependency {dep!r} of {strategy_id!r} is not registered"
                    )

        return result
