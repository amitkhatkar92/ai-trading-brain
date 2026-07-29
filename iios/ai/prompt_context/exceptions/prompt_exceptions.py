"""
prompt_exceptions.py -- iios.ai.prompt_context.exceptions
===========================================================
Exception hierarchy for the A3 Prompt & Context Platform.

All exceptions inherit from :class:`AIException` (A1 AI Foundation) for
full Core Platform compatibility.  This module does not modify A1 --
it only imports the shared base class and adds new error codes.

Hierarchy
---------
AIException                            AI-000  (A1 base)
├── AIPromptException                  AI-800  prompt errors
│   ├── AIPromptNotFoundError          AI-801
│   ├── AIPromptAlreadyExistsError     AI-802
│   ├── AIPromptVersionError           AI-803
│   ├── AIPromptDisabledError          AI-804
│   └── AIPromptValidationError        AI-805
├── AIContextAssemblyException         AI-810  context assembly errors
│   ├── AIContextIncompleteError       AI-811
│   └── AIContextBudgetExceededError   AI-812
├── AIVariableException                AI-820  variable substitution errors
│   ├── AIMissingVariableError         AI-821
│   └── AIInvalidVariableError         AI-822
└── AIPromptPolicyViolationError       AI-830  policy framework violations

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

from iios.ai.foundation.exceptions import AIException


# ---------------------------------------------------------------------------
# AI-800 Prompt errors
# ---------------------------------------------------------------------------

class AIPromptException(AIException):
    """Prompt-related error.  Code: AI-800."""
    CODE = "AI-800"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.CODE)


class AIPromptNotFoundError(AIPromptException):
    """Requested prompt_id does not exist in the registry.  Code: AI-801."""
    CODE = "AI-801"

    def __init__(self, prompt_id: str) -> None:
        super().__init__(f"Prompt not found: {prompt_id!r}")
        self.error_code = self.CODE


class AIPromptAlreadyExistsError(AIPromptException):
    """A prompt with the same identity is already registered.  Code: AI-802."""
    CODE = "AI-802"

    def __init__(self, prompt_id: str) -> None:
        super().__init__(f"Prompt already exists: {prompt_id!r}")
        self.error_code = self.CODE


class AIPromptVersionError(AIPromptException):
    """Invalid or unknown prompt version operation.  Code: AI-803."""
    CODE = "AI-803"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.error_code = self.CODE


class AIPromptDisabledError(AIPromptException):
    """Attempted to use a disabled prompt template.  Code: AI-804."""
    CODE = "AI-804"

    def __init__(self, prompt_id: str) -> None:
        super().__init__(f"Prompt is disabled: {prompt_id!r}")
        self.error_code = self.CODE


class AIPromptValidationError(AIPromptException):
    """Prompt template or composition failed validation.  Code: AI-805."""
    CODE = "AI-805"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.error_code = self.CODE


# ---------------------------------------------------------------------------
# AI-810 Context assembly errors
# ---------------------------------------------------------------------------

class AIContextAssemblyException(AIException):
    """Context assembly error.  Code: AI-810."""
    CODE = "AI-810"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.CODE)


class AIContextIncompleteError(AIContextAssemblyException):
    """Context could not be assembled -- no segments fit the budget.  Code: AI-811."""
    CODE = "AI-811"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.error_code = self.CODE


class AIContextBudgetExceededError(AIContextAssemblyException):
    """Assembled context exceeds the configured token budget.  Code: AI-812."""
    CODE = "AI-812"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.error_code = self.CODE


# ---------------------------------------------------------------------------
# AI-820 Variable substitution errors
# ---------------------------------------------------------------------------

class AIVariableException(AIException):
    """Variable substitution error.  Code: AI-820."""
    CODE = "AI-820"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.CODE)


class AIMissingVariableError(AIVariableException):
    """A required template variable was not supplied.  Code: AI-821."""
    CODE = "AI-821"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.error_code = self.CODE


class AIInvalidVariableError(AIVariableException):
    """A supplied variable value is invalid for the template.  Code: AI-822."""
    CODE = "AI-822"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.error_code = self.CODE


# ---------------------------------------------------------------------------
# AI-830 Policy violations
# ---------------------------------------------------------------------------

class AIPromptPolicyViolationError(AIException):
    """A registered A3 policy rejected an operation.  Code: AI-830."""
    CODE = "AI-830"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.CODE)
