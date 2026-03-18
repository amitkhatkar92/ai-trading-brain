"""
Meta-Learning — Strategy Weight Predictor
==========================================
Takes the MetaModel's raw predicted R-multiples and converts them into
a normalised capital allocation weight for each strategy.

Conversion pipeline
-------------------
  Raw predictions (may be negative):
    {"Mean_Reversion": 1.35, "Breakout": –0.20, "Momentum": 0.72}

  1. Clip negative predictions to 0 (don't allocate to expected losers)
  2. Apply temperature softmax to produce probability-style weights
  3. Enforce minimum and maximum allocation caps
  4. Normalise to sum = 1.0

Temperature parameter:
  Low  T (e.g. 0.5) → sharply concentrates weight on best strategy
  High T (e.g. 2.0) → more uniform spread across strategies
  Default T = 1.0 for balanced allocation

Caps:
  max_weight = 0.65  (no single strategy gets >65% of capital)
  min_weight = 0.05  (if included, at least 5% allocation)

When the model is not trained (< k observations), falls back to
an equal-weight allocation across all provided strategies.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field

from utils import get_logger
from .feature_extractor import FeatureVector
from .meta_model        import MetaModel

log = get_logger(__name__)

TEMPERATURE   = 1.0     # softmax temperature
MAX_WEIGHT    = 0.65    # cap per strategy
MIN_WEIGHT    = 0.05    # floor if included
N_STRATEGIES  = 4       # max strategies to include (top-N by prediction)


@dataclass
class StrategyAllocation:
    """Final capital allocation output from the predictor."""
    features_desc:     str
    allocations:       dict[str, float]   # sum ≈ 1.0
    raw_predictions:   dict[str, float]
    model_active:      bool
    top_strategy:      str = ""

    def print_allocation(self) -> None:
        _print_allocation_report(self)


class StrategyWeightPredictor:
    """
    Converts MetaModel predictions → normalised strategy allocation dict.

    Usage::
        predictor  = StrategyWeightPredictor(model)
        allocation = predictor.predict(features, strategies)
        allocation.print_allocation()
    """

    def __init__(self, model: MetaModel) -> None:
        self._model = model
        log.info("[StrategyWeightPredictor] Initialised. "
                 "T=%.1f  MaxWt=%.0f%%  Top-N=%d.",
                 TEMPERATURE, MAX_WEIGHT * 100, N_STRATEGIES)

    # ── Public API ────────────────────────────────────────────────────────
    def predict(self, features: FeatureVector,
                strategies: list[str]) -> StrategyAllocation:
        """
        Predict allocation weights for the given strategies under current
        market features.
        """
        if not strategies:
            return StrategyAllocation(
                features_desc   = features.describe(),
                allocations     = {},
                raw_predictions = {},
                model_active    = False,
            )

        if not self._model.is_trained():
            # Fallback: equal weights
            w  = 1.0 / len(strategies)
            return StrategyAllocation(
                features_desc   = features.describe(),
                allocations     = {s: round(w, 4) for s in strategies},
                raw_predictions = {},
                model_active    = False,
                top_strategy    = strategies[0] if strategies else "",
            )

        raw = self._model.predict(features, strategies)
        allocs = self._convert_to_weights(raw)

        top = max(allocs, key=allocs.get) if allocs else ""
        log.info("[WeightPredictor] Allocation: %s",
                 "  ".join(f"{s}={w*100:.0f}%" for s, w in
                           sorted(allocs.items(), key=lambda kv: kv[1],
                                  reverse=True)))

        return StrategyAllocation(
            features_desc   = features.describe(),
            allocations     = allocs,
            raw_predictions = raw,
            model_active    = True,
            top_strategy    = top,
        )

    # ── Private helpers ───────────────────────────────────────────────────
    @staticmethod
    def _convert_to_weights(raw: dict[str, float]) -> dict[str, float]:
        # Step 1: clip negatives
        clipped = {s: max(0.0, r) for s, r in raw.items()}

        # Step 2: take top-N strategies only
        sorted_strats = sorted(clipped.items(), key=lambda kv: kv[1],
                               reverse=True)[:N_STRATEGIES]
        top = dict(sorted_strats)

        # If all clipped to 0 → equal weight for all
        if all(v == 0.0 for v in top.values()):
            n = len(top)
            return {s: round(1.0 / n, 4) for s in top} if n else {}

        # Step 3: softmax with temperature
        scores  = [v / TEMPERATURE for v in top.values()]
        max_s   = max(scores)  # numerical stability
        exps    = [math.exp(s - max_s) for s in scores]
        total   = sum(exps)
        weights = {s: e / total for s, e in zip(top.keys(), exps)}

        # Step 4: cap max weight and redistribute excess
        weights = _cap_and_renorm(weights, MAX_WEIGHT)

        # Step 5: remove strategies below min weight
        weights = {s: w for s, w in weights.items() if w >= MIN_WEIGHT}
        if weights:
            s_total = sum(weights.values())
            weights = {s: round(w / s_total, 4) for s, w in weights.items()}

        return weights


def _cap_and_renorm(weights: dict[str, float], cap: float) -> dict[str, float]:
    """
    Iteratively cap any strategy at `cap` and redistribute excess
    proportionally to uncapped strategies until stable.
    """
    for _ in range(10):   # max 10 redistribution passes
        excess        = sum(max(0.0, w - cap) for w in weights.values())
        if excess < 1e-6:
            break
        capped        = {s: min(w, cap) for s, w in weights.items()}
        under_cap     = {s: w for s, w in capped.items() if w < cap}
        if not under_cap:
            break
        total_under   = sum(under_cap.values())
        if total_under == 0:
            break
        redistributed = {s: w + excess * (w / total_under)
                         for s, w in under_cap.items()}
        at_cap        = {s: cap for s, w in capped.items() if w == cap}
        weights       = {**redistributed, **at_cap}
    return weights


def _print_allocation_report(alloc: StrategyAllocation) -> None:
    w      = 58
    status = "✅ Model Active" if alloc.model_active else "⚠️  Fallback (equal-weight)"
    print()
    print("═" * w)
    print(f"{'  META-LEARNING STRATEGY ALLOCATION':^{w}}")
    print("═" * w)
    print(f"  Market: {alloc.features_desc}")
    print(f"  Model:  {status}")
    print("─" * w)

    if alloc.raw_predictions:
        print(f"  {'Strategy':<28}  {'Pred R':>7}  {'Alloc':>6}")
        print("  " + "─" * (w - 2))
        for s, wt in sorted(alloc.allocations.items(),
                            key=lambda kv: kv[1], reverse=True):
            pred = alloc.raw_predictions.get(s, 0.0)
            bar  = "█" * int(wt * 30)
            print(f"  {s:<28}  {pred:+6.2f}R  {wt*100:5.1f}%  {bar}")
    else:
        print(f"  {'Strategy':<28}  {'Alloc':>6}")
        print("  " + "─" * (w - 2))
        for s, wt in sorted(alloc.allocations.items(),
                            key=lambda kv: kv[1], reverse=True):
            bar = "█" * int(wt * 30)
            print(f"  {s:<28}  {wt*100:5.1f}%  {bar}")

    print("═" * w)
    print()
