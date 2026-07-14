"""iios/investment/portfolio/optimization/constraint_solver.py

Enforces OptimizationConstraintSet on raw optimized weights.
Returns a corrected weight map and a list of adjustments made.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.optimization.optimization_constraints import (
    ConstraintSeverity,
    ConstraintType,
    OptimizationConstraint,
    OptimizationConstraintSet,
)
from iios.investment.portfolio.optimization.optimization_engine import AssetProxy
from iios.investment.portfolio.optimization.optimization_types import ConstraintOutcome


WeightMap = Dict[str, float]


@dataclass(frozen=True)
class ConstraintAdjustment:
    """Record of one constraint enforcement action."""

    adjustment_id: str            = field(default_factory=lambda: str(uuid.uuid4()))
    constraint_id: str            = ""
    constraint_type: str          = ""
    symbol:        str            = ""
    dimension_key: str            = ""
    action:        str            = ""      # "clamp", "scale", "redistribute"
    before:        float          = 0.0
    after:         float          = 0.0
    delta:         float          = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_id":   self.constraint_id,
            "constraint_type": self.constraint_type,
            "symbol":          self.symbol,
            "action":          self.action,
            "before":          round(self.before, 6),
            "after":           round(self.after, 6),
            "delta":           round(self.delta, 6),
        }


@dataclass(frozen=True)
class ConstraintSolution:
    """Result of applying all constraints to a weight map."""

    solution_id:      str                          = field(default_factory=lambda: str(uuid.uuid4()))
    weights:          Dict[str, float]             = field(default_factory=dict)
    adjustments:      Tuple[ConstraintAdjustment, ...] = field(default_factory=tuple)
    hard_satisfied:   bool                         = True
    violations:       Tuple[str, ...]              = field(default_factory=tuple)
    warnings:         Tuple[str, ...]              = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "solution_id":    self.solution_id,
            "hard_satisfied": self.hard_satisfied,
            "violations":     list(self.violations),
            "warnings":       list(self.warnings),
            "adjustments":    len(self.adjustments),
        }


class ConstraintSolver:
    """
    Applies OptimizationConstraintSet to a raw weight map.
    Constraints are applied in order of severity (HARD first).
    The solver is deterministic and stateless.
    """

    def solve(
        self,
        weights:   WeightMap,
        assets:    List[AssetProxy],
        constraints: OptimizationConstraintSet,
        request_min_weight: float = 0.0,
        request_max_weight: float = 0.25,
    ) -> ConstraintSolution:
        w           = dict(weights)
        adjustments: List[ConstraintAdjustment] = []
        violations:  List[str] = []
        warnings:    List[str] = []

        asset_map: Dict[str, AssetProxy] = {a.symbol: a for a in assets}

        # --- HARD constraints first ---
        for c in list(constraints.hard_constraints) + list(constraints.soft_constraints):
            if not c.enabled:
                continue
            ct = c.constraint_type

            # 1. Position weight limits
            if ct == ConstraintType.POSITION_WEIGHT:
                lo = c.lower_bound if c.lower_bound is not None else request_min_weight
                hi = c.upper_bound if c.upper_bound is not None else request_max_weight
                for sym in list(w):
                    old = w[sym]
                    new = max(lo, min(hi, old))
                    if abs(new - old) > 1e-9:
                        adjustments.append(ConstraintAdjustment(
                            constraint_id   = c.constraint_id,
                            constraint_type = ct.value,
                            symbol          = sym,
                            action          = "clamp",
                            before          = old,
                            after           = new,
                            delta           = new - old,
                        ))
                        w[sym] = new

            # 2. Budget (normalize to sum=1)
            elif ct == ConstraintType.BUDGET:
                total = sum(w.values())
                if total > 0 and abs(total - 1.0) > 1e-6:
                    for sym in w:
                        w[sym] /= total

            # 3. Sector limits
            elif ct == ConstraintType.SECTOR:
                key    = c.dimension_key
                hi     = c.upper_bound if c.upper_bound is not None else 1.0
                syms_in_sector = [
                    s for s, a in asset_map.items()
                    if a.sector == key and s in w
                ]
                sector_w = sum(w[s] for s in syms_in_sector)
                if sector_w > hi and syms_in_sector:
                    scale = hi / sector_w
                    for sym in syms_in_sector:
                        old    = w[sym]
                        w[sym] = old * scale
                        adjustments.append(ConstraintAdjustment(
                            constraint_id   = c.constraint_id,
                            constraint_type = ct.value,
                            symbol          = sym,
                            dimension_key   = key,
                            action          = "scale",
                            before          = old,
                            after           = w[sym],
                            delta           = w[sym] - old,
                        ))

            # 4. Leverage
            elif ct == ConstraintType.LEVERAGE:
                hi    = c.upper_bound if c.upper_bound is not None else 1.0
                gross = sum(abs(v) for v in w.values())
                if gross > hi:
                    scale = hi / gross
                    for sym in w:
                        w[sym] *= scale

            # 5. Turnover (soft warning only)
            elif ct == ConstraintType.TURNOVER:
                prior_w = {a.symbol: a.prior_weight for a in assets}
                turnover = sum(abs(w.get(s, 0.0) - prior_w.get(s, 0.0)) for s in w)
                hi       = c.upper_bound if c.upper_bound is not None else 1.0
                if turnover > hi:
                    msg = f"Turnover {turnover:.1%} exceeds {hi:.1%} limit"
                    if c.severity == ConstraintSeverity.HARD:
                        violations.append(msg)
                    else:
                        warnings.append(msg)

            # 6. Long only
            elif ct == ConstraintType.LONG_ONLY:
                for sym in list(w):
                    if w[sym] < 0:
                        w[sym] = 0.0

        # Final renormalization
        total = sum(w.values())
        if total > 0:
            w = {sym: v / total for sym, v in w.items()}

        hard_ok = len(violations) == 0
        return ConstraintSolution(
            weights        = w,
            adjustments    = tuple(adjustments),
            hard_satisfied = hard_ok,
            violations     = tuple(violations),
            warnings       = tuple(warnings),
        )
