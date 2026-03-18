"""
Centralised logger factory.
Every agent uses get_logger(__name__) to get a pre-configured logger.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from config import LOG_DIR, LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes to console + a rotating file."""
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

    # Rotating file handler (10 MB × 5 backups)
    fh = RotatingFileHandler(
        os.path.join(LOG_DIR, "ai_trading_brain.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
