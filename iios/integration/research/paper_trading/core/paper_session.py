"""core/paper_session.py — PaperSession model."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import SessionStatus
from iios.integration.research.paper_trading.paper_trading_exceptions import SessionStateError


@dataclass
class PaperSession:
    """
    Tracks the lifecycle and progress of a paper trading session.

    A session ties a PaperAccount to a strategy replay over a bar sequence.
    """

    session_id:         str
    account_id:         str
    strategy_id:        Optional[str]
    strategy_name:      Optional[str]
    status:             SessionStatus     = SessionStatus.IDLE
    start_timestamp:    Optional[float]   = None   # simulation clock start
    end_timestamp:      Optional[float]   = None   # simulation clock end
    current_timestamp:  float             = 0.0
    bar_index:          int               = 0
    total_bars:         int               = 0
    created_at:         float             = field(default_factory=time.time)
    started_at:         Optional[float]   = None
    ended_at:           Optional[float]   = None
    error_message:      Optional[str]     = None
    checkpoint:         Optional[dict]    = None
    tags:               list[str]         = field(default_factory=list)
    metadata:           dict[str, Any]    = field(default_factory=dict)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        account_id:    str,
        strategy_id:   Optional[str]  = None,
        strategy_name: Optional[str]  = None,
        *,
        session_id:    Optional[str]  = None,
        tags:          Optional[list] = None,
        metadata:      Optional[dict] = None,
    ) -> "PaperSession":
        return cls(
            session_id     = session_id or f"sess_{uuid.uuid4().hex[:12]}",
            account_id     = account_id,
            strategy_id    = strategy_id,
            strategy_name  = strategy_name,
            status         = SessionStatus.IDLE,
            tags           = tags or [],
            metadata       = metadata or {},
        )

    # ── Lifecycle transitions ─────────────────────────────────────────────────

    def start(self, total_bars: int) -> None:
        if self.status != SessionStatus.IDLE:
            raise SessionStateError(
                f"Cannot start session in status {self.status.value!r}"
            )
        self.total_bars  = total_bars
        self.bar_index   = 0
        self.status      = SessionStatus.ACTIVE
        self.started_at  = time.time()

    def advance(self, bar_index: int, timestamp: float) -> None:
        self.bar_index         = bar_index
        self.current_timestamp = timestamp

    def end(self, *, failed: bool = False, aborted: bool = False) -> None:
        if failed:
            self.status = SessionStatus.FAILED
        elif aborted:
            self.status = SessionStatus.CANCELLED
        else:
            self.status = SessionStatus.COMPLETED
        self.ended_at = time.time()

    def save_checkpoint(self, state: dict) -> None:
        """Persist an arbitrary state dict for session recovery."""
        self.checkpoint = state

    # ── Derived properties ────────────────────────────────────────────────────

    def progress(self) -> float:
        """Progress 0.0 – 1.0."""
        if self.total_bars <= 0:
            return 0.0
        return min(1.0, self.bar_index / self.total_bars)

    def is_active(self) -> bool:
        return self.status == SessionStatus.ACTIVE

    def is_terminal(self) -> bool:
        return self.status in (
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        )

    def elapsed_sec(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.ended_at or time.time()
        return end - self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":        self.session_id,
            "account_id":        self.account_id,
            "strategy_id":       self.strategy_id,
            "strategy_name":     self.strategy_name,
            "status":            self.status.value,
            "start_timestamp":   self.start_timestamp,
            "end_timestamp":     self.end_timestamp,
            "current_timestamp": self.current_timestamp,
            "bar_index":         self.bar_index,
            "total_bars":        self.total_bars,
            "progress":          self.progress(),
            "created_at":        self.created_at,
            "started_at":        self.started_at,
            "ended_at":          self.ended_at,
            "error_message":     self.error_message,
            "tags":              self.tags,
            "metadata":          self.metadata,
        }
