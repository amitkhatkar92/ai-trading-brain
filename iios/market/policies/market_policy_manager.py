"""
market_policy_manager.py — iios.market.policies
=================================================
Internal evaluation manager for the Market Policy Framework.

Orchestrates the full evaluation pipeline:
  load_policies → validate → evaluate_chain → resolve_conflicts
  → aggregate → generate_summary → generate_audit

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
from typing import List

from .constants import DEFAULT_POLICY_ACTION, EvaluationMode, PolicyAction
from .market_policy import MarketPolicy
from .market_policy_audit import MarketPolicyAuditReport, MarketPolicyAuditor
from .market_policy_chain import MarketPolicyChain
from .market_policy_evaluator import MarketPolicyEvaluator
from .market_policy_factory import MarketPolicyFactory
from .market_policy_history import MarketPolicyHistory
from .market_policy_priority import MarketPolicyPriorityResolver
from .market_policy_registry import MarketPolicyRegistry
from .market_policy_request import MarketPolicyRequest
from .market_policy_response import MarketEvaluationSummary, MarketPolicyResponse
from .market_policy_result import MarketPolicyResult
from .market_policy_statistics import MarketPolicyStatistics
from .market_policy_validator import MarketPolicyValidator


class MarketPolicyManager:
    """
    Internal coordinator that runs the full market policy evaluation pipeline for
    a single :class:`~.market_policy_request.MarketPolicyRequest`.

    This is **not** part of the public API — callers should use
    :class:`~.market_policy_engine.MarketPolicyEngine`.

    Parameters
    ----------
    registry :   Registered policies.
    evaluator :  Condition/rule evaluator.
    chain :      Multi-policy chain evaluator.
    validator :  Policy and request validator.
    auditor :    Audit report builder.
    statistics : Running statistics collector.
    history :    Bounded artefact history store.
    factory :    Object factory.
    """

    def __init__(
        self,
        registry:   MarketPolicyRegistry,
        evaluator:  MarketPolicyEvaluator,
        chain:      MarketPolicyChain,
        validator:  MarketPolicyValidator,
        auditor:    MarketPolicyAuditor,
        statistics: MarketPolicyStatistics,
        history:    MarketPolicyHistory,
        factory:    MarketPolicyFactory,
    ) -> None:
        self._registry  = registry
        self._evaluator = evaluator
        self._chain     = chain
        self._validator = validator
        self._auditor   = auditor
        self._stats     = statistics
        self._history   = history
        self._factory   = factory

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def run_evaluation(self, request: MarketPolicyRequest) -> MarketPolicyResponse:
        """
        Execute the full evaluation pipeline and return a
        :class:`~.market_policy_response.MarketPolicyResponse`.

        The pipeline never raises — any error produces a failure response.
        """
        start = time.perf_counter()
        self._stats.record_evaluation()
        self._history.record_request(request)

        try:
            # Phase 1: Validate request
            req_validation = self._validator.validate_request(request)
            if not req_validation.is_valid:
                return self._failure_response(
                    request,
                    f"Invalid request: {'; '.join(req_validation.failure_messages)}",
                    time.perf_counter() - start,
                )

            # Phase 2: Load applicable policies
            policies = self._load_policies(request)
            policies_loaded = len(policies)

            if not policies:
                # No policies — default approve
                final_action = DEFAULT_POLICY_ACTION
                results: List[MarketPolicyResult] = []
                conflict_applied = False
                strategy_used = ""
            else:
                # Phase 3: Evaluate chain
                mode = self._resolve_mode(request)
                results = self._chain.evaluate(policies, request.inputs, mode)

                # Phase 4: Resolve conflicts
                conflict_applied = len(results) > 1
                dominant = MarketPolicyPriorityResolver.resolve(results)
                final_action = dominant.action if dominant else DEFAULT_POLICY_ACTION
                strategy_used = self._describe_strategy(results, final_action)

            # Phase 5: Record stats
            self._record_action_stats(final_action)
            self._stats.record_policies_evaluated(len(results))

            # Phase 6: Generate summary
            dominant_result = MarketPolicyPriorityResolver.resolve(results)
            summary = MarketEvaluationSummary.from_results(
                tuple(results),
                final_action,
                dominant_policy_id   = dominant_result.policy_id   if dominant_result else "",
                dominant_policy_name = dominant_result.policy_name  if dominant_result else "",
                rationale            = (dominant_result.rationale   if dominant_result
                                        else "No policies registered — default approve"),
            )

            # Phase 7: Generate audit
            elapsed = time.perf_counter() - start
            audit = self._auditor.create_report(
                request,
                results,
                final_action,
                policies_loaded,
                elapsed,
                conflict_resolution_applied = conflict_applied,
                conflict_strategy_used      = strategy_used,
                final_rationale             = summary.rationale,
            )
            self._stats.record_evaluation_time(elapsed)

            # Phase 8: Build response
            response = MarketPolicyResponse.create_success(
                request_id           = request.request_id,
                evaluation_id        = request.evaluation_id,
                market_analysis_id   = request.market_analysis_id,
                exchange             = request.exchange,
                final_action         = final_action,
                results              = tuple(results),
                summary              = summary,
                evaluation_elapsed_s = elapsed,
            )
            self._history.record_response(response)
            self._history.record_audit(audit)
            return response

        except Exception as exc:
            elapsed = time.perf_counter() - start
            self._stats.record_evaluation_time(elapsed)
            return self._failure_response(request, str(exc), elapsed)

    # ------------------------------------------------------------------
    # Pipeline helpers
    # ------------------------------------------------------------------

    def _load_policies(self, request: MarketPolicyRequest) -> List[MarketPolicy]:
        """
        Return enabled policies matching the request's context policy_types.
        Empty policy_types list means all enabled policies.
        """
        policy_types = request.context.policy_types
        if not policy_types:
            return self._registry.list_enabled()
        result: List[MarketPolicy] = []
        for pt in policy_types:
            result.extend(self._registry.list_enabled_by_type(pt))
        return result

    @staticmethod
    def _resolve_mode(request: MarketPolicyRequest) -> EvaluationMode:
        """Determine the evaluation mode for this request."""
        mode_raw = request.metadata.get("evaluation_mode")
        if mode_raw:
            try:
                return EvaluationMode(mode_raw)
            except ValueError:
                pass
        return EvaluationMode.SEQUENTIAL

    @staticmethod
    def _describe_strategy(
        results: List[MarketPolicyResult],
        final_action: PolicyAction,
    ) -> str:
        if not results:
            return "no_policies"
        if any(r.action == PolicyAction.BLOCK for r in results):
            return "block_overrides_all"
        denying = [r for r in results if r.action == PolicyAction.REJECT]
        if denying:
            return "explicit_deny_overrides"
        if any(r.action == PolicyAction.ESCALATE for r in results):
            return "escalation_overrides_conditional"
        return "highest_priority_wins"

    def _record_action_stats(self, action: PolicyAction) -> None:
        if action == PolicyAction.APPROVE:
            self._stats.record_approved()
        elif action == PolicyAction.APPROVE_WITH_CONDITIONS:
            self._stats.record_conditionally_approved()
        elif action == PolicyAction.REJECT:
            self._stats.record_rejected()
        elif action == PolicyAction.BLOCK:
            self._stats.record_blocked()
        elif action == PolicyAction.ESCALATE:
            self._stats.record_escalated()
        elif action == PolicyAction.DEFER:
            self._stats.record_deferred()
        elif action == PolicyAction.REQUIRE_MANUAL_REVIEW:
            self._stats.record_manual_review()

    def _failure_response(
        self,
        request: MarketPolicyRequest,
        error:   str,
        elapsed: float,
    ) -> MarketPolicyResponse:
        return MarketPolicyResponse.create_failure(
            request_id           = request.request_id,
            evaluation_id        = request.evaluation_id,
            market_analysis_id   = request.market_analysis_id,
            exchange             = request.exchange,
            error_message        = error,
            evaluation_elapsed_s = elapsed,
        )
