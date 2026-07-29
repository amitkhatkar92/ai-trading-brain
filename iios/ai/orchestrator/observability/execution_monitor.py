"""
execution_monitor.py -- iios.ai.orchestrator.observability
============================================================
ExecutionMonitor, ProgressTracker, Timeline, ExecutionMetrics.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class TimelineEvent:
    """Immutable timeline event for a session."""
    event_id:    str
    event_type:  str
    step_id:     Optional[str]
    timestamp:   float
    duration_ms: Optional[float]

    @classmethod
    def create(
        cls,
        event_type:  str,
        step_id:     Optional[str]   = None,
        duration_ms: Optional[float] = None,
    ) -> "TimelineEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = event_type,
            step_id     = step_id,
            timestamp   = time.time(),
            duration_ms = duration_ms,
        )


@dataclass(frozen=True)
class Timeline:
    """Ordered, immutable sequence of timeline events for a session."""
    session_id: str
    events:     Tuple[TimelineEvent, ...]

    @classmethod
    def build(cls, session_id: str, events: List[TimelineEvent]) -> "Timeline":
        return cls(session_id=session_id, events=tuple(events))

    def event_count(self) -> int:
        return len(self.events)


@dataclass(frozen=True)
class ExecutionMetrics:
    """Immutable execution metrics snapshot for a session."""
    session_id:            str
    total_steps:           int
    completed_steps:       int
    failed_steps:          int
    skipped_steps:         int
    total_duration_ms:     float
    avg_step_duration_ms:  float
    peak_step_duration_ms: float

    @property
    def success_rate(self) -> float:
        if self.total_steps == 0:
            return 1.0
        return self.completed_steps / self.total_steps

    @classmethod
    def build(
        cls,
        session_id:     str,
        total_steps:    int,
        completed:      int,
        failed:         int,
        skipped:        int,
        step_durations: List[float],
        total_ms:       float,
    ) -> "ExecutionMetrics":
        avg_ms  = sum(step_durations) / len(step_durations) if step_durations else 0.0
        peak_ms = max(step_durations) if step_durations else 0.0
        return cls(
            session_id            = session_id,
            total_steps           = total_steps,
            completed_steps       = completed,
            failed_steps          = failed,
            skipped_steps         = skipped,
            total_duration_ms     = total_ms,
            avg_step_duration_ms  = avg_ms,
            peak_step_duration_ms = peak_ms,
        )


class ProgressTracker:
    """Tracks step-completion progress per session."""

    def __init__(self) -> None:
        self._lock:     threading.Lock                    = threading.Lock()
        self._progress: Dict[str, Tuple[int, int]]        = {}
        # session_id → (completed, total)

    def start(self, session_id: str, total_steps: int) -> None:
        with self._lock:
            self._progress[session_id] = (0, max(total_steps, 1))

    def advance(self, session_id: str, count: int = 1) -> None:
        with self._lock:
            completed, total = self._progress.get(session_id, (0, 1))
            self._progress[session_id] = (min(completed + count, total), total)

    def get_progress(self, session_id: str) -> float:
        """Return completion ratio 0.0 – 1.0."""
        with self._lock:
            completed, total = self._progress.get(session_id, (0, 1))
            return completed / total if total > 0 else 0.0

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._progress.pop(session_id, None)

    def tracked_count(self) -> int:
        with self._lock:
            return len(self._progress)


class ExecutionMonitor:
    """
    Records execution events and computes live metrics per session.
    All operations are thread-safe.
    """

    def __init__(self) -> None:
        self._lock:           threading.Lock                         = threading.Lock()
        self._starts:         Dict[str, float]                       = {}
        self._step_starts:    Dict[str, Dict[str, float]]            = {}
        self._timelines:      Dict[str, List[TimelineEvent]]         = {}
        self._step_durations: Dict[str, List[float]]                 = {}
        self._counters:       Dict[str, Dict[str, int]]              = {}

    # ── recording ─────────────────────────────────────────────────────────────

    def record_start(self, session_id: str, total_steps: int = 0) -> None:
        with self._lock:
            self._starts[session_id]         = time.time()
            self._step_starts[session_id]    = {}
            self._timelines[session_id]      = [TimelineEvent.create("session_start")]
            self._step_durations[session_id] = []
            self._counters[session_id]       = {
                "completed": 0, "failed": 0, "skipped": 0, "total": total_steps,
            }

    def record_step_start(self, session_id: str, step_id: str) -> None:
        with self._lock:
            self._step_starts.setdefault(session_id, {})[step_id] = time.time()
            self._timelines.setdefault(session_id, []).append(
                TimelineEvent.create("step_start", step_id=step_id)
            )

    def record_step_complete(self, session_id: str, step_id: str) -> None:
        with self._lock:
            start  = self._step_starts.get(session_id, {}).get(step_id, time.time())
            dur_ms = (time.time() - start) * 1000.0
            self._step_durations.setdefault(session_id, []).append(dur_ms)
            self._timelines.setdefault(session_id, []).append(
                TimelineEvent.create("step_complete", step_id=step_id, duration_ms=dur_ms)
            )
            ctrs = self._counters.setdefault(
                session_id, {"completed": 0, "failed": 0, "skipped": 0, "total": 0}
            )
            ctrs["completed"] += 1

    def record_step_failed(self, session_id: str, step_id: str) -> None:
        with self._lock:
            start  = self._step_starts.get(session_id, {}).get(step_id, time.time())
            dur_ms = (time.time() - start) * 1000.0
            self._step_durations.setdefault(session_id, []).append(dur_ms)
            self._timelines.setdefault(session_id, []).append(
                TimelineEvent.create("step_failed", step_id=step_id, duration_ms=dur_ms)
            )
            ctrs = self._counters.setdefault(
                session_id, {"completed": 0, "failed": 0, "skipped": 0, "total": 0}
            )
            ctrs["failed"] += 1

    def record_complete(self, session_id: str) -> None:
        with self._lock:
            self._timelines.setdefault(session_id, []).append(
                TimelineEvent.create("session_complete")
            )

    # ── accessors ─────────────────────────────────────────────────────────────

    def get_timeline(self, session_id: str) -> Timeline:
        with self._lock:
            events = list(self._timelines.get(session_id, []))
        return Timeline.build(session_id, events)

    def get_metrics(self, session_id: str) -> ExecutionMetrics:
        with self._lock:
            started_at     = self._starts.get(session_id, time.time())
            step_durations = list(self._step_durations.get(session_id, []))
            ctrs           = self._counters.get(
                session_id,
                {"completed": 0, "failed": 0, "skipped": 0, "total": 0},
            )
        total_ms = (time.time() - started_at) * 1000.0
        return ExecutionMetrics.build(
            session_id     = session_id,
            total_steps    = ctrs["total"],
            completed      = ctrs["completed"],
            failed         = ctrs["failed"],
            skipped        = ctrs["skipped"],
            step_durations = step_durations,
            total_ms       = total_ms,
        )

    def session_count(self) -> int:
        with self._lock:
            return len(self._starts)
