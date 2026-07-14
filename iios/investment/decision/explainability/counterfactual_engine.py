"""iios/investment/decision/explainability/counterfactual_engine.py
CounterfactualEngine — aggregates what-if, sensitivity, and threshold analyses.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.explainability.decision_explanation import DecisionExplanation
from iios.investment.decision.explainability.decision_sensitivity import (
    DecisionSensitivityAnalyzer,
    SensitivityReport,
)
from iios.investment.decision.explainability.explainability_constants import DecisionOutcome
from iios.investment.decision.explainability.threshold_analysis import (
    ThresholdAnalyzer,
    ThresholdReport,
)
from iios.investment.decision.explainability.what_if_analysis import (
    WhatIfAnalyzer,
    WhatIfReport,
)


@dataclass(frozen=True)
class CounterfactualReport:
    """
    Complete counterfactual analysis for one decision explanation.
    Answers: 'What would need to change for the outcome to be different?'
    """
    decision_id:       str
    actual_outcome:    str
    what_if:           WhatIfReport
    sensitivity:       SensitivityReport
    threshold:         ThresholdReport
    narrative:         str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":    self.decision_id,
            "actual_outcome": self.actual_outcome,
            "what_if":        self.what_if.to_dict(),
            "sensitivity":    self.sensitivity.to_dict(),
            "threshold":      self.threshold.to_dict(),
            "narrative":      self.narrative,
        }


class CounterfactualEngine:
    """Generates a complete CounterfactualReport from a DecisionExplanation."""

    def __init__(self) -> None:
        self._what_if     = WhatIfAnalyzer()
        self._sensitivity = DecisionSensitivityAnalyzer()
        self._threshold   = ThresholdAnalyzer()

    def analyze(
        self,
        explanation:       DecisionExplanation,
        controls_breached: bool = False,
    ) -> CounterfactualReport:
        outcome    = explanation.outcome
        confidence = explanation.overall_confidence
        risk       = explanation.overall_risk

        what_if_report     = self._what_if.analyze(confidence, risk, outcome, controls_breached)
        sensitivity_report = self._sensitivity.analyze(confidence, risk, outcome, controls_breached)
        threshold_report   = self._threshold.analyze(confidence, risk, outcome, controls_breached)

        narrative = self._build_narrative(
            explanation, outcome, what_if_report, sensitivity_report, threshold_report,
        )

        return CounterfactualReport(
            decision_id    = explanation.decision_id,
            actual_outcome = outcome.value,
            what_if        = what_if_report,
            sensitivity    = sensitivity_report,
            threshold      = threshold_report,
            narrative      = narrative,
        )

    @staticmethod
    def _build_narrative(
        exp: DecisionExplanation,
        outcome: DecisionOutcome,
        wif: WhatIfReport,
        sens: SensitivityReport,
        thresh: ThresholdReport,
    ) -> str:
        changed = wif.changed_count
        most_sensitive = sens.most_sensitive

        lines = [
            f"COUNTERFACTUAL ANALYSIS — {exp.subject_id} ({exp.subject_type})",
            "",
            f"Actual outcome: {outcome.value.upper()}",
            f"Confidence: {exp.overall_confidence:.1f}/100 | Risk: {exp.overall_risk:.1f}/100",
            "",
            f"What-if analysis tested {len(wif.scenarios)} hypothetical scenarios. "
            f"{changed} of them would produce a different outcome.",
            "",
            f"The most sensitive dimension is '{most_sensitive}' — small changes here "
            f"are most likely to flip the outcome.",
            "",
            thresh.verdict,
        ]
        return "\n".join(lines)
