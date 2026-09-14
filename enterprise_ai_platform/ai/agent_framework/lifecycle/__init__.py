"""
enterprise_ai_platform.ai.agent_framework.lifecycle
==================================
M1 Lifecycle layer — re-exports A1's lifecycle primitives so that A5
components depend only on this package's public surface, not directly
on A1 internals.
"""
from enterprise_ai_platform.ai.foundation.lifecycle.ai_foundation_lifecycle import AILifecycleAwareMixin
from enterprise_ai_platform.ai.foundation.lifecycle.ai_foundation_lifecycle import AILifecycleState
from enterprise_ai_platform.ai.foundation.lifecycle.exceptions import (
    AILifecycleError,
    AIInvalidTransitionError,
    AIModuleAlreadyRunningError,
    AIModuleNotRunningError,
)

__all__ = [
    "AILifecycleAwareMixin",
    "AILifecycleState",
    "AILifecycleError",
    "AIInvalidTransitionError",
    "AIModuleAlreadyRunningError",
    "AIModuleNotRunningError",
]
