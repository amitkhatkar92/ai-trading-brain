"""tests/unit/investment/market/integration/test_snapshot.py"""
from __future__ import annotations

import json

import pytest

from iios.investment.market.integration.aggregation_engine import AggregationEngine
from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.conflict_engine import ConflictEngine
from iios.investment.market.integration.consistency_validator import ConsistencyValidator
from iios.investment.market.integration.market_confidence import MarketConfidenceEngine
from iios.investment.market.integration.market_quality import MarketQualityEngine
from iios.investment.market.integration.market_snapshot import SnapshotBuilder
from iios.investment.market.integration.market_state import MarketStateClassifier
from iios.investment.market.integration.market_statistics import (
    avg_confidence, avg_quality, conflict_rate,
    regime_distribution, state_label_distribution,
)
from iios.investment.market.integration.market_summary import MarketSummaryBuilder
from iios.investment.market.integration.models import (
    ConflictSummary,
    MarketIntelligenceSnapshot,
    MarketStateLabel,
    QualityScore,
    ValidationReport,
    ValidationStatus,
)
from iios.investment.market.integration.snapshot_history import SnapshotHistory


def _build_snap(state: AggregationState) -> MarketIntelligenceSnapshot:
    validator  = ConsistencyValidator()
    conflict_e = ConflictEngine()
    quality_e  = MarketQualityEngine()
    conf_e     = MarketConfidenceEngine()
    state_clf  = MarketStateClassifier()
    summary_b  = MarketSummaryBuilder()
    snap_b     = SnapshotBuilder()

    report    = validator.validate(state)
    conflicts = conflict_e.process(state, report)
    quality   = quality_e.score(state, report, conflicts)
    conf      = conf_e.compute(state, quality, conflicts)
    label     = state_clf.classify(state)
    summary   = summary_b.build(state, label, quality, conflicts)

    return snap_b.build(
        state=state, label=label, quality=quality, confidence=conf,
        validation=report, conflicts=conflicts,
        engine_health={}, summary_text=summary,
    )


class TestMarketStateClassifier:
    def test_risk_on(self):
        state = AggregationState(
            1, 1.0, market_regime="bull",
            trend_direction="up", trend_strength=65.0,
            breadth_regime="positive", volatility_regime="normal",
            liquidity_regime="normal",
        )
        label = MarketStateClassifier().classify(state)
        assert label is MarketStateLabel.RISK_ON

    def test_risk_off(self):
        state = AggregationState(
            1, 1.0, market_regime="bear",
            trend_direction="down", trend_strength=70.0,
            breadth_regime="negative", volatility_regime="elevated",
        )
        label = MarketStateClassifier().classify(state)
        assert label is MarketStateLabel.RISK_OFF

    def test_crisis(self):
        state = AggregationState(
            1, 1.0, market_regime="crisis",
            volatility_regime="extreme",
        )
        label = MarketStateClassifier().classify(state)
        assert label is MarketStateLabel.CRISIS

    def test_recovery(self):
        state = AggregationState(
            1, 1.0, market_regime="bear",
            trend_direction="up", trend_strength=55.0,
            breadth_regime="positive",
        )
        label = MarketStateClassifier().classify(state)
        assert label is MarketStateLabel.RECOVERY

    def test_transition(self):
        state = AggregationState(
            1, 1.0, market_regime="bull",
            trend_direction="down",
        )
        label = MarketStateClassifier().classify(state)
        assert label is MarketStateLabel.TRANSITION

    def test_unknown_when_no_signals(self):
        state = AggregationState(1, 1.0)
        label = MarketStateClassifier().classify(state)
        assert label is MarketStateLabel.UNKNOWN


class TestMarketSummaryBuilder:
    def test_build_nonempty(self, full_bundle):
        engine  = AggregationEngine()
        state   = engine.aggregate(full_bundle)
        builder = MarketSummaryBuilder()
        quality = QualityScore(1, 75.0, 90.0, 80.0, 85.0, 70.0)
        conflicts = ConflictSummary(1, 0, 0, 0, 0, 0, 0, 0)
        text    = builder.build(state, MarketStateLabel.RISK_ON, quality, conflicts)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_build_includes_regime(self, full_bundle):
        engine  = AggregationEngine()
        state   = engine.aggregate(full_bundle)
        quality = QualityScore(1, 80.0, 90.0, 85.0, 88.0, 78.0)
        conflicts = ConflictSummary(1, 0, 0, 0, 0, 0, 0, 0)
        text    = MarketSummaryBuilder().build(state, MarketStateLabel.RISK_ON, quality, conflicts)
        assert "bull" in text.lower() or "RISK_ON" in text.upper()

    def test_build_detail(self, full_bundle):
        engine  = AggregationEngine()
        state   = engine.aggregate(full_bundle)
        quality = QualityScore(1, 80.0, 90.0, 85.0, 88.0, 78.0)
        conflicts = ConflictSummary(1, 2, 0, 1, 1, 0, 1, 1)
        detail  = MarketSummaryBuilder().build_detail(
            state, MarketStateLabel.RISK_ON, quality, conflicts)
        assert "Market State" in detail


class TestSnapshotBuilder:
    def test_builds_snapshot(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        snap   = _build_snap(state)
        assert isinstance(snap, MarketIntelligenceSnapshot)
        assert snap.market_regime == "bull"

    def test_snapshot_has_uuid(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        snap   = _build_snap(state)
        assert len(snap.snapshot_id) == 36

    def test_snapshot_serialisable(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        snap   = _build_snap(state)
        json.dumps(snap.to_dict())

    def test_snapshot_confidence_in_range(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        snap   = _build_snap(state)
        assert 0.0 <= snap.overall_confidence <= 100.0

    def test_crisis_snapshot_lower_confidence(self, crisis_bundle, full_bundle):
        engine   = AggregationEngine()
        snap_ok  = _build_snap(engine.aggregate(full_bundle))
        snap_bad = _build_snap(engine.aggregate(crisis_bundle))
        assert snap_bad.overall_confidence <= snap_ok.overall_confidence


class TestSnapshotHistory:
    def test_append_and_latest(self, full_bundle):
        engine  = AggregationEngine()
        state   = engine.aggregate(full_bundle)
        snap    = _build_snap(state)
        history = SnapshotHistory()
        history.append(snap)
        assert history.latest() is snap

    def test_recent(self, make_bundle):
        engine  = AggregationEngine()
        history = SnapshotHistory()
        for i in range(5):
            history.append(_build_snap(engine.aggregate(make_bundle(bar_index=i + 1))))
        assert len(history.recent(3)) == 3

    def test_confidence_series(self, make_bundle):
        engine  = AggregationEngine()
        history = SnapshotHistory()
        for i in range(4):
            history.append(_build_snap(engine.aggregate(make_bundle(bar_index=i + 1))))
        series = history.confidence_series(4)
        assert len(series) == 4
        assert all(0.0 <= v <= 100.0 for v in series)


class TestMarketStatistics:
    def test_avg_confidence(self, make_bundle):
        engine  = AggregationEngine()
        snaps   = [_build_snap(engine.aggregate(make_bundle(bar_index=i))) for i in range(1, 4)]
        avg     = avg_confidence(snaps)
        assert 0.0 <= avg <= 100.0

    def test_avg_quality(self, make_bundle):
        engine  = AggregationEngine()
        snaps   = [_build_snap(engine.aggregate(make_bundle(bar_index=i))) for i in range(1, 4)]
        avg     = avg_quality(snaps)
        assert 0.0 <= avg <= 100.0

    def test_conflict_rate_clean(self, make_bundle):
        engine = AggregationEngine()
        snaps  = [_build_snap(engine.aggregate(make_bundle(bar_index=i))) for i in range(1, 6)]
        rate   = conflict_rate(snaps)
        assert 0.0 <= rate <= 1.0

    def test_regime_distribution(self, make_bundle):
        engine = AggregationEngine()
        snaps  = [_build_snap(engine.aggregate(make_bundle(bar_index=i))) for i in range(1, 4)]
        dist   = regime_distribution(snaps)
        assert isinstance(dist, dict)
        assert "bull" in dist

    def test_state_label_distribution(self, make_bundle):
        engine = AggregationEngine()
        snaps  = [_build_snap(engine.aggregate(make_bundle(bar_index=i))) for i in range(1, 4)]
        dist   = state_label_distribution(snaps)
        assert isinstance(dist, dict)
        assert sum(dist.values()) == len(snaps)

    def test_empty_snapshots(self):
        assert avg_confidence([]) == 0.0
        assert avg_quality([]) == 0.0
        assert conflict_rate([]) == 0.0
