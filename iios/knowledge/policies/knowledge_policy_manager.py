"""
knowledge_policy_manager.py — iios.knowledge.policies
-------------------------------------------------------
KnowledgePolicyWorkflowManager — internal governance workflow orchestrator.

THIS IS AN INTERNAL MODULE — NOT PART OF THE PUBLIC API.

Orchestrates the 6-phase governance workflow:
  1. Validate Request       — structural validation of the policy request
  2. Load Policies          — load ACTIVE policies from registry
  3. Evaluate Policies      — evaluate each policy against artifacts
  4. Resolve Conflicts      — aggregate decisions via PolicyPriorityResolver
  5. Generate Audit Trail   — record all decisions in the audit log
  6. Build Response         — construct KnowledgePolicyResponse

NEVER RAISES.  All exceptions are caught and returned as failure responses.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from iios.common.logging.logging_manager import get_logger

from .constants import ACTOR_GOVERNANCE, GovernanceDecision
from .knowledge_policy_audit import KnowledgePolicyAudit, PolicyAuditEntry
from .knowledge_policy_evaluator import KnowledgePolicyEvaluator
from .knowledge_policy_events import (
    GovernancePolicyEventBus,
    make_governance_completed,
    make_governance_started,
)
from .knowledge_policy_history import KnowledgeGovernanceHistory
from .knowledge_policy_priority import PolicyPriorityResolver
from .knowledge_policy_registry import KnowledgePolicyRegistry
from .knowledge_policy_request import KnowledgePolicyRequest
from .knowledge_policy_response import GovernanceDecisionRecord, KnowledgePolicyResponse
from .knowledge_policy_result import PolicyEvaluationResult
from .knowledge_policy_statistics import KnowledgeGovernanceStatistics
from .knowledge_policy_validator import KnowledgeGovernanceValidator

_log = get_logger(__name__)


class KnowledgePolicyWorkflowManager:
    """
    Coordinates the 6-phase knowledge governance workflow.

    NEVER RAISES.  All exceptions are caught and returned as failure responses.
    """

    def __init__(
        self,
        *,
        evaluator:  KnowledgePolicyEvaluator,
        registry:   KnowledgePolicyRegistry,
        validator:  KnowledgeGovernanceValidator,
        resolver:   PolicyPriorityResolver,
        audit:      KnowledgePolicyAudit,
        statistics: KnowledgeGovernanceStatistics,
        history:    KnowledgeGovernanceHistory,
        event_bus:  GovernancePolicyEventBus,
    ) -> None:
        self._evaluator  = evaluator
        self._registry   = registry
        self._validator  = validator
        self._resolver   = resolver
        self._audit      = audit
        self._statistics = statistics
        self._history    = history
        self._event_bus  = event_bus

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run_governance(
        self,
        request: KnowledgePolicyRequest,
    ) -> KnowledgePolicyResponse:
        """
        Run the full 6-phase governance workflow.

        Returns KnowledgePolicyResponse.  NEVER RAISES.
        """
        start = time.time()
        try:
            return self._run(request, start)
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            _log.error(
                f"Governance workflow error: "
                f"knowledge_id={request.knowledge_id!r} error={exc!r}"
            )
            return self._fail(request, str(exc), elapsed)

    # ------------------------------------------------------------------
    # Workflow phases
    # ------------------------------------------------------------------

    def _run(
        self,
        request: KnowledgePolicyRequest,
        start:   float,
    ) -> KnowledgePolicyResponse:

        # Phase 1: Validate request
        validation = self._validator.validate_request(request)
        failures   = [v for v in validation if not v.passed]
        if failures:
            elapsed = (time.time() - start) * 1000
            return self._fail(
                request,
                "; ".join(f.message for f in failures),
                elapsed,
            )

        # Phase 2: Load ACTIVE policies
        self._event_bus.emit(
            make_governance_started(request.knowledge_id, request.subsystem_id)
        )
        active_policies = self._registry.active_only()

        if not active_policies:
            # No active policies → approve by default
            elapsed = (time.time() - start) * 1000
            return KnowledgePolicyResponse.success(
                request_id    = request.request_id,
                knowledge_id  = request.knowledge_id,
                decision      = GovernanceDecision.APPROVED,
                decisions     = [],
                warnings      = ["No active policies — approved by default"],
                evaluation_ms = elapsed,
            )

        # Phase 3: Evaluate policies
        eval_results: List[PolicyEvaluationResult] = []
        for policy in active_policies:
            result = self._evaluator.evaluate(
                policy,
                request.artifacts,
                request.context,
            )
            eval_results.append(result)
            self._history.record(result)

        # Phase 4: Resolve conflicts
        aggregate_decision, reason = self._resolver.resolve(eval_results)

        # Phase 5: Audit trail
        elapsed = (time.time() - start) * 1000
        decision_records: List[GovernanceDecisionRecord] = []
        audit_trail:      List[Dict[str, Any]]           = []

        for result in eval_results:
            dr = GovernanceDecisionRecord.from_evaluation_result(
                result, request.knowledge_id, request.subsystem_id,
            )
            decision_records.append(dr)

            entry = PolicyAuditEntry.create(
                knowledge_id    = request.knowledge_id,
                subsystem_id    = request.subsystem_id,
                policy_id       = result.policy_id,
                policy_name     = result.policy_name,
                decision        = result.decision,
                actor           = request.actor,
                reason          = result.reason,
                evaluation_ms   = elapsed,
                artifacts_count = len(request.artifacts),
            )
            self._audit.record(entry)
            audit_trail.append(entry.to_dict())
            self._statistics.record_evaluation(result.decision.value, elapsed)

        # Phase 6: Emit completion event + build response
        self._event_bus.emit(
            make_governance_completed(
                request.knowledge_id,
                request.subsystem_id,
                decision = aggregate_decision,
                reason   = reason,
            )
        )

        return KnowledgePolicyResponse.success(
            request_id    = request.request_id,
            knowledge_id  = request.knowledge_id,
            decision      = aggregate_decision,
            decisions     = decision_records,
            evaluation_ms = elapsed,
            audit_trail   = audit_trail,
        )

    # ------------------------------------------------------------------
    # Failure helper
    # ------------------------------------------------------------------

    def _fail(
        self,
        request:       KnowledgePolicyRequest,
        error_message: str,
        elapsed_ms:    float = 0.0,
    ) -> KnowledgePolicyResponse:
        return KnowledgePolicyResponse.failure(
            request_id    = request.request_id,
            knowledge_id  = request.knowledge_id,
            errors        = [error_message],
            decision      = GovernanceDecision.REJECTED,
            evaluation_ms = elapsed_ms,
        )
