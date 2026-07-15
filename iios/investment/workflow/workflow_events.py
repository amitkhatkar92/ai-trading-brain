"""iios/investment/workflow/workflow_events.py
WorkflowEvent — immutable event payload.
WorkflowEventPublisher — dispatches pipeline events to registered callbacks.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from iios.investment.workflow.workflow_types import PipelineEventType, WorkflowStage

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkflowEvent:
    """
    Immutable event emitted at key pipeline lifecycle points.
    Consumers receive a reference to this object via callback.
    """

    event_type:  PipelineEventType
    workflow_id: str
    request_id:  str
    stage:       Optional[WorkflowStage]   # None for workflow-level events
    emitted_at:  str                       # ISO-8601 UTC
    payload:     Dict[str, Any]            = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type":  self.event_type.value,
            "workflow_id": self.workflow_id,
            "request_id":  self.request_id,
            "stage":       self.stage.value if self.stage else None,
            "emitted_at":  self.emitted_at,
            "payload":     self.payload,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowEventPublisher:
    """
    Dispatches WorkflowEvents to registered callback functions.

    Thread-safe.  Callbacks receive the event synchronously in the calling thread.
    Callback exceptions are caught and logged — they never propagate to the pipeline.
    """

    def __init__(self) -> None:
        self._lock:      threading.RLock            = threading.RLock()
        self._callbacks: List[Callable[[WorkflowEvent], None]] = []

    def register(self, callback: Callable[[WorkflowEvent], None]) -> None:
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def unregister(self, callback: Callable[[WorkflowEvent], None]) -> None:
        with self._lock:
            try:
                self._callbacks.remove(callback)
            except ValueError:
                pass

    def publish(self, event: WorkflowEvent) -> None:
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(event)
            except Exception as exc:
                _log.error(
                    "WorkflowEventPublisher: callback %s raised %s for event %s",
                    cb,
                    exc,
                    event.event_type.value,
                )

    # ── Factory helpers ───────────────────────────────────────────────────────

    def emit_workflow_started(
        self, workflow_id: str, request_id: str, portfolio_id: str
    ) -> None:
        self.publish(WorkflowEvent(
            event_type  = PipelineEventType.WORKFLOW_STARTED,
            workflow_id = workflow_id,
            request_id  = request_id,
            stage       = None,
            emitted_at  = _now_iso(),
            payload     = {"portfolio_id": portfolio_id},
        ))

    def emit_stage_started(
        self, workflow_id: str, request_id: str, stage: WorkflowStage,
        attempt: int = 1,
    ) -> None:
        self.publish(WorkflowEvent(
            event_type  = PipelineEventType.STAGE_STARTED,
            workflow_id = workflow_id,
            request_id  = request_id,
            stage       = stage,
            emitted_at  = _now_iso(),
            payload     = {"attempt": attempt},
        ))

    def emit_stage_completed(
        self, workflow_id: str, request_id: str, stage: WorkflowStage,
        duration_ms: float, snapshot_id: Optional[str] = None,
    ) -> None:
        self.publish(WorkflowEvent(
            event_type  = PipelineEventType.STAGE_COMPLETED,
            workflow_id = workflow_id,
            request_id  = request_id,
            stage       = stage,
            emitted_at  = _now_iso(),
            payload     = {
                "duration_ms": round(duration_ms, 2),
                "snapshot_id": snapshot_id,
            },
        ))

    def emit_stage_retrying(
        self, workflow_id: str, request_id: str, stage: WorkflowStage,
        attempt: int, error: str,
    ) -> None:
        self.publish(WorkflowEvent(
            event_type  = PipelineEventType.STAGE_RETRYING,
            workflow_id = workflow_id,
            request_id  = request_id,
            stage       = stage,
            emitted_at  = _now_iso(),
            payload     = {"attempt": attempt, "error": error},
        ))

    def emit_stage_failed(
        self, workflow_id: str, request_id: str, stage: WorkflowStage,
        error: str,
    ) -> None:
        self.publish(WorkflowEvent(
            event_type  = PipelineEventType.STAGE_FAILED,
            workflow_id = workflow_id,
            request_id  = request_id,
            stage       = stage,
            emitted_at  = _now_iso(),
            payload     = {"error": error},
        ))

    def emit_workflow_completed(
        self, workflow_id: str, request_id: str, portfolio_id: str,
        duration_ms: float, snapshot_id: Optional[str],
    ) -> None:
        self.publish(WorkflowEvent(
            event_type  = PipelineEventType.WORKFLOW_COMPLETED,
            workflow_id = workflow_id,
            request_id  = request_id,
            stage       = None,
            emitted_at  = _now_iso(),
            payload     = {
                "portfolio_id": portfolio_id,
                "duration_ms":  round(duration_ms, 2),
                "snapshot_id":  snapshot_id,
            },
        ))

    def emit_workflow_failed(
        self, workflow_id: str, request_id: str, stage: Optional[WorkflowStage],
        error: str,
    ) -> None:
        self.publish(WorkflowEvent(
            event_type  = PipelineEventType.WORKFLOW_FAILED,
            workflow_id = workflow_id,
            request_id  = request_id,
            stage       = stage,
            emitted_at  = _now_iso(),
            payload     = {"error": error},
        ))

    def emit_workflow_cancelled(
        self, workflow_id: str, request_id: str,
    ) -> None:
        self.publish(WorkflowEvent(
            event_type  = PipelineEventType.WORKFLOW_CANCELLED,
            workflow_id = workflow_id,
            request_id  = request_id,
            stage       = None,
            emitted_at  = _now_iso(),
            payload     = {},
        ))

    def emit_snapshot_published(
        self, workflow_id: str, request_id: str,
        portfolio_id: str, snapshot_id: Optional[str],
    ) -> None:
        self.publish(WorkflowEvent(
            event_type  = PipelineEventType.PORTFOLIO_SNAPSHOT_PUBLISHED,
            workflow_id = workflow_id,
            request_id  = request_id,
            stage       = WorkflowStage.PORTFOLIO,
            emitted_at  = _now_iso(),
            payload     = {
                "portfolio_id": portfolio_id,
                "snapshot_id":  snapshot_id,
            },
        ))
