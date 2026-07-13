"""iios/investment/strategy/portfolio/allocation_engine.py
AllocationEngine — selects eligible strategies and produces allocations.
Bridges WeightOptimizer with ConstructionConstraints and eligibility checks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_allocation import (
    StrategyAllocation, AllocationMethod, AllocationStatus
)
from iios.investment.strategy.portfolio.construction_constraints import ConstructionConstraints
from iios.investment.strategy.portfolio.weight_optimizer import WeightOptimizer


@dataclass(frozen=True)
class AllocationResult:
    """Output of AllocationEngine.allocate()."""
    allocations:    Dict[str, StrategyAllocation]
    rejected_ids:   List[str]
    method:         str
    strategy_count: int
    total_weight:   float
    warnings:       List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return abs(self.total_weight - 1.0) < 1e-6 and self.strategy_count > 0


class AllocationEngine:
    """
    Selects strategies that pass eligibility checks, then delegates to
    WeightOptimizer to produce target weights.
    """

    def __init__(
        self,
        optimizer: Optional[WeightOptimizer] = None,
    ) -> None:
        self._optimizer = optimizer or WeightOptimizer()

    def allocate(
        self,
        strategies:  List[PortfolioStrategy],
        method:      AllocationMethod,
        constraints: ConstructionConstraints,
    ) -> AllocationResult:
        """
        Filter strategies by eligibility, compute weights, return allocations.
        """
        eligible, rejected_ids, warnings = self._filter(strategies, constraints)

        if len(eligible) < constraints.min_strategies:
            warnings.append(
                f"Only {len(eligible)} eligible strategies < min {constraints.min_strategies}"
            )

        # Trim to max_strategies (take top N by risk_adjusted_score)
        if len(eligible) > constraints.max_strategies:
            eligible.sort(key=lambda s: s.risk_adjusted_score, reverse=True)
            rejected_ids += [s.strategy_id for s in eligible[constraints.max_strategies:]]
            eligible = eligible[: constraints.max_strategies]
            warnings.append(
                f"Trimmed to max {constraints.max_strategies} strategies by risk-adjusted score"
            )

        if not eligible:
            return AllocationResult(
                allocations={},
                rejected_ids=rejected_ids,
                method=method.value,
                strategy_count=0,
                total_weight=0.0,
                warnings=warnings,
            )

        target_weights = self._optimizer.compute(eligible, method, constraints)

        now = datetime.now(timezone.utc)
        allocations: Dict[str, StrategyAllocation] = {}
        for s in eligible:
            w = target_weights.get(s.strategy_id, 0.0)
            allocations[s.strategy_id] = StrategyAllocation(
                strategy_id=s.strategy_id,
                strategy_name=s.strategy_name,
                weight=w,
                target_weight=w,
                status=AllocationStatus.ACTIVE,
                allocation_method=method,
                evaluation_score=s.evaluation_score,
                added_at=now,
                updated_at=now,
            )

        total_weight = sum(a.weight for a in allocations.values())
        return AllocationResult(
            allocations=allocations,
            rejected_ids=rejected_ids,
            method=method.value,
            strategy_count=len(allocations),
            total_weight=round(total_weight, 8),
            warnings=warnings,
        )

    def _filter(
        self,
        strategies:  List[PortfolioStrategy],
        constraints: ConstructionConstraints,
    ) -> Tuple[List[PortfolioStrategy], List[str], List[str]]:
        eligible:    List[PortfolioStrategy] = []
        rejected:    List[str] = []
        warnings:    List[str] = []

        for s in strategies:
            if not s.is_eligible:
                rejected.append(s.strategy_id)
                continue
            if constraints.require_approved and s.approval_status != "approved":
                rejected.append(s.strategy_id)
                continue
            if s.evaluation_score < constraints.min_eval_score:
                rejected.append(s.strategy_id)
                continue
            eligible.append(s)

        return eligible, rejected, warnings
