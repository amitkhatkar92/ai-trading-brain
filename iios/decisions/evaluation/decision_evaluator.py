"""
iios/decisions/evaluation/decision_evaluator.py
================================================
DecisionEvaluator — scores each DecisionCandidate across all dimensions.

Scoring is purely heuristic and investment-agnostic.
Future domain modules replace or extend dimension scorers via the
``register_scorer`` method — no framework modification needed.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from ..decision_constants import (
    DEFAULT_DIMENSION_WEIGHTS,
    DecisionDimension,
)
from ..models.decision_candidate import DecisionCandidate
from ..models.decision_request import DecisionRequest


# ── Default dimension scorers (stateless functions) ───────────────────────────

def _score_confidence(candidate: DecisionCandidate, _request: DecisionRequest) -> float:
    """Direct confidence from the option."""
    return max(0.0, min(1.0, candidate.option.confidence))


def _score_risk(candidate: DecisionCandidate, _request: DecisionRequest) -> float:
    """Inverted risk (low risk → high score)."""
    return max(0.0, min(1.0, 1.0 - candidate.option.risk_score))


def _score_evidence(candidate: DecisionCandidate, _request: DecisionRequest) -> float:
    """More evidence items → higher score (capped at 1.0 for ≥5 items)."""
    n = len(candidate.option.evidence)
    return min(1.0, n / 5.0)


def _score_completeness(candidate: DecisionCandidate, request: DecisionRequest) -> float:
    """Option description and name completeness."""
    score = 0.0
    if candidate.option.name:
        score += 0.4
    if candidate.option.description:
        score += 0.4
    if candidate.option.option_type.value != "generic":
        score += 0.2
    return score


def _score_consistency(candidate: DecisionCandidate, request: DecisionRequest) -> float:
    """
    Checks that the candidate type is consistent with the requested type.
    Returns 1.0 when types match or no preference given; 0.5 otherwise.
    """
    if request.decision_type is None:
        return 0.8  # no preference — neutral score
    if candidate.option.option_type == request.decision_type:
        return 1.0
    return 0.5


def _score_timeliness(candidate: DecisionCandidate, request: DecisionRequest) -> float:
    """
    Penalises old intelligence payloads. Uses 'created_at' in payload items.
    Falls back to 0.8 when no timing data available.
    """
    payload = request.intelligence_payload
    if not payload:
        return 0.8
    now   = time.time()
    ages  = [now - p.get("created_at", now) for p in payload if "created_at" in p]
    if not ages:
        return 0.8
    avg_age_s = sum(ages) / len(ages)
    # Decay: full score for < 60s, 0 for > 3600s
    return max(0.0, 1.0 - avg_age_s / 3_600.0)


_DEFAULT_SCORERS: dict[str, Callable[[DecisionCandidate, DecisionRequest], float]] = {
    DecisionDimension.CONFIDENCE.value:   _score_confidence,
    DecisionDimension.RISK.value:         _score_risk,
    DecisionDimension.EVIDENCE.value:     _score_evidence,
    DecisionDimension.COMPLETENESS.value: _score_completeness,
    DecisionDimension.CONSISTENCY.value:  _score_consistency,
    DecisionDimension.TIMELINESS.value:   _score_timeliness,
}


class DecisionEvaluator:
    """
    Scores DecisionCandidates across registered evaluation dimensions.

    Thread-safe; scorers and weights are read-only after initialisation.
    New scorers can be injected via ``register_scorer()``.
    """

    def __init__(
        self,
        weights:  dict[str, float] | None = None,
    ) -> None:
        self._scorers: dict[str, Callable[[DecisionCandidate, DecisionRequest], float]] = dict(
            _DEFAULT_SCORERS
        )
        self._weights: dict[str, float] = dict(weights or DEFAULT_DIMENSION_WEIGHTS)

    def register_scorer(
        self,
        dimension: str,
        scorer:    Callable[[DecisionCandidate, DecisionRequest], float],
        weight:    float | None = None,
    ) -> None:
        """Register (or replace) a dimension scorer. Optionally updates its weight."""
        self._scorers[dimension] = scorer
        if weight is not None:
            self._weights[dimension] = weight
            # Re-normalise weights
            total = sum(self._weights.values())
            if total > 0:
                self._weights = {k: v / total for k, v in self._weights.items()}

    def evaluate(
        self,
        candidate: DecisionCandidate,
        request:   DecisionRequest,
    ) -> DecisionCandidate:
        """
        Score ``candidate`` and populate its dimension_scores and composite_score.
        Returns the mutated candidate.
        """
        t0            = time.perf_counter()
        dim_scores:   dict[str, float] = {}
        composite:    float            = 0.0
        total_weight: float            = 0.0

        for dim, scorer in self._scorers.items():
            try:
                raw = scorer(candidate, request)
                raw = max(0.0, min(1.0, raw))  # clamp
            except Exception:
                raw = 0.0
            dim_scores[dim]  = raw
            w                = self._weights.get(dim, 0.0)
            composite       += raw * w
            total_weight    += w

        if total_weight > 0:
            composite /= total_weight

        candidate.mark_evaluated(
            composite_score  = composite,
            dimension_scores = dim_scores,
        )
        candidate.evaluation_ms = (time.perf_counter() - t0) * 1_000.0
        return candidate
