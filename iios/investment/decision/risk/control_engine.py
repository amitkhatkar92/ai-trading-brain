"""iios/investment/decision/risk/control_engine.py
ControlEngine — evaluates all registered controls against a DecisionRisk.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.risk.control_registry import ControlRegistry
from iios.investment.decision.risk.decision_risk import DecisionRisk
from iios.investment.decision.risk.risk_constants import (
    RiskControlStatus,
    RiskDimension,
)
from iios.investment.decision.risk.risk_controls import ControlViolation


@dataclass(frozen=True)
class ControlEvaluationResult:
    controls_checked:  int
    violations:        Tuple[ControlViolation, ...]
    warnings:          Tuple[ControlViolation, ...]
    hard_breach:       bool   # at least one hard-limit breached

    def to_dict(self) -> Dict[str, Any]:
        return {
            "controls_checked": self.controls_checked,
            "hard_breach":      self.hard_breach,
            "violations":       [v.to_dict() for v in self.violations],
            "warnings":         [v.to_dict() for v in self.warnings],
        }


_DIM_RISK_ATTR = {
    RiskDimension.MARKET:     "market_risk",
    RiskDimension.COMPANY:    "company_risk",
    RiskDimension.STRATEGY:   "strategy_risk",
    RiskDimension.EXECUTION:  "execution_risk",
    RiskDimension.CONFIDENCE: "confidence_risk",
}


class ControlEngine:
    """Evaluates all registered controls against a DecisionRisk object."""

    def __init__(self, registry: Optional[ControlRegistry] = None) -> None:
        self._registry = registry or ControlRegistry()

    def evaluate(self, decision_risk: DecisionRisk) -> ControlEvaluationResult:
        violations: List[ControlViolation] = []
        warnings:   List[ControlViolation] = []

        controls = self._registry.all_controls()
        for ctrl in controls:
            # Special control for overall risk (no dimension-specific attr)
            if ctrl.control_id == "ctrl_overall_max":
                actual = decision_risk.overall_risk
            else:
                attr   = _DIM_RISK_ATTR.get(ctrl.dimension)
                actual = getattr(decision_risk, attr, decision_risk.overall_risk) if attr else decision_risk.overall_risk

            if actual > ctrl.max_allowed:
                status = RiskControlStatus.BREACHED if ctrl.is_hard_limit else RiskControlStatus.WARNING
                msg    = (f"{'BREACH' if ctrl.is_hard_limit else 'WARNING'}: "
                          f"{ctrl.name} — actual={actual:.1f} > max={ctrl.max_allowed:.1f}")
                violation = ControlViolation(
                    control=ctrl, actual_value=actual, status=status, message=msg,
                )
                if ctrl.is_hard_limit:
                    violations.append(violation)
                else:
                    warnings.append(violation)

        hard_breach = any(v.is_hard_limit_breach for v in violations)

        return ControlEvaluationResult(
            controls_checked=len(controls),
            violations=tuple(violations),
            warnings=tuple(warnings),
            hard_breach=hard_breach,
        )
