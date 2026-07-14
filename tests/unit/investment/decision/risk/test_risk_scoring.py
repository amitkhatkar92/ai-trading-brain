"""tests/unit/investment/decision/risk/test_risk_scoring.py
Tests for compute_risk_score, DecisionRisk, RiskStatisticsTracker,
RiskHealthMonitor, RiskConfidenceEstimator.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.risk.decision_risk import DecisionRisk, build_decision_risk
from iios.investment.decision.risk.decision_risk_score import (
    DecisionRiskScore,
    compute_risk_score,
)
from iios.investment.decision.risk.risk_confidence import RiskConfidenceEstimator
from iios.investment.decision.risk.risk_constants import (
    RiskEngineStatus,
    RiskLevel,
    RiskQualityGrade,
)
from iios.investment.decision.risk.risk_health import RiskHealthMonitor
from iios.investment.decision.risk.risk_statistics import RiskStatisticsTracker


# ─── compute_risk_score ───────────────────────────────────────────────────────

class TestComputeRiskScore:
    def test_zero_inputs(self):
        r = compute_risk_score(0.0, 0.0, 0.0, 0.0, 0.0)
        assert r.overall_risk == pytest.approx(0.0)
        assert r.risk_level == RiskLevel.MINIMAL

    def test_max_inputs(self):
        r = compute_risk_score(100.0, 100.0, 100.0, 100.0, 100.0)
        assert r.overall_risk == pytest.approx(100.0)
        assert r.risk_level == RiskLevel.CRITICAL

    def test_midpoint_inputs(self):
        r = compute_risk_score(50.0, 50.0, 50.0, 50.0, 50.0)
        assert r.overall_risk == pytest.approx(50.0)

    def test_weighted_dimension(self):
        # Only market risk set to 100, rest 0
        r = compute_risk_score(100.0, 0.0, 0.0, 0.0, 0.0)
        assert r.base_risk == pytest.approx(30.0)  # 0.30 weight

    def test_scenario_adjustment(self):
        base   = compute_risk_score(50.0, 50.0, 50.0, 50.0, 50.0)
        with_s = compute_risk_score(50.0, 50.0, 50.0, 50.0, 50.0, scenario_blended_risk=80.0)
        assert with_s.overall_risk > base.overall_risk

    def test_grade_improves_with_lower_risk(self):
        low  = compute_risk_score(5.0,  5.0,  5.0,  5.0,  5.0)
        high = compute_risk_score(90.0, 90.0, 90.0, 90.0, 90.0)
        assert low.grade.value < high.grade.value or low.grade == RiskQualityGrade.A

    def test_scenario_weight_clamped(self):
        r = compute_risk_score(50.0, 50.0, 50.0, 50.0, 50.0,
                               scenario_blended_risk=80.0, scenario_weight=2.0)
        assert r.scenario_weight <= 0.40

    def test_returns_dataclass(self):
        r = compute_risk_score(30.0, 30.0, 30.0, 30.0, 30.0)
        assert isinstance(r, DecisionRiskScore)

    def test_to_dict(self):
        r = compute_risk_score(30.0, 30.0, 30.0, 30.0, 30.0)
        d = r.to_dict()
        assert "overall_risk" in d and "risk_level" in d and "grade" in d


# ─── build_decision_risk ──────────────────────────────────────────────────────

class TestBuildDecisionRisk:
    def test_basic_build(self):
        dr = build_decision_risk(
            decision_id="D1", subject_id="INFY", subject_type="equity",
            market_risk=40.0, company_risk=30.0, strategy_risk=35.0,
            execution_risk=25.0, confidence_risk=20.0,
            controls_breached=False, scenarios_evaluated=0, version=1,
        )
        assert isinstance(dr, DecisionRisk)
        assert 0.0 <= dr.overall_risk <= 100.0

    def test_overall_risk_matches_weighted_sum(self):
        dr = build_decision_risk(
            decision_id="D1", subject_id="INFY", subject_type="equity",
            market_risk=50.0, company_risk=50.0, strategy_risk=50.0,
            execution_risk=50.0, confidence_risk=50.0,
            controls_breached=False, scenarios_evaluated=0, version=1,
        )
        assert dr.overall_risk == pytest.approx(50.0)

    def test_is_elevated_when_high(self):
        dr = build_decision_risk(
            decision_id="D1", subject_id="INFY", subject_type="equity",
            market_risk=70.0, company_risk=70.0, strategy_risk=70.0,
            execution_risk=70.0, confidence_risk=70.0,
            controls_breached=False, scenarios_evaluated=0, version=1,
        )
        assert dr.is_elevated

    def test_not_elevated_when_low(self):
        dr = build_decision_risk(
            decision_id="D1", subject_id="INFY", subject_type="equity",
            market_risk=20.0, company_risk=20.0, strategy_risk=20.0,
            execution_risk=20.0, confidence_risk=20.0,
            controls_breached=False, scenarios_evaluated=0, version=1,
        )
        assert not dr.is_elevated

    def test_blocks_execution_on_critical(self):
        dr = build_decision_risk(
            decision_id="D1", subject_id="INFY", subject_type="equity",
            market_risk=90.0, company_risk=90.0, strategy_risk=90.0,
            execution_risk=90.0, confidence_risk=90.0,
            controls_breached=False, scenarios_evaluated=0, version=1,
        )
        assert dr.blocks_execution

    def test_controls_breached_forces_blocks_execution(self):
        dr = build_decision_risk(
            decision_id="D1", subject_id="INFY", subject_type="equity",
            market_risk=10.0, company_risk=10.0, strategy_risk=10.0,
            execution_risk=10.0, confidence_risk=10.0,
            controls_breached=True, scenarios_evaluated=0, version=1,
        )
        assert dr.blocks_execution

    def test_dimension_risk_accessor(self):
        from iios.investment.decision.risk.risk_constants import RiskDimension
        dr = build_decision_risk(
            decision_id="D1", subject_id="INFY", subject_type="equity",
            market_risk=40.0, company_risk=30.0, strategy_risk=35.0,
            execution_risk=25.0, confidence_risk=20.0,
            controls_breached=False, scenarios_evaluated=0, version=1,
        )
        assert dr.dimension_risk(RiskDimension.MARKET) == pytest.approx(40.0)

    def test_custom_weights(self):
        dr = build_decision_risk(
            decision_id="D1", subject_id="INFY", subject_type="equity",
            market_risk=100.0, company_risk=0.0, strategy_risk=0.0,
            execution_risk=0.0, confidence_risk=0.0,
            controls_breached=False, scenarios_evaluated=0, version=1,
            mw=1.0, cw=0.0, sw=0.0, ew=0.0, cnw=0.0,
        )
        assert dr.overall_risk == pytest.approx(100.0)

    def test_to_dict_keys(self):
        dr = build_decision_risk(
            decision_id="D1", subject_id="INFY", subject_type="equity",
            market_risk=40.0, company_risk=30.0, strategy_risk=35.0,
            execution_risk=25.0, confidence_risk=20.0,
            controls_breached=False, scenarios_evaluated=0, version=1,
        )
        d = dr.to_dict()
        assert all(k in d for k in ("decision_id", "overall_risk", "risk_level"))


# ─── RiskStatisticsTracker ───────────────────────────────────────────────────

class TestRiskStatisticsTracker:
    def test_initial_state(self):
        t = RiskStatisticsTracker()
        s = t.summary()
        assert s.total_evaluations == 0

    def test_record_success(self):
        t = RiskStatisticsTracker()
        t.record_success(overall_risk=40.0, duration_ms=50.0)
        s = t.summary()
        assert s.successful == 1
        assert s.avg_overall_risk == pytest.approx(40.0)

    def test_record_failure(self):
        t = RiskStatisticsTracker()
        t.record_failure()
        s = t.summary()
        assert s.failed == 1 and s.total_evaluations == 1

    def test_elevated_count(self):
        t = RiskStatisticsTracker()
        t.record_success(65.0, 10.0)
        t.record_success(30.0, 10.0)
        assert t.summary().elevated_count == 1

    def test_critical_count(self):
        t = RiskStatisticsTracker()
        t.record_success(85.0, 10.0)
        t.record_success(30.0, 10.0)
        assert t.summary().critical_count == 1

    def test_success_rate(self):
        t = RiskStatisticsTracker()
        t.record_success(30.0, 10.0)
        t.record_failure()
        assert t.summary().success_rate == pytest.approx(0.5)

    def test_reset(self):
        t = RiskStatisticsTracker()
        t.record_success(40.0, 10.0)
        t.reset()
        assert t.summary().total_evaluations == 0

    def test_to_dict_keys(self):
        t = RiskStatisticsTracker()
        d = t.summary().to_dict()
        assert "success_rate" in d and "elevated_rate" in d


# ─── RiskHealthMonitor ───────────────────────────────────────────────────────

class TestRiskHealthMonitor:
    def test_initial_status(self):
        m = RiskHealthMonitor()
        r = m.report()
        assert r.status == RiskEngineStatus.INITIALIZING

    def test_set_status(self):
        m = RiskHealthMonitor()
        m.set_status(RiskEngineStatus.READY)
        assert m.report().status == RiskEngineStatus.READY

    def test_record_success_resets_consecutive(self):
        m = RiskHealthMonitor()
        m.record_failure()
        m.record_failure()
        m.record_success(100.0)
        assert m.report().consecutive_failures == 0

    def test_five_consecutive_failures_degrades(self):
        m = RiskHealthMonitor()
        m.set_status(RiskEngineStatus.READY)
        for _ in range(5):
            m.record_failure()
        assert m.report().status == RiskEngineStatus.DEGRADED

    def test_healthy_after_start(self):
        m = RiskHealthMonitor()
        m.set_status(RiskEngineStatus.READY)
        assert m.report().is_healthy

    def test_avg_duration(self):
        m = RiskHealthMonitor()
        m.record_success(100.0)
        m.record_success(200.0)
        assert m.report().avg_duration_ms == pytest.approx(150.0, abs=1.0)

    def test_reset(self):
        m = RiskHealthMonitor()
        m.record_success(50.0)
        m.reset()
        assert m.report().total_evaluations == 0


# ─── RiskConfidenceEstimator ─────────────────────────────────────────────────

class TestRiskConfidenceEstimator:
    def setup_method(self):
        self.estimator = RiskConfidenceEstimator()

    def test_rich_inputs_high_confidence(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        r = self.estimator.estimate(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        assert r.risk_confidence > 30.0

    def test_result_in_range(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        r = self.estimator.estimate(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        )
        assert 0.0 <= r.risk_confidence <= 100.0

    def test_to_dict_keys(
        self, rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
    ):
        d = self.estimator.estimate(
            rich_evidence_snapshot, rich_reasoning_snapshot, rich_confidence_snapshot,
        ).to_dict()
        assert "risk_confidence" in d
