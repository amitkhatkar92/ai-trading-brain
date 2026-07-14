"""iios/investment/portfolio/allocation/cash_manager.py

Computes the residual cash position after position allocations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.allocation.allocation_plan import AllocationRequest, CashAllocation


@dataclass(frozen=True)
class CashPosition:
    """
    Cash breakdown for an allocation plan.
    Amounts are in the plan's currency.
    """

    cash_capital:      float  = 0.0   # Total residual cash
    cash_pct:          float  = 0.0   # cash / total_capital
    reserve_capital:   float  = 0.0   # Mandatory cash reserve (min_cash_reserve_pct × total)
    reserve_pct:       float  = 0.0   # reserve / total_capital
    deployable_capital:float  = 0.0   # cash_capital - reserve_capital (free cash)
    deployable_pct:    float  = 0.0   # deployable / total_capital
    is_above_minimum:  bool   = False  # cash ≥ reserve
    is_within_maximum: bool   = True   # cash ≤ max_cash_pct
    excess_cash:       float  = 0.0   # cash_capital - reserve_capital when positive
    shortfall:         float  = 0.0   # reserve - cash when reserve > cash
    currency:          str    = "INR"
    notes:             Tuple[str, ...] = field(default_factory=tuple)

    def to_cash_allocation(self) -> CashAllocation:
        return CashAllocation(
            cash_capital    = self.cash_capital,
            cash_weight     = self.cash_pct,
            reserve_capital = self.reserve_capital,
            reserve_weight  = self.reserve_pct,
            free_cash       = self.deployable_capital,
            currency        = self.currency,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cash_capital":       round(self.cash_capital, 2),
            "cash_pct":           round(self.cash_pct, 6),
            "reserve_capital":    round(self.reserve_capital, 2),
            "reserve_pct":        round(self.reserve_pct, 6),
            "deployable_capital": round(self.deployable_capital, 2),
            "deployable_pct":     round(self.deployable_pct, 6),
            "is_above_minimum":   self.is_above_minimum,
            "is_within_maximum":  self.is_within_maximum,
            "excess_cash":        round(self.excess_cash, 2),
            "shortfall":          round(self.shortfall, 2),
            "currency":           self.currency,
            "notes":              list(self.notes),
        }


class CashManager:
    """
    Computes the cash position that remains after allocating to positions.
    No external data required — purely arithmetic.
    """

    MAX_CASH_DEFAULT: float = 0.40   # If no policy override, warn above 40%

    def compute(
        self,
        total_capital:     float,
        invested_capital:  float,        # Sum of absolute position allocations
        request:           AllocationRequest,
        max_cash_pct:      Optional[float] = None,
    ) -> CashPosition:
        """
        Parameters
        ----------
        total_capital:
            Total investable capital in the plan.
        invested_capital:
            Sum of absolute dollar amounts across all position allocations.
        request:
            The AllocationRequest driving this run (provides cash_reserve_pct).
        max_cash_pct:
            Optional upper bound for cash.  Defaults to 40%.
        """
        notes:    List[str] = []
        max_cash  = max_cash_pct if max_cash_pct is not None else self.MAX_CASH_DEFAULT

        cash = max(0.0, total_capital - invested_capital)
        cash_pct = cash / total_capital if total_capital > 0 else 0.0

        reserve         = total_capital * request.cash_reserve_pct
        reserve_pct     = request.cash_reserve_pct
        deployable      = max(0.0, cash - reserve)
        deployable_pct  = deployable / total_capital if total_capital > 0 else 0.0
        is_above_min    = cash >= reserve
        is_within_max   = cash_pct <= max_cash
        excess          = max(0.0, cash - reserve)
        shortfall       = max(0.0, reserve - cash)

        if not is_above_min:
            notes.append(
                f"Cash ${cash:.2f} below required reserve ${reserve:.2f} "
                f"(shortfall ${shortfall:.2f})"
            )
        if not is_within_max:
            notes.append(
                f"Cash {cash_pct:.1%} exceeds max_cash_pct {max_cash:.1%}"
            )

        return CashPosition(
            cash_capital       = round(cash, 2),
            cash_pct           = cash_pct,
            reserve_capital    = round(reserve, 2),
            reserve_pct        = reserve_pct,
            deployable_capital = round(deployable, 2),
            deployable_pct     = deployable_pct,
            is_above_minimum   = is_above_min,
            is_within_maximum  = is_within_max,
            excess_cash        = round(excess, 2),
            shortfall          = round(shortfall, 2),
            currency           = request.currency,
            notes              = tuple(notes),
        )
