"""iios/investment/portfolio/construction/security_selector.py

Selects eligible InvestmentRecommendations from an input list and ranks them
for weight assignment.

The selector is deterministic: given the same inputs and the same
SelectionPolicy, it always produces the same ordered output.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.construction.construction_types import (
    ConstructionDirection,
    SelectionCriterion,
)
from iios.investment.portfolio.construction.selection_filters import FilterChain, FilterResult
from iios.investment.portfolio.construction.selection_history import SelectionHistory, SelectionRecord
from iios.investment.portfolio.construction.selection_policy import SelectionPolicy, BALANCED_POLICY


# ---------------------------------------------------------------------------
# SelectionResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SelectionResult:
    """
    Output of SecuritySelector.select().

    selected      — ordered list (rank 1 first) ready for weight assignment.
    filter_result — full audit trail of which recs were excluded and why.
    record        — lightweight record stored in SelectionHistory.
    """

    selected:      Tuple[Any, ...]  = field(default_factory=tuple)
    filter_result: FilterResult     = field(default_factory=FilterResult)
    record:        SelectionRecord  = field(default_factory=SelectionRecord)
    duration_ms:   float            = 0.0

    @property
    def count(self) -> int:
        return len(self.selected)

    @property
    def symbols(self) -> Tuple[str, ...]:
        return tuple(r.symbol for r in self.selected)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count":         self.count,
            "symbols":       list(self.symbols),
            "filter_result": self.filter_result.to_dict(),
            "record":        self.record.to_dict(),
            "duration_ms":   round(self.duration_ms, 2),
        }


# ---------------------------------------------------------------------------
# SecuritySelector
# ---------------------------------------------------------------------------

class SecuritySelector:
    """
    Selects and ranks InvestmentRecommendations for portfolio construction.

    Steps (deterministic):
      1. Apply FilterChain — remove ineligible recommendations.
      2. Apply SelectionPolicy quality gates — remove below-threshold recs.
      3. Rank survivors by policy score (descending), then by symbol (tiebreaker).
      4. Truncate to max_long_holdings (longs) + max_short_holdings (shorts).
      5. Record to SelectionHistory.

    The selector never modifies recommendations — it only selects and orders.
    """

    def __init__(
        self,
        policy: Optional[SelectionPolicy] = None,
        filter_chain: Optional[FilterChain] = None,
        history: Optional[SelectionHistory] = None,
    ) -> None:
        self._policy       = policy or BALANCED_POLICY
        self._filter_chain = filter_chain or FilterChain.default()
        self._history      = history or SelectionHistory()

    # ------------------------------------------------------------------
    # Main public method
    # ------------------------------------------------------------------

    def select(
        self,
        recommendations: List[Any],
        request: Any,
        *,
        policy: Optional[SelectionPolicy] = None,
    ) -> SelectionResult:
        """
        Select and rank recommendations.

        Parameters
        ----------
        recommendations : list of InvestmentRecommendation
        request         : ConstructionRequest
        policy          : override the instance policy for this call

        Returns
        -------
        SelectionResult
        """
        t0 = time.monotonic()
        pol = policy or self._policy

        # Step 1 — Filter chain
        passed, filter_result = self._filter_chain.apply(recommendations, request)

        # Step 2 — Policy quality gates
        qualified: List[Any] = []
        gate_rejected: List[Any] = []
        for rec in passed:
            if pol.passes_quality_gates(rec):
                qualified.append(rec)
            else:
                gate_rejected.append(rec)

        # Step 3 — Rank (deterministic: score desc, symbol asc)
        scored = [(rec, pol.score(rec)) for rec in qualified]
        scored.sort(key=lambda t: (-t[1], t[0].symbol))

        # Step 4 — Split and truncate by direction
        longs  = [(r, s) for r, s in scored if r.is_long or r.direction == ConstructionDirection.NEUTRAL]
        shorts = [(r, s) for r, s in scored if r.is_short]

        max_long  = max(1, min(pol.max_long_holdings, request.max_holdings))
        max_short = pol.max_short_holdings if request.allow_short else 0

        selected_longs  = [r for r, _ in longs[:max_long]]
        selected_shorts = [r for r, _ in shorts[:max_short]]
        selected        = selected_longs + selected_shorts

        duration_ms = (time.monotonic() - t0) * 1000.0

        record = SelectionRecord(
            portfolio_id=request.portfolio_id,
            request_id=request.request_id,
            recommendations_in=len(recommendations),
            recommendations_out=len(selected),
            filters_applied=tuple(self._filter_chain.filter_names),
            rejected_count=filter_result.rejected_count + len(gate_rejected),
            selected_symbols=tuple(r.symbol for r in selected),
            policy_name=pol.policy_name,
            selection_criterion=pol.primary_criterion.value,
            duration_ms=duration_ms,
        )
        self._history.add(record)

        return SelectionResult(
            selected=tuple(selected),
            filter_result=filter_result,
            record=record,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def policy(self) -> SelectionPolicy:
        return self._policy

    @property
    def history(self) -> SelectionHistory:
        return self._history

    def set_policy(self, policy: SelectionPolicy) -> None:
        self._policy = policy

    def stats(self) -> Dict[str, Any]:
        return {
            "policy":          self._policy.to_dict(),
            "history_count":   self._history.count(),
            "avg_pass_rate":   round(self._history.avg_pass_rate(), 4),
            "filter_names":    self._filter_chain.filter_names,
        }
