"""
iios/intelligence/governance/quality_context.py
================================================
Thread-local execution context for the Governance Engine.
Note: context-manager helpers use ``_scope`` suffix to avoid shadowing
module names in __init__ imports.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from .quality_constants import IntelligenceType


@dataclass
class GovernanceDiagnostic:
    level:   str
    message: str
    source:  str
    ts:      float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level":   self.level,
            "message": self.message,
            "source":  self.source,
            "ts":      self.ts,
        }


class GovernanceContextState:
    """Mutable per-thread context for an active governance evaluation."""

    def __init__(self) -> None:
        self.product_id:      str | None               = None
        self.product_type:    IntelligenceType | None  = None
        self.record_id:       str | None               = None
        self.source_id:       str | None               = None
        self.depth:           int                      = 0
        self.started_at:      float                    = time.time()
        self._diagnostics:    list[GovernanceDiagnostic] = []

    def add_diagnostic(
        self,
        level:   str,
        message: str,
        source:  str,
    ) -> None:
        self._diagnostics.append(
            GovernanceDiagnostic(level=level, message=message, source=source)
        )

    def warnings(self) -> list[GovernanceDiagnostic]:
        return [d for d in self._diagnostics if d.level == "WARNING"]

    def errors(self) -> list[GovernanceDiagnostic]:
        return [d for d in self._diagnostics if d.level == "ERROR"]

    @property
    def elapsed_s(self) -> float:
        return time.time() - self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id":   self.product_id,
            "product_type": self.product_type.value if self.product_type else None,
            "record_id":    self.record_id,
            "source_id":    self.source_id,
            "depth":        self.depth,
            "elapsed_s":    round(self.elapsed_s, 4),
            "diagnostics":  [d.to_dict() for d in self._diagnostics],
        }


# ── Thread-local storage ─────────────────────────────────────────────────────

_CTX_LOCAL: threading.local             = threading.local()
_LOCK:      threading.Lock              = threading.Lock()
_INSTANCE:  _GovernanceContextManager | None = None


class _GovernanceContextManager:
    @staticmethod
    def _current() -> GovernanceContextState:
        if not hasattr(_CTX_LOCAL, "state"):
            _CTX_LOCAL.state = GovernanceContextState()
        return _CTX_LOCAL.state

    def get(self) -> GovernanceContextState:
        return self._current()

    @contextmanager
    def evaluation(
        self,
        product_id:   str,
        product_type: IntelligenceType | None = None,
        source_id:    str | None              = None,
    ) -> Generator[GovernanceContextState, None, None]:
        ctx   = self._current()
        saved = (ctx.product_id, ctx.product_type, ctx.source_id, ctx.depth)
        ctx.product_id   = product_id
        ctx.product_type = product_type
        ctx.source_id    = source_id
        ctx.depth        = saved[3] + 1
        ctx.started_at   = time.time()
        try:
            yield ctx
        finally:
            (ctx.product_id, ctx.product_type,
             ctx.source_id, ctx.depth) = saved

    @contextmanager
    def certification(
        self,
        record_id: str,
    ) -> Generator[GovernanceContextState, None, None]:
        ctx  = self._current()
        prev = ctx.record_id
        ctx.record_id = record_id
        try:
            yield ctx
        finally:
            ctx.record_id = prev


def _get_manager() -> _GovernanceContextManager:
    global _INSTANCE
    if _INSTANCE is None:
        with _LOCK:
            if _INSTANCE is None:
                _INSTANCE = _GovernanceContextManager()
    return _INSTANCE


def get_governance_context() -> GovernanceContextState:
    return _get_manager().get()


def reset_governance_context() -> None:
    global _INSTANCE
    with _LOCK:
        _INSTANCE = None
    if hasattr(_CTX_LOCAL, "state"):
        del _CTX_LOCAL.state


# ── Module-level convenience helpers (using _scope to avoid shadowing) ────────

@contextmanager
def evaluation_scope(
    product_id:   str,
    product_type: IntelligenceType | None = None,
    source_id:    str | None              = None,
) -> Generator[GovernanceContextState, None, None]:
    with _get_manager().evaluation(product_id, product_type, source_id) as ctx:
        yield ctx


@contextmanager
def certification_scope(
    record_id: str,
) -> Generator[GovernanceContextState, None, None]:
    with _get_manager().certification(record_id) as ctx:
        yield ctx
