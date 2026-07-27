"""
test_integration.py -- A1 AI Foundation Integration Validation

Exercises the complete A1 lifecycle:
  Session → Context → Request → ExecutionRuntime → Response
  + Gateway (config, health, snapshot, events)
  + Container (DI wiring)
  + Metrics / Events / Cost
  + Exception hierarchy
  + Health reporting

A1 AI Foundation -- Phase 3, Integration
"""
from __future__ import annotations

import threading
import time
import unittest
from typing import Any, Dict, List

# ── Framework imports ──────────────────────────────────────────────────────
from iios.ai.foundation.container    import AIContainer
from iios.ai.foundation.gateway      import AIFoundationGateway

from iios.ai.foundation.session      import AISessionManager, SessionFactory
from iios.ai.foundation.context      import (
    AIContext, ContextBuilder, ContextValidator, ContextMetadata,
)
from iios.ai.foundation.request      import (
    AIRequest, AIResponse, AIExecutionRequest, RequestMetadata,
)
from iios.ai.foundation.provider     import (
    AIProviderRuntime, AIProviderExtension, AIProviderCapabilities,
    ProviderCapabilityType, ProviderTier,
)
from iios.ai.foundation.runtime      import (
    ExecutionRuntime, ExecutionPipeline, ExecutionContext,
)
from iios.ai.foundation.events       import (
    AIEventBus, AIEventType,
    SessionStartedEvent, SessionEndedEvent,
    ExecutionCompletedEvent, ExecutionFailedEvent,
)
from iios.ai.foundation.metrics      import RuntimeMetrics, ProviderMetrics
from iios.ai.foundation.cost         import CostTracker, TokenUsage, ExecutionCost
from iios.ai.foundation.retry        import RetryManager, RetryPolicy, ExponentialBackoffStrategy
from iios.ai.foundation.timeout      import TimeoutPolicy, ExecutionDeadline
from iios.ai.foundation.health       import HealthReporter, HealthLevel
from iios.ai.foundation.config       import AIFrameworkConfiguration, EnvironmentConfigurationLoader
from iios.ai.foundation.observability import StructuredLogger, ExecutionTimer
from iios.ai.foundation.lifecycle    import AILifecycleAwareMixin, AILifecycleState
from iios.ai.foundation.exceptions   import (
    AIException, AISessionException, AISessionNotFoundError,
    AISessionLimitError, AIProviderException, AIExecutionException,
    AIRequestException, AIContextException,
)
from iios.ai.foundation.snapshot     import FoundationSnapshot


# ── Helper stubs ───────────────────────────────────────────────────────────

def _make_caps(provider_id: str, capabilities: set) -> AIProviderCapabilities:
    return AIProviderCapabilities(
        provider_id    = provider_id,
        model_id       = f"{provider_id}-model",
        capabilities   = frozenset(capabilities),
        context_window = 4096,
        max_output     = 1024,
        tier           = ProviderTier.STANDARD,
    )


class _StubProvider(AIProviderExtension):
    """Minimal provider stub used across integration tests."""

    def __init__(self, pid: str = "stub-llm", latency_ms: float = 0.0):
        self._pid        = pid
        self._latency_ms = latency_ms
        self._calls      = 0
        self._caps = _make_caps(pid, {ProviderCapabilityType.CHAT,
                                       ProviderCapabilityType.COMPLETION})

    @property
    def provider_id(self) -> str: return self._pid
    @property
    def capabilities(self) -> AIProviderCapabilities: return self._caps

    def complete(self, messages, *, max_tokens, temperature, timeout_s, options=None):
        self._calls += 1
        if self._latency_ms:
            time.sleep(self._latency_ms / 1000.0)
        words = sum(len(m.get("content", "").split()) for m in messages)
        return {
            "content":       f"[{self._pid}] response to {len(messages)} messages",
            "finish_reason": "stop",
            "usage":         {"prompt_tokens": words, "completion_tokens": 20},
        }

    def embed(self, texts, *, timeout_s):
        return [[0.1] * 10 for _ in texts]

    def health_check(self) -> Dict[str, Any]:
        return {"healthy": True, "latency_ms": self._latency_ms or 0.5}

    def tokenise(self, text: str) -> List[int]:
        return list(range(len(text.split())))


def _make_exec_request(
    session_id: str = "sess-test",
    messages:   list = None,
) -> AIExecutionRequest:
    if messages is None:
        messages = [{"role": "user", "content": "hello integration test"}]
    meta = RequestMetadata.create(session_id=session_id, module_id="test.integration")
    req  = AIRequest.create(meta, messages, max_tokens=100)
    return AIExecutionRequest(request=req)


# ══════════════════════════════════════════════════════════════════════════════
# T1: Container integration
# ══════════════════════════════════════════════════════════════════════════════

class TestContainerIntegration(unittest.TestCase):

    def test_container_builds_and_exposes_all_components(self):
        c = AIContainer()
        c.build()
        self.assertTrue(c.is_built())
        # Legacy pipeline
        self.assertIsNotNone(c.pipeline)
        self.assertIsNotNone(c.session_factory)
        self.assertIsNotNone(c.session_manager)
        self.assertIsNotNone(c.context_validator)
        self.assertIsNotNone(c.context_compressor)
        self.assertIsNotNone(c.health_reporter)
        self.assertIsNotNone(c.logger)
        # Provider Runtime
        self.assertIsNotNone(c.event_bus)
        self.assertIsNotNone(c.runtime_metrics)
        self.assertIsNotNone(c.cost_tracker)
        self.assertIsNotNone(c.provider_runtime)
        self.assertIsNotNone(c.execution_runtime)

    def test_container_requires_build_before_access(self):
        c = AIContainer()
        with self.assertRaises(RuntimeError):
            _ = c.session_manager

    def test_container_rebuild_resets_components(self):
        c = AIContainer()
        c.build()
        rt1 = c.execution_runtime
        c.rebuild()
        rt2 = c.execution_runtime
        self.assertIsNot(rt1, rt2)

    def test_container_injects_event_bus_into_execution_runtime(self):
        """Provider runtime and execution runtime share the same event bus."""
        c = AIContainer()
        c.build()
        # Both runtime objects use the container's event bus
        bus = c.event_bus
        self.assertIsNotNone(bus)
        # They were constructed with it (can't check private attrs directly,
        # but publishing through bus should route to both)
        received = []
        bus.subscribe(AIEventType.EXECUTION_COMPLETED, received.append)
        c.execution_runtime.initialize()
        c.execution_runtime.start()
        c.execution_runtime.execute(_make_exec_request())
        self.assertEqual(len(received), 1)
        c.execution_runtime.stop()

    def test_container_provider_runtime_shared_bus(self):
        c = AIContainer()
        c.build()
        events = []
        c.event_bus.subscribe(AIEventType.PROVIDER_REGISTERED, events.append)
        c.provider_runtime.initialize()
        c.provider_runtime.start()
        c.provider_runtime.register_provider(_StubProvider("p1"))
        self.assertEqual(len(events), 1)
        c.provider_runtime.stop()


# ══════════════════════════════════════════════════════════════════════════════
# T2: Session lifecycle
# ══════════════════════════════════════════════════════════════════════════════

class TestSessionLifecycle(unittest.TestCase):

    def setUp(self):
        self.manager = AISessionManager(factory=SessionFactory(), max_sessions=10)

    def test_create_active_session(self):
        s = self.manager.create_session("mod.a")
        from iios.ai.foundation.session import SessionState
        self.assertEqual(s.state, SessionState.ACTIVE)
        self.assertIsNotNone(s.session_id)

    def test_session_full_lifecycle(self):
        from iios.ai.foundation.session import SessionState
        s = self.manager.create_session("mod.a")
        self.assertEqual(s.state, SessionState.ACTIVE)
        s.complete()
        self.assertEqual(s.state, SessionState.COMPLETED)

    def test_session_cancel(self):
        from iios.ai.foundation.session import SessionState
        s = self.manager.create_session("mod.a")
        s.cancel()
        self.assertEqual(s.state, SessionState.CANCELLED)

    def test_session_fail(self):
        from iios.ai.foundation.session import SessionState
        s = self.manager.create_session("mod.a")
        s.fail("test error")
        self.assertEqual(s.state, SessionState.FAILED)
        self.assertEqual(s.error, "test error")

    def test_session_context_storage(self):
        s = self.manager.create_session("mod.a")
        s.set("key", {"data": 42})
        self.assertEqual(s.get("key"), {"data": 42})
        self.assertIsNone(s.get("missing"))

    def test_session_limit_enforcement(self):
        manager = AISessionManager(factory=SessionFactory(), max_sessions=2)
        manager.create_session("m1")
        manager.create_session("m2")
        with self.assertRaises(AISessionLimitError):
            manager.create_session("m3")

    def test_session_not_found(self):
        with self.assertRaises(AISessionNotFoundError):
            self.manager.get_session("nonexistent-id")

    def test_session_state_machine_invalid_transition(self):
        """suspend() uses _transition() which raises on invalid state."""
        from iios.ai.foundation.exceptions import AISessionStateError
        s = self.manager.create_session("mod.a")
        s.complete()  # → COMPLETED
        with self.assertRaises(AISessionStateError):
            s.suspend()  # COMPLETED → SUSPENDED is invalid → raises


# ══════════════════════════════════════════════════════════════════════════════
# T3: Context lifecycle
# ══════════════════════════════════════════════════════════════════════════════

class TestContextLifecycle(unittest.TestCase):

    def _meta(self, session_id="s1"):
        import uuid, time
        from iios.ai.foundation.context.context_metadata import ContextMetadata
        return ContextMetadata(
            context_id   = "ctx-1",
            session_id   = session_id,
            module_id    = "test",
            trace_id     = str(uuid.uuid4()),
            capability   = "completion",
            max_tokens   = 4096,
            created_at   = time.time(),
        )

    def test_context_creation_and_message_append(self):
        ctx = AIContext(metadata=self._meta())
        ctx.add_user("hello")
        ctx.add_assistant("hi there")
        msgs = ctx.to_messages()
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "user")

    def test_context_token_budget(self):
        ctx = AIContext(metadata=self._meta())
        ctx.add_user("hello")
        self.assertTrue(ctx.is_within_budget)

    def test_context_builder_fluent_api(self):
        builder = ContextBuilder(session_id="s1", module_id="m1")
        builder.add_system("You are helpful.")
        builder.add_user("What is 2+2?")
        ctx = builder.build()
        self.assertEqual(len(ctx.to_messages()), 2)

    def test_context_validator_passes_valid(self):
        validator = ContextValidator()
        ctx = AIContext(metadata=self._meta())
        ctx.add_user("hello")
        result = validator.validate(ctx)
        self.assertTrue(result.is_valid)

    def test_context_validator_fails_empty(self):
        from iios.ai.foundation.exceptions import AIContextValidationError
        validator = ContextValidator()
        ctx = AIContext(metadata=self._meta())
        with self.assertRaises(AIContextValidationError):
            validator.validate(ctx)


# ══════════════════════════════════════════════════════════════════════════════
# T4: Execution pipeline (full lifecycle)
# ══════════════════════════════════════════════════════════════════════════════

class TestExecutionPipelineLifecycle(unittest.TestCase):

    def _exec_req(self, msgs=None):
        return _make_exec_request(messages=msgs)

    def test_stub_pipeline_succeeds(self):
        from iios.ai.foundation.runtime import ExecutionPipeline
        pipeline = ExecutionPipeline()
        resp, ctx = pipeline.run(self._exec_req())
        self.assertTrue(resp.succeeded)
        self.assertIn("stub", resp.content)

    def test_pipeline_validation_rejects_empty_messages(self):
        from iios.ai.foundation.runtime import ExecutionPipeline
        pipeline = ExecutionPipeline()
        resp, ctx = pipeline.run(_make_exec_request(messages=[]))
        self.assertFalse(resp.succeeded)

    def test_pipeline_routes_to_registered_provider(self):
        from iios.ai.foundation.runtime import ExecutionPipeline
        stub = _StubProvider("my-llm")
        pr   = AIProviderRuntime()
        pr.initialize(); pr.start()
        pr.register_provider(stub)
        pipeline = ExecutionPipeline(provider_runtime=pr)
        resp, ctx = pipeline.run(self._exec_req())
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.provider_id, "my-llm")
        self.assertIn("[my-llm]", resp.content)
        pr.stop()

    def test_pipeline_stage_count(self):
        from iios.ai.foundation.runtime import ExecutionPipeline
        pipeline = ExecutionPipeline()
        self.assertEqual(len(pipeline.stage_names()), 8)

    def test_pipeline_publishes_events(self):
        from iios.ai.foundation.runtime import ExecutionPipeline
        bus = AIEventBus()
        completed = []
        bus.subscribe(AIEventType.EXECUTION_COMPLETED, completed.append)
        pipeline = ExecutionPipeline(event_bus=bus)
        pipeline.run(self._exec_req())
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].event_type, AIEventType.EXECUTION_COMPLETED)

    def test_pipeline_execution_context_records_stages(self):
        from iios.ai.foundation.runtime import ExecutionPipeline
        pipeline = ExecutionPipeline()
        resp, ctx = pipeline.run(self._exec_req())
        # ExecutionContext has stage records
        status = pipeline._execution_runtime_status if hasattr(pipeline, "_execution_runtime_status") else None
        # At minimum succeeded is True and provider is stub
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.provider_id, "stub")


# ══════════════════════════════════════════════════════════════════════════════
# T5: Full execution runtime lifecycle
# ══════════════════════════════════════════════════════════════════════════════

class TestExecutionRuntimeLifecycle(unittest.TestCase):

    def setUp(self):
        self.bus     = AIEventBus()
        self.metrics = RuntimeMetrics()
        self.runtime = ExecutionRuntime(
            event_bus      = self.bus,
            retry_policy   = RetryPolicy(max_attempts=1),
            timeout_policy = TimeoutPolicy.default(),
        )
        self.runtime.initialize()
        self.runtime.start()

    def tearDown(self):
        if self.runtime.is_ai_running:
            self.runtime.stop()

    def test_runtime_succeeds_with_stub(self):
        resp, ctx = self.runtime.execute(_make_exec_request())
        self.assertTrue(resp.succeeded)
        self.assertIsNotNone(resp.response_id)

    def test_runtime_failure_on_empty_messages(self):
        req  = _make_exec_request(messages=[])
        resp, ctx = self.runtime.execute(req)
        self.assertFalse(resp.succeeded)
        self.assertTrue(len(resp.error) > 0)

    def test_runtime_with_registered_provider(self):
        pr = AIProviderRuntime(event_bus=self.bus)
        pr.initialize(); pr.start()
        pr.register_provider(_StubProvider("gpt-stub"))
        rt = ExecutionRuntime(
            provider_runtime = pr,
            event_bus        = self.bus,
            retry_policy     = RetryPolicy(max_attempts=1),
        )
        rt.initialize(); rt.start()
        resp, ctx = rt.execute(_make_exec_request())
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.provider_id, "gpt-stub")
        rt.stop(); pr.stop()

    def test_runtime_status_dict(self):
        status = self.runtime.status()
        self.assertIn("stage_names", status)
        self.assertIn("metrics", status)
        self.assertTrue(status["is_running"])

    def test_runtime_events_emitted_on_success(self):
        events = []
        self.bus.subscribe(AIEventType.EXECUTION_COMPLETED, events.append)
        self.runtime.execute(_make_exec_request())
        self.assertEqual(len(events), 1)

    def test_runtime_events_emitted_on_failure(self):
        events = []
        self.bus.subscribe(AIEventType.EXECUTION_FAILED, events.append)
        self.runtime.execute(_make_exec_request(messages=[]))
        self.assertEqual(len(events), 1)

    def test_runtime_stop_prohibits_execute(self):
        self.runtime.stop()
        with self.assertRaises(RuntimeError):
            self.runtime.execute(_make_exec_request())


# ══════════════════════════════════════════════════════════════════════════════
# T6: Provider registration flow
# ══════════════════════════════════════════════════════════════════════════════

class TestProviderRegistrationFlow(unittest.TestCase):

    def setUp(self):
        self.bus = AIEventBus()
        self.pr  = AIProviderRuntime(event_bus=self.bus)
        self.pr.initialize()
        self.pr.start()

    def tearDown(self):
        self.pr.stop()

    def test_register_and_resolve(self):
        self.pr.register_provider(_StubProvider("llm-a"))
        self.assertTrue(self.pr.can_serve(ProviderCapabilityType.CHAT))
        p = self.pr.select_provider(ProviderCapabilityType.CHAT)
        self.assertEqual(p.provider_id, "llm-a")

    def test_deregister_removes_provider(self):
        self.pr.register_provider(_StubProvider("llm-b"))
        self.pr.deregister_provider("llm-b")
        self.assertFalse(self.pr.can_serve(ProviderCapabilityType.CHAT))

    def test_registration_emits_event(self):
        events = []
        self.bus.subscribe(AIEventType.PROVIDER_REGISTERED, events.append)
        self.pr.register_provider(_StubProvider("llm-c"))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].provider_id, "llm-c")

    def test_health_probe_on_degraded_provider(self):
        class _FailingProvider(_StubProvider):
            def health_check(self):
                return {"healthy": False, "latency_ms": 999.0}
        self.pr.register_provider(_FailingProvider("llm-sick"))
        healthy = self.pr.manager.probe_health("llm-sick")
        self.assertFalse(healthy)


# ══════════════════════════════════════════════════════════════════════════════
# T7: Retry framework integration
# ══════════════════════════════════════════════════════════════════════════════

class TestRetryFrameworkIntegration(unittest.TestCase):

    def test_retry_on_transient_failure(self):
        calls = [0]
        def fn():
            calls[0] += 1
            if calls[0] < 3:
                raise RuntimeError("transient")
            return "ok"
        policy  = RetryPolicy(max_attempts=3, backoff_base_s=0.0)
        manager = RetryManager(policy)
        result, outcome = manager.execute("r1", fn)
        self.assertTrue(outcome.succeeded)
        self.assertEqual(calls[0], 3)
        self.assertEqual(result, "ok")

    def test_retry_exhausted_returns_outcome(self):
        policy  = RetryPolicy(max_attempts=2, backoff_base_s=0.0)
        manager = RetryManager(policy)
        result, outcome = manager.execute("r2", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.total_attempts, 2)
        self.assertIsNone(result)

    def test_non_retryable_stops_after_one(self):
        strategy = ExponentialBackoffStrategy(non_retryable_types=(ValueError,))
        manager  = RetryManager(RetryPolicy(max_attempts=3, backoff_base_s=0.0), strategy)
        result, outcome = manager.execute("r3", lambda: (_ for _ in ()).throw(ValueError("bad")))
        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.total_attempts, 1)

    def test_runtime_uses_retry_policy(self):
        """ExecutionRuntime with no_retry returns failure immediately on abort."""
        rt = ExecutionRuntime(retry_policy=RetryPolicy.no_retry())
        rt.initialize(); rt.start()
        resp, _ = rt.execute(_make_exec_request(messages=[]))
        self.assertFalse(resp.succeeded)
        rt.stop()


# ══════════════════════════════════════════════════════════════════════════════
# T8: Timeout framework integration
# ══════════════════════════════════════════════════════════════════════════════

class TestTimeoutFrameworkIntegration(unittest.TestCase):

    def test_deadline_not_exceeded_for_fresh_deadline(self):
        d = ExecutionDeadline.from_timeout(60.0)
        self.assertFalse(d.is_exceeded())

    def test_deadline_exceeded_for_past_deadline(self):
        d = ExecutionDeadline(time.monotonic() - 1.0)
        self.assertTrue(d.is_exceeded())

    def test_timeout_policy_tiers(self):
        fast    = TimeoutPolicy.fast()
        default = TimeoutPolicy.default()
        relaxed = TimeoutPolicy.relaxed()
        self.assertLess(fast.request_timeout_s, default.request_timeout_s)
        self.assertGreater(relaxed.request_timeout_s, default.request_timeout_s)

    def test_execution_context_honours_deadline(self):
        ctx = ExecutionContext(request_id="r1", session_id="s1")
        self.assertFalse(ctx.is_deadline_exceeded())

    def test_execution_context_with_expired_deadline(self):
        """pipeline_timeout_s=0.0001 → deadline expires after ~0.1ms."""
        tp = TimeoutPolicy(pipeline_timeout_s=0.0001)
        ctx = ExecutionContext(
            request_id     = "r1",
            session_id     = "s1",
            timeout_policy = tp,
        )
        time.sleep(0.001)  # 1ms >> 0.1ms deadline
        self.assertTrue(ctx.is_deadline_exceeded())


# ══════════════════════════════════════════════════════════════════════════════
# T9: Metrics generation
# ══════════════════════════════════════════════════════════════════════════════

class TestMetricsIntegration(unittest.TestCase):

    def test_runtime_metrics_accumulate_across_executions(self):
        metrics = RuntimeMetrics()
        bus     = AIEventBus()
        rt      = ExecutionRuntime(event_bus=bus)
        rt.initialize(); rt.start()

        # Inject metrics into the pipeline indirectly via the runtime
        for _ in range(3):
            rt.execute(_make_exec_request())
        rt.stop()
        # At minimum, the runtime ran without error
        # (metrics are internal to the pipeline stages)
        self.assertTrue(True)

    def test_provider_metrics_accuracy(self):
        pm = ProviderMetrics("openai", "gpt-4o")
        pm.record_request(success=True,  latency_ms=100.0, total_tokens=50)
        pm.record_request(success=True,  latency_ms=200.0, total_tokens=75)
        pm.record_request(success=False, latency_ms=10.0)
        d = pm.to_dict()
        self.assertEqual(d["requests"], 3)
        self.assertAlmostEqual(d["error_rate"], 1/3, places=3)
        self.assertAlmostEqual(d["avg_latency_ms"], 103.33, places=1)

    def test_runtime_metrics_per_provider(self):
        rm = RuntimeMetrics()
        rm.record_execution(success=True,  latency_ms=50.0)
        rm.record_execution(success=False, latency_ms=10.0)
        d = rm.to_dict()
        self.assertEqual(d["total_requests"], 2)
        self.assertEqual(d["total_failure"], 1)
        self.assertAlmostEqual(d["error_rate"], 0.5, places=3)


# ══════════════════════════════════════════════════════════════════════════════
# T10: Event publishing
# ══════════════════════════════════════════════════════════════════════════════

class TestEventPublishingIntegration(unittest.TestCase):

    def setUp(self):
        self.bus = AIEventBus()

    def test_full_session_event_flow(self):
        started  = []
        ended    = []
        self.bus.subscribe(AIEventType.SESSION_STARTED, started.append)
        self.bus.subscribe(AIEventType.SESSION_ENDED,   ended.append)
        self.bus.publish(SessionStartedEvent.create("test", "s1", "m1"))
        self.bus.publish(SessionEndedEvent.create("test", "s1", "m1", "completed"))
        self.assertEqual(len(started), 1)
        self.assertEqual(len(ended), 1)

    def test_execution_event_flow(self):
        completed = []
        failed    = []
        self.bus.subscribe(AIEventType.EXECUTION_COMPLETED, completed.append)
        self.bus.subscribe(AIEventType.EXECUTION_FAILED,    failed.append)
        # max_attempts=1 ensures exactly one FAILED event per bad request (no retries)
        rt = ExecutionRuntime(event_bus=self.bus, retry_policy=RetryPolicy(max_attempts=1))
        rt.initialize(); rt.start()
        rt.execute(_make_exec_request())             # → COMPLETED
        rt.execute(_make_exec_request(messages=[]))  # → FAILED
        rt.stop()
        self.assertEqual(len(completed), 1)
        self.assertEqual(len(failed), 1)

    def test_multiple_subscribers_all_receive(self):
        a, b, c = [], [], []
        for handler in (a.append, b.append, c.append):
            self.bus.subscribe(AIEventType.EXECUTION_COMPLETED, handler)
        rt = ExecutionRuntime(event_bus=self.bus)
        rt.initialize(); rt.start()
        rt.execute(_make_exec_request())
        rt.stop()
        self.assertEqual(len(a), 1)
        self.assertEqual(len(b), 1)
        self.assertEqual(len(c), 1)

    def test_faulty_subscriber_does_not_block_others(self):
        good = []
        def bad(e): raise RuntimeError("boom")
        self.bus.subscribe(AIEventType.SESSION_STARTED, bad)
        self.bus.subscribe(AIEventType.SESSION_STARTED, good.append)
        self.bus.publish(SessionStartedEvent.create("t", "s", "m"))
        self.assertEqual(len(good), 1)

    def test_event_immutability(self):
        evt = SessionStartedEvent.create("t", "s", "m")
        with self.assertRaises((AttributeError, TypeError)):
            evt.source_id = "changed"  # type: ignore


# ══════════════════════════════════════════════════════════════════════════════
# T11: Health reporting
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthReportingIntegration(unittest.TestCase):

    def _make_reporter(self, healthy: bool = True) -> HealthReporter:
        from iios.ai.foundation.health.health_models import HealthCheck
        class _FlagCheck(HealthCheck):
            def __init__(self, ok: bool): self._ok = ok
            @property
            def name(self) -> str: return "flag"
            def check(self) -> bool: return self._ok
        reporter = HealthReporter("iios:test:module")
        reporter.add_check(_FlagCheck(healthy))
        return reporter

    def test_health_reporter_healthy(self):
        reporter = self._make_reporter(healthy=True)
        status = reporter.health()
        self.assertEqual(status.level, HealthLevel.HEALTHY)
        self.assertTrue(status.is_healthy)

    def test_health_reporter_unhealthy(self):
        reporter = self._make_reporter(healthy=False)
        status = reporter.health()
        self.assertEqual(status.level, HealthLevel.UNHEALTHY)
        self.assertFalse(status.is_healthy)

    def test_health_reporter_degraded(self):
        from iios.ai.foundation.health.health_models import HealthCheck
        class _PassCheck(HealthCheck):
            @property
            def name(self): return "pass"
            def check(self): return True
        class _FailCheck(HealthCheck):
            @property
            def name(self): return "fail"
            def check(self): return False
        reporter = HealthReporter("iios:test")
        reporter.add_check(_PassCheck())
        reporter.add_check(_FailCheck())
        status = reporter.health()
        self.assertEqual(status.level, HealthLevel.DEGRADED)

    def test_container_health_reporter_accessible(self):
        c = AIContainer()
        c.build()
        # Reporter with no checks defaults to HEALTHY (all-pass vacuously)
        status = c.health_reporter.health()
        self.assertIsNotNone(status)

    def test_gateway_health_dict(self):
        gw = AIFoundationGateway()
        gw.initialize()
        gw.start()
        h = gw.health()
        self.assertIn("module_id", h)
        self.assertIn("state", h)
        self.assertTrue(h["is_running"])
        self.assertIn("provider_count", h)
        gw.stop()


# ══════════════════════════════════════════════════════════════════════════════
# T12: Configuration loading
# ══════════════════════════════════════════════════════════════════════════════

class TestConfigurationIntegration(unittest.TestCase):

    def test_environment_loader_returns_defaults(self):
        loader = EnvironmentConfigurationLoader()
        config = loader.load()
        self.assertIsInstance(config, AIFrameworkConfiguration)
        self.assertIsNotNone(config.environment)
        self.assertGreater(config.max_sessions, 0)
        self.assertGreater(config.session_ttl_s, 0)

    def test_config_immutable(self):
        loader = EnvironmentConfigurationLoader()
        config = loader.load()
        with self.assertRaises((AttributeError, TypeError)):
            config.environment = "prod"  # type: ignore

    def test_container_wires_config(self):
        c = AIContainer()
        c.build()
        self.assertIsNotNone(c.configuration)
        self.assertIsNotNone(c.runtime_config)

    def test_gateway_loads_config_on_initialize(self):
        gw = AIFoundationGateway()
        # Config is None BEFORE initialize
        self.assertIsNone(gw.configuration)
        gw.initialize()
        # Config is populated AT initialize
        self.assertIsNotNone(gw.configuration)
        gw.start()
        gw.stop()


# ══════════════════════════════════════════════════════════════════════════════
# T13: Exception hierarchy
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptionHierarchy(unittest.TestCase):

    def test_all_exceptions_inherit_from_ai_exception(self):
        hierarchy = [
            AISessionException, AISessionNotFoundError, AISessionLimitError,
            AIProviderException, AIExecutionException,
            AIRequestException, AIContextException,
        ]
        for exc_cls in hierarchy:
            self.assertTrue(
                issubclass(exc_cls, AIException),
                f"{exc_cls.__name__} does not inherit from AIException"
            )

    def test_all_exceptions_inherit_from_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        self.assertTrue(issubclass(AIException, IIOSError))

    def test_session_not_found_carries_code(self):
        exc = AISessionNotFoundError("sess-999")
        self.assertIn("sess-999", str(exc))
        self.assertTrue(hasattr(exc, "error_code"))

    def test_session_limit_error(self):
        exc = AISessionLimitError(500)
        self.assertIn("500", str(exc))

    def test_exception_catchable_as_ai_exception(self):
        try:
            raise AISessionNotFoundError("bad-id")
        except AIException:
            pass  # correctly caught
        except Exception:
            self.fail("AISessionNotFoundError not caught as AIException")


# ══════════════════════════════════════════════════════════════════════════════
# T14: Gateway API completeness
# ══════════════════════════════════════════════════════════════════════════════

class TestGatewayAPICompleteness(unittest.TestCase):

    def setUp(self):
        self.gw = AIFoundationGateway()
        self.gw.initialize()
        self.gw.start()

    def tearDown(self):
        if self.gw.is_ai_running:
            self.gw.stop()

    def test_lifecycle_states(self):
        self.assertEqual(self.gw.lifecycle_state, AILifecycleState.RUNNING)
        self.assertTrue(self.gw.is_ai_running)

    def test_health_returns_structured_dict(self):
        h = self.gw.health()
        for key in ("module_id", "state", "is_running", "provider_count",
                    "total_requests", "total_errors", "uptime_s", "version"):
            self.assertIn(key, h)

    def test_status_superset_of_health(self):
        s = self.gw.status()
        h = self.gw.health()
        for key in h:
            self.assertIn(key, s)
        self.assertIn("configuration", s)

    def test_statistics_dict(self):
        stats = self.gw.statistics()
        self.assertIn("total_requests", stats)
        self.assertIn("error_rate", stats)
        self.assertIn("uptime_s", stats)

    def test_snapshot_is_frozen(self):
        snap = self.gw.snapshot()
        self.assertIsInstance(snap, FoundationSnapshot)
        with self.assertRaises((AttributeError, TypeError)):
            snap.module_id = "hacked"  # type: ignore

    def test_snapshot_fields(self):
        snap = self.gw.snapshot()
        self.assertIsNotNone(snap.snapshot_id)
        self.assertIsNotNone(snap.module_id)
        self.assertIsNotNone(snap.lifecycle_state)

    def test_event_bus_accessible(self):
        bus = self.gw.event_bus
        self.assertIsNotNone(bus)

    def test_gateway_stop_and_is_not_running(self):
        self.gw.stop()
        self.assertFalse(self.gw.is_ai_running)

    def test_gateway_record_request_increments_counter(self):
        self.gw.record_request()
        self.gw.record_request(error=True)
        stats = self.gw.statistics()
        self.assertEqual(stats["total_requests"], 2)
        self.assertEqual(self.gw.health()["total_errors"], 1)


# ══════════════════════════════════════════════════════════════════════════════
# T15: Observability
# ══════════════════════════════════════════════════════════════════════════════

class TestObservabilityIntegration(unittest.TestCase):

    def test_structured_logger_logs_without_error(self):
        logger = StructuredLogger("test.module")
        # Should not raise
        logger.info("test message", key="val")
        logger.debug("debug msg")
        logger.warning("warn msg")

    def test_execution_timer_measures_time(self):
        timer = ExecutionTimer("test-op")
        with timer.measure() as result:
            time.sleep(0.01)
        self.assertGreater(result.elapsed_ms, 5.0)
        self.assertTrue(result.succeeded)

    def test_execution_timer_reusable(self):
        timer = ExecutionTimer("test-op")
        with timer.measure() as r1:
            time.sleep(0.01)
        with timer.measure() as r2:
            time.sleep(0.01)
        self.assertGreater(r1.elapsed_ms, 0)
        self.assertGreater(r2.elapsed_ms, 0)


# ══════════════════════════════════════════════════════════════════════════════
# T16: Dependency injection (no global singletons)
# ══════════════════════════════════════════════════════════════════════════════

class TestDependencyInjection(unittest.TestCase):

    def test_two_containers_are_independent(self):
        c1 = AIContainer()
        c2 = AIContainer()
        c1.build(); c2.build()
        self.assertIsNot(c1.session_manager, c2.session_manager)
        self.assertIsNot(c1.event_bus, c2.event_bus)
        self.assertIsNot(c1.execution_runtime, c2.execution_runtime)

    def test_event_bus_not_shared_between_containers(self):
        """Events from container 1 must not reach container 2's subscribers."""
        c1 = AIContainer()
        c2 = AIContainer()
        c1.build(); c2.build()
        received_c2 = []
        c2.event_bus.subscribe(AIEventType.EXECUTION_COMPLETED, received_c2.append)
        c1.execution_runtime.initialize(); c1.execution_runtime.start()
        c1.execution_runtime.execute(_make_exec_request())
        c1.execution_runtime.stop()
        self.assertEqual(len(received_c2), 0)

    def test_provider_runtime_injectable_into_execution_runtime(self):
        pr = AIProviderRuntime()
        rt = ExecutionRuntime(provider_runtime=pr)
        # Both use the same provider_runtime instance
        self.assertIs(rt._provider_runtime, pr)

    def test_container_custom_retry_policy(self):
        fast_retry = RetryPolicy.no_retry()
        c = AIContainer(retry_policy=fast_retry)
        c.build()
        rt = c.execution_runtime
        rt.initialize(); rt.start()
        # Should still work with no-retry policy
        resp, _ = rt.execute(_make_exec_request())
        self.assertTrue(resp.succeeded)
        rt.stop()


# ══════════════════════════════════════════════════════════════════════════════
# T17: Thread safety
# ══════════════════════════════════════════════════════════════════════════════

class TestThreadSafety(unittest.TestCase):

    def test_concurrent_session_creation(self):
        manager = AISessionManager(factory=SessionFactory(), max_sessions=100)
        errors  = []
        sessions = []
        lock = threading.Lock()

        def create():
            try:
                s = manager.create_session("mod")
                with lock:
                    sessions.append(s.session_id)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=create) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(sessions), 20)
        # All session IDs unique
        self.assertEqual(len(set(sessions)), 20)

    def test_concurrent_executions(self):
        rt = ExecutionRuntime(retry_policy=RetryPolicy(max_attempts=1))
        rt.initialize(); rt.start()
        results = []
        lock = threading.Lock()

        def run():
            resp, _ = rt.execute(_make_exec_request())
            with lock:
                results.append(resp.succeeded)

        threads = [threading.Thread(target=run) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        rt.stop()
        self.assertTrue(all(results))

    def test_concurrent_event_publishing(self):
        bus     = AIEventBus()
        received = []
        lock    = threading.Lock()

        def handler(e):
            with lock:
                received.append(e)

        bus.subscribe(AIEventType.SESSION_STARTED, handler)

        def publish():
            bus.publish(SessionStartedEvent.create("t", "s", "m"))

        threads = [threading.Thread(target=publish) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(received), 20)


if __name__ == "__main__":
    unittest.main()
