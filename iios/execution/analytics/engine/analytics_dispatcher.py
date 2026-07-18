"""
iios/execution/analytics/engine/analytics_dispatcher.py
=======================================================
AnalyticsDispatcher — dispatches analytics pipelines to downstream
analytics frameworks.

Delegation targets:
  - Performance Analytics Framework (M3) — pending; stub interface
  - Predictive Intelligence Framework (M4) — pending; stub interface

The dispatcher performs NO calculations.
It only delegates pipeline execution to the registered frameworks.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import DISPATCHER_SYSTEM_ID, PipelineStage, PipelineStatus
from .exceptions import AnalyticsDispatchError, AnalyticsEngineNotRunningError
from .analytics_pipeline import AnalyticsPipeline

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class AnalyticsDispatcher(LifecycleAwareMixin):
    """
    Dispatches analytics pipelines to downstream frameworks.

    Both frameworks are optional at runtime.  When a framework is not
    registered, delegation is skipped and logged at DEBUG level.

    Thread-safe.  Must be started before use.
    """

    def __init__(self) -> None:
        super().__init__()
        self._lock                       = threading.RLock()
        self._dispatch_count:   int      = 0
        self._performance_framework: Optional[Any] = None
        self._predictive_framework:  Optional[Any] = None

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("AnalyticsDispatcher started.", system_id=DISPATCHER_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info(
            "AnalyticsDispatcher stopped.",
            system_id      = DISPATCHER_SYSTEM_ID,
            dispatch_count = self._dispatch_count,
        )

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise AnalyticsEngineNotRunningError()

    # ── Framework registration ────────────────────────────────────────────────

    def register_performance_framework(self, framework: Any) -> None:
        """Register the M3 Performance Analytics Framework."""
        with self._lock:
            self._performance_framework = framework
        _log.info("Performance Analytics Framework (M3) registered.")

    def register_predictive_framework(self, framework: Any) -> None:
        """Register the M4 Predictive Intelligence Framework."""
        with self._lock:
            self._predictive_framework = framework
        _log.info("Predictive Intelligence Framework (M4) registered.")

    def deregister_performance_framework(self) -> None:
        """Deregister the M3 Performance Analytics Framework."""
        with self._lock:
            self._performance_framework = None

    def deregister_predictive_framework(self) -> None:
        """Deregister the M4 Predictive Intelligence Framework."""
        with self._lock:
            self._predictive_framework = None

    # ── Dispatch API ──────────────────────────────────────────────────────────

    def dispatch(self, pipeline: AnalyticsPipeline) -> None:
        """
        Dispatch a pipeline to all registered downstream frameworks.

        Mutates pipeline in-place with results and timing.
        Raises AnalyticsDispatchError on unrecoverable failure.
        """
        self._assert_running()
        pipeline.start()
        try:
            if pipeline.has_performance:
                self._dispatch_to_performance(pipeline)
            if pipeline.has_predictive:
                self._dispatch_to_predictive(pipeline)
            pipeline.complete()
            with self._lock:
                self._dispatch_count += 1
            _log.debug(
                "Pipeline dispatched successfully.",
                pipeline_id = pipeline.pipeline_id,
                request_id  = pipeline.request_id,
                session_id  = pipeline.session_id,
            )
        except AnalyticsDispatchError:
            raise
        except Exception as exc:
            pipeline.fail(str(exc))
            raise AnalyticsDispatchError(
                f"Pipeline dispatch failed: {exc}",
                pipeline_id=pipeline.pipeline_id,
            ) from exc

    # ── Private delegation ────────────────────────────────────────────────────

    def _dispatch_to_performance(self, pipeline: AnalyticsPipeline) -> None:
        """
        Delegate to M3 Performance Analytics Framework.

        When M3 is available its published interface is called here.
        Until then, delegation is deferred and noted in debug logs.
        """
        pipeline.advance_to(PipelineStage.DISPATCHING)
        with self._lock:
            framework = self._performance_framework
        if framework is not None:
            try:
                result = framework.process(pipeline.request_id)
                pipeline.performance_result = result
            except Exception as exc:
                _log.warning(
                    "Performance framework delegation failed; skipping.",
                    pipeline_id = pipeline.pipeline_id,
                    error       = str(exc),
                )
        else:
            _log.debug(
                "Performance Analytics Framework (M3) not yet available; "
                "delegation deferred.",
                pipeline_id = pipeline.pipeline_id,
            )
        pipeline.advance_to(PipelineStage.PROCESSING)

    def _dispatch_to_predictive(self, pipeline: AnalyticsPipeline) -> None:
        """
        Delegate to M4 Predictive Intelligence Framework.

        When M4 is available its published interface is called here.
        Until then, delegation is deferred and noted in debug logs.
        """
        pipeline.advance_to(PipelineStage.DISPATCHING)
        with self._lock:
            framework = self._predictive_framework
        if framework is not None:
            try:
                result = framework.predict(pipeline.request_id)
                pipeline.predictive_result = result
            except Exception as exc:
                _log.warning(
                    "Predictive framework delegation failed; skipping.",
                    pipeline_id = pipeline.pipeline_id,
                    error       = str(exc),
                )
        else:
            _log.debug(
                "Predictive Intelligence Framework (M4) not yet available; "
                "delegation deferred.",
                pipeline_id = pipeline.pipeline_id,
            )
        pipeline.advance_to(PipelineStage.PROCESSING)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def dispatch_count(self) -> int:
        with self._lock:
            return self._dispatch_count

    @property
    def has_performance_framework(self) -> bool:
        with self._lock:
            return self._performance_framework is not None

    @property
    def has_predictive_framework(self) -> bool:
        with self._lock:
            return self._predictive_framework is not None
