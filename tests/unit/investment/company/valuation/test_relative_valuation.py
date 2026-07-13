"""tests/unit/investment/company/valuation/test_relative_valuation.py"""
from __future__ import annotations

import pytest
from iios.investment.company.valuation.relative_valuation import RelativeValuationEngine
from iios.investment.company.valuation.valuation_assumptions import RelativeValuationAssumptions
from iios.investment.company.valuation.valuation_model import ValuationStatus


@pytest.fixture()
def engine():
    return RelativeValuationEngine()


@pytest.fixture()
def explicit_targets():
    return RelativeValuationAssumptions(
        target_pe       = 25.0,
        target_ev_ebitda= 16.0,
        target_pb       = 4.0,
        target_pfcf     = 20.0,
    )


class TestRelativeValuationEngine:
    def test_pe_implied_value(self, engine, explicit_targets):
        result = engine.estimate(
            assumptions          = explicit_targets,
            earnings_per_share   = 10.0,
            book_value_per_share = None,
            fcf_per_share        = None,
            revenue_per_share    = None,
            ebitda_per_share     = None,
        )
        assert result.status == ValuationStatus.COMPUTED
        # P/E implied = 10 × 25 = 250
        assert abs(result.intrinsic_value - 250.0) < 1.0

    def test_multiple_methods_blend(self, engine, explicit_targets):
        result = engine.estimate(
            assumptions          = explicit_targets,
            earnings_per_share   = 10.0,
            book_value_per_share = 100.0,
            fcf_per_share        = 8.0,
            revenue_per_share    = None,
            ebitda_per_share     = None,
        )
        assert result.status == ValuationStatus.COMPUTED
        # Blended should be between lowest and highest implied
        assert result.value_low <= result.intrinsic_value <= result.value_high

    def test_no_basis_returns_insufficient(self, engine):
        result = engine.estimate(
            assumptions          = RelativeValuationAssumptions(),
            earnings_per_share   = None,
            book_value_per_share = None,
            fcf_per_share        = None,
            revenue_per_share    = None,
            ebitda_per_share     = None,
        )
        assert result.status == ValuationStatus.INSUFFICIENT_DATA

    def test_historical_median_as_target(self, engine):
        r = RelativeValuationAssumptions()   # no explicit targets
        result = engine.estimate(
            assumptions          = r,
            earnings_per_share   = 10.0,
            book_value_per_share = None,
            fcf_per_share        = None,
            revenue_per_share    = None,
            ebitda_per_share     = None,
            historical_pe        = [20.0, 22.0, 24.0, 21.0, 23.0],
        )
        assert result.status == ValuationStatus.COMPUTED
        # Median PE ≈ 22 → implied ≈ 220
        assert abs(result.intrinsic_value - 220.0) < 5.0

    def test_ev_ebitda_deducts_net_debt(self, engine, explicit_targets):
        result = engine.estimate(
            assumptions          = explicit_targets,
            earnings_per_share   = None,
            book_value_per_share = None,
            fcf_per_share        = None,
            revenue_per_share    = None,
            ebitda_per_share     = 20.0,
            net_debt_per_share   = 50.0,
        )
        assert result.status == ValuationStatus.COMPUTED
        # ev_per_share = 20 * 16 = 320; equity = 320 - 50 = 270
        assert abs(result.intrinsic_value - 270.0) < 10.0

    def test_confidence_in_range(self, engine, explicit_targets):
        result = engine.estimate(
            assumptions          = explicit_targets,
            earnings_per_share   = 10.0,
            book_value_per_share = 100.0,
            fcf_per_share        = 8.0,
            revenue_per_share    = None,
            ebitda_per_share     = None,
        )
        assert 0 < result.confidence <= 1.0
