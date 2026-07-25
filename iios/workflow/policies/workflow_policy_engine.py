"""
workflow_policy_engine.py — iios.workflow.policies
---------------------------------------------------
WorkflowPolicyEngine — central governance evaluation engine.

The engine orchestrates the full governance pipeline:
  1. Load applicable policies from the registry
  2. Evaluate the policy chain (sequential by default)
  3. Resolve conflicts to produce a single winning action
  4. Generate a governance decision
  5. Record an audit entry
  6. Update statistics and history
  7. Emit domain events
  8. Return a WorkflowPolicyResponse

The engine NEVER raises exceptions for governance-level decisions.
Rejections, blocks, and emergency-stops are expressed as decisions.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_POLICY_ENGINE,
    PolicyEventType,
    PolicyType,
)
from .exceptions import WorkflowPolicyEngineError
from .workflow_policy import WorkflowPolicy
from .workflow_policy_audit import WorkflowPolicyAudit
from .workflow_policy_chain import WorkflowPolicyChain
from .workflow_policy_evaluator import WorkflowPolicyEvaluator
from .workflow_policy_events import WorkflowPolicyEvent, WorkflowPolicyEventBus
from .workflow_policy_history import WorkflowPolicyHistory
from .workflow_policy_registry import WorkflowPolicyRegistry
from .workflow_policy_request import WorkflowPolicyRequest
from .workflow_policy_response import WorkflowPolicyResponse
from .workflow_policy_result import WorkflowPolicyResult
from .workflow_policy_statistics import WorkflowPolicyStatistics
from .workflow_policy_validator import WorkflowPolicyValidator

_log = get_logger(__name__)

_ENGINE_STATE_STOPPED  = "stopped"
_ENGINE_STATE_RUNNING  = "running"


class WorkflowPolicyEngine:
    """
    Central governance policy evaluation engine.

    Composes registry, evaluator, validator, chain, audit, statistics,
    history, and event bus into a single evaluation pipeline.
    """

    def __init__(
        self,
        *,
        engine_id:  Optional[str]                         = None,
        registry:   Optional[WorkflowPolicyRegistry]      = None,
        evaluator:  Optional[WorkflowPolicyEvaluator]     = None,
        validator:  Optional[WorkflowPolicyValidator]     = None,
        chain:      Optional[WorkflowPolicyChain]         = None,
        audit:      Optional[WorkflowPolicyAudit]         = None,
        statistics: Optional[WorkflowPolicyStatistics]   = None,
        history:    Optional[WorkflowPolicyHistory]       = None,
        event_bus:  Optional[WorkflowPolicyEventBus]     = None,
    ) -> None:
        self._engine_id  = engine_id or f"wpe-{uuid.uuid4().hex[:8]}"
        self._registry   = registry   or WorkflowPolicyRegistry()
        self._evaluator  = evaluator  or WorkflowPolicyEvaluator()
        self._validator  = validator  or WorkflowPolicyValidator()
        self._chain      = chain      or WorkflowPolicyChain()
        self._audit      = audit      or WorkflowPolicyAudit()
        self._statistics = statistics or WorkflowPolicyStatistics()
        self._history    = history    or WorkflowPolicyHistory()
        self._event_bus  = event_bus  or WorkflowPolicyEventBus()
        self._state      = _ENGINE_STATE_STOPPED
        self._lock       = threading.Lock()

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize and start the engine."""
        with self._lock:
            if self._state == _ENGINE_STATE_RUNNING:
                return
            self._state = _ENGINE_STATE_RUNNING
        _log.info(f"Engine: initialized engine_id={self._engine_id!r}")
        self._emit(PolicyEventType.WORKFLOW_GOVERNANCE_STARTED, {
            "engine_id": self._engine_id,
        })

    def stop(self) -> None:
        """Stop the engine."""
        with self._lock:
            self._state = _ENGINE_STATE_STOPPED
        _log.info(f"Engine: stopped engine_id={self._engine_id!r}")

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._state == _ENGINE_STATE_RUNNING

    # ----------------------------------------------------------------
    # Policy registration
    # ----------------------------------------------------------------

    def register_policy(self, policy: WorkflowPolicy) -> None:
        """
        Validate and register a governance policy.

        Raises:
            WorkflowPolicyValidationError if policy is invalid.
            WorkflowPolicyRegistryError if registry is full.
        """
        self._validator.validate_or_raise(policy)
        self._registry.register(policy)
        _log.debug(f"Engine: registered policy={policy.policy_id!r} name={policy.name!r}")
        self._emit(PolicyEventType.WORKFLOW_POLICY_LOADED, {
            "policy_id":   policy.policy_id,
            "policy_name": policy.name,
        })

    def validate_policy(self, policy: WorkflowPolicy) -> Dict[str, Any]:
        """Validate a policy without registering it.  Returns validation dict."""
        result = self._validator.validate(policy)
        return result.to_dict()

    # ----------------------------------------------------------------
    # Governance evaluation
    # ----------------------------------------------------------------

    def evaluate_governance(
        self,
        request: WorkflowPolicyRequest,
    ) -> WorkflowPolicyResponse:
        """
        Evaluate governance policies for a workflow request.

        NEVER raises for governance-level decisions.

        Returns:
            WorkflowPolicyResponse with governance decision.
        """
        t0 = time.monotonic()

        self._history.record_request(request)
        self._emit(PolicyEventType.WORKFLOW_GOVERNANCE_STARTED, {
            "request_id":  request.request_id,
            "workflow_id": request.workflow_id,
        })

        try:
            response = self._run_evaluation(request, t0)
        except Exception as exc:
            _log.error(
                f"Engine: unexpected evaluation error "
                f"request={request.request_id!r}: {exc!r}"
            )
            # Safety net — return an approval on internal error to avoid
            # blocking workflows due to a governance system failure.
            # In production you may want to invert this to fail-safe-block.
            elapsed  = (time.monotonic() - t0) * 1000.0
            response = WorkflowPolicyResponse.approved(
                request,
                [],
                reasoning          = f"Governance engine error (fail-open): {exc!r}",
                evaluation_time_ms = elapsed,
            )

        self._history.record_response(response)
        self._emit_decision_event(response)
        self._statistics.record_evaluation(
            decision            = response.decision,
            evaluation_time_ms  = response.evaluation_time_ms,
            had_applicable_policies = response.policies_evaluated > 0,
        )
        self._emit(PolicyEventType.WORKFLOW_GOVERNANCE_COMPLETED, {
            "request_id":  request.request_id,
            "workflow_id": request.workflow_id,
            "decision":    response.decision.value,
        })
        return response

    def _run_evaluation(
        self,
        request: WorkflowPolicyRequest,
        t0:      float,
    ) -> WorkflowPolicyResponse:
        # 1. Collect applicable policies
        policies = self._collect_policies(request)

        if not policies:
            elapsed = (time.monotonic() - t0) * 1000.0
            return WorkflowPolicyResponse.approved(
                request,
                [],
                reasoning          = "No governance policies registered — default approval",
                evaluation_time_ms = elapsed,
            )

        self._emit(PolicyEventType.WORKFLOW_POLICY_VALIDATED, {
            "request_id":      request.request_id,
            "policy_count":    len(policies),
        })

        # 2. Evaluate the chain
        winning_action, results, reasoning = self._chain.evaluate(
            policies, request.context
        )

        elapsed = (time.monotonic() - t0) * 1000.0

        # 3. Build response
        from .constants import PolicyAction, action_to_decision
        decision = action_to_decision(winning_action)

        if winning_action == PolicyAction.APPROVE:
            response = WorkflowPolicyResponse.approved(
                request, results,
                reasoning          = reasoning,
                evaluation_time_ms = elapsed,
            )
        elif winning_action == PolicyAction.APPROVE_WITH_CONDITIONS:
            conditions = [r.reasoning for r in results
                          if r.action == PolicyAction.APPROVE_WITH_CONDITIONS]
            response = WorkflowPolicyResponse.approved_with_conditions(
                request, results, conditions,
                reasoning          = reasoning,
                evaluation_time_ms = elapsed,
            )
        elif winning_action == PolicyAction.EMERGENCY_STOP:
            response = WorkflowPolicyResponse.emergency_stopped(
                request, results, reasoning,
                evaluation_time_ms = elapsed,
            )
        elif winning_action == PolicyAction.BLOCK:
            response = WorkflowPolicyResponse.blocked(
                request, results, reasoning,
                evaluation_time_ms = elapsed,
            )
        else:
            response = WorkflowPolicyResponse.rejected(
                request, results, reasoning,
                evaluation_time_ms = elapsed,
            )

        # 4. Audit
        audit_rec = self._audit.record(request, response)
        # Attach audit_id — rebuild the frozen dataclass (cheap with frozen=True)
        import dataclasses
        response = dataclasses.replace(response, audit_id=audit_rec.audit_id)

        return response

    def _collect_policies(
        self,
        request: WorkflowPolicyRequest,
    ) -> List[WorkflowPolicy]:
        """
        Collect all applicable, enabled policies from the registry.

        If the request specifies type or domain filters, only those
        policies are returned.  Otherwise, all enabled policies are used.
        """
        if request.has_type_filter:
            policies: List[WorkflowPolicy] = []
            for pt in request.policy_types:
                policies.extend(self._registry.get_by_type(pt))
            # De-duplicate
            seen: set = set()
            unique = []
            for p in policies:
                if p.policy_id not in seen:
                    seen.add(p.policy_id)
                    unique.append(p)
            policies = unique
        elif request.has_domain_filter:
            policies = []
            for d in request.policy_domains:
                policies.extend(self._registry.get_by_domain(d))
            seen = set()
            unique = []
            for p in policies:
                if p.policy_id not in seen:
                    seen.add(p.policy_id)
                    unique.append(p)
            policies = unique
        else:
            policies = self._registry.enabled_policies()

        return [p for p in policies if p.enabled]

    # ----------------------------------------------------------------
    # Event helpers
    # ----------------------------------------------------------------

    def _emit(
        self,
        event_type: PolicyEventType,
        payload:    Dict[str, Any],
        *,
        request_id:  str = "",
        workflow_id: str = "",
    ) -> None:
        event = WorkflowPolicyEvent.create(
            event_type  = event_type,
            engine_id   = self._engine_id,
            request_id  = request_id or payload.get("request_id", ""),
            workflow_id = workflow_id or payload.get("workflow_id", ""),
            payload     = payload,
        )
        self._event_bus.emit(event)

    def _emit_decision_event(self, response: WorkflowPolicyResponse) -> None:
        from .constants import GovernanceDecision, PolicyEventType
        decision_event_map = {
            GovernanceDecision.APPROVED:                    PolicyEventType.WORKFLOW_APPROVED,
            GovernanceDecision.APPROVED_WITH_CONDITIONS:    PolicyEventType.WORKFLOW_APPROVED,
            GovernanceDecision.REJECTED:                    PolicyEventType.WORKFLOW_REJECTED,
            GovernanceDecision.BLOCKED:                     PolicyEventType.WORKFLOW_BLOCKED,
            GovernanceDecision.EMERGENCY_STOPPED:           PolicyEventType.EMERGENCY_STOP_TRIGGERED,
            GovernanceDecision.REQUIRES_MANUAL_APPROVAL:    PolicyEventType.APPROVAL_REQUESTED,
            GovernanceDecision.REQUIRES_EXECUTIVE_APPROVAL: PolicyEventType.APPROVAL_REQUESTED,
            GovernanceDecision.ESCALATED:                   PolicyEventType.APPROVAL_REQUESTED,
        }
        event_type = decision_event_map.get(response.decision)
        if event_type:
            self._emit(event_type, {
                "request_id":  response.request_id,
                "workflow_id": response.workflow_id,
                "decision":    response.decision.value,
            })

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        return {
            "engine_id":       self._engine_id,
            "state":           self._state,
            "is_running":      self.is_running,
            "policy_count":    self._registry.policy_count(),
            "audit_count":     self._audit.audit_count(),
            "request_count":   self._history.request_count(),
            "response_count":  self._history.response_count(),
            "listener_count":  self._event_bus.listener_count(),
        }

    def status(self) -> Dict[str, Any]:
        return self.health()

    def statistics(self) -> Dict[str, Any]:
        return self._statistics.report().to_dict()

    def history(self) -> "WorkflowPolicyHistory":
        return self._history

    def event_bus(self) -> "WorkflowPolicyEventBus":
        return self._event_bus

    @property
    def engine_id(self) -> str:
        return self._engine_id

    @property
    def registry(self) -> WorkflowPolicyRegistry:
        return self._registry
