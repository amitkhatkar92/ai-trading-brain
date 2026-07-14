"""iios/investment/portfolio/optimization/optimization_constraints.py

Constraint definitions for portfolio optimization.
Constraints describe what weights are valid — the solver enforces them.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Tuple


class ConstraintType(str, Enum):
    """Category of an optimization constraint."""

    BUDGET          = "budget"            # Weights sum to 1 (or ≤ max_leverage)
    POSITION_WEIGHT = "position_weight"   # Min/max weight per position
    SECTOR          = "sector"            # Max sector concentration
    INDUSTRY        = "industry"          # Max industry concentration
    ASSET_CLASS     = "asset_class"       # Max asset-class concentration
    COUNTRY         = "country"           # Max country concentration
    CURRENCY        = "currency"          # Max currency exposure
    LEVERAGE        = "leverage"          # Max gross leverage
    TURNOVER        = "turnover"          # Max total weight change vs prior
    LIQUIDITY       = "liquidity"         # Min position dollar size
    ESG             = "esg"               # ESG score floors
    CUSTOM          = "custom"            # Pluggable institutional constraint

    # These are soft (advisory) by default
    LONG_ONLY       = "long_only"         # All weights ≥ 0
    MAX_POSITIONS   = "max_positions"     # Cap on number of active positions


class ConstraintSeverity(str, Enum):
    HARD = "hard"   # Must not be violated — optimizer rejects the plan
    SOFT = "soft"   # Advisory — logged but plan proceeds


@dataclass(frozen=True)
class OptimizationConstraint:
    """
    A single portfolio constraint.
    The constraint is active if `enabled` is True.
    """

    constraint_id:   str               = field(default_factory=lambda: str(uuid.uuid4()))
    name:            str               = ""
    constraint_type: ConstraintType    = ConstraintType.CUSTOM
    severity:        ConstraintSeverity= ConstraintSeverity.HARD
    enabled:         bool              = True

    # Numeric bounds (semantic depends on constraint_type)
    lower_bound:     Optional[float]   = None
    upper_bound:     Optional[float]   = None

    # Dimension key for sector/industry/country/currency constraints
    dimension_key:   str               = ""   # e.g. "technology", "INR"

    # Symbol-specific (for per-symbol weight constraints)
    symbol:          str               = ""

    description:     str               = ""
    metadata:        Dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_id":  self.constraint_id,
            "name":           self.name,
            "type":           self.constraint_type.value,
            "severity":       self.severity.value,
            "enabled":        self.enabled,
            "lower_bound":    self.lower_bound,
            "upper_bound":    self.upper_bound,
            "dimension_key":  self.dimension_key,
            "symbol":         self.symbol,
            "description":    self.description,
        }


# ---------------------------------------------------------------------------
# OptimizationConstraintSet — the full set of constraints for one run
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OptimizationConstraintSet:
    """Immutable set of constraints for one optimization run."""

    constraint_set_id:  str                              = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str                              = ""
    constraints:        Tuple[OptimizationConstraint, ...]= field(default_factory=tuple)
    description:        str                              = ""

    @property
    def active(self) -> Tuple[OptimizationConstraint, ...]:
        return tuple(c for c in self.constraints if c.enabled)

    @property
    def hard_constraints(self) -> Tuple[OptimizationConstraint, ...]:
        return tuple(c for c in self.active if c.severity == ConstraintSeverity.HARD)

    @property
    def soft_constraints(self) -> Tuple[OptimizationConstraint, ...]:
        return tuple(c for c in self.active if c.severity == ConstraintSeverity.SOFT)

    def by_type(self, ct: ConstraintType) -> Tuple[OptimizationConstraint, ...]:
        return tuple(c for c in self.active if c.constraint_type == ct)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_set_id": self.constraint_set_id,
            "portfolio_id":      self.portfolio_id,
            "total":             len(self.constraints),
            "active":            len(self.active),
            "hard":              len(self.hard_constraints),
            "soft":              len(self.soft_constraints),
            "constraints":       [c.to_dict() for c in self.constraints],
        }


# ---------------------------------------------------------------------------
# Constraint factory helpers
# ---------------------------------------------------------------------------

def budget_constraint(long_only: bool = True) -> OptimizationConstraint:
    return OptimizationConstraint(
        name            = "budget",
        constraint_type = ConstraintType.BUDGET,
        severity        = ConstraintSeverity.HARD,
        lower_bound     = 0.0 if long_only else -1.0,
        upper_bound     = 1.0,
        description     = "Weights must sum to 1 (long-only)" if long_only else "Gross leverage ≤ 100%",
    )


def position_weight_constraint(min_w: float, max_w: float) -> OptimizationConstraint:
    return OptimizationConstraint(
        name            = "position_weight",
        constraint_type = ConstraintType.POSITION_WEIGHT,
        severity        = ConstraintSeverity.HARD,
        lower_bound     = min_w,
        upper_bound     = max_w,
        description     = f"Each position: {min_w:.2%} ≤ w ≤ {max_w:.2%}",
    )


def sector_constraint(sector: str, max_weight: float) -> OptimizationConstraint:
    return OptimizationConstraint(
        name            = f"sector_{sector}",
        constraint_type = ConstraintType.SECTOR,
        severity        = ConstraintSeverity.HARD,
        upper_bound     = max_weight,
        dimension_key   = sector,
        description     = f"Sector '{sector}' ≤ {max_weight:.1%}",
    )


def leverage_constraint(max_leverage: float = 1.0) -> OptimizationConstraint:
    return OptimizationConstraint(
        name            = "leverage",
        constraint_type = ConstraintType.LEVERAGE,
        severity        = ConstraintSeverity.HARD,
        upper_bound     = max_leverage,
        description     = f"Gross leverage ≤ {max_leverage:.1f}×",
    )


def turnover_constraint(max_turnover: float) -> OptimizationConstraint:
    return OptimizationConstraint(
        name            = "turnover",
        constraint_type = ConstraintType.TURNOVER,
        severity        = ConstraintSeverity.SOFT,
        upper_bound     = max_turnover,
        description     = f"Total turnover ≤ {max_turnover:.1%}",
    )


def default_constraint_set(
    portfolio_id:    str   = "",
    min_weight:      float = 0.0,
    max_weight:      float = 0.25,
    max_sector:      float = 0.40,
    max_leverage:    float = 1.0,
    long_only:       bool  = True,
) -> OptimizationConstraintSet:
    """Returns a standard institutional constraint set."""
    return OptimizationConstraintSet(
        portfolio_id = portfolio_id,
        constraints  = (
            budget_constraint(long_only=long_only),
            position_weight_constraint(min_weight, max_weight),
            leverage_constraint(max_leverage),
        ),
    )
