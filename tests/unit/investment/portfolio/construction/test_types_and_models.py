"""tests/unit/investment/portfolio/construction/test_types_and_models.py

Tests for construction_types, portfolio_blueprint models, and
InvestmentRecommendation.
"""
from __future__ import annotations

import time
import pytest

from iios.investment.portfolio.construction.construction_types import (
    AssetClass,
    ConstructionStatus,
    ConstructionType,
    ConstraintOutcome,
    ConstraintSeverity,
    MarketCapCategory,
    QualityDimension,
    ValidationCategory,
    ValidationOutcome,
    WeightingMethod,
)
from iios.investment.portfolio.construction.portfolio_blueprint import (
    ConstructionRequest,
    ConstructionResult,
    InvestmentRecommendation,
    PortfolioBlueprint,
    PortfolioSlot,
)
from iios.investment.portfolio.construction.construction_types import (
    ConstructionDirection,
    SelectionCriterion,
)


class TestConstructionStatus:
    def test_completed_is_terminal(self):
        assert ConstructionStatus.COMPLETED.is_terminal
        assert ConstructionStatus.FAILED.is_terminal
        assert ConstructionStatus.CANCELLED.is_terminal

    def test_in_progress_not_terminal(self):
        assert not ConstructionStatus.IN_PROGRESS.is_terminal
        assert not ConstructionStatus.PENDING.is_terminal

    def test_completed_is_successful(self):
        assert ConstructionStatus.COMPLETED.is_successful
        assert not ConstructionStatus.FAILED.is_successful

    def test_str_value(self):
        assert ConstructionStatus.COMPLETED == "completed"


class TestWeightingMethod:
    def test_all_methods_have_string_values(self):
        for m in WeightingMethod:
            assert isinstance(m.value, str)

    def test_equal_value(self):
        assert WeightingMethod.EQUAL == "equal"


class TestAssetClass:
    def test_equity_value(self):
        assert AssetClass.EQUITY == "equity"

    def test_unknown_exists(self):
        assert AssetClass.UNKNOWN == "unknown"


class TestInvestmentRecommendation:
    def test_default_fields(self):
        r = InvestmentRecommendation(symbol="AAPL", name="Apple")
        assert r.symbol == "AAPL"
        assert r.conviction == 0.5
        assert r.confidence == 0.5
        assert r.direction == ConstructionDirection.LONG
        assert not r.is_expired

    def test_quality_score(self):
        r = InvestmentRecommendation(confidence=0.8, risk_score=0.2)
        assert abs(r.quality_score - 0.64) < 1e-6

    def test_composite_score(self):
        r = InvestmentRecommendation(conviction=1.0, confidence=1.0, risk_score=0.0)
        # composite = 0.4*1 + 0.4*1 + 0.2*(1*1) = 1.0
        assert abs(r.composite_score - 1.0) < 1e-6

    def test_is_long(self):
        r = InvestmentRecommendation(direction=ConstructionDirection.LONG)
        assert r.is_long and not r.is_short

    def test_is_short(self):
        r = InvestmentRecommendation(direction=ConstructionDirection.SHORT)
        assert r.is_short and not r.is_long

    def test_expired_when_valid_until_passed(self):
        r = InvestmentRecommendation(valid_until=time.time() - 1)
        assert r.is_expired

    def test_not_expired_when_future(self):
        r = InvestmentRecommendation(valid_until=time.time() + 3600)
        assert not r.is_expired

    def test_to_dict_keys(self):
        r = InvestmentRecommendation(symbol="TCS")
        d = r.to_dict()
        assert "symbol" in d
        assert "conviction" in d
        assert "quality_score" in d
        assert "composite_score" in d


class TestPortfolioSlot:
    def test_abs_weight_positive(self):
        s = PortfolioSlot(symbol="RELIANCE", target_weight=0.05)
        assert s.abs_weight == 0.05

    def test_abs_weight_short(self):
        s = PortfolioSlot(
            symbol="SBIN",
            target_weight=-0.03,
            direction=ConstructionDirection.SHORT,
        )
        assert s.abs_weight == 0.03

    def test_weight_within_bounds(self):
        s = PortfolioSlot(target_weight=0.05, min_weight=0.0, max_weight=0.10)
        assert s.weight_within_bounds

    def test_to_dict_has_symbol(self):
        s = PortfolioSlot(symbol="INFY")
        assert s.to_dict()["symbol"] == "INFY"


class TestConstructionRequest:
    def test_defaults(self):
        r = ConstructionRequest(portfolio_id="PF-1")
        assert r.portfolio_id == "PF-1"
        assert r.max_holdings == 30
        assert r.min_holdings == 5
        assert r.target_cash_pct == 0.05

    def test_to_dict(self):
        r = ConstructionRequest(portfolio_id="PF-X")
        d = r.to_dict()
        assert "portfolio_id" in d
        assert "weighting_method" in d
        assert "construction_type" in d

    def test_frozen(self):
        r = ConstructionRequest(portfolio_id="PF-1")
        with pytest.raises((AttributeError, TypeError)):
            r.portfolio_id = "CHANGED"  # type: ignore


class TestConstructionResult:
    def test_succeeded_status(self):
        r = ConstructionResult(status=ConstructionStatus.COMPLETED)
        assert r.succeeded
        assert not r.failed

    def test_failed_status(self):
        r = ConstructionResult(status=ConstructionStatus.FAILED)
        assert r.failed
        assert not r.succeeded

    def test_has_blueprint_false(self):
        r = ConstructionResult()
        assert not r.has_blueprint

    def test_to_dict_status(self):
        r = ConstructionResult(status=ConstructionStatus.COMPLETED)
        assert r.to_dict()["status"] == "completed"


class TestPortfolioBlueprint:
    def _make_blueprint(self) -> PortfolioBlueprint:
        slots = tuple(
            PortfolioSlot(symbol=f"S{i}", target_weight=0.1)
            for i in range(5)
        )
        return PortfolioBlueprint(
            portfolio_id    = "PF-1",
            slots           = slots,
            long_count      = 5,
            long_weight_sum = 0.5,
            cash_weight     = 0.5,
        )

    def test_total_slots(self):
        bp = self._make_blueprint()
        assert bp.total_slots == 5

    def test_not_empty(self):
        bp = self._make_blueprint()
        assert not bp.is_empty

    def test_empty_blueprint(self):
        bp = PortfolioBlueprint()
        assert bp.is_empty

    def test_symbols(self):
        bp = self._make_blueprint()
        assert "S0" in bp.symbols

    def test_to_dict_has_blueprint_id(self):
        bp = self._make_blueprint()
        d = bp.to_dict()
        assert "blueprint_id" in d
        assert "slots" in d
