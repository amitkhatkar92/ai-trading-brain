"""
portfolio_dispatcher.py — iios.portfolio.engine
================================================
Portfolio workflow dispatcher.

Routes portfolio pipelines to the appropriate framework components:
  - Portfolio Policy Framework (M3 — registered when available)
  - Portfolio Optimization Framework (M4 — registered when available)

When frameworks are not registered the dispatcher proceeds with a
pass-through dispatch (no policy evaluation, no optimization).

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    DISPATCHER_SYSTEM_ID,
    EngineState,
    PipelineStatus,
    PortfolioWorkflowType,
)
from .portfolio_pipeline import PortfolioPipeline, PipelineStage
from .portfolio_request import PortfolioRequest
from .exceptions import PortfolioDispatchError

_log = get_logger(__name__)

# Workflow types that require capital allocation
_ALLOCATION_WORKFLOWS = frozenset({
    PortfolioWorkflowType.CAPITAL_ALLOCATION,
    PortfolioWorkflowType.PORTFOLIO_CREATION,
})

# Workflow types that trigger rebalancing
_REBALANCING_WORKFLOWS = frozenset({
    PortfolioWorkflowType.PORTFOLIO_REBALANCING,
    PortfolioWorkflowType.RISK_SYNCHRONIZATION,
})


class PortfolioDispatcher:
    """
    Routes portfolio pipelines to external frameworks.

    Frameworks are optional plugins — the dispatcher runs without them and
    they can be registered at any time via :meth:`register_policy_framework`
    and :meth:`register_optimization_framework`.

    The dispatcher NEVER:
    - Evaluates portfolio policies (that is M3's responsibility)
    - Runs optimization algorithms (that is M4's responsibility)
    - Executes trades
    - Communicates with brokers
    """

    def __init__(self) -> None:
        self._policy_framework: Optional[Callable]       = None  # M3 hook
        self._optimization_framework: Optional[Callable] = None  # M4 hook
        self._dispatch_count: int = 0
        self._failure_count:  int = 0

    # ------------------------------------------------------------------
    # Framework registration (M3 / M4 hooks)
    # ------------------------------------------------------------------

    def register_policy_framework(self, framework: Callable) -> None:
        """Register the Portfolio Policy Framework (M3)."""
        self._policy_framework = framework
        _log.info(f"Portfolio Policy Framework registered with dispatcher")

    def register_optimization_framework(self, framework: Callable) -> None:
        """Register the Portfolio Optimization Framework (M4)."""
        self._optimization_framework = framework
        _log.info(f"Portfolio Optimization Framework registered with dispatcher")

    def unregister_policy_framework(self) -> None:
        self._policy_framework = None

    def unregister_optimization_framework(self) -> None:
        self._optimization_framework = None

    @property
    def has_policy_framework(self) -> bool:
        return self._policy_framework is not None

    @property
    def has_optimization_framework(self) -> bool:
        return self._optimization_framework is not None

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(
        self,
        pipeline: PortfolioPipeline,
        request:  PortfolioRequest,
    ) -> PortfolioPipeline:
        """
        Dispatch a pipeline through available frameworks.

        Workflow routing:
        1. Delegate to Policy Framework (M3) if registered.
        2. Delegate to Optimization Framework (M4) if registered.
        3. Determine post-dispatch state (ALLOCATING / REBALANCING / PUBLISHING).

        Parameters
        ----------
        pipeline : The active pipeline to dispatch.
        request :  The originating workflow request.

        Returns
        -------
        PortfolioPipeline
            The same pipeline instance (mutated in-place).
        """
        t0 = time.monotonic()
        try:
            # Delegate to Policy Framework (M3) if registered
            if self._policy_framework is not None:
                stage_start = time.time()
                try:
                    self._policy_framework(pipeline, request)
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "policy_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.COMPLETED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                    ))
                except Exception as exc:
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "policy_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.FAILED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                        error        = str(exc),
                    ))
                    raise PortfolioDispatchError(
                        str(exc),
                        workflow_type=request.workflow_type.value,
                    ) from exc

            # Delegate to Optimization Framework (M4) if registered
            if self._optimization_framework is not None:
                stage_start = time.time()
                try:
                    self._optimization_framework(pipeline, request)
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "optimization_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.COMPLETED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                    ))
                except Exception as exc:
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "optimization_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.FAILED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                        error        = str(exc),
                    ))
                    raise PortfolioDispatchError(
                        str(exc),
                        workflow_type=request.workflow_type.value,
                    ) from exc

            self._dispatch_count += 1
            return pipeline

        except PortfolioDispatchError:
            self._failure_count += 1
            raise
        except Exception as exc:
            self._failure_count += 1
            raise PortfolioDispatchError(
                str(exc), workflow_type=request.workflow_type.value
            ) from exc

    def determine_next_state(self, workflow_type: PortfolioWorkflowType) -> EngineState:
        """
        Determine the engine state after dispatching based on workflow type.

        Returns
        -------
        EngineState
            ALLOCATING, REBALANCING, or PUBLISHING.
        """
        if workflow_type in _ALLOCATION_WORKFLOWS:
            return EngineState.ALLOCATING
        if workflow_type in _REBALANCING_WORKFLOWS:
            return EngineState.REBALANCING
        return EngineState.PUBLISHING

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def statistics(self) -> dict:
        return {
            "dispatch_count":             self._dispatch_count,
            "failure_count":              self._failure_count,
            "has_policy_framework":       self.has_policy_framework,
            "has_optimization_framework": self.has_optimization_framework,
        }
