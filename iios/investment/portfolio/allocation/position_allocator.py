"""iios/investment/portfolio/allocation/position_allocator.py

Converts a PortfolioBlueprint + AllocationRequest into a Tuple of PositionAllocation.

The conversion is DETERMINISTIC: same blueprint + same request → same allocations.
No market data. No external I/O. No randomness.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.allocation.allocation_plan import (
    AllocationRequest,
    PositionAllocation,
)
from iios.investment.portfolio.allocation.allocation_rules import (
    AllocationRule,
    WeightMap,
    default_rule_chain,
)
from iios.investment.portfolio.allocation.allocation_types import AllocationDirection, AllocationMethod


class PositionAllocator:
    """
    Allocates total_capital across portfolio blueprint slots.

    Supported methods:
        BLUEPRINT_WEIGHT — Use blueprint.target_weight × total_capital directly.
        EQUAL            — Equal dollars across all slots.
        CONVICTION       — Proportional to slot.conviction.
        CONFIDENCE       — Proportional to slot.confidence.
        RISK_ADJUSTED    — confidence × (1 − risk_score).
        COMPOSITE        — Weighted blend: 0.4×conviction + 0.4×confidence + 0.2×risk-adj.

    In every case the following limit chain is applied after raw weight calculation:
        NegativeLongBlock → MaxPositionCap → CashReserve → MinPositionSize
    """

    def __init__(self, rules: Optional[List[AllocationRule]] = None) -> None:
        self._rules = rules if rules is not None else default_rule_chain()

    def allocate(
        self,
        blueprint:  Any,                  # PortfolioBlueprint (duck-typed to avoid circular import)
        request:    AllocationRequest,
    ) -> Tuple[PositionAllocation, ...]:
        """
        Main entry point.  Returns an immutable tuple of PositionAllocation.
        """
        slots = list(getattr(blueprint, "slots", []))
        if not slots:
            return ()

        # --- Filter excluded / non-allowed symbols ----------------------
        if request.symbols_excluded:
            slots = [s for s in slots if s.symbol not in request.symbols_excluded]
        if request.symbols_allowed:
            slots = [s for s in slots if s.symbol in request.symbols_allowed]

        # --- Compute raw dollar weights ---------------------------------
        raw: WeightMap = self._compute_raw_weights(slots, request)

        # --- Apply rule chain (mutates raw in-place) --------------------
        for rule in self._rules:
            rule.apply(raw, request)

        if not raw:
            return ()

        # --- Build PositionAllocation objects ---------------------------
        total = request.total_capital
        results: List[PositionAllocation] = []
        slot_map = {s.symbol: s for s in slots}

        for rank, (symbol, capital) in enumerate(
            sorted(raw.items(), key=lambda kv: abs(kv[1]), reverse=True), start=1
        ):
            slot = slot_map.get(symbol)
            if slot is None:
                continue

            direction = (
                AllocationDirection.SHORT
                if capital < 0
                else AllocationDirection.LONG
            )

            # Blueprint weight (signed fraction in the blueprint)
            blueprint_weight = float(getattr(slot, "target_weight", 0.0))
            allocated_weight = capital / total if total > 0 else 0.0
            weight_delta     = allocated_weight - abs(blueprint_weight)

            max_cap = request.max_position_weight * total
            if request.max_position_dollars > 0:
                max_cap = min(max_cap, request.max_position_dollars)
            min_cap = max(request.min_trade_size, request.min_position_weight * total)

            results.append(PositionAllocation(
                symbol             = symbol,
                name               = str(getattr(slot, "name", symbol)),
                direction          = direction,
                blueprint_weight   = blueprint_weight,
                allocated_weight   = allocated_weight,
                weight_delta       = weight_delta,
                allocated_capital  = round(capital, 2),
                min_capital        = round(min_cap, 2),
                max_capital        = round(max_cap, 2),
                sector             = str(getattr(slot, "sector", "unknown")),
                industry           = str(getattr(slot, "industry", "unknown")),
                asset_class        = str(getattr(getattr(slot, "asset_class", None), "value", getattr(slot, "asset_class", "equity"))),
                blueprint_slot_id  = str(getattr(slot, "slot_id", "")),
                recommendation_id  = str(getattr(slot, "recommendation_id", "")),
                source_decision_id = str(getattr(slot, "source_decision_id", "")),
                conviction         = float(getattr(slot, "conviction", 0.5)),
                confidence         = float(getattr(slot, "confidence", 0.5)),
                risk_score         = float(getattr(slot, "risk_score", 0.5)),
                rank               = rank,
            ))

        return tuple(results)

    # ------------------------------------------------------------------
    def _compute_raw_weights(
        self,
        slots:   list,
        request: AllocationRequest,
    ) -> WeightMap:
        method = request.method

        if method == AllocationMethod.BLUEPRINT_WEIGHT:
            return self._by_blueprint_weight(slots, request)
        if method == AllocationMethod.EQUAL:
            return self._by_equal(slots, request)
        if method == AllocationMethod.CONVICTION:
            return self._by_score(slots, request, attr="conviction")
        if method == AllocationMethod.CONFIDENCE:
            return self._by_score(slots, request, attr="confidence")
        if method == AllocationMethod.RISK_ADJUSTED:
            return self._by_risk_adjusted(slots, request)
        if method == AllocationMethod.COMPOSITE:
            return self._by_composite(slots, request)

        # Fallback to blueprint weight for unknown methods
        return self._by_blueprint_weight(slots, request)

    def _by_blueprint_weight(self, slots: list, request: AllocationRequest) -> WeightMap:
        """Use the blueprint's target_weight directly × total_capital."""
        weights: WeightMap = {}
        for slot in slots:
            w = float(getattr(slot, "target_weight", 0.0))
            if w == 0.0:
                continue
            symbol    = slot.symbol
            investable = request.total_capital * (1.0 - request.cash_reserve_pct)
            # Absolute weight (blueprint may carry sign for shorts)
            weights[symbol] = w * investable if w > 0 else abs(w) * investable * -1
        return weights

    def _by_equal(self, slots: list, request: AllocationRequest) -> WeightMap:
        """Equal dollars across all slots (longs only unless allow_short)."""
        active = slots if request.allow_short else [s for s in slots if float(getattr(s, "target_weight", 1.0)) >= 0]
        if not active:
            return {}
        investable = request.total_capital * (1.0 - request.cash_reserve_pct)
        per_slot   = investable / len(active)
        return {slot.symbol: per_slot for slot in active}

    def _by_score(self, slots: list, request: AllocationRequest, attr: str) -> WeightMap:
        """Proportional to a numeric slot attribute (conviction, confidence, …)."""
        longs = [s for s in slots if float(getattr(s, "target_weight", 1.0)) >= 0]
        if not longs:
            return {}
        scores     = {s.symbol: max(0.0, float(getattr(s, attr, 0.0))) for s in longs}
        total_score= sum(scores.values())
        if total_score <= 0:
            return self._by_equal(longs, request)
        investable = request.total_capital * (1.0 - request.cash_reserve_pct)
        return {sym: (score / total_score) * investable for sym, score in scores.items()}

    def _by_risk_adjusted(self, slots: list, request: AllocationRequest) -> WeightMap:
        """confidence × (1 − risk_score) proportional allocation."""
        longs = [s for s in slots if float(getattr(s, "target_weight", 1.0)) >= 0]
        if not longs:
            return {}
        scores = {
            s.symbol: float(getattr(s, "confidence", 0.5)) * (1.0 - float(getattr(s, "risk_score", 0.5)))
            for s in longs
        }
        total_score = sum(scores.values())
        if total_score <= 0:
            return self._by_equal(longs, request)
        investable = request.total_capital * (1.0 - request.cash_reserve_pct)
        return {sym: (score / total_score) * investable for sym, score in scores.items()}

    def _by_composite(self, slots: list, request: AllocationRequest) -> WeightMap:
        """Blend: 0.4×conviction + 0.4×confidence + 0.2×risk_adjusted."""
        longs = [s for s in slots if float(getattr(s, "target_weight", 1.0)) >= 0]
        if not longs:
            return {}
        scores: Dict[str, float] = {}
        for s in longs:
            conviction = float(getattr(s, "conviction", 0.5))
            confidence = float(getattr(s, "confidence", 0.5))
            risk_score = float(getattr(s, "risk_score", 0.5))
            scores[s.symbol] = 0.4 * conviction + 0.4 * confidence + 0.2 * confidence * (1.0 - risk_score)
        total_score = sum(scores.values())
        if total_score <= 0:
            return self._by_equal(longs, request)
        investable = request.total_capital * (1.0 - request.cash_reserve_pct)
        return {sym: (score / total_score) * investable for sym, score in scores.items()}
