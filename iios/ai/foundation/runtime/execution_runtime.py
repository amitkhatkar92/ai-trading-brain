"""
execution_runtime.py -- iios.ai.foundation.runtime
===================================================
ExecutionRuntime -- lifecycle-aware AI execution runtime.
ExecutionCoordinator -- per-request coordinator.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import time
import threading
from typing import Any, Dict, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from ..lifecycle.ai_foundation_lifecycle import AILifecycleAwareMixin
from ..lifecycle.constants               import VERSION
from ..events.event_bus                  import AIEventBus
from ..metrics.metrics_models            import RuntimeMetrics
from ..provider.provider_manager         import AIProviderRuntime
from ..request.request_models            import AIResponse, AIExecutionRequest
from ..retry.retry_models                import RetryPolicy, RetryManager, ExponentialBackoffStrategy
from ..timeout.timeout_models            import TimeoutPolicy

from .execution_context  import ExecutionContext
from .execution_pipeline import ExecutionPipeline

_log = get_logger(__name__)

RUNTIME_SYSTEM_ID = "iios:ai:foundation:runtime"


class ExecutionCoordinator:
    """
    Per-request coordinator.

    Wraps :class:`ExecutionPipeline` with retry and timeout policy.
    One instance is created per request by :class:`ExecutionRuntime`.

    Usage::

        coordinator = ExecutionCoordinator(pipeline, retry_policy, timeout_policy)
        response, ctx = coordinator.execute(exec_request)
    """

    def __init__(
        self,
        pipeline:       ExecutionPipeline,
        retry_policy:   RetryPolicy    = RetryPolicy(),
        timeout_policy: TimeoutPolicy  = TimeoutPolicy(),
    ) -> None:
        self._pipeline       = pipeline
        self._retry_policy   = retry_policy
        self._timeout_policy = timeout_policy
        self._retry_manager  = RetryManager(retry_policy, ExponentialBackoffStrategy())

    def execute(
        self,
        exec_request: AIExecutionRequest,
    ) -> Tuple[AIResponse, ExecutionContext]:
        """
        Execute with retry.  Returns (response, last_context).
        Never raises.
        """
        last_ctx: Optional[ExecutionContext] = None

        def _attempt() -> Tuple[AIResponse, ExecutionContext]:
            resp, ctx = self._pipeline.run(exec_request)
            last_ctx_ref[0] = ctx
            if not resp.succeeded:
                raise RuntimeError(resp.error_message or "execution failed")
            return resp, ctx

        last_ctx_ref: list = [None]
        result, outcome = self._retry_manager.execute(
            exec_request.request.metadata.request_id,
            _attempt,
        )
        if outcome.succeeded and result is not None:
            return result
        # Return the last context even on failure
        ctx = last_ctx_ref[0]
        if ctx is None:
            ctx = ExecutionContext(
                request_id = exec_request.request.metadata.request_id,
                session_id = exec_request.request.metadata.session_id,
            )
        response = AIResponse.failure(
            request_id  = ctx.request_id,
            session_id  = ctx.session_id,
            error       = outcome.last_error or "all retry attempts failed",
            latency_ms  = ctx.elapsed_ms(),
            provider_id = getattr(ctx, "provider_id", ""),
            model_id    = getattr(ctx, "model_id", ""),
        )
        return response, ctx


class ExecutionRuntime(AILifecycleAwareMixin):
    """
    Lifecycle-aware AI execution runtime.

    Composes: pipeline + provider runtime + retry + timeout + metrics.

    Usage::

        runtime = ExecutionRuntime()
        runtime.initialize()
        runtime.start()
        response, ctx = runtime.execute(exec_request)
        runtime.stop()
    """

    SYSTEM_ID: str = RUNTIME_SYSTEM_ID
    VERSION:   str = VERSION

    def __init__(
        self,
        provider_runtime: Optional[AIProviderRuntime] = None,
        event_bus:        Optional[AIEventBus]         = None,
        retry_policy:     RetryPolicy                  = RetryPolicy(),
        timeout_policy:   TimeoutPolicy                = TimeoutPolicy(),
    ) -> None:
        self._provider_runtime = provider_runtime
        self._event_bus        = event_bus
        self._retry_policy     = retry_policy
        self._timeout_policy   = timeout_policy
        self._metrics          = RuntimeMetrics()
        self._pipeline:     Optional[ExecutionPipeline]     = None
        self._coordinator:  Optional[ExecutionCoordinator]  = None
        self._started_at:   Optional[float]                 = None
        self._lock          = threading.Lock()

    # ---- lifecycle hooks --------------------------------------------------

    def _on_initialize(self) -> None:
        self._pipeline = ExecutionPipeline(
            provider_runtime = self._provider_runtime,
            runtime_metrics  = self._metrics,
            event_bus        = self._event_bus,
        )
        self._coordinator = ExecutionCoordinator(
            pipeline       = self._pipeline,
            retry_policy   = self._retry_policy,
            timeout_policy = self._timeout_policy,
        )
        _log.info("ExecutionRuntime: initialized")

    def _on_start(self) -> None:
        self._started_at = time.time()
        _log.info("ExecutionRuntime: started")

    def _on_stop(self) -> None:
        _log.info(
            f"ExecutionRuntime: stopped "
            f"(total_requests={self._metrics.to_dict().get('total_requests', 0)})"
        )

    # ---- public API -------------------------------------------------------

    def execute(
        self,
        exec_request: AIExecutionRequest,
    ) -> Tuple[AIResponse, ExecutionContext]:
        """
        Execute an AI request through the full runtime pipeline.

        Returns (AIResponse, ExecutionContext). Never raises.
        """
        if self._coordinator is None:
            raise RuntimeError(
                "ExecutionRuntime.execute() called before initialize()/start()"
            )
        return self._coordinator.execute(exec_request)

    @property
    def metrics(self) -> RuntimeMetrics:
        return self._metrics

    @property
    def pipeline(self) -> Optional[ExecutionPipeline]:
        return self._pipeline

    def status(self) -> Dict[str, Any]:
        m = self._metrics.to_dict()
        return {
            "system_id":    self.SYSTEM_ID,
            "state":        self.lifecycle_state.value,
            "is_running":   self.is_ai_running,
            "uptime_s":     (time.time() - self._started_at) if self._started_at else 0.0,
            "stage_names":  self._pipeline.stage_names() if self._pipeline else [],
            "metrics":      m,
        }

    def __repr__(self) -> str:
        return (
            f"<ExecutionRuntime "
            f"state={self.lifecycle_state.value!r} "
            f"requests={self._metrics.to_dict().get('total_requests', 0)}>"
        )
