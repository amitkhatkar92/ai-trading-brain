"""
test_prompt_context.py -- A3 Prompt & Context Platform test suite

Covers:
  - Prompt registration, deregistration, enable/disable, lookup, search
  - Version management (create, activate, rollback, audit history)
  - Context building (segments, priority ordering, budget truncation, merge)
  - Variable substitution (renderer, missing-variable errors)
  - Prompt composition (with/without context)
  - Validation framework (prompt, context, variable validators)
  - Policy framework (selection, priority, version, validation, token budget)
  - Event publishing (all event types, multi-subscriber)
  - Gateway public API completeness
  - Exception hierarchy

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import threading
import unittest
from typing import List

from iios.ai.foundation.exceptions import AIException

from iios.ai.prompt_context.composer import PromptComposer, PromptRenderer
from iios.ai.prompt_context.container import PromptContextContainer
from iios.ai.prompt_context.context import AssembledContext, ContextAssembler, ContextBuilder
from iios.ai.prompt_context.core import (
    ContextMetadata,
    ContextPriority,
    ContextSegment,
    PromptCategory,
    PromptMetadata,
    PromptTemplate,
    PromptVariables,
    PromptVersion,
    estimate_tokens,
)
from iios.ai.prompt_context.events import (
    ContextBuiltEvent,
    PromptEventBus,
    PromptEventType,
    PromptRegisteredEvent,
    PromptRenderedEvent,
    ValidationFailedEvent,
    ValidationSucceededEvent,
)
from iios.ai.prompt_context.exceptions import (
    AIContextIncompleteError,
    AIMissingVariableError,
    AIPromptAlreadyExistsError,
    AIPromptDisabledError,
    AIPromptException,
    AIPromptNotFoundError,
    AIPromptPolicyViolationError,
    AIPromptVersionError,
)
from iios.ai.prompt_context.gateway import PromptContextGateway
from iios.ai.prompt_context.policy import (
    ActiveVersionPolicy,
    DefaultContextPriorityPolicy,
    DefaultPromptSelectionPolicy,
    FixedTokenBudgetPolicy,
    PerModuleTokenBudgetPolicy,
    PermissiveValidationPolicy,
    StrictValidationPolicy,
)
from iios.ai.prompt_context.registry import PromptRegistry
from iios.ai.prompt_context.validation import ContextValidator, PromptValidator, VariableValidator
from iios.ai.prompt_context.versioning import PromptHistory, VersionManager


# ---------------------------------------------------------------------------
# Prompt Registration
# ---------------------------------------------------------------------------

class TestPromptRegistration(unittest.TestCase):

    def setUp(self):
        self.registry = PromptRegistry()

    def test_register_creates_template_with_active_version(self):
        t = self.registry.register("greeting", PromptCategory.SYSTEM, "Hello {{name}}!", variables=("name",))
        self.assertIsNotNone(t.active_version)
        self.assertEqual(t.active_version.template_text, "Hello {{name}}!")
        self.assertTrue(t.enabled)

    def test_register_duplicate_name_raises(self):
        self.registry.register("dup", PromptCategory.CUSTOM, "text")
        with self.assertRaises(AIPromptAlreadyExistsError):
            self.registry.register("dup", PromptCategory.CUSTOM, "other text")

    def test_deregister_removes_template(self):
        t = self.registry.register("temp", PromptCategory.CUSTOM, "text")
        self.registry.deregister(t.prompt_id)
        with self.assertRaises(AIPromptNotFoundError):
            self.registry.get(t.prompt_id)

    def test_deregister_unknown_raises(self):
        with self.assertRaises(AIPromptNotFoundError):
            self.registry.deregister("nonexistent")

    def test_enable_disable(self):
        t = self.registry.register("toggle", PromptCategory.CUSTOM, "text")
        self.registry.disable(t.prompt_id)
        self.assertFalse(self.registry.get(t.prompt_id).enabled)
        self.registry.enable(t.prompt_id)
        self.assertTrue(self.registry.get(t.prompt_id).enabled)

    def test_get_unknown_raises(self):
        with self.assertRaises(AIPromptNotFoundError):
            self.registry.get("unknown-id")


# ---------------------------------------------------------------------------
# Model / Prompt Lookup
# ---------------------------------------------------------------------------

class TestPromptLookup(unittest.TestCase):

    def setUp(self):
        self.registry = PromptRegistry()
        self.t1 = self.registry.register(
            "sys-analyst", PromptCategory.SYSTEM, "You are an analyst.", tags=("finance", "core")
        )
        self.t2 = self.registry.register(
            "sys-summary", PromptCategory.SUMMARIZATION, "Summarize: {{text}}", tags=("finance",),
            variables=("text",),
        )

    def test_find_by_name(self):
        found = self.registry.find_by_name("sys-analyst")
        self.assertEqual(found.prompt_id, self.t1.prompt_id)

    def test_find_by_name_missing_returns_none(self):
        self.assertIsNone(self.registry.find_by_name("does-not-exist"))

    def test_search_by_category(self):
        results = self.registry.search(category=PromptCategory.SYSTEM)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].prompt_id, self.t1.prompt_id)

    def test_search_by_tag(self):
        results = self.registry.search(tag="finance")
        self.assertEqual(len(results), 2)

    def test_search_enabled_only(self):
        self.registry.disable(self.t2.prompt_id)
        results = self.registry.search(enabled_only=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].prompt_id, self.t1.prompt_id)

    def test_list_all(self):
        self.assertEqual(len(self.registry.list_all()), 2)
        self.assertEqual(len(self.registry), 2)


# ---------------------------------------------------------------------------
# Version Management
# ---------------------------------------------------------------------------

class TestVersionManagement(unittest.TestCase):

    def setUp(self):
        self.registry = PromptRegistry()
        self.template = self.registry.register("versioned", PromptCategory.CUSTOM, "v1 text")

    def test_initial_version_is_active(self):
        v1 = self.template.active_version
        self.assertEqual(v1.version_number, 1)
        self.assertTrue(v1.active)

    def test_add_version_activates_by_default(self):
        v2 = self.registry.add_version(self.template.prompt_id, "v2 text")
        self.assertEqual(v2.version_number, 2)
        self.assertTrue(v2.active)
        self.assertEqual(self.template.active_version.version_id, v2.version_id)

    def test_add_version_without_activation(self):
        v2 = self.registry.add_version(self.template.prompt_id, "v2 text", activate=False)
        self.assertFalse(v2.active)
        # original v1 remains active
        self.assertEqual(self.template.active_version.version_number, 1)

    def test_rollback_to_previous_version(self):
        v1 = self.template.active_version
        self.registry.add_version(self.template.prompt_id, "v2 text")
        rolled = self.registry.rollback(self.template.prompt_id, v1.version_id)
        self.assertEqual(rolled.version_id, v1.version_id)
        self.assertTrue(self.template.active_version.active)
        self.assertEqual(self.template.active_version.version_id, v1.version_id)

    def test_rollback_unknown_version_raises(self):
        with self.assertRaises(AIPromptVersionError):
            self.registry.rollback(self.template.prompt_id, "bogus-version-id")

    def test_history_ordered(self):
        self.registry.add_version(self.template.prompt_id, "v2 text")
        self.registry.add_version(self.template.prompt_id, "v3 text")
        history = self.template.history()
        self.assertEqual([v.version_number for v in history], [1, 2, 3])

    def test_audit_history_recorded(self):
        vm = self.registry.version_manager
        self.registry.add_version(self.template.prompt_id, "v2 text")
        entries = vm.history.for_prompt(self.template.prompt_id)
        self.assertEqual(len(entries), 2)  # initial create + v2 create


# ---------------------------------------------------------------------------
# Context Building
# ---------------------------------------------------------------------------

class TestContextBuilding(unittest.TestCase):

    def test_add_segments_and_build(self):
        ctx = (
            ContextBuilder("s1", "m1")
            .add_system("system instructions")
            .add_user("what is the regime?")
            .build()
        )
        self.assertEqual(len(ctx.segments), 2)
        self.assertTrue(ctx.is_within_budget)

    def test_priority_ordering(self):
        ctx = (
            ContextBuilder("s1", "m1")
            .add_retrieved("low priority doc")
            .add_system("critical instructions")
            .add_user("high priority query")
            .build()
        )
        priorities = [s.priority for s in ctx.segments]
        self.assertEqual(priorities, sorted(priorities, key=lambda p: p.value))
        self.assertEqual(ctx.segments[0].source, "system")

    def test_truncation_when_budget_exceeded(self):
        ctx = (
            ContextBuilder("s1", "m1")
            .with_max_tokens(5)
            .add_system("short", estimated_tokens=3)
            .add_retrieved("this will not fit", estimated_tokens=100)
            .build()
        )
        self.assertTrue(ctx.truncated)
        self.assertEqual(len(ctx.segments), 1)

    def test_no_segments_fit_raises(self):
        with self.assertRaises(AIContextIncompleteError):
            (
                ContextBuilder("s1", "m1")
                .with_max_tokens(1)
                .add_system("too big", estimated_tokens=50)
                .build()
            )

    def test_merge_multiple_sources(self):
        first = ContextBuilder("s1", "m1").add_system("base instructions").build()
        merged = (
            ContextBuilder("s1", "m1")
            .merge(first)
            .add_user("follow-up query")
            .build()
        )
        self.assertEqual(len(merged.segments), 2)

    def test_estimate_tokens_is_provider_independent(self):
        self.assertEqual(estimate_tokens(""), 0)
        self.assertGreater(estimate_tokens("a" * 40), 0)

    def test_max_tokens_must_be_positive(self):
        with self.assertRaises(AIContextIncompleteError):
            ContextBuilder("s1", "m1").with_max_tokens(0)

    def test_to_text_joins_segments(self):
        ctx = ContextBuilder("s1", "m1").add_system("A").add_user("B").build()
        text = ctx.to_text(separator="|")
        self.assertIn("A", text)
        self.assertIn("B", text)
        self.assertIn("|", text)


# ---------------------------------------------------------------------------
# Variable Substitution / Rendering
# ---------------------------------------------------------------------------

class TestVariableSubstitution(unittest.TestCase):

    def setUp(self):
        self.renderer = PromptRenderer()

    def test_render_substitutes_variables(self):
        version = PromptVersion.create("p1", 1, "Hello {{name}}, you have {{count}} items.", ("name", "count"))
        rendered = self.renderer.render(version, PromptVariables({"name": "Trader", "count": 5}))
        self.assertEqual(rendered, "Hello Trader, you have 5 items.")

    def test_render_missing_declared_variable_raises(self):
        version = PromptVersion.create("p1", 1, "Hello {{name}}!", ("name",))
        with self.assertRaises(AIMissingVariableError):
            self.renderer.render(version, PromptVariables({}))

    def test_render_unresolved_template_variable_raises(self):
        # variable used in template text but not declared -- still must resolve
        version = PromptVersion.create("p1", 1, "Hello {{name}}!", ())
        with self.assertRaises(AIMissingVariableError):
            self.renderer.render(version, PromptVariables({}))

    def test_render_no_variables_needed(self):
        version = PromptVersion.create("p1", 1, "Static text with no variables.", ())
        rendered = self.renderer.render(version, PromptVariables({}))
        self.assertEqual(rendered, "Static text with no variables.")


# ---------------------------------------------------------------------------
# Prompt Composition
# ---------------------------------------------------------------------------

class TestPromptComposition(unittest.TestCase):

    def setUp(self):
        self.registry = PromptRegistry()
        self.composer = PromptComposer()

    def test_compose_without_context(self):
        t = self.registry.register("greet", PromptCategory.INSTRUCTION, "Hi {{name}}!", variables=("name",))
        result = self.composer.compose(t, PromptVariables({"name": "Alice"}))
        self.assertEqual(result.rendered_text, "Hi Alice!")
        self.assertFalse(result.context_included)

    def test_compose_with_context(self):
        t = self.registry.register("greet2", PromptCategory.INSTRUCTION, "Hi {{name}}!", variables=("name",))
        ctx = ContextBuilder("s1", "m1").add_system("background info").build()
        result = self.composer.compose(t, PromptVariables({"name": "Bob"}), context=ctx)
        self.assertTrue(result.context_included)
        self.assertIn("background info", result.rendered_text)
        self.assertIn("Hi Bob!", result.rendered_text)

    def test_compose_disabled_prompt_raises(self):
        t = self.registry.register("disabled-prompt", PromptCategory.CUSTOM, "text")
        self.registry.disable(t.prompt_id)
        with self.assertRaises(AIPromptDisabledError):
            self.composer.compose(t, PromptVariables({}))

    def test_compose_system_category_sets_system_text(self):
        t = self.registry.register("sys-prompt", PromptCategory.SYSTEM, "System rules.")
        result = self.composer.compose(t, PromptVariables({}))
        self.assertEqual(result.system_text, "System rules.")

    def test_compose_no_active_version_raises(self):
        metadata = PromptMetadata.create("empty", PromptCategory.CUSTOM)
        template = PromptTemplate(metadata)  # no versions added
        with self.assertRaises(AIPromptVersionError):
            self.composer.compose(template, PromptVariables({}))


# ---------------------------------------------------------------------------
# Validation Framework
# ---------------------------------------------------------------------------

class TestValidationFramework(unittest.TestCase):

    def setUp(self):
        self.registry = PromptRegistry()
        self.prompt_validator = PromptValidator()
        self.context_validator = ContextValidator()
        self.variable_validator = VariableValidator()

    def test_prompt_validator_valid_template(self):
        t = self.registry.register("valid", PromptCategory.CUSTOM, "Hello {{name}}", variables=("name",))
        result = self.prompt_validator.validate(t)
        self.assertTrue(result.is_valid)

    def test_prompt_validator_disabled_is_invalid(self):
        t = self.registry.register("disabled", PromptCategory.CUSTOM, "text")
        self.registry.disable(t.prompt_id)
        result = self.prompt_validator.validate(t)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("disabled" in e for e in result.errors))

    def test_prompt_validator_empty_template_text_invalid(self):
        result = self.prompt_validator.validate_template_text("   ")
        self.assertFalse(result.is_valid)

    def test_prompt_validator_unbalanced_delimiters_invalid(self):
        result = self.prompt_validator.validate_template_text("Hello {{name}")
        self.assertFalse(result.is_valid)

    def test_prompt_validator_with_missing_variables(self):
        t = self.registry.register("needs-var", PromptCategory.CUSTOM, "Hi {{name}}", variables=("name",))
        result = self.prompt_validator.validate(t, PromptVariables({}))
        self.assertFalse(result.is_valid)

    def test_variable_validator_pass(self):
        version = PromptVersion.create("p1", 1, "Hi {{x}}", ("x",))
        result = self.variable_validator.validate(version, PromptVariables({"x": 1}))
        self.assertTrue(result.is_valid)

    def test_context_validator_pass(self):
        ctx = ContextBuilder("s1", "m1").add_system("ok").build()
        result = self.context_validator.validate(ctx)
        self.assertTrue(result.is_valid)

    def test_context_validator_flags_truncation(self):
        ctx = (
            ContextBuilder("s1", "m1")
            .with_max_tokens(2)
            .add_system("fits", estimated_tokens=2)
            .add_retrieved("does not fit", estimated_tokens=50)
            .build()
        )
        result = self.context_validator.validate(ctx)
        self.assertFalse(result.is_valid)


# ---------------------------------------------------------------------------
# Policy Framework
# ---------------------------------------------------------------------------

class TestPolicyFramework(unittest.TestCase):

    def test_default_prompt_selection_policy(self):
        registry = PromptRegistry()
        t1 = registry.register("a", PromptCategory.CUSTOM, "a-text")
        registry.disable(t1.prompt_id)
        t2 = registry.register("b", PromptCategory.CUSTOM, "b-text")
        policy = DefaultPromptSelectionPolicy()
        selected = policy.select([t1, t2])
        self.assertEqual(selected.prompt_id, t2.prompt_id)

    def test_default_prompt_selection_policy_no_candidates(self):
        policy = DefaultPromptSelectionPolicy()
        self.assertIsNone(policy.select([]))

    def test_default_context_priority_policy_orders_ascending(self):
        segments = [
            ContextSegment.create("retrieval", "low", priority=ContextPriority.LOW),
            ContextSegment.create("system", "critical", priority=ContextPriority.CRITICAL),
        ]
        ordered = DefaultContextPriorityPolicy().order(segments)
        self.assertEqual(ordered[0].source, "system")

    def test_active_version_policy(self):
        registry = PromptRegistry()
        t = registry.register("p", PromptCategory.CUSTOM, "text")
        policy = ActiveVersionPolicy()
        self.assertEqual(policy.resolve(t).version_id, t.active_version.version_id)

    def test_strict_validation_policy_raises_on_failure(self):
        from iios.ai.prompt_context.validation import ValidationResult
        policy = StrictValidationPolicy()
        with self.assertRaises(AIPromptPolicyViolationError):
            policy.enforce(ValidationResult(False, ("bad",)))

    def test_permissive_validation_policy_never_raises(self):
        from iios.ai.prompt_context.validation import ValidationResult
        policy = PermissiveValidationPolicy()
        policy.enforce(ValidationResult(False, ("bad",)))  # must not raise

    def test_fixed_token_budget_policy(self):
        policy = FixedTokenBudgetPolicy(2048)
        self.assertEqual(policy.max_tokens_for("any.module"), 2048)

    def test_fixed_token_budget_policy_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            FixedTokenBudgetPolicy(0)

    def test_per_module_token_budget_policy(self):
        policy = PerModuleTokenBudgetPolicy({"m1": 100}, default=50)
        self.assertEqual(policy.max_tokens_for("m1"), 100)
        self.assertEqual(policy.max_tokens_for("m2"), 50)


# ---------------------------------------------------------------------------
# Event Publishing
# ---------------------------------------------------------------------------

class TestEventPublishing(unittest.TestCase):

    def setUp(self):
        self.bus = PromptEventBus()

    def test_prompt_registered_event(self):
        received: List = []
        self.bus.subscribe(PromptEventType.PROMPT_REGISTERED, received.append)
        registry = PromptRegistry(event_bus=self.bus)
        registry.register("evt-prompt", PromptCategory.CUSTOM, "text")
        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], PromptRegisteredEvent)

    def test_prompt_rendered_event(self):
        received: List = []
        self.bus.subscribe(PromptEventType.PROMPT_RENDERED, received.append)
        registry = PromptRegistry(event_bus=self.bus)
        t = registry.register("evt-render", PromptCategory.CUSTOM, "Hi {{n}}", variables=("n",))
        composer = PromptComposer(event_bus=self.bus)
        composer.compose(t, PromptVariables({"n": "x"}))
        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], PromptRenderedEvent)

    def test_context_built_event(self):
        received: List = []
        self.bus.subscribe(PromptEventType.CONTEXT_BUILT, received.append)
        ContextBuilder("s1", "m1", event_bus=self.bus).add_system("hi").build()
        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], ContextBuiltEvent)

    def test_validation_events_via_gateway(self):
        gw = PromptContextGateway()
        gw.initialize()
        gw.start()
        ok_events: List = []
        fail_events: List = []
        gw.event_bus.subscribe(PromptEventType.VALIDATION_SUCCEEDED, ok_events.append)
        gw.event_bus.subscribe(PromptEventType.VALIDATION_FAILED, fail_events.append)
        t = gw.register_prompt("v-evt", PromptCategory.CUSTOM, "Hi {{n}}", variables=("n",))
        gw.validate_prompt(t.prompt_id, {"n": "x"})
        gw.validate_prompt(t.prompt_id, {})
        gw.stop()
        self.assertEqual(len(ok_events), 1)
        self.assertEqual(len(fail_events), 1)
        self.assertIsInstance(ok_events[0], ValidationSucceededEvent)
        self.assertIsInstance(fail_events[0], ValidationFailedEvent)

    def test_multiple_subscribers_all_receive(self):
        a, b = [], []
        self.bus.subscribe(PromptEventType.PROMPT_REGISTERED, a.append)
        self.bus.subscribe(PromptEventType.PROMPT_REGISTERED, b.append)
        registry = PromptRegistry(event_bus=self.bus)
        registry.register("multi-sub", PromptCategory.CUSTOM, "text")
        self.assertEqual(len(a), 1)
        self.assertEqual(len(b), 1)

    def test_published_count_increments(self):
        registry = PromptRegistry(event_bus=self.bus)
        registry.register("count-me", PromptCategory.CUSTOM, "text")
        self.assertEqual(self.bus.published_count, 1)

    def test_unsubscribe_stops_delivery(self):
        received: List = []
        sub_id = self.bus.subscribe(PromptEventType.PROMPT_REGISTERED, received.append)
        self.bus.unsubscribe(sub_id)
        registry = PromptRegistry(event_bus=self.bus)
        registry.register("unsub-test", PromptCategory.CUSTOM, "text")
        self.assertEqual(len(received), 0)


# ---------------------------------------------------------------------------
# Gateway API Completeness
# ---------------------------------------------------------------------------

class TestGatewayAPICompleteness(unittest.TestCase):

    def setUp(self):
        self.gw = PromptContextGateway()
        self.gw.initialize()
        self.gw.start()

    def tearDown(self):
        if self.gw.lifecycle_state.value == "running":
            self.gw.stop()

    def test_register_get_list(self):
        t = self.gw.register_prompt("api-test", PromptCategory.CUSTOM, "text")
        self.assertEqual(self.gw.get_prompt(t.prompt_id).prompt_id, t.prompt_id)
        self.assertIn(t.prompt_id, [x.prompt_id for x in self.gw.list_templates()])

    def test_find_by_name(self):
        t = self.gw.register_prompt("find-me", PromptCategory.CUSTOM, "text")
        found = self.gw.find_prompt_by_name("find-me")
        self.assertEqual(found.prompt_id, t.prompt_id)

    def test_enable_disable_remove(self):
        t = self.gw.register_prompt("lifecycle-test", PromptCategory.CUSTOM, "text")
        self.gw.disable_prompt(t.prompt_id)
        self.assertFalse(self.gw.get_prompt(t.prompt_id).enabled)
        self.gw.enable_prompt(t.prompt_id)
        self.assertTrue(self.gw.get_prompt(t.prompt_id).enabled)
        self.gw.remove_prompt(t.prompt_id)
        with self.assertRaises(AIPromptNotFoundError):
            self.gw.get_prompt(t.prompt_id)

    def test_versioning_via_gateway(self):
        t = self.gw.register_prompt("ver-test", PromptCategory.CUSTOM, "v1")
        v2 = self.gw.add_version(t.prompt_id, "v2")
        self.assertEqual(self.gw.get_prompt(t.prompt_id).active_version.version_id, v2.version_id)
        history = self.gw.version_history(t.prompt_id)
        self.assertEqual(len(history), 2)

    def test_build_context_and_compose(self):
        t = self.gw.register_prompt("compose-test", PromptCategory.INSTRUCTION, "Q: {{q}}", variables=("q",))
        ctx = self.gw.build_context("s1", "m1").add_user("background").build()
        result = self.gw.compose_prompt(t.prompt_id, {"q": "2+2?"}, context=ctx)
        self.assertIn("2+2?", result.rendered_text)

    def test_validate_prompt_and_context(self):
        t = self.gw.register_prompt("validate-test", PromptCategory.CUSTOM, "Hi {{n}}", variables=("n",))
        result = self.gw.validate_prompt(t.prompt_id, {"n": "x"})
        self.assertTrue(result.is_valid)
        ctx = self.gw.build_context("s1", "m1").add_system("x").build()
        ctx_result = self.gw.validate_context(ctx)
        self.assertTrue(ctx_result.is_valid)

    def test_health_and_status(self):
        h = self.gw.health()
        self.assertIn("module_id", h)
        self.assertTrue(h["is_running"])
        s = self.gw.status()
        self.assertIn("events_published", s)

    def test_snapshot(self):
        self.gw.register_prompt("snap-test", PromptCategory.CUSTOM, "text")
        snap = self.gw.snapshot()
        self.assertEqual(snap.template_count, 1)

    def test_lifecycle_stop(self):
        self.gw.stop()
        self.assertFalse(self.gw.health()["is_running"])


# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy(unittest.TestCase):

    def test_all_inherit_ai_exception(self):
        for exc_cls, args in [
            (AIPromptNotFoundError, ("pid",)),
            (AIPromptAlreadyExistsError, ("pid",)),
            (AIPromptVersionError, ("msg",)),
            (AIPromptDisabledError, ("pid",)),
        ]:
            with self.subTest(exc_cls=exc_cls):
                exc = exc_cls(*args)
                self.assertIsInstance(exc, AIPromptException)
                self.assertIsInstance(exc, AIException)

    def test_error_codes_unique(self):
        codes = {
            AIPromptNotFoundError("x").error_code,
            AIPromptAlreadyExistsError("x").error_code,
            AIPromptVersionError("x").error_code,
            AIPromptDisabledError("x").error_code,
        }
        self.assertEqual(len(codes), 4)

    def test_policy_violation_error_message(self):
        exc = AIPromptPolicyViolationError("violation detail")
        self.assertIn("violation detail", str(exc))

    def test_missing_variable_error_is_ai_exception(self):
        exc = AIMissingVariableError("missing x")
        self.assertIsInstance(exc, AIException)

    def test_context_incomplete_error_is_ai_exception(self):
        exc = AIContextIncompleteError("no fit")
        self.assertIsInstance(exc, AIException)


# ---------------------------------------------------------------------------
# Container / Dependency Injection
# ---------------------------------------------------------------------------

class TestContainerIntegration(unittest.TestCase):

    def test_container_build_wires_all_components(self):
        c = PromptContextContainer()
        c.build()
        self.assertTrue(c.is_built)
        self.assertIsNotNone(c.registry)
        self.assertIsNotNone(c.assembler)
        self.assertIsNotNone(c.composer)
        self.assertIsNotNone(c.event_bus)
        self.assertIsNotNone(c.version_manager)

    def test_two_containers_independent(self):
        c1 = PromptContextContainer()
        c2 = PromptContextContainer()
        c1.registry.register("only-in-c1", PromptCategory.CUSTOM, "text")
        self.assertEqual(len(c1.registry), 1)
        self.assertEqual(len(c2.registry), 0)

    def test_custom_policies_injectable(self):
        budget_policy = FixedTokenBudgetPolicy(1234)
        c = PromptContextContainer(token_budget_policy=budget_policy)
        self.assertEqual(c.token_budget_policy.max_tokens_for("any"), 1234)

    def test_gateway_uses_injected_container(self):
        c = PromptContextContainer()
        gw = PromptContextGateway(container=c)
        gw.initialize()
        gw.start()
        gw.register_prompt("inj-test", PromptCategory.CUSTOM, "text")
        self.assertEqual(len(c.registry), 1)
        gw.stop()


# ---------------------------------------------------------------------------
# Thread Safety
# ---------------------------------------------------------------------------

class TestThreadSafety(unittest.TestCase):

    def test_concurrent_registration(self):
        registry = PromptRegistry()
        errors: List[Exception] = []

        def _register(i):
            try:
                registry.register(f"concurrent-{i}", PromptCategory.CUSTOM, "text")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=_register, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(registry), 20)

    def test_concurrent_context_building(self):
        results: List[AssembledContext] = []
        lock = threading.Lock()

        def _build(i):
            ctx = ContextBuilder(f"s{i}", "m1").add_system("x").add_user(f"query {i}").build()
            with lock:
                results.append(ctx)

        threads = [threading.Thread(target=_build, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 20)


if __name__ == "__main__":
    unittest.main()
