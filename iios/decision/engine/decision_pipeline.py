"""
decision_pipeline.py — iios.decision.engine
=============================================
Mutable processing pipeline tracking a single decision workflow.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    PIPELINE_ACTIVE_STATES,
    PIPELINE_TERMINAL_STATES,
    PIPELINE_VALID_TRANSITIONS,
    PipelineState,
)
from .exceptions import DecisionPipelineError


class DecisionPipeline:
    """
    Tracks the full processing state of one decision workflow.

    Created by :class:`DecisionPipelineFactory` for each submitted request.
    Mutated by :class:`DecisionManager` as the workflow advances.

    State machine::

        IDLE → INITIALIZING → COLLECTING → VALIDATING →
        DISPATCHING → EVALUATING → PUBLISHING → COMPLETED
        Any active state → FAILED | STOPPED | CANCELLED

    Thread safety: all mutations are serialised by an internal RLock.
    """

    def __init__(
        self,
        *,
        pipeline_id:  Optional[str] = None,
        session_id:   str           = "",
        request_id:   str           = "",
        decision_id:  str           = "",
        workflow_id:  str           = "",
        portfolio_id: str           = "",
        strategy_id:  str           = "",
    ) -> None:
        self._pipeline_id  = pipeline_id or str(uuid.uuid4())
        self._session_id   = session_id
        self._request_id   = request_id
        self._decision_id  = decision_id
        self._workflow_id  = workflow_id
        self._portfolio_id = portfolio_id
        self._strategy_id  = strategy_id

        now = time.time()
        self._state:        PipelineState        = PipelineState.IDLE
        self._failure_reason: str                = ""
        self._created_at:  float                 = now
        self._updated_at:  float                 = now
        self._started_at:  Optional[float]       = None
        self._completed_at: Optional[float]      = None
        self._collection_start: Optional[float]  = None
        self._collection_end:   Optional[float]  = None
        self._dispatch_start:   Optional[float]  = None
        self._dispatch_end:     Optional[float]  = None
        self._inputs:     Dict[str, Any]         = {}
        self._results:    Dict[str, Any]         = {}

        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def pipeline_id(self) -> str:
        return self._pipeline_id

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def decision_id(self) -> str:
        return self._decision_id

    @property
    def state(self) -> PipelineState:
        with self._lock:
            return self._state

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._state in PIPELINE_ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        with self._lock:
            return self._state in PIPELINE_TERMINAL_STATES

    @property
    def failure_reason(self) -> str:
        with self._lock:
            return self._failure_reason

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def started_at(self) -> Optional[float]:
        with self._lock:
            return self._started_at

    @property
    def completed_at(self) -> Optional[float]:
        with self._lock:
            return self._completed_at

    @property
    def collection_time_s(self) -> float:
        with self._lock:
            if self._collection_start and self._collection_end:
                return self._collection_end - self._collection_start
            return 0.0

    @property
    def dispatch_time_s(self) -> float:
        with self._lock:
            if self._dispatch_start and self._dispatch_end:
                return self._dispatch_end - self._dispatch_start
            return 0.0

    @property
    def total_time_s(self) -> float:
        with self._lock:
            if self._started_at:
                end = self._completed_at or time.time()
                return end - self._started_at
            return 0.0

    @property
    def inputs(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._inputs)

    @property
    def results(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._results)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _advance(self, to_state: PipelineState, reason: str = "") -> None:
        """Internal: advance to *to_state* or raise DecisionPipelineError."""
        allowed = PIPELINE_VALID_TRANSITIONS.get(self._state, frozenset())
        if to_state not in allowed:
            raise DecisionPipelineError(
                self._pipeline_id,
                f"Invalid pipeline transition {self._state.value!r} → {to_state.value!r}",
            )
        self._state    = to_state
        self._updated_at = time.time()
        if reason:
            self._failure_reason = reason

    def start(self) -> None:
        """IDLE → INITIALIZING; marks start time."""
        with self._lock:
            self._advance(PipelineState.INITIALIZING)
            self._started_at = time.time()

    def begin_collecting(self) -> None:
        """INITIALIZING → COLLECTING."""
        with self._lock:
            self._advance(PipelineState.COLLECTING)
            self._collection_start = time.time()

    def begin_validating(self) -> None:
        """COLLECTING → VALIDATING; marks collection end."""
        with self._lock:
            self._collection_end = time.time()
            self._advance(PipelineState.VALIDATING)

    def retry_collecting(self) -> None:
        """VALIDATING → COLLECTING (re-collect on insufficient inputs)."""
        with self._lock:
            self._advance(PipelineState.COLLECTING)
            self._collection_start = time.time()

    def begin_dispatching(self) -> None:
        """VALIDATING → DISPATCHING."""
        with self._lock:
            self._advance(PipelineState.DISPATCHING)
            self._dispatch_start = time.time()

    def begin_evaluating(self) -> None:
        """DISPATCHING → EVALUATING."""
        with self._lock:
            self._advance(PipelineState.EVALUATING)

    def begin_publishing(self) -> None:
        """EVALUATING → PUBLISHING; marks dispatch end."""
        with self._lock:
            self._dispatch_end = time.time()
            self._advance(PipelineState.PUBLISHING)

    def complete(self) -> None:
        """PUBLISHING → COMPLETED; marks completion time."""
        with self._lock:
            self._advance(PipelineState.COMPLETED)
            self._completed_at = time.time()

    def fail(self, reason: str = "") -> None:
        """Any active state → FAILED."""
        with self._lock:
            allowed = PIPELINE_VALID_TRANSITIONS.get(self._state, frozenset())
            if PipelineState.FAILED not in allowed:
                return  # already terminal — ignore
            self._state          = PipelineState.FAILED
            self._failure_reason = reason
            self._completed_at   = time.time()
            self._updated_at     = self._completed_at

    def stop(self) -> None:
        """Any active state → STOPPED."""
        with self._lock:
            allowed = PIPELINE_VALID_TRANSITIONS.get(self._state, frozenset())
            if PipelineState.STOPPED not in allowed:
                return  # already terminal — ignore
            self._state        = PipelineState.STOPPED
            self._completed_at = time.time()
            self._updated_at   = self._completed_at

    def cancel(self) -> None:
        """IDLE → CANCELLED."""
        with self._lock:
            allowed = PIPELINE_VALID_TRANSITIONS.get(self._state, frozenset())
            if PipelineState.CANCELLED not in allowed:
                return
            self._state        = PipelineState.CANCELLED
            self._completed_at = time.time()
            self._updated_at   = self._completed_at

    # ------------------------------------------------------------------
    # Input / result management
    # ------------------------------------------------------------------
    def add_input(self, key: str, value: Any) -> None:
        """Store a collected institutional input."""
        with self._lock:
            self._inputs[key] = value

    def add_result(self, key: str, value: Any) -> None:
        """Store a dispatch or evaluation result."""
        with self._lock:
            self._results[key] = value

    def get_input(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._inputs.get(key, default)

    def get_result(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._results.get(key, default)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        with self._lock:
            return {
                "pipeline_id":       self._pipeline_id,
                "session_id":        self._session_id,
                "request_id":        self._request_id,
                "decision_id":       self._decision_id,
                "state":             self._state.value,
                "failure_reason":    self._failure_reason,
                "collection_time_s": self.collection_time_s,
                "dispatch_time_s":   self.dispatch_time_s,
                "total_time_s":      self.total_time_s,
                "created_at":        self._created_at,
                "started_at":        self._started_at,
                "completed_at":      self._completed_at,
                "framework_version": VERSION,
            }

    def __repr__(self) -> str:
        return (
            f"DecisionPipeline(id={self._pipeline_id!r}, "
            f"decision={self._decision_id!r}, "
            f"state={self._state.value!r})"
        )
