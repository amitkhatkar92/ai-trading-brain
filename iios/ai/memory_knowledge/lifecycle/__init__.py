"""
iios.ai.memory_knowledge.lifecycle
===================================
M1 Lifecycle layer — re-exports A1's lifecycle primitives so that A4
components depend only on this package's public surface, not directly
on A1 internals.
"""
from iios.ai.foundation.lifecycle.ai_foundation_lifecycle import AILifecycleAwareMixin
from iios.ai.foundation.lifecycle.ai_foundation_lifecycle import AILifecycleState

__all__ = [
    "AILifecycleAwareMixin",
    "AILifecycleState",
]
