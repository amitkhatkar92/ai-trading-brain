"""
analytics_component_registry.py — iios.execution.analytics.integration
=======================================================================
Manages the lifecycle of M1-M5 analytics components as a single unit.

:class:`AnalyticsComponentRegistry` owns the five component instances,
starts them in dependency order, registers M3/M4 with the M2 engine,
and provides accessor properties for downstream consumers.
"""
from __future__ import annotations

import threading
from typing import Dict, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.execution.analytics.lifecycle import AnalyticsLifecycle
from iios.execution.analytics.engine import ExecutionAnalyticsEngine
from iios.execution.analytics.performance import PerformanceAnalyticsEngine
from iios.execution.analytics.predictive import PredictiveIntelligenceEngine
from iios.execution.analytics.snapshot import (
    AnalyticsSnapshotFactory,
    AnalyticsSnapshotStore,
)
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger

from .constants import (
    COMPONENT_REG_ID,
    INTEGRATION_VERSION,
    ACTOR_SYSTEM,
    ComponentType,
)
from .analytics_component_factory import AnalyticsComponentFactory
from .exceptions import IntegrationComponentError

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=COMPONENT_REG_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsComponentRegistry(LifecycleAwareMixin):
    """
    Manages M1-M5 analytics component instances as a cohesive unit.

    Start/stop order
    ----------------
    *Start:*  M3 → M4 → M1 → M5-store → M5-factory → M2 (M3+M4 registered)
    *Stop:*   M2 → M5-factory → M5-store → M1 → M4 → M3

    This ordering ensures that:
    * M3 and M4 are available when M2 starts (to register immediately).
    * M5 store is up before the factory, which depends on the store.
    * M2 is stopped first so it drains cleanly before its frameworks stop.
    """

    def __init__(
        self,
        factory: Optional[AnalyticsComponentFactory] = None,
    ) -> None:
        super().__init__()
        self._factory = factory or AnalyticsComponentFactory()
        self._lock    = threading.Lock()

        # Component instances — created lazily in _on_start
        self._lifecycle: Optional[AnalyticsLifecycle]       = None
        self._engine:    Optional[ExecutionAnalyticsEngine]  = None
        self._performance: Optional[PerformanceAnalyticsEngine] = None
        self._predictive:  Optional[PredictiveIntelligenceEngine] = None
        self._snap_store:  Optional[AnalyticsSnapshotStore]  = None
        self._snap_factory: Optional[AnalyticsSnapshotFactory] = None

    # ------------------------------------------------------------------
    # LifecycleAwareMixin hooks
    # ------------------------------------------------------------------
    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            engine_id  = COMPONENT_REG_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = INTEGRATION_VERSION,
            actor      = ACTOR_SYSTEM,
        )
        self._create_and_start_all()
        _log.info("AnalyticsComponentRegistry: all M1-M5 components started")

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            engine_id  = COMPONENT_REG_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = INTEGRATION_VERSION,
            actor      = ACTOR_SYSTEM,
        )
        self._stop_all()
        _log.info("AnalyticsComponentRegistry: all M1-M5 components stopped")

    # ------------------------------------------------------------------
    # Component accessors (raise if registry not running)
    # ------------------------------------------------------------------
    @property
    def lifecycle(self) -> AnalyticsLifecycle:
        self._assert_running()
        return self._lifecycle  # type: ignore[return-value]

    @property
    def engine(self) -> ExecutionAnalyticsEngine:
        self._assert_running()
        return self._engine  # type: ignore[return-value]

    @property
    def performance(self) -> PerformanceAnalyticsEngine:
        self._assert_running()
        return self._performance  # type: ignore[return-value]

    @property
    def predictive(self) -> PredictiveIntelligenceEngine:
        self._assert_running()
        return self._predictive  # type: ignore[return-value]

    @property
    def snapshot_factory(self) -> AnalyticsSnapshotFactory:
        self._assert_running()
        return self._snap_factory  # type: ignore[return-value]

    @property
    def snapshot_store(self) -> AnalyticsSnapshotStore:
        self._assert_running()
        return self._snap_store  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Running-state helpers
    # ------------------------------------------------------------------
    def component_running_map(self) -> Dict[ComponentType, bool]:
        """Return mapping of each component type to its running state."""
        return {
            ComponentType.LIFECYCLE:   self._is_comp_running(self._lifecycle),
            ComponentType.ENGINE:      self._is_comp_running(self._engine),
            ComponentType.PERFORMANCE: self._is_comp_running(self._performance),
            ComponentType.PREDICTIVE:  self._is_comp_running(self._predictive),
            ComponentType.SNAPSHOT:    self._is_comp_running(self._snap_factory),
        }

    def is_lifecycle_running(self)   -> bool: return self._is_comp_running(self._lifecycle)
    def is_engine_running(self)      -> bool: return self._is_comp_running(self._engine)
    def is_performance_running(self) -> bool: return self._is_comp_running(self._performance)
    def is_predictive_running(self)  -> bool: return self._is_comp_running(self._predictive)
    def is_snapshot_running(self)    -> bool: return self._is_comp_running(self._snap_factory)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            from .exceptions import IntegrationNotRunningError
            raise IntegrationNotRunningError("component_registry")

    def _create_and_start_all(self) -> None:
        """Instantiate and start M1-M5 in the correct dependency order."""
        # M3
        self._performance = self._factory.create_performance()
        self._safe_start(self._performance, ComponentType.PERFORMANCE)

        # M4
        self._predictive = self._factory.create_predictive()
        self._safe_start(self._predictive, ComponentType.PREDICTIVE)

        # M1
        self._lifecycle = self._factory.create_lifecycle()
        self._safe_start(self._lifecycle, ComponentType.LIFECYCLE)

        # M5 store
        self._snap_store = self._factory.create_snapshot_store()
        self._safe_start(self._snap_store, ComponentType.SNAPSHOT)

        # M5 factory (store must already be running)
        self._snap_factory = self._factory.create_snapshot_factory(self._snap_store)
        self._safe_start(self._snap_factory, ComponentType.SNAPSHOT)

        # M2 — register M3/M4 before starting so they are wired in _on_start
        self._engine = self._factory.create_engine()
        self._safe_start(self._engine, ComponentType.ENGINE)
        # Register M3/M4 with M2 after M2 is running
        if self._is_comp_running(self._engine):
            try:
                self._engine.register_performance_framework(self._performance)
                self._engine.register_predictive_framework(self._predictive)
            except Exception as exc:
                _log.warning(
                    f"AnalyticsComponentRegistry: failed to register M3/M4 with M2: {exc}"
                )

    def _stop_all(self) -> None:
        """Stop M1-M5 in reverse dependency order."""
        for comp, label in [
            (self._engine,       "M2-engine"),
            (self._snap_factory, "M5-factory"),
            (self._snap_store,   "M5-store"),
            (self._lifecycle,    "M1-lifecycle"),
            (self._predictive,   "M4-predictive"),
            (self._performance,  "M3-performance"),
        ]:
            if comp is not None and self._is_comp_running(comp):
                try:
                    comp.stop()
                except Exception as exc:
                    _log.warning(
                        f"AnalyticsComponentRegistry: error stopping {label}: {exc}"
                    )

    @staticmethod
    def _is_comp_running(comp: object | None) -> bool:
        if comp is None:
            return False
        try:
            state = comp.lifecycle_state()  # type: ignore[union-attr]
            return state in _RUNNING
        except Exception:
            return False

    def _safe_start(self, comp: object, component_type: ComponentType) -> None:
        """Start *comp*; log a warning but do not raise on failure."""
        try:
            comp.start()  # type: ignore[union-attr]
        except Exception as exc:
            _log.warning(
                f"AnalyticsComponentRegistry: failed to start {component_type.value}: {exc}"
            )
