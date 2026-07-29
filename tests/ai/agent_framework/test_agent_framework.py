"""
test_agent_framework.py -- tests.ai.agent_framework
====================================================
Comprehensive test suite for A5 — AI Agent Framework.

Test classes
------------
TestAgentIdentity          — AgentIdentity, AgentMetadata
TestAgentCapabilities      — CapabilityType, AgentCapability, AgentCapabilities
TestAgentConfiguration     — AgentConfiguration settings management
TestAgentPermissions       — grant/revoke/check permissions
TestAgentHealthAndMetrics  — health states, metrics accumulation
TestAgentSpec              — AgentSpec factory, properties
TestAgentEvents            — event creation, event bus pub/sub
TestBaseAgent              — lifecycle transitions, hooks, thread safety
TestAgentRegistry          — register, find, list, unregister
TestAgentFactory           — builder registration, agent creation
TestAgentManager           — full lifecycle through manager
TestAgentExecution         — task creation, execution, results
TestCapabilityFramework    — CapabilityDefinition, CapabilityRegistry
TestRoleFramework          — AgentRole, AgentProfile, CapabilityProfile, PermissionProfile
TestPolicyFramework        — ExecutionPolicy, PermissionPolicy, CapabilityPolicy
TestSnapshotFramework      — AgentSnapshot, AgentFrameworkSnapshot
TestSpecialistAgents       — all 14 specialist placeholders
TestGateway                — full gateway lifecycle and all public APIs
"""
from __future__ import annotations

import time
from typing import Any

import pytest

# ── Core imports ──────────────────────────────────────────────────────────────
from iios.ai.agent_framework.core.agent_identity    import AgentIdentity, AgentMetadata
from iios.ai.agent_framework.core.agent_capabilities import (
    CapabilityType, AgentCapability, AgentCapabilities,
)
from iios.ai.agent_framework.core.agent_config       import AgentConfiguration
from iios.ai.agent_framework.core.agent_permissions  import (
    PermissionLevel, AgentPermission, AgentPermissions,
)
from iios.ai.agent_framework.core.agent_health       import HealthStatus, AgentHealth
from iios.ai.agent_framework.core.agent_metrics      import MetricRecord, AgentMetrics
from iios.ai.agent_framework.core.agent_spec         import AgentSpec

# ── Events ────────────────────────────────────────────────────────────────────
from iios.ai.agent_framework.events.agent_events     import (
    AgentEventType,
    AgentRegisteredEvent, AgentStartedEvent, AgentStoppedEvent,
    AgentSuspendedEvent, AgentResumedEvent, AgentHealthChangedEvent,
    TaskAssignedEvent, TaskStartedEvent, TaskCompletedEvent, TaskFailedEvent,
    CapabilityAddedEvent, PermissionGrantedEvent, PermissionRevokedEvent,
)
from iios.ai.agent_framework.events.agent_event_bus  import AgentEventBus

# ── Engine ────────────────────────────────────────────────────────────────────
from iios.ai.agent_framework.engine.agent_task              import (
    TaskStatus, TaskPriority, AgentTask, AgentResult,
)
from iios.ai.agent_framework.engine.agent_execution_context import AgentExecutionContext
from iios.ai.agent_framework.engine.agent_execution_engine  import AgentExecutionEngine

# ── Base ──────────────────────────────────────────────────────────────────────
from iios.ai.agent_framework.base.base_agent import BaseAIAgent

# ── Registry ──────────────────────────────────────────────────────────────────
from iios.ai.agent_framework.registry.agent_descriptor import AgentDescriptor
from iios.ai.agent_framework.registry.agent_registry   import AgentRegistry
from iios.ai.agent_framework.registry.agent_factory    import AgentFactory

# ── Manager ───────────────────────────────────────────────────────────────────
from iios.ai.agent_framework.manager.agent_manager import AgentManager

# ── Capabilities ──────────────────────────────────────────────────────────────
from iios.ai.agent_framework.capabilities.capability_definitions import (
    CapabilityDefinition, CapabilityRegistry,
)

# ── Roles ─────────────────────────────────────────────────────────────────────
from iios.ai.agent_framework.roles.agent_role          import RoleType, AgentRole
from iios.ai.agent_framework.roles.capability_profile  import CapabilityProfile
from iios.ai.agent_framework.roles.permission_profile  import PermissionProfile
from iios.ai.agent_framework.roles.agent_profile       import AgentProfile

# ── Policy ────────────────────────────────────────────────────────────────────
from iios.ai.agent_framework.policy.execution_policy  import (
    DefaultExecutionPolicy, ActiveOnlyPolicy, RateLimitPolicy,
)
from iios.ai.agent_framework.policy.permission_policy import (
    DefaultPermissionPolicy, StrictPermissionPolicy,
)
from iios.ai.agent_framework.policy.capability_policy import (
    DefaultCapabilityPolicy, StrictCapabilityPolicy,
)

# ── Snapshot ──────────────────────────────────────────────────────────────────
from iios.ai.agent_framework.snapshot.agent_snapshot import (
    AgentSnapshot, AgentFrameworkSnapshot,
)

# ── Specialists ───────────────────────────────────────────────────────────────
from iios.ai.agent_framework.specialists.specialist_agents import (
    MarketAnalystAgent, TechnicalAnalystAgent, FundamentalAnalystAgent,
    MacroAnalystAgent, NewsAnalystAgent, SentimentAnalystAgent,
    RiskAnalystAgent, PortfolioAnalystAgent, ComplianceAnalystAgent,
    ResearchAnalystAgent, OptionsAnalystAgent, CryptoAnalystAgent,
    AuditAgent, LearningAgent, ALL_SPECIALIST_CLASSES,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from iios.ai.agent_framework.exceptions import (
    AIAgentNotFoundError, AIAgentAlreadyExistsError,
    AIAgentNotRunningError, AIAgentAlreadyRunningError,
    AIAgentValidationError,
    AITaskNotFoundError, AITaskExecutionError, AITaskTimeoutError,
    AICapabilityNotFoundError, AICapabilityNotPermittedError,
    AIRegistrationFailedError,
    AIPermissionDeniedError, AIPermissionNotFoundError,
    AIRoleNotFoundError,
    AIAgentPolicyViolationError,
)

# ── Gateway ───────────────────────────────────────────────────────────────────
from iios.ai.agent_framework.gateway.agent_framework_gateway import AgentFrameworkGateway


# ===========================================================================
# Shared fixtures and concrete test agent
# ===========================================================================

class EchoAgent(BaseAIAgent):
    """Minimal concrete agent that echoes its payload back."""

    AGENT_TYPE = "EchoAgent"

    def execute_task(self, task: AgentTask, context: AgentExecutionContext) -> AgentResult:
        return AgentResult.success(task, {"echo": task.payload}, time.time())


def _make_spec(agent_name: str = "Echo", agent_type: str = "EchoAgent") -> AgentSpec:
    identity = AgentIdentity.create(agent_name, agent_type)
    return AgentSpec.create(
        identity     = identity,
        description  = "Test agent",
        capabilities = AgentCapabilities.create(
            AgentCapability.create(CapabilityType.ANALYSIS, "Echo Analysis"),
        ),
        permissions = AgentPermissions.create(
            AgentPermission.create("market_data", PermissionLevel.READ),
        ),
    )


def _make_agent(agent_name: str = "Echo") -> EchoAgent:
    return EchoAgent(_make_spec(agent_name))


@pytest.fixture
def spec() -> AgentSpec:
    return _make_spec()


@pytest.fixture
def agent() -> EchoAgent:
    return _make_agent()


@pytest.fixture
def active_agent() -> EchoAgent:
    a = _make_agent()
    a.activate()
    return a


@pytest.fixture
def registry() -> AgentRegistry:
    return AgentRegistry()


@pytest.fixture
def event_bus() -> AgentEventBus:
    return AgentEventBus()


@pytest.fixture
def factory() -> AgentFactory:
    f = AgentFactory()
    f.register_builder("EchoAgent", EchoAgent)
    return f


@pytest.fixture
def manager(registry, factory, event_bus) -> AgentManager:
    return AgentManager(registry, factory, event_bus)


@pytest.fixture
def engine(registry, event_bus) -> AgentExecutionEngine:
    return AgentExecutionEngine(registry=registry, event_bus=event_bus)


@pytest.fixture
def gateway() -> AgentFrameworkGateway:
    gw = AgentFrameworkGateway()
    gw.initialize()
    gw.start()
    return gw


# ===========================================================================
# T1 — Agent Identity
# ===========================================================================

class TestAgentIdentity:
    def test_create_generates_uuid(self):
        i = AgentIdentity.create("Foo", "FooAgent")
        assert len(i.agent_id) == 36  # UUID4

    def test_qualified_name_format(self):
        i = AgentIdentity.create("Foo", "FooAgent", namespace="iios:test")
        assert i.qualified_name == "iios:test:Foo:1.0.0"

    def test_immutable(self):
        i = AgentIdentity.create("Foo", "FooAgent")
        with pytest.raises((AttributeError, TypeError)):
            i.agent_name = "Bar"  # type: ignore[misc]

    def test_metadata_create(self):
        i = AgentIdentity.create("Foo", "FooAgent")
        m = AgentMetadata.create(i, description="desc", author="alice", tags=["tag1"])
        assert m.description == "desc"
        assert m.author == "alice"
        assert "tag1" in m.tags

    def test_metadata_timestamps(self):
        before = time.time()
        i = AgentIdentity.create("X", "X")
        m = AgentMetadata.create(i)
        after = time.time()
        assert before <= m.created_at <= after
        assert m.created_at == m.updated_at

    def test_different_agents_have_different_ids(self):
        a = AgentIdentity.create("A", "AAgent")
        b = AgentIdentity.create("A", "AAgent")
        assert a.agent_id != b.agent_id


# ===========================================================================
# T2 — Agent Capabilities
# ===========================================================================

class TestAgentCapabilities:
    def test_capability_type_values(self):
        assert CapabilityType.ANALYSIS.value == "analysis"
        assert CapabilityType.PREDICTION.value == "prediction"

    def test_capability_create(self):
        c = AgentCapability.create(CapabilityType.RESEARCH, "Research", "desc")
        assert c.capability_type == CapabilityType.RESEARCH
        assert c.name == "Research"

    def test_capabilities_has_capability(self):
        caps = AgentCapabilities.create(
            AgentCapability.create(CapabilityType.ANALYSIS, "A"),
        )
        assert caps.has_capability(CapabilityType.ANALYSIS)
        assert not caps.has_capability(CapabilityType.PLANNING)

    def test_capabilities_by_type(self):
        c1 = AgentCapability.create(CapabilityType.ANALYSIS, "A1")
        c2 = AgentCapability.create(CapabilityType.ANALYSIS, "A2")
        c3 = AgentCapability.create(CapabilityType.RESEARCH,  "R1")
        caps = AgentCapabilities.create(c1, c2, c3)
        assert len(caps.by_type(CapabilityType.ANALYSIS)) == 2
        assert len(caps.by_type(CapabilityType.RESEARCH))  == 1

    def test_capabilities_add(self):
        caps = AgentCapabilities.empty()
        assert caps.count() == 0
        new_caps = caps.add(AgentCapability.create(CapabilityType.PLANNING, "P"))
        assert new_caps.count() == 1
        assert caps.count() == 0  # original unchanged

    def test_capabilities_types_set(self):
        c1 = AgentCapability.create(CapabilityType.ANALYSIS, "A")
        c2 = AgentCapability.create(CapabilityType.RESEARCH,  "R")
        caps = AgentCapabilities.create(c1, c2)
        types = caps.capability_types()
        assert CapabilityType.ANALYSIS in types
        assert CapabilityType.RESEARCH in types

    def test_capability_immutable(self):
        c = AgentCapability.create(CapabilityType.ANALYSIS, "A")
        with pytest.raises((AttributeError, TypeError)):
            c.name = "B"  # type: ignore[misc]


# ===========================================================================
# T3 — Agent Configuration
# ===========================================================================

class TestAgentConfiguration:
    def test_create_stores_settings(self):
        cfg = AgentConfiguration.create("agent-1", timeout_ms=5000, retries=3)
        assert cfg.get("timeout_ms") == 5000
        assert cfg.get("retries")    == 3

    def test_get_missing_returns_default(self):
        cfg = AgentConfiguration.empty("a")
        assert cfg.get("missing") is None
        assert cfg.get("missing", "x") == "x"

    def test_with_settings_bumps_version(self):
        cfg  = AgentConfiguration.create("a", x=1)
        cfg2 = cfg.with_settings(x=2, y=3)
        assert cfg2.version == cfg.version + 1
        assert cfg2.get("x") == 2
        assert cfg2.get("y") == 3

    def test_with_settings_original_unchanged(self):
        cfg  = AgentConfiguration.create("a", x=1)
        cfg2 = cfg.with_settings(x=99)
        assert cfg.get("x") == 1  # original intact

    def test_as_dict(self):
        cfg = AgentConfiguration.create("a", k1="v1", k2="v2")
        d = cfg.as_dict()
        assert d["k1"] == "v1"
        assert d["k2"] == "v2"


# ===========================================================================
# T4 — Agent Permissions
# ===========================================================================

class TestAgentPermissions:
    def test_has_permission_exact_level(self):
        perms = AgentPermissions.create(
            AgentPermission.create("market_data", PermissionLevel.READ),
        )
        assert perms.has_permission("market_data", PermissionLevel.READ)

    def test_higher_level_satisfies_lower(self):
        perms = AgentPermissions.create(
            AgentPermission.create("portfolio", PermissionLevel.ADMIN),
        )
        assert perms.has_permission("portfolio", PermissionLevel.READ)
        assert perms.has_permission("portfolio", PermissionLevel.WRITE)
        assert perms.has_permission("portfolio", PermissionLevel.EXECUTE)

    def test_lower_level_does_not_satisfy_higher(self):
        perms = AgentPermissions.create(
            AgentPermission.create("risk", PermissionLevel.READ),
        )
        assert not perms.has_permission("risk", PermissionLevel.WRITE)

    def test_missing_resource_denied(self):
        perms = AgentPermissions.empty()
        assert not perms.has_permission("market_data", PermissionLevel.READ)

    def test_wildcard_grant(self):
        perms = AgentPermissions.create(
            AgentPermission.create("*", PermissionLevel.READ),
        )
        assert perms.has_permission("market_data", PermissionLevel.READ)
        assert perms.has_permission("portfolio",   PermissionLevel.READ)

    def test_grant_returns_new_instance(self):
        perms  = AgentPermissions.empty()
        perms2 = perms.grant(AgentPermission.create("x", PermissionLevel.READ))
        assert perms.count()  == 0
        assert perms2.count() == 1

    def test_revoke(self):
        p = AgentPermission.create("market_data", PermissionLevel.READ)
        perms  = AgentPermissions.create(p)
        perms2 = perms.revoke("market_data")
        assert not perms2.has_permission("market_data", PermissionLevel.READ)

    def test_assert_permission_raises(self):
        perms = AgentPermissions.empty()
        with pytest.raises(AIPermissionDeniedError):
            perms.assert_permission("market_data", PermissionLevel.READ)

    def test_permission_level_rank_order(self):
        assert PermissionLevel.NONE.rank()    == 0
        assert PermissionLevel.READ.rank()    == 1
        assert PermissionLevel.WRITE.rank()   == 2
        assert PermissionLevel.EXECUTE.rank() == 3
        assert PermissionLevel.ADMIN.rank()   == 4


# ===========================================================================
# T5 — Agent Health and Metrics
# ===========================================================================

class TestAgentHealthAndMetrics:
    def test_health_healthy(self):
        h = AgentHealth.healthy("a1", "OK")
        assert h.is_healthy()
        assert h.is_usable()
        assert h.status == HealthStatus.HEALTHY

    def test_health_degraded_is_usable(self):
        h = AgentHealth.degraded("a1", "slowed")
        assert not h.is_healthy()
        assert h.is_usable()

    def test_health_unhealthy_not_usable(self):
        h = AgentHealth.unhealthy("a1", "crashed")
        assert not h.is_usable()

    def test_health_unknown(self):
        h = AgentHealth.unknown("a1")
        assert h.status == HealthStatus.UNKNOWN

    def test_health_details_as_dict(self):
        h = AgentHealth.healthy("a1", key="val")
        assert h.details_as_dict()["key"] == "val"

    def test_metrics_empty(self):
        m = AgentMetrics.empty("a1")
        assert m.tasks_assigned  == 0
        assert m.tasks_completed == 0
        assert m.tasks_failed    == 0
        assert m.success_rate    == 0.0

    def test_metrics_task_assigned(self):
        m = AgentMetrics.empty("a1").with_task_assigned()
        assert m.tasks_assigned == 1

    def test_metrics_task_completed(self):
        m = AgentMetrics.empty("a1").with_task_completed(100.0)
        assert m.tasks_completed    == 1
        assert m.avg_execution_ms   == 100.0
        assert m.total_execution_ms == 100.0

    def test_metrics_task_failed(self):
        m = AgentMetrics.empty("a1").with_task_failed()
        assert m.tasks_failed == 1

    def test_metrics_success_rate(self):
        m = (
            AgentMetrics.empty("a1")
            .with_task_completed(10.0)
            .with_task_completed(10.0)
            .with_task_failed()
        )
        assert abs(m.success_rate - 2/3) < 0.001

    def test_metrics_immutable(self):
        m  = AgentMetrics.empty("a1")
        m2 = m.with_task_assigned()
        assert m.tasks_assigned  == 0
        assert m2.tasks_assigned == 1

    def test_metric_record_create(self):
        r = MetricRecord.create("a1", "latency_ms", 42.5, "ms")
        assert r.name  == "latency_ms"
        assert r.value == 42.5
        assert r.unit  == "ms"


# ===========================================================================
# T6 — Agent Spec
# ===========================================================================

class TestAgentSpec:
    def test_spec_create(self, spec):
        assert spec.agent_name == "Echo"
        assert spec.agent_type == "EchoAgent"

    def test_spec_qualified_name(self, spec):
        assert "Echo" in spec.qualified_name
        assert "1.0.0" in spec.qualified_name

    def test_spec_initial_health_healthy(self, spec):
        h = spec.initial_health()
        assert h.is_healthy()

    def test_spec_initial_metrics_empty(self, spec):
        m = spec.initial_metrics()
        assert m.tasks_assigned == 0

    def test_spec_immutable(self, spec):
        with pytest.raises((AttributeError, TypeError)):
            spec.agent_type = "X"  # type: ignore[misc]


# ===========================================================================
# T7 — Agent Events
# ===========================================================================

class TestAgentEvents:
    def test_registered_event_fields(self):
        e = AgentRegisteredEvent.create("id1", "Echo", "EchoAgent")
        assert e.event_type  == AgentEventType.AGENT_REGISTERED
        assert e.agent_name  == "Echo"
        assert e.agent_type  == "EchoAgent"
        assert len(e.event_id) == 36

    def test_task_assigned_event(self):
        e = TaskAssignedEvent.create("a1", "t1", "analyse", "high")
        assert e.event_type == AgentEventType.TASK_ASSIGNED
        assert e.task_id    == "t1"
        assert e.priority   == "high"

    def test_task_completed_event(self):
        e = TaskCompletedEvent.create("a1", "t1", 55.0)
        assert e.execution_ms == 55.0

    def test_task_failed_event(self):
        e = TaskFailedEvent.create("a1", "t1", "boom")
        assert e.error_message == "boom"

    def test_health_changed_event(self):
        e = AgentHealthChangedEvent.create("a1", "healthy", "degraded", "slow")
        assert e.previous_status == "healthy"
        assert e.current_status  == "degraded"

    def test_event_bus_subscribe_publish(self):
        bus     = AgentEventBus()
        received = []
        bus.subscribe(AgentEventType.AGENT_REGISTERED, received.append)
        bus.publish(AgentRegisteredEvent.create("a1", "Echo", "EchoAgent"))
        assert len(received) == 1

    def test_event_bus_unsubscribe(self):
        bus     = AgentEventBus()
        received = []
        bus.subscribe(AgentEventType.AGENT_STARTED, received.append)
        bus.unsubscribe(AgentEventType.AGENT_STARTED, received.append)
        bus.publish(AgentStartedEvent.create("a1"))
        assert len(received) == 0

    def test_event_bus_published_count(self):
        bus = AgentEventBus()
        bus.publish(AgentStartedEvent.create("a1"))
        bus.publish(AgentStoppedEvent.create("a1"))
        assert bus.published_count == 2

    def test_event_bus_subscriber_count(self):
        bus = AgentEventBus()
        bus.subscribe(AgentEventType.TASK_ASSIGNED, lambda e: None)
        bus.subscribe(AgentEventType.TASK_ASSIGNED, lambda e: None)
        assert bus.subscriber_count(AgentEventType.TASK_ASSIGNED) == 2

    def test_event_bus_handler_exception_does_not_propagate(self):
        bus = AgentEventBus()
        bus.subscribe(AgentEventType.AGENT_STARTED, lambda e: 1/0)
        bus.publish(AgentStartedEvent.create("a1"))  # should not raise

    def test_event_bus_clear(self):
        bus = AgentEventBus()
        bus.subscribe(AgentEventType.AGENT_STARTED, lambda e: None)
        bus.clear()
        assert bus.subscriber_count(AgentEventType.AGENT_STARTED) == 0

    def test_events_are_immutable(self):
        e = AgentStartedEvent.create("a1")
        with pytest.raises((AttributeError, TypeError)):
            e.agent_id = "x"  # type: ignore[misc]


# ===========================================================================
# T8 — Base Agent
# ===========================================================================

class TestBaseAgent:
    def test_initial_state_inactive(self, agent):
        assert not agent.is_active
        assert not agent.is_shutdown

    def test_activate_sets_active(self, agent):
        agent.activate()
        assert agent.is_active

    def test_double_activate_raises(self, agent):
        agent.activate()
        with pytest.raises(AIAgentAlreadyRunningError):
            agent.activate()

    def test_suspend_from_active(self, active_agent):
        active_agent.suspend()
        assert not active_agent.is_active

    def test_suspend_from_inactive_raises(self, agent):
        with pytest.raises(AIAgentNotRunningError):
            agent.suspend()

    def test_resume_after_suspend(self, active_agent):
        active_agent.suspend()
        active_agent.resume()
        assert active_agent.is_active

    def test_resume_when_active_raises(self, active_agent):
        with pytest.raises(AIAgentAlreadyRunningError):
            active_agent.resume()

    def test_shutdown_stops_agent(self, active_agent):
        active_agent.shutdown()
        assert not active_agent.is_active
        assert active_agent.is_shutdown

    def test_shutdown_idempotent(self, agent):
        agent.shutdown()
        agent.shutdown()  # second call should not raise

    def test_get_health_returns_health(self, agent):
        h = agent.get_health()
        assert isinstance(h, AgentHealth)

    def test_active_agent_health_healthy(self, active_agent):
        assert active_agent.get_health().is_healthy()

    def test_shutdown_agent_health_unhealthy(self, agent):
        agent.shutdown()
        assert not agent.get_health().is_healthy()

    def test_metrics_initially_empty(self, agent):
        m = agent.metrics
        assert m.tasks_assigned == 0

    def test_record_task_assigned(self, agent):
        agent.record_task_assigned()
        assert agent.metrics.tasks_assigned == 1

    def test_record_task_completed(self, agent):
        agent.record_task_assigned()
        agent.record_task_completed(50.0)
        assert agent.metrics.tasks_completed == 1
        assert agent.metrics.avg_execution_ms == 50.0

    def test_record_task_failed(self, agent):
        agent.record_task_failed()
        assert agent.metrics.tasks_failed == 1

    def test_repr(self, agent):
        r = repr(agent)
        assert "EchoAgent" in r
        assert "inactive" in r


# ===========================================================================
# T9 — Agent Task and Result
# ===========================================================================

class TestAgentExecution:
    def test_task_create(self):
        t = AgentTask.create("a1", "analyse", {"x": 1}, priority=TaskPriority.HIGH)
        assert t.agent_id  == "a1"
        assert t.task_type == "analyse"
        assert t.priority  == TaskPriority.HIGH
        assert len(t.task_id) == 36

    def test_task_get_meta(self):
        t = AgentTask.create("a1", "analyse", foo="bar")
        assert t.get_meta("foo") == "bar"
        assert t.get_meta("missing") is None

    def test_result_success(self):
        t = AgentTask.create("a1", "x")
        r = AgentResult.success(t, {"ok": True}, time.time())
        assert r.is_success()
        assert not r.is_failure()
        assert r.output == {"ok": True}
        assert r.error  is None

    def test_result_failure(self):
        t = AgentTask.create("a1", "x")
        r = AgentResult.failure(t, "boom", time.time())
        assert r.is_failure()
        assert r.error == "boom"

    def test_result_execution_ms_positive(self):
        t = AgentTask.create("a1", "x")
        started = time.time() - 0.05
        r = AgentResult.success(t, {}, started)
        assert r.execution_ms >= 0

    def test_execution_context_create(self):
        ctx = AgentExecutionContext.create("a1", "t1", key="val")
        assert ctx.agent_id    == "a1"
        assert ctx.task_id     == "t1"
        assert ctx.get_meta("key") == "val"
        assert not ctx.has_memory
        assert not ctx.has_prompt
        assert not ctx.has_model

    def test_execution_context_with_gateways(self):
        ctx = AgentExecutionContext.create("a1", "t1", memory_gateway=object())
        assert ctx.has_memory

    def test_engine_executes_task(self, registry, event_bus, active_agent):
        registry.register(active_agent)
        engine = AgentExecutionEngine(registry=registry, event_bus=event_bus)
        task   = AgentTask.create(active_agent.agent_id, "analyse", {"data": 42})
        result = engine.assign_task(task)
        assert result.is_success()
        assert result.output == {"echo": {"data": 42}}

    def test_engine_publishes_events(self, registry, event_bus, active_agent):
        registry.register(active_agent)
        engine   = AgentExecutionEngine(registry=registry, event_bus=event_bus)
        received = []
        event_bus.subscribe(AgentEventType.TASK_COMPLETED, received.append)
        task = AgentTask.create(active_agent.agent_id, "analyse")
        engine.assign_task(task)
        assert len(received) == 1

    def test_engine_inactive_agent_raises(self, registry, event_bus, agent):
        registry.register(agent)  # NOT activated
        engine = AgentExecutionEngine(registry=registry, event_bus=event_bus)
        task   = AgentTask.create(agent.agent_id, "analyse")
        with pytest.raises(AIAgentNotRunningError):
            engine.assign_task(task)

    def test_engine_updates_agent_metrics(self, registry, event_bus, active_agent):
        registry.register(active_agent)
        engine = AgentExecutionEngine(registry=registry, event_bus=event_bus)
        task   = AgentTask.create(active_agent.agent_id, "analyse")
        engine.assign_task(task)
        assert active_agent.metrics.tasks_completed == 1


# ===========================================================================
# T10 — Agent Registry
# ===========================================================================

class TestAgentRegistry:
    def test_register_and_count(self, registry, agent):
        registry.register(agent)
        assert registry.count() == 1

    def test_register_duplicate_raises(self, registry, agent):
        registry.register(agent)
        with pytest.raises(AIAgentAlreadyExistsError):
            registry.register(agent)

    def test_get_registered(self, registry, agent):
        registry.register(agent)
        found = registry.get(agent.agent_id)
        assert found is agent

    def test_get_missing_raises(self, registry):
        with pytest.raises(AIAgentNotFoundError):
            registry.get("nonexistent-id")

    def test_unregister(self, registry, agent):
        registry.register(agent)
        registry.unregister(agent.agent_id)
        assert registry.count() == 0

    def test_unregister_missing_raises(self, registry):
        with pytest.raises(AIAgentNotFoundError):
            registry.unregister("nonexistent-id")

    def test_is_registered(self, registry, agent):
        assert not registry.is_registered(agent.agent_id)
        registry.register(agent)
        assert registry.is_registered(agent.agent_id)

    def test_find_by_name(self, registry):
        a = _make_agent("Alpha")
        b = _make_agent("Beta")
        registry.register(a)
        registry.register(b)
        found = registry.find_by_name("Alpha")
        assert found is a

    def test_find_by_type(self, registry):
        a1 = _make_agent("A1")
        a2 = _make_agent("A2")
        registry.register(a1)
        registry.register(a2)
        found = registry.find_by_type("EchoAgent")
        assert len(found) == 2

    def test_find_by_capability(self, registry, agent):
        registry.register(agent)
        found = registry.find_by_capability(CapabilityType.ANALYSIS)
        assert agent in found

    def test_find_active(self, registry):
        a = _make_agent("A")
        b = _make_agent("B")
        a.activate()
        registry.register(a)
        registry.register(b)
        assert a in registry.find_active()
        assert b not in registry.find_active()

    def test_list_all_returns_descriptors(self, registry, agent):
        registry.register(agent)
        descriptors = registry.list_all()
        assert len(descriptors) == 1
        assert isinstance(descriptors[0], AgentDescriptor)


# ===========================================================================
# T11 — Agent Factory
# ===========================================================================

class TestAgentFactory:
    def test_create_registered_type(self, factory, spec):
        agent = factory.create(spec)
        assert isinstance(agent, EchoAgent)

    def test_create_unregistered_raises(self, factory):
        identity = AgentIdentity.create("X", "UnknownType")
        spec     = AgentSpec.create(identity)
        with pytest.raises(AIAgentNotFoundError):
            factory.create(spec)

    def test_register_non_callable_raises(self, factory):
        with pytest.raises(AIRegistrationFailedError):
            factory.register_builder("bad", "not_callable")  # type: ignore

    def test_can_create(self, factory):
        assert factory.can_create("EchoAgent")
        assert not factory.can_create("UnknownAgent")

    def test_available_types(self, factory):
        assert "EchoAgent" in factory.available_types()

    def test_unregister_builder(self, factory):
        factory.unregister_builder("EchoAgent")
        assert not factory.can_create("EchoAgent")


# ===========================================================================
# T12 — Agent Manager
# ===========================================================================

class TestAgentManager:
    def test_register_agent(self, manager, agent):
        desc = manager.register_agent(agent)
        assert isinstance(desc, AgentDescriptor)

    def test_register_publishes_event(self, manager, event_bus, agent):
        received = []
        event_bus.subscribe(AgentEventType.AGENT_REGISTERED, received.append)
        manager.register_agent(agent)
        assert len(received) == 1

    def test_create_and_register(self, manager, spec):
        agent = manager.create_and_register(spec)
        assert isinstance(agent, EchoAgent)

    def test_start_agent(self, manager, agent):
        manager.register_agent(agent)
        manager.start_agent(agent.agent_id)
        assert agent.is_active

    def test_stop_agent(self, manager, agent):
        manager.register_agent(agent)
        manager.start_agent(agent.agent_id)
        manager.stop_agent(agent.agent_id)
        assert agent.is_shutdown

    def test_suspend_and_resume(self, manager, agent):
        manager.register_agent(agent)
        manager.start_agent(agent.agent_id)
        manager.suspend_agent(agent.agent_id)
        assert not agent.is_active
        manager.resume_agent(agent.agent_id)
        assert agent.is_active

    def test_list_agents(self, manager, agent):
        manager.register_agent(agent)
        assert len(manager.list_agents()) == 1

    def test_find_agent(self, manager, agent):
        manager.register_agent(agent)
        found = manager.find_agent(agent.agent_id)
        assert found is agent

    def test_find_agents_by_capability(self, manager, agent):
        manager.register_agent(agent)
        found = manager.find_agents_by_capability(CapabilityType.ANALYSIS)
        assert len(found) == 1

    def test_get_agent_health(self, manager, agent):
        manager.register_agent(agent)
        h = manager.get_agent_health(agent.agent_id)
        assert isinstance(h, AgentHealth)

    def test_get_agent_metrics(self, manager, agent):
        manager.register_agent(agent)
        m = manager.get_agent_metrics(agent.agent_id)
        assert isinstance(m, AgentMetrics)


# ===========================================================================
# T13 — Capability Framework
# ===========================================================================

class TestCapabilityFramework:
    def test_builtin_capabilities_registered(self):
        for ct in CapabilityType:
            if ct != CapabilityType.CUSTOM:
                assert CapabilityRegistry.is_registered(ct)

    def test_get_analysis_definition(self):
        defn = CapabilityRegistry.get(CapabilityType.ANALYSIS)
        assert defn.name == "Analysis"

    def test_get_unknown_raises(self):
        # Temporarily clear registry, verify get() raises, then restore
        saved = dict(CapabilityRegistry._definitions)
        CapabilityRegistry._definitions.clear()
        try:
            with pytest.raises(AICapabilityNotFoundError):
                CapabilityRegistry.get(CapabilityType.ANALYSIS)
        finally:
            CapabilityRegistry._definitions.update(saved)

    def test_list_all_not_empty(self):
        assert len(CapabilityRegistry.list_all()) >= 8

    def test_custom_registration(self):
        defn = CapabilityDefinition(
            capability_type = CapabilityType.CUSTOM,
            name            = "Custom Test",
            description     = "For testing",
            input_schema    = None,
            output_schema   = None,
            version         = "1.0.0",
        )
        CapabilityRegistry.register(defn)
        retrieved = CapabilityRegistry.get(CapabilityType.CUSTOM)
        assert retrieved.name == "Custom Test"


# ===========================================================================
# T14 — Role Framework
# ===========================================================================

class TestRoleFramework:
    def test_agent_role_create(self):
        role = AgentRole.create(
            role_type            = RoleType.ANALYST,
            name                 = "Analyst",
            description          = "Analyses data",
            default_capabilities = frozenset({CapabilityType.ANALYSIS}),
            default_resources    = frozenset({"market_data"}),
        )
        assert role.role_type == RoleType.ANALYST
        assert CapabilityType.ANALYSIS in role.default_capabilities

    def test_capability_profile_satisfies(self):
        cp = CapabilityProfile.create(
            name                  = "test",
            required_capabilities = frozenset({CapabilityType.ANALYSIS}),
        )
        assert cp.satisfies(frozenset({CapabilityType.ANALYSIS, CapabilityType.RESEARCH}))
        assert not cp.satisfies(frozenset({CapabilityType.RESEARCH}))

    def test_permission_profile_create(self):
        pp = PermissionProfile.create(
            "analyst",
            {"market_data": PermissionLevel.READ, "portfolio": PermissionLevel.READ},
        )
        assert pp.has_grant("market_data", PermissionLevel.READ)
        assert not pp.has_grant("portfolio", PermissionLevel.WRITE)

    def test_agent_profile_create(self):
        role = AgentRole.create(RoleType.ANALYST, "Analyst")
        cp   = CapabilityProfile.create("cp")
        pp   = PermissionProfile.empty()
        prof = AgentProfile.create("agent-1", role, cp, pp)
        assert prof.agent_id == "agent-1"
        assert prof.role.role_type == RoleType.ANALYST

    def test_role_types_enum(self):
        assert RoleType.ANALYST.value   == "analyst"
        assert RoleType.AUDITOR.value   == "auditor"
        assert RoleType.LEARNER.value   == "learner"


# ===========================================================================
# T15 — Policy Framework
# ===========================================================================

class TestPolicyFramework:
    def test_default_execution_policy_allows_all(self, active_agent):
        task   = AgentTask.create(active_agent.agent_id, "x")
        policy = DefaultExecutionPolicy()
        policy.evaluate(active_agent, task)  # should not raise

    def test_active_only_policy_allows_active(self, active_agent):
        task   = AgentTask.create(active_agent.agent_id, "x")
        policy = ActiveOnlyPolicy()
        policy.evaluate(active_agent, task)  # should not raise

    def test_active_only_policy_blocks_inactive(self, agent):
        task   = AgentTask.create(agent.agent_id, "x")
        policy = ActiveOnlyPolicy()
        with pytest.raises(AIAgentNotRunningError):
            policy.evaluate(agent, task)

    def test_rate_limit_policy_allows_within_limit(self, active_agent):
        policy = RateLimitPolicy(max_per_second=100)
        task   = AgentTask.create(active_agent.agent_id, "x")
        for _ in range(5):
            policy.evaluate(active_agent, task)  # should not raise

    def test_default_permission_policy_allows_all(self, active_agent):
        policy = DefaultPermissionPolicy()
        policy.check(active_agent, "market_data", PermissionLevel.ADMIN)  # should not raise

    def test_strict_permission_policy_checks_perms(self, active_agent):
        policy = StrictPermissionPolicy()
        # active_agent has READ on market_data
        policy.check(active_agent, "market_data", PermissionLevel.READ)   # OK
        with pytest.raises(AIPermissionDeniedError):
            policy.check(active_agent, "market_data", PermissionLevel.ADMIN)

    def test_default_capability_policy_allows_all(self, active_agent):
        task   = AgentTask.create(active_agent.agent_id, "any_task_type")
        policy = DefaultCapabilityPolicy()
        policy.check(active_agent, task)  # should not raise

    def test_strict_capability_policy_blocks_missing(self, active_agent):
        policy = StrictCapabilityPolicy({"summarize": CapabilityType.SUMMARIZATION})
        task   = AgentTask.create(active_agent.agent_id, "summarize")
        # active_agent has ANALYSIS but not SUMMARIZATION
        with pytest.raises(AICapabilityNotPermittedError):
            policy.check(active_agent, task)

    def test_strict_capability_policy_allows_matching(self, active_agent):
        policy = StrictCapabilityPolicy({"analyse": CapabilityType.ANALYSIS})
        task   = AgentTask.create(active_agent.agent_id, "analyse")
        policy.check(active_agent, task)  # active_agent has ANALYSIS


# ===========================================================================
# T16 — Snapshot Framework
# ===========================================================================

class TestSnapshotFramework:
    def test_agent_framework_snapshot_capture(self, registry, event_bus):
        a = _make_agent()
        a.activate()
        registry.register(a)
        snap = AgentFrameworkSnapshot.capture(registry, event_bus)
        assert snap.total_agents  == 1
        assert snap.active_agents == 1
        assert len(snap.agent_snapshots) == 1

    def test_snapshot_agent_fields(self, registry, event_bus):
        a = _make_agent()
        registry.register(a)
        snap = AgentFrameworkSnapshot.capture(registry, event_bus)
        agent_snap = list(snap.agent_snapshots)[0]
        assert agent_snap.agent_name == "Echo"

    def test_snapshot_empty_registry(self, registry, event_bus):
        snap = AgentFrameworkSnapshot.capture(registry, event_bus)
        assert snap.total_agents  == 0
        assert snap.active_agents == 0

    def test_snapshot_events_count(self, registry, event_bus):
        event_bus.publish(AgentStartedEvent.create("a1"))
        event_bus.publish(AgentStartedEvent.create("a2"))
        snap = AgentFrameworkSnapshot.capture(registry, event_bus)
        assert snap.events_published == 2

    def test_snapshot_has_uuid(self, registry, event_bus):
        snap = AgentFrameworkSnapshot.capture(registry, event_bus)
        assert len(snap.snapshot_id) == 36

    def test_snapshot_immutable(self, registry, event_bus):
        snap = AgentFrameworkSnapshot.capture(registry, event_bus)
        with pytest.raises((AttributeError, TypeError)):
            snap.total_agents = 99  # type: ignore[misc]


# ===========================================================================
# T17 — Specialist Agents
# ===========================================================================

class TestSpecialistAgents:
    def test_all_14_specialists_defined(self):
        assert len(ALL_SPECIALIST_CLASSES) == 14

    @pytest.mark.parametrize("cls", ALL_SPECIALIST_CLASSES)
    def test_specialist_has_agent_type(self, cls):
        assert hasattr(cls, "AGENT_TYPE")
        assert cls.AGENT_TYPE

    @pytest.mark.parametrize("cls", ALL_SPECIALIST_CLASSES)
    def test_specialist_create_spec_returns_valid_spec(self, cls):
        spec = cls.create_spec()
        assert isinstance(spec, AgentSpec)
        assert spec.agent_name
        assert spec.capabilities.count() > 0

    @pytest.mark.parametrize("cls", ALL_SPECIALIST_CLASSES)
    def test_specialist_instantiate_with_spec(self, cls):
        spec  = cls.create_spec()
        agent = cls(spec)
        assert agent.agent_id == spec.agent_id

    @pytest.mark.parametrize("cls", ALL_SPECIALIST_CLASSES)
    def test_specialist_execute_task_returns_failure_result(self, cls):
        spec  = cls.create_spec()
        agent = cls(spec)
        agent.activate()
        task    = AgentTask.create(agent.agent_id, "test")
        context = AgentExecutionContext.create(agent.agent_id, task.task_id)
        result  = agent.execute_task(task, context)
        assert isinstance(result, AgentResult)
        # Placeholder always returns failure with "placeholder" in error
        assert result.is_failure()
        assert "placeholder" in (result.error or "").lower()

    def test_market_analyst_has_analysis_capability(self):
        spec = MarketAnalystAgent.create_spec()
        assert spec.capabilities.has_capability(CapabilityType.ANALYSIS)

    def test_risk_analyst_has_portfolio_read_permission(self):
        spec = RiskAnalystAgent.create_spec()
        assert spec.permissions.has_permission("portfolio", PermissionLevel.READ)

    def test_learning_agent_has_knowledge_write_permission(self):
        spec = LearningAgent.create_spec()
        assert spec.permissions.has_permission("knowledge", PermissionLevel.WRITE)

    def test_audit_agent_type(self):
        assert AuditAgent.AGENT_TYPE == "AuditAgent"


# ===========================================================================
# T18 — Gateway
# ===========================================================================

class TestGateway:
    def test_gateway_lifecycle(self):
        gw = AgentFrameworkGateway()
        gw.initialize()
        gw.start()
        assert gw.is_ai_running

    def test_gateway_health_keys(self, gateway):
        h = gateway.health()
        assert "system_id"        in h
        assert "version"          in h
        assert "is_running"       in h
        assert "total_agents"     in h
        assert "active_agents"    in h
        assert "events_published" in h

    def test_gateway_health_is_running_true(self, gateway):
        assert gateway.health()["is_running"] is True

    def test_gateway_system_id(self, gateway):
        assert gateway.health()["system_id"] == "iios:ai:agent_framework:gateway"

    def test_gateway_register_agent(self, gateway):
        spec  = _make_spec()
        agent = EchoAgent(spec)
        desc  = gateway.register_agent(agent)
        assert isinstance(desc, AgentDescriptor)

    def test_gateway_create_and_register(self, gateway):
        gateway._container.factory.register_builder("EchoAgent", EchoAgent)
        spec  = _make_spec()
        agent = gateway.create_and_register(spec)
        assert isinstance(agent, EchoAgent)

    def test_gateway_start_stop_agent(self, gateway):
        spec  = _make_spec()
        agent = EchoAgent(spec)
        gateway.register_agent(agent)
        gateway.start_agent(agent.agent_id)
        assert agent.is_active
        gateway.stop_agent(agent.agent_id)
        assert agent.is_shutdown

    def test_gateway_assign_task(self, gateway):
        spec  = _make_spec()
        agent = EchoAgent(spec)
        gateway.register_agent(agent)
        gateway.start_agent(agent.agent_id)
        task   = AgentTask.create(agent.agent_id, "analyse", {"x": 1})
        result = gateway.assign_task(task)
        assert result.is_success()

    def test_gateway_list_agents(self, gateway):
        spec  = _make_spec()
        agent = EchoAgent(spec)
        gateway.register_agent(agent)
        agents = gateway.list_agents()
        assert len(agents) >= 1

    def test_gateway_find_agents_by_capability(self, gateway):
        spec  = _make_spec()
        agent = EchoAgent(spec)
        gateway.register_agent(agent)
        found = gateway.find_agents_by_capability(CapabilityType.ANALYSIS)
        assert len(found) >= 1

    def test_gateway_get_agent_health(self, gateway):
        spec  = _make_spec()
        agent = EchoAgent(spec)
        gateway.register_agent(agent)
        h = gateway.get_agent_health(agent.agent_id)
        assert isinstance(h, AgentHealth)

    def test_gateway_get_agent_metrics(self, gateway):
        spec  = _make_spec()
        agent = EchoAgent(spec)
        gateway.register_agent(agent)
        m = gateway.get_agent_metrics(agent.agent_id)
        assert isinstance(m, AgentMetrics)

    def test_gateway_snapshot(self, gateway):
        snap = gateway.snapshot()
        assert isinstance(snap, AgentFrameworkSnapshot)

    def test_gateway_status_has_uptime(self, gateway):
        s = gateway.status()
        assert "uptime_s" in s
        assert s["uptime_s"] >= 0

    def test_gateway_suspend_resume(self, gateway):
        spec  = _make_spec()
        agent = EchoAgent(spec)
        gateway.register_agent(agent)
        gateway.start_agent(agent.agent_id)
        gateway.suspend_agent(agent.agent_id)
        assert not agent.is_active
        gateway.resume_agent(agent.agent_id)
        assert agent.is_active

    def test_gateway_event_counts_after_tasks(self, gateway):
        spec  = _make_spec()
        agent = EchoAgent(spec)
        gateway.register_agent(agent)
        gateway.start_agent(agent.agent_id)
        task = AgentTask.create(agent.agent_id, "analyse")
        gateway.assign_task(task)
        health = gateway.health()
        assert health["events_published"] > 0
