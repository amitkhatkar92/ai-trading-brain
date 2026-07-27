"""
test_provider_runtime.py -- tests for the A1 Provider Runtime

Covers:
- Provider registration and capability lookup
- ProviderResolver and ProviderSelector
- AIProviderRuntime lifecycle
- ProviderManager health probes and events
"""
from __future__ import annotations

import time
import unittest
from typing import Any, Dict, List, Optional, Sequence

from iios.ai.foundation.provider import (
    AIProviderCapabilities,
    AIProviderExtension,
    AIProviderRuntime,
    ProviderCapabilityType,
    ProviderManager,
    ProviderRegistry,
    ProviderResolver,
    ProviderSelector,
    ProviderSelectionStrategy,
    ProviderStatus,
    ProviderTier,
    ProviderProfile,
)
from iios.ai.foundation.events import AIEventBus, AIEventType, ProviderRegisteredEvent


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

def _caps(provider_id: str, model_id: str, caps: set) -> AIProviderCapabilities:
    return AIProviderCapabilities(
        provider_id    = provider_id,
        model_id       = model_id,
        capabilities   = frozenset(caps),
        context_window = 4096,
        max_output     = 1024,
        tier           = ProviderTier.STANDARD,
    )


class StubProvider(AIProviderExtension):
    def __init__(self, pid: str, healthy: bool = True):
        self._pid     = pid
        self._healthy = healthy
        self._caps    = _caps(pid, f"{pid}-model",
                              {ProviderCapabilityType.CHAT, ProviderCapabilityType.COMPLETION})

    @property
    def provider_id(self) -> str:
        return self._pid

    @property
    def capabilities(self) -> AIProviderCapabilities:
        return self._caps

    def complete(self, messages, *, max_tokens, temperature, timeout_s, options=None):
        return {"content": "stub", "finish_reason": "stop", "usage": {}}

    def embed(self, texts, *, timeout_s):
        return [[0.1, 0.2] for _ in texts]

    def health_check(self) -> Dict[str, Any]:
        return {"healthy": self._healthy, "latency_ms": 1.0}

    def tokenise(self, text: str) -> List[int]:
        return list(range(len(text.split())))


class EmbeddingProvider(StubProvider):
    def __init__(self):
        super().__init__("embed-provider")
        self._caps = _caps(
            "embed-provider", "embed-model",
            {ProviderCapabilityType.EMBEDDING},
        )


# ---------------------------------------------------------------------------
# Test: ProviderCapabilities
# ---------------------------------------------------------------------------

class TestProviderCapabilities(unittest.TestCase):

    def test_supports_single(self):
        caps = _caps("p1", "m1", {ProviderCapabilityType.CHAT})
        self.assertTrue(caps.supports(ProviderCapabilityType.CHAT))
        self.assertFalse(caps.supports(ProviderCapabilityType.EMBEDDING))

    def test_supports_all(self):
        caps = _caps("p1", "m1", {ProviderCapabilityType.CHAT, ProviderCapabilityType.EMBEDDING})
        self.assertTrue(caps.supports_all(ProviderCapabilityType.CHAT, ProviderCapabilityType.EMBEDDING))
        self.assertFalse(caps.supports_all(ProviderCapabilityType.CHAT, ProviderCapabilityType.VISION))

    def test_to_dict(self):
        caps = _caps("p1", "m1", {ProviderCapabilityType.CHAT})
        d    = caps.to_dict()
        self.assertEqual(d["provider_id"], "p1")
        self.assertIn("chat", d["capabilities"])

    def test_frozen(self):
        caps = _caps("p1", "m1", {ProviderCapabilityType.CHAT})
        with self.assertRaises((AttributeError, TypeError)):
            caps.provider_id = "x"  # type: ignore


# ---------------------------------------------------------------------------
# Test: ProviderRegistry
# ---------------------------------------------------------------------------

class TestProviderRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = ProviderRegistry()

    def test_register_and_get(self):
        p = StubProvider("openai")
        self.registry.register(p, activate=True)
        result = self.registry.get("openai")
        self.assertIs(result, p)

    def test_deregister(self):
        p = StubProvider("openai")
        self.registry.register(p)
        self.registry.deregister("openai")
        self.assertIsNone(self.registry.get("openai"))

    def test_find_for_capability(self):
        self.registry.register(StubProvider("openai"), activate=True)
        self.registry.register(EmbeddingProvider(), activate=True)
        chat = self.registry.find_for_capability(ProviderCapabilityType.CHAT)
        emb  = self.registry.find_for_capability(ProviderCapabilityType.EMBEDDING)
        self.assertEqual(len(chat), 1)
        self.assertEqual(chat[0].provider_id, "openai")
        self.assertEqual(len(emb), 1)
        self.assertEqual(emb[0].provider_id, "embed-provider")

    def test_active_only_excludes_unavailable(self):
        self.registry.register(StubProvider("bad"), activate=True)
        self.registry.set_status("bad", ProviderStatus.UNAVAILABLE)
        found = self.registry.find_for_capability(ProviderCapabilityType.CHAT, active_only=True)
        self.assertEqual(len(found), 0)

    def test_count(self):
        self.registry.register(StubProvider("a"))
        self.registry.register(StubProvider("b"))
        self.assertEqual(self.registry.count(), 2)

    def test_all_profiles(self):
        self.registry.register(StubProvider("x"))
        profiles = self.registry.all_profiles()
        self.assertEqual(len(profiles), 1)
        self.assertIsInstance(profiles[0], ProviderProfile)


# ---------------------------------------------------------------------------
# Test: ProviderResolver
# ---------------------------------------------------------------------------

class TestProviderResolver(unittest.TestCase):

    def setUp(self):
        self.registry = ProviderRegistry()
        self.registry.register(StubProvider("p1"), activate=True)
        self.registry.register(EmbeddingProvider(), activate=True)
        self.resolver = ProviderResolver(self.registry)

    def test_resolve_chat(self):
        results = self.resolver.resolve(ProviderCapabilityType.CHAT)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].provider_id, "p1")

    def test_resolve_first(self):
        first = self.resolver.resolve_first(ProviderCapabilityType.CHAT)
        self.assertIsNotNone(first)
        self.assertEqual(first.provider_id, "p1")

    def test_can_serve(self):
        self.assertTrue(self.resolver.can_serve(ProviderCapabilityType.CHAT))
        self.assertFalse(self.resolver.can_serve(ProviderCapabilityType.VISION))

    def test_resolve_none(self):
        result = self.resolver.resolve_first(ProviderCapabilityType.AUDIO)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Test: ProviderSelector
# ---------------------------------------------------------------------------

class TestProviderSelector(unittest.TestCase):

    def _providers(self, n):
        return [StubProvider(f"p{i}") for i in range(n)]

    def test_first_available_selects_first(self):
        sel = ProviderSelector(ProviderSelectionStrategy.FIRST_AVAILABLE)
        providers = self._providers(3)
        chosen = sel.select(ProviderCapabilityType.CHAT, providers)
        self.assertIs(chosen, providers[0])

    def test_round_robin_rotates(self):
        sel = ProviderSelector(ProviderSelectionStrategy.ROUND_ROBIN)
        providers = self._providers(3)
        cap = ProviderCapabilityType.CHAT
        results = [sel.select(cap, providers) for _ in range(6)]
        ids = [r.provider_id for r in results]
        # Should have all 3 represented across 6 calls
        self.assertIn("p0", ids)
        self.assertIn("p1", ids)
        self.assertIn("p2", ids)

    def test_select_empty_returns_none(self):
        sel = ProviderSelector()
        self.assertIsNone(sel.select(ProviderCapabilityType.CHAT, []))


# ---------------------------------------------------------------------------
# Test: ProviderManager (event emission)
# ---------------------------------------------------------------------------

class TestProviderManager(unittest.TestCase):

    def test_register_emits_event(self):
        bus      = AIEventBus()
        registry = ProviderRegistry()
        manager  = ProviderManager(registry, bus)
        received = []
        bus.subscribe(AIEventType.PROVIDER_REGISTERED, received.append)
        manager.register(StubProvider("openai"))
        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], ProviderRegisteredEvent)
        self.assertEqual(received[0].provider_id, "openai")

    def test_deregister_emits_event(self):
        bus      = AIEventBus()
        registry = ProviderRegistry()
        manager  = ProviderManager(registry, bus)
        manager.register(StubProvider("openai"))
        deregistered = []
        bus.subscribe(AIEventType.PROVIDER_DEREGISTERED, deregistered.append)
        manager.deregister("openai")
        self.assertEqual(len(deregistered), 1)

    def test_health_probe_marks_unavailable(self):
        bus      = AIEventBus()
        registry = ProviderRegistry()
        manager  = ProviderManager(registry, bus)
        manager.register(StubProvider("bad", healthy=False))
        healthy = manager.probe_health("bad")
        self.assertFalse(healthy)
        self.assertEqual(registry.get_status("bad"), ProviderStatus.DEGRADED)


# ---------------------------------------------------------------------------
# Test: AIProviderRuntime lifecycle
# ---------------------------------------------------------------------------

class TestAIProviderRuntime(unittest.TestCase):

    def test_lifecycle(self):
        runtime = AIProviderRuntime()
        runtime.initialize()
        runtime.start()
        self.assertTrue(runtime.is_ai_running)
        profile = runtime.register_provider(StubProvider("openai"))
        self.assertEqual(profile.provider_id, "openai")
        self.assertTrue(runtime.can_serve(ProviderCapabilityType.CHAT))
        provider = runtime.select_provider(ProviderCapabilityType.CHAT)
        self.assertIsNotNone(provider)
        self.assertEqual(provider.provider_id, "openai")
        runtime.stop()
        self.assertFalse(runtime.is_ai_running)

    def test_status_dict(self):
        runtime = AIProviderRuntime()
        runtime.initialize()
        runtime.start()
        runtime.register_provider(StubProvider("a"))
        status = runtime.status()
        self.assertIn("provider_count", status)
        self.assertEqual(status["provider_count"], 1)
        runtime.stop()

    def test_deregister(self):
        runtime = AIProviderRuntime()
        runtime.initialize()
        runtime.start()
        runtime.register_provider(StubProvider("temp"))
        runtime.deregister_provider("temp")
        self.assertFalse(runtime.can_serve(ProviderCapabilityType.CHAT))
        runtime.stop()


if __name__ == "__main__":
    unittest.main()
