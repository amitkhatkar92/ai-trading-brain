"""
decision_scoring_engine.py — iios.decision.optimization
=========================================================
Computes optimization scores for all candidates simultaneously.

Cross-candidate min-max normalization ensures scores are comparable
within the candidate set.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Dict, List

from .decision_candidate  import CandidateScore, DecisionCandidate
from .decision_constraint import ConstraintEvaluationResult
from .decision_objective  import DecisionObjective
from .decision_optimization_context import DecisionOptimizationContext


class DecisionScoringEngine:
    """
    Scores all candidates against a list of objectives with min-max
    normalization across the candidate population.

    Scoring algorithm
    -----------------
    1. Extract raw values for every (candidate, objective) pair.
    2. Normalise each objective's values to [0, 1] using min-max.
    3. MINIMIZE objectives invert the scale.
    4. Compute ``total_score = Σ(weight_i × norm_score_i)``.
    5. Divide by total weight (so total_score ∈ [0, 1]).
    6. Subtract constraint penalty → ``final_score``.
    7. Multiply by candidate confidence → ``confidence_adjusted_score``.
    """

    def score_all(
        self,
        candidates:          List[DecisionCandidate],
        objectives:          List[DecisionObjective],
        constraint_results:  Dict[str, ConstraintEvaluationResult],
        context:             DecisionOptimizationContext,
    ) -> List[CandidateScore]:
        """
        Compute and return a :class:`CandidateScore` for every candidate.
        """
        if not candidates:
            return []

        candidate_datas = [c.to_dict() for c in candidates]

        # --- Step 1 & 2: collect raw values and normalise per objective ---
        obj_scores: Dict[str, List[float]] = {}  # obj_id -> [score per candidate]

        for obj in objectives:
            raw_values = [obj.extract_value(cd) for cd in candidate_datas]
            min_val = min(raw_values)
            max_val = max(raw_values)
            obj_scores[obj.objective_id] = [
                obj.normalize_score(v, min_val, max_val) for v in raw_values
            ]

        total_weight = sum(obj.weight for obj in objectives) or 1.0

        # --- Step 3-7: compute final score for each candidate ---
        scores: List[CandidateScore] = []

        for idx, candidate in enumerate(candidates):
            per_obj: Dict[str, float] = {}
            total = 0.0

            for obj in objectives:
                s = obj_scores[obj.objective_id][idx]
                per_obj[obj.objective_id] = s
                total += obj.weight * s

            total_score = total / total_weight

            cr = constraint_results.get(candidate.candidate_id)
            penalty    = cr.total_penalty if cr else 0.0
            is_feasible = cr.is_feasible if cr else True

            final_score = max(0.0, total_score - penalty)
            confidence_adj = final_score * max(0.0, min(1.0, candidate.confidence))

            scores.append(CandidateScore(
                candidate_id               = candidate.candidate_id,
                total_score                = total_score,
                objective_scores           = per_obj,
                constraint_penalty         = penalty,
                final_score                = final_score,
                is_feasible                = is_feasible,
                confidence_adjusted_score  = confidence_adj,
            ))

        return scores

    # ------------------------------------------------------------------
    # Single-candidate fallback (no normalisation — used when only one
    # candidate exists)
    # ------------------------------------------------------------------

    def score_single(
        self,
        candidate:          DecisionCandidate,
        objectives:         List[DecisionObjective],
        constraint_result:  ConstraintEvaluationResult,
        context:            DecisionOptimizationContext,
    ) -> CandidateScore:
        return self.score_all(
            [candidate], objectives, {candidate.candidate_id: constraint_result}, context
        )[0]
