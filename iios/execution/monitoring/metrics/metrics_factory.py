"""iios/execution/monitoring/metrics/metrics_factory.py
==================================================
MetricsFactory — LifecycleAwareMixin factory for metrics framework objects.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import FACTORY_SYSTEM_ID, VERSION, MetricType, WindowSize
from .exceptions import MetricsEngineNotRunningError
from .metrics_context import MetricsContext
from .metrics_request import MetricsRequest, make_metrics_request
from .metrics_response import MetricsResponse, make_metrics_response
from .metrics_snapshot import MetricsSnapshot, make_metrics_snapshot

_log = get_logger(__name__)


class MetricsFactory(LifecycleAwareMixin):
    """
    Lifecycle-aware factory for MetricsSnapshot, MetricsRequest,
    and MetricsResponse objects.
    """

    def __init__(self) -> None:
        super().__init__()
        self._version_counters: Dict[str, int] = {}

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("MetricsFactory starting.", system_id=FACTORY_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("MetricsFactory stopping.", system_id=FACTORY_SYSTEM_ID)

    def _assert_running(self) -> None:
        state = self.lifecycle_state()
        if state not in (EngineState.RUNNING, "running"):
            raise MetricsEngineNotRunningError()

    # ── Snapshot factory ──────────────────────────────────────────────────────

    def _next_version(self, session_id: str) -> int:
        v = self._version_counters.get(session_id, 0) + 1
        self._version_counters[session_id] = v
        return v

    def create_snapshot(
        self,
        context:        MetricsContext,
        metrics:        Dict[str, float],
        *,
        window_metrics: Optional[Dict[str, Dict[str, float]]] = None,
        point_counts:   Optional[Dict[str, int]]              = None,
    ) -> MetricsSnapshot:
        self._assert_running()
        version = self._next_version(context.session_id)
        snapshot = make_metrics_snapshot(
            session_id=context.session_id,
            portfolio_id=context.portfolio_id,
            metrics=metrics,
            snapshot_version=version,
            window_metrics=window_metrics,
            point_counts=point_counts,
            strategy_id=context.strategy_id,
            gateway_id=context.gateway_id,
        )
        _log.info(
            "MetricsSnapshot created.",
            session_id=context.session_id,
            version=version,
            metric_count=len(metrics),
        )
        return snapshot

    # ── Request factory ───────────────────────────────────────────────────────

    def create_request(
        self,
        session_id:   str,
        metric_types: Tuple[MetricType, ...],
        *,
        window_size:    WindowSize            = WindowSize.FIVE_MINUTES,
        from_timestamp: Optional[float]       = None,
        to_timestamp:   Optional[float]       = None,
        metadata:       Optional[Dict[str, Any]] = None,
    ) -> MetricsRequest:
        self._assert_running()
        return make_metrics_request(
            session_id=session_id,
            metric_types=metric_types,
            window_size=window_size,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            metadata=metadata,
        )

    # ── Response factory ──────────────────────────────────────────────────────

    def create_response(
        self,
        request:         MetricsRequest,
        metrics:         Dict[str, float],
        *,
        window_metrics:          Optional[Dict[str, Dict[str, float]]] = None,
        calculation_duration_ms: float                                  = 0.0,
        errors:                  Optional[Tuple[str, ...]]              = None,
    ) -> MetricsResponse:
        self._assert_running()
        return make_metrics_response(
            request_id=request.request_id,
            session_id=request.session_id,
            metrics=metrics,
            window_metrics=window_metrics,
            calculation_duration_ms=calculation_duration_ms,
            errors=errors,
        )
