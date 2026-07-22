"""
portfolio_policy_engine.py — iios.portfolio.policies
=====================================================
Primary public interface of the Portfolio Policy Framework.

PortfolioPolicyEngine is the ONLY interface external callers use to
interact with the Institutional Portfolio Policy Framework.

Responsibilities
----------------
* Accept and validate portfolio policy evaluation requests
* Load and manage institutional policies
* Coordinate policy evaluation workflows
* Generate audit trails
* Maintain statistics and history
* Emit lifecycle events

Non-Responsibilities (intentional exclusions)
---------------------------------------------
* Portfolio optimisation (delegated to M4)
* Trade execution
* Broker communication
* Capital allocation or rebalancing decisions

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from iios.common.errors.exceptions import IIOSError
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin

from .constants import (
    ACTOR_ENGINE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    POLICY_SYSTEM_ID,
    VERSION,
    PolicyAction,
    PolicyPriority,
    PolicyType,
)
from .exceptions import (
    PortfolioPolicyCapacityError,
    PortfolioPolicyNotFoundError,
    PortfolioPolicyNotRunningError,
)
from .portfolio_policy import PortfolioPolicy
from .portfolio_policy_evaluator import PortfolioPolicyEvaluator
from .portfolio_policy_events import PolicyEngineEvent
from .portfolio_policy_factory import PortfolioPolicyFactory
from .portfolio_policy_history import PortfolioPolicyHistory
from .portfolio_policy_manager import PortfolioPolicyManager
from .portfolio_policy_registry import PortfolioPolicyRegistry
from .portfolio_policy_request import PortfolioPolicyRequest
from .portfolio_policy_response import PortfolioPolicyResponse
from .portfolio_policy_result import PortfolioPolicyResult
from .portfolio_policy_statistics import PortfolioPolicyStatistics
from .portfolio_policy_validator import PolicyValidationResult, PortfolioPolicyValidator

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=POLICY_SYSTEM_ID)


@dataclass(frozen=True)
class PolicyEngineStatus:
    """
    Immutable status snapshot of the PortfolioPolicyEngine.

    Fields
    ------
    lifecycle_state :         Current LifecycleAwareMixin state value.
    total_policies :          Total registered policies.
    active_policies :         Currently active policies.
    evaluations_total :       Cumulative evaluation runs.
    evaluations_approved :    Evaluations that resulted in APPROVE.
    evaluations_rejected :    Evaluations that resulted in REJECT.
    evaluations_blocked :     Evaluations that resulted in BLOCK.
    evaluations_escalated :   Evaluations that resulted in ESCALATE.
    is_healthy :              True when engine is running.
    uptime_s :                Seconds since last start().
    captured_at :             Wall-clock timestamp of this snapshot.
    framework_version :       Framework version string.
    """
    lifecycle_state:       str
    total_policies:        int
    active_policies:       int
    evaluations_total:     int
    evaluations_approved:  int
    evaluations_rejected:  int
    evaluations_blocked:   int
    evaluations_escalated: int
    is_healthy:            bool
    uptime_s:              float
    captured_at:           float
    framework_version:     str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lifecycle_state":       self.lifecycle_state,
            "total_policies":        self.total_policies,
            "active_policies":       self.active_policies,
            "evaluations_total":     self.evaluations_total,
            "evaluations_approved":  self.evaluations_approved,
            "evaluations_rejected":  self.evaluations_rejected,
            "evaluations_blocked":   self.evaluations_blocked,
            "evaluations_escalated": self.evaluations_escalated,
            "is_healthy":            self.is_healthy,
            "uptime_s":              self.uptime_s,
            "captured_at":           self.captured_at,
            "framework_version":     self.framework_version,
        }


class PortfolioPolicyEngine(LifecycleAwareMixin):
    """
    Institutional Portfolio Policy Engine.

    This is the ONLY public interface external callers should use.

    Parameters
    ----------
    max_policies : Maximum policies the registry may hold.
    max_history :  Maximum history entries per collection.

    Examples
    --------
    ::

        engine = PortfolioPolicyEngine()
        engine.start()

        engine.register_policy(my_risk_policy)

        request  = PortfolioPolicyRequest.create("pf-001")
        response = engine.submit(request)

        if response.is_approved:
            # proceed with portfolio workflow
            pass

        engine.stop()
    """

    def __init__(
        self,
        max_policies: int = DEFAULT_MAX_POLICIES,
        max_history:  int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._started_at: Optional[float] = None

        # Sub-components
        self._registry   = PortfolioPolicyRegistry(max_policies)
        self._validator  = PortfolioPolicyValidator()
        self._evaluator  = PortfolioPolicyEvaluator()
        self._statistics = PortfolioPolicyStatistics()
        self._history    = PortfolioPolicyHistory(max_entries=max_history)
        self._factory    = PortfolioPolicyFactory()
        self._manager    = PortfolioPolicyManager(
            registry       = self._registry,
            evaluator      = self._evaluator,
            validator      = self._validator,
            statistics     = self._statistics,
            history        = self._history,
            dispatch_event = self._dispatch_event,
        )

        self._listeners: List[Callable[[PolicyEngineEvent], None]] = []
        self._listener_lock = threading.Lock()

    # ==================================================================
    # LifecycleAwareMixin hooks
    # ==================================================================

    def _on_start(self) -> None:
        self._started_at = time.time()
        _log.info(f"PortfolioPolicyEngine starting (version={VERSION})")
        _audit.log_lifecycle_event(
            engine_id  = POLICY_SYSTEM_ID,
            from_state = "STOPPED",
            to_state   = "RUNNING",
            version    = VERSION,
            actor      = ACTOR_ENGINE,
        )

    def _on_stop(self) -> None:
        _log.info(f"PortfolioPolicyEngine stopping")
        _audit.log_lifecycle_event(
            engine_id  = POLICY_SYSTEM_ID,
            from_state = "RUNNING",
            to_state   = "STOPPED",
            version    = VERSION,
            actor      = ACTOR_ENGINE,
        )

    # ==================================================================
    # Primary submission API
    # ==================================================================

    def submit(self, request: PortfolioPolicyRequest) -> PortfolioPolicyResponse:
        """
        Submit a policy evaluation request for immediate processing.

        Parameters
        ----------
        request : Policy evaluation request.

        Returns
        -------
        PortfolioPolicyResponse
            Always returned — failures are captured in the response.

        Raises
        ------
        PortfolioPolicyNotRunningError
            When the engine has not been started.
        """
        self._assert_running()
        return self._manager.evaluate_portfolio(request)

    # ==================================================================
    # Convenience evaluation
    # ==================================================================

    def evaluate(
        self,
        portfolio_id:  str,
        policy_types:  Optional[List[PolicyType]] = None,
        *,
        inputs:   Optional[Dict[str, Any]] = None,
        priority: PolicyPriority = PolicyPriority.MEDIUM,
    ) -> PortfolioPolicyResponse:
        """
        Convenience method — create a request and evaluate immediately.

        Parameters
        ----------
        portfolio_id : Portfolio to evaluate.
        policy_types : Specific policy types to evaluate (None = all active).
        inputs :       Input data dict for policy conditions.
        priority :     Evaluation priority.
        """
        self._assert_running()
        request = self._factory.create_request(
            portfolio_id,
            policy_types,
            priority = priority,
            inputs   = inputs,
        )
        return self._manager.evaluate_portfolio(request)

    # ==================================================================
    # Policy management
    # ==================================================================

    def register_policy(self, policy: PortfolioPolicy) -> None:
        """
        Register a policy with the engine.

        Raises
        ------
        PortfolioPolicyNotRunningError
            When the engine has not been started.
        PortfolioPolicyCapacityError
            When the registry is at capacity.
        """
        self._assert_running()
        self._registry.register(policy)
        self._statistics.record_policy_registered()
        _log.info(
            f"Policy registered: id={policy.policy_id!r} "
            f"type={policy.policy_type.value!r} priority={policy.priority.name}"
        )

    def deactivate_policy(self, policy_id: str) -> bool:
        """
        Deactivate a registered policy.

        Returns True if found and deactivated, False if not found.
        """
        self._assert_running()
        result = self._registry.deactivate(policy_id)
        if result:
            self._statistics.record_policy_deactivated()
        return result

    def activate_policy(self, policy_id: str) -> bool:
        """Re-activate a previously deactivated policy."""
        self._assert_running()
        return self._registry.activate(policy_id)

    def get_policy(self, policy_id: str) -> Optional[PortfolioPolicy]:
        """Return a registered policy by ID, or None."""
        self._assert_running()
        return self._registry.get(policy_id)

    def list_policies(
        self, policy_type: Optional[PolicyType] = None
    ) -> List[PortfolioPolicy]:
        """
        List registered policies.

        Parameters
        ----------
        policy_type : If provided, return only policies of this type.
                      If None, return all active policies.
        """
        self._assert_running()
        if policy_type is not None:
            return self._registry.find_by_type(policy_type)
        return self._registry.all_active()

    # ==================================================================
    # Validation
    # ==================================================================

    def validate(self, request: PortfolioPolicyRequest) -> PolicyValidationResult:
        """Validate a request without submitting it for evaluation."""
        self._assert_running()
        return self._validator.validate_request(request)

    def validate_policy(self, policy: PortfolioPolicy) -> PolicyValidationResult:
        """Validate a policy configuration without registering it."""
        self._assert_running()
        return self._validator.validate_policy(policy)

    # ==================================================================
    # Introspection
    # ==================================================================

    def status(self) -> PolicyEngineStatus:
        """Return a current status snapshot."""
        snap = self._statistics.snapshot()
        uptime = (time.time() - self._started_at) if self._started_at else 0.0
        return PolicyEngineStatus(
            lifecycle_state       = self.lifecycle_state().value,
            total_policies        = self._registry.policy_count(),
            active_policies       = self._registry.active_count(),
            evaluations_total     = snap["evaluations_total"],
            evaluations_approved  = snap["evaluations_approved"],
            evaluations_rejected  = snap["evaluations_rejected"],
            evaluations_blocked   = snap["evaluations_blocked"],
            evaluations_escalated = snap["evaluations_escalated"],
            is_healthy            = self.lifecycle_state().value == "running",
            uptime_s              = uptime,
            captured_at           = time.time(),
            framework_version     = VERSION,
        )

    def statistics(self) -> Dict[str, Any]:
        """Return a statistics snapshot dict."""
        snap = self._statistics.snapshot()
        snap["total_policies"]  = self._registry.policy_count()
        snap["active_policies"] = self._registry.active_count()
        return snap

    def health(self) -> Dict[str, Any]:
        """Return an engine health dict."""
        lc    = self.lifecycle_state().value
        snap  = self._statistics.snapshot()
        return {
            "is_healthy":       lc == "running",
            "lifecycle_state":  lc,
            "registry":         {
                "total":  self._registry.policy_count(),
                "active": self._registry.active_count(),
            },
            "evaluator":        {"available": True},
            "validator":        {"available": True},
            "statistics":       snap,
        }

    def history(self) -> Dict[str, Any]:
        """Return a history summary dict."""
        summary = self._history.summary()
        events  = self._history.events()
        return {
            "events":    [e.to_dict() for e in events],
            "requests":  self._history.request_count(),
            "responses": self._history.response_count(),
            "audits":    self._history.audit_count(),
            "summary":   summary,
        }

    # ==================================================================
    # Event listeners
    # ==================================================================

    def add_listener(self, listener: Callable[[PolicyEngineEvent], None]) -> None:
        """Register a callable to receive policy engine events."""
        with self._listener_lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[PolicyEngineEvent], None]) -> None:
        """Deregister a previously registered event listener."""
        with self._listener_lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise PortfolioPolicyNotRunningError()

    def _dispatch_event(self, event: PolicyEngineEvent) -> None:
        with self._listener_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(f"Policy engine listener error: {exc}")
