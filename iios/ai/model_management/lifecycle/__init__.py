"""
iios.ai.model_management.lifecycle
=====================================
M1 Lifecycle — A2 reuses A1's :class:`AILifecycleAwareMixin`.

No new state machine is needed: the CREATED → INITIALIZED → RUNNING →
STOPPED contract is identical across all AI Platform modules (A1-A10).

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from iios.ai.foundation.lifecycle.ai_foundation_lifecycle import AILifecycleAwareMixin
from iios.ai.foundation.lifecycle.constants               import AILifecycleState
from iios.ai.foundation.lifecycle.exceptions import (
    AIInvalidTransitionError,
    AILifecycleError,
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
