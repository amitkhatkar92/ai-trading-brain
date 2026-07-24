"""
integration_policy_engine.py — iios.integration.policies
----------------------------------------------------------
IntegrationPolicyEngine — central coordinator for the Integration
Governance Policy Framework.

Responsibilities:
  - Load and validate governance policies
  - Evaluate policies against integration contexts
  - Resolve policy conflicts using the priority resolver
  - Generate governance decisions
  - Create audit trail entries
  - Emit governance lifecycle events
  - Maintain statistics and history

MUST NOT:
  - Execute connectors or adapters
  - Open network connections
  - Call REST APIs or WebSocket sessions
  - Publish messages to Kafka, RabbitMQ, or any queue
  - Access databases
  - Authenticate with providers
  - Execute cloud SDKs

These responsibilities belong to the Integration Services Framework (M4).

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import time
import threading
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_ENGINE_ID,
    PolicyAction,
    PolicyEventType,
)
from .exceptions import PolicyEngineNotReadyError
from .integration_policy import IntegrationPolicy
from .integration_policy_audit import IntegrationAuditEntry, IntegrationPolicyAudit
from .integration_policy_chain import IntegrationPolicyChain
from .integration_policy_context import IntegrationPolicyContext
from .integration_policy_evaluator import IntegrationPolicyEvaluator
from .integration_policy_events import IntegrationPolicyEventBus
from .integration_policy_factory import IntegrationPolicyFactory
from .integration_policy_history import IntegrationPolicyHistory
from .integration_policy_priority import IntegrationPolicyPriority
from .integration_policy_registry import IntegrationPolicyRegistry
from .integration_policy_request import IntegrationPolicyRequest
from .integration_policy_response import IntegrationPolicyResponse
from .integration_policy_result import GovernanceDecision
from .integration_policy_statistics import IntegrationPolicyStatistics
from .integration_policy_validator import IntegrationPolicyValidator

_log = get_logger(__name__)


class IntegrationPolicyEngine:
    """
    Central coordinator for the Integration Governance Policy Framework.

    Thread-safe.  Manages policy lifecycle, evaluation, conflict
    resolution, audit, events, statistics, and history.
    """

    def __init__(
        self,
        engine_id: str                                    = DEFAULT_ENGINE_ID,
        registry:  Optional[IntegrationPolicyRegistry]   = None,
        evaluator: Optional[IntegrationPolicyEvaluator]  = None,
        validator: Optional[IntegrationPolicyValidator]  = None,
        event_bus: Optional[IntegrationPolicyEventBus]   = None,
        stats:     Optional[IntegrationPolicyStatistics] = None,
        history:   Optional[IntegrationPolicyHistory]    = None,
        audit:     Optional[IntegrationPolicyAudit]      = None,
    ) -> None:
        self._engine_id = engine_id
        self._registry  = registry  or IntegrationPolicyRegistry()
        self._evaluator = evaluator or IntegrationPolicyEvaluator()
        self._validator = validator or IntegrationPolicyValidator()
        self._event_bus = event_bus or IntegrationPolicyEventBus()
        self._stats     = stats     or IntegrationPolicyStatistics()
        self._history   = history   or IntegrationPolicyHistory()
        self._audit     = audit     or IntegrationPolicyAudit()
        self._factory   = IntegrationPolicyFactory()

        self._ready      = False
        self._started_at: Optional[float] = None
        self._lock        = threading.Lock()

    # ── properties ────────────────────────────────────────────────────

    @property
    def engine_id(self) -> str:
        return self._engine_id

    @property
    def registry(self) -> IntegrationPolicyRegistry:
        return self._registry

    @property
    def event_bus(self) -> IntegrationPolicyEventBus:
        return self._event_bus

    @property
    def stats(self) -> IntegrationPolicyStatistics:
        return self._stats

    @property
    def history(self) -> IntegrationPolicyHistory:
        return self._history

    @property
    def audit(self) -> IntegrationPolicyAudit:
        return self._audit

    @property
    def is_ready(self) -> bool:
        return self._ready

    # ── lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        """Mark the engine as ready to accept evaluation requests."""
        with self._lock:
            if not self._ready:
                self._started_at = time.monotonic()
                self._ready      = True
                _log.info(f"[{self._engine_id}] IntegrationPolicyEngine started")

    def stop(self) -> None:
        """Stop the engine — no further evaluation requests are accepted."""
        with self._lock:
            self._ready = False
            _log.info(f"[{self._engine_id}] IntegrationPolicyEngine stopped")

    # ── policy management ─────────────────────────────────────────────

    def load_policy(self, policy: IntegrationPolicy) -> None:
        """Validate and register a single governance policy."""
        self._validator.validate_or_raise(policy)
        self._registry.register(policy)
        self._event_bus.emit(
            PolicyEventType.POLICY_LOADED,
            self._engine_id,
            "",
            {"policy_id": policy.policy_id, "name": policy.name},
        )
        self._event_bus.emit(
            PolicyEventType.POLICY_VALIDATED,
            self._engine_id,
            "",
            {"policy_id": policy.policy_id},
        )
        _log.info(
            f"[{self._engine_id}] Loaded policy: {policy.name!r} [{policy.policy_id}]"
        )

    def load_policies(self, policies: List[IntegrationPolicy]) -> None:
        """Validate and register multiple governance policies."""
        for policy in policies:
            self.load_policy(policy)

    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy from the registry.  Returns True if removed."""
        return self._registry.deregister(policy_id)

    # ── governance evaluation ─────────────────────────────────────────

    def evaluate(self, request: IntegrationPolicyRequest) -> IntegrationPolicyResponse:
        """
        Evaluate a governance request against all applicable policies.

        Always returns an IntegrationPolicyResponse — never raises for
        policy failures.  Raises PolicyEngineNotReadyError only when
        the engine has not been started or has been stopped.
        """
        if not self._ready:
            raise PolicyEngineNotReadyError(
                f"Policy engine '{self._engine_id}' is not started"
            )

        self._history.record_request(request)
        start_ns = time.perf_counter_ns()

        self._event_bus.emit(
            PolicyEventType.GOVERNANCE_STARTED,
            self._engine_id,
            request.request_id,
        )

        try:
            response = self._evaluate_internal(request, start_ns)
        except Exception as exc:
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
            _log.info(
                f"[{self._engine_id}] Evaluation error for "
                f"request {request.request_id!r}: {exc}"
            )
            decision = GovernanceDecision.create(
                request_id     = request.request_id,
                final_action   = PolicyAction.REJECT,
                policy_results = [],
                reasons        = [str(exc)],
            )
            response = IntegrationPolicyResponse.rejected(
                request.request_id,
                decision,
                evaluation_time_ms = elapsed_ms,
            )

        self._history.record_response(response)
        self._stats.record_evaluation_time(response.evaluation_time_ms)
        self._stats.record_evaluated()
        self._emit_outcome_event(response, request.request_id)
        return response

    def _evaluate_internal(
        self,
        request:  IntegrationPolicyRequest,
        start_ns: int,
    ) -> IntegrationPolicyResponse:
        ctx = request.policy_context

        all_policies = self._registry.all_enabled()

        # Resolve domain/type filter lists (convert from tuple of enum members)
        dom_list = (
            list(request.requested_domains)
            if request.requested_domains else None
        )
        typ_list = (
            list(request.requested_types)
            if request.requested_types else None
        )

        decision = self._evaluator.evaluate(all_policies, ctx, dom_list, typ_list)

        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000

        # Record audit entry
        audit_entry = IntegrationAuditEntry.create(
            request_id         = request.request_id,
            context_id         = ctx.context_id,
            decision           = decision,
            policy_results     = list(decision.policy_results),
            evaluation_time_ms = elapsed_ms,
        )
        self._audit.record(audit_entry)

        # Per-policy statistics
        approved_count = sum(1 for r in decision.policy_results if r.is_approved)
        rejected_count = sum(1 for r in decision.policy_results if r.is_blocking)
        for _ in range(approved_count):
            self._stats.record_approved()
        for _ in range(rejected_count):
            self._stats.record_rejected()

        # Action-level statistics
        fa = decision.final_action
        if fa == PolicyAction.BLOCK:
            self._stats.record_blocked()
        elif fa == PolicyAction.EMERGENCY_STOP:
            self._stats.record_emergency_stop()
        elif fa == PolicyAction.REQUIRE_SECURITY_APPROVAL:
            self._stats.record_security_review()
        elif fa == PolicyAction.ESCALATE:
            self._stats.record_escalation()

        n_evaluated = len(decision.policy_results)

        if decision.approved:
            return IntegrationPolicyResponse.approved(
                request.request_id,
                decision,
                policies_evaluated  = n_evaluated,
                policies_approved   = approved_count,
                policies_rejected   = rejected_count,
                evaluation_time_ms  = elapsed_ms,
                audit_id            = audit_entry.audit_id,
            )
        return IntegrationPolicyResponse.rejected(
            request.request_id,
            decision,
            policies_evaluated  = n_evaluated,
            policies_approved   = approved_count,
            policies_rejected   = rejected_count,
            evaluation_time_ms  = elapsed_ms,
            audit_id            = audit_entry.audit_id,
        )

    def _emit_outcome_event(
        self,
        response:   IntegrationPolicyResponse,
        request_id: str,
    ) -> None:
        action = response.decision.final_action
        if action == PolicyAction.EMERGENCY_STOP:
            outcome = PolicyEventType.EMERGENCY_STOP_TRIGGERED
        elif action == PolicyAction.REQUIRE_SECURITY_APPROVAL:
            outcome = PolicyEventType.SECURITY_APPROVAL_REQUESTED
        elif action == PolicyAction.BLOCK:
            outcome = PolicyEventType.INTEGRATION_BLOCKED
        elif action in (PolicyAction.REJECT,):
            outcome = PolicyEventType.INTEGRATION_REJECTED
        else:
            outcome = PolicyEventType.INTEGRATION_APPROVED

        self._event_bus.emit(outcome, self._engine_id, request_id)
        self._event_bus.emit(
            PolicyEventType.GOVERNANCE_COMPLETED,
            self._engine_id,
            request_id,
            {"approved": response.is_approved},
        )

    # ── chain evaluation ──────────────────────────────────────────────

    def evaluate_chain(
        self,
        chain:          IntegrationPolicyChain,
        policy_context: IntegrationPolicyContext,
    ) -> GovernanceDecision:
        """Evaluate a policy chain and return its governance decision."""
        execution = chain.execute(policy_context)
        if execution.decision is None:
            return GovernanceDecision.create(
                request_id     = policy_context.engine_request_id,
                final_action   = PolicyAction.APPROVE,
                policy_results = [],
            )
        return execution.decision

    # ── validation ────────────────────────────────────────────────────

    def validate_policy(self, policy: IntegrationPolicy):
        """Validate a policy without registering it.  Returns a report."""
        return self._validator.validate(policy)

    # ── query ─────────────────────────────────────────────────────────

    def query(self, request_id: str) -> Optional[IntegrationPolicyResponse]:
        """Return the cached response for a prior request, if available."""
        return self._history.response_for_request(request_id)

    # ── status ────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "engine_id":      self._engine_id,
            "ready":          self._ready,
            "policy_count":   self._registry.count(),
            "uptime_seconds": (
                time.monotonic() - self._started_at
                if self._started_at else 0.0
            ),
            "statistics":     self._stats.report().to_dict(),
        }
