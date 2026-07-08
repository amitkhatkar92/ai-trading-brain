"""
iios/intelligence/reasoning/reasoning_session.py
=================================================
ReasoningSession — mutable lifecycle object for one reasoning run.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .reasoning_constants import ReasoningStatus, ReasoningType, DEFAULT_SESSION_TIMEOUT_S
from .reasoning_exceptions import SessionStateError
from .reasoning_result import ReasoningOutput, ReasoningResult


@dataclass
class ReasoningSession:
    """
    A single reasoning session: from question to conclusion.

    Thread-safe via an internal RLock.
    All state mutations go through the lifecycle methods.
    """

    session_id:    str                    = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    topic:         str                    = ""
    reasoning_type: ReasoningType         = ReasoningType.GENERIC
    status:        ReasoningStatus        = ReasoningStatus.PENDING
    reasoner_id:   str | None             = None
    evidence_ids:  list[str]              = field(default_factory=list)
    debate_ids:    list[str]              = field(default_factory=list)
    outputs:       list[ReasoningOutput]  = field(default_factory=list)
    result:        ReasoningResult | None = None
    timeout_s:     float                  = DEFAULT_SESSION_TIMEOUT_S
    started_at:    float | None           = None
    ended_at:      float | None           = None
    metadata:      dict[str, Any]         = field(default_factory=dict)
    created_at:    float                  = field(default_factory=time.time)
    _lock:         threading.RLock        = field(
        default_factory=threading.RLock,
        compare=False,
        repr=False,
        init=False,
    )

    # -- Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        with self._lock:
            if self.status != ReasoningStatus.PENDING:
                raise SessionStateError(
                    self.session_id, self.status.value, "pending"
                )
            self.status     = ReasoningStatus.RUNNING
            self.started_at = time.time()

    def complete(self, result: ReasoningResult) -> None:
        with self._lock:
            if self.status not in (
                ReasoningStatus.RUNNING,
                ReasoningStatus.PAUSED,
            ):
                raise SessionStateError(
                    self.session_id, self.status.value, "running|paused"
                )
            self.status   = ReasoningStatus.COMPLETED
            self.result   = result
            self.ended_at = time.time()

    def fail(self, error: str = "") -> None:
        with self._lock:
            self.status   = ReasoningStatus.FAILED
            self.ended_at = time.time()
            if error:
                self.metadata["error"] = error

    def cancel(self) -> None:
        with self._lock:
            if self.status in (
                ReasoningStatus.COMPLETED,
                ReasoningStatus.FAILED,
            ):
                return
            self.status   = ReasoningStatus.CANCELLED
            self.ended_at = time.time()

    def pause(self) -> None:
        with self._lock:
            if self.status != ReasoningStatus.RUNNING:
                raise SessionStateError(
                    self.session_id, self.status.value, "running"
                )
            self.status = ReasoningStatus.PAUSED

    def resume(self) -> None:
        with self._lock:
            if self.status != ReasoningStatus.PAUSED:
                raise SessionStateError(
                    self.session_id, self.status.value, "paused"
                )
            self.status = ReasoningStatus.RUNNING

    # -- Evidence & debate bookkeeping ─────────────────────────────────────────

    def add_evidence(self, evidence_id: str) -> None:
        with self._lock:
            if evidence_id not in self.evidence_ids:
                self.evidence_ids.append(evidence_id)

    def add_debate(self, debate_id: str) -> None:
        with self._lock:
            if debate_id not in self.debate_ids:
                self.debate_ids.append(debate_id)

    def add_output(self, output: ReasoningOutput) -> None:
        with self._lock:
            self.outputs.append(output)

    # -- Properties ────────────────────────────────────────────────────────────

    @property
    def duration_ms(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.ended_at or time.time()
        return (end - self.started_at) * 1_000

    @property
    def is_timed_out(self) -> bool:
        if self.started_at is None:
            return False
        return time.time() - self.started_at > self.timeout_s

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            ReasoningStatus.COMPLETED,
            ReasoningStatus.FAILED,
            ReasoningStatus.CANCELLED,
            ReasoningStatus.TIMEOUT,
        )

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":     self.session_id,
            "topic":          self.topic,
            "reasoning_type": self.reasoning_type.value,
            "status":         self.status.value,
            "reasoner_id":    self.reasoner_id,
            "evidence_count": len(self.evidence_ids),
            "debate_count":   len(self.debate_ids),
            "output_count":   len(self.outputs),
            "timeout_s":      self.timeout_s,
            "duration_ms":    round(self.duration_ms, 2),
            "started_at":     self.started_at,
            "ended_at":       self.ended_at,
            "metadata":       self.metadata,
            "created_at":     self.created_at,
        }
