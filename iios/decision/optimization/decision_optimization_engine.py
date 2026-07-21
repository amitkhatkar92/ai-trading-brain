"""
decision_optimization_engine.py — iios.decision.optimization
=============================================================
Primary public interface for the Decision Optimization Framework.

``DecisionOptimizationEngine`` is the single entry point for all
optimization requests.  It is lifecycle-aware, thread-safe, and emits
structured events.  It NEVER evaluates policies, executes trades, or
communicates with brokers.

``OptimizationFrameworkAdapter`` bridges the engine to the M2
``OptimizationFrameworkProtocol`` so it can be injected into M2's
``DecisionDispatcher`` without modification.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_OBJECTIVES,
    DEFAULT_MAX_CONSTRAINTS,
    DEFAULT_MAX_STRATEGIES,
    OPTIMIZATION_SYSTEM_ID,
    VERSION,
)
from .decision_candidate             import DecisionCandidate
from .decision_constraint            import DecisionConstraint
from .decision_objective             import DecisionObjective
from .decision_optimization_context  import DecisionOptimizationContext
from .decision_optimization_events   import (
    make_candidates_loaded,
    make_constraints_loaded,
    make_objectives_loaded,
    make_optimization_completed,
    make_optimization_failed,
    make_optimization_started,
    make_solution_selected,
    make_solution_validated,
)
from .decision_optimization_factory  import DecisionOptimizationFactory
from .decision_optimization_history  import DecisionOptimizationHistory
from .decision_optimization_manager  import DecisionOptimizationManager
from .decision_optimization_registry import DecisionOptimizationRegistry
from .decision_optimization_request  import DecisionOptimizationRequest
from .decision_optimization_response import DecisionOptimizationResponse
from .decision_optimization_statistics import DecisionOptimizationStatistics
from .decision_optimization_strategy import DecisionOptimizationStrategy
from .decision_optimizer             import DecisionOptimizer
from .decision_solution_validator    import DecisionSolutionValidator
from .decision_strategy_registry     import DecisionStrategyRegistry
from .exceptions import OptimizationEngineNotRunningError

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=OPTIMIZATION_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class DecisionOptimizationEngine(LifecycleAwareMixin):
    """
    Primary public interface for the Decision Optimization Framework.

    Responsibilities
    ----------------
    - Register / deregister objectives, constraints, and strategies.
    - Optimize a :class:`DecisionOptimizationRequest` and return a
      :class:`DecisionOptimizationResponse`.
    - Emit lifecycle events to registered listeners.
    - Track runtime statistics.
    - Maintain a bounded history of events and responses.

    Guarantees
    ----------
    - ``optimize()`` never raises on *business logic* errors; failures
      are captured in the response's ``error`` field.
    - Thread-safe for concurrent ``optimize()`` calls.
    - Does NOT evaluate policies, execute trades, or communicate with brokers.

    Parameters
    ----------
    max_objectives :  Maximum objectives in the registry.
    max_constraints : Maximum constraints in the registry.
    max_strategies :  Maximum strategies in the registry.
    max_history :     Maximum events/responses in history.
    engine_id :       Optional identifier override.
    """

    SYSTEM_ID = OPTIMIZATION_SYSTEM_ID

    def __init__(
        self,
        max_objectives:  int           = DEFAULT_MAX_OBJECTIVES,
        max_constraints: int           = DEFAULT_MAX_CONSTRAINTS,
        max_strategies:  int           = DEFAULT_MAX_STRATEGIES,
        max_history:     int           = DEFAULT_MAX_HISTORY,
        engine_id:       Optional[str] = None,
    ) -> None:
        super().__init__()
        self._engine_id = engine_id or OPTIMIZATION_SYSTEM_ID

        # Registries
        self._opt_registry       = DecisionOptimizationRegistry(
            max_objectives  = max_objectives,
            max_constraints = max_constraints,
        )
        self._strategy_registry  = DecisionStrategyRegistry(max_strategies)

        # Core components
        self._optimizer          = DecisionOptimizer()
        self._solution_validator = DecisionSolutionValidator()
        self._manager            = DecisionOptimizationManager(
            registry          = self._opt_registry,
            strategy_registry = self._strategy_registry,
            optimizer         = self._optimizer,
        )

        # Observability
        self._statistics = DecisionOptimizationStatistics()
        self._history    = DecisionOptimizationHistory(
            max_events    = max_history,
            max_responses = max_history,
        )
        self._factory    = DecisionOptimizationFactory()

        # Listeners
        self._listeners: List[Callable] = []

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        _log.debug(f"DecisionOptimizationEngine: starting ({self._engine_id})")
        _audit.log_lifecycle_event(
            engine_id  = self._engine_id,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )

    def _on_stop(self) -> None:
        _log.debug(f"DecisionOptimizationEngine: stopping ({self._engine_id})")
        _audit.log_lifecycle_event(
            engine_id  = self._engine_id,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _assert_running(self) -> None:
        state = self.lifecycle_state()
        if state not in _RUNNING:
            raise OptimizationEngineNotRunningError(
                f"DecisionOptimizationEngine not running (state={state!r})"
            )

    # ------------------------------------------------------------------
    # Primary interface
    # ------------------------------------------------------------------

    def optimize(
        self,
        request: DecisionOptimizationRequest,
    ) -> DecisionOptimizationResponse:
        """
        Optimize *request* and return a :class:`DecisionOptimizationResponse`.

        Raises
        ------
        :class:`OptimizationEngineNotRunningError` — lifecycle violation.
        """
        self._assert_running()
        t_start = time.time()

        request_id  = request.request_id
        decision_id = request.context.decision_id

        # Record request
        self._statistics.record_request_started(len(request.candidates))

        # Emit start events
        start_ev = make_optimization_started(
            request_id, decision_id, ACTOR_ENGINE,
            candidate_count = len(request.candidates),
            strategy        = request.strategy_id,
        )
        self._emit(start_ev)
        self._emit(make_candidates_loaded(
            request_id, decision_id, ACTOR_ENGINE, count=len(request.candidates)
        ))

        try:
            obj_count  = len(self._opt_registry.get_objectives(request.objective_ids))
            con_count  = len(self._opt_registry.get_constraints(request.constraint_ids))
            self._emit(make_objectives_loaded(
                request_id, decision_id, ACTOR_ENGINE, count=obj_count
            ))
            self._emit(make_constraints_loaded(
                request_id, decision_id, ACTOR_ENGINE, count=con_count
            ))

            summary, report = self._manager.optimize(request)
            elapsed         = time.time() - t_start

            if summary.solution is not None:
                sol = summary.solution

                # Validate
                vr = self._solution_validator.validate(sol)
                self._emit(make_solution_validated(
                    request_id, decision_id, ACTOR_ENGINE,
                    solution_id = sol.solution_id,
                    is_valid    = vr.is_valid,
                ))

                self._emit(make_solution_selected(
                    request_id, decision_id, ACTOR_ENGINE,
                    solution_id = sol.solution_id,
                    rank        = sol.rank,
                    is_optimal  = sol.is_optimal,
                ))

                self._emit(make_optimization_completed(
                    request_id, decision_id, ACTOR_ENGINE,
                    selected_id       = sol.selected_candidate.candidate_id,
                    final_score       = sol.final_score,
                    evaluation_time_s = elapsed,
                    is_optimal        = sol.is_optimal,
                ))

                response = DecisionOptimizationResponse.success(
                    request_id          = request_id,
                    decision_id         = decision_id,
                    solution            = sol,
                    summary             = summary,
                    optimization_report = report,
                    evaluation_time_s   = elapsed,
                )

                self._statistics.record_request_completed(
                    success           = True,
                    evaluation_time_s = elapsed,
                    violations        = len(sol.constraint_violations),
                )

            else:
                # Manager returned no solution
                reason = summary.rationale or "No feasible solution found"
                self._emit(make_optimization_failed(
                    request_id, decision_id, ACTOR_ENGINE, reason=reason
                ))
                response = DecisionOptimizationResponse.failure(
                    request_id, decision_id, reason
                )
                self._statistics.record_request_completed(
                    success           = False,
                    evaluation_time_s = time.time() - t_start,
                )

        except Exception as exc:
            _log.warning(
                f"DecisionOptimizationEngine: error for request "
                f"{request_id!r}: {exc}"
            )
            self._emit(make_optimization_failed(
                request_id, decision_id, ACTOR_ENGINE, reason=str(exc)
            ))
            response = DecisionOptimizationResponse.failure(
                request_id, decision_id, str(exc)
            )
            self._statistics.record_request_completed(
                success           = False,
                evaluation_time_s = time.time() - t_start,
            )

        self._history.record_response(response.to_dict())
        return response

    # ------------------------------------------------------------------
    # Registry management
    # ------------------------------------------------------------------

    def register_objective(self, objective: DecisionObjective) -> None:
        self._opt_registry.register_objective(objective)

    def deregister_objective(self, objective_id: str) -> bool:
        return self._opt_registry.deregister_objective(objective_id) is not None

    def get_objective(self, objective_id: str) -> Optional[DecisionObjective]:
        return self._opt_registry.find_objective(objective_id)

    def list_objectives(self) -> List[DecisionObjective]:
        return self._opt_registry.all_objectives()

    def register_constraint(self, constraint: DecisionConstraint) -> None:
        self._opt_registry.register_constraint(constraint)

    def deregister_constraint(self, constraint_id: str) -> bool:
        return self._opt_registry.deregister_constraint(constraint_id) is not None

    def get_constraint(self, constraint_id: str) -> Optional[DecisionConstraint]:
        return self._opt_registry.find_constraint(constraint_id)

    def list_constraints(self) -> List[DecisionConstraint]:
        return self._opt_registry.all_constraints()

    def register_strategy(self, strategy: DecisionOptimizationStrategy) -> None:
        self._strategy_registry.register(strategy)

    def get_strategy(self, strategy_id: str) -> Optional[DecisionOptimizationStrategy]:
        return self._strategy_registry.find(strategy_id)

    def list_strategies(self) -> List[DecisionOptimizationStrategy]:
        return self._strategy_registry.all_strategies()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def factory(self) -> DecisionOptimizationFactory:
        return self._factory

    def history(self) -> DecisionOptimizationHistory:
        return self._history

    def statistics(self) -> DecisionOptimizationStatistics:
        return self._statistics

    def health(self) -> dict:
        state = self.lifecycle_state()
        stats = self._statistics.snapshot()
        return {
            "engine_id":          self._engine_id,
            "state":              str(state),
            "is_healthy":         state in _RUNNING,
            "objective_count":    self._opt_registry.objective_count(),
            "constraint_count":   self._opt_registry.constraint_count(),
            "strategy_count":     self._strategy_registry.count(),
            "events_stored":      self._history.event_count(),
            **stats,
        }

    def status(self) -> dict:
        return {
            "engine_id":       self._engine_id,
            "state":           str(self.lifecycle_state()),
            "version":         VERSION,
            "objective_count": self._opt_registry.objective_count(),
            "constraint_count": self._opt_registry.constraint_count(),
        }

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    def add_listener(self, callback: Callable) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _emit(self, event: Any) -> None:
        self._history.record_event(event)
        for cb in list(self._listeners):
            try:
                cb(event)
            except Exception as exc:
                _log.warning(
                    f"DecisionOptimizationEngine: listener {cb!r} raised: {exc}"
                )


# ---------------------------------------------------------------------------
# M2 OptimizationFrameworkProtocol adapter
# ---------------------------------------------------------------------------

class OptimizationFrameworkAdapter:
    """
    Bridges :class:`DecisionOptimizationEngine` to the M2
    ``OptimizationFrameworkProtocol``.

    M2 protocol signature::

        def optimize(
            self,
            context:       DecisionEngineContext,
            policy_result: Dict[str, Any],
            inputs:        Dict[str, Any],
        ) -> Dict[str, Any]: ...

    The adapter converts the M2 arguments into a
    :class:`DecisionOptimizationRequest` and delegates to the engine.

    Candidates are expected in ``inputs["candidates"]`` as a list of
    :class:`DecisionCandidate` objects OR dicts.

    Usage::

        adapter = OptimizationFrameworkAdapter(engine)
        dispatcher.set_optimization_framework(adapter)
    """

    def __init__(self, engine: DecisionOptimizationEngine) -> None:
        self._engine = engine

    def optimize(
        self,
        context:       Any,
        policy_result: Dict[str, Any],
        inputs:        Dict[str, Any],
    ) -> Dict[str, Any]:
        """Optimize via the M2 protocol interface."""
        opt_ctx = DecisionOptimizationContext.from_engine_context(
            context,
            policy_result = policy_result or {},
            snapshots     = inputs.get("snapshots", {}),
        )

        # Resolve candidates from inputs
        raw_candidates = inputs.get("candidates", [])
        candidates: List[DecisionCandidate] = []
        for item in raw_candidates:
            if isinstance(item, DecisionCandidate):
                candidates.append(item)
            elif isinstance(item, dict):
                try:
                    candidates.append(
                        DecisionCandidate.create(
                            symbol          = item.get("symbol", "UNKNOWN"),
                            direction       = item.get("direction", "hold"),
                            quantity        = float(item.get("quantity", 0)),
                            price           = float(item.get("price", 0)),
                            expected_return = float(item.get("expected_return", 0)),
                            risk_score      = float(item.get("risk_score", 0.5)),
                            confidence      = float(item.get("confidence", 0.5)),
                            candidate_id    = item.get("candidate_id"),
                            decision_id     = opt_ctx.decision_id,
                        )
                    )
                except Exception:
                    pass

        req      = DecisionOptimizationRequest.create(opt_ctx, candidates)
        response = self._engine.optimize(req)

        return {
            "selected_candidate_id": (
                response.solution.selected_candidate.candidate_id
                if response.solution else None
            ),
            "final_score":            response.solution.final_score if response.solution else 0.0,
            "is_optimal":             response.is_optimal,
            "is_feasible":            response.is_feasible,
            "is_success":             response.is_success,
            "rationale":              response.solution.rationale if response.solution else "",
            "candidates_evaluated":   (
                response.summary.candidates_evaluated if response.summary else 0
            ),
            "optimization_strategy":  (
                response.summary.optimization_strategy if response.summary else ""
            ),
            "error":                  response.error,
            "response_id":            response.response_id,
        }
