"""iios/execution/recovery/lifecycle/__init__.py
==================================================
Public surface for C7 Execution Recovery Lifecycle.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

# ── Primary entry point ───────────────────────────────────────────────────────
from .recovery_lifecycle import RecoveryLifecycle  # noqa: F401

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
    ACTOR_POLICY,
    ACTOR_WATCHDOG,
    RecoveryState,
    RecoveryTrigger,
    RecoveryEventType,
    VALID_TRANSITIONS,
    ACTIVE_STATES,
    TERMINAL_STATES,
    IMMUTABLE_STATES,
    SUCCESS_STATES,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (  # noqa: F401
    RecoveryError,
    RecoveryNotRunningError,
    RecoveryAlreadyRunningError,
    RecoverySessionNotFoundError,
    RecoveryInvalidTransitionError,
    RecoveryValidationError,
    RecoverySessionAlreadyExistsError,
    RecoveryHistoryError,
    RecoverySessionTerminalError,
)

# ── Domain objects ────────────────────────────────────────────────────────────
from .recovery_context import RecoveryContext, make_recovery_context  # noqa: F401
from .recovery_metadata import RecoveryMetadata, make_recovery_metadata  # noqa: F401
from .recovery_session import RecoverySession  # noqa: F401
from .recovery_state import RecoveryStateRecord, can_transition  # noqa: F401
from .recovery_transition import RecoveryTransition, make_recovery_transition  # noqa: F401
from .recovery_events import (  # noqa: F401
    RecoveryEvent,
    make_recovery_created,
    make_recovery_initialized,
    make_recovery_detecting,
    make_recovery_assessing,
    make_recovery_ready,
    make_recovery_started,
    make_recovery_verifying,
    make_recovery_completed,
    make_recovery_failed,
    make_recovery_aborted,
    make_recovery_archived,
)

# ── Supporting components ─────────────────────────────────────────────────────
from .recovery_validation import RecoveryValidationResult, RecoveryValidator  # noqa: F401
from .recovery_statistics import RecoveryStatistics  # noqa: F401
from .recovery_history import RecoveryHistory  # noqa: F401
from .recovery_registry import RecoveryRegistry  # noqa: F401
from .recovery_factory import RecoveryFactory  # noqa: F401

__all__ = [
    # Primary entry point
    "RecoveryLifecycle",
    # Constants
    "LIFECYCLE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_TRANSITIONS",
    "ACTOR_LIFECYCLE",
    "ACTOR_OPERATOR",
    "ACTOR_SYSTEM",
    "ACTOR_POLICY",
    "ACTOR_WATCHDOG",
    "RecoveryState",
    "RecoveryTrigger",
    "RecoveryEventType",
    "VALID_TRANSITIONS",
    "ACTIVE_STATES",
    "TERMINAL_STATES",
    "IMMUTABLE_STATES",
    "SUCCESS_STATES",
    # Exceptions
    "RecoveryError",
    "RecoveryNotRunningError",
    "RecoveryAlreadyRunningError",
    "RecoverySessionNotFoundError",
    "RecoveryInvalidTransitionError",
    "RecoveryValidationError",
    "RecoverySessionAlreadyExistsError",
    "RecoveryHistoryError",
    "RecoverySessionTerminalError",
    # Domain objects
    "RecoveryContext",
    "make_recovery_context",
    "RecoveryMetadata",
    "make_recovery_metadata",
    "RecoverySession",
    "RecoveryStateRecord",
    "can_transition",
    "RecoveryTransition",
    "make_recovery_transition",
    "RecoveryEvent",
    "make_recovery_created",
    "make_recovery_initialized",
    "make_recovery_detecting",
    "make_recovery_assessing",
    "make_recovery_ready",
    "make_recovery_started",
    "make_recovery_verifying",
    "make_recovery_completed",
    "make_recovery_failed",
    "make_recovery_aborted",
    "make_recovery_archived",
    # Supporting components
    "RecoveryValidationResult",
    "RecoveryValidator",
    "RecoveryStatistics",
    "RecoveryHistory",
    "RecoveryRegistry",
    "RecoveryFactory",
]
