"""iios/investment/portfolio/construction/construction_rules.py

Construction rules are transformation / enforcement functions applied
to the intermediate weight map before the blueprint is finalised.

Rules do NOT optimise weights.  They apply deterministic adjustments:
  • Cap weights at limits
  • Redistribute excess proportionally
  • Enforce minimum position sizes
  • Enforce cash reserve
  • Enforce market-neutral net exposure
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# Weight map type
# ---------------------------------------------------------------------------

#: Internal representation: symbol → raw_weight (signed for shorts)
WeightMap = Dict[str, float]


# ---------------------------------------------------------------------------
# RuleApplication result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RuleApplication:
    """Records how a rule modified the weight map."""

    rule_name:      str             = ""
    symbols_changed:Tuple[str, ...] = field(default_factory=tuple)
    delta_max:      float           = 0.0   # largest single-weight change
    notes:          Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name":       self.rule_name,
            "symbols_changed": list(self.symbols_changed),
            "delta_max":       round(self.delta_max, 6),
            "notes":           list(self.notes),
        }


# ---------------------------------------------------------------------------
# Abstract rule
# ---------------------------------------------------------------------------

class ConstructionRule(abc.ABC):
    """
    Abstract base for a deterministic weight-adjustment rule.

    apply() receives a mutable WeightMap (symbol → weight) and the
    ConstructionRequest, modifies the map in-place, and returns a
    RuleApplication describing what changed.
    """

    @property
    @abc.abstractmethod
    def rule_name(self) -> str: ...

    @abc.abstractmethod
    def apply(self, weights: WeightMap, request: Any) -> RuleApplication: ...


# ---------------------------------------------------------------------------
# Concrete rules
# ---------------------------------------------------------------------------

class MaxWeightCapRule(ConstructionRule):
    """
    Cap any single absolute weight at request.max_single_weight.
    Excess weight is redistributed proportionally to uncapped positions.
    """

    @property
    def rule_name(self) -> str:
        return "max_weight_cap"

    def apply(self, weights: WeightMap, request: Any) -> RuleApplication:
        limit    = request.max_single_weight
        changed: List[str] = []
        notes:   List[str] = []

        # Separate longs and shorts; work on absolute values
        long_syms  = {s: w for s, w in weights.items() if w >= 0}
        short_syms = {s: w for s, w in weights.items() if w < 0}

        for book, sign in [(long_syms, 1.0), (short_syms, -1.0)]:
            if not book:
                continue
            abs_book = {s: abs(w) for s, w in book.items()}
            capped = _cap_and_redistribute(abs_book, limit)
            for sym, new_abs in capped.items():
                old_abs = abs_book[sym]
                new_w   = sign * new_abs
                if abs(new_w - weights[sym]) > 1e-9:
                    changed.append(sym)
                    notes.append(
                        f"{sym}: {weights[sym]:.6f} → {new_w:.6f} (cap={limit:.4f})"
                    )
                weights[sym] = new_w

        return RuleApplication(
            rule_name=self.rule_name,
            symbols_changed=tuple(sorted(changed)),
            delta_max=max(
                (abs(weights[s] - long_syms.get(s, short_syms.get(s, 0)))
                 for s in changed), default=0.0
            ),
            notes=tuple(notes),
        )


class MinWeightFloorRule(ConstructionRule):
    """
    Remove any long position whose absolute weight falls below
    request.min_single_weight.  Short positions are treated symmetrically.

    Note: This may reduce the holding count below min_holdings — that
    is caught by the validator, not here.
    """

    @property
    def rule_name(self) -> str:
        return "min_weight_floor"

    def apply(self, weights: WeightMap, request: Any) -> RuleApplication:
        floor   = request.min_single_weight
        to_drop = [s for s, w in weights.items() if abs(w) < floor - 1e-9]
        for sym in to_drop:
            del weights[sym]
        return RuleApplication(
            rule_name=self.rule_name,
            symbols_changed=tuple(sorted(to_drop)),
            delta_max=0.0,
            notes=tuple(f"{s}: dropped (weight below floor {floor:.4f})" for s in to_drop),
        )


class CashReserveRule(ConstructionRule):
    """
    Scales all long weights down by (1 − target_cash_pct) to ensure
    that cash_weight ≈ target_cash_pct after construction.

    Only long positions are affected; short positions retain their raw
    absolute weight (short proceeds are separate from cash).
    """

    @property
    def rule_name(self) -> str:
        return "cash_reserve"

    def apply(self, weights: WeightMap, request: Any) -> RuleApplication:
        target_cash = request.target_cash_pct
        investable  = 1.0 - target_cash
        if investable <= 0:
            return RuleApplication(rule_name=self.rule_name)

        long_syms = {s: w for s, w in weights.items() if w > 0}
        if not long_syms:
            return RuleApplication(rule_name=self.rule_name)

        long_sum = sum(long_syms.values())
        if long_sum <= 0:
            return RuleApplication(rule_name=self.rule_name)

        scale = investable / long_sum
        if abs(scale - 1.0) < 1e-9:
            return RuleApplication(rule_name=self.rule_name)

        changed: List[str] = []
        for sym in long_syms:
            old = weights[sym]
            weights[sym] = old * scale
            if abs(weights[sym] - old) > 1e-9:
                changed.append(sym)

        return RuleApplication(
            rule_name=self.rule_name,
            symbols_changed=tuple(sorted(changed)),
            delta_max=abs(scale - 1.0) * (max(long_syms.values(), default=0.0)),
            notes=(f"scaled by {scale:.6f} for cash reserve {target_cash:.4f}",),
        )


class MarketNeutralRule(ConstructionRule):
    """
    For MARKET_NEUTRAL construction type: balance long and short book
    so |long_sum - short_sum| ≤ tolerance (1%).

    Scales the larger book down to match the smaller book.
    """

    TOLERANCE: float = 0.01

    @property
    def rule_name(self) -> str:
        return "market_neutral"

    def apply(self, weights: WeightMap, request: Any) -> RuleApplication:
        from iios.investment.portfolio.construction.construction_types import ConstructionType

        if request.construction_type != ConstructionType.MARKET_NEUTRAL:
            return RuleApplication(rule_name=self.rule_name)

        long_syms  = {s: w for s, w in weights.items() if w > 0}
        short_syms = {s: w for s, w in weights.items() if w < 0}

        long_sum  = sum(long_syms.values())
        short_sum = abs(sum(short_syms.values()))

        if long_sum < 1e-9 or short_sum < 1e-9:
            return RuleApplication(
                rule_name=self.rule_name,
                notes=("skipped: one book is empty",),
            )

        if abs(long_sum - short_sum) <= self.TOLERANCE:
            return RuleApplication(rule_name=self.rule_name)

        changed: List[str] = []
        if long_sum > short_sum:
            scale = short_sum / long_sum
            for sym in long_syms:
                old = weights[sym]
                weights[sym] = old * scale
                changed.append(sym)
            note = f"long book scaled by {scale:.6f} to match short {short_sum:.4f}"
        else:
            scale = long_sum / short_sum
            for sym in short_syms:
                old = weights[sym]
                weights[sym] = old * scale  # still negative
                changed.append(sym)
            note = f"short book scaled by {scale:.6f} to match long {long_sum:.4f}"

        return RuleApplication(
            rule_name=self.rule_name,
            symbols_changed=tuple(sorted(changed)),
            delta_max=abs(1.0 - scale) * max(abs(w) for w in weights.values()),
            notes=(note,),
        )


class NormaliseRule(ConstructionRule):
    """
    Final normalisation: long weights sum to exactly (1 − cash_pct).
    Short weights sum to exactly short_exposure_pct (request parameter).

    Run this LAST in a RuleSet.
    """

    @property
    def rule_name(self) -> str:
        return "normalise"

    def apply(self, weights: WeightMap, request: Any) -> RuleApplication:
        investable = 1.0 - request.target_cash_pct

        long_syms  = {s: w for s, w in weights.items() if w > 0}
        short_syms = {s: w for s, w in weights.items() if w < 0}

        changed: List[str] = []
        notes:   List[str] = []

        if long_syms:
            long_sum = sum(long_syms.values())
            if long_sum > 1e-9:
                scale = investable / long_sum
                if abs(scale - 1.0) > 1e-9:
                    for sym in long_syms:
                        old = weights[sym]
                        weights[sym] = old * scale
                        changed.append(sym)
                    notes.append(f"long normalised x{scale:.6f}")

        if short_syms and request.allow_short and request.short_exposure_pct > 0:
            short_abs_sum = abs(sum(short_syms.values()))
            if short_abs_sum > 1e-9:
                target_short = request.short_exposure_pct
                scale = target_short / short_abs_sum
                if abs(scale - 1.0) > 1e-9:
                    for sym in short_syms:
                        old = weights[sym]
                        weights[sym] = old * scale   # stays negative
                        changed.append(sym)
                    notes.append(f"short normalised x{scale:.6f}")

        return RuleApplication(
            rule_name=self.rule_name,
            symbols_changed=tuple(sorted(set(changed))),
            notes=tuple(notes),
        )


# ---------------------------------------------------------------------------
# RuleSet — ordered, named collection
# ---------------------------------------------------------------------------

class RuleSet:
    """
    Ordered collection of ConstructionRules applied sequentially.

    apply() mutates the weight map and returns a list of RuleApplications.
    """

    def __init__(self, rules: List[ConstructionRule] | None = None) -> None:
        self._rules: List[ConstructionRule] = list(rules or [])

    def add(self, rule: ConstructionRule) -> "RuleSet":
        self._rules.append(rule)
        return self

    def apply_all(self, weights: WeightMap, request: Any) -> List[RuleApplication]:
        results: List[RuleApplication] = []
        for rule in self._rules:
            results.append(rule.apply(weights, request))
        return results

    @property
    def rule_names(self) -> List[str]:
        return [r.rule_name for r in self._rules]

    @classmethod
    def default(cls) -> "RuleSet":
        """Standard rule set: max cap → min floor → cash reserve → normalise."""
        return cls([
            MaxWeightCapRule(),
            MinWeightFloorRule(),
            CashReserveRule(),
            NormaliseRule(),
        ])

    @classmethod
    def market_neutral(cls) -> "RuleSet":
        """Market-neutral rule set: cap → floor → neutral balance → normalise."""
        return cls([
            MaxWeightCapRule(),
            MinWeightFloorRule(),
            MarketNeutralRule(),
            NormaliseRule(),
        ])


# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------

def _cap_and_redistribute(abs_weights: Dict[str, float], cap: float) -> Dict[str, float]:
    """
    Cap absolute weights at `cap` and redistribute excess to uncapped positions.
    Deterministic: processes symbols in sorted order.
    """
    weights = {s: min(w, cap) for s, w in abs_weights.items()}

    for _ in range(20):  # bounded iterations
        excess = sum(abs_weights[s] - weights[s] for s in abs_weights)
        if excess < 1e-9:
            break
        uncapped = {s: w for s, w in weights.items() if w < cap - 1e-9}
        uncapped_total = sum(uncapped.values())
        if uncapped_total < 1e-9:
            break
        for s in sorted(uncapped):  # deterministic order
            delta = excess * (uncapped[s] / uncapped_total)
            new_w = uncapped[s] + delta
            weights[s] = min(new_w, cap)

    return weights
