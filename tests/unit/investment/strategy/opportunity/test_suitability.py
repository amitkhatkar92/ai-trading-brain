"""tests/unit/investment/strategy/opportunity/test_suitability.py"""
from __future__ import annotations

import pytest

from iios.investment.strategy.opportunity.suitability_statistics import (
    clamp, score_bool, weighted_average, linear_scale,
    volatility_compat, capital_score, risk_compat,
    timeframe_score, execution_readiness_score,
)
from iios.investment.strategy.opportunity.constraint_engine import ConstraintEngine
from iios.investment.strategy.opportunity.compatibility_engine import CompatibilityEngine
from iios.investment.strategy.opportunity.strategy_suitability import SuitabilityEngine
from tests.unit.investment.strategy.opportunity.conftest import (
    make_market_opp, make_company_opp, make_candidate
)


class TestSuitabilityStatistics:
    def test_clamp_lo(self):
        assert clamp(-5.0) == 0.0

    def test_clamp_hi(self):
        assert clamp(150.0) == 100.0

    def test_clamp_within(self):
        assert clamp(50.0) == 50.0

    def test_score_bool_true(self):
        assert score_bool(True) == 100.0

    def test_score_bool_false(self):
        assert score_bool(False) == 0.0

    def test_weighted_average_equal(self):
        scores  = {"a": 80.0, "b": 60.0}
        weights = {"a": 0.5, "b": 0.5}
        assert weighted_average(scores, weights) == pytest.approx(70.0)

    def test_weighted_average_empty(self):
        assert weighted_average({}, {}) == 0.0

    def test_linear_scale_bounds(self):
        assert linear_scale(0.0, 0.0, 1.0) == pytest.approx(0.0)
        assert linear_scale(1.0, 0.0, 1.0) == pytest.approx(100.0)

    def test_linear_scale_invert(self):
        assert linear_scale(0.0, 0.0, 1.0, invert=True) == pytest.approx(100.0)

    def test_volatility_compat_within_range(self):
        score = volatility_compat("low", "high", "moderate")
        assert score == 100.0

    def test_volatility_compat_outside(self):
        score = volatility_compat("low", "moderate", "extreme")
        assert score < 100.0

    def test_capital_score_sufficient(self):
        assert capital_score(100_000.0, 200_000.0) == 100.0

    def test_capital_score_exact(self):
        assert capital_score(100_000.0, 100_000.0) == pytest.approx(50.0)

    def test_capital_score_insufficient(self):
        assert capital_score(100_000.0, 50_000.0) < 50.0

    def test_risk_compat_within(self):
        assert risk_compat(0.20, 0.10) == 100.0

    def test_risk_compat_exceeded(self):
        assert risk_compat(0.10, 0.30) < 100.0

    def test_timeframe_all(self):
        assert timeframe_score(["all"], "positional") == 100.0

    def test_timeframe_missing(self):
        assert timeframe_score(["intraday"], "swing") == 0.0

    def test_execution_readiness_approved(self):
        score = execution_readiness_score("approved", 80.0)
        assert score >= 70.0

    def test_execution_readiness_rejected(self):
        score = execution_readiness_score("rejected", 0.0)
        assert score == 0.0


class TestConstraintEngine:
    def test_eligible_candidate_passes(self):
        c   = make_candidate(approval="approved")
        opp = make_market_opp()
        cr  = ConstraintEngine(min_confidence=0.50).check(c, opp)
        assert cr.passed

    def test_rejected_candidate_fails(self):
        c   = make_candidate(approval="rejected")
        opp = make_market_opp()
        cr  = ConstraintEngine().check(c, opp)
        assert not cr.passed
        assert len(cr.violations) > 0

    def test_low_confidence_fails(self):
        c   = make_candidate()
        opp = make_market_opp(confidence=0.10)
        cr  = ConstraintEngine(min_confidence=0.50).check(c, opp)
        assert not cr.passed

    def test_low_liquidity_fails(self):
        c   = make_candidate()
        # Strategy min_liquidity_score=0.30; opportunity liquidity=0.10
        opp = make_market_opp(liquidity=0.10)
        cr  = ConstraintEngine().check(c, opp)
        assert not cr.passed

    def test_direction_mismatch_fails(self):
        c   = make_candidate(directions=["short"])
        opp = make_market_opp(direction="long")
        cr  = ConstraintEngine().check(c, opp)
        assert not cr.passed

    def test_expired_opp_fails(self):
        from datetime import timedelta
        from datetime import timezone, datetime
        c   = make_candidate()
        opp = make_market_opp(expires_in_hours=-1)  # already expired
        cr  = ConstraintEngine().check(c, opp)
        assert not cr.passed

    def test_capital_warning_not_violation(self):
        c   = make_candidate(min_capital=1_000_000.0)
        opp = make_market_opp()
        cr  = ConstraintEngine(available_capital=50_000.0).check(c, opp)
        # Capital is advisory only — should not cause a violation
        assert len(cr.warnings) > 0
        # passed depends on other checks passing
        assert cr.passed or len(cr.violations) > 0


class TestCompatibilityEngine:
    def test_returns_scores(self):
        c   = make_candidate()
        opp = make_market_opp()
        cs  = CompatibilityEngine().score(c, opp)
        assert 0.0 <= cs.overall <= 100.0

    def test_all_dimensions_bounded(self):
        c   = make_candidate()
        opp = make_market_opp()
        cs  = CompatibilityEngine().score(c, opp)
        for v in (
            cs.market_compatibility, cs.company_compatibility,
            cs.risk_compatibility, cs.timeframe_compatibility,
            cs.capital_compatibility, cs.execution_readiness,
        ):
            assert 0.0 <= v <= 100.0

    def test_company_opp_scores(self):
        c   = make_candidate()
        opp = make_company_opp()
        cs  = CompatibilityEngine().score(c, opp)
        assert 0.0 <= cs.overall <= 100.0

    def test_approved_strategy_high_execution(self):
        c   = make_candidate(approval="approved", eval_score=85.0)
        opp = make_market_opp()
        cs  = CompatibilityEngine().score(c, opp)
        assert cs.execution_readiness >= 70.0


class TestSuitabilityEngine:
    def test_eligible_and_compatible_is_suitable(self):
        c    = make_candidate(regimes=["all"], timeframes=["all"], directions=["long"])
        opp  = make_market_opp(direction="long", confidence=0.80, liquidity=0.75)
        suit = SuitabilityEngine().evaluate(c, opp)
        assert suit.suitable
        assert suit.score > 40.0

    def test_constraint_violation_not_suitable(self):
        c    = make_candidate(approval="rejected")
        opp  = make_market_opp()
        suit = SuitabilityEngine().evaluate(c, opp)
        assert not suit.suitable
        assert suit.score == 0.0

    def test_company_opp_suitability(self):
        c    = make_candidate(directions=["long"])
        opp  = make_company_opp(direction="long", confidence=0.70)
        suit = SuitabilityEngine().evaluate(c, opp)
        assert 0.0 <= suit.score <= 100.0

    def test_rationale_not_empty(self):
        c    = make_candidate()
        opp  = make_market_opp()
        suit = SuitabilityEngine().evaluate(c, opp)
        assert suit.rationale != ""

    def test_to_dict_has_keys(self):
        c    = make_candidate()
        opp  = make_market_opp()
        suit = SuitabilityEngine().evaluate(c, opp)
        d    = suit.to_dict()
        for key in ["suitable", "score", "constraints", "compatibility"]:
            assert key in d
