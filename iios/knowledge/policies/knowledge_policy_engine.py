"""
knowledge_policy_engine.py — iios.knowledge.policies
------------------------------------------------------
PRIMARY PUBLIC INTERFACE for the Knowledge Governance Policy Framework.

Responsibilities (this module ONLY):
  - Accept governance evaluation requests via evaluate()
  - Manage policy lifecycle: register, deregister, archive
  - Wire and coordinate all governance subsystems
  - Expose health(), status(), statistics(), audit() introspection
  - Provide governance_delegate callable for M2 KnowledgeEngine integration

This module NEVER:
  - Performs knowledge reasoning (M4 responsibility)
  - Performs semantic search or embedding generation
  - Accesses vector databases
  - Executes LLM inference

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_GOVERNANCE,
    DEFAULT_MAX_AUDIT_ENTRIES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    GOVERNANCE_SYSTEM_ID,
    GovernanceDecision,
    GovernanceEngineState,
    PolicyChainMode,
    PolicyDomain,
    PolicyPriority,
    PolicyType,
    VERSION,
)
from .exceptions import GovernanceNotRunningError
from .knowledge_policy import KnowledgePolicy
from .knowledge_policy_audit import KnowledgePolicyAudit, PolicyAuditEntry
from .knowledge_policy_chain import ChainResult, KnowledgePolicyChain
from .knowledge_policy_evaluator import KnowledgePolicyEvaluator
from .knowledge_policy_events import GovernancePolicyEvent, GovernancePolicyEventBus
from .knowledge_policy_factory import KnowledgePolicyFactory
from .knowledge_policy_history import KnowledgeGovernanceHistory
from .knowledge_policy_manager import KnowledgePolicyWorkflowManager
from .knowledge_policy_priority import PolicyPriorityResolver
from .knowledge_policy_registry import KnowledgePolicyRegistry
from .knowledge_policy_request import KnowledgePolicyRequest
from .knowledge_policy_response import KnowledgePolicyResponse
from .knowledge_policy_statistics import KnowledgeGovernanceStatistics
from .knowledge_policy_validator import KnowledgeGovernanceValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=GOVERNANCE_SYSTEM_ID)


class KnowledgeGovernancePolicyEngine(LifecycleAwareMixin):
    """
    Institutional Knowledge Governance Policy Framework.

    Evaluates enterprise knowledge requests against a configurable,
    versioned, and auditable set of governance policies.

    Integration with M2 (Knowledge Engine)
    ----------------------------------------
    Pass ``engine.governance_delegate`` as ``governance_delegate`` to
    ``KnowledgeEngine``.  The delegate converts M2 dispatcher calls to
    a ``KnowledgePolicyRequest`` and returns a governance result dict.

    Parameters
    ----------
    registry :      KnowledgePolicyRegistry (created if None)
    evaluator :     KnowledgePolicyEvaluator (created if None)
    max_policies :  Maximum registered policies
    max_history :   Maximum evaluation history entries
    max_audit :     Maximum audit entries
    """

    def __init__(
        self,
        registry:   Optional[KnowledgePolicyRegistry]       = None,
        evaluator:  Optional[KnowledgePolicyEvaluator]      = None,
        statistics: Optional[KnowledgeGovernanceStatistics] = None,
        history:    Optional[KnowledgeGovernanceHistory]    = None,
        audit:      Optional[KnowledgePolicyAudit]          = None,
        event_bus:  Optional[GovernancePolicyEventBus]      = None,
        validator:  Optional[KnowledgeGovernanceValidator]  = None,
        factory:    Optional[KnowledgePolicyFactory]        = None,
        manager:    Optional[KnowledgePolicyWorkflowManager] = None,
        *,
        max_policies: int = DEFAULT_MAX_POLICIES,
        max_history:  int = DEFAULT_MAX_HISTORY,
        max_audit:    int = DEFAULT_MAX_AUDIT_ENTRIES,
    ) -> None:
        super().__init__()
        self._max_policies = max_policies

        # Subsystems
        self._registry   = registry   or KnowledgePolicyRegistry(max_policies=max_policies)
        self._evaluator  = evaluator  or KnowledgePolicyEvaluator()
        self._statistics = statistics or KnowledgeGovernanceStatistics()
        self._history    = history    or KnowledgeGovernanceHistory(max_entries=max_history)
        self._audit      = audit      or KnowledgePolicyAudit(max_entries=max_audit)
        self._event_bus  = event_bus  or GovernancePolicyEventBus()
        self._factory    = factory    or KnowledgePolicyFactory()
        self._resolver   = PolicyPriorityResolver()
        self._validator  = validator  or KnowledgeGovernanceValidator(
            max_policies    = max_policies,
            active_count_fn = self._registry.active_count,
        )
        self._manager = manager or KnowledgePolicyWorkflowManager(
            evaluator  = self._evaluator,
            registry   = self._registry,
            validator  = self._validator,
            resolver   = self._resolver,
            audit      = self._audit,
            statistics = self._statistics,
            history    = self._history,
            event_bus  = self._event_bus,
        )

        self._state      = GovernanceEngineState.IDLE
        self._state_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        with self._state_lock:
            self._state = GovernanceEngineState.IDLE
        _audit.log_lifecycle_event(
            engine_id  = GOVERNANCE_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = ACTOR_GOVERNANCE,
        )
        _log.info(f"KnowledgeGovernancePolicyEngine started: version={VERSION!r}")

    def _on_stop(self) -> None:
        with self._state_lock:
            self._state = GovernanceEngineState.STOPPED
        _audit.log_lifecycle_event(
            engine_id  = GOVERNANCE_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = ACTOR_GOVERNANCE,
        )
        _log.info("KnowledgeGovernancePolicyEngine stopped")

    # ------------------------------------------------------------------
    # Guard helper
    # ------------------------------------------------------------------

    def _require_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise GovernanceNotRunningError()

    # ------------------------------------------------------------------
    # Primary interface — evaluate
    # ------------------------------------------------------------------

    def evaluate(self, request: KnowledgePolicyRequest) -> KnowledgePolicyResponse:
        """
        Evaluate a governance request against all active policies.

        Raises GovernanceNotRunningError if the engine is not running.
        """
        self._require_running()
        _log.debug(
            f"Governance evaluation: "
            f"knowledge_id={request.knowledge_id!r} "
            f"request_id={request.request_id!r}"
        )
        with self._state_lock:
            self._state = GovernanceEngineState.EVALUATING
        try:
            response = self._manager.run_governance(request)
            _log.info(
                f"Governance completed: "
                f"knowledge_id={request.knowledge_id!r} "
                f"decision={response.decision.value!r}"
            )
            return response
        finally:
            with self._state_lock:
                self._state = GovernanceEngineState.IDLE

    # ------------------------------------------------------------------
    # M2 integration delegate
    # ------------------------------------------------------------------

    def evaluate_for_dispatcher(
        self,
        knowledge_id: str,
        context:      Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Governance delegate compatible with M2 KnowledgeDispatcher.

        Returns a dict with: status, decision, approved, response_id, errors.
        """
        if self.lifecycle_state().value != "running":
            return {
                "status":   "engine_not_running",
                "decision": GovernanceDecision.REJECTED.value,
                "approved": False,
            }

        request = self._factory.create_request(
            knowledge_id = knowledge_id,
            subsystem_id = context.get("subsystem_id", "unknown"),
            artifacts    = context.get("artifacts", {}),
            metadata     = context.get("metadata", {}),
        )
        response = self.evaluate(request)
        return {
            "status":      "evaluated",
            "decision":    response.decision.value,
            "approved":    response.is_approved,
            "response_id": response.response_id,
            "passed":      response.passed,
            "errors":      list(response.errors),
        }

    @property
    def governance_delegate(self) -> Callable[[str, Dict[str, Any]], Dict[str, Any]]:
        """Bound delegate for M2 KnowledgeEngine integration."""
        return self.evaluate_for_dispatcher

    # ------------------------------------------------------------------
    # Chain evaluation
    # ------------------------------------------------------------------

    def evaluate_chain(
        self,
        chain:   KnowledgePolicyChain,
        request: KnowledgePolicyRequest,
    ) -> ChainResult:
        """Evaluate a policy chain against the request's artifacts."""
        self._require_running()
        return chain.evaluate(request.artifacts, request.context, self._evaluator)

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def register_policy(self, policy: KnowledgePolicy) -> None:
        """Register a governance policy with the engine."""
        self._require_running()
        self._registry.register(policy)
        _log.info(
            f"Policy registered: policy_id={policy.policy_id!r} name={policy.name!r}"
        )

    def deregister_policy(self, policy_id: str) -> bool:
        """Remove a policy from the active registry."""
        self._require_running()
        removed = self._registry.deregister(policy_id)
        if removed:
            _log.info(f"Policy deregistered: policy_id={policy_id!r}")
        return removed

    def archive_policy(self, policy_id: str) -> bool:
        """Archive a policy (retained for audit, no longer evaluated)."""
        self._require_running()
        archived = self._registry.archive_policy(policy_id)
        if archived:
            _log.info(f"Policy archived: policy_id={policy_id!r}")
        return archived

    def get_policy(self, policy_id: str) -> Optional[KnowledgePolicy]:
        """Retrieve a policy by ID (None if not found)."""
        return self._registry.get_optional(policy_id)

    def list_policies(self) -> List[KnowledgePolicy]:
        """List all registered active policies."""
        return self._registry.all_active()

    # ------------------------------------------------------------------
    # Event listener management
    # ------------------------------------------------------------------

    def add_listener(
        self, fn: Callable[[GovernancePolicyEvent], None],
    ) -> None:
        self._event_bus.add_listener(fn)

    def remove_listener(
        self, fn: Callable[[GovernancePolicyEvent], None],
    ) -> bool:
        return self._event_bus.remove_listener(fn)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Return a health assessment dict."""
        running = self.lifecycle_state().value == "running"
        return {
            "status":            "healthy" if running else "stopped",
            "lifecycle_state":   self.lifecycle_state().value,
            "engine_state":      self._state.value,
            "active_policies":   self._registry.active_count(),
            "archived_policies": self._registry.archived_count(),
            "audit_entries":     self._audit.count(),
            "history_entries":   self._history.count(),
        }

    def status(self) -> Dict[str, Any]:
        """Return detailed status dict."""
        stats = self._statistics.snapshot()
        return {
            "version":           VERSION,
            "lifecycle_state":   self.lifecycle_state().value,
            "engine_state":      self._state.value,
            "active_policies":   self._registry.active_count(),
            "archived_policies": self._registry.archived_count(),
            "total_policies":    self._registry.total_count(),
            "audit_entries":     self._audit.count(),
            **stats,
        }

    def statistics(self) -> Dict[str, Any]:
        """Return 8-counter governance statistics."""
        return self._statistics.snapshot()

    def history(self, n: int = 50) -> list:
        """Return recent governance evaluation results."""
        return self._history.recent(n)

    def audit_for(self, knowledge_id: str) -> List[PolicyAuditEntry]:
        """Return audit entries for a specific knowledge_id."""
        return self._audit.for_knowledge_id(knowledge_id)

    def audit_summary(self) -> Dict[str, int]:
        """Return audit summary counts by decision value."""
        return self._audit.summary()

    def engine_state(self) -> GovernanceEngineState:
        """Return current engine processing state."""
        with self._state_lock:
            return self._state
