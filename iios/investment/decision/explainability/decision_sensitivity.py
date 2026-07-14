"""iios/investment/decision/explainability/decision_sensitivity.py
DecisionSensitivity — measures how sensitive the outcome is to each factor.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from iios.investment.decision.explainability.explainability_constants import (
    DecisionOutcome,
    SENSITIVITY_PERTURBATION_STEP,
)
from iios.investment.decision.explainability.what_if_analysis import _project_outcome


@dataclass(frozen=True)
class SensitivityEntry:
    dimension:          str     # "confidence" | "market_risk" | "company_risk" | ...
    base_value:         float
    perturb_up:         float   # base + step
    perturb_down:       float   # base - step
    outcome_up:         str
    outcome_down:       str
    outcome_flipped_up:   bool
    outcome_flipped_down: bool
    sensitivity_score:  float   # 0–100 (100 = very sensitive)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension":           self.dimension,
            "base_value":          round(self.base_value, 2),
            "perturb_up":          round(self.perturb_up, 2),
            "perturb_down":        round(self.perturb_down, 2),
            "outcome_up":          self.outcome_up,
            "outcome_down":        self.outcome_down,
            "outcome_flipped_up":  self.outcome_flipped_up,
            "outcome_flipped_down": self.outcome_flipped_down,
            "sensitivity_score":   round(self.sensitivity_score, 2),
        }


@dataclass(frozen=True)
class SensitivityReport:
    overall_sensitivity: float   # 0–100 average sensitivity
    most_sensitive:      str     # dimension with highest sensitivity_score
    entries:             Tuple[SensitivityEntry, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_sensitivity": round(self.overall_sensitivity, 2),
            "most_sensitive":      self.most_sensitive,
            "entries":             [e.to_dict() for e in self.entries],
        }


class DecisionSensitivityAnalyzer:
    """Measures how sensitive the DecisionOutcome is to ±perturbations on key dimensions."""

    def analyze(
        self,
        actual_confidence:   float,
        actual_risk:         float,
        actual_outcome:      DecisionOutcome,
        controls_breached:   bool = False,
        step:                float = SENSITIVITY_PERTURBATION_STEP,
    ) -> SensitivityReport:
        entries: List[SensitivityEntry] = []
        base_out = actual_outcome.value

        # Confidence sensitivity
        up_c   = min(100.0, actual_confidence + step)
        down_c = max(0.0,   actual_confidence - step)
        o_up   = _project_outcome(up_c,   actual_risk, controls_breached)
        o_down = _project_outcome(down_c, actual_risk, controls_breached)
        sc     = 100.0 if (o_up.value != base_out or o_down.value != base_out) else (
            abs(up_c - actual_confidence) / max(1.0, 100.0 - actual_confidence) * 50.0
        )
        entries.append(SensitivityEntry(
            dimension="confidence", base_value=actual_confidence,
            perturb_up=up_c, perturb_down=down_c,
            outcome_up=o_up.value, outcome_down=o_down.value,
            outcome_flipped_up=o_up.value != base_out,
            outcome_flipped_down=o_down.value != base_out,
            sensitivity_score=round(min(100.0, sc), 2),
        ))

        # Risk sensitivity
        up_r   = min(100.0, actual_risk + step)
        down_r = max(0.0,   actual_risk - step)
        o_up   = _project_outcome(actual_confidence, up_r,   controls_breached)
        o_down = _project_outcome(actual_confidence, down_r, controls_breached)
        sr     = 100.0 if (o_up.value != base_out or o_down.value != base_out) else (
            abs(up_r - actual_risk) / max(1.0, 100.0 - actual_risk) * 50.0
        )
        entries.append(SensitivityEntry(
            dimension="risk", base_value=actual_risk,
            perturb_up=up_r, perturb_down=down_r,
            outcome_up=o_up.value, outcome_down=o_down.value,
            outcome_flipped_up=o_up.value != base_out,
            outcome_flipped_down=o_down.value != base_out,
            sensitivity_score=round(min(100.0, sr), 2),
        ))

        avg_s  = sum(e.sensitivity_score for e in entries) / max(1, len(entries))
        most   = max(entries, key=lambda e: e.sensitivity_score).dimension

        return SensitivityReport(
            overall_sensitivity = round(avg_s, 2),
            most_sensitive      = most,
            entries             = tuple(entries),
        )
