"""
iios/monitoring/logging_manager.py
=====================================
Central logging management — initialisation, rotation, search, and export.

``LoggingManager`` wraps the standard Python logging infrastructure and
provides IIOS-specific conveniences:
  - Structured context injection
  - Per-layer log channels
  - Level governance (override any logger's level at runtime)
  - In-memory ring buffer for searchable recent logs
  - Log export to JSON / plain text

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import io
import json
import logging
import logging.handlers
import os
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .logger_factory import LoggerFactory, IIOSLogger, get_logger, reset_factory
from .structured_logger import StructuredLogger, get_structured_logger
from .monitoring_constants import IIOS_LAYER_NAMES

__all__ = [
    "LoggingManager",
    "get_logging_manager",
]

_instance_lock = threading.Lock()
_instance: Optional["LoggingManager"] = None


# ---------------------------------------------------------------------------
# In-memory log handler
# ---------------------------------------------------------------------------


class _RingBufferHandler(logging.Handler):
    """A logging handler that stores recent records in a ring buffer."""

    def __init__(self, maxsize: int = 5000) -> None:
        super().__init__()
        self._buffer: deque[dict[str, Any]] = deque(maxlen=maxsize)
        self._lock2 = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
        # Merge extra attributes
        for key in ("component", "layer", "correlation_id", "request_id", "trace_id"):
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        with self._lock2:
            self._buffer.append(entry)

    def records(self) -> list[dict[str, Any]]:
        with self._lock2:
            return list(self._buffer)

    def clear(self) -> None:
        with self._lock2:
            self._buffer.clear()


# ---------------------------------------------------------------------------
# LoggingManager
# ---------------------------------------------------------------------------


class LoggingManager:
    """Central manager for the IIOS logging system.

    Args:
        log_dir:        Directory for rotating log files.
        log_level:      Root log level.
        json_format:    Emit JSON-structured console output.
        buffer_size:    Size of the in-memory ring buffer.
        max_bytes:      Max bytes per rotating log file.
        backup_count:   Number of backup log files.
    """

    def __init__(
        self,
        log_dir: str = "logs",
        log_level: str = "INFO",
        json_format: bool = False,
        buffer_size: int = 5000,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 7,
    ) -> None:
        self._log_dir = Path(log_dir)
        self._log_level = log_level
        self._json_format = json_format
        self._lock = threading.Lock()

        # Ring buffer handler — attached to root logger
        self._buffer_handler = _RingBufferHandler(buffer_size)
        self._buffer_handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(self._buffer_handler)

        # Underlying factory
        self._factory = LoggerFactory(
            log_dir=str(log_dir),
            log_level=log_level,
            json_format=json_format,
            max_bytes=max_bytes,
            backup_count=backup_count,
        )

        # Per-component/layer loggers cache
        self._loggers: dict[str, IIOSLogger] = {}

    # ------------------------------------------------------------------
    # Logger access
    # ------------------------------------------------------------------

    def get_logger(
        self,
        name: str,
        component: str = "",
        layer: str = "",
        **extra: Any,
    ) -> IIOSLogger:
        """Return a configured ``IIOSLogger``."""
        key = f"{name}:{component}:{layer}"
        with self._lock:
            if key not in self._loggers:
                self._loggers[key] = self._factory.get_logger(
                    name, component=component, layer=layer, **extra
                )
            return self._loggers[key]

    def get_structured(self, name: str, component: str = "", layer: str = "") -> StructuredLogger:
        """Return a ``StructuredLogger``."""
        return get_structured_logger(name, component=component, layer=layer)

    def get_layer_logger(self, layer_name: str) -> IIOSLogger:
        """Return a logger pre-configured for an IIOS layer."""
        return self.get_logger(
            f"iios.layers.{layer_name.lower()}",
            component=layer_name,
            layer=layer_name,
        )

    # ------------------------------------------------------------------
    # Level management
    # ------------------------------------------------------------------

    def set_level(self, level: str, logger_name: str = "") -> None:
        """Set the log level for *logger_name* (empty = root logger)."""
        numeric = getattr(logging, level.upper(), logging.INFO)
        target = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        target.setLevel(numeric)

    def set_component_level(self, component: str, level: str) -> None:
        """Set log level for the ``iios.<component>`` namespace."""
        self.set_level(level, f"iios.{component.lower()}")

    def get_level(self, logger_name: str = "") -> str:
        """Return the effective log level name for *logger_name*."""
        logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        return logging.getLevelName(logger.getEffectiveLevel())

    # ------------------------------------------------------------------
    # Search and query
    # ------------------------------------------------------------------

    def search(
        self,
        query: Optional[str] = None,
        level: Optional[str] = None,
        component: Optional[str] = None,
        layer: Optional[str] = None,
        logger_name: Optional[str] = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Search the in-memory log buffer.

        Args:
            query:        Substring to search in message (case-insensitive).
            level:        Filter by log level (e.g. ``"ERROR"``).
            component:    Filter by component name.
            layer:        Filter by IIOS layer name.
            logger_name:  Filter by logger name prefix.
            limit:        Maximum results to return.

        Returns:
            List of log record dicts (most recent first).
        """
        records = list(reversed(self._buffer_handler.records()))
        if query:
            q = query.lower()
            records = [r for r in records if q in r.get("message", "").lower()]
        if level:
            records = [r for r in records if r.get("level") == level.upper()]
        if component:
            records = [r for r in records if r.get("component") == component]
        if layer:
            records = [r for r in records if r.get("layer") == layer]
        if logger_name:
            records = [r for r in records if r.get("logger", "").startswith(logger_name)]
        return records[:limit]

    def recent(self, n: int = 50) -> list[dict[str, Any]]:
        """Return up to *n* most recent log entries."""
        return list(reversed(self._buffer_handler.records()))[:n]

    def errors(self, n: int = 50) -> list[dict[str, Any]]:
        """Return recent ERROR and CRITICAL records."""
        return self.search(level="ERROR", limit=n) + self.search(level="CRITICAL", limit=n)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_json(self, limit: int = 1000) -> str:
        """Export recent log records as a JSON string."""
        records = list(reversed(self._buffer_handler.records()))[:limit]
        return json.dumps(records, indent=2, default=str)

    def export_text(self, limit: int = 1000) -> str:
        """Export recent log records as plain text (one line per record)."""
        records = list(reversed(self._buffer_handler.records()))[:limit]
        lines = []
        for r in records:
            lines.append(
                f"{r.get('timestamp', '')} {r.get('level', 'INFO'):<8} "
                f"[{r.get('logger', '')}] {r.get('message', '')}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def add_file_channel(self, filename: str, level: str = "DEBUG") -> None:
        """Add an additional rotating file handler."""
        self._factory.add_file_handler(filename, level)

    def archive_logs(self, archive_dir: str = "logs/archive") -> list[str]:
        """Move rotated .log.N files to *archive_dir*."""
        archived: list[str] = []
        archive_path = Path(archive_dir)
        archive_path.mkdir(parents=True, exist_ok=True)
        for f in self._log_dir.glob("*.log.*"):
            dest = archive_path / f.name
            try:
                f.rename(dest)
                archived.append(str(dest))
            except OSError:
                pass
        return archived

    def clear_buffer(self) -> None:
        """Clear the in-memory ring buffer."""
        self._buffer_handler.clear()

    def shutdown(self) -> None:
        """Flush and close all log handlers."""
        self._factory.shutdown()

    @property
    def buffer_size(self) -> int:
        return len(self._buffer_handler.records())


def get_logging_manager(
    log_dir: str = "logs",
    log_level: str = "INFO",
    json_format: bool = False,
) -> "LoggingManager":
    """Return (or create) the global ``LoggingManager`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = LoggingManager(
                log_dir=log_dir,
                log_level=log_level,
                json_format=json_format,
            )
        return _instance


def _reset_logging_manager() -> None:
    global _instance
    with _instance_lock:
        if _instance is not None:
            _instance.shutdown()
        _instance = None
    reset_factory()
