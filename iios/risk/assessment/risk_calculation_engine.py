"""
risk_calculation_engine.py — iios.risk.assessment
===================================================
Central calculation dispatch engine — orchestrates all quantitative
sub-engines and returns a consolidated set of metrics.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_EWMA_DECAY,
    DEFAULT_VAR_HORIZON_DAYS,
    ForecastHorizon,
    OptimizationObjective,
    StressScenario,
    VERSION,
)
from .exceptions import RiskCalculationError
from .risk_assessment_response import (
    ExpectedShortfallReport,
    MitigationPlan,
    RiskForecast,
    RiskOptimizationReport,
    ScenarioAnalysisReport,
    StressTestReport,
    VaRReport,
)
from .risk_concentration_engine import ConcentrationResult, RiskConcentrationEngine
from .risk_expected_shortfall_engine import RiskExpectedShortfallEngine
from .risk_exposure_engine import ExposureReport, RiskExposureEngine
from .risk_forecasting_engine import RiskForecastingEngine
from .risk_limit_engine import LimitUtilisationResult, RiskLimitEngine
from .risk_measurement_engine import RiskMeasurementEngine
from .risk_mitigation_engine import RiskMitigationEngine
from .risk_optimization_engine import RiskOptimizationEngine
from .risk_scenario_engine import RiskScenarioEngine
from .risk_score_engine import RiskScoreComponents, RiskScoreEngine
from .risk_sensitivity_engine import RiskSensitivityEngine
from .risk_stress_testing_engine import RiskStressTestingEngine
from .risk_var_engine import RiskVaREngine


class CalculationBundle:
    """
    All quantitative results produced by a single calculation run.

    Attributes are set to ``None`` when the corresponding engine was
    not requested or data was insufficient.
    """
    __slots__ = (
        "var_report", "es_report", "stress_report", "scenario_report",
        "exposure_report", "forecasts", "mitigation_plan",
        "optimization_report", "concentration", "score_components",
        "limit_results", "duration_s",
    )

    def __init__(self) -> None:
        self.var_report:          Optional[VaRReport]               = None
        self.es_report:           Optional[ExpectedShortfallReport]  = None
        self.stress_report:       Optional[StressTestReport]         = None
        self.scenario_report:     Optional[ScenarioAnalysisReport]   = None
        self.exposure_report:     Optional[ExposureReport]           = None
        self.forecasts:           List[RiskForecast]                 = []
        self.mitigation_plan:     Optional[MitigationPlan]           = None
        self.optimization_report: Optional[RiskOptimizationReport]   = None
        self.concentration:       Optional[ConcentrationResult]      = None
        self.score_components:    Optional[RiskScoreComponents]      = None
        self.limit_results:       Dict[str, LimitUtilisationResult]  = {}
        self.duration_s:          float                              = 0.0


class RiskCalculationEngine:
    """
    Central calculation dispatch engine.

    Instantiates and coordinates all quantitative sub-engines.
    Used internally by :class:`~.risk_assessment_manager.RiskAssessmentManager`.

    Parameters
    ----------
    Injects all sub-engines; if omitted, defaults are constructed.
    """

    VERSION: str = VERSION

    def __init__(
        self,
        var_engine:           Optional[RiskVaREngine]              = None,
        es_engine:            Optional[RiskExpectedShortfallEngine] = None,
        measurement_engine:   Optional[RiskMeasurementEngine]      = None,
        stress_engine:        Optional[RiskStressTestingEngine]     = None,
        scenario_engine:      Optional[RiskScenarioEngine]         = None,
        sensitivity_engine:   Optional[RiskSensitivityEngine]      = None,
        exposure_engine:      Optional[RiskExposureEngine]         = None,
        concentration_engine: Optional[RiskConcentrationEngine]    = None,
        limit_engine:         Optional[RiskLimitEngine]            = None,
        forecasting_engine:   Optional[RiskForecastingEngine]      = None,
        score_engine:         Optional[RiskScoreEngine]            = None,
        mitigation_engine:    Optional[RiskMitigationEngine]       = None,
        optimization_engine:  Optional[RiskOptimizationEngine]     = None,
    ) -> None:
        self._var          = var_engine          or RiskVaREngine()
        self._es           = es_engine           or RiskExpectedShortfallEngine()
        self._measure      = measurement_engine  or RiskMeasurementEngine()
        self._stress       = stress_engine       or RiskStressTestingEngine()
        self._scenario     = scenario_engine     or RiskScenarioEngine()
        self._sensitivity  = sensitivity_engine  or RiskSensitivityEngine()
        self._exposure     = exposure_engine     or RiskExposureEngine()
        self._concentration = concentration_engine or RiskConcentrationEngine()
        self._limit        = limit_engine        or RiskLimitEngine()
        self._forecast     = forecasting_engine  or RiskForecastingEngine()
        self._score        = score_engine        or RiskScoreEngine()
        self._mitigation   = mitigation_engine   or RiskMitigationEngine()
        self._optimisation = optimization_engine or RiskOptimizationEngine()

    # ------------------------------------------------------------------
    # Full calculation run
    # ------------------------------------------------------------------

    def run(
        self,
        assessment_id:    str,
        portfolio_id:     str,
        portfolio_value:  float,
        positions:        Dict[str, float],
        returns:          List[float],
        limits:           Dict[str, float],
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        horizon_days:     int   = DEFAULT_VAR_HORIZON_DAYS,
        decay:            float = DEFAULT_EWMA_DECAY,
        objectives:       Optional[List[OptimizationObjective]] = None,
    ) -> CalculationBundle:
        """
        Execute all risk calculations and return a
        :class:`CalculationBundle`.

        Parameters are passed directly from the assessment request.
        All engines are called in the order that satisfies their
        data dependencies.
        """
        t0      = time.monotonic()
        bundle  = CalculationBundle()

        # 1. VaR
        try:
            bundle.var_report = self._var.build_var_report(
                assessment_id    = assessment_id,
                portfolio_id     = portfolio_id,
                returns          = returns,
                portfolio_value  = portfolio_value,
                positions        = positions,
                confidence_level = confidence_level,
                horizon_days     = horizon_days,
            )
        except Exception as exc:
            raise RiskCalculationError(str(exc), engine="VaREngine") from exc

        # 2. ES
        try:
            bundle.es_report = self._es.build_es_report(
                assessment_id    = assessment_id,
                portfolio_id     = portfolio_id,
                returns          = returns,
                portfolio_value  = portfolio_value,
                confidence_level = confidence_level,
            )
        except Exception as exc:
            raise RiskCalculationError(str(exc), engine="ESEngine") from exc

        # 3. Concentration
        bundle.concentration = self._concentration.analyse(positions)

        # 4. Exposure
        try:
            bundle.exposure_report = self._exposure.build_exposure_report(
                assessment_id   = assessment_id,
                portfolio_id    = portfolio_id,
                portfolio_value = portfolio_value,
                positions       = positions,
            )
        except Exception as exc:
            raise RiskCalculationError(str(exc), engine="ExposureEngine") from exc

        # 5. Stress testing
        try:
            bundle.stress_report = self._stress.build_stress_test_report(
                assessment_id   = assessment_id,
                portfolio_id    = portfolio_id,
                portfolio_value = portfolio_value,
            )
        except Exception as exc:
            raise RiskCalculationError(str(exc), engine="StressEngine") from exc

        # 6. Scenario analysis
        try:
            bundle.scenario_report = self._scenario.build_scenario_report(
                assessment_id   = assessment_id,
                portfolio_id    = portfolio_id,
                portfolio_value = portfolio_value,
                returns         = returns,
                horizon_days    = horizon_days,
            )
        except Exception as exc:
            raise RiskCalculationError(str(exc), engine="ScenarioEngine") from exc

        # 7. Limit checks
        if limits:
            var_val = bundle.var_report.historical_var if bundle.var_report else 0.0
            current_metrics = {
                "var_limit":           var_val,
                "concentration_limit": bundle.concentration.top_position_weight if bundle.concentration else 0.0,
            }
            bundle.limit_results = self._limit.check_all_limits(current_metrics, limits)

        # 8. Forecasts
        try:
            bundle.forecasts = self._forecast.build_all_forecasts(
                assessment_id    = assessment_id,
                portfolio_id     = portfolio_id,
                returns          = returns,
                portfolio_value  = portfolio_value,
                confidence_level = confidence_level,
                decay            = decay,
            )
        except Exception as exc:
            raise RiskCalculationError(str(exc), engine="ForecastEngine") from exc

        # 9. Risk score
        var_pct            = bundle.var_report.historical_var_pct if bundle.var_report else 0.0
        hhi                = bundle.concentration.hhi if bundle.concentration else 0.0
        worst_stress_pct   = bundle.stress_report.worst_loss_pct if bundle.stress_report else 0.0
        max_util           = max(
            (r.utilisation for r in bundle.limit_results.values()), default=0.0
        )
        bundle.score_components = self._score.calculate(
            var_pct                = var_pct,
            hhi                    = hhi,
            worst_stress_loss_pct  = worst_stress_pct,
            max_limit_utilisation  = max_util,
        )
        risk_score = bundle.score_components.total_score

        # 10. Mitigation
        max_dd  = self._es.calculate_max_drawdown(returns)
        es_pct  = bundle.es_report.es_historical_pct if bundle.es_report else 0.0
        ann_vol = self._measure.calculate_annualised_volatility(returns)
        max_pos_w = bundle.concentration.top_position_weight if bundle.concentration else 0.0

        bundle.mitigation_plan = self._mitigation.generate_plan(
            assessment_id       = assessment_id,
            portfolio_id        = portfolio_id,
            risk_score          = risk_score,
            var_pct             = var_pct,
            es_pct              = es_pct,
            max_drawdown        = max_dd,
            hhi                 = hhi,
            top_position_weight = max_pos_w,
            annual_volatility   = ann_vol,
            worst_stress_pct    = worst_stress_pct,
            max_limit_util      = max_util,
        )

        # 11. Optimisation
        if objectives:
            try:
                max_w = bundle.concentration.top_position_weight if bundle.concentration else 0.0
                n_pos = len(positions)
                sharpe = self._measure.calculate_sharpe_ratio(returns)
                gross_exp_pct = (bundle.exposure_report.gross_exposure_pct
                                 if bundle.exposure_report else 1.0)
                bundle.optimization_report = self._optimisation.optimise(
                    assessment_id       = assessment_id,
                    portfolio_id        = portfolio_id,
                    risk_score          = risk_score,
                    objectives          = objectives,
                    hhi                 = hhi,
                    max_weight          = max_w,
                    n_positions         = n_pos,
                    var_pct             = var_pct,
                    es_pct              = es_pct,
                    sharpe              = sharpe,
                    annual_vol          = ann_vol,
                    gross_exposure_pct  = gross_exp_pct,
                )
            except Exception as exc:
                raise RiskCalculationError(str(exc), engine="OptimisationEngine") from exc

        bundle.duration_s = time.monotonic() - t0
        return bundle
