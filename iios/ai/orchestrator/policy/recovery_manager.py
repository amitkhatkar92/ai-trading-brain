"""
recovery_manager.py -- iios.ai.orchestrator.policy
====================================================
Failure recovery infrastructure: strategies, retry, rollback.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import fnmatch
import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..exceptions.orchestrator_exceptions import (
    AIMaxRetriesExceededError,
    AIRecoveryFailedError,
    AIRollbackFailedError,
)


class RecoveryStrategy(str, Enum):
    """Available recovery strategies for failed steps."""
    RETRY      = "retry"
    ROLLBACK   = "rollback"
    COMPENSATE = "compensate"
    SKIP       = "skip"
    FAIL       = "fail"


class RetryCoordinator:
    """Executes a callable with configurable retries and optional backoff."""

    def retry(
        self,
        handler_fn:  Callable[[], Any],
        max_retries: int   = 3,
        backoff_s:   float = 0.0,
        task_id:     str   = "",
    ) -> Any:
        """
        Invoke *handler_fn* up to ``max_retries + 1`` times.
        Raises :class:`AIMaxRetriesExceededError` when all attempts fail.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                return handler_fn()
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries and backoff_s > 0:
                    time.sleep(backoff_s * (attempt + 1))

        raise AIMaxRetriesExceededError(
            f"All {max_retries + 1} attempts failed for '{task_id}': {last_exc}"
        ) from last_exc


class RollbackManager:
    """
    Registers and executes rollback functions for completed steps.

    Rollbacks are executed in LIFO order (reverse of registration).
    """

    def __init__(self) -> None:
        self._lock:      threading.Lock                           = threading.Lock()
        self._rollbacks: Dict[str, List[Tuple[str, Callable]]]   = {}
        # plan_id → [(step_id, rollback_fn), ...]

    def register_rollback(
        self,
        plan_id:     str,
        step_id:     str,
        rollback_fn: Callable[[], None],
    ) -> None:
        with self._lock:
            if plan_id not in self._rollbacks:
                self._rollbacks[plan_id] = []
            self._rollbacks[plan_id].append((step_id, rollback_fn))

    def rollback(
        self,
        plan_id:        str,
        up_to_step_id:  Optional[str] = None,
    ) -> bool:
        """
        Execute all registered rollbacks for *plan_id* in LIFO order.

        If *up_to_step_id* is given, only rolls back from the most recent
        entry down to (and including) that step.

        Returns True on full success.
        Raises :class:`AIRollbackFailedError` if any rollback fn raises.
        """
        with self._lock:
            entries = list(reversed(self._rollbacks.get(plan_id, [])))

        if not entries:
            return True

        if up_to_step_id:
            indices = [i for i, (sid, _) in enumerate(entries) if sid == up_to_step_id]
            if indices:
                entries = entries[: indices[0] + 1]

        errors: List[str] = []
        for step_id, fn in entries:
            try:
                fn()
            except Exception as exc:
                errors.append(f"Rollback for step '{step_id}' failed: {exc}")

        if errors:
            raise AIRollbackFailedError("; ".join(errors))
        return True

    def clear(self, plan_id: str) -> None:
        with self._lock:
            self._rollbacks.pop(plan_id, None)

    def registered_plan_count(self) -> int:
        with self._lock:
            return len(self._rollbacks)


class RecoveryManager:
    """
    Orchestrates failure recovery using pluggable :class:`RecoveryStrategy` rules.

    Strategies are matched by action-pattern (fnmatch) against the failed action.
    First match wins; default strategy is FAIL.
    """

    def __init__(
        self,
        retry_coordinator: RetryCoordinator,
        rollback_manager:  RollbackManager,
    ) -> None:
        self._retry:       RetryCoordinator                         = retry_coordinator
        self._rollback:    RollbackManager                          = rollback_manager
        self._lock:        threading.Lock                           = threading.Lock()
        self._strategies:  List[Tuple[str, RecoveryStrategy]]      = []

    def register_strategy(self, action_pattern: str, strategy: RecoveryStrategy) -> None:
        with self._lock:
            self._strategies.append((action_pattern, strategy))

    def get_strategy(self, action: str) -> RecoveryStrategy:
        """Return the first matching strategy for *action*, defaulting to FAIL."""
        with self._lock:
            for pattern, strategy in self._strategies:
                if fnmatch.fnmatch(action, pattern):
                    return strategy
        return RecoveryStrategy.FAIL

    def recover(
        self,
        session_id:    str,
        failed_action: str,
        handler_fn:    Optional[Callable[[], Any]] = None,
        plan_id:       Optional[str] = None,
        max_retries:   int   = 3,
        backoff_s:     float = 0.0,
    ) -> bool:
        """
        Attempt recovery for a failed action.

        Returns True if recovery succeeded.
        Raises :class:`AIRecoveryFailedError` when strategy is FAIL
        or all recovery attempts fail.
        """
        strategy = self.get_strategy(failed_action)

        if strategy == RecoveryStrategy.FAIL:
            raise AIRecoveryFailedError(
                f"Recovery strategy is FAIL for action '{failed_action}'"
            )

        if strategy == RecoveryStrategy.SKIP:
            return True

        if strategy == RecoveryStrategy.RETRY:
            if handler_fn is None:
                raise AIRecoveryFailedError("handler_fn required for RETRY strategy")
            try:
                self._retry.retry(
                    handler_fn  = handler_fn,
                    max_retries = max_retries,
                    backoff_s   = backoff_s,
                    task_id     = session_id,
                )
                return True
            except AIMaxRetriesExceededError as exc:
                raise AIRecoveryFailedError(str(exc)) from exc

        if strategy == RecoveryStrategy.ROLLBACK:
            if plan_id is None:
                raise AIRecoveryFailedError("plan_id required for ROLLBACK strategy")
            self._rollback.rollback(plan_id)
            return True

        if strategy == RecoveryStrategy.COMPENSATE:
            # Compensation is domain-specific — acknowledged as handled
            return True

        return False

    def strategy_count(self) -> int:
        with self._lock:
            return len(self._strategies)
