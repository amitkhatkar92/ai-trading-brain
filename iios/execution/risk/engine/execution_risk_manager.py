"""iios/execution/risk/engine/execution_risk_manager.py
==================================================
RiskManager — internal coordinator for the Execution Risk Engine.

Owns the registry, factory, validator, statistics, history, and rule
registry.  Drives the M1 ExecutionRisk lifecycle from CREATED through
to a terminal outcome state.

Non-responsibilities
--------------------
* Does NOT implement any risk rules — rules are registered externally.
* Does NOT communicate with brokers.
* Does NOT execute orders.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import copy
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.risk.lifecycle import RiskState

from .constants import (
    ACTOR_ENGINE,
    DEFAULT_MAX_EVALUATIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_RULES,
    MANAGER_SYSTEM_ID,
    OperationType,
    RuleOutcome,
    VERSION,
)
from .exceptions import (
    EvaluationAggregationError,
    EvaluationCreationError,
    EvaluationExecutionError,
    EvaluationNotFoundError,
    EvaluationOperationError,
    RiskEngineNotRunningError,
    RuleRegistrationError,
)
from .execution_risk_events import (
    RiskEngineEvent,
    make_engine_started_event,
    make_engine_stopped_event,
    make_evaluation_completed_event,
    make_evaluation_failed_event,
    make_evaluation_started_event,
    make_rule_execution_completed_event,
    make_rule_execution_started_event,
    make_snapshot_published_event,
)
from .execution_risk_factory import EvaluationFactory
from .execution_risk_history import EngineRiskHistory
from .execution_risk_registry import EngineRiskRegistry
from .execution_risk_request import (
    EvaluationRequest,
    QueryEvaluationRequest,
    RiskRuleProtocol,
    RuleResult,
)
from .execution_risk_result import (
    EvaluationResult,
    make_failure_result,
    make_success_result,
)
from .execution_risk_snapshot import RiskEngineSnapshot, make_engine_risk_snapshot
from .execution_risk_statistics import EngineRiskStatistics
from .execution_risk_validation import EngineValidator, ValidationResult

_log   = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID)


# ── Aggregation helper ────────────────────────────────────────────────────────

def _aggregate_outcome(rule_results: List[RuleResult]) -> RuleOutcome:
    """
    Derive an aggregated engine-level outcome from individual rule results.

    Priority (highest first):
      BLOCKED > ERROR > WARNING > PASSED/SKIPPED
    If there are no rule results, the evaluation PASSES by default.
    """
    if not rule_results:
        return RuleOutcome.PASSED

    outcomes = {r.outcome for r in rule_results}

    if RuleOutcome.BLOCKED in outcomes:
        return RuleOutcome.BLOCKED
    if RuleOutcome.ERROR in outcomes:
        return RuleOutcome.ERROR
    if RuleOutcome.WARNING in outcomes:
        return RuleOutcome.WARNING
    return RuleOutcome.PASSED


def _outcome_to_risk_state(outcome: RuleOutcome) -> RiskState:
    """Map an aggregated RuleOutcome to the corresponding M1 RiskState."""
    return {
        RuleOutcome.PASSED:  RiskState.PASSED,
        RuleOutcome.WARNING: RiskState.WARNING,
        RuleOutcome.BLOCKED: RiskState.BLOCKED,
        RuleOutcome.ERROR:   RiskState.FAILED,
        RuleOutcome.SKIPPED: RiskState.PASSED,
    }[outcome]


class RiskManager(LifecycleAwareMixin):
    """
    Internal coordinator for the Execution Risk Engine.

    The manager is the only component that directly touches the M1
    ExecutionRisk domain objects and drives their state machine.
    """

    def __init__(
        self,
        max_evaluations: int = DEFAULT_MAX_EVALUATIONS,
        max_history:     int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._registry  = EngineRiskRegistry(max_evaluations=max_evaluations)
        self._factory   = EvaluationFactory()
        self._validator = EngineValidator()
        self._statistics = EngineRiskStatistics()
        self._history    = EngineRiskHistory(max_size=max_history)

        self._rules: Dict[str, RiskRuleProtocol] = {}
        self._events: List[RiskEngineEvent]       = []
        self._lock   = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise RiskEngineNotRunningError()

    def _on_start(self) -> None:
        self._registry.start()
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        _log.info("RiskManager started.")
        self._emit(make_engine_started_event())

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            MANAGER_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        self._emit(make_engine_stopped_event())
        _log.info("RiskManager stopped.", evaluations=self._registry.count)
        self._registry.stop()

    # ── Rule registration ─────────────────────────────────────────────────────

    def register_rule(self, rule: RiskRuleProtocol) -> None:
        """Register *rule* with the manager."""
        self._assert_running()
        name = rule.rule_name
        if not name:
            raise RuleRegistrationError("rule_name must not be empty", rule_name="")
        with self._lock:
            if name in self._rules:
                raise RuleRegistrationError(
                    f"Rule '{name}' is already registered", rule_name=name
                )
            self._rules[name] = rule
        _log.info("Rule registered.", rule_name=name)

    def deregister_rule(self, rule_name: str) -> None:
        """Remove *rule_name* from the manager."""
        self._assert_running()
        with self._lock:
            if rule_name not in self._rules:
                raise RuleRegistrationError(
                    f"Rule '{rule_name}' is not registered", rule_name=rule_name
                )
            del self._rules[rule_name]
        _log.info("Rule deregistered.", rule_name=rule_name)

    def registered_rules(self) -> List[str]:
        """Return a list of registered rule names."""
        with self._lock:
            return list(self._rules.keys())

    @property
    def rule_count(self) -> int:
        with self._lock:
            return len(self._rules)

    # ── Evaluate ──────────────────────────────────────────────────────────────

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """
        Execute a full risk evaluation for *request*.

        Lifecycle
        ---------
        1. Validate request
        2. Create M1 ExecutionRisk (CREATED)
        3. Register in registry
        4. CREATED → PENDING_EVALUATION → EVALUATING
        5. Execute applicable rules
        6. Aggregate results → terminal RiskState
        7. Record statistics; build result; append to history

        Thread safety
        -------------
        The registry and statistics mutations are protected by the
        registry's internal lock and _lock respectively.
        """
        self._assert_running()
        t0 = time.time()

        # ── 1. Validate ───────────────────────────────────────────────────────
        vr = self._validator.validate_request(request)
        if not vr.is_valid:
            elapsed_ms = (time.time() - t0) * 1_000.0
            self._statistics.record_failed()
            result = make_failure_result(
                request_id=request.request_id,
                operation_type=OperationType.EVALUATE,
                error_code="VALIDATION_FAILED",
                error_message="; ".join(vr.errors),
                elapsed_ms=elapsed_ms,
            )
            self._history.append(result)
            return result

        # ── 2. Create M1 ExecutionRisk ────────────────────────────────────────
        try:
            risk = self._factory.create_from_request(request)
        except Exception as exc:
            elapsed_ms = (time.time() - t0) * 1_000.0
            self._statistics.record_failed()
            result = make_failure_result(
                request_id=request.request_id,
                operation_type=OperationType.EVALUATE,
                error_code="CREATION_FAILED",
                error_message=str(exc),
                elapsed_ms=elapsed_ms,
            )
            self._history.append(result)
            raise EvaluationCreationError(str(exc)) from exc

        # ── 3. Register ───────────────────────────────────────────────────────
        self._registry.register(risk)
        self._statistics.record_started()

        # ── 4. Transition to EVALUATING ───────────────────────────────────────
        risk.transition_to(RiskState.PENDING_EVALUATION, actor=ACTOR_ENGINE)
        risk.transition_to(RiskState.EVALUATING, actor=ACTOR_ENGINE)
        self._registry.notify_transition(risk, RiskState.EVALUATING)

        # ── 5. Emit EVALUATION_STARTED event ──────────────────────────────────
        self._emit(
            make_evaluation_started_event(
                risk.risk_id,
                portfolio_id=risk.portfolio_id,
                strategy_id=risk.strategy_id,
            )
        )

        # ── 6. Build EvaluationContext ────────────────────────────────────────
        context = self._factory.create_evaluation_context(risk, request)

        # ── 7. Execute applicable rules ───────────────────────────────────────
        with self._lock:
            applicable_rules = [
                r for r in self._rules.values() if r.is_applicable(request)
            ]

        rule_results: List[RuleResult] = []
        t_eval_start = time.time()

        for rule in applicable_rules:
            self._emit(
                make_rule_execution_started_event(
                    risk.risk_id,
                    rule.rule_name,
                    portfolio_id=risk.portfolio_id,
                    strategy_id=risk.strategy_id,
                )
            )
            try:
                rr = rule.evaluate(request, context)
            except Exception as exc:
                _log.warning(
                    "Rule raised an exception; wrapping as ERROR.",
                    rule_name=rule.rule_name,
                    error=str(exc),
                )
                rr = RuleResult(
                    rule_name=rule.rule_name,
                    rule_category=rule.risk_category.value,
                    outcome=RuleOutcome.ERROR,
                    message=f"Rule raised: {exc}",
                    elapsed_ms=0.0,
                )
            rule_results.append(rr)
            self._emit(
                make_rule_execution_completed_event(
                    risk.risk_id,
                    rule.rule_name,
                    rr.outcome,
                    portfolio_id=risk.portfolio_id,
                    strategy_id=risk.strategy_id,
                )
            )

        evaluation_ms = (time.time() - t_eval_start) * 1_000.0

        # ── 8. Aggregate ──────────────────────────────────────────────────────
        t_agg = time.time()
        outcome = _aggregate_outcome(rule_results)
        aggregation_ms = (time.time() - t_agg) * 1_000.0

        # ── 9. Transition M1 risk to terminal outcome state ───────────────────
        target_state = _outcome_to_risk_state(outcome)
        risk.transition_to(target_state, actor=ACTOR_ENGINE, evaluation_time_ms=evaluation_ms)
        self._registry.notify_transition(risk, target_state, evaluation_time_ms=evaluation_ms)

        # ── 10. Statistics ────────────────────────────────────────────────────
        passed  = sum(1 for r in rule_results if r.passed)
        warned  = sum(1 for r in rule_results if r.warned)
        blocked = sum(1 for r in rule_results if r.blocked)
        errored = sum(1 for r in rule_results if r.errored)
        skipped = sum(1 for r in rule_results if r.outcome == RuleOutcome.SKIPPED)
        self._statistics.record_rule_execution(
            passed=passed, warned=warned, blocked=blocked,
            errored=errored, skipped=skipped,
        )

        elapsed_ms = (time.time() - t0) * 1_000.0

        if target_state == RiskState.PASSED:
            self._statistics.record_completed_passed(evaluation_ms, aggregation_ms)
        elif target_state == RiskState.WARNING:
            self._statistics.record_completed_warned(evaluation_ms, aggregation_ms)
        elif target_state == RiskState.BLOCKED:
            self._statistics.record_completed_blocked(evaluation_ms, aggregation_ms)
        else:
            self._statistics.record_failed()

        # ── 11. Emit EVALUATION_COMPLETED or FAILED ───────────────────────────
        if target_state == RiskState.FAILED:
            self._emit(
                make_evaluation_failed_event(
                    risk.risk_id,
                    reason="rule errors",
                    portfolio_id=risk.portfolio_id,
                    strategy_id=risk.strategy_id,
                )
            )
        else:
            self._emit(
                make_evaluation_completed_event(
                    risk.risk_id, outcome,
                    portfolio_id=risk.portfolio_id,
                    strategy_id=risk.strategy_id,
                )
            )

        # ── 12. Build result ──────────────────────────────────────────────────
        succeeded = target_state != RiskState.FAILED
        if succeeded:
            result = make_success_result(
                request_id=request.request_id,
                operation_type=OperationType.EVALUATE,
                evaluation_id=risk.risk_id,
                outcome=outcome,
                elapsed_ms=elapsed_ms,
                rule_results=tuple(rule_results),
            )
        else:
            result = make_failure_result(
                request_id=request.request_id,
                operation_type=OperationType.EVALUATE,
                error_code="RULE_ERRORS",
                error_message="One or more rules encountered errors",
                elapsed_ms=elapsed_ms,
                evaluation_id=risk.risk_id,
                rule_results=tuple(rule_results),
            )

        self._history.append(result)
        return result

    # ── Archive ───────────────────────────────────────────────────────────────

    def archive(self, evaluation_id: str) -> EvaluationResult:
        """Transition an evaluation to ARCHIVED."""
        self._assert_running()
        t0 = time.time()

        risk = self._registry.get(evaluation_id)
        if risk is None:
            raise EvaluationNotFoundError(evaluation_id)

        try:
            risk.transition_to(RiskState.ARCHIVED, actor=ACTOR_ENGINE)
            self._registry.notify_transition(risk, RiskState.ARCHIVED)
            self._statistics.record_archived()
        except Exception as exc:
            raise EvaluationOperationError(str(exc), operation="archive") from exc

        elapsed_ms = (time.time() - t0) * 1_000.0
        result = make_success_result(
            request_id=str(uuid.uuid4()),
            operation_type=OperationType.ARCHIVE,
            evaluation_id=evaluation_id,
            outcome=RuleOutcome.PASSED,
            elapsed_ms=elapsed_ms,
        )
        self._history.append(result)
        return result

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(self, request: QueryEvaluationRequest) -> EvaluationResult:
        """Query the registry and return matching evaluations in data dict."""
        self._assert_running()
        t0 = time.time()

        vr = self._validator.validate_query(request)
        if not vr.is_valid:
            elapsed_ms = (time.time() - t0) * 1_000.0
            return make_failure_result(
                request_id=request.request_id,
                operation_type=OperationType.QUERY,
                error_code="VALIDATION_FAILED",
                error_message="; ".join(vr.errors),
                elapsed_ms=elapsed_ms,
            )

        # Resolve candidates
        if request.evaluation_id:
            risk = self._registry.get(request.evaluation_id)
            candidates = [risk] if risk else []
        elif request.execution_id:
            candidates = self._registry.by_execution(request.execution_id)
        elif request.portfolio_id:
            candidates = self._registry.by_portfolio(request.portfolio_id)
        elif request.strategy_id:
            candidates = self._registry.by_strategy(request.strategy_id)
        elif request.risk_category:
            candidates = self._registry.by_category(request.risk_category)
        else:
            candidates = (
                self._registry.all()
                if request.include_archived
                else self._registry.active() + self._registry.passed()
                   + self._registry.blocked()
            )

        if not request.include_archived:
            from iios.execution.risk.lifecycle import RiskState as LS
            candidates = [c for c in candidates if c.state != LS.ARCHIVED]

        limited = candidates[: request.limit]

        elapsed_ms = (time.time() - t0) * 1_000.0
        result = make_success_result(
            request_id=request.request_id,
            operation_type=OperationType.QUERY,
            evaluation_id="",
            outcome=RuleOutcome.PASSED,
            elapsed_ms=elapsed_ms,
            data={
                "evaluations": [
                    {
                        "risk_id":       r.risk_id,
                        "state":         r.state.value,
                        "risk_category": r.risk_category.value,
                        "portfolio_id":  r.portfolio_id,
                        "strategy_id":   r.strategy_id,
                        "execution_id":  r.execution_id,
                        "created_at":    r.created_at,
                    }
                    for r in limited
                ],
                "count":  len(limited),
                "total":  len(candidates),
            },
        )
        self._history.append(result)
        return result

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> RiskEngineSnapshot:
        """Return a point-in-time snapshot of the engine state."""
        self._assert_running()
        snap = make_engine_risk_snapshot(
            evaluations=self._registry.all(),
            statistics=copy.copy(self._statistics),
            rule_count=self.rule_count,
        )
        self._emit(make_snapshot_published_event())
        return snap

    # ── Observers ─────────────────────────────────────────────────────────────

    def statistics(self) -> EngineRiskStatistics:
        """Return a shallow copy of the current statistics."""
        return copy.copy(self._statistics)

    def history(self) -> EngineRiskHistory:
        """Return the history store (not a copy)."""
        return self._history

    def events(self) -> List[RiskEngineEvent]:
        """Return all emitted events in order."""
        with self._lock:
            return list(self._events)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _emit(self, event: RiskEngineEvent) -> None:
        with self._lock:
            self._events.append(event)
