"""iios/investment/portfolio/optimization/constraint_validator.py

Validates an OptimizationPlan against its constraint set.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.optimization.optimization_constraints import (
    ConstraintSeverity,
    ConstraintType,
    OptimizationConstraintSet,
)
from iios.investment.portfolio.optimization.optimization_plan import OptimizationPlan
from iios.investment.portfolio.optimization.optimization_types import (
    ConstraintOutcome,
    WEIGHT_SUM_TOLERANCE,
)


@dataclass(frozen=True)
class ConstraintCheck:
    """Result of validating one constraint against an optimization plan."""

    check_id:        str               = field(default_factory=lambda: str(uuid.uuid4()))
    constraint_id:   str               = ""
    constraint_name: str               = ""
    constraint_type: str               = ""
    outcome:         ConstraintOutcome = ConstraintOutcome.SATISFIED
    actual:          float             = 0.0
    bound:           float             = 0.0
    symbol:          str               = ""
    dimension_key:   str               = ""
    message:         str               = ""

    @property
    def passed(self) -> bool:
        return self.outcome == ConstraintOutcome.SATISFIED

    @property
    def is_violation(self) -> bool:
        return self.outcome == ConstraintOutcome.VIOLATED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id":        self.check_id,
            "constraint_id":   self.constraint_id,
            "constraint_name": self.constraint_name,
            "constraint_type": self.constraint_type,
            "outcome":         self.outcome.value,
            "actual":          round(self.actual, 6),
            "bound":           round(self.bound, 6),
            "symbol":          self.symbol,
            "dimension_key":   self.dimension_key,
            "message":         self.message,
        }


@dataclass(frozen=True)
class ConstraintValidationReport:
    """Summary of all constraint checks on an OptimizationPlan."""

    report_id:    str                       = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id:      str                       = ""
    portfolio_id: str                       = ""
    checks:       Tuple[ConstraintCheck, ...] = field(default_factory=tuple)
    total:        int                       = 0
    satisfied:    int                       = 0
    warnings:     int                       = 0
    violations:   int                       = 0
    is_feasible:  bool                      = True
    validated_at: float                     = field(default_factory=time.time)

    @property
    def satisfaction_rate(self) -> float:
        return self.satisfied / self.total if self.total else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":         self.report_id,
            "plan_id":           self.plan_id,
            "portfolio_id":      self.portfolio_id,
            "total":             self.total,
            "satisfied":         self.satisfied,
            "warnings":          self.warnings,
            "violations":        self.violations,
            "is_feasible":       self.is_feasible,
            "satisfaction_rate": round(self.satisfaction_rate, 4),
            "validated_at":      self.validated_at,
            "checks":            [c.to_dict() for c in self.checks],
        }


class ConstraintValidator:
    """Validates an OptimizationPlan against its constraint set."""

    def validate(
        self,
        plan:        OptimizationPlan,
        constraints: OptimizationConstraintSet,
    ) -> ConstraintValidationReport:
        checks: List[ConstraintCheck] = []
        weights = {p.symbol: p.optimized_weight for p in plan.positions}

        for c in constraints.active:
            ct = c.constraint_type

            # -- Budget: weights sum ≈ 1 ---
            if ct == ConstraintType.BUDGET:
                total = sum(weights.values())
                delta = abs(total - 1.0)
                ok    = delta <= WEIGHT_SUM_TOLERANCE
                checks.append(ConstraintCheck(
                    constraint_id   = c.constraint_id,
                    constraint_name = c.name,
                    constraint_type = ct.value,
                    outcome         = ConstraintOutcome.SATISFIED if ok else ConstraintOutcome.VIOLATED,
                    actual          = total,
                    bound           = 1.0,
                    message         = f"Weight sum {total:.6f} {'ok' if ok else 'VIOLATED'}",
                ))

            # -- Position weight ---
            elif ct == ConstraintType.POSITION_WEIGHT:
                lo = c.lower_bound if c.lower_bound is not None else 0.0
                hi = c.upper_bound if c.upper_bound is not None else 1.0
                for sym, w in weights.items():
                    if w < lo - 1e-8 or w > hi + 1e-8:
                        outcome = (ConstraintOutcome.WARNING
                                   if c.severity == ConstraintSeverity.SOFT
                                   else ConstraintOutcome.VIOLATED)
                        checks.append(ConstraintCheck(
                            constraint_id   = c.constraint_id,
                            constraint_name = c.name,
                            constraint_type = ct.value,
                            outcome         = outcome,
                            actual          = w,
                            bound           = hi,
                            symbol          = sym,
                            message         = f"{sym} weight {w:.4%} outside [{lo:.2%}, {hi:.2%}]",
                        ))
                    else:
                        checks.append(ConstraintCheck(
                            constraint_id   = c.constraint_id,
                            constraint_name = c.name,
                            constraint_type = ct.value,
                            outcome         = ConstraintOutcome.SATISFIED,
                            actual          = w,
                            bound           = hi,
                            symbol          = sym,
                            message         = f"{sym} weight {w:.4%} ok",
                        ))

            # -- Sector ---
            elif ct == ConstraintType.SECTOR:
                key   = c.dimension_key
                hi    = c.upper_bound if c.upper_bound is not None else 1.0
                sec_w = plan.sector_weights.get(key, 0.0)
                ok    = sec_w <= hi + 1e-6
                checks.append(ConstraintCheck(
                    constraint_id   = c.constraint_id,
                    constraint_name = c.name,
                    constraint_type = ct.value,
                    outcome         = ConstraintOutcome.SATISFIED if ok else ConstraintOutcome.VIOLATED,
                    actual          = sec_w,
                    bound           = hi,
                    dimension_key   = key,
                    message         = f"Sector {key}: {sec_w:.1%} vs {hi:.1%} limit",
                ))

            # -- Leverage ---
            elif ct == ConstraintType.LEVERAGE:
                gross = sum(abs(v) for v in weights.values())
                hi    = c.upper_bound if c.upper_bound is not None else 1.0
                ok    = gross <= hi + 1e-6
                checks.append(ConstraintCheck(
                    constraint_id   = c.constraint_id,
                    constraint_name = c.name,
                    constraint_type = ct.value,
                    outcome         = ConstraintOutcome.SATISFIED if ok else ConstraintOutcome.VIOLATED,
                    actual          = gross,
                    bound           = hi,
                    message         = f"Gross leverage {gross:.2f}× vs {hi:.2f}× limit",
                ))

        total      = len(checks)
        satisfied  = sum(1 for c in checks if c.passed)
        warnings   = sum(1 for c in checks if c.outcome == ConstraintOutcome.WARNING)
        violations = sum(1 for c in checks if c.is_violation)

        return ConstraintValidationReport(
            plan_id      = plan.plan_id,
            portfolio_id = plan.portfolio_id,
            checks       = tuple(checks),
            total        = total,
            satisfied    = satisfied,
            warnings     = warnings,
            violations   = violations,
            is_feasible  = violations == 0,
        )
