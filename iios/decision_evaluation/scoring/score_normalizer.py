"""iios/decision_evaluation/scoring/score_normalizer.py"""
from __future__ import annotations

import math
import statistics

from ..evaluation_constants import CriterionDirection, NormalizationMethod
from ..criteria.criterion import Criterion


class ScoreNormalizer:
    """
    Normalizes raw scores within each criterion across all alternatives.
    Returns: {alt_id: {criterion_id: normalized_score}} in [0, 1].
    """

    def normalize(
        self,
        raw_scores: dict[str, dict[str, float]],
        criteria:   list[Criterion],
        method:     NormalizationMethod = NormalizationMethod.MINMAX,
    ) -> dict[str, dict[str, float]]:
        if not raw_scores:
            return {}

        alt_ids  = list(raw_scores.keys())
        result:  dict[str, dict[str, float]] = {aid: {} for aid in alt_ids}

        for crit in criteria:
            cid    = crit.criterion_id
            values = {aid: raw_scores[aid].get(cid, 0.0) for aid in alt_ids}

            if method == NormalizationMethod.NONE:
                norm_values = {aid: max(0.0, min(1.0, v)) for aid, v in values.items()}
            elif method == NormalizationMethod.ZSCORE:
                norm_values = self._zscore(values, crit.direction)
            elif method == NormalizationMethod.MAXABS:
                norm_values = self._maxabs(values, crit.direction)
            else:  # MINMAX (default)
                norm_values = self._minmax(values, crit.direction, crit)

            for aid, nv in norm_values.items():
                result[aid][cid] = nv

        return result

    # ── Private helpers ────────────────────────────────────────────────────

    def _minmax(
        self,
        values:    dict[str, float],
        direction: CriterionDirection,
        crit:      Criterion,
    ) -> dict[str, float]:
        vals = list(values.values())
        mn   = min(vals)
        mx   = max(vals)
        rng  = mx - mn

        if rng == 0.0:
            return {aid: 1.0 for aid in values}

        if direction == CriterionDirection.MINIMIZE:
            return {aid: (mx - v) / rng for aid, v in values.items()}

        if direction == CriterionDirection.TARGET:
            target = getattr(crit, "target_val", None) or ((mn + mx) / 2)
            max_dev = max(abs(v - target) for v in vals) or 1.0
            return {aid: 1.0 - abs(v - target) / max_dev for aid, v in values.items()}

        # MAXIMIZE (default)
        return {aid: (v - mn) / rng for aid, v in values.items()}

    def _zscore(
        self,
        values:    dict[str, float],
        direction: CriterionDirection,
    ) -> dict[str, float]:
        vals = list(values.values())
        mu   = statistics.mean(vals)
        if len(vals) < 2:
            std = 1.0
        else:
            std  = statistics.stdev(vals) or 1.0

        def _sigmoid(x: float) -> float:
            return 1.0 / (1.0 + math.exp(-x))

        normalized: dict[str, float] = {}
        for aid, v in values.items():
            z   = (v - mu) / std
            sig = _sigmoid(z)
            normalized[aid] = (1.0 - sig) if direction == CriterionDirection.MINIMIZE else sig
        return normalized

    def _maxabs(
        self,
        values:    dict[str, float],
        direction: CriterionDirection,
    ) -> dict[str, float]:
        max_abs = max(abs(v) for v in values.values()) or 1.0
        result  = {aid: v / max_abs for aid, v in values.items()}
        # Clip to [0, 1]
        result  = {aid: max(0.0, min(1.0, v)) for aid, v in result.items()}
        if direction == CriterionDirection.MINIMIZE:
            result = {aid: 1.0 - v for aid, v in result.items()}
        return result
