"""tests/unit/investment/portfolio/test_portfolio_intelligence_engine.py
Full test suite for the Portfolio & Risk Intelligence Engine.
Target: ≥ 150 tests.
"""
from __future__ import annotations

import asyncio
import threading
import time

import pytest

from iios.investment.portfolio import (
    # Engine
    PortfolioIntelligenceEngine,
    get_portfolio_engine,
    reset_portfolio_engine,
    # Manager
    PortfolioManager,
    get_portfolio_manager,
    reset_portfolio_manager,
    # Registry
    PortfolioRegistry,
    get_portfolio_registry,
    reset_portfolio_registry,
    # Factory
    PortfolioFactory,
    # Context
    PortfolioContextState,
    get_portfolio_context,
    reset_portfolio_context,
    portfolio_session,
    portfolio_stage_scope,
    # Core
    Position,
    PositionGroup,
    AssetAllocation,
    Portfolio,
    PortfolioSnapshot,
    PortfolioHistory,
    PortfolioProfile,
    PortfolioStatistics,
    PortfolioIntelligence,
    # Risk
    RiskProfile,
    RiskStatistics,
    RiskRegistry,
    DrawdownAnalysis,
    DrawdownEngine,
    RiskAnalyzer,
    RiskEngine,
    # Exposure
    ExposureLimits,
    ExposureReport,
    ExposureTracker,
    ExposureEngine,
    # Allocation
    AllocationConstraints,
    AllocationReport,
    CapitalAllocator,
    AllocationEngine,
    # Analytics
    PerformanceAnalysis,
    PerformanceAnalyzer,
    DiversificationAnalysis,
    DiversificationAnalyzer,
    ConcentrationAnalysis,
    ConcentrationAnalyzer,
    AllocationAnalysis,
    AllocationAnalyzer,
    PortfolioAnalytics,
    PortfolioAnalyzer,
    # Enums
    AllocationStatus,
    AssetClass,
    DrawdownSeverity,
    PortfolioHealthStatus,
    PortfolioObjective,
    PortfolioStatus,
    PortfolioType,
    PositionStatus,
    PositionType,
    RiskCategory,
    RiskLevel,
    # Exceptions
    PortfolioIntelligenceError,
    PortfolioNotFoundError,
    PortfolioAlreadyExistsError,
    PositionNotFoundError,
    PortfolioEngineNotInitializedError,
    PortfolioEngineAlreadyRunningError,
    PortfolioRegistryOverflowError,
    DrawdownLimitExceededError,
    RiskLimitExceededError,
    ExposureLimitExceededError,
)
from iios.investment.portfolio.portfolio_constants import (
    PORTFOLIO_ENGINE_VERSION,
    PORTFOLIO_ENGINE_SYSTEM_ID,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pos(
    ticker:  str   = "TCS",
    qty:     float = 100.0,
    cost:    float = 3_000.0,
    price:   float = 3_300.0,
    sector:  str   = "technology",
    country: str   = "IN",
    asset_class: AssetClass = AssetClass.EQUITY,
) -> Position:
    return PortfolioFactory.make_position(
        ticker        = ticker,
        quantity      = qty,
        avg_cost      = cost,
        current_price = price,
        asset_class   = asset_class,
        sector        = sector,
        country       = country,
    )


def _portfolio_with_positions(n: int = 3, cash: float = 50_000.0) -> Portfolio:
    pf = PortfolioFactory.make_portfolio(name="Test", cash=cash)
    tickers = ["TCS", "INFY", "WIPRO", "HDFCBANK", "RELIANCE", "TATASTEEL", "SUNPHARMA"]
    sectors = ["technology", "technology", "technology", "financials", "energy", "materials", "healthcare"]
    for i in range(min(n, len(tickers))):
        pos = _pos(ticker=tickers[i], sector=sectors[i], qty=10, cost=1_000.0, price=1_100.0)
        pf.add_position(pos)
    return pf


# ─────────────────────────────────────────────────────────────────────────────
# autouse fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_all():
    reset_portfolio_engine()
    reset_portfolio_manager()
    reset_portfolio_registry()
    reset_portfolio_context()
    yield
    reset_portfolio_engine()
    reset_portfolio_manager()
    reset_portfolio_registry()
    reset_portfolio_context()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants & Enums
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version(self):
        assert PORTFOLIO_ENGINE_VERSION == "1.0.0"

    def test_system_id(self):
        assert "portfolio" in PORTFOLIO_ENGINE_SYSTEM_ID

    def test_portfolio_type_equity(self):
        assert PortfolioType.EQUITY.value == "equity"

    def test_risk_level_very_high(self):
        assert RiskLevel.VERY_HIGH.value == "very_high"

    def test_drawdown_severity_critical(self):
        assert DrawdownSeverity.CRITICAL.value == "critical"

    def test_asset_class_unknown(self):
        assert AssetClass.UNKNOWN.value == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_error(self):
        e = PortfolioIntelligenceError("test", code="PR-000")
        assert e.code == "PR-000"

    def test_portfolio_not_found(self):
        e = PortfolioNotFoundError(portfolio_id="P1")
        assert e.portfolio_id == "P1"
        assert isinstance(e, PortfolioIntelligenceError)

    def test_portfolio_already_exists(self):
        e = PortfolioAlreadyExistsError(portfolio_id="P1")
        assert e.portfolio_id == "P1"

    def test_position_not_found(self):
        e = PositionNotFoundError(position_id="X1")
        assert e.position_id == "X1"

    def test_engine_not_initialized(self):
        assert issubclass(PortfolioEngineNotInitializedError, PortfolioIntelligenceError)

    def test_registry_overflow(self):
        e = PortfolioRegistryOverflowError(capacity=5, current=5)
        assert e.capacity == 5

    def test_drawdown_limit(self):
        e = DrawdownLimitExceededError(current_pct=0.25, limit_pct=0.20)
        assert e.current_pct == pytest.approx(0.25)

    def test_risk_limit_exceeded(self):
        e = RiskLimitExceededError(limit_name="concentration", value=0.30)
        assert e.limit_name == "concentration"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Position
# ─────────────────────────────────────────────────────────────────────────────

class TestPosition:
    def test_defaults(self):
        p = Position()
        assert p.position_id != ""
        assert p.asset_class == AssetClass.UNKNOWN

    def test_cost_basis_derived(self):
        p = _pos(qty=100, cost=50.0)
        assert p.cost_basis == pytest.approx(5_000.0)

    def test_market_value_derived(self):
        p = _pos(qty=10, cost=100.0, price=120.0)
        assert p.market_value == pytest.approx(1_200.0)

    def test_update_price(self):
        p = _pos(qty=10, cost=100.0, price=100.0)
        p.update_price(150.0)
        assert p.market_value == pytest.approx(1_500.0)
        assert p.unrealized_pnl == pytest.approx(500.0)

    def test_unrealized_pnl_pct(self):
        p = _pos(qty=10, cost=100.0, price=110.0)
        assert p.unrealized_pnl_pct == pytest.approx(0.10, abs=1e-4)

    def test_to_dict(self):
        p = _pos()
        d = p.to_dict()
        assert "ticker" in d
        assert "market_value" in d


# ─────────────────────────────────────────────────────────────────────────────
# 4. PositionGroup
# ─────────────────────────────────────────────────────────────────────────────

class TestPositionGroup:
    def test_defaults(self):
        pg = PositionGroup(group_name="TECH", dimension="sector")
        assert pg.group_id != ""

    def test_to_dict(self):
        pg = PositionGroup(group_name="IN", dimension="country", total_weight=0.60)
        d = pg.to_dict()
        assert d["total_weight"] == pytest.approx(0.60)

    def test_position_ids(self):
        pg = PositionGroup(position_ids=["p1", "p2"])
        assert len(pg.position_ids) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 5. AssetAllocation
# ─────────────────────────────────────────────────────────────────────────────

class TestAssetAllocation:
    def test_defaults(self):
        aa = AssetAllocation()
        assert aa.asset_class == AssetClass.UNKNOWN

    def test_deviation_computed(self):
        aa = AssetAllocation(target_weight=0.60, actual_weight=0.70)
        assert aa.deviation == pytest.approx(0.10, abs=1e-6)

    def test_overallocated_status(self):
        aa = AssetAllocation(target_weight=0.50, actual_weight=0.60)
        assert aa.status == AllocationStatus.OVERALLOCATED

    def test_within_limits_status(self):
        aa = AssetAllocation(target_weight=0.50, actual_weight=0.52)
        assert aa.status == AllocationStatus.WITHIN_LIMITS

    def test_to_dict(self):
        aa = AssetAllocation(asset_class=AssetClass.EQUITY, actual_weight=0.70)
        d = aa.to_dict()
        assert d["asset_class"] == "equity"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Portfolio
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolio:
    def test_defaults(self):
        pf = Portfolio()
        assert pf.portfolio_id != ""
        assert pf.status == PortfolioStatus.DRAFT

    def test_total_nav_cash_only(self):
        pf = Portfolio(cash=100_000.0)
        assert pf.total_nav == pytest.approx(100_000.0)

    def test_add_position_updates_nav(self):
        pf = Portfolio(cash=50_000.0)
        pos = _pos(qty=10, cost=1_000.0, price=1_200.0)
        pf.add_position(pos)
        assert pf.total_nav == pytest.approx(50_000.0 + 12_000.0)

    def test_remove_position(self):
        pf = Portfolio(cash=50_000.0)
        pos = _pos(qty=10, cost=1_000.0, price=1_000.0)
        pf.add_position(pos)
        pid = pos.position_id
        pf.remove_position(pid)
        assert pf.position_count == 0

    def test_weights_sum_to_one_approx(self):
        pf = _portfolio_with_positions(n=3, cash=0.0)
        weights = [p.weight for p in pf.positions.values()]
        assert sum(weights) == pytest.approx(1.0, abs=0.01)

    def test_by_sector(self):
        pf = _portfolio_with_positions(n=3)
        by_s = pf.by_sector()
        assert isinstance(by_s, dict)
        assert len(by_s) >= 1

    def test_unrealized_pnl(self):
        pf = Portfolio(cash=0.0)
        pf.add_position(_pos(qty=10, cost=1_000.0, price=1_100.0))
        assert pf.unrealized_pnl == pytest.approx(1_000.0)

    def test_to_dict(self):
        pf = Portfolio(name="MyPF", cash=10_000.0)
        d = pf.to_dict()
        assert d["name"] == "MyPF"
        assert "total_nav" in d


# ─────────────────────────────────────────────────────────────────────────────
# 7. PortfolioSnapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioSnapshot:
    def test_defaults(self):
        s = PortfolioSnapshot()
        assert s.snapshot_id != ""
        assert s.health_status == PortfolioHealthStatus.UNKNOWN

    def test_is_stale_fresh(self):
        s = PortfolioSnapshot()
        assert not s.is_stale(ttl_sec=3_600)

    def test_is_stale_old(self):
        s = PortfolioSnapshot()
        s.created_at = time.time() - 7_200
        assert s.is_stale(ttl_sec=3_600)

    def test_to_dict(self):
        s = PortfolioSnapshot(portfolio_id="P1", total_nav=500_000.0)
        d = s.to_dict()
        assert d["total_nav"] == 500_000.0


# ─────────────────────────────────────────────────────────────────────────────
# 8. PortfolioHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioHistory:
    def test_add_and_get_latest(self):
        h = PortfolioHistory()
        s = PortfolioSnapshot(portfolio_id="P1")
        h.add("P1", s)
        assert h.get_latest("P1") is s

    def test_missing_returns_none(self):
        h = PortfolioHistory()
        assert h.get_latest("NOPE") is None

    def test_count(self):
        h = PortfolioHistory()
        for _ in range(5):
            h.add("P1", PortfolioSnapshot(portfolio_id="P1"))
        assert h.count("P1") == 5

    def test_ring_buffer(self):
        h = PortfolioHistory(max_per_portfolio=3)
        for _ in range(10):
            h.add("P1", PortfolioSnapshot(portfolio_id="P1"))
        assert h.count("P1") == 3

    def test_all_portfolios(self):
        h = PortfolioHistory()
        h.add("A", PortfolioSnapshot(portfolio_id="A"))
        h.add("B", PortfolioSnapshot(portfolio_id="B"))
        assert set(h.all_portfolios()) == {"A", "B"}


# ─────────────────────────────────────────────────────────────────────────────
# 9. DrawdownEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestDrawdownEngine:
    def setup_method(self):
        self.eng = DrawdownEngine()

    def _pf(self, nav: float) -> Portfolio:
        pf = Portfolio(cash=nav)
        return pf

    def test_no_drawdown(self):
        pf = self._pf(100_000.0)
        r  = self.eng.analyze(pf, peak_nav=100_000.0)
        assert r.current_drawdown_pct == pytest.approx(0.0, abs=1e-4)
        assert not r.is_in_drawdown

    def test_minor_drawdown(self):
        pf = self._pf(97_000.0)
        r  = self.eng.analyze(pf, peak_nav=100_000.0)
        assert r.drawdown_severity == DrawdownSeverity.MINOR
        assert r.is_in_drawdown

    def test_severe_drawdown(self):
        pf = self._pf(70_000.0)
        r  = self.eng.analyze(pf, peak_nav=100_000.0)
        assert r.drawdown_severity == DrawdownSeverity.SEVERE

    def test_critical_drawdown(self):
        pf = self._pf(60_000.0)
        r  = self.eng.analyze(pf, peak_nav=100_000.0)
        assert r.drawdown_severity == DrawdownSeverity.CRITICAL

    def test_recovery_required(self):
        pf = self._pf(80_000.0)
        r  = self.eng.analyze(pf, peak_nav=100_000.0)
        assert r.recovery_required_pct == pytest.approx(0.25, abs=1e-4)

    def test_zero_nav_safe(self):
        pf = Portfolio()  # nav = 0
        r  = self.eng.analyze(pf, peak_nav=0.0)
        assert isinstance(r, DrawdownAnalysis)


# ─────────────────────────────────────────────────────────────────────────────
# 10. RiskProfile
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskProfile:
    def test_defaults(self):
        rp = RiskProfile()
        assert rp.risk_level == RiskLevel.UNKNOWN

    def test_add_warning(self):
        rp = RiskProfile()
        rp.add_warning("high concentration")
        rp.add_warning("high concentration")   # dedup
        assert len(rp.risk_warnings) == 1

    def test_to_dict(self):
        rp = RiskProfile(portfolio_id="P1", overall_risk_score=75.0)
        d  = rp.to_dict()
        assert d["overall_risk_score"] == 75.0


# ─────────────────────────────────────────────────────────────────────────────
# 11. RiskAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskAnalyzer:
    def setup_method(self):
        self.az  = RiskAnalyzer()
        self.dd  = DrawdownEngine()

    def _analyze(self, pf: Portfolio) -> RiskProfile:
        dd = self.dd.analyze(pf, peak_nav=pf.total_nav)
        return self.az.analyze(pf, dd, hhi=0.1, top_position_weight=0.10, cash_pct=0.10)

    def test_returns_risk_profile(self):
        pf = _portfolio_with_positions(n=3, cash=50_000.0)
        r  = self._analyze(pf)
        assert isinstance(r, RiskProfile)

    def test_risk_score_in_range(self):
        pf = _portfolio_with_positions(n=3, cash=50_000.0)
        r  = self._analyze(pf)
        assert 0 <= r.overall_risk_score <= 100

    def test_high_concentration_raises_risk(self):
        pf = Portfolio(cash=100_000.0)
        dd = self.dd.analyze(pf, peak_nav=100_000.0)
        r  = self.az.analyze(pf, dd, hhi=0.5, top_position_weight=0.50)
        assert r.concentration_risk_score > 50

    def test_risk_level_classified(self):
        pf = _portfolio_with_positions(n=5, cash=50_000.0)
        r  = self._analyze(pf)
        assert r.risk_level != RiskLevel.UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# 12. RiskEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskEngine:
    def test_analyze_returns_profile(self):
        pf  = _portfolio_with_positions(n=3, cash=50_000.0)
        eng = RiskEngine()
        dd  = DrawdownEngine().analyze(pf, peak_nav=pf.total_nav)
        r   = eng.analyze(pf, dd, hhi=0.1, top_position_weight=0.10)
        assert isinstance(r, RiskProfile)

    def test_statistics_tracked(self):
        pf  = _portfolio_with_positions(n=2, cash=20_000.0)
        eng = RiskEngine()
        dd  = DrawdownEngine().analyze(pf, peak_nav=pf.total_nav)
        eng.analyze(pf, dd)
        stats = eng.get_statistics(pf.portfolio_id)
        assert stats is not None
        assert stats.analysis_count == 1

    def test_risk_registry_accessible(self):
        eng = RiskEngine()
        assert isinstance(eng.registry(), RiskRegistry)


# ─────────────────────────────────────────────────────────────────────────────
# 13. ExposureLimits
# ─────────────────────────────────────────────────────────────────────────────

class TestExposureLimits:
    def test_defaults(self):
        lim = ExposureLimits()
        assert lim.max_single_position == pytest.approx(0.25)

    def test_custom_limit(self):
        lim = ExposureLimits(custom_limits={"TCS": 0.15})
        assert lim.get_custom("TCS") == pytest.approx(0.15)

    def test_to_dict(self):
        lim = ExposureLimits()
        d   = lim.to_dict()
        assert "max_sector_exposure" in d


# ─────────────────────────────────────────────────────────────────────────────
# 14. ExposureEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestExposureEngine:
    def test_empty_portfolio(self):
        eng = ExposureEngine()
        pf  = Portfolio(cash=100_000.0)
        r   = eng.analyze(pf)
        assert isinstance(r, ExposureReport)
        assert r.cash_pct == pytest.approx(1.0)

    def test_long_exposure_computed(self):
        eng = ExposureEngine()
        pf  = _portfolio_with_positions(n=3, cash=50_000.0)
        r   = eng.analyze(pf)
        assert r.long_exposure > 0

    def test_by_sector_populated(self):
        eng = ExposureEngine()
        pf  = _portfolio_with_positions(n=3, cash=0.0)
        r   = eng.analyze(pf)
        assert len(r.by_sector) >= 1

    def test_limit_breach_detected(self):
        eng = ExposureEngine()
        lim = ExposureLimits(max_single_position=0.05)   # very tight limit
        pf  = Portfolio(cash=1_000.0)
        # Single position that is 90% of NAV
        pos = _pos(qty=100, cost=100.0, price=100.0)   # mv=10000, nav=11000
        pf.add_position(pos)
        pf.update_cash(1_000.0)
        r   = eng.analyze(pf, limits=lim)
        assert len(r.limit_breaches) > 0

    def test_set_portfolio_limits(self):
        eng = ExposureEngine()
        lim = ExposureLimits(max_single_position=0.10)
        eng.set_limits("P1", lim)
        assert eng.get_limits("P1").max_single_position == pytest.approx(0.10)


# ─────────────────────────────────────────────────────────────────────────────
# 15. AllocationConstraints
# ─────────────────────────────────────────────────────────────────────────────

class TestAllocationConstraints:
    def test_defaults(self):
        c = AllocationConstraints()
        assert c.min_cash_pct == pytest.approx(0.05)

    def test_set_target(self):
        c = AllocationConstraints()
        c.set_target(AssetClass.EQUITY, 0.70)
        assert c.get_target(AssetClass.EQUITY) == pytest.approx(0.70)

    def test_to_dict(self):
        c = AllocationConstraints()
        d = c.to_dict()
        assert "target_allocations" in d


# ─────────────────────────────────────────────────────────────────────────────
# 16. AllocationEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestAllocationEngine:
    def test_analyze_no_targets(self):
        eng = AllocationEngine()
        pf  = _portfolio_with_positions(n=3, cash=50_000.0)
        r   = eng.analyze(pf)
        assert isinstance(r, AllocationReport)
        assert r.allocation_score == pytest.approx(50.0)

    def test_with_targets_deviation(self):
        eng = AllocationEngine()
        con = AllocationConstraints()
        con.set_target(AssetClass.EQUITY, 0.90)   # target 90%, actual ~50%
        pf  = _portfolio_with_positions(n=3, cash=50_000.0)
        r   = eng.analyze(pf, constraints=con)
        assert r.rebalancing_needed

    def test_score_within_range(self):
        eng = AllocationEngine()
        pf  = _portfolio_with_positions(n=3, cash=50_000.0)
        r   = eng.analyze(pf)
        assert 0 <= r.allocation_score <= 100

    def test_set_constraints(self):
        eng = AllocationEngine()
        con = AllocationConstraints(max_single_position=0.10)
        eng.set_constraints("P1", con)
        assert eng.get_constraints("P1").max_single_position == pytest.approx(0.10)


# ─────────────────────────────────────────────────────────────────────────────
# 17. PerformanceAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformanceAnalyzer:
    def test_empty_portfolio(self):
        az = PerformanceAnalyzer()
        r  = az.analyze(Portfolio(cash=100_000.0))
        assert r.performance_score == pytest.approx(50.0)

    def test_positive_pnl_raises_score(self):
        az = PerformanceAnalyzer()
        pf = Portfolio(cash=0.0)
        pf.add_position(_pos(qty=10, cost=100.0, price=150.0))  # +50% pnl
        r  = az.analyze(pf)
        assert r.performance_score > 50.0

    def test_negative_pnl_lowers_score(self):
        az = PerformanceAnalyzer()
        pf = Portfolio(cash=0.0)
        pf.add_position(_pos(qty=10, cost=100.0, price=80.0))   # -20% pnl
        r  = az.analyze(pf)
        assert r.performance_score < 50.0

    def test_to_dict(self):
        az = PerformanceAnalyzer()
        pf = _portfolio_with_positions(n=2)
        r  = az.analyze(pf)
        d  = r.to_dict()
        assert "performance_score" in d


# ─────────────────────────────────────────────────────────────────────────────
# 18. DiversificationAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestDiversificationAnalyzer:
    def test_empty_portfolio(self):
        az = DiversificationAnalyzer()
        r  = az.analyze(Portfolio())
        assert isinstance(r, DiversificationAnalysis)

    def test_single_position_max_hhi(self):
        az = DiversificationAnalyzer()
        pf = Portfolio(cash=0.0)
        pf.add_position(_pos(qty=10, cost=100.0, price=100.0))
        r  = az.analyze(pf)
        assert r.hhi == pytest.approx(1.0, abs=1e-4)
        assert r.diversification_score == pytest.approx(0.0, abs=1.0)

    def test_two_equal_positions(self):
        az = DiversificationAnalyzer()
        pf = Portfolio(cash=0.0)
        for t in ["A", "B"]:
            pf.add_position(_pos(ticker=t, qty=10, cost=100.0, price=100.0))
        r  = az.analyze(pf)
        assert r.hhi == pytest.approx(0.5, abs=1e-4)

    def test_more_positions_better_score(self):
        az = DiversificationAnalyzer()
        pf1 = Portfolio(cash=0.0)
        pf1.add_position(_pos(qty=10, cost=100.0, price=100.0))
        pf5 = _portfolio_with_positions(n=5, cash=0.0)
        r1  = az.analyze(pf1)
        r5  = az.analyze(pf5)
        assert r5.diversification_score > r1.diversification_score

    def test_to_dict(self):
        az = DiversificationAnalyzer()
        r  = az.analyze(_portfolio_with_positions(n=3))
        d  = r.to_dict()
        assert "hhi" in d


# ─────────────────────────────────────────────────────────────────────────────
# 19. ConcentrationAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestConcentrationAnalyzer:
    def test_empty(self):
        az = ConcentrationAnalyzer()
        r  = az.analyze(Portfolio())
        assert isinstance(r, ConcentrationAnalysis)

    def test_single_position_concentrated(self):
        az = ConcentrationAnalyzer()
        pf = Portfolio(cash=0.0)
        pf.add_position(_pos(qty=10, cost=100.0, price=100.0))
        r  = az.analyze(pf)
        assert r.is_concentrated
        assert r.top1_weight == pytest.approx(1.0, abs=1e-4)

    def test_balanced_not_concentrated(self):
        az = ConcentrationAnalyzer()
        pf = _portfolio_with_positions(n=5, cash=50_000.0)
        r  = az.analyze(pf)
        assert not r.is_concentrated

    def test_to_dict(self):
        az = ConcentrationAnalyzer()
        r  = az.analyze(_portfolio_with_positions(n=3))
        d  = r.to_dict()
        assert "top1_weight" in d


# ─────────────────────────────────────────────────────────────────────────────
# 20. PortfolioAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioAnalyzer:
    def setup_method(self):
        self.az   = PortfolioAnalyzer()
        self.dd   = DrawdownEngine()
        self.exp  = ExposureEngine()
        self.alc  = AllocationEngine()

    def _run(self, pf: Portfolio) -> PortfolioAnalytics:
        dd  = self.dd.analyze(pf, peak_nav=pf.total_nav)
        exp = self.exp.analyze(pf)
        alc = self.alc.analyze(pf)
        return self.az.analyze(pf, dd, exp, alc)

    def test_returns_analytics(self):
        pf = _portfolio_with_positions(n=3, cash=50_000.0)
        r  = self._run(pf)
        assert isinstance(r, PortfolioAnalytics)

    def test_scores_in_range(self):
        pf = _portfolio_with_positions(n=3, cash=50_000.0)
        r  = self._run(pf)
        for score in [r.diversification_score, r.concentration_score,
                      r.liquidity_score, r.performance_score]:
            assert 0 <= score <= 100

    def test_by_sector_populated(self):
        pf = _portfolio_with_positions(n=3, cash=0.0)
        r  = self._run(pf)
        assert len(r.by_sector) >= 1

    def test_to_dict(self):
        pf = _portfolio_with_positions(n=3)
        r  = self._run(pf)
        d  = r.to_dict()
        assert "hhi" in d
        assert "diversification_score" in d


# ─────────────────────────────────────────────────────────────────────────────
# 21. PortfolioRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioRegistry:
    def test_register_and_check(self):
        r = PortfolioRegistry()
        r.register("P1", "Growth Fund")
        assert r.is_registered("P1")

    def test_duplicate_raises(self):
        r = PortfolioRegistry()
        r.register("P1", "Fund")
        with pytest.raises(PortfolioAlreadyExistsError):
            r.register("P1", "Fund")

    def test_get_info(self):
        r = PortfolioRegistry()
        r.register("P1", "Fund", portfolio_type="equity")
        info = r.get_info("P1")
        assert info["name"] == "Fund"

    def test_not_found_raises(self):
        r = PortfolioRegistry()
        with pytest.raises(PortfolioNotFoundError):
            r.get_info("NOPE")

    def test_overflow(self):
        r = PortfolioRegistry(max_portfolios=2)
        r.register("A", "A")
        r.register("B", "B")
        with pytest.raises(PortfolioRegistryOverflowError):
            r.register("C", "C")

    def test_all_portfolios(self):
        r = PortfolioRegistry()
        r.register("X", "X")
        r.register("Y", "Y")
        assert set(r.all_portfolios()) == {"X", "Y"}

    def test_register_analyzer(self):
        r = PortfolioRegistry()
        r.register_analyzer("az1", object())
        assert r.has_analyzer("az1")

    def test_statistics(self):
        r = PortfolioRegistry()
        r.register("P1", "Fund")
        s = r.statistics()
        assert s["registered_portfolios"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 22. PortfolioContext
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioContext:
    def test_get_context_returns_state(self):
        ctx = get_portfolio_context()
        assert isinstance(ctx, PortfolioContextState)

    def test_request_id_generated(self):
        ctx = get_portfolio_context()
        assert ctx.request_id != ""

    def test_session_manager(self):
        with portfolio_session("req-abc", {"key": "val"}) as ctx:
            assert ctx.request_id == "req-abc"

    def test_stage_scope(self):
        with portfolio_stage_scope("analysis") as ctx:
            assert ctx.stage == "analysis"

    def test_reset_context(self):
        reset_portfolio_context()
        ctx = get_portfolio_context()
        assert ctx is not None


# ─────────────────────────────────────────────────────────────────────────────
# 23. PortfolioFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioFactory:
    def test_make_portfolio(self):
        pf = PortfolioFactory.make_portfolio(name="Growth", cash=100_000.0)
        assert pf.name == "Growth"
        assert pf.cash == 100_000.0

    def test_make_profile(self):
        pf = PortfolioFactory.make_portfolio(name="P")
        pr = PortfolioFactory.make_profile(pf)
        assert pr.portfolio_id == pf.portfolio_id

    def test_make_position(self):
        pos = PortfolioFactory.make_position(ticker="INFY", quantity=50, avg_cost=1_500.0)
        assert pos.ticker == "INFY"
        assert pos.cost_basis == pytest.approx(75_000.0)

    def test_make_snapshot(self):
        s = PortfolioFactory.make_snapshot("P1", total_nav=500_000.0)
        assert s.total_nav == 500_000.0

    def test_position_market_value(self):
        pos = PortfolioFactory.make_position(ticker="X", quantity=100, avg_cost=50.0, current_price=60.0)
        assert pos.market_value == pytest.approx(6_000.0)


# ─────────────────────────────────────────────────────────────────────────────
# 24. PortfolioManager
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioManager:
    def setup_method(self):
        reset_portfolio_registry()
        self.mgr = PortfolioManager(registry=PortfolioRegistry())

    def test_create_portfolio(self):
        pr = self.mgr.create_portfolio(name="Fund", cash=100_000.0)
        assert isinstance(pr, PortfolioProfile)
        assert pr.portfolio.name == "Fund"

    def test_duplicate_create_raises(self):
        pr = self.mgr.create_portfolio(name="Fund", cash=100_000.0)
        with pytest.raises(PortfolioAlreadyExistsError):
            # Re-registering same portfolio_id would raise through registry
            self.mgr._registry.register(pr.portfolio_id, "Fund2")

    def test_get_profile(self):
        pr = self.mgr.create_portfolio(name="Fund")
        p2 = self.mgr.get_profile(pr.portfolio_id)
        assert p2.portfolio_id == pr.portfolio_id

    def test_get_profile_not_found(self):
        with pytest.raises(PortfolioNotFoundError):
            self.mgr.get_profile("NOPE")

    def test_add_position(self):
        pr  = self.mgr.create_portfolio(name="Fund", cash=100_000.0)
        pos = _pos(qty=10, cost=1_000.0, price=1_100.0)
        pf  = self.mgr.add_position(pr.portfolio_id, pos)
        assert pf.position_count == 1

    def test_remove_position(self):
        pr  = self.mgr.create_portfolio(name="Fund", cash=100_000.0)
        pos = _pos()
        self.mgr.add_position(pr.portfolio_id, pos)
        self.mgr.remove_position(pr.portfolio_id, pos.position_id)
        assert pr.portfolio.position_count == 0

    def test_update_position_price(self):
        pr  = self.mgr.create_portfolio(name="Fund", cash=100_000.0)
        pos = _pos(qty=10, cost=1_000.0, price=1_000.0)
        self.mgr.add_position(pr.portfolio_id, pos)
        updated = self.mgr.update_position_price(pr.portfolio_id, pos.position_id, 1_500.0)
        assert updated.current_price == 1_500.0

    def test_analyze_returns_intelligence(self):
        pr = self.mgr.create_portfolio(name="Fund", cash=100_000.0)
        self.mgr.add_position(pr.portfolio_id, _pos(qty=10, cost=1_000.0, price=1_100.0))
        intel = self.mgr.analyze(pr.portfolio_id)
        assert isinstance(intel, PortfolioIntelligence)

    def test_analyze_builds_snapshot(self):
        pr = self.mgr.create_portfolio(name="Fund", cash=50_000.0)
        self.mgr.analyze(pr.portfolio_id)
        snap = self.mgr.summary(pr.portfolio_id)
        assert isinstance(snap, PortfolioSnapshot)

    def test_get_latest(self):
        pr = self.mgr.create_portfolio(name="Fund", cash=50_000.0)
        self.mgr.analyze(pr.portfolio_id)
        latest = self.mgr.get_latest(pr.portfolio_id)
        assert latest.portfolio_id == pr.portfolio_id

    def test_recent(self):
        for i in range(5):
            pr = self.mgr.create_portfolio(name=f"Fund{i}", cash=10_000.0)
            self.mgr.analyze(pr.portfolio_id)
        assert len(self.mgr.recent(3)) == 3

    def test_statistics(self):
        pr = self.mgr.create_portfolio(name="F", cash=10_000.0)
        self.mgr.analyze(pr.portfolio_id)
        s = self.mgr.statistics()
        assert s["analyses_total"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 25. PortfolioIntelligenceEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioIntelligenceEngine:
    def test_not_running_by_default(self):
        eng = PortfolioIntelligenceEngine()
        assert not eng.is_running

    def test_initialize_sets_running(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        assert eng.is_running

    def test_double_initialize_raises(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        with pytest.raises(PortfolioEngineAlreadyRunningError):
            eng.initialize()

    def test_analyze_requires_initialized(self):
        eng = PortfolioIntelligenceEngine()
        with pytest.raises(PortfolioEngineNotInitializedError):
            eng.analyze("P1")

    def test_create_and_analyze(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        pr  = eng.create_portfolio(name="Fund", cash=100_000.0)
        eng.add_position(pr.portfolio_id, _pos(qty=10, cost=1_000.0, price=1_100.0))
        intel = eng.analyze(pr.portfolio_id)
        assert isinstance(intel, PortfolioIntelligence)

    def test_get_profile(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        pr  = eng.create_portfolio(name="F")
        p2  = eng.get_profile(pr.portfolio_id)
        assert p2.portfolio_id == pr.portfolio_id

    def test_get_latest(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        pr  = eng.create_portfolio(name="F", cash=10_000.0)
        eng.analyze(pr.portfolio_id)
        assert eng.get_latest(pr.portfolio_id).portfolio_id == pr.portfolio_id

    def test_recent(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        for i in range(5):
            pr = eng.create_portfolio(name=f"F{i}", cash=10_000.0)
            eng.analyze(pr.portfolio_id)
        assert len(eng.recent(3)) == 3

    def test_summary(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        pr  = eng.create_portfolio(name="F", cash=50_000.0)
        eng.analyze(pr.portfolio_id)
        snap = eng.summary(pr.portfolio_id)
        assert isinstance(snap, PortfolioSnapshot)

    def test_health_running(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        assert eng.health()["status"] == "running"

    def test_health_stopped(self):
        eng = PortfolioIntelligenceEngine()
        assert eng.health()["status"] == "stopped"

    def test_shutdown(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        eng.shutdown()
        assert not eng.is_running

    def test_stats(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        pr  = eng.create_portfolio(name="F", cash=10_000.0)
        eng.analyze(pr.portfolio_id)
        s = eng.stats()
        assert "analyses_total" in s


# ─────────────────────────────────────────────────────────────────────────────
# 26. Async analyze
# ─────────────────────────────────────────────────────────────────────────────

class TestAsync:
    def test_async_analyze(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        pr  = eng.create_portfolio(name="F", cash=50_000.0)

        async def _run():
            return await eng.analyze_async(pr.portfolio_id)

        result = asyncio.run(_run())
        assert isinstance(result, PortfolioIntelligence)

    def test_async_multiple(self):
        eng = PortfolioIntelligenceEngine()
        eng.initialize()
        profiles = [eng.create_portfolio(name=f"F{i}", cash=10_000.0) for i in range(3)]

        async def _run():
            tasks = [eng.analyze_async(p.portfolio_id) for p in profiles]
            return await asyncio.gather(*tasks)

        results = asyncio.run(_run())
        assert len(results) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 27. Singletons
# ─────────────────────────────────────────────────────────────────────────────

class TestSingletons:
    def test_engine_singleton(self):
        e1 = get_portfolio_engine()
        e2 = get_portfolio_engine()
        assert e1 is e2

    def test_reset_engine_creates_new(self):
        e1 = get_portfolio_engine()
        reset_portfolio_engine()
        e2 = get_portfolio_engine()
        assert e1 is not e2

    def test_manager_singleton(self):
        m1 = get_portfolio_manager()
        m2 = get_portfolio_manager()
        assert m1 is m2

    def test_registry_singleton(self):
        r1 = get_portfolio_registry()
        r2 = get_portfolio_registry()
        assert r1 is r2


# ─────────────────────────────────────────────────────────────────────────────
# 28. Concurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_analyze(self):
        reset_portfolio_registry()
        mgr    = PortfolioManager(registry=PortfolioRegistry())
        prs    = [mgr.create_portfolio(name=f"F{i}", cash=50_000.0) for i in range(8)]
        errors: list[Exception] = []
        results: list[PortfolioIntelligence] = []

        def _worker(pid: str):
            try:
                intel = mgr.analyze(pid)
                results.append(intel)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(p.portfolio_id,)) for p in prs]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == len(prs)

    def test_concurrent_position_updates(self):
        reset_portfolio_registry()
        mgr = PortfolioManager(registry=PortfolioRegistry())
        pr  = mgr.create_portfolio(name="F", cash=100_000.0)
        pos = _pos(qty=10, cost=1_000.0, price=1_000.0)
        mgr.add_position(pr.portfolio_id, pos)

        errors: list[Exception] = []

        def _update(price: float):
            try:
                mgr.update_position_price(pr.portfolio_id, pos.position_id, price)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_update, args=(float(1_000 + i * 10),)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_concurrent_registry(self):
        reg    = PortfolioRegistry(max_portfolios=100)
        errors: list[Exception] = []

        def _register(i: int):
            try:
                reg.register(f"P{i}", f"Fund {i}")
            except PortfolioAlreadyExistsError:
                pass
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_register, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors


# ─────────────────────────────────────────────────────────────────────────────
# 29. Package imports
# ─────────────────────────────────────────────────────────────────────────────

class TestPackageImports:
    def test_all_exports_importable(self):
        import iios.investment.portfolio as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing export: {name}"

    def test_version(self):
        import iios.investment.portfolio as pkg
        assert pkg.__version__ == PORTFOLIO_ENGINE_VERSION

    def test_system_id(self):
        import iios.investment.portfolio as pkg
        assert "portfolio" in pkg.__system_id__
