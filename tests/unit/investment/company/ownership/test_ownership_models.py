"""tests/unit/investment/company/ownership/test_ownership_models.py"""
from __future__ import annotations

import pytest

from iios.investment.company.ownership.shareholder_registry import (
    ShareholderRecord, ShareholderRegistry, build_shareholder_registry,
)
from iios.investment.company.ownership.ownership_profile import (
    ConcentrationLevel, PromoterStabilityLabel,
)
from iios.investment.company.ownership.ownership_concentration import (
    classify_concentration_level,
    score_concentration_risk,
    score_herfindahl_proxy,
    score_control_concentration,
)
from iios.investment.company.ownership.ownership_stability import (
    classify_promoter_stability,
    score_ownership_stability,
    score_promoter_conviction,
)
from iios.investment.company.ownership.ownership_distribution import (
    compute_ownership_entropy, score_distribution_quality,
)


class TestShareholderRegistry:
    def test_build_from_good_data(self, good_ownership_data):
        reg = build_shareholder_registry("INFY", good_ownership_data)
        assert reg.ticker == "INFY"
        assert reg.promoter_pct == pytest.approx(52.0)
        assert reg.institutional_pct == pytest.approx(28.0)
        assert reg.jurisdiction == "IN"

    def test_build_empty(self):
        reg = build_shareholder_registry("X", None)
        assert reg.promoter_pct is None
        assert reg.institutional_pct is None

    def test_computed_free_float(self):
        reg = ShareholderRegistry(ticker="T")
        reg.promoter_pct = 52.0
        reg.government_pct = 5.0
        ff = reg.computed_free_float
        assert ff == pytest.approx(43.0)

    def test_free_float_explicit(self):
        reg = ShareholderRegistry(ticker="T")
        reg.free_float_pct = 45.0
        assert reg.computed_free_float == 45.0

    def test_records_built(self, good_ownership_data):
        reg = build_shareholder_registry("T", good_ownership_data)
        cats = [r.category for r in reg.records]
        assert "promoter" in cats
        assert "institutional" in cats

    def test_to_dict(self, good_ownership_data):
        reg = build_shareholder_registry("INFY", good_ownership_data)
        d = reg.to_dict()
        assert d["ticker"] == "INFY"
        assert "promoter_pct" in d

    def test_institutional_quality_category(self):
        reg = ShareholderRegistry(ticker="T")
        reg.institutional_pct = 45.0
        assert reg.institutional_quality_category == "exceptional"
        reg.institutional_pct = 35.0
        assert reg.institutional_quality_category == "high"
        reg.institutional_pct = 3.0
        assert reg.institutional_quality_category == "negligible"


class TestShareholderRecord:
    def test_to_dict(self):
        r = ShareholderRecord(category="promoter", holding_pct=52.0)
        d = r.to_dict()
        assert d["category"] == "promoter"
        assert d["holding_pct"] == pytest.approx(52.0)


class TestConcentrationLevel:
    def test_classify_highly(self):
        assert classify_concentration_level(0.85) == ConcentrationLevel.HIGHLY_CONCENTRATED

    def test_classify_moderate(self):
        assert classify_concentration_level(0.55) == ConcentrationLevel.MODERATE

    def test_classify_widely_held(self):
        assert classify_concentration_level(0.15) == ConcentrationLevel.WIDELY_HELD

    def test_classify_none(self):
        assert classify_concentration_level(None) == ConcentrationLevel.UNKNOWN

    def test_concentration_risk_score_range(self):
        for top10, prom, ff in [(0.9, 0.8, 0.10), (0.5, 0.4, 0.40), (0.2, 0.1, 0.70)]:
            s = score_concentration_risk(top10, prom, ff)
            assert 0.0 <= s <= 100.0


class TestHerfindahlProxy:
    def test_equal_distribution(self):
        s = score_herfindahl_proxy(0.25, 0.25, 0.25, 0.25)
        assert s >= 75.0   # equal distribution → high diversity score

    def test_monopoly(self):
        s = score_herfindahl_proxy(0.99, 0.0, 0.01, None)
        assert s < 15.0

    def test_none(self):
        s = score_herfindahl_proxy(None, None, None, None)
        assert s == 50.0


class TestControlConcentration:
    def test_optimal_promoter(self):
        s = score_control_concentration(0.52, 0.28, False)
        assert s >= 60.0

    def test_dominant_promoter(self):
        s1 = score_control_concentration(0.52, 0.28, False)
        s2 = score_control_concentration(0.80, 0.08, True)
        assert s1 > s2


class TestPromoterStability:
    def test_strong(self):
        lbl = classify_promoter_stability(0.52, 0.5, 1.5, 0.05)
        assert lbl in (PromoterStabilityLabel.STRONG, PromoterStabilityLabel.STABLE)

    def test_concerning_pledge(self):
        lbl = classify_promoter_stability(0.52, 0.0, -1.0, 0.60)
        assert lbl == PromoterStabilityLabel.CONCERNING

    def test_declining(self):
        lbl = classify_promoter_stability(0.40, -4.0, -8.0, 0.05)
        assert lbl in (PromoterStabilityLabel.DECLINING, PromoterStabilityLabel.CONCERNING)

    def test_stability_score_range(self):
        for args in [
            (0.52, 0.5, 1.5, 0.8, 0.05),
            (0.75, -3.0, -7.0, -2.0, 0.55),
            (None, None, None, None, None),
        ]:
            s = score_ownership_stability(*args)
            assert 0.0 <= s <= 100.0

    def test_conviction_high_holding_low_pledge(self):
        s = score_promoter_conviction(0.55, 0.05, 1.0)
        assert s >= 75.0

    def test_conviction_high_pledge(self):
        s1 = score_promoter_conviction(0.55, 0.05, 1.0)
        s2 = score_promoter_conviction(0.55, 0.60, 1.0)
        assert s1 > s2


class TestOwnershipDistribution:
    def test_entropy_equal(self):
        h = compute_ownership_entropy({"a": 25.0, "b": 25.0, "c": 25.0, "d": 25.0})
        assert h == pytest.approx(1.0)

    def test_entropy_concentrated(self):
        h = compute_ownership_entropy({"a": 99.0, "b": 1.0})
        assert h < 0.15

    def test_distribution_quality_good(self, good_ownership_data):
        d = good_ownership_data
        s = score_distribution_quality(
            d["promoter_holding_pct"], d["institutional_holding_pct"],
            d["retail_holding_pct"], d["government_holding_pct"],
            d["fii_holding_pct"], d["dii_holding_pct"], d["free_float_pct"],
        )
        assert 0.0 <= s <= 100.0

    def test_distribution_quality_none(self):
        s = score_distribution_quality(None, None, None, None, None, None, None)
        assert 0.0 <= s <= 100.0
