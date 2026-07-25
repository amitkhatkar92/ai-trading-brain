"""
governance_policy_manager.py — iios.supervisor.policy
-------------------------------------------------------
Evaluation orchestrator for the governance policy framework.

Pipeline:
  1. validate_request
  2. load policies (filter by type + enabled)
  3. chain.evaluate
  4. resolve_conflicts
  5. build_summary
  6. build_response

Never raises — all exceptions → create_failure response.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
from typing import List, Optional

from .constants import (
    ACTION_SEVERITY,
    DEFAULT_POLICY_ACTION,
    DENY_ACTIONS,
    EvaluationMode,
    PolicyAction,
)
from .governance_policy_chain import GovernancePolicyChain
from .governance_policy_evaluator import GovernancePolicyEvaluator
from .governance_policy_factory import GovernancePolicyFactory
from .governance_policy_history import GovernancePolicyHistory
from .governance_policy_registry import GovernancePolicyRegistry
from .governance_policy_request import GovernancePolicyRequest
from .governance_policy_response import (
    GovernanceEvaluationSummary,
    GovernancePolicyResponse,
)
from .governance_policy_result import GovernancePolicyResult
from .governance_policy_statistics import GovernancePolicyStatistics
from .governance_policy_validation import GovernancePolicyValidator


class GovernancePolicyManager:
    """
    Orchestrates governance policy evaluation for a single request.

    Parameters
    ----------
    registry :   Policy registry.
    evaluator :  Individual policy evaluator.
    chain :      Multi-policy chain evaluator.
    validator :  Request / policy validator.
    statistics : Statistics accumulator.
    history :    Evaluation history store.
    factory :    Object factory (for default request construction).
    """

    def __init__(
        self,
        registry:   Optional[GovernancePolicyRegistry]   = None,
        evaluator:  Optional[GovernancePolicyEvaluator]  = None,
        chain:      Optional[GovernancePolicyChain]      = None,
        validator:  Optional[GovernancePolicyValidator]  = None,
        statistics: Optional[GovernancePolicyStatistics] = None,
        history:    Optional[GovernancePolicyHistory]    = None,
        factory:    Optional[GovernancePolicyFactory]    = None,
    ) -> None:
        self._registry   = registry   or GovernancePolicyRegistry()
        self._evaluator  = evaluator  or GovernancePolicyEvaluator()
        self._chain      = chain      or GovernancePolicyChain(self._evaluator)
        self._validator  = validator  or GovernancePolicyValidator()
        self._statistics = statistics or GovernancePolicyStatistics()
        self._history    = history    or GovernancePolicyHistory()
        self._factory    = factory    or GovernancePolicyFactory()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_evaluation(
        self, request: GovernancePolicyRequest
    ) -> GovernancePolicyResponse:
        """Run a full evaluation pipeline. Never raises."""
        start = time.perf_counter()
        self._statistics.record_evaluation()
        self._history.record_request(request)

        try:
            # 1. Validate request
            validation = self._validator.validate_request(request)
            if not validation.is_valid:
                elapsed = time.perf_counter() - start
                self._statistics.record_failure()
                reason = "; ".join(validation.failure_messages)
                response = GovernancePolicyResponse.create_failure(
                    request_id     = request.request_id,
                    supervision_id = request.supervision_id,
                    subsystem_id   = request.subsystem_id,
                    error_message  = f"Validation failed: {reason}",
                    evaluation_elapsed_s = elapsed,
                )
                self._history.record_response(response)
                return response

            # 2. Load policies (filter by type and enabled)
            all_policies = self._registry.enabled_policies()
            if request.policy_types:
                filtered = [
                    p for p in all_policies
                    if p.policy_type in request.policy_types
                ]
                skipped = len(all_policies) - len(filtered)
            else:
                filtered = all_policies
                skipped  = 0

            # 3. Evaluate chain
            results: List[GovernancePolicyResult] = self._chain.evaluate(
                filtered,
                dict(request.inputs),
                EvaluationMode.SEQUENTIAL,
            )

            # 4. Resolve conflicts
            final_action, dominant_policy_id, dominant_policy_name, rationale = (
                self._resolve_conflicts(results)
            )

            # 5. Build summary
            summary = GovernanceEvaluationSummary.from_results(
                tuple(results),
                final_action,
                dominant_policy_id   = dominant_policy_id,
                dominant_policy_name = dominant_policy_name,
                rationale            = rationale,
            )

            elapsed = time.perf_counter() - start

            # 6. Build response
            response = GovernancePolicyResponse.create_success(
                request_id           = request.request_id,
                supervision_id       = request.supervision_id,
                subsystem_id         = request.subsystem_id,
                final_action         = final_action,
                results              = tuple(results),
                summary              = summary,
                policies_evaluated   = len(results),
                policies_skipped     = skipped,
                evaluation_elapsed_s = elapsed,
            )

            # Stats
            self._statistics.record_success(elapsed)
            self._statistics.record_policies_evaluated(len(results))
            if final_action in DENY_ACTIONS:
                self._statistics.record_denied()
            else:
                self._statistics.record_approved()

            self._history.record_response(response)
            return response

        except Exception as exc:  # pylint: disable=broad-except
            elapsed = time.perf_counter() - start
            self._statistics.record_failure()
            response = GovernancePolicyResponse.create_failure(
                request_id     = request.request_id,
                supervision_id = request.supervision_id,
                subsystem_id   = request.subsystem_id,
                error_message  = str(exc),
                evaluation_elapsed_s = elapsed,
            )
            self._history.record_response(response)
            return response

    # ------------------------------------------------------------------
    # Conflict resolution
    # ------------------------------------------------------------------

    def _resolve_conflicts(
        self, results: List[GovernancePolicyResult]
    ) -> tuple:
        """
        Determine the governing final action.

        Highest-severity action wins.
        Ties broken by PolicyPriority (lower value = higher priority).
        """
        if not results:
            return DEFAULT_POLICY_ACTION, "", "", "No policies evaluated — default applied"

        dominant = max(
            results,
            key=lambda r: (
                ACTION_SEVERITY.get(r.action, 0),
                -r.priority.value,   # lower value → more dominant
            ),
        )
        return (
            dominant.action,
            dominant.policy_id,
            dominant.policy_name,
            dominant.rationale,
        )
