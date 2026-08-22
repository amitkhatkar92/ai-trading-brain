"""
risk_assessment_manager.py — iios.risk.assessment
===================================================
Internal assessment pipeline coordinator.

Orchestrates: validate → load_models → calculate → build_reports →
validate_results → publish.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_ASSESSMENT_ENGINE,
    ACTOR_CALCULATOR,
    AssessmentStatus,
    ForecastHorizon,
    OptimizationObjective,
    RISK_SCORE_HIGH,
    RISK_SCORE_LOW,
    RISK_SCORE_MEDIUM,
    VERSION,
)
from .exceptions import RiskAssessmentValidationError
from .risk_assessment_events import (
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
)
from .risk_assessment_factory import RiskAssessmentFactory
from .risk_assessment_history import RiskAssessmentHistory
from .risk_assessment_registry import RiskAssessmentRegistry
from .risk_assessment_request import RiskAssessmentRequest
from .risk_assessment_response import (
    RiskAssessmentReport,
    RiskAssessmentSummary,
)
from .risk_assessment_statistics import RiskAssessmentStatistics
from .risk_assessment_validator import RiskAssessmentValidator
from .risk_calculation_engine import RiskCalculationEngine
from .risk_model_registry import RiskModelRegistry

_log = get_logger(__name__)


class RiskAssessmentManager:
    """
    Internal pipeline coordinator for risk assessments.

    **Not part of the public API** — callers use
    :class:`~.risk_assessment_engine.RiskAssessmentEngine`.

    Pipeline stages
    ---------------
    1. Validate request
    2. Load models
    3. Execute calculations
    4. Build consolidated report
    5. Validate report
    6. Register and publish
    """

    VERSION: str = VERSION

    def __init__(
        self,
        registry:     Optional[RiskAssessmentRegistry]   = None,
        calculator:   Optional[RiskCalculationEngine]    = None,
        validator:    Optional[RiskAssessmentValidator]  = None,
        statistics:   Optional[RiskAssessmentStatistics] = None,
        history:      Optional[RiskAssessmentHistory]    = None,
        model_registry: Optional[RiskModelRegistry]     = None,
        factory:      Optional[RiskAssessmentFactory]    = None,
    ) -> None:
        self._registry     = registry      or RiskAssessmentRegistry()
        self._calculator   = calculator    or RiskCalculationEngine()
        self._validator    = validator     or RiskAssessmentValidator()
        self._stats        = statistics    or RiskAssessmentStatistics()
        self._history      = history       or RiskAssessmentHistory()
        self._model_reg    = model_registry or RiskModelRegistry()
        self._factory      = factory       or RiskAssessmentFactory()

    # ------------------------------------------------------------------
    # Primary pipeline entry
    # ------------------------------------------------------------------

    def run_assessment(
        self,
        request:    RiskAssessmentRequest,
        objectives: Optional[List[OptimizationObjective]] = None,
    ) -> RiskAssessmentReport:
        """
        Execute the full assessment pipeline for *request*.

        Parameters
        ----------
        request :
            Validated, policy-approved assessment request.
        objectives :
            Optional list of optimization objectives to pursue.

        Returns
        -------
        RiskAssessmentReport
            Complete assessment output.
        """
        t0 = time.monotonic()
        self._stats.record_assessment_started()
        self._history.record_request(request)

        ev_started = make_assessment_started(
            request.assessment_id, request.portfolio_id,
            actor=ACTOR_ASSESSMENT_ENGINE,
        )
        self._history.record_event(ev_started)

        try:
            # Stage 1 — Validate request
            self._validator.validate_request_or_raise(request)

            # Stage 2 — Load models
            model_count = self._model_reg.count()
            ev_models   = make_models_loaded(
                request.assessment_id, request.portfolio_id,
                models_count=model_count, actor=ACTOR_CALCULATOR,
            )
            self._history.record_event(ev_models)
            self._stats.record_model_runtime(0.0)   # count without timing overhead

            # Stage 3 — Execute calculations
            bundle = self._calculator.run(
                assessment_id    = request.assessment_id,
                portfolio_id     = request.portfolio_id,
                portfolio_value  = request.portfolio_value,
                positions        = request.positions,
                returns          = request.returns,
                limits           = request.limits,
                confidence_level = request.confidence_level,
                horizon_days     = request.var_horizon_days,
                objectives       = objectives,
            )

            risk_score = (
                bundle.score_components.total_score
                if bundle.score_components else 0.0
            )

            ev_calc = make_risk_calculated(
                request.assessment_id, request.portfolio_id,
                risk_score=risk_score, actor=ACTOR_CALCULATOR,
            )
            self._history.record_event(ev_calc)

            if bundle.stress_report:
                self._stats.record_stress_test()
                ev_stress = make_stress_test_completed(
                    request.assessment_id, request.portfolio_id,
                    worst_loss_pct=bundle.stress_report.worst_loss_pct,
                    actor=ACTOR_CALCULATOR,
                )
                self._history.record_event(ev_stress)

            if bundle.scenario_report:
                self._stats.record_scenario_analysis()
                ev_scen = make_scenario_analysis_completed(
                    request.assessment_id, request.portfolio_id,
                    expected_return_pct=bundle.scenario_report.expected_return_pct,
                    actor=ACTOR_CALCULATOR,
                )
                self._history.record_event(ev_scen)

            if bundle.optimization_report:
                self._stats.record_optimization_run(success=True)
                ev_opt = make_optimization_completed(
                    request.assessment_id, request.portfolio_id,
                    optimization_gain=bundle.optimization_report.optimization_gain,
                    actor=ACTOR_CALCULATOR,
                )
                self._history.record_event(ev_opt)

            if bundle.mitigation_plan:
                ev_mit = make_mitigation_generated(
                    request.assessment_id, request.portfolio_id,
                    actions_count=bundle.mitigation_plan.total_actions,
                    actor=ACTOR_CALCULATOR,
                )
                self._history.record_event(ev_mit)

            for _ in bundle.forecasts:
                self._stats.record_forecast()

            # Stage 4 — Build summary
            summary = self._build_summary(request, bundle, risk_score)

            # Stage 5 — Build report
            duration = time.monotonic() - t0
            report   = RiskAssessmentReport.create(
                assessment_id       = request.assessment_id,
                portfolio_id        = request.portfolio_id,
                risk_id             = request.risk_id,
                status              = AssessmentStatus.COMPLETED,
                risk_score          = risk_score,
                duration_s          = duration,
                var_report          = bundle.var_report,
                es_report           = bundle.es_report,
                stress_test_report  = bundle.stress_report,
                scenario_report     = bundle.scenario_report,
                exposure_report     = bundle.exposure_report,
                forecasts           = list(bundle.forecasts),
                mitigation_plan     = bundle.mitigation_plan,
                optimization_report = bundle.optimization_report,
                summary             = summary,
            )

            # Stage 6 — Validate report
            self._validator.validate_report(report)

            ev_val = make_assessment_validated(
                request.assessment_id, request.portfolio_id,
                checks_passed=5, actor=ACTOR_ASSESSMENT_ENGINE,
            )
            self._history.record_event(ev_val)

            # Stage 7 — Register and publish
            self._registry.register(report)
            self._stats.record_assessment_completed()
            self._stats.record_assessment_time(duration)
            self._history.record_report(report)

            ev_pub = make_assessment_published(
                request.assessment_id, request.portfolio_id,
                risk_score=risk_score, actor=ACTOR_ASSESSMENT_ENGINE,
            )
            self._history.record_event(ev_pub)

            _log.info(
                f"Assessment completed assessment_id={request.assessment_id} "
                f"risk_score={risk_score:.1f} duration={duration:.3f}s"
            )
            return report

        except Exception as exc:
            duration = time.monotonic() - t0
            self._stats.record_assessment_failed()
            ev_fail = make_assessment_failed(
                request.assessment_id, request.portfolio_id,
                reason=str(exc), actor=ACTOR_ASSESSMENT_ENGINE,
            )
            self._history.record_event(ev_fail)
            self._history.record_error(str(exc))
            _log.info(
                f"Assessment failed assessment_id={request.assessment_id} "
                f"error={exc}"
            )
            raise

    # ------------------------------------------------------------------
    # Summary builder
    # ------------------------------------------------------------------

    def _build_summary(
        self,
        request:    RiskAssessmentRequest,
        bundle:     Any,
        risk_score: float,
    ) -> RiskAssessmentSummary:
        var_95      = bundle.var_report.historical_var if bundle.var_report else 0.0
        var_95_pct  = bundle.var_report.historical_var_pct if bundle.var_report else 0.0
        es_95       = bundle.es_report.es_historical if bundle.es_report else 0.0
        worst_stress = bundle.stress_report.worst_loss if bundle.stress_report else 0.0
        hhi         = bundle.concentration.hhi if bundle.concentration else 0.0
        mit_count   = bundle.mitigation_plan.total_actions if bundle.mitigation_plan else 0

        # Determine top risks
        top_risks = []
        if bundle.concentration and bundle.concentration.is_concentrated:
            top_risks.append("concentration")
        if var_95_pct > 0.05:
            top_risks.append("var_elevated")
        if bundle.stress_report and bundle.stress_report.worst_loss_pct > 0.20:
            top_risks.append("stress_loss_high")

        band = (
            "critical" if risk_score >= 80
            else "high"    if risk_score >= 60
            else "medium"  if risk_score >= 30
            else "low"
        )

        return RiskAssessmentSummary(
            summary_id         = str(uuid.uuid4()),
            assessment_id      = request.assessment_id,
            portfolio_id       = request.portfolio_id,
            status             = AssessmentStatus.COMPLETED,
            risk_score         = risk_score,
            risk_band          = band,
            var_95             = var_95,
            var_95_pct         = var_95_pct,
            es_95              = es_95,
            worst_stress_loss  = worst_stress,
            hhi                = hhi,
            top_risks          = tuple(top_risks),
            mitigations_count  = mit_count,
        )
