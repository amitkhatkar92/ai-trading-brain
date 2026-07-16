"""iios/execution/positions/integration/position_component_registry.py
==================================================
ComponentRegistry — tracks all live Position Management component
instances registered with the integration layer.

Not a LifecycleAwareMixin — it is a plain, thread-safe registry
that stores references to the four live components.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .constants import (
    ALL_COMPONENT_NAMES,
    COMPONENT_BOOK,
    COMPONENT_ENGINE,
    COMPONENT_RISK,
    COMPONENT_SNAPSHOT,
    HealthStatus,
    VERSION,
)
from .exceptions import ComponentNotFoundError, ComponentRegistrationError
from .position_component_health import (
    ComponentHealthRecord,
    HealthReport,
    make_health_report,
)
from .position_component_status import ComponentStatus

if TYPE_CHECKING:
    from iios.investment.workflow.engine_lifecycle import EngineState
    from iios.execution.positions.engine import PositionEngine
    from iios.execution.positions.book import PositionBook
    from iios.execution.positions.risk import PositionRiskManager
    from iios.execution.positions.snapshot import PositionSnapshotStore


class ComponentRegistry:
    """
    Thread-safe registry of the four live Position Management components.

    Responsibilities
    ----------------
    * Hold references to: PositionEngine, PositionBook,
      PositionRiskManager, PositionSnapshotStore.
    * Answer liveness and health queries without owning lifecycle.
    * Produce ``ComponentStatus`` and ``HealthReport`` on demand.

    Non-responsibilities
    --------------------
    * Does NOT start or stop components.
    * Does NOT manage component lifecycle.
    """

    def __init__(self) -> None:
        self._lock:    threading.Lock = threading.Lock()
        self._engine:  Optional[Any]  = None
        self._book:    Optional[Any]  = None
        self._risk:    Optional[Any]  = None
        self._snapshot: Optional[Any] = None

    # ── Registration ──────────────────────────────────────────────────────────

    def register_engine(self, engine: Any) -> None:
        with self._lock:
            if engine is None:
                raise ComponentRegistrationError(COMPONENT_ENGINE)
            self._engine = engine

    def register_book(self, book: Any) -> None:
        with self._lock:
            if book is None:
                raise ComponentRegistrationError(COMPONENT_BOOK)
            self._book = book

    def register_risk(self, risk_manager: Any) -> None:
        with self._lock:
            if risk_manager is None:
                raise ComponentRegistrationError(COMPONENT_RISK)
            self._risk = risk_manager

    def register_snapshot(self, snapshot_store: Any) -> None:
        with self._lock:
            if snapshot_store is None:
                raise ComponentRegistrationError(COMPONENT_SNAPSHOT)
            self._snapshot = snapshot_store

    # ── Access ────────────────────────────────────────────────────────────────

    def require_engine(self) -> Any:
        with self._lock:
            if self._engine is None:
                raise ComponentNotFoundError(COMPONENT_ENGINE)
            return self._engine

    def require_book(self) -> Any:
        with self._lock:
            if self._book is None:
                raise ComponentNotFoundError(COMPONENT_BOOK)
            return self._book

    def require_risk(self) -> Any:
        with self._lock:
            if self._risk is None:
                raise ComponentNotFoundError(COMPONENT_RISK)
            return self._risk

    def require_snapshot(self) -> Any:
        with self._lock:
            if self._snapshot is None:
                raise ComponentNotFoundError(COMPONENT_SNAPSHOT)
            return self._snapshot

    def get_engine(self) -> Optional[Any]:
        with self._lock:
            return self._engine

    def get_book(self) -> Optional[Any]:
        with self._lock:
            return self._book

    def get_risk(self) -> Optional[Any]:
        with self._lock:
            return self._risk

    def get_snapshot(self) -> Optional[Any]:
        with self._lock:
            return self._snapshot

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_registered(self, component_name: str) -> bool:
        with self._lock:
            return self._component_by_name(component_name) is not None

    def all_registered(self) -> bool:
        with self._lock:
            return all(
                c is not None
                for c in [self._engine, self._book, self._risk, self._snapshot]
            )

    def registered_count(self) -> int:
        with self._lock:
            return sum(
                1 for c in [self._engine, self._book, self._risk, self._snapshot]
                if c is not None
            )

    # ── Status & health ───────────────────────────────────────────────────────

    def component_status(self, component_name: str) -> ComponentStatus:
        """Return a ``ComponentStatus`` for the named component."""
        from iios.investment.workflow.engine_lifecycle import EngineState

        with self._lock:
            comp = self._component_by_name(component_name)

        if comp is None:
            return ComponentStatus(
                component_name=component_name,
                is_registered=False,
                is_running=False,
                is_healthy=False,
                lifecycle_state="NOT_REGISTERED",
                message="Component not registered",
            )

        try:
            lc_state = comp.lifecycle_state()
            is_running = lc_state == EngineState.RUNNING
            lc_str = lc_state.value if hasattr(lc_state, "value") else str(lc_state)
        except Exception as exc:
            return ComponentStatus(
                component_name=component_name,
                is_registered=True,
                is_running=False,
                is_healthy=False,
                lifecycle_state="UNKNOWN",
                message=f"lifecycle_state() raised: {exc}",
            )

        return ComponentStatus(
            component_name=component_name,
            is_registered=True,
            is_running=is_running,
            is_healthy=is_running,
            lifecycle_state=lc_str,
        )

    def all_statuses(self) -> List[ComponentStatus]:
        return [self.component_status(n) for n in sorted(ALL_COMPONENT_NAMES)]

    def health_report(self) -> HealthReport:
        """Produce a ``HealthReport`` over all four components."""
        records: List[ComponentHealthRecord] = []
        now = time.time()

        for name in sorted(ALL_COMPONENT_NAMES):
            status = self.component_status(name)
            if status.is_healthy:
                hs = HealthStatus.HEALTHY
                msg = "OK"
            elif not status.is_registered:
                hs = HealthStatus.CRITICAL
                msg = "Component not registered"
            else:
                hs = HealthStatus.DEGRADED
                msg = status.message or f"Not running (state={status.lifecycle_state})"

            records.append(
                ComponentHealthRecord(
                    component_name=name,
                    status=hs,
                    is_running=status.is_running,
                    message=msg,
                    checked_at=now,
                )
            )

        return make_health_report(records)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _component_by_name(self, name: str) -> Optional[Any]:
        if name == COMPONENT_ENGINE:
            return self._engine
        if name == COMPONENT_BOOK:
            return self._book
        if name == COMPONENT_RISK:
            return self._risk
        if name == COMPONENT_SNAPSHOT:
            return self._snapshot
        return None
