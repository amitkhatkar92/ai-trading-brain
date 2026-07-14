"""iios/investment/decision/explainability/summary_builder.py
SummaryBuilder — constructs structured summaries from upstream engine snapshots.
"""
from __future__ import annotations

from typing import List, Tuple

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot
from iios.investment.decision.explainability.decision_explanation import (
    DecisionExplanation,
    ExplanationFactor,
)
from iios.investment.decision.explainability.explainability_constants import (
    CAUTION_CONFIDENCE_MIN,
    INSUFFICIENT_DATA_ITEMS,
    PROCEED_CONFIDENCE_MIN,
    PROCEED_RISK_MAX,
    DecisionOutcome,
    FactorSource,
)


def derive_outcome(
    evidence_snapshot:   EvidenceSnapshot,
    confidence_snapshot: ConfidenceSnapshot,
    risk_snapshot:       RiskSnapshot,
) -> DecisionOutcome:
    """Deterministically derive a DecisionOutcome from upstream engine outputs."""
    if risk_snapshot.blocks_execution:
        return DecisionOutcome.HALT

    if evidence_snapshot.item_count <= INSUFFICIENT_DATA_ITEMS:
        return DecisionOutcome.INSUFFICIENT_DATA

    conf = confidence_snapshot.overall_confidence
    risk = risk_snapshot.overall_risk

    if conf < CAUTION_CONFIDENCE_MIN:
        return DecisionOutcome.INSUFFICIENT_DATA

    if conf >= PROCEED_CONFIDENCE_MIN and risk < PROCEED_RISK_MAX:
        return DecisionOutcome.PROCEED

    return DecisionOutcome.CAUTION


class SummaryBuilder:
    """
    Constructs a DecisionExplanation from the 4 upstream engine snapshots.
    Consumes ONLY upstream outputs — never analyses markets/companies directly.
    """

    def build(
        self,
        evidence_snapshot:   EvidenceSnapshot,
        reasoning_snapshot:  ReasoningSnapshot,
        confidence_snapshot: ConfidenceSnapshot,
        risk_snapshot:       RiskSnapshot,
    ) -> DecisionExplanation:
        outcome     = derive_outcome(evidence_snapshot, confidence_snapshot, risk_snapshot)
        conf        = confidence_snapshot.overall_confidence
        risk        = risk_snapshot.overall_risk
        ev_quality  = evidence_snapshot.quality_score
        rq          = reasoning_snapshot.quality_score.overall
        consistency = reasoning_snapshot.logic_result.consistency_score

        supporting = self._build_supporting_factors(
            evidence_snapshot, confidence_snapshot, risk_snapshot,
        )
        opposing   = self._build_opposing_factors(
            evidence_snapshot, confidence_snapshot, risk_snapshot,
        )
        assumptions = self._build_assumptions(evidence_snapshot, confidence_snapshot)
        key_risks   = self._build_key_risks(risk_snapshot)

        one_line  = self._one_line(
            evidence_snapshot.subject_id, evidence_snapshot.subject_type,
            outcome, conf, risk,
        )
        exec_sum  = self._executive_summary(
            evidence_snapshot, confidence_snapshot, risk_snapshot, outcome,
        )
        tech_sum  = self._technical_summary(
            evidence_snapshot, reasoning_snapshot, confidence_snapshot, risk_snapshot,
        )

        return DecisionExplanation(
            decision_id           = risk_snapshot.decision_id,
            subject_id            = evidence_snapshot.subject_id,
            subject_type          = evidence_snapshot.subject_type,
            outcome               = outcome,
            one_line_summary      = one_line,
            executive_summary     = exec_sum,
            technical_summary     = tech_sum,
            supporting_factors    = tuple(supporting),
            opposing_factors      = tuple(opposing),
            assumptions           = tuple(assumptions),
            key_risks             = tuple(key_risks),
            overall_confidence    = conf,
            overall_risk          = risk,
            evidence_quality      = ev_quality,
            reasoning_quality     = rq,
            evidence_item_count   = evidence_snapshot.item_count,
            source_count          = len(evidence_snapshot.sources_included),
            evidence_coverage     = evidence_snapshot.coverage_fraction,
            evidence_freshness    = evidence_snapshot.overall_freshness,
            reasoning_step_count  = reasoning_snapshot.reasoning_chain.step_count,
            logic_consistency     = consistency,
        )

    # ── Factor builders ───────────────────────────────────────────────────────

    def _build_supporting_factors(
        self,
        ev: EvidenceSnapshot,
        cs: ConfidenceSnapshot,
        rs: RiskSnapshot,
    ) -> List[ExplanationFactor]:
        factors: List[ExplanationFactor] = []

        # Evidence quality
        if ev.quality_score >= 70.0:
            factors.append(ExplanationFactor(
                name="Strong evidence quality",
                description=f"Evidence quality score of {ev.quality_score:.0f}/100 supports a reliable assessment.",
                impact=min(100.0, ev.quality_score),
                source_engine=FactorSource.EVIDENCE,
                is_positive=True,
            ))

        # Evidence coverage
        if ev.coverage_fraction >= 0.60:
            factors.append(ExplanationFactor(
                name="Adequate evidence coverage",
                description=f"{ev.coverage_fraction*100:.0f}% of expected evidence categories are covered.",
                impact=min(100.0, ev.coverage_fraction * 100.0),
                source_engine=FactorSource.EVIDENCE,
                is_positive=True,
            ))

        # High confidence
        if cs.overall_confidence >= 60.0:
            factors.append(ExplanationFactor(
                name="High assessment confidence",
                description=f"Overall confidence of {cs.overall_confidence:.0f}/100 ({cs.confidence_level.value}).",
                impact=min(100.0, cs.overall_confidence),
                source_engine=FactorSource.CONFIDENCE,
                is_positive=True,
            ))

        # Low risk
        if rs.overall_risk < 40.0:
            factors.append(ExplanationFactor(
                name="Acceptable risk level",
                description=f"Overall risk of {rs.overall_risk:.0f}/100 ({rs.risk_level.value}) is within acceptable bounds.",
                impact=min(100.0, 100.0 - rs.overall_risk),
                source_engine=FactorSource.RISK,
                is_positive=True,
            ))

        # Required items met
        if ev.required_items_met:
            factors.append(ExplanationFactor(
                name="Required evidence items satisfied",
                description="All mandatory evidence categories were collected.",
                impact=70.0,
                source_engine=FactorSource.EVIDENCE,
                is_positive=True,
            ))

        # Fresh data
        if ev.overall_freshness >= 0.80:
            factors.append(ExplanationFactor(
                name="Fresh market data",
                description=f"Evidence freshness of {ev.overall_freshness*100:.0f}% indicates timely information.",
                impact=ev.overall_freshness * 60.0,
                source_engine=FactorSource.EVIDENCE,
                is_positive=True,
            ))

        return sorted(factors, key=lambda f: f.impact, reverse=True)[:6]

    def _build_opposing_factors(
        self,
        ev: EvidenceSnapshot,
        cs: ConfidenceSnapshot,
        rs: RiskSnapshot,
    ) -> List[ExplanationFactor]:
        factors: List[ExplanationFactor] = []

        # Low confidence
        if cs.overall_confidence < 60.0:
            factors.append(ExplanationFactor(
                name="Limited assessment confidence",
                description=f"Overall confidence of {cs.overall_confidence:.0f}/100 ({cs.confidence_level.value}) is below the reliable threshold.",
                impact=min(100.0, 100.0 - cs.overall_confidence),
                source_engine=FactorSource.CONFIDENCE,
                is_positive=False,
            ))

        # High risk
        if rs.overall_risk >= 60.0:
            factors.append(ExplanationFactor(
                name="Elevated risk level",
                description=f"Overall risk of {rs.overall_risk:.0f}/100 ({rs.risk_level.value}) exceeds acceptable bounds.",
                impact=min(100.0, rs.overall_risk),
                source_engine=FactorSource.RISK,
                is_positive=False,
            ))

        # High market risk
        dr = rs.decision_risk
        if dr.market_risk >= 60.0:
            factors.append(ExplanationFactor(
                name="Elevated market risk",
                description=f"Market risk dimension score of {dr.market_risk:.0f}/100.",
                impact=min(100.0, dr.market_risk),
                source_engine=FactorSource.RISK,
                is_positive=False,
            ))

        # Low evidence coverage
        if ev.coverage_fraction < 0.50:
            factors.append(ExplanationFactor(
                name="Incomplete evidence coverage",
                description=f"Only {ev.coverage_fraction*100:.0f}% of expected evidence categories present.",
                impact=min(100.0, (1.0 - ev.coverage_fraction) * 80.0),
                source_engine=FactorSource.EVIDENCE,
                is_positive=False,
            ))

        # Stale data
        if ev.overall_freshness < 0.50:
            factors.append(ExplanationFactor(
                name="Stale evidence data",
                description=f"Evidence freshness of {ev.overall_freshness*100:.0f}% indicates outdated information.",
                impact=min(100.0, (1.0 - ev.overall_freshness) * 70.0),
                source_engine=FactorSource.EVIDENCE,
                is_positive=False,
            ))

        # Controls breached
        if rs.decision_risk.controls_breached:
            factors.append(ExplanationFactor(
                name="Risk controls breached",
                description="One or more hard risk controls have been violated, blocking execution.",
                impact=100.0,
                source_engine=FactorSource.RISK,
                is_positive=False,
            ))

        # High uncertainty
        if cs.decision_confidence.uncertainty >= 40.0:
            factors.append(ExplanationFactor(
                name="High assessment uncertainty",
                description=f"Confidence uncertainty of {cs.decision_confidence.uncertainty:.0f}/100 reduces reliability.",
                impact=min(100.0, cs.decision_confidence.uncertainty),
                source_engine=FactorSource.CONFIDENCE,
                is_positive=False,
            ))

        return sorted(factors, key=lambda f: f.impact, reverse=True)[:6]

    def _build_assumptions(
        self,
        ev: EvidenceSnapshot,
        cs: ConfidenceSnapshot,
    ) -> List[str]:
        assumptions = []
        if not ev.required_items_met:
            assumptions.append("Some required evidence items are missing; analysis proceeds with available data.")
        if not cs.decision_confidence.scoring_available:
            assumptions.append("Strategy scoring data is unavailable; confidence is estimated from evidence and reasoning only.")
        if ev.overall_freshness < 0.70:
            assumptions.append("Evidence freshness is below optimal; some data may not reflect current market conditions.")
        if ev.coverage_fraction < 0.80:
            assumptions.append(f"Evidence coverage is {ev.coverage_fraction*100:.0f}%; gaps may affect assessment completeness.")
        return assumptions

    def _build_key_risks(self, rs: RiskSnapshot) -> List[str]:
        risks = []
        dr = rs.decision_risk
        if dr.market_risk >= 50.0:
            risks.append(f"Market risk is elevated ({dr.market_risk:.0f}/100).")
        if dr.company_risk >= 50.0:
            risks.append(f"Company-specific risk is elevated ({dr.company_risk:.0f}/100).")
        if dr.strategy_risk >= 50.0:
            risks.append(f"Strategy performance risk is elevated ({dr.strategy_risk:.0f}/100).")
        if dr.execution_risk >= 50.0:
            risks.append(f"Execution risk is elevated ({dr.execution_risk:.0f}/100).")
        if rs.decision_risk.controls_breached:
            risks.append("Hard risk controls are breached — execution is blocked.")
        if not risks:
            risks.append("No critical risk dimensions identified.")
        return risks

    # ── Narrative builders ────────────────────────────────────────────────────

    @staticmethod
    def _one_line(
        subject_id: str, subject_type: str,
        outcome: DecisionOutcome, conf: float, risk: float,
    ) -> str:
        label_map = {
            "proceed": "PROCEED",
            "caution": "CAUTION",
            "halt": "HALT",
            "insufficient_data": "INSUFFICIENT DATA",
        }
        label = label_map[outcome.value]
        return (
            f"{subject_id} ({subject_type}) — Assessment: {label} "
            f"| Confidence: {conf:.0f}/100 | Risk: {risk:.0f}/100"
        )[:120]

    @staticmethod
    def _executive_summary(
        ev: EvidenceSnapshot,
        cs: ConfidenceSnapshot,
        rs: RiskSnapshot,
        outcome: DecisionOutcome,
    ) -> str:
        outcome_desc = {
            "proceed": "is suitable for consideration",
            "caution": "requires additional scrutiny before consideration",
            "halt": "should not be considered due to elevated risk or control breaches",
            "insufficient_data": "cannot be reliably assessed due to insufficient evidence",
        }[outcome.value]
        return (
            f"Analysis of {ev.subject_id} ({ev.subject_type}) indicates that this subject "
            f"{outcome_desc}. "
            f"The assessment is based on {ev.item_count} evidence items across "
            f"{len(ev.sources_included)} source categories, achieving {ev.coverage_fraction*100:.0f}% "
            f"coverage. Overall confidence: {cs.overall_confidence:.0f}/100 "
            f"({cs.confidence_level.value}). Overall risk: {rs.overall_risk:.0f}/100 "
            f"({rs.risk_level.value}). "
            f"Risk policy status: {rs.policy_status.value}."
        )

    @staticmethod
    def _technical_summary(
        ev: EvidenceSnapshot,
        rs_n: ReasoningSnapshot,
        cs: ConfidenceSnapshot,
        rs: RiskSnapshot,
    ) -> str:
        dc = cs.decision_confidence
        dr = rs.decision_risk
        return (
            f"EVIDENCE: {ev.item_count} items | quality={ev.quality_score:.1f}/100 | "
            f"coverage={ev.coverage_fraction*100:.0f}% | freshness={ev.overall_freshness*100:.0f}% | "
            f"required_met={ev.required_items_met}\n"
            f"REASONING: {rs_n.reasoning_chain.step_count} steps | "
            f"consistency={rs_n.logic_result.consistency_score:.1f}/100 | "
            f"quality={rs_n.quality_score.overall:.1f}/100 | "
            f"avg_step_confidence={rs_n.reasoning_chain.avg_step_confidence:.1f}\n"
            f"CONFIDENCE: overall={cs.overall_confidence:.1f}/100 | level={cs.confidence_level.value} | "
            f"evidence_conf={dc.evidence_confidence:.1f} | reasoning_conf={dc.reasoning_confidence:.1f} | "
            f"uncertainty={dc.uncertainty:.1f} | calibration={cs.calibration_status.value}\n"
            f"RISK: overall={rs.overall_risk:.1f}/100 | level={rs.risk_level.value} | "
            f"market={dr.market_risk:.1f} | company={dr.company_risk:.1f} | "
            f"strategy={dr.strategy_risk:.1f} | execution={dr.execution_risk:.1f} | "
            f"policy={rs.policy_status.value} | controls_breached={dr.controls_breached}"
        )
