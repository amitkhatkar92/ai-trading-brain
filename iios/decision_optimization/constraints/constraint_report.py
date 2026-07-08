"""iios/decision_optimization/constraints/constraint_report.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from ..optimization_context import Candidate
from .constraint_checker import ConstraintCheckResult, OptimizationConstraint


@dataclass
class ConstraintReport:
    report_id:         str  = field(default_factory=lambda: str(uuid.uuid4()))
    total_candidates:  int  = 0
    total_constraints: int  = 0
    feasible_ids:      list[str] = field(default_factory=list)
    infeasible_ids:    list[str] = field(default_factory=list)
    violations:        list[ConstraintCheckResult] = field(default_factory=list)
    hard_violations:   int  = 0
    soft_violations:   int  = 0
    generated_at:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "report_id":         self.report_id,
            "total_candidates":  self.total_candidates,
            "total_constraints": self.total_constraints,
            "feasible_count":    len(self.feasible_ids),
            "infeasible_count":  len(self.infeasible_ids),
            "hard_violations":   self.hard_violations,
            "soft_violations":   self.soft_violations,
        }


def build_constraint_report(
    candidates:  list[Candidate],
    constraints: list[OptimizationConstraint],
    solve_results: dict[str, list[ConstraintCheckResult]],
) -> ConstraintReport:
    feasible:    list[str] = []
    infeasible:  list[str] = []
    violations:  list[ConstraintCheckResult] = []
    hard_count = 0
    soft_count = 0

    for cand in candidates:
        checks         = solve_results.get(cand.candidate_id, [])
        has_hard_fail  = any(not r.satisfied and r.is_hard  for r in checks)
        for r in checks:
            if not r.satisfied:
                violations.append(r)
                if r.is_hard:
                    hard_count += 1
                else:
                    soft_count += 1
        if has_hard_fail:
            infeasible.append(cand.candidate_id)
        else:
            feasible.append(cand.candidate_id)

    return ConstraintReport(
        total_candidates  = len(candidates),
        total_constraints = len(constraints),
        feasible_ids      = feasible,
        infeasible_ids    = infeasible,
        violations        = violations,
        hard_violations   = hard_count,
        soft_violations   = soft_count,
    )
