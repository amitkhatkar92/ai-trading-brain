"""
iios/observation/collectors/base_collector.py
=============================================
BaseCollector — root of the IIOS Observation Collection Framework.

Every data collector in IIOS must inherit from BaseCollector.

Lifecycle stages::

    collector.initialise()
    collector.authenticate()
    collector.connect()
    observations = collector.run()   # full pipeline
    collector.shutdown()

``run()`` orchestrates: collect → validate → normalise → publish.
Subclasses implement ``_do_collect()`` and ``_do_normalise()``.
Built-in: retry policy, circuit breaker, rate limiter, checkpointing.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..observation_constants import (
    CollectorType,
    ObservationSource,
    ObservationType,
    SYSTEM_OBSERVER,
)
from ..models.observation          import Observation
from ..models.observation_source   import ObservationSourceInfo
from ..models.observation_metadata import ObservationMetadata
from .collector_constants import (
    CircuitBreakerState,
    CollectorCategory,
    CollectorStatus,
    DEFAULT_BACKOFF_BASE_S,
    DEFAULT_BACKOFF_MAX_S,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CIRCUIT_FAILURE_THRESHOLD,
    DEFAULT_CIRCUIT_RECOVERY_S,
    DEFAULT_MAX_RETRIES,
    DEFAULT_POLL_INTERVAL_S,
    DEFAULT_RATE_LIMIT_CALLS,
    DEFAULT_RATE_LIMIT_WINDOW_S,
    DEFAULT_TIMEOUT_S,
    ExecutionMode,
    RetryStrategy,
)
from .collector_exceptions import (
    CollectorCircuitOpenError,
    CollectorRateLimitError,
    CollectorRetryExhaustedError,
    CollectorShutdownError,
)

__all__ = [
    "RetryPolicy",
    "CircuitBreaker",
    "RateLimiter",
    "CollectorConfig",
    "CollectorStats",
    "BaseCollector",
    "CollectorHook",
]

_LOG = logging.getLogger("iios.collector.base")

CollectorHook = Callable[["BaseCollector", list[Observation]], None]


# ── Reliability primitives ────────────────────────────────────────────────────

@dataclass
class RetryPolicy:
    """Configures retry behaviour for a collector."""
    max_retries:  int           = DEFAULT_MAX_RETRIES
    strategy:     RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay_s: float         = DEFAULT_BACKOFF_BASE_S
    max_delay_s:  float         = DEFAULT_BACKOFF_MAX_S
    jitter:       bool          = True

    def delay(self, attempt: int) -> float:
        """Return the delay (seconds) before the given retry attempt."""
        if self.strategy == RetryStrategy.NONE:
            return 0.0
        if self.strategy == RetryStrategy.FIXED:
            d = self.base_delay_s
        elif self.strategy == RetryStrategy.LINEAR:
            d = self.base_delay_s * attempt
        elif self.strategy == RetryStrategy.FIBONACCI:
            a, b = 1, 1
            for _ in range(max(0, attempt - 1)):
                a, b = b, a + b
            d = self.base_delay_s * a
        else:  # EXPONENTIAL (default)
            d = self.base_delay_s * (2 ** max(0, attempt - 1))
        d = min(d, self.max_delay_s)
        if self.jitter:
            import random
            d = d * (0.5 + random.random() * 0.5)
        return max(0.0, d)


@dataclass
class CircuitBreaker:
    """
    Simple three-state circuit breaker.

    States: CLOSED (passing) → OPEN (blocking) → HALF_OPEN (probing).
    """
    failure_threshold:  int   = DEFAULT_CIRCUIT_FAILURE_THRESHOLD
    recovery_timeout_s: float = DEFAULT_CIRCUIT_RECOVERY_S

    _state:           CircuitBreakerState = field(
        default=CircuitBreakerState.CLOSED, init=False, repr=False)
    _failure_count:   int                 = field(default=0, init=False, repr=False)
    _last_failure_at: float               = field(default=0.0, init=False, repr=False)
    _lock:            threading.Lock      = field(
        default_factory=threading.Lock, init=False, repr=False)

    @property
    def state(self) -> CircuitBreakerState:
        return self._state

    def allow_request(self) -> bool:
        with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True
            if self._state == CircuitBreakerState.OPEN:
                if (time.time() - self._last_failure_at) >= self.recovery_timeout_s:
                    self._state = CircuitBreakerState.HALF_OPEN
                    return True
                return False
            return True  # HALF_OPEN: allow one probe

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state         = CircuitBreakerState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count  += 1
            self._last_failure_at = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitBreakerState.OPEN

    def reset(self) -> None:
        with self._lock:
            self._failure_count   = 0
            self._last_failure_at = 0.0
            self._state           = CircuitBreakerState.CLOSED

    def to_dict(self) -> dict[str, Any]:
        return {
            "state":           self._state.value,
            "failure_count":   self._failure_count,
            "last_failure_at": self._last_failure_at,
        }


@dataclass
class RateLimiter:
    """Sliding-window token-bucket rate limiter."""
    max_calls: int   = DEFAULT_RATE_LIMIT_CALLS
    window_s:  float = DEFAULT_RATE_LIMIT_WINDOW_S

    _calls: list[float]    = field(default_factory=list, init=False, repr=False)
    _lock:  threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def allow(self) -> bool:
        now = time.time()
        with self._lock:
            cutoff     = now - self.window_s
            self._calls = [t for t in self._calls if t > cutoff]
            if len(self._calls) >= self.max_calls:
                return False
            self._calls.append(now)
            return True

    @property
    def remaining(self) -> int:
        now = time.time()
        with self._lock:
            cutoff     = now - self.window_s
            self._calls = [t for t in self._calls if t > cutoff]
            return max(0, self.max_calls - len(self._calls))

    def reset(self) -> None:
        with self._lock:
            self._calls.clear()


# ── Configuration & stats ─────────────────────────────────────────────────────

@dataclass
class CollectorConfig:
    """Full configuration for a collector instance."""
    name:             str
    collector_type:   CollectorType     = CollectorType.PULL
    category:         CollectorCategory = CollectorCategory.MARKET_DATA
    source:           ObservationSource = ObservationSource.UNKNOWN
    obs_type:         ObservationType   = ObservationType.UNKNOWN
    execution_mode:   ExecutionMode     = ExecutionMode.SYNC
    poll_interval_s:  float             = DEFAULT_POLL_INTERVAL_S
    batch_size:       int               = DEFAULT_BATCH_SIZE
    timeout_s:        float             = DEFAULT_TIMEOUT_S
    enabled:          bool              = True
    retry_policy:     RetryPolicy       = field(default_factory=RetryPolicy)
    circuit_breaker:  CircuitBreaker    = field(default_factory=CircuitBreaker)
    rate_limiter:     RateLimiter       = field(default_factory=RateLimiter)
    instruments:      list[str]         = field(default_factory=list)
    exchanges:        list[str]         = field(default_factory=list)
    attributes:       dict[str, Any]    = field(default_factory=dict)
    version:          str               = "1.0.0"


@dataclass
class CollectorStats:
    """Live runtime statistics for one collector."""
    name:             str             = ""
    status:           CollectorStatus = CollectorStatus.IDLE
    total_collected:  int             = 0
    total_published:  int             = 0
    total_errors:     int             = 0
    total_retries:    int             = 0
    total_skipped:    int             = 0
    run_count:        int             = 0
    last_run_at:      float           = 0.0
    last_success_at:  float           = 0.0
    last_error_at:    float           = 0.0
    last_error:       str             = ""
    is_running:       bool            = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":            self.name,
            "status":          self.status.value,
            "total_collected": self.total_collected,
            "total_published": self.total_published,
            "total_errors":    self.total_errors,
            "total_retries":   self.total_retries,
            "run_count":       self.run_count,
            "last_run_at":     self.last_run_at,
            "last_success_at": self.last_success_at,
            "last_error":      self.last_error,
            "is_running":      self.is_running,
        }


# ── BaseCollector ─────────────────────────────────────────────────────────────

class BaseCollector(ABC):
    """
    Root of the IIOS Observation Collection Framework hierarchy.

    Subclasses implement two abstract methods:

    * ``_do_collect() -> Any``       — fetch raw data from source
    * ``_do_normalise(raw) -> list[Observation]``  — convert to observations

    The ``run()`` method drives the full pipeline:
    COLLECT → VALIDATE → NORMALISE → PUBLISH
    with built-in retry, circuit-breaker, and rate-limiter guards.
    """

    def __init__(self, config: CollectorConfig) -> None:
        self.config      = config
        self._log        = logging.getLogger(f"iios.collector.{config.name}")
        self._stats      = CollectorStats(name=config.name)
        self._lock       = threading.RLock()
        self._status     = CollectorStatus.IDLE
        self._hooks:     list[CollectorHook] = []
        self._start_time = 0.0
        self._checkpoint: dict[str, Any] = {}

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def status(self) -> CollectorStatus:
        return self._status

    @property
    def stats(self) -> CollectorStats:
        return self._stats

    @property
    def is_running(self) -> bool:
        return self._status == CollectorStatus.COLLECTING

    @property
    def is_enabled(self) -> bool:
        return self.config.enabled

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialise(self) -> None:
        """One-time setup. Call before first ``run()``."""
        with self._lock:
            self._set_status(CollectorStatus.INITIALISING)
            self._start_time = time.time()
            self._do_initialise()
            self._set_status(CollectorStatus.CONFIGURED)
            self._log.info("Initialised: %s", self.name)

    def configure(self, **kwargs: Any) -> None:
        """Update configuration fields at runtime."""
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)

    def authenticate(self) -> None:
        """Perform source authentication. No-op by default."""
        with self._lock:
            self._set_status(CollectorStatus.AUTHENTICATING)
            self._do_authenticate()

    def connect(self) -> None:
        """Establish connection to data source. No-op by default."""
        with self._lock:
            self._set_status(CollectorStatus.CONNECTING)
            self._do_connect()

    def run(self) -> list[Observation]:
        """
        Full pipeline: collect → validate → normalise → publish.

        Respects retry policy, circuit breaker, and rate limiter.
        Returns the list of observations published this run.
        """
        if not self.config.enabled:
            return []

        if self._status == CollectorStatus.STOPPED:
            raise CollectorShutdownError(self.name)

        if not self.config.circuit_breaker.allow_request():
            raise CollectorCircuitOpenError(
                f"Circuit open for '{self.name}'", collector_name=self.name)

        if not self.config.rate_limiter.allow():
            raise CollectorRateLimitError(
                f"Rate limit exceeded for '{self.name}'", collector_name=self.name)

        attempt   = 0
        last_exc: Optional[Exception] = None

        while attempt <= self.config.retry_policy.max_retries:
            attempt += 1
            try:
                return self._execute_pipeline()
            except (CollectorCircuitOpenError, CollectorShutdownError):
                raise
            except Exception as exc:
                last_exc                    = exc
                self._stats.total_errors   += 1
                self._stats.last_error      = str(exc)
                self._stats.last_error_at   = time.time()
                self.config.circuit_breaker.record_failure()
                self._set_status(CollectorStatus.ERROR)
                self._log.warning(
                    "Attempt %d/%d failed [%s]: %s",
                    attempt, self.config.retry_policy.max_retries + 1, self.name, exc,
                )
                if attempt <= self.config.retry_policy.max_retries:
                    delay = self.config.retry_policy.delay(attempt)
                    self._stats.total_retries += 1
                    if delay > 0:
                        time.sleep(delay)

        raise CollectorRetryExhaustedError(
            f"All {self.config.retry_policy.max_retries} retries exhausted for '{self.name}'",
            collector_name = self.name,
            attempts       = attempt,
        )

    def health_check(self) -> dict[str, Any]:
        """Return structured health data for this collector."""
        return {
            "name":           self.name,
            "status":         self._status.value,
            "stats":          self._stats.to_dict(),
            "circuit":        self.config.circuit_breaker.to_dict(),
            "rate_remaining": self.config.rate_limiter.remaining,
            "uptime_s":       round(time.time() - self._start_time, 1) if self._start_time else 0,
        }

    def pause(self) -> None:
        with self._lock:
            if self._status not in (CollectorStatus.STOPPED, CollectorStatus.STOPPING):
                self._set_status(CollectorStatus.PAUSED)

    def resume(self) -> None:
        with self._lock:
            if self._status == CollectorStatus.PAUSED:
                self._set_status(CollectorStatus.IDLE)

    def shutdown(self) -> None:
        """Gracefully stop the collector."""
        with self._lock:
            if self._status in (CollectorStatus.STOPPED, CollectorStatus.STOPPING):
                return
            self._set_status(CollectorStatus.STOPPING)
            try:
                self._do_shutdown()
            except Exception as exc:
                self._log.error("Shutdown error [%s]: %s", self.name, exc)
            finally:
                self._set_status(CollectorStatus.STOPPED)
                self._log.info("Stopped: %s", self.name)

    def add_hook(self, hook: CollectorHook) -> None:
        """Register a post-collection hook: ``hook(collector, observations)``."""
        self._hooks.append(hook)

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def _do_collect(self) -> Any:
        """Fetch raw data from the source. Returns raw payload (any type)."""

    @abstractmethod
    def _do_normalise(self, raw: Any) -> list[Observation]:
        """Convert raw payload to a list of Observation objects."""

    # ── Overridable lifecycle hooks ───────────────────────────────────────────

    def _do_initialise(self)  -> None: pass
    def _do_authenticate(self) -> None: pass
    def _do_connect(self)      -> None: pass
    def _do_shutdown(self)     -> None: pass

    def _do_validate(self, observations: list[Observation]) -> list[Observation]:
        """Filter out observations with None content. Override for custom rules."""
        valid = [o for o in observations if o.content is not None]
        self._stats.total_skipped += len(observations) - len(valid)
        return valid

    # ── Internal pipeline ─────────────────────────────────────────────────────

    def _execute_pipeline(self) -> list[Observation]:
        t0 = time.perf_counter()
        self._set_status(CollectorStatus.COLLECTING)
        self._stats.last_run_at = time.time()
        self._stats.run_count  += 1
        self._stats.is_running  = True

        try:
            raw          = self._do_collect()
            observations = self._do_normalise(raw)
            observations = self._do_validate(observations)
            self._publish(observations)
            self.config.circuit_breaker.record_success()
            self._stats.total_collected += len(observations)
            self._stats.last_success_at  = time.time()
            self._set_status(CollectorStatus.IDLE)
            elapsed = (time.perf_counter() - t0) * 1_000.0
            self._log.debug(
                "Collected %d observations in %.1f ms [%s]",
                len(observations), elapsed, self.name,
            )
            return observations
        finally:
            self._stats.is_running = False

    def _publish(self, observations: list[Observation]) -> None:
        """Submit observations to the ObservationEngine and call hooks."""
        try:
            from ..observation_engine import get_observation_engine
            engine = get_observation_engine()
            if engine._initialized:
                for obs in observations:
                    engine.submit(obs, actor=SYSTEM_OBSERVER)
                    self._stats.total_published += 1
        except Exception as exc:
            self._log.debug("Engine publish skipped: %s", exc)

        for hook in self._hooks:
            try:
                hook(self, observations)
            except Exception as exc:
                self._log.warning("Hook error [%s]: %s", self.name, exc)

    def _set_status(self, status: CollectorStatus) -> None:
        self._status       = status
        self._stats.status = status

    # ── Convenience builders ──────────────────────────────────────────────────

    def _make_source_info(
        self,
        instrument: str = "",
        exchange:   str = "",
        batch_id:   str = "",
    ) -> ObservationSourceInfo:
        return ObservationSourceInfo(
            source       = self.config.source,
            source_name  = self.config.name,
            feed_name    = self.config.name,
            instrument   = instrument,
            exchange     = exchange,
            batch_id     = batch_id,
            submitted_by = SYSTEM_OBSERVER,
        )

    def _make_observation(
        self,
        content:    Any,
        title:      str   = "",
        instrument: str   = "",
        exchange:   str   = "",
        confidence: float = 0.80,
    ) -> Observation:
        from ..observation_factory import get_observation_factory
        return get_observation_factory().create(
            content    = content,
            obs_type   = self.config.obs_type,
            title      = title or f"{self.config.name}: {instrument}",
            source     = self.config.source,
            confidence = confidence,
            instrument = instrument,
            exchange   = exchange,
            actor      = SYSTEM_OBSERVER,
        )

    # ── Checkpointing ─────────────────────────────────────────────────────────

    def save_checkpoint(self, data: dict[str, Any]) -> None:
        """Persist progress checkpoint for crash recovery."""
        with self._lock:
            self._checkpoint.update(data)

    def load_checkpoint(self) -> dict[str, Any]:
        """Load the last saved checkpoint."""
        with self._lock:
            return dict(self._checkpoint)

    def clear_checkpoint(self) -> None:
        with self._lock:
            self._checkpoint.clear()

    # ── Collect alias ─────────────────────────────────────────────────────────

    def collect(self) -> list[Observation]:
        """Alias for ``run()`` — legacy compatibility."""
        return self.run()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r} status={self._status.value!r}>"
