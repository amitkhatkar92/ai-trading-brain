"""
portfolio_solution.py — iios.portfolio.optimization
=====================================================
AllocationPlan, RebalancingPlan, PortfolioSolution, and
PortfolioOptimizationSummary value objects.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import AllocationCapability, RebalancingCapability, VERSION


# ---------------------------------------------------------------------------
# AllocationPlan
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AllocationPlan:
    """
    Immutable allocation plan for a portfolio candidate.

    Fields
    ------
    plan_id :          Unique identifier.
    candidate_id :     Candidate this plan belongs to.
    portfolio_id :     Portfolio identifier.
    allocation_type :  AllocationCapability enum value.
    allocations :      Dict mapping asset/sector/strategy → weight (0–1) or amount.
    total :            Sum of allocation values.
    generated_at :     Wall-clock generation timestamp.
    metadata :         Supplementary data.
    framework_version: Framework version string.
    """
    plan_id:           str
    candidate_id:      str
    portfolio_id:      str
    allocation_type:   AllocationCapability
    allocations:       Dict[str, float]
    total:             float
    generated_at:      float
    metadata:          Dict[str, Any]
    framework_version: str = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id":          self.plan_id,
            "candidate_id":     self.candidate_id,
            "portfolio_id":     self.portfolio_id,
            "allocation_type":  self.allocation_type.value,
            "allocations":      dict(self.allocations),
            "total":            self.total,
            "asset_count":      len(self.allocations),
            "generated_at":     self.generated_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# RebalancingPlan
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RebalancingPlan:
    """
    Immutable rebalancing plan for a portfolio candidate.

    Fields
    ------
    plan_id :           Unique identifier.
    candidate_id :      Candidate this plan belongs to.
    portfolio_id :      Portfolio identifier.
    rebalancing_type :  RebalancingCapability enum value.
    actions :           List of rebalancing action dicts.
    trigger :           Human-readable trigger description.
    generated_at :      Wall-clock generation timestamp.
    metadata :          Supplementary data.
    framework_version : Framework version string.
    """
    plan_id:            str
    candidate_id:       str
    portfolio_id:       str
    rebalancing_type:   RebalancingCapability
    actions:            tuple   # Tuple[Dict, ...]
    trigger:            str
    generated_at:       float
    metadata:           Dict[str, Any]
    framework_version:  str = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id":           self.plan_id,
            "candidate_id":      self.candidate_id,
            "portfolio_id":      self.portfolio_id,
            "rebalancing_type":  self.rebalancing_type.value,
            "actions":           list(self.actions),
            "action_count":      len(self.actions),
            "trigger":           self.trigger,
            "generated_at":      self.generated_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# PortfolioSolution (mutable — rank & is_selected set post-construction)
# ---------------------------------------------------------------------------

@dataclass
class PortfolioSolution:
    """
    Mutable optimization solution for one portfolio candidate.

    ``rank`` and ``is_selected`` are set by the ranking and selection
    engines after the initial solution is constructed.
    """
    solution_id:           str
    optimization_id:       str
    candidate_id:          str
    portfolio_id:          str
    strategy_name:         str
    objectives_evaluated:  int
    constraints_satisfied: int
    constraints_violated:  int
    allocation_plan:       Optional[AllocationPlan]
    rebalancing_plan:      Optional[RebalancingPlan]
    score:                 float   # 0.0 to 1.0
    is_feasible:           bool
    reason:                str
    constraint_violations: List[str]
    objective_scores:      Dict[str, float]
    evaluated_at:          float
    framework_version:     str = VERSION
    rank:                  int  = 0
    is_selected:           bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "solution_id":          self.solution_id,
            "optimization_id":      self.optimization_id,
            "candidate_id":         self.candidate_id,
            "portfolio_id":         self.portfolio_id,
            "strategy_name":        self.strategy_name,
            "objectives_evaluated": self.objectives_evaluated,
            "constraints_satisfied": self.constraints_satisfied,
            "constraints_violated":  self.constraints_violated,
            "score":                self.score,
            "rank":                 self.rank,
            "is_feasible":          self.is_feasible,
            "is_selected":          self.is_selected,
            "reason":               self.reason,
            "allocation_plan":      self.allocation_plan.to_dict() if self.allocation_plan else None,
            "rebalancing_plan":     self.rebalancing_plan.to_dict() if self.rebalancing_plan else None,
            "objective_scores":     dict(self.objective_scores),
            "constraint_violations": list(self.constraint_violations),
            "evaluated_at":         self.evaluated_at,
            "framework_version":    self.framework_version,
        }


# ---------------------------------------------------------------------------
# PortfolioOptimizationSummary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioOptimizationSummary:
    """
    Compact, counts-based summary of an optimization run.
    """
    optimization_id:         str
    portfolio_id:            str
    strategy_name:           str
    total_candidates:        int
    feasible_candidates:     int
    infeasible_candidates:   int
    selected_candidate_id:   str
    selected_solution_id:    str
    best_score:              float
    avg_score:               float
    objectives_evaluated:    int
    constraints_evaluated:   int
    constraints_violated:    int
    elapsed_s:               float
    evaluated_at:            float
    framework_version:       str = VERSION

    @property
    def has_selection(self) -> bool:
        return bool(self.selected_candidate_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "optimization_id":         self.optimization_id,
            "portfolio_id":            self.portfolio_id,
            "strategy_name":           self.strategy_name,
            "total_candidates":        self.total_candidates,
            "feasible_candidates":     self.feasible_candidates,
            "infeasible_candidates":   self.infeasible_candidates,
            "selected_candidate_id":   self.selected_candidate_id,
            "selected_solution_id":    self.selected_solution_id,
            "best_score":              self.best_score,
            "avg_score":               self.avg_score,
            "objectives_evaluated":    self.objectives_evaluated,
            "constraints_evaluated":   self.constraints_evaluated,
            "constraints_violated":    self.constraints_violated,
            "elapsed_s":               self.elapsed_s,
            "evaluated_at":            self.evaluated_at,
            "framework_version":       self.framework_version,
        }
