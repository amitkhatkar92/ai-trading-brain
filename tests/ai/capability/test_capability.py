"""
test_capability.py
==================
Comprehensive test suite for the A9 Enterprise Capability Platform.

Coverage:
  1.  Exceptions (24 classes)
  2.  Core types (CapabilityType, CapabilityCategory, CapabilityStatus,
                  CapabilityVersion, CapabilityMetadata, CapabilityDescriptor)
  3.  Engine (CapabilityContext, CapabilityRequest, ExecutionStatus,
              ExecutionResult, CapabilityResponse, CapabilityExecutor)
  4.  Policy — Permission/Authorization
  5.  Policy — Policy/PolicyEngine
  6.  Policy — QuotaManager
  7.  Policy — AuditManager
  8.  Registry (CapabilityRegistry)
  9.  Connectors (BaseConnector, ConnectorRegistry)
  10. Skills (BaseSkill, SkillRegistry)
  11. Events (all event types + CapabilityEventBus)
  12. Snapshot
  13. Container
  14. Gateway (lifecycle + all public APIs)
"""
from __future__ import annotations

import time
import uuid

import pytest

# ── imports ───────────────────────────────────────────────────────────────────

from iios.ai.capability.exceptions import (
    AICapabilityException,
    AICapabilityNotFoundError,
    AICapabilityAlreadyExistsError,
    AICapabilityDisabledError,
    AICapabilityVersionError,
    AICapabilityRegistrationError,
    AICapabilityExecutionException,
    AICapabilityTimeoutError,
    AICapabilityRetryExhaustedError,
    AICapabilityValidationError,
    AICapabilityResultError,
    AICapabilityAuthorizationException,
    AICapabilityPermissionDeniedError,
    AICapabilityPolicyViolationError,
    AICapabilityQuotaExceededError,
    AICapabilityRateLimitError,
    AIConnectorException,
    AIConnectorNotFoundError,
    AIConnectorConnectionError,
    AIConnectorTimeoutError,
    AISkillException,
    AISkillNotFoundError,
    AISkillExecutionError,
    AICapabilityAuditException,
)

from iios.ai.capability.core import (
    CapabilityType, CapabilityCategory, CapabilityStatus,
    CapabilityVersion, CapabilityMetadata, CapabilityDescriptor,
)

from iios.ai.capability.engine import (
    CapabilityContext, CapabilityRequest,
    ExecutionStatus, ExecutionResult, CapabilityResponse,
    CapabilityExecutor,
)

from iios.ai.capability.policy import (
    CapabilityPermission, CapabilityRole, CapabilityAuthorization,
    PolicyEffect, CapabilityPolicy, CapabilityPolicyEngine,
    QuotaEntry, QuotaManager,
    CapabilityAuditEventType, CapabilityAuditRecord,
    CapabilityAuditReport, CapabilityAuditManager,
)

from iios.ai.capability.registry import CapabilityRegistry

from iios.ai.capability.connectors import (
    ConnectorType, ConnectorStatus, ConnectorDescriptor,
    BaseConnector, ConnectorRegistry,
)

from iios.ai.capability.skills import (
    SkillCategory, SkillDescriptor, BaseSkill, SkillRegistry,
)

from iios.ai.capability.events import (
    CapabilityEventType, CapabilityEvent,
    CapabilityRegisteredEvent, CapabilityEnabledEvent, CapabilityDisabledEvent,
    CapabilityDeregisteredEvent, CapabilityExecutedEvent, CapabilityFailedEvent,
    CapabilityTimeoutEvent, ConnectorRegisteredEvent, ConnectorInvokedEvent,
    SkillRegisteredEvent, SkillExecutedEvent,
    AuthorizationGrantedEvent, AuthorizationDeniedEvent,
    QuotaExceededEvent, PolicyAddedEvent, PolicyRemovedEvent,
    CapabilityEventBus,
)

from iios.ai.capability.snapshot  import CapabilitySystemSnapshot
from iios.ai.capability.container import CapabilityContainer
from iios.ai.capability.gateway   import CapabilityGateway


# ── helpers ───────────────────────────────────────────────────────────────────

def _descriptor(
    name:            str              = "my_tool",
    cap_type:        CapabilityType   = CapabilityType.TOOL,
    category:        CapabilityCategory = CapabilityCategory.COMPUTATION,
    requires_auth:   bool             = False,
    status:          CapabilityStatus = CapabilityStatus.ACTIVE,
    max_retries:     int              = 0,
    timeout_seconds: float            = 30.0,
) -> CapabilityDescriptor:
    return CapabilityDescriptor.create(
        name=name, capability_type=cap_type, category=category,
        requires_auth=requires_auth, status=status,
        max_retries=max_retries, timeout_seconds=timeout_seconds,
    )


def _ctx(principal: str = "agent_x") -> CapabilityContext:
    return CapabilityContext.create(principal)


def _gw() -> CapabilityGateway:
    gw = CapabilityGateway()
    gw.start()
    return gw


# ═════════════════════════════════════════════════════════════════════════════
# 1. EXCEPTIONS
# ═════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base(self):
        ex = AICapabilityException("test")
        assert ex.error_code == "AI-1400"
        assert "AI-1400" in ex.message

    def test_not_found(self):
        ex = AICapabilityNotFoundError("cap")
        assert ex.error_code == "AI-1401"
        assert isinstance(ex, AICapabilityException)

    def test_already_exists(self):
        assert AICapabilityAlreadyExistsError("c").error_code == "AI-1402"

    def test_disabled(self):
        assert AICapabilityDisabledError("c").error_code == "AI-1403"

    def test_version_error(self):
        assert AICapabilityVersionError("v").error_code == "AI-1404"

    def test_registration_error(self):
        assert AICapabilityRegistrationError("r").error_code == "AI-1405"

    def test_execution_exception(self):
        ex = AICapabilityExecutionException("e")
        assert ex.error_code == "AI-1410"
        assert isinstance(ex, AICapabilityException)

    def test_timeout(self):
        assert AICapabilityTimeoutError("t").error_code == "AI-1411"

    def test_retry_exhausted(self):
        assert AICapabilityRetryExhaustedError("r").error_code == "AI-1412"

    def test_validation(self):
        assert AICapabilityValidationError("v").error_code == "AI-1413"

    def test_result_error(self):
        assert AICapabilityResultError("r").error_code == "AI-1414"

    def test_auth_exception(self):
        ex = AICapabilityAuthorizationException("a")
        assert ex.error_code == "AI-1420"

    def test_permission_denied(self):
        ex = AICapabilityPermissionDeniedError("p")
        assert ex.error_code == "AI-1421"
        assert isinstance(ex, AICapabilityAuthorizationException)

    def test_policy_violation(self):
        assert AICapabilityPolicyViolationError("p").error_code == "AI-1422"

    def test_quota_exceeded(self):
        assert AICapabilityQuotaExceededError("q").error_code == "AI-1423"

    def test_rate_limit(self):
        assert AICapabilityRateLimitError("r").error_code == "AI-1424"

    def test_connector_exception(self):
        ex = AIConnectorException("c")
        assert ex.error_code == "AI-1430"

    def test_connector_not_found(self):
        assert AIConnectorNotFoundError("c").error_code == "AI-1431"

    def test_connector_connection_error(self):
        assert AIConnectorConnectionError("c").error_code == "AI-1432"

    def test_connector_timeout(self):
        assert AIConnectorTimeoutError("c").error_code == "AI-1433"

    def test_skill_exception(self):
        assert AISkillException("s").error_code == "AI-1440"

    def test_skill_not_found(self):
        ex = AISkillNotFoundError("s")
        assert ex.error_code == "AI-1441"
        assert isinstance(ex, AISkillException)

    def test_skill_execution_error(self):
        assert AISkillExecutionError("s").error_code == "AI-1442"

    def test_audit_exception(self):
        assert AICapabilityAuditException("a").error_code == "AI-1450"

    def test_full_inheritance_chain(self):
        ex = AICapabilityPermissionDeniedError("p")
        assert isinstance(ex, AICapabilityException)

    def test_connector_inheritance(self):
        ex = AIConnectorConnectionError("c")
        assert isinstance(ex, AICapabilityException)


# ═════════════════════════════════════════════════════════════════════════════
# 2. CORE TYPES
# ═════════════════════════════════════════════════════════════════════════════

class TestCapabilityVersion:
    def test_create(self):
        v = CapabilityVersion.create(2, 3, 1)
        assert v.major == 2
        assert str(v)  == "2.3.1"

    def test_parse(self):
        v = CapabilityVersion.parse("1.2.3")
        assert (v.major, v.minor, v.patch) == (1, 2, 3)

    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            CapabilityVersion.parse("bad")

    def test_compatible(self):
        v1 = CapabilityVersion.parse("1.0.0")
        v2 = CapabilityVersion.parse("1.5.2")
        assert v1.is_compatible_with(v2)

    def test_incompatible(self):
        v1 = CapabilityVersion.parse("1.0.0")
        v2 = CapabilityVersion.parse("2.0.0")
        assert not v1.is_compatible_with(v2)

    def test_ordering(self):
        v1 = CapabilityVersion.parse("1.0.0")
        v2 = CapabilityVersion.parse("1.1.0")
        assert v1 < v2
        assert v2 > v1


class TestCapabilityMetadata:
    def test_create(self):
        m = CapabilityMetadata.create("my_tool", description="does stuff", author="alice",
                                      tags=frozenset({"ai", "test"}))
        assert m.name   == "my_tool"
        assert m.author == "alice"
        assert "ai" in m.tags

    def test_defaults(self):
        m = CapabilityMetadata.create("t")
        assert m.author      == ""
        assert m.tags        == frozenset()
        assert m.metadata_id != ""


class TestCapabilityDescriptor:
    def test_create_defaults(self):
        d = CapabilityDescriptor.create("my_tool")
        assert d.name            == "my_tool"
        assert d.capability_type == CapabilityType.TOOL
        assert d.is_executable()

    def test_disabled_not_executable(self):
        d = CapabilityDescriptor.create("t", status=CapabilityStatus.DISABLED)
        assert not d.is_executable()

    def test_with_status(self):
        d    = CapabilityDescriptor.create("t")
        d2   = d.with_status(CapabilityStatus.DISABLED)
        assert not d2.is_executable()
        assert d.is_executable()   # original unchanged

    def test_type_enum_values(self):
        assert CapabilityType.SKILL.value          == "skill"
        assert CapabilityType.CONNECTOR.value      == "connector"
        assert CapabilityType.WORKFLOW_ACTION.value == "workflow_action"

    def test_category_enum(self):
        assert CapabilityCategory.DATA.value        == "data"
        assert CapabilityCategory.INTEGRATION.value == "integration"

    def test_status_executable(self):
        assert CapabilityStatus.ACTIVE.is_executable()
        assert not CapabilityStatus.DISABLED.is_executable()
        assert not CapabilityStatus.DEPRECATED.is_executable()


# ═════════════════════════════════════════════════════════════════════════════
# 3. ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class TestCapabilityContext:
    def test_create(self):
        ctx = CapabilityContext.create("agent_x", session_id="s1", tier="gold")
        assert ctx.principal_id == "agent_x"
        assert ctx.session_id   == "s1"
        assert ctx.get_env("tier") == "gold"

    def test_missing_env(self):
        ctx = CapabilityContext.create("a")
        assert ctx.get_env("missing", "default") == "default"


class TestCapabilityRequest:
    def test_create(self):
        ctx = _ctx()
        req = CapabilityRequest.create("cap_001", ctx, x=10, y=20)
        assert req.capability_id == "cap_001"
        assert req.get_param("x") == 10
        assert req.get_param("missing", 99) == 99

    def test_params_dict(self):
        ctx = _ctx()
        req = CapabilityRequest.create("cap", ctx, a=1, b=2)
        d   = req.params_dict()
        assert d["a"] == 1
        assert d["b"] == 2


class TestExecutionResult:
    def test_success(self):
        r = ExecutionResult.success("req", "cap", output=42, started_at=time.time() - 0.1)
        assert r.is_successful()
        assert r.output == 42
        assert r.duration_ms > 0

    def test_failure(self):
        r = ExecutionResult.failure("req", "cap", "oops", time.time())
        assert r.is_failed()
        assert r.error == "oops"
        assert r.output is None

    def test_timeout(self):
        r = ExecutionResult.timeout("req", "cap", time.time())
        assert r.status == ExecutionStatus.TIMEOUT
        assert r.is_failed()

    def test_terminal_status(self):
        assert ExecutionStatus.SUCCESS.is_terminal()
        assert ExecutionStatus.FAILED.is_terminal()
        assert not ExecutionStatus.RUNNING.is_terminal()


class TestCapabilityResponse:
    def test_create(self):
        result   = ExecutionResult.success("req", "cap", "ok", time.time())
        response = CapabilityResponse.create("req", result)
        assert response.is_successful()
        assert response.result.output == "ok"

    def test_failed_response(self):
        result   = ExecutionResult.failure("req", "cap", "err", time.time())
        response = CapabilityResponse.create("req", result)
        assert not response.is_successful()


class TestCapabilityExecutor:
    def test_execute_success(self):
        executor = CapabilityExecutor()
        d        = _descriptor()
        executor.register_handler(d.descriptor_id, lambda p: p.get("x", 0) * 2)
        ctx  = _ctx()
        req  = CapabilityRequest.create(d.descriptor_id, ctx, x=21)
        resp = executor.execute(req, d)
        assert resp.is_successful()
        assert resp.result.output == 42

    def test_execute_disabled_raises(self):
        executor = CapabilityExecutor()
        d        = _descriptor(status=CapabilityStatus.DISABLED)
        executor.register_handler(d.descriptor_id, lambda p: None)
        ctx = _ctx()
        req = CapabilityRequest.create(d.descriptor_id, ctx)
        with pytest.raises(AICapabilityDisabledError):
            executor.execute(req, d)

    def test_execute_no_handler_raises(self):
        executor = CapabilityExecutor()
        d        = _descriptor()
        ctx      = _ctx()
        req      = CapabilityRequest.create(d.descriptor_id, ctx)
        with pytest.raises(AICapabilityNotFoundError):
            executor.execute(req, d)

    def test_execute_failure_no_retry(self):
        executor = CapabilityExecutor()
        d        = _descriptor(max_retries=0)
        executor.register_handler(d.descriptor_id, lambda p: (_ for _ in ()).throw(ValueError("boom")))
        ctx  = _ctx()
        req  = CapabilityRequest.create(d.descriptor_id, ctx)
        resp = executor.execute(req, d)
        assert not resp.is_successful()

    def test_execute_retry_exhausted_raises(self):
        executor = CapabilityExecutor()
        d        = _descriptor(max_retries=2)

        def always_fail(p):
            raise RuntimeError("fail")

        executor.register_handler(d.descriptor_id, always_fail)
        ctx = _ctx()
        req = CapabilityRequest.create(d.descriptor_id, ctx)
        with pytest.raises(AICapabilityRetryExhaustedError):
            executor.execute(req, d)

    def test_authorize_fn_called(self):
        executor = CapabilityExecutor()
        d        = _descriptor()
        executor.register_handler(d.descriptor_id, lambda p: "ok")

        called   = []
        def auth_fn(pid, cid):
            called.append((pid, cid))

        ctx  = _ctx()
        req  = CapabilityRequest.create(d.descriptor_id, ctx)
        executor.execute(req, d, authorize_fn=auth_fn)
        assert len(called) == 1

    def test_authorize_fn_deny(self):
        executor = CapabilityExecutor()
        d        = _descriptor()
        executor.register_handler(d.descriptor_id, lambda p: "ok")

        def deny_fn(pid, cid):
            raise AICapabilityPermissionDeniedError("denied")

        ctx = _ctx()
        req = CapabilityRequest.create(d.descriptor_id, ctx)
        with pytest.raises(AICapabilityPermissionDeniedError):
            executor.execute(req, d, authorize_fn=deny_fn)

    def test_stats(self):
        executor = CapabilityExecutor()
        d        = _descriptor()
        executor.register_handler(d.descriptor_id, lambda p: 1)
        ctx      = _ctx()
        req      = CapabilityRequest.create(d.descriptor_id, ctx)
        executor.execute(req, d)
        assert executor.total_executions()  == 1
        assert executor.failed_executions() == 0

    def test_has_handler(self):
        executor = CapabilityExecutor()
        executor.register_handler("cap_1", lambda p: None)
        assert executor.has_handler("cap_1")
        assert not executor.has_handler("cap_2")


# ═════════════════════════════════════════════════════════════════════════════
# 4. POLICY — PERMISSION / AUTHORIZATION
# ═════════════════════════════════════════════════════════════════════════════

class TestCapabilityPermission:
    def test_create(self):
        p = CapabilityPermission.create("agent_x", "cap_001", granted_by="admin")
        assert p.principal_id  == "agent_x"
        assert p.capability_id == "cap_001"
        assert p.is_active()

    def test_expired(self):
        p = CapabilityPermission.create("a", "c", expires_at=time.time() - 1.0)
        assert p.is_expired()
        assert not p.is_active()

    def test_not_expired(self):
        p = CapabilityPermission.create("a", "c", expires_at=time.time() + 3600)
        assert not p.is_expired()


class TestCapabilityRole:
    def test_grants(self):
        r = CapabilityRole.create("analyst", frozenset({"data.*"}))
        assert r.grants("data.read")
        assert not r.grants("admin.delete")

    def test_wildcard(self):
        r = CapabilityRole.create("admin", frozenset({"*"}))
        assert r.grants("anything")

    def test_exact_match(self):
        r = CapabilityRole.create("r", frozenset({"cap_001"}))
        assert r.grants("cap_001")
        assert not r.grants("cap_002")


class TestCapabilityAuthorization:
    def test_direct_grant(self):
        auth = CapabilityAuthorization()
        perm = CapabilityPermission.create("agent_x", "cap_001")
        auth.grant(perm)
        assert auth.is_authorized("agent_x", "cap_001")

    def test_not_authorized(self):
        auth = CapabilityAuthorization()
        assert not auth.is_authorized("agent_x", "cap_001")

    def test_authorize_raises(self):
        auth = CapabilityAuthorization()
        with pytest.raises(AICapabilityPermissionDeniedError):
            auth.authorize("agent_x", "cap_001")

    def test_revoke(self):
        auth = CapabilityAuthorization()
        perm = CapabilityPermission.create("agent_x", "cap_001")
        auth.grant(perm)
        auth.revoke("agent_x", "cap_001")
        assert not auth.is_authorized("agent_x", "cap_001")

    def test_role_authorization(self):
        auth = CapabilityAuthorization()
        role = CapabilityRole.create("analyst", frozenset({"data.*"}))
        auth.create_role(role)
        auth.assign_role("agent_x", "analyst")
        assert auth.is_authorized("agent_x", "data.read")
        assert not auth.is_authorized("agent_x", "admin.delete")

    def test_revoke_role(self):
        auth = CapabilityAuthorization()
        role = CapabilityRole.create("analyst", frozenset({"data.*"}))
        auth.create_role(role)
        auth.assign_role("agent_x", "analyst")
        auth.revoke_role("agent_x", "analyst")
        assert not auth.is_authorized("agent_x", "data.read")

    def test_list_permissions(self):
        auth = CapabilityAuthorization()
        perm = CapabilityPermission.create("agent_x", "cap_001")
        auth.grant(perm)
        assert len(auth.list_permissions("agent_x")) == 1

    def test_expired_permission_not_active(self):
        auth = CapabilityAuthorization()
        perm = CapabilityPermission.create("agent_x", "cap_001",
                                            expires_at=time.time() - 1.0)
        auth.grant(perm)
        assert not auth.is_authorized("agent_x", "cap_001")


# ═════════════════════════════════════════════════════════════════════════════
# 5. POLICY — POLICY ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class TestCapabilityPolicy:
    def test_matches_wildcard(self):
        p = CapabilityPolicy.create("allow-all")
        assert p.matches("anyone", "anything")

    def test_matches_specific(self):
        p = CapabilityPolicy.create("deny-broker", principal_pattern="agent_*",
                                     capability_pattern="broker.*",
                                     effect=PolicyEffect.DENY)
        assert p.matches("agent_x", "broker.order")
        assert not p.matches("service_x", "broker.order")

    def test_create(self):
        p = CapabilityPolicy.create("p", effect=PolicyEffect.DENY, priority=200)
        assert p.priority == 200
        assert p.effect   == PolicyEffect.DENY


class TestCapabilityPolicyEngine:
    def test_default_allow(self):
        engine = CapabilityPolicyEngine()
        assert engine.evaluate("agent_x", "cap_001") is True

    def test_deny_policy(self):
        engine = CapabilityPolicyEngine()
        p = CapabilityPolicy.create("deny-broker", capability_pattern="broker.*",
                                     effect=PolicyEffect.DENY, priority=200)
        engine.add_policy(p)
        with pytest.raises(AICapabilityPolicyViolationError):
            engine.evaluate("agent_x", "broker.order")

    def test_allow_policy_passes(self):
        engine = CapabilityPolicyEngine()
        p = CapabilityPolicy.create("allow-data", capability_pattern="data.*",
                                     effect=PolicyEffect.ALLOW, priority=100)
        engine.add_policy(p)
        assert engine.evaluate("agent_x", "data.read") is True

    def test_higher_priority_deny_wins(self):
        engine  = CapabilityPolicyEngine()
        allow_p = CapabilityPolicy.create("allow-all", priority=50)
        deny_p  = CapabilityPolicy.create("deny-broker", capability_pattern="broker.*",
                                           effect=PolicyEffect.DENY, priority=200)
        engine.add_policy(allow_p)
        engine.add_policy(deny_p)
        with pytest.raises(AICapabilityPolicyViolationError):
            engine.evaluate("agent_x", "broker.order")

    def test_remove_policy(self):
        engine = CapabilityPolicyEngine()
        p = CapabilityPolicy.create("deny", capability_pattern="*",
                                     effect=PolicyEffect.DENY)
        engine.add_policy(p)
        engine.remove_policy(p.policy_id)
        assert engine.evaluate("agent_x", "any") is True

    def test_policy_count(self):
        engine = CapabilityPolicyEngine()
        engine.add_policy(CapabilityPolicy.create("p1"))
        engine.add_policy(CapabilityPolicy.create("p2"))
        assert engine.policy_count() == 2


# ═════════════════════════════════════════════════════════════════════════════
# 6. POLICY — QUOTA
# ═════════════════════════════════════════════════════════════════════════════

class TestQuotaManager:
    def test_no_quota_always_passes(self):
        qm = QuotaManager()
        qm.record_execution("a", "c")   # no quota set — should not raise

    def test_hourly_limit(self):
        qm = QuotaManager()
        qm.set_quota("agent_x", "cap", max_per_hour=2)
        qm.record_execution("agent_x", "cap")
        qm.record_execution("agent_x", "cap")
        with pytest.raises(AICapabilityQuotaExceededError):
            qm.record_execution("agent_x", "cap")

    def test_daily_limit(self):
        qm = QuotaManager()
        qm.set_quota("agent_x", "cap", max_per_day=2)
        qm.record_execution("agent_x", "cap")
        qm.record_execution("agent_x", "cap")
        with pytest.raises(AICapabilityQuotaExceededError):
            qm.record_execution("agent_x", "cap")

    def test_check_quota_false_when_exceeded(self):
        qm = QuotaManager()
        qm.set_quota("agent_x", "cap", max_per_hour=1)
        qm.record_execution("agent_x", "cap")
        assert not qm.check_quota("agent_x", "cap")

    def test_check_quota_true_when_ok(self):
        qm = QuotaManager()
        qm.set_quota("agent_x", "cap", max_per_hour=10)
        assert qm.check_quota("agent_x", "cap")

    def test_get_usage(self):
        qm = QuotaManager()
        qm.set_quota("a", "c", max_per_hour=100)
        qm.record_execution("a", "c")
        qm.record_execution("a", "c")
        usage = qm.get_usage("a", "c")
        assert usage["hour_count"] == 2

    def test_quota_count(self):
        qm = QuotaManager()
        qm.set_quota("a1", "c1")
        qm.set_quota("a2", "c2")
        assert qm.quota_count() == 2

    def test_different_principals_independent(self):
        qm = QuotaManager()
        qm.set_quota("a1", "cap", max_per_hour=1)
        qm.set_quota("a2", "cap", max_per_hour=10)
        qm.record_execution("a1", "cap")
        with pytest.raises(AICapabilityQuotaExceededError):
            qm.record_execution("a1", "cap")
        qm.record_execution("a2", "cap")   # should succeed


# ═════════════════════════════════════════════════════════════════════════════
# 7. POLICY — AUDIT
# ═════════════════════════════════════════════════════════════════════════════

class TestCapabilityAuditManager:
    def test_record_and_total(self):
        mgr = CapabilityAuditManager()
        mgr.record(CapabilityAuditEventType.EXECUTE_SUCCESS, "a", "c", "success")
        assert mgr.total_count() == 1

    def test_query_by_principal(self):
        mgr = CapabilityAuditManager()
        mgr.record(CapabilityAuditEventType.EXECUTE_SUCCESS, "a1", "c", "ok")
        mgr.record(CapabilityAuditEventType.EXECUTE_SUCCESS, "a2", "c", "ok")
        results = mgr.query(principal_id="a1")
        assert all(r.principal_id == "a1" for r in results)

    def test_query_by_event_type(self):
        mgr = CapabilityAuditManager()
        mgr.record(CapabilityAuditEventType.EXECUTE_SUCCESS, "a", "c", "ok")
        mgr.record(CapabilityAuditEventType.AUTH_DENIED,     "a", "c", "denied")
        results = mgr.query(event_type=CapabilityAuditEventType.AUTH_DENIED)
        assert all(r.event_type == CapabilityAuditEventType.AUTH_DENIED for r in results)

    def test_generate_report(self):
        mgr = CapabilityAuditManager()
        mgr.record(CapabilityAuditEventType.EXECUTE_SUCCESS, "a", "c", "ok")
        mgr.record(CapabilityAuditEventType.EXECUTE_SUCCESS, "a", "c", "ok")
        mgr.record(CapabilityAuditEventType.EXECUTE_FAILURE, "a", "c", "fail")
        report = mgr.generate_report("a")
        assert report.total_records   == 3
        assert report.success_count   == 2
        assert report.failure_count   == 1

    def test_audit_record_fields(self):
        mgr = CapabilityAuditManager()
        r   = mgr.record(CapabilityAuditEventType.AUTH_DENIED, "a", "c", "denied",
                          duration_ms=5.0, notes="no perm")
        assert r.duration_ms == pytest.approx(5.0)
        assert r.notes       == "no perm"


# ═════════════════════════════════════════════════════════════════════════════
# 8. REGISTRY
# ═════════════════════════════════════════════════════════════════════════════

class TestCapabilityRegistry:
    def test_register_and_get(self):
        reg = CapabilityRegistry()
        d   = _descriptor()
        reg.register(d)
        assert reg.get(d.descriptor_id).descriptor_id == d.descriptor_id

    def test_duplicate_raises(self):
        reg = CapabilityRegistry()
        d   = _descriptor()
        reg.register(d)
        with pytest.raises(AICapabilityAlreadyExistsError):
            reg.register(d)

    def test_get_missing_raises(self):
        reg = CapabilityRegistry()
        with pytest.raises(AICapabilityNotFoundError):
            reg.get("nope")

    def test_deregister(self):
        reg = CapabilityRegistry()
        d   = _descriptor()
        reg.register(d)
        reg.deregister(d.descriptor_id)
        assert reg.get_optional(d.descriptor_id) is None

    def test_enable_disable(self):
        reg = CapabilityRegistry()
        d   = _descriptor(status=CapabilityStatus.ACTIVE)
        reg.register(d)
        reg.disable(d.descriptor_id)
        assert not reg.get(d.descriptor_id).is_executable()
        reg.enable(d.descriptor_id)
        assert reg.get(d.descriptor_id).is_executable()

    def test_discover_by_type(self):
        reg = CapabilityRegistry()
        t1  = _descriptor("tool_1",  cap_type=CapabilityType.TOOL)
        s1  = _descriptor("skill_1", cap_type=CapabilityType.SKILL)
        reg.register(t1)
        reg.register(s1)
        tools  = reg.discover(capability_type=CapabilityType.TOOL)
        skills = reg.discover(capability_type=CapabilityType.SKILL)
        assert t1 in tools
        assert s1 not in tools
        assert s1 in skills

    def test_discover_by_category(self):
        reg = CapabilityRegistry()
        d1  = _descriptor("d1", category=CapabilityCategory.DATA)
        d2  = _descriptor("d2", category=CapabilityCategory.COMPUTATION)
        reg.register(d1)
        reg.register(d2)
        results = reg.discover(category=CapabilityCategory.DATA)
        assert d1 in results
        assert d2 not in results

    def test_discover_active_only(self):
        reg = CapabilityRegistry()
        a   = _descriptor("active", status=CapabilityStatus.ACTIVE)
        dis = _descriptor("disabled", status=CapabilityStatus.DISABLED)
        reg.register(a)
        reg.register(dis)
        active = reg.discover(active_only=True)
        assert a   in active
        assert dis not in active

    def test_discover_by_tags(self):
        reg = CapabilityRegistry()
        d   = CapabilityDescriptor.create("tagged", tags=frozenset({"finance", "realtime"}))
        reg.register(d)
        results = reg.discover(tags=frozenset({"finance"}))
        assert d in results
        no_match = reg.discover(tags=frozenset({"sports"}))
        assert d not in no_match

    def test_count(self):
        reg = CapabilityRegistry()
        reg.register(_descriptor("d1"))
        reg.register(_descriptor("d2"))
        assert reg.count() == 2


# ═════════════════════════════════════════════════════════════════════════════
# 9. CONNECTORS
# ═════════════════════════════════════════════════════════════════════════════

class _MockConnector(BaseConnector):
    """Minimal concrete connector for testing."""

    def connect(self)    -> None: self._status = ConnectorStatus.CONNECTED
    def disconnect(self) -> None: self._status = ConnectorStatus.DISCONNECTED
    def is_connected(self) -> bool: return self._status == ConnectorStatus.CONNECTED
    def ping(self)       -> bool: return self.is_connected()
    def invoke(self, method, params): return {"method": method, **params}


def _mock_connector(
    name: str            = "mock_conn",
    ctype: ConnectorType = ConnectorType.HTTP_SERVICE,
) -> _MockConnector:
    desc = ConnectorDescriptor.create(name, connector_type=ctype)
    return _MockConnector(desc)


class TestConnectors:
    def test_descriptor_create(self):
        d = ConnectorDescriptor.create("http_conn", ConnectorType.HTTP_SERVICE,
                                        endpoint="api.example.internal")
        assert d.connector_type == ConnectorType.HTTP_SERVICE
        assert d.endpoint       == "api.example.internal"

    def test_mock_connector_lifecycle(self):
        c = _mock_connector()
        assert not c.is_connected()
        c.connect()
        assert c.is_connected()
        assert c.ping()
        c.disconnect()
        assert not c.is_connected()

    def test_connector_invoke(self):
        c = _mock_connector()
        c.connect()
        result = c.invoke("get_data", {"symbol": "NIFTY"})
        assert result["method"] == "get_data"
        assert result["symbol"] == "NIFTY"

    def test_connector_registry_register(self):
        reg = ConnectorRegistry()
        c   = _mock_connector()
        reg.register(c)
        assert reg.get(c.connector_id).connector_id == c.connector_id

    def test_connector_registry_not_found(self):
        reg = ConnectorRegistry()
        with pytest.raises(AIConnectorNotFoundError):
            reg.get("nope")

    def test_connector_registry_list_by_type(self):
        reg = ConnectorRegistry()
        c1  = _mock_connector("c1", ConnectorType.HTTP_SERVICE)
        c2  = _mock_connector("c2", ConnectorType.DATABASE)
        reg.register(c1)
        reg.register(c2)
        http_list = reg.list_connectors(ConnectorType.HTTP_SERVICE)
        assert c1 in http_list
        assert c2 not in http_list

    def test_connector_type_values(self):
        assert ConnectorType.MARKET_DATA.value  == "market_data"
        assert ConnectorType.BROKER_API.value   == "broker_api"
        assert ConnectorType.FILE_STORAGE.value == "file_storage"


# ═════════════════════════════════════════════════════════════════════════════
# 10. SKILLS
# ═════════════════════════════════════════════════════════════════════════════

class _MockSkill(BaseSkill):
    """Minimal concrete skill for testing."""

    def __init__(self, name: str = "mock_skill",
                 category: SkillCategory = SkillCategory.CALCULATION) -> None:
        self._desc = SkillDescriptor.create(name, category=category)

    @property
    def skill_id(self) -> str:
        return self._desc.skill_id

    @property
    def skill_descriptor(self) -> SkillDescriptor:
        return self._desc

    def validate_input(self, parameters):
        return "x" in parameters

    def execute(self, parameters):
        return parameters["x"] ** 2


class TestSkills:
    def test_descriptor_create(self):
        d = SkillDescriptor.create("calc", SkillCategory.CALCULATION,
                                    description="adds numbers")
        assert d.category    == SkillCategory.CALCULATION
        assert d.description == "adds numbers"

    def test_mock_skill(self):
        s = _MockSkill()
        assert s.validate_input({"x": 5})
        assert not s.validate_input({})
        assert s.execute({"x": 4}) == 16

    def test_skill_registry_register(self):
        reg = SkillRegistry()
        s   = _MockSkill()
        reg.register(s)
        assert reg.get(s.skill_id).skill_id == s.skill_id

    def test_skill_registry_not_found(self):
        reg = SkillRegistry()
        with pytest.raises(AISkillNotFoundError):
            reg.get("nope")

    def test_skill_registry_list_by_category(self):
        reg = SkillRegistry()
        s1  = _MockSkill("calc", SkillCategory.CALCULATION)
        s2  = _MockSkill("parser", SkillCategory.PARSING)
        reg.register(s1)
        reg.register(s2)
        calcs   = reg.list_skills(SkillCategory.CALCULATION)
        parsers = reg.list_skills(SkillCategory.PARSING)
        assert s1 in calcs
        assert s2 not in calcs
        assert s2 in parsers

    def test_skill_category_values(self):
        assert SkillCategory.SUMMARIZATION.value  == "summarization"
        assert SkillCategory.CLASSIFICATION.value == "classification"


# ═════════════════════════════════════════════════════════════════════════════
# 11. EVENTS
# ═════════════════════════════════════════════════════════════════════════════

class TestEvents:
    def test_capability_registered(self):
        e = CapabilityRegisteredEvent.create("src", "cid", "my_tool")
        assert e.event_type      == CapabilityEventType.CAPABILITY_REGISTERED
        assert e.capability_name == "my_tool"

    def test_capability_enabled(self):
        e = CapabilityEnabledEvent.create("src", "cid")
        assert e.event_type == CapabilityEventType.CAPABILITY_ENABLED

    def test_capability_disabled(self):
        e = CapabilityDisabledEvent.create("src", "cid")
        assert e.event_type == CapabilityEventType.CAPABILITY_DISABLED

    def test_capability_deregistered(self):
        e = CapabilityDeregisteredEvent.create("src", "cid")
        assert e.event_type == CapabilityEventType.CAPABILITY_DEREGISTERED

    def test_capability_executed(self):
        e = CapabilityExecutedEvent.create("src", "cid", "agent_x", 12.5)
        assert e.duration_ms == pytest.approx(12.5)

    def test_capability_failed(self):
        e = CapabilityFailedEvent.create("src", "cid", "agent_x", "oops")
        assert e.error == "oops"

    def test_capability_timeout(self):
        e = CapabilityTimeoutEvent.create("src", "cid", "agent_x")
        assert e.event_type == CapabilityEventType.CAPABILITY_TIMEOUT

    def test_connector_registered(self):
        e = ConnectorRegisteredEvent.create("src", "con_id", "my_conn")
        assert e.connector_name == "my_conn"

    def test_connector_invoked(self):
        e = ConnectorInvokedEvent.create("src", "con_id", "get_quote")
        assert e.method == "get_quote"

    def test_skill_registered(self):
        e = SkillRegisteredEvent.create("src", "sid", "calc")
        assert e.skill_name == "calc"

    def test_skill_executed(self):
        e = SkillExecutedEvent.create("src", "sid", 3.5)
        assert e.duration_ms == pytest.approx(3.5)

    def test_auth_granted(self):
        e = AuthorizationGrantedEvent.create("src", "agent_x", "cap_001")
        assert e.principal_id  == "agent_x"
        assert e.capability_id == "cap_001"

    def test_auth_denied(self):
        e = AuthorizationDeniedEvent.create("src", "agent_x", "cap_001", "no permission")
        assert e.reason == "no permission"

    def test_quota_exceeded(self):
        e = QuotaExceededEvent.create("src", "agent_x", "cap_001", "daily")
        assert e.quota_type == "daily"

    def test_policy_added(self):
        e = PolicyAddedEvent.create("src", "pid", "deny-broker")
        assert e.policy_name == "deny-broker"

    def test_policy_removed(self):
        e = PolicyRemovedEvent.create("src", "pid")
        assert e.policy_id == "pid"


class TestCapabilityEventBus:
    def test_subscribe_publish(self):
        bus      = CapabilityEventBus()
        received = []
        bus.subscribe(CapabilityEventType.CAPABILITY_REGISTERED,
                      lambda e: received.append(e))
        bus.publish(CapabilityRegisteredEvent.create("src", "cid", "t"))
        assert len(received) == 1

    def test_unsubscribe(self):
        bus   = CapabilityEventBus()
        calls = []
        h     = lambda e: calls.append(e)
        bus.subscribe(CapabilityEventType.CAPABILITY_EXECUTED, h)
        bus.unsubscribe(CapabilityEventType.CAPABILITY_EXECUTED, h)
        bus.publish(CapabilityExecutedEvent.create("src", "c", "a"))
        assert len(calls) == 0

    def test_subscribe_all(self):
        bus  = CapabilityEventBus()
        seen = []
        bus.subscribe_all(lambda e: seen.append(e))
        bus.publish(CapabilityRegisteredEvent.create("src", "c1", "t1"))
        bus.publish(CapabilityEnabledEvent.create("src", "c1"))
        assert len(seen) == 2

    def test_exception_isolation(self):
        bus = CapabilityEventBus()
        bus.subscribe(CapabilityEventType.CAPABILITY_REGISTERED, lambda e: 1/0)
        bus.publish(CapabilityRegisteredEvent.create("src", "c", "t"))   # must not raise

    def test_history(self):
        bus = CapabilityEventBus()
        bus.publish(CapabilityRegisteredEvent.create("src", "c1", "t"))
        bus.publish(CapabilityEnabledEvent.create("src", "c1"))
        h = bus.history(CapabilityEventType.CAPABILITY_REGISTERED)
        assert len(h) == 1

    def test_clear_history(self):
        bus = CapabilityEventBus()
        bus.publish(CapabilityRegisteredEvent.create("src", "c", "t"))
        bus.clear_history()
        assert bus.history() == []


# ═════════════════════════════════════════════════════════════════════════════
# 12. SNAPSHOT
# ═════════════════════════════════════════════════════════════════════════════

class TestSnapshot:
    def test_build(self):
        snap = CapabilitySystemSnapshot.build(
            is_running=True, total_capabilities=10, active_capabilities=8,
            disabled_capabilities=2, total_connectors=3, total_skills=5,
            total_handlers=8, total_audit_records=100, total_executions=50,
            failed_executions=2, total_roles=4, total_permissions=12,
            policy_count=5, quota_count=3,
        )
        assert snap.is_running            is True
        assert snap.total_capabilities    == 10
        assert snap.active_capabilities   == 8
        assert snap.disabled_capabilities == 2
        assert snap.total_connectors      == 3
        assert snap.total_skills          == 5

    def test_unique_snapshot_id(self):
        s1 = CapabilitySystemSnapshot.build(
            True, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        s2 = CapabilitySystemSnapshot.build(
            True, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        assert s1.snapshot_id != s2.snapshot_id


# ═════════════════════════════════════════════════════════════════════════════
# 13. CONTAINER
# ═════════════════════════════════════════════════════════════════════════════

class TestContainer:
    def test_all_components(self):
        c = CapabilityContainer()
        assert c.event_bus    is not None
        assert c.registry     is not None
        assert c.connectors   is not None
        assert c.skills       is not None
        assert c.executor     is not None
        assert c.authorization is not None
        assert c.policy_engine is not None
        assert c.quota        is not None
        assert c.audit        is not None

    def test_same_instances(self):
        c = CapabilityContainer()
        assert c.registry is c.registry
        assert c.audit    is c.audit


# ═════════════════════════════════════════════════════════════════════════════
# 14. GATEWAY
# ═════════════════════════════════════════════════════════════════════════════

class TestGateway:
    def test_lifecycle(self):
        gw = CapabilityGateway()
        assert not gw.is_ai_running
        gw.start()
        assert gw.is_ai_running
        gw.stop()
        assert not gw.is_ai_running

    def test_system_id_version(self):
        gw = CapabilityGateway()
        assert gw.SYSTEM_ID == "iios:ai:capability:gateway"
        assert gw.VERSION   == "1.0.0"

    def test_call_without_start_raises(self):
        gw = CapabilityGateway()
        with pytest.raises(AICapabilityException):
            gw.list_capabilities()

    def test_register_and_find(self):
        gw = _gw()
        d  = _descriptor()
        gw.register_capability(d)
        found = gw.find_capability(d.descriptor_id)
        assert found is not None
        assert found.descriptor_id == d.descriptor_id
        gw.stop()

    def test_get_capability(self):
        gw = _gw()
        d  = _descriptor()
        gw.register_capability(d)
        assert gw.get_capability(d.descriptor_id).name == d.name
        gw.stop()

    def test_list_capabilities_empty(self):
        gw = _gw()
        assert gw.list_capabilities() == []
        gw.stop()

    def test_list_capabilities_with_filter(self):
        gw = _gw()
        t1 = _descriptor("tool_1",  cap_type=CapabilityType.TOOL)
        s1 = _descriptor("skill_1", cap_type=CapabilityType.SKILL)
        gw.register_capability(t1)
        gw.register_capability(s1)
        tools = gw.list_capabilities(capability_type=CapabilityType.TOOL)
        assert len(tools) == 1
        assert tools[0].descriptor_id == t1.descriptor_id
        gw.stop()

    def test_enable_disable(self):
        gw = _gw()
        d  = _descriptor()
        gw.register_capability(d)
        gw.disable_capability(d.descriptor_id)
        assert not gw.get_capability(d.descriptor_id).is_executable()
        gw.enable_capability(d.descriptor_id)
        assert gw.get_capability(d.descriptor_id).is_executable()
        gw.stop()

    def test_deregister(self):
        gw = _gw()
        d  = _descriptor()
        gw.register_capability(d)
        gw.deregister_capability(d.descriptor_id)
        assert gw.find_capability(d.descriptor_id) is None
        gw.stop()

    def test_register_handler_and_execute(self):
        gw = _gw()
        d  = _descriptor(requires_auth=False)
        gw.register_capability(d)
        gw.register_handler(d.descriptor_id, lambda p: p.get("x", 0) * 3)
        ctx  = _ctx()
        req  = CapabilityRequest.create(d.descriptor_id, ctx, x=7)
        resp = gw.execute_capability(req)
        assert resp.is_successful()
        assert resp.result.output == 21
        gw.stop()

    def test_execute_audits(self):
        gw = _gw()
        d  = _descriptor(requires_auth=False)
        gw.register_capability(d)
        gw.register_handler(d.descriptor_id, lambda p: "done")
        ctx = _ctx()
        req = CapabilityRequest.create(d.descriptor_id, ctx)
        gw.execute_capability(req)
        assert gw._c.audit.total_count() == 1
        gw.stop()

    def test_execute_emits_event(self):
        gw   = _gw()
        d    = _descriptor(requires_auth=False)
        gw.register_capability(d)
        gw.register_handler(d.descriptor_id, lambda p: "ok")
        seen = []
        # Subscribe BEFORE execution to capture the execution event
        gw._c.event_bus.subscribe_all(lambda e: seen.append(e.event_type))
        ctx  = _ctx()
        req  = CapabilityRequest.create(d.descriptor_id, ctx)
        gw.execute_capability(req)
        types = [e.value for e in seen]
        assert CapabilityEventType.CAPABILITY_EXECUTED.value in types
        gw.stop()

    def test_execute_requires_auth_denied(self):
        gw = _gw()
        d  = _descriptor(requires_auth=True)
        gw.register_capability(d)
        gw.register_handler(d.descriptor_id, lambda p: "ok")
        ctx = _ctx("no_perm_agent")
        req = CapabilityRequest.create(d.descriptor_id, ctx)
        with pytest.raises(AICapabilityPermissionDeniedError):
            gw.execute_capability(req)
        gw.stop()

    def test_execute_requires_auth_granted(self):
        gw   = _gw()
        d    = _descriptor(requires_auth=True)
        gw.register_capability(d)
        gw.register_handler(d.descriptor_id, lambda p: "ok")
        perm = CapabilityPermission.create("agent_x", d.descriptor_id)
        gw.grant_permission(perm)
        ctx  = _ctx("agent_x")
        req  = CapabilityRequest.create(d.descriptor_id, ctx)
        resp = gw.execute_capability(req)
        assert resp.is_successful()
        gw.stop()

    def test_execute_policy_deny(self):
        gw = _gw()
        d  = _descriptor(requires_auth=False)
        gw.register_capability(d)
        gw.register_handler(d.descriptor_id, lambda p: "ok")
        policy = CapabilityPolicy.create(
            "deny-cap", capability_pattern=d.descriptor_id,
            effect=PolicyEffect.DENY, priority=500
        )
        gw.add_policy(policy)
        ctx = _ctx()
        req = CapabilityRequest.create(d.descriptor_id, ctx)
        with pytest.raises(AICapabilityPolicyViolationError):
            gw.execute_capability(req)
        gw.stop()

    def test_execute_quota_exceeded(self):
        gw = _gw()
        d  = _descriptor(requires_auth=False)
        gw.register_capability(d)
        gw.register_handler(d.descriptor_id, lambda p: "ok")
        gw.set_quota("agent_x", d.descriptor_id, max_per_hour=1)
        ctx = _ctx("agent_x")
        gw.execute_capability(CapabilityRequest.create(d.descriptor_id, ctx))
        with pytest.raises(AICapabilityQuotaExceededError):
            gw.execute_capability(CapabilityRequest.create(d.descriptor_id, ctx))
        gw.stop()

    def test_authorize_capability(self):
        gw   = _gw()
        d    = _descriptor()
        gw.register_capability(d)
        perm = CapabilityPermission.create("agent_x", d.descriptor_id)
        gw.grant_permission(perm)
        assert gw.authorize_capability("agent_x", d.descriptor_id) is True
        gw.stop()

    def test_is_authorized(self):
        gw   = _gw()
        perm = CapabilityPermission.create("agent_x", "any_cap")
        gw.grant_permission(perm)
        assert gw.is_authorized("agent_x", "any_cap")
        assert not gw.is_authorized("agent_y", "any_cap")
        gw.stop()

    def test_revoke_permission(self):
        gw   = _gw()
        perm = CapabilityPermission.create("agent_x", "cap_001")
        gw.grant_permission(perm)
        gw.revoke_permission("agent_x", "cap_001")
        assert not gw.is_authorized("agent_x", "cap_001")
        gw.stop()

    def test_create_and_assign_role(self):
        gw   = _gw()
        role = CapabilityRole.create("analyst", frozenset({"data.*"}))
        gw.create_role(role)
        gw.assign_role("agent_x", "analyst")
        assert gw.is_authorized("agent_x", "data.read")
        gw.stop()

    def test_revoke_role(self):
        gw   = _gw()
        role = CapabilityRole.create("analyst", frozenset({"data.*"}))
        gw.create_role(role)
        gw.assign_role("agent_x", "analyst")
        gw.revoke_role("agent_x", "analyst")
        assert not gw.is_authorized("agent_x", "data.read")
        gw.stop()

    def test_list_roles(self):
        gw = _gw()
        assert gw.list_roles() == []
        role = CapabilityRole.create("analyst", frozenset({"data.*"}))
        gw.create_role(role)
        assert len(gw.list_roles()) == 1
        gw.stop()

    def test_add_and_remove_policy(self):
        gw     = _gw()
        policy = CapabilityPolicy.create("deny-broker", capability_pattern="broker.*",
                                          effect=PolicyEffect.DENY, priority=500)
        gw.add_policy(policy)
        assert len(gw.list_policies()) == 1
        gw.remove_policy(policy.policy_id)
        assert len(gw.list_policies()) == 0
        gw.stop()

    def test_evaluate_policy_allow(self):
        gw = _gw()
        assert gw.evaluate_policy("agent_x", "data.read") is True
        gw.stop()

    def test_evaluate_policy_deny(self):
        gw = _gw()
        p  = CapabilityPolicy.create("deny", capability_pattern="admin.*",
                                      effect=PolicyEffect.DENY)
        gw.add_policy(p)
        with pytest.raises(AICapabilityPolicyViolationError):
            gw.evaluate_policy("agent_x", "admin.delete")
        gw.stop()

    def test_quota_flow(self):
        gw = _gw()
        gw.set_quota("agent_x", "cap_001", max_per_hour=5)
        assert gw.check_quota("agent_x", "cap_001") is True
        usage = gw.get_usage("agent_x", "cap_001")
        assert usage["hour_count"] == 0
        gw.stop()

    def test_register_connector(self):
        gw = _gw()
        c  = _mock_connector()
        gw.register_connector(c)
        assert gw.get_connector(c.connector_id).connector_id == c.connector_id
        gw.stop()

    def test_list_connectors(self):
        gw = _gw()
        c1 = _mock_connector("c1", ConnectorType.HTTP_SERVICE)
        c2 = _mock_connector("c2", ConnectorType.DATABASE)
        gw.register_connector(c1)
        gw.register_connector(c2)
        http = gw.list_connectors(ConnectorType.HTTP_SERVICE)
        assert c1 in http
        assert c2 not in http
        gw.stop()

    def test_register_skill(self):
        gw = _gw()
        s  = _MockSkill()
        gw.register_skill(s)
        assert gw.get_skill(s.skill_id).skill_id == s.skill_id
        gw.stop()

    def test_list_skills(self):
        gw = _gw()
        s1 = _MockSkill("calc",   SkillCategory.CALCULATION)
        s2 = _MockSkill("parser", SkillCategory.PARSING)
        gw.register_skill(s1)
        gw.register_skill(s2)
        calcs = gw.list_skills(SkillCategory.CALCULATION)
        assert s1 in calcs
        assert s2 not in calcs
        gw.stop()

    def test_audit_report(self):
        gw = _gw()
        d  = _descriptor(requires_auth=False)
        gw.register_capability(d)
        gw.register_handler(d.descriptor_id, lambda p: "ok")
        ctx = _ctx("agent_x")
        gw.execute_capability(CapabilityRequest.create(d.descriptor_id, ctx))
        gw.execute_capability(CapabilityRequest.create(d.descriptor_id, ctx))
        report = gw.audit_report("agent_x")
        assert report.total_records   == 2
        assert report.success_count   == 2
        gw.stop()

    def test_health(self):
        gw = _gw()
        h  = gw.health()
        assert h["is_running"]         is True
        assert "total_capabilities"   in h
        assert h["system_id"]          == "iios:ai:capability:gateway"
        gw.stop()

    def test_snapshot(self):
        gw = _gw()
        d  = _descriptor()
        gw.register_capability(d)
        s  = gw.snapshot()
        assert s.is_running          is True
        assert s.total_capabilities  == 1
        assert s.active_capabilities == 1
        gw.stop()

    def test_events_emitted_on_register(self):
        gw   = _gw()
        seen = []
        gw._c.event_bus.subscribe(CapabilityEventType.CAPABILITY_REGISTERED,
                                   lambda e: seen.append(e))
        gw.register_capability(_descriptor())
        assert len(seen) == 1
        gw.stop()

    def test_connector_event_emitted(self):
        gw   = _gw()
        seen = []
        gw._c.event_bus.subscribe(CapabilityEventType.CONNECTOR_REGISTERED,
                                   lambda e: seen.append(e))
        gw.register_connector(_mock_connector())
        assert len(seen) == 1
        gw.stop()

    def test_skill_event_emitted(self):
        gw   = _gw()
        seen = []
        gw._c.event_bus.subscribe(CapabilityEventType.SKILL_REGISTERED,
                                   lambda e: seen.append(e))
        gw.register_skill(_MockSkill())
        assert len(seen) == 1
        gw.stop()

    def test_query_audit(self):
        gw = _gw()
        d  = _descriptor(requires_auth=False)
        gw.register_capability(d)
        gw.register_handler(d.descriptor_id, lambda p: "ok")
        ctx = _ctx("agent_x")
        gw.execute_capability(CapabilityRequest.create(d.descriptor_id, ctx))
        records = gw.query_audit(principal_id="agent_x")
        assert len(records) >= 1
        gw.stop()
