"""iios/investment/strategy/opportunity/matching_profile.py
MatchingProfile — pluggable configuration for the matching framework.
Different policies (conservative, aggressive, momentum-only, …) are
expressed as different MatchingProfile instances injected at runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class MatchingProfile:
    """
    Controls how the MatchingEngine scores strategies against opportunities.

    All weights are normalised internally — they need not sum to 1.0.
    Set a weight to 0.0 to exclude a dimension entirely.
    """
    # ── scoring dimension weights ─────────────────────────────────────────────
    regime_weight:     float = 0.22
    timeframe_weight:  float = 0.16
    direction_weight:  float = 0.16
    volatility_weight: float = 0.14
    liquidity_weight:  float = 0.14
    sector_weight:     float = 0.09
    momentum_weight:   float = 0.09

    # ── acceptance thresholds ─────────────────────────────────────────────────
    min_matching_score:   float = 40.0  # below this → not a candidate
    hard_reject_below:    float = 20.0  # hard-reject regardless of other signals
    min_opp_confidence:   float = 0.25  # skip opportunities with confidence < this
    min_opp_liquidity:    float = 0.15  # skip opportunities with liquidity < this

    # ── penalty parameters ────────────────────────────────────────────────────
    regime_mismatch_penalty:    float = 30.0  # score points deducted
    direction_mismatch_penalty: float = 25.0
    liquidity_gap_penalty:      float = 20.0  # when opp liquidity < strategy minimum

    # ── policy identity (for auditability) ───────────────────────────────────
    policy_name: str = "default"

    def normalized_weights(self) -> Dict[str, float]:
        """Return weights as a dict normalised to sum exactly to 1.0."""
        raw = {
            "regime":     self.regime_weight,
            "timeframe":  self.timeframe_weight,
            "direction":  self.direction_weight,
            "volatility": self.volatility_weight,
            "liquidity":  self.liquidity_weight,
            "sector":     self.sector_weight,
            "momentum":   self.momentum_weight,
        }
        total = sum(raw.values())
        if total <= 0.0:
            return {k: 0.0 for k in raw}
        return {k: v / total for k, v in raw.items()}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_name":        self.policy_name,
            "min_matching_score": self.min_matching_score,
            "hard_reject_below":  self.hard_reject_below,
            "min_opp_confidence": self.min_opp_confidence,
            "weights":            self.normalized_weights(),
        }


# ── built-in profiles ─────────────────────────────────────────────────────────

DEFAULT_PROFILE = MatchingProfile(policy_name="default")

MOMENTUM_PROFILE = MatchingProfile(
    regime_weight=0.25,
    timeframe_weight=0.20,
    direction_weight=0.20,
    momentum_weight=0.20,
    volatility_weight=0.10,
    liquidity_weight=0.05,
    sector_weight=0.00,
    policy_name="momentum",
)

CONSERVATIVE_PROFILE = MatchingProfile(
    regime_weight=0.30,
    liquidity_weight=0.25,
    volatility_weight=0.20,
    timeframe_weight=0.15,
    direction_weight=0.05,
    sector_weight=0.05,
    momentum_weight=0.00,
    min_matching_score=55.0,
    hard_reject_below=35.0,
    min_opp_confidence=0.50,
    min_opp_liquidity=0.40,
    policy_name="conservative",
)
