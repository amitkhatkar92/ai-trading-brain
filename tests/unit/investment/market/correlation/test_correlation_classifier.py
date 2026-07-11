"""test_correlation_classifier.py — tests for CorrelationRegimeClassifier and RegimeTransitionDetector."""
from __future__ import annotations

import pytest

from iios.investment.market.correlation.models import (
    AssetClass,
    CorrelationEventType,
    CorrelationMatrix,
    CorrelationMethod,
    CorrelationRegimeType,
    DependencyGraph,
    IntermarketAnalysis,
    RiskLevel,
    SystemicRiskMetrics,
)
from iios.investment.market.correlation.correlation_statistics import CorrelationStatistics
from iios.investment.market.correlation.correlation_classifier import CorrelationRegimeClassifier
from iios.investment.market.correlation.regime_transition import CorrelationRegimeTransitionDetector
from iios.investment.market.correlation.correlation_regime import build_regime_snapshot


def _matrix(avg_corr: float):
    syms = ["A", "B", "C"]
    data = {s: {t: (1.0 if s == t else avg_corr) for t in syms} for s in syms}
    return CorrelationMatrix(
        symbols=syms, data=data, method=CorrelationMethod.PEARSON,
        window=60, n_observations=60, bar_index=0, timestamp=0.0, confidence=0.9,
    )


def _empty_intermarket():
    return IntermarketAnalysis(
        relationships=[], anomalies=[], risk_on_signals=0, risk_off_signals=0,
        flight_to_safety=False, bar_index=0, timestamp=0.0,
    )


def _empty_systemic():
    return SystemicRiskMetrics(
        risk_level=RiskLevel.LOW, avg_pairwise_correlation=0.0,
        avg_abs_correlation=0.0, correlation_concentration=0.0,
        contagion_index=0.0, interconnectedness=0.0, systemic_risk_score=0.0,
        most_interconnected=[], n_correlated_clusters=0,
    )


def _prime_stats(avg_corr: float, n: int = 10) -> CorrelationStatistics:
    stats = CorrelationStatistics(window=20)
    m = _matrix(avg_corr)
    for _ in range(n):
        stats.update(m)
    return stats


# ── CorrelationRegimeClassifier ───────────────────────────────────────────

class TestCorrelationRegimeClassifier:
    def test_high_corr_regime(self):
        clf    = CorrelationRegimeClassifier()
        stats  = _prime_stats(0.75)
        result = clf.classify(
            _matrix(0.75), stats, _empty_intermarket(), _empty_systemic(),
            previous_regime=None, duration_bars=1,
        )
        assert result.regime == CorrelationRegimeType.HIGHLY_CORRELATED

    def test_moderate_corr_regime(self):
        clf    = CorrelationRegimeClassifier()
        stats  = _prime_stats(0.50)
        result = clf.classify(
            _matrix(0.50), stats, _empty_intermarket(), _empty_systemic(),
            None, 1,
        )
        assert result.regime == CorrelationRegimeType.MODERATELY_CORRELATED

    def test_weakly_corr_regime(self):
        clf    = CorrelationRegimeClassifier()
        stats  = _prime_stats(0.25)
        result = clf.classify(
            _matrix(0.25), stats, _empty_intermarket(), _empty_systemic(),
            None, 1,
        )
        assert result.regime in (
            CorrelationRegimeType.WEAKLY_CORRELATED,
            CorrelationRegimeType.INDEPENDENT,
        )

    def test_independent_regime(self):
        clf    = CorrelationRegimeClassifier()
        stats  = _prime_stats(0.05)
        result = clf.classify(
            _matrix(0.05), stats, _empty_intermarket(), _empty_systemic(),
            None, 1,
        )
        assert result.regime in (
            CorrelationRegimeType.INDEPENDENT,
            CorrelationRegimeType.WEAKLY_CORRELATED,
        )

    def test_inverse_regime(self):
        clf    = CorrelationRegimeClassifier()
        stats  = _prime_stats(-0.40)
        result = clf.classify(
            _matrix(-0.40), stats, _empty_intermarket(), _empty_systemic(),
            None, 1,
        )
        assert result.regime in (
            CorrelationRegimeType.INVERSE_CORRELATION,
            CorrelationRegimeType.RISK_OFF,
            CorrelationRegimeType.FLIGHT_TO_SAFETY,
            CorrelationRegimeType.INDEPENDENT,
        )

    def test_confidence_range(self):
        clf    = CorrelationRegimeClassifier()
        stats  = _prime_stats(0.60)
        result = clf.classify(
            _matrix(0.60), stats, _empty_intermarket(), _empty_systemic(),
            None, 5,
        )
        assert 0.0 <= result.confidence <= 1.0

    def test_transition_probability_range(self):
        clf    = CorrelationRegimeClassifier()
        stats  = _prime_stats(0.50)
        result = clf.classify(
            _matrix(0.50), stats, _empty_intermarket(), _empty_systemic(),
            None, 10,
        )
        assert 0.0 <= result.transition_probability <= 1.0

    def test_previous_regime_stored(self):
        clf    = CorrelationRegimeClassifier()
        stats  = _prime_stats(0.60)
        result = clf.classify(
            _matrix(0.60), stats, _empty_intermarket(), _empty_systemic(),
            previous_regime=CorrelationRegimeType.NEUTRAL if hasattr(CorrelationRegimeType, 'NEUTRAL')
            else CorrelationRegimeType.INDEPENDENT,
            duration_bars=3,
        )
        assert result.duration_bars == 3

    def test_regime_score_range(self):
        clf    = CorrelationRegimeClassifier()
        stats  = _prime_stats(0.50)
        result = clf.classify(
            _matrix(0.50), stats, _empty_intermarket(), _empty_systemic(),
            None, 1,
        )
        assert 0.0 <= result.regime_score <= 100.0

    def test_to_dict(self):
        clf    = CorrelationRegimeClassifier()
        stats  = _prime_stats(0.50)
        result = clf.classify(
            _matrix(0.50), stats, _empty_intermarket(), _empty_systemic(), None, 1
        )
        d = result.to_dict()
        assert "regime" in d


# ── CorrelationRegimeTransitionDetector ──────────────────────────────────

class TestCorrelationRegimeTransitionDetector:
    def test_initial_regime_unknown(self):
        td = CorrelationRegimeTransitionDetector()
        assert td.current_regime == CorrelationRegimeType.UNKNOWN

    def test_first_update_triggers_transition(self):
        td   = CorrelationRegimeTransitionDetector()
        snap = build_regime_snapshot(
            CorrelationRegimeType.HIGHLY_CORRELATED, 0.85, 1, None, 0.75, 0.10, 80.0
        )
        events = td.update(snap, bar_index=0)
        assert td.current_regime == CorrelationRegimeType.HIGHLY_CORRELATED
        assert any(e.event_type == CorrelationEventType.REGIME_CHANGE for e in events)

    def test_no_event_when_regime_unchanged(self):
        td   = CorrelationRegimeTransitionDetector()
        snap = build_regime_snapshot(
            CorrelationRegimeType.MODERATELY_CORRELATED, 0.75, 1, None, 0.50, 0.10, 60.0
        )
        td.update(snap, bar_index=0)
        events = td.update(snap, bar_index=1)
        assert events == []

    def test_duration_increments(self):
        td   = CorrelationRegimeTransitionDetector()
        snap = build_regime_snapshot(
            CorrelationRegimeType.MODERATELY_CORRELATED, 0.75, 1, None, 0.50, 0.10, 60.0
        )
        for i in range(5):
            td.update(snap, bar_index=i)
        assert td.duration_bars >= 4

    def test_previous_regime_tracked(self):
        td = CorrelationRegimeTransitionDetector()
        snap1 = build_regime_snapshot(
            CorrelationRegimeType.INDEPENDENT, 0.70, 1, None, 0.05, 0.10, 10.0
        )
        td.update(snap1, bar_index=0)
        snap2 = build_regime_snapshot(
            CorrelationRegimeType.HIGHLY_CORRELATED, 0.90, 1, None, 0.80, 0.05, 90.0
        )
        td.update(snap2, bar_index=1)
        assert td.previous_regime == CorrelationRegimeType.INDEPENDENT
