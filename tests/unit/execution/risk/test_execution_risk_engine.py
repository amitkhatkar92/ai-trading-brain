"""tests/unit/execution/risk/test_execution_risk_engine.py
==================================================
Test suite for C6 Phase 4 M2 — IIOS Execution Risk Engine.

Coverage targets
----------------
Class 01  — constants & enumerations
Class 02  — exceptions
Class 03  — EvaluationContext / make_evaluation_context
Class 04  — RuleResult
Class 05  — EvaluationRequest
Class 06  — QueryEvaluationRequest
Class 07  — RiskRuleProtocol (structural check via isinstance)
Class 08  — EvaluationResult / make_success_result / make_failure_result
Class 09  — EngineOpStateRecord
Class 10  — EngineRiskStatistics
Class 11  — EngineRiskHistory
Class 12  — EngineRiskRegistry (lifecycle + delegation)
Class 13  — EvaluationFactory
Class 14  — ValidationResult / EngineValidator
Class 15  — RiskEngineEvent / event factory functions
Class 16  — EvaluationSummary / RiskEngineSnapshot / make_engine_risk_snapshot
Class 17  — RiskManager — lifecycle
Class 18  — RiskManager — evaluate (happy-paths, aggregation, rules)
Class 19  — RiskManager — archive / query / snapshot / statistics / history
Class 20  — RiskEngine facade
Class 21  — Concurrency / edge-cases / regression guards

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import copy
import threading
import time
import uuid
from typing import Any, Dict, List

import pytest

from iios.execution.risk.lifecycle import RiskCategory, RiskState

from iios.execution.risk.engine import (
    ACTOR_ENGINE,
    DEFAULT_MAX_EVALUATIONS,
    DEFAULT_MAX_HISTORY,
    ENGINE_SYSTEM_ID,
    VERSION,
    EngineEventType,
    EngineOpState,
    EngineRiskHistory,
    EngineRiskRegistry,
    EngineRiskStatistics,
    EngineValidator,
    EvaluationContext,
    EvaluationFactory,
    EvaluationNotFoundError,
    EvaluationRequest,
    EvaluationResult,
    EvaluationSummary,
    OperationType,
    QueryEvaluationRequest,
    RiskEngine,
    RiskEngineEvent,
    RiskEngineNotRunningError,
    RiskEngineValidationError,
    RiskEngineSnapshot,
    RiskManager,
    RiskRuleProtocol,
    RuleOutcome,
    RuleRegistrationError,
    RuleResult,
    ValidationCode,
    ValidationResult,
    make_engine_risk_snapshot,
    make_engine_started_event,
    make_engine_stopped_event,
    make_evaluation_completed_event,
    make_evaluation_context,
    make_evaluation_failed_event,
    make_evaluation_started_event,
    make_failure_result,
    make_rule_execution_completed_event,
    make_rule_execution_started_event,
    make_snapshot_published_event,
    make_success_result,
    EngineOpStateRecord,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers / fixtures
# ═══════════════════════════════════════════════════════════════════════════════

def _make_request(**kw) -> EvaluationRequest:
    kw.setdefault("risk_category", RiskCategory.EXPOSURE)
    kw.setdefault("execution_id",  "exec-001")
    return EvaluationRequest(**kw)


def _make_query(**kw) -> QueryEvaluationRequest:
    return QueryEvaluationRequest(**kw)


def _make_rule_result(
    name:    str        = "test_rule",
    outcome: RuleOutcome = RuleOutcome.PASSED,
    msg:     str        = "ok",
) -> RuleResult:
    return RuleResult(
        rule_name=name,
        rule_category=RiskCategory.EXPOSURE.value,
        outcome=outcome,
        message=msg,
        elapsed_ms=1.0,
    )


class _PassRule:
    """Minimal risk rule that always passes."""
    rule_name     = "pass_rule"
    risk_category = RiskCategory.EXPOSURE

    def is_applicable(self, request):
        return True

    def evaluate(self, request, context):
        return RuleResult(
            rule_name=self.rule_name,
            rule_category=self.risk_category.value,
            outcome=RuleOutcome.PASSED,
            message="pass",
            elapsed_ms=0.1,
        )


class _WarnRule:
    rule_name     = "warn_rule"
    risk_category = RiskCategory.MARGIN

    def is_applicable(self, request):
        return True

    def evaluate(self, request, context):
        return RuleResult(
            rule_name=self.rule_name,
            rule_category=self.risk_category.value,
            outcome=RuleOutcome.WARNING,
            message="warn",
            elapsed_ms=0.1,
        )


class _BlockRule:
    rule_name     = "block_rule"
    risk_category = RiskCategory.EXPOSURE

    def is_applicable(self, request):
        return True

    def evaluate(self, request, context):
        return RuleResult(
            rule_name=self.rule_name,
            rule_category=self.risk_category.value,
            outcome=RuleOutcome.BLOCKED,
            message="blocked",
            elapsed_ms=0.1,
        )


class _ErrorRule:
    rule_name     = "error_rule"
    risk_category = RiskCategory.EXPOSURE

    def is_applicable(self, request):
        return True

    def evaluate(self, request, context):
        raise RuntimeError("boom")


class _NotApplicableRule:
    rule_name     = "na_rule"
    risk_category = RiskCategory.COMPLIANCE

    def is_applicable(self, request):
        return False

    def evaluate(self, request, context):
        raise AssertionError("should not be called")


@pytest.fixture
def engine():
    e = RiskEngine()
    e.start()
    yield e
    if e.lifecycle_state().value == "running":
        e.stop()


@pytest.fixture
def manager():
    m = RiskManager()
    m.start()
    yield m
    if m.lifecycle_state().value == "running":
        m.stop()


@pytest.fixture
def registry():
    r = EngineRiskRegistry()
    r.start()
    yield r
    if r.lifecycle_state().value == "running":
        r.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# Class 01 — Constants & enumerations
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstantsAndEnumerations:
    def test_engine_system_id_format(self):
        assert ENGINE_SYSTEM_ID.startswith("iios:")

    def test_version_semver(self):
        parts = VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_rule_outcome_values(self):
        assert RuleOutcome.PASSED.value  == "PASSED"
        assert RuleOutcome.WARNING.value == "WARNING"
        assert RuleOutcome.BLOCKED.value == "BLOCKED"
        assert RuleOutcome.ERROR.value   == "ERROR"
        assert RuleOutcome.SKIPPED.value == "SKIPPED"

    def test_operation_type_values(self):
        assert OperationType.EVALUATE.value == "EVALUATE"
        assert OperationType.QUERY.value    == "QUERY"
        assert OperationType.ARCHIVE.value  == "ARCHIVE"

    def test_engine_event_type_all_defined(self):
        required = {
            "EVALUATION_STARTED", "RULE_EXECUTION_STARTED",
            "RULE_EXECUTION_COMPLETED", "EVALUATION_COMPLETED",
            "EVALUATION_FAILED", "SNAPSHOT_PUBLISHED",
            "ENGINE_STARTED", "ENGINE_STOPPED",
        }
        assert {e.value for e in EngineEventType} == required

    def test_engine_op_state_values(self):
        assert EngineOpState.IDLE.value      == "IDLE"
        assert EngineOpState.COMPLETED.value == "COMPLETED"
        assert EngineOpState.FAILED.value    == "FAILED"

    def test_validation_code_values(self):
        assert ValidationCode.IDENTIFIER_MISSING.value  == "IDENTIFIER_MISSING"
        assert ValidationCode.EVALUATION_NOT_FOUND.value == "EVALUATION_NOT_FOUND"


# ═══════════════════════════════════════════════════════════════════════════════
# Class 02 — Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_not_running_no_args(self):
        from iios.execution.risk.engine import RiskEngineNotRunningError
        exc = RiskEngineNotRunningError()
        assert "ERM-001" in str(exc)

    def test_operation_error_has_operation_field(self):
        from iios.execution.risk.engine import EvaluationOperationError
        exc = EvaluationOperationError("fail", operation="evaluate")
        assert exc.operation == "evaluate"
        assert "ERM-002" in str(exc)

    def test_creation_error(self):
        from iios.execution.risk.engine import EvaluationCreationError
        exc = EvaluationCreationError("bad create")
        assert "ERM-003" in str(exc)

    def test_execution_error_has_rule_name(self):
        from iios.execution.risk.engine import EvaluationExecutionError
        exc = EvaluationExecutionError("rule fail", rule_name="my_rule")
        assert exc.rule_name == "my_rule"
        assert "ERM-004" in str(exc)

    def test_not_found_has_evaluation_id(self):
        from iios.execution.risk.engine import EvaluationNotFoundError
        exc = EvaluationNotFoundError("abc-123")
        assert exc.evaluation_id == "abc-123"
        assert "ERM-007" in str(exc)

    def test_rule_registration_error(self):
        from iios.execution.risk.engine import RuleRegistrationError
        exc = RuleRegistrationError("dup", rule_name="my_rule")
        assert exc.rule_name == "my_rule"
        assert "ERM-008" in str(exc)

    def test_validation_error(self):
        from iios.execution.risk.engine import RiskEngineValidationError
        exc = RiskEngineValidationError("bad input")
        assert "ERM-009" in str(exc)

    def test_all_inherit_from_base(self):
        from iios.execution.risk.engine import (
            ExecutionRiskEngineError,
            EvaluationAggregationError,
            EvaluationFinalizationError,
            RiskEngineStateError,
        )
        from iios.common.errors.exceptions import IIOSError
        for cls in (
            ExecutionRiskEngineError,
            RiskEngineNotRunningError,
            EvaluationAggregationError,
            EvaluationFinalizationError,
            RiskEngineStateError,
        ):
            assert issubclass(cls, IIOSError)


# ═══════════════════════════════════════════════════════════════════════════════
# Class 03 — EvaluationContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluationContext:
    def test_make_evaluation_context_defaults(self):
        ctx = make_evaluation_context("eval-1", RiskCategory.EXPOSURE)
        assert ctx.evaluation_id == "eval-1"
        assert ctx.risk_category == RiskCategory.EXPOSURE
        assert ctx.context_id
        assert ctx.created_at > 0
        assert not ctx.has_execution_snapshot
        assert not ctx.has_position_snapshot
        assert not ctx.has_risk_limits

    def test_make_evaluation_context_with_snapshots(self):
        ctx = make_evaluation_context(
            "eval-2", RiskCategory.MARGIN,
            execution_snapshot={"qty": 100},
            position_snapshot={"pnl": -5.0},
            risk_limits={"max_loss": 100.0},
        )
        assert ctx.has_execution_snapshot
        assert ctx.has_position_snapshot
        assert ctx.has_risk_limits

    def test_age_ms_increases(self):
        ctx = make_evaluation_context("e", RiskCategory.EXPOSURE)
        time.sleep(0.01)
        assert ctx.age_ms >= 10.0

    def test_frozen_cannot_mutate(self):
        ctx = make_evaluation_context("e", RiskCategory.EXPOSURE)
        with pytest.raises(Exception):
            ctx.evaluation_id = "other"

    def test_to_dict_keys(self):
        ctx = make_evaluation_context("e", RiskCategory.EXPOSURE)
        d = ctx.to_dict()
        assert "context_id" in d
        assert "risk_category" in d
        assert d["risk_category"] == "EXPOSURE"


# ═══════════════════════════════════════════════════════════════════════════════
# Class 04 — RuleResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuleResult:
    def test_passed_property(self):
        assert _make_rule_result(outcome=RuleOutcome.PASSED).passed
        assert _make_rule_result(outcome=RuleOutcome.SKIPPED).passed
        assert not _make_rule_result(outcome=RuleOutcome.BLOCKED).passed

    def test_blocked_property(self):
        assert _make_rule_result(outcome=RuleOutcome.BLOCKED).blocked

    def test_warned_property(self):
        assert _make_rule_result(outcome=RuleOutcome.WARNING).warned

    def test_errored_property(self):
        assert _make_rule_result(outcome=RuleOutcome.ERROR).errored

    def test_to_dict(self):
        rr = _make_rule_result(outcome=RuleOutcome.WARNING, msg="watch out")
        d = rr.to_dict()
        assert d["outcome"] == "WARNING"
        assert d["message"] == "watch out"

    def test_frozen(self):
        rr = _make_rule_result()
        with pytest.raises(Exception):
            rr.outcome = RuleOutcome.BLOCKED


# ═══════════════════════════════════════════════════════════════════════════════
# Class 05 — EvaluationRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluationRequest:
    def test_defaults(self):
        req = EvaluationRequest()
        assert req.request_id
        assert req.risk_category is None
        assert req.operation_type == OperationType.EVALUATE

    def test_with_category(self):
        req = EvaluationRequest(risk_category=RiskCategory.LIQUIDITY)
        assert req.risk_category == RiskCategory.LIQUIDITY

    def test_has_execution_snapshot(self):
        req = EvaluationRequest(execution_snapshot={"a": 1})
        assert req.has_execution_snapshot
        assert not req.has_position_snapshot

    def test_created_at_set(self):
        req = EvaluationRequest()
        assert req.created_at > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Class 06 — QueryEvaluationRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestQueryEvaluationRequest:
    def test_defaults(self):
        q = QueryEvaluationRequest()
        assert q.limit == 100
        assert not q.include_archived
        assert q.operation_type == OperationType.QUERY

    def test_custom_limit(self):
        q = QueryEvaluationRequest(limit=10)
        assert q.limit == 10


# ═══════════════════════════════════════════════════════════════════════════════
# Class 07 — RiskRuleProtocol
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskRuleProtocol:
    def test_pass_rule_is_protocol(self):
        assert isinstance(_PassRule(), RiskRuleProtocol)

    def test_block_rule_is_protocol(self):
        assert isinstance(_BlockRule(), RiskRuleProtocol)

    def test_non_conforming_is_not_protocol(self):
        class Bad:
            pass
        assert not isinstance(Bad(), RiskRuleProtocol)


# ═══════════════════════════════════════════════════════════════════════════════
# Class 08 — EvaluationResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluationResult:
    def test_make_success(self):
        r = make_success_result(
            request_id="req-1",
            operation_type=OperationType.EVALUATE,
            evaluation_id="eval-1",
            outcome=RuleOutcome.PASSED,
            elapsed_ms=10.0,
        )
        assert r.succeeded
        assert not r.failed
        assert r.is_passed
        assert not r.is_blocked

    def test_make_failure(self):
        r = make_failure_result(
            request_id="req-2",
            operation_type=OperationType.EVALUATE,
            error_code="ERR",
            error_message="bad",
            elapsed_ms=5.0,
        )
        assert r.failed
        assert not r.succeeded
        assert r.outcome is None

    def test_blocked_outcome(self):
        rr = _make_rule_result(outcome=RuleOutcome.BLOCKED)
        r = make_success_result(
            request_id="x", operation_type=OperationType.EVALUATE,
            evaluation_id="e", outcome=RuleOutcome.BLOCKED, elapsed_ms=1.0,
            rule_results=(rr,),
        )
        assert r.is_blocked
        assert len(r.blocked_rules) == 1

    def test_warning_rules(self):
        rr = _make_rule_result(outcome=RuleOutcome.WARNING)
        r = make_success_result(
            request_id="x", operation_type=OperationType.EVALUATE,
            evaluation_id="e", outcome=RuleOutcome.WARNING, elapsed_ms=1.0,
            rule_results=(rr,),
        )
        assert r.has_warnings
        assert len(r.warning_rules) == 1

    def test_to_dict_keys(self):
        r = make_success_result(
            request_id="r", operation_type=OperationType.EVALUATE,
            evaluation_id="e", outcome=RuleOutcome.PASSED, elapsed_ms=1.0,
        )
        d = r.to_dict()
        assert "result_id" in d
        assert "operation_type" in d
        assert "is_blocked" in d

    def test_frozen(self):
        r = make_success_result(
            request_id="r", operation_type=OperationType.EVALUATE,
            evaluation_id="e", outcome=RuleOutcome.PASSED, elapsed_ms=1.0,
        )
        with pytest.raises(Exception):
            r.succeeded = False


# ═══════════════════════════════════════════════════════════════════════════════
# Class 09 — EngineOpStateRecord
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineOpStateRecord:
    def _make(self, state=EngineOpState.EVALUATING, exited_at=None):
        return EngineOpStateRecord(
            state=state,
            operation_id="op-1",
            operation_type=OperationType.EVALUATE,
            entered_at=time.time(),
            exited_at=exited_at,
        )

    def test_is_current_when_no_exit(self):
        r = self._make()
        assert r.is_current
        assert r.duration_ms is None

    def test_with_exit_stamps_time(self):
        r = self._make()
        r2 = r.with_exit()
        assert not r2.is_current
        assert r2.duration_ms >= 0

    def test_is_terminal_for_completed(self):
        r = self._make(state=EngineOpState.COMPLETED)
        assert r.is_terminal

    def test_is_terminal_for_failed(self):
        r = self._make(state=EngineOpState.FAILED)
        assert r.is_terminal

    def test_non_terminal_idle(self):
        r = self._make(state=EngineOpState.IDLE)
        assert not r.is_terminal

    def test_to_dict(self):
        r = self._make()
        d = r.to_dict()
        assert d["state"] == "EVALUATING"
        assert "duration_ms" in d

    def test_frozen(self):
        r = self._make()
        with pytest.raises(Exception):
            r.state = EngineOpState.IDLE


# ═══════════════════════════════════════════════════════════════════════════════
# Class 10 — EngineRiskStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineRiskStatistics:
    def test_initial_zeros(self):
        s = EngineRiskStatistics()
        assert s.evaluations_started   == 0
        assert s.evaluations_completed == 0
        assert s.success_rate          == 1.0  # no ops → 100%

    def test_record_started(self):
        s = EngineRiskStatistics()
        s.record_started()
        assert s.evaluations_started  == 1
        assert s.total_operations     == 1

    def test_record_completed_passed(self):
        s = EngineRiskStatistics()
        s.record_started()
        s.record_completed_passed(evaluation_ms=10.0, aggregation_ms=2.0)
        assert s.evaluations_completed  == 1
        assert s.evaluations_passed     == 1
        assert s.average_evaluation_time_ms == pytest.approx(10.0)

    def test_record_completed_warned(self):
        s = EngineRiskStatistics()
        s.record_started()
        s.record_completed_warned(5.0, 1.0)
        assert s.evaluations_warned == 1

    def test_record_completed_blocked(self):
        s = EngineRiskStatistics()
        s.record_started()
        s.record_completed_blocked(5.0, 1.0)
        assert s.evaluations_blocked == 1

    def test_record_failed(self):
        s = EngineRiskStatistics()
        s.record_failed()
        assert s.evaluations_failed  == 1
        assert s.failed_operations   == 1

    def test_record_rule_execution(self):
        s = EngineRiskStatistics()
        s.record_rule_execution(passed=2, warned=1, blocked=0, errored=0, skipped=1)
        assert s.rule_executions_total   == 4
        assert s.rule_executions_passed  == 2
        assert s.rule_executions_warned  == 1
        assert s.rule_executions_skipped == 1

    def test_pass_rate_and_block_rate(self):
        s = EngineRiskStatistics()
        s.record_started()
        s.record_completed_passed(1.0, 0.0)
        s.record_started()
        s.record_completed_blocked(1.0, 0.0)
        assert s.pass_rate   == pytest.approx(0.5)
        assert s.block_rate  == pytest.approx(0.5)

    def test_success_rate_with_failures(self):
        s = EngineRiskStatistics()
        s.record_failed()
        assert s.success_rate == pytest.approx(0.0)

    def test_to_dict_keys(self):
        s = EngineRiskStatistics()
        d = s.to_dict()
        assert "evaluations_started" in d
        assert "average_evaluation_time_ms" in d


# ═══════════════════════════════════════════════════════════════════════════════
# Class 11 — EngineRiskHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineRiskHistory:
    def _make_result(self, evaluation_id="e1") -> EvaluationResult:
        return make_success_result(
            request_id="r", operation_type=OperationType.EVALUATE,
            evaluation_id=evaluation_id, outcome=RuleOutcome.PASSED, elapsed_ms=1.0,
        )

    def test_append_and_count(self):
        h = EngineRiskHistory()
        h.append(self._make_result())
        assert len(h) == 1

    def test_latest(self):
        h = EngineRiskHistory()
        r1 = self._make_result("e1")
        r2 = self._make_result("e2")
        h.append(r1)
        h.append(r2)
        latest = h.latest(1)
        assert latest[0].evaluation_id == "e2"

    def test_eviction(self):
        h = EngineRiskHistory(max_size=2)
        h.append(self._make_result("e1"))
        h.append(self._make_result("e2"))
        h.append(self._make_result("e3"))
        assert len(h) == 2
        assert h.evicted == 1
        assert h.total   == 3

    def test_by_evaluation(self):
        h = EngineRiskHistory()
        h.append(self._make_result("e1"))
        h.append(self._make_result("e2"))
        results = h.by_evaluation("e1")
        assert len(results) == 1
        assert results[0].evaluation_id == "e1"

    def test_failed_filter(self):
        h = EngineRiskHistory()
        h.append(self._make_result("e1"))
        fail = make_failure_result(
            request_id="r", operation_type=OperationType.EVALUATE,
            error_code="X", error_message="y", elapsed_ms=1.0,
        )
        h.append(fail)
        assert len(h.failed()) == 1
        assert len(h.successful()) == 1

    def test_by_operation(self):
        h = EngineRiskHistory()
        h.append(self._make_result("e1"))
        archive_r = make_success_result(
            request_id="r", operation_type=OperationType.ARCHIVE,
            evaluation_id="e1", outcome=RuleOutcome.PASSED, elapsed_ms=1.0,
        )
        h.append(archive_r)
        assert len(h.by_operation(OperationType.EVALUATE))  == 1
        assert len(h.by_operation(OperationType.ARCHIVE))   == 1

    def test_is_empty(self):
        h = EngineRiskHistory()
        assert h.is_empty()
        h.append(self._make_result())
        assert not h.is_empty()

    def test_all(self):
        h = EngineRiskHistory()
        h.append(self._make_result("a"))
        h.append(self._make_result("b"))
        assert len(h.all()) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Class 12 — EngineRiskRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineRiskRegistry:
    def test_start_stop(self):
        r = EngineRiskRegistry()
        r.start()
        assert r.lifecycle_state().value == "running"
        r.stop()
        assert r.lifecycle_state().value != "running"

    def test_assert_running_raises_when_stopped(self):
        r = EngineRiskRegistry()
        with pytest.raises(RiskEngineNotRunningError):
            r._assert_running()

    def test_register_and_get(self, registry):
        from iios.execution.risk.lifecycle import RiskFactory as LifecycleFactory
        factory = LifecycleFactory()
        risk = factory.create(RiskCategory.EXPOSURE, execution_id="exec-1")
        registry.register(risk)
        assert registry.get(risk.risk_id) == risk

    def test_count_and_is_empty(self, registry):
        assert registry.is_empty
        from iios.execution.risk.lifecycle import RiskFactory as LF
        risk = LF().create(RiskCategory.EXPOSURE)
        registry.register(risk)
        assert registry.count == 1
        assert not registry.is_empty

    def test_filter_by_state(self, registry):
        from iios.execution.risk.lifecycle import RiskFactory as LF, RiskState
        risk = LF().create(RiskCategory.EXPOSURE)
        registry.register(risk)
        assert len(registry.by_state(RiskState.CREATED)) == 1

    def test_filter_by_category(self, registry):
        from iios.execution.risk.lifecycle import RiskFactory as LF
        risk = LF().create(RiskCategory.MARGIN)
        registry.register(risk)
        assert len(registry.by_category(RiskCategory.MARGIN)) == 1
        assert len(registry.by_category(RiskCategory.EXPOSURE)) == 0

    def test_deregister(self, registry):
        from iios.execution.risk.lifecycle import RiskFactory as LF
        risk = LF().create(RiskCategory.EXPOSURE)
        registry.register(risk)
        registry.deregister(risk.risk_id)
        assert registry.count == 0

    def test_notify_transition(self, registry):
        from iios.execution.risk.lifecycle import RiskFactory as LF, RiskState
        risk = LF().create(RiskCategory.EXPOSURE)
        registry.register(risk)
        risk.transition_to(RiskState.PENDING_EVALUATION)
        risk.transition_to(RiskState.EVALUATING)
        risk.transition_to(RiskState.PASSED)
        registry.notify_transition(risk, RiskState.PASSED, evaluation_time_ms=5.0)
        # no exception = success

    def test_lifecycle_statistics_accessible(self, registry):
        stats = registry.lifecycle_statistics()
        assert hasattr(stats, "evaluations_created")


# ═══════════════════════════════════════════════════════════════════════════════
# Class 13 — EvaluationFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluationFactory:
    def test_create_from_request(self):
        req = _make_request()
        factory = EvaluationFactory()
        risk = factory.create_from_request(req)
        assert risk.risk_category == RiskCategory.EXPOSURE
        assert risk.execution_id  == "exec-001"

    def test_create_with_expiry_ttl(self):
        req = _make_request(expiry_ttl_seconds=60.0)
        factory = EvaluationFactory()
        risk = factory.create_from_request(req)
        assert risk.expiry_time is not None
        assert risk.expiry_time > time.time()

    def test_create_evaluation_context(self):
        req = _make_request(portfolio_id="port-1")
        factory = EvaluationFactory()
        risk = factory.create_from_request(req)
        ctx = factory.create_evaluation_context(risk, req)
        assert ctx.evaluation_id == risk.risk_id
        assert ctx.portfolio_id  == "port-1"


# ═══════════════════════════════════════════════════════════════════════════════
# Class 14 — ValidationResult & EngineValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineValidator:
    @pytest.fixture
    def v(self):
        return EngineValidator()

    def test_valid_request(self, v):
        req = _make_request()
        r = v.validate_request(req)
        assert r.is_valid

    def test_missing_risk_category(self, v):
        req = EvaluationRequest()
        r = v.validate_request(req)
        assert not r.is_valid
        assert r.error_count > 0

    def test_negative_expiry_ttl(self, v):
        req = _make_request(expiry_ttl_seconds=-1.0)
        r = v.validate_request(req)
        assert not r.is_valid

    def test_warn_missing_ids(self, v):
        req = EvaluationRequest(risk_category=RiskCategory.EXPOSURE)
        r = v.validate_request(req)
        assert r.is_valid
        assert r.warning_count > 0

    def test_valid_query(self, v):
        q = _make_query(limit=10)
        r = v.validate_query(q)
        assert r.is_valid

    def test_zero_limit_invalid(self, v):
        q = _make_query(limit=0)
        r = v.validate_query(q)
        assert not r.is_valid

    def test_raise_if_invalid_raises(self, v):
        req = EvaluationRequest()
        r = v.validate_request(req)
        with pytest.raises(RiskEngineValidationError):
            v.raise_if_invalid(r)

    def test_raise_if_invalid_does_not_raise_for_valid(self, v):
        req = _make_request()
        r = v.validate_request(req)
        v.raise_if_invalid(r)  # no exception

    def test_validate_evaluation_complete_empty(self, v):
        r = v.validate_evaluation_complete([])
        assert r.is_valid

    def test_validate_evaluation_complete_missing_name(self, v):
        rr = RuleResult(
            rule_name="", rule_category="EXPOSURE",
            outcome=RuleOutcome.PASSED, message="ok", elapsed_ms=1.0,
        )
        r = v.validate_evaluation_complete([rr])
        assert not r.is_valid

    def test_validation_result_to_dict(self):
        vr = ValidationResult(is_valid=True, errors=(), warnings=("w",))
        d = vr.to_dict()
        assert d["is_valid"]
        assert d["warning_count"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Class 15 — RiskEngineEvent & factory functions
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskEngineEvents:
    def test_engine_started(self):
        e = make_engine_started_event()
        assert e.event_type == EngineEventType.ENGINE_STARTED
        assert e.event_id
        assert e.occurred_at > 0

    def test_engine_stopped(self):
        e = make_engine_stopped_event()
        assert e.event_type == EngineEventType.ENGINE_STOPPED

    def test_evaluation_started(self):
        e = make_evaluation_started_event("eval-1", portfolio_id="p1", strategy_id="s1")
        assert e.event_type     == EngineEventType.EVALUATION_STARTED
        assert e.evaluation_id  == "eval-1"
        assert e.portfolio_id   == "p1"
        assert e.strategy_id    == "s1"

    def test_rule_execution_started(self):
        e = make_rule_execution_started_event("eval-1", "my_rule")
        assert e.event_type == EngineEventType.RULE_EXECUTION_STARTED
        assert e.rule_name  == "my_rule"

    def test_rule_execution_completed(self):
        e = make_rule_execution_completed_event("eval-1", "my_rule", RuleOutcome.PASSED)
        assert e.event_type == EngineEventType.RULE_EXECUTION_COMPLETED
        assert e.metadata["outcome"] == "PASSED"

    def test_evaluation_completed(self):
        e = make_evaluation_completed_event("eval-1", RuleOutcome.BLOCKED)
        assert e.event_type == EngineEventType.EVALUATION_COMPLETED
        assert e.metadata["outcome"] == "BLOCKED"

    def test_evaluation_failed(self):
        e = make_evaluation_failed_event("eval-1", reason="rule errors")
        assert e.event_type == EngineEventType.EVALUATION_FAILED

    def test_snapshot_published(self):
        e = make_snapshot_published_event()
        assert e.event_type == EngineEventType.SNAPSHOT_PUBLISHED

    def test_frozen(self):
        e = make_engine_started_event()
        with pytest.raises(Exception):
            e.event_id = "x"

    def test_to_dict(self):
        e = make_evaluation_started_event("e1")
        d = e.to_dict()
        assert "event_id" in d
        assert "event_type" in d


# ═══════════════════════════════════════════════════════════════════════════════
# Class 16 — Snapshot types
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotTypes:
    def _make_risk(self, category=RiskCategory.EXPOSURE):
        from iios.execution.risk.lifecycle import RiskFactory as LF
        return LF().create(category, execution_id="e1", portfolio_id="p1")

    def test_evaluation_summary_from_risk(self):
        risk = self._make_risk()
        s = EvaluationSummary.from_risk(risk, rule_count=2, elapsed_ms=5.0)
        assert s.evaluation_id == risk.risk_id
        assert s.rule_count    == 2
        assert s.elapsed_ms    == 5.0

    def test_evaluation_summary_to_dict(self):
        risk = self._make_risk()
        s = EvaluationSummary.from_risk(risk)
        d = s.to_dict()
        assert "evaluation_id" in d
        assert "risk_category" in d

    def test_make_engine_risk_snapshot_empty(self):
        stats = EngineRiskStatistics()
        snap = make_engine_risk_snapshot([], stats, 0)
        assert snap.is_empty
        assert snap.total_evaluations == 0

    def test_make_engine_risk_snapshot_counts(self):
        from iios.execution.risk.lifecycle import RiskFactory as LF, RiskState
        stats = EngineRiskStatistics()
        risk1 = LF().create(RiskCategory.EXPOSURE)
        risk2 = LF().create(RiskCategory.MARGIN)
        risk2.transition_to(RiskState.PENDING_EVALUATION)
        risk2.transition_to(RiskState.EVALUATING)
        risk2.transition_to(RiskState.PASSED)
        snap = make_engine_risk_snapshot([risk1, risk2], stats, 3)
        assert snap.total_evaluations == 2
        assert snap.passed_count      == 1
        assert snap.registered_rule_count == 3

    def test_snapshot_to_dict_keys(self):
        stats = EngineRiskStatistics()
        snap = make_engine_risk_snapshot([], stats, 0)
        d = snap.to_dict()
        assert "snapshot_id" in d
        assert "is_healthy" in d

    def test_is_healthy_when_no_failures(self):
        stats = EngineRiskStatistics()
        snap = make_engine_risk_snapshot([], stats, 0)
        assert snap.is_healthy

    def test_frozen(self):
        stats = EngineRiskStatistics()
        snap = make_engine_risk_snapshot([], stats, 0)
        with pytest.raises(Exception):
            snap.total_evaluations = 99


# ═══════════════════════════════════════════════════════════════════════════════
# Class 17 — RiskManager lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskManagerLifecycle:
    def test_start_stop(self):
        m = RiskManager()
        m.start()
        assert m.lifecycle_state().value == "running"
        m.stop()
        assert m.lifecycle_state().value != "running"

    def test_double_start_raises(self):
        m = RiskManager()
        m.start()
        try:
            with pytest.raises(Exception):
                m.start()
        finally:
            m.stop()

    def test_operations_raise_when_stopped(self):
        m = RiskManager()
        req = _make_request()
        with pytest.raises(RiskEngineNotRunningError):
            m.evaluate(req)

    def test_register_rule_when_stopped(self):
        m = RiskManager()
        with pytest.raises(RiskEngineNotRunningError):
            m.register_rule(_PassRule())

    def test_engine_started_event_emitted(self):
        m = RiskManager()
        m.start()
        try:
            events = m.events()
            types = [e.event_type for e in events]
            assert EngineEventType.ENGINE_STARTED in types
        finally:
            m.stop()

    def test_engine_stopped_event_emitted(self):
        m = RiskManager()
        m.start()
        m.stop()
        events = m.events()
        types = [e.event_type for e in events]
        assert EngineEventType.ENGINE_STOPPED in types


# ═══════════════════════════════════════════════════════════════════════════════
# Class 18 — RiskManager evaluate
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskManagerEvaluate:
    def test_no_rules_returns_passed(self, manager):
        req = _make_request()
        result = manager.evaluate(req)
        assert result.succeeded
        assert result.outcome == RuleOutcome.PASSED
        assert result.evaluation_id

    def test_pass_rule_returns_passed(self, manager):
        manager.register_rule(_PassRule())
        result = manager.evaluate(_make_request())
        assert result.outcome == RuleOutcome.PASSED

    def test_warn_rule_returns_warning(self, manager):
        manager.register_rule(_WarnRule())
        result = manager.evaluate(_make_request())
        assert result.outcome == RuleOutcome.WARNING

    def test_block_rule_returns_blocked(self, manager):
        manager.register_rule(_BlockRule())
        result = manager.evaluate(_make_request())
        assert result.outcome == RuleOutcome.BLOCKED
        assert result.succeeded  # blocked is a valid business outcome

    def test_error_rule_wrapped_as_failed(self, manager):
        manager.register_rule(_ErrorRule())
        result = manager.evaluate(_make_request())
        assert not result.succeeded
        assert any(r.errored for r in result.rule_results)

    def test_not_applicable_rule_skipped(self, manager):
        manager.register_rule(_NotApplicableRule())
        result = manager.evaluate(_make_request())
        # NA rule not applied → no rule_results
        assert len(result.rule_results) == 0
        assert result.outcome == RuleOutcome.PASSED

    def test_block_takes_priority_over_warn(self, manager):
        manager.register_rule(_WarnRule())
        manager.register_rule(_BlockRule())
        result = manager.evaluate(_make_request())
        assert result.outcome == RuleOutcome.BLOCKED

    def test_invalid_request_returns_failure(self, manager):
        req = EvaluationRequest()  # no risk_category
        result = manager.evaluate(req)
        assert not result.succeeded
        assert "VALIDATION_FAILED" in result.error_code

    def test_evaluation_id_maps_to_m1_risk(self, manager):
        result = manager.evaluate(_make_request())
        assert result.evaluation_id  # not empty

    def test_rule_results_collected(self, manager):
        manager.register_rule(_PassRule())
        manager.register_rule(_WarnRule())
        result = manager.evaluate(_make_request())
        assert len(result.rule_results) == 2

    def test_statistics_updated_after_evaluate(self, manager):
        manager.evaluate(_make_request())
        stats = manager.statistics()
        assert stats.evaluations_started >= 1

    def test_history_updated_after_evaluate(self, manager):
        manager.evaluate(_make_request())
        assert len(manager.history()) >= 1

    def test_evaluation_started_event_emitted(self, manager):
        manager.evaluate(_make_request())
        types = [e.event_type for e in manager.events()]
        assert EngineEventType.EVALUATION_STARTED in types

    def test_evaluation_completed_event_emitted(self, manager):
        manager.evaluate(_make_request())
        types = [e.event_type for e in manager.events()]
        assert EngineEventType.EVALUATION_COMPLETED in types

    def test_m1_risk_state_after_pass(self, manager):
        result = manager.evaluate(_make_request())
        risk = manager._registry.get(result.evaluation_id)
        assert risk is not None
        assert risk.state == RiskState.PASSED

    def test_m1_risk_state_after_block(self, manager):
        manager.register_rule(_BlockRule())
        result = manager.evaluate(_make_request())
        risk = manager._registry.get(result.evaluation_id)
        assert risk.state == RiskState.BLOCKED

    def test_elapsed_ms_is_positive(self, manager):
        result = manager.evaluate(_make_request())
        assert result.elapsed_ms >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# Class 19 — RiskManager archive / query / snapshot / statistics / history
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskManagerOtherOps:
    def test_archive_existing(self, manager):
        result = manager.evaluate(_make_request())
        archive_r = manager.archive(result.evaluation_id)
        assert archive_r.succeeded
        risk = manager._registry.get(result.evaluation_id)
        assert risk.state == RiskState.ARCHIVED

    def test_archive_not_found_raises(self, manager):
        with pytest.raises(EvaluationNotFoundError):
            manager.archive("nonexistent-id")

    def test_query_all_no_filter(self, manager):
        manager.evaluate(_make_request())
        manager.evaluate(_make_request())
        q = _make_query()
        result = manager.query(q)
        assert result.succeeded
        assert result.data["count"] >= 2

    def test_query_by_portfolio(self, manager):
        manager.evaluate(_make_request(portfolio_id="port-A"))
        manager.evaluate(_make_request(portfolio_id="port-B"))
        result = manager.query(_make_query(portfolio_id="port-A"))
        for ev in result.data["evaluations"]:
            assert ev["portfolio_id"] == "port-A"

    def test_query_limit_respected(self, manager):
        for _ in range(5):
            manager.evaluate(_make_request())
        result = manager.query(_make_query(limit=2))
        assert result.data["count"] == 2

    def test_query_archived_excluded_by_default(self, manager):
        r = manager.evaluate(_make_request())
        manager.archive(r.evaluation_id)
        result = manager.query(_make_query())
        ids = [e["risk_id"] for e in result.data["evaluations"]]
        assert r.evaluation_id not in ids

    def test_query_archived_included_when_flag_set(self, manager):
        r = manager.evaluate(_make_request())
        manager.archive(r.evaluation_id)
        result = manager.query(_make_query(include_archived=True))
        ids = [e["risk_id"] for e in result.data["evaluations"]]
        assert r.evaluation_id in ids

    def test_query_invalid_limit_returns_failure(self, manager):
        result = manager.query(_make_query(limit=0))
        assert not result.succeeded

    def test_snapshot_returns_correct_counts(self, manager):
        manager.register_rule(_PassRule())
        manager.evaluate(_make_request())
        snap = manager.snapshot()
        assert isinstance(snap, RiskEngineSnapshot)
        assert snap.total_evaluations >= 1
        assert snap.registered_rule_count == 1

    def test_snapshot_event_emitted(self, manager):
        manager.snapshot()
        types = [e.event_type for e in manager.events()]
        assert EngineEventType.SNAPSHOT_PUBLISHED in types

    def test_statistics_is_copy(self, manager):
        s1 = manager.statistics()
        s2 = manager.statistics()
        assert s1 is not s2

    def test_rule_count_property(self, manager):
        assert manager.rule_count == 0
        manager.register_rule(_PassRule())
        assert manager.rule_count == 1

    def test_registered_rules_list(self, manager):
        manager.register_rule(_PassRule())
        names = manager.registered_rules()
        assert "pass_rule" in names

    def test_deregister_rule(self, manager):
        manager.register_rule(_PassRule())
        manager.deregister_rule("pass_rule")
        assert manager.rule_count == 0

    def test_deregister_nonexistent_raises(self, manager):
        with pytest.raises(RuleRegistrationError):
            manager.deregister_rule("no_such_rule")

    def test_register_duplicate_raises(self, manager):
        manager.register_rule(_PassRule())
        with pytest.raises(RuleRegistrationError):
            manager.register_rule(_PassRule())


# ═══════════════════════════════════════════════════════════════════════════════
# Class 20 — RiskEngine facade
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskEngineFacade:
    def test_start_stop(self):
        e = RiskEngine()
        e.start()
        assert e.lifecycle_state().value == "running"
        e.stop()

    def test_operations_raise_when_not_running(self):
        e = RiskEngine()
        with pytest.raises(RiskEngineNotRunningError):
            e.evaluate(_make_request())

    def test_evaluate_returns_result(self, engine):
        result = engine.evaluate(_make_request())
        assert isinstance(result, EvaluationResult)

    def test_register_and_deregister_rule(self, engine):
        engine.register_rule(_PassRule())
        assert "pass_rule" in engine.registered_rules()
        engine.deregister_rule("pass_rule")
        assert "pass_rule" not in engine.registered_rules()

    def test_rule_count_property(self, engine):
        assert engine.rule_count == 0
        engine.register_rule(_PassRule())
        assert engine.rule_count == 1

    def test_evaluation_count_property(self, engine):
        engine.evaluate(_make_request())
        assert engine.evaluation_count >= 1

    def test_snapshot(self, engine):
        snap = engine.snapshot()
        assert isinstance(snap, RiskEngineSnapshot)

    def test_statistics(self, engine):
        stats = engine.statistics()
        assert isinstance(stats, EngineRiskStatistics)

    def test_history(self, engine):
        engine.evaluate(_make_request())
        h = engine.history()
        assert isinstance(h, EngineRiskHistory)
        assert len(h) >= 1

    def test_events(self, engine):
        engine.evaluate(_make_request())
        evts = engine.events()
        assert len(evts) > 0

    def test_archive(self, engine):
        result = engine.evaluate(_make_request())
        ar = engine.archive(result.evaluation_id)
        assert ar.succeeded

    def test_query(self, engine):
        engine.evaluate(_make_request())
        result = engine.query(_make_query())
        assert result.succeeded

    def test_register_rule_when_stopped_raises(self):
        e = RiskEngine()
        with pytest.raises(RiskEngineNotRunningError):
            e.register_rule(_PassRule())


# ═══════════════════════════════════════════════════════════════════════════════
# Class 21 — Concurrency / edge-cases / regression guards
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrencyAndEdgeCases:
    def test_concurrent_evaluate(self, engine):
        engine.register_rule(_PassRule())
        results = []
        errors  = []

        def evaluate_one():
            try:
                r = engine.evaluate(_make_request())
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=evaluate_one) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 20
        assert all(r.succeeded for r in results)

    def test_concurrent_register_deregister(self, engine):
        """Multiple threads registering different rules concurrently."""
        errors = []

        class NamedRule:
            def __init__(self, name):
                self.rule_name     = name
                self.risk_category = RiskCategory.EXPOSURE
            def is_applicable(self, req): return True
            def evaluate(self, req, ctx):
                return RuleResult(
                    rule_name=self.rule_name, rule_category="EXPOSURE",
                    outcome=RuleOutcome.PASSED, message="ok", elapsed_ms=0.0,
                )

        def reg(name):
            try:
                engine.register_rule(NamedRule(name))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reg, args=(f"rule_{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert engine.rule_count >= 10

    def test_history_thread_safe(self, engine):
        errors = []

        def evaluate_and_check():
            try:
                engine.evaluate(_make_request())
                _ = len(engine.history())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=evaluate_and_check) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_statistics_pass_plus_block_counts(self, engine):
        engine.register_rule(_BlockRule())
        engine.evaluate(_make_request())
        stats = engine.statistics()
        assert stats.evaluations_blocked == 1
        assert stats.evaluations_passed  == 0

    def test_zero_max_evaluations_clamps_to_one(self):
        m = RiskManager(max_evaluations=0)
        m.start()
        try:
            assert m._registry._inner._max >= 1
        finally:
            m.stop()

    def test_zero_max_history_clamps_to_one(self):
        h = EngineRiskHistory(max_size=0)
        assert h._max >= 1

    def test_multiple_error_rules_all_wrapped(self, engine):
        class ErrorRule2:
            rule_name     = "error_rule_2"
            risk_category = RiskCategory.EXPOSURE
            def is_applicable(self, req): return True
            def evaluate(self, req, ctx): raise ValueError("second boom")

        engine.register_rule(_ErrorRule())
        engine.register_rule(ErrorRule2())
        result = engine.evaluate(_make_request())
        assert not result.succeeded
        assert sum(1 for r in result.rule_results if r.errored) == 2

    def test_snapshot_empty_engine(self, engine):
        snap = engine.snapshot()
        assert snap.is_empty
        assert snap.is_healthy

    def test_events_list_grows_monotonically(self, engine):
        n1 = len(engine.events())
        engine.evaluate(_make_request())
        n2 = len(engine.events())
        assert n2 > n1

    def test_archive_twice_raises(self, engine):
        result = engine.evaluate(_make_request())
        engine.archive(result.evaluation_id)
        with pytest.raises(Exception):  # InvalidRiskTransitionError propagated
            engine.archive(result.evaluation_id)

    def test_rule_expiry_context_snapshot_forwarded(self, engine):
        ctx_holder = []

        class SnapshotCapture:
            rule_name     = "snap_capture"
            risk_category = RiskCategory.EXPOSURE
            def is_applicable(self, req): return True
            def evaluate(self, req, context):
                ctx_holder.append(context)
                return RuleResult(
                    rule_name=self.rule_name, rule_category="EXPOSURE",
                    outcome=RuleOutcome.PASSED, message="ok", elapsed_ms=0.0,
                )

        engine.register_rule(SnapshotCapture())
        req = _make_request(
            execution_snapshot={"qty": 100},
            risk_limits={"max_loss": 500},
        )
        engine.evaluate(req)
        assert len(ctx_holder) == 1
        ctx = ctx_holder[0]
        assert ctx.has_execution_snapshot
        assert ctx.has_risk_limits
