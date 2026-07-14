"""iios/investment/decision/risk/risk_pipeline.py
7-stage risk evaluation pipeline.
Pluggable via BaseRiskModule ABC.
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.capital_exposure import CapitalExposureAnalyzer
from iios.investment.decision.risk.company_risk import CompanyRiskEvaluator, CompanyRiskResult
from iios.investment.decision.risk.concentration_analysis import ConcentrationAnalyzer
from iios.investment.decision.risk.confidence_risk import ConfidenceRiskEvaluator, ConfidenceRiskResult
from iios.investment.decision.risk.control_engine import ControlEngine, ControlEvaluationResult
from iios.investment.decision.risk.control_registry import ControlRegistry
from iios.investment.decision.risk.decision_risk import DecisionRisk, build_decision_risk
from iios.investment.decision.risk.decision_risk_score import compute_risk_score
from iios.investment.decision.risk.execution_risk import ExecutionRiskEvaluator, ExecutionRiskResult
from iios.investment.decision.risk.exposure_engine import ExposureEngine, ExposureReport
from iios.investment.decision.risk.market_risk import MarketRiskEvaluator, MarketRiskResult
from iios.investment.decision.risk.position_exposure import PositionExposureAnalyzer
from iios.investment.decision.risk.risk_confidence import RiskConfidenceEstimator, RiskConfidenceResult
from iios.investment.decision.risk.risk_constants import (
    RiskDimension,
    RiskPolicyStatus,
)
from iios.investment.decision.risk.risk_policies import PolicyValidationResult, PolicyValidator
from iios.investment.decision.risk.risk_quality import RiskQualityEvaluator, RiskQualityReport
from iios.investment.decision.risk.scenario_registry import ScenarioRegistry
from iios.investment.decision.risk.scenario_risk import ScenarioRiskAnalyzer, ScenarioRiskResult
from iios.investment.decision.risk.strategy_risk import StrategyRiskEvaluator, StrategyRiskResult


# ── Pluggable extension point ─────────────────────────────────────────────────

class BaseRiskModule(abc.ABC):
    """ABC for custom risk modules injected into the pipeline."""

    @property
    @abc.abstractmethod
    def module_id(self) -> str: ...

    @abc.abstractmethod
    def evaluate(self, context: "RiskContext") -> Dict[str, Any]:
        """Evaluate risk and return a dict of metadata to attach to context."""
        ...


# ── Pipeline context (mutable, internal) ─────────────────────────────────────

@dataclass
class RiskContext:
    """Mutable pipeline context passed through all stages."""
    evidence_snapshot:   EvidenceSnapshot
    reasoning_snapshot:  ReasoningSnapshot
    confidence_snapshot: ConfidenceSnapshot
    decision_id:         str

    # Populated by stages
    market_result:     Optional[MarketRiskResult]     = None
    company_result:    Optional[CompanyRiskResult]    = None
    strategy_result:   Optional[StrategyRiskResult]   = None
    execution_result:  Optional[ExecutionRiskResult]  = None
    confidence_result: Optional[ConfidenceRiskResult] = None
    scenario_result:   Optional[ScenarioRiskResult]   = None
    exposure_report:   Optional[ExposureReport]       = None
    control_result:    Optional[ControlEvaluationResult] = None
    policy_result:     Optional[PolicyValidationResult]  = None
    decision_risk:     Optional[DecisionRisk]             = None
    risk_confidence:   Optional[RiskConfidenceResult]     = None
    quality_report:    Optional[RiskQualityReport]        = None
    custom_metadata:   Dict[str, Any] = field(default_factory=dict)


# ── Pipeline result ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PipelineResult:
    decision_risk:   DecisionRisk
    scenario_result: ScenarioRiskResult
    exposure_report: ExposureReport
    control_result:  ControlEvaluationResult
    policy_result:   PolicyValidationResult
    risk_confidence: RiskConfidenceResult
    quality_report:  RiskQualityReport
    duration_ms:     float
    custom_metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_risk":   self.decision_risk.to_dict(),
            "scenario_result": self.scenario_result.to_dict(),
            "exposure_report": self.exposure_report.to_dict(),
            "control_result":  self.control_result.to_dict(),
            "policy_result":   self.policy_result.to_dict(),
            "risk_confidence": self.risk_confidence.to_dict(),
            "quality_report":  self.quality_report.to_dict(),
            "duration_ms":     round(self.duration_ms, 2),
        }


# ── 7-Stage Pipeline ──────────────────────────────────────────────────────────

class RiskPipeline:
    """
    Orchestrates 7 sequential evaluation stages:
      1. Market risk
      2. Company risk
      3. Strategy risk
      4. Execution risk
      5. Confidence risk
      6. Scenario analysis
      7. Exposure + controls + policies

    Custom modules are run after stage 7 and their output is stored in
    context.custom_metadata.
    """

    def __init__(
        self,
        scenario_registry:  Optional[ScenarioRegistry]  = None,
        control_registry:   Optional[ControlRegistry]   = None,
        custom_modules:     Optional[List[BaseRiskModule]] = None,
        max_allowed_risk:   float = 70.0,
    ) -> None:
        self._market_eval    = MarketRiskEvaluator()
        self._company_eval   = CompanyRiskEvaluator()
        self._strategy_eval  = StrategyRiskEvaluator()
        self._execution_eval = ExecutionRiskEvaluator()
        self._confidence_eval = ConfidenceRiskEvaluator()
        self._scenario_analyzer = ScenarioRiskAnalyzer(scenario_registry)
        self._exposure_engine   = ExposureEngine()
        self._control_engine    = ControlEngine(control_registry)
        self._policy_validator  = PolicyValidator(max_allowed_risk)
        self._risk_conf_estimator = RiskConfidenceEstimator()
        self._quality_evaluator   = RiskQualityEvaluator()
        self._custom_modules: List[BaseRiskModule] = custom_modules or []

    def run(self, ctx: RiskContext) -> PipelineResult:
        t0 = time.perf_counter()

        # ── Stage 1: Market risk ──────────────────────────────────────────────
        ctx.market_result  = self._market_eval.evaluate(ctx.evidence_snapshot)

        # ── Stage 2: Company risk ─────────────────────────────────────────────
        ctx.company_result = self._company_eval.evaluate(ctx.evidence_snapshot)

        # ── Stage 3: Strategy risk ────────────────────────────────────────────
        ctx.strategy_result = self._strategy_eval.evaluate(ctx.evidence_snapshot)

        # ── Stage 4: Execution risk ───────────────────────────────────────────
        ctx.execution_result = self._execution_eval.evaluate(
            ctx.reasoning_snapshot, ctx.confidence_snapshot,
        )

        # ── Stage 5: Confidence risk ──────────────────────────────────────────
        ctx.confidence_result = self._confidence_eval.evaluate(ctx.confidence_snapshot)

        # ── Stage 6: Scenario analysis ────────────────────────────────────────
        ctx.scenario_result = self._scenario_analyzer.analyze(
            market_risk     = ctx.market_result.market_risk,
            company_risk    = ctx.company_result.company_risk,
            strategy_risk   = ctx.strategy_result.strategy_risk,
            execution_risk  = ctx.execution_result.execution_risk,
            confidence_risk = ctx.confidence_result.confidence_risk,
        )

        # ── Stage 7a: Exposure ────────────────────────────────────────────────
        ctx.exposure_report = self._exposure_engine.analyze(ctx.evidence_snapshot)

        # ── Stage 7b: Compute composite risk → DecisionRisk ──────────────────
        risk_score = compute_risk_score(
            market_risk     = ctx.market_result.market_risk,
            company_risk    = ctx.company_result.company_risk,
            strategy_risk   = ctx.strategy_result.strategy_risk,
            execution_risk  = ctx.execution_result.execution_risk,
            confidence_risk = ctx.confidence_result.confidence_risk,
            scenario_blended_risk = ctx.scenario_result.blended_risk,
        )

        # ── Stage 7c: Controls ────────────────────────────────────────────────
        # Build a provisional DecisionRisk for control evaluation
        provisional_dr = build_decision_risk(
            decision_id  = ctx.decision_id,
            subject_id   = ctx.evidence_snapshot.subject_id,
            subject_type = ctx.evidence_snapshot.subject_type,
            market_risk  = ctx.market_result.market_risk,
            company_risk = ctx.company_result.company_risk,
            strategy_risk = ctx.strategy_result.strategy_risk,
            execution_risk = ctx.execution_result.execution_risk,
            confidence_risk = ctx.confidence_result.confidence_risk,
            controls_breached = False,
            scenarios_evaluated = ctx.scenario_result.scenario_count,
            version = 1,
        )
        ctx.control_result = self._control_engine.evaluate(provisional_dr)

        # ── Stage 7d: Policies ────────────────────────────────────────────────
        # Rebuild with controls_breached flag
        ctx.decision_risk = build_decision_risk(
            decision_id  = ctx.decision_id,
            subject_id   = ctx.evidence_snapshot.subject_id,
            subject_type = ctx.evidence_snapshot.subject_type,
            market_risk  = ctx.market_result.market_risk,
            company_risk = ctx.company_result.company_risk,
            strategy_risk = ctx.strategy_result.strategy_risk,
            execution_risk = ctx.execution_result.execution_risk,
            confidence_risk = ctx.confidence_result.confidence_risk,
            scenarios_evaluated = ctx.scenario_result.scenario_count,
            controls_breached = ctx.control_result.hard_breach,
            version = 1,
        )
        ctx.policy_result = self._policy_validator.validate(ctx.decision_risk)

        # ── Risk confidence + quality ─────────────────────────────────────────
        ctx.risk_confidence = self._risk_conf_estimator.estimate(
            ctx.evidence_snapshot, ctx.reasoning_snapshot, ctx.confidence_snapshot,
        )
        ctx.quality_report = self._quality_evaluator.evaluate(
            ctx.risk_confidence, ctx.scenario_result,
        )

        # ── Custom modules ────────────────────────────────────────────────────
        for module in self._custom_modules:
            try:
                ctx.custom_metadata[module.module_id] = module.evaluate(ctx)
            except Exception:
                pass   # custom modules must not crash the pipeline

        duration_ms = (time.perf_counter() - t0) * 1000.0

        return PipelineResult(
            decision_risk   = ctx.decision_risk,
            scenario_result = ctx.scenario_result,
            exposure_report = ctx.exposure_report,
            control_result  = ctx.control_result,
            policy_result   = ctx.policy_result,
            risk_confidence = ctx.risk_confidence,
            quality_report  = ctx.quality_report,
            duration_ms     = round(duration_ms, 2),
            custom_metadata = dict(ctx.custom_metadata),
        )
