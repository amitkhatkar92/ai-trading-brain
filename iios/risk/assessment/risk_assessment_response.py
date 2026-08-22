"""
risk_assessment_response.py — iios.risk.assessment
====================================================
Immutable output value objects for the Risk Assessment Framework.

Includes all report types produced by the assessment pipeline:
  VaRReport, ExpectedShortfallReport, StressTestReport,
  ScenarioAnalysisReport, ExposureReport, RiskForecast,
  MitigationPlan, RiskOptimizationReport, RiskAssessmentReport,
  RiskAssessmentSummary.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    AssessmentStatus,
    ForecastHorizon,
    LimitStatus,
    OptimizationObjective,
    ScenarioType,
    StressScenario,
    VERSION,
)


# ---------------------------------------------------------------------------
# VaRReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VaRReport:
    """Value at Risk calculation results."""
    report_id:           str
    assessment_id:       str
    portfolio_id:        str
    confidence_level:    float
    horizon_days:        int
    historical_var:      float   # Absolute currency amount
    historical_var_pct:  float   # As % of portfolio value
    parametric_var:      float
    parametric_var_pct:  float
    component_var:       Dict[str, float]   # position_id → component VaR
    portfolio_value:     float
    returns_used:        int
    model_version:       str = VERSION
    calculated_at:       float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        assessment_id:    str,
        portfolio_id:     str,
        confidence_level: float,
        horizon_days:     int,
        historical_var:   float,
        portfolio_value:  float,
        returns_used:     int,
        *,
        report_id:        Optional[str]         = None,
        parametric_var:   float                 = 0.0,
        component_var:    Optional[Dict[str, float]] = None,
    ) -> "VaRReport":
        pv = portfolio_value if portfolio_value != 0 else 1.0
        return cls(
            report_id          = report_id or str(uuid.uuid4()),
            assessment_id      = assessment_id,
            portfolio_id       = portfolio_id,
            confidence_level   = confidence_level,
            horizon_days       = horizon_days,
            historical_var     = historical_var,
            historical_var_pct = historical_var / pv,
            parametric_var     = parametric_var,
            parametric_var_pct = parametric_var / pv,
            component_var      = dict(component_var or {}),
            portfolio_value    = portfolio_value,
            returns_used       = returns_used,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "assessment_id":      self.assessment_id,
            "portfolio_id":       self.portfolio_id,
            "confidence_level":   self.confidence_level,
            "horizon_days":       self.horizon_days,
            "historical_var":     self.historical_var,
            "historical_var_pct": self.historical_var_pct,
            "parametric_var":     self.parametric_var,
            "parametric_var_pct": self.parametric_var_pct,
            "portfolio_value":    self.portfolio_value,
            "returns_used":       self.returns_used,
            "calculated_at":      self.calculated_at,
        }


# ---------------------------------------------------------------------------
# ExpectedShortfallReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExpectedShortfallReport:
    """Expected Shortfall (CVaR) calculation results."""
    report_id:        str
    assessment_id:    str
    portfolio_id:     str
    confidence_level: float
    es_historical:    float   # Absolute currency amount
    es_historical_pct: float
    es_parametric:    float
    es_parametric_pct: float
    portfolio_value:  float
    returns_used:     int
    var_reference:    float   # VaR at same confidence for reference
    model_version:    str = VERSION
    calculated_at:    float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        assessment_id:    str,
        portfolio_id:     str,
        confidence_level: float,
        es_historical:    float,
        portfolio_value:  float,
        returns_used:     int,
        *,
        report_id:      Optional[str] = None,
        es_parametric:  float = 0.0,
        var_reference:  float = 0.0,
    ) -> "ExpectedShortfallReport":
        pv = portfolio_value if portfolio_value != 0 else 1.0
        return cls(
            report_id         = report_id or str(uuid.uuid4()),
            assessment_id     = assessment_id,
            portfolio_id      = portfolio_id,
            confidence_level  = confidence_level,
            es_historical     = es_historical,
            es_historical_pct = es_historical / pv,
            es_parametric     = es_parametric,
            es_parametric_pct = es_parametric / pv,
            portfolio_value   = portfolio_value,
            returns_used      = returns_used,
            var_reference     = var_reference,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":         self.report_id,
            "assessment_id":     self.assessment_id,
            "confidence_level":  self.confidence_level,
            "es_historical":     self.es_historical,
            "es_historical_pct": self.es_historical_pct,
            "es_parametric":     self.es_parametric,
            "portfolio_value":   self.portfolio_value,
            "var_reference":     self.var_reference,
            "calculated_at":     self.calculated_at,
        }


# ---------------------------------------------------------------------------
# StressTestReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StressScenarioResult:
    """Single stress scenario outcome."""
    scenario:      StressScenario
    stressed_loss: float   # Absolute loss in currency
    stressed_loss_pct: float   # As % of portfolio
    stressed_value:   float
    shock_params:  Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario":        self.scenario.value,
            "stressed_loss":   self.stressed_loss,
            "stressed_loss_pct": self.stressed_loss_pct,
            "stressed_value":  self.stressed_value,
            "shock_params":    self.shock_params,
        }


@dataclass(frozen=True)
class StressTestReport:
    """Stress test results across all scenarios."""
    report_id:       str
    assessment_id:   str
    portfolio_id:    str
    portfolio_value: float
    scenarios:       Tuple[StressScenarioResult, ...]
    worst_scenario:  StressScenario
    worst_loss:      float
    worst_loss_pct:  float
    model_version:   str = VERSION
    calculated_at:   float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        assessment_id:   str,
        portfolio_id:    str,
        portfolio_value: float,
        scenarios:       List[StressScenarioResult],
        *,
        report_id: Optional[str] = None,
    ) -> "StressTestReport":
        worst = max(scenarios, key=lambda s: s.stressed_loss, default=None)
        return cls(
            report_id       = report_id or str(uuid.uuid4()),
            assessment_id   = assessment_id,
            portfolio_id    = portfolio_id,
            portfolio_value = portfolio_value,
            scenarios       = tuple(scenarios),
            worst_scenario  = worst.scenario if worst else StressScenario.CUSTOM,
            worst_loss      = worst.stressed_loss if worst else 0.0,
            worst_loss_pct  = worst.stressed_loss_pct if worst else 0.0,
        )

    def get_scenario(self, scenario: StressScenario) -> Optional[StressScenarioResult]:
        for s in self.scenarios:
            if s.scenario == scenario:
                return s
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":       self.report_id,
            "assessment_id":   self.assessment_id,
            "portfolio_value": self.portfolio_value,
            "scenarios":       [s.to_dict() for s in self.scenarios],
            "worst_scenario":  self.worst_scenario.value,
            "worst_loss":      self.worst_loss,
            "worst_loss_pct":  self.worst_loss_pct,
            "calculated_at":   self.calculated_at,
        }


# ---------------------------------------------------------------------------
# ScenarioAnalysisReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScenarioOutcome:
    """Single forward scenario outcome."""
    scenario_type:       ScenarioType
    probability:         float
    projected_value:     float
    projected_return:    float
    projected_return_pct: float
    risk_contribution:   float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_type":        self.scenario_type.value,
            "probability":          self.probability,
            "projected_value":      self.projected_value,
            "projected_return":     self.projected_return,
            "projected_return_pct": self.projected_return_pct,
            "risk_contribution":    self.risk_contribution,
        }


@dataclass(frozen=True)
class ScenarioAnalysisReport:
    """Forward scenario analysis across all scenario types."""
    report_id:            str
    assessment_id:        str
    portfolio_id:         str
    portfolio_value:      float
    expected_return:      float
    expected_return_pct:  float
    outcomes:             Tuple[ScenarioOutcome, ...]
    probability_weighted_loss: float
    model_version:        str = VERSION
    calculated_at:        float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        assessment_id:  str,
        portfolio_id:   str,
        portfolio_value: float,
        expected_return: float,
        outcomes:       List[ScenarioOutcome],
        *,
        report_id: Optional[str] = None,
    ) -> "ScenarioAnalysisReport":
        pv = portfolio_value if portfolio_value != 0 else 1.0
        pw_loss = sum(
            o.probability * max(0.0, -o.projected_return) for o in outcomes
        )
        return cls(
            report_id             = report_id or str(uuid.uuid4()),
            assessment_id         = assessment_id,
            portfolio_id          = portfolio_id,
            portfolio_value       = portfolio_value,
            expected_return       = expected_return,
            expected_return_pct   = expected_return / pv,
            outcomes              = tuple(outcomes),
            probability_weighted_loss = pw_loss,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "assessment_id":      self.assessment_id,
            "portfolio_value":    self.portfolio_value,
            "expected_return":    self.expected_return,
            "expected_return_pct": self.expected_return_pct,
            "outcomes":           [o.to_dict() for o in self.outcomes],
            "probability_weighted_loss": self.probability_weighted_loss,
            "calculated_at":      self.calculated_at,
        }


# ---------------------------------------------------------------------------
# ExposureReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExposureReport:
    """Gross and net exposure analysis."""
    report_id:        str
    assessment_id:    str
    portfolio_id:     str
    portfolio_value:  float
    gross_exposure:   float
    net_exposure:     float
    gross_exposure_pct: float
    net_exposure_pct:   float
    long_exposure:    float
    short_exposure:   float
    exposure_by_position: Dict[str, float]   # position_id → abs exposure
    model_version:    str = VERSION
    calculated_at:    float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        assessment_id: str,
        portfolio_id:  str,
        portfolio_value: float,
        positions:     Dict[str, float],
        *,
        report_id: Optional[str] = None,
    ) -> "ExposureReport":
        pv = portfolio_value if portfolio_value != 0 else 1.0
        long_exp  = sum(w * portfolio_value for w in positions.values() if w > 0)
        short_exp = sum(abs(w) * portfolio_value for w in positions.values() if w < 0)
        gross_exp = long_exp + short_exp
        net_exp   = long_exp - short_exp
        by_pos    = {pos: abs(w) * portfolio_value for pos, w in positions.items()}
        return cls(
            report_id           = report_id or str(uuid.uuid4()),
            assessment_id       = assessment_id,
            portfolio_id        = portfolio_id,
            portfolio_value     = portfolio_value,
            gross_exposure      = gross_exp,
            net_exposure        = net_exp,
            gross_exposure_pct  = gross_exp / pv,
            net_exposure_pct    = net_exp / pv,
            long_exposure       = long_exp,
            short_exposure      = short_exp,
            exposure_by_position = by_pos,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":          self.report_id,
            "assessment_id":      self.assessment_id,
            "portfolio_value":    self.portfolio_value,
            "gross_exposure":     self.gross_exposure,
            "net_exposure":       self.net_exposure,
            "gross_exposure_pct": self.gross_exposure_pct,
            "net_exposure_pct":   self.net_exposure_pct,
            "long_exposure":      self.long_exposure,
            "short_exposure":     self.short_exposure,
            "calculated_at":      self.calculated_at,
        }


# ---------------------------------------------------------------------------
# RiskForecast
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskForecast:
    """Forward risk forecast for a given horizon."""
    forecast_id:          str
    assessment_id:        str
    portfolio_id:         str
    horizon:              ForecastHorizon
    horizon_days:         int
    forecast_var:         float
    forecast_var_pct:     float
    forecast_volatility:  float   # Annualised vol
    forecast_return:      float
    forecast_return_pct:  float
    ewma_decay:           float
    model_version:        str = VERSION
    calculated_at:        float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        assessment_id:       str,
        portfolio_id:        str,
        horizon:             ForecastHorizon,
        horizon_days:        int,
        forecast_var:        float,
        forecast_volatility: float,
        forecast_return:     float,
        portfolio_value:     float,
        ewma_decay:          float,
        *,
        forecast_id: Optional[str] = None,
    ) -> "RiskForecast":
        pv = portfolio_value if portfolio_value != 0 else 1.0
        return cls(
            forecast_id          = forecast_id or str(uuid.uuid4()),
            assessment_id        = assessment_id,
            portfolio_id         = portfolio_id,
            horizon              = horizon,
            horizon_days         = horizon_days,
            forecast_var         = forecast_var,
            forecast_var_pct     = forecast_var / pv,
            forecast_volatility  = forecast_volatility,
            forecast_return      = forecast_return,
            forecast_return_pct  = forecast_return / pv,
            ewma_decay           = ewma_decay,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forecast_id":         self.forecast_id,
            "assessment_id":       self.assessment_id,
            "horizon":             self.horizon.value,
            "horizon_days":        self.horizon_days,
            "forecast_var":        self.forecast_var,
            "forecast_var_pct":    self.forecast_var_pct,
            "forecast_volatility": self.forecast_volatility,
            "forecast_return":     self.forecast_return,
            "calculated_at":       self.calculated_at,
        }


# ---------------------------------------------------------------------------
# MitigationAction / MitigationPlan
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MitigationAction:
    """Single recommended mitigation action."""
    action_id:    str
    trigger:      str    # Risk driver that triggered this recommendation
    description:  str
    priority:     str    # high / medium / low
    impact_score: float  # Estimated risk score reduction

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id":    self.action_id,
            "trigger":      self.trigger,
            "description":  self.description,
            "priority":     self.priority,
            "impact_score": self.impact_score,
        }


@dataclass(frozen=True)
class MitigationPlan:
    """Complete risk mitigation recommendation plan."""
    plan_id:      str
    assessment_id: str
    portfolio_id: str
    actions:      Tuple[MitigationAction, ...]
    total_actions: int
    high_priority: int
    risk_score_before: float
    estimated_risk_score_after: float
    model_version:  str = VERSION
    generated_at:   float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        assessment_id:     str,
        portfolio_id:      str,
        actions:           List[MitigationAction],
        risk_score_before: float,
        *,
        plan_id: Optional[str] = None,
    ) -> "MitigationPlan":
        high_count = sum(1 for a in actions if a.priority == "high")
        estimated_reduction = sum(a.impact_score for a in actions)
        return cls(
            plan_id                    = plan_id or str(uuid.uuid4()),
            assessment_id              = assessment_id,
            portfolio_id               = portfolio_id,
            actions                    = tuple(actions),
            total_actions              = len(actions),
            high_priority              = high_count,
            risk_score_before          = risk_score_before,
            estimated_risk_score_after = max(0.0, risk_score_before - estimated_reduction),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id":                      self.plan_id,
            "assessment_id":                self.assessment_id,
            "total_actions":                self.total_actions,
            "high_priority":                self.high_priority,
            "risk_score_before":            self.risk_score_before,
            "estimated_risk_score_after":   self.estimated_risk_score_after,
            "actions":                      [a.to_dict() for a in self.actions],
            "generated_at":                 self.generated_at,
        }


# ---------------------------------------------------------------------------
# RiskOptimizationReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OptimizationRecommendation:
    """Single optimization recommendation."""
    rec_id:      str
    objective:   OptimizationObjective
    description: str
    current:     float
    target:      float
    improvement: float   # Estimated improvement metric

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rec_id":      self.rec_id,
            "objective":   self.objective.value,
            "description": self.description,
            "current":     self.current,
            "target":      self.target,
            "improvement": self.improvement,
        }


@dataclass(frozen=True)
class RiskOptimizationReport:
    """Risk optimization analysis and recommendations."""
    report_id:        str
    assessment_id:    str
    portfolio_id:     str
    objectives:       Tuple[OptimizationObjective, ...]
    recommendations:  Tuple[OptimizationRecommendation, ...]
    risk_score_before: float
    risk_score_after:  float
    optimization_gain: float
    model_version:    str = VERSION
    calculated_at:    float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        assessment_id:     str,
        portfolio_id:      str,
        objectives:        List[OptimizationObjective],
        recommendations:   List[OptimizationRecommendation],
        risk_score_before: float,
        risk_score_after:  float,
        *,
        report_id: Optional[str] = None,
    ) -> "RiskOptimizationReport":
        return cls(
            report_id         = report_id or str(uuid.uuid4()),
            assessment_id     = assessment_id,
            portfolio_id      = portfolio_id,
            objectives        = tuple(objectives),
            recommendations   = tuple(recommendations),
            risk_score_before = risk_score_before,
            risk_score_after  = risk_score_after,
            optimization_gain = risk_score_before - risk_score_after,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":         self.report_id,
            "assessment_id":     self.assessment_id,
            "objectives":        [o.value for o in self.objectives],
            "recommendations":   [r.to_dict() for r in self.recommendations],
            "risk_score_before": self.risk_score_before,
            "risk_score_after":  self.risk_score_after,
            "optimization_gain": self.optimization_gain,
            "calculated_at":     self.calculated_at,
        }


# ---------------------------------------------------------------------------
# RiskAssessmentSummary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskAssessmentSummary:
    """High-level summary of completed risk assessment."""
    summary_id:        str
    assessment_id:     str
    portfolio_id:      str
    status:            AssessmentStatus
    risk_score:        float   # 0-100
    risk_band:         str     # low / medium / high / critical
    var_95:            float
    var_95_pct:        float
    es_95:             float
    worst_stress_loss: float
    hhi:               float   # Concentration
    top_risks:         Tuple[str, ...]
    mitigations_count: int
    model_version:     str = VERSION
    created_at:        float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id":        self.summary_id,
            "assessment_id":     self.assessment_id,
            "portfolio_id":      self.portfolio_id,
            "status":            self.status.value,
            "risk_score":        self.risk_score,
            "risk_band":         self.risk_band,
            "var_95":            self.var_95,
            "var_95_pct":        self.var_95_pct,
            "es_95":             self.es_95,
            "worst_stress_loss": self.worst_stress_loss,
            "hhi":               self.hhi,
            "top_risks":         list(self.top_risks),
            "mitigations_count": self.mitigations_count,
            "created_at":        self.created_at,
        }


# ---------------------------------------------------------------------------
# RiskAssessmentReport — master aggregated report
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskAssessmentReport:
    """
    Complete risk assessment output aggregating all sub-reports.

    This is the primary output of :class:`~.risk_assessment_engine.RiskAssessmentEngine`.
    """
    report_id:          str
    assessment_id:      str
    portfolio_id:       str
    risk_id:            str
    status:             AssessmentStatus
    risk_score:         float
    var_report:         Optional[VaRReport]
    es_report:          Optional[ExpectedShortfallReport]
    stress_test_report: Optional[StressTestReport]
    scenario_report:    Optional[ScenarioAnalysisReport]
    exposure_report:    Optional[ExposureReport]
    forecasts:          Tuple[RiskForecast, ...]
    mitigation_plan:    Optional[MitigationPlan]
    optimization_report: Optional[RiskOptimizationReport]
    summary:            Optional[RiskAssessmentSummary]
    duration_s:         float
    model_version:      str = VERSION
    published_at:       float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        assessment_id:   str,
        portfolio_id:    str,
        risk_id:         str,
        status:          AssessmentStatus,
        risk_score:      float,
        duration_s:      float,
        *,
        report_id:            Optional[str]                       = None,
        var_report:           Optional[VaRReport]                  = None,
        es_report:            Optional[ExpectedShortfallReport]    = None,
        stress_test_report:   Optional[StressTestReport]           = None,
        scenario_report:      Optional[ScenarioAnalysisReport]     = None,
        exposure_report:      Optional[ExposureReport]             = None,
        forecasts:            Optional[List[RiskForecast]]         = None,
        mitigation_plan:      Optional[MitigationPlan]             = None,
        optimization_report:  Optional[RiskOptimizationReport]     = None,
        summary:              Optional[RiskAssessmentSummary]      = None,
    ) -> "RiskAssessmentReport":
        return cls(
            report_id           = report_id or str(uuid.uuid4()),
            assessment_id       = assessment_id,
            portfolio_id        = portfolio_id,
            risk_id             = risk_id,
            status              = status,
            risk_score          = risk_score,
            var_report          = var_report,
            es_report           = es_report,
            stress_test_report  = stress_test_report,
            scenario_report     = scenario_report,
            exposure_report     = exposure_report,
            forecasts           = tuple(forecasts or []),
            mitigation_plan     = mitigation_plan,
            optimization_report = optimization_report,
            summary             = summary,
            duration_s          = duration_s,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":      self.report_id,
            "assessment_id":  self.assessment_id,
            "portfolio_id":   self.portfolio_id,
            "risk_id":        self.risk_id,
            "status":         self.status.value,
            "risk_score":     self.risk_score,
            "duration_s":     self.duration_s,
            "model_version":  self.model_version,
            "published_at":   self.published_at,
            "has_var":        self.var_report is not None,
            "has_es":         self.es_report is not None,
            "has_stress":     self.stress_test_report is not None,
            "has_scenarios":  self.scenario_report is not None,
            "has_exposure":   self.exposure_report is not None,
            "forecast_count": len(self.forecasts),
            "has_mitigation": self.mitigation_plan is not None,
            "has_optimization": self.optimization_report is not None,
        }
