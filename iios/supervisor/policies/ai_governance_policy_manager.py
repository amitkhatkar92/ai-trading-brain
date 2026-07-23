"""
ai_governance_policy_manager.py — iios.supervisor.policies
------------------------------------------------------------
Governance evaluation orchestrator.

Pipeline (for every :meth:`run_evaluation` call):
  1. Validate request
  2. Load policies (filter by type + enabled)
  3. Evaluate chain
  4. Resolve policy conflicts
  5. Apply enterprise priority overrides
  6. Generate governance decision summary
  7. Generate audit report
  8. Build response

Never raises — any exception → create_failure response with
EMERGENCY_STOP as the safe default.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple

from .constants import (
    ACTION_SEVERITY,
    AIGovernancePolicyAction,
    DEFAULT_GOVERNANCE_ACTION,
    DENY_ACTIONS,
    EvaluationMode,
    HUMAN_REVIEW_ACTIONS,
    STOP_ACTIONS,
    PolicyPriority,
)
from .ai_governance_policy_audit import AIGovernancePolicyAuditGenerator, GovernanceAuditReport
from .ai_governance_policy_chain import AIGovernancePolicyChain
from .ai_governance_policy_evaluator import AIGovernancePolicyEvaluator
from .ai_governance_policy_factory import AIGovernancePolicyFactory
from .ai_governance_policy_history import AIGovernancePolicyHistory
from .ai_governance_policy_registry import AIGovernancePolicyRegistry
from .ai_governance_policy_request import AIGovernancePolicyRequest
from .ai_governance_policy_response import (
    AIGovernancePolicyResponse,
    GovernanceDecisionSummary,
)
from .ai_governance_policy_result import AIGovernancePolicyResult
from .ai_governance_policy_statistics import AIGovernancePolicyStatistics
from .ai_governance_policy_validator import AIGovernancePolicyValidator


class AIGovernancePolicyManager:
    """
    Orchestrates governance policy evaluation for a single request.

    All subsystems are injectable for testability.
    """

    def __init__(
        self,
        registry:   Optional[AIGovernancePolicyRegistry]   = None,
        evaluator:  Optional[AIGovernancePolicyEvaluator]  = None,
        chain:      Optional[AIGovernancePolicyChain]       = None,
        validator:  Optional[AIGovernancePolicyValidator]  = None,
        statistics: Optional[AIGovernancePolicyStatistics] = None,
        history:    Optional[AIGovernancePolicyHistory]    = None,
        factory:    Optional[AIGovernancePolicyFactory]    = None,
        audit_gen:  Optional[AIGovernancePolicyAuditGenerator] = None,
    ) -> None:
        self._registry   = registry   or AIGovernancePolicyRegistry()
        self._evaluator  = evaluator  or AIGovernancePolicyEvaluator()
        self._chain      = chain      or AIGovernancePolicyChain(self._evaluator)
        self._validator  = validator  or AIGovernancePolicyValidator()
        self._statistics = statistics or AIGovernancePolicyStatistics()
        self._history    = history    or AIGovernancePolicyHistory()
        self._factory    = factory    or AIGovernancePolicyFactory()
        self._audit_gen  = audit_gen  or AIGovernancePolicyAuditGenerator()

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def run_evaluation(
        self, request: AIGovernancePolicyRequest
    ) -> AIGovernancePolicyResponse:
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
                response = AIGovernancePolicyResponse.create_failure(
                    request_id           = request.request_id,
                    supervision_id       = request.supervision_id,
                    subsystem_id         = request.subsystem_id,
                    error_message        = f"Validation failed: {reason}",
                    evaluation_elapsed_s = elapsed,
                )
                self._history.record_response(response)
                return response

            # 2. Load policies (filter by type + enabled)
            all_enabled = self._registry.enabled_policies()
            if request.policy_types:
                filtered = [
                    p for p in all_enabled
                    if p.policy_type in request.policy_types
                ]
                skipped = len(all_enabled) - len(filtered)
            else:
                filtered = all_enabled
                skipped  = 0

            total_loaded = len(filtered) + skipped

            # 3. Evaluate chain (SEQUENTIAL with emergency-stop priority)
            results: List[AIGovernancePolicyResult] = self._chain.evaluate(
                filtered,
                dict(request.inputs),
                EvaluationMode.SEQUENTIAL,
            )

            # 4. Resolve conflicts + apply enterprise priority overrides
            (
                final_action,
                dominant_policy_id,
                dominant_policy_name,
                rationale,
                conflict_applied,
            ) = self._resolve_conflicts(results)

            # 5. Build decision summary
            summary = GovernanceDecisionSummary.from_results(
                tuple(results),
                final_action,
                dominant_policy_id   = dominant_policy_id,
                dominant_policy_name = dominant_policy_name,
                rationale            = rationale,
            )

            elapsed = time.perf_counter() - start

            # 6. Build response
            response = AIGovernancePolicyResponse.create_success(
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

            # 7. Generate audit report
            audit_report = self._audit_gen.generate(
                request,
                results,
                response,
                total_policies_loaded       = total_loaded,
                dominant_policy_id          = dominant_policy_id,
                dominant_policy_name        = dominant_policy_name,
                conflict_resolution_applied = conflict_applied,
            )
            self._history.record_audit(audit_report)

            # 8. Update statistics
            self._statistics.record_success(elapsed)
            self._statistics.record_policies_evaluated(len(results))
            self._update_action_stats(final_action)

            self._history.record_response(response)
            return response

        except Exception as exc:  # pylint: disable=broad-except
            elapsed = time.perf_counter() - start
            self._statistics.record_failure()
            self._statistics.record_emergency_stop()
            response = AIGovernancePolicyResponse.create_failure(
                request_id           = request.request_id,
                supervision_id       = request.supervision_id,
                subsystem_id         = request.subsystem_id,
                error_message        = str(exc),
                evaluation_elapsed_s = elapsed,
            )
            self._history.record_response(response)
            return response

    # ------------------------------------------------------------------
    # Conflict resolution
    # ------------------------------------------------------------------

    def _resolve_conflicts(
        self,
        results: List[AIGovernancePolicyResult],
    ) -> Tuple[AIGovernancePolicyAction, str, str, str, bool]:
        """
        Determine the final governance action using enterprise conflict rules.

        Conflict Resolution Order (spec-compliant):
        1. EMERGENCY_STOP overrides all
        2. CRITICAL priority + deny action overrides all remaining
        3. BLOCK overrides REJECT
        4. REQUIRE_HUMAN_APPROVAL overrides automation
        5. Highest ACTION_SEVERITY wins; ties broken by priority (lower=higher)

        Returns
        -------
        (final_action, dominant_policy_id, dominant_policy_name, rationale, conflict_applied)
        """
        if not results:
            return (
                DEFAULT_GOVERNANCE_ACTION, "", "",
                "No policies evaluated — default action applied",
                False,
            )

        # Rule 1: EMERGENCY_STOP overrides all
        emergency = [r for r in results if r.action in STOP_ACTIONS]
        if emergency:
            dom = min(emergency, key=lambda r: r.priority.value)
            return (
                AIGovernancePolicyAction.EMERGENCY_STOP,
                dom.policy_id, dom.policy_name,
                f"EMERGENCY STOP — {dom.rationale}",
                True,
            )

        # Rule 2: CRITICAL priority + deny action
        critical_denies = [
            r for r in results
            if r.priority == PolicyPriority.CRITICAL and r.action in DENY_ACTIONS
        ]
        if critical_denies:
            dom = max(critical_denies, key=lambda r: ACTION_SEVERITY.get(r.action, 0))
            return (
                dom.action, dom.policy_id, dom.policy_name,
                f"CRITICAL policy override — {dom.rationale}",
                True,
            )

        # Rules 3-5: highest severity wins, ties broken by priority
        dom = max(
            results,
            key=lambda r: (
                ACTION_SEVERITY.get(r.action, 0),
                -r.priority.value,  # lower value = higher priority
            ),
        )
        conflict_applied = len({ACTION_SEVERITY.get(r.action, 0) for r in results}) > 1
        return (
            dom.action, dom.policy_id, dom.policy_name,
            dom.rationale,
            conflict_applied,
        )

    # ------------------------------------------------------------------
    # Statistics helpers
    # ------------------------------------------------------------------

    def _update_action_stats(self, action: AIGovernancePolicyAction) -> None:
        if action == AIGovernancePolicyAction.APPROVE:
            self._statistics.record_approved()
        elif action == AIGovernancePolicyAction.APPROVE_WITH_CONDITIONS:
            self._statistics.record_conditionally_approved()
        elif action == AIGovernancePolicyAction.REJECT:
            self._statistics.record_rejected()
        elif action == AIGovernancePolicyAction.BLOCK:
            self._statistics.record_blocked()
        elif action == AIGovernancePolicyAction.ESCALATE:
            self._statistics.record_escalated()
        elif action == AIGovernancePolicyAction.REQUIRE_HUMAN_APPROVAL:
            self._statistics.record_human_review()
        elif action == AIGovernancePolicyAction.REQUIRE_MANUAL_REVIEW:
            self._statistics.record_manual_review()
        elif action == AIGovernancePolicyAction.EMERGENCY_STOP:
            self._statistics.record_emergency_stop()
