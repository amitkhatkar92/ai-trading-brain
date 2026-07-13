"""iios/investment/strategy/lifecycle/restart_manager.py
Strategy restart policies and coordinated restart scheduling.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RestartPolicy(str, Enum):
    """When a strategy should be automatically restarted after termination."""

    NEVER         = "never"
    ON_FAILURE    = "on_failure"    # restart only if the strategy failed
    ON_COMPLETION = "on_completion" # restart when it finishes normally
    ALWAYS        = "always"        # restart regardless of exit reason


@dataclass
class RestartRecord:
    """Log entry for a single strategy restart event."""

    strategy_id: str
    reason: str
    restart_number: int
    restarted_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    previous_status: str = ""


class RestartManager:
    """
    Manages restart policies and coordinates restart decision logic.

    When the RecoveryEngine detects a failed or completed strategy it
    calls should_restart() and then schedule_restart() which invokes
    the user-supplied restart_fn callback.
    """

    def __init__(
        self,
        restart_fn: Optional[Callable[[str], None]] = None,
        max_restarts: int = 5,
    ) -> None:
        """
        Args:
            restart_fn: Called with strategy_id when a restart is triggered.
            max_restarts: Maximum lifetime restart count per strategy.
        """
        self._restart_fn = restart_fn
        self._max_restarts = max_restarts
        self._lock = threading.RLock()
        self._policies: Dict[str, RestartPolicy] = {}
        self._restart_counts: Dict[str, int] = {}
        self._restart_history: Dict[str, List[RestartRecord]] = {}

    # ── Policy API ────────────────────────────────────────────────────────────

    def set_policy(self, strategy_id: str, policy: RestartPolicy) -> None:
        with self._lock:
            self._policies[strategy_id] = policy

    def get_policy(self, strategy_id: str) -> RestartPolicy:
        with self._lock:
            return self._policies.get(strategy_id, RestartPolicy.NEVER)

    # ── Decision API ──────────────────────────────────────────────────────────

    def should_restart(self, strategy_id: str, exit_was_failure: bool) -> bool:
        """Return True if the strategy should be automatically restarted."""
        policy = self.get_policy(strategy_id)
        with self._lock:
            count = self._restart_counts.get(strategy_id, 0)

        if count >= self._max_restarts:
            return False

        if policy == RestartPolicy.NEVER:
            return False
        if policy == RestartPolicy.ON_FAILURE:
            return exit_was_failure
        if policy == RestartPolicy.ON_COMPLETION:
            return not exit_was_failure
        if policy == RestartPolicy.ALWAYS:
            return True
        return False

    def schedule_restart(
        self,
        strategy_id: str,
        reason: str,
        previous_status: str = "",
    ) -> bool:
        """
        Log the restart event and invoke restart_fn.

        Returns True if the restart callback was triggered successfully.
        """
        with self._lock:
            count = self._restart_counts.get(strategy_id, 0) + 1
            self._restart_counts[strategy_id] = count
            record = RestartRecord(
                strategy_id=strategy_id,
                reason=reason,
                restart_number=count,
                previous_status=previous_status,
            )
            self._restart_history.setdefault(strategy_id, []).append(record)

        logger.info(
            "Restart #%d scheduled for %s — reason: %s",
            count, strategy_id, reason,
        )

        if self._restart_fn is not None:
            try:
                self._restart_fn(strategy_id)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "restart_fn raised for strategy %s", strategy_id
                )
        return True

    # ── Observability ─────────────────────────────────────────────────────────

    def restart_count(self, strategy_id: str) -> int:
        with self._lock:
            return self._restart_counts.get(strategy_id, 0)

    def restart_history(self, strategy_id: str) -> List[RestartRecord]:
        with self._lock:
            return list(self._restart_history.get(strategy_id, []))

    def reset_strategy(self, strategy_id: str) -> None:
        """Clear restart history and count for a strategy."""
        with self._lock:
            self._restart_counts.pop(strategy_id, None)
            self._restart_history.pop(strategy_id, None)
