"""iios/execution/positions/integration/position_component_factory.py
==================================================
ComponentFactory — creates and wires all four Position Management
component instances.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

from typing import Tuple

from iios.execution.positions.engine import PositionEngine
from iios.execution.positions.book import PositionBook
from iios.execution.positions.risk import PositionRiskManager
from iios.execution.positions.snapshot import PositionSnapshotStore

from .constants import (
    DEFAULT_MAX_CACHE_ENTRIES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POSITIONS,
)


class ComponentFactory:
    """
    Creates all four Position Management components with consistent
    default parameters.

    Usage
    -----
    factory = ComponentFactory()
    engine, book, risk, snapshot_store = factory.create_all()
    """

    def __init__(
        self,
        max_positions: int = DEFAULT_MAX_POSITIONS,
        max_history:   int = DEFAULT_MAX_HISTORY,
        max_cache:     int = DEFAULT_MAX_CACHE_ENTRIES,
    ) -> None:
        self._max_positions = max(1, max_positions)
        self._max_history   = max(1, max_history)
        self._max_cache     = max(1, max_cache)

    # ── Factory methods ───────────────────────────────────────────────────────

    def create_engine(self) -> PositionEngine:
        """Create a new :class:`PositionEngine` instance (not started)."""
        return PositionEngine(
            max_positions=self._max_positions,
            max_history=self._max_history,
        )

    def create_book(self) -> PositionBook:
        """Create a new :class:`PositionBook` instance (not started)."""
        return PositionBook(
            max_positions=self._max_positions,
            max_history=self._max_history,
        )

    def create_risk_manager(self) -> PositionRiskManager:
        """Create a new :class:`PositionRiskManager` instance (not started)."""
        return PositionRiskManager(
            max_positions=self._max_positions,
            max_history=self._max_history,
        )

    def create_snapshot_store(self) -> PositionSnapshotStore:
        """Create a new :class:`PositionSnapshotStore` instance (not started)."""
        return PositionSnapshotStore(
            max_positions=self._max_positions,
            max_cache=self._max_cache,
            max_history=self._max_history,
        )

    def create_all(
        self,
    ) -> Tuple[PositionEngine, PositionBook, PositionRiskManager, PositionSnapshotStore]:
        """
        Create all four components.

        Returns
        -------
        (engine, book, risk_manager, snapshot_store) — all un-started.
        """
        return (
            self.create_engine(),
            self.create_book(),
            self.create_risk_manager(),
            self.create_snapshot_store(),
        )
