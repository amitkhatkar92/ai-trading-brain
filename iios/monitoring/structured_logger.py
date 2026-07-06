"""
iios/monitoring/structured_logger.py
======================================
Structured contextual logger with correlation-ID propagation.

``StructuredLogger`` wraps an ``IIOSLogger`` and injects a
``MonitoringContext`` into every log record, enabling end-to-end
correlation across all IIOS layers.

Thread-local context storage means callers do not need to pass the
context object explicitly — set it once per request/cycle and all log
calls within that thread automatically inherit it.

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import json
import threading
import traceback
from contextlib import contextmanager
from typing import Any, Generator, Optional

from .logger_factory import IIOSLogger, get_logger
from .monitoring_models import LogRecord, MonitoringContext

__all__ = [
    "StructuredLogger",
    "get_structured_logger",
    "set_context",
    "get_context",
    "clear_context",
    "correlation_context",
]

# Thread-local storage for the active MonitoringContext
_thread_local = threading.local()


def set_context(ctx: MonitoringContext) -> None:
    """Set the active ``MonitoringContext`` for the current thread."""
    _thread_local.ctx = ctx


def get_context() -> Optional[MonitoringContext]:
    """Return the active ``MonitoringContext`` for the current thread."""
    return getattr(_thread_local, "ctx", None)


def clear_context() -> None:
    """Clear the monitoring context for the current thread."""
    if hasattr(_thread_local, "ctx"):
        del _thread_local.ctx


@contextmanager
def correlation_context(
    correlation_id: str = "",
    component: str = "",
    layer: str = "",
    **kwargs: Any,
) -> Generator[MonitoringContext, None, None]:
    """Context manager that installs a ``MonitoringContext`` for the block.

    Usage::

        with correlation_context(correlation_id="req-123", layer="RiskGuardian") as ctx:
            log.info("processing")
        # Context is restored after the block
    """
    import uuid
    prev = get_context()
    ctx = MonitoringContext(
        correlation_id=correlation_id or str(uuid.uuid4()),
        component=component,
        layer=layer,
        **kwargs,
    )
    set_context(ctx)
    try:
        yield ctx
    finally:
        if prev is not None:
            set_context(prev)
        else:
            clear_context()


# ---------------------------------------------------------------------------
# StructuredLogger
# ---------------------------------------------------------------------------


class StructuredLogger:
    """A structured, context-aware logger for IIOS subsystems.

    Args:
        name:       Python logger name (dotted module path).
        component:  IIOS component identifier.
        layer:      IIOS layer name.
        emit_json:  If ``True``, format log payloads as JSON strings rather
                    than human-readable text (useful in non-JSON-handler envs).
    """

    def __init__(
        self,
        name: str,
        component: str = "",
        layer: str = "",
        emit_json: bool = False,
    ) -> None:
        self._name = name
        self._component = component
        self._layer = layer
        self._emit_json = emit_json
        self._logger: IIOSLogger = get_logger(
            name, component=component, layer=layer
        )

    # ------------------------------------------------------------------
    # Log methods
    # ------------------------------------------------------------------

    def debug(self, message: str, **extra: Any) -> None:
        self._log("DEBUG", message, extra)

    def info(self, message: str, **extra: Any) -> None:
        self._log("INFO", message, extra)

    def warning(self, message: str, **extra: Any) -> None:
        self._log("WARNING", message, extra)

    def error(self, message: str, exc: Optional[BaseException] = None, **extra: Any) -> None:
        if exc is not None:
            extra["exc_type"] = type(exc).__name__
            extra["exc_str"] = str(exc)
            extra["stack_trace"] = traceback.format_exc()
        self._log("ERROR", message, extra)

    def critical(self, message: str, exc: Optional[BaseException] = None, **extra: Any) -> None:
        if exc is not None:
            extra["exc_type"] = type(exc).__name__
            extra["exc_str"] = str(exc)
            extra["stack_trace"] = traceback.format_exc()
        self._log("CRITICAL", message, extra)

    def exception(self, message: str, **extra: Any) -> None:
        """Log at ERROR level with current exception info."""
        extra["stack_trace"] = traceback.format_exc()
        self._log("ERROR", message, extra, exc_info=True)

    # ------------------------------------------------------------------
    # Record builder
    # ------------------------------------------------------------------

    def build_record(self, level: str, message: str, extra: dict[str, Any]) -> LogRecord:
        """Build a structured ``LogRecord`` with all context fields."""
        import os
        ctx = get_context()
        record = LogRecord(
            level=level,
            message=message,
            logger_name=self._name,
            component=self._component,
            layer=self._layer,
            thread_id=threading.current_thread().ident or 0,
            thread_name=threading.current_thread().name,
            process_id=os.getpid(),
        )
        if ctx:
            record.correlation_id = ctx.correlation_id
            record.request_id = ctx.request_id
            record.session_id = ctx.session_id
            record.execution_id = ctx.execution_id
            record.trace_id = ctx.trace_id
            record.span_id = ctx.span_id
            if ctx.component and not record.component:
                record.component = ctx.component
            if ctx.layer and not record.layer:
                record.layer = ctx.layer
        record.extra = extra
        return record

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log(self, level: str, message: str, extra: dict[str, Any], exc_info: bool = False) -> None:
        import logging

        ctx = get_context()
        log_extra: dict[str, Any] = {
            "component": self._component,
            "layer": self._layer,
        }
        if ctx:
            log_extra.update({
                "correlation_id": ctx.correlation_id,
                "request_id": ctx.request_id,
                "session_id": ctx.session_id,
                "trace_id": ctx.trace_id,
                "span_id": ctx.span_id,
            })
        log_extra.update(extra)

        if self._emit_json:
            payload = {"msg": message, **log_extra}
            message = json.dumps(payload, default=str)

        self._logger.log(
            getattr(logging, level, logging.INFO),
            message,
            extra=log_extra,
            exc_info=exc_info,
        )

    # ------------------------------------------------------------------
    # Context binding
    # ------------------------------------------------------------------

    def bind(self, **kwargs: Any) -> "StructuredLogger":
        """Return a new ``StructuredLogger`` with additional static context."""
        new = StructuredLogger(
            self._name,
            component=kwargs.pop("component", self._component),
            layer=kwargs.pop("layer", self._layer),
            emit_json=self._emit_json,
        )
        new._logger = self._logger.bind(**kwargs)
        return new


# ---------------------------------------------------------------------------
# Module-level factory helper
# ---------------------------------------------------------------------------

_loggers: dict[str, StructuredLogger] = {}
_loggers_lock = threading.Lock()


def _reset_structured_loggers() -> None:
    """Clear the singleton logger cache. For testing only."""
    with _loggers_lock:
        _loggers.clear()


def get_structured_logger(
    name: str,
    component: str = "",
    layer: str = "",
    emit_json: bool = False,
) -> StructuredLogger:
    """Return (or create) a ``StructuredLogger`` for *name*."""
    key = f"{name}:{component}:{layer}"
    with _loggers_lock:
        if key not in _loggers:
            _loggers[key] = StructuredLogger(
                name, component=component, layer=layer, emit_json=emit_json
            )
        return _loggers[key]
