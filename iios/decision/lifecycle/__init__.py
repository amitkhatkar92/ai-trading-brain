"""
iios.decision.lifecycle
========================
Institutional Decision Lifecycle — C9 M1.

Primary public entry point
--------------------------
:class:`DecisionLifecycle` is the ONLY interface external callers use.

    >>> from iios.decision.lifecycle import DecisionLifecycle
    >>> lc = DecisionLifecycle()
    >>> lc.start()
    >>> session = lc.create("d-001")
    >>> lc.initialize(session.session_id)
    >>> lc.collect(session.session_id)
    >>> lc.evaluate(session.session_id)
    >>> lc.ready(session.session_id)
    >>> lc.activate(session.session_id)
    >>> lc.complete(session.session_id)
    >>> lc.archive(session.session_id)
    >>> lc.stop()

This module manages decision state transitions ONLY.
It performs NO policy evaluation, NO optimization, NO execution.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Primary public interface
# ---------------------------------------------------------------------------
from .decision_lifecycle import DecisionLifecycle

# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------
from .decision_session    import DecisionSession
from .decision_context    import DecisionContext
from .decision_metadata   import DecisionMetadata

# ---------------------------------------------------------------------------
# State machine types
# ---------------------------------------------------------------------------
from .decision_state      import DecisionStateRecord, can_transition
from .decision_transition import DecisionTransition, make_transition

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
from .decision_events import (
    DecisionEvent,
    make_decision_created,
    make_decision_initialized,
    make_decision_started,
    make_decision_paused,
    make_decision_resumed,
    make_decision_completed,
    make_decision_failed,
    make_decision_archived,
)

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------
from .decision_registry   import DecisionRegistry
from .decision_factory    import DecisionFactory
from .decision_history    import DecisionHistory
from .decision_statistics import DecisionStatistics

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
from .decision_validation import (
    DecisionValidator,
    DecisionValidationResult,
    ValidationCheckResult,
)

# ---------------------------------------------------------------------------
# Constants (enums, state machine, identifiers)
# ---------------------------------------------------------------------------
from .constants import (
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    SCHEMA_VERSION,
    ACTIVE_STATES,
    TERMINAL_STATES,
    IMMUTABLE_STATES,
    SUCCESS_STATES,
    VALID_TRANSITIONS,
    DecisionState,
    DecisionScope,
    DecisionType,
    DecisionPriority,
    DecisionTrigger,
    DecisionEventType,
    DecisionValidationCode,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
from .exceptions import (
    DecisionLifecycleError,
    DecisionSessionNotFoundError,
    DecisionInvalidTransitionError,
    DecisionLifecycleNotRunningError,
    DecisionSessionAlreadyExistsError,
    DecisionValidationError,
    DecisionSessionTerminatedError,
)

__all__: list[str] = [
    # Primary interface
    "DecisionLifecycle",
    # Domain objects
    "DecisionSession",
    "DecisionContext",
    "DecisionMetadata",
    # State machine
    "DecisionStateRecord",
    "DecisionTransition",
    "can_transition",
    "make_transition",
    # Events
    "DecisionEvent",
    "make_decision_created",
    "make_decision_initialized",
    "make_decision_started",
    "make_decision_paused",
    "make_decision_resumed",
    "make_decision_completed",
    "make_decision_failed",
    "make_decision_archived",
    # Infrastructure
    "DecisionRegistry",
    "DecisionFactory",
    "DecisionHistory",
    "DecisionStatistics",
    # Validation
    "DecisionValidator",
    "DecisionValidationResult",
    "ValidationCheckResult",
    # Constants
    "LIFECYCLE_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "ACTIVE_STATES",
    "TERMINAL_STATES",
    "IMMUTABLE_STATES",
    "SUCCESS_STATES",
    "VALID_TRANSITIONS",
    "DecisionState",
    "DecisionScope",
    "DecisionType",
    "DecisionPriority",
    "DecisionTrigger",
    "DecisionEventType",
    "DecisionValidationCode",
    # Exceptions
    "DecisionLifecycleError",
    "DecisionSessionNotFoundError",
    "DecisionInvalidTransitionError",
    "DecisionLifecycleNotRunningError",
    "DecisionSessionAlreadyExistsError",
    "DecisionValidationError",
    "DecisionSessionTerminatedError",
]
