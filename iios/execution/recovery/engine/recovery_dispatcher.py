"""
iios/execution/recovery/engine/recovery_dispatcher.py
=====================================================
RecoveryDispatcher — dispatches recovery workflows to the Policy Framework
and Failover Framework via abstract ports.

The dispatcher does NOT implement policies or failover logic.
All decision logic is delegated:
  - Recovery decisions → PolicyFrameworkPort (M3)
  - Failover execution → FailoverFrameworkPort (M4)

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import DISPATCHER_ID, VERSION
from .exceptions import RecoveryDispatchError, RecoveryEngineNotRunningError
from .recovery_context import RecoveryContext
from .recovery_request import RecoveryRequest

_log = get_logger(__name__)


# ── Port interfaces ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PolicyDecision:
    """
    Decision returned by the Recovery Policy Framework (M3).

    The engine uses this to determine whether to proceed with recovery
    and whether failover should be triggered.
    """
    approved:          bool
    plan_id:           str             = ""
    instructions:      Tuple[str, ...] = ()
    requires_failover: bool            = False
    subsystem_id:      str             = ""
    metadata:          Dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved":          self.approved,
            "plan_id":           self.plan_id,
            "instructions":      list(self.instructions),
            "requires_failover": self.requires_failover,
            "subsystem_id":      self.subsystem_id,
        }


@dataclass(frozen=True)
class FailoverResult:
    """
    Result returned by the Failover Framework (M4).

    Indicates whether failover was triggered and its outcome.
    """
    triggered:   bool
    result:      str            = ""
    failover_id: str            = ""
    metadata:    Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggered":   self.triggered,
            "result":      self.result,
            "failover_id": self.failover_id,
        }


@dataclass(frozen=True)
class DispatchResult:
    """Result of a single dispatch call."""

    dispatch_id:     str
    dispatched:      bool
    policy_decision: PolicyDecision
    failover_result: Optional[FailoverResult]
    dispatched_at:   float
    duration_ms:     float         = 0.0
    error_message:   str           = ""
    metadata:        Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.dispatched and not self.error_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dispatch_id":     self.dispatch_id,
            "dispatched":      self.dispatched,
            "policy_decision": self.policy_decision.to_dict(),
            "failover_result": self.failover_result.to_dict() if self.failover_result else None,
            "dispatched_at":   self.dispatched_at,
            "duration_ms":     self.duration_ms,
            "error_message":   self.error_message,
        }


class PolicyFrameworkPort(ABC):
    """
    Abstract port for the Recovery Policy Framework (M3).

    The engine calls this port to obtain a recovery decision.
    Implementations should not be provided here — they belong in M3.
    """

    @abstractmethod
    def invoke(
        self,
        request: RecoveryRequest,
        context: RecoveryContext,
    ) -> PolicyDecision:
        """Return a PolicyDecision for the given request and context."""


class FailoverFrameworkPort(ABC):
    """
    Abstract port for the Failover Framework (M4).

    The engine calls this port to trigger failover when the policy requires it.
    Implementations should not be provided here — they belong in M4.
    """

    @abstractmethod
    def trigger_failover(
        self,
        request: RecoveryRequest,
        context: RecoveryContext,
    ) -> FailoverResult:
        """Trigger failover and return the result."""


# ── Null implementations (used when framework is not yet wired) ───────────────

class NullPolicyFramework(PolicyFrameworkPort):
    """
    No-op policy framework.

    Used when M3 is not yet available.  Always approves recovery and does
    not require failover.
    """

    def invoke(
        self,
        request: RecoveryRequest,
        context: RecoveryContext,
    ) -> PolicyDecision:
        _log.debug(
            "NullPolicyFramework invoked — approving by default.",
            request_id=request.request_id,
        )
        return PolicyDecision(
            approved          = True,
            plan_id           = "",
            instructions      = (),
            requires_failover = False,
            subsystem_id      = request.subsystem_id,
        )


class NullFailoverFramework(FailoverFrameworkPort):
    """
    No-op failover framework.

    Used when M4 is not yet available.  Never triggers failover.
    """

    def trigger_failover(
        self,
        request: RecoveryRequest,
        context: RecoveryContext,
    ) -> FailoverResult:
        _log.debug(
            "NullFailoverFramework invoked — no failover triggered.",
            request_id=request.request_id,
        )
        return FailoverResult(
            triggered   = False,
            result      = "no_failover_framework",
            failover_id = "",
        )


# ── Dispatcher ────────────────────────────────────────────────────────────────

class RecoveryDispatcher(LifecycleAwareMixin):
    """
    Dispatches recovery workflows to the Policy and Failover frameworks.

    The dispatcher is stateless per dispatch — it delegates all logic to
    the injected port implementations.
    """

    def __init__(
        self,
        policy_framework:   Optional[PolicyFrameworkPort]   = None,
        failover_framework: Optional[FailoverFrameworkPort] = None,
    ) -> None:
        super().__init__()
        self._policy   = policy_framework   or NullPolicyFramework()
        self._failover = failover_framework or NullFailoverFramework()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info(
            "RecoveryDispatcher started.",
            system_id   = DISPATCHER_ID,
            policy_impl = type(self._policy).__name__,
            failover_impl = type(self._failover).__name__,
        )

    def _on_stop(self) -> None:
        _log.info("RecoveryDispatcher stopped.", system_id=DISPATCHER_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in (EngineState.RUNNING, "running"):
            raise RecoveryEngineNotRunningError()

    # ── Port injection ────────────────────────────────────────────────────────

    def set_policy_framework(self, port: PolicyFrameworkPort) -> None:
        """Inject the M3 policy framework at runtime."""
        self._policy = port
        _log.info("PolicyFrameworkPort wired.", impl=type(port).__name__)

    def set_failover_framework(self, port: FailoverFrameworkPort) -> None:
        """Inject the M4 failover framework at runtime."""
        self._failover = port
        _log.info("FailoverFrameworkPort wired.", impl=type(port).__name__)

    # ── Dispatch ─────────────────────────────────────────────────────────────

    def dispatch(
        self,
        request: RecoveryRequest,
        context: RecoveryContext,
    ) -> DispatchResult:
        """
        Dispatch a recovery workflow.

        1. Invoke the Policy Framework to get a decision.
        2. If the decision requires failover, invoke the Failover Framework.
        3. Return a DispatchResult.

        Raises RecoveryDispatchError on hard failure.
        """
        self._assert_running()
        started_at = time.time()
        dispatch_id = str(uuid.uuid4())

        try:
            policy_decision = self._policy.invoke(request, context)
        except Exception as exc:
            raise RecoveryDispatchError(
                f"Policy framework invocation failed: {exc}",
                request_id=request.request_id,
            ) from exc

        failover_result: Optional[FailoverResult] = None
        if policy_decision.requires_failover:
            try:
                failover_result = self._failover.trigger_failover(request, context)
            except Exception as exc:
                raise RecoveryDispatchError(
                    f"Failover framework invocation failed: {exc}",
                    request_id=request.request_id,
                ) from exc

        duration_ms = (time.time() - started_at) * 1000.0
        _log.info(
            "Recovery dispatched.",
            request_id      = request.request_id,
            policy_approved = policy_decision.approved,
            failover        = failover_result.triggered if failover_result else False,
            duration_ms     = duration_ms,
        )
        return DispatchResult(
            dispatch_id     = dispatch_id,
            dispatched      = policy_decision.approved,
            policy_decision = policy_decision,
            failover_result = failover_result,
            dispatched_at   = started_at,
            duration_ms     = duration_ms,
        )
