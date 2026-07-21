"""
decision_solution_selector.py — iios.decision.optimization
===========================================================
Selects the optimal candidate using the configured strategy.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import OptimizationStrategyType
from .decision_candidate import CandidateScore, DecisionCandidate
from .decision_optimization_context import DecisionOptimizationContext
from .decision_optimization_strategy import DecisionOptimizationStrategy
from .decision_priority_engine import DecisionPriorityEngine
from .decision_ranking_engine import DecisionRanking

_log = get_logger(__name__)


class DecisionSolutionSelector:
    """
    Applies the configured :class:`DecisionOptimizationStrategy` to select
    the best :class:`DecisionCandidate` from the scored and ranked set.

    Strategy dispatch table
    -----------------------
    WEIGHTED_SCORE          → Feasible candidate with highest ``confidence_adjusted_score``
    PRIORITY_BASED          → Feasible candidate with highest ``confidence × return``
    CONSTRAINT_SATISFACTION → First candidate satisfying ALL constraints (even soft)
    RULE_BASED              → Same as WEIGHTED_SCORE (rule config reserved)
    MULTI_OBJECTIVE         → Feasible candidate with highest ``final_score``
    PARETO_RANKING          → Best Pareto-rank-1 candidate by ``final_score``
    LEXICOGRAPHIC           → Lexicographic sort by objective scores (desc)
    CUSTOM                  → Delegates to ``strategy._custom_callable``
    """

    def __init__(self) -> None:
        self._priority_engine = DecisionPriorityEngine()

    def select(
        self,
        candidates: List[DecisionCandidate],
        scores:     List[CandidateScore],
        rankings:   List[DecisionRanking],
        strategy:   DecisionOptimizationStrategy,
        context:    DecisionOptimizationContext,
    ) -> Optional[DecisionCandidate]:
        """
        Return the selected candidate or ``None`` if no feasible candidate
        exists.
        """
        if not candidates or not scores:
            return None

        score_map: Dict[str, CandidateScore] = {s.candidate_id: s for s in scores}
        cand_map:  Dict[str, DecisionCandidate] = {c.candidate_id: c for c in candidates}

        st = strategy.strategy_type

        if st == OptimizationStrategyType.WEIGHTED_SCORE:
            return self._by_confidence_adjusted(rankings, cand_map)

        if st == OptimizationStrategyType.PRIORITY_BASED:
            feasible = [c for c in candidates if score_map.get(c.candidate_id, CandidateScore(c.candidate_id,0,{},0,0,False,0)).is_feasible]
            return self._priority_engine.top_priority(feasible or candidates, context)

        if st == OptimizationStrategyType.CONSTRAINT_SATISFACTION:
            feasible = [c for c in candidates if score_map.get(c.candidate_id, CandidateScore(c.candidate_id,0,{},0,0,False,0)).is_feasible]
            if feasible:
                # Pick highest confidence among feasible
                return max(feasible, key=lambda c: c.confidence)
            return None

        if st == OptimizationStrategyType.RULE_BASED:
            return self._by_confidence_adjusted(rankings, cand_map)

        if st == OptimizationStrategyType.MULTI_OBJECTIVE:
            return self._by_final_score(rankings, cand_map)

        if st == OptimizationStrategyType.PARETO_RANKING:
            return self._pareto_select(candidates, scores, cand_map)

        if st == OptimizationStrategyType.LEXICOGRAPHIC:
            return self._lexicographic_select(candidates, scores, cand_map)

        if st == OptimizationStrategyType.CUSTOM:
            if strategy._custom_callable is not None:
                try:
                    result = strategy._custom_callable(candidates, scores, rankings, context)
                    if isinstance(result, DecisionCandidate):
                        return result
                except Exception as exc:
                    _log.warning(
                        f"DecisionSolutionSelector: custom callable raised: {exc}"
                    )
            return self._by_confidence_adjusted(rankings, cand_map)

        # fallback
        return self._by_confidence_adjusted(rankings, cand_map)

    # ------------------------------------------------------------------
    # Internal strategies
    # ------------------------------------------------------------------

    def _by_confidence_adjusted(
        self,
        rankings: List[DecisionRanking],
        cand_map: Dict[str, DecisionCandidate],
    ) -> Optional[DecisionCandidate]:
        """Return rank-1 feasible candidate (highest confidence_adjusted_score)."""
        for r in rankings:
            if r.is_feasible:
                return cand_map.get(r.candidate_id)
        return None

    def _by_final_score(
        self,
        rankings: List[DecisionRanking],
        cand_map: Dict[str, DecisionCandidate],
    ) -> Optional[DecisionCandidate]:
        """Return feasible candidate with highest final_score."""
        best = None
        best_score = float("-inf")
        for r in rankings:
            if r.is_feasible and r.final_score > best_score:
                best_score = r.final_score
                best = cand_map.get(r.candidate_id)
        return best

    def _pareto_select(
        self,
        candidates: List[DecisionCandidate],
        scores:     List[CandidateScore],
        cand_map:   Dict[str, DecisionCandidate],
    ) -> Optional[DecisionCandidate]:
        """Select from Pareto-rank-1 by highest final_score."""
        feasible = [s for s in scores if s.is_feasible]
        if not feasible:
            return None

        # Pareto front: non-dominated solutions
        pareto: List[CandidateScore] = []
        for s in feasible:
            dominated = False
            for other in feasible:
                if other.candidate_id == s.candidate_id:
                    continue
                # other dominates s if at least as good on all objectives
                # and strictly better on at least one
                if (other.total_score >= s.total_score and
                        other.confidence_adjusted_score >= s.confidence_adjusted_score and
                        other.final_score > s.final_score):
                    dominated = True
                    break
            if not dominated:
                pareto.append(s)

        if not pareto:
            pareto = feasible

        best = max(pareto, key=lambda s: (s.final_score, s.confidence_adjusted_score))
        return cand_map.get(best.candidate_id)

    def _lexicographic_select(
        self,
        candidates: List[DecisionCandidate],
        scores:     List[CandidateScore],
        cand_map:   Dict[str, DecisionCandidate],
    ) -> Optional[DecisionCandidate]:
        """Sort feasible candidates by objective scores lexicographically."""
        feasible = [s for s in scores if s.is_feasible]
        if not feasible:
            return None

        def lex_key(s: CandidateScore) -> tuple:
            # Sort by each objective score descending (negate for max sort)
            return tuple(-v for v in s.objective_scores.values())

        feasible.sort(key=lex_key)
        return cand_map.get(feasible[0].candidate_id)
