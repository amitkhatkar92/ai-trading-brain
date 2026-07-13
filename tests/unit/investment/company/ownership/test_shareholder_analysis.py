"""tests/unit/investment/company/ownership/test_shareholder_analysis.py"""
from __future__ import annotations

import pytest

from iios.investment.company.ownership.shareholder_analysis import ShareholderAnalysisEngine
from iios.investment.company.ownership.shareholder_registry import build_shareholder_registry
from iios.investment.company.ownership.ownership_profile import (
    OwnershipStructureProfile, ConcentrationLevel, PromoterStabilityLabel,
    InstitutionalParticipationLabel,
)
from iios.investment.company.ownership.ownership_concentration import classify_concentration_level
from iios.investment.company.ownership.ownership_stability import classify_promoter_stability
from iios.investment.company.ownership.ownership_distribution import score_distribution_quality


@pytest.fixture
def engine():
    return ShareholderAnalysisEngine()


class TestShareholderAnalysisEngine:
    def test_returns_profile(self, engine, good_ownership_data):
        reg = build_shareholder_registry("INFY", good_ownership_data)
        result = engine.compute(reg)
        assert isinstance(result, OwnershipStructureProfile)

    def test_good_data_scores(self, engine, good_ownership_data):
        reg = build_shareholder_registry("INFY", good_ownership_data)
        result = engine.compute(reg)
        assert result.overall_structure_score >= 55.0
        assert 0.0 <= result.promoter_stability_score <= 100.0
        assert 0.0 <= result.institutional_quality_score <= 100.0

    def test_risky_data_lower_score(self, engine, good_ownership_data, risky_ownership_data):
        reg_good  = build_shareholder_registry("G", good_ownership_data)
        reg_risky = build_shareholder_registry("R", risky_ownership_data)
        good_result  = engine.compute(reg_good)
        risky_result = engine.compute(reg_risky)
        assert good_result.overall_structure_score > risky_result.overall_structure_score

    def test_concentration_level_type(self, engine, good_ownership_data):
        reg = build_shareholder_registry("T", good_ownership_data)
        result = engine.compute(reg)
        assert isinstance(result.concentration_level, ConcentrationLevel)

    def test_promoter_stability_type(self, engine, good_ownership_data):
        reg = build_shareholder_registry("T", good_ownership_data)
        result = engine.compute(reg)
        assert isinstance(result.promoter_stability, PromoterStabilityLabel)

    def test_institutional_participation_type(self, engine, good_ownership_data):
        reg = build_shareholder_registry("T", good_ownership_data)
        result = engine.compute(reg)
        assert isinstance(result.institutional_participation, InstitutionalParticipationLabel)

    def test_good_data_institutional_participation(self, engine, good_ownership_data):
        reg = build_shareholder_registry("T", good_ownership_data)
        result = engine.compute(reg)
        assert result.institutional_participation in (
            InstitutionalParticipationLabel.HIGH,
            InstitutionalParticipationLabel.MODERATE,
            InstitutionalParticipationLabel.EXCEPTIONAL,
        )

    def test_risky_data_institutional_participation(self, engine, risky_ownership_data):
        reg = build_shareholder_registry("T", risky_ownership_data)
        result = engine.compute(reg)
        assert result.institutional_participation in (
            InstitutionalParticipationLabel.LOW,
            InstitutionalParticipationLabel.NEGLIGIBLE,
            InstitutionalParticipationLabel.UNKNOWN,
        )

    def test_good_promoter_stability(self, engine, good_ownership_data):
        reg = build_shareholder_registry("T", good_ownership_data)
        result = engine.compute(reg)
        assert result.promoter_stability not in (
            PromoterStabilityLabel.DECLINING,
            PromoterStabilityLabel.CONCERNING,
        )

    def test_risky_promoter_stability(self, engine, risky_ownership_data):
        reg = build_shareholder_registry("T", risky_ownership_data)
        result = engine.compute(reg)
        assert result.promoter_stability in (
            PromoterStabilityLabel.CONCERNING,
            PromoterStabilityLabel.DECLINING,
        )

    def test_empty_registry(self, engine):
        reg = build_shareholder_registry("T", None)
        result = engine.compute(reg)
        assert isinstance(result, OwnershipStructureProfile)
        assert 0.0 <= result.overall_structure_score <= 100.0

    def test_all_scores_in_range(self, engine, good_ownership_data):
        reg = build_shareholder_registry("T", good_ownership_data)
        result = engine.compute(reg)
        for s in [
            result.overall_structure_score, result.promoter_stability_score,
            result.institutional_quality_score, result.distribution_quality_score,
            result.free_float_score,
        ]:
            assert 0.0 <= s <= 100.0, f"Score out of range: {s}"


class TestConcentrationFunctions:
    def test_highly_concentrated(self):
        assert classify_concentration_level(0.90) == ConcentrationLevel.HIGHLY_CONCENTRATED

    def test_concentrated(self):
        label = classify_concentration_level(0.70)
        assert label == ConcentrationLevel.CONCENTRATED

    def test_moderate(self):
        assert classify_concentration_level(0.55) == ConcentrationLevel.MODERATE

    def test_widely_held(self):
        assert classify_concentration_level(0.20) == ConcentrationLevel.WIDELY_HELD

    def test_unknown(self):
        assert classify_concentration_level(None) == ConcentrationLevel.UNKNOWN


class TestStabilityFunctions:
    def test_strong(self):
        lbl = classify_promoter_stability(0.52, 0.5, 1.2, 0.05)
        assert lbl in (PromoterStabilityLabel.STRONG, PromoterStabilityLabel.STABLE)

    def test_concerning_from_pledge(self):
        lbl = classify_promoter_stability(0.52, -0.5, -1.0, 0.65)
        assert lbl in (
            PromoterStabilityLabel.CONCERNING,
            PromoterStabilityLabel.DECLINING,
        )

    def test_declining_from_selling(self):
        lbl = classify_promoter_stability(0.40, -4.0, -8.0, 0.05)
        assert lbl in (
            PromoterStabilityLabel.DECLINING,
            PromoterStabilityLabel.CONCERNING,
        )

    def test_none_inputs(self):
        lbl = classify_promoter_stability(None, None, None, None)
        assert isinstance(lbl, PromoterStabilityLabel)


class TestDistributionFunctions:
    def test_balanced_distribution(self):
        s = score_distribution_quality(
            promoter_pct=52.0, institutional_pct=28.0, retail_pct=12.0,
            government_pct=0.0, fii_pct=12.0, dii_pct=10.0, free_float_pct=45.0,
        )
        assert s >= 60.0

    def test_monopoly_distribution(self):
        s = score_distribution_quality(
            promoter_pct=90.0, institutional_pct=5.0, retail_pct=5.0,
            government_pct=None, fii_pct=None, dii_pct=None, free_float_pct=10.0,
        )
        assert s < 50.0
