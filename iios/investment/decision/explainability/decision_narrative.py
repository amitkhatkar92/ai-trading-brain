"""iios/investment/decision/explainability/decision_narrative.py
DecisionNarrative — generates structured narrative sections for an explanation.
Supports pluggable NarrativeTemplate for multilingual/regulatory variants.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.explainability.decision_explanation import DecisionExplanation
from iios.investment.decision.explainability.explainability_constants import DecisionOutcome


@dataclass(frozen=True)
class NarrativeReport:
    """Full structured narrative for one decision explanation."""
    decision_id:       str
    subject_id:        str
    outcome_header:    str    # "PROCEED" / "CAUTION" / "HALT" / "INSUFFICIENT DATA"
    situation:         str    # What is being assessed?
    methodology:       str    # How was it assessed?
    findings:          str    # What was found?
    conclusion:        str    # What does it mean?
    caveats:           str    # Limitations / assumptions
    audit_note:        str    # Immutable audit reference

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":    self.decision_id,
            "subject_id":     self.subject_id,
            "outcome_header": self.outcome_header,
            "situation":      self.situation,
            "methodology":    self.methodology,
            "findings":       self.findings,
            "conclusion":     self.conclusion,
            "caveats":        self.caveats,
            "audit_note":     self.audit_note,
        }

    def as_text(self) -> str:
        return (
            f"=== {self.outcome_header} ===\n\n"
            f"SITUATION\n{self.situation}\n\n"
            f"METHODOLOGY\n{self.methodology}\n\n"
            f"FINDINGS\n{self.findings}\n\n"
            f"CONCLUSION\n{self.conclusion}\n\n"
            f"CAVEATS\n{self.caveats}\n\n"
            f"AUDIT\n{self.audit_note}\n"
        )


class NarrativeTemplate(abc.ABC):
    """ABC for pluggable narrative templates (English default + custom variants)."""

    @property
    @abc.abstractmethod
    def template_id(self) -> str: ...

    @abc.abstractmethod
    def render(self, explanation: DecisionExplanation) -> NarrativeReport: ...


class EnglishNarrativeTemplate(NarrativeTemplate):
    """
    Default English-language institutional narrative template.
    Produces regulator-friendly, human-readable reports.
    """

    @property
    def template_id(self) -> str:
        return "en_institutional_v1"

    def render(self, explanation: DecisionExplanation) -> NarrativeReport:
        outcome_labels = {
            "proceed": "ASSESSMENT: PROCEED",
            "caution": "ASSESSMENT: CAUTION",
            "halt": "ASSESSMENT: HALT",
            "insufficient_data": "ASSESSMENT: INSUFFICIENT DATA",
        }
        header = outcome_labels[explanation.outcome.value]

        situation = (
            f"This report provides an automated decision intelligence assessment for "
            f"{explanation.subject_id} (type: {explanation.subject_type}). "
            f"The assessment integrates evidence quality analysis, multi-step logical "
            f"reasoning, statistical confidence estimation, and multi-dimensional risk "
            f"evaluation to produce a transparent and auditable conclusion."
        )

        methodology = (
            f"The assessment pipeline processed {explanation.evidence_item_count} evidence "
            f"items from {explanation.source_count} source categories "
            f"(coverage: {explanation.evidence_coverage*100:.0f}%, "
            f"freshness: {explanation.evidence_freshness*100:.0f}%). "
            f"A {explanation.reasoning_step_count}-step reasoning chain was constructed "
            f"(logic consistency: {explanation.logic_consistency:.0f}/100). "
            f"Confidence was estimated at {explanation.overall_confidence:.0f}/100 and "
            f"risk was assessed at {explanation.overall_risk:.0f}/100."
        )

        sup_text = "; ".join(f.name for f in explanation.supporting_factors[:3]) or "None identified"
        opp_text = "; ".join(f.name for f in explanation.opposing_factors[:3]) or "None identified"

        findings = (
            f"Supporting factors: {sup_text}.\n"
            f"Opposing factors: {opp_text}.\n"
            f"Net factor impact score: {explanation.net_impact_score:+.1f}.\n"
            f"Key risks: {'; '.join(explanation.key_risks[:3]) or 'None identified'}."
        )

        conclusion_map = {
            "proceed": (
                f"Based on available evidence, {explanation.subject_id} demonstrates "
                f"acceptable confidence ({explanation.overall_confidence:.0f}/100) and "
                f"risk ({explanation.overall_risk:.0f}/100) profiles. "
                f"The assessment supports consideration subject to standard review processes."
            ),
            "caution": (
                f"The assessment of {explanation.subject_id} indicates elevated uncertainty "
                f"or risk. Confidence: {explanation.overall_confidence:.0f}/100, "
                f"Risk: {explanation.overall_risk:.0f}/100. "
                f"Additional diligence is recommended before proceeding."
            ),
            "halt": (
                f"The assessment of {explanation.subject_id} has identified critical risk "
                f"conditions or policy violations that preclude further consideration at "
                f"this time. Risk: {explanation.overall_risk:.0f}/100. "
                f"Review and remediation are required before re-assessment."
            ),
            "insufficient_data": (
                f"Insufficient evidence was available to produce a reliable assessment of "
                f"{explanation.subject_id}. "
                f"Only {explanation.evidence_item_count} evidence items were collected. "
                f"Additional data collection is required."
            ),
        }
        conclusion = conclusion_map[explanation.outcome.value]

        caveats_parts = list(explanation.assumptions) or ["No material assumptions identified."]
        caveats = " ".join(caveats_parts)

        audit_note = (
            f"This assessment was generated automatically by the IIOS Decision Intelligence "
            f"Pipeline. It is deterministic, reproducible, and fully traceable to the "
            f"originating evidence, reasoning, confidence, and risk engine outputs. "
            f"Decision ID: {explanation.decision_id}."
        )

        return NarrativeReport(
            decision_id    = explanation.decision_id,
            subject_id     = explanation.subject_id,
            outcome_header = header,
            situation      = situation,
            methodology    = methodology,
            findings       = findings,
            conclusion     = conclusion,
            caveats        = caveats,
            audit_note     = audit_note,
        )


class DecisionNarrative:
    """
    Generates a NarrativeReport from a DecisionExplanation.
    Supports pluggable NarrativeTemplates.
    """

    def __init__(self, template: NarrativeTemplate | None = None) -> None:
        self._template = template or EnglishNarrativeTemplate()

    def generate(self, explanation: DecisionExplanation) -> NarrativeReport:
        return self._template.render(explanation)

    def register_template(self, template: NarrativeTemplate) -> None:
        self._template = template
