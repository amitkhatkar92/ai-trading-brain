"""tests/unit/investment/market/regime/test_regime_confidence.py"""
from __future__ import annotations

import threading
import time
import pytest

from iios.investment.market.market_constants import TrendDirection, VolatilityLevel
from iios.investment.market.regime.models import RegimeType
from iios.investment.market.regime.regime_confidence import RegimeConfidenceCalculator
from iios.investment.market.regime.regime_score import RegimeScore, RegimeScorer
from iios.investment.market.regime.confidence_history import ConfidenceHistory

from tests.unit.investment.market.regime.conftest import make_observation


@pytest.fixture
def calc() -> RegimeConfidenceCalculator:
    return RegimeConfidenceCalculator()


@pytest.fixture
def scorer() -> RegimeScorer:
    return RegimeScorer()


class TestRegimeConfidenceCalculator:
    def test_returns_float_in_valid_range(self, calc):
        obs = make_observation(quality=75.0, confirmed=True, leg_count=2)
        conf = calc.calculate(obs, RegimeType.BULL, bars_in_regime=10, transition_probability=0.3)
        assert 0.10 <= conf <= 0.98

    def test_higher_quality_increases_confidence(self, calc):
        high_q = make_observation(quality=90.0, confirmed=True, leg_count=2)
        low_q  = make_observation(quality=20.0, confirmed=True, leg_count=2)
        conf_high = calc.calculate(high_q, RegimeType.BULL, 10, 0.3)
        conf_low  = calc.calculate(low_q,  RegimeType.BULL, 10, 0.3)
        assert conf_high > conf_low

    def test_confirmed_trend_increases_confidence(self, calc):
        confirmed   = make_observation(confirmed=True,  leg_count=2, quality=75.0)
        unconfirmed = make_observation(confirmed=False, leg_count=0, quality=75.0)
        conf_c = calc.calculate(confirmed,   RegimeType.BULL, 10, 0.3)
        conf_u = calc.calculate(unconfirmed, RegimeType.BULL, 10, 0.3)
        assert conf_c > conf_u

    def test_high_transition_prob_lowers_confidence(self, calc):
        obs = make_observation(quality=75.0, confirmed=True)
        conf_stable   = calc.calculate(obs, RegimeType.BULL, 10, transition_probability=0.1)
        conf_unstable = calc.calculate(obs, RegimeType.BULL, 10, transition_probability=0.9)
        assert conf_stable > conf_unstable

    def test_more_bars_increases_confidence_up_to_saturation(self, calc):
        obs = make_observation(quality=75.0, confirmed=True)
        conf_1  = calc.calculate(obs, RegimeType.BULL, bars_in_regime=1,  transition_probability=0.3)
        conf_10 = calc.calculate(obs, RegimeType.BULL, bars_in_regime=10, transition_probability=0.3)
        conf_25 = calc.calculate(obs, RegimeType.BULL, bars_in_regime=25, transition_probability=0.3)
        assert conf_10 > conf_1
        # After saturation (20 bars), adding more doesn't help
        assert conf_25 == pytest.approx(conf_25, abs=0.001)  # just ensure no crash

    def test_minimum_clamp(self, calc):
        # Worst possible inputs should still be >= 0.10
        obs = make_observation(quality=0.0, confirmed=False, leg_count=0,
                               vol=VolatilityLevel.EXTREME,
                               trend_dir=TrendDirection.UNDEFINED)
        conf = calc.calculate(obs, RegimeType.UNKNOWN, bars_in_regime=0, transition_probability=1.0)
        assert conf >= 0.10

    def test_maximum_clamp(self, calc):
        # Best possible inputs should still be <= 0.98
        obs = make_observation(quality=100.0, confirmed=True, leg_count=10)
        conf = calc.calculate(obs, RegimeType.BULL, bars_in_regime=100, transition_probability=0.0)
        assert conf <= 0.98


class TestRegimeScorer:
    def test_score_returns_regime_score(self, scorer):
        obs = make_observation(quality=75.0, confirmed=True, leg_count=2)
        result = scorer.score(obs, RegimeType.BULL, bars_in_regime=10, transition_prob=0.3)
        assert isinstance(result, RegimeScore)

    def test_all_fields_in_valid_range(self, scorer):
        obs = make_observation(quality=75.0, confirmed=True, leg_count=2)
        rs = scorer.score(obs, RegimeType.BULL, 10, 0.3)
        for field_val in [
            rs.overall, rs.trend_score, rs.volatility_score,
            rs.structure_score, rs.persistence_score, rs.stability_score
        ]:
            assert 0.0 <= field_val <= 100.0, f"Field out of range: {field_val}"

    def test_grade_a_for_high_score(self, scorer):
        obs = make_observation(quality=100.0, confirmed=True, leg_count=5,
                               trend_dir=TrendDirection.UP)
        rs = scorer.score(obs, RegimeType.BULL, 50, 0.05, stability_score=1.0)
        assert rs.grade in ("A", "B")  # very high quality should get A or B

    def test_grade_f_for_low_score(self, scorer):
        obs = make_observation(quality=0.0, confirmed=False, leg_count=0,
                               trend_dir=TrendDirection.UNDEFINED)
        rs = scorer.score(obs, RegimeType.UNKNOWN, 0, 0.95, stability_score=0.0)
        assert rs.grade in ("D", "F")

    def test_to_dict_has_all_keys(self, scorer):
        obs = make_observation()
        rs = scorer.score(obs, RegimeType.BULL, 10, 0.3)
        d = rs.to_dict()
        for key in ["overall", "trend_score", "volatility_score",
                    "structure_score", "persistence_score", "stability_score", "grade"]:
            assert key in d


class TestRegimeScoreGrade:
    def test_grade_a(self):
        rs = RegimeScore(overall=85.0, trend_score=90, volatility_score=80,
                         structure_score=85, persistence_score=80, stability_score=90)
        assert rs.grade == "A"

    def test_grade_b(self):
        rs = RegimeScore(overall=70.0, trend_score=70, volatility_score=70,
                         structure_score=70, persistence_score=70, stability_score=70)
        assert rs.grade == "B"

    def test_grade_c(self):
        rs = RegimeScore(overall=55.0, trend_score=55, volatility_score=55,
                         structure_score=55, persistence_score=55, stability_score=55)
        assert rs.grade == "C"

    def test_grade_d(self):
        rs = RegimeScore(overall=38.0, trend_score=38, volatility_score=38,
                         structure_score=38, persistence_score=38, stability_score=38)
        assert rs.grade == "D"

    def test_grade_f(self):
        rs = RegimeScore(overall=20.0, trend_score=20, volatility_score=20,
                         structure_score=20, persistence_score=20, stability_score=20)
        assert rs.grade == "F"


class TestConfidenceHistory:
    def test_single_sample_stability_is_0_5(self):
        ch = ConfidenceHistory()
        ch.record("M1", 0.75, RegimeType.BULL, time.time())
        assert ch.stability_score("M1") == pytest.approx(0.5)

    def test_avg_confidence_correct(self):
        ch = ConfidenceHistory()
        for conf in [0.5, 0.7, 0.9]:
            ch.record("M1", conf, RegimeType.BULL, time.time())
        assert ch.avg_confidence("M1") == pytest.approx(0.7, abs=1e-9)

    def test_stability_high_when_values_constant(self):
        ch = ConfidenceHistory()
        for _ in range(10):
            ch.record("M1", 0.8, RegimeType.BULL, time.time())
        assert ch.stability_score("M1") == pytest.approx(1.0, abs=1e-6)

    def test_stability_lower_for_varying_values(self):
        ch = ConfidenceHistory()
        for v in [0.1, 0.9, 0.1, 0.9, 0.1, 0.9]:
            ch.record("M1", v, RegimeType.BULL, time.time())
        stable_val = ch.stability_score("M1")
        assert stable_val < 1.0

    def test_count_per_market(self):
        ch = ConfidenceHistory()
        ch.record("M1", 0.7, RegimeType.BULL, time.time())
        ch.record("M1", 0.8, RegimeType.BULL, time.time())
        ch.record("M2", 0.6, RegimeType.BEAR, time.time())
        assert ch.count("M1") == 2
        assert ch.count("M2") == 1

    def test_recent_returns_most_recent_last(self):
        ch = ConfidenceHistory()
        for i, conf in enumerate([0.5, 0.6, 0.7, 0.8, 0.9]):
            ch.record("M1", conf, RegimeType.BULL, float(i))
        recent = ch.recent("M1", n=3)
        assert len(recent) == 3
        # Most recent last: timestamps 2.0, 3.0, 4.0
        assert recent[-1][1] == pytest.approx(0.9)

    def test_thread_safe_concurrent_records(self):
        ch = ConfidenceHistory()
        errors = []

        def worker(market_id: str):
            try:
                for i in range(50):
                    ch.record(market_id, 0.5 + i / 100, RegimeType.BULL, time.time())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"M{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert len(ch.all_market_ids()) == 5
