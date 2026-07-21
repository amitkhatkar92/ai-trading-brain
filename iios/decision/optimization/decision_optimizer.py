"""
decision_optimizer.py — iios.decision.optimization
====================================================
Core optimization algorithm:
  constraints → scoring → ranking → selection → solution

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .decision_candidate          import CandidateScore, DecisionCandidate
from .decision_constraint         import ConstraintEvaluationResult, DecisionConstraint
from .decision_constraint_engine  import DecisionConstraintEngine
from .decision_objective          import DecisionObjective
from .decision_optimization_context import DecisionOptimizationContext
from .decision_optimization_strategy import DecisionOptimizationStrategy
from .decision_ranking_engine     import DecisionRanking, DecisionRankingEngine
from .decision_scoring_engine     import DecisionScoringEngine
from .decision_solution           import DecisionSolution
from .decision_solution_selector  import DecisionSolutionSelector
from .decision_solution_validator import DecisionSolutionValidator

_log = get_logger(__name__)


class DecisionOptimizer:
    """
    Executes the full optimization workflow for a set of candidates.

    The optimizer is stateless — all dependencies are injected or
    instantiated fresh per call.

    Parameters
    ----------
    constraint_engine : Evaluates constraints.
    scoring_engine :    Scores candidates against objectives.
    ranking_engine :    Ranks scored candidates.
    solution_selector : Selects the optimal candidate.
    solution_validator: Validates the selected solution.
    """

    def __init__(self) -> None:
        self._constraint_engine  = DecisionConstraintEngine()
        self._scoring_engine     = DecisionScoringEngine()
        self._ranking_engine     = DecisionRankingEngine()
        self._solution_selector  = DecisionSolutionSelector()
        self._solution_validator = DecisionSolutionValidator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(
        self,
        request_id:  str,
        decision_id: str,
        candidates:  List[DecisionCandidate],
        objectives:  List[DecisionObjective],
        constraints: List[DecisionConstraint],
        strategy:    DecisionOptimizationStrategy,
        context:     DecisionOptimizationContext,
    ) -> DecisionSolution:
        """
        Run the full optimization pipeline and return a
        :class:`DecisionSolution`.

        Raises
        ------
        :class:`NoCandidatesError` : When *candidates* is empty.
        :class:`NoFeasibleSolutionError` : When every candidate violates
            at least one hard constraint.
        """
        from .exceptions import NoCandidatesError, NoFeasibleSolutionError

        if not candidates:
            raise NoCandidatesError()

        t_start = time.time()

        # 1 — constraint evaluation for every candidate
        constraint_results: Dict[str, ConstraintEvaluationResult] = {}
        for candidate in candidates:
            cr = self._constraint_engine.evaluate_all(candidate, constraints, context)
            constraint_results[candidate.candidate_id] = cr

        # 2 — scoring (objectives + penalty)
        scores: List[CandidateScore] = self._scoring_engine.score_all(
            candidates, objectives, constraint_results, context
        )

        # 3 — ranking
        rankings: List[DecisionRanking] = self._ranking_engine.rank(scores)

        # 4 — selection
        selected = self._solution_selector.select(
            candidates, scores, rankings, strategy, context
        )

        if selected is None:
            raise NoFeasibleSolutionError(
                f"All {len(candidates)} candidate(s) violate hard constraints"
            )

        # 5 — gather per-candidate data for the selected candidate
        score_map = {s.candidate_id: s for s in scores}
        cr_map    = constraint_results
        sel_score = score_map.get(selected.candidate_id)
        sel_cr    = cr_map.get(selected.candidate_id)

        final_score      = sel_score.confidence_adjusted_score if sel_score else 0.0
        obj_scores       = sel_score.objective_scores if sel_score else {}
        is_feasible      = sel_cr.is_feasible if sel_cr else True
        violations       = sel_cr.violated_soft if sel_cr else ()
        sel_rank         = next(
            (r.rank for r in rankings if r.candidate_id == selected.candidate_id), 1
        )
        is_optimal       = sel_rank == 1 and is_feasible

        rationale = self._build_rationale(
            selected, sel_score, sel_cr, strategy, is_optimal, len(candidates)
        )

        solution = DecisionSolution(
            solution_id           = str(uuid.uuid4()),
            request_id            = request_id,
            decision_id           = decision_id,
            selected_candidate    = selected,
            final_score           = final_score,
            rank                  = sel_rank,
            rankings              = tuple(rankings),
            objective_scores      = obj_scores,
            constraint_violations = tuple(violations),
            optimization_strategy = strategy.name,
            rationale             = rationale,
            evaluation_time_s     = time.time() - t_start,
            generated_at          = datetime.now(timezone.utc),
            is_optimal            = is_optimal,
            is_feasible           = is_feasible,
        )

        # 6 — validate
        vr = self._solution_validator.validate(solution)
        if not vr.is_valid:
            _log.warning(
                f"DecisionOptimizer: solution validation failed for "
                f"{solution.solution_id!r}: {vr.error_messages}"
            )

        return solution

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_rationale(
        self,
        candidate: DecisionCandidate,
        score:     Optional[CandidateScore],
        cr:        Optional[ConstraintEvaluationResult],
        strategy:  DecisionOptimizationStrategy,
        is_optimal: bool,
        total:     int,
    ) -> str:
        parts = [
            f"Selected {candidate.symbol} {candidate.direction.upper()} "
            f"(qty={candidate.quantity}, price={candidate.price}) "
            f"via {strategy.name}."
        ]
        if score:
            parts.append(
                f"Score={score.confidence_adjusted_score:.4f} "
                f"(total={score.total_score:.4f}, penalty={score.constraint_penalty:.4f})."
            )
        if cr and cr.violated_soft:
            parts.append(
                f"Soft constraint warnings: {', '.join(cr.violated_soft)}."
            )
        parts.append(
            f"{'Optimal' if is_optimal else 'Best available'} "
            f"from {total} candidate(s)."
        )
        return " ".join(parts)
