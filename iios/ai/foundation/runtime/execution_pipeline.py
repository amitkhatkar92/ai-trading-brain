"""
execution_pipeline.py -- iios.ai.foundation.runtime
====================================================
ExecutionPipeline -- 8-stage AI execution pipeline for the runtime.

Stages
------
1. Request           -- build ExecutionContext
2. Validation        -- validate request structure
3. Policy Evaluation -- evaluate policies (extensible)
4. Provider Resolution -- select provider
5. Execution         -- call provider (or stub)
6. Response Validation -- validate provider output
7. Metrics           -- record metrics
8. Response          -- assemble final result

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import abc
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from ..events.ai_events import (
    ExecutionStartedEvent, ExecutionCompletedEvent,
    ExecutionFailedEvent, ProviderSelectedEvent,
)
from ..events.event_bus       import AIEventBus
from ..metrics.metrics_models import RuntimeMetrics, ExecutionMetrics
from ..provider.provider_constants import ProviderCapabilityType
from ..provider.provider_manager   import AIProviderRuntime
from ..request.request_models      import AIRequest, AIResponse, AIExecutionRequest

from .execution_context import ExecutionContext

_log = get_logger(__name__)

SYSTEM_ID = "iios:ai:foundation:runtime:pipeline"


# ---------------------------------------------------------------------------
# Abstract pipeline stage
# ---------------------------------------------------------------------------

class RuntimePipelineStage(abc.ABC):
    """
    Abstract base for all runtime pipeline stages.

    Each stage receives the :class:`ExecutionContext` and may:
    * read / write context attributes
    * set ``context.aborted = True`` to halt the pipeline
    * raise an exception (which the coordinator catches)
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique stage name used in records and logs."""

    @abc.abstractmethod
    def execute(self, context: ExecutionContext) -> None:
        """Execute the stage.  Modify ``context`` in place."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} stage={self.name!r}>"


# ---------------------------------------------------------------------------
# Concrete pipeline stages
# ---------------------------------------------------------------------------

class RequestStage(RuntimePipelineStage):
    """Stage 1 -- validate and prepare the execution context."""

    name = "request"

    def execute(self, context: ExecutionContext) -> None:
        req = context.get("exec_request")
        if req is None:
            context.abort("no exec_request in context")
            return
        if not isinstance(req, AIExecutionRequest):
            context.abort(f"exec_request must be AIExecutionRequest, got {type(req).__name__}")
            return
        context.set("ai_request", req.request)


class ValidationStage(RuntimePipelineStage):
    """Stage 2 -- validate the AIRequest structure."""

    name = "validation"

    def execute(self, context: ExecutionContext) -> None:
        req = context.get("ai_request")
        if req is None:
            context.abort("ai_request missing after request stage")
            return
        if not req.messages:
            context.abort("request has no messages")
            return
        for msg in req.messages:
            if "role" not in msg or "content" not in msg:
                context.abort("message missing role or content")
                return


class PolicyEvaluationStage(RuntimePipelineStage):
    """
    Stage 3 -- evaluate request against registered policies.

    Policy evaluators are callables: (ExecutionContext) -> Optional[str].
    A non-None return value is treated as a policy violation reason
    and aborts the pipeline.
    """

    name = "policy_evaluation"

    def __init__(
        self,
        policies: Optional[List[Callable[[ExecutionContext], Optional[str]]]] = None,
    ) -> None:
        self._policies = policies or []

    def add_policy(self, policy: Callable[[ExecutionContext], Optional[str]]) -> None:
        self._policies.append(policy)

    def execute(self, context: ExecutionContext) -> None:
        for policy_fn in self._policies:
            try:
                violation = policy_fn(context)
                if violation:
                    context.abort(f"policy_violation: {violation}")
                    return
            except Exception as exc:
                _log.warning(f"PolicyEvaluationStage: policy error {exc}")


class ProviderResolutionStage(RuntimePipelineStage):
    """Stage 4 -- select provider for the request."""

    name = "provider_resolution"

    def __init__(self, provider_runtime: Optional[AIProviderRuntime] = None) -> None:
        self._runtime = provider_runtime

    def execute(self, context: ExecutionContext) -> None:
        req = context.get("ai_request")
        if req is None:
            context.abort("no ai_request for provider resolution")
            return

        # Use hint from exec_request policy_overrides if provided
        exec_req: AIExecutionRequest = context.get("exec_request")
        preferred = (exec_req.policy_overrides or {}).get("preferred_provider_id", "") if exec_req else ""
        if preferred:
            context.provider_id = preferred
            return

        if self._runtime and self._runtime.is_ai_running:
            capability_str = req.metadata.capability
            try:
                cap = ProviderCapabilityType(capability_str)
                ext = self._runtime.select_provider(cap)
                if ext:
                    context.provider_id = ext.provider_id
                    context.model_id    = ext.capabilities.model_id
                    return
            except (ValueError, Exception):
                pass

        # No provider resolved -- stub mode (tests / dry runs)
        context.provider_id = "stub"
        context.model_id    = "stub-model"


class ExecutionStage(RuntimePipelineStage):
    """
    Stage 5 -- call the provider.

    If a real provider is available via the runtime, it is called.
    Otherwise a stub response is returned (for tests and dry runs).
    """

    name = "execution"

    def __init__(self, provider_runtime: Optional[AIProviderRuntime] = None) -> None:
        self._runtime = provider_runtime

    def execute(self, context: ExecutionContext) -> None:
        if context.is_deadline_exceeded():
            context.abort("pipeline deadline exceeded before execution")
            return

        req: Optional[AIRequest] = context.get("ai_request")
        if req is None:
            context.abort("no ai_request for execution")
            return

        provider_id = context.provider_id

        if (
            self._runtime
            and self._runtime.is_ai_running
            and provider_id not in ("", "stub")
        ):
            ext = self._runtime.registry.get(provider_id)
            if ext:
                try:
                    raw = ext.complete(
                        messages    = list(req.messages),
                        max_tokens  = req.max_tokens,
                        temperature = req.temperature,
                        timeout_s   = req.metadata.timeout_s,
                    )
                    context.raw_response = raw
                    return
                except Exception as exc:
                    context.error = exc
                    context.abort(f"provider_error: {exc}")
                    return

        # Stub response
        context.raw_response = {
            "content":       "(stub response)",
            "finish_reason": "stop",
            "usage":         {"prompt_tokens": 10, "completion_tokens": 20},
        }


class ResponseValidationStage(RuntimePipelineStage):
    """Stage 6 -- validate provider output (non-fatal)."""

    name = "response_validation"

    def execute(self, context: ExecutionContext) -> None:
        raw = context.raw_response
        if raw is None:
            _log.warning("ResponseValidationStage: no raw_response -- aborted pipeline?")
            return
        if not isinstance(raw, dict):
            _log.warning(f"ResponseValidationStage: unexpected response type {type(raw)}")
            return
        if "content" not in raw:
            _log.warning("ResponseValidationStage: response missing 'content' key")


class MetricsStage(RuntimePipelineStage):
    """Stage 7 -- record execution metrics."""

    name = "metrics"

    def __init__(self, runtime_metrics: Optional[RuntimeMetrics] = None) -> None:
        self._metrics = runtime_metrics

    def execute(self, context: ExecutionContext) -> None:
        latency_ms = context.elapsed_ms()
        succeeded  = (not context.aborted) and (context.error is None)
        if self._metrics:
            self._metrics.record_execution(
                success    = succeeded,
                latency_ms = latency_ms,
            )
            pm = self._metrics.provider_metrics(
                context.provider_id, context.model_id
            )
            usage = context.raw_response.get("usage", {}) if context.raw_response else {}
            pm.record_request(
                success      = succeeded,
                latency_ms   = latency_ms,
                total_tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0),
            )
        context.set("execution_latency_ms", latency_ms)
        context.set("execution_succeeded",  succeeded)


class ResponseStage(RuntimePipelineStage):
    """Stage 8 -- assemble the final AIResponse."""

    name = "response"

    def execute(self, context: ExecutionContext) -> None:
        req: Optional[AIRequest] = context.get("ai_request")
        raw = context.raw_response

        if context.aborted or raw is None:
            response = AIResponse.failure(
                request_id  = context.request_id,
                session_id  = context.session_id,
                error       = context.abort_reason or "pipeline aborted",
                latency_ms  = context.elapsed_ms(),
                provider_id = context.provider_id,
                model_id    = context.model_id,
            )
        else:
            usage      = raw.get("usage", {})
            response   = AIResponse.success(
                request_id     = context.request_id,
                session_id     = context.session_id,
                content        = str(raw.get("content", "")),
                finish_reason  = str(raw.get("finish_reason", "stop")),
                prompt_tokens  = int(usage.get("prompt_tokens", 0)),
                output_tokens  = int(usage.get("completion_tokens", 0)),
                latency_ms     = context.elapsed_ms(),
                provider_id    = context.provider_id,
                model_id       = context.model_id,
            )
        context.set("ai_response", response)


# ---------------------------------------------------------------------------
# ExecutionPipeline
# ---------------------------------------------------------------------------

class ExecutionPipeline:
    """
    Stateless 8-stage AI execution pipeline.

    Stages are executed sequentially.  Any stage may abort the pipeline
    by setting ``context.aborted = True``; subsequent stages see
    ``context.aborted`` and can choose to skip or clean up.

    The pipeline itself never raises -- all errors are captured in
    the returned :class:`ExecutionContext`.

    Parameters
    ----------
    provider_runtime : Optional runtime for provider selection/execution.
    runtime_metrics :  Optional metrics aggregator.
    event_bus :        Optional event bus for lifecycle events.
    """

    def __init__(
        self,
        provider_runtime: Optional[AIProviderRuntime] = None,
        runtime_metrics:  Optional[RuntimeMetrics]    = None,
        event_bus:        Optional[AIEventBus]         = None,
    ) -> None:
        self._event_bus = event_bus
        self._stages: List[RuntimePipelineStage] = [
            RequestStage(),
            ValidationStage(),
            PolicyEvaluationStage(),
            ProviderResolutionStage(provider_runtime),
            ExecutionStage(provider_runtime),
            ResponseValidationStage(),
            MetricsStage(runtime_metrics),
            ResponseStage(),
        ]

    def run(self, exec_request: AIExecutionRequest) -> Tuple[AIResponse, ExecutionContext]:
        """
        Execute the pipeline for ``exec_request``.

        Returns
        -------
        (AIResponse, ExecutionContext)
            Always returns -- never raises.
        """
        ctx = ExecutionContext(
            request_id = exec_request.request.metadata.request_id,
            session_id = exec_request.request.metadata.session_id,
            trace_id   = exec_request.request.metadata.trace_id,
        )
        ctx.set("exec_request", exec_request)

        if self._event_bus:
            self._event_bus.publish(
                ExecutionStartedEvent.create(
                    source_id  = SYSTEM_ID,
                    request_id = ctx.request_id,
                    session_id = ctx.session_id,
                    trace_id   = ctx.trace_id,
                )
            )

        for stage in self._stages:
            rec = ctx.begin_stage(stage.name)
            try:
                stage.execute(ctx)
                rec.complete(succeeded=True)
            except Exception as exc:
                rec.complete(succeeded=False, error=str(exc))
                ctx.error = exc
                ctx.abort(f"stage_error in {stage.name}: {exc}")
                _log.error(f"ExecutionPipeline: stage {stage.name!r} raised {exc}")

            if ctx.aborted:
                break

        response: AIResponse = ctx.get("ai_response") or AIResponse.failure(
            request_id  = ctx.request_id,
            session_id  = ctx.session_id,
            error       = "pipeline produced no response",
            latency_ms  = ctx.elapsed_ms(),
            provider_id = ctx.provider_id,
            model_id    = ctx.model_id,
        )

        if self._event_bus:
            if response.succeeded:
                self._event_bus.publish(
                    ExecutionCompletedEvent.create(
                        source_id    = SYSTEM_ID,
                        request_id   = ctx.request_id,
                        session_id   = ctx.session_id,
                        provider_id  = ctx.provider_id,
                        latency_ms   = ctx.elapsed_ms(),
                        prompt_tokens  = response.prompt_tokens,
                        output_tokens  = response.output_tokens,
                        trace_id       = ctx.trace_id,
                    )
                )
            else:
                self._event_bus.publish(
                    ExecutionFailedEvent.create(
                        source_id   = SYSTEM_ID,
                        request_id  = ctx.request_id,
                        session_id  = ctx.session_id,
                        provider_id = ctx.provider_id,
                        error_code  = "EXECUTION_FAILED",
                        error_msg   = response.error or "",
                        trace_id    = ctx.trace_id,
                    )
                )

        return response, ctx

    def add_stage(self, stage: RuntimePipelineStage, position: Optional[int] = None) -> None:
        """Insert a custom stage at ``position`` (appends if None)."""
        if position is None:
            self._stages.append(stage)
        else:
            self._stages.insert(position, stage)

    def stage_names(self) -> List[str]:
        return [s.name for s in self._stages]
