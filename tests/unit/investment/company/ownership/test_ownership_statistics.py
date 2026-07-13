"""tests/unit/investment/company/ownership/test_ownership_statistics.py"""
from __future__ import annotations

import pytest

from iios.investment.company.ownership.ownership_statistics import (
    clamp, safe_mean, pct_to_100,
    score_promoter_holding, score_institutional_holding,
    score_free_float, score_insider_holding,
    score_pledge_risk, score_promoter_stability,
    score_institutional_change, score_insider_buying,
    score_top10_concentration, score_dividend_policy,
    score_buyback_quality, score_roic_spread,
    score_roe_sustainability, score_dilution_risk,
    _label_ownership_score,
)


class TestClamp:
    def test_within(self): assert clamp(50.0) == 50.0
    def test_below(self):  assert clamp(-5.0) == 0.0
    def test_above(self):  assert clamp(105.0) == 100.0


class TestSafeMean:
    def test_basic(self):     assert safe_mean([10.0, 20.0]) == 15.0
    def test_nones(self):     assert safe_mean([None, 10.0]) == 10.0
    def test_empty(self):     assert safe_mean([]) is None


class TestPctNormalize:
    def test_fraction(self):  assert pct_to_100(0.52) == pytest.approx(52.0)
    def test_already(self):   assert pct_to_100(52.0) == pytest.approx(52.0)
    def test_none(self):      assert pct_to_100(None) is None


class TestScorePromoterHolding:
    def test_optimal(self):
        s = score_promoter_holding(0.52)
        assert s >= 80.0

    def test_too_low(self):
        s = score_promoter_holding(0.05)
        assert s < 30.0

    def test_too_high(self):
        s1 = score_promoter_holding(0.65)
        s2 = score_promoter_holding(0.90)
        assert s1 > s2

    def test_none(self):
        s = score_promoter_holding(None)
        assert s == pytest.approx(35.0)

    def test_range(self):
        for v in [0.10, 0.30, 0.52, 0.70, 0.85]:
            assert 0.0 <= score_promoter_holding(v) <= 100.0


class TestScoreInstitutionalHolding:
    def test_high(self):
        s = score_institutional_holding(0.35)
        assert s >= 75.0

    def test_negligible(self):
        assert score_institutional_holding(0.02) < 30.0

    def test_none(self):
        assert score_institutional_holding(None) == pytest.approx(30.0)


class TestScoreFreeFloat:
    def test_optimal(self):
        s = score_free_float(0.40)
        assert s >= 80.0

    def test_very_low(self):
        assert score_free_float(0.05) < 20.0

    def test_very_high(self):
        s1 = score_free_float(0.60)
        s2 = score_free_float(0.95)
        assert s1 > s2


class TestScoreInsiderHolding:
    def test_high_ceo(self):
        assert score_insider_holding(0.05) >= 70.0

    def test_zero(self):
        assert score_insider_holding(0.0) == 0.0

    def test_none(self):
        assert score_insider_holding(None) == pytest.approx(35.0)


class TestScorePledgeRisk:
    def test_low_pledge(self):
        assert score_pledge_risk(0.05) < 15.0

    def test_high_pledge(self):
        assert score_pledge_risk(0.60) >= 60.0

    def test_none(self):
        assert score_pledge_risk(None) == pytest.approx(20.0)

    def test_range(self):
        for v in [0, 0.1, 0.3, 0.5, 0.8, 1.0]:
            assert 0.0 <= score_pledge_risk(v) <= 100.0


class TestScorePromoterStability:
    def test_stable(self):
        s = score_promoter_stability(0.5, 1.5)
        assert s >= 65.0

    def test_selling(self):
        s = score_promoter_stability(-4.0, -8.0)
        assert s < 30.0

    def test_both_none(self):
        assert score_promoter_stability(None, None) == 50.0


class TestScoreInstitutionalChange:
    def test_increasing(self):
        assert score_institutional_change(2.0) >= 80.0

    def test_decreasing(self):
        assert score_institutional_change(-4.0) < 30.0

    def test_none(self):
        assert score_institutional_change(None) == 50.0


class TestScoreInsiderBuying:
    def test_net_buying(self):
        s = score_insider_buying(8, 1, 70.0)
        assert s >= 70.0

    def test_net_selling(self):
        s = score_insider_buying(0, 5, -80.0)
        assert s < 25.0

    def test_no_activity(self):
        assert score_insider_buying(0, 0, None) == pytest.approx(50.0)


class TestScoreTop10Concentration:
    def test_optimal(self):
        s = score_top10_concentration(0.55)
        assert s >= 80.0

    def test_dispersed(self):
        assert score_top10_concentration(0.15) < 45.0

    def test_none(self):
        assert score_top10_concentration(None) == pytest.approx(50.0)


class TestScoreDividendPolicy:
    def test_optimal_payout(self):
        s = score_dividend_policy(0.35, 0.12)
        assert s >= 80.0

    def test_unsustainable(self):
        s = score_dividend_policy(0.95, -0.05)
        assert s < 40.0


class TestScoreBuybackQuality:
    def test_high_roic(self):
        s = score_buyback_quality(0.22, 0.15)
        assert s >= 80.0

    def test_none(self):
        s = score_buyback_quality(None, None)
        assert 0.0 <= s <= 100.0


class TestScoreROICSpread:
    def test_above_wacc(self):
        s = score_roic_spread(0.20)
        assert s >= 80.0

    def test_below_wacc(self):
        s = score_roic_spread(0.05)
        assert s < 50.0

    def test_none(self):
        assert 0.0 <= score_roic_spread(None) <= 100.0


class TestScoreROESustainability:
    def test_strong(self):
        assert score_roe_sustainability(0.25, 0.30) >= 80.0

    def test_none_roe(self):
        assert 0.0 <= score_roe_sustainability(None, None) <= 100.0


class TestScoreDilutionRisk:
    def test_low_esop(self):
        assert score_dilution_risk(0.01) < 15.0

    def test_high_esop(self):
        assert score_dilution_risk(0.10) >= 55.0

    def test_none(self):
        assert score_dilution_risk(None) < 25.0


class TestLabelOwnershipScore:
    @pytest.mark.parametrize("score,expected", [
        (85, "exceptional"), (68, "strong"), (55, "adequate"),
        (38, "weak"), (15, "poor"),
    ])
    def test_labels(self, score, expected):
        assert _label_ownership_score(float(score)) == expected
