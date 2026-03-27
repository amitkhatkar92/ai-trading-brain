"""
Centralised logger factory.
Every agent uses get_logger(__name__) to get a pre-configured logger.
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

_daily_setup_done = False
_daily_setup_lock = threading.Lock()


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


def _setup_daily_log(fmt: logging.Formatter) -> None:
    """Attach a date-keyed file handler to the root logger exactly once."""
    global _daily_setup_done
    with _daily_setup_lock:
        if _daily_setup_done:
            return
        os.makedirs(_DAILY_LOG_DIR, exist_ok=True)
        root = logging.getLogger()
        root.addHandler(_DailyFileHandler(_DAILY_LOG_DIR, fmt))
        # Root level must be ≤ child level so propagated records reach the handler
        if root.level == logging.NOTSET:
            root.setLevel(logging.DEBUG)
        _daily_setup_done = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes to console + a rotating file + a daily file."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:          # Avoid duplicate handlers on re-import
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Rotating file handler (10 MB × 5 backups) — backward-compatible location
    fh = RotatingFileHandler(
        os.path.join(LOG_DIR, "ai_trading_brain.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Daily file handler — logs/YYYY-MM-DD.log (shared via root logger, setup once)
    _setup_daily_log(fmt)

    return logger
