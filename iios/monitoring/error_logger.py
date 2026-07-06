"""
iios/monitoring/error_logger.py
=================================
Error tracking with deduplication, frequency analysis, and suppression.

``ErrorLogger`` captures every exception with its full stack trace and
provides:
  - Fingerprint-based deduplication (same error → increment count)
  - Sliding-window frequency tracking (errors/minute)
  - Automatic alerting when error frequency exceeds thresholds
  - In-memory ring buffer with optional file persistence

Architecture Reference: IIOS-ARC-001 Layer 17
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
import traceback
from collections import defaultdict, deque
from typing import Any, Callable, Optional

from .monitoring_models import ErrorRecord
from .monitoring_constants import MAX_ERROR_DEDUP_WINDOW_SECONDS

__all__ = [
    "ErrorLogger",
    "get_error_logger",
]

_LOG = logging.getLogger("iios.monitoring.errors")
_instance_lock = threading.Lock()
_instance: Optional["ErrorLogger"] = None


class ErrorLogger:
    """Tracks errors with deduplication, frequency, and frequency-based alerting.

    Args:
        max_records:        Maximum error records to keep in memory.
        dedup_window_secs:  Window (seconds) in which duplicate errors are
                            merged rather than creating a new record.
        freq_window_secs:   Sliding window for frequency counting.
        freq_alert_threshold: Errors per window to trigger a frequency alert.
    """

    def __init__(
        self,
        max_records: int = 2000,
        dedup_window_secs: int = MAX_ERROR_DEDUP_WINDOW_SECONDS,
        freq_window_secs: int = 60,
        freq_alert_threshold: int = 10,
    ) -> None:
        self._lock = threading.Lock()
        self._records: deque[ErrorRecord] = deque(maxlen=max_records)
        # fingerprint → ErrorRecord (dedup index)
        self._dedup: dict[str, ErrorRecord] = {}
        # fingerprint → list of monotonic timestamps (freq window)
        self._freq: dict[str, deque] = defaultdict(lambda: deque())
        self._dedup_window = dedup_window_secs
        self._freq_window = freq_window_secs
        self._freq_threshold = freq_alert_threshold
        self._total_errors = 0
        self._alert_callbacks: list[Callable[[ErrorRecord, int], None]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture(
        self,
        exc: Optional[BaseException] = None,
        message: str = "",
        component: str = "",
        layer: str = "",
        correlation_id: str = "",
        **context: Any,
    ) -> ErrorRecord:
        """Capture an exception or error message.

        Args:
            exc:            Optional exception instance.
            message:        Error message (used if exc is None).
            component:      Source component.
            layer:          Source IIOS layer.
            correlation_id: Correlation ID for linking to request.
            **context:      Additional context fields.

        Returns:
            ``ErrorRecord`` (possibly updated dedup entry).
        """
        if exc is not None:
            error_type = type(exc).__name__
            msg = message or str(exc)
            tb = traceback.format_exc()
        else:
            error_type = "Error"
            msg = message
            tb = ""

        fingerprint = _fingerprint(error_type, msg, component)

        now_mono = time.monotonic()
        with self._lock:
            # Dedup check
            existing = self._dedup.get(fingerprint)
            if existing and _within_window(existing, now_mono, self._dedup_window):
                existing.count += 1
                existing.last_seen = _now_iso()
                record = existing
            else:
                record = ErrorRecord(
                    error_type=error_type,
                    message=msg,
                    component=component,
                    layer=layer,
                    stack_trace=tb,
                    correlation_id=correlation_id,
                    fingerprint=fingerprint,
                    context=context,
                )
                self._records.append(record)
                self._dedup[fingerprint] = record

            self._total_errors += 1
            # Frequency tracking
            self._freq[fingerprint].append(now_mono)
            # Prune old timestamps outside the window
            window_start = now_mono - self._freq_window
            freq_deque = self._freq[fingerprint]
            while freq_deque and freq_deque[0] < window_start:
                freq_deque.popleft()
            freq_count = len(freq_deque)

        # Alert callbacks if frequency threshold exceeded
        if freq_count >= self._freq_threshold:
            for cb in list(self._alert_callbacks):
                try:
                    cb(record, freq_count)
                except Exception:
                    pass

        return record

    def capture_exception(
        self,
        component: str = "",
        layer: str = "",
        correlation_id: str = "",
        **context: Any,
    ) -> Callable:
        """Decorator that captures any exception raised by the decorated callable."""
        def decorator(fn: Callable) -> Callable:
            import functools
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    self.capture(exc, component=component, layer=layer,
                                 correlation_id=correlation_id, **context)
                    raise
            return wrapper
        return decorator

    def on_frequency_alert(self, callback: Callable[[ErrorRecord, int], None]) -> None:
        """Register a callback fired when error frequency exceeds threshold."""
        with self._lock:
            self._alert_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def recent(self, n: int = 50, component: Optional[str] = None) -> list[ErrorRecord]:
        """Return up to *n* most recent error records."""
        with self._lock:
            records = list(reversed(list(self._records)))
        if component:
            records = [r for r in records if r.component == component]
        return records[:n]

    def unique_errors(self) -> list[ErrorRecord]:
        """Return one record per unique error fingerprint."""
        with self._lock:
            return list(self._dedup.values())

    def top_errors(self, n: int = 10) -> list[ErrorRecord]:
        """Return the *n* most frequent errors."""
        with self._lock:
            records = sorted(self._dedup.values(), key=lambda r: r.count, reverse=True)
        return records[:n]

    def frequency(self, fingerprint: str) -> int:
        """Return errors matching *fingerprint* in the current window."""
        with self._lock:
            dq = self._freq.get(fingerprint, deque())
            now_mono = time.monotonic()
            window_start = now_mono - self._freq_window
            return sum(1 for ts in dq if ts >= window_start)

    @property
    def total_errors(self) -> int:
        return self._total_errors

    @property
    def unique_error_count(self) -> int:
        with self._lock:
            return len(self._dedup)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._dedup.clear()
            self._freq.clear()
            self._total_errors = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fingerprint(error_type: str, message: str, component: str) -> str:
    # Normalise message (strip numbers/UUIDs for grouping)
    import re
    normalised = re.sub(r"\b[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}\b", "UUID", message)
    normalised = re.sub(r"\b\d+\b", "N", normalised)
    key = f"{error_type}:{component}:{normalised[:200]}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def _within_window(record: ErrorRecord, now_mono: float, window_secs: int) -> bool:
    """Check if the record was last seen within the dedup window."""
    try:
        from datetime import datetime, timezone
        last = datetime.fromisoformat(record.last_seen)
        age = (datetime.now(timezone.utc) - last).total_seconds()
        return age <= window_secs
    except Exception:
        return False


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def get_error_logger() -> ErrorLogger:
    """Return (or create) the global ``ErrorLogger`` singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = ErrorLogger()
        return _instance


def _reset_error_logger() -> None:
    global _instance
    with _instance_lock:
        _instance = None
