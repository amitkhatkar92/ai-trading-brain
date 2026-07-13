"""iios/investment/strategy/lifecycle/recovery_engine.py
Top-level recovery coordinator.

Integrates CheckpointManager, FailureHandler, and RestartManager into
a single cohesive recovery system.  The StrategyLifecycleEngine is the
only caller; strategies never interact with the recovery engine directly.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, List, Optional

from iios.investment.strategy.lifecycle.checkpoint_manager import (
    Checkpoint,
    CheckpointManager,
)
from iios.investment.strategy.lifecycle.failure_handler import (
    CircuitState,
    FailureHandler,
    FailurePolicy,
    FailureRecord,
)
from iios.investment.strategy.lifecycle.restart_manager import (
    RestartManager,
    RestartPolicy,
)

logger = logging.getLogger(__name__)


class RecoveryDecision:
    """Result of recovery analysis for a failed or completed strategy."""

    __slots__ = (
        "strategy_id", "should_retry", "should_restart",
        "retry_delay_s", "checkpoint", "reason",
    )

    def __init__(
        self,
        strategy_id: str,
        should_retry: bool = False,
        should_restart: bool = False,
        retry_delay_s: float = 0.0,
        checkpoint: Optional[Checkpoint] = None,
        reason: str = "",
    ) -> None:
        self.strategy_id = strategy_id
        self.should_retry = should_retry
        self.should_restart = should_restart
        self.retry_delay_s = retry_delay_s
        self.checkpoint = checkpoint
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "should_retry": self.should_retry,
            "should_restart": self.should_restart,
            "retry_delay_s": self.retry_delay_s,
            "has_checkpoint": self.checkpoint is not None,
            "reason": self.reason,
        }


class RecoveryEngine:
    """
    Orchestrates recovery for failed and completed strategy executions.

    Workflow:
      1. Strategy fails → LifecycleEngine calls handle_failure()
      2. RecoveryEngine consults FailureHandler: circuit open? max retries?
      3. Returns RecoveryDecision (retry or restart recommendation)
      4. On success → LifecycleEngine calls handle_success() to reset counts

    Checkpointing:
      - save_checkpoint() should be called before each execution
      - On failure, handle_failure() returns the latest checkpoint so the
        strategy can resume from its last good state
    """

    def __init__(
        self,
        default_failure_policy: Optional[FailurePolicy] = None,
        max_restarts_per_strategy: int = 5,
        restart_fn: Optional[Callable[[str], None]] = None,
        max_checkpoints_per_strategy: int = 10,
    ) -> None:
        self._checkpoint_manager = CheckpointManager(
            max_per_strategy=max_checkpoints_per_strategy
        )
        self._failure_handler = FailureHandler(
            default_policy=default_failure_policy
        )
        self._restart_manager = RestartManager(
            restart_fn=restart_fn,
            max_restarts=max_restarts_per_strategy,
        )

    # ── Configuration ─────────────────────────────────────────────────────────

    def configure_strategy(
        self,
        strategy_id: str,
        failure_policy: Optional[FailurePolicy] = None,
        restart_policy: RestartPolicy = RestartPolicy.NEVER,
    ) -> None:
        """Set per-strategy failure and restart policies."""
        if failure_policy is not None:
            self._failure_handler.set_policy(strategy_id, failure_policy)
        self._restart_manager.set_policy(strategy_id, restart_policy)

    # ── Checkpointing ─────────────────────────────────────────────────────────

    def save_checkpoint(
        self,
        strategy_id: str,
        state_snapshot: Dict[str, Any],
        cycle_id: str = "",
        label: str = "",
    ) -> Checkpoint:
        return self._checkpoint_manager.save(
            strategy_id, state_snapshot, cycle_id, label
        )

    def load_latest_checkpoint(self, strategy_id: str) -> Optional[Checkpoint]:
        return self._checkpoint_manager.load_latest(strategy_id)

    def list_checkpoints(self, strategy_id: str) -> List[Checkpoint]:
        return self._checkpoint_manager.list_checkpoints(strategy_id)

    # ── Failure / success handling ────────────────────────────────────────────

    def handle_failure(
        self,
        strategy_id: str,
        error_type: str,
        error_message: str,
        attempt: int,
        is_terminal_failure: bool = False,
    ) -> RecoveryDecision:
        """
        Process a strategy failure and return a recovery recommendation.

        Args:
            strategy_id: The failing strategy.
            error_type:  Exception class name or error category string.
            error_message: Human-readable description.
            attempt:     0-based attempt index (0 = first failure).
            is_terminal_failure: If True, bypass retry logic entirely.
        """
        self._failure_handler.record_failure(
            strategy_id, error_type, error_message, attempt
        )
        checkpoint = self._checkpoint_manager.load_latest(strategy_id)

        if is_terminal_failure:
            should_restart = self._restart_manager.should_restart(
                strategy_id, exit_was_failure=True
            )
            if should_restart:
                self._restart_manager.schedule_restart(
                    strategy_id,
                    reason=error_message,
                    previous_status="failed",
                )
            return RecoveryDecision(
                strategy_id=strategy_id,
                should_retry=False,
                should_restart=should_restart,
                checkpoint=checkpoint,
                reason=f"Terminal failure: {error_message}",
            )

        should_retry = self._failure_handler.should_retry(
            strategy_id, error_type, attempt
        )
        retry_delay = (
            self._failure_handler.retry_delay(strategy_id, attempt)
            if should_retry
            else 0.0
        )

        # When retries are exhausted, check the restart policy
        should_restart = False
        if not should_retry:
            should_restart = self._restart_manager.should_restart(
                strategy_id, exit_was_failure=True
            )
            if should_restart:
                self._restart_manager.schedule_restart(
                    strategy_id,
                    reason=f"Retries exhausted: {error_message}",
                    previous_status="failed",
                )

        return RecoveryDecision(
            strategy_id=strategy_id,
            should_retry=should_retry,
            should_restart=should_restart,
            retry_delay_s=retry_delay,
            checkpoint=checkpoint,
            reason=(
                f"Retry {attempt + 1} in {retry_delay:.1f}s"
                if should_retry
                else f"Max retries reached ({error_type})"
            ),
        )

    def handle_success(self, strategy_id: str) -> None:
        """Signal successful execution — resets failure counts and circuit."""
        self._failure_handler.record_success(strategy_id)

    def handle_completion(
        self, strategy_id: str
    ) -> Optional[RecoveryDecision]:
        """
        Handle a normally-completed strategy.

        Returns a RecoveryDecision if the strategy should be restarted;
        returns None if no further action is needed.
        """
        self._failure_handler.record_success(strategy_id)
        should_restart = self._restart_manager.should_restart(
            strategy_id, exit_was_failure=False
        )
        if should_restart:
            self._restart_manager.schedule_restart(
                strategy_id,
                reason="normal completion",
                previous_status="completed",
            )
            return RecoveryDecision(
                strategy_id=strategy_id,
                should_restart=True,
                reason="Restart-on-completion policy",
            )
        return None

    # ── Circuit breaker ───────────────────────────────────────────────────────

    def is_circuit_open(self, strategy_id: str) -> bool:
        return self._failure_handler.is_circuit_open(strategy_id)

    def circuit_state(self, strategy_id: str) -> CircuitState:
        return self._failure_handler.circuit_state(strategy_id)

    # ── Observability ─────────────────────────────────────────────────────────

    def failure_history(self, strategy_id: str) -> List[FailureRecord]:
        return self._failure_handler.get_failure_history(strategy_id)

    def restart_count(self, strategy_id: str) -> int:
        return self._restart_manager.restart_count(strategy_id)

    def reset_strategy(self, strategy_id: str) -> None:
        """Fully reset all recovery state for a strategy."""
        self._failure_handler.reset_strategy(strategy_id)
        self._restart_manager.reset_strategy(strategy_id)
        self._checkpoint_manager.purge_strategy(strategy_id)

    # ── Sub-system access (for advanced callers) ──────────────────────────────

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        return self._checkpoint_manager

    @property
    def failure_handler(self) -> FailureHandler:
        return self._failure_handler

    @property
    def restart_manager(self) -> RestartManager:
        return self._restart_manager
