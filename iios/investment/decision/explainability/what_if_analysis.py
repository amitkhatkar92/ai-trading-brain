"""iios/investment/decision/explainability/what_if_analysis.py
WhatIfAnalysis — evaluates hypothetical input changes and their effect on outcome.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.explainability.explainability_constants import (
    DecisionOutcome,
    PROCEED_CONFIDENCE_MIN,
    PROCEED_RISK_MAX,
    CAUTION_CONFIDENCE_MIN,
)


@dataclass(frozen=True)
class WhatIfScenario:
    """A hypothetical change and its projected effect."""
    scenario_id:         str
    description:         str
    modified_confidence: float    # 0–100
    modified_risk:       float    # 0–100
    projected_outcome:   DecisionOutcome
    outcome_changed:     bool
    delta_confidence:    float    # vs actual
    delta_risk:          float    # vs actual

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id":         self.scenario_id,
            "description":         self.description,
            "modified_confidence": round(self.modified_confidence, 2),
            "modified_risk":       round(self.modified_risk, 2),
            "projected_outcome":   self.projected_outcome.value,
            "outcome_changed":     self.outcome_changed,
            "delta_confidence":    round(self.delta_confidence, 2),
            "delta_risk":          round(self.delta_risk, 2),
        }


@dataclass(frozen=True)
class WhatIfReport:
    actual_outcome:  str
    scenarios:       Tuple[WhatIfScenario, ...]
    changed_count:   int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actual_outcome": self.actual_outcome,
            "changed_count":  self.changed_count,
            "scenarios":      [s.to_dict() for s in self.scenarios],
        }


def _project_outcome(
    confidence: float,
    risk:       float,
    controls_breached: bool = False,
) -> DecisionOutcome:
    if controls_breached or risk >= 80.0:
        return DecisionOutcome.HALT
    if confidence < CAUTION_CONFIDENCE_MIN:
        return DecisionOutcome.INSUFFICIENT_DATA
    if confidence >= PROCEED_CONFIDENCE_MIN and risk < PROCEED_RISK_MAX:
        return DecisionOutcome.PROCEED
    return DecisionOutcome.CAUTION


class WhatIfAnalyzer:
    """Evaluates hypothetical scenarios against the actual outcome."""

    def analyze(
        self,
        actual_confidence:   float,
        actual_risk:         float,
        actual_outcome:      DecisionOutcome,
        controls_breached:   bool = False,
    ) -> WhatIfReport:
        scenarios: List[WhatIfScenario] = []

        hypotheticals = [
            ("conf+10", f"If confidence were {actual_confidence+10:.0f}/100",
             actual_confidence + 10.0, actual_risk),
            ("conf-10", f"If confidence were {actual_confidence-10:.0f}/100",
             actual_confidence - 10.0, actual_risk),
            ("risk+10", f"If risk were {actual_risk+10:.0f}/100",
             actual_confidence, actual_risk + 10.0),
            ("risk-10", f"If risk were {actual_risk-10:.0f}/100",
             actual_confidence, actual_risk - 10.0),
            ("conf_high", "If confidence were 80/100",
             80.0, actual_risk),
            ("conf_low", "If confidence were 30/100",
             30.0, actual_risk),
            ("risk_low", "If risk were 30/100",
             actual_confidence, 30.0),
            ("risk_high", "If risk were 75/100",
             actual_confidence, 75.0),
        ]

        for sid, desc, c, r in hypotheticals:
            c = max(0.0, min(100.0, c))
            r = max(0.0, min(100.0, r))
            proj = _project_outcome(c, r, controls_breached)
            scenarios.append(WhatIfScenario(
                scenario_id         = sid,
                description         = desc,
                modified_confidence = c,
                modified_risk       = r,
                projected_outcome   = proj,
                outcome_changed     = proj != actual_outcome,
                delta_confidence    = round(c - actual_confidence, 2),
                delta_risk          = round(r - actual_risk, 2),
            ))

        changed = sum(1 for s in scenarios if s.outcome_changed)
        return WhatIfReport(
            actual_outcome = actual_outcome.value,
            scenarios      = tuple(scenarios),
            changed_count  = changed,
        )
