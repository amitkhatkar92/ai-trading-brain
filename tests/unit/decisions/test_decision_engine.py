"""
tests/unit/decisions/test_decision_engine.py
=============================================
Comprehensive unit tests for the Decision Engine Core.
Target: ≥ 90 tests.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid

import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────

def _pid() -> str:
    return f"req:{uuid.uuid4().hex[:8]}"


def _make_option(
    name:        str        = "test_option",
    option_type: str        = "accept",
    confidence:  float      = 0.8,
    risk_score:  float      = 0.2,
    evidence:    list | None = None,
) -> "DecisionOption":
    from iios.decisions import DecisionOption, DecisionType
    return DecisionOption(
        name        = name,
        option_type = DecisionType(option_type),
        confidence  = confidence,
        risk_score  = risk_score,
        evidence    = evidence or [{"source": "test"}],
    )


def _make_request(
    options:   list | None = None,
    source_id: str         = "test_source",
) -> "DecisionRequest":
    from iios.decisions import DecisionRequest
    return DecisionRequest(
        source_id = source_id,
        options   = options or [_make_option()],
    )


def _reset_all() -> None:
    from iios.decisions.core.decision_engine import reset_decision_engine
    from iios.decisions.core.decision_manager import reset_decision_manager
    from iios.decisions.registry.decision_registry import reset_decision_registry
    from iios.decisions.monitoring.decision_monitor import reset_decision_monitor
    from iios.decisions.decision_context import reset_decision_context

    reset_decision_engine()
    reset_decision_manager()
    reset_decision_registry()
    reset_decision_monitor()
    reset_decision_context()


@pytest.fixture(autouse=True)
def clean_singletons():
    _reset_all()
    yield
    _reset_all()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants & enums
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_decision_types_present(self):
        from iios.decisions import DecisionType
        assert DecisionType.ACCEPT in list(DecisionType)
        assert DecisionType.REJECT in list(DecisionType)
        assert DecisionType.DEFER in list(DecisionType)

    def test_decision_status_values(self):
        from iios.decisions import DecisionStatus
        assert DecisionStatus.COMPLETED.value == "completed"
        assert DecisionStatus.FAILED.value    == "failed"

    def test_workflow_stages_complete(self):
        from iios.decisions import WorkflowStage
        stages = {s.value for s in WorkflowStage}
        for expected in ("receive", "validate", "generate", "evaluate",
                         "policy_check", "score", "rank", "select", "explain", "publish"):
            assert expected in stages

    def test_default_weights_sum_to_one(self):
        from iios.decisions import DEFAULT_DIMENSION_WEIGHTS
        total = sum(DEFAULT_DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_version_string(self):
        from iios.decisions import DECISION_ENGINE_VERSION
        assert DECISION_ENGINE_VERSION == "1.0.0"

    def test_policy_outcome_values(self):
        from iios.decisions import PolicyOutcome
        assert PolicyOutcome.PASS.value == "pass"
        assert PolicyOutcome.FAIL.value == "fail"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_exception(self):
        from iios.decisions import DecisionEngineError
        with pytest.raises(DecisionEngineError):
            raise DecisionEngineError("test", "DE-000")

    def test_not_found(self):
        from iios.decisions import DecisionNotFoundError
        exc = DecisionNotFoundError("d1")
        assert "DE-011" in str(exc)
        assert "d1" in str(exc)

    def test_already_exists(self):
        from iios.decisions import DecisionAlreadyExistsError
        exc = DecisionAlreadyExistsError("d1")
        assert "DE-012" in str(exc)

    def test_invalid_request(self):
        from iios.decisions import InvalidDecisionRequestError
        exc = InvalidDecisionRequestError("bad request")
        assert "DE-021" in str(exc)

    def test_no_candidates(self):
        from iios.decisions import NoCandidatesError
        exc = NoCandidatesError("req1")
        assert "DE-041" in str(exc)

    def test_engine_not_initialized(self):
        from iios.decisions import EngineNotInitializedError
        exc = EngineNotInitializedError()
        assert "DE-071" in str(exc)

    def test_engine_already_running(self):
        from iios.decisions import EngineAlreadyRunningError
        exc = EngineAlreadyRunningError()
        assert "DE-072" in str(exc)

    def test_policy_violation(self):
        from iios.decisions import PolicyViolationError
        exc = PolicyViolationError("pol1", "reason")
        assert "DE-031" in str(exc)

    def test_workflow_stage_failed(self):
        from iios.decisions import WorkflowStageFailedError
        exc = WorkflowStageFailedError("validate", "bad input")
        assert "DE-051" in str(exc)

    def test_hierarchy(self):
        from iios.decisions import (
            DecisionEngineError,
            DecisionNotFoundError,
            EngineNotInitializedError,
        )
        assert issubclass(DecisionNotFoundError, DecisionEngineError)
        assert issubclass(EngineNotInitializedError, DecisionEngineError)


# ─────────────────────────────────────────────────────────────────────────────
# 3. DecisionContext
# ─────────────────────────────────────────────────────────────────────────────

class TestDecisionContext:
    def test_workflow_scope(self):
        from iios.decisions.decision_context import workflow_scope
        from iios.decisions import DecisionType
        with workflow_scope("req1", DecisionType.ACCEPT, "src1") as ctx:
            assert ctx.request_id == "req1"
            assert ctx.depth == 1

    def test_stage_scope(self):
        from iios.decisions.decision_context import workflow_scope, stage_scope
        from iios.decisions import WorkflowStage
        with workflow_scope("req1") as ctx:
            with stage_scope(WorkflowStage.VALIDATE) as ctx2:
                assert ctx2.current_stage == WorkflowStage.VALIDATE

    def test_diagnostics(self):
        from iios.decisions.decision_context import get_decision_context, workflow_scope
        with workflow_scope("req2"):
            ctx = get_decision_context()
            ctx.add_diagnostic("WARNING", "test warning", "validate", "tester")
            assert len(ctx.warnings()) == 1

    def test_singleton(self):
        from iios.decisions.decision_context import get_decision_context
        assert get_decision_context() is get_decision_context()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Models
# ─────────────────────────────────────────────────────────────────────────────

class TestDecisionOption:
    def test_defaults(self):
        from iios.decisions import DecisionOption, DecisionType
        opt = DecisionOption()
        assert opt.option_type == DecisionType.GENERIC

    def test_to_dict_keys(self):
        from iios.decisions import DecisionOption
        d = DecisionOption().to_dict()
        for k in ("option_id", "name", "option_type", "confidence", "risk_score"):
            assert k in d

    def test_add_evidence(self):
        from iios.decisions import DecisionOption
        opt = DecisionOption()
        opt.add_evidence({"source": "test"})
        assert len(opt.evidence) == 1


class TestDecisionCandidate:
    def test_defaults(self):
        from iios.decisions import DecisionCandidate, CandidateStatus
        c = DecisionCandidate()
        assert c.status == CandidateStatus.PENDING

    def test_mark_evaluated(self):
        from iios.decisions import DecisionCandidate, CandidateStatus
        c = DecisionCandidate()
        c.mark_evaluated(0.75, {"confidence": 0.8})
        assert c.status == CandidateStatus.EVALUATED
        assert c.composite_score == 0.75

    def test_passed_all_policies(self):
        from iios.decisions import DecisionCandidate, PolicyOutcome
        c = DecisionCandidate()
        c.add_policy_result("pol1", PolicyOutcome.PASS, "ok")
        assert c.passed_all_policies

    def test_has_policy_failure(self):
        from iios.decisions import DecisionCandidate, PolicyOutcome
        c = DecisionCandidate()
        c.add_policy_result("pol1", PolicyOutcome.FAIL, "failed")
        assert c.has_policy_failure

    def test_to_dict(self):
        from iios.decisions import DecisionCandidate
        d = DecisionCandidate().to_dict()
        assert "candidate_id" in d
        assert "composite_score" in d


class TestDecision:
    def test_defaults(self):
        from iios.decisions import Decision, DecisionStatus
        d = Decision()
        assert d.status == DecisionStatus.PENDING

    def test_complete(self):
        from iios.decisions import Decision, DecisionStatus
        d = Decision()
        d.complete()
        assert d.status == DecisionStatus.COMPLETED
        assert d.completed_at > 0

    def test_fail(self):
        from iios.decisions import Decision, DecisionStatus
        d = Decision()
        d.fail("test error")
        assert d.status == DecisionStatus.FAILED
        assert "test error" in d.errors

    def test_to_dict_keys(self):
        from iios.decisions import Decision
        d = Decision().to_dict()
        for k in ("decision_id", "decision_type", "status", "confidence",
                  "risk_score", "rationale", "candidates"):
            assert k in d


class TestDecisionRequest:
    def test_defaults(self):
        from iios.decisions import DecisionRequest, DecisionPriority
        r = DecisionRequest()
        assert r.priority == DecisionPriority.MEDIUM

    def test_is_expired_false(self):
        from iios.decisions import DecisionRequest
        r = DecisionRequest(ttl_s=3600.0)
        assert not r.is_expired()

    def test_is_expired_true(self):
        from iios.decisions import DecisionRequest
        r = DecisionRequest(ttl_s=0.001)
        time.sleep(0.01)
        assert r.is_expired()

    def test_to_dict(self):
        from iios.decisions import DecisionRequest
        d = DecisionRequest().to_dict()
        assert "request_id" in d


class TestDecisionResult:
    def test_add_stage(self):
        from iios.decisions import DecisionResult
        from iios.decisions import WorkflowStage
        r = DecisionResult()
        r.add_stage(WorkflowStage.VALIDATE, True, 1.5, "ok")
        assert len(r.stage_records) == 1

    def test_to_dict(self):
        from iios.decisions import DecisionResult
        d = DecisionResult().to_dict()
        assert "result_id" in d
        assert "succeeded" in d


class TestDecisionHistory:
    def test_append_and_latest(self):
        from iios.decisions import DecisionHistory, Decision
        h = DecisionHistory(source_id="src1")
        for _ in range(5):
            h.append(Decision())
        assert len(h.latest(3)) == 3

    def test_statistics(self):
        from iios.decisions import DecisionHistory, Decision
        h = DecisionHistory(source_id="src1")
        d = Decision()
        d.complete()
        h.append(d)
        s = h.statistics()
        assert s.total == 1
        assert s.completed == 1


# ─────────────────────────────────────────────────────────────────────────────
# 5. Registry
# ─────────────────────────────────────────────────────────────────────────────

class TestDecisionRegistry:
    def test_register_and_get(self):
        from iios.decisions.registry.decision_registry import get_decision_registry
        from iios.decisions import Decision
        reg = get_decision_registry()
        d   = Decision()
        d.complete()
        reg.register(d)
        assert reg.get(d.decision_id).decision_id == d.decision_id

    def test_duplicate_raises(self):
        from iios.decisions.registry.decision_registry import get_decision_registry
        from iios.decisions import Decision, DecisionAlreadyExistsError
        reg = get_decision_registry()
        d   = Decision()
        reg.register(d)
        with pytest.raises(DecisionAlreadyExistsError):
            reg.register(d)

    def test_not_found_raises(self):
        from iios.decisions.registry.decision_registry import get_decision_registry
        from iios.decisions import DecisionNotFoundError
        with pytest.raises(DecisionNotFoundError):
            get_decision_registry().get("nonexistent")

    def test_for_source(self):
        from iios.decisions.registry.decision_registry import get_decision_registry
        from iios.decisions import Decision, DecisionMetadata
        reg = get_decision_registry()
        for _ in range(3):
            d = Decision(metadata=DecisionMetadata(source_id="src_x"))
            reg.register(d)
        assert len(reg.for_source("src_x")) == 3

    def test_cancel(self):
        from iios.decisions.registry.decision_registry import get_decision_registry
        from iios.decisions import Decision, DecisionStatus
        reg = get_decision_registry()
        d   = Decision()
        reg.register(d)
        reg.cancel(d.decision_id)
        assert reg.get(d.decision_id).status == DecisionStatus.CANCELLED

    def test_expire_stale(self):
        from iios.decisions.registry.decision_registry import get_decision_registry
        from iios.decisions import Decision, DecisionStatus
        reg = get_decision_registry()
        d   = Decision()
        reg.register(d)
        time.sleep(0.01)
        expired = reg.expire_stale(ttl_s=0.005)
        assert d.decision_id in expired

    def test_stats(self):
        from iios.decisions.registry.decision_registry import get_decision_registry
        s = get_decision_registry().stats()
        assert "total" in s

    def test_singleton(self):
        from iios.decisions.registry.decision_registry import get_decision_registry
        assert get_decision_registry() is get_decision_registry()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Policies
# ─────────────────────────────────────────────────────────────────────────────

class TestPolicies:
    def _candidate(self, confidence: float = 0.8, risk: float = 0.2):
        from iios.decisions import DecisionCandidate
        c = DecisionCandidate(option=_make_option(confidence=confidence, risk_score=risk))
        return c

    def _request(self):
        return _make_request()

    def test_min_confidence_pass(self):
        from iios.decisions import MinConfidencePolicy, PolicyOutcome
        pol = MinConfidencePolicy(0.5)
        outcome, _ = pol.apply(self._candidate(confidence=0.8), self._request())
        assert outcome == PolicyOutcome.PASS

    def test_min_confidence_fail(self):
        from iios.decisions import MinConfidencePolicy, PolicyOutcome
        pol = MinConfidencePolicy(0.9)
        outcome, _ = pol.apply(self._candidate(confidence=0.5), self._request())
        assert outcome == PolicyOutcome.FAIL

    def test_max_risk_pass(self):
        from iios.decisions import MaxRiskPolicy, PolicyOutcome
        pol = MaxRiskPolicy(0.5)
        outcome, _ = pol.apply(self._candidate(risk=0.3), self._request())
        assert outcome == PolicyOutcome.PASS

    def test_max_risk_fail(self):
        from iios.decisions import MaxRiskPolicy, PolicyOutcome
        pol = MaxRiskPolicy(0.3)
        outcome, _ = pol.apply(self._candidate(risk=0.8), self._request())
        assert outcome == PolicyOutcome.FAIL

    def test_require_evidence_pass(self):
        from iios.decisions import RequireEvidencePolicy, PolicyOutcome
        pol = RequireEvidencePolicy()
        c   = self._candidate()
        c.option.evidence = [{"src": "x"}]
        outcome, _ = pol.apply(c, self._request())
        assert outcome == PolicyOutcome.PASS

    def test_require_evidence_fail(self):
        from iios.decisions import RequireEvidencePolicy, PolicyOutcome
        pol = RequireEvidencePolicy()
        c   = self._candidate()
        c.option.evidence = []
        outcome, _ = pol.apply(c, self._request())
        assert outcome == PolicyOutcome.FAIL

    def test_not_expired_request_pass(self):
        from iios.decisions import NotExpiredRequestPolicy, PolicyOutcome, DecisionRequest
        pol = NotExpiredRequestPolicy()
        r   = DecisionRequest(ttl_s=3600.0)
        outcome, _ = pol.apply(self._candidate(), r)
        assert outcome == PolicyOutcome.PASS

    def test_not_expired_request_fail(self):
        from iios.decisions import NotExpiredRequestPolicy, PolicyOutcome, DecisionRequest
        pol = NotExpiredRequestPolicy()
        r   = DecisionRequest(ttl_s=0.001)
        time.sleep(0.01)
        outcome, _ = pol.apply(self._candidate(), r)
        assert outcome == PolicyOutcome.FAIL

    def test_allowlist_type_pass(self):
        from iios.decisions import AllowlistTypePolicy, PolicyOutcome
        pol = AllowlistTypePolicy(["accept", "reject"])
        c   = self._candidate()
        c.option.option_type = __import__("iios.decisions", fromlist=["DecisionType"]).DecisionType.ACCEPT
        outcome, _ = pol.apply(c, self._request())
        assert outcome == PolicyOutcome.PASS

    def test_allowlist_type_fail(self):
        from iios.decisions import AllowlistTypePolicy, PolicyOutcome, DecisionType
        pol = AllowlistTypePolicy(["accept"])
        c   = self._candidate()
        c.option.option_type = DecisionType.REJECT
        outcome, _ = pol.apply(c, self._request())
        assert outcome == PolicyOutcome.FAIL

    def test_policy_name(self):
        from iios.decisions import MinConfidencePolicy
        pol = MinConfidencePolicy(0.6)
        assert "0.60" in pol.name


# ─────────────────────────────────────────────────────────────────────────────
# 7. Evaluator & Ranker
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluatorRanker:
    def test_evaluate_populates_scores(self):
        from iios.decisions.evaluation.decision_evaluator import DecisionEvaluator
        from iios.decisions import DecisionCandidate, CandidateStatus
        ev  = DecisionEvaluator()
        c   = DecisionCandidate(option=_make_option(confidence=0.9, risk_score=0.1))
        req = _make_request()
        ev.evaluate(c, req)
        assert c.status == CandidateStatus.EVALUATED
        assert 0.0 <= c.composite_score <= 1.0
        assert len(c.dimension_scores) > 0

    def test_high_confidence_low_risk_scores_higher(self):
        from iios.decisions.evaluation.decision_evaluator import DecisionEvaluator
        from iios.decisions import DecisionCandidate
        ev   = DecisionEvaluator()
        req  = _make_request()
        good = DecisionCandidate(option=_make_option(confidence=0.95, risk_score=0.05))
        bad  = DecisionCandidate(option=_make_option(confidence=0.3, risk_score=0.9))
        ev.evaluate(good, req)
        ev.evaluate(bad,  req)
        assert good.composite_score > bad.composite_score

    def test_register_scorer(self):
        from iios.decisions.evaluation.decision_evaluator import DecisionEvaluator
        from iios.decisions import DecisionCandidate
        ev  = DecisionEvaluator()
        req = _make_request()
        ev.register_scorer("custom_dim", lambda c, r: 0.99, weight=0.1)
        c = DecisionCandidate(option=_make_option())
        ev.evaluate(c, req)
        assert "custom_dim" in c.dimension_scores
        assert c.dimension_scores["custom_dim"] == pytest.approx(0.99)

    def test_ranker_assigns_ranks(self):
        from iios.decisions.evaluation.decision_evaluator import DecisionEvaluator
        from iios.decisions.evaluation.decision_ranker import DecisionRanker
        from iios.decisions import DecisionCandidate
        ev  = DecisionEvaluator()
        rk  = DecisionRanker()
        req = _make_request()
        cands = [
            DecisionCandidate(option=_make_option(confidence=0.9, risk_score=0.1)),
            DecisionCandidate(option=_make_option(confidence=0.5, risk_score=0.5)),
        ]
        for c in cands:
            ev.evaluate(c, req)
        ranked = rk.rank(cands)
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2

    def test_ranker_select_best(self):
        from iios.decisions.evaluation.decision_evaluator import DecisionEvaluator
        from iios.decisions.evaluation.decision_ranker import DecisionRanker
        from iios.decisions import DecisionCandidate, CandidateStatus
        ev  = DecisionEvaluator()
        rk  = DecisionRanker()
        req = _make_request()
        cands = [DecisionCandidate(option=_make_option()) for _ in range(3)]
        for c in cands:
            ev.evaluate(c, req)
        ranked   = rk.rank(cands)
        selected = rk.select_best(ranked)
        assert selected is not None
        assert selected.selected
        assert selected.status == CandidateStatus.SELECTED

    def test_ranker_policy_failures_at_bottom(self):
        from iios.decisions.evaluation.decision_evaluator import DecisionEvaluator
        from iios.decisions.evaluation.decision_ranker import DecisionRanker
        from iios.decisions import DecisionCandidate, PolicyOutcome
        ev   = DecisionEvaluator()
        rk   = DecisionRanker()
        req  = _make_request()
        good = DecisionCandidate(option=_make_option(confidence=0.5))
        bad  = DecisionCandidate(option=_make_option(confidence=0.9))
        bad.add_policy_result("pol", PolicyOutcome.FAIL, "no")
        for c in (good, bad):
            ev.evaluate(c, req)
        ranked = rk.rank([good, bad])
        # passing candidate must appear first
        assert not ranked[0].has_policy_failure


# ─────────────────────────────────────────────────────────────────────────────
# 8. Workflow
# ─────────────────────────────────────────────────────────────────────────────

class TestDecisionWorkflow:
    def _make_workflow(self, policies=None):
        from iios.decisions.evaluation.decision_evaluator import DecisionEvaluator
        from iios.decisions.evaluation.decision_ranker import DecisionRanker
        from iios.decisions.workflow.decision_factory import DecisionFactory
        from iios.decisions.workflow.decision_workflow import DecisionWorkflow
        from iios.decisions import MinConfidencePolicy, MaxRiskPolicy
        return DecisionWorkflow(
            evaluator = DecisionEvaluator(),
            ranker    = DecisionRanker(),
            factory   = DecisionFactory(),
            policies  = policies or [MinConfidencePolicy(0.3), MaxRiskPolicy(0.9)],
        )

    def test_full_workflow_succeeds(self):
        wf     = self._make_workflow()
        req    = _make_request(options=[_make_option(confidence=0.8, risk_score=0.2)])
        result = wf.run(req)
        assert result.succeeded
        assert result.decision.is_completed

    def test_all_stages_recorded(self):
        from iios.decisions import WorkflowStage
        wf     = self._make_workflow()
        result = wf.run(_make_request())
        stages = {s.stage for s in result.stage_records}
        for expected in WorkflowStage:
            assert expected in stages

    def test_expired_request_fails(self):
        from iios.decisions import DecisionRequest
        wf  = self._make_workflow()
        req = DecisionRequest(ttl_s=0.001)
        time.sleep(0.01)
        result = wf.run(req)
        assert not result.succeeded

    def test_no_options_auto_generates(self):
        from iios.decisions import DecisionRequest
        wf     = self._make_workflow()
        result = wf.run(DecisionRequest(source_id="src1"))
        # workflow auto-generates options
        assert result.total_candidates > 0

    def test_all_candidates_fail_policies(self):
        from iios.decisions import MinConfidencePolicy
        # All options have confidence=0.1 but policy requires ≥0.9
        wf  = self._make_workflow(policies=[MinConfidencePolicy(0.9)])
        req = _make_request(options=[_make_option(confidence=0.1)])
        result = wf.run(req)
        # Decision is built but no candidate selected
        assert not result.decision.selected_candidate_id

    def test_on_publish_callback(self):
        from iios.decisions.evaluation.decision_evaluator import DecisionEvaluator
        from iios.decisions.evaluation.decision_ranker import DecisionRanker
        from iios.decisions.workflow.decision_factory import DecisionFactory
        from iios.decisions.workflow.decision_workflow import DecisionWorkflow

        published = []
        wf = DecisionWorkflow(
            evaluator  = DecisionEvaluator(),
            ranker     = DecisionRanker(),
            factory    = DecisionFactory(),
            policies   = [],
            on_publish = published.append,
        )
        wf.run(_make_request())
        assert len(published) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 9. DecisionManager
# ─────────────────────────────────────────────────────────────────────────────

class TestDecisionManager:
    def test_decide_returns_result(self):
        from iios.decisions.core.decision_manager import get_decision_manager
        mgr    = get_decision_manager()
        result = mgr.decide(_make_request())
        assert result.succeeded

    def test_decision_stored_in_registry(self):
        from iios.decisions.core.decision_manager import get_decision_manager
        from iios.decisions.registry.decision_registry import get_decision_registry
        mgr    = get_decision_manager()
        result = mgr.decide(_make_request())
        reg    = get_decision_registry()
        assert reg.has(result.decision.decision_id)

    def test_get_decision(self):
        from iios.decisions.core.decision_manager import get_decision_manager
        mgr    = get_decision_manager()
        result = mgr.decide(_make_request())
        d      = mgr.get(result.decision.decision_id)
        assert d.decision_id == result.decision.decision_id

    def test_cancel_decision(self):
        from iios.decisions.core.decision_manager import get_decision_manager
        from iios.decisions import DecisionStatus
        mgr    = get_decision_manager()
        result = mgr.decide(_make_request())
        mgr.cancel(result.decision.decision_id)
        assert mgr.get(result.decision.decision_id).status == DecisionStatus.CANCELLED

    def test_recent(self):
        from iios.decisions.core.decision_manager import get_decision_manager
        mgr = get_decision_manager()
        for _ in range(5):
            mgr.decide(_make_request())
        assert len(mgr.recent(5)) == 5

    def test_statistics(self):
        from iios.decisions.core.decision_manager import get_decision_manager
        mgr = get_decision_manager()
        mgr.decide(_make_request())
        s = mgr.statistics()
        assert s.total >= 1

    def test_register_policy(self):
        from iios.decisions.core.decision_manager import get_decision_manager
        from iios.decisions import MaxRiskPolicy
        mgr = get_decision_manager()
        mgr.register_policy(MaxRiskPolicy(0.5))
        assert any("max_risk" in n for n in mgr.policy_names())

    def test_singleton_identity(self):
        from iios.decisions.core.decision_manager import get_decision_manager
        assert get_decision_manager() is get_decision_manager()


# ─────────────────────────────────────────────────────────────────────────────
# 10. DecisionEngine (top-level gateway)
# ─────────────────────────────────────────────────────────────────────────────

class TestDecisionEngine:
    def _engine(self):
        from iios.decisions import get_decision_engine
        eng = get_decision_engine()
        eng.initialize()
        return eng

    def test_initialize_and_is_running(self):
        eng = self._engine()
        assert eng.is_running

    def test_double_initialize_raises(self):
        from iios.decisions import EngineAlreadyRunningError
        eng = self._engine()
        with pytest.raises(EngineAlreadyRunningError):
            eng.initialize()

    def test_not_initialized_raises(self):
        from iios.decisions import get_decision_engine, EngineNotInitializedError
        eng = get_decision_engine()   # fresh, not initialized
        with pytest.raises(EngineNotInitializedError):
            eng.decide(_make_request())

    def test_shutdown(self):
        eng = self._engine()
        eng.shutdown()
        assert not eng.is_running

    def test_decide_returns_result(self):
        eng    = self._engine()
        result = eng.decide(_make_request())
        assert result.succeeded

    def test_make_request(self):
        eng = self._engine()
        r   = eng.make_request(
            options   = [_make_option()],
            source_id = "test",
        )
        from iios.decisions import DecisionRequest
        assert isinstance(r, DecisionRequest)

    def test_get_decision(self):
        eng    = self._engine()
        result = eng.decide(_make_request())
        d      = eng.get(result.decision.decision_id)
        assert d.decision_id == result.decision.decision_id

    def test_cancel(self):
        from iios.decisions import DecisionStatus
        eng    = self._engine()
        result = eng.decide(_make_request())
        eng.cancel(result.decision.decision_id)
        assert eng.get(result.decision.decision_id).status == DecisionStatus.CANCELLED

    def test_recent(self):
        eng = self._engine()
        for _ in range(4):
            eng.decide(_make_request())
        assert len(eng.recent(10)) == 4

    def test_for_source(self):
        eng = self._engine()
        for _ in range(3):
            eng.decide(_make_request(source_id="src_test"))
        assert len(eng.for_source("src_test")) == 3

    def test_statistics(self):
        eng    = self._engine()
        eng.decide(_make_request())
        s = eng.statistics()
        assert s.total >= 1

    def test_register_policy(self):
        from iios.decisions import AllowlistTypePolicy
        eng = self._engine()
        eng.register_policy(AllowlistTypePolicy(["accept"]))
        assert any("allowlist" in n for n in eng.policy_names())

    def test_health_running(self):
        eng = self._engine()
        h   = eng.health()
        assert h["status"] in ("healthy", "degraded")

    def test_health_stopped(self):
        from iios.decisions import get_decision_engine
        eng = get_decision_engine()
        h   = eng.health()
        assert h["status"] == "stopped"

    def test_stats_has_version(self):
        eng = self._engine()
        s   = eng.stats()
        assert s["engine_version"] == "1.0.0"

    def test_async_decide(self):
        eng = self._engine()

        async def _run():
            return await eng.decide_async(_make_request())

        result = asyncio.run(_run())
        assert result.succeeded

    def test_version(self):
        from iios.decisions import DecisionEngine
        assert DecisionEngine.VERSION == "1.0.0"


# ─────────────────────────────────────────────────────────────────────────────
# 11. Monitoring
# ─────────────────────────────────────────────────────────────────────────────

class TestDecisionMonitor:
    def test_record_succeeded(self):
        from iios.decisions.monitoring.decision_monitor import get_decision_monitor
        from iios.decisions import DecisionResult
        mon    = get_decision_monitor()
        result = DecisionResult(succeeded=True, total_elapsed_ms=12.5)
        mon.record(result, source_id="src1")
        m = mon.source_metrics("src1")
        assert m is not None
        assert m.succeeded == 1

    def test_record_failed(self):
        from iios.decisions.monitoring.decision_monitor import get_decision_monitor
        from iios.decisions import DecisionResult
        mon    = get_decision_monitor()
        result = DecisionResult(succeeded=False, total_elapsed_ms=5.0, errors=["oops"])
        mon.record(result, source_id="src2")
        m = mon.source_metrics("src2")
        assert m.failed == 1

    def test_health(self):
        from iios.decisions.monitoring.decision_monitor import get_decision_monitor
        h = get_decision_monitor().health()
        assert "status" in h
        assert "total_decisions" in h

    def test_singleton(self):
        from iios.decisions.monitoring.decision_monitor import get_decision_monitor
        assert get_decision_monitor() is get_decision_monitor()


# ─────────────────────────────────────────────────────────────────────────────
# 12. Concurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_decisions(self):
        from iios.decisions import get_decision_engine
        eng = get_decision_engine()
        eng.initialize()
        errors: list = []
        results: list = []

        def _decide():
            try:
                r = eng.decide(_make_request(source_id="concurrent"))
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_decide) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 20

    def test_concurrent_registry_access(self):
        from iios.decisions.registry.decision_registry import get_decision_registry
        registries = []

        def _get():
            registries.append(get_decision_registry())

        threads = [threading.Thread(target=_get) for _ in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r is registries[0] for r in registries)


# ─────────────────────────────────────────────────────────────────────────────
# 13. Package imports
# ─────────────────────────────────────────────────────────────────────────────

class TestPackageImports:
    def test_all_symbols_importable(self):
        import iios.decisions as dec
        for sym in (
            "DecisionEngine", "get_decision_engine", "reset_decision_engine",
            "DecisionManager", "DecisionRequest", "Decision", "DecisionResult",
            "DecisionOption", "DecisionCandidate", "DecisionPolicy",
            "MinConfidencePolicy", "MaxRiskPolicy",
        ):
            assert hasattr(dec, sym), f"Missing: {sym}"

    def test_exception_hierarchy(self):
        from iios.decisions import (
            DecisionEngineError,
            DecisionNotFoundError,
            EngineNotInitializedError,
            NoCandidatesError,
        )
        assert issubclass(DecisionNotFoundError, DecisionEngineError)
        assert issubclass(EngineNotInitializedError, DecisionEngineError)
        assert issubclass(NoCandidatesError, DecisionEngineError)

    def test_decision_from_package(self):
        from iios.decisions import Decision, DecisionType
        d = Decision(decision_type=DecisionType.ACCEPT)
        assert d.decision_type == DecisionType.ACCEPT
