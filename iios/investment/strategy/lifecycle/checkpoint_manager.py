"""iios/investment/strategy/lifecycle/checkpoint_manager.py
Strategy state checkpointing — in-memory ring buffer with deep-copy isolation.

Provides save / load / purge for strategy execution state snapshots.
Designed as an extension point: persistence can be layered on top without
changing the interface.
"""
from __future__ import annotations

import copy
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional


@dataclass
class Checkpoint:
    """Immutable point-in-time state snapshot for a strategy."""

    checkpoint_id: str = field(
        default_factory=lambda: f"ckpt-{uuid.uuid4().hex[:10]}"
    )
    strategy_id: str = ""
    cycle_id: str = ""
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    label: str = ""

    def to_dict(self) -> dict:
        return {
            "checkpoint_id": self.checkpoint_id,
            "strategy_id": self.strategy_id,
            "cycle_id": self.cycle_id,
            "label": self.label,
            "created_at": self.created_at.isoformat(),
        }


class CheckpointManager:
    """
    Thread-safe checkpoint store.

    Keeps the last ``max_per_strategy`` checkpoints per strategy and a
    global ring of the last ``max_global`` checkpoints.

    State snapshots are deep-copied on save so mutation of the original
    dict after saving cannot corrupt the stored snapshot.
    """

    def __init__(
        self,
        max_per_strategy: int = 10,
        max_global: int = 500,
    ) -> None:
        self._lock = threading.RLock()
        self._per_strategy: Dict[str, Deque[Checkpoint]] = {}
        self._global: Deque[Checkpoint] = deque(maxlen=max_global)
        self._max_per = max_per_strategy
        self._max_global = max_global

    # ── Write ─────────────────────────────────────────────────────────────────

    def save(
        self,
        strategy_id: str,
        state_snapshot: Dict[str, Any],
        cycle_id: str = "",
        label: str = "",
    ) -> Checkpoint:
        """Create a deep-copy checkpoint and store it."""
        ckpt = Checkpoint(
            strategy_id=strategy_id,
            cycle_id=cycle_id,
            state_snapshot=copy.deepcopy(state_snapshot),
            label=label,
        )
        with self._lock:
            if strategy_id not in self._per_strategy:
                self._per_strategy[strategy_id] = deque(maxlen=self._max_per)
            self._per_strategy[strategy_id].append(ckpt)
            self._global.append(ckpt)
        return ckpt

    # ── Read ──────────────────────────────────────────────────────────────────

    def load_latest(self, strategy_id: str) -> Optional[Checkpoint]:
        """Return the most recent checkpoint for a strategy, or None."""
        with self._lock:
            deq = self._per_strategy.get(strategy_id)
            return deq[-1] if deq else None

    def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load a specific checkpoint by ID from the global ring."""
        with self._lock:
            for ckpt in self._global:
                if ckpt.checkpoint_id == checkpoint_id:
                    return ckpt
            return None

    def list_checkpoints(self, strategy_id: str) -> List[Checkpoint]:
        """Return all checkpoints for a strategy, oldest first."""
        with self._lock:
            deq = self._per_strategy.get(strategy_id, deque())
            return list(deq)

    # ── Purge ─────────────────────────────────────────────────────────────────

    def purge_strategy(self, strategy_id: str) -> int:
        """Remove all checkpoints for a strategy. Returns count removed."""
        with self._lock:
            deq = self._per_strategy.pop(strategy_id, deque())
            purged = len(deq)
            self._global = deque(
                (c for c in self._global if c.strategy_id != strategy_id),
                maxlen=self._max_global,
            )
            return purged

    # ── Query ─────────────────────────────────────────────────────────────────

    def checkpoint_count(self, strategy_id: Optional[str] = None) -> int:
        with self._lock:
            if strategy_id:
                return len(self._per_strategy.get(strategy_id, deque()))
            return len(self._global)

    def known_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._per_strategy.keys())
