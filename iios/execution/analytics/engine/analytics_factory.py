"""
iios/execution/analytics/engine/analytics_factory.py
====================================================
EngineAnalyticsFactory — lifecycle-aware factory for creating analytics
engine objects (requests, contexts, pipelines, snapshots).

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_SYSTEM,
    FACTORY_SYSTEM_ID,
    AnalyticsRequestType,
    EngineAnalyticsState,
)
from .exceptions import AnalyticsEngineNotRunningError
from .analytics_context import EngineAnalyticsContext, make_engine_analytics_context
from .analytics_pipeline import AnalyticsPipeline, make_analytics_pipeline
from .analytics_request import AnalyticsRequest, make_analytics_request
from .analytics_response import (
    AnalyticsResponse,
    AnalyticsSnapshot,
    ResponseStatus,
    make_analytics_response,
    make_analytics_snapshot,
)

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class EngineAnalyticsFactory(LifecycleAwareMixin):
    """
    Factory for analytics engine objects.

    Creates requests, contexts, pipelines, snapshots, and responses.
    Must be started before use.
    """

    def _on_start(self) -> None:
        _log.info("EngineAnalyticsFactory started.", system_id=FACTORY_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info("EngineAnalyticsFactory stopped.", system_id=FACTORY_SYSTEM_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise AnalyticsEngineNotRunningError()

    # ── Request factory ───────────────────────────────────────────────────────

    def create_request(
        self,
        execution_session_id: str,
        *,
        request_type: AnalyticsRequestType      = AnalyticsRequestType.ON_DEMAND,
        requester:    str                       = ACTOR_SYSTEM,
        priority:     int                       = 5,
        reason:       str                       = "",
        tags:         Tuple[str, ...]            = (),
        metadata:     Optional[Dict[str, Any]]  = None,
    ) -> AnalyticsRequest:
        self._assert_running()
        return make_analytics_request(
            execution_session_id,
            request_type = request_type,
            requester    = requester,
            priority     = priority,
            reason       = reason,
            tags         = tags,
            metadata     = metadata,
        )

    # ── Context factory ───────────────────────────────────────────────────────

    def create_context(
        self,
        request_id:           str,
        execution_session_id: str,
        *,
        monitoring_snapshot: Optional[Any]           = None,
        recovery_snapshot:   Optional[Any]           = None,
        gateway_snapshot:    Optional[Any]           = None,
        risk_snapshot:       Optional[Any]           = None,
        execution_context:   Optional[Any]           = None,
        requester:           str                     = ACTOR_SYSTEM,
        priority:            int                     = 5,
        metadata:            Optional[Dict[str, Any]] = None,
    ) -> EngineAnalyticsContext:
        self._assert_running()
        return make_engine_analytics_context(
            request_id,
            execution_session_id,
            monitoring_snapshot = monitoring_snapshot,
            recovery_snapshot   = recovery_snapshot,
            gateway_snapshot    = gateway_snapshot,
            risk_snapshot       = risk_snapshot,
            execution_context   = execution_context,
            requester           = requester,
            priority            = priority,
            metadata            = metadata,
        )

    # ── Pipeline factory ──────────────────────────────────────────────────────

    def create_pipeline(
        self,
        request_id:      str,
        session_id:      str,
        *,
        has_performance: bool                    = True,
        has_predictive:  bool                    = False,
        metadata:        Optional[Dict[str, Any]] = None,
    ) -> AnalyticsPipeline:
        self._assert_running()
        return make_analytics_pipeline(
            request_id,
            session_id,
            has_performance = has_performance,
            has_predictive  = has_predictive,
            metadata        = metadata,
        )

    # ── Snapshot factory ──────────────────────────────────────────────────────

    def create_snapshot(
        self,
        engine_state: EngineAnalyticsState,
        *,
        request_id:  str                      = "",
        session_id:  str                      = "",
        pipeline_id: str                      = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> AnalyticsSnapshot:
        self._assert_running()
        return make_analytics_snapshot(
            engine_state,
            request_id  = request_id,
            session_id  = session_id,
            pipeline_id = pipeline_id,
            metadata    = metadata,
        )

    # ── Response factory ──────────────────────────────────────────────────────

    def create_response(
        self,
        request_id: str,
        status:     ResponseStatus,
        *,
        session_id:    str                         = "",
        pipeline_id:   str                         = "",
        snapshot:      Optional[AnalyticsSnapshot] = None,
        error_message: str                         = "",
        processing_ms: float                       = 0.0,
        collection_ms: float                       = 0.0,
        dispatch_ms:   float                       = 0.0,
        metadata:      Optional[Dict[str, Any]]    = None,
    ) -> AnalyticsResponse:
        self._assert_running()
        return make_analytics_response(
            request_id,
            status,
            session_id    = session_id,
            pipeline_id   = pipeline_id,
            snapshot      = snapshot,
            error_message = error_message,
            processing_ms = processing_ms,
            collection_ms = collection_ms,
            dispatch_ms   = dispatch_ms,
            metadata      = metadata,
        )
