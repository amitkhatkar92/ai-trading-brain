"""tests/unit/investment/company/governance/test_management_statistics.py"""
from __future__ import annotations

import pytest

from iios.investment.company.governance.management_statistics import (
    clamp, safe_mean, score_roic, score_ceo_tenure, score_board_independence,
    score_accruals, score_ocf_to_ni, score_debt_level, score_payout_ratio,
    score_leadership_stability, _label_score,
)


class TestClamp:
    def test_within(self):
        assert clamp(5.0, 0, 10) == 5.0

    def test_below(self):
        assert clamp(-1.0, 0, 10) == 0.0

    def test_above(self):
        assert clamp(15.0, 0, 10) == 10.0


class TestSafeMean:
    def test_basic(self):
        assert safe_mean([10.0, 20.0, 30.0]) == 20.0

    def test_with_nones(self):
        assert safe_mean([None, 10.0, None]) == 10.0

    def test_empty(self):
        assert safe_mean([]) is None


class TestScoreROIC:
    def test_exceptional(self):
        assert score_roic(0.25) == pytest.approx(100.0)

    def test_good(self):
        s = score_roic(0.15)
        assert 55 < s < 80

    def test_poor(self):
        assert score_roic(0.0) == pytest.approx(0.0)

    def test_none(self):
        assert score_roic(None) == 0.0

    def test_range(self):
        for r in [0.0, 0.05, 0.10, 0.15, 0.20, 0.30]:
            assert 0.0 <= score_roic(r) <= 100.0


class TestScoreCeoTenure:
    def test_optimal(self):
        s = score_ceo_tenure(8.0)
        assert s >= 80.0

    def test_very_new(self):
        assert score_ceo_tenure(0.5) == pytest.approx(30.0)

    def test_long_tenure(self):
        s1 = score_ceo_tenure(10.0)
        s2 = score_ceo_tenure(25.0)
        assert s1 > s2   # entrenchment risk

    def test_none(self):
        assert score_ceo_tenure(None) == 50.0

    def test_range(self):
        for t in [0, 1, 3, 8, 15, 20, 30]:
            s = score_ceo_tenure(float(t))
            assert 0.0 <= s <= 100.0


class TestScoreBoardIndependence:
    def test_excellent(self):
        assert score_board_independence(0.75) == pytest.approx(100.0)

    def test_weak(self):
        s = score_board_independence(0.20)
        assert s < 40

    def test_none(self):
        assert score_board_independence(None) == 30.0

    def test_range(self):
        for r in [0.0, 0.25, 0.50, 0.66, 0.80, 1.0]:
            s = score_board_independence(r)
            assert 0.0 <= s <= 100.0


class TestScoreAccruals:
    def test_excellent(self):
        assert score_accruals(0.02) == pytest.approx(100.0)

    def test_concerning(self):
        s = score_accruals(0.20)
        assert s <= 30

    def test_none(self):
        assert score_accruals(None) == 50.0


class TestScoreOcfToNi:
    def test_excellent(self):
        assert score_ocf_to_ni(1.20) >= 100.0

    def test_below_one(self):
        s = score_ocf_to_ni(0.60)
        assert s <= 30

    def test_none(self):
        assert score_ocf_to_ni(None) == 50.0


class TestScoreDebtLevel:
    def test_low_debt(self):
        assert score_debt_level(0.1) >= 85

    def test_high_debt(self):
        assert score_debt_level(3.0) < 25

    def test_negative_equity(self):
        assert score_debt_level(-1.0) == 0.0

    def test_none(self):
        assert score_debt_level(None) == 50.0


class TestScorePayoutRatio:
    def test_optimal(self):
        assert score_payout_ratio(0.35) >= 80

    def test_high(self):
        assert score_payout_ratio(0.90) < 55

    def test_none(self):
        assert score_payout_ratio(None) == 50.0


class TestScoreLeadershipStability:
    def test_stable(self):
        s = score_leadership_stability(8.0, 0, False)
        assert s >= 75

    def test_chaotic(self):
        s = score_leadership_stability(2.0, 4, True)
        assert s < 50

    def test_ceo_chairman_penalty(self):
        s1 = score_leadership_stability(8.0, 0, False)
        s2 = score_leadership_stability(8.0, 0, True)
        assert s2 < s1


class TestLabelScore:
    @pytest.mark.parametrize("score,expected", [
        (85, "exceptional"), (70, "strong"), (50, "adequate"),
        (30, "weak"), (10, "poor"),
    ])
    def test_labels(self, score, expected):
        assert _label_score(float(score)) == expected
