"""
iios/intelligence/reasoning/confidence/confidence_calculator.py
===============================================================
Calculates individual confidence dimensions from raw inputs.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..evidence.evidence_registry import Evidence
    from ..debate.debate_summary import DebateSummary
    from ..reasoning_result import ReasoningOutput


class ConfidenceCalculator:
    """
    Pure, stateless calculator for individual confidence dimensions.
    All methods return a normalised float in [0.0, 1.0].
    """

    # -- Evidence confidence ───────────────────────────────────────────────────

    def evidence_confidence(
        self, evidence_items: list[Evidence]
    ) -> float:
        """
        Weighted average of evidence quality scores.
        Returns 0.0 for empty lists.
        """
        if not evidence_items:
            return 0.0
        total = sum(e.composite_score for e in evidence_items)
        return min(1.0, total / len(evidence_items))

    # -- Source confidence ─────────────────────────────────────────────────────

    def source_confidence(
        self,
        sources: list[str],
        weights: dict[str, float] | None = None,
    ) -> float:
        """
        Average confidence based on known source reliability weights.
        Unknown sources receive weight 0.5 (neutral).
        Returns 0.0 for empty source lists.
        """
        if not sources:
            return 0.0
        w_map     = weights or {}
        total     = sum(w_map.get(s, 0.5) for s in sources)
        return min(1.0, total / len(sources))

    # -- Reasoning confidence ──────────────────────────────────────────────────

    def reasoning_confidence(
        self, outputs: list[ReasoningOutput]
    ) -> float:
        """
        Average confidence of individual reasoning step outputs.
        Returns 0.0 for empty lists.
        """
        if not outputs:
            return 0.0
        return sum(o.confidence for o in outputs) / len(outputs)

    # -- Consensus confidence ──────────────────────────────────────────────────

    def consensus_confidence(
        self, summary: DebateSummary | None
    ) -> float:
        """
        Converts a DebateSummary's consensus_score directly to a confidence value.
        Returns 0.5 (neutral) if no summary is provided.
        """
        if summary is None:
            return 0.5
        return max(0.0, min(1.0, summary.consensus_score))

    # -- Historical reliability ────────────────────────────────────────────────

    def historical_reliability(
        self,
        hit_rate:   float | None = None,
        sample_size: int         = 0,
    ) -> float:
        """
        Bayesian-inspired estimate from historical hit rate + sample size.
        Uses a Laplace-smoothed estimate: (hits + 1) / (n + 2).

        Parameters
        ----------
        hit_rate    : Fraction of past correct conclusions [0, 1] or None.
        sample_size : Number of past observations.
        """
        if hit_rate is None:
            return 0.5   # no history → neutral prior
        hits = hit_rate * sample_size
        return (hits + 1.0) / (sample_size + 2.0)

    # -- Risk adjustment ───────────────────────────────────────────────────────

    def risk_adjustment(
        self,
        volatility:  float = 0.0,   # [0, 1]; 0 = stable
        uncertainty: float = 0.0,   # [0, 1]; 0 = certain environment
    ) -> float:
        """
        Returns a multiplicative penalty factor in [0, 1].
        Both inputs are expected in [0, 1].
        """
        penalty = (volatility + uncertainty) / 2.0
        return max(0.0, 1.0 - min(1.0, penalty))

    # -- Final score ───────────────────────────────────────────────────────────

    def compute_final(
        self,
        evidence:   float,
        source:     float,
        reasoning:  float,
        consensus:  float,
        historical: float,
        risk_adj:   float = 1.0,
        weights:    dict[str, float] | None = None,
    ) -> float:
        """
        Combine all dimensions into a single final score.

        Allows caller to override default weights.
        """
        from ..reasoning_constants import (
            CONFIDENCE_WEIGHT_EVIDENCE,
            CONFIDENCE_WEIGHT_SOURCE,
            CONFIDENCE_WEIGHT_REASONING,
            CONFIDENCE_WEIGHT_CONSENSUS,
            CONFIDENCE_WEIGHT_HISTORICAL,
        )
        w = weights or {}
        we  = w.get("evidence",   CONFIDENCE_WEIGHT_EVIDENCE)
        ws  = w.get("source",     CONFIDENCE_WEIGHT_SOURCE)
        wr  = w.get("reasoning",  CONFIDENCE_WEIGHT_REASONING)
        wc  = w.get("consensus",  CONFIDENCE_WEIGHT_CONSENSUS)
        wh  = w.get("historical", CONFIDENCE_WEIGHT_HISTORICAL)

        total_w = we + ws + wr + wc + wh
        if total_w == 0.0:
            return 0.0

        base = (
            we * evidence
            + ws * source
            + wr * reasoning
            + wc * consensus
            + wh * historical
        ) / total_w
        return max(0.0, min(1.0, base * max(0.0, min(1.0, risk_adj))))
