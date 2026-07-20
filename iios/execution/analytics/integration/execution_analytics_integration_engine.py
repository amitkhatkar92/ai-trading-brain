"""
execution_analytics_integration_engine.py — iios.execution.analytics.integration
==================================================================================
PRIMARY PUBLIC INTERFACE for the Execution Analytics Integration subsystem.

:class:`ExecutionAnalyticsIntegration` is the ONLY entry point that external
callers (orchestrators, controllers, services) interact with.  All M1-M5
analytics components are hidden behind this facade.

Usage example::

    integration = ExecutionAnalyticsIntegration()
    integration.initialize()
    integration.start()

    request = AnalyticsIntegrationRequest(execution_session_id="exec-001")
    response = integration.submit(request)

    snapshot = response.snapshot          # ExecutionAnalyticsSnapshot
    health   = integration.health()       # AnalyticsIntegrationHealth
    status   = integration.status()       # AnalyticsIntegrationStatus
    stats    = integration.statistics()   # AnalyticsIntegrationStatistics

    integration.stop()
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.execution.analytics.snapshot import ExecutionAnalyticsSnapshot
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger

from .constants import (
    INTEGRATION_SYSTEM_ID,
    INTEGRATION_VERSION,
    ACTOR_INTEGRATION,
    ComponentType,
    IntegrationStatus,
)
from .exceptions import (
    IntegrationAlreadyRunningError,
    IntegrationNotRunningError,
    IntegrationNotReadyError,
)
from .analytics_integration_request import AnalyticsIntegrationRequest
from .analytics_integration_response import AnalyticsIntegrationResponse
from .analytics_integration_health import (
    AnalyticsIntegrationHealth,
    assess_integration_health,
)
from .analytics_integration_status import (
    AnalyticsIntegrationStatus,
    build_integration_status,
)
from .analytics_integration_statistics import AnalyticsIntegrationStatistics
from .analytics_integration_history import AnalyticsIntegrationHistory
from .analytics_integration_validation import (
    AnalyticsIntegrationValidator,
    IntegrationValidationResult,
)
from .analytics_integration_registry import AnalyticsIntegrationRegistry
from .analytics_component_registry import AnalyticsComponentRegistry
from .analytics_component_factory import AnalyticsComponentFactory
from .analytics_integration_manager import AnalyticsIntegrationManager
from .analytics_integration_snapshot import IntegrationSnapshotRecord
from .analytics_integration_events import (
    make_analytics_initialized,
    make_analytics_started,
    make_analytics_stopped,
    make_analytics_restarted,
    make_analytics_health_changed,
    AnalyticsIntegrationEvent,
)

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=INTEGRATION_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class ExecutionAnalyticsIntegration(LifecycleAwareMixin):
    """
    Execution Analytics Integration subsystem — primary public entry point.

    Coordinates the M1-M5 analytics components as a single operational unit
    and exposes a clean, lifecycle-aware API to callers.

    This class performs NO analytics calculations, NO predictive calculations,
    NO reporting, and NO trade execution.  Its sole responsibility is to
    orchestrate the analytics pipeline and deliver
    :class:`~iios.execution.analytics.snapshot.ExecutionAnalyticsSnapshot`
    objects to callers.

    Parameters
    ----------
    factory :  Optional :class:`AnalyticsComponentFactory` for dependency
               injection (primarily for testing).

    Lifecycle
    ---------
    1. :meth:`initialize` — allocate and wire sub-components (idempotent).
    2. :meth:`start`      — start all sub-components.
    3. :meth:`stop`       — stop all sub-components.
    4. :meth:`restart`    — stop then start (convenience).

    All operational methods raise :class:`IntegrationNotRunningError` when
    called before :meth:`start`.
    """

    def __init__(
        self,
        factory: Optional[AnalyticsComponentFactory] = None,
    ) -> None:
        super().__init__()
        self._lock           = threading.RLock()
        self._initialized    = False
        self._started_at: Optional[float] = None
        self._last_health:   Optional[AnalyticsIntegrationHealth] = None

        # Sub-components — allocated in initialize()
        self._factory:    AnalyticsComponentFactory       = factory or AnalyticsComponentFactory()
        self._components: Optional[AnalyticsComponentRegistry] = None
        self._reg_int:    AnalyticsIntegrationRegistry    = AnalyticsIntegrationRegistry()
        self._stats:      AnalyticsIntegrationStatistics  = AnalyticsIntegrationStatistics()
        self._history:    AnalyticsIntegrationHistory     = AnalyticsIntegrationHistory()
        self._validator:  AnalyticsIntegrationValidator   = AnalyticsIntegrationValidator()
        self._manager:    Optional[AnalyticsIntegrationManager] = None

    # ==================================================================
    # Lifecycle API
    # ==================================================================

    def initialize(self) -> None:
        """
        Allocate and wire all internal sub-components.

        This method is idempotent — calling it more than once is safe.
        It must be called before :meth:`start`.

        Raises
        ------
        IntegrationAlreadyRunningError
            If :meth:`start` has already been called and the subsystem is
            currently running.
        """
        with self._lock:
            if self.lifecycle_state() in _RUNNING:
                raise IntegrationAlreadyRunningError()
            if self._initialized:
                return

            self._components = AnalyticsComponentRegistry(factory=self._factory)
            self._manager = AnalyticsIntegrationManager(
                components = self._components,
                registry   = self._reg_int,
                statistics = self._stats,
                history    = self._history,
                validator  = self._validator,
            )
            self._initialized = True

            init_evt = make_analytics_initialized(source=INTEGRATION_SYSTEM_ID)
            self._history.record_event(init_evt)
            _log.info("ExecutionAnalyticsIntegration: initialized")

    def _on_start(self) -> None:
        """
        LifecycleAwareMixin hook — starts all sub-components.

        :meth:`initialize` must be called first.

        Raises
        ------
        IntegrationNotReadyError
            If :meth:`initialize` has not been called.
        """
        if not self._initialized:
            raise IntegrationNotReadyError("call initialize() before start()")

        _audit.log_lifecycle_event(
            engine_id  = INTEGRATION_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = INTEGRATION_VERSION,
            actor      = ACTOR_INTEGRATION,
        )

        self._components.start()     # type: ignore[union-attr]
        self._manager.start()        # type: ignore[union-attr]
        self._started_at = time.time()

        start_evt = make_analytics_started(source=INTEGRATION_SYSTEM_ID)
        self._history.record_event(start_evt)
        _log.info(f"ExecutionAnalyticsIntegration: started (version {INTEGRATION_VERSION})")

    def _on_stop(self) -> None:
        """LifecycleAwareMixin hook — stops all sub-components."""
        _audit.log_lifecycle_event(
            engine_id  = INTEGRATION_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = INTEGRATION_VERSION,
            actor      = ACTOR_INTEGRATION,
        )

        if self._manager is not None and self._manager.lifecycle_state() in _RUNNING:
            self._manager.stop()
        if self._components is not None and self._components.lifecycle_state() in _RUNNING:
            self._components.stop()

        stop_evt = make_analytics_stopped(
            source = INTEGRATION_SYSTEM_ID,
            reason = "stop() called",
        )
        self._history.record_event(stop_evt)
        _log.info("ExecutionAnalyticsIntegration: stopped")

    def restart(self) -> None:
        """
        Restart the integration subsystem.

        Equivalent to calling :meth:`stop` then :meth:`start`.
        After restart, all statistics are preserved; history is preserved.
        """
        with self._lock:
            was_running = self.lifecycle_state() in _RUNNING
            if was_running:
                self.stop()
            self.start()

            restart_evt = make_analytics_restarted(source=INTEGRATION_SYSTEM_ID)
            self._history.record_event(restart_evt)
            _log.info("ExecutionAnalyticsIntegration: restarted")

    # ==================================================================
    # Operational API
    # ==================================================================

    def submit(self, request: AnalyticsIntegrationRequest) -> AnalyticsIntegrationResponse:
        """
        Submit an analytics integration request.

        Orchestrates the full M1-M5 pipeline:
        M1 session creation → M2 engine invocation → M3 performance analytics
        → M4 predictive intelligence → M5 snapshot publication.

        All non-critical steps (M2/M3/M4) degrade gracefully; a PARTIAL
        response is returned rather than raising when optional steps fail.

        Parameters
        ----------
        request :  :class:`AnalyticsIntegrationRequest` to process.

        Returns
        -------
        AnalyticsIntegrationResponse
            Contains the published :class:`ExecutionAnalyticsSnapshot` in
            ``response.snapshot`` when snapshot creation succeeded.

        Raises
        ------
        IntegrationNotRunningError
            When the subsystem is not in a running state.
        """
        self._assert_running()
        return self._manager.process(request)   # type: ignore[union-attr]

    def query(
        self,
        *,
        execution_session_id: Optional[str] = None,
        analytics_session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ExecutionAnalyticsSnapshot]:
        """
        Query previously published snapshots from M5 snapshot store.

        Parameters
        ----------
        execution_session_id :  Filter by execution session.
        analytics_session_id :  Filter by analytics session.
        request_id :            Filter by originating request.
        limit :                 Maximum number of snapshots to return.

        Returns
        -------
        list of ExecutionAnalyticsSnapshot
            Ordered oldest-first.  Empty list when no matches found.

        Raises
        ------
        IntegrationNotRunningError
            When the subsystem is not running.
        """
        self._assert_running()
        store = self._components.snapshot_store  # type: ignore[union-attr]

        try:
            if request_id is not None:
                # Query via history — match by request_id
                records = self._history.snapshots_for_request(request_id)
                return [r.snapshot for r in records[:limit]]

            if analytics_session_id:
                results = store.get_by_analytics_session(analytics_session_id)
                return list(results[:limit])

            if execution_session_id:
                results = store.get_by_execution_session(execution_session_id)
                return list(results[:limit])

            # No filter — return latest
            latest = store.get_latest(limit=limit)
            return list(latest)
        except Exception as exc:
            _log.warning("ExecutionAnalyticsIntegration.query: %s", exc)
            return []

    def snapshot(self) -> Optional[ExecutionAnalyticsSnapshot]:
        """
        Return the most recently published :class:`ExecutionAnalyticsSnapshot`.

        Returns ``None`` when no snapshots have been published yet or when
        the subsystem is not running.
        """
        if self.lifecycle_state() not in _RUNNING:
            return None
        record = self._history.latest_snapshot()
        return record.snapshot if record is not None else None

    def validate(
        self,
        *,
        include_performance: bool = True,
        include_predictions: bool = True,
    ) -> IntegrationValidationResult:
        """
        Run all seven integration validation checks.

        Can be called when the subsystem is running or initialised (not
        necessarily both).  Returns :class:`IntegrationValidationResult`
        regardless of outcome.

        Parameters
        ----------
        include_performance :  Check M3 readiness (default True).
        include_predictions :  Check M4 readiness (default True).
        """
        if self._manager is not None and self._manager.lifecycle_state() in _RUNNING:
            return self._manager.validate_subsystem(
                include_performance = include_performance,
                include_predictions = include_predictions,
            )

        # Subsystem not running — return validation result reflecting that
        return self._validator.validate(
            lifecycle_running   = False,
            engine_running      = False,
            performance_running = False,
            predictive_running  = False,
            snapshot_running    = False,
            integration_running = False,
            include_performance = include_performance,
            include_predictions = include_predictions,
        )

    # ==================================================================
    # Observability API
    # ==================================================================

    def health(self) -> AnalyticsIntegrationHealth:
        """
        Return the current :class:`AnalyticsIntegrationHealth`.

        Safe to call whether or not the subsystem is running.
        When not running all components are reported as NOT_STARTED.
        """
        is_running = self.lifecycle_state() in _RUNNING

        if not is_running or self._components is None:
            h = assess_integration_health(
                lifecycle_running   = False,
                engine_running      = False,
                performance_running = False,
                predictive_running  = False,
                snapshot_running    = False,
                integration_running = False,
            )
        else:
            crmap = self._components.component_running_map()
            h = assess_integration_health(
                lifecycle_running   = crmap.get(ComponentType.LIFECYCLE,   False),
                engine_running      = crmap.get(ComponentType.ENGINE,      False),
                performance_running = crmap.get(ComponentType.PERFORMANCE, False),
                predictive_running  = crmap.get(ComponentType.PREDICTIVE,  False),
                snapshot_running    = crmap.get(ComponentType.SNAPSHOT,    False),
                integration_running = is_running,
            )

        # Emit health-changed event when overall health changes
        if self._last_health is not None:
            prev = self._last_health.overall_health.value
            curr = h.overall_health.value
            if prev != curr:
                evt = make_analytics_health_changed(
                    previous_health = prev,
                    current_health  = curr,
                )
                self._history.record_event(evt)

        self._last_health = h
        return h

    def status(self) -> AnalyticsIntegrationStatus:
        """
        Return the current :class:`AnalyticsIntegrationStatus`.

        Safe to call whether or not the subsystem is running.
        """
        is_running = self.lifecycle_state() in _RUNNING
        crmap: Dict[ComponentType, bool] = {}
        if self._components is not None:
            try:
                crmap = self._components.component_running_map()
            except Exception:
                crmap = {ct: False for ct in ComponentType}

        h = self.health()
        return build_integration_status(
            health                = h,
            is_running            = is_running,
            active_requests       = self._reg_int.active_count(),
            total_requests        = self._stats.analytics_requests,
            total_snapshots       = self._stats.analytics_snapshots_published,
            started_at            = self._started_at,
            component_running_map = crmap,
        )

    def statistics(self) -> AnalyticsIntegrationStatistics:
        """Return the shared :class:`AnalyticsIntegrationStatistics` instance."""
        return self._stats

    def history(self) -> List[AnalyticsIntegrationResponse]:
        """
        Return the list of retained :class:`AnalyticsIntegrationResponse` objects.

        Ordered oldest-first.  Returns at most the history capacity entries.
        """
        return self._history.responses()

    def events(self) -> List[AnalyticsIntegrationEvent]:
        """Return retained :class:`AnalyticsIntegrationEvent` objects (oldest first)."""
        return self._history.events()

    def snapshot_records(self) -> List[IntegrationSnapshotRecord]:
        """Return retained :class:`IntegrationSnapshotRecord` objects (oldest first)."""
        return self._history.snapshots()

    # ==================================================================
    # Internal
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise IntegrationNotRunningError("ExecutionAnalyticsIntegration")

    def __repr__(self) -> str:
        state = self.lifecycle_state()
        state_str = state.value if hasattr(state, "value") else str(state)
        return (
            f"ExecutionAnalyticsIntegration("
            f"state={state_str!r}, "
            f"version={INTEGRATION_VERSION!r})"
        )
