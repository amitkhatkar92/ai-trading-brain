"""iios/execution/oms/order_queue/queue_policy.py
==================================================
QueuePolicy — ordering and filtering strategy for queue entries.

Eight named policies cover all institutional scheduling scenarios.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.order_queue.constants import (
    ExecutionMode,
    QueueEntryState,
    QueuePolicyType,
)
from iios.execution.oms.order_queue.queue_entry import QueueEntry
from iios.execution.oms.order_queue.queue_priority import priority_sort_key


@dataclass
class QueuePolicy:
    """
    Named policy: filters eligible entries and orders them for dispatch.

    select() = filter() + order()
    """
    policy_type:             QueuePolicyType = QueuePolicyType.FIFO
    description:             str  = ""
    is_active:               bool = True
    allowed_execution_modes: frozenset[ExecutionMode] = field(default_factory=frozenset)

    def filter(
        self,
        entries: list[QueueEntry],
        now: float | None = None,
    ) -> list[QueueEntry]:
        """
        Return entries eligible under this policy.
        Subclasses override for mode-specific filtering.
        """
        if not self.is_active:
            return []
        now = now if now is not None else time.time()
        result = [e for e in entries if e.state == QueueEntryState.READY and not e.is_expired]
        if self.allowed_execution_modes:
            result = [e for e in result if e.execution_mode in self.allowed_execution_modes]
        return result

    def order(self, entries: list[QueueEntry]) -> list[QueueEntry]:
        """Sort eligible entries by dispatch priority for this policy."""
        return sorted(entries, key=lambda e: priority_sort_key(e, self.policy_type))

    def select(
        self,
        entries: list[QueueEntry],
        now: float | None = None,
    ) -> list[QueueEntry]:
        """Combined filter + order pipeline."""
        return self.order(self.filter(entries, now))

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_type": self.policy_type.value,
            "description": self.description,
            "is_active":   self.is_active,
            "allowed_execution_modes": [m.value for m in self.allowed_execution_modes],
        }


# ── Policy Factories ──────────────────────────────────────────────────────────

def make_fifo_policy() -> QueuePolicy:
    """FIFO: all READY entries ordered by arrival time."""
    return QueuePolicy(
        policy_type=QueuePolicyType.FIFO,
        description="First-in, first-out dispatch ordering.",
    )


def make_priority_policy() -> QueuePolicy:
    """Priority: READY entries ordered by priority level, then arrival."""
    return QueuePolicy(
        policy_type=QueuePolicyType.PRIORITY,
        description="Dispatch highest-priority entries first.",
    )


def make_scheduled_policy() -> QueuePolicy:
    """Scheduled: READY entries ordered by their scheduled ready_at."""
    return QueuePolicy(
        policy_type=QueuePolicyType.SCHEDULED,
        description="Dispatch entries ordered by scheduled ready time.",
    )


def make_delayed_policy() -> QueuePolicy:
    """Delayed: same as SCHEDULED — entries with a ready_at delay."""
    return QueuePolicy(
        policy_type=QueuePolicyType.DELAYED,
        description="Dispatch entries after their delay has elapsed.",
    )


def make_recovery_policy() -> QueuePolicy:
    """
    Recovery: includes RETRY_PENDING entries.
    Ordered by (retry_count ASC, next_retry_at ASC).
    """
    class _RecoveryPolicy(QueuePolicy):
        def filter(self, entries: list[QueueEntry], now: float | None = None) -> list[QueueEntry]:
            if not self.is_active:
                return []
            t = now if now is not None else time.time()
            return [
                e for e in entries
                if (
                    (e.state == QueueEntryState.READY and not e.is_expired) or
                    (e.state == QueueEntryState.RETRY_PENDING and e.next_retry_at <= t)
                )
            ]

    return _RecoveryPolicy(
        policy_type=QueuePolicyType.RECOVERY,
        description="Dispatch retry-pending and ready entries for order recovery.",
    )


def make_replay_policy() -> QueuePolicy:
    """Replay: BACKTEST-mode READY entries, FIFO ordered."""
    return QueuePolicy(
        policy_type=QueuePolicyType.REPLAY,
        description="FIFO dispatch for BACKTEST mode entries.",
        allowed_execution_modes=frozenset({ExecutionMode.BACKTEST}),
    )


def make_paper_trading_policy() -> QueuePolicy:
    """Paper Trading: PAPER-mode READY entries, FIFO ordered."""
    return QueuePolicy(
        policy_type=QueuePolicyType.PAPER_TRADING,
        description="FIFO dispatch for PAPER trading entries.",
        allowed_execution_modes=frozenset({ExecutionMode.PAPER, ExecutionMode.SIMULATION}),
    )


def make_backtest_policy() -> QueuePolicy:
    """Backtest: BACKTEST-mode READY entries, FIFO ordered."""
    return QueuePolicy(
        policy_type=QueuePolicyType.BACKTEST,
        description="FIFO dispatch for BACKTEST entries.",
        allowed_execution_modes=frozenset({ExecutionMode.BACKTEST}),
    )


def get_policy(policy_type: QueuePolicyType) -> QueuePolicy:
    """Return a fresh policy instance for the given type."""
    _map = {
        QueuePolicyType.FIFO:          make_fifo_policy,
        QueuePolicyType.PRIORITY:      make_priority_policy,
        QueuePolicyType.SCHEDULED:     make_scheduled_policy,
        QueuePolicyType.DELAYED:       make_delayed_policy,
        QueuePolicyType.RECOVERY:      make_recovery_policy,
        QueuePolicyType.REPLAY:        make_replay_policy,
        QueuePolicyType.PAPER_TRADING: make_paper_trading_policy,
        QueuePolicyType.BACKTEST:      make_backtest_policy,
    }
    factory = _map.get(policy_type, make_fifo_policy)
    return factory()
