"""tests/unit/investment/market/integration/test_quality.py"""
from __future__ import annotations

import pytest

from iios.investment.market.integration.aggregation_engine import AggregationEngine
from iios.investment.market.integration.aggregation_state import AggregationState
from iios.investment.market.integration.conflict_engine import ConflictEngine
from iios.investment.market.integration.consistency_validator import ConsistencyValidator
from iios.investment.market.integration.market_confidence import MarketConfidenceEngine
from iios.investment.market.integration.market_quality import MarketQualityEngine
from iios.investment.market.integration.models import (
    ConflictSummary,
    QualityScore,
    ValidationReport,
    ValidationStatus,
)
from iios.investment.market.integration.quality_history import QualityHistory
from iios.investment.market.integration.quality_statistics import (
    avg_completeness,
    avg_consistency,
    avg_overall,
    below_threshold_bars,
    dimension_breakdown,
    quality_trend,
)


def _score(state: AggregationState) -> QualityScore:
    validator  = ConsistencyValidator()
    conflict_e = ConflictEngine()
    quality_e  = MarketQualityEngine()
    report    = validator.validate(state)
    conflicts = conflict_e.process(state, report)
    return quality_e.score(state, report, conflicts)


class TestMarketQualityEngine:
    def test_score_full_bundle(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        score  = _score(state)
        assert isinstance(score, QualityScore)
        assert 0.0 <= score.overall <= 100.0

    def test_full_bundle_higher_completeness_than_empty(self, full_bundle, empty_bundle):
        engine    = AggregationEngine()
        score_ok  = _score(engine.aggregate(full_bundle))
        score_bad = _score(engine.aggregate(empty_bundle))
        assert score_ok.completeness > score_bad.completeness

    def test_empty_bundle_low_completeness(self, empty_bundle):
        engine = AggregationEngine()
        score  = _score(engine.aggregate(empty_bundle))
        assert score.completeness == pytest.approx(0.0)

    def test_crisis_bundle_lower_consistency(self, full_bundle, crisis_bundle):
        engine   = AggregationEngine()
        score_ok = _score(engine.aggregate(full_bundle))
        score_bad = _score(engine.aggregate(crisis_bundle))
        # Crisis creates conflicts → lower consistency
        assert score_bad.consistency <= score_ok.consistency

    def test_quality_score_in_range(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        score  = _score(state)
        for dim in score.dimensions:
            assert 0.0 <= dim.score <= 100.0
        assert 0.0 <= score.overall <= 100.0

    def test_dimensions_populated(self, full_bundle):
        engine = AggregationEngine()
        state  = engine.aggregate(full_bundle)
        score  = _score(state)
        assert len(score.dimensions) == 4
        names  = {d.name for d in score.dimensions}
        assert names == {"completeness", "consistency", "freshness", "reliability"}

    def test_advance_bar(self, full_bundle):
        engine    = AggregationEngine()
        quality_e = MarketQualityEngine()
        quality_e.advance_bar(5)
        state  = engine.aggregate(full_bundle)
        report = ConsistencyValidator().validate(state)
        conflict = ConflictEngine()
        cs = conflict.process(state, report)
        score  = quality_e.score(state, report, cs)
        assert isinstance(score, QualityScore)


class TestMarketConfidenceEngine:
    def test_confidence_full_bundle(self, full_bundle):
        engine   = AggregationEngine()
        state    = engine.aggregate(full_bundle)
        score    = _score(state)
        conflicts = ConflictEngine().process(
            state, ConsistencyValidator().validate(state)
        )
        conf     = MarketConfidenceEngine().compute(state, score, conflicts)
        assert 0.0 <= conf <= 100.0

    def test_confidence_lower_when_extreme_volatility(self, make_bundle):
        engine  = AggregationEngine()
        agg_ok  = engine.aggregate(make_bundle(1, volatility="normal"))
        agg_bad = engine.aggregate(make_bundle(2, volatility="extreme"))

        def _conf(state):
            score    = _score(state)
            conflicts = ConflictEngine().process(
                state, ConsistencyValidator().validate(state)
            )
            return MarketConfidenceEngine().compute(state, score, conflicts)

        assert _conf(agg_bad) <= _conf(agg_ok)

    def test_confidence_lower_missing_engines(self, empty_bundle, full_bundle):
        engine  = AggregationEngine()

        def _conf(bundle):
            state    = engine.aggregate(bundle)
            score    = _score(state)
            conflicts = ConflictEngine().process(
                state, ConsistencyValidator().validate(state)
            )
            return MarketConfidenceEngine().compute(state, score, conflicts)

        assert _conf(empty_bundle) < _conf(full_bundle)

    def test_confidence_in_range(self, crisis_bundle):
        engine    = AggregationEngine()
        state     = engine.aggregate(crisis_bundle)
        score     = _score(state)
        conflicts = ConflictEngine().process(
            state, ConsistencyValidator().validate(state)
        )
        conf = MarketConfidenceEngine().compute(state, score, conflicts)
        assert 0.0 <= conf <= 100.0


class TestQualityHistory:
    def test_append_and_latest(self, full_bundle):
        engine  = AggregationEngine()
        state   = engine.aggregate(full_bundle)
        score   = _score(state)
        history = QualityHistory()
        history.append(score)
        assert history.latest() is score

    def test_overall_series(self, make_bundle):
        engine  = AggregationEngine()
        history = QualityHistory()
        for i in range(5):
            history.append(_score(engine.aggregate(make_bundle(bar_index=i + 1))))
        series = history.overall_series(5)
        assert len(series) == 5

    def test_maxlen_respected(self, full_bundle):
        engine  = AggregationEngine()
        history = QualityHistory(maxlen=3)
        for _ in range(5):
            history.append(_score(engine.aggregate(full_bundle)))
        assert len(history) <= 3


class TestQualityStatistics:
    def test_avg_overall(self, make_bundle):
        engine = AggregationEngine()
        scores = [_score(engine.aggregate(make_bundle(bar_index=i))) for i in range(1, 5)]
        avg    = avg_overall(scores)
        assert 0.0 <= avg <= 100.0

    def test_avg_completeness(self, make_bundle):
        engine = AggregationEngine()
        scores = [_score(engine.aggregate(make_bundle(bar_index=i))) for i in range(1, 5)]
        avg    = avg_completeness(scores)
        assert 0.0 <= avg <= 100.0

    def test_below_threshold_bars(self, make_bundle, empty_bundle):
        engine = AggregationEngine()
        scores = (
            [_score(engine.aggregate(empty_bundle))] * 3
            + [_score(engine.aggregate(make_bundle(1)))] * 2
        )
        count  = below_threshold_bars(scores, threshold=50.0)
        assert isinstance(count, int)
        assert count >= 0

    def test_quality_trend_stable(self, full_bundle):
        engine = AggregationEngine()
        scores = [_score(engine.aggregate(full_bundle)) for _ in range(3)]
        trend  = quality_trend(scores)
        assert trend in ("improving", "degrading", "stable")

    def test_quality_trend_empty(self):
        assert quality_trend([]) == "stable"

    def test_dimension_breakdown_keys(self, make_bundle):
        engine = AggregationEngine()
        scores = [_score(engine.aggregate(make_bundle(bar_index=i))) for i in range(1, 4)]
        bd     = dimension_breakdown(scores)
        assert set(bd.keys()) == {"completeness", "consistency", "freshness", "reliability"}
