"""iios/decision_evaluation/analytics/evaluation_analytics.py"""
from __future__ import annotations

import copy
import statistics


class EvaluationAnalytics:
    """Post-evaluation analytics: sensitivity, importance, consistency."""

    # ── Criterion importance ───────────────────────────────────────────────

    def criterion_importance(self, result) -> dict[str, float]:  # type: ignore[type-arg]
        """
        Importance of each criterion based on normalized score variance
        across alternatives. Higher variance → more discriminating → higher importance.
        """
        scored = result.scored_alternatives
        if not scored:
            return {}

        all_crit_ids: set[str] = set()
        for a in scored:
            for cs in a.criterion_scores:
                all_crit_ids.add(cs.criterion_id)

        importance: dict[str, float] = {}
        for cid in all_crit_ids:
            vals = [
                cs.normalized_score
                for a in scored
                for cs in a.criterion_scores
                if cs.criterion_id == cid
            ]
            if len(vals) < 2:
                importance[cid] = 0.0
            else:
                importance[cid] = statistics.variance(vals)

        # Normalize so max == 1
        max_val = max(importance.values()) if importance else 0.0
        if max_val > 0:
            importance = {k: v / max_val for k, v in importance.items()}
        return importance

    # ── Sensitivity analysis ───────────────────────────────────────────────

    def sensitivity_analysis(
        self,
        request,                        # type: ignore[type-arg]
        criterion_id: str,
        weight_range: tuple[float, float] = (0.0, 1.0),
        steps: int = 10,
    ) -> dict:
        """
        Varies the weight of one criterion across weight_range in `steps` increments
        and records how the top-ranked alternative changes.
        """
        from ..scoring.scoring_engine import ScoringEngine
        from ..ranking.ranking_engine import RankingEngine

        if steps < 2:
            steps = 2
        low, high = weight_range
        step_size = (high - low) / max(steps - 1, 1)
        weight_values = [low + i * step_size for i in range(steps)]

        scoring = ScoringEngine()
        ranking = RankingEngine()

        weights_tested: list[float] = []
        top_alts:       list[str]   = []

        for w in weight_values:
            override = {criterion_id: w}
            scored   = scoring.score(
                request.alternatives,
                request.criteria,
                weights       = override,
                normalization = request.normalization,
                method        = request.scoring_method,
            )
            ranked = ranking.rank(scored, method=request.ranking_method)
            top    = ranked[0].alternative_id if ranked else None
            weights_tested.append(w)
            top_alts.append(top or "")

        # Rank changes: when does top_alternative change?
        rank_changes: list[dict] = []
        for i in range(1, len(top_alts)):
            if top_alts[i] != top_alts[i - 1]:
                rank_changes.append({
                    "at_weight": weights_tested[i],
                    "from":      top_alts[i - 1],
                    "to":        top_alts[i],
                })

        return {
            "criterion_id":  criterion_id,
            "weights":       weights_tested,
            "top_alternative": top_alts,
            "rank_changes":  rank_changes,
        }

    # ── Consistency check ──────────────────────────────────────────────────

    def consistency_check(self, result) -> dict:  # type: ignore[type-arg]
        """
        Checks that ranked order is consistent with composite scores.
        """
        issues:   list[str] = []
        ranked    = result.ranked_alternatives
        if not ranked:
            return {"consistent": True, "issues": []}

        for i in range(len(ranked) - 1):
            a, b = ranked[i], ranked[i + 1]
            if a.composite_score < b.composite_score - 1e-9:
                issues.append(
                    f"Rank {a.rank} ({a.alternative_id}) has lower score than "
                    f"rank {b.rank} ({b.alternative_id})"
                )

        return {"consistent": len(issues) == 0, "issues": issues}
