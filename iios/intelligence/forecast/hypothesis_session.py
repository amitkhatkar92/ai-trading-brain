"""
iios/intelligence/forecast/hypothesis_session.py
================================================
HypothesisSession — tracks one active round of hypothesis testing.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .hypothesis_constants import HypothesisStatus
from .hypothesis_exceptions import HypothesisStateError


class HypothesisSession:
    """
    Represents a single evaluation session for one hypothesis.

    State machine::

        PENDING → ACTIVE → (TESTING) → COMPLETED | FAILED | CANCELLED
    """

    PENDING   = "pending"
    ACTIVE    = "active"
    TESTING   = "testing"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"

    def __init__(
        self,
        session_id:    str | None = None,
        hypothesis_id: str        = "",
        metadata:      dict[str, Any] | None = None,
    ) -> None:
        self.session_id:    str            = session_id or str(uuid.uuid4())
        self.hypothesis_id: str            = hypothesis_id
        self._status:       str            = self.PENDING
        self.metadata:      dict[str, Any] = metadata or {}
        self._notes:        list[str]      = []
        self.started_at:    float | None   = None
        self.ended_at:      float | None   = None
        self.created_at:    float          = time.time()
        self._lock:         threading.RLock = threading.RLock()

    # -- Status accessors ──────────────────────────────────────────────────────

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_active(self) -> bool:
        return self._status in (self.ACTIVE, self.TESTING)

    @property
    def is_terminal(self) -> bool:
        return self._status in (self.COMPLETED, self.FAILED, self.CANCELLED)

    @property
    def duration_s(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.ended_at or time.time()
        return end - self.started_at

    # -- Transitions ───────────────────────────────────────────────────────────

    def start(self) -> None:
        with self._lock:
            if self._status != self.PENDING:
                raise HypothesisStateError(
                    self.session_id, self._status, self.PENDING
                )
            self._status    = self.ACTIVE
            self.started_at = time.time()

    def begin_testing(self) -> None:
        with self._lock:
            if self._status != self.ACTIVE:
                raise HypothesisStateError(
                    self.session_id, self._status, self.ACTIVE
                )
            self._status = self.TESTING

    def complete(self, note: str = "") -> None:
        with self._lock:
            if self.is_terminal:
                raise HypothesisStateError(
                    self.session_id, self._status, f"non-terminal"
                )
            if note:
                self._notes.append(note)
            self._status  = self.COMPLETED
            self.ended_at = time.time()

    def fail(self, reason: str = "") -> None:
        with self._lock:
            if self.is_terminal:
                raise HypothesisStateError(
                    self.session_id, self._status, "non-terminal"
                )
            if reason:
                self._notes.append(reason)
            self._status  = self.FAILED
            self.ended_at = time.time()

    def cancel(self, reason: str = "") -> None:
        with self._lock:
            if self.is_terminal:
                raise HypothesisStateError(
                    self.session_id, self._status, "non-terminal"
                )
            if reason:
                self._notes.append(reason)
            self._status  = self.CANCELLED
            self.ended_at = time.time()

    def add_note(self, note: str) -> None:
        with self._lock:
            self._notes.append(note)

    def notes(self) -> list[str]:
        with self._lock:
            return list(self._notes)

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":    self.session_id,
            "hypothesis_id": self.hypothesis_id,
            "status":        self._status,
            "started_at":    self.started_at,
            "ended_at":      self.ended_at,
            "duration_s":    self.duration_s,
            "notes":         list(self._notes),
            "metadata":      self.metadata,
            "created_at":    self.created_at,
        }
