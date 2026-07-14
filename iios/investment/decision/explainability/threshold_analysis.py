"""iios/investment/decision/explainability/threshold_analysis.py
ThresholdAnalysis — finds exact thresholds where DecisionOutcome would change.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from iios.investment.decision.explainability.explainability_constants import DecisionOutcome
from iios.investment.decision.explainability.what_if_analysis import _project_outcome


@dataclass(frozen=True)
class ThresholdResult:
    """Result of threshold analysis for one dimension."""
    dimension:                 str
    current_value:             float
    threshold_to_proceed:      Optional[float]   # None if already PROCEED or impossible
    threshold_to_halt:         Optional[float]   # None if already HALT or impossible
    distance_to_proceed:       Optional[float]   # None if already PROCEED
    distance_to_halt:          Optional[float]   # None if already HALT
    current_outcome:           str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension":            self.dimension,
            "current_value":        round(self.current_value, 2),
            "threshold_to_proceed": None if self.threshold_to_proceed is None
                                    else round(self.threshold_to_proceed, 2),
            "threshold_to_halt":    None if self.threshold_to_halt is None
                                    else round(self.threshold_to_halt, 2),
            "distance_to_proceed":  None if self.distance_to_proceed is None
                                    else round(self.distance_to_proceed, 2),
            "distance_to_halt":     None if self.distance_to_halt is None
                                    else round(self.distance_to_halt, 2),
            "current_outcome":      self.current_outcome,
        }


@dataclass(frozen=True)
class ThresholdReport:
    confidence_threshold: ThresholdResult
    risk_threshold:       ThresholdResult
    verdict:              str  # plain-English summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_threshold": self.confidence_threshold.to_dict(),
            "risk_threshold":       self.risk_threshold.to_dict(),
            "verdict":              self.verdict,
        }


class ThresholdAnalyzer:
    """Binary-search threshold finder for confidence and risk dimensions."""

    def analyze(
        self,
        actual_confidence: float,
        actual_risk:       float,
        actual_outcome:    DecisionOutcome,
        controls_breached: bool = False,
        resolution:        float = 0.5,
    ) -> ThresholdReport:
        conf_result = self._find_thresholds(
            "confidence", actual_confidence,
            lambda v: _project_outcome(v, actual_risk, controls_breached),
            actual_outcome, resolution,
        )
        risk_result = self._find_thresholds(
            "risk", actual_risk,
            lambda v: _project_outcome(actual_confidence, v, controls_breached),
            actual_outcome, resolution,
        )

        verdict = self._make_verdict(
            actual_outcome, actual_confidence, actual_risk,
            conf_result, risk_result,
        )
        return ThresholdReport(
            confidence_threshold = conf_result,
            risk_threshold       = risk_result,
            verdict              = verdict,
        )

    def _find_thresholds(
        self, dim: str, current: float,
        outcome_fn, current_outcome: DecisionOutcome,
        resolution: float,
    ) -> ThresholdResult:
        # Search upward for PROCEED threshold
        proceed_thresh: Optional[float] = None
        halt_thresh:    Optional[float] = None

        if current_outcome != DecisionOutcome.PROCEED:
            # Scan upward (for confidence) or downward (for risk) to find PROCEED
            if dim == "confidence":
                v = current
                while v <= 100.0:
                    if outcome_fn(v) == DecisionOutcome.PROCEED:
                        proceed_thresh = v
                        break
                    v += resolution
            else:  # risk — scan downward
                v = current
                while v >= 0.0:
                    if outcome_fn(v) == DecisionOutcome.PROCEED:
                        proceed_thresh = v
                        break
                    v -= resolution

        if current_outcome != DecisionOutcome.HALT:
            if dim == "confidence":
                v = current
                while v >= 0.0:
                    if outcome_fn(v) == DecisionOutcome.HALT:
                        halt_thresh = v
                        break
                    v -= resolution
            else:  # risk — scan upward
                v = current
                while v <= 100.0:
                    if outcome_fn(v) == DecisionOutcome.HALT:
                        halt_thresh = v
                        break
                    v += resolution

        dist_proceed = None if proceed_thresh is None else abs(current - proceed_thresh)
        dist_halt    = None if halt_thresh    is None else abs(current - halt_thresh)

        return ThresholdResult(
            dimension            = dim,
            current_value        = current,
            threshold_to_proceed = proceed_thresh,
            threshold_to_halt    = halt_thresh,
            distance_to_proceed  = dist_proceed,
            distance_to_halt     = dist_halt,
            current_outcome      = current_outcome.value,
        )

    @staticmethod
    def _make_verdict(
        outcome: DecisionOutcome,
        conf: float, risk: float,
        conf_r: ThresholdResult, risk_r: ThresholdResult,
    ) -> str:
        if outcome == DecisionOutcome.PROCEED:
            parts = []
            if conf_r.distance_to_halt is not None:
                parts.append(
                    f"Confidence must drop by {conf_r.distance_to_halt:.1f} points to trigger HALT."
                )
            if risk_r.distance_to_halt is not None:
                parts.append(
                    f"Risk must rise by {risk_r.distance_to_halt:.1f} points to trigger HALT."
                )
            return " ".join(parts) or "Outcome is PROCEED with comfortable margins."

        if outcome == DecisionOutcome.HALT:
            return (
                f"Critical conditions are active. Execution is blocked. "
                f"Remediation is required before re-assessment."
            )

        # CAUTION or INSUFFICIENT_DATA
        parts = []
        if conf_r.threshold_to_proceed is not None:
            parts.append(
                f"Confidence must reach {conf_r.threshold_to_proceed:.1f}/100 "
                f"(currently {conf:.1f}) to qualify as PROCEED."
            )
        if risk_r.threshold_to_proceed is not None:
            parts.append(
                f"Risk must reduce to {risk_r.threshold_to_proceed:.1f}/100 "
                f"(currently {risk:.1f}) to qualify as PROCEED."
            )
        return " ".join(parts) or f"Outcome is {outcome.value.upper()}."
