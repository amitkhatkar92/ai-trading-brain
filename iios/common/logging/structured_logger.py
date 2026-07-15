"""iios/common/logging/structured_logger.py
Structured JSON logger for the IIOS platform.

Every log entry automatically includes:
  • Timestamp (ISO-8601 UTC)
  • Logger name / engine / component / module
  • Thread ID
  • Severity
  • Message
  • Workflow ID, Correlation ID, Request ID, Trace ID, Session ID
  • Portfolio ID, Decision ID, Market ID, Company ID, Strategy ID
  • Elapsed time (if provided)
  • Exception info
  • Arbitrary context key–value pairs

Usage::

    from iios.common.logging.structured_logger import StructuredLogger

    log = StructuredLogger.get("my.module", engine_id="iios:my:engine")
    log.info("Engine started", elapsed_ms=12.3)
    log.error("Unexpected failure", exc=exc, context={"portfolio_id": "P-001"})

    # Use with bound context
    from iios.common.logging.logging_context import LoggingContext
    with LoggingContext(workflow_id="WF-001", request_id="REQ-abc").bind():
        log.info("Processing")  # workflow_id and request_id auto-injected
"""
from __future__ import annotations

import json
import logging
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, MutableMapping, Optional, Tuple

from iios.common.logging.logging_context import LoggingContext


# ── JSON formatter ────────────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.

    Output format::

        {"ts":"2026-01-01T00:00:00.123456+00:00","level":"INFO",
         "logger":"iios.market.integration","msg":"Engine started",
         "engine_id":"iios:market:intelligence:integration",
         "thread_id":139872321,...}
    """

    def format(self, record: logging.LogRecord) -> str:
        ctx = LoggingContext.to_dict()

        entry: Dict[str, Any] = {
            "ts":       self._utc_iso(record.created),
            "level":    record.levelname,
            "logger":   record.name,
            "module":   record.module,
            "func":     record.funcName,
            "line":     record.lineno,
            "thread_id": record.thread,
            "msg":       record.getMessage(),
        }

        # Context IDs from LoggingContext
        for key, val in ctx.items():
            entry[key] = val

        # Per-record extra fields injected by StructuredLogger
        for attr in (
            "engine_id", "component", "elapsed_ms",
            "workflow_id", "correlation_id", "request_id",
            "trace_id", "session_id",
        ):
            val = getattr(record, attr, None)
            if val is not None and attr not in entry:
                entry[attr] = val

        # Arbitrary context dict
        ctx_dict = getattr(record, "ctx_dict", None)
        if ctx_dict:
            entry["context"] = ctx_dict

        # Exception
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        elif record.exc_text:
            entry["exc"] = record.exc_text

        return json.dumps(entry, default=str)

    @staticmethod
    def _utc_iso(epoch: float) -> str:
        return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


class TextFormatter(logging.Formatter):
    """
    Human-readable formatter that includes context IDs.

    Pattern: ``%(asctime)s %(levelname)-8s [%(workflow_id)s] %(name)s: %(message)s``
    """

    _FMT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
    _DATEFMT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self._FMT, datefmt=self._DATEFMT)

    def format(self, record: logging.LogRecord) -> str:
        # Inject context into record for use by %(workflow_id)s etc.
        ctx = LoggingContext.to_dict()
        for k, v in ctx.items():
            if not hasattr(record, k):
                setattr(record, k, v)
        return super().format(record)


# ── StructuredLogger ──────────────────────────────────────────────────────────

class StructuredLogger:
    """
    Thin wrapper around ``logging.Logger`` that:

    1. Automatically injects all ``LoggingContext`` fields into each record.
    2. Accepts an optional ``context`` dict for extra structured data.
    3. Accepts ``elapsed_ms`` for timing information.
    4. Accepts ``exc`` (an exception instance) in addition to the standard
       ``exc_info`` mechanism.

    All standard logger methods are forwarded to the underlying
    ``logging.Logger``, making ``StructuredLogger`` a drop-in replacement.
    """

    def __init__(
        self,
        name:       str,
        *,
        engine_id:  str = "",
        component:  str = "",
    ) -> None:
        self._name:      str = name
        self._engine_id: str = engine_id
        self._component: str = component
        self._logger:    logging.Logger = logging.getLogger(name)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def get(
        cls,
        name:      str,
        *,
        engine_id: str = "",
        component: str = "",
    ) -> "StructuredLogger":
        """Shortcut factory matching ``logging.getLogger()`` semantics."""
        return cls(name, engine_id=engine_id, component=component)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def engine_id(self) -> str:
        return self._engine_id

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    # ── Level checks ─────────────────────────────────────────────────────────

    def isEnabledFor(self, level: int) -> bool:
        return self._logger.isEnabledFor(level)

    # ── Core log methods ──────────────────────────────────────────────────────

    def debug(
        self,
        msg:        str,
        *,
        elapsed_ms: Optional[float]        = None,
        exc:        Optional[BaseException] = None,
        context:    Optional[Dict[str, Any]] = None,
        **kw: Any,
    ) -> None:
        if self._logger.isEnabledFor(logging.DEBUG):
            self._emit(logging.DEBUG, msg, elapsed_ms, exc, context, **kw)

    def info(
        self,
        msg:        str,
        *,
        elapsed_ms: Optional[float]        = None,
        exc:        Optional[BaseException] = None,
        context:    Optional[Dict[str, Any]] = None,
        **kw: Any,
    ) -> None:
        if self._logger.isEnabledFor(logging.INFO):
            self._emit(logging.INFO, msg, elapsed_ms, exc, context, **kw)

    def warning(
        self,
        msg:        str,
        *,
        elapsed_ms: Optional[float]        = None,
        exc:        Optional[BaseException] = None,
        context:    Optional[Dict[str, Any]] = None,
        **kw: Any,
    ) -> None:
        if self._logger.isEnabledFor(logging.WARNING):
            self._emit(logging.WARNING, msg, elapsed_ms, exc, context, **kw)

    # Alias
    warn = warning

    def error(
        self,
        msg:        str,
        *,
        elapsed_ms: Optional[float]        = None,
        exc:        Optional[BaseException] = None,
        context:    Optional[Dict[str, Any]] = None,
        **kw: Any,
    ) -> None:
        if self._logger.isEnabledFor(logging.ERROR):
            self._emit(logging.ERROR, msg, elapsed_ms, exc, context, **kw)

    def critical(
        self,
        msg:        str,
        *,
        elapsed_ms: Optional[float]        = None,
        exc:        Optional[BaseException] = None,
        context:    Optional[Dict[str, Any]] = None,
        **kw: Any,
    ) -> None:
        if self._logger.isEnabledFor(logging.CRITICAL):
            self._emit(logging.CRITICAL, msg, elapsed_ms, exc, context, **kw)

    def exception(
        self,
        msg:     str,
        *,
        exc:     Optional[BaseException] = None,
        context: Optional[Dict[str, Any]] = None,
        **kw: Any,
    ) -> None:
        """Log at ERROR with current exception info."""
        exc_info: Any = exc if exc is not None else True
        self._emit(logging.ERROR, msg, None, exc if exc else None, context,
                   exc_info=exc_info, **kw)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _emit(
        self,
        level:      int,
        msg:        str,
        elapsed_ms: Optional[float],
        exc:        Optional[BaseException],
        context:    Optional[Dict[str, Any]],
        *,
        exc_info:   Any = None,
        **kw: Any,
    ) -> None:
        extra: Dict[str, Any] = {}
        if self._engine_id:
            extra["engine_id"] = self._engine_id
        if self._component:
            extra["component"] = self._component
        if elapsed_ms is not None:
            extra["elapsed_ms"] = round(elapsed_ms, 3)
        if context:
            extra["ctx_dict"] = context

        # Build exc_info tuple if an exception instance was passed
        if exc is not None and exc_info is None:
            exc_info = (type(exc), exc, exc.__traceback__)

        self._logger.log(
            level, msg,
            exc_info = exc_info,
            extra    = extra,
            stacklevel = 3,
        )

    # ── Structured entry (explicit) ───────────────────────────────────────────

    def structured(
        self,
        level:      int,
        msg:        str,
        *,
        elapsed_ms: Optional[float]        = None,
        exc:        Optional[BaseException] = None,
        context:    Optional[Dict[str, Any]] = None,
        **kw: Any,
    ) -> None:
        """
        Emit a structured log entry at an explicit numeric level.

        Example::

            log.structured(logging.INFO, "Snapshot published",
                           context={"snapshot_id": snap.snapshot_id})
        """
        if self._logger.isEnabledFor(level):
            self._emit(level, msg, elapsed_ms, exc, context, **kw)

    # ── Level management ─────────────────────────────────────────────────────

    def set_level(self, level: int) -> None:
        self._logger.setLevel(level)

    @property
    def level(self) -> int:
        return self._logger.level

    def __repr__(self) -> str:
        return f"StructuredLogger({self._name!r}, engine_id={self._engine_id!r})"
