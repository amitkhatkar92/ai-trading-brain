"""
iios/monitoring/logger_factory.py
===================================
Factory for creating consistently configured Python loggers.

Every IIOS subsystem should obtain loggers through this factory to ensure:
  - Consistent format across all modules
  - Centralised handler management
  - Correlation-ID propagation via ``logging.LoggerAdapter``
  - Log-level governance

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import threading
from pathlib import Path
from typing import Any, Optional

__all__ = [
    "LoggerFactory",
    "IIOSLogger",
    "get_logger",
]

_FACTORY_LOCK = threading.RLock()  # RLock allows re-entry from same thread
_FACTORY: Optional["LoggerFactory"] = None

# Sentinel to track whether root IIOS logging has been initialised
_BOOTSTRAP_DONE = False

# ---------------------------------------------------------------------------
# IIOSLogger — LoggerAdapter with automatic context injection
# ---------------------------------------------------------------------------


class IIOSLogger(logging.LoggerAdapter):
    """A ``LoggerAdapter`` that merges per-instance context into every record.

    Usage::

        log = get_logger("iios.risk", component="RiskGuardian", layer="RiskGuardian")
        log.info("VIX kill-switch triggered", extra={"vix": 46.2})

    All ``extra`` keyword arguments end up in the log record and — if a JSON
    formatter is in use — in the structured output.
    """

    def __init__(
        self,
        logger: logging.Logger,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(logger, context or {})

    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        """Merge adapter context with per-call extra."""
        extra = dict(self.extra)
        call_extra = kwargs.pop("extra", {})
        extra.update(call_extra)
        # Inject thread info
        extra.setdefault("thread_id", threading.current_thread().ident)
        extra.setdefault("thread_name", threading.current_thread().name)
        extra.setdefault("process_id", os.getpid())
        kwargs["extra"] = extra
        return msg, kwargs

    def bind(self, **kwargs: Any) -> "IIOSLogger":
        """Return a new adapter with additional context merged in."""
        new_ctx = dict(self.extra)
        new_ctx.update(kwargs)
        return IIOSLogger(self.logger, new_ctx)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class LoggerFactory:
    """Creates and manages ``IIOSLogger`` instances.

    A single factory instance is usually enough for the entire process.
    Use ``get_logger()`` module-level helper for convenience.

    Args:
        log_dir:     Directory for rotating log files. ``None`` → file logging
                     disabled.
        log_level:   Root log level (default ``INFO``).
        json_format: If ``True``, use JSON-structured output on the console.
        max_bytes:   Max size of each log file before rotation.
        backup_count: Number of rotated files to keep.
    """

    _FORMAT_PLAIN = (
        "%(asctime)s %(levelname)-8s "
        "[%(name)-42s] "
        "%(message)s"
    )
    _DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(
        self,
        log_dir: Optional[str] = None,
        log_level: str = "INFO",
        json_format: bool = False,
        max_bytes: int = 10 * 1024 * 1024,   # 10 MB
        backup_count: int = 7,
        console: bool = True,
    ) -> None:
        self._log_dir = Path(log_dir) if log_dir else None
        self._log_level = getattr(logging, log_level.upper(), logging.INFO)
        self._json_format = json_format
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._console = console
        self._lock = threading.Lock()
        self._configured_loggers: set[str] = set()
        self._handlers: list[logging.Handler] = []

        self._configure_root()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_logger(
        self,
        name: str,
        component: str = "",
        layer: str = "",
        **extra: Any,
    ) -> IIOSLogger:
        """Return an ``IIOSLogger`` for *name*.

        Args:
            name:      Logger name (use dotted module path, e.g. ``"iios.risk"``).
            component: IIOS component name for context tagging.
            layer:     IIOS layer name for context tagging.
            **extra:   Additional context fields.

        Returns:
            ``IIOSLogger`` with the given context bound.
        """
        logger = logging.getLogger(name)
        ctx: dict[str, Any] = {"logger_name": name}
        if component:
            ctx["component"] = component
        if layer:
            ctx["layer"] = layer
        ctx.update(extra)
        return IIOSLogger(logger, ctx)

    def set_level(self, level: str, logger_name: str = "") -> None:
        """Set log level for the named logger (or root if name is empty)."""
        numeric = getattr(logging, level.upper(), logging.INFO)
        target = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        target.setLevel(numeric)

    def add_file_handler(self, filename: str, level: str = "DEBUG") -> None:
        """Add a rotating file handler for *filename*."""
        path = self._log_dir / filename if self._log_dir else Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            str(path),
            maxBytes=self._max_bytes,
            backupCount=self._backup_count,
            encoding="utf-8",
        )
        handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        handler.setFormatter(self._make_formatter())
        logging.getLogger().addHandler(handler)
        self._handlers.append(handler)

    def shutdown(self) -> None:
        """Flush and close all managed handlers."""
        for handler in self._handlers:
            try:
                handler.flush()
                handler.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _configure_root(self) -> None:
        """Configure the root Python logger once."""
        global _BOOTSTRAP_DONE
        with _FACTORY_LOCK:
            if _BOOTSTRAP_DONE:
                return
            root = logging.getLogger()
            root.setLevel(self._log_level)

            if self._console:
                ch = logging.StreamHandler(sys.stdout)
                ch.setLevel(self._log_level)
                ch.setFormatter(self._make_formatter())
                root.addHandler(ch)
                self._handlers.append(ch)

            if self._log_dir:
                self._log_dir.mkdir(parents=True, exist_ok=True)
                fh = logging.handlers.RotatingFileHandler(
                    str(self._log_dir / "iios.log"),
                    maxBytes=self._max_bytes,
                    backupCount=self._backup_count,
                    encoding="utf-8",
                )
                fh.setLevel(logging.DEBUG)
                fh.setFormatter(self._make_formatter())
                root.addHandler(fh)
                self._handlers.append(fh)

            _BOOTSTRAP_DONE = True

    def _make_formatter(self) -> logging.Formatter:
        if self._json_format:
            return _JSONFormatter()
        return logging.Formatter(self._FORMAT_PLAIN, datefmt=self._DATE_FORMAT)


# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------


class _JSONFormatter(logging.Formatter):
    """Emits log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread_id": record.thread,
            "thread_name": record.threadName,
            "process_id": record.process,
        }
        # Merge any extra fields set on the record
        for key, val in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "message", "module", "msecs", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName",
            ):
                payload[key] = val

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def get_logger(
    name: str,
    component: str = "",
    layer: str = "",
    **extra: Any,
) -> IIOSLogger:
    """Return an ``IIOSLogger``. Uses (or creates) the global factory."""
    global _FACTORY
    with _FACTORY_LOCK:
        if _FACTORY is None:
            _FACTORY = LoggerFactory()
    return _FACTORY.get_logger(name, component=component, layer=layer, **extra)


def reset_factory() -> None:
    """Reset the global factory — for tests only."""
    global _FACTORY, _BOOTSTRAP_DONE
    with _FACTORY_LOCK:
        if _FACTORY is not None:
            _FACTORY.shutdown()
        _FACTORY = None
        _BOOTSTRAP_DONE = False
