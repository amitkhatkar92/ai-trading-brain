"""
test_model_management.py -- A2 Model Management test suite

Covers:
  - Model registration, deregistration, enable/disable, lookup, search
  - Version management (add, activate, rollback, audit history)
  - Capability discovery (static catalogue, per-model queries)
  - Routing decisions (strategy, no-model error, exclusion, tier preference)
  - Policy evaluation (selection, failover, cost, latency, capability, validation)
  - Health monitoring (success/failure recording, threshold, recovery, status override)
  - Event publishing (all 10 event types, multi-subscriber, unsubscribe)
  - Gateway API completeness
  - Exception hierarchy
  - Container DI wiring
  - Thread safety

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import threading
import unittest
from typing import List

from iios.ai.foundation.exceptions import AIException

from iios.ai.model_management.capabilities import ModelCapabilities, ModelCapabilityType
from iios.ai.model_management.configuration import ConfigurationLoader, ModelConfiguration, RuntimeSettings
from iios.ai.model_management.container import ModelManagementContainer
from iios.ai.model_management.core import (
    AIModel,
    AIModelDescriptor,
    AIModelVersion,
    ModelCategory,
    ModelMetadata,
    ModelTier,
)
from iios.ai.model_management.events import (
    FailoverTriggeredEvent,
    HealthCheckFailedEvent,
    HealthCheckPassedEvent,
    ModelDisabledEvent,
    ModelEnabledEvent,
    ModelEventBus,
    ModelEventType,
    ModelHealthChangedEvent,
    ModelRegisteredEvent,
    ModelRemovedEvent,
    RoutingCompletedEvent,
    VersionActivatedEvent,
)
from iios.ai.model_management.exceptions import (
    AIFailoverExhaustedError,
    AIHealthException,
    AIModelAlreadyExistsError,
    AIModelConfigurationError,
    AIModelDisabledError,
    AIModelException,
    AIModelNotFoundError,
    AIModelPolicyViolationError,
    AIModelUnhealthyError,
    AIModelVersionError,
    AINoModelAvailableError,
    AIRoutingException,
)
from iios.ai.model_management.gateway import ModelManagementGateway
from iios.ai.model_management.health import AvailabilityStatus, HealthMonitor, HealthReport, ModelHealth
from iios.ai.model_management.policy import (
    AllowAllCostPolicy,
    CapabilityBasedSelectionPolicy,
    FixedPreferredModelPolicy,
    NoFailoverPolicy,
    NoPreferencePolicy,
    PermissiveCapabilityPolicy,
    PermissiveLatencyPolicy,
    PermissiveModelValidationPolicy,
    SimpleFailoverPolicy,
    StrictCapabilityPolicy,
    StrictModelValidationPolicy,
    TierBudgetCostPolicy,
)
from iios.ai.model_management.registry import AIModelRegistry
from iios.ai.model_management.router import (
    CapabilityFirstStrategy,
    ModelRouter,
    RoundRobinStrategy,
    RoutingContext,
    RoutingDecision,
    TierPreferenceStrategy,
)
from iios.ai.model_management.snapshot import ModelManagementSnapshot

# Capability shortcuts
CHAT       = ModelCapabilityType.CHAT
EMBED      = ModelCapabilityType.EMBEDDINGS
VISION     = ModelCapabilityType.VISION
STREAMING  = ModelCapabilityType.STREAMING
TOOL       = ModelCapabilityType.TOOL_CALLING


def _register_chat_model(registry: AIModelRegistry, name: str = "chat-model") -> AIModel:
    return registry.register(
        name, ModelCategory.LANGUAGE_MODEL, frozenset({CHAT, STREAMING}),
        tier=ModelTier.STANDARD,
    )


# ---------------------------------------------------------------------------
# Model Registration
# ---------------------------------------------------------------------------

class TestModelRegistration(unittest.TestCase):

    def setUp(self):
        self.registry = AIModelRegistry()

    def test_register_creates_model_with_active_version(self):
        m = _register_chat_model(self.registry)
        self.assertIsNotNone(m.active_version)
        self.assertTrue(m.enabled)
        self.assertIn(CHAT, m.active_version.descriptor.capabilities)

    def test_register_duplicate_name_raises(self):
        _register_chat_model(self.registry)
        with self.assertRaises(AIModelAlreadyExistsError):
            _register_chat_model(self.registry)

    def test_deregister_removes_model(self):
        m = _register_chat_model(self.registry)
        self.registry.deregister(m.model_id)
        with self.assertRaises(AIModelNotFoundError):
            self.registry.get(m.model_id)

    def test_deregister_unknown_raises(self):
        with self.assertRaises(AIModelNotFoundError):
            self.registry.deregister("bogus-id")

    def test_enable_disable(self):
        m = _register_chat_model(self.registry)
        self.registry.disable(m.model_id)
        self.assertFalse(self.registry.get(m.model_id).enabled)
        self.registry.enable(m.model_id)
        self.assertTrue(self.registry.get(m.model_id).enabled)

    def test_get_unknown_raises(self):
        with self.assertRaises(AIModelNotFoundError):
            self.registry.get("unknown-id")


# ---------------------------------------------------------------------------
# Model Lookup
# ---------------------------------------------------------------------------

class TestModelLookup(unittest.TestCase):

    def setUp(self):
        self.registry = AIModelRegistry()
        self.m1 = self.registry.register(
            "chat-a", ModelCategory.LANGUAGE_MODEL, frozenset({CHAT, STREAMING}),
            tier=ModelTier.STANDARD, tags=("prod",),
        )
        self.m2 = self.registry.register(
            "embed-b", ModelCategory.EMBEDDING, frozenset({EMBED}),
            tier=ModelTier.BUDGET, tags=("prod",),
        )

    def test_find_by_name_found(self):
        found = self.registry.find_by_name("chat-a")
        self.assertEqual(found.model_id, self.m1.model_id)

    def test_find_by_name_not_found(self):
        self.assertIsNone(self.registry.find_by_name("does-not-exist"))

    def test_search_by_category(self):
        results = self.registry.search(category=ModelCategory.EMBEDDING)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].model_id, self.m2.model_id)

    def test_search_by_capability(self):
        results = self.registry.search(capability=EMBED)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].model_id, self.m2.model_id)

    def test_search_by_tier(self):
        results = self.registry.search(tier=ModelTier.BUDGET)
        self.assertEqual(len(results), 1)

    def test_search_enabled_only(self):
        self.registry.disable(self.m2.model_id)
        results = self.registry.search(enabled_only=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].model_id, self.m1.model_id)

    def test_list_all(self):
        self.assertEqual(len(self.registry.list_all()), 2)
        self.assertEqual(len(self.registry), 2)


# ---------------------------------------------------------------------------
# Version Management
# ---------------------------------------------------------------------------

class TestVersionManagement(unittest.TestCase):

    def setUp(self):
        self.registry = AIModelRegistry()
        self.model    = _register_chat_model(self.registry)

    def test_initial_version_is_active(self):
        v = self.model.active_version
        self.assertEqual(v.version_number, 1)
        self.assertTrue(v.active)

    def test_add_version_activates_by_default(self):
        v2 = self.registry.add_version(self.model.model_id, frozenset({CHAT, VISION}))
        self.assertEqual(v2.version_number, 2)
        self.assertTrue(v2.active)
        self.assertEqual(self.model.active_version.version_id, v2.version_id)

    def test_add_version_without_activation(self):
        v2 = self.registry.add_version(self.model.model_id, frozenset({CHAT}), activate=False)
        self.assertFalse(v2.active)
        self.assertEqual(self.model.active_version.version_number, 1)

    def test_rollback_to_prior_version(self):
        v1 = self.model.active_version
        self.registry.add_version(self.model.model_id, frozenset({CHAT, TOOL}))
        rolled = self.registry.rollback(self.model.model_id, v1.version_id)
        self.assertEqual(rolled.version_id, v1.version_id)
        self.assertEqual(self.model.active_version.version_id, v1.version_id)

    def test_rollback_unknown_version_raises(self):
        with self.assertRaises(AIModelVersionError):
            self.registry.rollback(self.model.model_id, "bogus-version-id")

    def test_version_history_ordered(self):
        self.registry.add_version(self.model.model_id, frozenset({CHAT}))
        self.registry.add_version(self.model.model_id, frozenset({CHAT, STREAMING}))
        history = self.model.history()
        self.assertEqual([v.version_number for v in history], [1, 2, 3])

    def test_activate_version_explicit(self):
        v1_id = self.model.active_version.version_id
        v2    = self.registry.add_version(self.model.model_id, frozenset({EMBED}))
        self.registry.activate_version(self.model.model_id, v1_id)
        self.assertEqual(self.model.active_version.version_id, v1_id)


# ---------------------------------------------------------------------------
# Capability Discovery
# ---------------------------------------------------------------------------

class TestCapabilityDiscovery(unittest.TestCase):

    def test_list_capabilities_returns_all_types(self):
        gw = ModelManagementGateway()
        gw.initialize()
        gw.start()
        caps = gw.list_capabilities()
        self.assertIn(CHAT, caps)
        self.assertIn(EMBED, caps)
        self.assertIn(VISION, caps)
        self.assertIn(ModelCapabilityType.AUDIO, caps)
        self.assertIn(ModelCapabilityType.STRUCTURED_OUTPUT, caps)
        self.assertEqual(len(caps), 10)
        gw.stop()

    def test_model_capabilities_supports(self):
        mc = ModelCapabilities(frozenset({CHAT, STREAMING}))
        self.assertTrue(mc.supports(CHAT))
        self.assertFalse(mc.supports(VISION))

    def test_model_capabilities_supports_all(self):
        mc = ModelCapabilities(frozenset({CHAT, STREAMING, TOOL}))
        self.assertTrue(mc.supports_all(frozenset({CHAT, STREAMING})))
        self.assertFalse(mc.supports_all(frozenset({CHAT, VISION})))

    def test_model_capabilities_supports_any(self):
        mc = ModelCapabilities(frozenset({CHAT}))
        self.assertTrue(mc.supports_any(frozenset({CHAT, VISION})))
        self.assertFalse(mc.supports_any(frozenset({VISION, EMBED})))

    def test_model_capabilities_list_all(self):
        mc = ModelCapabilities(frozenset({CHAT, EMBED}))
        self.assertEqual(len(mc.list_all()), 2)

    def test_model_capabilities_len_and_contains(self):
        mc = ModelCapabilities(frozenset({CHAT, STREAMING}))
        self.assertEqual(len(mc), 2)
        self.assertIn(CHAT, mc)
        self.assertNotIn(VISION, mc)


# ---------------------------------------------------------------------------
# Routing Decisions
# ---------------------------------------------------------------------------

class TestRoutingDecisions(unittest.TestCase):

    def setUp(self):
        self.registry = AIModelRegistry()
        self.health   = HealthMonitor()
        self.m1 = self.registry.register(
            "chat-m1", ModelCategory.LANGUAGE_MODEL, frozenset({CHAT, STREAMING}),
            tier=ModelTier.STANDARD,
        )
        self.m2 = self.registry.register(
            "embed-m2", ModelCategory.EMBEDDING, frozenset({EMBED}),
            tier=ModelTier.BUDGET,
        )

    def _router(self, strategy=None):
        return ModelRouter(self.registry, self.health, strategy=strategy)

    def test_route_by_capability(self):
        router = self._router(CapabilityFirstStrategy())
        ctx    = RoutingContext.for_capability(CHAT)
        dec    = router.route(ctx)
        self.assertEqual(dec.model_id, self.m1.model_id)

    def test_route_no_capability_restriction(self):
        router = self._router()
        ctx    = RoutingContext()
        dec    = router.route(ctx)
        self.assertIn(dec.model_id, {self.m1.model_id, self.m2.model_id})

    def test_route_unsatisfiable_raises(self):
        router = self._router()
        ctx    = RoutingContext.for_capability(VISION)
        with self.assertRaises(AINoModelAvailableError):
            router.route(ctx)

    def test_route_excluded_model(self):
        router = self._router()
        ctx    = RoutingContext(exclude_model_ids=frozenset({self.m1.model_id}))
        dec    = router.route(ctx)
        self.assertEqual(dec.model_id, self.m2.model_id)

    def test_route_disabled_model_excluded(self):
        self.registry.disable(self.m1.model_id)
        router = self._router(CapabilityFirstStrategy())
        ctx    = RoutingContext.for_capability(CHAT)
        with self.assertRaises(AINoModelAvailableError):
            router.route(ctx)

    def test_tier_preference_strategy(self):
        self.registry.register(
            "budget-m3", ModelCategory.LANGUAGE_MODEL, frozenset({CHAT}),
            tier=ModelTier.BUDGET,
        )
        router = self._router(TierPreferenceStrategy())
        ctx    = RoutingContext(required_capabilities=frozenset({CHAT}), preferred_tier=ModelTier.BUDGET)
        dec    = router.route(ctx)
        # budget model should be preferred
        self.assertNotEqual(dec.model_id, self.m1.model_id)

    def test_round_robin_cycles(self):
        # Register a second CHAT model
        m3 = self.registry.register(
            "chat-m3", ModelCategory.LANGUAGE_MODEL, frozenset({CHAT}),
            tier=ModelTier.STANDARD,
        )
        router  = self._router(RoundRobinStrategy())
        ctx     = RoutingContext.for_capability(CHAT)
        results = {router.route(ctx).model_id for _ in range(4)}
        self.assertGreaterEqual(len(results), 2)   # both models should be selected

    def test_routing_decision_immutable(self):
        router = self._router()
        dec    = router.route(RoutingContext())
        with self.assertRaises((AttributeError, TypeError)):
            dec.model_id = "hacked"   # type: ignore[misc]

    def test_route_unhealthy_model_skipped(self):
        # Mark m1 as unavailable by recording many failures
        for _ in range(5):
            self.health.record_failure(self.m1.model_id)
        router = self._router(CapabilityFirstStrategy())
        ctx    = RoutingContext.for_capability(CHAT)
        with self.assertRaises(AINoModelAvailableError):
            router.route(ctx)

    def test_routing_strategy_name_accessible(self):
        self.assertEqual(CapabilityFirstStrategy.STRATEGY_NAME, "capability_first")
        self.assertEqual(TierPreferenceStrategy.STRATEGY_NAME, "tier_preference")
        self.assertEqual(RoundRobinStrategy.STRATEGY_NAME, "round_robin")


# ---------------------------------------------------------------------------
# Policy Evaluation
# ---------------------------------------------------------------------------

class TestPolicyEvaluation(unittest.TestCase):

    def _make_model(self, name="p-model", tier=ModelTier.STANDARD, caps=None):
        registry = AIModelRegistry()
        return registry.register(name, ModelCategory.LANGUAGE_MODEL, frozenset(caps or {CHAT}), tier=tier)

    def test_capability_based_selection_policy(self):
        m1 = self._make_model()
        m2 = self._make_model("p-embed", caps={EMBED})
        health = HealthMonitor()
        policy = CapabilityBasedSelectionPolicy()
        ctx    = RoutingContext.for_capability(CHAT)
        result = policy.select([m1, m2], ctx, health)
        self.assertEqual(result.model_id, m1.model_id)

    def test_capability_based_selection_no_match(self):
        m1 = self._make_model()
        health = HealthMonitor()
        policy = CapabilityBasedSelectionPolicy()
        ctx    = RoutingContext.for_capability(VISION)
        result = policy.select([m1], ctx, health)
        self.assertIsNone(result)

    def test_simple_failover_policy(self):
        m1 = self._make_model("m1")
        m2 = self._make_model("m2")
        policy = SimpleFailoverPolicy()
        result = policy.select_failover(m1.model_id, [m1, m2])
        self.assertEqual(result.model_id, m2.model_id)

    def test_no_failover_policy(self):
        m1 = self._make_model("m1")
        m2 = self._make_model("m2")
        policy = NoFailoverPolicy()
        result = policy.select_failover(m1.model_id, [m1, m2])
        self.assertIsNone(result)

    def test_allow_all_cost_policy(self):
        m = self._make_model(tier=ModelTier.ENTERPRISE)
        policy = AllowAllCostPolicy()
        self.assertTrue(policy.is_within_budget(m))

    def test_tier_budget_cost_policy(self):
        m_budget   = self._make_model("b", tier=ModelTier.BUDGET)
        m_premium  = self._make_model("p", tier=ModelTier.PREMIUM)
        policy = TierBudgetCostPolicy(ModelTier.STANDARD)
        self.assertTrue(policy.is_within_budget(m_budget))
        self.assertFalse(policy.is_within_budget(m_premium))

    def test_permissive_latency_policy(self):
        m      = self._make_model()
        ctx    = RoutingContext()
        policy = PermissiveLatencyPolicy()
        self.assertTrue(policy.is_within_latency(m, ctx))

    def test_no_preference_policy(self):
        policy = NoPreferencePolicy()
        self.assertIsNone(policy.preferred_model_id())

    def test_fixed_preferred_model_policy(self):
        policy = FixedPreferredModelPolicy("some-model-id")
        self.assertEqual(policy.preferred_model_id(), "some-model-id")

    def test_strict_capability_policy(self):
        m = self._make_model(caps={CHAT, STREAMING})
        strict = StrictCapabilityPolicy()
        self.assertTrue(strict.satisfies(m, frozenset({CHAT})))
        self.assertFalse(strict.satisfies(m, frozenset({VISION})))

    def test_permissive_capability_policy(self):
        m = self._make_model(caps={CHAT})
        perm = PermissiveCapabilityPolicy()
        self.assertTrue(perm.satisfies(m, frozenset({CHAT, VISION})))  # any overlap
        self.assertFalse(perm.satisfies(m, frozenset({VISION, EMBED})))

    def test_strict_model_validation_policy_raises(self):
        policy = StrictModelValidationPolicy()
        with self.assertRaises(AIModelPolicyViolationError):
            policy.enforce(False, "reason")

    def test_permissive_model_validation_policy_never_raises(self):
        policy = PermissiveModelValidationPolicy()
        policy.enforce(False, "ignored")  # must not raise


# ---------------------------------------------------------------------------
# Health Monitoring
# ---------------------------------------------------------------------------

class TestHealthMonitoring(unittest.TestCase):

    def test_initial_status_unknown(self):
        monitor = HealthMonitor()
        report  = monitor.get_report("new-model")
        self.assertEqual(report.status, AvailabilityStatus.UNKNOWN)

    def test_record_success_sets_available(self):
        monitor = HealthMonitor()
        monitor.record_success("m1")
        self.assertEqual(monitor.get_report("m1").status, AvailabilityStatus.AVAILABLE)
        self.assertTrue(monitor.is_healthy("m1"))

    def test_single_failure_sets_degraded(self):
        monitor = HealthMonitor()
        monitor.record_success("m1")
        monitor.record_failure("m1")
        self.assertEqual(monitor.get_report("m1").status, AvailabilityStatus.DEGRADED)
        self.assertTrue(monitor.is_healthy("m1"))

    def test_three_consecutive_failures_set_unavailable(self):
        monitor = HealthMonitor()
        for _ in range(3):
            monitor.record_failure("m1")
        self.assertEqual(monitor.get_report("m1").status, AvailabilityStatus.UNAVAILABLE)
        self.assertFalse(monitor.is_healthy("m1"))

    def test_recovery_after_unavailable(self):
        monitor = HealthMonitor()
        for _ in range(3):
            monitor.record_failure("m1")
        monitor.record_success("m1")
        self.assertEqual(monitor.get_report("m1").status, AvailabilityStatus.AVAILABLE)

    def test_failure_count_increments(self):
        monitor = HealthMonitor()
        monitor.record_failure("m1")
        monitor.record_failure("m1")
        self.assertEqual(monitor.get_report("m1").failure_count, 2)

    def test_set_available_override(self):
        monitor = HealthMonitor()
        for _ in range(5):
            monitor.record_failure("m1")
        monitor.set_available("m1")
        self.assertTrue(monitor.is_healthy("m1"))

    def test_set_unavailable_override(self):
        monitor = HealthMonitor()
        monitor.record_success("m1")
        monitor.set_unavailable("m1")
        self.assertFalse(monitor.is_healthy("m1"))

    def test_health_report_is_healthy_property(self):
        r = HealthReport("m1", AvailabilityStatus.AVAILABLE, 0, 0, None, None)
        self.assertTrue(r.is_healthy)
        r2 = HealthReport("m1", AvailabilityStatus.UNAVAILABLE, 3, 0, None, None)
        self.assertFalse(r2.is_healthy)

    def test_unknown_is_healthy_optimistic(self):
        monitor = HealthMonitor()
        self.assertTrue(monitor.is_healthy("never-seen"))


# ---------------------------------------------------------------------------
# Event Publishing
# ---------------------------------------------------------------------------

class TestEventPublishing(unittest.TestCase):

    def setUp(self):
        self.bus = ModelEventBus()

    def test_model_registered_event(self):
        received: List = []
        self.bus.subscribe(ModelEventType.MODEL_REGISTERED, received.append)
        registry = AIModelRegistry(event_bus=self.bus)
        _register_chat_model(registry)
        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], ModelRegisteredEvent)

    def test_model_removed_event(self):
        received: List = []
        self.bus.subscribe(ModelEventType.MODEL_REMOVED, received.append)
        registry = AIModelRegistry(event_bus=self.bus)
        m        = _register_chat_model(registry)
        registry.deregister(m.model_id)
        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], ModelRemovedEvent)

    def test_model_enabled_disabled_events(self):
        en_events, dis_events = [], []
        self.bus.subscribe(ModelEventType.MODEL_ENABLED, en_events.append)
        self.bus.subscribe(ModelEventType.MODEL_DISABLED, dis_events.append)
        registry = AIModelRegistry(event_bus=self.bus)
        m        = _register_chat_model(registry)
        registry.disable(m.model_id)
        registry.enable(m.model_id)
        self.assertEqual(len(dis_events), 1)
        self.assertEqual(len(en_events), 1)

    def test_version_activated_event(self):
        received: List = []
        self.bus.subscribe(ModelEventType.VERSION_ACTIVATED, received.append)
        registry = AIModelRegistry(event_bus=self.bus)
        m        = _register_chat_model(registry)
        registry.add_version(m.model_id, frozenset({CHAT}))
        self.assertGreaterEqual(len(received), 1)
        self.assertIsInstance(received[-1], VersionActivatedEvent)

    def test_routing_completed_event(self):
        received: List = []
        self.bus.subscribe(ModelEventType.ROUTING_COMPLETED, received.append)
        registry = AIModelRegistry(event_bus=self.bus)
        health   = HealthMonitor(event_bus=self.bus)
        _register_chat_model(registry)
        router = ModelRouter(registry, health, event_bus=self.bus)
        router.route(RoutingContext.for_capability(CHAT))
        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], RoutingCompletedEvent)

    def test_health_check_events(self):
        pass_events, fail_events = [], []
        self.bus.subscribe(ModelEventType.HEALTH_CHECK_PASSED, pass_events.append)
        self.bus.subscribe(ModelEventType.HEALTH_CHECK_FAILED, fail_events.append)
        monitor = HealthMonitor(event_bus=self.bus)
        monitor.record_success("m1")
        monitor.record_failure("m1")
        self.assertEqual(len(pass_events), 1)
        self.assertEqual(len(fail_events), 1)

    def test_health_changed_event_on_threshold(self):
        received: List = []
        self.bus.subscribe(ModelEventType.MODEL_HEALTH_CHANGED, received.append)
        monitor = HealthMonitor(event_bus=self.bus)
        for _ in range(3):
            monitor.record_failure("m1")
        self.assertGreaterEqual(len(received), 1)
        self.assertIsInstance(received[-1], ModelHealthChangedEvent)

    def test_multiple_subscribers_all_receive(self):
        a, b = [], []
        self.bus.subscribe(ModelEventType.MODEL_REGISTERED, a.append)
        self.bus.subscribe(ModelEventType.MODEL_REGISTERED, b.append)
        registry = AIModelRegistry(event_bus=self.bus)
        _register_chat_model(registry)
        self.assertEqual(len(a), 1)
        self.assertEqual(len(b), 1)

    def test_unsubscribe_stops_delivery(self):
        received: List = []
        sub_id = self.bus.subscribe(ModelEventType.MODEL_REGISTERED, received.append)
        self.bus.unsubscribe(sub_id)
        registry = AIModelRegistry(event_bus=self.bus)
        _register_chat_model(registry)
        self.assertEqual(len(received), 0)

    def test_published_count_increments(self):
        registry = AIModelRegistry(event_bus=self.bus)
        _register_chat_model(registry)
        self.assertGreater(self.bus.published_count, 0)


# ---------------------------------------------------------------------------
# Gateway API Completeness
# ---------------------------------------------------------------------------

class TestGatewayAPICompleteness(unittest.TestCase):

    def setUp(self):
        self.gw = ModelManagementGateway()
        self.gw.initialize()
        self.gw.start()

    def tearDown(self):
        if self.gw.lifecycle_state.value == "running":
            self.gw.stop()

    def test_register_get_list(self):
        m = self.gw.register_model("gw-chat", ModelCategory.LANGUAGE_MODEL, frozenset({CHAT}))
        got = self.gw.get_model(m.model_id)
        self.assertEqual(got.model_id, m.model_id)
        all_models = self.gw.list_models()
        self.assertEqual(len(all_models), 1)

    def test_find_model_by_name(self):
        m = self.gw.register_model("gw-find", ModelCategory.CUSTOM, frozenset({CHAT}))
        found = self.gw.find_model("gw-find")
        self.assertEqual(found.model_id, m.model_id)

    def test_enable_disable_remove(self):
        m = self.gw.register_model("gw-toggle", ModelCategory.CUSTOM, frozenset({CHAT}))
        self.gw.disable_model(m.model_id)
        self.assertFalse(self.gw.get_model(m.model_id).enabled)
        self.gw.enable_model(m.model_id)
        self.assertTrue(self.gw.get_model(m.model_id).enabled)
        self.gw.remove_model(m.model_id)
        with self.assertRaises(AIModelNotFoundError):
            self.gw.get_model(m.model_id)

    def test_versioning_via_gateway(self):
        m  = self.gw.register_model("gw-version", ModelCategory.CUSTOM, frozenset({CHAT}))
        v2 = self.gw.add_version(m.model_id, frozenset({CHAT, STREAMING}))
        self.assertEqual(self.gw.get_model(m.model_id).active_version.version_id, v2.version_id)
        self.assertEqual(len(self.gw.version_history(m.model_id)), 2)

    def test_route_request_via_gateway(self):
        self.gw.register_model("gw-route", ModelCategory.LANGUAGE_MODEL, frozenset({CHAT}))
        ctx = RoutingContext.for_capability(CHAT)
        dec = self.gw.route_request(ctx)
        self.assertIsNotNone(dec.model_id)

    def test_list_capabilities_returns_all(self):
        caps = self.gw.list_capabilities()
        self.assertEqual(len(caps), 10)

    def test_health_and_status(self):
        h = self.gw.health()
        self.assertIn("module_id", h)
        self.assertTrue(h["is_running"])
        s = self.gw.status()
        self.assertIn("events_published", s)

    def test_snapshot(self):
        self.gw.register_model("gw-snap", ModelCategory.CUSTOM, frozenset({CHAT}))
        snap = self.gw.snapshot()
        self.assertEqual(snap.model_count, 1)

    def test_health_recording(self):
        m = self.gw.register_model("gw-health", ModelCategory.CUSTOM, frozenset({CHAT}))
        self.gw.record_success(m.model_id)
        self.gw.record_failure(m.model_id)
        report = self.gw.get_health(m.model_id)
        self.assertEqual(report.failure_count, 1)

    def test_lifecycle_stop(self):
        self.gw.stop()
        self.assertFalse(self.gw.health()["is_running"])


# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy(unittest.TestCase):

    def test_all_inherit_ai_exception(self):
        for exc_cls, args in [
            (AIModelNotFoundError, ("mid",)),
            (AIModelAlreadyExistsError, ("name",)),
            (AIModelVersionError, ("msg",)),
            (AIModelDisabledError, ("mid",)),
            (AINoModelAvailableError, ()),
            (AIModelUnhealthyError, ("mid",)),
            (AIModelPolicyViolationError, ("reason",)),
        ]:
            with self.subTest(exc_cls=exc_cls):
                exc = exc_cls(*args)
                self.assertIsInstance(exc, AIModelException)
                self.assertIsInstance(exc, AIException)

    def test_error_codes_are_unique(self):
        codes = {
            AIModelNotFoundError("x").error_code,
            AIModelAlreadyExistsError("x").error_code,
            AIModelVersionError("x").error_code,
            AIModelDisabledError("x").error_code,
            AINoModelAvailableError().error_code,
            AIModelUnhealthyError("x").error_code,
            AIModelPolicyViolationError("x").error_code,
        }
        self.assertEqual(len(codes), 7)

    def test_routing_exception_is_model_exception(self):
        exc = AINoModelAvailableError("no model")
        self.assertIsInstance(exc, AIRoutingException)
        self.assertIsInstance(exc, AIModelException)

    def test_health_exception_is_model_exception(self):
        exc = AIModelUnhealthyError("mid")
        self.assertIsInstance(exc, AIHealthException)
        self.assertIsInstance(exc, AIModelException)


# ---------------------------------------------------------------------------
# Container DI Wiring
# ---------------------------------------------------------------------------

class TestContainerDIWiring(unittest.TestCase):

    def test_build_wires_all_components(self):
        c = ModelManagementContainer()
        c.build()
        self.assertTrue(c.is_built)
        self.assertIsNotNone(c.registry)
        self.assertIsNotNone(c.router)
        self.assertIsNotNone(c.health_monitor)
        self.assertIsNotNone(c.event_bus)
        self.assertIsNotNone(c.configuration_loader)

    def test_two_containers_are_independent(self):
        c1 = ModelManagementContainer()
        c2 = ModelManagementContainer()
        c1.registry.register("only-in-c1", ModelCategory.CUSTOM, frozenset({CHAT}))
        self.assertEqual(len(c1.registry), 1)
        self.assertEqual(len(c2.registry), 0)

    def test_injected_container_used_by_gateway(self):
        c  = ModelManagementContainer()
        gw = ModelManagementGateway(container=c)
        gw.initialize()
        gw.start()
        gw.register_model("injected", ModelCategory.CUSTOM, frozenset({CHAT}))
        self.assertEqual(len(c.registry), 1)
        gw.stop()

    def test_custom_routing_strategy_injectable(self):
        c = ModelManagementContainer(routing_strategy=RoundRobinStrategy())
        self.assertIsInstance(c.router.strategy, RoundRobinStrategy)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class TestConfiguration(unittest.TestCase):

    def test_default_configuration(self):
        loader = ConfigurationLoader()
        config = loader.load_for_model("any-model-id")
        self.assertEqual(config.model_id, "any-model-id")
        self.assertGreater(config.timeout_ms, 0)

    def test_override_applied(self):
        loader = ConfigurationLoader()
        override = ModelConfiguration("m1", timeout_ms=5_000)
        loader.with_override(override)
        config = loader.load_for_model("m1")
        self.assertEqual(config.timeout_ms, 5_000)

    def test_runtime_settings_defaults(self):
        settings = RuntimeSettings()
        self.assertEqual(settings.default_tier, ModelTier.STANDARD)
        self.assertTrue(settings.enable_failover)

    def test_with_timeout_creates_copy(self):
        config  = ModelConfiguration("m1", timeout_ms=1_000)
        updated = config.with_timeout(500)
        self.assertEqual(updated.timeout_ms, 500)
        self.assertEqual(config.timeout_ms, 1_000)   # original unchanged


# ---------------------------------------------------------------------------
# Thread Safety
# ---------------------------------------------------------------------------

class TestThreadSafety(unittest.TestCase):

    def test_concurrent_registration(self):
        registry = AIModelRegistry()
        errors: List = []

        def _register(i):
            try:
                registry.register(
                    f"concurrent-{i}", ModelCategory.CUSTOM, frozenset({CHAT})
                )
            except Exception as exc:   # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=_register, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(registry), 20)

    def test_concurrent_health_recording(self):
        monitor = HealthMonitor()
        errors: List = []

        def _record(i):
            try:
                if i % 2 == 0:
                    monitor.record_success("shared-model")
                else:
                    monitor.record_failure("shared-model")
            except Exception as exc:   # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=_record, args=(i,)) for i in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
