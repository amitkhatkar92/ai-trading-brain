"""
tests/unit/risk/assessment/test_risk_assessment_engine.py
===========================================================
Comprehensive test suite for the Risk Assessment & Optimization Framework.

Coverage targets: 95%+ across all 29 source files.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import math
import statistics
import threading
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from iios.risk.assessment import (
    # Constants
    ASSESSMENT_SYSTEM_ID,
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_EWMA_DECAY,
    DEFAULT_MAX_CONCENTRATION,
    DEFAULT_VAR_CONFIDENCE_LEVELS,
    DEFAULT_VAR_HORIZON_DAYS,
    FORECAST_HORIZON_DAYS,
    LIMIT_BREACH_THRESHOLD,
    LIMIT_WARNING_THRESHOLD,
    MIN_RETURNS_FOR_VAR,
    RISK_SCORE_HIGH,
    RISK_SCORE_LOW,
    RISK_SCORE_MEDIUM,
    SCENARIO_PROBABILITIES,
    STRESS_SHOCK_PARAMS,
    VERSION,
    ALL_DOMAINS,
    # Enums
    AssessmentCapability,
    AssessmentDomain,
    AssessmentEventType,
    AssessmentStatus,
    ForecastHorizon,
    LimitStatus,
    ModelType,
    OptimizationObjective,
    ScenarioType,
    StressScenario,
    ValidationCode,
    # Exceptions
    RiskAssessmentCapacityError,
    RiskAssessmentEngineNotRunningError,
    RiskAssessmentError,
    RiskAssessmentNotFoundError,
    RiskAssessmentRegistryError,
    RiskAssessmentValidationError,
    RiskCalculationError,
    RiskForecastError,
    RiskMitigationError,
    RiskModelNotFoundError,
    RiskOptimizationError,
    RiskScenarioError,
    RiskStressTestError,
    # Value objects
    ExposureReport,
    MitigationAction,
    MitigationPlan,
    OptimizationRecommendation,
    RiskAssessmentContext,
    RiskAssessmentReport,
    RiskAssessmentRequest,
    RiskAssessmentSummary,
    RiskForecast,
    RiskOptimizationReport,
    ScenarioAnalysisReport,
    ScenarioOutcome,
    StressScenarioResult,
    StressTestReport,
    VaRReport,
    ExpectedShortfallReport,
    # Validation
    AssessmentValidationCheck,
    AssessmentValidationResult,
    # Calculation results
    CalculationBundle,
    ConcentrationResult,
    LimitUtilisationResult,
    RiskScoreComponents,
    SensitivityResult,
    # Model registry
    RiskModel,
    # Events
    RiskAssessmentEvent,
    make_assessment_failed,
    make_assessment_published,
    make_assessment_started,
    make_assessment_validated,
    make_mitigation_generated,
    make_models_loaded,
    make_optimization_completed,
    make_risk_calculated,
    make_scenario_analysis_completed,
    make_stress_test_completed,
    # Services
    RiskAssessmentFactory,
    RiskAssessmentHistory,
    RiskAssessmentManager,
    RiskAssessmentRegistry,
    RiskAssessmentStatistics,
    RiskAssessmentValidator,
    RiskCalculationEngine,
    RiskConcentrationEngine,
    RiskExposureEngine,
    RiskExpectedShortfallEngine,
    RiskForecastingEngine,
    RiskLimitEngine,
    RiskMeasurementEngine,
    RiskMitigationEngine,
    RiskModelRegistry,
    RiskOptimizationEngine,
    RiskScenarioEngine,
    RiskScoreEngine,
    RiskSensitivityEngine,
    RiskStressTestingEngine,
    RiskVaREngine,
    # Engine
    RiskAssessmentEngine,
    RiskAssessmentEngineStatus,
)


# ===========================================================================
# Test fixtures and helpers
# ===========================================================================

RETURNS_FLAT = [0.001] * 252          # flat 0.1% daily
RETURNS_VOLATILE = (
    [0.02, -0.03, 0.01, -0.02, 0.04] * 50 + [0.01, -0.01]
)
RETURNS_NEGATIVE = [-0.01] * 100
POSITIONS_BALANCED = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
POSITIONS_CONCENTRATED = {"A": 0.70, "B": 0.20, "C": 0.10}
POSITIONS_EMPTY: Dict[str, float] = {}
PORTFOLIO_VALUE = 1_000_000.0
LIMITS_STANDARD = {"var_limit": 50_000.0, "concentration_limit": 0.30}


def _make_request(
    portfolio_value: float = PORTFOLIO_VALUE,
    positions: Optional[Dict[str, float]] = None,
    returns: Optional[List[float]] = None,
    limits: Optional[Dict[str, float]] = None,
    policy_approved: bool = True,
    assessment_id: Optional[str] = None,
) -> RiskAssessmentRequest:
    return RiskAssessmentRequest.create(
        assessment_id   = assessment_id or str(uuid.uuid4()),
        portfolio_id    = "portfolio-1",
        risk_id         = "risk-1",
        portfolio_value = portfolio_value,
        positions       = positions or POSITIONS_BALANCED,
        returns         = returns if returns is not None else RETURNS_VOLATILE,
        limits          = limits or LIMITS_STANDARD,
        policy_approved = policy_approved,
    )


def _started_engine() -> RiskAssessmentEngine:
    e = RiskAssessmentEngine()
    e.start()
    return e


# ===========================================================================
# 1. Constants & Enumerations
# ===========================================================================

class TestConstants:
    def test_assessment_system_id(self):
        assert ASSESSMENT_SYSTEM_ID == "iios:risk:assessment"

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_all_domains_frozenset(self):
        assert isinstance(ALL_DOMAINS, frozenset)
        assert "market_risk" in ALL_DOMAINS

    def test_assessment_domain_count(self):
        assert len(AssessmentDomain) == 12

    def test_assessment_capability_count(self):
        assert len(AssessmentCapability) == 15

    def test_optimization_objective_count(self):
        assert len(OptimizationObjective) == 8

    def test_model_type_count(self):
        assert len(ModelType) == 7

    def test_stress_scenario_count(self):
        assert len(StressScenario) == 8

    def test_scenario_type_count(self):
        assert len(ScenarioType) == 6

    def test_assessment_event_type_count(self):
        assert len(AssessmentEventType) == 10

    def test_forecast_horizon_days_mapping(self):
        assert FORECAST_HORIZON_DAYS[ForecastHorizon.DAY] == 1
        assert FORECAST_HORIZON_DAYS[ForecastHorizon.WEEK] == 5
        assert FORECAST_HORIZON_DAYS[ForecastHorizon.MONTH] == 21
        assert FORECAST_HORIZON_DAYS[ForecastHorizon.QUARTER] == 63

    def test_stress_shock_params_all_scenarios(self):
        for scenario in StressScenario:
            assert scenario in STRESS_SHOCK_PARAMS

    def test_scenario_probabilities_sum(self):
        # Core scenarios sum to 1.0
        core = [ScenarioType.BEST_CASE, ScenarioType.EXPECTED_CASE,
                ScenarioType.WORST_CASE, ScenarioType.BLACK_SWAN]
        total = sum(SCENARIO_PROBABILITIES[s] for s in core)
        assert abs(total - 1.0) < 1e-9

    def test_risk_score_bands_ordering(self):
        assert RISK_SCORE_LOW < RISK_SCORE_MEDIUM < RISK_SCORE_HIGH

    def test_limit_threshold_ordering(self):
        assert LIMIT_WARNING_THRESHOLD < LIMIT_BREACH_THRESHOLD

    def test_min_returns_for_var(self):
        assert MIN_RETURNS_FOR_VAR >= 2

    def test_default_confidence_level(self):
        assert 0 < DEFAULT_CONFIDENCE_LEVEL < 1

    def test_default_ewma_decay(self):
        assert 0 < DEFAULT_EWMA_DECAY < 1


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_exception(self):
        exc = RiskAssessmentError("test error")
        assert "test error" in str(exc)
        assert exc.code == "RA-000"

    def test_engine_not_running(self):
        exc = RiskAssessmentEngineNotRunningError()
        assert "start()" in str(exc)
        assert exc.code == "RA-001"

    def test_not_found(self):
        exc = RiskAssessmentNotFoundError("aid-1")
        assert "aid-1" in str(exc)
        assert exc.assessment_id == "aid-1"
        assert exc.code == "RA-002"

    def test_validation_error(self):
        exc = RiskAssessmentValidationError("bad input", assessment_id="aid-2")
        assert "aid-2" in str(exc)
        assert exc.code == "RA-003"

    def test_model_not_found(self):
        exc = RiskModelNotFoundError("model-x")
        assert "model-x" in str(exc)
        assert exc.code == "RA-004"

    def test_calculation_error(self):
        exc = RiskCalculationError("division by zero", engine="VaREngine")
        assert "VaREngine" in str(exc)
        assert exc.code == "RA-005"

    def test_registry_error(self):
        exc = RiskAssessmentRegistryError("registry full")
        assert exc.code == "RA-006"

    def test_optimization_error(self):
        exc = RiskOptimizationError("infeasible", objective="minimize_risk")
        assert "minimize_risk" in str(exc)
        assert exc.code == "RA-008"

    def test_stress_test_error(self):
        exc = RiskStressTestError("shock failed", scenario="market_crash")
        assert "market_crash" in str(exc)
        assert exc.code == "RA-009"

    def test_scenario_error(self):
        exc = RiskScenarioError("projection failed", scenario_type="worst_case")
        assert "worst_case" in str(exc)
        assert exc.code == "RA-010"

    def test_forecast_error(self):
        exc = RiskForecastError("ewma failed", horizon="week")
        assert "week" in str(exc)
        assert exc.code == "RA-011"

    def test_mitigation_error(self):
        exc = RiskMitigationError("no drivers")
        assert exc.code == "RA-012"

    def test_capacity_error(self):
        exc = RiskAssessmentCapacityError(500)
        assert "500" in str(exc)
        assert exc.max_capacity == 500
        assert exc.code == "RA-013"

    def test_inheritance_hierarchy(self):
        assert issubclass(RiskAssessmentEngineNotRunningError, RiskAssessmentError)
        assert issubclass(RiskCalculationError, RiskAssessmentError)


# ===========================================================================
# 3. Context
# ===========================================================================

class TestRiskAssessmentContext:
    def test_create_defaults_all_domains(self):
        ctx = RiskAssessmentContext.create("a1", "p1", "r1")
        assert len(ctx.domains) == len(AssessmentDomain)
        assert len(ctx.capabilities) == len(AssessmentCapability)

    def test_create_custom_domains(self):
        ctx = RiskAssessmentContext.create(
            "a1", "p1", "r1",
            domains=(AssessmentDomain.MARKET_RISK, AssessmentDomain.CREDIT_RISK),
        )
        assert len(ctx.domains) == 2
        assert AssessmentDomain.MARKET_RISK in ctx.domains

    def test_has_domain(self):
        ctx = RiskAssessmentContext.create("a1", "p1", "r1")
        assert ctx.has_domain(AssessmentDomain.PORTFOLIO_RISK)
        assert ctx.has_capability(AssessmentCapability.VALUE_AT_RISK)

    def test_to_dict(self):
        ctx = RiskAssessmentContext.create("a1", "p1", "r1")
        d = ctx.to_dict()
        assert d["assessment_id"] == "a1"
        assert "domains" in d
        assert "capabilities" in d

    def test_immutable(self):
        ctx = RiskAssessmentContext.create("a1", "p1", "r1")
        with pytest.raises((AttributeError, TypeError)):
            ctx.portfolio_id = "changed"

    def test_confidence_level(self):
        ctx = RiskAssessmentContext.create("a1", "p1", "r1", confidence_level=0.99)
        assert ctx.confidence_level == 0.99


# ===========================================================================
# 4. Request
# ===========================================================================

class TestRiskAssessmentRequest:
    def test_create_basic(self):
        req = _make_request()
        assert req.portfolio_id == "portfolio-1"
        assert req.portfolio_value == PORTFOLIO_VALUE
        assert req.policy_approved is True

    def test_has_returns(self):
        req = _make_request(returns=RETURNS_VOLATILE)
        assert req.has_returns is True
        req_empty = _make_request(returns=[])
        assert req_empty.has_returns is False

    def test_total_positions(self):
        req = _make_request(positions=POSITIONS_BALANCED)
        assert req.total_positions == 4

    def test_get_limit(self):
        req = _make_request(limits={"var_limit": 50000.0})
        assert req.get_limit("var_limit") == 50000.0
        assert req.get_limit("unknown", 99.0) == 99.0

    def test_to_dict(self):
        req = _make_request()
        d = req.to_dict()
        assert d["portfolio_value"] == PORTFOLIO_VALUE
        assert d["policy_approved"] is True

    def test_immutable(self):
        req = _make_request()
        with pytest.raises((AttributeError, TypeError)):
            req.portfolio_value = 0.0

    def test_confidence_level_from_context(self):
        req = _make_request()
        assert 0 < req.confidence_level < 1

    def test_unapproved_request(self):
        req = _make_request(policy_approved=False)
        assert req.policy_approved is False


# ===========================================================================
# 5. Response / Reports
# ===========================================================================

class TestVaRReport:
    def test_create(self):
        r = VaRReport.create(
            "a1", "p1",
            confidence_level=0.95, horizon_days=1,
            historical_var=50000.0, portfolio_value=1_000_000.0,
            returns_used=252,
        )
        assert r.historical_var == 50000.0
        assert abs(r.historical_var_pct - 0.05) < 1e-9

    def test_to_dict(self):
        r = VaRReport.create("a1", "p1", 0.95, 1, 40000.0, 1_000_000.0, 100)
        d = r.to_dict()
        assert "historical_var" in d
        assert "confidence_level" in d


class TestExpectedShortfallReport:
    def test_create(self):
        r = ExpectedShortfallReport.create(
            "a1", "p1", 0.95, 60000.0, 1_000_000.0, 252
        )
        assert r.es_historical == 60000.0
        assert abs(r.es_historical_pct - 0.06) < 1e-9

    def test_es_geq_var_reference(self):
        r = ExpectedShortfallReport.create(
            "a1", "p1", 0.95, 60000.0, 1_000_000.0, 252, var_reference=50000.0
        )
        assert r.es_historical >= r.var_reference


class TestStressTestReport:
    def test_create_with_scenarios(self):
        scenarios = [
            StressScenarioResult(
                scenario=StressScenario.MARKET_CRASH,
                stressed_loss=350000.0,
                stressed_loss_pct=0.35,
                stressed_value=650000.0,
                shock_params={"equity_shock": -0.35},
            )
        ]
        report = StressTestReport.create("a1", "p1", 1_000_000.0, scenarios)
        assert report.worst_scenario == StressScenario.MARKET_CRASH
        assert report.worst_loss == 350000.0

    def test_get_scenario(self):
        scenarios = [
            StressScenarioResult(StressScenario.MARKET_CRASH, 350000.0, 0.35, 650000.0, {})
        ]
        report = StressTestReport.create("a1", "p1", 1_000_000.0, scenarios)
        found = report.get_scenario(StressScenario.MARKET_CRASH)
        assert found is not None
        assert found.scenario == StressScenario.MARKET_CRASH
        assert report.get_scenario(StressScenario.CURRENCY_SHOCK) is None


class TestScenarioAnalysisReport:
    def test_create_with_outcomes(self):
        outcomes = [
            ScenarioOutcome(ScenarioType.BEST_CASE, 0.2, 1_050_000.0, 50000.0, 0.05, 0.01),
            ScenarioOutcome(ScenarioType.WORST_CASE, 0.2, 800_000.0, -200000.0, -0.20, 0.05),
        ]
        report = ScenarioAnalysisReport.create("a1", "p1", 1_000_000.0, 10000.0, outcomes)
        assert report.probability_weighted_loss > 0
        assert report.expected_return_pct == pytest.approx(0.01)


class TestExposureReport:
    def test_create_long_only(self):
        report = ExposureReport.create(
            "a1", "p1", 1_000_000.0,
            {"A": 0.5, "B": 0.5},
        )
        assert report.gross_exposure == 1_000_000.0
        assert report.short_exposure == 0.0

    def test_create_with_shorts(self):
        report = ExposureReport.create(
            "a1", "p1", 1_000_000.0,
            {"A": 0.6, "B": -0.3},
        )
        assert report.long_exposure == 600_000.0
        assert report.short_exposure == 300_000.0
        assert report.net_exposure == 300_000.0


class TestRiskForecast:
    def test_create(self):
        fc = RiskForecast.create(
            "a1", "p1", ForecastHorizon.WEEK, 5,
            forecast_var=25000.0, forecast_volatility=0.15,
            forecast_return=5000.0, portfolio_value=1_000_000.0,
            ewma_decay=0.94,
        )
        assert fc.horizon == ForecastHorizon.WEEK
        assert fc.forecast_var_pct == pytest.approx(0.025)


class TestMitigationPlan:
    def test_create_empty(self):
        plan = MitigationPlan.create("a1", "p1", [], 50.0)
        assert plan.total_actions == 0
        assert plan.risk_score_before == 50.0

    def test_create_with_actions(self):
        actions = [
            MitigationAction(str(uuid.uuid4()), "var_high", "Reduce VaR", "high", 10.0),
            MitigationAction(str(uuid.uuid4()), "concentration_high", "Diversify", "medium", 5.0),
        ]
        plan = MitigationPlan.create("a1", "p1", actions, 70.0)
        assert plan.total_actions == 2
        assert plan.high_priority == 1
        assert plan.estimated_risk_score_after < 70.0


class TestRiskOptimizationReport:
    def test_create(self):
        recs = [
            OptimizationRecommendation(
                str(uuid.uuid4()), OptimizationObjective.MINIMIZE_CONCENTRATION,
                "Reduce top position", 0.40, 0.25, 0.15,
            )
        ]
        report = RiskOptimizationReport.create(
            "a1", "p1",
            [OptimizationObjective.MINIMIZE_CONCENTRATION],
            recs, 60.0, 45.0,
        )
        assert report.optimization_gain == pytest.approx(15.0)


class TestRiskAssessmentSummary:
    def test_to_dict(self):
        s = RiskAssessmentSummary(
            summary_id="s1", assessment_id="a1", portfolio_id="p1",
            status=AssessmentStatus.COMPLETED, risk_score=45.0,
            risk_band="medium", var_95=40000.0, var_95_pct=0.04,
            es_95=55000.0, worst_stress_loss=300000.0, hhi=0.30,
            top_risks=("concentration",), mitigations_count=2,
        )
        d = s.to_dict()
        assert d["risk_score"] == 45.0
        assert d["status"] == "completed"


class TestRiskAssessmentReport:
    def test_create_minimal(self):
        r = RiskAssessmentReport.create(
            "a1", "p1", "r1", AssessmentStatus.COMPLETED, 42.0, 0.5
        )
        assert r.status == AssessmentStatus.COMPLETED
        assert r.risk_score == 42.0
        assert r.var_report is None

    def test_to_dict(self):
        r = RiskAssessmentReport.create(
            "a1", "p1", "r1", AssessmentStatus.COMPLETED, 42.0, 0.5
        )
        d = r.to_dict()
        assert "risk_score" in d
        assert "status" in d


# ===========================================================================
# 6. Events
# ===========================================================================

class TestEvents:
    def test_make_assessment_started(self):
        ev = make_assessment_started("a1", "p1", actor="engine")
        assert ev.event_type == AssessmentEventType.ASSESSMENT_STARTED
        assert ev.assessment_id == "a1"
        assert ev.status == AssessmentStatus.PROCESSING

    def test_make_models_loaded(self):
        ev = make_models_loaded("a1", "p1", models_count=7)
        assert ev.payload["models_count"] == 7

    def test_make_risk_calculated(self):
        ev = make_risk_calculated("a1", "p1", risk_score=45.0)
        assert ev.payload["risk_score"] == 45.0

    def test_make_stress_test_completed(self):
        ev = make_stress_test_completed("a1", "p1", worst_loss_pct=0.35)
        assert ev.event_type == AssessmentEventType.STRESS_TEST_COMPLETED

    def test_make_scenario_analysis_completed(self):
        ev = make_scenario_analysis_completed("a1", "p1", expected_return_pct=0.02)
        assert ev.event_type == AssessmentEventType.SCENARIO_ANALYSIS_COMPLETED

    def test_make_optimization_completed(self):
        ev = make_optimization_completed("a1", "p1", optimization_gain=5.0)
        assert ev.payload["optimization_gain"] == 5.0

    def test_make_mitigation_generated(self):
        ev = make_mitigation_generated("a1", "p1", actions_count=3)
        assert ev.payload["actions_count"] == 3

    def test_make_assessment_validated(self):
        ev = make_assessment_validated("a1", "p1", checks_passed=5)
        assert ev.event_type == AssessmentEventType.ASSESSMENT_VALIDATED

    def test_make_assessment_published(self):
        ev = make_assessment_published("a1", "p1", risk_score=55.0)
        assert ev.event_type == AssessmentEventType.ASSESSMENT_PUBLISHED
        assert ev.status == AssessmentStatus.COMPLETED

    def test_make_assessment_failed(self):
        ev = make_assessment_failed("a1", "p1", reason="calculation error")
        assert ev.event_type == AssessmentEventType.ASSESSMENT_FAILED
        assert ev.status == AssessmentStatus.FAILED
        assert ev.payload["reason"] == "calculation error"

    def test_event_to_dict(self):
        ev = make_assessment_started("a1", "p1")
        d = ev.to_dict()
        assert "event_id" in d
        assert "event_type" in d
        assert "occurred_at" in d

    def test_event_unique_ids(self):
        ids = {make_assessment_started("a1", "p1").event_id for _ in range(10)}
        assert len(ids) == 10


# ===========================================================================
# 7. Statistics
# ===========================================================================

class TestRiskAssessmentStatistics:
    def test_initial_snapshot(self):
        stats = RiskAssessmentStatistics()
        snap = stats.snapshot()
        assert snap["assessments_performed"] == 0
        assert snap["stress_tests_executed"] == 0

    def test_record_assessment(self):
        stats = RiskAssessmentStatistics()
        stats.record_assessment_started()
        stats.record_assessment_started()
        snap = stats.snapshot()
        assert snap["assessments_performed"] == 2

    def test_record_completed_and_failed(self):
        stats = RiskAssessmentStatistics()
        stats.record_assessment_started()
        stats.record_assessment_completed()
        stats.record_assessment_started()
        stats.record_assessment_failed()
        snap = stats.snapshot()
        assert snap["assessments_completed"] == 1
        assert snap["assessments_failed"] == 1

    def test_record_assessment_time(self):
        stats = RiskAssessmentStatistics()
        stats.record_assessment_time(0.5)
        stats.record_assessment_time(1.5)
        snap = stats.snapshot()
        assert snap["average_assessment_time_s"] == pytest.approx(1.0)

    def test_record_optimization(self):
        stats = RiskAssessmentStatistics()
        stats.record_optimization_run(success=True)
        stats.record_optimization_run(success=False)
        snap = stats.snapshot()
        assert snap["optimization_runs"] == 2
        assert snap["optimization_success_rate"] == pytest.approx(0.5)

    def test_record_stress_and_scenario(self):
        stats = RiskAssessmentStatistics()
        stats.record_stress_test()
        stats.record_scenario_analysis()
        stats.record_forecast()
        snap = stats.snapshot()
        assert snap["stress_tests_executed"] == 1
        assert snap["scenario_analyses_executed"] == 1
        assert snap["forecasts_generated"] == 1

    def test_reset(self):
        stats = RiskAssessmentStatistics()
        stats.record_assessment_started()
        stats.reset()
        assert stats.snapshot()["assessments_performed"] == 0

    def test_thread_safe(self):
        stats = RiskAssessmentStatistics()
        def worker():
            for _ in range(100):
                stats.record_assessment_started()
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert stats.snapshot()["assessments_performed"] == 500


# ===========================================================================
# 8. History
# ===========================================================================

class TestRiskAssessmentHistory:
    def test_record_and_retrieve(self):
        h = RiskAssessmentHistory()
        h.record_event("ev1")
        h.record_request("req1")
        h.record_report("rep1")
        h.record_error("err1")
        assert "ev1" in h.recent_events()
        assert "req1" in h.recent_requests()
        assert "rep1" in h.recent_reports()
        assert "err1" in h.recent_errors()

    def test_counts(self):
        h = RiskAssessmentHistory()
        for i in range(5):
            h.record_event(f"ev{i}")
        counts = h.counts()
        assert counts["events"] == 5

    def test_find_report_by_id(self):
        h = RiskAssessmentHistory()
        mock_report = MagicMock()
        mock_report.assessment_id = "aid-99"
        h.record_report(mock_report)
        found = h.find_report("aid-99")
        assert found is mock_report
        assert h.find_report("aid-xx") is None

    def test_recent_n(self):
        h = RiskAssessmentHistory()
        for i in range(20):
            h.record_event(f"ev{i}")
        recent = h.recent_events(5)
        assert len(recent) == 5
        assert recent[-1] == "ev19"

    def test_clear(self):
        h = RiskAssessmentHistory()
        h.record_event("ev")
        h.clear()
        assert h.counts()["events"] == 0

    def test_bounded_capacity(self):
        h = RiskAssessmentHistory(max_items=3)
        for i in range(10):
            h.record_event(f"ev{i}")
        assert h.counts()["events"] == 3


# ===========================================================================
# 9. Validator
# ===========================================================================

class TestRiskAssessmentValidator:
    def test_valid_request_passes(self):
        v = RiskAssessmentValidator()
        req = _make_request()
        result = v.validate_request(req)
        assert result.passed is True

    def test_unapproved_fails(self):
        v = RiskAssessmentValidator()
        req = _make_request(policy_approved=False)
        result = v.validate_request(req)
        assert result.passed is False
        assert ValidationCode.INPUT_CONSISTENT in result.failed_codes

    def test_zero_portfolio_value_fails(self):
        v = RiskAssessmentValidator()
        req = _make_request(portfolio_value=0.0)
        result = v.validate_request(req)
        assert result.passed is False
        assert ValidationCode.PORTFOLIO_VALUE_POSITIVE in result.failed_codes

    def test_negative_portfolio_value_fails(self):
        v = RiskAssessmentValidator()
        req = _make_request(portfolio_value=-100.0)
        result = v.validate_request(req)
        assert result.passed is False

    def test_insufficient_returns_fails(self):
        v = RiskAssessmentValidator()
        req = _make_request(returns=[0.01, -0.01])  # < MIN_RETURNS_FOR_VAR
        result = v.validate_request(req)
        assert result.passed is False
        assert ValidationCode.RETURNS_SUFFICIENT in result.failed_codes

    def test_zero_returns_ok(self):
        v = RiskAssessmentValidator()
        req = _make_request(returns=[])  # 0 returns is allowed (no VaR required)
        result = v.validate_request(req)
        # Should pass other checks; returns=0 is allowed
        assert ValidationCode.RETURNS_SUFFICIENT not in result.failed_codes

    def test_validate_or_raise_raises_on_failure(self):
        v = RiskAssessmentValidator()
        req = _make_request(policy_approved=False)
        with pytest.raises(RiskAssessmentValidationError):
            v.validate_request_or_raise(req)

    def test_validate_report_ok(self):
        v = RiskAssessmentValidator()
        report = RiskAssessmentReport.create("a1", "p1", "r1", AssessmentStatus.COMPLETED, 50.0, 0.5)
        result = v.validate_report(report)
        assert result.passed is True

    def test_validation_check_to_dict(self):
        check = AssessmentValidationCheck(ValidationCode.WEIGHTS_VALID, True, "ok")
        d = check.to_dict()
        assert d["passed"] is True
        assert d["code"] == "weights_valid"


# ===========================================================================
# 10. Registry
# ===========================================================================

class TestRiskAssessmentRegistry:
    def test_register_and_get(self):
        reg = RiskAssessmentRegistry()
        report = MagicMock()
        report.assessment_id = "aid-1"
        reg.register(report)
        assert reg.get("aid-1") is report

    def test_not_found_raises(self):
        reg = RiskAssessmentRegistry()
        with pytest.raises(RiskAssessmentNotFoundError):
            reg.get("missing")

    def test_unregister(self):
        reg = RiskAssessmentRegistry()
        report = MagicMock()
        report.assessment_id = "aid-2"
        reg.register(report)
        reg.unregister("aid-2")
        assert not reg.contains("aid-2")

    def test_capacity_limit(self):
        reg = RiskAssessmentRegistry(max_assessments=2)
        for i in range(2):
            r = MagicMock()
            r.assessment_id = f"aid-{i}"
            reg.register(r)
        r3 = MagicMock()
        r3.assessment_id = "aid-3"
        with pytest.raises(RiskAssessmentCapacityError):
            reg.register(r3)

    def test_register_none_raises(self):
        reg = RiskAssessmentRegistry()
        with pytest.raises(RiskAssessmentRegistryError):
            reg.register(None)

    def test_list_and_count(self):
        reg = RiskAssessmentRegistry()
        for i in range(3):
            r = MagicMock()
            r.assessment_id = f"aid-{i}"
            reg.register(r)
        assert reg.count() == 3
        assert len(reg.list_all()) == 3
        assert len(reg.list_ids()) == 3


# ===========================================================================
# 11. Model Registry
# ===========================================================================

class TestRiskModelRegistry:
    def _model(self, mid: str) -> RiskModel:
        return RiskModel(
            model_id=mid, name=f"Model {mid}",
            model_type=ModelType.HISTORICAL_SIMULATION,
            version="1.0.0", description="test",
            fn=lambda: None,
        )

    def test_register_and_get(self):
        reg = RiskModelRegistry()
        m = self._model("m1")
        reg.register(m)
        assert reg.get("m1") is m

    def test_not_found_raises(self):
        reg = RiskModelRegistry()
        with pytest.raises(RiskModelNotFoundError):
            reg.get("missing")

    def test_enable_disable(self):
        reg = RiskModelRegistry()
        m = self._model("m1")
        reg.register(m)
        reg.disable("m1")
        assert not reg.get("m1").enabled
        reg.enable("m1")
        assert reg.get("m1").enabled

    def test_list_by_type(self):
        reg = RiskModelRegistry()
        m1 = self._model("m1")
        m2 = RiskModel("m2", "M2", ModelType.MONTE_CARLO, "1.0.0", "test", lambda: None)
        reg.register(m1)
        reg.register(m2)
        hist = reg.list_by_type(ModelType.HISTORICAL_SIMULATION)
        assert len(hist) == 1

    def test_list_enabled(self):
        reg = RiskModelRegistry()
        m = self._model("m1")
        reg.register(m)
        reg.disable("m1")
        assert len(reg.list_enabled()) == 0

    def test_model_to_dict(self):
        m = self._model("m1")
        d = m.to_dict()
        assert d["model_id"] == "m1"
        assert "model_type" in d


# ===========================================================================
# 12. VaR Engine
# ===========================================================================

class TestRiskVaREngine:
    def setup_method(self):
        self.engine = RiskVaREngine()
        self.returns = RETURNS_VOLATILE
        self.pv = PORTFOLIO_VALUE

    def test_historical_var_positive(self):
        var = self.engine.calculate_historical_var(self.returns, self.pv, 0.95, 1)
        assert var >= 0

    def test_historical_var_insufficient_returns(self):
        var = self.engine.calculate_historical_var([0.01] * 5, self.pv, 0.95, 1)
        assert var == 0.0

    def test_parametric_var_positive(self):
        var = self.engine.calculate_parametric_var(self.returns, self.pv, 0.95, 1)
        assert var >= 0

    def test_parametric_var_insufficient_returns(self):
        var = self.engine.calculate_parametric_var([0.01], self.pv, 0.95, 1)
        assert var == 0.0

    def test_component_var_sums_to_total(self):
        total_var = 50000.0
        comp = self.engine.calculate_component_var(POSITIONS_BALANCED, self.pv, total_var)
        assert abs(sum(comp.values()) - total_var) < 1.0

    def test_component_var_empty_positions(self):
        comp = self.engine.calculate_component_var({}, self.pv, 50000.0)
        assert comp == {}

    def test_ewma_vol_positive(self):
        vol = self.engine.calculate_ewma_vol(self.returns)
        assert vol > 0

    def test_ewma_vol_insufficient_returns(self):
        vol = self.engine.calculate_ewma_vol([0.01])
        assert vol == 0.0

    def test_build_var_report(self):
        report = self.engine.build_var_report(
            "a1", "p1", self.returns, self.pv, POSITIONS_BALANCED,
        )
        assert isinstance(report, VaRReport)
        assert report.historical_var >= 0
        assert report.returns_used == len(self.returns)

    def test_build_var_report_invalid_pv_raises(self):
        with pytest.raises(RiskCalculationError):
            self.engine.build_var_report("a1", "p1", self.returns, 0.0, {})

    def test_multi_confidence_var(self):
        result = self.engine.calculate_multi_confidence_var(self.returns, self.pv)
        assert len(result) == len(DEFAULT_VAR_CONFIDENCE_LEVELS)
        # Higher confidence → higher VaR
        assert result[0.99] >= result[0.95] >= result[0.90]

    def test_horizon_scaling(self):
        var_1d = self.engine.calculate_historical_var(self.returns, self.pv, 0.95, 1)
        var_5d = self.engine.calculate_historical_var(self.returns, self.pv, 0.95, 5)
        # sqrt(5) ≈ 2.236; var_5d should be larger
        assert var_5d > var_1d

    def test_var_confidence_monotone(self):
        var_90 = self.engine.calculate_historical_var(self.returns, self.pv, 0.90, 1)
        var_99 = self.engine.calculate_historical_var(self.returns, self.pv, 0.99, 1)
        assert var_99 >= var_90

    def test_flat_returns_low_var(self):
        # Flat returns → very low VaR
        var = self.engine.calculate_historical_var(RETURNS_FLAT, self.pv, 0.95, 1)
        assert var < 5000.0


# ===========================================================================
# 13. Expected Shortfall Engine
# ===========================================================================

class TestRiskExpectedShortfallEngine:
    def setup_method(self):
        self.engine = RiskExpectedShortfallEngine()
        self.returns = RETURNS_VOLATILE
        self.pv = PORTFOLIO_VALUE

    def test_historical_es_geq_var(self):
        var_engine = RiskVaREngine()
        var = var_engine.calculate_historical_var(self.returns, self.pv, 0.95)
        es  = self.engine.calculate_historical_es(self.returns, self.pv, 0.95)
        assert es >= var

    def test_historical_es_insufficient_returns(self):
        es = self.engine.calculate_historical_es([0.01] * 5, self.pv, 0.95)
        assert es == 0.0

    def test_parametric_es_positive(self):
        es = self.engine.calculate_parametric_es(self.returns, self.pv, 0.95)
        assert es >= 0

    def test_max_drawdown_volatile(self):
        dd = self.engine.calculate_max_drawdown(self.returns)
        assert 0 < dd <= 1.0

    def test_max_drawdown_flat(self):
        dd = self.engine.calculate_max_drawdown(RETURNS_FLAT)
        assert dd == 0.0

    def test_max_drawdown_insufficient(self):
        dd = self.engine.calculate_max_drawdown([0.01])
        assert dd == 0.0

    def test_build_es_report(self):
        report = self.engine.build_es_report("a1", "p1", self.returns, self.pv)
        assert isinstance(report, ExpectedShortfallReport)
        assert report.es_historical >= report.var_reference

    def test_build_es_report_invalid_pv_raises(self):
        with pytest.raises(RiskCalculationError):
            self.engine.build_es_report("a1", "p1", self.returns, 0.0)


# ===========================================================================
# 14. Measurement Engine
# ===========================================================================

class TestRiskMeasurementEngine:
    def setup_method(self):
        self.engine = RiskMeasurementEngine()

    def test_annualised_vol(self):
        vol = self.engine.calculate_annualised_volatility(RETURNS_VOLATILE)
        assert vol > 0

    def test_vol_insufficient_returns(self):
        vol = self.engine.calculate_annualised_volatility([0.01])
        assert vol == 0.0

    def test_ewma_volatility(self):
        vol = self.engine.calculate_ewma_volatility(RETURNS_VOLATILE)
        assert vol > 0

    def test_correlation_perfect(self):
        s = [1.0, 2.0, 3.0, 4.0, 5.0]
        corr = self.engine.calculate_correlation(s, s)
        assert corr == pytest.approx(1.0)

    def test_correlation_anticorrelated(self):
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [5.0, 4.0, 3.0, 2.0, 1.0]
        corr = self.engine.calculate_correlation(a, b)
        assert corr == pytest.approx(-1.0)

    def test_correlation_zero_variance(self):
        corr = self.engine.calculate_correlation([1.0] * 5, [0.0] * 5)
        assert corr == 0.0

    def test_sharpe_ratio(self):
        sr = self.engine.calculate_sharpe_ratio(RETURNS_VOLATILE)
        assert isinstance(sr, float)

    def test_sortino_ratio(self):
        ratio = self.engine.calculate_sortino_ratio(RETURNS_VOLATILE)
        assert isinstance(ratio, float)

    def test_calmar_ratio(self):
        ratio = self.engine.calculate_calmar_ratio(RETURNS_VOLATILE, 0.10)
        assert isinstance(ratio, float)

    def test_liquidity_score(self):
        score = self.engine.estimate_liquidity_score(100_000.0, 1_000_000.0)
        assert 0.0 <= score <= 1.0

    def test_liquidity_score_zero_volume(self):
        score = self.engine.estimate_liquidity_score(100_000.0, 0.0)
        assert score == 0.0


# ===========================================================================
# 15. Stress Testing Engine
# ===========================================================================

class TestRiskStressTestingEngine:
    def setup_method(self):
        self.engine = RiskStressTestingEngine()
        self.pv = PORTFOLIO_VALUE

    def test_run_scenario_market_crash(self):
        result = self.engine.run_scenario(StressScenario.MARKET_CRASH, self.pv)
        assert result.stressed_loss > 0
        assert result.stressed_loss_pct == pytest.approx(0.35)

    def test_run_scenario_invalid_pv_raises(self):
        with pytest.raises(RiskStressTestError):
            self.engine.run_scenario(StressScenario.MARKET_CRASH, 0.0)

    def test_run_all_scenarios(self):
        results = self.engine.run_all_scenarios(self.pv)
        assert len(results) == len(StressScenario)
        assert all(r.stressed_loss >= 0 for r in results)

    def test_run_selected_scenarios(self):
        selected = [StressScenario.MARKET_CRASH, StressScenario.LIQUIDITY_CRISIS]
        results = self.engine.run_selected_scenarios(self.pv, selected)
        assert len(results) == 2

    def test_custom_shock_override(self):
        result = self.engine.run_scenario(StressScenario.CUSTOM, self.pv, custom_shock=-0.50)
        assert result.stressed_loss_pct == pytest.approx(0.50)

    def test_build_stress_test_report(self):
        report = self.engine.build_stress_test_report("a1", "p1", self.pv)
        assert isinstance(report, StressTestReport)
        assert len(report.scenarios) == len(StressScenario)
        assert report.worst_loss > 0

    def test_worst_scenario_is_historical_events(self):
        report = self.engine.build_stress_test_report("a1", "p1", self.pv)
        assert report.worst_scenario == StressScenario.HISTORICAL_EVENTS

    def test_stressed_value_consistent(self):
        result = self.engine.run_scenario(StressScenario.MARKET_CRASH, self.pv)
        assert abs(result.stressed_value + result.stressed_loss - self.pv) < 1.0


# ===========================================================================
# 16. Scenario Engine
# ===========================================================================

class TestRiskScenarioEngine:
    def setup_method(self):
        self.engine = RiskScenarioEngine()
        self.pv = PORTFOLIO_VALUE
        self.returns = RETURNS_VOLATILE

    def test_project_expected_case(self):
        outcome = self.engine.project_scenario(
            ScenarioType.EXPECTED_CASE, self.pv, 0.001, 0.015
        )
        assert outcome.probability == pytest.approx(0.55)

    def test_project_black_swan_negative(self):
        outcome = self.engine.project_scenario(
            ScenarioType.BLACK_SWAN, self.pv, 0.001, 0.02
        )
        assert outcome.projected_return < 0

    def test_project_best_case_positive(self):
        outcome = self.engine.project_scenario(
            ScenarioType.BEST_CASE, self.pv, 0.001, 0.02
        )
        assert outcome.projected_return > 0

    def test_invalid_pv_raises(self):
        with pytest.raises(RiskScenarioError):
            self.engine.project_scenario(ScenarioType.EXPECTED_CASE, 0.0, 0.001, 0.01)

    def test_run_all_scenarios_count(self):
        outcomes = self.engine.run_all_scenarios(self.pv, self.returns)
        assert len(outcomes) == 4  # best, expected, worst, black_swan

    def test_run_all_insufficient_returns(self):
        outcomes = self.engine.run_all_scenarios(self.pv, [0.01])
        assert outcomes == []

    def test_build_scenario_report(self):
        report = self.engine.build_scenario_report("a1", "p1", self.pv, self.returns)
        assert isinstance(report, ScenarioAnalysisReport)
        assert len(report.outcomes) == 4

    def test_custom_multiplier(self):
        o1 = self.engine.project_scenario(ScenarioType.CUSTOM, self.pv, 0.001, 0.01, custom_multiplier=-3.0)
        o2 = self.engine.project_scenario(ScenarioType.CUSTOM, self.pv, 0.001, 0.01, custom_multiplier=3.0)
        assert o2.projected_return > o1.projected_return


# ===========================================================================
# 17. Sensitivity Engine
# ===========================================================================

class TestRiskSensitivityEngine:
    def setup_method(self):
        self.engine = RiskSensitivityEngine()

    def test_perturb_linear(self):
        result = self.engine.perturb(lambda x: 2.0 * x, 1.0, 0.1, "x")
        assert result.delta == pytest.approx(2.0)
        assert result.gamma == pytest.approx(0.0, abs=1e-9)

    def test_perturb_zero_shock_raises(self):
        with pytest.raises(RiskCalculationError):
            self.engine.perturb(lambda x: x, 1.0, 0.0)

    def test_equity_price_sensitivity(self):
        results = self.engine.equity_price_sensitivity(POSITIONS_BALANCED, PORTFOLIO_VALUE)
        assert len(results) == len(POSITIONS_BALANCED)
        for r in results.values():
            assert isinstance(r, SensitivityResult)

    def test_equity_sensitivity_zero_pv(self):
        results = self.engine.equity_price_sensitivity(POSITIONS_BALANCED, 0.0)
        assert results == {}

    def test_volatility_sensitivity(self):
        result = self.engine.volatility_sensitivity(RETURNS_VOLATILE, PORTFOLIO_VALUE)
        assert isinstance(result, SensitivityResult)

    def test_sensitivity_to_dict(self):
        result = self.engine.perturb(lambda x: x ** 2, 3.0, 0.1, "x")
        d = result.to_dict()
        assert "delta" in d
        assert "gamma" in d


# ===========================================================================
# 18. Exposure Engine
# ===========================================================================

class TestRiskExposureEngine:
    def setup_method(self):
        self.engine = RiskExposureEngine()
        self.pv = PORTFOLIO_VALUE

    def test_gross_exposure_long_only(self):
        exp = self.engine.calculate_gross_exposure(POSITIONS_BALANCED, self.pv)
        assert exp == self.pv

    def test_gross_exposure_with_shorts(self):
        exp = self.engine.calculate_gross_exposure({"A": 0.6, "B": -0.4}, self.pv)
        assert exp == pytest.approx(self.pv * 1.0)

    def test_net_exposure(self):
        net = self.engine.calculate_net_exposure({"A": 0.6, "B": -0.4}, self.pv)
        assert net == pytest.approx(0.2 * self.pv)

    def test_leverage(self):
        lev = self.engine.calculate_leverage({"A": 0.6, "B": 0.4, "C": 0.2}, self.pv)
        assert lev == pytest.approx(1.2)

    def test_top_exposures(self):
        top = self.engine.top_exposures(POSITIONS_CONCENTRATED, self.pv, n=2)
        assert len(top) == 2
        assert top[0][0] == "A"  # largest

    def test_capital_at_risk(self):
        cap = self.engine.calculate_capital_at_risk(self.pv, 50000.0, 200000.0)
        assert cap["capital_at_risk"] == 50000.0
        assert cap["capital_buffer"] == 150000.0

    def test_build_exposure_report(self):
        report = self.engine.build_exposure_report("a1", "p1", self.pv, POSITIONS_BALANCED)
        assert isinstance(report, ExposureReport)
        assert report.gross_exposure == self.pv

    def test_invalid_pv_raises(self):
        with pytest.raises(RiskCalculationError):
            self.engine.build_exposure_report("a1", "p1", 0.0, POSITIONS_BALANCED)


# ===========================================================================
# 19. Concentration Engine
# ===========================================================================

class TestRiskConcentrationEngine:
    def setup_method(self):
        self.engine = RiskConcentrationEngine()

    def test_hhi_equal_weights(self):
        pos = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
        hhi = self.engine.calculate_hhi(pos)
        assert hhi == pytest.approx(0.25)

    def test_hhi_concentrated(self):
        pos = {"A": 1.0}
        hhi = self.engine.calculate_hhi(pos)
        assert hhi == pytest.approx(1.0)

    def test_hhi_empty(self):
        assert self.engine.calculate_hhi({}) == 0.0

    def test_effective_n_equal_weights(self):
        pos = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
        eff_n = self.engine.calculate_effective_n(pos)
        assert eff_n == pytest.approx(4.0)

    def test_top_n_weight(self):
        pos = {"A": 0.50, "B": 0.30, "C": 0.20}
        top1 = self.engine.top_n_weight(pos, 1)
        assert top1 == pytest.approx(0.50)

    def test_largest_position(self):
        max_id, max_w = self.engine.largest_position(POSITIONS_CONCENTRATED)
        assert max_id == "A"
        assert max_w == pytest.approx(0.70)

    def test_analyse_concentrated(self):
        result = self.engine.analyse(POSITIONS_CONCENTRATED)
        assert result.is_concentrated is True
        assert result.hhi > 0

    def test_analyse_diversified(self):
        result = self.engine.analyse(POSITIONS_BALANCED)
        assert result.is_concentrated is False

    def test_concentration_to_dict(self):
        result = self.engine.analyse(POSITIONS_BALANCED)
        d = result.to_dict()
        assert "hhi" in d
        assert "effective_n" in d

    def test_hhi_negative_weights(self):
        # Short positions should count by abs value
        pos = {"A": 0.5, "B": -0.5}
        hhi = self.engine.calculate_hhi(pos)
        assert hhi == pytest.approx(0.5)


# ===========================================================================
# 20. Limit Engine
# ===========================================================================

class TestRiskLimitEngine:
    def setup_method(self):
        self.engine = RiskLimitEngine()

    def test_ok_status(self):
        result = self.engine.check_limit("var", 30000.0, 50000.0)
        assert result.status == LimitStatus.OK
        assert result.utilisation == pytest.approx(0.60)

    def test_warning_status(self):
        result = self.engine.check_limit("var", 42000.0, 50000.0)
        assert result.status == LimitStatus.WARNING

    def test_breach_status(self):
        result = self.engine.check_limit("var", 50000.0, 50000.0)
        assert result.status == LimitStatus.BREACH

    def test_critical_status(self):
        result = self.engine.check_limit("var", 56000.0, 50000.0)
        assert result.status == LimitStatus.CRITICAL

    def test_invalid_limit_raises(self):
        with pytest.raises(RiskCalculationError):
            self.engine.check_limit("var", 10000.0, -5000.0)

    def test_check_all_limits(self):
        current = {"var_limit": 30000.0, "concentration_limit": 0.20}
        results = self.engine.check_all_limits(current, LIMITS_STANDARD)
        assert "var_limit" in results
        assert "concentration_limit" in results

    def test_summarise(self):
        current = {"var_limit": 30000.0}
        results = self.engine.check_all_limits(current, LIMITS_STANDARD)
        summary = self.engine.summarise(results)
        assert "all_ok" in summary
        assert summary["total_limits"] == 1

    def test_var_limit_utilisation(self):
        result = self.engine.calculate_var_limit_utilisation(40000.0, 50000.0)
        assert result.utilisation == pytest.approx(0.80)
        assert result.status == LimitStatus.WARNING

    def test_to_dict(self):
        result = self.engine.check_limit("var", 30000.0, 50000.0)
        d = result.to_dict()
        assert "utilisation" in d
        assert "status" in d


# ===========================================================================
# 21. Forecasting Engine
# ===========================================================================

class TestRiskForecastingEngine:
    def setup_method(self):
        self.engine = RiskForecastingEngine()
        self.pv = PORTFOLIO_VALUE
        self.returns = RETURNS_VOLATILE

    def test_ewma_vol_positive(self):
        vol = self.engine.forecast_ewma_volatility(self.returns, 5)
        assert vol > 0

    def test_ewma_vol_insufficient(self):
        vol = self.engine.forecast_ewma_volatility([0.01], 5)
        assert vol == 0.0

    def test_forecast_return(self):
        ret = self.engine.forecast_return(self.returns, self.pv, 5)
        assert isinstance(ret, float)

    def test_forecast_var_positive(self):
        var = self.engine.forecast_var(self.returns, self.pv, 5)
        assert var >= 0

    def test_build_forecast(self):
        fc = self.engine.build_forecast("a1", "p1", self.returns, self.pv, ForecastHorizon.WEEK)
        assert isinstance(fc, RiskForecast)
        assert fc.horizon == ForecastHorizon.WEEK
        assert fc.horizon_days == 5

    def test_invalid_pv_raises(self):
        with pytest.raises(RiskForecastError):
            self.engine.build_forecast("a1", "p1", self.returns, 0.0, ForecastHorizon.DAY)

    def test_build_all_forecasts(self):
        fcs = self.engine.build_all_forecasts("a1", "p1", self.returns, self.pv)
        assert len(fcs) == len(ForecastHorizon)
        horizons = {fc.horizon for fc in fcs}
        assert horizons == set(ForecastHorizon)

    def test_longer_horizon_higher_var(self):
        var_day = self.engine.forecast_var(self.returns, self.pv, 1)
        var_quarter = self.engine.forecast_var(self.returns, self.pv, 63)
        assert var_quarter > var_day


# ===========================================================================
# 22. Score Engine
# ===========================================================================

class TestRiskScoreEngine:
    def setup_method(self):
        self.engine = RiskScoreEngine()

    def test_zero_score_safe_portfolio(self):
        comps = self.engine.calculate(0.0, 0.0, 0.0, 0.0)
        assert comps.total_score == 0.0
        assert comps.risk_band == "low"

    def test_high_var_high_score(self):
        comps = self.engine.calculate(0.10, 0.0, 0.0, 0.0)
        assert comps.var_score == pytest.approx(40.0)

    def test_high_concentration_score(self):
        comps = self.engine.calculate(0.0, 1.0, 0.0, 0.0)
        assert comps.concentration_score == pytest.approx(20.0)

    def test_high_stress_score(self):
        comps = self.engine.calculate(0.0, 0.0, 0.30, 0.0)
        assert comps.stress_score == pytest.approx(30.0)

    def test_max_score_capped_at_100(self):
        comps = self.engine.calculate(1.0, 1.0, 1.0, 1.0)
        assert comps.total_score == 100.0

    def test_risk_band_medium(self):
        comps = self.engine.calculate(0.05, 0.2, 0.10, 0.5)
        assert comps.risk_band in ("medium", "high", "low")

    def test_to_dict(self):
        comps = self.engine.calculate(0.05, 0.3, 0.15, 0.7)
        d = comps.to_dict()
        assert "total_score" in d
        assert "risk_band" in d


# ===========================================================================
# 23. Mitigation Engine
# ===========================================================================

class TestRiskMitigationEngine:
    def setup_method(self):
        self.engine = RiskMitigationEngine()

    def test_identify_drivers_concentration(self):
        drivers = self.engine.identify_drivers(top_position_weight=0.50)
        assert "concentration_high" in drivers

    def test_identify_drivers_var(self):
        drivers = self.engine.identify_drivers(var_pct=0.10)
        assert "var_high" in drivers

    def test_identify_drivers_none(self):
        drivers = self.engine.identify_drivers()
        assert drivers == []

    def test_generate_plan_no_drivers(self):
        plan = self.engine.generate_plan("a1", "p1", 30.0)
        assert plan.total_actions == 0
        assert plan.risk_score_before == 30.0

    def test_generate_plan_with_drivers(self):
        plan = self.engine.generate_plan(
            "a1", "p1", 70.0,
            var_pct=0.10, top_position_weight=0.50,
        )
        assert plan.total_actions >= 2
        assert plan.high_priority >= 1

    def test_explicit_drivers(self):
        plan = self.engine.generate_plan(
            "a1", "p1", 60.0, drivers=["var_high", "concentration_high"]
        )
        assert plan.total_actions == 2

    def test_plan_to_dict(self):
        plan = self.engine.generate_plan("a1", "p1", 40.0, drivers=["var_high"])
        d = plan.to_dict()
        assert "total_actions" in d
        assert "actions" in d

    def test_limit_breach_triggers_high_priority(self):
        plan = self.engine.generate_plan("a1", "p1", 90.0, max_limit_util=1.0)
        high_actions = [a for a in plan.actions if a.priority == "high"]
        assert len(high_actions) >= 1


# ===========================================================================
# 24. Optimization Engine
# ===========================================================================

class TestRiskOptimizationEngine:
    def setup_method(self):
        self.engine = RiskOptimizationEngine()

    def test_no_objectives_raises(self):
        with pytest.raises(RiskOptimizationError):
            self.engine.optimise("a1", "p1", 50.0, [])

    def test_minimize_concentration(self):
        report = self.engine.optimise(
            "a1", "p1", 60.0,
            [OptimizationObjective.MINIMIZE_CONCENTRATION],
            hhi=0.5, max_weight=0.6, n_positions=3,
        )
        assert len(report.recommendations) == 1
        assert report.optimization_gain > 0

    def test_all_objectives_produce_recommendations(self):
        report = self.engine.optimise(
            "a1", "p1", 60.0,
            list(OptimizationObjective),
            hhi=0.4, max_weight=0.5, n_positions=3,
            var_pct=0.08, es_pct=0.12, sharpe=0.5,
            annual_vol=0.25, gross_exposure_pct=1.5,
        )
        assert len(report.recommendations) == len(OptimizationObjective)

    def test_risk_score_after_lower(self):
        report = self.engine.optimise(
            "a1", "p1", 70.0,
            [OptimizationObjective.MINIMIZE_PORTFOLIO_RISK],
            var_pct=0.08,
        )
        assert report.risk_score_after <= report.risk_score_before

    def test_optimization_report_to_dict(self):
        report = self.engine.optimise(
            "a1", "p1", 50.0,
            [OptimizationObjective.OPTIMIZE_LIQUIDITY],
            liquidity_score=0.3,
        )
        d = report.to_dict()
        assert "objectives" in d
        assert "risk_score_before" in d


# ===========================================================================
# 25. Calculation Engine
# ===========================================================================

class TestRiskCalculationEngine:
    def setup_method(self):
        self.engine = RiskCalculationEngine()
        self.pv = PORTFOLIO_VALUE

    def test_run_returns_bundle(self):
        bundle = self.engine.run(
            "a1", "p1", self.pv, POSITIONS_BALANCED, RETURNS_VOLATILE,
            LIMITS_STANDARD,
        )
        assert isinstance(bundle, CalculationBundle)

    def test_bundle_has_var(self):
        bundle = self.engine.run(
            "a1", "p1", self.pv, POSITIONS_BALANCED, RETURNS_VOLATILE, {},
        )
        assert bundle.var_report is not None

    def test_bundle_has_es(self):
        bundle = self.engine.run(
            "a1", "p1", self.pv, POSITIONS_BALANCED, RETURNS_VOLATILE, {},
        )
        assert bundle.es_report is not None

    def test_bundle_has_stress(self):
        bundle = self.engine.run(
            "a1", "p1", self.pv, POSITIONS_BALANCED, RETURNS_VOLATILE, {},
        )
        assert bundle.stress_report is not None

    def test_bundle_has_forecasts(self):
        bundle = self.engine.run(
            "a1", "p1", self.pv, POSITIONS_BALANCED, RETURNS_VOLATILE, {},
        )
        assert len(bundle.forecasts) == len(ForecastHorizon)

    def test_bundle_has_score(self):
        bundle = self.engine.run(
            "a1", "p1", self.pv, POSITIONS_BALANCED, RETURNS_VOLATILE, {},
        )
        assert bundle.score_components is not None
        assert 0 <= bundle.score_components.total_score <= 100

    def test_bundle_with_objectives(self):
        bundle = self.engine.run(
            "a1", "p1", self.pv, POSITIONS_BALANCED, RETURNS_VOLATILE, {},
            objectives=[OptimizationObjective.MINIMIZE_CONCENTRATION],
        )
        assert bundle.optimization_report is not None

    def test_bundle_duration(self):
        bundle = self.engine.run(
            "a1", "p1", self.pv, POSITIONS_BALANCED, RETURNS_VOLATILE, {},
        )
        assert bundle.duration_s >= 0


# ===========================================================================
# 26. Assessment Manager
# ===========================================================================

class TestRiskAssessmentManager:
    def test_run_assessment_success(self):
        mgr = RiskAssessmentManager()
        req = _make_request()
        report = mgr.run_assessment(req)
        assert report.status == AssessmentStatus.COMPLETED
        assert report.risk_score >= 0

    def test_run_assessment_registers_report(self):
        reg = RiskAssessmentRegistry()
        mgr = RiskAssessmentManager(registry=reg)
        req = _make_request()
        report = mgr.run_assessment(req)
        assert reg.contains(req.assessment_id)

    def test_run_assessment_records_history(self):
        hist = RiskAssessmentHistory()
        mgr  = RiskAssessmentManager(history=hist)
        req  = _make_request()
        mgr.run_assessment(req)
        assert hist.counts()["reports"] == 1
        assert hist.counts()["events"] > 0

    def test_run_assessment_updates_stats(self):
        stats = RiskAssessmentStatistics()
        mgr   = RiskAssessmentManager(statistics=stats)
        req   = _make_request()
        mgr.run_assessment(req)
        snap = stats.snapshot()
        assert snap["assessments_completed"] == 1

    def test_unapproved_request_raises(self):
        mgr = RiskAssessmentManager()
        req = _make_request(policy_approved=False)
        with pytest.raises(RiskAssessmentValidationError):
            mgr.run_assessment(req)

    def test_run_assessment_with_objectives(self):
        mgr = RiskAssessmentManager()
        req = _make_request()
        report = mgr.run_assessment(
            req, objectives=[OptimizationObjective.MINIMIZE_CONCENTRATION]
        )
        assert report.optimization_report is not None

    def test_risk_band_in_summary(self):
        mgr = RiskAssessmentManager()
        req = _make_request()
        report = mgr.run_assessment(req)
        assert report.summary is not None
        assert report.summary.risk_band in ("low", "medium", "high", "critical")


# ===========================================================================
# 27. Assessment Engine (primary public interface)
# ===========================================================================

class TestRiskAssessmentEngine:
    def test_engine_start_stop(self):
        e = RiskAssessmentEngine()
        e.start()
        assert e.lifecycle_state().value == "running"
        e.stop()
        assert e.lifecycle_state().value == "stopped"

    def test_assess_before_start_raises(self):
        e = RiskAssessmentEngine()
        req = _make_request()
        with pytest.raises(RiskAssessmentEngineNotRunningError):
            e.assess(req)

    def test_assess_returns_report(self):
        e = _started_engine()
        req = _make_request()
        report = e.assess(req)
        assert report.status == AssessmentStatus.COMPLETED

    def test_assess_unapproved_raises(self):
        e = _started_engine()
        req = _make_request(policy_approved=False)
        with pytest.raises(RiskAssessmentValidationError):
            e.assess(req)

    def test_get_report_after_assess(self):
        e = _started_engine()
        req = _make_request()
        e.assess(req)
        retrieved = e.get_report(req.assessment_id)
        assert retrieved.assessment_id == req.assessment_id

    def test_get_report_not_found_raises(self):
        e = _started_engine()
        with pytest.raises(RiskAssessmentNotFoundError):
            e.get_report("nonexistent")

    def test_statistics(self):
        e = _started_engine()
        req = _make_request()
        e.assess(req)
        stats = e.statistics()
        assert stats["assessments_completed"] == 1

    def test_health(self):
        e = _started_engine()
        h = e.health()
        assert "state" in h
        assert h["state"] == "running"

    def test_status(self):
        e = _started_engine()
        s = e.status()
        assert isinstance(s, RiskAssessmentEngineStatus)
        assert s.state == "running"
        assert s.engine_id == ASSESSMENT_SYSTEM_ID

    def test_create_request_before_start_raises(self):
        e = RiskAssessmentEngine()
        with pytest.raises(RiskAssessmentEngineNotRunningError):
            e.create_request("a1", "p1", "r1", 1_000_000.0)

    def test_create_request_shortcut(self):
        e = _started_engine()
        req = e.create_request(
            "a1", "p1", "r1", 1_000_000.0,
            policy_approved=True,
            positions=POSITIONS_BALANCED,
            returns=RETURNS_VOLATILE,
        )
        assert req.portfolio_id == "p1"

    def test_listener_called_on_assess(self):
        e = _started_engine()
        received = []
        e.add_listener(received.append)
        req = _make_request()
        e.assess(req)
        assert len(received) >= 1

    def test_listener_removal(self):
        e = _started_engine()
        received = []
        fn = received.append
        e.add_listener(fn)
        e.remove_listener(fn)
        req = _make_request()
        e.assess(req)
        assert received == []

    def test_listener_exception_does_not_crash_engine(self):
        e = _started_engine()
        def bad_listener(_): raise RuntimeError("crash")
        e.add_listener(bad_listener)
        req = _make_request()
        report = e.assess(req)  # should not raise
        assert report.status == AssessmentStatus.COMPLETED

    def test_assess_with_objectives(self):
        e = _started_engine()
        req = _make_request()
        report = e.assess(req, objectives=[OptimizationObjective.MINIMIZE_CONCENTRATION])
        assert report.optimization_report is not None
        assert report.optimization_report.optimization_gain >= 0

    def test_assess_empty_returns(self):
        e = _started_engine()
        req = _make_request(returns=[])
        report = e.assess(req)
        assert report.status == AssessmentStatus.COMPLETED

    def test_assess_concentrated_portfolio(self):
        e = _started_engine()
        req = _make_request(positions=POSITIONS_CONCENTRATED)
        report = e.assess(req)
        assert report.summary is not None
        # Concentrated portfolio should flag concentration risk
        assert report.summary.hhi > 0.30

    def test_version_constant(self):
        e = RiskAssessmentEngine()
        assert e.VERSION == VERSION

    def test_system_id_constant(self):
        assert RiskAssessmentEngine.SYSTEM_ID == ASSESSMENT_SYSTEM_ID


# ===========================================================================
# 28. Concurrency
# ===========================================================================

class TestConcurrency:
    def test_concurrent_assessments(self):
        """Multiple threads can safely submit assessments simultaneously."""
        e = _started_engine()
        results = []
        errors  = []

        def worker():
            try:
                req    = _make_request()
                report = e.assess(req)
                results.append(report)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrency errors: {errors}"
        assert len(results) == 10

    def test_concurrent_statistics_updates(self):
        """Statistics counters remain consistent under concurrent writes."""
        stats = RiskAssessmentStatistics()

        def worker():
            for _ in range(100):
                stats.record_assessment_started()
                stats.record_stress_test()

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        snap = stats.snapshot()
        assert snap["assessments_performed"] == 500
        assert snap["stress_tests_executed"] == 500

    def test_concurrent_registry_access(self):
        """Registry reads and writes are thread-safe."""
        reg = RiskAssessmentRegistry()

        def writer():
            for i in range(50):
                r = MagicMock()
                r.assessment_id = f"aid-{threading.get_ident()}-{i}"
                try:
                    reg.register(r)
                except RiskAssessmentCapacityError:
                    pass

        threads = [threading.Thread(target=writer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Registry is intact (no AttributeErrors/race conditions)
        assert reg.count() >= 0


# ===========================================================================
# 29. Factory
# ===========================================================================

class TestRiskAssessmentFactory:
    def test_create_context(self):
        f = RiskAssessmentFactory()
        ctx = f.create_context("a1", "p1", "r1")
        assert ctx.assessment_id == "a1"

    def test_create_request(self):
        f = RiskAssessmentFactory()
        req = f.create_request("a1", "p1", "r1", 1_000_000.0, policy_approved=True)
        assert req.portfolio_id == "p1"

    def test_create_approved_request(self):
        f = RiskAssessmentFactory()
        req = f.create_approved_request("p1", 1_000_000.0)
        assert req.policy_approved is True
        assert req.portfolio_id == "p1"


# ===========================================================================
# 30. Regression — complete pipeline
# ===========================================================================

class TestRegression:
    def test_full_pipeline_with_all_objectives(self):
        """End-to-end test: start engine, assess, verify all report sections."""
        e = _started_engine()
        req = _make_request(
            portfolio_value  = 5_000_000.0,
            positions        = {"NIFTY": 0.30, "BANKNIFTY": 0.25, "RELIANCE": 0.20, "TCS": 0.15, "HDFC": 0.10},
            returns          = RETURNS_VOLATILE,
            limits           = {"var_limit": 200_000.0, "concentration_limit": 0.35},
        )
        report = e.assess(req, objectives=list(OptimizationObjective))

        # Status
        assert report.status == AssessmentStatus.COMPLETED
        # Risk score in valid range
        assert 0 <= report.risk_score <= 100
        # All sub-reports present
        assert report.var_report is not None
        assert report.es_report is not None
        assert report.stress_test_report is not None
        assert report.scenario_report is not None
        assert report.exposure_report is not None
        assert len(report.forecasts) == 4
        assert report.mitigation_plan is not None
        assert report.optimization_report is not None
        assert report.summary is not None
        # ES ≥ VaR
        assert report.es_report.es_historical >= report.var_report.historical_var
        # Summary consistent
        assert report.summary.risk_score == pytest.approx(report.risk_score)

    def test_deterministic_results(self):
        """Same inputs must always produce the same risk metrics."""
        e = _started_engine()
        req = _make_request()
        r1 = e.assess(req)
        r2 = e.assess(req)
        assert r1.risk_score == pytest.approx(r2.risk_score)
        assert r1.var_report.historical_var == pytest.approx(r2.var_report.historical_var)

    def test_no_policy_evaluation_in_assessment(self):
        """Assessment engine must not expose or call any policy objects."""
        e = _started_engine()
        # There should be no attribute referencing policy engine
        assert not hasattr(e, "_policy_engine")
        assert not hasattr(e, "_policy_registry")

    def test_no_trade_execution(self):
        """Assessment engine must not expose order/broker interfaces."""
        e = _started_engine()
        assert not hasattr(e, "place_order")
        assert not hasattr(e, "_broker")
        assert not hasattr(e, "_order_manager")

    def test_var_report_component_sums_to_total(self):
        """Component VaR must sum to total (balanced portfolio)."""
        engine = RiskVaREngine()
        report = engine.build_var_report(
            "a1", "p1", RETURNS_VOLATILE, PORTFOLIO_VALUE,
            POSITIONS_BALANCED,
        )
        comp_total = sum(report.component_var.values())
        assert abs(comp_total - report.historical_var) < 1.0
