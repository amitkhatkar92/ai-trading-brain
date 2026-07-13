"""iios/investment/strategy/lifecycle/dependency_registry.py
Registry of strategy dependency declarations (semantic layer above the graph).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional


class DependencyType(str, Enum):
    """Semantic type of a dependency — for documentation and future routing."""

    MARKET_INTELLIGENCE  = "market_intelligence"
    COMPANY_INTELLIGENCE = "company_intelligence"
    PORTFOLIO            = "portfolio"
    RISK                 = "risk"
    EXECUTION            = "execution"
    STRATEGY             = "strategy"   # depends on another strategy's output
    CUSTOM               = "custom"


@dataclass
class DependencyDeclaration:
    """
    Declared dependency of one strategy on another (or on an engine layer).

    required=True  — downstream strategy does not run if dependency fails.
    required=False — downstream strategy runs regardless; dependency is advisory.
    """

    strategy_id: str
    depends_on: str
    dependency_type: DependencyType = DependencyType.STRATEGY
    required: bool = True
    description: str = ""


class DependencyRegistry:
    """
    Thread-safe authoritative store of DependencyDeclaration objects.

    The DependencyGraph is built from these declarations; this registry
    is the source of truth for what each strategy declared it needs.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # strategy_id → list of declarations
        self._declarations: Dict[str, List[DependencyDeclaration]] = {}

    # ── Write ─────────────────────────────────────────────────────────────────

    def declare(self, declaration: DependencyDeclaration) -> None:
        with self._lock:
            self._declarations.setdefault(
                declaration.strategy_id, []
            ).append(declaration)

    def declare_many(self, declarations: List[DependencyDeclaration]) -> None:
        for decl in declarations:
            self.declare(decl)

    def remove_strategy(self, strategy_id: str) -> None:
        """Remove all declarations where strategy_id is the dependent."""
        with self._lock:
            self._declarations.pop(strategy_id, None)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_dependencies(
        self, strategy_id: str
    ) -> List[DependencyDeclaration]:
        with self._lock:
            return list(self._declarations.get(strategy_id, []))

    def get_dependency_ids(self, strategy_id: str) -> FrozenSet[str]:
        with self._lock:
            decls = self._declarations.get(strategy_id, [])
            return frozenset(d.depends_on for d in decls)

    def get_required_dependency_ids(self, strategy_id: str) -> FrozenSet[str]:
        with self._lock:
            decls = self._declarations.get(strategy_id, [])
            return frozenset(d.depends_on for d in decls if d.required)

    def all_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._declarations.keys())

    def all_declarations(self) -> List[DependencyDeclaration]:
        with self._lock:
            result: List[DependencyDeclaration] = []
            for decls in self._declarations.values():
                result.extend(decls)
            return result
