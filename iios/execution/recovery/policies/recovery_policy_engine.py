"""
iios/execution/recovery/policies/recovery_policy_engine.py
==========================================================
RecoveryPolicyEngine — PRIMARY ENTRY POINT for the Recovery Policy Framework.

Accepts a PolicyEvaluationRequest, evaluates registered policies against the
context, selects the best strategy, and returns a RecoveryPolicyDecision.

Also exports RecoveryPolicyEngineAdapter which implements M2's
PolicyFrameworkPort so the engine can be injected into the Recovery Dispatcher.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from typing import Any, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    ENGINE_ID,
    VERSION,
    FailureCategory,
    FailureSeverity,
    PolicyPriority,
    RecoveryRecommendation,
    RecoveryStrategyType,
    SEVERITY_PRIORITY_MAP,
)
from .exceptions import (
    RecoveryPolicyEvaluationError,
    RecoveryPolicyNotRunningError,
)
from .recovery_context import PolicyEvaluationContext, make_policy_evaluation_context
from .recovery_events import (
    make_decision_published,
    make_engine_started,
    make_engine_stopped,
    make_fallback_policy_selected,
    make_policy_evaluation_failed,
    make_policy_evaluation_started,
    make_strategy_selected,
)
from .recovery_factory import RecoveryPolicyFactory
from .recovery_history import RecoveryPolicyHistory
from .recovery_policy import (
    EmergencyShutdownPolicy,
    FailoverPolicy,
    ManualInterventionPolicy,
    PolicyEvaluationResult,
    RestartPolicy,
    ResumePolicy,
    RetryPolicy,
    RollbackPolicy,
)
from .recovery_policy_manager import RecoveryPolicyManager
from .recovery_priority import RecoveryPriorityEvaluator
from .recovery_request import PolicyEvaluationRequest
from .recovery_response import (
    PolicyEvaluationReport,
    RecoveryPolicyDecision,
)
from .recovery_statistics import RecoveryPolicyStatistics
from .recovery_strategy import make_strategy
from .recovery_validation import PolicyEvaluationValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__)

# Map strategy type → recommendation
_STRATEGY_TO_RECOMMENDATION = {
    RecoveryStrategyType.RETRY:               RecoveryRecommendation.RETRY,
    RecoveryStrategyType.RESUME:              RecoveryRecommendation.RESUME,
    RecoveryStrategyType.ROLLBACK:            RecoveryRecommendation.ROLLBACK,
    RecoveryStrategyType.RESTART:             RecoveryRecommendation.RESTART,
    RecoveryStrategyType.FAILOVER:            RecoveryRecommendation.FAILOVER,
    RecoveryStrategyType.MANUAL_INTERVENTION: RecoveryRecommendation.MANUAL_INTERVENTION,
    RecoveryStrategyType.EMERGENCY_SHUTDOWN:  RecoveryRecommendation.EMERGENCY_SHUTDOWN,
    RecoveryStrategyType.COMPOSITE:           RecoveryRecommendation.MANUAL_INTERVENTION,
}


class RecoveryPolicyEngine(LifecycleAwareMixin):
    """
    Primary entry point for the Recovery Policy Framework.

    Lifecycle:
        engine.start()                     # registers default policies
        decision = engine.evaluate(req)    # evaluate and return decision
        engine.stop()

    Thread-safe: evaluate() may be called concurrently from multiple threads.
    """

    def __init__(self) -> None:
        super().__init__()
        self._manager    = RecoveryPolicyManager()
        self._factory    = RecoveryPolicyFactory()
        self._validator  = PolicyEvaluationValidator()
        self._priority   = RecoveryPriorityEvaluator()
        self._stats      = RecoveryPolicyStatistics()
        self._history    = RecoveryPolicyHistory()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._factory.start()
        self._manager.start()
        self._register_default_policies()
        _audit.log_lifecycle_event(ENGINE_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("RecoveryPolicyEngine started", version=VERSION)
        self._history.append_event(make_engine_started(actor=ACTOR_ENGINE))

    def _on_stop(self) -> None:
        self._history.append_event(make_engine_stopped(actor=ACTOR_ENGINE))
        self._manager.stop()
        self._factory.stop()
        _audit.log_lifecycle_event(ENGINE_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        _log.info("RecoveryPolicyEngine stopped")

    def _register_default_policies(self) -> None:
        """Register built-in policies in priority order."""
        for policy in [
            EmergencyShutdownPolicy(),
            FailoverPolicy(),
            RollbackPolicy(),
            RestartPolicy(),
            RetryPolicy(),
            ResumePolicy(),
            ManualInterventionPolicy(),   # fallback — lowest priority
        ]:
            self._manager.add_policy(policy)

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryPolicyNotRunningError()

    # ── Primary entry point ───────────────────────────────────────────────────

    def evaluate(self, request: PolicyEvaluationRequest) -> RecoveryPolicyDecision:
        """
        Evaluate the request against all registered policies and return the
        best RecoveryPolicyDecision.

        Never raises unless the engine is not running.
        """
        self._assert_running()

        start_ns = time.perf_counter_ns()
        self._history.append_request(request)
        self._history.append_event(
            make_policy_evaluation_started(
                request.request_id, actor=ACTOR_ENGINE
            )
        )
        self._stats.record_evaluation()

        # Step 1 — validate request
        vr = self._validator.validate_request(request)
        if not vr.is_valid:
            _log.warning(
                "Invalid evaluation request",
                request_id=request.request_id,
                errors=vr.errors,
            )

        context = request.context

        # Step 2 — get ordered policies for this context
        policies = self._manager.get_ordered_policies(context)
        fallback  = self._manager.get_fallback_policy()

        # Step 3 — evaluate each policy
        matched_results: List[PolicyEvaluationResult] = []
        rejected_names:  List[str]                    = []
        rules_evaluated  = 0

        for policy in policies:
            if policy.is_fallback:
                continue   # evaluate fallback only if nothing else matches
            try:
                result = policy.evaluate(context)
                rules_evaluated += len(policy.rules)
            except Exception as exc:
                _log.error(
                    "Policy evaluation failed",
                    policy_name=policy.name,
                    error=str(exc),
                )
                self._history.append_event(
                    make_policy_evaluation_failed(
                        request.request_id,
                        actor=ACTOR_ENGINE,
                        reason=str(exc),
                        policy_name=policy.name,
                    )
                )
                rejected_names.append(policy.name)
                continue

            result.policy_name = policy.name
            if result.matched:
                matched_results.append(result)
            else:
                rejected_names.append(policy.name)

        # Step 4 — select best result
        used_fallback = False
        if matched_results:
            best = max(matched_results, key=lambda r: r.confidence_score)
        elif fallback is not None:
            best = fallback.evaluate(context)
            best.policy_name = fallback.name
            used_fallback = True
            self._history.append_event(
                make_fallback_policy_selected(
                    request.request_id,
                    actor=ACTOR_ENGINE,
                    reason=f"No policy matched for {context.failure_category.value}",
                )
            )
        else:
            # Last-resort: manual intervention with zero confidence
            best = PolicyEvaluationResult(
                matched          = True,
                strategy_type    = RecoveryStrategyType.MANUAL_INTERVENTION,
                confidence_score = 0.0,
                reasons          = ["no policies registered"],
                policy_name      = "none",
            )
            used_fallback = True

        # Step 5 — compute priority
        priority_score = self._priority.evaluate(context)
        priority = priority_score.final_priority

        # Step 6 — resolve recommendation and strategy
        recommendation = _STRATEGY_TO_RECOMMENDATION.get(
            best.strategy_type, RecoveryRecommendation.MANUAL_INTERVENTION
        )
        strategy = make_strategy(best.strategy_type)

        # Step 7 — build evaluation report
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1e6
        report = PolicyEvaluationReport(
            report_id          = str(uuid.uuid4()),
            request_id         = request.request_id,
            policies_evaluated = len(policies),
            rules_evaluated    = rules_evaluated,
            matched_policies   = tuple(r.policy_name for r in matched_results),
            rejected_policies  = tuple(rejected_names),
            selected_policy    = best.policy_name,
            selected_strategy  = best.strategy_type,
            confidence_score   = best.confidence_score,
            evaluation_time_ms = elapsed_ms,
            reasons            = tuple(best.reasons),
            used_fallback      = used_fallback,
        )

        # Step 8 — build decision
        requires_failover = best.strategy_type == RecoveryStrategyType.FAILOVER
        requires_manual   = best.strategy_type in (
            RecoveryStrategyType.MANUAL_INTERVENTION,
            RecoveryStrategyType.EMERGENCY_SHUTDOWN,
        )

        decision = self._factory.create_decision(
            request_id                   = request.request_id,
            execution_session_id         = request.execution_session_id,
            subsystem_id                 = request.subsystem_id,
            is_approved                  = best.matched,
            strategy_type                = best.strategy_type,
            priority                     = priority,
            recommendation               = recommendation,
            failure_category             = request.failure_category,
            failure_severity             = request.failure_severity,
            confidence_score             = best.confidence_score,
            policy_name                  = best.policy_name,
            evaluation_report            = report,
            matched_rules                = tuple(best.matched_rules),
            evaluation_reasons           = tuple(best.reasons),
            requires_failover            = requires_failover,
            requires_manual_intervention = requires_manual,
            evaluation_time_ms           = elapsed_ms,
        )

        # Step 9 — update statistics
        self._update_statistics(decision, elapsed_ms, used_fallback)

        # Step 10 — persist in history
        self._history.append_decision(decision)
        self._history.append_report(report)

        # Step 11 — emit events
        self._history.append_event(
            make_strategy_selected(
                request.request_id,
                decision.decision_id,
                actor=ACTOR_ENGINE,
                policy_name=decision.policy_name,
                reason=f"strategy={decision.strategy_type.value} "
                       f"confidence={decision.confidence_score:.2f}",
            )
        )
        self._history.append_event(
            make_decision_published(
                request.request_id,
                decision.decision_id,
                actor=ACTOR_ENGINE,
                policy_name=decision.policy_name,
            )
        )

        _log.info(
            "Policy decision published",
            request_id=request.request_id,
            decision_id=decision.decision_id,
            strategy=decision.strategy_type.value,
            confidence=f"{decision.confidence_score:.2f}",
            policy=decision.policy_name,
            elapsed_ms=f"{elapsed_ms:.2f}",
        )
        return decision

    # ── Statistics / history accessors ────────────────────────────────────────

    @property
    def statistics(self) -> RecoveryPolicyStatistics:
        return self._stats

    @property
    def history(self) -> RecoveryPolicyHistory:
        return self._history

    # ── Policy management passthrough ─────────────────────────────────────────

    def register_policy(self, policy: "RecoveryPolicy") -> None:  # type: ignore[name-defined]
        """Register an additional policy at runtime."""
        self._assert_running()
        self._manager.add_policy(policy)

    def deactivate_policy(self, name: str) -> None:
        self._assert_running()
        self._manager.deactivate(name)

    def activate_policy(self, name: str) -> None:
        self._assert_running()
        self._manager.activate(name)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _update_statistics(
        self,
        decision: RecoveryPolicyDecision,
        elapsed_ms: float,
        used_fallback: bool,
    ) -> None:
        self._stats.record_decision(approved=decision.is_approved)
        self._stats.record_evaluation_time(elapsed_ms)
        if used_fallback:
            self._stats.record_fallback_used()

        st = decision.strategy_type
        if st == RecoveryStrategyType.RETRY:
            self._stats.record_retry_recommendation()
        elif st == RecoveryStrategyType.RESUME:
            self._stats.record_resume_recommendation()
        elif st == RecoveryStrategyType.ROLLBACK:
            self._stats.record_rollback_recommendation()
        elif st == RecoveryStrategyType.RESTART:
            self._stats.record_restart_recommendation()
        elif st == RecoveryStrategyType.FAILOVER:
            self._stats.record_failover_recommendation()
        elif st == RecoveryStrategyType.MANUAL_INTERVENTION:
            self._stats.record_manual_intervention()
        elif st == RecoveryStrategyType.EMERGENCY_SHUTDOWN:
            self._stats.record_emergency_shutdown()


# ── M2 bridge adapter ─────────────────────────────────────────────────────────

class RecoveryPolicyEngineAdapter:
    """
    Bridge adapter that implements M2's PolicyFrameworkPort.

    Wraps a RecoveryPolicyEngine so it can be injected directly into M2's
    RecoveryDispatcher without modifications to either layer.

    Lazy import of M2 types prevents circular imports at module load time.
    """

    def __init__(self, engine: RecoveryPolicyEngine) -> None:
        self._engine = engine

    def invoke(self, m2_request: Any, m2_context: Any) -> Any:
        """
        Convert M2 RecoveryRequest + RecoveryContext to a M3 request,
        evaluate, and return an M2 PolicyDecision.
        """
        from iios.execution.recovery.engine.recovery_dispatcher import PolicyDecision  # lazy

        eval_request = _make_eval_request_from_m2(m2_request, m2_context)
        decision = self._engine.evaluate(eval_request)

        return PolicyDecision(
            approved          = decision.is_approved,
            plan_id           = decision.decision_id,
            instructions      = decision.evaluation_reasons,
            requires_failover = decision.requires_failover,
            subsystem_id      = decision.subsystem_id,
            metadata          = {
                "policy_name":       decision.policy_name,
                "strategy_type":     decision.strategy_type.value,
                "confidence_score":  decision.confidence_score,
            },
        )


def _make_eval_request_from_m2(
    m2_request: Any, m2_context: Any
) -> PolicyEvaluationRequest:
    """Map M2 RecoveryRequest + RecoveryContext to M3 PolicyEvaluationRequest."""
    from .recovery_request import make_policy_evaluation_request

    failure_category = _map_failure_type_to_category(
        getattr(getattr(m2_request, "failure_context", None), "failure_type", "")
    )
    failure_severity = _map_severity_str(
        getattr(getattr(m2_request, "failure_context", None), "severity", "")
    )

    risk_snap = getattr(m2_context, "risk_snapshot", None)

    context = make_policy_evaluation_context(
        execution_session_id  = getattr(m2_request, "execution_session_id", ""),
        subsystem_id          = getattr(m2_request, "subsystem_id", ""),
        failure_category      = failure_category,
        failure_severity      = failure_severity,
        failure_reason        = getattr(
            getattr(m2_request, "failure_context", None), "failure_reason", ""
        ),
        failure_type          = getattr(
            getattr(m2_request, "failure_context", None), "failure_type", ""
        ),
        has_monitoring_snapshot = getattr(m2_context, "monitoring_snapshot", None) is not None,
        has_gateway_snapshot  = getattr(m2_context, "gateway_snapshot", None) is not None,
        has_risk_snapshot     = risk_snap is not None,
        request_id            = getattr(m2_request, "request_id", ""),
    )
    return make_policy_evaluation_request(
        execution_session_id = context.execution_session_id,
        subsystem_id         = context.subsystem_id,
        context              = context,
        failure_category     = failure_category,
        failure_severity     = failure_severity,
        request_id           = getattr(m2_request, "request_id", None),
    )


def _map_failure_type_to_category(failure_type: str) -> FailureCategory:
    _ft = (failure_type or "").lower()
    if "broker" in _ft:
        return FailureCategory.BROKER_FAILURE
    if "gateway" in _ft:
        return FailureCategory.GATEWAY_FAILURE
    if "network" in _ft:
        return FailureCategory.NETWORK_FAILURE
    if "timeout" in _ft:
        return FailureCategory.TIMEOUT
    if "risk" in _ft:
        return FailureCategory.RISK_VIOLATION
    if "data" in _ft or "integrity" in _ft:
        return FailureCategory.DATA_INTEGRITY_FAILURE
    if "infra" in _ft:
        return FailureCategory.INFRASTRUCTURE_FAILURE
    if "execution" in _ft:
        return FailureCategory.EXECUTION_FAILURE
    return FailureCategory.UNKNOWN_FAILURE


def _map_severity_str(severity: Any) -> FailureSeverity:
    s = str(severity).lower() if severity else "unknown"
    return {
        "critical": FailureSeverity.CRITICAL,
        "high":     FailureSeverity.HIGH,
        "medium":   FailureSeverity.MEDIUM,
        "low":      FailureSeverity.LOW,
    }.get(s, FailureSeverity.UNKNOWN)
