"""
iios.ai.prompt_context.lifecycle
===================================
M1 Lifecycle -- the A3 Prompt & Context Platform reuses the shared
:class:`AILifecycleAwareMixin` defined in A1 AI Foundation rather than
reimplementing a state machine.  This keeps the CREATED -> INITIALIZED
-> RUNNING -> STOPPED contract identical across every AI Platform module
(A1-A10).

Usage::

    from iios.ai.prompt_context.lifecycle import AILifecycleAwareMixin

    class MyEngine(AILifecycleAwareMixin):
        SYSTEM_ID = "iios:ai:prompt_context:my_engine"
        VERSION   = "1.0.0"

A3 Prompt & Context Platform -- Phase 3, Module 3
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
