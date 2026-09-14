"""
enterprise_ai_platform.ai.orchestrator.lifecycle
================================
M1 Lifecycle layer — re-exports A1 lifecycle primitives so A10
components depend only on this package, not directly on A1 internals.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
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
