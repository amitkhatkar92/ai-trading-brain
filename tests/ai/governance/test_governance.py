"""
test_governance.py
===================
Comprehensive test suite for the A8 AI Governance Platform.

Coverage:
  1.  Exceptions (all 26 error classes)
  2.  Core types (GovernanceMetadata, GovernanceContext, GovernanceDecision, GovernancePolicy)
  3.  Events (13 event types + GovernanceEventBus)
  4.  Policy layer (PolicyRule, PolicyRegistry, PolicyEngine)
  5.  Permissions layer (RolePolicy, CapabilityRestriction, AccessControl, PermissionManager)
  6.  Audit layer (AuditRecord integrity, AuditHistory, AuditReport, AuditManager)
  7.  Explainability layer (EvidenceReference, DecisionTrace, Explanation, ExplainabilityManager)
  8.  Compliance layer (ComplianceRule, ComplianceResult, ComplianceReport, ComplianceManager)
  9.  Risk governance (RiskThreshold, RiskPolicy, RiskViolation, GovernanceRiskManager)
  10. GovernanceManager (integrated pipeline)
  11. Snapshot layer
  12. Container
  13. Gateway (lifecycle + all public APIs)
"""
from __future__ import annotations

import time
import uuid

import pytest

# ── imports ───────────────────────────────────────────────────────────────────

from iios.ai.governance.exceptions.governance_exceptions import (
    AIGovernanceException,
    AIPolicyException, AIPolicyNotFoundError, AIPolicyAlreadyExistsError,
    AIPolicyViolationError, AIPolicyEvaluationError, AIPolicyConflictError,
    AIPermissionException, AIPermissionDeniedError, AIRoleNotFoundError,
    AIRoleAlreadyExistsError, AICapabilityRestrictionError,
    AIAuditException, AIAuditRecordNotFoundError, AIAuditReportError,
    AIExplainabilityException, AIExplanationNotFoundError, AIDecisionTraceError,
    AIComplianceException, AIComplianceRuleNotFoundError,
    AIComplianceViolationError, AIComplianceReportError,
    AIRiskGovernanceException, AIRiskThresholdExceededError,
    AIRiskPolicyNotFoundError, AIEscalationRequiredError,
    AIGovernancePolicyException, AIGovernancePolicyViolationError,
)

from iios.ai.governance.core import (
    GovernanceStatus, GovernanceSeverity, GovernanceDomain, GovernanceMetadata,
    GovernanceContext,
    GovernanceDecisionType, GovernanceDecision,
    PolicyEffect, PolicyScope, GovernancePolicy,
)

from iios.ai.governance.events import (
    GovernanceEventType, GovernanceEvent,
    PolicyEvaluatedEvent, PolicyViolatedEvent, PolicyRegisteredEvent,
    PermissionGrantedEvent, PermissionDeniedEvent,
    AuditRecordedEvent,
    ExplanationGeneratedEvent,
    ComplianceCheckedEvent, ComplianceViolatedEvent,
    GovernanceDecisionIssuedEvent,
    RiskThresholdExceededEvent, EscalationTriggeredEvent,
    GovernanceEventBus,
)

from iios.ai.governance.policy import (
    RuleOperator, PolicyRule, PolicyEvaluation, PolicyViolation,
    PolicyRegistry,
    PolicyEngine,
)

from iios.ai.governance.permissions import (
    RolePolicy, CapabilityRestriction, AccessControl,
    PermissionManager,
)

from iios.ai.governance.audit import (
    AuditEventType, AuditRecord, AuditEvent,
    AuditHistory, AuditReport, AuditManager,
)

from iios.ai.governance.explainability import (
    EvidenceReference, DecisionTrace, Explanation, ExplainabilityManager,
)

from iios.ai.governance.compliance import (
    ComplianceFramework, ComplianceRule, ComplianceResult,
    ComplianceReport, ComplianceManager,
)

from iios.ai.governance.risk import (
    RiskCategory, RiskThreshold, RiskPolicy, RiskViolation,
    GovernanceRiskManager,
)

from iios.ai.governance.snapshot import PolicySnapshot, GovernanceFrameworkSnapshot
from iios.ai.governance.container import GovernanceContainer
from iios.ai.governance.gateway   import GovernanceGateway


# ── helpers ───────────────────────────────────────────────────────────────────

def _ctx(action: str = "model.invoke", resource: str = "model_abc",
         principal: str = "agent_x") -> GovernanceContext:
    return GovernanceContext.create(action, resource, principal)

def _policy(effect: PolicyEffect = PolicyEffect.ALLOW,
            action: str = "*") -> GovernancePolicy:
    return GovernancePolicy.create(
        name       = f"policy_{uuid.uuid4().hex[:6]}",
        scope      = PolicyScope.GLOBAL,
        effect     = effect,
        actions    = frozenset({action}),
    )


# ═════════════════════════════════════════════════════════════════════════════
# 1. EXCEPTIONS
# ═════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base(self):
        ex = AIGovernanceException("test")
        assert ex.error_code == "AI-1300"
        assert "AI-1300" in ex.message

    def test_policy_not_found(self):
        ex = AIPolicyNotFoundError("p")
        assert ex.error_code == "AI-1311"
        assert isinstance(ex, AIPolicyException)

    def test_policy_already_exists(self):
        assert AIPolicyAlreadyExistsError("p").error_code == "AI-1312"

    def test_policy_violation(self):
        assert AIPolicyViolationError("p").error_code == "AI-1313"

    def test_policy_evaluation_error(self):
        assert AIPolicyEvaluationError("p").error_code == "AI-1314"

    def test_policy_conflict(self):
        assert AIPolicyConflictError("p").error_code == "AI-1315"

    def test_permission_denied(self):
        ex = AIPermissionDeniedError("access denied")
        assert ex.error_code == "AI-1321"
        assert isinstance(ex, AIPermissionException)

    def test_role_not_found(self):
        assert AIRoleNotFoundError("r").error_code == "AI-1322"

    def test_role_already_exists(self):
        assert AIRoleAlreadyExistsError("r").error_code == "AI-1323"

    def test_capability_restriction(self):
        assert AICapabilityRestrictionError("c").error_code == "AI-1324"

    def test_audit_not_found(self):
        assert AIAuditRecordNotFoundError("a").error_code == "AI-1331"

    def test_audit_report_error(self):
        assert AIAuditReportError("a").error_code == "AI-1332"

    def test_explanation_not_found(self):
        assert AIExplanationNotFoundError("e").error_code == "AI-1341"

    def test_decision_trace_error(self):
        assert AIDecisionTraceError("d").error_code == "AI-1342"

    def test_compliance_rule_not_found(self):
        assert AIComplianceRuleNotFoundError("c").error_code == "AI-1351"

    def test_compliance_violation(self):
        assert AIComplianceViolationError("c").error_code == "AI-1352"

    def test_compliance_report_error(self):
        assert AIComplianceReportError("c").error_code == "AI-1353"

    def test_risk_threshold_exceeded(self):
        ex = AIRiskThresholdExceededError("r")
        assert ex.error_code == "AI-1361"
        assert isinstance(ex, AIRiskGovernanceException)

    def test_risk_policy_not_found(self):
        assert AIRiskPolicyNotFoundError("r").error_code == "AI-1362"

    def test_escalation_required(self):
        assert AIEscalationRequiredError("e").error_code == "AI-1363"

    def test_governance_policy_violation(self):
        ex = AIGovernancePolicyViolationError("g")
        assert ex.error_code == "AI-1371"
        assert isinstance(ex, AIGovernancePolicyException)

    def test_inheritance_chain(self):
        ex = AIPolicyNotFoundError("p")
        assert isinstance(ex, AIGovernanceException)

    def test_compliance_inheritance(self):
        ex = AIComplianceViolationError("c")
        assert isinstance(ex, AIGovernanceException)


# ═════════════════════════════════════════════════════════════════════════════
# 2. CORE TYPES
# ═════════════════════════════════════════════════════════════════════════════

class TestGovernanceMetadata:
    def test_create(self):
        m = GovernanceMetadata.create(
            GovernanceDomain.POLICY, "agent_x", "user1",
            severity=GovernanceSeverity.HIGH
        )
        assert m.domain   == GovernanceDomain.POLICY
        assert m.severity == GovernanceSeverity.HIGH
        assert m.governance_id is not None

    def test_severity_score(self):
        assert GovernanceSeverity.CRITICAL.score() > GovernanceSeverity.HIGH.score()
        assert GovernanceSeverity.HIGH.score() > GovernanceSeverity.MEDIUM.score()


class TestGovernanceContext:
    def test_create(self):
        ctx = GovernanceContext.create("model.invoke", "model_abc", "agent_x", session_id="s1")
        assert ctx.action       == "model.invoke"
        assert ctx.resource     == "model_abc"
        assert ctx.principal_id == "agent_x"
        assert ctx.session_id   == "s1"

    def test_get_env(self):
        ctx = GovernanceContext.create("a", "r", "p", model_version="v2")
        assert ctx.get_env("model_version") == "v2"
        assert ctx.get_env("missing", "default") == "default"


class TestGovernanceDecision:
    def test_allow(self):
        ctx = _ctx()
        d   = GovernanceDecision.allow(ctx, rationale="ok")
        assert d.decision_type == GovernanceDecisionType.ALLOW
        assert d.is_allowed()
        assert not d.is_denied()

    def test_deny(self):
        ctx = _ctx()
        d   = GovernanceDecision.deny(ctx, rationale="blocked")
        assert d.decision_type == GovernanceDecisionType.DENY
        assert d.is_denied()

    def test_escalate(self):
        ctx = _ctx()
        d   = GovernanceDecision.escalate(ctx)
        assert d.decision_type == GovernanceDecisionType.ESCALATE
        assert d.is_denied()
        assert d.severity       == GovernanceSeverity.CRITICAL

    def test_decision_type_blocking(self):
        assert GovernanceDecisionType.DENY.is_blocking()
        assert GovernanceDecisionType.ESCALATE.is_blocking()
        assert not GovernanceDecisionType.ALLOW.is_blocking()


class TestGovernancePolicy:
    def test_create(self):
        p = GovernancePolicy.create(
            "deny-all", PolicyScope.GLOBAL, PolicyEffect.DENY,
            actions=frozenset({"data.*"}), priority=200
        )
        assert p.priority == 200
        assert p.effect   == PolicyEffect.DENY

    def test_matches_action(self):
        p = GovernancePolicy.create("p", PolicyScope.GLOBAL, PolicyEffect.ALLOW,
                                    actions=frozenset({"model.*"}))
        assert p.matches_action("model.invoke")
        assert not p.matches_action("data.read")

    def test_matches_principal_wildcard(self):
        p = _policy()
        assert p.matches_principal("any_agent")

    def test_matches_principal_specific(self):
        p = GovernancePolicy.create("p", PolicyScope.AGENT, PolicyEffect.DENY,
                                    principals=frozenset({"agent_x"}))
        assert p.matches_principal("agent_x")
        assert not p.matches_principal("agent_y")

    def test_governance_status_terminal(self):
        assert GovernanceStatus.APPROVED.is_terminal()
        assert GovernanceStatus.DENIED.is_terminal()
        assert not GovernanceStatus.PENDING.is_terminal()


# ═════════════════════════════════════════════════════════════════════════════
# 3. EVENTS
# ═════════════════════════════════════════════════════════════════════════════

class TestEvents:
    def test_policy_evaluated(self):
        e = PolicyEvaluatedEvent.create("src", "pid", True, "model.invoke")
        assert e.event_type == GovernanceEventType.POLICY_EVALUATED
        assert e.allowed is True

    def test_policy_violated(self):
        e = PolicyViolatedEvent.create("src", "pid", "agent_x", "model.invoke")
        assert e.event_type == GovernanceEventType.POLICY_VIOLATED

    def test_policy_registered(self):
        e = PolicyRegisteredEvent.create("src", "pid", "my_policy")
        assert e.policy_name == "my_policy"

    def test_permission_granted(self):
        e = PermissionGrantedEvent.create("src", "agent_x", "model.invoke", "model_abc")
        assert e.action == "model.invoke"

    def test_permission_denied(self):
        e = PermissionDeniedEvent.create("src", "a", "b", "c", "unauthorized")
        assert e.reason == "unauthorized"

    def test_audit_recorded(self):
        e = AuditRecordedEvent.create("src", "aid", "agent_x", "data.read")
        assert e.audit_id == "aid"

    def test_explanation_generated(self):
        e = ExplanationGeneratedEvent.create("src", "eid", "did")
        assert e.decision_id == "did"

    def test_compliance_checked(self):
        e = ComplianceCheckedEvent.create("src", "agent_x", True, 5)
        assert e.rules_evaluated == 5

    def test_compliance_violated(self):
        e = ComplianceViolatedEvent.create("src", "agent_x", "rule_1", "high")
        assert e.severity == "high"

    def test_governance_decision_issued(self):
        e = GovernanceDecisionIssuedEvent.create("src", "did", "allow", "agent_x")
        assert e.decision_type == "allow"

    def test_risk_threshold_exceeded(self):
        e = RiskThresholdExceededEvent.create("src", "agent_x", "vix", 52.0, 45.0)
        assert e.actual_value == pytest.approx(52.0)

    def test_escalation_triggered(self):
        e = EscalationTriggeredEvent.create("src", "agent_x", "high risk", "critical")
        assert e.severity == "critical"


class TestGovernanceEventBus:
    def test_subscribe_publish(self):
        bus      = GovernanceEventBus()
        received = []
        bus.subscribe(GovernanceEventType.POLICY_EVALUATED,
                      lambda e: received.append(e))
        e = PolicyEvaluatedEvent.create("src", "pid", True, "model.invoke")
        bus.publish(e)
        assert len(received) == 1

    def test_unsubscribe(self):
        bus   = GovernanceEventBus()
        calls = []
        h     = lambda e: calls.append(e)
        bus.subscribe(GovernanceEventType.AUDIT_RECORDED, h)
        bus.unsubscribe(GovernanceEventType.AUDIT_RECORDED, h)
        bus.publish(AuditRecordedEvent.create("src", "aid", "s", "a"))
        assert len(calls) == 0

    def test_subscribe_all(self):
        bus  = GovernanceEventBus()
        seen = []
        bus.subscribe_all(lambda e: seen.append(e))
        bus.publish(PolicyEvaluatedEvent.create("src", "pid", True, "a"))
        bus.publish(AuditRecordedEvent.create("src", "aid", "s", "a"))
        assert len(seen) == 2

    def test_exception_isolation(self):
        bus = GovernanceEventBus()
        bus.subscribe(GovernanceEventType.POLICY_EVALUATED, lambda e: 1/0)
        bus.publish(PolicyEvaluatedEvent.create("src", "pid", True, "a"))

    def test_history_filtered(self):
        bus = GovernanceEventBus()
        bus.publish(PolicyEvaluatedEvent.create("src", "pid", True, "a"))
        bus.publish(AuditRecordedEvent.create("src", "aid", "s", "b"))
        h = bus.history(GovernanceEventType.POLICY_EVALUATED)
        assert len(h) == 1

    def test_clear_history(self):
        bus = GovernanceEventBus()
        bus.publish(PolicyEvaluatedEvent.create("src", "pid", True, "a"))
        bus.clear_history()
        assert bus.history() == []


# ═════════════════════════════════════════════════════════════════════════════
# 4. POLICY LAYER
# ═════════════════════════════════════════════════════════════════════════════

class TestPolicyRule:
    def test_equals_match(self):
        rule = PolicyRule.create("env-check", "tier", RuleOperator.EQUALS, "prod")
        assert rule.evaluate("prod") is True
        assert rule.evaluate("dev")  is False

    def test_contains_match(self):
        rule = PolicyRule.create("r", "tag", RuleOperator.CONTAINS, "urgent")
        assert rule.evaluate("tag:urgent:high") is True
        assert rule.evaluate("tag:normal")       is False

    def test_greater_match(self):
        rule = PolicyRule.create("r", "risk", RuleOperator.GREATER, 0.8)
        assert rule.evaluate(0.9)  is True
        assert rule.evaluate(0.5)  is False

    def test_exists(self):
        rule = PolicyRule.create("r", "k", RuleOperator.EXISTS)
        assert rule.evaluate("anything") is True
        assert rule.evaluate(None)       is False

    def test_not_exists(self):
        rule = PolicyRule.create("r", "k", RuleOperator.NOT_EXISTS)
        assert rule.evaluate(None) is True
        assert rule.evaluate("x")  is False


class TestPolicyRegistry:
    def test_register_and_get(self):
        reg = PolicyRegistry()
        p   = _policy()
        reg.register(p)
        assert reg.get(p.policy_id).policy_id == p.policy_id

    def test_duplicate_raises(self):
        reg = PolicyRegistry()
        p   = _policy()
        reg.register(p)
        with pytest.raises(AIPolicyAlreadyExistsError):
            reg.register(p)

    def test_get_missing_raises(self):
        reg = PolicyRegistry()
        with pytest.raises(AIPolicyNotFoundError):
            reg.get("nope")

    def test_list_active_only(self):
        reg = PolicyRegistry()
        p1  = _policy()
        p2  = GovernancePolicy.create("inactive", PolicyScope.GLOBAL, PolicyEffect.ALLOW,
                                      is_active=False)
        reg.register(p1)
        reg.register(p2)
        active = reg.list_policies(active_only=True)
        assert p1 in active
        assert p2 not in active

    def test_deregister(self):
        reg = PolicyRegistry()
        p   = _policy()
        reg.register(p)
        reg.deregister(p.policy_id)
        assert reg.get_optional(p.policy_id) is None


class TestPolicyEngine:
    def test_allow_when_no_policies(self):
        engine = PolicyEngine()
        ctx    = _ctx()
        d      = engine.evaluate(ctx)
        assert d.is_allowed()

    def test_deny_policy_matches(self):
        engine = PolicyEngine()
        p      = _policy(PolicyEffect.DENY, "model.*")
        engine.registry.register(p)
        ctx = _ctx("model.invoke")
        d   = engine.evaluate(ctx)
        assert d.is_denied()
        assert engine.violation_count() == 1

    def test_allow_policy_matches(self):
        engine = PolicyEngine()
        p      = _policy(PolicyEffect.ALLOW, "data.*")
        engine.registry.register(p)
        ctx = _ctx("data.read")
        d   = engine.evaluate(ctx)
        assert d.is_allowed()

    def test_escalate_policy(self):
        engine = PolicyEngine()
        p = GovernancePolicy.create("esc", PolicyScope.GLOBAL, PolicyEffect.ESCALATE,
                                    actions=frozenset({"admin.*"}))
        engine.registry.register(p)
        ctx = _ctx("admin.delete")
        d   = engine.evaluate(ctx)
        assert d.decision_type == GovernanceDecisionType.ESCALATE

    def test_deny_takes_priority_over_allow(self):
        engine = PolicyEngine()
        allow  = GovernancePolicy.create("allow-all", PolicyScope.GLOBAL, PolicyEffect.ALLOW,
                                         priority=50)
        deny   = GovernancePolicy.create("deny-model", PolicyScope.GLOBAL, PolicyEffect.DENY,
                                         actions=frozenset({"model.*"}), priority=200)
        engine.registry.register(allow)
        engine.registry.register(deny)
        ctx = _ctx("model.invoke")
        d   = engine.evaluate(ctx)
        assert d.is_denied()

    def test_clear_violations(self):
        engine = PolicyEngine()
        p      = _policy(PolicyEffect.DENY, "*")
        engine.registry.register(p)
        engine.evaluate(_ctx())
        assert engine.violation_count() >= 1
        engine.clear_violations()
        assert engine.violation_count() == 0


# ═════════════════════════════════════════════════════════════════════════════
# 5. PERMISSIONS LAYER
# ═════════════════════════════════════════════════════════════════════════════

class TestRolePolicy:
    def test_create(self):
        r = RolePolicy.create("analyst", frozenset({"data.read", "model.invoke"}))
        assert r.has_capability("data.read")
        assert not r.has_capability("admin.delete")

    def test_wildcard_capability(self):
        r = RolePolicy.create("admin", frozenset({"*"}))
        assert r.has_capability("anything")


class TestCapabilityRestriction:
    def test_create(self):
        cr = CapabilityRestriction.create("agent_x", denied_capabilities=frozenset({"admin.*"}))
        assert "admin.*" in cr.denied_capabilities

    def test_expiry(self):
        cr = CapabilityRestriction.create("a", expires_at=time.time() - 1.0)
        assert cr.is_expired()

    def test_not_expired(self):
        cr = CapabilityRestriction.create("a", expires_at=time.time() + 3600)
        assert not cr.is_expired()


class TestAccessControl:
    def test_assign_and_authorize(self):
        ac   = AccessControl()
        role = RolePolicy.create("r", frozenset({"data.read"}))
        ac.add_role(role)
        ac.assign_role("agent_x", role.role_id)
        assert ac.is_authorized("agent_x", "data.read")

    def test_deny_without_role(self):
        ac = AccessControl()
        assert not ac.is_authorized("agent_x", "data.read")

    def test_restriction_blocks_capability(self):
        ac   = AccessControl()
        role = RolePolicy.create("r", frozenset({"*"}))
        ac.add_role(role)
        ac.assign_role("agent_x", role.role_id)
        cr = CapabilityRestriction.create("agent_x", denied_capabilities=frozenset({"admin.delete"}))
        ac.add_restriction(cr)
        assert not ac.is_authorized("agent_x", "admin.delete")
        assert ac.is_authorized("agent_x", "data.read")   # still allowed


class TestPermissionManager:
    def test_system_roles_bootstrapped(self):
        pm    = PermissionManager()
        names = [r.name for r in pm.list_roles()]
        assert "admin" in names
        assert "agent" in names

    def test_assign_and_authorize(self):
        pm = PermissionManager()
        pm.assign_role("agent_x", "agent")
        pm.authorize("agent_x", "data.read")   # should not raise

    def test_permission_denied(self):
        pm = PermissionManager()
        with pytest.raises(AIPermissionDeniedError):
            pm.authorize("unknown_agent", "admin.delete")

    def test_create_duplicate_role_raises(self):
        pm   = PermissionManager()
        role = RolePolicy.create("custom_role", frozenset({"data.read"}))
        pm.create_role(role)
        with pytest.raises(AIRoleAlreadyExistsError):
            pm.create_role(role)

    def test_role_not_found_on_assign(self):
        pm = PermissionManager()
        with pytest.raises(AIRoleNotFoundError):
            pm.assign_role("a", "nonexistent_role")

    def test_revoke_role(self):
        pm = PermissionManager()
        pm.assign_role("agent_x", "agent")
        pm.revoke_role("agent_x", "agent")
        assert not pm.is_authorized("agent_x", "data.read")


# ═════════════════════════════════════════════════════════════════════════════
# 6. AUDIT LAYER
# ═════════════════════════════════════════════════════════════════════════════

class TestAuditRecord:
    def test_create(self):
        r = AuditRecord.create(
            AuditEventType.AGENT_ACTION, "agent_x", "agent_x",
            "model.invoke", "model_abc", "allowed"
        )
        assert r.outcome == "allowed"
        assert r.record_hash != ""

    def test_integrity_valid(self):
        r = AuditRecord.create(
            AuditEventType.AGENT_ACTION, "agent_x", "agent_x",
            "model.invoke", "model_abc", "allowed"
        )
        assert r.verify_integrity()

    def test_audit_event_from_record(self):
        r  = AuditRecord.create(AuditEventType.AGENT_ACTION, "a", "a", "act", "res", "allowed")
        ae = AuditEvent.from_record(r)
        assert ae.audit_id == r.record_id


class TestAuditManager:
    def test_record_and_get(self):
        mgr = AuditManager()
        r   = mgr.record(AuditEventType.AGENT_ACTION, "a", "a", "act", "res", "allowed")
        assert mgr.get(r.record_id).record_id == r.record_id

    def test_get_missing_raises(self):
        mgr = AuditManager()
        with pytest.raises(AIAuditRecordNotFoundError):
            mgr.get("nope")

    def test_chain_linking(self):
        mgr = AuditManager()
        r1  = mgr.record(AuditEventType.AGENT_ACTION, "a", "a", "act1", "res", "allowed")
        r2  = mgr.record(AuditEventType.AGENT_ACTION, "a", "a", "act2", "res", "allowed")
        assert r2.previous_hash == r1.record_hash

    def test_verify_chain_integrity(self):
        mgr = AuditManager()
        for i in range(5):
            mgr.record(AuditEventType.AGENT_ACTION, "a", "a", f"act{i}", "res", "allowed")
        assert mgr.verify_chain_integrity()

    def test_query_by_subject(self):
        mgr = AuditManager()
        mgr.record(AuditEventType.AGENT_ACTION, "agent_x", "agent_x", "a", "r", "allowed")
        mgr.record(AuditEventType.AGENT_ACTION, "agent_y", "agent_y", "b", "r", "denied")
        xs = mgr.query(subject_id="agent_x")
        assert all(r.subject_id == "agent_x" for r in xs)

    def test_generate_report(self):
        mgr = AuditManager()
        for _ in range(3):
            mgr.record(AuditEventType.AGENT_ACTION, "a", "a", "act", "r", "allowed")
        mgr.record(AuditEventType.AGENT_ACTION, "a", "a", "act", "r", "denied")
        report = mgr.generate_report("a")
        assert report.total_records == 4
        assert report.denied_count  == 1
        assert report.allowed_count == 3


# ═════════════════════════════════════════════════════════════════════════════
# 7. EXPLAINABILITY LAYER
# ═════════════════════════════════════════════════════════════════════════════

class TestExplainability:
    def _decision(self) -> GovernanceDecision:
        return GovernanceDecision.allow(_ctx())

    def test_evidence_reference(self):
        ev = EvidenceReference.create("policy", "pid", description="matched allow", weight=0.9)
        assert ev.weight == pytest.approx(0.9)
        assert ev.source_type == "policy"

    def test_decision_trace(self):
        d = self._decision()
        trace = DecisionTrace.build(d.decision_id, ["step1", "step2"], confidence=0.95)
        assert len(trace.steps) == 2
        assert trace.confidence == pytest.approx(0.95)

    def test_explanation_generate(self):
        d  = self._decision()
        ex = Explanation.generate(d, "agent_x")
        assert ex.decision_id == d.decision_id
        assert ex.subject_id  == "agent_x"
        assert "ALLOW" in ex.summary.upper() or "allow" in ex.summary.lower()

    def test_explainability_manager_store_retrieve(self):
        mgr = ExplainabilityManager()
        d   = self._decision()
        ex  = Explanation.generate(d, "agent_x")
        mgr.add(ex)
        assert mgr.get(ex.explanation_id).explanation_id == ex.explanation_id

    def test_get_missing_raises(self):
        mgr = ExplainabilityManager()
        with pytest.raises(AIExplanationNotFoundError):
            mgr.get("nope")

    def test_for_decision(self):
        mgr = ExplainabilityManager()
        d   = self._decision()
        ex1 = mgr.generate_and_store(d, "agent_x")
        ex2 = mgr.generate_and_store(d, "agent_x")
        result = mgr.for_decision(d.decision_id)
        assert len(result) == 2

    def test_total_count(self):
        mgr = ExplainabilityManager()
        d   = self._decision()
        mgr.generate_and_store(d, "a")
        assert mgr.total_count() == 1


# ═════════════════════════════════════════════════════════════════════════════
# 8. COMPLIANCE LAYER
# ═════════════════════════════════════════════════════════════════════════════

class TestCompliance:
    def test_rule_create(self):
        r = ComplianceRule.create("no-pii", ComplianceFramework.GDPR,
                                  severity=GovernanceSeverity.HIGH, is_blocking=True)
        assert r.framework   == ComplianceFramework.GDPR
        assert r.is_blocking is True

    def test_result_build(self):
        rule = ComplianceRule.create("r", ComplianceFramework.INTERNAL)
        res  = ComplianceResult.build(rule, "agent_x", True)
        assert res.passed is True

    def test_report_build(self):
        rule = ComplianceRule.create("r", ComplianceFramework.INTERNAL,
                                     severity=GovernanceSeverity.HIGH)
        r1   = ComplianceResult.build(rule, "a", True)
        r2   = ComplianceResult.build(rule, "a", False)
        report = ComplianceReport.build("a", [r1, r2])
        assert report.total_rules   == 2
        assert report.passed_rules  == 1
        assert report.failed_rules  == 1

    def test_manager_default_all_pass(self):
        mgr  = ComplianceManager()
        rule = ComplianceRule.create("r", ComplianceFramework.INTERNAL)
        mgr.add_rule(rule)
        report = mgr.check("agent_x", object())
        assert report.overall_passed is True

    def test_manager_custom_checker_fail(self):
        def bad_checker(subject, rule):
            return False
        mgr  = ComplianceManager(default_checker=bad_checker)
        rule = ComplianceRule.create("r", ComplianceFramework.INTERNAL,
                                     severity=GovernanceSeverity.HIGH)
        mgr.add_rule(rule)
        report = mgr.check("a", None)
        assert report.overall_passed is False

    def test_raise_on_blocking(self):
        def bad_checker(subject, rule):
            return False
        mgr  = ComplianceManager(default_checker=bad_checker)
        rule = ComplianceRule.create("r", ComplianceFramework.INTERNAL,
                                     severity=GovernanceSeverity.HIGH)
        mgr.add_rule(rule)
        with pytest.raises(AIComplianceViolationError):
            mgr.check("a", None, raise_on_blocking=True)

    def test_rule_not_found(self):
        mgr = ComplianceManager()
        with pytest.raises(AIComplianceRuleNotFoundError):
            mgr.get_rule("nope")

    def test_remove_rule(self):
        mgr  = ComplianceManager()
        rule = ComplianceRule.create("r", ComplianceFramework.INTERNAL)
        mgr.add_rule(rule)
        mgr.remove_rule(rule.rule_id)
        assert mgr.rule_count() == 0


# ═════════════════════════════════════════════════════════════════════════════
# 9. RISK GOVERNANCE
# ═════════════════════════════════════════════════════════════════════════════

class TestRiskGovernance:
    def _threshold(
        self,
        key:    str   = "vix",
        max_v:  float = 45.0,
        escalate: bool = False,
    ) -> RiskThreshold:
        return RiskThreshold.create(
            f"threshold_{key}", RiskCategory.FINANCIAL, key, max_v,
            severity             = GovernanceSeverity.HIGH,
            requires_escalation  = escalate,
        )

    def test_threshold_exceeded(self):
        t = self._threshold("vix", 45.0)
        assert t.is_exceeded(46.0) is True
        assert t.is_exceeded(44.0) is False

    def test_risk_policy_create(self):
        t  = self._threshold()
        rp = RiskPolicy.create("market-risk", RiskCategory.FINANCIAL,
                               thresholds=frozenset({t}))
        assert rp.auto_block is True

    def test_risk_violation_create(self):
        t  = self._threshold()
        rv = RiskViolation.create(t, "agent_x", 50.0)
        assert rv.actual_value    == pytest.approx(50.0)
        assert rv.threshold_value == pytest.approx(45.0)

    def test_evaluate_no_violation(self):
        mgr = GovernanceRiskManager()
        t   = self._threshold("vix", 45.0)
        rp  = RiskPolicy.create("rp", RiskCategory.FINANCIAL, frozenset({t}))
        mgr.add_policy(rp)
        vs  = mgr.evaluate("agent_x", {"vix": 30.0})
        assert vs == []

    def test_evaluate_violation(self):
        mgr = GovernanceRiskManager()
        t   = self._threshold("vix", 45.0)
        rp  = RiskPolicy.create("rp", RiskCategory.FINANCIAL, frozenset({t}))
        mgr.add_policy(rp)
        vs  = mgr.evaluate("agent_x", {"vix": 55.0})
        assert len(vs) == 1
        assert vs[0].actual_value == pytest.approx(55.0)

    def test_raise_on_exceed(self):
        mgr = GovernanceRiskManager()
        t   = self._threshold("vix", 45.0)
        rp  = RiskPolicy.create("rp", RiskCategory.FINANCIAL, frozenset({t}))
        mgr.add_policy(rp)
        with pytest.raises(AIRiskThresholdExceededError):
            mgr.evaluate("agent_x", {"vix": 55.0}, raise_on_exceed=True)

    def test_raise_on_escalation(self):
        mgr = GovernanceRiskManager()
        t   = self._threshold("vix", 45.0, escalate=True)
        rp  = RiskPolicy.create("rp", RiskCategory.FINANCIAL, frozenset({t}))
        mgr.add_policy(rp)
        with pytest.raises(AIEscalationRequiredError):
            mgr.evaluate("agent_x", {"vix": 55.0}, raise_on_escalation=True)

    def test_get_policy_not_found(self):
        mgr = GovernanceRiskManager()
        with pytest.raises(AIRiskPolicyNotFoundError):
            mgr.get_policy("nope")

    def test_violation_history(self):
        mgr = GovernanceRiskManager()
        t   = self._threshold()
        rp  = RiskPolicy.create("rp", RiskCategory.FINANCIAL, frozenset({t}))
        mgr.add_policy(rp)
        mgr.evaluate("agent_x", {"vix": 55.0})
        assert mgr.violation_count() == 1
        mgr.clear_violations()
        assert mgr.violation_count() == 0


# ═════════════════════════════════════════════════════════════════════════════
# 10. GOVERNANCE MANAGER (integrated pipeline)
# ═════════════════════════════════════════════════════════════════════════════

class TestGovernanceManager:
    def _container(self) -> GovernanceContainer:
        return GovernanceContainer()

    def test_allow_decision(self):
        c   = self._container()
        ctx = _ctx()
        d   = c.governance.evaluate(ctx)
        assert d.is_allowed()

    def test_deny_via_policy(self):
        c   = self._container()
        p   = _policy(PolicyEffect.DENY, "model.*")
        c.policy_registry.register(p)
        ctx = _ctx("model.invoke")
        d   = c.governance.evaluate(ctx)
        assert d.is_denied()

    def test_audit_recorded_after_evaluate(self):
        c   = self._container()
        ctx = _ctx()
        c.governance.evaluate(ctx)
        assert c.audit.total_count() == 1

    def test_explanation_stored_after_evaluate(self):
        c   = self._container()
        ctx = _ctx()
        c.governance.evaluate(ctx, explain=True)
        assert c.explainability.total_count() == 1

    def test_risk_escalation(self):
        c = self._container()
        t = RiskThreshold.create("vix_limit", RiskCategory.FINANCIAL, "vix", 45.0,
                                  severity=GovernanceSeverity.HIGH)
        rp = RiskPolicy.create("market-risk", RiskCategory.FINANCIAL, frozenset({t}))
        c.risk.add_policy(rp)
        ctx = _ctx()
        d   = c.governance.evaluate(ctx, risk_context={"vix": 55.0})
        assert d.decision_type == GovernanceDecisionType.ESCALATE

    def test_authorize_wrapper(self):
        c = self._container()
        c.permissions.assign_role("agent_x", "agent")
        c.governance.authorize("agent_x", "data.read")  # should not raise

    def test_compliance_check_wrapper(self):
        c    = self._container()
        rule = ComplianceRule.create("r", ComplianceFramework.INTERNAL)
        c.compliance.add_rule(rule)
        report = c.governance.check_compliance("agent_x", object())
        assert report.overall_passed is True


# ═════════════════════════════════════════════════════════════════════════════
# 11. SNAPSHOT LAYER
# ═════════════════════════════════════════════════════════════════════════════

class TestSnapshots:
    def test_policy_snapshot(self):
        snap = PolicySnapshot.capture(10, 8, 3)
        assert snap.total_policies  == 10
        assert snap.active_policies == 8
        assert snap.violation_count == 3

    def test_framework_snapshot(self):
        snap = GovernanceFrameworkSnapshot.build(
            is_running=True,
            total_policies=5,
            active_policies=5,
            total_audit_records=100,
            total_explanations=20,
            total_risk_violations=2,
            total_roles=5,
            compliance_rules=10,
        )
        assert snap.is_running         is True
        assert snap.total_policies     == 5
        assert snap.total_audit_records == 100


# ═════════════════════════════════════════════════════════════════════════════
# 12. CONTAINER
# ═════════════════════════════════════════════════════════════════════════════

class TestContainer:
    def test_all_components_wired(self):
        c = GovernanceContainer()
        assert c.event_bus      is not None
        assert c.policy_engine  is not None
        assert c.permissions    is not None
        assert c.audit          is not None
        assert c.explainability is not None
        assert c.compliance     is not None
        assert c.risk           is not None
        assert c.governance     is not None

    def test_same_instance(self):
        c = GovernanceContainer()
        assert c.audit is c.audit


# ═════════════════════════════════════════════════════════════════════════════
# 13. GATEWAY
# ═════════════════════════════════════════════════════════════════════════════

class TestGateway:
    def _gw(self) -> GovernanceGateway:
        gw = GovernanceGateway()
        gw.start()
        return gw

    def test_start_stop(self):
        gw = GovernanceGateway()
        assert not gw.is_ai_running
        gw.start()
        assert gw.is_ai_running
        gw.stop()
        assert not gw.is_ai_running

    def test_call_without_start_raises(self):
        gw = GovernanceGateway()
        with pytest.raises(AIGovernanceException):
            gw.evaluate_policy(_ctx())

    def test_system_id_version(self):
        gw = GovernanceGateway()
        assert gw.SYSTEM_ID == "iios:ai:governance:gateway"
        assert gw.VERSION   == "1.0.0"

    def test_evaluate_policy_allow(self):
        gw = self._gw()
        d  = gw.evaluate_policy(_ctx())
        assert d.is_allowed()
        gw.stop()

    def test_register_and_list_policies(self):
        gw = self._gw()
        p  = _policy(PolicyEffect.DENY, "admin.*")
        gw.register_policy(p)
        pids = [pp.policy_id for pp in gw.list_policies()]
        assert p.policy_id in pids
        gw.stop()

    def test_evaluate_policy_deny(self):
        gw = self._gw()
        p  = _policy(PolicyEffect.DENY, "model.*")
        gw.register_policy(p)
        d  = gw.evaluate_policy(_ctx("model.invoke"))
        assert d.is_denied()
        gw.stop()

    def test_authorize_and_deny(self):
        gw = self._gw()
        gw.assign_role("agent_x", "agent")
        gw.authorize("agent_x", "data.read")   # should not raise
        with pytest.raises(AIPermissionDeniedError):
            gw.authorize("no_role_agent", "admin.delete")
        gw.stop()

    def test_is_authorized(self):
        gw = self._gw()
        gw.assign_role("agent_x", "agent")
        assert gw.is_authorized("agent_x", "data.read")
        assert not gw.is_authorized("agent_x", "admin.delete")
        gw.stop()

    def test_revoke_role(self):
        gw = self._gw()
        gw.assign_role("agent_x", "agent")
        gw.revoke_role("agent_x", "agent")
        assert not gw.is_authorized("agent_x", "data.read")
        gw.stop()

    def test_record_audit(self):
        gw = self._gw()
        r  = gw.record_audit(
            AuditEventType.AGENT_ACTION, "agent_x", "agent_x",
            "model.invoke", "model_abc", "allowed"
        )
        assert r.record_id is not None
        gw.stop()

    def test_query_audit(self):
        gw = self._gw()
        gw.record_audit(AuditEventType.AGENT_ACTION, "agent_x", "agent_x",
                        "model.invoke", "model_abc", "allowed")
        records = gw.query_audit(subject_id="agent_x")
        assert len(records) >= 1
        gw.stop()

    def test_verify_audit_integrity(self):
        gw = self._gw()
        gw.record_audit(AuditEventType.AGENT_ACTION, "a", "a", "act", "r", "allowed")
        assert gw.verify_audit_integrity()
        gw.stop()

    def test_generate_explanation(self):
        gw = self._gw()
        d  = gw.evaluate_policy(_ctx(), explain=False)
        ex = gw.generate_explanation(d, "agent_x")
        assert ex.decision_id == d.decision_id
        gw.stop()

    def test_get_explanation(self):
        gw = self._gw()
        d  = gw.evaluate_policy(_ctx(), explain=True)
        exs = gw.explanations_for_decision(d.decision_id)
        assert len(exs) >= 1
        ex  = gw.get_explanation(exs[0].explanation_id)
        assert ex.explanation_id == exs[0].explanation_id
        gw.stop()

    def test_check_compliance_pass(self):
        gw = self._gw()
        r  = gw.check_compliance("agent_x", object())
        assert r.overall_passed is True   # no rules → trivially passes
        gw.stop()

    def test_add_compliance_rule_and_check(self):
        gw   = self._gw()
        rule = ComplianceRule.create("r", ComplianceFramework.INTERNAL)
        gw.add_compliance_rule(rule)
        r = gw.check_compliance("agent_x", object())
        assert r.overall_passed is True
        gw.stop()

    def test_evaluate_risk_no_violation(self):
        gw = self._gw()
        vs = gw.evaluate_risk("agent_x", {"vix": 30.0})
        assert vs == []
        gw.stop()

    def test_add_risk_policy_and_evaluate(self):
        gw = self._gw()
        t  = RiskThreshold.create("vix", RiskCategory.FINANCIAL, "vix", 45.0,
                                   severity=GovernanceSeverity.HIGH)
        rp = RiskPolicy.create("mp", RiskCategory.FINANCIAL, frozenset({t}))
        gw.add_risk_policy(rp)
        vs = gw.evaluate_risk("agent_x", {"vix": 55.0})
        assert len(vs) == 1
        gw.stop()

    def test_evaluate_policy_with_risk_context_escalates(self):
        gw = self._gw()
        t  = RiskThreshold.create("vix", RiskCategory.FINANCIAL, "vix", 45.0,
                                   severity=GovernanceSeverity.HIGH)
        rp = RiskPolicy.create("mp", RiskCategory.FINANCIAL, frozenset({t}))
        gw.add_risk_policy(rp)
        d = gw.evaluate_policy(_ctx(), risk_context={"vix": 55.0})
        assert d.decision_type == GovernanceDecisionType.ESCALATE
        gw.stop()

    def test_health(self):
        gw = self._gw()
        h  = gw.health()
        assert h["is_running"] is True
        assert "total_policies" in h
        gw.stop()

    def test_snapshot(self):
        gw = self._gw()
        s  = gw.snapshot()
        assert s.is_running is True
        gw.stop()

    def test_list_violations(self):
        gw = self._gw()
        p  = _policy(PolicyEffect.DENY, "model.*")
        gw.register_policy(p)
        gw.evaluate_policy(_ctx("model.invoke"))
        vs = gw.list_violations()
        assert len(vs) >= 1
        gw.stop()

    def test_list_risk_violations(self):
        gw = self._gw()
        t  = RiskThreshold.create("vix", RiskCategory.FINANCIAL, "vix", 45.0)
        rp = RiskPolicy.create("mp", RiskCategory.FINANCIAL, frozenset({t}))
        gw.add_risk_policy(rp)
        gw.evaluate_risk("agent_x", {"vix": 55.0})
        vs = gw.list_risk_violations("agent_x")
        assert len(vs) == 1
        gw.stop()

    def test_events_emitted(self):
        gw   = self._gw()
        seen = []
        gw._c.event_bus.subscribe_all(lambda e: seen.append(e.event_type))
        gw.evaluate_policy(_ctx())
        types = [e.value for e in seen]
        assert GovernanceEventType.AUDIT_RECORDED.value in types
        assert GovernanceEventType.GOVERNANCE_DECISION_ISSUED.value in types
        gw.stop()

    def test_deregister_policy(self):
        gw = self._gw()
        p  = _policy(PolicyEffect.DENY, "model.*")
        gw.register_policy(p)
        gw.deregister_policy(p.policy_id)
        d = gw.evaluate_policy(_ctx("model.invoke"))
        assert d.is_allowed()   # no more deny policy
        gw.stop()

    def test_list_roles(self):
        gw    = self._gw()
        roles = gw.list_roles()
        assert len(roles) >= 5   # bootstrap roles
        gw.stop()

    def test_create_role(self):
        gw   = self._gw()
        role = RolePolicy.create("data_scientist", frozenset({"data.read", "model.invoke"}))
        gw.create_role(role)
        names = [r.name for r in gw.list_roles()]
        assert "data_scientist" in names
        gw.stop()
