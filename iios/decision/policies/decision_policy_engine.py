"""
decision_policy_engine.py — iios.decision.policies
====================================================
Primary public interface for the Decision Policy Framework.

``DecisionPolicyEngine`` is the single entry point for all policy
evaluations.  It is lifecycle-aware, thread-safe, and emits structured
events.  It NEVER optimises, executes, or communicates with brokers.

``PolicyFrameworkAdapter`` bridges the engine to the M2
``PolicyFrameworkProtocol`` so it can be injected into M2's
``DecisionDispatcher`` without modification.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    APPROVAL_ACTIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    ESCALATION_ACTIONS,
    POLICIES_SYSTEM_ID,
    VERSION,
    PolicyAction,
    PolicyType,
)
from .decision_policy          import DecisionPolicy
from .decision_policy_context  import PolicyEvaluationContext
from .decision_policy_evaluator import DecisionPolicyEvaluator
from .decision_policy_events   import (
    make_policy_approved,
    make_policy_blocked,
    make_policy_escalated,
    make_policy_evaluation_completed,
    make_policy_evaluation_started,
    make_policy_rejected,
)
from .decision_policy_factory  import DecisionPolicyFactory
from .decision_policy_history  import DecisionPolicyHistory
from .decision_policy_manager  import DecisionPolicyManager
from .decision_policy_registry import DecisionPolicyRegistry
from .decision_policy_request  import PolicyEvaluationRequest
from .decision_policy_response import DecisionPolicyResponse
from .decision_policy_statistics import DecisionPolicyStatistics
from .decision_policy_validator import DecisionPolicyValidator
from .exceptions import PolicyEngineNotRunningError

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=POLICIES_SYSTEM_ID)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class DecisionPolicyEngine(LifecycleAwareMixin):
    """
    Primary public interface for the Decision Policy Framework.

    Responsibilities
    ----------------
    - Register / deregister institutional policies.
    - Evaluate a :class:`PolicyEvaluationRequest` against all applicable
      policies and return a :class:`DecisionPolicyResponse`.
    - Emit lifecycle events to registered listeners.
    - Track runtime statistics.
    - Maintain a bounded history of events and responses.

    Guarantees
    ----------
    - ``evaluate()`` never raises on *policy business logic* errors; all
      failures are captured in the response's ``error`` field.
    - Thread-safe for concurrent ``evaluate()`` calls.
    - Does NOT optimise, execute, or communicate with brokers.

    Parameters
    ----------
    max_policies :          Maximum policies in the registry.
    max_history :           Maximum events/responses in history.
    policy_framework_id :   Optional identifier override.
    """

    SYSTEM_ID = POLICIES_SYSTEM_ID

    def __init__(
        self,
        max_policies:         int           = DEFAULT_MAX_POLICIES,
        max_history:          int           = DEFAULT_MAX_HISTORY,
        policy_framework_id:  Optional[str] = None,
    ) -> None:
        super().__init__()
        self._framework_id = policy_framework_id or POLICIES_SYSTEM_ID

        # Subsystems
        self._registry   = DecisionPolicyRegistry(max_policies=max_policies)
        self._evaluator  = DecisionPolicyEvaluator()
        self._validator  = DecisionPolicyValidator()
        self._manager    = DecisionPolicyManager(
            registry  = self._registry,
            evaluator = self._evaluator,
            validator = self._validator,
        )
        self._statistics = DecisionPolicyStatistics()
        self._history    = DecisionPolicyHistory(
            max_events    = max_history,
            max_responses = max_history,
        )
        self._factory    = DecisionPolicyFactory()

        # Listeners
        self._listeners: List[Callable[["DecisionPolicyEvent"], None]] = []  # type: ignore[name-defined]

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        _log.debug(f"DecisionPolicyEngine: starting ({self._framework_id})")
        _audit.log_lifecycle_event(
            engine_id  = self._framework_id,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )

    def _on_stop(self) -> None:
        _log.debug(f"DecisionPolicyEngine: stopping ({self._framework_id})")
        _audit.log_lifecycle_event(
            engine_id  = self._framework_id,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = ACTOR_SYSTEM,
        )

    # ------------------------------------------------------------------
    # Internal guard
    # ------------------------------------------------------------------

    def _assert_running(self) -> None:
        state = self.lifecycle_state()
        if state not in _RUNNING:
            raise PolicyEngineNotRunningError(
                f"DecisionPolicyEngine is not running (state={state!r})"
            )

    # ------------------------------------------------------------------
    # Primary evaluation interface
    # ------------------------------------------------------------------

    def evaluate(self, request: PolicyEvaluationRequest) -> DecisionPolicyResponse:
        """
        Evaluate *request* against all applicable policies.

        Returns
        -------
        :class:`DecisionPolicyResponse` — always returned; never raises
        on policy business logic errors.

        Raises
        ------
        :class:`PolicyEngineNotRunningError` — if the engine is not
        running (lifecycle error, not a business-logic error).
        """
        self._assert_running()
        t_start = time.time()

        request_id  = request.request_id
        decision_id = request.context.decision_id

        # Record start
        self._statistics.record_evaluation_started()
        start_event = make_policy_evaluation_started(
            request_id   = request_id,
            decision_id  = decision_id,
            source       = ACTOR_ENGINE,
            policy_count = self._registry.active_count(),
            chain_mode   = request.chain_mode.value,
        )
        self._history.record_event(start_event)
        self._notify_listeners(start_event)

        try:
            summary, audit = self._manager.evaluate(request)
            elapsed        = time.time() - t_start
            final_action   = summary.final_action

            # Emit outcome event
            outcome_event = self._make_outcome_event(
                request_id, decision_id, final_action, summary.reason if hasattr(summary, "reason") else ""
            )
            self._history.record_event(outcome_event)
            self._notify_listeners(outcome_event)

            # Completion event
            done_event = make_policy_evaluation_completed(
                request_id        = request_id,
                decision_id       = decision_id,
                source            = ACTOR_ENGINE,
                final_action      = final_action.value,
                evaluation_time_s = elapsed,
                total_evaluated   = summary.total_evaluated,
            )
            self._history.record_event(done_event)
            self._notify_listeners(done_event)

            response = DecisionPolicyResponse.success(
                request_id        = request_id,
                decision_id       = decision_id,
                action            = final_action,
                summary           = summary,
                audit_report      = audit,
                evaluation_time_s = elapsed,
            )

            # Update stats
            self._statistics.record_evaluation_completed(final_action, elapsed)
            self._statistics.record_coverage(summary.coverage)

        except Exception as exc:
            _log.warning(
                f"DecisionPolicyEngine: evaluation error for request "
                f"{request_id!r}: {exc}"
            )
            elapsed  = time.time() - t_start
            response = DecisionPolicyResponse.failure(
                request_id  = request_id,
                decision_id = decision_id,
                error       = str(exc),
            )
            self._statistics.record_evaluation_completed(PolicyAction.BLOCK, elapsed)

        self._history.record_response(response)
        return response

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def register_policy(self, policy: DecisionPolicy) -> None:
        """Register *policy* in the engine's policy registry."""
        self._registry.register(policy)

    def deregister_policy(self, policy_id: str) -> bool:
        """Remove *policy_id* from the registry.  Returns True if found."""
        removed = self._registry.deregister(policy_id)
        return removed is not None

    def get_policy(self, policy_id: str) -> Optional[DecisionPolicy]:
        """Return the policy or None if not registered."""
        return self._registry.find(policy_id)

    def list_policies(
        self,
        policy_type: Optional[PolicyType] = None,
    ) -> List[DecisionPolicy]:
        """
        Return all active policies, optionally filtered by *policy_type*.
        """
        if policy_type is not None:
            return self._registry.policies_by_type(policy_type)
        return self._registry.active_policies()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def history(self) -> DecisionPolicyHistory:
        """Return the engine's event/response history."""
        return self._history

    def statistics(self) -> DecisionPolicyStatistics:
        """Return the engine's runtime statistics."""
        return self._statistics

    def factory(self) -> DecisionPolicyFactory:
        """Return the engine's factory for constructing policy objects."""
        return self._factory

    def health(self) -> dict:
        stats = self._statistics.snapshot()
        state = self.lifecycle_state()
        return {
            "engine_id":     self._framework_id,
            "state":         str(state),
            "is_healthy":    state in _RUNNING,
            "policy_count":  self._registry.policy_count(),
            "active_count":  self._registry.active_count(),
            "events_stored": self._history.event_count(),
            **stats,
        }

    def status(self) -> dict:
        return {
            "engine_id":       self._framework_id,
            "state":           str(self.lifecycle_state()),
            "version":         VERSION,
            "policy_count":    self._registry.policy_count(),
            "response_count":  self._history.response_count(),
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

    def _notify_listeners(self, event: Any) -> None:
        for cb in list(self._listeners):
            try:
                cb(event)
            except Exception as exc:
                _log.warning(
                    f"DecisionPolicyEngine: listener {cb!r} raised: {exc}"
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_outcome_event(
        self,
        request_id:  str,
        decision_id: str,
        action:      PolicyAction,
        reason:      str,
    ):
        if action == PolicyAction.BLOCK:
            return make_policy_blocked(
                request_id, decision_id, ACTOR_ENGINE, reason=reason
            )
        if action == PolicyAction.REJECT:
            return make_policy_rejected(
                request_id, decision_id, ACTOR_ENGINE, reason=reason
            )
        if action in ESCALATION_ACTIONS:
            return make_policy_escalated(
                request_id, decision_id, ACTOR_ENGINE, reason=reason
            )
        return make_policy_approved(
            request_id, decision_id, ACTOR_ENGINE,
            action         = action.value,
            has_conditions = (action == PolicyAction.APPROVE_WITH_CONDITIONS),
        )


# ---------------------------------------------------------------------------
# M2 PolicyFrameworkProtocol adapter
# ---------------------------------------------------------------------------

class PolicyFrameworkAdapter:
    """
    Bridges :class:`DecisionPolicyEngine` to the M2
    ``PolicyFrameworkProtocol``.

    The M2 protocol is::

        class PolicyFrameworkProtocol(Protocol, runtime_checkable):
            def evaluate(self, context: DecisionEngineContext, inputs: Dict) -> Dict: ...

    Usage::

        adapter = PolicyFrameworkAdapter(engine)
        dispatcher.register_framework("policy", adapter)
    """

    def __init__(self, engine: DecisionPolicyEngine) -> None:
        self._engine = engine

    def evaluate(self, context: Any, inputs: Dict) -> Dict:
        """
        Evaluate the M2 context + inputs against all registered policies.

        Returns a plain dict compatible with M2's framework result
        interface.
        """
        eval_ctx = PolicyEvaluationContext.from_engine_context(
            context,
            snapshots=inputs.get("snapshots") if isinstance(inputs, dict) else {},
        )
        # Merge remaining inputs
        if isinstance(inputs, dict):
            merged = {k: v for k, v in inputs.items() if k != "snapshots"}
        else:
            merged = {}

        # Rebuild context with merged inputs
        eval_ctx = PolicyEvaluationContext.create(
            context_id  = eval_ctx.context_id,
            request_id  = eval_ctx.request_id,
            decision_id = eval_ctx.decision_id,
            session_id  = eval_ctx.session_id,
            pipeline_id = eval_ctx.pipeline_id,
            inputs      = {**eval_ctx.inputs, **merged},
            snapshots   = eval_ctx.snapshots,
            metadata    = eval_ctx.metadata,
        )

        req      = PolicyEvaluationRequest.create(eval_ctx)
        response = self._engine.evaluate(req)

        return {
            "action":                   response.action.value,
            "is_approved":              response.is_approved,
            "is_rejected":              response.is_rejected,
            "is_blocked":               response.is_blocked,
            "evaluation_time_s":        response.evaluation_time_s,
            "conditions":               list(response.summary.conditions)
                                        if response.summary else [],
            "total_policies_evaluated": response.summary.total_evaluated
                                        if response.summary else 0,
            "error":                    response.error,
            "response_id":              response.response_id,
        }
