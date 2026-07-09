"""iios/investment/company/company_context.py
Thread-local context for company intelligence operations.
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class CompanyContextState:
    """Per-thread context for a company analysis session."""

    session_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    company_id:    str   = ""
    stage:         str   = ""
    current_stage: str   = ""
    source_id:     str   = ""
    started_at:    float = field(default_factory=time.time)
    diagnostics:   list  = field(default_factory=list)   # list[tuple[str, str]]
    metadata:      dict  = field(default_factory=dict)

    def add_diagnostic(self, level: str, message: str) -> None:
        self.diagnostics.append((level, message))

    def warnings(self) -> list[str]:
        return [m for lv, m in self.diagnostics if lv == "WARNING"]

    def errors(self) -> list[str]:
        return [m for lv, m in self.diagnostics if lv == "ERROR"]

    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":    self.session_id,
            "company_id":    self.company_id,
            "current_stage": self.current_stage,
            "source_id":     self.source_id,
            "started_at":    self.started_at,
            "elapsed_ms":    self.elapsed_ms(),
        }


_local: threading.local = threading.local()


def get_company_context() -> CompanyContextState:
    if not hasattr(_local, "ctx") or _local.ctx is None:
        _local.ctx = CompanyContextState()
    return _local.ctx


def reset_company_context() -> None:
    _local.ctx = None


@contextmanager
def company_session(
    request_id: str  = "",
    metadata:   dict | None = None,
    company_id: str  = "",
    source_id:  str  = "",
) -> Iterator[CompanyContextState]:
    prev = getattr(_local, "ctx", None)
    ctx  = CompanyContextState(
        request_id = request_id or str(uuid.uuid4()),
        company_id = company_id,
        source_id  = source_id,
        metadata   = metadata or {},
    )
    _local.ctx = ctx
    try:
        yield ctx
    finally:
        _local.ctx = prev


@contextmanager
def company_stage_scope(stage: str) -> Iterator[CompanyContextState]:
    ctx  = get_company_context()
    prev_stage         = ctx.stage
    prev_current_stage = ctx.current_stage
    ctx.stage          = stage
    ctx.current_stage  = stage
    try:
        yield ctx
    finally:
        ctx.stage         = prev_stage
        ctx.current_stage = prev_current_stage
