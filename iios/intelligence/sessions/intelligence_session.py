"""
iios/intelligence/sessions/intelligence_session.py
==================================================
IntelligenceSession — the fundamental unit of intelligence execution.

A session groups one or more workflow executions under a single identity,
supports nesting (parent → child), checkpointing, pause/resume, and
TTL-based expiry.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from ..intelligence_constants import (
    SessionStatus,
    Priority,
    SESSION_TTL_SECONDS,
    SYSTEM_ACTOR,
)
from .session_result import SessionResult

__all__ = ["IntelligenceSession"]


@dataclass
class IntelligenceSession:
    """
    Represents a complete intelligence execution context.

    Fields
    ------
    session_id:    Unique session ID (UUID)
    actor:         Who initiated the session
    priority:      Execution priority
    parent_id:     Parent session ID (for nested sessions)
    status:        Current lifecycle status
    result:        Populated after session completes
    metadata:      Free-form key/value pairs
    tags:          Arbitrary string labels
    created_at:    Creation timestamp
    started_at:    When execution began
    finished_at:   When execution ended
    ttl:           Time-to-live in seconds
    checkpoint_id: ID of last saved checkpoint (None if none)
    """
    session_id:    str                      = field(default_factory=lambda: str(uuid.uuid4()))
    actor:         str                      = SYSTEM_ACTOR
    priority:      Priority                 = Priority.NORMAL
    parent_id:     Optional[str]            = None
    status:        SessionStatus            = SessionStatus.PENDING
    result:        Optional[SessionResult]  = None
    metadata:      dict[str, Any]           = field(default_factory=dict)
    tags:          list[str]                = field(default_factory=list)
    created_at:    float                    = field(default_factory=time.time)
    started_at:    Optional[float]          = None
    finished_at:   Optional[float]          = None
    ttl:           float                    = float(SESSION_TTL_SECONDS)
    checkpoint_id: Optional[str]            = None

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl

    @property
    def is_active(self) -> bool:
        return self.status in (SessionStatus.ACTIVE, SessionStatus.RECOVERING)

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
            SessionStatus.EXPIRED,
        )

    @property
    def is_nested(self) -> bool:
        return self.parent_id is not None

    @property
    def duration_ms(self) -> float:
        end = self.finished_at or time.time()
        start = self.started_at or self.created_at
        return (end - start) * 1_000.0

    # ── Lifecycle transitions ─────────────────────────────────────────────────

    def start(self) -> None:
        self.status     = SessionStatus.ACTIVE
        self.started_at = time.time()

    def pause(self) -> None:
        if self.status == SessionStatus.ACTIVE:
            self.status = SessionStatus.PAUSED

    def resume(self) -> None:
        if self.status == SessionStatus.PAUSED:
            self.status = SessionStatus.ACTIVE

    def complete(self, result: Optional[SessionResult] = None) -> None:
        self.status      = SessionStatus.COMPLETED
        self.finished_at = time.time()
        if result is not None:
            self.result = result

    def fail(self, reason: str = "") -> None:
        self.status      = SessionStatus.FAILED
        self.finished_at = time.time()
        if self.result is None:
            self.result = SessionResult(session_id=self.session_id)
        self.result.fail(reason)

    def cancel(self) -> None:
        self.status      = SessionStatus.CANCELLED
        self.finished_at = time.time()

    def expire(self) -> None:
        self.status      = SessionStatus.EXPIRED
        self.finished_at = time.time()

    def mark_recovering(self, checkpoint_id: Optional[str] = None) -> None:
        self.status        = SessionStatus.RECOVERING
        self.checkpoint_id = checkpoint_id

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "session_id":    self.session_id,
            "actor":         self.actor,
            "priority":      self.priority.name,
            "parent_id":     self.parent_id,
            "status":        self.status.value,
            "tags":          self.tags,
            "created_at":    self.created_at,
            "started_at":    self.started_at,
            "finished_at":   self.finished_at,
            "duration_ms":   round(self.duration_ms, 3),
            "is_expired":    self.is_expired,
            "checkpoint_id": self.checkpoint_id,
        }
