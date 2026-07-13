"""tests/unit/investment/company/valuation/test_margin_of_safety.py"""
from __future__ import annotations

import pytest
from iios.investment.company.valuation.margin_of_safety import MarginOfSafetyEngine
from iios.investment.company.valuation.fair_value_estimate import (
    FairValueEstimate, ValuationRange, classify_margin_of_safety,
)
from iios.investment.company.valuation.valuation_model import ValuationBand


@pytest.fixture()
def engine():
    return MarginOfSafetyEngine()


def _fv(intrinsic: float) -> FairValueEstimate:
    return FairValueEstimate(
        intrinsic_value    = intrinsic,
        value_range        = ValuationRange(low=intrinsic*0.8, mid=intrinsic, high=intrinsic*1.2),
        model_weights_used = {},
        contributing_models= ["dcf"],
        confidence         = 0.7,
    )


class TestClassifyMarginOfSafety:
    def test_deeply_undervalued(self):
        assert classify_margin_of_safety(50.0) == ValuationBand.DEEPLY_UNDERVALUED

    def test_undervalued(self):
        assert classify_margin_of_safety(20.0) == ValuationBand.UNDERVALUED

    def test_fair_value_positive(self):
        assert classify_margin_of_safety(5.0) == ValuationBand.FAIR_VALUE

    def test_fair_value_negative(self):
        assert classify_margin_of_safety(-10.0) == ValuationBand.FAIR_VALUE

    def test_overvalued(self):
        assert classify_margin_of_safety(-25.0) == ValuationBand.OVERVALUED

    def test_significantly_overvalued(self):
        assert classify_margin_of_safety(-50.0) == ValuationBand.SIGNIFICANTLY_OVERVALUED


class TestMarginOfSafetyEngine:
    def test_undervalued_scenario(self, engine):
        fv = _fv(200.0)
        mos = engine.compute(fv, market_price=120.0)
        assert mos is not None
        assert mos.margin_of_safety_pct > 0
        assert mos.is_undervalued is True
        assert mos.is_overvalued is False

    def test_overvalued_scenario(self, engine):
        fv = _fv(100.0)
        mos = engine.compute(fv, market_price=160.0)
        assert mos is not None
        assert mos.margin_of_safety_pct < 0
        assert mos.is_overvalued is True
        assert mos.is_undervalued is False

    def test_fair_value_scenario(self, engine):
        fv = _fv(100.0)
        mos = engine.compute(fv, market_price=100.0)
        assert mos is not None
        assert abs(mos.margin_of_safety_pct) < 1.0

    def test_no_market_price_returns_none(self, engine):
        fv = _fv(200.0)
        assert engine.compute(fv, market_price=None) is None

    def test_zero_market_price_returns_none(self, engine):
        fv = _fv(200.0)
        assert engine.compute(fv, market_price=0.0) is None

    def test_band_is_set(self, engine):
        fv = _fv(300.0)
        mos = engine.compute(fv, market_price=150.0)
        assert mos.band in ValuationBand.__members__.values()

    def test_premium_is_opposite_sign_of_mos(self, engine):
        fv = _fv(200.0)
        mos = engine.compute(fv, market_price=150.0)
        # mos_pct > 0, premium < 0
        assert mos.margin_of_safety_pct > 0
        assert mos.premium_discount_pct < 0

    def test_to_dict_serialisable(self, engine):
        import json
        fv = _fv(200.0)
        mos = engine.compute(fv, market_price=150.0)
        json.dumps(mos.to_dict())
