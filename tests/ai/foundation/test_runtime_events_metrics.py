"""
test_runtime_events_metrics.py -- tests for runtime, events, metrics, cost.

Covers:
- ExecutionPipeline stub execution
- ExecutionRuntime lifecycle
- Event bus publish / subscribe / unsubscribe
- Event factory methods
- RuntimeMetrics / ProviderMetrics accumulation
- CostTracker recording and summary
- TokenUsage / ExecutionCost models
"""
from __future__ import annotations

import time
import unittest

from iios.ai.foundation.events import (
    AIEventBus, AIEventType,
    SessionStartedEvent, ExecutionCompletedEvent,
    ProviderRegisteredEvent, RetryStartedEvent,
)
from iios.ai.foundation.metrics import (
    RuntimeMetrics, ProviderMetrics, SessionMetrics, ExecutionMetrics,
)
from iios.ai.foundation.cost import (
    TokenUsage, ExecutionCost, CostSummary, CostTracker,
)
from iios.ai.foundation.request import AIRequest, AIExecutionRequest, RequestMetadata
from iios.ai.foundation.runtime import (
    ExecutionPipeline, ExecutionRuntime, ExecutionContext,
)


# ---------------------------------------------------------------------------
# Test: AIEventBus
# ---------------------------------------------------------------------------

class TestAIEventBus(unittest.TestCase):

    def test_subscribe_and_publish(self):
        bus = AIEventBus()
        received = []
        bus.subscribe(AIEventType.SESSION_STARTED, received.append)
        evt = SessionStartedEvent.create(
            source_id="test", session_id="s1", module_id="m1"
        )
        bus.publish(evt)
        self.assertEqual(len(received), 1)
        self.assertIs(received[0], evt)

    def test_unsubscribe(self):
        bus = AIEventBus()
        received = []
        sub_id = bus.subscribe(AIEventType.SESSION_STARTED, received.append)
        bus.unsubscribe(sub_id)
        bus.publish(SessionStartedEvent.create("t", "s", "m"))
        self.assertEqual(len(received), 0)

    def test_multiple_subscribers(self):
        bus = AIEventBus()
        a, b = [], []
        bus.subscribe(AIEventType.EXECUTION_COMPLETED, a.append)
        bus.subscribe(AIEventType.EXECUTION_COMPLETED, b.append)
        bus.publish(ExecutionCompletedEvent.create("t", "r1", "s1", "p1", 10.0))
        self.assertEqual(len(a), 1)
        self.assertEqual(len(b), 1)

    def test_faulty_handler_does_not_break_others(self):
        bus = AIEventBus()
        good = []
        def bad(e): raise ValueError("oops")
        bus.subscribe(AIEventType.PROVIDER_REGISTERED, bad)
        bus.subscribe(AIEventType.PROVIDER_REGISTERED, good.append)
        bus.publish(ProviderRegisteredEvent.create("t", "openai", "gpt-4o"))
        self.assertEqual(len(good), 1)  # good handler still received

    def test_subscriber_count(self):
        bus = AIEventBus()
        bus.subscribe(AIEventType.RETRY_STARTED, lambda e: None)
        bus.subscribe(AIEventType.RETRY_STARTED, lambda e: None)
        self.assertEqual(bus.subscriber_count(AIEventType.RETRY_STARTED), 2)

    def test_clear(self):
        bus = AIEventBus()
        bus.subscribe(AIEventType.SESSION_ENDED, lambda e: None)
        bus.clear()
        self.assertEqual(bus.subscriber_count(), 0)

    def test_event_factories_produce_correct_types(self):
        e = RetryStartedEvent.create("src", "req-1", 1, 3, 1.0)
        self.assertEqual(e.event_type, AIEventType.RETRY_STARTED)
        self.assertEqual(e.attempt, 1)
        self.assertEqual(e.max_attempts, 3)

    def test_event_to_dict(self):
        e = SessionStartedEvent.create("src", "s1", "m1")
        d = e.to_dict()
        self.assertIn("event_id", d)
        self.assertIn("event_type", d)
        self.assertIn("source_id", d)


# ---------------------------------------------------------------------------
# Test: Metrics
# ---------------------------------------------------------------------------

class TestProviderMetrics(unittest.TestCase):

    def test_success_rate(self):
        pm = ProviderMetrics("openai", "gpt-4o")
        pm.record_request(success=True, latency_ms=100.0)
        pm.record_request(success=True, latency_ms=200.0)
        pm.record_request(success=False, latency_ms=50.0)
        self.assertAlmostEqual(pm.success_rate(), 2/3, places=3)
        self.assertAlmostEqual(pm.error_rate(), 1/3, places=3)

    def test_latency_avg(self):
        pm = ProviderMetrics("p", "m")
        pm.record_request(success=True, latency_ms=100.0)
        pm.record_request(success=True, latency_ms=200.0)
        d = pm.to_dict()
        self.assertAlmostEqual(d["avg_latency_ms"], 150.0, places=1)

    def test_to_dict_keys(self):
        pm = ProviderMetrics("p", "m")
        d  = pm.to_dict()
        for key in ("provider_id", "model_id", "requests", "error_rate", "avg_latency_ms"):
            self.assertIn(key, d)


class TestRuntimeMetrics(unittest.TestCase):

    def test_global_accumulation(self):
        rm = RuntimeMetrics()
        rm.record_execution(success=True, latency_ms=50.0)
        rm.record_execution(success=False, latency_ms=10.0)
        d = rm.to_dict()
        self.assertEqual(d["total_requests"], 2)
        self.assertEqual(d["total_failure"], 1)

    def test_provider_metrics_created(self):
        rm = RuntimeMetrics()
        pm = rm.provider_metrics("openai", "gpt-4o")
        pm.record_request(success=True, latency_ms=80.0)
        d = rm.to_dict()
        self.assertIn("openai", d["providers"])


class TestSessionMetrics(unittest.TestCase):

    def test_record_and_dict(self):
        sm = SessionMetrics("sess-1")
        sm.record(success=True, latency_ms=100.0, tokens=50)
        sm.record(success=False, latency_ms=20.0)
        d = sm.to_dict()
        self.assertEqual(d["requests"], 2)
        self.assertEqual(d["total_tokens"], 50)


class TestExecutionMetrics(unittest.TestCase):

    def test_stage_recording(self):
        em = ExecutionMetrics("req-1")
        em.record_stage("validation", 5.0, True)
        em.record_stage("execution", 120.0, True)
        em.complete(succeeded=True, provider_id="openai", total_tokens=100)
        d = em.to_dict()
        self.assertIn("validation", d["stages"])
        self.assertTrue(d["succeeded"])
        self.assertEqual(d["total_tokens"], 100)


# ---------------------------------------------------------------------------
# Test: Cost Framework
# ---------------------------------------------------------------------------

class TestTokenUsage(unittest.TestCase):

    def test_create_sums_tokens(self):
        u = TokenUsage.create(prompt_tokens=100, completion_tokens=50)
        self.assertEqual(u.total_tokens, 150)
        self.assertEqual(u.cached_tokens, 0)

    def test_to_dict(self):
        u = TokenUsage.create(100, 50)
        d = u.to_dict()
        self.assertEqual(d["total_tokens"], 150)

    def test_frozen(self):
        u = TokenUsage.create(10, 5)
        with self.assertRaises((AttributeError, TypeError)):
            u.total_tokens = 999  # type: ignore


class TestExecutionCost(unittest.TestCase):

    def test_create(self):
        usage = TokenUsage.create(100, 50)
        cost  = ExecutionCost.create("openai", "gpt-4o", usage, 0.001, 0.002)
        self.assertAlmostEqual(cost.total_cost_usd, 0.003, places=4)

    def test_to_dict(self):
        usage = TokenUsage.create(100, 50)
        cost  = ExecutionCost.create("openai", "gpt-4o", usage)
        d     = cost.to_dict()
        self.assertIn("execution_id", d)
        self.assertIn("token_usage", d)


class TestCostTracker(unittest.TestCase):

    def _make_cost(self, pid="openai", cost_usd=0.01):
        usage = TokenUsage.create(100, 50)
        return ExecutionCost.create(pid, "gpt-4o", usage, cost_usd / 2, cost_usd / 2)

    def test_record_and_summary(self):
        tracker = CostTracker("sess-1", budget_usd=1.0)
        tracker.record(self._make_cost(cost_usd=0.01))
        tracker.record(self._make_cost(cost_usd=0.02))
        self.assertEqual(tracker.execution_count(), 2)
        self.assertAlmostEqual(tracker.total_cost_usd(), 0.03, places=4)
        summary = tracker.summary()
        self.assertIsInstance(summary, CostSummary)
        self.assertEqual(summary.execution_count, 2)

    def test_over_budget(self):
        tracker = CostTracker("s", budget_usd=0.005)
        tracker.record(self._make_cost(cost_usd=0.01))
        self.assertTrue(tracker.is_over_budget())

    def test_no_budget_never_over(self):
        tracker = CostTracker("s", budget_usd=0.0)
        tracker.record(self._make_cost(cost_usd=999.0))
        self.assertFalse(tracker.is_over_budget())

    def test_per_provider_summary(self):
        tracker = CostTracker("s")
        tracker.record(self._make_cost("openai", 0.01))
        tracker.record(self._make_cost("anthropic", 0.02))
        summary = tracker.summary()
        self.assertIn("openai", summary.by_provider)
        self.assertIn("anthropic", summary.by_provider)


# ---------------------------------------------------------------------------
# Test: ExecutionPipeline (with stub)
# ---------------------------------------------------------------------------

def _make_exec_request(session_id: str = "s1") -> AIExecutionRequest:
    meta = RequestMetadata.create(session_id=session_id, module_id="test")
    req  = AIRequest.create(
        metadata   = meta,
        messages   = [{"role": "user", "content": "hello"}],
        max_tokens = 100,
    )
    return AIExecutionRequest(request=req)


class TestExecutionPipeline(unittest.TestCase):

    def test_stub_pipeline_succeeds(self):
        pipeline = ExecutionPipeline()
        response, ctx = pipeline.run(_make_exec_request())
        self.assertTrue(response.succeeded)
        self.assertIn("stub", response.content)

    def test_empty_messages_aborts(self):
        meta = RequestMetadata.create(session_id="s", module_id="t")
        req  = AIRequest.create(meta, [], max_tokens=100)
        er   = AIExecutionRequest(request=req)
        pipeline = ExecutionPipeline()
        response, ctx = pipeline.run(er)
        self.assertFalse(response.succeeded)

    def test_stage_names(self):
        pipeline = ExecutionPipeline()
        names = pipeline.stage_names()
        self.assertIn("validation", names)
        self.assertIn("execution", names)
        self.assertIn("response", names)
        self.assertEqual(len(names), 8)

    def test_custom_stage_appended(self):
        from iios.ai.foundation.runtime import RuntimePipelineStage
        class MyStage(RuntimePipelineStage):
            name = "custom"
            def execute(self, ctx): ctx.set("custom_ran", True)
        pipeline = ExecutionPipeline()
        pipeline.add_stage(MyStage())
        self.assertIn("custom", pipeline.stage_names())

    def test_event_bus_receives_events(self):
        bus = AIEventBus()
        received = []
        bus.subscribe(AIEventType.EXECUTION_COMPLETED, received.append)
        pipeline = ExecutionPipeline(event_bus=bus)
        pipeline.run(_make_exec_request())
        self.assertEqual(len(received), 1)


# ---------------------------------------------------------------------------
# Test: ExecutionRuntime lifecycle
# ---------------------------------------------------------------------------

class TestExecutionRuntime(unittest.TestCase):

    def test_lifecycle(self):
        runtime = ExecutionRuntime()
        runtime.initialize()
        runtime.start()
        self.assertTrue(runtime.is_ai_running)
        response, ctx = runtime.execute(_make_exec_request())
        self.assertTrue(response.succeeded)
        runtime.stop()
        self.assertFalse(runtime.is_ai_running)

    def test_status_dict(self):
        runtime = ExecutionRuntime()
        runtime.initialize()
        runtime.start()
        status = runtime.status()
        self.assertIn("stage_names", status)
        self.assertIn("metrics", status)
        runtime.stop()


if __name__ == "__main__":
    unittest.main()
