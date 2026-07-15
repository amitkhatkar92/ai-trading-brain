"""iios/common/logging/logging_manager.py
Central logging manager for the IIOS platform.

Responsibilities:
  • Initialize logging infrastructure (handlers, formatters, levels)
  • Maintain a registry of StructuredLogger instances
  • Support runtime log-level changes per logger or package
  • Configure rolling file handlers, console handlers, JSON output

Usage::

    from iios.common.logging.logging_manager import LoggingManager, LoggingConfig

    # One-time initialization at startup
    cfg = LoggingConfig(
        level        = "INFO",
        json_console = True,
        log_file     = "/var/log/iios/iios.log",
        max_bytes    = 50 * 1024 * 1024,
        backup_count = 10,
    )
    LoggingManager.configure(cfg)

    # Get a logger anywhere in the codebase
    log = LoggingManager.get_logger("iios.market.integration",
                                    engine_id="iios:market:intelligence:integration")
    log.info("Market engine ready")

    # Runtime level override
    LoggingManager.set_level("iios.market", "DEBUG")
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from iios.common.logging.structured_logger import JsonFormatter, StructuredLogger, TextFormatter


# ── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class LoggingConfig:
    """
    Immutable configuration for the LoggingManager.

    All attributes have sensible defaults so only non-default values need
    to be specified at call sites.
    """

    # Root log level
    level: str = "INFO"

    # Console output
    console:      bool = True
    json_console: bool = False   # True = JSON, False = human-readable text

    # File output
    log_file:    Optional[str] = None
    json_file:   bool          = True    # always JSON for file output
    max_bytes:   int           = 50 * 1024 * 1024   # 50 MB
    backup_count: int          = 10
    compress:    bool          = True    # gzip rotated files

    # Per-package level overrides: {"iios.market": "DEBUG", ...}
    level_overrides: Dict[str, str] = field(default_factory=dict)

    # Disable IIOS package loggers by default
    silence_third_party: bool = True

    def root_level_int(self) -> int:
        return _level_int(self.level)


def _level_int(level: str) -> int:
    """Convert a level name string to its integer value."""
    lvl = getattr(logging, level.upper(), None)
    if not isinstance(lvl, int):
        raise ValueError(f"Unknown log level: {level!r}")
    return lvl


# ── LoggingManager ────────────────────────────────────────────────────────────

class LoggingManager:
    """
    Thread-safe singleton-style central logging manager.

    All public methods are class methods; no instantiation is needed.
    """

    _lock:      threading.Lock           = threading.Lock()
    _registry:  Dict[str, StructuredLogger] = {}
    _config:    Optional[LoggingConfig]  = None
    _initialized: bool                   = False
    _handlers:  List[logging.Handler]    = []

    # ── Configuration ─────────────────────────────────────────────────────────

    @classmethod
    def configure(cls, config: LoggingConfig) -> None:
        """
        Initialize logging infrastructure with the provided configuration.

        Safe to call multiple times (reconfigures on each call).
        Should be called once at application startup.
        """
        with cls._lock:
            cls._config = config
            root = logging.getLogger()

            # Remove previously added handlers
            for h in cls._handlers:
                root.removeHandler(h)
            cls._handlers.clear()

            root.setLevel(config.root_level_int())

            # ── Console handler ────────────────────────────────────────────
            if config.console:
                ch = logging.StreamHandler()
                ch.setLevel(config.root_level_int())
                ch.setFormatter(
                    JsonFormatter() if config.json_console else TextFormatter()
                )
                root.addHandler(ch)
                cls._handlers.append(ch)

            # ── File handler ───────────────────────────────────────────────
            if config.log_file:
                os.makedirs(os.path.dirname(config.log_file) or ".", exist_ok=True)
                fh = logging.handlers.RotatingFileHandler(
                    filename    = config.log_file,
                    maxBytes    = config.max_bytes,
                    backupCount = config.backup_count,
                    encoding    = "utf-8",
                )
                fh.setLevel(config.root_level_int())
                fh.setFormatter(
                    JsonFormatter() if config.json_file else TextFormatter()
                )
                if config.compress:
                    fh.namer  = cls._gzip_namer
                    fh.rotator = cls._gzip_rotator
                root.addHandler(fh)
                cls._handlers.append(fh)

            # ── Per-package overrides ─────────────────────────────────────
            for pkg, lvl in config.level_overrides.items():
                logging.getLogger(pkg).setLevel(_level_int(lvl))

            # ── Silence noisy third-party loggers ─────────────────────────
            if config.silence_third_party:
                for name in ("urllib3", "requests", "asyncio", "websockets", "httpx"):
                    logging.getLogger(name).setLevel(logging.WARNING)

            cls._initialized = True

    @classmethod
    def default_config(cls) -> None:
        """Apply a minimal default configuration (console, INFO, text format)."""
        cls.configure(LoggingConfig())

    # ── Logger registry ───────────────────────────────────────────────────────

    @classmethod
    def get_logger(
        cls,
        name:       str,
        *,
        engine_id:  str = "",
        component:  str = "",
    ) -> StructuredLogger:
        """
        Return the StructuredLogger for the given name.

        Creates a new instance on first call; returns the cached instance
        on subsequent calls (same semantics as ``logging.getLogger``).
        """
        key = f"{name}:{engine_id}"
        with cls._lock:
            if key not in cls._registry:
                cls._registry[key] = StructuredLogger(
                    name,
                    engine_id = engine_id,
                    component = component,
                )
            return cls._registry[key]

    @classmethod
    def registered_loggers(cls) -> Dict[str, StructuredLogger]:
        """Return a copy of the current logger registry."""
        with cls._lock:
            return dict(cls._registry)

    # ── Runtime level management ──────────────────────────────────────────────

    @classmethod
    def set_level(cls, name: str, level: str) -> None:
        """
        Change the log level for a named logger (or package) at runtime.

        Example::

            LoggingManager.set_level("iios.market", "DEBUG")
        """
        logging.getLogger(name).setLevel(_level_int(level))

    @classmethod
    def get_level(cls, name: str) -> str:
        """Return the effective log level name for a named logger."""
        lvl = logging.getLogger(name).getEffectiveLevel()
        return logging.getLevelName(lvl)

    @classmethod
    def set_all_levels(cls, level: str) -> None:
        """Set the log level for the root logger and all registered loggers."""
        lvl_int = _level_int(level)
        logging.getLogger().setLevel(lvl_int)
        with cls._lock:
            for sl in cls._registry.values():
                sl.logger.setLevel(lvl_int)

    # ── Handler management ────────────────────────────────────────────────────

    @classmethod
    def add_handler(cls, handler: logging.Handler) -> None:
        """Add a custom handler to the root logger."""
        with cls._lock:
            logging.getLogger().addHandler(handler)
            cls._handlers.append(handler)

    @classmethod
    def remove_handler(cls, handler: logging.Handler) -> None:
        """Remove a handler from the root logger."""
        with cls._lock:
            logging.getLogger().removeHandler(handler)
            try:
                cls._handlers.remove(handler)
            except ValueError:
                pass

    @classmethod
    def handlers(cls) -> List[logging.Handler]:
        """Return a copy of the managed handler list."""
        with cls._lock:
            return list(cls._handlers)

    # ── Teardown ──────────────────────────────────────────────────────────────

    @classmethod
    def shutdown(cls) -> None:
        """
        Flush and close all managed handlers.

        Call at application shutdown to ensure all buffered log records
        are written.
        """
        with cls._lock:
            for h in cls._handlers:
                try:
                    h.flush()
                    h.close()
                except Exception:
                    pass
            cls._handlers.clear()
            cls._registry.clear()
            cls._initialized = False

    # ── Rotation helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _gzip_namer(default_name: str) -> str:
        """Append .gz to rotated log file names."""
        return default_name + ".gz"

    @staticmethod
    def _gzip_rotator(source: str, dest: str) -> None:
        """Compress a rotated log file with gzip."""
        import gzip
        import shutil
        with open(source, "rb") as f_in, gzip.open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(source)


# ── Module-level convenience function ─────────────────────────────────────────

def get_logger(
    name:       str,
    *,
    engine_id:  str = "",
    component:  str = "",
) -> StructuredLogger:
    """
    Module-level shortcut for ``LoggingManager.get_logger()``.

    Intended for use in module-level logger declarations::

        from iios.common.logging.logging_manager import get_logger
        _log = get_logger(__name__, engine_id="iios:market:integration")
    """
    return LoggingManager.get_logger(name, engine_id=engine_id, component=component)
