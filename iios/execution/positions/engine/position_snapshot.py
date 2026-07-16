"""iios/execution/positions/engine/position_snapshot.py
==================================================
EngineSnapshot — full point-in-time snapshot of the Position Engine.

PositionSummary — lightweight per-position summary included in a snapshot.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .constants import VERSION
from .position_statistics import EngineStatistics

if TYPE_CHECKING:
    from iios.execution.positions.lifecycle import Position


# ── PositionSummary ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PositionSummary:
    """
    Lightweight read-only summary of a single position,
    included in an ``EngineSnapshot``.
    """

    position_id:    str
    instrument:     str
    exchange:       str
    direction:      str
    state:          str
    quantity:       str
    open_quantity:  str
    portfolio_id:   str
    strategy_id:    str
    created_at:     float
    updated_at:     float

    @classmethod
    def from_position(cls, position: "Position") -> "PositionSummary":
        return cls(
            position_id=position.position_id,
            instrument=position.instrument,
            exchange=position.exchange,
            direction=position.direction.value,
            state=position.state.value,
            quantity=str(position.quantity),
            open_quantity=str(position.open_quantity),
            portfolio_id=position.portfolio_id,
            strategy_id=position.strategy_id,
            created_at=position.created_at,
            updated_at=position.updated_at,
        )

    def to_dict(self) -> dict:
        return {
            "position_id":   self.position_id,
            "instrument":    self.instrument,
            "exchange":      self.exchange,
            "direction":     self.direction,
            "state":         self.state,
            "quantity":      self.quantity,
            "open_quantity": self.open_quantity,
            "portfolio_id":  self.portfolio_id,
            "strategy_id":   self.strategy_id,
            "created_at":    self.created_at,
            "updated_at":    self.updated_at,
        }


# ── EngineSnapshot ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EngineSnapshot:
    """
    Full point-in-time snapshot of the Position Engine.

    Captures aggregate counts, per-position summaries, and statistics.
    Produced by ``PositionEngine.snapshot()``.
    """

    snapshot_id:     str
    total_positions: int
    active_count:    int
    closed_count:    int
    archived_count:  int
    suspended_count: int
    summaries:       tuple[PositionSummary, ...]
    statistics:      EngineStatistics
    taken_at:        float
    version:         str = VERSION
    metadata:        Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_empty(self) -> bool:
        return self.total_positions == 0

    @property
    def is_healthy(self) -> bool:
        """Healthy when the engine has no failed operations on record."""
        return self.statistics.failure_count == 0

    @property
    def summary_count(self) -> int:
        return len(self.summaries)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":     self.snapshot_id,
            "total_positions": self.total_positions,
            "active_count":    self.active_count,
            "closed_count":    self.closed_count,
            "archived_count":  self.archived_count,
            "suspended_count": self.suspended_count,
            "summary_count":   self.summary_count,
            "summaries":       [s.to_dict() for s in self.summaries],
            "statistics":      self.statistics.to_dict(),
            "taken_at":        self.taken_at,
            "version":         self.version,
            "is_empty":        self.is_empty,
            "is_healthy":      self.is_healthy,
            "metadata":        dict(self.metadata),
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def make_engine_snapshot(
    positions:   List["Position"],
    statistics:  EngineStatistics,
    *,
    metadata: Dict[str, Any] | None = None,
) -> EngineSnapshot:
    """Build a snapshot from a list of live positions and current statistics."""
    from iios.execution.positions.lifecycle import (
        ACTIVE_STATES, CLOSED_STATES, TERMINAL_STATES, SUSPENDED_STATES,
    )
    summaries    = tuple(PositionSummary.from_position(p) for p in positions)
    active_cnt   = sum(1 for p in positions if p.state in ACTIVE_STATES)
    closed_cnt   = sum(1 for p in positions if p.state in CLOSED_STATES)
    archived_cnt = sum(1 for p in positions if p.state in TERMINAL_STATES)
    suspended_cnt = sum(1 for p in positions if p.state in SUSPENDED_STATES)

    return EngineSnapshot(
        snapshot_id=str(uuid.uuid4()),
        total_positions=len(positions),
        active_count=active_cnt,
        closed_count=closed_cnt,
        archived_count=archived_cnt,
        suspended_count=suspended_cnt,
        summaries=summaries,
        statistics=statistics,
        taken_at=time.time(),
        metadata=metadata or {},
    )
