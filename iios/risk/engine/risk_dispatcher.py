"""
risk_dispatcher.py — iios.risk.engine
========================================
Risk workflow dispatcher.

Routes risk pipelines to the appropriate framework components:
  - Risk Policy Framework (M3 — registered when available)
  - Risk Assessment & Optimization Framework (M4 — registered when available)

When frameworks are not registered the dispatcher proceeds with a
pass-through dispatch (no policy evaluation, no risk calculations).

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    DISPATCHER_SYSTEM_ID,
    EngineState,
    PipelineStatus,
    RiskWorkflowType,
    ASSESSMENT_WORKFLOWS,
    MONITORING_WORKFLOWS,
)
from .risk_pipeline import RiskPipeline, PipelineStage
from .risk_request import RiskRequest
from .exceptions import RiskDispatchError

_log = get_logger(__name__)


class RiskDispatcher:
    """
    Routes risk pipelines to external frameworks.

    Frameworks are optional plugins — the dispatcher runs without them and
    they can be registered at any time via :meth:`register_policy_framework`
    and :meth:`register_assessment_framework`.

    The dispatcher NEVER:
    - Evaluates risk policies (that is M3's responsibility)
    - Runs risk calculations (that is M4's responsibility)
    - Executes trades
    - Communicates with brokers
    """

    def __init__(self) -> None:
        self._policy_framework:     Optional[Callable] = None  # M3 hook
        self._assessment_framework: Optional[Callable] = None  # M4 hook
        self._dispatch_count: int = 0
        self._failure_count:  int = 0

    # ------------------------------------------------------------------
    # Framework registration
    # ------------------------------------------------------------------

    def register_policy_framework(self, framework: Callable) -> None:
        """Register the Risk Policy Framework (M3)."""
        self._policy_framework = framework
        _log.info("Risk Policy Framework registered with dispatcher")

    def register_assessment_framework(self, framework: Callable) -> None:
        """Register the Risk Assessment & Optimization Framework (M4)."""
        self._assessment_framework = framework
        _log.info("Risk Assessment Framework registered with dispatcher")

    def unregister_policy_framework(self) -> None:
        self._policy_framework = None

    def unregister_assessment_framework(self) -> None:
        self._assessment_framework = None

    @property
    def has_policy_framework(self) -> bool:
        return self._policy_framework is not None

    @property
    def has_assessment_framework(self) -> bool:
        return self._assessment_framework is not None

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(
        self,
        pipeline: RiskPipeline,
        request:  RiskRequest,
    ) -> RiskPipeline:
        """
        Dispatch a pipeline through available frameworks.

        Workflow routing:
        1. Delegate to Risk Policy Framework (M3) if registered.
        2. Delegate to Risk Assessment Framework (M4) if registered.
        3. Return the pipeline for post-dispatch handling.

        Returns
        -------
        RiskPipeline
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
                    raise RiskDispatchError(
                        str(exc), workflow_type=request.workflow_type.value,
                    ) from exc

            # Delegate to Assessment Framework (M4)
            if self._assessment_framework is not None:
                stage_start = time.time()
                try:
                    self._assessment_framework(pipeline, request)
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "assessment_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.COMPLETED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                    ))
                except Exception as exc:
                    pipeline.add_stage(PipelineStage(
                        stage_name   = "assessment_framework",
                        engine_state = EngineState.DISPATCHING,
                        status       = PipelineStatus.FAILED,
                        started_at   = stage_start,
                        completed_at = time.time(),
                        error        = str(exc),
                    ))
                    raise RiskDispatchError(
                        str(exc), workflow_type=request.workflow_type.value,
                    ) from exc

            self._dispatch_count += 1
            return pipeline

        except RiskDispatchError:
            self._failure_count += 1
            raise
        except Exception as exc:
            self._failure_count += 1
            raise RiskDispatchError(
                str(exc), workflow_type=request.workflow_type.value
            ) from exc

    def determine_next_state(self, workflow_type: RiskWorkflowType) -> EngineState:
        """
        Determine the engine state after dispatching based on workflow type.

        Returns
        -------
        EngineState
            ASSESSING, MONITORING, or PUBLISHING.
        """
        if workflow_type in ASSESSMENT_WORKFLOWS:
            return EngineState.ASSESSING
        if workflow_type in MONITORING_WORKFLOWS:
            return EngineState.MONITORING
        return EngineState.PUBLISHING

    def statistics(self) -> dict:
        return {
            "dispatch_count":        self._dispatch_count,
            "failure_count":         self._failure_count,
            "has_policy_framework":  self._policy_framework is not None,
            "has_assessment_framework": self._assessment_framework is not None,
        }
