"""
exceptions.py — iios.ai.foundation.lifecycle
=============================================
Exception hierarchy for the AI Foundation Lifecycle subsystem.

Error-code prefix: AFL (AI Foundation Lifecycle).

A1 AI Foundation — Phase 3, Module 1
"""
from __future__ import annotations

from typing import Optional

from iios.common.errors.exceptions import IIOSError

from .constants import AILifecycleState


class AILifecycleError(IIOSError):
    """
    Base exception for the AI Foundation Lifecycle subsystem.

    All AI lifecycle exceptions derive from this class.
    """
    DEFAULT_CODE: str = "AFL-000"


class AIInvalidTransitionError(AILifecycleError):
    """Raised when an attempted lifecycle state transition is not permitted."""
    DEFAULT_CODE = "AFL-001"

    def __init__(
        self,
        from_state: AILifecycleState,
        to_state:   AILifecycleState,
        module_id:  str = "",
    ) -> None:
        prefix = f"[{module_id}] " if module_id else ""
        super().__init__(
            f"{prefix}Invalid AI lifecycle transition: "
            f"{from_state.value!r} → {to_state.value!r}",
            code    = self.DEFAULT_CODE,
            context = {
                "from_state": from_state.value,
                "to_state":   to_state.value,
                "module_id":  module_id,
            },
        )
        self.from_state = from_state
        self.to_state   = to_state


class AIModuleAlreadyRunningError(AILifecycleError):
    """Raised when ``start()`` is called on a module that is already running."""
    DEFAULT_CODE = "AFL-002"

    def __init__(self, module_id: str = "") -> None:
        prefix = f"[{module_id}] " if module_id else ""
        super().__init__(
            f"{prefix}AI module is already running.",
            code    = self.DEFAULT_CODE,
            context = {"module_id": module_id},
        )


class AIModuleNotRunningError(AILifecycleError):
    """Raised when an operation requires a running module but it is not running."""
    DEFAULT_CODE = "AFL-003"

    def __init__(self, module_id: str = "", operation: str = "") -> None:
        prefix = f"[{module_id}] " if module_id else ""
        op_msg = f" during '{operation}'" if operation else ""
        super().__init__(
            f"{prefix}AI module is not running{op_msg}.",
            code    = self.DEFAULT_CODE,
            context = {"module_id": module_id, "operation": operation},
        )


class AIModuleInitializationError(AILifecycleError):
    """Raised when module initialization fails."""
    DEFAULT_CODE = "AFL-004"


class AIModuleShutdownError(AILifecycleError):
    """Raised when an operation is attempted on a permanently stopped module."""
    DEFAULT_CODE = "AFL-005"
