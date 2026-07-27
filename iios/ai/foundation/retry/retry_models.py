"""
retry_models.py -- iios.ai.foundation.retry
============================================
RetryPolicy, RetryStrategy, RetryManager -- provider-independent
retry framework.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import abc
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, Type

SCHEMA_VER = "1.0"


# ---------------------------------------------------------------------------
# Retry classification
# ---------------------------------------------------------------------------

class RetryClassification(str, Enum):
    """How a failure should be treated by the retry framework."""
    RETRYABLE     = "retryable"      # retry immediately per policy
    NON_RETRYABLE = "non_retryable"  # do not retry (auth, validation, etc.)
    MAYBE         = "maybe"          # retry once, then give up


# ---------------------------------------------------------------------------
# RetryPolicy -- immutable configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetryPolicy:
    """
    Immutable retry configuration.

    Fields
    ------
    max_attempts :    Maximum total attempts (1 = no retry).
    backoff_base_s :  Base delay in seconds before first retry.
    backoff_max_s :   Maximum delay cap.
    backoff_factor :  Multiplier per attempt (exponential growth).
    timeout_s :       Per-attempt timeout (0 = no per-attempt timeout).
    """
    max_attempts:   int   = 3
    backoff_base_s: float = 1.0
    backoff_max_s:  float = 30.0
    backoff_factor: float = 2.0
    timeout_s:      float = 0.0
    schema:         str   = SCHEMA_VER

    def delay_for(self, attempt: int) -> float:
        """Compute back-off delay for attempt number ``attempt`` (0-indexed)."""
        return min(self.backoff_base_s * (self.backoff_factor ** attempt), self.backoff_max_s)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_attempts":   self.max_attempts,
            "backoff_base_s": self.backoff_base_s,
            "backoff_max_s":  self.backoff_max_s,
            "backoff_factor": self.backoff_factor,
            "timeout_s":      self.timeout_s,
        }

    @classmethod
    def no_retry(cls) -> "RetryPolicy":
        return cls(max_attempts=1)

    @classmethod
    def aggressive(cls) -> "RetryPolicy":
        return cls(max_attempts=5, backoff_base_s=0.5, backoff_max_s=10.0)

    @classmethod
    def conservative(cls) -> "RetryPolicy":
        return cls(max_attempts=2, backoff_base_s=5.0, backoff_max_s=30.0)


# ---------------------------------------------------------------------------
# Retry outcome
# ---------------------------------------------------------------------------

@dataclass
class RetryOutcome:
    """Mutable record of a retry sequence outcome."""
    request_id:    str
    total_attempts: int          = 0
    succeeded:     bool          = False
    total_delay_s: float         = 0.0
    last_error:    Optional[str] = None
    last_error_type: str         = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "total_attempts": self.total_attempts,
            "succeeded":      self.succeeded,
            "total_delay_s":  round(self.total_delay_s, 3),
            "last_error":     self.last_error,
        }


# ---------------------------------------------------------------------------
# Abstract RetryStrategy
# ---------------------------------------------------------------------------

class RetryStrategy(abc.ABC):
    """
    Abstract retry strategy.

    Subclasses determine WHICH exceptions are retryable and HOW the
    delay is computed. They do NOT call ``time.sleep`` -- that is the
    responsibility of :class:`RetryManager`.
    """

    @abc.abstractmethod
    def classify(self, exc: Exception) -> RetryClassification:
        """Classify whether ``exc`` should trigger a retry."""

    @abc.abstractmethod
    def delay_s(self, attempt: int, policy: RetryPolicy) -> float:
        """Return the delay in seconds before attempt number ``attempt``."""


class ExponentialBackoffStrategy(RetryStrategy):
    """
    Standard exponential back-off strategy.

    Classifies all exceptions as RETRYABLE unless they are in
    ``non_retryable_types``.
    """

    def __init__(
        self,
        non_retryable_types: Optional[Tuple[Type[Exception], ...]] = None,
    ) -> None:
        self._non_retryable = non_retryable_types or ()

    def classify(self, exc: Exception) -> RetryClassification:
        if isinstance(exc, self._non_retryable):
            return RetryClassification.NON_RETRYABLE
        return RetryClassification.RETRYABLE

    def delay_s(self, attempt: int, policy: RetryPolicy) -> float:
        return policy.delay_for(attempt)


class FixedDelayStrategy(RetryStrategy):
    """Retries with a fixed delay between every attempt."""

    def __init__(self, delay_s: float = 1.0) -> None:
        self._delay = delay_s

    def classify(self, exc: Exception) -> RetryClassification:
        return RetryClassification.RETRYABLE

    def delay_s(self, attempt: int, policy: RetryPolicy) -> float:
        return self._delay


# ---------------------------------------------------------------------------
# RetryManager
# ---------------------------------------------------------------------------

class RetryManager:
    """
    Executes a callable with retry logic defined by a :class:`RetryPolicy`
    and a :class:`RetryStrategy`.

    Usage::

        manager = RetryManager(
            policy   = RetryPolicy(max_attempts=3),
            strategy = ExponentialBackoffStrategy(),
        )
        result, outcome = manager.execute("req-001", lambda: call_provider())
        if not outcome.succeeded:
            ...
    """

    def __init__(
        self,
        policy:   RetryPolicy          = RetryPolicy(),
        strategy: Optional[RetryStrategy] = None,
    ) -> None:
        self._policy   = policy
        self._strategy = strategy or ExponentialBackoffStrategy()

    def execute(
        self,
        request_id: str,
        fn:         Callable[[], Any],
    ) -> Tuple[Any, RetryOutcome]:
        """
        Execute ``fn`` with retry logic.

        Returns
        -------
        (result, RetryOutcome)
            ``result`` is None on exhaustion.  Check ``outcome.succeeded``.
        """
        outcome = RetryOutcome(request_id=request_id)
        last_exc: Optional[Exception] = None

        for attempt in range(self._policy.max_attempts):
            outcome.total_attempts = attempt + 1
            try:
                result = fn()
                outcome.succeeded = True
                return result, outcome
            except Exception as exc:
                last_exc = exc
                outcome.last_error      = str(exc)
                outcome.last_error_type = type(exc).__name__

                classification = self._strategy.classify(exc)
                if classification == RetryClassification.NON_RETRYABLE:
                    break

                # Last attempt -- don't sleep, just exit
                if attempt == self._policy.max_attempts - 1:
                    break

                delay = self._strategy.delay_s(attempt, self._policy)
                outcome.total_delay_s += delay
                time.sleep(delay)

        return None, outcome

    @property
    def policy(self) -> RetryPolicy:
        return self._policy
