"""tests/unit/investment/company/test_company_intelligence_engine.py
Full test suite for the Company Intelligence Engine.
Target: ≥ 148 tests covering all source modules.
"""
from __future__ import annotations

import asyncio
import threading
import time

import pytest

from iios.investment.company import (
    # Engine
    CompanyIntelligenceEngine,
    get_company_engine,
    reset_company_engine,
    # Manager
    CompanyManager,
    CompanyStatistics,
    get_company_manager,
    reset_company_manager,
    # Registry
    CompanyRegistry,
    get_company_registry,
    reset_company_registry,
    # Factory
    CompanyFactory,
    # Context
    CompanyContextState,
    company_session,
    company_stage_scope,
    get_company_context,
    reset_company_context,
    # Profile
    CompanyIdentity,
    CompanyMetadata,
    CompanySnapshot,
    CompanyProfile,
    CompanyHistory,
    # Financials
    IncomeStatementAnalysis,
    IncomeStatementAnalyzer,
    BalanceSheetAnalysis,
    BalanceSheetAnalyzer,
    CashflowAnalysis,
    CashflowAnalyzer,
    FinancialQualityAnalysis,
    FinancialQualityAnalyzer,
    FinancialAnalysis,
    FinancialEngine,
    # Fundamentals
    ValuationAnalysis,
    ValuationEngine,
    OwnershipAnalysis,
    OwnershipEngine,
    GovernanceAnalysis,
    GovernanceEngine,
    CorporateAction,
    CorporateActionsAnalysis,
    CorporateActionEngine,
    FundamentalAnalysis,
    FundamentalEngine,
    # Models
    CompanyHealth,
    CompanySignal,
    CompanySignalStrength,
    CompanySignalType,
    CompanyIntelligence,
    # Enums / constants
    BusinessModel,
    CompanyStage,
    CorporateActionType,
    FinancialHealth,
    GovernanceQuality,
    GrowthProfile,
    ListingStatus,
    MarketCapCategory,
    OwnershipConcentration,
    SectorClassification,
    ValuationStatus,
    BIG4_FIRMS,
    # Exceptions
    CompanyIntelligenceError,
    CompanyAlreadyExistsError,
    CompanyNotFoundError,
    CompanyEngineAlreadyRunningError,
    CompanyEngineNotInitializedError,
    CompanyRegistryOverflowError,
    FinancialAnalysisFailedError,
    FinancialDataMissingError,
    GovernanceDataMissingError,
    OwnershipDataMissingError,
    ProfileInvalidError,
    ProfileNotFoundError,
    ProfileStaleError,
    ValuationDataMissingError,
    ValuationInvalidError,
)
from iios.investment.company.company_constants import (
    COMPANY_ENGINE_VERSION,
    COMPANY_ENGINE_SYSTEM_ID,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _income(
    revenue=1_000,
    revenue_prev=900,
    gross=600,
    ebitda=200,
    pat=100,
) -> dict:
    return {
        "revenue":      revenue,
        "revenue_prev": revenue_prev,
        "gross_profit": gross,
        "ebitda":       ebitda,
        "pat":          pat,
        "interest":     20,
        "depreciation": 30,
    }


def _balance(
    assets=2_000,
    debt=500,
    equity=1_500,
    curr_a=800,
    curr_l=300,
    cash=200,
) -> dict:
    return {
        "total_assets":         assets,
        "total_debt":           debt,
        "equity":               equity,
        "current_assets":       curr_a,
        "current_liabilities":  curr_l,
        "cash":                 cash,
        "goodwill":             0,
    }


def _cashflow(ocf=150, capex=-50) -> dict:
    return {
        "operating_cf": ocf,
        "investing_cf": capex - 20,
        "financing_cf": -30,
        "capex":        capex,
    }


def _valuation(
    price=100,
    mktcap=10_000,
    pe=15,
    pb=2,
    ev=12_000,
    ebitda=200,
    rev=1_000,
) -> dict:
    return {
        "price":      price,
        "market_cap": mktcap,
        "pe":         pe,
        "pb":         pb,
        "ev":         ev,
        "ebitda":     ebitda,
        "revenue":    rev,
    }


def _ownership(
    promoter=55,
    inst=25,
    retail=20,
    pledge=5,
    change=1,
) -> dict:
    return {
        "promoter_holding":      promoter,
        "institutional_holding": inst,
        "retail_holding":        retail,
        "promoter_pledge":       pledge,
        "promoter_change_qoq":   change,
    }


def _governance(
    board=10,
    indep=5,
    audit="Deloitte",
    rpt=2,
    csr=True,
) -> dict:
    return {
        "board_size":            board,
        "independent_directors": indep,
        "audit_firm":            audit,
        "related_party_pct":     rpt,
        "has_csr_report":        csr,
    }


# ─────────────────────────────────────────────────────────────────────────────
# autouse fixture — reset all singletons between tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_all():
    reset_company_engine()
    reset_company_manager()
    reset_company_registry()
    reset_company_context()
    yield
    reset_company_engine()
    reset_company_manager()
    reset_company_registry()
    reset_company_context()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants & Enums
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version_string(self):
        assert COMPANY_ENGINE_VERSION == "1.0.0"

    def test_system_id(self):
        assert "company" in COMPANY_ENGINE_SYSTEM_ID

    def test_sector_enum_has_unknown(self):
        assert SectorClassification.UNKNOWN.value == "unknown"

    def test_financial_health_distressed(self):
        assert FinancialHealth.DISTRESSED.value == "distressed"

    def test_big4_contains_deloitte(self):
        assert "deloitte" in BIG4_FIRMS

    def test_corporate_action_type_dividend(self):
        assert CorporateActionType.DIVIDEND in CorporateActionType


# ─────────────────────────────────────────────────────────────────────────────
# 2. Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_error_is_exception(self):
        e = CompanyIntelligenceError("base", code="CI-000")
        assert isinstance(e, Exception)
        assert e.code == "CI-000"

    def test_company_not_found_subclass(self):
        assert issubclass(CompanyNotFoundError, CompanyIntelligenceError)

    def test_company_already_exists(self):
        e = CompanyAlreadyExistsError("dup", company_id="C1")
        assert e.company_id == "C1"

    def test_profile_stale(self):
        e = ProfileStaleError("stale profile")
        assert isinstance(e, CompanyIntelligenceError)

    def test_financial_analysis_failed(self):
        assert issubclass(FinancialAnalysisFailedError, CompanyIntelligenceError)

    def test_financial_data_missing(self):
        e = FinancialDataMissingError("no data")
        assert isinstance(e, CompanyIntelligenceError)

    def test_valuation_invalid(self):
        e = ValuationInvalidError("bad val")
        assert isinstance(e, CompanyIntelligenceError)

    def test_governance_data_missing(self):
        e = GovernanceDataMissingError("no gov")
        assert isinstance(e, CompanyIntelligenceError)

    def test_engine_not_initialized(self):
        assert issubclass(CompanyEngineNotInitializedError, CompanyIntelligenceError)

    def test_registry_overflow(self):
        e = CompanyRegistryOverflowError("full", capacity=5, current=5)
        assert e.capacity == 5


# ─────────────────────────────────────────────────────────────────────────────
# 3. CompanyIdentity
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyIdentity:
    def test_defaults(self):
        ident = CompanyIdentity()
        assert ident.company_id != ""
        assert ident.sector == SectorClassification.UNKNOWN

    def test_display_name_fallback(self):
        ident = CompanyIdentity(ticker="TCS")
        assert ident.display_name() == "TCS"

    def test_display_name_short(self):
        ident = CompanyIdentity(ticker="TCS", short_name="Tata Consult")
        assert ident.display_name() == "Tata Consult"

    def test_to_dict_keys(self):
        ident = CompanyIdentity(ticker="INFY", name="Infosys")
        d = ident.to_dict()
        assert "ticker" in d
        assert "sector" in d
        assert d["currency"] == "INR"


# ─────────────────────────────────────────────────────────────────────────────
# 4. CompanyMetadata
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyMetadata:
    def test_defaults(self):
        m = CompanyMetadata()
        assert m.business_model == BusinessModel.UNKNOWN

    def test_to_dict(self):
        m = CompanyMetadata(company_id="C1", employees=5000)
        d = m.to_dict()
        assert d["employees"] == 5000

    def test_get_attribute(self):
        m = CompanyMetadata(attributes={"foo": "bar"})
        assert m.get("foo") == "bar"
        assert m.get("missing") is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. CompanySnapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanySnapshot:
    def test_defaults(self):
        s = CompanySnapshot()
        assert s.health == FinancialHealth.UNKNOWN

    def test_is_stale_fresh(self):
        s = CompanySnapshot()
        assert not s.is_stale(ttl_sec=3_600)

    def test_is_stale_old(self):
        s = CompanySnapshot()
        s.created_at = time.time() - 7_200
        assert s.is_stale(ttl_sec=3_600)

    def test_to_dict(self):
        s = CompanySnapshot(company_id="C1", price=500.0)
        d = s.to_dict()
        assert d["price"] == 500.0
        assert "health" in d


# ─────────────────────────────────────────────────────────────────────────────
# 6. CompanyProfile
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyProfile:
    def test_defaults(self):
        p = CompanyProfile()
        assert p.latest_snapshot is None

    def test_update_snapshot(self):
        p = CompanyProfile(company_id="C1")
        snap = CompanySnapshot(company_id="C1", price=200.0)
        p.update_snapshot(snap)
        assert p.latest_snapshot is snap

    def test_update_financials(self):
        p = CompanyProfile(company_id="C1")
        p.update_financials({"revenue": 1000}, {}, {})
        assert p.income_data["revenue"] == 1000

    def test_to_dict(self):
        p = CompanyProfile(company_id="C1")
        d = p.to_dict()
        assert d["company_id"] == "C1"
        assert "has_snapshot" in d


# ─────────────────────────────────────────────────────────────────────────────
# 7. CompanyHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyHistory:
    def test_add_and_get_latest(self):
        h = CompanyHistory()
        s = CompanySnapshot(company_id="C1")
        h.add("C1", s)
        assert h.get_latest("C1") is s

    def test_missing_returns_none(self):
        h = CompanyHistory()
        assert h.get_latest("NOPE") is None

    def test_count(self):
        h = CompanyHistory()
        for _ in range(5):
            h.add("C1", CompanySnapshot(company_id="C1"))
        assert h.count("C1") == 5

    def test_ring_buffer_max(self):
        h = CompanyHistory(max_per_company=3)
        for _ in range(10):
            h.add("C1", CompanySnapshot(company_id="C1"))
        assert h.count("C1") == 3

    def test_all_companies(self):
        h = CompanyHistory()
        h.add("A", CompanySnapshot(company_id="A"))
        h.add("B", CompanySnapshot(company_id="B"))
        assert set(h.all_companies()) == {"A", "B"}


# ─────────────────────────────────────────────────────────────────────────────
# 8. IncomeStatementAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestIncomeStatementAnalyzer:
    def setup_method(self):
        self.az = IncomeStatementAnalyzer()

    def test_empty_returns_defaults(self):
        r = self.az.analyze({})
        assert isinstance(r, IncomeStatementAnalysis)
        assert r.health_score == 50.0

    def test_growth_positive(self):
        r = self.az.analyze(_income(revenue=1_100, revenue_prev=1_000))
        assert r.revenue_growth_yoy == pytest.approx(0.10, abs=1e-4)
        assert r.revenue_trend == "growing"

    def test_high_margin_yields_strong(self):
        r = self.az.analyze(_income(pat=250))
        assert r.profitability in (FinancialHealth.STRONG, FinancialHealth.VERY_STRONG)

    def test_declining_revenue(self):
        r = self.az.analyze(_income(revenue=900, revenue_prev=1_000))
        assert r.revenue_trend == "declining"

    def test_to_dict(self):
        r = self.az.analyze(_income())
        d = r.to_dict()
        assert "revenue_growth_yoy" in d


# ─────────────────────────────────────────────────────────────────────────────
# 9. BalanceSheetAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestBalanceSheetAnalyzer:
    def setup_method(self):
        self.az = BalanceSheetAnalyzer()

    def test_empty_returns_defaults(self):
        r = self.az.analyze({})
        assert isinstance(r, BalanceSheetAnalysis)

    def test_de_ratio(self):
        r = self.az.analyze(_balance(debt=300, equity=1_500))
        assert r.debt_to_equity == pytest.approx(0.20, abs=1e-3)

    def test_current_ratio(self):
        r = self.az.analyze(_balance(curr_a=900, curr_l=300))
        assert r.current_ratio == pytest.approx(3.0, abs=1e-3)

    def test_net_cash_positive(self):
        r = self.az.analyze(_balance(debt=100, cash=300))
        assert r.is_net_cash

    def test_highly_leveraged_classified_correctly(self):
        r = self.az.analyze(_balance(debt=5_000, equity=500))
        assert r.leverage_health == FinancialHealth.DISTRESSED


# ─────────────────────────────────────────────────────────────────────────────
# 10. CashflowAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestCashflowAnalyzer:
    def setup_method(self):
        self.az = CashflowAnalyzer()

    def test_empty_returns_defaults(self):
        r = self.az.analyze({})
        assert isinstance(r, CashflowAnalysis)

    def test_positive_fcf(self):
        r = self.az.analyze(_cashflow(ocf=200, capex=-50))
        assert r.is_cash_generative

    def test_negative_ocf_distressed(self):
        r = self.az.analyze({"operating_cf": -50, "investing_cf": -20, "financing_cf": 0, "capex": -10})
        assert r.cf_health == FinancialHealth.DISTRESSED

    def test_to_dict(self):
        r = self.az.analyze(_cashflow())
        d = r.to_dict()
        assert "free_cf" in d


# ─────────────────────────────────────────────────────────────────────────────
# 11. FinancialQualityAnalyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestFinancialQuality:
    def setup_method(self):
        self.income_az = IncomeStatementAnalyzer()
        self.balance_az = BalanceSheetAnalyzer()
        self.cf_az = CashflowAnalyzer()
        self.qa = FinancialQualityAnalyzer()

    def _analyze(self, inc_data=None, bal_data=None, cf_data=None):
        inc = self.income_az.analyze(inc_data or _income())
        bal = self.balance_az.analyze(bal_data or _balance())
        # Pass revenue and pat so cf_quality (OCF/PAT) is computed correctly
        pat = inc.revenue * inc.pat_margin if inc.revenue > 0 else 0.0
        cf  = self.cf_az.analyze(cf_data or _cashflow(), revenue=inc.revenue, pat=pat)
        return self.qa.analyze(inc, cf, bal)

    def test_high_quality(self):
        # Use high OCF (>PAT) to ensure high quality
        r = self._analyze(
            cf_data={"operating_cf": 200, "investing_cf": -20, "financing_cf": 0, "capex": -50},
            inc_data=_income(pat=120),
        )
        assert r.quality_level in ("high", "moderate")

    def test_to_dict(self):
        r = self._analyze()
        d = r.to_dict()
        assert "earnings_quality_score" in d

    def test_poor_quality_when_no_cf(self):
        r = self._analyze(cf_data={"operating_cf": -200, "investing_cf": 0, "financing_cf": 0, "capex": 0})
        assert r.quality_level in ("low", "poor")


# ─────────────────────────────────────────────────────────────────────────────
# 12. FinancialEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestFinancialEngine:
    def setup_method(self):
        self.eng = FinancialEngine()

    def test_returns_financial_analysis(self):
        r = self.eng.analyze(_income(), _balance(), _cashflow())
        assert isinstance(r, FinancialAnalysis)

    def test_health_score_range(self):
        r = self.eng.analyze(_income(), _balance(), _cashflow())
        assert 0 <= r.health_score <= 100

    def test_composite_health_object(self):
        r = self.eng.analyze(_income(), _balance(), _cashflow())
        assert r.income.revenue == 1_000

    def test_empty_inputs_safe(self):
        r = self.eng.analyze({}, {}, {})
        assert isinstance(r, FinancialAnalysis)

    def test_to_dict(self):
        r = self.eng.analyze(_income(), _balance(), _cashflow())
        d = r.to_dict()
        assert "income" in d
        assert "health_score" in d


# ─────────────────────────────────────────────────────────────────────────────
# 13. ValuationEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestValuationEngine:
    def setup_method(self):
        self.eng = ValuationEngine()

    def test_empty_returns_unknown(self):
        r = self.eng.analyze({})
        assert r.status == ValuationStatus.UNKNOWN

    def test_low_pe_deeply_undervalued(self):
        r = self.eng.analyze({"pe": 5, "pb": 0.8})
        assert r.status in (ValuationStatus.DEEPLY_UNDERVALUED, ValuationStatus.UNDERVALUED)

    def test_high_pe_overvalued(self):
        r = self.eng.analyze({"pe": 80})
        assert r.status in (ValuationStatus.OVERVALUED, ValuationStatus.DEEPLY_OVERVALUED)

    def test_ev_ebitda_computed(self):
        r = self.eng.analyze({"ev": 12_000, "ebitda": 400})
        assert r.ev_ebitda == pytest.approx(30.0, abs=1e-2)

    def test_to_dict(self):
        r = self.eng.analyze(_valuation())
        d = r.to_dict()
        assert "valuation_score" in d


# ─────────────────────────────────────────────────────────────────────────────
# 14. OwnershipEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestOwnershipEngine:
    def setup_method(self):
        self.eng = OwnershipEngine()

    def test_empty_returns_defaults(self):
        r = self.eng.analyze({})
        assert r.concentration == OwnershipConcentration.UNKNOWN

    def test_high_promoter_concentrated(self):
        r = self.eng.analyze(_ownership(promoter=65))
        assert r.concentration == OwnershipConcentration.CONCENTRATED

    def test_low_promoter_distributed(self):
        r = self.eng.analyze(_ownership(promoter=20))
        assert r.concentration == OwnershipConcentration.DISTRIBUTED

    def test_high_pledge_flagged(self):
        r = self.eng.analyze(_ownership(pledge=30))
        assert r.high_pledge

    def test_to_dict(self):
        r = self.eng.analyze(_ownership())
        d = r.to_dict()
        assert "ownership_score" in d


# ─────────────────────────────────────────────────────────────────────────────
# 15. GovernanceEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestGovernanceEngine:
    def setup_method(self):
        self.eng = GovernanceEngine()

    def test_empty_returns_defaults(self):
        r = self.eng.analyze({})
        assert r.quality == GovernanceQuality.UNKNOWN

    def test_big4_detected(self):
        r = self.eng.analyze(_governance(audit="Ernst & Young"))
        assert r.is_big4

    def test_non_big4(self):
        r = self.eng.analyze(_governance(audit="LocalFirm"))
        assert not r.is_big4

    def test_high_indep_good_quality(self):
        r = self.eng.analyze(_governance(board=10, indep=7, csr=True))
        assert r.quality in (GovernanceQuality.EXCELLENT, GovernanceQuality.GOOD)


# ─────────────────────────────────────────────────────────────────────────────
# 16. CorporateActionEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestCorporateActionEngine:
    def setup_method(self):
        self.eng = CorporateActionEngine()

    def test_empty_list(self):
        r = self.eng.analyze("C1", [])
        assert len(r.actions) == 0

    def test_dividends_detected(self):
        actions = [
            {"action_type": "dividend", "date": "2024-01-01", "value": 5.0},
            {"action_type": "dividend", "date": "2023-01-01", "value": 4.5},
            {"action_type": "dividend", "date": "2022-01-01", "value": 4.0},
        ]
        r = self.eng.analyze("C1", actions)
        assert r.has_regular_dividends
        assert len(r.recent_dividends) == 3

    def test_unknown_type_fallback(self):
        r = self.eng.analyze("C1", [{"action_type": "foobar"}])
        assert r.actions[0].action_type == CorporateActionType.OTHER

    def test_to_dict(self):
        r = self.eng.analyze("C1", [{"action_type": "BONUS", "value": 1}])
        d = r.to_dict()
        assert d["has_bonus"]


# ─────────────────────────────────────────────────────────────────────────────
# 17. FundamentalEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestFundamentalEngine:
    def setup_method(self):
        self.eng = FundamentalEngine()

    def test_returns_fundamental_analysis(self):
        r = self.eng.analyze("C1", valuation_data=_valuation(), ownership_data=_ownership(), governance_data=_governance())
        assert isinstance(r, FundamentalAnalysis)

    def test_attractiveness_in_range(self):
        r = self.eng.analyze("C1", valuation_data=_valuation(), ownership_data=_ownership(), governance_data=_governance())
        assert 0 <= r.attractiveness_score <= 100

    def test_risk_score_in_range(self):
        r = self.eng.analyze("C1", valuation_data=_valuation(), ownership_data=_ownership(), governance_data=_governance())
        assert 0 <= r.risk_score <= 100

    def test_empty_inputs_safe(self):
        r = self.eng.analyze("C1")
        assert isinstance(r, FundamentalAnalysis)


# ─────────────────────────────────────────────────────────────────────────────
# 18. CompanyHealth
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyHealth:
    def test_defaults_healthy_threshold(self):
        h = CompanyHealth(overall_score=60.0)
        assert h.is_healthy

    def test_below_threshold_not_healthy(self):
        h = CompanyHealth(overall_score=59.9)
        assert not h.is_healthy

    def test_labels_generated(self):
        h = CompanyHealth(overall_score=80.0, financial_score=80.0)
        assert h.labels["overall"] == "GOOD"

    def test_to_dict(self):
        h = CompanyHealth()
        d = h.to_dict()
        assert "labels" in d
        assert "is_healthy" in d


# ─────────────────────────────────────────────────────────────────────────────
# 19. CompanySignal
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanySignal:
    def test_defaults(self):
        s = CompanySignal()
        assert s.signal_id != ""
        assert s.direction == "neutral"

    def test_signal_type_constants(self):
        assert CompanySignalType.FINANCIAL == "financial"
        assert CompanySignalStrength.STRONG == "strong"

    def test_to_dict(self):
        s = CompanySignal(company_id="C1", label="test")
        d = s.to_dict()
        assert d["company_id"] == "C1"


# ─────────────────────────────────────────────────────────────────────────────
# 20. CompanyIntelligence
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyIntelligence:
    def test_defaults(self):
        ci = CompanyIntelligence()
        assert ci.intelligence_id != ""

    def test_add_signal(self):
        ci = CompanyIntelligence(company_id="C1")
        s = CompanySignal(company_id="C1", label="x")
        ci.add_signal(s)
        assert len(ci.signals) == 1

    def test_add_opportunity_dedup(self):
        ci = CompanyIntelligence()
        ci.add_opportunity("foo")
        ci.add_opportunity("foo")
        assert len(ci.opportunities) == 1

    def test_add_risk(self):
        ci = CompanyIntelligence()
        ci.add_risk("risk1")
        assert "risk1" in ci.risks

    def test_to_dict(self):
        ci = CompanyIntelligence(company_id="C1")
        d = ci.to_dict()
        assert "intelligence_id" in d
        assert "health_score" in d


# ─────────────────────────────────────────────────────────────────────────────
# 21. CompanyRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyRegistry:
    def test_register_and_check(self):
        r = CompanyRegistry()
        r.register_company("C1", "TCS", "Tata Consultancy")
        assert r.is_registered("C1")

    def test_duplicate_raises(self):
        r = CompanyRegistry()
        r.register_company("C1", "TCS", "Tata Consultancy")
        with pytest.raises(CompanyAlreadyExistsError):
            r.register_company("C1", "TCS", "Tata Consultancy")

    def test_get_not_found_raises(self):
        r = CompanyRegistry()
        with pytest.raises(CompanyNotFoundError):
            r.get_company_info("NOPE")

    def test_all_companies(self):
        r = CompanyRegistry()
        r.register_company("A", "A", "Alpha")
        r.register_company("B", "B", "Beta")
        assert set(r.all_companies()) == {"A", "B"}

    def test_register_analyzer(self):
        r = CompanyRegistry()
        r.register_analyzer("az1", object())
        assert r.has_analyzer("az1")

    def test_analyzer_not_found_raises(self):
        r = CompanyRegistry()
        with pytest.raises(Exception):
            r.get_analyzer("NOPE")

    def test_overflow(self):
        r = CompanyRegistry(max_companies=2)
        r.register_company("A", "A", "Alpha")
        r.register_company("B", "B", "Beta")
        with pytest.raises(CompanyRegistryOverflowError):
            r.register_company("C", "C", "Gamma")

    def test_statistics(self):
        r = CompanyRegistry()
        r.register_company("X", "X", "X Corp")
        stats = r.statistics()
        assert stats["registered_companies"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 22. CompanyContext
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyContext:
    def test_get_context_returns_state(self):
        ctx = get_company_context()
        assert isinstance(ctx, CompanyContextState)

    def test_context_context_request_id_default(self):
        ctx = get_company_context()
        assert ctx.request_id != ""

    def test_session_context_manager(self):
        with company_session("req-123", {"key": "val"}) as ctx:
            assert ctx.request_id == "req-123"

    def test_stage_scope(self):
        with company_stage_scope("analysis") as ctx:
            assert ctx.stage == "analysis"

    def test_reset_context(self):
        reset_company_context()
        ctx = get_company_context()
        assert ctx is not None


# ─────────────────────────────────────────────────────────────────────────────
# 23. CompanyFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyFactory:
    def test_make_identity(self):
        ident = CompanyFactory.make_identity("C1", "TCS", "Tata CS")
        assert ident.ticker == "TCS"

    def test_make_metadata(self):
        m = CompanyFactory.make_metadata("C1", employees=50_000)
        assert m.employees == 50_000

    def test_make_snapshot(self):
        s = CompanyFactory.make_snapshot("C1", price=3_500.0, market_cap=1e12)
        assert s.price == 3_500.0

    def test_make_profile(self):
        ident = CompanyFactory.make_identity("C1", "TCS", "Tata CS")
        p = CompanyFactory.make_profile(ident)
        assert p.company_id == "C1"
        assert p.company_meta is not None

    def test_make_signal(self):
        s = CompanyFactory.make_signal("C1", "test_signal", direction="positive")
        assert s.direction == "positive"
        assert s.company_id == "C1"


# ─────────────────────────────────────────────────────────────────────────────
# 24. CompanyManager
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyManager:
    def setup_method(self):
        reset_company_registry()
        self.mgr = CompanyManager(registry=CompanyRegistry())

    def test_register_company_returns_profile(self):
        p = self.mgr.register_company("C1", ticker="TCS", name="Tata CS")
        assert isinstance(p, CompanyProfile)

    def test_register_idempotent(self):
        self.mgr.register_company("C1", ticker="TCS")
        p2 = self.mgr.register_company("C1", ticker="TCS")
        assert p2.company_id == "C1"

    def test_get_profile_not_found(self):
        with pytest.raises(CompanyNotFoundError):
            self.mgr.get_profile("NOPE")

    def test_analyze_returns_intelligence(self):
        ci = self.mgr.analyze(
            "C1",
            income_data=_income(),
            balance_data=_balance(),
            cashflow_data=_cashflow(),
            valuation_data=_valuation(),
            ownership_data=_ownership(),
            governance_data=_governance(),
        )
        assert isinstance(ci, CompanyIntelligence)
        assert ci.company_id == "C1"

    def test_analyze_creates_snapshot(self):
        self.mgr.analyze("C1", income_data=_income(), balance_data=_balance(), cashflow_data=_cashflow())
        snap = self.mgr.summary("C1")
        assert isinstance(snap, CompanySnapshot)

    def test_get_latest(self):
        self.mgr.analyze("C1", income_data=_income(), balance_data=_balance(), cashflow_data=_cashflow())
        latest = self.mgr.get_latest("C1")
        assert latest.company_id == "C1"

    def test_get_latest_not_found(self):
        with pytest.raises(CompanyNotFoundError):
            self.mgr.get_latest("NOPE")

    def test_recent(self):
        for i in range(5):
            self.mgr.analyze(f"C{i}", income_data=_income(), balance_data=_balance(), cashflow_data=_cashflow())
        assert len(self.mgr.recent(3)) == 3

    def test_statistics_dict(self):
        self.mgr.analyze("C1", income_data=_income(), balance_data=_balance(), cashflow_data=_cashflow())
        stats = self.mgr.statistics()
        assert stats["analyses_total"] >= 1

    def test_stats_object(self):
        self.mgr.analyze("C1")
        obj = self.mgr.stats_object()
        assert isinstance(obj, CompanyStatistics)


# ─────────────────────────────────────────────────────────────────────────────
# 25. CompanyIntelligenceEngine
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyIntelligenceEngine:
    def test_not_running_by_default(self):
        eng = CompanyIntelligenceEngine()
        assert not eng.is_running

    def test_initialize_sets_running(self):
        eng = CompanyIntelligenceEngine()
        eng.initialize()
        assert eng.is_running

    def test_double_initialize_raises(self):
        eng = CompanyIntelligenceEngine()
        eng.initialize()
        with pytest.raises(CompanyEngineAlreadyRunningError):
            eng.initialize()

    def test_analyze_requires_initialized(self):
        eng = CompanyIntelligenceEngine()
        with pytest.raises(CompanyEngineNotInitializedError):
            eng.analyze("C1")

    def test_analyze_returns_intelligence(self):
        eng = CompanyIntelligenceEngine()
        eng.initialize()
        ci = eng.analyze(
            "C1",
            income_data=_income(),
            balance_data=_balance(),
            cashflow_data=_cashflow(),
        )
        assert isinstance(ci, CompanyIntelligence)

    def test_register_company(self):
        eng = CompanyIntelligenceEngine()
        eng.initialize()
        p = eng.register_company("C1", ticker="INFY", name="Infosys")
        assert p.identity.ticker == "INFY"

    def test_get_latest(self):
        eng = CompanyIntelligenceEngine()
        eng.initialize()
        eng.analyze("C1", income_data=_income(), balance_data=_balance(), cashflow_data=_cashflow())
        latest = eng.get_latest("C1")
        assert latest.company_id == "C1"

    def test_recent(self):
        eng = CompanyIntelligenceEngine()
        eng.initialize()
        for i in range(5):
            eng.analyze(f"C{i}")
        assert len(eng.recent(3)) == 3

    def test_health_when_running(self):
        eng = CompanyIntelligenceEngine()
        eng.initialize()
        h = eng.health()
        assert h["status"] == "running"

    def test_health_when_stopped(self):
        eng = CompanyIntelligenceEngine()
        assert eng.health()["status"] == "stopped"

    def test_stats(self):
        eng = CompanyIntelligenceEngine()
        eng.initialize()
        eng.analyze("C1")
        s = eng.stats()
        assert "analyses_total" in s

    def test_shutdown(self):
        eng = CompanyIntelligenceEngine()
        eng.initialize()
        eng.shutdown()
        assert not eng.is_running


# ─────────────────────────────────────────────────────────────────────────────
# 26. Async analyze
# ─────────────────────────────────────────────────────────────────────────────

class TestAsyncAnalyze:
    def test_async_analyze(self):
        eng = CompanyIntelligenceEngine()
        eng.initialize()

        async def _run():
            return await eng.analyze_async("C1", income_data=_income())

        result = asyncio.run(_run())
        assert isinstance(result, CompanyIntelligence)

    def test_async_multiple(self):
        eng = CompanyIntelligenceEngine()
        eng.initialize()

        async def _run():
            tasks = [
                eng.analyze_async(f"C{i}", income_data=_income())
                for i in range(3)
            ]
            return await asyncio.gather(*tasks)

        results = asyncio.run(_run())
        assert len(results) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 27. Singleton helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestSingletons:
    def test_get_engine_singleton(self):
        e1 = get_company_engine()
        e2 = get_company_engine()
        assert e1 is e2

    def test_reset_engine_creates_new(self):
        e1 = get_company_engine()
        reset_company_engine()
        e2 = get_company_engine()
        assert e1 is not e2

    def test_get_manager_singleton(self):
        m1 = get_company_manager()
        m2 = get_company_manager()
        assert m1 is m2

    def test_get_registry_singleton(self):
        r1 = get_company_registry()
        r2 = get_company_registry()
        assert r1 is r2


# ─────────────────────────────────────────────────────────────────────────────
# 28. Concurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_analyze(self):
        reset_company_registry()
        mgr = CompanyManager(registry=CompanyRegistry())
        errors: list[Exception] = []
        results: list[CompanyIntelligence] = []

        def _worker(cid: str):
            try:
                ci = mgr.analyze(cid, income_data=_income(), balance_data=_balance())
                results.append(ci)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(f"C{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 10

    def test_concurrent_registry(self):
        registry = CompanyRegistry(max_companies=200)
        errors: list[Exception] = []

        def _register(i: int):
            try:
                registry.register_company(f"C{i}", f"T{i}", f"Co{i}")
            except CompanyAlreadyExistsError:
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
        import iios.investment.company as pkg
        assert hasattr(pkg, "__all__")
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing export: {name}"

    def test_version_in_package(self):
        import iios.investment.company as pkg
        assert pkg.__version__ == COMPANY_ENGINE_VERSION

    def test_system_id_in_package(self):
        import iios.investment.company as pkg
        assert "company" in pkg.__system_id__
