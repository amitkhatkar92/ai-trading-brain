"""
iios/events/event_constants.py
================================
Constants for the IIOS Event & Messaging Framework.
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_DELAY",
    "DEFAULT_TIMEOUT",
    "DEFAULT_QUEUE_SIZE",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_STREAM_CHUNK",
    "DEFAULT_WORKFLOW_TIMEOUT",
    "MAX_HANDLERS",
    "MAX_WORKFLOW_STEPS",
    "DLQ_RETENTION_DAYS",
    "WILDCARD",
    "BROADCAST_TOPIC",
    "SYSTEM_SOURCE",
    "CORRELATION_HEADER",
    "CAUSATION_HEADER",
]

# Retry / delivery
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_RETRY_DELAY: float = 1.0       # seconds
DEFAULT_RETRY_BACKOFF: float = 2.0     # exponential multiplier
MAX_RETRY_JITTER: float = 0.5          # random jitter fraction

# Timeouts
DEFAULT_TIMEOUT: float = 30.0
DEFAULT_QUEUE_TIMEOUT: float = 5.0
DEFAULT_WORKFLOW_TIMEOUT: float = 300.0

# Sizes
DEFAULT_QUEUE_SIZE: int = 10_000
DEFAULT_BATCH_SIZE: int = 100
DEFAULT_STREAM_CHUNK: int = 50
MAX_HANDLERS: int = 256
MAX_WORKFLOW_STEPS: int = 100

# Retention
DLQ_RETENTION_DAYS: int = 7

# Special topics / sources
WILDCARD: str = "*"
BROADCAST_TOPIC: str = "__broadcast__"
SYSTEM_SOURCE: str = "iios.system"

# Header keys
CORRELATION_HEADER: str = "x-correlation-id"
CAUSATION_HEADER: str = "x-causation-id"
