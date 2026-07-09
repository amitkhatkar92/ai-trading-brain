"""iios/execution/planning/planning_context.py"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class PlanningContextState:
    session_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id:       str   = ""
    order_id:      str   = ""
    stage:         str   = ""
    current_stage: str   = ""
    source_id:     str   = ""
    started_at:    float = field(default_factory=time.time)
    diagnostics:   list  = field(default_factory=list)
    metadata:      dict  = field(default_factory=dict)

    def add_diagnostic(self, level: str, message: str) -> None:
        self.diagnostics.append((level, message))

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":    self.session_id,
            "request_id":    self.request_id,
            "plan_id":       self.plan_id,
            "order_id":      self.order_id,
            "stage":         self.stage,
            "current_stage": self.current_stage,
            "elapsed_ms":    self.elapsed_ms(),
        }


_local: threading.local = threading.local()


def get_planning_context() -> PlanningContextState:
    if not hasattr(_local, "ctx") or _local.ctx is None:
        _local.ctx = PlanningContextState()
    return _local.ctx


def reset_planning_context() -> None:
    _local.ctx = None


@contextmanager
def planning_session(
    request_id: str       = "",
    metadata:   dict | None = None,
    order_id:   str       = "",
) -> Iterator[PlanningContextState]:
    prev = getattr(_local, "ctx", None)
    ctx  = PlanningContextState(
        request_id = request_id or str(uuid.uuid4()),
        order_id   = order_id,
        metadata   = metadata or {},
    )
    _local.ctx = ctx
    try:
        yield ctx
    finally:
        _local.ctx = prev


@contextmanager
def planning_stage_scope(stage: str) -> Iterator[PlanningContextState]:
    ctx               = get_planning_context()
    prev_stage        = ctx.stage
    prev_curr         = ctx.current_stage
    ctx.stage         = stage
    ctx.current_stage = stage
    try:
        yield ctx
    finally:
        ctx.stage         = prev_stage
        ctx.current_stage = prev_curr
