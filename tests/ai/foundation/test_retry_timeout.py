"""
test_retry_timeout.py -- tests for Retry and Timeout frameworks.

Covers:
- RetryPolicy configuration and delay computation
- RetryManager execution with success / failure / non-retryable
- ExponentialBackoffStrategy and FixedDelayStrategy classification
- TimeoutPolicy tiers
- ExecutionDeadline expiry and assertion
- TimeoutController fire/cancel
"""
from __future__ import annotations

import time
import unittest

from iios.ai.foundation.retry import (
    RetryClassification,
    RetryPolicy,
    RetryManager,
    RetryOutcome,
    ExponentialBackoffStrategy,
    FixedDelayStrategy,
)
from iios.ai.foundation.timeout import (
    TimeoutPolicy,
    ExecutionDeadline,
    TimeoutController,
)


# ---------------------------------------------------------------------------
# Test: RetryPolicy
# ---------------------------------------------------------------------------

class TestRetryPolicy(unittest.TestCase):

    def test_defaults(self):
        p = RetryPolicy()
        self.assertEqual(p.max_attempts, 3)
        self.assertEqual(p.backoff_base_s, 1.0)

    def test_no_retry(self):
        p = RetryPolicy.no_retry()
        self.assertEqual(p.max_attempts, 1)

    def test_delay_for_attempt(self):
        p = RetryPolicy(backoff_base_s=1.0, backoff_factor=2.0, backoff_max_s=10.0)
        self.assertAlmostEqual(p.delay_for(0), 1.0)
        self.assertAlmostEqual(p.delay_for(1), 2.0)
        self.assertAlmostEqual(p.delay_for(2), 4.0)
        self.assertAlmostEqual(p.delay_for(10), 10.0)  # capped

    def test_to_dict(self):
        d = RetryPolicy().to_dict()
        self.assertIn("max_attempts", d)
        self.assertIn("backoff_base_s", d)

    def test_frozen(self):
        p = RetryPolicy()
        with self.assertRaises((AttributeError, TypeError)):
            p.max_attempts = 10  # type: ignore


# ---------------------------------------------------------------------------
# Test: RetryStrategy
# ---------------------------------------------------------------------------

class TestRetryStrategy(unittest.TestCase):

    def test_exponential_classifies_retryable(self):
        s   = ExponentialBackoffStrategy()
        exc = RuntimeError("transient")
        self.assertEqual(s.classify(exc), RetryClassification.RETRYABLE)

    def test_exponential_non_retryable_types(self):
        s   = ExponentialBackoffStrategy(non_retryable_types=(ValueError,))
        self.assertEqual(s.classify(ValueError("bad")), RetryClassification.NON_RETRYABLE)
        self.assertEqual(s.classify(RuntimeError("ok")), RetryClassification.RETRYABLE)

    def test_fixed_delay_is_constant(self):
        p = RetryPolicy()
        s = FixedDelayStrategy(delay_s=3.0)
        self.assertAlmostEqual(s.delay_s(0, p), 3.0)
        self.assertAlmostEqual(s.delay_s(5, p), 3.0)

    def test_fixed_delay_always_retryable(self):
        s = FixedDelayStrategy()
        self.assertEqual(s.classify(RuntimeError()), RetryClassification.RETRYABLE)


# ---------------------------------------------------------------------------
# Test: RetryManager
# ---------------------------------------------------------------------------

class TestRetryManager(unittest.TestCase):

    def test_success_first_attempt(self):
        manager = RetryManager(RetryPolicy(max_attempts=3))
        result, outcome = manager.execute("r1", lambda: 42)
        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.total_attempts, 1)
        self.assertEqual(result, 42)

    def test_success_after_retry(self):
        calls = [0]
        def fn():
            calls[0] += 1
            if calls[0] < 2:
                raise RuntimeError("transient")
            return "ok"
        manager = RetryManager(RetryPolicy(max_attempts=3, backoff_base_s=0.0))
        result, outcome = manager.execute("r2", fn)
        self.assertTrue(outcome.succeeded)
        self.assertEqual(outcome.total_attempts, 2)
        self.assertEqual(result, "ok")

    def test_all_attempts_fail(self):
        manager = RetryManager(RetryPolicy(max_attempts=2, backoff_base_s=0.0))
        result, outcome = manager.execute("r3", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.total_attempts, 2)
        self.assertIsNone(result)

    def test_non_retryable_stops_immediately(self):
        calls = [0]
        def fn():
            calls[0] += 1
            raise ValueError("bad input")
        strategy = ExponentialBackoffStrategy(non_retryable_types=(ValueError,))
        manager  = RetryManager(RetryPolicy(max_attempts=3, backoff_base_s=0.0), strategy)
        result, outcome = manager.execute("r4", fn)
        self.assertFalse(outcome.succeeded)
        self.assertEqual(outcome.total_attempts, 1)  # stopped after 1

    def test_outcome_to_dict(self):
        manager = RetryManager(RetryPolicy(max_attempts=1))
        _, outcome = manager.execute("r5", lambda: 1)
        d = outcome.to_dict()
        self.assertIn("request_id", d)
        self.assertIn("succeeded", d)


# ---------------------------------------------------------------------------
# Test: TimeoutPolicy
# ---------------------------------------------------------------------------

class TestTimeoutPolicy(unittest.TestCase):

    def test_defaults(self):
        p = TimeoutPolicy()
        self.assertEqual(p.request_timeout_s, 30.0)
        self.assertEqual(p.pipeline_timeout_s, 60.0)

    def test_fast_tier(self):
        p = TimeoutPolicy.fast()
        self.assertLess(p.request_timeout_s, 30.0)

    def test_relaxed_tier(self):
        p = TimeoutPolicy.relaxed()
        self.assertGreater(p.request_timeout_s, 30.0)

    def test_frozen(self):
        p = TimeoutPolicy()
        with self.assertRaises((AttributeError, TypeError)):
            p.request_timeout_s = 5.0  # type: ignore

    def test_to_dict(self):
        d = TimeoutPolicy().to_dict()
        self.assertIn("request_timeout_s", d)
        self.assertIn("pipeline_timeout_s", d)


# ---------------------------------------------------------------------------
# Test: ExecutionDeadline
# ---------------------------------------------------------------------------

class TestExecutionDeadline(unittest.TestCase):

    def test_not_exceeded_immediately(self):
        d = ExecutionDeadline.from_timeout(60.0)
        self.assertFalse(d.is_exceeded())

    def test_exceeded_with_past_deadline(self):
        d = ExecutionDeadline(time.monotonic() - 1.0)
        self.assertTrue(d.is_exceeded())

    def test_no_deadline_never_exceeded(self):
        d = ExecutionDeadline.no_deadline()
        self.assertFalse(d.is_exceeded())

    def test_remaining_s_positive(self):
        d = ExecutionDeadline.from_timeout(60.0)
        self.assertGreater(d.remaining_s(), 0)

    def test_remaining_s_zero_when_expired(self):
        d = ExecutionDeadline(time.monotonic() - 1.0)
        self.assertEqual(d.remaining_s(), 0.0)

    def test_assert_not_exceeded_raises(self):
        d = ExecutionDeadline(time.monotonic() - 1.0)
        with self.assertRaises(TimeoutError):
            d.assert_not_exceeded("test_op")

    def test_assert_not_exceeded_ok(self):
        d = ExecutionDeadline.from_timeout(60.0)
        d.assert_not_exceeded("test_op")  # should not raise


# ---------------------------------------------------------------------------
# Test: TimeoutController
# ---------------------------------------------------------------------------

class TestTimeoutController(unittest.TestCase):

    def test_cancels_before_firing(self):
        fired = [False]
        def cb():
            fired[0] = True
        ctrl = TimeoutController(timeout_s=0.5, on_timeout=cb)
        ctrl.start()
        ctrl.stop()  # cancel before timeout
        time.sleep(0.1)
        self.assertFalse(ctrl.is_timed_out())

    def test_fires_on_timeout(self):
        fired = [False]
        def cb():
            fired[0] = True
        ctrl = TimeoutController(timeout_s=0.05, on_timeout=cb)
        ctrl.start()
        time.sleep(0.15)
        self.assertTrue(ctrl.is_timed_out())


if __name__ == "__main__":
    unittest.main()
