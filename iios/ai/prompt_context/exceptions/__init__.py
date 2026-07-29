"""
iios.ai.prompt_context.exceptions
===================================
Exception hierarchy for the A3 Prompt & Context Platform.
"""
from __future__ import annotations

from .prompt_exceptions import (
    AIPromptException,
    AIPromptNotFoundError,
    AIPromptAlreadyExistsError,
    AIPromptVersionError,
    AIPromptDisabledError,
    AIPromptValidationError,
    AIContextAssemblyException,
    AIContextIncompleteError,
    AIContextBudgetExceededError,
    AIVariableException,
    AIMissingVariableError,
    AIInvalidVariableError,
    AIPromptPolicyViolationError,
)

__all__ = [
    "AIPromptException",
    "AIPromptNotFoundError",
    "AIPromptAlreadyExistsError",
    "AIPromptVersionError",
    "AIPromptDisabledError",
    "AIPromptValidationError",
    "AIContextAssemblyException",
    "AIContextIncompleteError",
    "AIContextBudgetExceededError",
    "AIVariableException",
    "AIMissingVariableError",
    "AIInvalidVariableError",
    "AIPromptPolicyViolationError",
]
