"""iios/common/errors/retry_policy.py
Retry policies for the IIOS platform.

Supports:
  • NoRetry                    — never retry
  • FixedRetry                 — constant delay between attempts
  • ExponentialBackoff         — delay doubles each attempt
  • ExponentialBackoffWithJitter — adds random jitter to prevent thundering herd

All policies support a RetryClassifier that decides which exceptions are
eligible for retry.  Non-retriable exceptions immediately stop the retry
loop regardless of remaining attempts.

Usage::

    from iios.common.errors.retry_policy import ExponentialBackoffWithJitter, RetryClassifier
    from iios.common.errors.exceptions import IntegrationError, TimeoutError

    policy = ExponentialBackoffWithJitter(
        max_retries = 3,
        base_delay  = 0.5,
        max_delay   = 10.0,
        classifier  = RetryClassifier(retriable={IntegrationError, TimeoutError}),
    )

    decision = policy.should_retry(attempt=1, exc=exc)
    if decision.should_retry:
        time.sleep(decision.delay_sec)
"""
from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, FrozenSet, Optional, Set, Type, Union


# ── RetryDecision ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RetryDecision:
    """
    Immutable result of a retry policy evaluation.

    Attributes
    ----------
    should_retry:
        True if the operation should be retried.
    delay_sec:
        Seconds to wait before the next attempt.
    attempt:
        The 1-based attempt number that just failed.
    reason:
        Human-readable explanation of the decision.
    """
    should_retry: bool
    delay_sec:    float
    attempt:      int
    reason:       str = ""


# ── RetryClassifier ───────────────────────────────────────────────────────────

class RetryClassifier:
    """
    Decides whether an exception is eligible for retry.

    Can be constructed from:
    • A set of exception types — retry if isinstance(exc, any_of_these)
    • A callable predicate     — retry if predicate(exc) returns True
    • Both                     — union of both checks

    If neither is provided, all exceptions are retriable (permissive default).
    """

    def __init__(
        self,
        retriable:  Optional[Set[Type[BaseException]]] = None,
        predicate:  Optional[Callable[[BaseException], bool]] = None,
    ) -> None:
        self._retriable: FrozenSet[Type[BaseException]] = (
            frozenset(retriable) if retriable else frozenset()
        )
        self._predicate: Optional[Callable[[BaseException], bool]] = predicate

    def is_retriable(self, exc: BaseException) -> bool:
        """Return True if *exc* should be retried."""
        if not self._retriable and self._predicate is None:
            return True   # permissive default
        type_match = (
            isinstance(exc, tuple(self._retriable)) if self._retriable else False
        )
        pred_match = (
            self._predicate(exc) if self._predicate is not None else False
        )
        return type_match or pred_match

    @classmethod
    def permissive(cls) -> "RetryClassifier":
        """Return a classifier that retries all exceptions."""
        return cls()

    @classmethod
    def strict(cls, *exc_types: Type[BaseException]) -> "RetryClassifier":
        """Return a classifier that only retries the listed exception types."""
        return cls(retriable=set(exc_types))

    @classmethod
    def non_retriable(cls) -> "RetryClassifier":
        """Return a classifier that never retries (always returns False)."""
        return cls(predicate=lambda _: False)


# ── Abstract base ─────────────────────────────────────────────────────────────

class RetryPolicy(ABC):
    """
    Abstract base class for all retry policies.

    Implementations compute a RetryDecision given the attempt number and
    the exception that caused the failure.  Implementations MUST NOT call
    ``time.sleep()`` — the caller (RecoveryEngine) decides whether to sleep.
    """

    @abstractmethod
    def should_retry(self, attempt: int, exc: BaseException) -> RetryDecision:
        """
        Evaluate whether *exc* on attempt *attempt* should be retried.

        :param attempt: 1-based count of the attempt that just failed.
        :param exc:     The exception that caused the failure.
        :returns:       A RetryDecision.
        """
        ...

    @property
    @abstractmethod
    def max_retries(self) -> int:
        """Maximum number of retry attempts (not counting the original call)."""
        ...


# ── Concrete policies ─────────────────────────────────────────────────────────

class NoRetry(RetryPolicy):
    """
    Never retry — immediately propagate the exception.

    Use for operations that are deterministic, idempotent, or where the
    cost of retrying is higher than the cost of failing fast.
    """

    @property
    def max_retries(self) -> int:
        return 0

    def should_retry(self, attempt: int, exc: BaseException) -> RetryDecision:
        return RetryDecision(
            should_retry = False,
            delay_sec    = 0.0,
            attempt      = attempt,
            reason       = "NoRetry policy: retries disabled",
        )


class FixedRetry(RetryPolicy):
    """
    Retry up to *max_retries* times with a constant *delay_sec* between attempts.

    Usage::

        policy = FixedRetry(max_retries=3, delay_sec=1.0)
    """

    def __init__(
        self,
        max_retries: int   = 3,
        delay_sec:   float = 1.0,
        classifier:  Optional[RetryClassifier] = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries}")
        if delay_sec < 0:
            raise ValueError(f"delay_sec must be >= 0, got {delay_sec}")
        self._max_retries: int              = max_retries
        self._delay_sec:   float            = delay_sec
        self._classifier:  RetryClassifier  = classifier or RetryClassifier.permissive()

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def should_retry(self, attempt: int, exc: BaseException) -> RetryDecision:
        if not self._classifier.is_retriable(exc):
            return RetryDecision(
                should_retry = False,
                delay_sec    = 0.0,
                attempt      = attempt,
                reason       = f"Non-retriable exception: {type(exc).__name__}",
            )
        if attempt > self._max_retries:
            return RetryDecision(
                should_retry = False,
                delay_sec    = 0.0,
                attempt      = attempt,
                reason       = f"Max retries ({self._max_retries}) exhausted after {attempt} attempts",
            )
        return RetryDecision(
            should_retry = True,
            delay_sec    = self._delay_sec,
            attempt      = attempt,
            reason       = f"Fixed retry: attempt {attempt}/{self._max_retries}, delay={self._delay_sec}s",
        )


class ExponentialBackoff(RetryPolicy):
    """
    Retry with exponentially increasing delay between attempts.

    delay = min(base_delay * (multiplier ** (attempt - 1)), max_delay)

    Usage::

        policy = ExponentialBackoff(
            max_retries = 5,
            base_delay  = 0.5,
            max_delay   = 30.0,
            multiplier  = 2.0,
        )
    """

    def __init__(
        self,
        max_retries: int   = 3,
        base_delay:  float = 1.0,
        max_delay:   float = 60.0,
        multiplier:  float = 2.0,
        classifier:  Optional[RetryClassifier] = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries}")
        if base_delay <= 0:
            raise ValueError(f"base_delay must be > 0, got {base_delay}")
        if max_delay < base_delay:
            raise ValueError(f"max_delay ({max_delay}) must be >= base_delay ({base_delay})")
        if multiplier <= 0:
            raise ValueError(f"multiplier must be > 0, got {multiplier}")
        self._max_retries: int              = max_retries
        self._base_delay:  float            = base_delay
        self._max_delay:   float            = max_delay
        self._multiplier:  float            = multiplier
        self._classifier:  RetryClassifier  = classifier or RetryClassifier.permissive()

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def _compute_delay(self, attempt: int) -> float:
        delay = self._base_delay * (self._multiplier ** (attempt - 1))
        return min(delay, self._max_delay)

    def should_retry(self, attempt: int, exc: BaseException) -> RetryDecision:
        if not self._classifier.is_retriable(exc):
            return RetryDecision(
                should_retry = False,
                delay_sec    = 0.0,
                attempt      = attempt,
                reason       = f"Non-retriable exception: {type(exc).__name__}",
            )
        if attempt > self._max_retries:
            return RetryDecision(
                should_retry = False,
                delay_sec    = 0.0,
                attempt      = attempt,
                reason       = f"Max retries ({self._max_retries}) exhausted after {attempt} attempts",
            )
        delay = self._compute_delay(attempt)
        return RetryDecision(
            should_retry = True,
            delay_sec    = delay,
            attempt      = attempt,
            reason       = f"Exponential backoff: attempt {attempt}/{self._max_retries}, delay={delay:.3f}s",
        )


class ExponentialBackoffWithJitter(ExponentialBackoff):
    """
    Exponential backoff with uniform random jitter to prevent thundering herd.

    delay = min(base_delay * multiplier^(attempt-1), max_delay) * U(jitter_min, 1.0)

    Usage::

        policy = ExponentialBackoffWithJitter(
            max_retries = 4,
            base_delay  = 1.0,
            max_delay   = 30.0,
            jitter_min  = 0.5,   # delay between 50% and 100% of computed value
        )
    """

    def __init__(
        self,
        max_retries: int   = 3,
        base_delay:  float = 1.0,
        max_delay:   float = 60.0,
        multiplier:  float = 2.0,
        jitter_min:  float = 0.5,
        classifier:  Optional[RetryClassifier] = None,
    ) -> None:
        super().__init__(
            max_retries = max_retries,
            base_delay  = base_delay,
            max_delay   = max_delay,
            multiplier  = multiplier,
            classifier  = classifier,
        )
        if not (0.0 <= jitter_min <= 1.0):
            raise ValueError(f"jitter_min must be in [0, 1], got {jitter_min}")
        self._jitter_min: float = jitter_min

    def _compute_delay(self, attempt: int) -> float:
        base = super()._compute_delay(attempt)
        jitter = random.uniform(self._jitter_min, 1.0)
        return base * jitter

    def should_retry(self, attempt: int, exc: BaseException) -> RetryDecision:
        decision = super().should_retry(attempt, exc)
        if decision.should_retry:
            return RetryDecision(
                should_retry = True,
                delay_sec    = decision.delay_sec,
                attempt      = attempt,
                reason       = (
                    f"Exponential backoff with jitter: attempt {attempt}/{self._max_retries},"
                    f" delay={decision.delay_sec:.3f}s"
                ),
            )
        return decision
