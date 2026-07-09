"""iios/execution/planning/routing/route_evaluator.py
Scores candidate routes on cost, latency, and liquidity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.routing.route_registry import VenueInfo


@dataclass
class RouteScore:
    """Numeric score breakdown for a single candidate venue/route."""

    venue_id:        str   = ""
    cost_score:      float = 50.0    # 0–100; higher = cheaper
    latency_score:   float = 50.0    # 0–100; higher = faster
    liquidity_score: float = 50.0    # 0–100; higher = more liquid
    composite_score: float = 50.0    # weighted composite
    notes:           list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue_id":        self.venue_id,
            "cost_score":      self.cost_score,
            "latency_score":   self.latency_score,
            "liquidity_score": self.liquidity_score,
            "composite_score": self.composite_score,
            "notes":           self.notes,
        }


class RouteEvaluator:
    """
    Scores execution venues for a given order context.

    Weights: cost 40%, latency 30%, liquidity 30%.
    """

    COST_WEIGHT      = 0.40
    LATENCY_WEIGHT   = 0.30
    LIQUIDITY_WEIGHT = 0.30

    # Benchmark references for normalisation
    MAX_FEE_RATE_BPS = 20.0    # 20 bps = worst fee → score 0
    MAX_LATENCY_MS   = 500.0   # 500ms = worst latency → score 0

    def evaluate(
        self,
        venues:         list[VenueInfo],
        order_value:    float = 0.0,
        liquidity_score: float = 50.0,
    ) -> list[RouteScore]:
        scores: list[RouteScore] = []
        for v in venues:
            cs = self._cost_score(v)
            ls = self._latency_score(v)
            composite = (
                cs * self.COST_WEIGHT
                + ls * self.LATENCY_WEIGHT
                + liquidity_score * self.LIQUIDITY_WEIGHT
            )
            scores.append(RouteScore(
                venue_id        = v.venue_id,
                cost_score      = round(cs, 2),
                latency_score   = round(ls, 2),
                liquidity_score = round(liquidity_score, 2),
                composite_score = round(composite, 2),
            ))
        return sorted(scores, key=lambda x: x.composite_score, reverse=True)

    def _cost_score(self, v: VenueInfo) -> float:
        fee_bps = v.fee_rate * 10_000
        return max(0.0, min(100.0, (1.0 - fee_bps / self.MAX_FEE_RATE_BPS) * 100.0))

    def _latency_score(self, v: VenueInfo) -> float:
        return max(0.0, min(100.0, (1.0 - v.latency_ms / self.MAX_LATENCY_MS) * 100.0))
