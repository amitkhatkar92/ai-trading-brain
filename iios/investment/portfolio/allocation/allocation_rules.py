"""iios/investment/portfolio/allocation/allocation_rules.py

Deterministic allocation adjustment rules applied post-weight-calculation.

Rules take the raw weight map (symbol → dollars) and return the same map,
possibly with small adjustments such as removing positions below the minimum
dollar threshold or capping over-sized positions.

All rules are pure (no external I/O, no market data lookups).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.allocation.allocation_plan import AllocationRequest

# Type alias: symbol → signed dollars (negative = short)
WeightMap = Dict[str, float]


@dataclass(frozen=True)
class AllocationRuleApplication:
    """Record of a single rule application."""

    rule_name:      str            = ""
    symbols_changed:List[str]      = field(default_factory=list)
    symbols_removed:List[str]      = field(default_factory=list)
    delta_max:      float          = 0.0   # Maximum absolute delta applied to any position
    notes:          List[str]      = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name":       self.rule_name,
            "symbols_changed": self.symbols_changed,
            "symbols_removed": self.symbols_removed,
            "delta_max":       round(self.delta_max, 2),
            "notes":           list(self.notes),
        }


class AllocationRule(abc.ABC):
    """Abstract base for deterministic allocation adjustment rules."""

    @property
    @abc.abstractmethod
    def rule_name(self) -> str: ...

    @abc.abstractmethod
    def apply(
        self,
        weights:  WeightMap,
        request:  AllocationRequest,
    ) -> AllocationRuleApplication:
        """
        Mutates *weights* in-place (caller passes a working copy).
        Returns a record of what changed.
        """


# ---------------------------------------------------------------------------
# Concrete rules
# ---------------------------------------------------------------------------

class MinPositionSizeRule(AllocationRule):
    """
    Remove positions whose absolute dollar value is below the minimum.
    Freed capital stays in cash (caller adjusts residual).
    """

    @property
    def rule_name(self) -> str:
        return "min_position_size"

    def apply(self, weights: WeightMap, request: AllocationRequest) -> AllocationRuleApplication:
        threshold = max(request.min_trade_size, 1.0)
        to_remove = [s for s, v in weights.items() if abs(v) < threshold]
        for sym in to_remove:
            del weights[sym]
        return AllocationRuleApplication(
            rule_name       = self.rule_name,
            symbols_removed = to_remove,
            notes           = [f"Removed {len(to_remove)} position(s) below ${threshold:.2f}"],
        )


class MaxPositionCapRule(AllocationRule):
    """
    Cap each position so it does not exceed max_position_weight × total_capital.
    Freed capital stays in cash.
    """

    @property
    def rule_name(self) -> str:
        return "max_position_cap"

    def apply(self, weights: WeightMap, request: AllocationRequest) -> AllocationRuleApplication:
        if request.total_capital <= 0:
            return AllocationRuleApplication(rule_name=self.rule_name)

        cap = request.max_position_weight * request.total_capital
        # Override with absolute cap if provided
        if request.max_position_dollars > 0:
            cap = min(cap, request.max_position_dollars)

        changed: List[str] = []
        delta_max: float   = 0.0

        for sym in list(weights):
            v    = weights[sym]
            sign = 1 if v >= 0 else -1
            if abs(v) > cap:
                delta  = abs(v) - cap
                if delta > delta_max:
                    delta_max = delta
                weights[sym] = sign * cap
                changed.append(sym)

        return AllocationRuleApplication(
            rule_name       = self.rule_name,
            symbols_changed = changed,
            delta_max       = delta_max,
            notes           = [f"Capped {len(changed)} position(s) at ${cap:.2f}"],
        )


class CashReserveRule(AllocationRule):
    """
    Ensure total invested capital does not exceed (1 − cash_reserve_pct) × total_capital.
    If over-allocated, scale all positions down proportionally.
    """

    @property
    def rule_name(self) -> str:
        return "cash_reserve"

    def apply(self, weights: WeightMap, request: AllocationRequest) -> AllocationRuleApplication:
        if request.total_capital <= 0 or not weights:
            return AllocationRuleApplication(rule_name=self.rule_name)

        max_investable = request.total_capital * (1.0 - request.cash_reserve_pct)
        total_abs      = sum(abs(v) for v in weights.values())

        if total_abs <= max_investable:
            return AllocationRuleApplication(
                rule_name = self.rule_name,
                notes     = ["Capital within cash reserve limits"],
            )

        scale          = max_investable / total_abs
        changed: List[str] = []
        delta_max: float   = 0.0

        for sym in list(weights):
            old = weights[sym]
            new = old * scale
            if abs(old - new) > 0.005:
                delta_max = max(delta_max, abs(old - new))
                weights[sym] = new
                changed.append(sym)

        return AllocationRuleApplication(
            rule_name       = self.rule_name,
            symbols_changed = changed,
            delta_max       = delta_max,
            notes           = [
                f"Scaled {len(changed)} positions by {scale:.4f} to maintain "
                f"{request.cash_reserve_pct:.1%} cash reserve"
            ],
        )


class NegativeLongBlockRule(AllocationRule):
    """
    Block LONG positions with negative dollar allocation (should not exist after blueprint
    weight conversion, but defensive guard).
    """

    @property
    def rule_name(self) -> str:
        return "negative_long_block"

    def apply(self, weights: WeightMap, request: AllocationRequest) -> AllocationRuleApplication:
        to_remove = [s for s, v in weights.items() if v < 0 and not request.allow_short]
        for sym in to_remove:
            del weights[sym]
        return AllocationRuleApplication(
            rule_name       = self.rule_name,
            symbols_removed = to_remove,
            notes           = [f"Blocked {len(to_remove)} negative allocation(s)"],
        )


# ---------------------------------------------------------------------------
# Default rule chain
# ---------------------------------------------------------------------------

def default_rule_chain() -> List[AllocationRule]:
    """Returns the standard ordered list of allocation rules."""
    return [
        NegativeLongBlockRule(),
        MaxPositionCapRule(),
        CashReserveRule(),
        MinPositionSizeRule(),
    ]
