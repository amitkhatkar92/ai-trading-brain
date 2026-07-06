"""
iios/infrastructure/utilities/retry.py
=======================================
Retry decorator and helper with exponential backoff + jitter.
"""

from __future__ import annotations

import functools
import logging
import random
import time
from typing import Any, Callable, Optional, Tuple, Type, TypeVar

__all__ = ["retry", "RetryConfig"]

_LOG = logging.getLogger("iios.infrastructure.utilities.retry")
F = TypeVar("F", bound=Callable[..., Any])


class RetryConfig:
    def __init__(
        self,
        max_attempts: int = 3,
        backoff_base: float = 0.5,
        backoff_max: float = 30.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ) -> None:
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.exceptions = exceptions

    def backoff_for(self, attempt: int) -> float:
        delay = min(
            self.backoff_base * (self.backoff_multiplier ** attempt),
            self.backoff_max,
        )
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay


def retry(
    max_attempts: int = 3,
    backoff_base: float = 0.5,
    backoff_max: float = 30.0,
    backoff_multiplier: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable[[F], F]:
    """Retry decorator with exponential back-off.

    Usage::

        @retry(max_attempts=5, exceptions=(IOError,))
        def unstable_network_call():
            ...
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        backoff_base=backoff_base,
        backoff_max=backoff_max,
        backoff_multiplier=backoff_multiplier,
        jitter=jitter,
        exceptions=exceptions,
    )

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(config.max_attempts):
                try:
                    return fn(*args, **kwargs)
                except config.exceptions as exc:
                    if attempt == config.max_attempts - 1:
                        raise
                    delay = config.backoff_for(attempt)
                    _LOG.warning(
                        "%s attempt %d/%d failed: %s — retrying in %.2fs",
                        fn.__name__, attempt + 1, config.max_attempts, exc, delay,
                    )
                    if on_retry:
                        on_retry(attempt + 1, exc)
                    time.sleep(delay)
        return wrapper  # type: ignore[return-value]

    return decorator
