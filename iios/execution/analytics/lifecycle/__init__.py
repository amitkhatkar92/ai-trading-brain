"""
iios/execution/analytics/lifecycle/__init__.py
==============================================
Public API for the C8 Execution Analytics Lifecycle subsystem.

Primary entry point: AnalyticsLifecycle

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

# ── Primary entry point ───────────────────────────────────────────────────────
from .analytics_lifecycle import AnalyticsLifecycle  # noqa: F401

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (  # noqa: F401
    LIFECYCLE_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    VERSION,
    SCHEMA_VERSION,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_TRANSITIONS,
    ACTOR_LIFECYCLE,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    ACTOR_ANALYTICS,
    ACTOR_SCHEDULER,
    ACTIVE_STATES,
    TERMINAL_STATES,
    IMMUTABLE_STATES,
    SUCCESS_STATES,
    VALID_TRANSITIONS,
    AnalyticsState,
    AnalyticsScope,
    AnalyticsMode,
    AnalyticsTrigger,
    AnalyticsEventType,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (  # noqa: F401
    AnalyticsError,
    AnalyticsNotRunningError,
    AnalyticsSessionNotFoundError,
    AnalyticsInvalidTransitionError,
    AnalyticsValidationError,
    AnalyticsSessionAlreadyExistsError,
    AnalyticsSessionTerminalError,
    AnalyticsHistoryError,
)

# ── Domain objects ────────────────────────────────────────────────────────────
from .analytics_session import AnalyticsSession  # noqa: F401
from .analytics_state import (  # noqa: F401
    AnalyticsStateRecord,
    can_transition,
)
from .analytics_transition import (  # noqa: F401
    AnalyticsTransition,
    make_analytics_transition,
)
from .analytics_context import (  # noqa: F401
    AnalyticsContext,
    make_analytics_context,
)
from .analytics_metadata import (  # noqa: F401
    AnalyticsMetadata,
    make_analytics_metadata,
)

# ── Events ────────────────────────────────────────────────────────────────────
from .analytics_events import (  # noqa: F401
    AnalyticsEvent,
    make_analytics_created,
    make_analytics_initialized,
    make_analytics_started,
    make_analytics_paused,
    make_analytics_resumed,
    make_analytics_completed,
    make_analytics_failed,
    make_analytics_archived,
)

# ── Services ──────────────────────────────────────────────────────────────────
from .analytics_statistics import AnalyticsStatistics  # noqa: F401
from .analytics_history import AnalyticsHistory  # noqa: F401
from .analytics_registry import AnalyticsRegistry  # noqa: F401
from .analytics_factory import AnalyticsFactory  # noqa: F401
from .analytics_validation import (  # noqa: F401
    AnalyticsValidationResult,
    AnalyticsValidator,
)

__all__ = [
    # Primary
    "AnalyticsLifecycle",
    # Constants
    "LIFECYCLE_SYSTEM_ID", "REGISTRY_SYSTEM_ID", "FACTORY_SYSTEM_ID",
    "VERSION", "SCHEMA_VERSION",
    "DEFAULT_MAX_SESSIONS", "DEFAULT_MAX_HISTORY", "DEFAULT_MAX_TRANSITIONS",
    "ACTOR_LIFECYCLE", "ACTOR_OPERATOR", "ACTOR_SYSTEM",
    "ACTOR_ANALYTICS", "ACTOR_SCHEDULER",
    "ACTIVE_STATES", "TERMINAL_STATES", "IMMUTABLE_STATES",
    "SUCCESS_STATES", "VALID_TRANSITIONS",
    "AnalyticsState", "AnalyticsScope", "AnalyticsMode",
    "AnalyticsTrigger", "AnalyticsEventType",
    # Exceptions
    "AnalyticsError", "AnalyticsNotRunningError",
    "AnalyticsSessionNotFoundError", "AnalyticsInvalidTransitionError",
    "AnalyticsValidationError", "AnalyticsSessionAlreadyExistsError",
    "AnalyticsSessionTerminalError", "AnalyticsHistoryError",
    # Domain objects
    "AnalyticsSession",
    "AnalyticsStateRecord", "can_transition",
    "AnalyticsTransition", "make_analytics_transition",
    "AnalyticsContext", "make_analytics_context",
    "AnalyticsMetadata", "make_analytics_metadata",
    # Events
    "AnalyticsEvent",
    "make_analytics_created", "make_analytics_initialized",
    "make_analytics_started", "make_analytics_paused",
    "make_analytics_resumed", "make_analytics_completed",
    "make_analytics_failed", "make_analytics_archived",
    # Services
    "AnalyticsStatistics", "AnalyticsHistory",
    "AnalyticsRegistry", "AnalyticsFactory",
    "AnalyticsValidationResult", "AnalyticsValidator",
]
