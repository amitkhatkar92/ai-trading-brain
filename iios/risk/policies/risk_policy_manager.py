"""
risk_policy_manager.py — iios.risk.policies
=============================================
Internal evaluation manager for the Risk Policy Framework.

Orchestrates the full evaluation pipeline:
  load_policies → validate → evaluate_chain → resolve_conflicts
  → aggregate → generate_summary → generate_audit

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple

from .constants import DEFAULT_POLICY_ACTION, EvaluationMode, PolicyAction
from .risk_policy import RiskPolicy
from .risk_policy_audit import RiskPolicyAuditReport, RiskPolicyAuditor
from .risk_policy_chain import RiskPolicyChain
from .risk_policy_evaluator import RiskPolicyEvaluator
from .risk_policy_factory import RiskPolicyFactory
from .risk_policy_history import RiskPolicyHistory
from .risk_policy_priority import PolicyPriorityResolver
from .risk_policy_registry import RiskPolicyRegistry
from .risk_policy_request import RiskPolicyRequest
from .risk_policy_response import RiskEvaluationSummary, RiskPolicyResponse
from .risk_policy_result import RiskPolicyResult
from .risk_policy_statistics import RiskPolicyStatistics
from .risk_policy_validator import RiskPolicyValidator


class RiskPolicyManager:
    """
    Internal coordinator that runs the full policy evaluation pipeline for
    a single :class:`~.risk_policy_request.RiskPolicyRequest`.

    This is **not** part of the public API — callers should use
    :class:`~.risk_policy_engine.RiskPolicyEngine`.

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
        registry:   RiskPolicyRegistry,
        evaluator:  RiskPolicyEvaluator,
        chain:      RiskPolicyChain,
        validator:  RiskPolicyValidator,
        auditor:    RiskPolicyAuditor,
        statistics: RiskPolicyStatistics,
        history:    RiskPolicyHistory,
        factory:    RiskPolicyFactory,
    ) -> None:
        self._registry   = registry
        self._evaluator  = evaluator
        self._chain      = chain
        self._validator  = validator
        self._auditor    = auditor
        self._stats      = statistics
        self._history    = history
        self._factory    = factory

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def run_evaluation(self, request: RiskPolicyRequest) -> RiskPolicyResponse:
        """
        Execute the full evaluation pipeline and return a
        :class:`~.risk_policy_response.RiskPolicyResponse`.

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
                results: List[RiskPolicyResult] = []
                conflict_applied = False
                strategy_used = ""
            else:
                # Phase 3: Evaluate chain
                mode = self._resolve_mode(request)
                results = self._chain.evaluate(policies, request.inputs, mode)

                # Phase 4: Resolve conflicts
                conflict_applied = len(results) > 1
                dominant = PolicyPriorityResolver.resolve(results)
                final_action = dominant.action if dominant else DEFAULT_POLICY_ACTION
                strategy_used = self._describe_strategy(results, final_action)

            # Phase 5: Record stats
            self._record_action_stats(final_action)
            self._stats.record_policies_evaluated(len(results))

            # Phase 6: Generate summary
            dominant_result = PolicyPriorityResolver.resolve(results)
            summary = RiskEvaluationSummary.from_results(
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
            response = RiskPolicyResponse.create_success(
                request_id           = request.request_id,
                evaluation_id        = request.evaluation_id,
                portfolio_id         = request.portfolio_id,
                risk_id              = request.risk_id,
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
    # Pipeline phases
    # ------------------------------------------------------------------

    def _load_policies(self, request: RiskPolicyRequest) -> List[RiskPolicy]:
        """
        Return enabled policies matching the request's context policy_types.
        Empty policy_types list means all enabled policies.
        """
        policy_types = request.context.policy_types
        if not policy_types:
            return self._registry.list_enabled()
        result: List[RiskPolicy] = []
        for pt in policy_types:
            result.extend(self._registry.list_enabled_by_type(pt))
        return result

    @staticmethod
    def _resolve_mode(request: RiskPolicyRequest) -> EvaluationMode:
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
        results: List[RiskPolicyResult],
        final_action: PolicyAction,
    ) -> str:
        if not results:
            return ""
        from .constants import ConflictResolutionStrategy
        for strategy in (
            ConflictResolutionStrategy.IMMEDIATE_ACTION_OVERRIDES_ALL,
            ConflictResolutionStrategy.CRITICAL_OVERRIDES,
            ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES,
            ConflictResolutionStrategy.ESCALATION_OVERRIDES_CONDITIONAL,
            ConflictResolutionStrategy.HIGHEST_PRIORITY_WINS,
        ):
            if PolicyPriorityResolver.applies_strategy(results, strategy):
                return strategy.value
        return ConflictResolutionStrategy.HIGHEST_PRIORITY_WINS.value

    def _record_action_stats(self, action: PolicyAction) -> None:
        from .constants import PolicyAction as PA
        mapping = {
            PA.APPROVE:                  self._stats.record_approved,
            PA.APPROVE_WITH_CONDITIONS:  self._stats.record_conditionally_approved,
            PA.REJECT:                   self._stats.record_rejected,
            PA.BLOCK:                    self._stats.record_blocked,
            PA.ESCALATE:                 self._stats.record_escalated,
            PA.DEFER:                    self._stats.record_deferred,
            PA.REQUIRE_MANUAL_REVIEW:    self._stats.record_manual_review,
            PA.REQUIRE_IMMEDIATE_ACTION: self._stats.record_immediate_action,
        }
        fn = mapping.get(action)
        if fn:
            fn()

    def _failure_response(
        self,
        request: RiskPolicyRequest,
        message: str,
        elapsed: float,
    ) -> RiskPolicyResponse:
        response = RiskPolicyResponse.create_failure(
            request_id    = request.request_id,
            evaluation_id = request.evaluation_id,
            portfolio_id  = request.portfolio_id,
            risk_id       = request.risk_id,
            error_message = message,
            elapsed_s     = elapsed,
        )
        self._history.record_response(response)
        return response
