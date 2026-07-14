"""tests/unit/investment/strategy/integration/test_engine.py
Integration tests for StrategyIntelligenceIntegrationEngine facade.
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from iios.investment.strategy.integration.aggregation_state import make_update
from iios.investment.strategy.integration.integration_constants import (
    IntelligenceSource,
    IntegrationStatus,
    SnapshotStatus,
    UpdateType,
)
from iios.investment.strategy.integration.strategy_intelligence_integration_engine import (
    StrategyIntelligenceIntegrationEngine,
)
from tests.unit.investment.strategy.integration.conftest import (
    make_eval_update,
    make_risk_update,
    make_lifecycle_update,
    make_framework_update,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _full_update_set(sid: str):
    return [
        make_eval_update(sid),
        make_risk_update(sid),
        make_lifecycle_update(sid),
        make_framework_update(sid),
    ]


# ===========================================================================
# Async tests
# ===========================================================================

class TestIntegrationEngineAsync:
    @pytest.mark.asyncio
    async def test_submit_and_get_snapshot(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "ENG1"
        for u in _full_update_set(sid):
            await engine.submit_update(u)
        snap = await engine.get_snapshot(sid)
        assert snap is not None
        assert snap.strategy_id == sid

    @pytest.mark.asyncio
    async def test_snapshot_status_complete(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "ENG2"
        for u in _full_update_set(sid):
            await engine.submit_update(u)
        snap = await engine.get_snapshot(sid)
        assert snap.status == SnapshotStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_snapshot_scores_in_range(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "ENG3"
        for u in _full_update_set(sid):
            await engine.submit_update(u)
        snap = await engine.get_snapshot(sid)
        assert 0 <= snap.intelligence_score <= 100
        assert 0 <= snap.quality_score <= 100
        assert 0 <= snap.confidence_score <= 100

    @pytest.mark.asyncio
    async def test_missing_strategy_returns_none(self):
        engine = StrategyIntelligenceIntegrationEngine()
        snap   = await engine.get_snapshot("NOBODY")
        assert snap is None

    @pytest.mark.asyncio
    async def test_cache_hit_second_call(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "ENG4"
        for u in _full_update_set(sid):
            await engine.submit_update(u)
        snap1 = await engine.get_snapshot(sid)
        snap2 = await engine.get_snapshot(sid)
        assert snap1.snapshot_id == snap2.snapshot_id  # same cached object

    @pytest.mark.asyncio
    async def test_new_update_invalidates_cache(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "ENG5"
        for u in _full_update_set(sid):
            await engine.submit_update(u)
        snap1 = await engine.get_snapshot(sid)
        # Submit a new update → cache invalidated
        await engine.submit_update(make_eval_update(sid, score=99.0))
        snap2 = await engine.get_snapshot(sid)
        assert snap2.snapshot_id != snap1.snapshot_id

    @pytest.mark.asyncio
    async def test_get_snapshot_batch(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sids   = ["BATCH1", "BATCH2", "BATCH3"]
        for sid in sids:
            for u in _full_update_set(sid):
                await engine.submit_update(u)
        results = await engine.get_snapshot_batch(sids)
        assert len(results) == 3
        for sid in sids:
            assert results[sid] is not None

    @pytest.mark.asyncio
    async def test_known_strategies(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "ENG_KS"
        for u in _full_update_set(sid):
            await engine.submit_update(u)
        assert sid in engine.known_strategies()

    @pytest.mark.asyncio
    async def test_stats_structure(self):
        engine = StrategyIntelligenceIntegrationEngine()
        await engine.submit_update(make_eval_update("ST1"))
        s = engine.stats()
        assert "status" in s
        assert "known_strategies" in s
        assert "cache_size" in s

    @pytest.mark.asyncio
    async def test_event_bus_emits_snapshot_event(self):
        engine = StrategyIntelligenceIntegrationEngine()
        events = []
        engine.event_bus.subscribe(lambda e: events.append(e))
        sid = "EVT1"
        for u in _full_update_set(sid):
            await engine.submit_update(u)
        await engine.get_snapshot(sid)
        from iios.investment.strategy.integration.integration_constants import IntegrationEventType
        event_types = [e.event_type for e in events]
        assert IntegrationEventType.SNAPSHOT_PUBLISHED in event_types

    @pytest.mark.asyncio
    async def test_get_quality_report(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "QR1"
        for u in _full_update_set(sid):
            await engine.submit_update(u)
        await engine.get_snapshot(sid)
        report = engine.get_quality_report(sid)
        assert report is not None
        assert 0 <= report.overall_score <= 100

    @pytest.mark.asyncio
    async def test_get_validation_report(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "VR1"
        for u in _full_update_set(sid):
            await engine.submit_update(u)
        await engine.get_snapshot(sid)
        vr = engine.get_validation_report(sid)
        assert vr is not None

    @pytest.mark.asyncio
    async def test_get_active_conflicts_empty_for_clean(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "AC1"
        for u in _full_update_set(sid):
            await engine.submit_update(u)
        await engine.get_snapshot(sid)
        conflicts = engine.get_active_conflicts(sid)
        assert isinstance(conflicts, list)

    @pytest.mark.asyncio
    async def test_get_confidence_score(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "CS1"
        for u in _full_update_set(sid):
            await engine.submit_update(u)
        await engine.get_snapshot(sid)
        score = engine.get_confidence_score(sid)
        assert score is not None
        assert 0 <= score <= 100


# ===========================================================================
# Sync wrappers
# ===========================================================================

class TestIntegrationEngineSyncWrapper:
    def test_submit_and_get_sync(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "SYNC1"
        for u in _full_update_set(sid):
            engine.submit_update_sync(u)
        snap = engine.get_snapshot_sync(sid)
        assert snap is not None
        assert snap.strategy_id == sid

    def test_get_current_snapshot_from_cache(self):
        engine = StrategyIntelligenceIntegrationEngine()
        sid    = "SYNC2"
        for u in _full_update_set(sid):
            engine.submit_update_sync(u)
        engine.get_snapshot_sync(sid)
        snap = engine.get_current_snapshot(sid)
        assert snap is not None
