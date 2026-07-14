"""tests/unit/investment/decision/evidence/test_engine.py"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from iios.investment.decision.evidence.evidence_collection_engine import EvidenceCollectionEngine
from iios.investment.decision.evidence.evidence_constants import (
    EvidenceEngineStatus, EvidenceSourceType, EvidenceValidationStatus,
)
from iios.investment.decision.evidence.provider_registry import ProviderRegistry


# ========================= Helpers =======================================

def _engine_with_providers(*providers) -> EvidenceCollectionEngine:
    reg = ProviderRegistry()
    for p in providers:
        reg.register(p)
    engine = EvidenceCollectionEngine(registry=reg)
    engine.start()
    return engine


# ========================= Lifecycle =====================================

class TestEngineLifecycle:
    def test_initial_status_is_initializing(self):
        eng = EvidenceCollectionEngine()
        assert eng.status == EvidenceEngineStatus.INITIALIZING

    def test_start_makes_ready(self):
        eng = EvidenceCollectionEngine()
        eng.start()
        assert eng.status == EvidenceEngineStatus.READY

    def test_stop(self):
        eng = EvidenceCollectionEngine()
        eng.start()
        eng.stop()
        assert eng.status == EvidenceEngineStatus.STOPPED

    def test_collect_when_not_started_raises(self, decision_id, subject_id, subject_type):
        eng = EvidenceCollectionEngine()  # not started
        with pytest.raises(RuntimeError):
            eng.collect_sync(decision_id, subject_id, subject_type)


# ========================= Collection ====================================

@pytest.mark.asyncio
class TestEngineCollection:
    async def test_empty_registry_returns_snapshot(self, decision_id, subject_id, subject_type):
        eng  = _engine_with_providers()
        snap = await eng.collect(decision_id, subject_id, subject_type, payloads={})
        assert snap is not None
        assert snap.decision_id == decision_id
        assert snap.item_count  == 0

    async def test_with_one_provider(self, stub_market_provider, market_item,
                                     decision_id, subject_id, subject_type):
        eng  = _engine_with_providers(stub_market_provider)
        snap = await eng.collect(decision_id, subject_id, subject_type)
        assert snap.item_count >= 1

    async def test_with_two_providers(self, stub_market_provider, stub_risk_provider,
                                      market_item, risk_item,
                                      decision_id, subject_id, subject_type):
        eng  = _engine_with_providers(stub_market_provider, stub_risk_provider)
        snap = await eng.collect(decision_id, subject_id, subject_type)
        assert snap.item_count >= 2

    async def test_snapshot_has_quality_score(self, stub_market_provider, stub_risk_provider,
                                              decision_id, subject_id, subject_type):
        eng  = _engine_with_providers(stub_market_provider, stub_risk_provider)
        snap = await eng.collect(decision_id, subject_id, subject_type)
        assert 0.0 <= snap.quality_score <= 100.0

    async def test_snapshot_stored_in_history(self, stub_market_provider,
                                              decision_id, subject_id, subject_type):
        eng  = _engine_with_providers(stub_market_provider)
        snap = await eng.collect(decision_id, subject_id, subject_type)
        retrieved = eng.get_snapshot(snap.snapshot_id)
        assert retrieved is snap

    async def test_get_latest(self, stub_market_provider, decision_id, subject_id, subject_type):
        eng = _engine_with_providers(stub_market_provider)
        await eng.collect(decision_id, subject_id, subject_type)
        latest = eng.get_latest(subject_id)
        assert latest is not None

    async def test_version_increments(self, stub_market_provider, decision_id, subject_id, subject_type):
        eng = _engine_with_providers(stub_market_provider)
        s1  = await eng.collect(decision_id, subject_id, subject_type)
        s2  = await eng.collect(str(uuid.uuid4()), subject_id, subject_type)
        assert s2.version > s1.version

    async def test_payload_injected_to_provider(self, decision_id, subject_type):
        """Provider with real payload extracts items from it."""
        from iios.investment.decision.evidence.market_evidence import MarketEvidenceProvider
        reg = ProviderRegistry()
        reg.register(MarketEvidenceProvider())
        eng = EvidenceCollectionEngine(registry=reg)
        eng.start()
        payloads = {"market": {"last_price": 2100.0, "volume": 500_000, "rsi_14": 55.0}}
        snap = await eng.collect(decision_id, "WIPRO", "equity",
                                 payloads=payloads)
        assert snap.item_count >= 1

    async def test_provider_failure_is_non_fatal(self, decision_id, subject_id, subject_type,
                                                  StubProvider):
        """A provider that throws must not abort collection."""
        from iios.investment.decision.evidence.evidence_provider import BaseEvidenceProvider
        from iios.investment.decision.evidence.evidence_item import EvidenceItem
        from typing import List, Optional, Dict, Any

        class BrokenProvider(BaseEvidenceProvider):
            @property
            def source_type(self): return EvidenceSourceType.EXTERNAL
            @property
            def provider_name(self): return "BrokenProvider"
            def collect(self, *a, **kw) -> List[EvidenceItem]:
                raise RuntimeError("deliberate failure")

        reg = ProviderRegistry()
        reg.register(BrokenProvider())
        eng = EvidenceCollectionEngine(registry=reg)
        eng.start()
        snap = await eng.collect(decision_id, subject_id, subject_type)
        assert snap is not None  # must survive the failure


# ========================= Sync wrapper ==================================

class TestCollectSync:
    def test_collect_sync(self, stub_market_provider, decision_id, subject_id, subject_type):
        eng  = _engine_with_providers(stub_market_provider)
        snap = eng.collect_sync(decision_id, subject_id, subject_type)
        assert snap.decision_id == decision_id


# ========================= Stats & Query =================================

class TestEngineQuery:
    def test_stats(self, stub_market_provider, decision_id, subject_id, subject_type):
        eng = _engine_with_providers(stub_market_provider)
        eng.collect_sync(decision_id, subject_id, subject_type)
        s = eng.stats()
        assert "status" in s
        assert "registry" in s
        assert "evidence" in s

    def test_get_events(self, stub_market_provider, decision_id, subject_id, subject_type):
        eng = _engine_with_providers(stub_market_provider)
        eng.collect_sync(decision_id, subject_id, subject_type)
        events = eng.get_events(decision_id)
        assert len(events) >= 1

    def test_get_history_for_subject(self, stub_market_provider, decision_id, subject_id, subject_type):
        eng = _engine_with_providers(stub_market_provider)
        eng.collect_sync(decision_id, subject_id, subject_type)
        snapshots = eng.get_history(subject_id)
        assert len(snapshots) >= 1
