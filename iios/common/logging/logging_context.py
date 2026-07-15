"""iios/common/logging/logging_context.py
Thread-safe, async-safe logging context using Python contextvars.

Provides automatic propagation of observability identifiers
(trace_id, workflow_id, correlation_id, request_id, etc.) across
synchronous call stacks and asyncio coroutines.

Usage::

    from iios.common.logging.logging_context import LoggingContext

    # Bind context for the current call stack
    ctx = LoggingContext(
        workflow_id    = "WF-001",
        correlation_id = "CORR-abc123",
        request_id     = "REQ-xyz789",
    )
    with ctx.bind():
        # All logging calls within this block automatically include these IDs
        logger.info("Processing started")

    # Or use the class-level helpers directly
    LoggingContext.set_workflow_id("WF-002")
    wid = LoggingContext.get_workflow_id()   # "WF-002"
    LoggingContext.clear()                   # reset all
"""
from __future__ import annotations

from contextvars import ContextVar, Token
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Generator, Iterator, Optional
import threading
import uuid


# ── Per-field context variables ───────────────────────────────────────────────
# Each field is an independent ContextVar so they can be set/cleared independently.

_CTX_WORKFLOW_ID:    ContextVar[str] = ContextVar("iios_workflow_id",    default="")
_CTX_TRACE_ID:       ContextVar[str] = ContextVar("iios_trace_id",       default="")
_CTX_CORRELATION_ID: ContextVar[str] = ContextVar("iios_correlation_id", default="")
_CTX_REQUEST_ID:     ContextVar[str] = ContextVar("iios_request_id",     default="")
_CTX_SESSION_ID:     ContextVar[str] = ContextVar("iios_session_id",     default="")
_CTX_PORTFOLIO_ID:   ContextVar[str] = ContextVar("iios_portfolio_id",   default="")
_CTX_DECISION_ID:    ContextVar[str] = ContextVar("iios_decision_id",    default="")
_CTX_MARKET_ID:      ContextVar[str] = ContextVar("iios_market_id",      default="")
_CTX_COMPANY_ID:     ContextVar[str] = ContextVar("iios_company_id",     default="")
_CTX_STRATEGY_ID:    ContextVar[str] = ContextVar("iios_strategy_id",    default="")
_CTX_ENGINE_ID:      ContextVar[str] = ContextVar("iios_engine_id",      default="")

# Ordered list of all (name, ContextVar) pairs
_ALL_VARS: list = [
    ("workflow_id",    _CTX_WORKFLOW_ID),
    ("trace_id",       _CTX_TRACE_ID),
    ("correlation_id", _CTX_CORRELATION_ID),
    ("request_id",     _CTX_REQUEST_ID),
    ("session_id",     _CTX_SESSION_ID),
    ("portfolio_id",   _CTX_PORTFOLIO_ID),
    ("decision_id",    _CTX_DECISION_ID),
    ("market_id",      _CTX_MARKET_ID),
    ("company_id",     _CTX_COMPANY_ID),
    ("strategy_id",    _CTX_STRATEGY_ID),
    ("engine_id",      _CTX_ENGINE_ID),
]


@dataclass
class LoggingContext:
    """
    Container for all logging context identifiers.

    Supports ``with ctx.bind()`` as a context manager that sets/restores
    all field ContextVars atomically.
    """

    workflow_id:    str = ""
    trace_id:       str = ""
    correlation_id: str = ""
    request_id:     str = ""
    session_id:     str = ""
    portfolio_id:   str = ""
    decision_id:    str = ""
    market_id:      str = ""
    company_id:     str = ""
    strategy_id:    str = ""
    engine_id:      str = ""

    @contextmanager
    def bind(self) -> Generator[None, None, None]:
        """
        Bind this context to the current call stack for the duration of
        the ``with`` block, then restore the previous values.
        """
        tokens: list[tuple[ContextVar[str], Token[str]]] = []
        try:
            if self.workflow_id:
                tokens.append((_CTX_WORKFLOW_ID,    _CTX_WORKFLOW_ID.set(self.workflow_id)))
            if self.trace_id:
                tokens.append((_CTX_TRACE_ID,       _CTX_TRACE_ID.set(self.trace_id)))
            if self.correlation_id:
                tokens.append((_CTX_CORRELATION_ID, _CTX_CORRELATION_ID.set(self.correlation_id)))
            if self.request_id:
                tokens.append((_CTX_REQUEST_ID,     _CTX_REQUEST_ID.set(self.request_id)))
            if self.session_id:
                tokens.append((_CTX_SESSION_ID,     _CTX_SESSION_ID.set(self.session_id)))
            if self.portfolio_id:
                tokens.append((_CTX_PORTFOLIO_ID,   _CTX_PORTFOLIO_ID.set(self.portfolio_id)))
            if self.decision_id:
                tokens.append((_CTX_DECISION_ID,    _CTX_DECISION_ID.set(self.decision_id)))
            if self.market_id:
                tokens.append((_CTX_MARKET_ID,      _CTX_MARKET_ID.set(self.market_id)))
            if self.company_id:
                tokens.append((_CTX_COMPANY_ID,     _CTX_COMPANY_ID.set(self.company_id)))
            if self.strategy_id:
                tokens.append((_CTX_STRATEGY_ID,    _CTX_STRATEGY_ID.set(self.strategy_id)))
            if self.engine_id:
                tokens.append((_CTX_ENGINE_ID,      _CTX_ENGINE_ID.set(self.engine_id)))
            yield
        finally:
            for var, token in reversed(tokens):
                var.reset(token)

    # ── Class-level read helpers ───────────────────────────────────────────────

    @classmethod
    def current(cls) -> "LoggingContext":
        """Return a snapshot of the current context as a LoggingContext instance."""
        return cls(
            workflow_id    = _CTX_WORKFLOW_ID.get(),
            trace_id       = _CTX_TRACE_ID.get(),
            correlation_id = _CTX_CORRELATION_ID.get(),
            request_id     = _CTX_REQUEST_ID.get(),
            session_id     = _CTX_SESSION_ID.get(),
            portfolio_id   = _CTX_PORTFOLIO_ID.get(),
            decision_id    = _CTX_DECISION_ID.get(),
            market_id      = _CTX_MARKET_ID.get(),
            company_id     = _CTX_COMPANY_ID.get(),
            strategy_id    = _CTX_STRATEGY_ID.get(),
            engine_id      = _CTX_ENGINE_ID.get(),
        )

    @classmethod
    def to_dict(cls) -> Dict[str, str]:
        """Return current context as a dict (omitting empty strings)."""
        return {
            name: var.get()
            for name, var in _ALL_VARS
            if var.get()
        }

    @classmethod
    def clear(cls) -> None:
        """Clear all context variables by resetting to empty string."""
        for _, var in _ALL_VARS:
            var.set("")

    # ── Class-level write helpers ─────────────────────────────────────────────

    @classmethod
    def set_workflow_id(cls, value: str) -> Token[str]:
        return _CTX_WORKFLOW_ID.set(value)

    @classmethod
    def set_trace_id(cls, value: str) -> Token[str]:
        return _CTX_TRACE_ID.set(value)

    @classmethod
    def set_correlation_id(cls, value: str) -> Token[str]:
        return _CTX_CORRELATION_ID.set(value)

    @classmethod
    def set_request_id(cls, value: str) -> Token[str]:
        return _CTX_REQUEST_ID.set(value)

    @classmethod
    def set_session_id(cls, value: str) -> Token[str]:
        return _CTX_SESSION_ID.set(value)

    @classmethod
    def set_portfolio_id(cls, value: str) -> Token[str]:
        return _CTX_PORTFOLIO_ID.set(value)

    @classmethod
    def set_decision_id(cls, value: str) -> Token[str]:
        return _CTX_DECISION_ID.set(value)

    @classmethod
    def set_market_id(cls, value: str) -> Token[str]:
        return _CTX_MARKET_ID.set(value)

    @classmethod
    def set_company_id(cls, value: str) -> Token[str]:
        return _CTX_COMPANY_ID.set(value)

    @classmethod
    def set_strategy_id(cls, value: str) -> Token[str]:
        return _CTX_STRATEGY_ID.set(value)

    @classmethod
    def set_engine_id(cls, value: str) -> Token[str]:
        return _CTX_ENGINE_ID.set(value)

    # ── Class-level read helpers ─────────────────────────────────────────────

    @classmethod
    def get_workflow_id(cls)    -> str: return _CTX_WORKFLOW_ID.get()

    @classmethod
    def get_trace_id(cls)       -> str: return _CTX_TRACE_ID.get()

    @classmethod
    def get_correlation_id(cls) -> str: return _CTX_CORRELATION_ID.get()

    @classmethod
    def get_request_id(cls)     -> str: return _CTX_REQUEST_ID.get()

    @classmethod
    def get_session_id(cls)     -> str: return _CTX_SESSION_ID.get()

    @classmethod
    def get_portfolio_id(cls)   -> str: return _CTX_PORTFOLIO_ID.get()

    @classmethod
    def get_decision_id(cls)    -> str: return _CTX_DECISION_ID.get()

    @classmethod
    def get_market_id(cls)      -> str: return _CTX_MARKET_ID.get()

    @classmethod
    def get_company_id(cls)     -> str: return _CTX_COMPANY_ID.get()

    @classmethod
    def get_strategy_id(cls)    -> str: return _CTX_STRATEGY_ID.get()

    @classmethod
    def get_engine_id(cls)      -> str: return _CTX_ENGINE_ID.get()

    # ── Convenience factory ───────────────────────────────────────────────────

    @classmethod
    def new_trace(
        cls,
        *,
        workflow_id:    str = "",
        correlation_id: str = "",
        request_id:     str = "",
        session_id:     str = "",
    ) -> "LoggingContext":
        """Create a context with a fresh trace_id and optional overrides."""
        return cls(
            trace_id       = str(uuid.uuid4()),
            workflow_id    = workflow_id,
            correlation_id = correlation_id or str(uuid.uuid4()),
            request_id     = request_id,
            session_id     = session_id,
        )
