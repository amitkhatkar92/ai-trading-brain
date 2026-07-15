"""tests/unit/investment/decision/integration/test_engine.py
Tests for DecisionIntelligenceIntegrationEngine — full lifecycle and query API.
"""
from __future__ import annotations

import asyncio
import pytest

from iios.investment.decision.integration.decision_intelligence_integration_engine import (
    DecisionIntelligenceIntegrationEngine,
)
from iios.investment.decision.integration.decision_snapshot import DecisionIntelligenceSnapshot
from iios.investment.decision.integration.integration_constants import (
    IntegrationStatus,
    SnapshotStatus,
)


def _run(engine, pipeline):
    did, sid, ev, rs, cs, ri, ex, cm = pipeline
    return engine.integrate_sync(
        decision_id=did + "_DEC", subject_id=sid, subject_type="equity",
        evidence=ev, reasoning=rs, confidence=cs, risk=ri,
        explanation=ex, committee=cm,
    )


class TestEngineLifecycle:
    def test_start_stop(self):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        assert eng.health().integration_status == IntegrationStatus.READY
        eng.stop()
        assert eng.health().integration_status == IntegrationStatus.STOPPED

    def test_double_start_raises(self):
        """Lifecycle framework raises on duplicate start."""
        from iios.investment.workflow.engine_lifecycle import EngineAlreadyRunningError
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        with pytest.raises(EngineAlreadyRunningError):
            eng.start()
        eng.stop()

    def test_stop_without_start_raises(self):
        """Lifecycle framework raises when stopping a non-running engine."""
        from iios.investment.workflow.engine_lifecycle import EngineNotRunningError
        eng = DecisionIntelligenceIntegrationEngine()
        with pytest.raises(EngineNotRunningError):
            eng.stop()

    def test_run_before_start_raises(self, _rich_pipeline):
        eng = DecisionIntelligenceIntegrationEngine()
        with pytest.raises(RuntimeError):
            did, sid, ev, *_ = _rich_pipeline
            eng.integrate_sync(did, sid, "equity", evidence=ev)

    def test_run_after_stop_raises(self, _rich_pipeline):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        eng.stop()
        with pytest.raises(RuntimeError):
            did, sid, ev, *_ = _rich_pipeline
            eng.integrate_sync(did, sid, "equity", evidence=ev)


class TestEngineSyncAPI:
    def test_returns_snapshot(self, _rich_pipeline):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            snap = _run(eng, _rich_pipeline)
            assert isinstance(snap, DecisionIntelligenceSnapshot)
        finally:
            eng.stop()

    def test_complete_snapshot_on_rich_data(self, _rich_pipeline):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            snap = _run(eng, _rich_pipeline)
            assert snap.snapshot_status == SnapshotStatus.COMPLETE
        finally:
            eng.stop()

    def test_partial_snapshot_with_only_evidence(self, _rich_pipeline):
        did, sid, ev, *_ = _rich_pipeline
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            snap = eng.integrate_sync(did+"_P", sid, "equity", evidence=ev)
            assert snap.snapshot_status == SnapshotStatus.PARTIAL
        finally:
            eng.stop()

    def test_stats_increment(self, _rich_pipeline):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            _run(eng, _rich_pipeline)
            _run(eng, _rich_pipeline)
            assert eng.stats().total_integrations >= 2
        finally:
            eng.stop()

    def test_health_healthy_after_success(self, _rich_pipeline):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            _run(eng, _rich_pipeline)
            assert eng.health().is_healthy
        finally:
            eng.stop()


class TestEngineQueryAPI:
    def test_get_snapshot_by_id(self, _rich_pipeline):
        did, sid, *_ = _rich_pipeline
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            snap = _run(eng, _rich_pipeline)
            found = eng.get_snapshot(snap.decision_id)
            assert found is not None
            assert found.snapshot_id == snap.snapshot_id
        finally:
            eng.stop()

    def test_get_snapshot_missing_returns_none(self):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            assert eng.get_snapshot("nonexistent") is None
        finally:
            eng.stop()

    def test_recent_snapshots(self, _rich_pipeline):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            _run(eng, _rich_pipeline)
            recent = eng.recent_snapshots(10)
            assert len(recent) >= 1
        finally:
            eng.stop()

    def test_known_decisions(self, _rich_pipeline):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            snap = _run(eng, _rich_pipeline)
            assert snap.decision_id in eng.known_decisions()
        finally:
            eng.stop()

    def test_intelligence_score_series(self, _rich_pipeline):
        did, sid, *_ = _rich_pipeline
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            _run(eng, _rich_pipeline)
            series = eng.intelligence_score_series(sid)
            assert len(series) >= 1
        finally:
            eng.stop()

    def test_quality_stats(self, _rich_pipeline):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            _run(eng, _rich_pipeline)
            qs = eng.quality_stats()
            assert qs.total_evaluations >= 1
        finally:
            eng.stop()

    def test_get_validation_report(self, _rich_pipeline):
        did, sid, ev, *_ = _rich_pipeline
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            eng.submit_evidence(ev)
            rep = eng.get_validation_report(ev.decision_id)
            assert rep is not None
        finally:
            eng.stop()

    def test_get_conflict_report(self, _rich_pipeline):
        did, sid, ev, *_ = _rich_pipeline
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            eng.submit_evidence(ev)
            rep = eng.get_conflict_report(ev.decision_id)
            assert rep is not None
        finally:
            eng.stop()


class TestEngineAsyncAPI:
    def test_async_returns_snapshot(self, _rich_pipeline):
        did, sid, ev, rs, cs, ri, ex, cm = _rich_pipeline
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            snap = asyncio.run(
                eng.integrate(
                    decision_id=did + "_ASYNC", subject_id=sid, subject_type="equity",
                    evidence=ev, reasoning=rs, confidence=cs, risk=ri,
                    explanation=ex, committee=cm,
                )
            )
            assert isinstance(snap, DecisionIntelligenceSnapshot)
        finally:
            eng.stop()

    def test_async_increments_stats(self, _rich_pipeline):
        did, sid, ev, rs, cs, ri, ex, cm = _rich_pipeline
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            asyncio.run(
                eng.integrate(
                    did + "_ASYNC2", sid, "equity",
                    evidence=ev, reasoning=rs, confidence=cs,
                    risk=ri, explanation=ex, committee=cm,
                )
            )
            assert eng.stats().total_integrations >= 1
        finally:
            eng.stop()


class TestEngineStatistics:
    def test_initial_zero(self):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            assert eng.stats().total_integrations == 0
        finally:
            eng.stop()

    def test_success_rate_after_runs(self, _rich_pipeline):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            _run(eng, _rich_pipeline)
            _run(eng, _rich_pipeline)
            assert eng.stats().success_rate > 0.0
        finally:
            eng.stop()

    def test_stats_to_dict(self, _rich_pipeline):
        eng = DecisionIntelligenceIntegrationEngine()
        eng.start()
        try:
            _run(eng, _rich_pipeline)
            d = eng.stats().to_dict()
            assert "total_integrations" in d
            assert "success_rate"       in d
        finally:
            eng.stop()
