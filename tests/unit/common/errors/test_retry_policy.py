"""tests/unit/common/errors/test_retry_policy.py
Unit tests for retry policies.
"""
from __future__ import annotations

import pytest

from iios.common.errors.exceptions import IntegrationError, TimeoutError, IIOSError
from iios.common.errors.retry_policy import (
    ExponentialBackoff,
    ExponentialBackoffWithJitter,
    FixedRetry,
    NoRetry,
    RetryClassifier,
    RetryDecision,
)


# ── RetryDecision ─────────────────────────────────────────────────────────────

class TestRetryDecision:

    def test_frozen(self):
        d = RetryDecision(should_retry=True, delay_sec=1.0, attempt=1)
        with pytest.raises((AttributeError, TypeError)):
            d.should_retry = False   # type: ignore[misc]

    def test_default_reason(self):
        d = RetryDecision(should_retry=True, delay_sec=0.5, attempt=1)
        assert d.reason == ""


# ── RetryClassifier ───────────────────────────────────────────────────────────

class TestRetryClassifier:

    def test_permissive_retries_all(self):
        clf = RetryClassifier.permissive()
        assert clf.is_retriable(ValueError("any"))
        assert clf.is_retriable(RuntimeError("any"))

    def test_strict_retries_only_listed(self):
        clf = RetryClassifier.strict(IntegrationError, TimeoutError)
        assert clf.is_retriable(IntegrationError("ok"))
        assert clf.is_retriable(TimeoutError("ok"))
        assert not clf.is_retriable(ValueError("not listed"))

    def test_non_retriable_never_retries(self):
        clf = RetryClassifier.non_retriable()
        assert not clf.is_retriable(IntegrationError("any"))
        assert not clf.is_retriable(ValueError("any"))

    def test_predicate_classifier(self):
        clf = RetryClassifier(predicate=lambda e: "transient" in str(e).lower())
        assert clf.is_retriable(ValueError("transient error"))
        assert not clf.is_retriable(ValueError("permanent"))

    def test_combined_retriable_and_predicate(self):
        clf = RetryClassifier(
            retriable  = {IntegrationError},
            predicate  = lambda e: "transient" in str(e),
        )
        assert clf.is_retriable(IntegrationError("anything"))
        assert clf.is_retriable(ValueError("transient"))
        assert not clf.is_retriable(ValueError("permanent"))

    def test_strict_with_subclass(self):
        clf = RetryClassifier.strict(IIOSError)
        assert clf.is_retriable(IntegrationError("sub"))   # subclass of IIOSError


# ── NoRetry ───────────────────────────────────────────────────────────────────

class TestNoRetry:

    def test_max_retries_is_zero(self):
        assert NoRetry().max_retries == 0

    def test_should_retry_always_false(self):
        policy = NoRetry()
        decision = policy.should_retry(1, ValueError("any"))
        assert not decision.should_retry
        assert decision.delay_sec == 0.0

    def test_attempt_preserved(self):
        policy = NoRetry()
        decision = policy.should_retry(5, ValueError("any"))
        assert decision.attempt == 5


# ── FixedRetry ────────────────────────────────────────────────────────────────

class TestFixedRetry:

    def test_first_attempt_retried(self):
        policy = FixedRetry(max_retries=3, delay_sec=0.5)
        d = policy.should_retry(1, ValueError())
        assert d.should_retry
        assert d.delay_sec == 0.5

    def test_exactly_max_retries_retried(self):
        policy = FixedRetry(max_retries=3, delay_sec=1.0)
        d = policy.should_retry(3, ValueError())
        assert d.should_retry

    def test_exceeding_max_retries_stops(self):
        policy = FixedRetry(max_retries=3, delay_sec=1.0)
        d = policy.should_retry(4, ValueError())
        assert not d.should_retry

    def test_non_retriable_exception_stops(self):
        clf = RetryClassifier.strict(IntegrationError)
        policy = FixedRetry(max_retries=5, classifier=clf)
        d = policy.should_retry(1, ValueError("not retriable"))
        assert not d.should_retry

    def test_retriable_exception_passes(self):
        clf = RetryClassifier.strict(IntegrationError)
        policy = FixedRetry(max_retries=5, classifier=clf)
        d = policy.should_retry(1, IntegrationError("retriable"))
        assert d.should_retry

    def test_delay_constant_across_attempts(self):
        policy = FixedRetry(max_retries=5, delay_sec=2.0)
        for attempt in range(1, 6):
            d = policy.should_retry(attempt, ValueError())
            if d.should_retry:
                assert d.delay_sec == 2.0

    def test_max_retries_property(self):
        assert FixedRetry(max_retries=7).max_retries == 7

    def test_negative_max_retries_raises(self):
        with pytest.raises(ValueError):
            FixedRetry(max_retries=-1)

    def test_negative_delay_raises(self):
        with pytest.raises(ValueError):
            FixedRetry(delay_sec=-0.1)

    def test_zero_delay_is_valid(self):
        policy = FixedRetry(delay_sec=0.0)
        d = policy.should_retry(1, ValueError())
        assert d.should_retry
        assert d.delay_sec == 0.0


# ── ExponentialBackoff ────────────────────────────────────────────────────────

class TestExponentialBackoff:

    def test_delays_increase(self):
        policy = ExponentialBackoff(max_retries=5, base_delay=1.0, max_delay=100.0, multiplier=2.0)
        delays = []
        for i in range(1, 6):
            d = policy.should_retry(i, ValueError())
            if d.should_retry:
                delays.append(d.delay_sec)
        # Delays should be non-decreasing
        for i in range(len(delays) - 1):
            assert delays[i] <= delays[i + 1]

    def test_delay_capped_at_max(self):
        policy = ExponentialBackoff(max_retries=10, base_delay=1.0, max_delay=5.0, multiplier=2.0)
        for i in range(1, 11):
            d = policy.should_retry(i, ValueError())
            if d.should_retry:
                assert d.delay_sec <= 5.0

    def test_base_delay_first_attempt(self):
        policy = ExponentialBackoff(max_retries=5, base_delay=1.0, max_delay=100.0, multiplier=2.0)
        d = policy.should_retry(1, ValueError())
        assert d.delay_sec == pytest.approx(1.0)

    def test_second_attempt_doubled(self):
        policy = ExponentialBackoff(max_retries=5, base_delay=1.0, max_delay=100.0, multiplier=2.0)
        d = policy.should_retry(2, ValueError())
        assert d.delay_sec == pytest.approx(2.0)

    def test_exceeds_max_retries_stops(self):
        policy = ExponentialBackoff(max_retries=3, base_delay=1.0, max_delay=10.0)
        d = policy.should_retry(4, ValueError())
        assert not d.should_retry

    def test_max_retries_property(self):
        assert ExponentialBackoff(max_retries=7).max_retries == 7

    def test_invalid_args_raise(self):
        with pytest.raises(ValueError):
            ExponentialBackoff(max_retries=-1)
        with pytest.raises(ValueError):
            ExponentialBackoff(base_delay=0.0)
        with pytest.raises(ValueError):
            ExponentialBackoff(max_delay=0.5, base_delay=1.0)
        with pytest.raises(ValueError):
            ExponentialBackoff(multiplier=0.0)

    def test_non_retriable_stops(self):
        clf = RetryClassifier.strict(IntegrationError)
        policy = ExponentialBackoff(max_retries=5, classifier=clf)
        d = policy.should_retry(1, ValueError("not retriable"))
        assert not d.should_retry


# ── ExponentialBackoffWithJitter ──────────────────────────────────────────────

class TestExponentialBackoffWithJitter:

    def test_delay_within_bounds(self):
        policy = ExponentialBackoffWithJitter(
            max_retries=5,
            base_delay=1.0,
            max_delay=30.0,
            jitter_min=0.5,
        )
        for i in range(1, 6):
            d = policy.should_retry(i, ValueError())
            if d.should_retry:
                # Delay must be positive
                assert d.delay_sec > 0
                # Delay must not exceed max_delay (ceiling after jitter)
                assert d.delay_sec <= 30.0

    def test_jitter_does_not_exceed_max_delay(self):
        policy = ExponentialBackoffWithJitter(
            max_retries=20,
            base_delay=1.0,
            max_delay=10.0,
            jitter_min=0.0,
        )
        for i in range(1, 21):
            d = policy.should_retry(i, ValueError())
            if d.should_retry:
                assert d.delay_sec <= 10.0

    def test_should_retry_stops_at_max(self):
        policy = ExponentialBackoffWithJitter(max_retries=2)
        d = policy.should_retry(3, ValueError())
        assert not d.should_retry

    def test_invalid_jitter_min_raises(self):
        with pytest.raises(ValueError):
            ExponentialBackoffWithJitter(jitter_min=-0.1)
        with pytest.raises(ValueError):
            ExponentialBackoffWithJitter(jitter_min=1.1)

    def test_zero_jitter_min(self):
        # jitter_min=0.0 means delay can be anywhere from 0 to base
        policy = ExponentialBackoffWithJitter(
            max_retries=5, base_delay=1.0, max_delay=10.0, jitter_min=0.0
        )
        d = policy.should_retry(1, ValueError())
        assert d.should_retry
        assert 0.0 <= d.delay_sec <= 1.0

    def test_full_jitter_min_one(self):
        # jitter_min=1.0 means no jitter — always the full delay
        policy = ExponentialBackoffWithJitter(
            max_retries=3, base_delay=1.0, max_delay=10.0, jitter_min=1.0
        )
        d = policy.should_retry(1, ValueError())
        assert d.delay_sec == pytest.approx(1.0, rel=1e-6)
