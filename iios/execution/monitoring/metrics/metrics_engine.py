"""iios/execution/monitoring/metrics/metrics_engine.py
==================================================
MetricsEngine — primary public API for the Execution Metrics Framework.

Owns: manager, factory, registry, validator, statistics, history,
and event dispatch.

IMPORTANT: The Metrics Framework ONLY computes metrics.
It MUST NOT generate alerts, block execution, execute trades,
or communicate with brokers.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import time
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ENGINE_SYSTEM_ID,
    VERSION,
    MetricType,
    WindowSize,
)
from .exceptions import (
    MetricCalculationError,
    MetricsEngineNotRunningError,
    MetricsValidationError,
)
from .metrics_context import MetricsContext, make_metrics_context
from .metrics_events import (
    MetricsEvent,
    make_aggregation_completed,
    make_calculation_failed,
    make_metrics_aggregated,
    make_metrics_calculated,
    make_metrics_collected,
    make_metrics_published,
)
from .metrics_factory import MetricsFactory
from .metrics_history import MetricsHistory
from .metrics_manager import MetricsManager
from .metrics_registry import MetricsRegistry
from .metrics_request import MetricsRequest
from .metrics_response import MetricsResponse
from .metrics_snapshot import MetricsSnapshot
from .metrics_statistics import MetricsStatistics
from .metrics_validation import MetricsValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)


class MetricsEngine(LifecycleAwareMixin):
    """
    Primary public API for the Execution Metrics Framework.

    Usage
    -----
    engine = MetricsEngine()
    engine.start()

    # Ingest data
    engine.record("session-1", MetricType.P99_LATENCY, 42.5)

    # Compute snapshot
    snapshot = engine.snapshot("session-1", "portfolio-A")

    # Process a structured request
    request  = engine.create_request("session-1", (MetricType.P95_LATENCY,))
    response = engine.process_request(request)

    engine.stop()
    """

    def __init__(
        self,
        max_points_per_series: int = 10_000,
        max_snapshots:         int = 50_000,
        max_history:           int = 1_000,
    ) -> None:
        super().__init__()
        self._manager   = MetricsManager(
            max_points_per_series=max_points_per_series
        )
        self._registry  = MetricsRegistry(max_snapshots=max_snapshots)
        self._factory   = MetricsFactory()
        self._validator = MetricsValidator()
        self._stats     = MetricsStatistics()
        self._history   = MetricsHistory(
            max_snapshots=max_history,
            max_responses=max_history,
            max_events=max_history,
        )
        self._listeners: List[Callable[[MetricsEvent], None]] = []
        self._listeners_lock = threading.Lock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        self._manager.start()
        self._registry.start()
        self._factory.start()
        _audit.log_lifecycle_event(
            ENGINE_SYSTEM_ID,
            EngineState.STOPPED,
            EngineState.RUNNING,
            VERSION,
        )
        _log.info(
            "MetricsEngine started.",
            system_id=ENGINE_SYSTEM_ID,
            version=VERSION,
        )

    def _on_stop(self) -> None:
        self._factory.stop()
        self._registry.stop()
        self._manager.stop()
        _log.info(
            "MetricsEngine stopped.",
            system_id=ENGINE_SYSTEM_ID,
            metrics_calculated=self._stats.metrics_calculated,
            metrics_published=self._stats.metrics_published,
        )

    def _assert_running(self) -> None:
        state = self.lifecycle_state()
        if state not in (EngineState.RUNNING, "running"):
            raise MetricsEngineNotRunningError()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _emit(self, event: MetricsEvent) -> None:
        self._history.append_event(event)
        with self._listeners_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "Event listener raised exception.",
                    event_type=event.event_type.value,
                    error=str(exc),
                )

    # ── Data ingestion ────────────────────────────────────────────────────────

    def record(
        self,
        session_id:  str,
        metric_type: MetricType,
        value:       float,
        *,
        timestamp: Optional[float]         = None,
        tags:      Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Ingest a single raw data point.

        Thread-safe.  May be called from any thread at high frequency.
        """
        self._assert_running()
        self._manager.record(
            session_id, metric_type, value,
            timestamp=timestamp, tags=tags
        )
        self._stats.record_data_point()
        self._emit(make_metrics_collected(session_id))

    def record_batch(
        self,
        session_id: str,
        batch: List[Tuple[MetricType, float]],
        *,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Ingest multiple data points for the same session at once."""
        self._assert_running()
        ts = time.time()
        for metric_type, value in batch:
            self._manager.record(
                session_id, metric_type, value,
                timestamp=ts, tags=tags
            )
            self._stats.record_data_point()

    # ── Request processing ────────────────────────────────────────────────────

    def create_request(
        self,
        session_id:   str,
        metric_types: Tuple[MetricType, ...],
        *,
        window_size:    WindowSize            = WindowSize.FIVE_MINUTES,
        from_timestamp: Optional[float]       = None,
        to_timestamp:   Optional[float]       = None,
    ) -> MetricsRequest:
        self._assert_running()
        return self._factory.create_request(
            session_id,
            metric_types,
            window_size=window_size,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def process_request(self, request: MetricsRequest) -> MetricsResponse:
        """
        Process a structured MetricsRequest and return a MetricsResponse.

        Validates the request, computes metrics, and records statistics.
        """
        self._assert_running()
        t0 = time.time()
        self._stats.record_request()

        # Validate
        result = self._validator.validate_request(request)
        if not result.is_valid:
            raise MetricsValidationError(
                "Request validation failed.",
                errors=tuple(result.errors),
            )

        errors: List[str] = []
        metrics: Dict[str, float] = {}

        for mt in request.metric_types:
            try:
                val = self._manager.compute_metric(
                    request.session_id, mt, request.window_size
                )
                metrics[mt.value] = val
            except Exception as exc:
                errors.append(f"{mt.value}: {exc}")
                self._stats.record_calculation_failure()
                self._emit(
                    make_calculation_failed(request.session_id, reason=str(exc))
                )

        duration_ms = (time.time() - t0) * 1_000.0
        self._stats.record_calculation(duration_ms)
        self._emit(make_metrics_calculated(request.session_id))

        response = self._factory.create_response(
            request,
            metrics,
            calculation_duration_ms=duration_ms,
            errors=tuple(errors) if errors else None,
        )
        self._history.append_response(response)
        return response

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(
        self,
        session_id:  str,
        portfolio_id: str,
        *,
        strategy_id:    Optional[str]         = None,
        gateway_id:     Optional[str]         = None,
        metric_types:   Optional[List[MetricType]] = None,
        windows:        Optional[List[WindowSize]]  = None,
    ) -> MetricsSnapshot:
        """
        Compute and return an immutable MetricsSnapshot.

        Computes session-wide aggregates and window-level aggregates.
        """
        self._assert_running()
        t0 = time.time()

        context = make_metrics_context(
            session_id=session_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            gateway_id=gateway_id,
        )

        mt_list = metric_types or list(MetricType)

        # Session-wide metrics
        metrics = self._manager.compute_all_session(session_id, mt_list)

        # Window metrics
        t1 = time.time()
        window_metrics = self._manager.compute_window_metrics(
            session_id, mt_list, windows
        )
        agg_duration_ms = (time.time() - t1) * 1_000.0
        self._stats.record_aggregation(agg_duration_ms)

        # Point counts
        point_counts = self._manager.compute_point_counts(session_id, mt_list)

        snap = self._factory.create_snapshot(
            context,
            metrics,
            window_metrics=window_metrics,
            point_counts=point_counts,
        )

        duration_ms = (time.time() - t0) * 1_000.0
        self._stats.record_calculation(duration_ms)
        self._emit(make_metrics_aggregated(session_id))
        return snap

    def publish(self, snapshot: MetricsSnapshot) -> None:
        """
        Register a snapshot in the registry and history.

        Emits METRICS_PUBLISHED event.
        """
        self._assert_running()
        self._registry.store(snapshot)
        self._history.append_snapshot(snapshot)
        self._stats.record_published()
        self._emit(make_metrics_published(snapshot.session_id))

    def snapshot_and_publish(
        self,
        session_id:  str,
        portfolio_id: str,
        *,
        strategy_id: Optional[str]             = None,
        gateway_id:  Optional[str]             = None,
        metric_types: Optional[List[MetricType]] = None,
        windows:      Optional[List[WindowSize]]  = None,
    ) -> MetricsSnapshot:
        """Compute a snapshot and immediately publish it."""
        snap = self.snapshot(
            session_id, portfolio_id,
            strategy_id=strategy_id,
            gateway_id=gateway_id,
            metric_types=metric_types,
            windows=windows,
        )
        self.publish(snap)
        return snap

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_latest_snapshot(self, session_id: str) -> MetricsSnapshot:
        self._assert_running()
        return self._registry.get_latest(session_id)  # type: ignore

    def find_latest_snapshot(self, session_id: str) -> Optional[MetricsSnapshot]:
        self._assert_running()
        return self._registry.find_latest(session_id)  # type: ignore

    def raw_values(
        self,
        session_id:  str,
        metric_type: MetricType,
        *,
        limit: Optional[int] = None,
    ) -> List[float]:
        self._assert_running()
        return self._manager.raw_values(
            session_id, metric_type, limit=limit
        )

    # ── Observability ─────────────────────────────────────────────────────────

    def statistics(self) -> MetricsStatistics:
        return self._stats.copy()

    def history(self) -> MetricsHistory:
        return self._history

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_event_listener(
        self, listener: Callable[[MetricsEvent], None]
    ) -> None:
        with self._listeners_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_event_listener(
        self, listener: Callable[[MetricsEvent], None]
    ) -> None:
        with self._listeners_lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass
