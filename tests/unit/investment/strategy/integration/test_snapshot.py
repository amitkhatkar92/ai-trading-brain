"""tests/unit/investment/strategy/integration/test_snapshot.py
Tests for StrategySnapshot, SnapshotCache, StrategySummary, StrategyState,
StrategyStatisticsTracker.
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.integration.aggregation_engine import AggregationEngine
from iios.investment.strategy.integration.aggregation_state import make_update
from iios.investment.strategy.integration.conflict_classifier import Conflict, ConflictClassifier
from iios.investment.strategy.integration.conflict_engine import ConflictEngine
from iios.investment.strategy.integration.consistency_validator import ConsistencyValidator
from iios.investment.strategy.integration.integration_constants import (
    ConflictSeverity,
    ConflictType,
    IntelligenceSource,
    ResolutionStrategy,
    SnapshotStatus,
    ValidationStatus,
)
from iios.investment.strategy.integration.snapshot_cache import SnapshotCache
from iios.investment.strategy.integration.strategy_snapshot import build_snapshot
from iios.investment.strategy.integration.strategy_statistics import StrategyStatisticsTracker
from iios.investment.strategy.integration.strategy_summary import build_strategy_summary
from iios.investment.strategy.integration.strategy_confidence import ConfidenceCalculator
from iios.investment.strategy.integration.strategy_quality import QualityFramework
from iios.investment.strategy.integration.validation_report import build_validation_report
from tests.unit.investment.strategy.integration.conftest import (
    make_eval_update,
    make_risk_update,
    make_lifecycle_update,
    make_framework_update,
    make_full_state,
)


def _make_full_snapshot(sid: str = "SS1"):
    sid, state, eng = make_full_state(sid)
    validation = build_validation_report(sid, [], completeness=1.0)
    summary    = build_strategy_summary(state, 80.0, 1.0, active_conflicts=0)
    snapshot   = build_snapshot(
        state=state,
        summary=summary,
        validation_report=validation,
        active_conflicts=[],
        intelligence_score=80.0,
        quality_score=75.0,
        confidence_score=78.0,
        freshness_score=0.95,
    )
    return snapshot


# ===========================================================================
# StrategySummary
# ===========================================================================

class TestStrategySummary:
    def test_build_returns_summary(self):
        sid, state, eng = make_full_state("SUM1")
        summary = build_strategy_summary(state, 80.0, 1.0)
        assert summary.strategy_id == sid
        assert 0 <= summary.overall_score <= 100

    def test_intelligence_gaps_for_partial_state(self):
        eng = AggregationEngine()
        sid = "GAP1"
        eng.apply(make_eval_update(sid))
        state = eng.get_state(sid)
        summary = build_strategy_summary(state, 50.0, 0.3)
        # LIFECYCLE, RISK, STRATEGY_FRAMEWORK are required but missing
        assert len(summary.intelligence_gaps) > 0

    def test_to_dict_keys(self):
        sid, state, eng = make_full_state("SUM2")
        s = build_strategy_summary(state, 70.0, 0.9)
        d = s.to_dict()
        assert "strategy_id" in d
        assert "overall_score" in d
        assert "intelligence_gaps" in d


# ===========================================================================
# StrategySnapshot (build_snapshot)
# ===========================================================================

class TestStrategySnapshot:
    def test_complete_status_on_good_data(self):
        snap = _make_full_snapshot("SNAP1")
        assert snap.status == SnapshotStatus.COMPLETE

    def test_invalid_status_on_validation_failure(self):
        from datetime import datetime, timezone
        from iios.investment.strategy.integration.consistency_rules import RuleCheckResult
        sid, state, eng = make_full_state("SNAP2")
        crit = RuleCheckResult(
            rule_id="R001", rule_name="t", passed=False,
            conflict_type=ConflictType.EVALUATION_VS_RISK,
            severity=ConflictSeverity.CRITICAL,
            description="crit",
            source_a=IntelligenceSource.EVALUATION,
            source_b=IntelligenceSource.RISK,
            checked_at=datetime.now(timezone.utc),
        )
        validation = build_validation_report(sid, [crit], completeness=1.0)
        summary    = build_strategy_summary(state, 70.0, 1.0)
        snap = build_snapshot(
            state=state,
            summary=summary,
            validation_report=validation,
            active_conflicts=[],
            intelligence_score=70.0,
            quality_score=70.0,
            confidence_score=70.0,
            freshness_score=0.95,
        )
        assert snap.status == SnapshotStatus.INVALID

    def test_partial_status_on_low_completeness(self):
        eng = AggregationEngine()
        sid = "SNAP3"
        eng.apply(make_eval_update(sid))
        state = eng.get_state(sid)
        validation = build_validation_report(sid, [], completeness=0.3)
        summary    = build_strategy_summary(state, 50.0, 0.3)
        snap = build_snapshot(
            state=state,
            summary=summary,
            validation_report=validation,
            active_conflicts=[],
            intelligence_score=50.0,
            quality_score=50.0,
            confidence_score=50.0,
            freshness_score=0.9,
        )
        assert snap.status == SnapshotStatus.PARTIAL

    def test_to_dict_completeness(self):
        snap = _make_full_snapshot("SNAP4")
        d = snap.to_dict()
        assert "snapshot_id" in d
        assert "strategy_id" in d
        assert "intelligence_score" in d
        assert "status" in d

    def test_sources_present(self):
        snap = _make_full_snapshot("SNAP5")
        assert len(snap.sources_present) == 4


# ===========================================================================
# SnapshotCache
# ===========================================================================

class TestSnapshotCache:
    def test_set_and_get(self):
        cache = SnapshotCache()
        snap  = _make_full_snapshot("CACHE1")
        cache.set(snap)
        assert cache.get("CACHE1") is snap

    def test_get_missing_returns_none(self):
        cache = SnapshotCache()
        assert cache.get("MISSING") is None

    def test_invalidate_removes(self):
        cache = SnapshotCache()
        snap  = _make_full_snapshot("INV1")
        cache.set(snap)
        cache.invalidate("INV1")
        assert cache.get("INV1") is None

    def test_size(self):
        cache = SnapshotCache()
        cache.set(_make_full_snapshot("SZ1"))
        cache.set(_make_full_snapshot("SZ2"))
        assert cache.size() == 2

    def test_known_strategies(self):
        cache = SnapshotCache()
        cache.set(_make_full_snapshot("KS1"))
        assert "KS1" in cache.known_strategies()

    def test_clear(self):
        cache = SnapshotCache()
        cache.set(_make_full_snapshot("CL1"))
        cache.clear()
        assert cache.size() == 0

    def test_all(self):
        cache = SnapshotCache()
        cache.set(_make_full_snapshot("AL1"))
        cache.set(_make_full_snapshot("AL2"))
        assert len(cache.all()) == 2


# ===========================================================================
# StrategyStatisticsTracker
# ===========================================================================

class TestStrategyStatisticsTracker:
    def test_record_update_increments(self):
        tracker = StrategyStatisticsTracker()
        u = make_eval_update("T1")
        tracker.record_update(u)
        stats = tracker.summary("T1")
        assert stats.total_updates == 1

    def test_avg_confidence(self):
        tracker = StrategyStatisticsTracker()
        tracker.record_update(make_eval_update("T2", confidence=80.0))
        tracker.record_update(make_eval_update("T2", confidence=60.0))
        stats = tracker.summary("T2")
        assert stats.avg_confidence == pytest.approx(70.0, abs=1.0)

    def test_record_snapshot(self):
        tracker = StrategyStatisticsTracker()
        tracker.record_snapshot("T3", active_conflicts=2)
        stats = tracker.summary("T3")
        assert stats.snapshot_count == 1
        assert stats.conflict_count == 2

    def test_to_dict(self):
        tracker = StrategyStatisticsTracker()
        tracker.record_update(make_eval_update("T4"))
        d = tracker.summary("T4").to_dict()
        assert "strategy_id" in d
        assert "avg_confidence" in d
