"""iios/common/errors/error_context.py
Error context propagation for the IIOS platform.

Uses Python contextvars so context automatically propagates across
synchronous call stacks and asyncio coroutines without explicit passing.

Usage::

    from iios.common.errors.error_context import ErrorContext, bind_error_context

    ctx = ErrorContext(
        engine_id      = "iios:market:intelligence:integration",
        stage          = "data_fetch",
        workflow_id    = "WF-001",
        correlation_id = "CORR-abc123",
        operation      = "get_multiple_quotes",
    )
    with bind_error_context(ctx):
        # All code in this block sees this context via get_error_context()
        run_operation()

    # In error handlers:
    ctx = get_error_context()
    if ctx:
        log.error("Failure", context=ctx.to_dict())
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Generator, List, Optional, Any


# ── Module-level ContextVar ───────────────────────────────────────────────────

_CONTEXT_VAR: ContextVar[Optional["ErrorContext"]] = ContextVar(
    "iios_error_context", default=None
)


# ── ErrorContext ──────────────────────────────────────────────────────────────

@dataclass
class ErrorContext:
    """
    Captures the full context at the time an error occurs.

    Fields are intentionally mutable so callers can enrich the context
    as the call stack unwinds.  Use ``to_dict()`` to create a frozen snapshot.
    """

    engine_id:       str                     = ""
    stage:           str                     = ""
    workflow_id:     str                     = ""
    correlation_id:  str                     = ""
    request_id:      str                     = ""
    operation:       str                     = ""
    component:       str                     = ""
    timestamp:       datetime                = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    # Ordered list of (exc_type_name, exc_message) pairs collected while
    # unwinding a nested exception chain.
    exception_chain: List[Dict[str, str]]    = field(default_factory=list)
    # Arbitrary extra metadata that does not fit the standard fields.
    extra:           Dict[str, Any]          = field(default_factory=dict)

    def add_to_chain(self, exc: BaseException) -> None:
        """
        Append an exception to the chain, preserving order of occurrence.

        Duplicates (same type + message) are silently ignored.
        """
        entry = {
            "type":    type(exc).__name__,
            "message": str(exc),
        }
        if entry not in self.exception_chain:
            self.exception_chain.append(entry)

    def enrich(self, **kwargs: Any) -> "ErrorContext":
        """
        Update fields in-place from keyword arguments.

        Unknown fields are stored in ``extra``.
        Returns self for chaining.
        """
        known = {f.name for f in self.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        for k, v in kwargs.items():
            if k in known:
                setattr(self, k, v)
            else:
                self.extra[k] = v
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable snapshot of this context."""
        d: Dict[str, Any] = {
            "engine_id":       self.engine_id,
            "stage":           self.stage,
            "workflow_id":     self.workflow_id,
            "correlation_id":  self.correlation_id,
            "request_id":      self.request_id,
            "operation":       self.operation,
            "component":       self.component,
            "timestamp":       self.timestamp.isoformat(),
            "exception_chain": self.exception_chain,
        }
        if self.extra:
            d["extra"] = self.extra
        # Omit empty string fields to keep output clean
        return {k: v for k, v in d.items() if v}

    def copy(self) -> "ErrorContext":
        """Return a shallow copy of this context."""
        return ErrorContext(
            engine_id       = self.engine_id,
            stage           = self.stage,
            workflow_id     = self.workflow_id,
            correlation_id  = self.correlation_id,
            request_id      = self.request_id,
            operation       = self.operation,
            component       = self.component,
            timestamp       = self.timestamp,
            exception_chain = list(self.exception_chain),
            extra           = dict(self.extra),
        )


# ── Context-var API ───────────────────────────────────────────────────────────

def get_error_context() -> Optional[ErrorContext]:
    """Return the current error context, or None if none is set."""
    return _CONTEXT_VAR.get()


def set_error_context(ctx: Optional[ErrorContext]) -> Token[Optional[ErrorContext]]:
    """
    Set the current error context and return the reset token.

    The caller is responsible for calling ``_CONTEXT_VAR.reset(token)``
    to restore the previous value.  Prefer the ``bind_error_context()``
    context manager instead.
    """
    return _CONTEXT_VAR.set(ctx)


def clear_error_context() -> None:
    """Clear the current error context (sets to None)."""
    _CONTEXT_VAR.set(None)


@contextmanager
def bind_error_context(ctx: ErrorContext) -> Generator[ErrorContext, None, None]:
    """
    Bind *ctx* as the current error context for the duration of the block,
    then restore the previous value.

    Exceptions are re-raised after restoring context; the exception is
    automatically added to the chain before re-raising so the context
    snapshot captures it.

    Usage::

        with bind_error_context(ctx) as bound:
            do_work()
    """
    token = _CONTEXT_VAR.set(ctx)
    try:
        yield ctx
    except BaseException as exc:
        ctx.add_to_chain(exc)
        raise
    finally:
        _CONTEXT_VAR.reset(token)


def current_context_dict() -> Dict[str, Any]:
    """
    Return the current error context as a dict, or an empty dict.

    Convenience function for passing context to log calls.
    """
    ctx = get_error_context()
    return ctx.to_dict() if ctx is not None else {}
