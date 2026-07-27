"""
iios.ai.foundation.lifecycle
=============================
A1 AI Foundation — M1 Lifecycle layer.

Primary public export
---------------------
:class:`AILifecycleAwareMixin` — the standard lifecycle base for ALL
AI Platform modules (A2–A10 must inherit from this).

    >>> from iios.ai.foundation.lifecycle import AILifecycleAwareMixin

State types
-----------
:class:`AILifecycleState` — operational state enum.
:class:`AILifecycleEvent` — immutable lifecycle event.

A1 AI Foundation — Phase 3, Module 1
"""
from __future__ import annotations

# Primary mixin — re-exported for convenience
from .ai_foundation_lifecycle import AILifecycleAwareMixin

# State types
from .ai_foundation_state  import AIStateRecord, AITransitionRecord, can_transition
from .ai_foundation_events import AILifecycleEvent

# Domain objects
from .ai_foundation_session  import AIFoundationSession
from .ai_foundation_registry import AIFoundationRegistry

# Enumerations
from .constants import (
    AILifecycleState,
    AILifecycleEventType,
    ACTIVE_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VERSION,
)

# Exceptions
from .exceptions import (
    AILifecycleError,
    AIInvalidTransitionError,
    AIModuleAlreadyRunningError,
    AIModuleNotRunningError,
    AIModuleInitializationError,
    AIModuleShutdownError,
)

__all__ = [
    # Primary export
    "AILifecycleAwareMixin",
    # State
    "AILifecycleState",
    "AILifecycleEventType",
    "AIStateRecord",
    "AITransitionRecord",
    "AILifecycleEvent",
    "can_transition",
    # Constants
    "ACTIVE_STATES",
    "TERMINAL_STATES",
    "VALID_TRANSITIONS",
    "VERSION",
    # Domain objects
    "AIFoundationSession",
    "AIFoundationRegistry",
    # Exceptions
    "AILifecycleError",
    "AIInvalidTransitionError",
    "AIModuleAlreadyRunningError",
    "AIModuleNotRunningError",
    "AIModuleInitializationError",
    "AIModuleShutdownError",
]
