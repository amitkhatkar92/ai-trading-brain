"""
decision_dispatcher.py — iios.decision.engine
===============================================
Decision workflow dispatcher.

Routes decision pipelines to the Decision Policy Framework (M3) and the
Decision Optimization Framework (M4).

Since M3 and M4 are not yet implemented, the dispatcher uses optional
protocol-based stubs.  When M3 and M4 are available they are injected via
``policy_framework`` and ``optimization_framework`` constructor arguments.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from iios.common.logging.logging_manager import get_logger

from .constants import DISPATCHER_SYSTEM_ID, VERSION
from .decision_context  import DecisionEngineContext
from .decision_pipeline import DecisionPipeline
from .exceptions import DecisionDispatchError

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Framework protocol interfaces (satisfied by M3 and M4 when implemented)
# ---------------------------------------------------------------------------
@runtime_checkable
class PolicyFrameworkProtocol(Protocol):
    """Interface contract for the Decision Policy Framework (C9 M3)."""

    def evaluate(
        self,
        context: DecisionEngineContext,
        inputs:  Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate the decision context against institutional policies."""
        ...


@runtime_checkable
class OptimizationFrameworkProtocol(Protocol):
    """Interface contract for the Decision Optimization Framework (C9 M4)."""

    def optimize(
        self,
        context:       DecisionEngineContext,
        policy_result: Dict[str, Any],
        inputs:        Dict[str, Any],
    ) -> Dict[str, Any]:
        """Optimize the decision given policy evaluation results."""
        ...


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
class DecisionDispatcher:
    """
    Routes decision pipelines through the evaluation chain:

    1. Invoke the Decision Policy Framework (M3) if available.
    2. Invoke the Decision Optimization Framework (M4) if available.
    3. Store results on the pipeline.

    If frameworks are not yet injected, the dispatcher records
    placeholder results so the pipeline can still complete.

    Parameters
    ----------
    policy_framework :       Optional :class:`PolicyFrameworkProtocol` (M3).
    optimization_framework : Optional :class:`OptimizationFrameworkProtocol` (M4).
    """

    def __init__(
        self,
        policy_framework:       Optional[PolicyFrameworkProtocol]       = None,
        optimization_framework: Optional[OptimizationFrameworkProtocol] = None,
    ) -> None:
        self._policy_framework       = policy_framework
        self._optimization_framework = optimization_framework
        self._source                 = DISPATCHER_SYSTEM_ID

    # ------------------------------------------------------------------
    # Primary dispatch operation
    # ------------------------------------------------------------------
    def dispatch(
        self,
        pipeline: DecisionPipeline,
        context:  DecisionEngineContext,
    ) -> Dict[str, Any]:
        """
        Execute the full dispatch chain for *pipeline*.

        Advances the pipeline through DISPATCHING → EVALUATING → PUBLISHING.
        Stores policy and optimization results on the pipeline.

        Returns the combined result dict.

        Raises
        ------
        DecisionDispatchError
            On an unrecoverable failure in the dispatch chain.
        """
        t_start = time.time()

        # DISPATCHING
        pipeline.begin_dispatching()
        _log.debug(
            f"DecisionDispatcher: dispatching pipeline "
            f"{pipeline.pipeline_id} for decision {context.decision_id}"
        )

        # EVALUATING — invoke Policy Framework (M3)
        pipeline.begin_evaluating()
        policy_result: Dict[str, Any] = {}
        try:
            if self._policy_framework is not None:
                policy_result = self._policy_framework.evaluate(
                    context, context.inputs
                )
            else:
                # M3 not yet available — record a pass-through result
                policy_result = {
                    "source":  "policy_framework_stub",
                    "status":  "deferred",
                    "version": VERSION,
                }
        except Exception as exc:
            pipeline.fail(f"Policy framework error: {exc}")
            raise DecisionDispatchError(f"Policy framework raised: {exc}") from exc

        pipeline.add_result("policy", policy_result)

        # Invoke Optimization Framework (M4)
        optimization_result: Dict[str, Any] = {}
        try:
            if self._optimization_framework is not None:
                optimization_result = self._optimization_framework.optimize(
                    context, policy_result, context.inputs
                )
            else:
                # M4 not yet available — record a pass-through result
                optimization_result = {
                    "source":  "optimization_framework_stub",
                    "status":  "deferred",
                    "version": VERSION,
                }
        except Exception as exc:
            pipeline.fail(f"Optimization framework error: {exc}")
            raise DecisionDispatchError(f"Optimization framework raised: {exc}") from exc

        pipeline.add_result("optimization", optimization_result)

        dispatch_time = time.time() - t_start
        pipeline.add_result("dispatch_time_s", dispatch_time)

        # PUBLISHING
        pipeline.begin_publishing()

        _log.debug(
            f"DecisionDispatcher: dispatch completed for "
            f"{pipeline.pipeline_id} in {dispatch_time:.4f}s"
        )

        return {
            "policy":        policy_result,
            "optimization":  optimization_result,
            "dispatch_time_s": dispatch_time,
        }

    # ------------------------------------------------------------------
    # Framework injection
    # ------------------------------------------------------------------
    def set_policy_framework(self, framework: PolicyFrameworkProtocol) -> None:
        """Inject or replace the Decision Policy Framework (M3)."""
        self._policy_framework = framework

    def set_optimization_framework(self, framework: OptimizationFrameworkProtocol) -> None:
        """Inject or replace the Decision Optimization Framework (M4)."""
        self._optimization_framework = framework

    @property
    def has_policy_framework(self) -> bool:
        return self._policy_framework is not None

    @property
    def has_optimization_framework(self) -> bool:
        return self._optimization_framework is not None
