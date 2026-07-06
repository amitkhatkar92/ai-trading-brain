"""
iios/infrastructure/infrastructure_models.py
=============================================
Shared dataclass models used across the IIOS Infrastructure Layer.
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .infrastructure_constants import (
    LifecycleScope,
    EventPriority,
    JobType,
    JobStatus,
    SerializationFormat,
    StorageFormat,
    CompressionFormat,
    HttpMethod,
)

__all__ = [
    "ServiceDescriptor",
    "ResolvedService",
    "EventEnvelope",
    "DeadLetterEntry",
    "CacheEntry",
    "CacheStats",
    "JobDefinition",
    "JobExecution",
    "StorageMetadata",
    "TransactionContext",
    "HttpRequest",
    "HttpResponse",
    "RetryPolicy",
    "CircuitBreakerState",
    "RateLimitState",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Dependency Injection models
# ---------------------------------------------------------------------------


@dataclass
class ServiceDescriptor:
    """Describes a registered service binding."""

    service_key: str
    implementation: Any
    scope: str = LifecycleScope.SINGLETON.value
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    registered_at: str = field(default_factory=_now_iso)
    singleton_instance: Any = field(default=None, repr=False)

    @property
    def is_singleton(self) -> bool:
        return self.scope == LifecycleScope.SINGLETON.value

    @property
    def is_scoped(self) -> bool:
        return self.scope == LifecycleScope.SCOPED.value

    @property
    def is_transient(self) -> bool:
        return self.scope == LifecycleScope.TRANSIENT.value


@dataclass
class ResolvedService:
    """Result of resolving a service from the container."""

    service_key: str
    instance: Any
    scope: str
    resolved_at: str = field(default_factory=_now_iso)
    resolution_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Event Bus models
# ---------------------------------------------------------------------------


@dataclass
class EventEnvelope:
    """Wraps any event for transport through the event bus."""

    event_type: str
    payload: Any
    event_id: str = field(default_factory=_new_id)
    correlation_id: str = field(default_factory=_new_id)
    source: str = ""
    priority: int = EventPriority.NORMAL.value
    timestamp: str = field(default_factory=_now_iso)
    timestamp_mono: float = field(default_factory=time.monotonic)
    metadata: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3

    @property
    def is_retryable(self) -> bool:
        return self.retry_count < self.max_retries

    # Needed for priority queue comparison
    def __lt__(self, other: "EventEnvelope") -> bool:
        return self.priority > other.priority  # higher priority = processed first


@dataclass
class DeadLetterEntry:
    """An event that failed all delivery attempts."""

    envelope: EventEnvelope
    failure_reason: str
    failed_at: str = field(default_factory=_now_iso)
    subscriber: str = ""


# ---------------------------------------------------------------------------
# Cache models
# ---------------------------------------------------------------------------


@dataclass
class CacheEntry:
    """A single item stored in the cache."""

    key: str
    value: Any
    created_at: float = field(default_factory=time.monotonic)
    expires_at: Optional[float] = None      # monotonic timestamp
    access_count: int = 0
    last_accessed: float = field(default_factory=time.monotonic)
    size_bytes: int = 0

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.monotonic() >= self.expires_at

    def touch(self) -> None:
        self.access_count += 1
        self.last_accessed = time.monotonic()


@dataclass
class CacheStats:
    """Runtime statistics for a cache instance."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    current_size: int = 0
    max_size: int = 0
    total_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def reset(self) -> None:
        self.hits = self.misses = self.evictions = self.expirations = 0


# ---------------------------------------------------------------------------
# Scheduler models
# ---------------------------------------------------------------------------


@dataclass
class JobDefinition:
    """Describes a scheduled job."""

    job_id: str = field(default_factory=_new_id)
    name: str = ""
    job_type: str = JobType.INTERVAL.value
    callable_path: str = ""        # "module.func" for serialisation
    schedule: str = ""             # cron expr or interval seconds
    priority: int = 50
    max_retries: int = 3
    retry_backoff: float = 1.0
    timeout_seconds: Optional[float] = None
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)
    tags: list[str] = field(default_factory=list)


@dataclass
class JobExecution:
    """Record of a single job run."""

    execution_id: str = field(default_factory=_new_id)
    job_id: str = ""
    status: str = JobStatus.PENDING.value
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_ms: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0

    def start(self) -> None:
        self.status = JobStatus.RUNNING.value
        self.started_at = _now_iso()

    def succeed(self, result: Any = None) -> None:
        self.status = JobStatus.SUCCEEDED.value
        self.finished_at = _now_iso()
        self.result = result

    def fail(self, error: str) -> None:
        self.status = JobStatus.FAILED.value
        self.finished_at = _now_iso()
        self.error = error


# ---------------------------------------------------------------------------
# Storage models
# ---------------------------------------------------------------------------


@dataclass
class StorageMetadata:
    """Metadata for a stored object."""

    key: str
    storage_format: str = StorageFormat.JSON.value
    compression: str = CompressionFormat.NONE.value
    size_bytes: int = 0
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    content_type: str = "application/json"
    checksum: str = ""
    tags: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Repository / UoW models
# ---------------------------------------------------------------------------


@dataclass
class TransactionContext:
    """Context for an active database transaction."""

    transaction_id: str = field(default_factory=_new_id)
    started_at: str = field(default_factory=_now_iso)
    committed: bool = False
    rolled_back: bool = False
    operations: list[dict[str, Any]] = field(default_factory=list)
    savepoints: list[str] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return not self.committed and not self.rolled_back


# ---------------------------------------------------------------------------
# Network models
# ---------------------------------------------------------------------------


@dataclass
class HttpRequest:
    """An outbound HTTP request."""

    url: str
    method: str = HttpMethod.GET.value
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    body: Optional[bytes] = None
    timeout: float = 30.0
    request_id: str = field(default_factory=_new_id)


@dataclass
class HttpResponse:
    """An HTTP response."""

    status_code: int
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    request_id: str = ""
    duration_ms: float = 0.0
    url: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        import json
        return json.loads(self.body)


# ---------------------------------------------------------------------------
# Utilities models
# ---------------------------------------------------------------------------


@dataclass
class RetryPolicy:
    """Configuration for retry behaviour."""

    max_attempts: int = 3
    backoff_base: float = 0.5       # seconds
    backoff_max: float = 30.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    exceptions: tuple = field(default_factory=lambda: (Exception,))

    def backoff_for(self, attempt: int) -> float:
        import random
        delay = min(self.backoff_base * (self.backoff_multiplier ** attempt), self.backoff_max)
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        return delay


@dataclass
class CircuitBreakerState:
    """Tracks the state of a circuit breaker."""

    name: str
    failure_count: int = 0
    success_count: int = 0
    last_failure_at: Optional[float] = None
    opened_at: Optional[float] = None
    state: str = "closed"      # closed | open | half_open
    threshold: int = 5
    reset_timeout: float = 60.0

    @property
    def is_open(self) -> bool:
        return self.state == "open"

    @property
    def is_closed(self) -> bool:
        return self.state == "closed"

    @property
    def is_half_open(self) -> bool:
        return self.state == "half_open"


@dataclass
class RateLimitState:
    """Sliding window rate limit tracker."""

    name: str
    limit: int                  # max calls per window
    window_seconds: float       # window size
    calls: list[float] = field(default_factory=list)   # monotonic timestamps

    @property
    def current_count(self) -> int:
        self._evict()
        return len(self.calls)

    def _evict(self) -> None:
        cutoff = time.monotonic() - self.window_seconds
        self.calls = [t for t in self.calls if t >= cutoff]

    def is_allowed(self) -> bool:
        self._evict()
        return len(self.calls) < self.limit

    def record(self) -> None:
        self.calls.append(time.monotonic())
