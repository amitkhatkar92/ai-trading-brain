"""
iios/monitoring/monitoring_models.py
======================================
Dataclass models for the IIOS Logging & Monitoring Framework.

All models are serializable to dict/JSON via ``dataclasses.asdict()``.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .monitoring_constants import (
    AlertLevel,
    AlertStatus,
    AuditAction,
    CheckCategory,
    EventCategory,
    HealthStatus,
    MetricType,
    TraceStatus,
)

__all__ = [
    "LogRecord",
    "AuditRecord",
    "EventRecord",
    "PerformanceRecord",
    "ErrorRecord",
    "MetricPoint",
    "MetricSeries",
    "TraceSpan",
    "TraceContext",
    "HealthCheckResult",
    "SystemHealthReport",
    "AlertEvent",
    "HeartbeatRecord",
    "DiagnosticSnapshot",
    "NotificationRecord",
    "MonitoringContext",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ms() -> float:
    return time.monotonic() * 1000


# ---------------------------------------------------------------------------
# Logging models
# ---------------------------------------------------------------------------


@dataclass
class LogRecord:
    """A single structured log entry."""

    level: str
    message: str
    logger_name: str
    timestamp: str = field(default_factory=_now_iso)
    timestamp_mono: float = field(default_factory=time.monotonic)
    # Context fields
    correlation_id: str = ""
    request_id: str = ""
    session_id: str = ""
    execution_id: str = ""
    trace_id: str = ""
    span_id: str = ""
    # Identity
    module: str = ""
    function: str = ""
    line: int = 0
    thread_id: int = 0
    thread_name: str = ""
    process_id: int = 0
    # IIOS layer
    layer: str = ""
    component: str = ""
    # Payload
    extra: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    stack_trace: Optional[str] = None


@dataclass
class AuditRecord:
    """An immutable audit trail entry."""

    action: str                    # AuditAction value
    actor: str                     # Who performed the action
    resource: str                  # What was acted upon
    timestamp: str = field(default_factory=_now_iso)
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    outcome: str = "success"       # success | failure
    reason: str = ""
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    ip_address: str = ""
    session_id: str = ""
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventRecord:
    """A business / lifecycle event."""

    category: str                   # EventCategory value
    event_type: str
    description: str
    timestamp: str = field(default_factory=_now_iso)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    component: str = ""
    layer: str = ""
    correlation_id: str = ""
    severity: str = "INFO"
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceRecord:
    """Records one timed execution."""

    operation: str
    duration_ms: float
    timestamp: str = field(default_factory=_now_iso)
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    component: str = ""
    layer: str = ""
    success: bool = True
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """Tracks a single error occurrence with deduplication support."""

    error_type: str
    message: str
    timestamp: str = field(default_factory=_now_iso)
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    component: str = ""
    layer: str = ""
    stack_trace: str = ""
    correlation_id: str = ""
    fingerprint: str = ""          # For deduplication
    count: int = 1
    first_seen: str = field(default_factory=_now_iso)
    last_seen: str = field(default_factory=_now_iso)
    context: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Metrics models
# ---------------------------------------------------------------------------


@dataclass
class MetricPoint:
    """A single metric observation."""

    name: str
    value: float
    metric_type: str               # MetricType value
    timestamp: float = field(default_factory=time.monotonic)
    timestamp_iso: str = field(default_factory=_now_iso)
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """A named metric with its history of observations."""

    name: str
    metric_type: str
    description: str = ""
    unit: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    points: list[MetricPoint] = field(default_factory=list)
    # Running aggregates (updated on each new point)
    count: int = 0
    total: float = 0.0
    minimum: float = float("inf")
    maximum: float = float("-inf")
    last_value: float = 0.0

    def record(self, value: float, labels: Optional[dict[str, str]] = None) -> None:
        """Record a new observation."""
        pt = MetricPoint(
            name=self.name,
            value=value,
            metric_type=self.metric_type,
            labels=labels or self.labels,
        )
        self.points.append(pt)
        self.count += 1
        self.total += value
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)
        self.last_value = value

    @property
    def average(self) -> float:
        return self.total / self.count if self.count > 0 else 0.0


# ---------------------------------------------------------------------------
# Tracing models
# ---------------------------------------------------------------------------


@dataclass
class TraceSpan:
    """One span within a distributed trace."""

    operation: str
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None
    status: str = TraceStatus.STARTED.value
    start_time: float = field(default_factory=time.monotonic)
    start_iso: str = field(default_factory=_now_iso)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    component: str = ""
    layer: str = ""
    error: Optional[str] = None
    tags: dict[str, str] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)

    def finish(self, error: Optional[str] = None) -> None:
        self.end_time = time.monotonic()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = TraceStatus.FAILED.value if error else TraceStatus.COMPLETED.value
        if error:
            self.error = error

    def add_log(self, message: str) -> None:
        self.logs.append(f"{_now_iso()} {message}")

    def set_tag(self, key: str, value: str) -> None:
        self.tags[key] = value


@dataclass
class TraceContext:
    """Groups all spans belonging to one logical trace."""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: str = ""
    status: str = TraceStatus.STARTED.value
    start_time: float = field(default_factory=time.monotonic)
    start_iso: str = field(default_factory=_now_iso)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    spans: list[TraceSpan] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def span_count(self) -> int:
        return len(self.spans)

    def finish(self, error: Optional[str] = None) -> None:
        self.end_time = time.monotonic()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = TraceStatus.FAILED.value if error else TraceStatus.COMPLETED.value


# ---------------------------------------------------------------------------
# Health models
# ---------------------------------------------------------------------------


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: str                        # HealthStatus value
    category: str = CheckCategory.CUSTOM.value
    message: str = ""
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=_now_iso)
    details: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY.value

    @property
    def is_degraded(self) -> bool:
        return self.status == HealthStatus.DEGRADED.value

    @property
    def is_unhealthy(self) -> bool:
        return self.status == HealthStatus.UNHEALTHY.value


@dataclass
class SystemHealthReport:
    """Aggregated health report for the entire IIOS system."""

    overall_status: str = HealthStatus.UNKNOWN.value
    timestamp: str = field(default_factory=_now_iso)
    checks: dict[str, HealthCheckResult] = field(default_factory=dict)
    summary: str = ""
    uptime_seconds: float = 0.0

    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.checks.values() if c.is_healthy)

    @property
    def degraded_count(self) -> int:
        return sum(1 for c in self.checks.values() if c.is_degraded)

    @property
    def unhealthy_count(self) -> int:
        return sum(1 for c in self.checks.values() if c.is_unhealthy)

    def compute_overall(self) -> None:
        """Set overall_status based on individual check results."""
        if not self.checks:
            self.overall_status = HealthStatus.UNKNOWN.value
        elif self.unhealthy_count > 0:
            self.overall_status = HealthStatus.UNHEALTHY.value
        elif self.degraded_count > 0:
            self.overall_status = HealthStatus.DEGRADED.value
        else:
            self.overall_status = HealthStatus.HEALTHY.value


# ---------------------------------------------------------------------------
# Alert models
# ---------------------------------------------------------------------------


@dataclass
class AlertEvent:
    """An alert generated by the monitoring framework."""

    level: str                         # AlertLevel value
    title: str
    message: str
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = AlertStatus.OPEN.value
    timestamp: str = field(default_factory=_now_iso)
    component: str = ""
    layer: str = ""
    metric_name: str = ""
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    correlation_id: str = ""
    tags: dict[str, str] = field(default_factory=dict)
    resolved_at: Optional[str] = None
    suppressed_until: Optional[float] = None   # monotonic timestamp

    @property
    def is_critical(self) -> bool:
        return self.level == AlertLevel.CRITICAL.value

    @property
    def fingerprint(self) -> str:
        """Deduplication key."""
        return f"{self.level}:{self.component}:{self.title}"


# ---------------------------------------------------------------------------
# Heartbeat model
# ---------------------------------------------------------------------------


@dataclass
class HeartbeatRecord:
    """Periodic health signal from a subsystem."""

    component: str
    timestamp: str = field(default_factory=_now_iso)
    timestamp_mono: float = field(default_factory=time.monotonic)
    status: str = HealthStatus.HEALTHY.value
    sequence: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Diagnostic model
# ---------------------------------------------------------------------------


@dataclass
class DiagnosticSnapshot:
    """Point-in-time system resource snapshot."""

    timestamp: str = field(default_factory=_now_iso)
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # CPU
    cpu_percent: float = 0.0
    cpu_count: int = 0
    # Memory
    mem_total_mb: float = 0.0
    mem_used_mb: float = 0.0
    mem_available_mb: float = 0.0
    mem_percent: float = 0.0
    # Disk
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_free_gb: float = 0.0
    disk_percent: float = 0.0
    # Process
    process_cpu_percent: float = 0.0
    process_mem_mb: float = 0.0
    process_threads: int = 0
    process_open_files: int = 0
    # Python
    python_version: str = ""
    gc_collections: tuple[int, int, int] = (0, 0, 0)
    # Custom
    extras: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Notification record
# ---------------------------------------------------------------------------


@dataclass
class NotificationRecord:
    """Record of a notification delivery attempt."""

    channel: str
    recipient: str
    subject: str
    body: str
    timestamp: str = field(default_factory=_now_iso)
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    alert_id: str = ""
    success: bool = True
    error: Optional[str] = None
    retries: int = 0


# ---------------------------------------------------------------------------
# Monitoring context (thread-local propagation)
# ---------------------------------------------------------------------------


@dataclass
class MonitoringContext:
    """Propagation context attached to one operation/request."""

    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    session_id: str = ""
    execution_id: str = ""
    trace_id: str = ""
    span_id: str = ""
    component: str = ""
    layer: str = ""
    user: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
