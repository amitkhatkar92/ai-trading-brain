"""iios/investment/portfolio/optimization/optimization_validator.py

Validates an OptimizationPlan for integrity, feasibility, and consistency.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.optimization.optimization_plan import OptimizationPlan
from iios.investment.portfolio.optimization.optimization_types import (
    WEIGHT_SUM_TOLERANCE,
    ConstraintOutcome,
)


@dataclass(frozen=True)
class ValidationFinding:
    """A single validation finding."""

    finding_id: str               = field(default_factory=lambda: str(uuid.uuid4()))
    category:   str               = ""
    outcome:    ConstraintOutcome = ConstraintOutcome.SATISFIED
    rule:       str               = ""
    message:    str               = ""
    actual:     float             = 0.0
    expected:   float             = 0.0

    @property
    def passed(self) -> bool:
        return self.outcome == ConstraintOutcome.SATISFIED

    @property
    def is_blocking(self) -> bool:
        return self.outcome == ConstraintOutcome.VIOLATED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "category":   self.category,
            "outcome":    self.outcome.value,
            "rule":       self.rule,
            "message":    self.message,
            "actual":     round(self.actual, 6),
            "expected":   round(self.expected, 6),
        }


@dataclass(frozen=True)
class OptimizationValidationReport:
    """Summary of validation checks on an OptimizationPlan."""

    report_id:    str                           = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id:      str                           = ""
    portfolio_id: str                           = ""
    findings:     Tuple[ValidationFinding, ...]= field(default_factory=tuple)
    total:        int                           = 0
    passed:       int                           = 0
    warnings:     int                           = 0
    failures:     int                           = 0
    is_valid:     bool                          = False
    duration_ms:  float                         = 0.0
    validated_at: float                         = field(default_factory=time.time)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def failed_findings(self) -> Tuple[ValidationFinding, ...]:
        return tuple(f for f in self.findings if f.is_blocking)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":    self.report_id,
            "plan_id":      self.plan_id,
            "portfolio_id": self.portfolio_id,
            "total":        self.total,
            "passed":       self.passed,
            "warnings":     self.warnings,
            "failures":     self.failures,
            "is_valid":     self.is_valid,
            "pass_rate":    round(self.pass_rate, 4),
            "duration_ms":  round(self.duration_ms, 2),
            "validated_at": self.validated_at,
            "findings":     [f.to_dict() for f in self.findings],
        }


class OptimizationValidator:
    """
    Validates OptimizationPlan integrity.
    Checks:
      1. Weight sum ≈ 1.0
      2. No negative weights (long-only mode)
      3. Non-empty positions
      4. Objective improvement ≥ 0 (optimization didn't make things worse)
      5. Convergence
      6. Capital conservation
    """

    def validate(self, plan: OptimizationPlan) -> OptimizationValidationReport:
        t0       = time.time()
        findings: List[ValidationFinding] = []

        weights  = {p.symbol: p.optimized_weight for p in plan.positions}
        w_sum    = sum(weights.values())

        # -- 1. Weight sum -----------------------------------------------
        delta = abs(w_sum - 1.0)
        if plan.total_positions > 0 and delta <= WEIGHT_SUM_TOLERANCE:
            findings.append(ValidationFinding(
                category = "weight_integrity",
                outcome  = ConstraintOutcome.SATISFIED,
                rule     = "weight_sum",
                message  = f"Weights sum to {w_sum:.6f} ≈ 1.0",
                actual   = w_sum, expected = 1.0,
            ))
        elif plan.total_positions > 0:
            findings.append(ValidationFinding(
                category = "weight_integrity",
                outcome  = ConstraintOutcome.VIOLATED,
                rule     = "weight_sum",
                message  = f"Weights sum to {w_sum:.6f}, expected 1.0 (delta {delta:.2e})",
                actual   = w_sum, expected = 1.0,
            ))

        # -- 2. No negative weights (informational) ----------------------
        neg = [(s, w) for s, w in weights.items() if w < -1e-8]
        if neg:
            for sym, w in neg:
                findings.append(ValidationFinding(
                    category = "weight_integrity",
                    outcome  = ConstraintOutcome.WARNING,
                    rule     = "non_negative_weights",
                    message  = f"{sym} has negative weight {w:.6f}",
                    actual   = w, expected = 0.0,
                ))
        else:
            findings.append(ValidationFinding(
                category = "weight_integrity",
                outcome  = ConstraintOutcome.SATISFIED,
                rule     = "non_negative_weights",
                message  = "All weights are non-negative",
            ))

        # -- 3. Position count -------------------------------------------
        n = plan.total_positions
        if n == 0:
            findings.append(ValidationFinding(
                category = "position_count",
                outcome  = ConstraintOutcome.WARNING,
                rule     = "has_positions",
                message  = "No optimized positions",
                actual   = 0, expected = 1,
            ))
        else:
            findings.append(ValidationFinding(
                category = "position_count",
                outcome  = ConstraintOutcome.SATISFIED,
                rule     = "has_positions",
                message  = f"{n} position(s) optimized",
                actual   = n, expected = n,
            ))

        # -- 4. Objective did not worsen (or is trivially zero) ----------
        obj_impr = plan.objective_improvement
        if obj_impr < -0.05:   # Allow tiny numerical noise
            findings.append(ValidationFinding(
                category = "objective_integrity",
                outcome  = ConstraintOutcome.WARNING,
                rule     = "objective_improvement",
                message  = f"Objective degraded by {abs(obj_impr):.4f} (prior was better)",
                actual   = obj_impr, expected = 0.0,
            ))
        else:
            findings.append(ValidationFinding(
                category = "objective_integrity",
                outcome  = ConstraintOutcome.SATISFIED,
                rule     = "objective_improvement",
                message  = f"Objective improved or unchanged ({obj_impr:+.4f})",
                actual   = obj_impr, expected = 0.0,
            ))

        # -- 5. Convergence ----------------------------------------------
        if plan.converged:
            findings.append(ValidationFinding(
                category = "convergence",
                outcome  = ConstraintOutcome.SATISFIED,
                rule     = "convergence",
                message  = f"Converged: {plan.convergence.value}",
            ))
        else:
            findings.append(ValidationFinding(
                category = "convergence",
                outcome  = ConstraintOutcome.WARNING,
                rule     = "convergence",
                message  = f"Did not converge ({plan.convergence.value})",
            ))

        # -- 6. Capital conservation ------------------------------------
        if plan.total_capital > 0:
            total_cap = plan.optimized_invested + plan.cash_capital
            delta_cap = abs(total_cap - plan.total_capital)
            if delta_cap <= 1.0:   # $1 tolerance
                findings.append(ValidationFinding(
                    category = "capital_integrity",
                    outcome  = ConstraintOutcome.SATISFIED,
                    rule     = "capital_conservation",
                    message  = f"Capital conserved: ${total_cap:.2f} ≈ ${plan.total_capital:.2f}",
                    actual   = total_cap, expected = plan.total_capital,
                ))
            else:
                findings.append(ValidationFinding(
                    category = "capital_integrity",
                    outcome  = ConstraintOutcome.VIOLATED,
                    rule     = "capital_conservation",
                    message  = f"Capital not conserved: ${total_cap:.2f} ≠ ${plan.total_capital:.2f}",
                    actual   = total_cap, expected = plan.total_capital,
                ))

        dur_ms   = (time.time() - t0) * 1000
        total    = len(findings)
        passed   = sum(1 for f in findings if f.passed)
        warnings = sum(1 for f in findings if f.outcome == ConstraintOutcome.WARNING)
        failures = sum(1 for f in findings if f.is_blocking)

        return OptimizationValidationReport(
            plan_id      = plan.plan_id,
            portfolio_id = plan.portfolio_id,
            findings     = tuple(findings),
            total        = total,
            passed       = passed,
            warnings     = warnings,
            failures     = failures,
            is_valid     = failures == 0,
            duration_ms  = dur_ms,
        )
