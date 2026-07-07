"""
iios/observation/collectors/__init__.py
=======================================
Public surface of the Observation Collection Framework.
"""
from __future__ import annotations

# ── Constants & Exceptions ────────────────────────────────────────────────────
from .collector_constants import (
    CollectorStatus, CollectorCategory, RetryStrategy,
    ScheduleType, CircuitBreakerState, ExecutionMode, LifecycleStage,
    DEFAULT_TIMEOUT_S, DEFAULT_MAX_RETRIES, DEFAULT_POLL_INTERVAL_S,
    DEFAULT_BATCH_SIZE, MAX_PARALLEL_COLLECTORS,
    COLLECTOR_NAMESPACE, SYSTEM_COLLECTOR,
)
from .collector_exceptions import (
    CollectorError, CollectorConfigError, CollectorAuthError,
    CollectorConnectionError, CollectorTimeoutError,
    CollectorRetryExhaustedError, CollectorCircuitOpenError,
    CollectorRateLimitError, CollectorValidationError,
    CollectorScheduleError, CollectorExecutionError,
    CollectorNotFoundError, CollectorAlreadyRegisteredError,
    CollectorShutdownError, CollectorNormalisationError,
    CollectorCheckpointError,
)

# ── Base framework ────────────────────────────────────────────────────────────
from .base_collector import (
    RetryPolicy, CircuitBreaker, RateLimiter,
    CollectorConfig, CollectorStats, BaseCollector, CollectorHook,
)
from .sync_collector        import SyncCollector
from .async_collector       import AsyncCollector
from .stream_collector      import StreamCollector
from .batch_collector       import BatchCollector, BatchCheckpoint
from .scheduled_collector   import ScheduledCollector, ScheduleConfig
from .event_collector       import EventCollector

# ── Infrastructure ────────────────────────────────────────────────────────────
from .collector_context     import (
    CollectorContext, get_collector_context, reset_collector_context,
    collector_operation, current_collector_name, current_run_id,
)
from .collector_metrics     import (
    RunRecord, MetricsSummary, CollectorMetrics,
    get_collector_metrics, reset_collector_metrics,
)
from .collector_registry    import (
    CollectorRegistry, get_collector_registry, reset_collector_registry,
)
from .collector_factory     import (
    CollectorFactory, get_collector_factory, reset_collector_factory,
)
from .collector_scheduler   import (
    ScheduledJob, CollectorScheduler, get_collector_scheduler, reset_collector_scheduler,
)
from .collector_executor    import (
    ExecutionResult, CollectorExecutor, get_collector_executor, reset_collector_executor,
)
from .collector_monitor     import (
    HealthReport, CollectorMonitor, get_collector_monitor, reset_collector_monitor,
)
from .collector_manager     import (
    CollectorManager, get_collector_manager, reset_collector_manager,
)

