"""tests/unit/investment/company/growth/test_growth_statistics.py"""
from __future__ import annotations

import math
import pytest

from iios.investment.company.growth.growth_statistics import (
    cagr, cagr_from_series, yoy_growth, growth_rates_from_series,
    trend_from_growth_rates, trend_from_direction_string,
    score_from_cagr, mean_reversion_estimate,
    clamp, safe_mean, safe_median, safe_stdev, coefficient_of_variation,
)
from iios.investment.company.growth.growth_profile import GrowthTrend


class TestCagr:
    def test_positive(self):
        result = cagr(100.0, 161.05, 5)
        assert result is not None
        assert abs(result - 0.10) < 0.001

    def test_negative_growth(self):
        result = cagr(200.0, 100.0, 3)
        assert result is not None
        assert result < 0

    def test_invalid_start(self):
        assert cagr(0.0, 100.0, 5) is None
        assert cagr(-1.0, 100.0, 5) is None

    def test_invalid_years(self):
        assert cagr(100.0, 200.0, 0) is None

    def test_flat(self):
        result = cagr(100.0, 100.0, 5)
        assert result is not None
        assert abs(result) < 1e-9


class TestCagrFromSeries:
    def test_basic(self):
        series = [100.0, 110.0, 121.0]  # 10% CAGR
        result = cagr_from_series(series)
        assert result is not None
        assert abs(result - 0.10) < 0.001

    def test_too_short(self):
        assert cagr_from_series([100.0]) is None
        assert cagr_from_series([]) is None

    def test_with_nones(self):
        result = cagr_from_series([None, 100.0, 121.0])
        assert result is not None  # Nones filtered out


class TestYoyGrowth:
    def test_positive(self):
        assert abs(yoy_growth(110.0, 100.0) - 0.10) < 1e-9

    def test_negative(self):
        assert yoy_growth(90.0, 100.0) == pytest.approx(-0.10)

    def test_zero_prior(self):
        assert yoy_growth(100.0, 0.0) is None

    def test_negative_prior(self):
        assert yoy_growth(100.0, -50.0) is None

    def test_none_inputs(self):
        assert yoy_growth(None, 100.0) is None
        assert yoy_growth(100.0, None) is None


class TestGrowthRatesFromSeries:
    def test_normal(self):
        series = [100.0, 110.0, 121.0, 133.1]
        rates = growth_rates_from_series(series)
        assert len(rates) == 3
        for r in rates:
            assert abs(r - 0.10) < 0.001

    def test_single_element(self):
        assert growth_rates_from_series([100.0]) == []

    def test_with_negatives_in_prior(self):
        series = [100.0, -20.0, 50.0]   # negative prior → None filtered
        rates = growth_rates_from_series(series)
        assert len(rates) < 3  # negative prior yoy is filtered


class TestTrendFromGrowthRates:
    def test_accelerating(self):
        rates = [0.05, 0.10, 0.15, 0.20, 0.25]
        assert trend_from_growth_rates(rates) == GrowthTrend.ACCELERATING

    def test_decelerating(self):
        rates = [0.25, 0.20, 0.15, 0.10, 0.05]
        assert trend_from_growth_rates(rates) == GrowthTrend.DECELERATING

    def test_declining(self):
        rates = [-0.15, -0.20, -0.25]
        result = trend_from_growth_rates(rates)
        assert result in (GrowthTrend.DECLINING, GrowthTrend.DECELERATING)

    def test_volatile(self):
        rates = [0.50, -0.40, 0.60, -0.30, 0.80]
        assert trend_from_growth_rates(rates) == GrowthTrend.VOLATILE

    def test_empty(self):
        assert trend_from_growth_rates([]) == GrowthTrend.INSUFFICIENT_DATA

    def test_stable(self):
        rates = [0.09, 0.10, 0.10, 0.11]
        assert trend_from_growth_rates(rates) == GrowthTrend.STABLE


class TestTrendFromDirectionString:
    @pytest.mark.parametrize("direction,expected", [
        ("improving",    GrowthTrend.STABLE),
        ("accelerating", GrowthTrend.ACCELERATING),
        ("declining",    GrowthTrend.DECLINING),
        ("decelerating", GrowthTrend.DECELERATING),
        ("recovering",   GrowthTrend.RECOVERING),
        ("volatile",     GrowthTrend.VOLATILE),
        (None,           GrowthTrend.INSUFFICIENT_DATA),
        ("",             GrowthTrend.STABLE),
    ])
    def test_mapping(self, direction, expected):
        assert trend_from_direction_string(direction) == expected


class TestScoreFromCagr:
    def test_exceptional(self):
        assert score_from_cagr(0.30) == 100.0

    def test_positive(self):
        assert score_from_cagr(0.10) == pytest.approx(50.0)

    def test_zero(self):
        assert score_from_cagr(0.0) == pytest.approx(0.0)

    def test_negative(self):
        s = score_from_cagr(-0.10)
        assert 0.0 <= s < 50.0

    def test_none(self):
        assert score_from_cagr(None) == 0.0


class TestMeanReversionEstimate:
    def test_high_growth_pulled_down(self):
        est = mean_reversion_estimate(0.40, long_run_mean=0.10, weight=0.60)
        assert est < 0.40
        assert est > 0.10

    def test_none_returns_long_run(self):
        assert mean_reversion_estimate(None, 0.10, 0.60) == 0.10


class TestSafeStatistics:
    def test_mean(self):
        assert safe_mean([1.0, 2.0, 3.0]) == 2.0
        assert safe_mean([]) is None
        assert safe_mean([None, 1.0, None]) == 1.0

    def test_median(self):
        assert safe_median([1.0, 2.0, 3.0]) == 2.0
        assert safe_median([]) is None

    def test_stdev(self):
        assert safe_stdev([2.0, 4.0]) is not None
        assert safe_stdev([1.0]) is None

    def test_cv(self):
        cv = coefficient_of_variation([10.0, 20.0, 30.0])
        assert cv is not None
        assert cv > 0
        # mean = 0 case
        assert coefficient_of_variation([1.0, -1.0]) is None

    def test_clamp(self):
        assert clamp(5.0, 0, 10) == 5.0
        assert clamp(-1.0, 0, 10) == 0.0
        assert clamp(15.0, 0, 10) == 10.0
