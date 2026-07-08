"""
iios/decisions/workflow/decision_workflow.py
=============================================
DecisionWorkflow — executes the 10-stage decision pipeline.

Stage order:
  1  RECEIVE      — intake and log the request
  2  VALIDATE     — structural validation of the request
  3  GENERATE     — derive DecisionCandidates from options / payload
  4  EVALUATE     — score every candidate
  5  POLICY_CHECK — apply all registered policies
  6  SCORE        — compute composite score (already done in EVALUATE)
  7  RANK         — sort candidates by score
  8  SELECT       — pick the best candidate
  9  EXPLAIN      — attach rationale
 10  PUBLISH      — build Decision, persist via callback
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from ..decision_constants import (
    CandidateStatus,
    DecisionPriority,
    DecisionType,
    WorkflowStage,
)
from ..decision_context import stage_scope, workflow_scope
from ..decision_exceptions import (
    InvalidDecisionRequestError,
    NoCandidatesError,
    WorkflowAbortedError,
    WorkflowStageFailedError,
)
from ..evaluation.decision_evaluator import DecisionEvaluator
from ..evaluation.decision_ranker import DecisionRanker
from ..models.decision import Decision
from ..models.decision_candidate import DecisionCandidate
from ..models.decision_option import DecisionOption
from ..models.decision_request import DecisionRequest
from ..models.decision_result import DecisionResult, StageRecord
from ..policies.decision_policy import DecisionPolicy
from .decision_factory import DecisionFactory


class DecisionWorkflow:
    """
    Executes the full 10-stage decision pipeline for one DecisionRequest.

    Injected dependencies:
    - ``evaluator``  : DecisionEvaluator
    - ``ranker``     : DecisionRanker
    - ``factory``    : DecisionFactory
    - ``policies``   : list of registered DecisionPolicy objects
    - ``on_publish`` : optional callback(Decision) → None
    """

    def __init__(
        self,
        evaluator:  DecisionEvaluator,
        ranker:     DecisionRanker,
        factory:    DecisionFactory,
        policies:   list[DecisionPolicy],
        on_publish: Callable[[Decision], None] | None = None,
    ) -> None:
        self._evaluator  = evaluator
        self._ranker     = ranker
        self._factory    = factory
        self._policies   = policies
        self._on_publish = on_publish

    # -- Public ────────────────────────────────────────────────────────────────

    def run(self, request: DecisionRequest) -> DecisionResult:
        """Execute all 10 stages and return a DecisionResult."""
        result = DecisionResult(request_id=request.request_id)
        t_start = time.perf_counter()

        with workflow_scope(
            request.request_id,
            decision_type = request.decision_type,
            source_id     = request.source_id,
            priority      = request.priority,
        ):
            try:
                # 1 – RECEIVE
                self._stage_receive(request, result)
                # 2 – VALIDATE
                self._stage_validate(request, result)
                # 3 – GENERATE
                candidates = self._stage_generate(request, result)
                # 4 – EVALUATE
                candidates = self._stage_evaluate(candidates, request, result)
                # 5 – POLICY_CHECK
                candidates = self._stage_policy_check(candidates, request, result)
                # 6 – SCORE (composite already computed in EVALUATE; update stats)
                self._stage_score(candidates, result)
                # 7 – RANK
                ranked = self._stage_rank(candidates, result)
                # 8 – SELECT
                selected = self._stage_select(ranked, result)
                # 9 – EXPLAIN
                self._stage_explain(selected, ranked, result)
                # 10 – PUBLISH
                decision = self._stage_publish(request, ranked, selected, result)

                result.decision          = decision
                result.total_candidates  = len(candidates)
                result.policy_pass_count = sum(1 for c in candidates if not c.has_policy_failure)
                result.policy_fail_count = sum(1 for c in candidates if c.has_policy_failure)
                result.succeeded         = decision.is_completed

            except (InvalidDecisionRequestError, NoCandidatesError) as exc:
                result.errors.append(str(exc))
                result.succeeded = False
                result.decision.fail(str(exc))

            except Exception as exc:
                result.errors.append(f"Unexpected workflow error: {exc}")
                result.succeeded = False
                result.decision.fail(str(exc))

        result.total_elapsed_ms = (time.perf_counter() - t_start) * 1_000.0
        return result

    # -- Stages ────────────────────────────────────────────────────────────────

    def _stage_receive(self, request: DecisionRequest, result: DecisionResult) -> None:
        t0 = time.perf_counter()
        with stage_scope(WorkflowStage.RECEIVE):
            # Just log receipt — no logic
            note = f"Received request {request.request_id!r} from {request.source_id!r}"
        result.add_stage(WorkflowStage.RECEIVE, True, (time.perf_counter() - t0) * 1e3, note)

    def _stage_validate(self, request: DecisionRequest, result: DecisionResult) -> None:
        t0 = time.perf_counter()
        with stage_scope(WorkflowStage.VALIDATE):
            if not request.request_id:
                raise InvalidDecisionRequestError("request_id is empty")
            if request.is_expired():
                raise InvalidDecisionRequestError(
                    f"Request {request.request_id!r} has expired (TTL={request.ttl_s}s)"
                )
        result.add_stage(WorkflowStage.VALIDATE, True, (time.perf_counter() - t0) * 1e3)

    def _stage_generate(
        self,
        request: DecisionRequest,
        result:  DecisionResult,
    ) -> list[DecisionCandidate]:
        t0 = time.perf_counter()
        candidates: list[DecisionCandidate] = []

        with stage_scope(WorkflowStage.GENERATE):
            if request.options:
                # Use caller-supplied options
                for opt in request.options:
                    candidates.append(DecisionCandidate(
                        request_id = request.request_id,
                        option     = opt,
                    ))
            else:
                # Auto-generate one generic option per DecisionType value
                # (generic fallback when no options are provided)
                for dt in DecisionType:
                    if dt == DecisionType.GENERIC:
                        continue
                    opt = DecisionOption(
                        name        = dt.value.capitalize(),
                        option_type = dt,
                        description = f"Auto-generated {dt.value} option",
                        confidence  = 0.5,
                        risk_score  = 0.5,
                    )
                    candidates.append(DecisionCandidate(
                        request_id = request.request_id,
                        option     = opt,
                    ))

            if not candidates:
                raise NoCandidatesError(request.request_id)

        result.add_stage(
            WorkflowStage.GENERATE, True,
            (time.perf_counter() - t0) * 1e3,
            f"{len(candidates)} candidate(s) generated",
        )
        return candidates

    def _stage_evaluate(
        self,
        candidates: list[DecisionCandidate],
        request:    DecisionRequest,
        result:     DecisionResult,
    ) -> list[DecisionCandidate]:
        t0 = time.perf_counter()
        with stage_scope(WorkflowStage.EVALUATE):
            for c in candidates:
                self._evaluator.evaluate(c, request)
        result.add_stage(
            WorkflowStage.EVALUATE, True,
            (time.perf_counter() - t0) * 1e3,
            f"{len(candidates)} candidate(s) evaluated",
        )
        return candidates

    def _stage_policy_check(
        self,
        candidates: list[DecisionCandidate],
        request:    DecisionRequest,
        result:     DecisionResult,
    ) -> list[DecisionCandidate]:
        t0 = time.perf_counter()
        with stage_scope(WorkflowStage.POLICY_CHECK):
            for c in candidates:
                for policy in self._policies:
                    outcome, reason = policy.apply(c, request)
                    c.add_policy_result(policy.name, outcome, reason)
        result.add_stage(
            WorkflowStage.POLICY_CHECK, True,
            (time.perf_counter() - t0) * 1e3,
            f"{len(self._policies)} policy/policies applied",
        )
        return candidates

    def _stage_score(
        self,
        candidates: list[DecisionCandidate],
        result:     DecisionResult,
    ) -> None:
        t0 = time.perf_counter()
        # Composite scores are already set by EVALUATE stage.
        with stage_scope(WorkflowStage.SCORE):
            pass
        result.add_stage(
            WorkflowStage.SCORE, True,
            (time.perf_counter() - t0) * 1e3,
            "Composite scores confirmed",
        )

    def _stage_rank(
        self,
        candidates: list[DecisionCandidate],
        result:     DecisionResult,
    ) -> list[DecisionCandidate]:
        t0 = time.perf_counter()
        with stage_scope(WorkflowStage.RANK):
            ranked = self._ranker.rank(candidates)
        result.add_stage(
            WorkflowStage.RANK, True,
            (time.perf_counter() - t0) * 1e3,
            f"Ranked {len(ranked)} candidate(s)",
        )
        return ranked

    def _stage_select(
        self,
        ranked:  list[DecisionCandidate],
        result:  DecisionResult,
    ) -> DecisionCandidate | None:
        t0 = time.perf_counter()
        with stage_scope(WorkflowStage.SELECT):
            selected = self._ranker.select_best(ranked)
        note = (
            f"Selected candidate {selected.candidate_id[:8]}…"
            if selected else "No candidate selected (all failed policies)"
        )
        result.add_stage(WorkflowStage.SELECT, selected is not None,
                         (time.perf_counter() - t0) * 1e3, note)
        return selected

    def _stage_explain(
        self,
        selected: DecisionCandidate | None,
        ranked:   list[DecisionCandidate],
        result:   DecisionResult,
    ) -> None:
        t0 = time.perf_counter()
        with stage_scope(WorkflowStage.EXPLAIN):
            # Rationale is built inside the factory; nothing extra needed here.
            pass
        result.add_stage(WorkflowStage.EXPLAIN, True, (time.perf_counter() - t0) * 1e3)

    def _stage_publish(
        self,
        request:  DecisionRequest,
        ranked:   list[DecisionCandidate],
        selected: DecisionCandidate | None,
        result:   DecisionResult,
    ) -> Decision:
        t0 = time.perf_counter()
        with stage_scope(WorkflowStage.PUBLISH):
            decision = self._factory.build(
                request           = request,
                ranked_candidates = ranked,
                selected          = selected,
                warnings          = list(result.warnings),
                errors            = list(result.errors),
            )
            if self._on_publish:
                self._on_publish(decision)
        result.add_stage(
            WorkflowStage.PUBLISH, True,
            (time.perf_counter() - t0) * 1e3,
            f"Decision {decision.decision_id[:8]}… published",
        )
        return decision
