"""tests/unit/decision_governance/test_governance_engine.py"""
from __future__ import annotations

import asyncio
import threading

import pytest

from iios.decision_governance import (
    # constants
    AlertSeverity, ApprovalLevel, ApprovalMode, ApprovalStatus,
    AuditEventType, GovernanceMode, GovernanceStatus,
    PolicyType, PolicyViolationSeverity,
    GOVERNANCE_ENGINE_VERSION,
    # exceptions
    ApprovalDeniedError, ApprovalEscalatedError, ApprovalExpiredError,
    ApprovalNotFoundError, AuditNotFoundError, AuditReplayError,
    CertificationExpiredError, CertificationNotFoundError, CertificationRevokedError,
    ComplianceViolationError,
    EngineAlreadyRunningError, EngineNotInitializedError,
    GovernanceEngineError, GovernanceNotFoundError,
    PolicyAlreadyExistsError, PolicyInvalidError, PolicyNotFoundError,
    PolicyViolationError, RegistryOverflowError,
    # context
    GovernanceSubject, governance_session, gov_stage_scope, reset_governance_context,
    # policies
    CompositePolicy, GovernancePolicy, PolicyExecutionResult, PolicyExecutor,
    PolicyLoader, PolicyValidator, PolicyViolation,
    PredicatePolicy, ScoreThresholdPolicy,
    # approval
    ApprovalEngine, ApprovalManager, ApprovalPolicy, ApprovalRecord, ApprovalResult,
    ApprovalWorkflow, AutoApprovalPolicy, ConditionalApprovalPolicy,
    EscalationApprovalPolicy, ScoreThresholdApprovalPolicy, WorkflowStep,
    get_approval_manager, reset_approval_manager,
    # audit
    AuditEngine, AuditEvent, AuditHistory, AuditManager, AuditRegistry, AuditReport,
    build_audit_report, get_audit_manager, get_audit_registry,
    reset_audit_manager, reset_audit_registry,
    # certification
    CertificationEngine, CertificationRecord,
    # compliance
    ComplianceChecker, ComplianceResult, ComplianceViolation,
    # monitoring
    AlertHandler, DashboardSnapshot, DecisionDashboard, DecisionMonitor,
    GovernanceAlert, GovernanceAlerts, GovernanceMetrics,
    # history
    GovernanceHistory,
    # registry
    GovernanceRegistry, get_governance_registry, reset_governance_registry,
    # manager
    GovernanceFactory, GovernanceManager, GovernanceRequest, GovernanceResult,
    get_governance_manager, reset_governance_manager,
    # engine
    DecisionGovernanceEngine, get_decision_governance_engine,
    reset_decision_governance_engine,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _subject(decision_id: str = "d1", score: float = 0.8, **payload) -> GovernanceSubject:
    return GovernanceSubject(decision_id=decision_id, score=score, payload=payload)


def _score_policy(pid: str, threshold: float, blocking: bool = True) -> ScoreThresholdPolicy:
    return ScoreThresholdPolicy(
        policy_id=pid, name=pid, threshold=threshold, blocking=blocking
    )


def _auto_approval(pid: str = "auto") -> AutoApprovalPolicy:
    return AutoApprovalPolicy(policy_id=pid, name=pid)


def _threshold_approval(pid: str, threshold: float) -> ScoreThresholdApprovalPolicy:
    return ScoreThresholdApprovalPolicy(policy_id=pid, name=pid, threshold=threshold)


def _request(
    subject: GovernanceSubject | None = None,
    gov_policies: list | None = None,
    appr_policies: list | None = None,
    workflow: ApprovalWorkflow | None = None,
    mode: GovernanceMode = GovernanceMode.LENIENT,
) -> GovernanceRequest:
    return GovernanceRequest(
        subject=subject or _subject(),
        governance_policies=gov_policies or [],
        approval_policies=appr_policies or [],
        workflow=workflow,
        mode=mode,
    )


@pytest.fixture(autouse=True)
def _reset_all():
    reset_decision_governance_engine()
    reset_governance_manager()
    reset_governance_registry()
    reset_approval_manager()
    reset_audit_registry()
    reset_audit_manager()
    reset_governance_context()
    yield
    reset_decision_governance_engine()
    reset_governance_manager()
    reset_governance_registry()
    reset_approval_manager()
    reset_audit_registry()
    reset_audit_manager()
    reset_governance_context()


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_governance_status_values(self):
        assert GovernanceStatus.APPROVED.value  == "approved"
        assert GovernanceStatus.REJECTED.value  == "rejected"
        assert GovernanceStatus.ESCALATED.value == "escalated"

    def test_approval_level_values(self):
        assert ApprovalLevel.AUTO.value       == "auto"
        assert ApprovalLevel.ESCALATION.value == "escalation"

    def test_approval_mode_values(self):
        assert ApprovalMode.AUTOMATIC.value   == "automatic"
        assert ApprovalMode.MANUAL.value      == "manual"

    def test_policy_type_values(self):
        assert PolicyType.GOVERNANCE.value    == "governance"
        assert PolicyType.COMPLIANCE.value    == "compliance"

    def test_governance_mode_values(self):
        assert GovernanceMode.STRICT.value     == "strict"
        assert GovernanceMode.AUDIT_ONLY.value == "audit_only"

    def test_version(self):
        assert GOVERNANCE_ENGINE_VERSION == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# TestExceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_error(self):
        e = GovernanceEngineError("boom", "GA-999")
        assert "GA-999" in str(e)

    def test_policy_not_found(self):
        e = PolicyNotFoundError("p1")
        assert "p1" in str(e)
        assert e.code == "GA-041"

    def test_approval_not_found(self):
        e = ApprovalNotFoundError("a1")
        assert e.code == "GA-021"

    def test_audit_not_found(self):
        e = AuditNotFoundError("ev1")
        assert e.code == "GA-031"

    def test_engine_not_initialized(self):
        e = EngineNotInitializedError()
        assert "GA-051" in str(e)

    def test_engine_already_running(self):
        e = EngineAlreadyRunningError()
        assert "GA-052" in str(e)

    def test_registry_overflow(self):
        e = RegistryOverflowError(100)
        assert "100" in str(e)

    def test_certification_not_found(self):
        e = CertificationNotFoundError("c1")
        assert e.code == "GA-071"

    def test_compliance_violation(self):
        e = ComplianceViolationError("rule-X")
        assert "rule-X" in str(e)
        assert e.code == "GA-081"

    def test_hierarchy(self):
        assert issubclass(PolicyNotFoundError,      GovernanceEngineError)
        assert issubclass(EngineNotInitializedError, GovernanceEngineError)
        assert issubclass(CertificationRevokedError, GovernanceEngineError)


# ═══════════════════════════════════════════════════════════════════════════════
# TestGovernanceSubject
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceSubject:
    def test_defaults(self):
        s = GovernanceSubject()
        assert s.subject_id
        assert s.score == 0.0
        assert s.payload == {}

    def test_get_key(self):
        s = GovernanceSubject(payload={"risk": 0.3})
        assert s.get("risk") == pytest.approx(0.3)
        assert s.get("absent", -1) == -1

    def test_to_dict(self):
        s = _subject("d1", score=0.7)
        d = s.to_dict()
        assert d["decision_id"] == "d1"
        assert "score" in d

    def test_unique_ids(self):
        s1 = GovernanceSubject()
        s2 = GovernanceSubject()
        assert s1.subject_id != s2.subject_id


# ═══════════════════════════════════════════════════════════════════════════════
# TestGovernanceContextScope
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceContextScope:
    def test_session(self):
        with governance_session("src", GovernanceMode.STRICT) as ctx:
            assert ctx.source_id == "src"
            assert ctx.mode == GovernanceMode.STRICT

    def test_stage_scope(self):
        with governance_session() as ctx:
            assert ctx.current_stage == ""
            with gov_stage_scope("policy"):
                assert ctx.current_stage == "policy"
            assert ctx.current_stage == ""

    def test_diagnostics(self):
        with governance_session() as ctx:
            ctx.add_diagnostic("WARNING", "w1")
            ctx.add_diagnostic("ERROR",   "e1")
            assert len(ctx.warnings()) == 1
            assert len(ctx.errors())   == 1

    def test_elapsed(self):
        import time
        with governance_session() as ctx:
            time.sleep(0.01)
            assert ctx.elapsed_ms() > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestGovernancePolicy
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernancePolicy:
    def test_score_policy_pass(self):
        p = _score_policy("p1", 0.5)
        assert p.validate(_subject(score=0.8)) is None

    def test_score_policy_fail(self):
        p = _score_policy("p1", 0.5)
        v = p.validate(_subject(score=0.3))
        assert v is not None
        assert v.is_blocking

    def test_score_policy_non_blocking(self):
        p = _score_policy("p1", 0.5, blocking=False)
        v = p.validate(_subject(score=0.3))
        assert v is not None
        assert not v.is_blocking

    def test_predicate_policy_pass(self):
        p = PredicatePolicy("p2", "P2", lambda s: s.score > 0.5)
        assert p.validate(_subject(score=0.9)) is None

    def test_predicate_policy_fail(self):
        p = PredicatePolicy("p2", "P2", lambda s: s.score > 0.5)
        v = p.validate(_subject(score=0.1))
        assert v is not None

    def test_composite_policy_first_fail(self):
        p1   = _score_policy("s1", 0.9)
        p2   = _score_policy("s2", 0.5)
        comp = CompositePolicy("c1", "C1", [p1, p2])
        v    = comp.validate(_subject(score=0.7))
        assert v is not None
        assert "s1" in v.message

    def test_policy_to_dict(self):
        p = _score_policy("p1", 0.5)
        d = p.to_dict()
        assert d["policy_id"] == "p1"


# ═══════════════════════════════════════════════════════════════════════════════
# TestPolicyExecutor
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyExecutor:
    def test_all_pass(self):
        exe    = PolicyExecutor()
        result = exe.execute(_subject(score=0.9), [_score_policy("p1", 0.5)])
        assert result.passed
        assert result.policies_evaluated == 1

    def test_blocking_violation(self):
        exe    = PolicyExecutor()
        result = exe.execute(_subject(score=0.1), [_score_policy("p1", 0.5)])
        assert not result.passed
        assert result.blocking_violations == 1

    def test_non_blocking_still_passes(self):
        exe    = PolicyExecutor()
        p      = _score_policy("p1", 0.5, blocking=False)
        result = exe.execute(_subject(score=0.1), [p])
        assert result.passed  # non-blocking → no blocking violation
        assert result.warning_violations == 1

    def test_execution_result_to_dict(self):
        exe    = PolicyExecutor()
        result = exe.execute(_subject(), [])
        d      = result.to_dict()
        assert "result_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestPolicyValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyValidator:
    def test_valid_policy(self):
        val = PolicyValidator()
        assert val.is_valid(_score_policy("p1", 0.5))

    def test_not_a_policy(self):
        val = PolicyValidator()
        with pytest.raises(PolicyInvalidError):
            val.validate(object())  # type: ignore[arg-type]

    def test_is_valid_false(self):
        val = PolicyValidator()
        assert not val.is_valid(object())  # type: ignore[arg-type]


# ═══════════════════════════════════════════════════════════════════════════════
# TestPolicyLoader
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyLoader:
    def test_load_score_threshold(self):
        cfg    = {"policy_id": "p1", "name": "P1", "type": "score_threshold", "threshold": 0.6}
        policy = PolicyLoader.load(cfg)
        assert policy.policy_id == "p1"
        assert policy.validate(_subject(score=0.7)) is None

    def test_load_predicate(self):
        cfg    = {"policy_id": "p2", "name": "P2", "type": "predicate"}
        policy = PolicyLoader.load(cfg, predicate=lambda s: s.score > 0)
        assert policy.validate(_subject(score=0.5)) is None

    def test_unknown_type_raises(self):
        cfg = {"policy_id": "px", "name": "PX", "type": "nonexistent"}
        with pytest.raises(PolicyInvalidError):
            PolicyLoader.load(cfg)

    def test_missing_threshold_raises(self):
        cfg = {"policy_id": "px", "name": "PX", "type": "score_threshold"}
        with pytest.raises(PolicyInvalidError):
            PolicyLoader.load(cfg)

    def test_load_many(self):
        cfgs = [
            {"policy_id": "p1", "name": "P1", "type": "score_threshold", "threshold": 0.3},
            {"policy_id": "p2", "name": "P2", "type": "score_threshold", "threshold": 0.4},
        ]
        policies = PolicyLoader.load_many(cfgs)
        assert len(policies) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TestApprovalPolicy
# ═══════════════════════════════════════════════════════════════════════════════

class TestApprovalPolicy:
    def test_auto_approval(self):
        ap  = _auto_approval()
        rec = ap.evaluate(_subject())
        assert rec.status == ApprovalStatus.APPROVED

    def test_threshold_approval_pass(self):
        ap  = _threshold_approval("ap1", 0.5)
        rec = ap.evaluate(_subject(score=0.8))
        assert rec.status == ApprovalStatus.APPROVED

    def test_threshold_approval_reject(self):
        ap  = _threshold_approval("ap1", 0.5)
        rec = ap.evaluate(_subject(score=0.2))
        assert rec.status == ApprovalStatus.REJECTED

    def test_conditional_approval_pass(self):
        ap  = ConditionalApprovalPolicy("ca1", "CA1", lambda s: s.score > 0.5)
        rec = ap.evaluate(_subject(score=0.9))
        assert rec.status == ApprovalStatus.APPROVED

    def test_escalation_policy(self):
        ap  = EscalationApprovalPolicy("esc1", "ESC1")
        rec = ap.evaluate(_subject())
        assert rec.status == ApprovalStatus.ESCALATED
        assert rec.level  == ApprovalLevel.ESCALATION

    def test_record_to_dict(self):
        ap  = _auto_approval()
        rec = ap.evaluate(_subject())
        d   = rec.to_dict()
        assert "record_id" in d
        assert d["status"] == "approved"


# ═══════════════════════════════════════════════════════════════════════════════
# TestApprovalWorkflow
# ═══════════════════════════════════════════════════════════════════════════════

class TestApprovalWorkflow:
    def test_all_approve(self):
        wf = ApprovalWorkflow("wf1", "WF1")
        wf.add_step(_threshold_approval("a1", 0.5), order=1)
        wf.add_step(_auto_approval("a2"), order=2)
        res = wf.execute(_subject(score=0.9))
        assert res.approved

    def test_required_rejection_stops(self):
        wf = ApprovalWorkflow()
        wf.add_step(_threshold_approval("a1", 0.9), order=1, required=True)
        wf.add_step(_auto_approval("a2"), order=2)
        res = wf.execute(_subject(score=0.2))
        assert not res.approved
        assert res.status == ApprovalStatus.REJECTED
        # Should have stopped after first step
        assert len(res.records) == 1

    def test_optional_rejection_continues(self):
        wf = ApprovalWorkflow()
        wf.add_step(_threshold_approval("a1", 0.9), order=1, required=False)
        wf.add_step(_auto_approval("a2"), order=2)
        res = wf.execute(_subject(score=0.2))
        assert res.approved  # second step approves

    def test_escalation_counted(self):
        wf = ApprovalWorkflow()
        wf.add_step(EscalationApprovalPolicy("esc1", "E1"), order=1, required=True)
        res = wf.execute(_subject())
        assert res.escalations == 1
        assert res.status == ApprovalStatus.ESCALATED


# ═══════════════════════════════════════════════════════════════════════════════
# TestApprovalEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestApprovalEngine:
    def test_evaluate_all_approve(self):
        eng = ApprovalEngine()
        res = eng.evaluate(_subject(score=0.9), [_threshold_approval("a1", 0.5)])
        assert res.approved

    def test_evaluate_one_reject(self):
        eng = ApprovalEngine()
        res = eng.evaluate(_subject(score=0.1), [_threshold_approval("a1", 0.5)])
        assert not res.approved
        assert res.status == ApprovalStatus.REJECTED

    def test_evaluate_escalation(self):
        eng = ApprovalEngine()
        res = eng.evaluate(_subject(), [EscalationApprovalPolicy("e1", "E1")])
        assert res.status == ApprovalStatus.ESCALATED
        assert res.escalations == 1

    def test_manual_approve(self):
        eng       = ApprovalEngine()
        initial   = eng.evaluate(_subject(), [EscalationApprovalPolicy("e1", "E1")])
        overridden = eng.approve_manual(initial, "admin", "reviewed")
        assert overridden.approved
        assert any(r.approver == "admin" for r in overridden.records)

    def test_manual_reject(self):
        eng       = ApprovalEngine()
        initial   = eng.evaluate(_subject(), [EscalationApprovalPolicy("e1", "E1")])
        overridden = eng.reject_manual(initial, "admin", "risky")
        assert not overridden.approved
        assert overridden.status == ApprovalStatus.REJECTED


# ═══════════════════════════════════════════════════════════════════════════════
# TestApprovalManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestApprovalManager:
    def test_store_and_get(self):
        mgr = ApprovalManager()
        res = ApprovalResult(decision_id="d1", approved=True)
        mgr.store(res)
        fetched = mgr.get(res.result_id)
        assert fetched.result_id == res.result_id

    def test_not_found_raises(self):
        mgr = ApprovalManager()
        with pytest.raises(ApprovalNotFoundError):
            mgr.get("ghost")

    def test_pending_escalated(self):
        mgr = ApprovalManager()
        e   = ApprovalResult(decision_id="d1", status=ApprovalStatus.ESCALATED, approved=False)
        a   = ApprovalResult(decision_id="d2", status=ApprovalStatus.APPROVED,  approved=True)
        mgr.store(e)
        mgr.store(a)
        pending = mgr.pending()
        assert len(pending) == 1
        assert pending[0].result_id == e.result_id

    def test_singleton(self):
        m1 = get_approval_manager()
        m2 = get_approval_manager()
        assert m1 is m2


# ═══════════════════════════════════════════════════════════════════════════════
# TestAuditEvent
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditEvent:
    def test_defaults(self):
        ev = AuditEvent()
        assert ev.event_id
        assert ev.event_type == AuditEventType.SUBMITTED

    def test_to_dict(self):
        ev = AuditEvent(decision_id="d1", event_type=AuditEventType.APPROVED)
        d  = ev.to_dict()
        assert d["decision_id"] == "d1"
        assert d["event_type"]  == "approved"

    def test_unique_ids(self):
        e1 = AuditEvent()
        e2 = AuditEvent()
        assert e1.event_id != e2.event_id


# ═══════════════════════════════════════════════════════════════════════════════
# TestAuditHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditHistory:
    def test_record_and_get(self):
        h  = AuditHistory()
        ev = AuditEvent(decision_id="d1")
        h.record(ev)
        assert h.get(ev.event_id).event_id == ev.event_id

    def test_not_found_raises(self):
        h = AuditHistory()
        with pytest.raises(AuditNotFoundError):
            h.get("ghost")

    def test_duplicate_raises(self):
        h  = AuditHistory()
        ev = AuditEvent(decision_id="d1")
        h.record(ev)
        with pytest.raises(Exception):  # AuditAlreadyExistsError
            h.record(ev)

    def test_by_decision(self):
        h = AuditHistory()
        h.record(AuditEvent(decision_id="d1"))
        h.record(AuditEvent(decision_id="d1"))
        h.record(AuditEvent(decision_id="d2"))
        assert len(h.by_decision("d1")) == 2
        assert len(h.by_decision("d2")) == 1

    def test_replay(self):
        h = AuditHistory()
        h.record(AuditEvent(decision_id="d1"))
        events = h.replay("d1")
        assert len(events) == 1

    def test_replay_unknown_raises(self):
        h = AuditHistory()
        with pytest.raises(AuditReplayError):
            h.replay("ghost")

    def test_compare(self):
        h = AuditHistory()
        h.record(AuditEvent(decision_id="d1", event_type=AuditEventType.APPROVED))
        h.record(AuditEvent(decision_id="d2", event_type=AuditEventType.REJECTED))
        cmp = h.compare("d1", "d2")
        assert "unique_to_a" in cmp
        assert "approved" in cmp["event_types_a"]


# ═══════════════════════════════════════════════════════════════════════════════
# TestAuditRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditRegistry:
    def test_register_and_get(self):
        reg = AuditRegistry()
        ev  = AuditEvent(decision_id="d1")
        reg.register(ev)
        assert len(reg.get("d1")) == 1

    def test_has(self):
        reg = AuditRegistry()
        reg.register(AuditEvent(decision_id="d1"))
        assert reg.has("d1")
        assert not reg.has("d9")

    def test_not_found_raises(self):
        reg = AuditRegistry()
        with pytest.raises(AuditNotFoundError):
            reg.get("ghost")

    def test_singleton(self):
        r1 = get_audit_registry()
        r2 = get_audit_registry()
        assert r1 is r2


# ═══════════════════════════════════════════════════════════════════════════════
# TestAuditReport
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditReport:
    def test_build_report(self):
        events = [
            AuditEvent(decision_id="d1", event_type=AuditEventType.SUBMITTED),
            AuditEvent(decision_id="d1", event_type=AuditEventType.APPROVED),
        ]
        report = build_audit_report("d1", events)
        assert report.event_count == 2
        assert report.decision_id == "d1"

    def test_summary_counts(self):
        events = [
            AuditEvent(decision_id="d1", event_type=AuditEventType.SUBMITTED),
            AuditEvent(decision_id="d1", event_type=AuditEventType.APPROVED),
        ]
        report = build_audit_report("d1", events)
        assert report.summary["total_events"] == 2

    def test_to_dict(self):
        report = build_audit_report("d1", [])
        d      = report.to_dict()
        assert "report_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestAuditEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditEngine:
    def test_record_submission(self):
        eng = AuditEngine()
        ev  = eng.record_submission(_subject("d1"))
        assert ev.event_type == AuditEventType.SUBMITTED
        assert ev.decision_id == "d1"

    def test_record_event(self):
        eng = AuditEngine()
        ev  = eng.record_event("d1", AuditEventType.APPROVED)
        assert ev.event_type == AuditEventType.APPROVED

    def test_build_report(self):
        eng = AuditEngine()
        eng.record_submission(_subject("d2"))
        report = eng.build_report("d2")
        assert report.event_count == 1

    def test_replay(self):
        eng = AuditEngine()
        eng.record_submission(_subject("d3"))
        events = eng.replay("d3")
        assert len(events) == 1

    def test_compare(self):
        eng = AuditEngine()
        eng.record_event("dx", AuditEventType.APPROVED)
        eng.record_event("dy", AuditEventType.REJECTED)
        cmp = eng.compare("dx", "dy")
        assert "unique_to_a" in cmp


# ═══════════════════════════════════════════════════════════════════════════════
# TestCertificationEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestCertificationEngine:
    def test_issue(self):
        eng  = CertificationEngine()
        cert = eng.issue("d1", "s1", basis="approved")
        assert cert.is_valid()
        assert cert.decision_id == "d1"

    def test_get(self):
        eng  = CertificationEngine()
        cert = eng.issue("d1", "s1")
        fetched = eng.get(cert.cert_id)
        assert fetched.cert_id == cert.cert_id

    def test_not_found_raises(self):
        eng = CertificationEngine()
        with pytest.raises(CertificationNotFoundError):
            eng.get("ghost")

    def test_revoke(self):
        eng  = CertificationEngine()
        cert = eng.issue("d1", "s1")
        eng.revoke(cert.cert_id, reason="test")
        assert not eng.is_valid(cert.cert_id)

    def test_double_revoke_raises(self):
        eng  = CertificationEngine()
        cert = eng.issue("d1", "s1")
        eng.revoke(cert.cert_id)
        with pytest.raises(CertificationRevokedError):
            eng.revoke(cert.cert_id)

    def test_statistics(self):
        eng  = CertificationEngine()
        c1   = eng.issue("d1", "s1")
        c2   = eng.issue("d2", "s2")
        eng.revoke(c1.cert_id)
        s = eng.statistics()
        assert s["total"]   == 2
        assert s["revoked"] == 1
        assert s["valid"]   == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestComplianceChecker
# ═══════════════════════════════════════════════════════════════════════════════

class TestComplianceChecker:
    def test_no_rules_passes(self):
        cc  = ComplianceChecker()
        res = cc.check(_subject())
        assert res.passed
        assert res.rules_checked == 0

    def test_rule_pass(self):
        cc = ComplianceChecker()
        cc.add_rule("r1", "R1", lambda s: None)   # None = no violation
        res = cc.check(_subject())
        assert res.passed

    def test_rule_violation(self):
        cc = ComplianceChecker()
        cc.add_rule("r1", "R1", lambda s: ComplianceViolation(message="bad"))
        res = cc.check(_subject())
        assert not res.passed
        assert len(res.violations) == 1

    def test_to_dict(self):
        cc  = ComplianceChecker()
        res = cc.check(_subject())
        d   = res.to_dict()
        assert "result_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestGovernanceMetrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceMetrics:
    def test_rates_zero_when_empty(self):
        m = GovernanceMetrics()
        assert m.approval_rate  == 0.0
        assert m.rejection_rate == 0.0

    def test_approval_rate(self):
        m = GovernanceMetrics(total_submitted=10, approved=8)
        assert m.approval_rate == pytest.approx(0.8)

    def test_to_dict(self):
        m = GovernanceMetrics(total_submitted=5)
        d = m.to_dict()
        assert d["total_submitted"] == 5


# ═══════════════════════════════════════════════════════════════════════════════
# TestGovernanceAlerts
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceAlerts:
    def test_raise_alert(self):
        ga = GovernanceAlerts()
        alert = ga.raise_alert(AlertSeverity.WARNING, "test")
        assert ga.count() == 1
        assert alert.severity == AlertSeverity.WARNING

    def test_handler_called(self):
        received = []
        ga = GovernanceAlerts()
        ga.add_handler(received.append)
        ga.raise_alert(AlertSeverity.INFO, "ping")
        assert len(received) == 1

    def test_acknowledge(self):
        ga    = GovernanceAlerts()
        alert = ga.raise_alert(AlertSeverity.INFO, "x")
        ga.acknowledge(alert.alert_id)
        assert ga.unacknowledged() == []

    def test_handler_exception_ignored(self):
        """Handlers that throw must never crash the engine."""
        ga = GovernanceAlerts()
        ga.add_handler(lambda _: (_ for _ in ()).throw(RuntimeError("boom")))  # type: ignore[attr-defined]
        # Should not raise
        ga.raise_alert(AlertSeverity.ERROR, "test")


# ═══════════════════════════════════════════════════════════════════════════════
# TestDecisionMonitor
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionMonitor:
    def test_sample_once(self):
        mon = DecisionMonitor(sampler=lambda: {"x": 1}, interval_seconds=60)
        s   = mon.sample_once()
        assert s["x"] == 1
        assert "sampled_at" in s

    def test_start_stop(self):
        mon = DecisionMonitor(sampler=lambda: {}, interval_seconds=0.05)
        mon.start()
        assert mon.is_running
        mon.stop()
        # after stop is_running should be False
        assert not mon.is_running


# ═══════════════════════════════════════════════════════════════════════════════
# TestGovernanceRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceRegistry:
    def test_register_and_get_policy(self):
        reg = GovernanceRegistry()
        reg.register_policy(_score_policy("p1", 0.5))
        assert reg.has_policy("p1")
        assert reg.get_policy("p1").policy_id == "p1"

    def test_duplicate_raises(self):
        reg = GovernanceRegistry()
        reg.register_policy(_score_policy("p1", 0.5))
        with pytest.raises(PolicyAlreadyExistsError):
            reg.register_policy(_score_policy("p1", 0.6))

    def test_overwrite(self):
        reg = GovernanceRegistry()
        reg.register_policy(_score_policy("p1", 0.5))
        reg.register_policy(_score_policy("p1", 0.9), overwrite=True)
        # No exception expected

    def test_register_workflow(self):
        reg = GovernanceRegistry()
        wf  = ApprovalWorkflow("wf1", "WF1")
        reg.register_workflow(wf)
        assert reg.has_workflow("wf1")

    def test_singleton(self):
        r1 = get_governance_registry()
        r2 = get_governance_registry()
        assert r1 is r2

    def test_statistics(self):
        reg = GovernanceRegistry()
        reg.register_policy(_score_policy("p1", 0.5))
        s   = reg.statistics()
        assert s["governance_policies"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestGovernanceManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceManager:
    def test_govern_auto_approve(self):
        mgr    = GovernanceManager()
        result = mgr.govern(_request(_subject(score=0.8)))
        assert result.approved
        assert result.status == GovernanceStatus.APPROVED

    def test_govern_policy_rejection_strict(self):
        mgr    = GovernanceManager()
        req    = _request(
            _subject(score=0.1),
            gov_policies=[_score_policy("p1", 0.5)],
            mode=GovernanceMode.STRICT,
        )
        result = mgr.govern(req)
        assert not result.approved
        assert result.status == GovernanceStatus.REJECTED

    def test_govern_lenient_continues_despite_violation(self):
        mgr    = GovernanceManager()
        req    = _request(
            _subject(score=0.1),
            gov_policies=[_score_policy("p1", 0.5)],
            appr_policies=[_auto_approval()],
            mode=GovernanceMode.LENIENT,
        )
        result = mgr.govern(req)
        # Lenient + auto-approve → approved
        assert result.approved

    def test_govern_approval_rejection(self):
        mgr    = GovernanceManager()
        req    = _request(
            _subject(score=0.1),
            appr_policies=[_threshold_approval("ap1", 0.9)],
        )
        result = mgr.govern(req)
        assert not result.approved
        assert result.status == GovernanceStatus.REJECTED

    def test_govern_bypass(self):
        mgr    = GovernanceManager()
        req    = _request(
            _subject(score=0.0),
            gov_policies=[_score_policy("p1", 0.9)],   # would normally reject
            mode=GovernanceMode.BYPASS,
        )
        result = mgr.govern(req)
        assert result.approved

    def test_govern_audit_only(self):
        mgr    = GovernanceManager()
        req    = _request(
            _subject(score=0.0),
            gov_policies=[_score_policy("p1", 0.9)],   # would normally reject
            mode=GovernanceMode.AUDIT_ONLY,
        )
        result = mgr.govern(req)
        assert result.approved

    def test_certification_issued_on_approval(self):
        mgr    = GovernanceManager()
        result = mgr.govern(_request(_subject()))
        assert result.certification is not None
        assert result.certification.is_valid()

    def test_get_result(self):
        mgr    = GovernanceManager()
        result = mgr.govern(_request(_subject()))
        fetched = mgr.get(result.result_id)
        assert fetched.result_id == result.result_id

    def test_not_found_raises(self):
        mgr = GovernanceManager()
        with pytest.raises(GovernanceNotFoundError):
            mgr.get("ghost")

    def test_statistics(self):
        mgr = GovernanceManager()
        mgr.govern(_request(_subject()))
        s = mgr.statistics()
        assert s["total"] == 1
        assert s["approved"] == 1

    def test_escalation_sets_status(self):
        mgr = GovernanceManager()
        req = _request(
            _subject(),
            appr_policies=[EscalationApprovalPolicy("e1", "E1")],
        )
        result = mgr.govern(req)
        assert result.status == GovernanceStatus.ESCALATED

    def test_singleton(self):
        m1 = get_governance_manager()
        m2 = get_governance_manager()
        assert m1 is m2


# ═══════════════════════════════════════════════════════════════════════════════
# TestDecisionGovernanceEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionGovernanceEngine:
    def test_initialize_and_running(self):
        eng = DecisionGovernanceEngine()
        assert not eng.is_running
        eng.initialize()
        assert eng.is_running

    def test_double_init_raises(self):
        eng = DecisionGovernanceEngine()
        eng.initialize()
        with pytest.raises(EngineAlreadyRunningError):
            eng.initialize()

    def test_not_initialized_raises(self):
        eng = DecisionGovernanceEngine()
        with pytest.raises(EngineNotInitializedError):
            eng.govern(_request())

    def test_shutdown(self):
        eng = DecisionGovernanceEngine()
        eng.initialize()
        eng.shutdown()
        assert not eng.is_running

    def test_govern(self):
        eng = DecisionGovernanceEngine()
        eng.initialize()
        result = eng.govern(_request(_subject()))
        assert result.approved

    def test_certify_shortcut(self):
        eng = DecisionGovernanceEngine()
        eng.initialize()
        result = eng.certify(_subject(score=0.9))
        assert result.approved
        assert result.certification is not None

    def test_govern_async(self):
        eng = DecisionGovernanceEngine()
        eng.initialize()

        async def _run():
            return await eng.govern_async(_request(_subject()))

        result = asyncio.run(_run())
        assert result.approved

    def test_register_policy(self):
        eng = DecisionGovernanceEngine()
        eng.initialize()
        p   = _score_policy("custom_p", 0.5)
        eng.register_policy(p)
        assert get_governance_registry().has_policy("custom_p")

    def test_register_approval(self):
        eng = DecisionGovernanceEngine()
        eng.initialize()
        ap  = _auto_approval("custom_ap")
        eng.register_approval(ap)
        assert get_governance_registry().has_approval("custom_ap")

    def test_register_workflow(self):
        eng = DecisionGovernanceEngine()
        eng.initialize()
        wf  = ApprovalWorkflow("wf_custom", "Custom WF")
        eng.register_workflow(wf)
        assert get_governance_registry().has_workflow("wf_custom")

    def test_health(self):
        eng = DecisionGovernanceEngine()
        eng.initialize()
        h   = eng.health()
        assert h["running"]  is True
        assert h["version"]  == "1.0.0"

    def test_stats(self):
        eng = DecisionGovernanceEngine()
        eng.initialize()
        s   = eng.stats()
        assert s["version"] == "1.0.0"

    def test_singleton(self):
        e1 = get_decision_governance_engine()
        e2 = get_decision_governance_engine()
        assert e1 is e2


# ═══════════════════════════════════════════════════════════════════════════════
# TestGovernanceHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceHistory:
    def test_store_and_get(self):
        h   = GovernanceHistory()
        res = GovernanceResult(request_id="r1")
        h.store(res)
        fetched = h.get(res.result_id)
        assert fetched.result_id == res.result_id  # type: ignore[union-attr]

    def test_not_found_raises(self):
        h = GovernanceHistory()
        with pytest.raises(GovernanceNotFoundError):
            h.get("ghost")

    def test_recent(self):
        h = GovernanceHistory()
        for _ in range(5):
            h.store(GovernanceResult())
        assert len(h.recent(3)) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# TestGovernanceFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceFactory:
    def test_make_subject(self):
        s = GovernanceFactory.make_subject("d1", score=0.7, tag="x")
        assert s.decision_id == "d1"
        assert s.score       == pytest.approx(0.7)
        assert s.get("tag")  == "x"

    def test_make_score_policy(self):
        p = GovernanceFactory.make_score_policy("p1", "P1", 0.6)
        assert p.validate(_subject(score=0.7)) is None
        assert p.validate(_subject(score=0.5)) is not None

    def test_make_auto_approval(self):
        ap  = GovernanceFactory.make_auto_approval()
        rec = ap.evaluate(_subject())
        assert rec.status == ApprovalStatus.APPROVED

    def test_make_threshold_approval(self):
        ap = GovernanceFactory.make_threshold_approval("ap1", "AP1", 0.5)
        assert ap.evaluate(_subject(score=0.9)).status == ApprovalStatus.APPROVED
        assert ap.evaluate(_subject(score=0.1)).status == ApprovalStatus.REJECTED

    def test_make_request(self):
        req = GovernanceFactory.make_request(_subject())
        assert isinstance(req, GovernanceRequest)
        assert req.subject is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TestDecisionDashboard
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionDashboard:
    def test_render(self):
        db  = DecisionDashboard()
        snap = db.render({"total_submitted": 5, "approved": 4, "rejected": 1})
        assert snap.total_submitted == 5
        assert snap.approved        == 4

    def test_to_dict(self):
        db   = DecisionDashboard()
        snap = db.render({})
        d    = snap.to_dict()
        assert "total_submitted" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestConcurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_governance(self):
        mgr     = GovernanceManager()
        results = []
        errors  = []

        def _run(i: int):
            try:
                req = _request(_subject(f"d{i}", score=0.7 + i * 0.01))
                results.append(mgr.govern(req))
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_run, args=(i,)) for i in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors)  == 0
        assert len(results) == 15
        assert all(r.succeeded for r in results)

    def test_concurrent_registry(self):
        reg    = GovernanceRegistry()
        errors = []

        def _reg(i: int):
            try:
                reg.register_policy(_score_policy(f"p{i}", 0.5), overwrite=True)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=_reg, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestPackageImports
# ═══════════════════════════════════════════════════════════════════════════════

class TestPackageImports:
    def test_all_symbols_importable(self):
        import iios.decision_governance as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing: {name}"

    def test_exception_hierarchy(self):
        assert issubclass(PolicyNotFoundError,       GovernanceEngineError)
        assert issubclass(EngineAlreadyRunningError,  GovernanceEngineError)
        assert issubclass(CertificationRevokedError,  GovernanceEngineError)

    def test_version(self):
        import iios.decision_governance as pkg
        assert pkg.__version__ == "1.0.0"
