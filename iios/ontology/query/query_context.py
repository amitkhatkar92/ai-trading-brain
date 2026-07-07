"""
iios/ontology/query/query_context.py
=====================================
Thread-local context for all in-flight query and resolution operations.

Provides:
* per-thread operation tracking (query_type, target, depth)
* structured diagnostic accumulation
* context-manager API for nested operations
* Singleton pair: get_query_context() / reset_query_context()
"""

from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator, Optional

from .query_constants import QueryType, ResolutionStrategy, SYSTEM_QUERY_ACTOR

__all__ = [
    "QueryDiagnosticLevel",
    "QueryDiagnostic",
    "QueryContext",
    "get_query_context",
    "reset_query_context",
]


# ── Diagnostic level ──────────────────────────────────────────────────────────

class QueryDiagnosticLevel:
    INFO    = "INFO"
    WARNING = "WARNING"
    ERROR   = "ERROR"


# ── Diagnostic entry ─────────────────────────────────────────────────────────

@dataclass
class QueryDiagnostic:
    level:      str
    message:    str
    source:     str
    timestamp:  float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "level":     self.level,
            "message":   self.message,
            "source":    self.source,
            "timestamp": self.timestamp,
        }


# ── Thread-local state ────────────────────────────────────────────────────────

class _ThreadLocalState(threading.local):
    def __init__(self) -> None:
        super().__init__()
        self._operation_id:   Optional[str]              = None
        self._actor:          str                        = SYSTEM_QUERY_ACTOR
        self._query_type:     Optional[QueryType]        = None
        self._strategy:       Optional[ResolutionStrategy] = None
        self._target:         Optional[str]              = None
        self._started_at:     float                      = 0.0
        self._depth:          int                        = 0
        self._diagnostics:    list[QueryDiagnostic]      = []


_tls = _ThreadLocalState()


# ── Context class ─────────────────────────────────────────────────────────────

class QueryContext:
    """
    Thread-local execution context for all query and resolution operations.

    Usage::

        ctx = get_query_context()
        with ctx.query_operation(QueryType.ANCESTORS, "iios.entity.Instrument"):
            with ctx.resolution("iios.entity.Instrument", ResolutionStrategy.AUTO):
                ...
    """

    # ── Property accessors ────────────────────────────────────────────────────

    @property
    def operation_id(self) -> Optional[str]:
        return _tls._operation_id

    @property
    def actor(self) -> str:
        return _tls._actor

    @property
    def query_type(self) -> Optional[QueryType]:
        return _tls._query_type

    @property
    def strategy(self) -> Optional[ResolutionStrategy]:
        return _tls._strategy

    @property
    def target(self) -> Optional[str]:
        return _tls._target

    @property
    def started_at(self) -> float:
        return _tls._started_at

    @property
    def depth(self) -> int:
        return _tls._depth

    @property
    def diagnostics(self) -> list[QueryDiagnostic]:
        return list(_tls._diagnostics)

    def elapsed_ms(self) -> float:
        if _tls._started_at == 0.0:
            return 0.0
        return (time.time() - _tls._started_at) * 1_000.0

    # ── Context managers ──────────────────────────────────────────────────────

    @contextmanager
    def query_operation(
        self,
        query_type:   QueryType,
        target:       str,
        actor:        str = SYSTEM_QUERY_ACTOR,
        operation_id: Optional[str] = None,
    ) -> Generator[None, None, None]:
        """Top-level context for a complete query operation."""
        prev_op   = _tls._operation_id
        prev_type = _tls._query_type
        prev_tgt  = _tls._target
        prev_act  = _tls._actor
        prev_ts   = _tls._started_at
        prev_diag = _tls._diagnostics

        _tls._operation_id = operation_id or str(uuid.uuid4())
        _tls._query_type   = query_type
        _tls._target       = target
        _tls._actor        = actor
        _tls._started_at   = time.time()
        _tls._diagnostics  = []
        try:
            yield
        finally:
            _tls._operation_id = prev_op
            _tls._query_type   = prev_type
            _tls._target       = prev_tgt
            _tls._actor        = prev_act
            _tls._started_at   = prev_ts
            _tls._diagnostics  = prev_diag

    @contextmanager
    def resolution(
        self,
        ref:      str,
        strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
    ) -> Generator[None, None, None]:
        """Nested context for a resolution step inside a query operation."""
        prev_tgt      = _tls._target
        prev_strategy = _tls._strategy
        prev_depth    = _tls._depth

        _tls._target   = ref
        _tls._strategy = strategy
        _tls._depth    = _tls._depth + 1
        try:
            yield
        finally:
            _tls._target   = prev_tgt
            _tls._strategy = prev_strategy
            _tls._depth    = prev_depth

    @contextmanager
    def navigation(
        self,
        start_uri: str,
    ) -> Generator[None, None, None]:
        """Nested context for a traversal step."""
        prev_tgt   = _tls._target
        prev_depth = _tls._depth

        _tls._target = start_uri
        _tls._depth  = _tls._depth + 1
        try:
            yield
        finally:
            _tls._target = prev_tgt
            _tls._depth  = prev_depth

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def add_diagnostic(
        self,
        level:   str,
        message: str,
        source:  str = "",
    ) -> None:
        _tls._diagnostics.append(
            QueryDiagnostic(level=level, message=message, source=source)
        )

    def warnings(self) -> list[QueryDiagnostic]:
        return [
            d for d in _tls._diagnostics
            if d.level == QueryDiagnosticLevel.WARNING
        ]

    def errors(self) -> list[QueryDiagnostic]:
        return [
            d for d in _tls._diagnostics
            if d.level == QueryDiagnosticLevel.ERROR
        ]


# ── Singleton ─────────────────────────────────────────────────────────────────

_ctx_lock = threading.Lock()
_ctx_instance: Optional[QueryContext] = None


def get_query_context() -> QueryContext:
    global _ctx_instance
    if _ctx_instance is None:
        with _ctx_lock:
            if _ctx_instance is None:
                _ctx_instance = QueryContext()
    return _ctx_instance


def reset_query_context() -> None:
    global _ctx_instance
    with _ctx_lock:
        _ctx_instance = None
    # Also clear TLS
    _tls._operation_id  = None
    _tls._actor         = SYSTEM_QUERY_ACTOR
    _tls._query_type    = None
    _tls._strategy      = None
    _tls._target        = None
    _tls._started_at    = 0.0
    _tls._depth         = 0
    _tls._diagnostics   = []
