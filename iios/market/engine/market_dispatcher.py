"""
market_dispatcher.py — iios.market.engine
============================================
Market workflow dispatcher.

Routes market pipelines to the appropriate framework components:
  - Market Policy Framework (M3 — registered when available)
  - Market Analytics & Intelligence Framework (M4 — registered when available)

When frameworks are not registered the dispatcher proceeds with a
pass-through dispatch (no policy evaluation, no analytics calculations).

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    DISPATCHER_SYSTEM_ID,
    EngineState,
    PipelineStatus,
    MarketWorkflowType,
    ANALYSIS_WORKFLOWS,
    MONITORING_WORKFLOWS,
)
from .market_pipeline import MarketPipeline, PipelineStage
from .market_request import MarketRequest
from .exceptions import MarketDispatchError

_log = get_logger(__name__)


class MarketDispatcher:
    """
    Routes market pipelines to external frameworks.

    Frameworks are optional plugins — the dispatcher runs without them and
    they can be registered at any time via
    :meth:`register_policy_framework` and
    :meth:`register_analytics_framework`.

    The dispatcher NEVER:
    - Evaluates market policies (that is M3's responsibility)
    - Runs market analytics or regime detection (that is M4's responsibility)
    - Makes trading decisions
    - Executes trades
    - Communicates with brokers
    """

    def __init__(self) -> None:
        self._policy_framework:    Optional[Callable] = None   # M3 hook
        self._analytics_framework: Optional[Callable] = None   # M4 hook
        self._dispatch_count: int = 0
        self._failure_count:  int = 0

    # ------------------------------------------------------------------
    # Framework registration
    # ------------------------------------------------------------------

    def register_policy_framework(self, framework: Callable) -> None:
        """Register the Market Policy Framework (M3)."""
        self._policy_framework = framework
        _log.info("Market Policy Framework registered with dispatcher")

    def register_analytics_framework(self, framework: Callable) -> None:
        """Register the Market Analytics & Intelligence Framework (M4)."""
        self._analytics_framework = framework
        _log.info("Market Analytics Framework registered with dispatcher")

    def unregister_policy_framework(self) -> None:
        self._policy_framework = None

    def unregister_analytics_framework(self) -> None:
        self._analytics_framework = None

    @property
    def has_policy_framework(self) -> bool:
        return self._policy_framework is not None

    @property
    def has_analytics_framework(self) -> bool:
        return self._analytics_framework is not None

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(
        self,
        pipeline: MarketPipeline,
        request:  MarketRequest,
    ) -> MarketPipeline:
        """
        Dispatch a pipeline through available frameworks.

        Workflow routing:
        1. Delegate to Market Policy Framework (M3) if registered.
        2. Delegate to Market Analytics Framework (M4) if registered.
        3. Return the pipeline for post-dispatch handling.

        Returns
        -------
        MarketPipeline
            The same pipeline instance (mutated in-place).
        """
        try:
            # Delegate to Policy Framework (M3)
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
                    raise MarketDispatchError(
                        str(exc), workflow_type=request.workflow_type.value,
                    ) from exc

            # Delegate to Analytics Framework (M4)
            if self._analytics_framework is not None:
                stage_start = time.time()
                try:
                    self._analytics_framework(pipeline, request)
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "analytics_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.COMPLETED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                    ))
                except Exception as exc:
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "analytics_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.FAILED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                        error        = str(exc),
                    ))
                    raise MarketDispatchError(
                        str(exc), workflow_type=request.workflow_type.value,
                    ) from exc

            self._dispatch_count += 1
            return pipeline

        except MarketDispatchError:
            self._failure_count += 1
            raise
        except Exception as exc:
            self._failure_count += 1
            raise MarketDispatchError(
                str(exc), workflow_type=request.workflow_type.value
            ) from exc

    def determine_next_state(self, workflow_type: MarketWorkflowType) -> EngineState:
        """
        Determine the engine state after dispatching based on workflow type.

        Returns
        -------
        EngineState
            ANALYZING, MONITORING, or PUBLISHING.
        """
        if workflow_type in ANALYSIS_WORKFLOWS:
            return EngineState.ANALYZING
        if workflow_type in MONITORING_WORKFLOWS:
            return EngineState.MONITORING
        return EngineState.PUBLISHING

    def statistics(self) -> dict:
        return {
            "dispatch_count":          self._dispatch_count,
            "failure_count":           self._failure_count,
            "has_policy_framework":    self._policy_framework is not None,
            "has_analytics_framework": self._analytics_framework is not None,
        }
