"""
Centralised logger factory.
Every agent uses get_logger(__name__) to get a pre-configured logger.

FILE DESCRIPTOR SAFETY
----------------------
With ~62 agents each calling get_logger(__name__), naive per-logger
FileHandler creation produces 62 × 2 = 124 open FDs pointing at the same
two log files.  At scale this exhausts the process FD budget (errno 24),
causing silent write failures and data corruption.

Fix: both FileHandlers live ONLY on the root logger, created exactly once
via _setup_root_file_handlers().  Child loggers add only a StreamHandler
(one FD = stdout, shared) and propagate records upward to the root's
file handlers.  Total file FDs = 2 regardless of how many agents exist.
"""

import logging
import os
import threading
from datetime import datetime as _dt
from logging.handlers import RotatingFileHandler
from config import LOG_DIR, LOG_LEVEL

# Daily log directory — logs/YYYY-MM-DD.log at project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DAILY_LOG_DIR = os.path.join(_PROJECT_ROOT, "logs")

_root_file_setup_done = False
_root_file_setup_lock = threading.Lock()


class _DailyFileHandler(logging.FileHandler):
    """File handler that writes to ``logs/YYYY-MM-DD.log``.

    Automatically reopens a new file when the calendar date changes so a
    continuous daemon process still gets one log file per day.
    """

    def __init__(self, log_dir: str, formatter: logging.Formatter) -> None:
        self._log_dir = log_dir
        self._today = ""
        super().__init__(self._current_path(), mode="a", encoding="utf-8", delay=False)
        self.setFormatter(formatter)

    def _current_path(self) -> str:
        self._today = _dt.now().strftime("%Y-%m-%d")
        return os.path.join(self._log_dir, f"{self._today}.log")

    def emit(self, record: logging.LogRecord) -> None:
        today = _dt.now().strftime("%Y-%m-%d")
        if today != self._today:
            self.close()
            self.baseFilename = os.path.abspath(
                os.path.join(self._log_dir, f"{today}.log")
            )
            self._today = today
            self.stream = self._open()
        super().emit(record)


def _setup_root_file_handlers(fmt: logging.Formatter) -> None:
    """Attach BOTH file handlers to the root logger exactly once.

    Called by every get_logger() invocation; the lock + flag ensure the
    handlers are only ever added once, keeping total open file FDs at 2
    (one rotating + one daily) for the entire process lifetime.
    """
    global _root_file_setup_done
    with _root_file_setup_lock:
        if _root_file_setup_done:
            return

        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(_DAILY_LOG_DIR, exist_ok=True)

        root = logging.getLogger()

        # Rotating file handler (10 MB × 5 backups)
        fh = RotatingFileHandler(
            os.path.join(LOG_DIR, "ai_trading_brain.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)

        # Daily file handler — logs/YYYY-MM-DD.log
        root.addHandler(_DailyFileHandler(_DAILY_LOG_DIR, fmt))

        # Root level must be ≤ child level so propagated records reach handlers
        if root.level == logging.NOTSET:
            root.setLevel(logging.DEBUG)

        _root_file_setup_done = True


def get_logger(name: str) -> logging.Logger:
    """Return a per-module logger.

    File output is handled by handlers on the ROOT logger (added once).
    Each child logger adds only a StreamHandler for console output, then
    propagates records upward.  This keeps total open file FDs at exactly
    2 no matter how many agents/modules call get_logger().
    """
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Ensure both file handlers exist on the root logger (idempotent)
    _setup_root_file_handlers(fmt)

    logger = logging.getLogger(name)
    if logger.handlers:          # Avoid duplicate StreamHandler on re-import
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # Console handler only — file I/O handled by root via propagation
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Propagate to root so the root's FileHandlers write the record.
    # Root has no StreamHandler, so there is no double-printing.
    logger.propagate = True

    return logger
