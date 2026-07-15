"""iios/common/errors/__init__.py
IIOS Common Error Handling Framework — public API.
"""
from __future__ import annotations

from iios.common.errors.exceptions import (
    IIOSError,
    ConfigurationError,
    ValidationError,
    WorkflowError,
    EngineError,
    DependencyError,
    IntegrationError,
    TimeoutError,
    RecoveryError,
    SecurityError,
)

from iios.common.errors.error_context import (
    ErrorContext,
    get_error_context,
    set_error_context,
    clear_error_context,
    bind_error_context,
    current_context_dict,
)

from iios.common.errors.retry_policy import (
    RetryDecision,
    RetryClassifier,
    RetryPolicy,
    NoRetry,
    FixedRetry,
    ExponentialBackoff,
    ExponentialBackoffWithJitter,
)

from iios.common.errors.recovery_engine import (
    RecoveryStrategy,
    RecoveryResult,
    CircuitBreakerHook,
    DeadLetterHook,
    RecoveryEngine,
)

from iios.common.errors.failure_metrics import (
    EngineMetricsSnapshot,
    FailureMetricsSnapshot,
    FailureTrendEntry,
    FailureTracker,
    get_failure_tracker,
    reset_failure_tracker,
)

from iios.common.errors.error_manager import (
    ErrorHandler,
    ErrorManager,
    get_error_manager,
    reset_error_manager,
)

__all__ = [
    # Exceptions
    "IIOSError",
    "ConfigurationError",
    "ValidationError",
    "WorkflowError",
    "EngineError",
    "DependencyError",
    "IntegrationError",
    "TimeoutError",
    "RecoveryError",
    "SecurityError",
    # Error context
    "ErrorContext",
    "get_error_context",
    "set_error_context",
    "clear_error_context",
    "bind_error_context",
    "current_context_dict",
    # Retry
    "RetryDecision",
    "RetryClassifier",
    "RetryPolicy",
    "NoRetry",
    "FixedRetry",
    "ExponentialBackoff",
    "ExponentialBackoffWithJitter",
    # Recovery
    "RecoveryStrategy",
    "RecoveryResult",
    "CircuitBreakerHook",
    "DeadLetterHook",
    "RecoveryEngine",
    # Metrics
    "EngineMetricsSnapshot",
    "FailureMetricsSnapshot",
    "FailureTrendEntry",
    "FailureTracker",
    "get_failure_tracker",
    "reset_failure_tracker",
    # Manager
    "ErrorHandler",
    "ErrorManager",
    "get_error_manager",
    "reset_error_manager",
]
