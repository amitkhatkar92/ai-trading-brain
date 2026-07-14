"""tests/unit/investment/decision/risk/test_exposure_analysis.py
Tests for PositionExposureAnalyzer, CapitalExposureAnalyzer,
ConcentrationAnalyzer, and ExposureEngine.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.evidence.evidence_constants import EvidenceSourceType
from iios.investment.decision.risk.capital_exposure import CapitalExposureAnalyzer
from iios.investment.decision.risk.concentration_analysis import ConcentrationAnalyzer
from iios.investment.decision.risk.exposure_engine import ExposureEngine
from iios.investment.decision.risk.position_exposure import PositionExposureAnalyzer
from iios.investment.decision.risk.risk_constants import ExposureLevel


# ─── PositionExposureAnalyzer ────────────────────────────────────────────────

class TestPositionExposureAnalyzer:
    def setup_method(self):
        self.analyzer = PositionExposureAnalyzer()

    def test_rich_snapshot_in_range(self, rich_evidence_snapshot):
        r = self.analyzer.analyze(rich_evidence_snapshot)
        assert 0.0 <= r.position_exposure_risk <= 100.0

    def test_minimal_higher_than_rich(self, rich_evidence_snapshot, minimal_evidence_snapshot):
        r_rich = self.analyzer.analyze(rich_evidence_snapshot)
        r_min  = self.analyzer.analyze(minimal_evidence_snapshot)
        assert r_min.position_exposure_risk >= r_rich.position_exposure_risk

    def test_capital_at_risk_bounded(self, rich_evidence_snapshot):
        r = self.analyzer.analyze(rich_evidence_snapshot)
        assert 0.0 < r.estimated_capital_at_risk <= 0.05

    def test_to_dict_keys(self, rich_evidence_snapshot):
        d = self.analyzer.analyze(rich_evidence_snapshot).to_dict()
        assert "position_exposure_risk" in d
        assert "estimated_capital_at_risk" in d


# ─── CapitalExposureAnalyzer ─────────────────────────────────────────────────

class TestCapitalExposureAnalyzer:
    def setup_method(self):
        self.analyzer = CapitalExposureAnalyzer()

    def test_returns_exposure_level(self, rich_evidence_snapshot):
        r = self.analyzer.analyze(rich_evidence_snapshot)
        assert isinstance(r.exposure_level, ExposureLevel)

    def test_capital_risk_in_range(self, rich_evidence_snapshot):
        r = self.analyzer.analyze(rich_evidence_snapshot)
        assert 0.0 <= r.capital_risk_score <= 100.0

    def test_allocation_risk_in_range(self, rich_evidence_snapshot):
        r = self.analyzer.analyze(rich_evidence_snapshot)
        assert 0.0 <= r.allocation_risk <= 100.0

    def test_minimal_snapshot_higher_risk(self, minimal_evidence_snapshot, rich_evidence_snapshot):
        r_min  = self.analyzer.analyze(minimal_evidence_snapshot)
        r_rich = self.analyzer.analyze(rich_evidence_snapshot)
        assert r_min.capital_risk_score >= r_rich.capital_risk_score

    def test_to_dict_keys(self, rich_evidence_snapshot):
        d = self.analyzer.analyze(rich_evidence_snapshot).to_dict()
        assert "capital_risk_score" in d and "exposure_level" in d


# ─── ConcentrationAnalyzer ───────────────────────────────────────────────────

class TestConcentrationAnalyzer:
    def setup_method(self):
        self.analyzer = ConcentrationAnalyzer()

    def test_empty_snapshot_returns_max_concentration(self, make_evidence_snapshot):
        snap = make_evidence_snapshot([], quality=0.0)
        r = self.analyzer.analyze(snap)
        assert r.herfindahl_index == pytest.approx(1.0)
        assert r.concentration_score == pytest.approx(100.0)

    def test_single_source_has_high_hhi(self, minimal_evidence_snapshot):
        r = self.analyzer.analyze(minimal_evidence_snapshot)
        assert r.herfindahl_index == pytest.approx(1.0)

    def test_diverse_sources_lower_hhi(self, rich_evidence_snapshot):
        r = self.analyzer.analyze(rich_evidence_snapshot)
        # Multiple source types: MARKET, COMPANY, STRATEGY
        assert r.herfindahl_index < 1.0

    def test_hhi_in_range(self, rich_evidence_snapshot):
        r = self.analyzer.analyze(rich_evidence_snapshot)
        assert 0.0 <= r.herfindahl_index <= 1.0

    def test_concentration_score_in_range(self, rich_evidence_snapshot):
        r = self.analyzer.analyze(rich_evidence_snapshot)
        assert 0.0 <= r.concentration_score <= 100.0

    def test_source_count_matches_distinct_types(self, rich_evidence_snapshot):
        r = self.analyzer.analyze(rich_evidence_snapshot)
        assert r.source_count >= 3   # MARKET, COMPANY, STRATEGY at minimum

    def test_dominant_source_is_string(self, rich_evidence_snapshot):
        r = self.analyzer.analyze(rich_evidence_snapshot)
        assert isinstance(r.dominant_source, str) and len(r.dominant_source) > 0

    def test_to_dict_keys(self, rich_evidence_snapshot):
        d = self.analyzer.analyze(rich_evidence_snapshot).to_dict()
        assert "herfindahl_index" in d and "concentration_score" in d


# ─── ExposureEngine ──────────────────────────────────────────────────────────

class TestExposureEngine:
    def setup_method(self):
        self.engine = ExposureEngine()

    def test_returns_report(self, rich_evidence_snapshot):
        r = self.engine.analyze(rich_evidence_snapshot)
        assert 0.0 <= r.exposure_risk <= 100.0

    def test_report_has_all_sub_results(self, rich_evidence_snapshot):
        r = self.engine.analyze(rich_evidence_snapshot)
        assert r.position is not None
        assert r.capital is not None
        assert r.concentration is not None

    def test_exposure_risk_composite_formula(self, rich_evidence_snapshot):
        r = self.engine.analyze(rich_evidence_snapshot)
        expected = (
            r.position.position_exposure_risk * 0.40
            + r.capital.capital_risk_score     * 0.40
            + r.concentration.concentration_score * 0.20
        )
        assert abs(r.exposure_risk - expected) < 0.1

    def test_to_dict_structure(self, rich_evidence_snapshot):
        d = self.engine.analyze(rich_evidence_snapshot).to_dict()
        assert "exposure_risk" in d
        assert "position" in d and "capital" in d and "concentration" in d
