"""tests/unit/investment/company/business_quality/test_economic_moat.py"""
import pytest

from iios.investment.company.business_quality.economic_moat import (
    MoatStrength, MoatType,
)
from iios.investment.company.business_quality.moat_detector import MoatDetector
from iios.investment.company.business_quality.competitive_advantage import (
    CompetitiveAdvantageDetector,
)
from tests.unit.investment.company.business_quality.conftest import make_ctx, make_earnings_snapshot
from iios.investment.company.business_quality.assessment_context import AssessmentContext


def make_wide_moat_ctx():
    """High ROIC, high margins, long history → wide moat signals."""
    from tests.unit.investment.company.business_quality.conftest import (
        make_financial_snapshot, make_earnings_snapshot,
    )
    fs = make_financial_snapshot(
        gross_margin=62.0, roic=25.0, net_margin=20.0,
        sga_pct=22.0, capex_pct=3.0, asset_turnover=1.5,
    )
    es = make_earnings_snapshot(
        avg_roic=25.0, avg_gross_margin=62.0, avg_net_margin=20.0,
        history_depth=8,
    )
    return AssessmentContext(ticker="WM", financial_snapshot=fs, earnings_snapshot=es)


def make_no_moat_ctx():
    from tests.unit.investment.company.business_quality.conftest import (
        make_financial_snapshot, make_earnings_snapshot,
    )
    fs = make_financial_snapshot(
        gross_margin=12.0, roic=4.0, net_margin=1.5,
        capex_pct=18.0, asset_turnover=0.8,
    )
    es = make_earnings_snapshot(avg_roic=4.0, avg_gross_margin=12.0, history_depth=5)
    return AssessmentContext(ticker="NM", financial_snapshot=fs, earnings_snapshot=es)


class TestMoatDetector:
    def test_wide_moat_classified_correctly(self):
        ctx = make_wide_moat_ctx()
        profile = MoatDetector().analyze(ctx)
        # Wide moat requires 5+ periods, high ROIC, high GM, 2+ types
        assert profile.moat_strength in [MoatStrength.WIDE, MoatStrength.NARROW]
        assert profile.moat_score > 0.0

    def test_no_moat_for_commodity(self):
        ctx = make_no_moat_ctx()
        profile = MoatDetector().analyze(ctx)
        assert profile.moat_strength in [MoatStrength.NONE, MoatStrength.UNKNOWN]

    def test_high_quality_scores_higher_than_commodity(self):
        hq = MoatDetector().analyze(make_wide_moat_ctx())
        nm = MoatDetector().analyze(make_no_moat_ctx())
        assert hq.moat_score > nm.moat_score

    def test_moat_score_in_range(self, ctx_high_quality):
        profile = MoatDetector().analyze(ctx_high_quality)
        assert 0.0 <= profile.moat_score <= 100.0

    def test_periods_analyzed_populated(self, ctx_high_quality):
        profile = MoatDetector().analyze(ctx_high_quality)
        assert profile.periods_analyzed >= 0

    def test_avg_roic_populated(self, ctx_high_quality):
        profile = MoatDetector().analyze(ctx_high_quality)
        assert profile.avg_roic is not None

    def test_avg_gross_margin_populated(self, ctx_high_quality):
        profile = MoatDetector().analyze(ctx_high_quality)
        assert profile.avg_gross_margin is not None

    def test_minimal_context_does_not_crash(self, ctx_minimal):
        profile = MoatDetector().analyze(ctx_minimal)
        assert profile.moat_strength == MoatStrength.UNKNOWN
        assert profile.moat_score == pytest.approx(0.0)

    def test_component_scores_in_range(self, ctx_high_quality):
        profile = MoatDetector().analyze(ctx_high_quality)
        for attr in ["brand_score", "cost_advantage_score", "scale_score",
                     "switching_cost_score", "ip_score"]:
            val = getattr(profile, attr)
            assert 0.0 <= val <= 100.0, f"{attr}={val} out of range"

    def test_to_dict_has_required_keys(self, ctx_high_quality):
        d = MoatDetector().analyze(ctx_high_quality).to_dict()
        for key in ["moat_strength", "moat_score", "detected_moat_types",
                    "avg_roic", "brand_score", "periods_analyzed"]:
            assert key in d

    def test_exceptional_roic_flag(self):
        ctx = make_wide_moat_ctx()
        profile = MoatDetector().analyze(ctx)
        # avg_roic >= 20 should add flag
        assert "exceptional_roic" in profile.flags


class TestCompetitiveAdvantageDetector:
    def test_brand_signal_for_high_gm(self):
        ctx = make_wide_moat_ctx()
        signals = CompetitiveAdvantageDetector().detect(ctx)
        brand_signals = [s for s in signals if s.moat_type == MoatType.BRAND]
        assert len(brand_signals) >= 1

    def test_cost_advantage_signal_for_high_roic(self):
        ctx = make_wide_moat_ctx()
        signals = CompetitiveAdvantageDetector().detect(ctx)
        ca_signals = [s for s in signals if s.moat_type == MoatType.COST_ADVANTAGE]
        assert len(ca_signals) >= 1

    def test_no_signals_for_commodity(self):
        ctx = make_no_moat_ctx()
        signals = CompetitiveAdvantageDetector().detect(ctx)
        high_strength = [s for s in signals if s.strength >= 0.50]
        assert len(high_strength) == 0

    def test_signal_strength_in_range(self, ctx_high_quality):
        signals = CompetitiveAdvantageDetector().detect(ctx_high_quality)
        for s in signals:
            assert 0.0 <= s.strength <= 1.0

    def test_signal_evidence_populated(self, ctx_high_quality):
        signals = CompetitiveAdvantageDetector().detect(ctx_high_quality)
        for s in signals:
            assert len(s.evidence) >= 1

    def test_to_dict(self, ctx_high_quality):
        signals = CompetitiveAdvantageDetector().detect(ctx_high_quality)
        for s in signals:
            d = s.to_dict()
            assert "moat_type" in d
            assert "strength" in d
