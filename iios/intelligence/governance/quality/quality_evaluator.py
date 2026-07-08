"""
iios/intelligence/governance/quality/quality_evaluator.py
===========================================================
QualityEvaluator — scores intelligence products across seven dimensions.
"""
from __future__ import annotations

import time
from typing import Any

from .quality_score import QualityScore, score_product
from ..quality_constants import (
    IntelligenceType,
    EvaluationDimension,
    DEFAULT_DIMENSION_WEIGHTS,
)


class QualityEvaluator:
    """
    Scores an intelligence product across all EvaluationDimension values.

    Plug-in architecture: callers may inject a ``scorer_fn`` that maps
    (content dict, product_type) → raw per-dimension scores.  If no
    scorer is provided the built-in heuristic evaluator is used.
    """

    def __init__(
        self,
        weights:    dict[str, float] | None = None,
    ) -> None:
        self._weights = weights or dict(DEFAULT_DIMENSION_WEIGHTS)

    # -- Public API ─────────────────────────────────────────────────────────────

    def evaluate(
        self,
        product_id:   str,
        product_type: IntelligenceType,
        content:      dict[str, Any],
        metadata:     dict[str, Any] | None = None,
    ) -> QualityScore:
        """
        Evaluate a single intelligence product.
        Returns a fully populated QualityScore.
        """
        raw = self._heuristic_score(product_type, content, metadata or {})
        return score_product(product_id, raw, self._weights)

    # -- Heuristic scoring ─────────────────────────────────────────────────────

    def _heuristic_score(
        self,
        product_type: IntelligenceType,
        content:      dict[str, Any],
        metadata:     dict[str, Any],
    ) -> dict[str, float]:
        """
        Heuristic per-dimension scorer.
        Produces [0, 1] scores from structural signals in the content dict.
        Domain-specific evaluators can override this via subclassing.
        """
        return {
            EvaluationDimension.ACCURACY.value:       self._score_accuracy(content, metadata),
            EvaluationDimension.CONSISTENCY.value:    self._score_consistency(content),
            EvaluationDimension.COMPLETENESS.value:   self._score_completeness(content),
            EvaluationDimension.TIMELINESS.value:     self._score_timeliness(content, metadata),
            EvaluationDimension.RELIABILITY.value:    self._score_reliability(content),
            EvaluationDimension.CONFIDENCE.value:     self._score_confidence(content),
            EvaluationDimension.EXPLAINABILITY.value: self._score_explainability(content),
        }

    @staticmethod
    def _score_accuracy(content: dict[str, Any], meta: dict[str, Any]) -> float:
        """Proxy: if outcome known and matches, score high; else use confidence."""
        if "actual_value" in content and "value" in content:
            pred   = float(content.get("value", 0))
            actual = float(content.get("actual_value", 0))
            if actual == 0:
                return 0.5
            err = abs(pred - actual) / abs(actual)
            return max(0.0, 1.0 - err)
        # Fall back to confidence as accuracy proxy
        return float(content.get("confidence", 0.5))

    @staticmethod
    def _score_consistency(content: dict[str, Any]) -> float:
        """
        Check that numeric range fields are internally consistent.
        range_low <= value <= range_high → 1.0; else penalise proportionally.
        """
        v  = content.get("value")
        lo = content.get("range_low")
        hi = content.get("range_high")
        if v is None:
            return 0.8   # no range info — neutral
        if lo is None or hi is None:
            return 0.8
        try:
            v, lo, hi = float(v), float(lo), float(hi)
        except (TypeError, ValueError):
            return 0.8
        if lo <= v <= hi:
            return 1.0
        # Penalise by how far outside range
        span = hi - lo or 1.0
        excess = max(lo - v, v - hi)
        return max(0.0, 1.0 - excess / span)

    @staticmethod
    def _score_completeness(content: dict[str, Any]) -> float:
        """Fraction of expected common fields that are non-None/non-empty."""
        EXPECTED = ["value", "confidence", "probability"]
        present  = sum(1 for k in EXPECTED if content.get(k) is not None)
        base     = present / len(EXPECTED)
        # Bonus for having metadata and a unique ID
        if content.get("metadata"):
            base = min(1.0, base + 0.05)
        if any(k.endswith("_id") for k in content):
            base = min(1.0, base + 0.05)
        return base

    @staticmethod
    def _score_timeliness(content: dict[str, Any], meta: dict[str, Any]) -> float:
        """Freshness: products created recently score higher."""
        created_at = content.get("created_at") or meta.get("created_at")
        if created_at is None:
            return 0.7
        try:
            age_s = time.time() - float(created_at)
        except (TypeError, ValueError):
            return 0.7
        # Full score within 5 min, degrades to 0.3 over 24 h
        if age_s < 300:
            return 1.0
        if age_s > 86_400:
            return 0.3
        return max(0.3, 1.0 - (age_s / 86_400) * 0.7)

    @staticmethod
    def _score_reliability(content: dict[str, Any]) -> float:
        """
        Proxy: model confidence + absence of error flags.
        """
        base = float(content.get("confidence", 0.5))
        if content.get("error") or content.get("failed"):
            base *= 0.3
        return max(0.0, min(1.0, base))

    @staticmethod
    def _score_confidence(content: dict[str, Any]) -> float:
        """Direct confidence score from product, clamped to [0,1]."""
        return max(0.0, min(1.0, float(content.get("confidence", 0.5))))

    @staticmethod
    def _score_explainability(content: dict[str, Any]) -> float:
        """
        Proxy: presence of explanation/summary text fields boosts score.
        """
        fields = ["explanation", "summary", "reasoning", "notes"]
        hits   = sum(1 for f in fields if content.get(f))
        return min(1.0, 0.4 + hits * 0.2)
