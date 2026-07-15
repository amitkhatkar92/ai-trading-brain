"""iios/common/logging/log_rotation.py
Log rotation configuration and handler factories for the IIOS platform.

Provides:
  • ``LogRotationConfig`` — frozen config for both size-based and
    time-based rotation with optional gzip compression.
  • ``create_rotating_handler()`` — size-based RotatingFileHandler.
  • ``create_timed_rotating_handler()`` — time-based TimedRotatingFileHandler.
  • ``configure_rotation()`` — convenience function that attaches a
    rotating handler to a named logger.

Usage::

    from iios.common.logging.log_rotation import LogRotationConfig, configure_rotation

    cfg = LogRotationConfig(
        filepath     = "/var/log/iios/audit.log",
        max_bytes    = 50 * 1024 * 1024,   # 50 MB
        backup_count = 10,
        compress     = True,
    )
    configure_rotation("iios.audit", cfg)
"""
from __future__ import annotations

import gzip
import logging
import logging.handlers
import os
import shutil
import threading
from dataclasses import dataclass, field
from typing import Optional


# ── Configuration ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LogRotationConfig:
    """
    Immutable rotation policy for a single log destination.

    Attributes
    ----------
    filepath:
        Absolute path to the log file.  Parent directory is created
        automatically.
    max_bytes:
        Rotate when the file reaches this size.  Default: 50 MB.
        Ignored by ``create_timed_rotating_handler``.
    backup_count:
        Number of rotated files to retain.  Default: 10.
    encoding:
        File encoding.  Default: ``"utf-8"``.
    when:
        Time-based rotation frequency (``"midnight"``, ``"h"``, etc.).
        Used only by ``create_timed_rotating_handler``.
    interval:
        Multiplier for ``when``.  Default: 1.
    compress:
        If True, gzip-compress rotated files in a background thread.
        Default: True.
    """

    filepath:     str  = ""
    max_bytes:    int  = 50 * 1024 * 1024
    backup_count: int  = 10
    encoding:     str  = "utf-8"
    when:         str  = "midnight"
    interval:     int  = 1
    compress:     bool = True


# ── Handlers ──────────────────────────────────────────────────────────────────

def create_rotating_handler(config: LogRotationConfig) -> logging.handlers.RotatingFileHandler:
    """
    Return a ``RotatingFileHandler`` configured per *config*.

    If ``config.compress`` is True, wraps in ``_CompressingRotatingHandler``
    so rotated files are gzip-compressed in a background thread.
    """
    _ensure_parent(config.filepath)

    if config.compress:
        handler: logging.handlers.RotatingFileHandler = _CompressingRotatingHandler(
            filename    = config.filepath,
            maxBytes    = config.max_bytes,
            backupCount = config.backup_count,
            encoding    = config.encoding,
        )
    else:
        handler = logging.handlers.RotatingFileHandler(
            filename    = config.filepath,
            maxBytes    = config.max_bytes,
            backupCount = config.backup_count,
            encoding    = config.encoding,
        )

    return handler


def create_timed_rotating_handler(
    config: LogRotationConfig,
) -> logging.handlers.TimedRotatingFileHandler:
    """
    Return a ``TimedRotatingFileHandler`` configured per *config*.

    If ``config.compress`` is True, overrides ``namer`` and ``rotator``
    so rotated files are gzip-compressed.
    """
    _ensure_parent(config.filepath)

    handler = logging.handlers.TimedRotatingFileHandler(
        filename    = config.filepath,
        when        = config.when,
        interval    = config.interval,
        backupCount = config.backup_count,
        encoding    = config.encoding,
    )

    if config.compress:
        handler.namer   = _gzip_namer
        handler.rotator = _gzip_rotator_bg

    return handler


# ── Convenience function ──────────────────────────────────────────────────────

def configure_rotation(
    logger_name: str,
    config:      LogRotationConfig,
    *,
    formatter:   Optional[logging.Formatter] = None,
    level:       int = logging.DEBUG,
) -> logging.handlers.RotatingFileHandler:
    """
    Attach a size-based rotating handler to a named logger.

    Returns the handler for further customisation.
    """
    handler = create_rotating_handler(config)
    handler.setLevel(level)
    if formatter is not None:
        handler.setFormatter(formatter)
    logging.getLogger(logger_name).addHandler(handler)
    return handler


# ── Compression helpers ───────────────────────────────────────────────────────

def _gzip_namer(default_name: str) -> str:
    """Return the rotated file name with a ``.gz`` suffix appended."""
    return default_name + ".gz"


def _gzip_rotator_bg(source: str, dest: str) -> None:
    """
    Compress *source* to *dest* (gzip) in the calling thread, then delete
    *source*.

    Runs inline; callers that need true background compression should use
    ``_CompressingRotatingHandler`` which offloads to a daemon thread.
    """
    _compress(source, dest)


def _compress(source: str, dest: str) -> None:
    """gzip *source* → *dest*, then delete *source*."""
    try:
        with open(source, "rb") as f_in, gzip.open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(source)
    except (OSError, IOError):
        pass   # best-effort; don't crash the logging subsystem


# ── Compressing rotating handler ──────────────────────────────────────────────

class _CompressingRotatingHandler(logging.handlers.RotatingFileHandler):
    """
    ``RotatingFileHandler`` that gzip-compresses each rotated file in a
    background daemon thread to keep the logging path latency minimal.
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.namer   = _gzip_namer
        self.rotator = self._async_rotator

    def _async_rotator(self, source: str, dest: str) -> None:
        t = threading.Thread(target=_compress, args=(source, dest), daemon=True)
        t.start()


# ── Utilities ─────────────────────────────────────────────────────────────────

def _ensure_parent(filepath: str) -> None:
    """Create parent directories of *filepath* if they don't exist."""
    parent = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(parent, exist_ok=True)
