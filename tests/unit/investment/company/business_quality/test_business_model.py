"""tests/unit/investment/company/business_quality/test_business_model.py"""
import pytest

from iios.investment.company.business_quality.business_model import (
    BusinessModelType, CapexIntensityLabel, RevenueVisibilityLabel,
)
from iios.investment.company.business_quality.business_model_analyzer import BusinessModelAnalyzer
from tests.unit.investment.company.business_quality.conftest import make_ctx


class TestBusinessModelAnalyzer:
    def test_asset_light_classification(self, ctx_high_quality):
        profile = BusinessModelAnalyzer().analyze(ctx_high_quality)
        assert profile.model_type in [
            BusinessModelType.ASSET_LIGHT,
            BusinessModelType.SUBSCRIPTION,
        ]

    def test_asset_heavy_classification(self, ctx_asset_heavy):
        profile = BusinessModelAnalyzer().analyze(ctx_asset_heavy)
        assert profile.model_type in [
            BusinessModelType.ASSET_HEAVY,
            BusinessModelType.MANUFACTURING,
            BusinessModelType.COMMODITY,
        ]

    def test_commodity_classification(self, ctx_commodity):
        profile = BusinessModelAnalyzer().analyze(ctx_commodity)
        assert profile.model_type in [
            BusinessModelType.COMMODITY,
            BusinessModelType.ASSET_HEAVY,
        ]

    def test_capex_intensity_light(self, ctx_high_quality):
        profile = BusinessModelAnalyzer().analyze(ctx_high_quality)
        assert profile.capex_intensity == CapexIntensityLabel.LIGHT
        assert profile.is_asset_light is True

    def test_capex_intensity_heavy(self, ctx_asset_heavy):
        profile = BusinessModelAnalyzer().analyze(ctx_asset_heavy)
        assert profile.capex_intensity == CapexIntensityLabel.HEAVY

    def test_high_gross_margin_revenue_visibility(self, ctx_high_quality):
        profile = BusinessModelAnalyzer().analyze(ctx_high_quality)
        assert profile.gross_margin_level == pytest.approx(60.0)
        assert profile.revenue_visibility in [
            RevenueVisibilityLabel.HIGH, RevenueVisibilityLabel.MEDIUM
        ]

    def test_minimal_context_produces_profile(self, ctx_minimal):
        profile = BusinessModelAnalyzer().analyze(ctx_minimal)
        assert isinstance(profile.model_type, BusinessModelType)
        assert 0.0 <= profile.model_confidence <= 1.0

    def test_model_confidence_set(self, ctx_high_quality):
        profile = BusinessModelAnalyzer().analyze(ctx_high_quality)
        assert profile.model_confidence > 0.0

    def test_to_dict_keys(self, ctx_high_quality):
        d = BusinessModelAnalyzer().analyze(ctx_high_quality).to_dict()
        for key in ["model_type", "capex_intensity", "is_asset_light",
                    "gross_margin_level", "revenue_visibility"]:
            assert key in d

    def test_score_high_quality_higher(self, ctx_high_quality, ctx_commodity):
        a = BusinessModelAnalyzer()
        score_hq  = a.score(a.analyze(ctx_high_quality))
        score_com = a.score(a.analyze(ctx_commodity))
        assert score_hq > score_com

    def test_rd_intensive_flag(self):
        ctx = make_ctx(rd_pct=8.0, gross_margin=50.0)
        profile = BusinessModelAnalyzer().analyze(ctx)
        assert profile.is_rd_intensive is True
        assert "rd_intensive" in profile.flags

    def test_operating_leverage_score_range(self, ctx_high_quality):
        profile = BusinessModelAnalyzer().analyze(ctx_high_quality)
        assert 0.0 <= profile.operating_leverage_score <= 100.0
