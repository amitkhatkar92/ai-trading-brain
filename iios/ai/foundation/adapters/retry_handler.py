"""
retry_handler.py — iios.ai.foundation.adapters
===============================================
:class:`RetryHandler` — exponential back-off retry logic for AI provider
calls.  Centralises retry policy so individual provider adapters remain
simple.

A1 AI Foundation — Phase 3, Module 4
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple, Type

from .constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF_BASE_S,
    DEFAULT_RETRY_BACKOFF_MAX_S,
    SCHEMA_VERSION,
)


# ---------------------------------------------------------------------------
# Retry snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetrySnapshot:
    """Outcome record for one :meth:`RetryHandler.execute` call."""
    attempt:      int
    succeeded:    bool
    total_delay_s: float
    last_error:   Optional[str]
    schema:       str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt":       self.attempt,
            "succeeded":     self.succeeded,
            "total_delay_s": round(self.total_delay_s, 3),
            "last_error":    self.last_error,
        }


# ---------------------------------------------------------------------------
# Retry handler
# ---------------------------------------------------------------------------

class RetryHandler:
    """
    Configurable exponential back-off retry handler.

    Performs up to ``max_retries`` retries with jitter-free exponential
    back-off.  Retries are triggered by any exception in
    ``retriable_exceptions``; all other exceptions propagate immediately.

    Parameters
    ----------
    max_retries :        Maximum number of retry attempts (0 = no retries).
    backoff_base_s :     Base delay in seconds before first retry.
    backoff_max_s :      Maximum delay cap in seconds.
    retriable_exceptions : Exception types that trigger a retry.  If ``None``,
                          all ``Exception`` subclasses are retried.

    Usage::

        handler = RetryHandler(max_retries=3)
        result, snap = handler.execute(lambda: provider.complete(req))
        if not snap.succeeded:
            log.error(f"all retries exhausted: {snap.last_error}")
    """

    def __init__(
        self,
        max_retries:           int   = DEFAULT_MAX_RETRIES,
        backoff_base_s:        float = DEFAULT_RETRY_BACKOFF_BASE_S,
        backoff_max_s:         float = DEFAULT_RETRY_BACKOFF_MAX_S,
        retriable_exceptions:  Optional[Tuple[Type[Exception], ...]] = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0; got {max_retries}.")
        self._max_retries    = max_retries
        self._backoff_base   = backoff_base_s
        self._backoff_max    = backoff_max_s
        self._retriable: Tuple[Type[Exception], ...] = (
            retriable_exceptions if retriable_exceptions is not None else (Exception,)
        )

    # ── Public interface ───────────────────────────────────────────────────────

    def execute(self, fn: Callable[[], Any]) -> Tuple[Any, RetrySnapshot]:
        """
        Execute ``fn`` with retry logic.

        Parameters
        ----------
        fn : Zero-argument callable to execute.

        Returns
        -------
        (result, RetrySnapshot)
            If all retries fail, ``result`` is ``None`` and
            :attr:`RetrySnapshot.succeeded` is ``False``.  The last
            exception is re-raised AFTER returning the snapshot only
            when ``max_retries == 0``.

        Raises
        ------
        Exception
            The last exception if all attempts fail (when ``max_retries > 0``
            the exception is captured in the snapshot but NOT re-raised — the
            caller should inspect ``snap.succeeded``).
        """
        total_delay = 0.0
        last_error: Optional[str] = None

        for attempt in range(self._max_retries + 1):
            try:
                result = fn()
                return result, RetrySnapshot(
                    attempt       = attempt,
                    succeeded     = True,
                    total_delay_s = total_delay,
                    last_error    = None,
                )
            except self._retriable as exc:
                last_error = str(exc)
                if attempt == self._max_retries:
                    break
                delay = min(
                    self._backoff_base * (2 ** attempt),
                    self._backoff_max,
                )
                total_delay += delay
                time.sleep(delay)

        return None, RetrySnapshot(
            attempt       = self._max_retries,
            succeeded     = False,
            total_delay_s = total_delay,
            last_error    = last_error,
        )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def delay_for(self, attempt: int) -> float:
        """Return the computed back-off delay for attempt number ``attempt``."""
        return min(self._backoff_base * (2 ** attempt), self._backoff_max)

    def __repr__(self) -> str:
        return (
            f"<RetryHandler max_retries={self._max_retries} "
            f"backoff={self._backoff_base}s..{self._backoff_max}s>"
        )
