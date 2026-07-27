"""
stages/ -- iios.ai.foundation.pipeline.stages
==============================================
The six standard pipeline stages.

Stage order (per architecture specification):
  1. ValidationStage          -- request schema + budget validation
  2. PolicyEvaluationStage    -- policy checks (safety, cost, retry)
  3. ProviderSelectionStage   -- route to best available provider
  4. ExecutionStage           -- send to provider and receive response
  5. ResultValidationStage    -- validate provider response
  6. ResponseStage            -- assemble final AIResponse

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from iios.common.logging.logging_manager import get_logger

from ..pipeline_stage   import PipelineStage
from ..pipeline_context import PipelineContext
from ...exceptions      import (
    AIPipelineStageError,
    AIRequestValidationError,
    AIProviderNotAvailableError,
    AIResponseValidationError,
    AIPolicyViolationError,
)
from ...request.request_models import AIResponse

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Stage 1 -- Validation
# ---------------------------------------------------------------------------

class ValidationStage(PipelineStage):
    """
    Validates the incoming :class:`AIExecutionRequest`.

    Checks:
    * Request has messages.
    * max_tokens is positive.
    * timeout_s is positive.
    """

    @property
    def name(self) -> str:
        return "validation"

    def _run(self, ctx: PipelineContext) -> None:
        req = ctx.execution_request.request
        if not req.messages:
            raise AIPipelineStageError(self.name, "Request has no messages.")
        if req.max_tokens <= 0:
            raise AIPipelineStageError(self.name, f"max_tokens must be positive; got {req.max_tokens}.")
        if req.metadata.timeout_s <= 0:
            raise AIPipelineStageError(self.name, f"timeout_s must be positive; got {req.metadata.timeout_s}.")
        _log.debug(f"ValidationStage: request_id={req.request_id!r} PASS")


# ---------------------------------------------------------------------------
# Stage 2 -- Policy Evaluation
# ---------------------------------------------------------------------------

class PolicyEvaluationStage(PipelineStage):
    """
    Evaluates configured policies against the request.

    In the skeleton implementation all requests pass.
    Concrete policies are injected via :attr:`policies`.

    A policy is a callable: ``(PipelineContext) -> None``
    It raises :class:`AIPolicyViolationError` to block the request.
    """

    def __init__(self) -> None:
        self._policies: list = []

    @property
    def name(self) -> str:
        return "policy_evaluation"

    def add_policy(self, name: str, fn) -> None:
        """Register a policy function ``fn(ctx: PipelineContext) -> None``."""
        self._policies.append((name, fn))

    def _run(self, ctx: PipelineContext) -> None:
        for policy_name, fn in self._policies:
            try:
                fn(ctx)
                ctx.policy_decisions.append(f"{policy_name}:PASS")
            except AIPolicyViolationError as exc:
                ctx.policy_decisions.append(f"{policy_name}:BLOCK")
                raise AIPipelineStageError(self.name, str(exc))
        _log.debug(
            f"PolicyEvaluationStage: request_id={ctx.request_id!r} "
            f"policies={len(self._policies)} all PASS"
        )


# ---------------------------------------------------------------------------
# Stage 3 -- Provider Selection
# ---------------------------------------------------------------------------

class ProviderSelectionStage(PipelineStage):
    """
    Selects the best available provider for the request.

    Uses ``provider_registry`` from the pipeline context data
    (injected by :class:`ExecutionPipeline` at run time) or falls
    back to ``provider_hint`` from the request.
    """

    @property
    def name(self) -> str:
        return "provider_selection"

    def _run(self, ctx: PipelineContext) -> None:
        req  = ctx.execution_request.request
        hint = req.provider_hint

        # Attempt to resolve via registry stored in context data
        registry = ctx.get("provider_registry")
        if registry is not None:
            try:
                from ...adapters.constants import AICapability
                cap = AICapability(req.capability)
                provider = registry.first_for(cap)
                ctx.provider_id = provider.provider_id
                ctx.model_id    = provider.model_id
                ctx.set("selected_provider", provider)
                _log.debug(
                    f"ProviderSelectionStage: selected "
                    f"provider={ctx.provider_id!r} model={ctx.model_id!r}"
                )
                return
            except Exception:
                pass  # fall through to hint or stub

        if hint:
            ctx.provider_id = hint
            _log.debug(f"ProviderSelectionStage: using hint provider={hint!r}")
        else:
            # No provider available -- mark for skeleton (no-op in testing)
            ctx.provider_id = "stub"
            ctx.model_id    = "stub-model"
            _log.debug("ProviderSelectionStage: no registry -- using stub provider")


# ---------------------------------------------------------------------------
# Stage 4 -- Execution
# ---------------------------------------------------------------------------

class ExecutionStage(PipelineStage):
    """
    Submits the request to the selected provider.

    If ``selected_provider`` was set in the context by Stage 3, calls
    ``provider.complete()``.  Otherwise stores a stub response so the
    pipeline can complete end-to-end during testing.
    """

    @property
    def name(self) -> str:
        return "execution"

    def _run(self, ctx: PipelineContext) -> None:
        provider = ctx.get("selected_provider")
        req      = ctx.execution_request.request

        if provider is not None:
            from ...adapters.ai_provider import AIProviderRequest
            from ...adapters.constants   import AICapability
            p_req = AIProviderRequest.create(
                messages    = list(req.messages),
                capability  = AICapability(req.capability),
                max_tokens  = req.max_tokens,
                temperature = req.temperature,
                timeout_s   = req.metadata.timeout_s,
            )
            p_resp = provider.complete(p_req)
            ctx.set("provider_response", p_resp)
            _log.debug(
                f"ExecutionStage: complete provider={provider.provider_id!r} "
                f"tokens={p_resp.total_tokens}"
            )
        else:
            # Stub -- no provider wired (used in unit tests / skeleton)
            ctx.set("stub_execution", True)
            _log.debug("ExecutionStage: stub execution (no provider wired)")


# ---------------------------------------------------------------------------
# Stage 5 -- Result Validation
# ---------------------------------------------------------------------------

class ResultValidationStage(PipelineStage):
    """
    Validates the provider response before finalising.

    Checks:
    * Response was received (or stub flag set).
    * Content is not empty (when a real provider is used).
    """

    @property
    def name(self) -> str:
        return "result_validation"

    @property
    def is_required(self) -> bool:
        return False   # non-fatal in skeleton

    def _run(self, ctx: PipelineContext) -> None:
        p_resp = ctx.get("provider_response")
        is_stub = ctx.get("stub_execution", False)

        if not is_stub and p_resp is not None:
            if not p_resp.content.strip():
                raise AIPipelineStageError(self.name, "Provider returned empty content.")
        _log.debug(f"ResultValidationStage: request_id={ctx.request_id!r} PASS")


# ---------------------------------------------------------------------------
# Stage 6 -- Response
# ---------------------------------------------------------------------------

class ResponseStage(PipelineStage):
    """
    Assembles the final :class:`AIResponse` from pipeline results
    and stores it in ``ctx.response``.
    """

    @property
    def name(self) -> str:
        return "response"

    def _run(self, ctx: PipelineContext) -> None:
        p_resp    = ctx.get("provider_response")
        is_stub   = ctx.get("stub_execution", False)
        latency_ms = ctx.elapsed_ms
        req       = ctx.execution_request.request

        if p_resp is not None and not is_stub:
            ctx.response = AIResponse.success(
                request_id    = req.request_id,
                session_id    = req.session_id,
                content       = p_resp.content,
                provider_id   = p_resp.provider_id,
                model_id      = p_resp.model_id,
                finish_reason = p_resp.finish_reason,
                prompt_tokens = p_resp.prompt_tokens,
                output_tokens = p_resp.output_tokens,
                latency_ms    = latency_ms,
            )
        else:
            # Stub response for skeleton / tests
            ctx.response = AIResponse.success(
                request_id    = req.request_id,
                session_id    = req.session_id,
                content       = "[stub response]",
                provider_id   = ctx.provider_id or "stub",
                model_id      = ctx.model_id    or "stub-model",
                finish_reason = "stop",
                prompt_tokens = 0,
                output_tokens = 0,
                latency_ms    = latency_ms,
            )
        _log.debug(
            f"ResponseStage: assembled response "
            f"request_id={ctx.request_id!r} latency={latency_ms:.1f}ms"
        )
