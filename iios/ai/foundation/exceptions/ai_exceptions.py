"""
ai_exceptions.py -- iios.ai.foundation.exceptions
==================================================
Unified exception hierarchy for the entire AI Platform (A1-A10).

All exceptions inherit from ``AIException`` which inherits from
``IIOSError`` for full Core Platform compatibility.

Hierarchy
---------
IIOSError
└── AIException                     AI-000  base
    ├── AIConfigurationException    AI-100  configuration errors
    │   ├── AIMissingConfigurationException  AI-101
    │   └── AIInvalidConfigurationException  AI-102
    ├── AISessionException          AI-200  session errors
    │   ├── AISessionNotFoundError  AI-201
    │   ├── AISessionExpiredError   AI-202
    │   ├── AISessionLimitError     AI-203
    │   └── AISessionStateError     AI-204
    ├── AIContextException          AI-300  context errors
    │   ├── AIContextTooLargeError  AI-301
    │   ├── AIContextValidationError AI-302
    │   └── AIContextBuildError     AI-303
    ├── AIRequestException          AI-400  request errors
    │   ├── AIRequestValidationError AI-401
    │   ├── AIRequestTimeoutError    AI-402
    │   └── AIRequestCancelledError  AI-403
    ├── AIProviderException         AI-500  provider errors
    │   ├── AIProviderNotAvailableError AI-501
    │   ├── AIProviderAuthError     AI-502
    │   ├── AIProviderRateLimitError AI-503
    │   └── AIProviderCapabilityError AI-504
    ├── AIExecutionException        AI-600  execution errors
    │   ├── AIPipelineError         AI-601
    │   ├── AIPipelineStageError    AI-602
    │   └── AIExecutionTimeoutError AI-603
    └── AIValidationException       AI-700  validation errors
        ├── AIResponseValidationError AI-701
        └── AIPolicyViolationError  AI-702

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from typing import Any, Optional

from iios.common.errors.exceptions import IIOSError


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class AIException(IIOSError):
    """Base exception for the entire AI Platform.  Code: AI-000."""
    CODE = "AI-000"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        self.error_code = code or self.CODE
        super().__init__(f"[{self.error_code}] {message}")


# ---------------------------------------------------------------------------
# AI-100 Configuration
# ---------------------------------------------------------------------------

class AIConfigurationException(AIException):
    """Configuration-related error.  Code: AI-100."""
    CODE = "AI-100"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.CODE)


class AIMissingConfigurationException(AIConfigurationException):
    """Required configuration key is absent.  Code: AI-101."""
    CODE = "AI-101"

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Missing required configuration key: '{key}'.")


class AIInvalidConfigurationException(AIConfigurationException):
    """Configuration value is present but invalid.  Code: AI-102."""
    CODE = "AI-102"

    def __init__(self, key: str, reason: str) -> None:
        self.key    = key
        self.reason = reason
        super().__init__(f"Invalid configuration for '{key}': {reason}")


# ---------------------------------------------------------------------------
# AI-200 Session
# ---------------------------------------------------------------------------

class AISessionException(AIException):
    """Session-related error.  Code: AI-200."""
    CODE = "AI-200"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.CODE)


class AISessionNotFoundError(AISessionException):
    """Session identifier not found in the registry.  Code: AI-201."""
    CODE = "AI-201"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: '{session_id}'.")


class AISessionExpiredError(AISessionException):
    """Session has exceeded its TTL and is no longer valid.  Code: AI-202."""
    CODE = "AI-202"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session has expired: '{session_id}'.")


class AISessionLimitError(AISessionException):
    """Maximum concurrent session limit reached.  Code: AI-203."""
    CODE = "AI-203"

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"Session limit reached ({limit} sessions active).")


class AISessionStateError(AISessionException):
    """Operation is invalid in the current session state.  Code: AI-204."""
    CODE = "AI-204"

    def __init__(self, session_id: str, state: str, operation: str) -> None:
        self.session_id = session_id
        self.state      = state
        self.operation  = operation
        super().__init__(
            f"Session '{session_id}' in state '{state}' "
            f"does not allow operation '{operation}'."
        )


# ---------------------------------------------------------------------------
# AI-300 Context
# ---------------------------------------------------------------------------

class AIContextException(AIException):
    """Context-related error.  Code: AI-300."""
    CODE = "AI-300"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.CODE)


class AIContextTooLargeError(AIContextException):
    """Context exceeds the token budget.  Code: AI-301."""
    CODE = "AI-301"

    def __init__(self, estimated_tokens: int, budget: int) -> None:
        self.estimated_tokens = estimated_tokens
        self.budget           = budget
        super().__init__(
            f"Context too large: estimated {estimated_tokens} tokens, "
            f"budget is {budget} tokens."
        )


class AIContextValidationError(AIContextException):
    """Context failed validation checks.  Code: AI-302."""
    CODE = "AI-302"

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Context validation failed: {reason}")


class AIContextBuildError(AIContextException):
    """Context could not be assembled.  Code: AI-303."""
    CODE = "AI-303"

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Context build failed: {reason}")


# ---------------------------------------------------------------------------
# AI-400 Request
# ---------------------------------------------------------------------------

class AIRequestException(AIException):
    """Request-related error.  Code: AI-400."""
    CODE = "AI-400"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.CODE)


class AIRequestValidationError(AIRequestException):
    """Request failed schema or semantic validation.  Code: AI-401."""
    CODE = "AI-401"

    def __init__(self, field: str, reason: str) -> None:
        self.field  = field
        self.reason = reason
        super().__init__(f"Request validation failed for '{field}': {reason}")


class AIRequestTimeoutError(AIRequestException):
    """Request exceeded its configured timeout.  Code: AI-402."""
    CODE = "AI-402"

    def __init__(self, request_id: str, timeout_s: float) -> None:
        self.request_id = request_id
        self.timeout_s  = timeout_s
        super().__init__(
            f"Request '{request_id}' timed out after {timeout_s:.1f}s."
        )


class AIRequestCancelledError(AIRequestException):
    """Request was cancelled before completion.  Code: AI-403."""
    CODE = "AI-403"

    def __init__(self, request_id: str, reason: str = "") -> None:
        self.request_id = request_id
        self.reason     = reason
        msg = f"Request '{request_id}' was cancelled."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)


# ---------------------------------------------------------------------------
# AI-500 Provider
# ---------------------------------------------------------------------------

class AIProviderException(AIException):
    """Provider-related error.  Code: AI-500."""
    CODE = "AI-500"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.CODE)


class AIProviderNotAvailableError(AIProviderException):
    """No provider is available for the requested capability.  Code: AI-501."""
    CODE = "AI-501"

    def __init__(self, capability: str) -> None:
        self.capability = capability
        super().__init__(
            f"No available provider for capability '{capability}'."
        )


class AIProviderAuthError(AIProviderException):
    """Provider authentication or authorisation failed.  Code: AI-502."""
    CODE = "AI-502"

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        super().__init__(f"Authentication failed for provider '{provider_id}'.")


class AIProviderRateLimitError(AIProviderException):
    """Provider rate limit exceeded.  Code: AI-503."""
    CODE = "AI-503"

    def __init__(self, provider_id: str, retry_after_s: float = 0.0) -> None:
        self.provider_id    = provider_id
        self.retry_after_s  = retry_after_s
        super().__init__(
            f"Rate limit exceeded for provider '{provider_id}' "
            f"(retry after {retry_after_s:.1f}s)."
        )


class AIProviderCapabilityError(AIProviderException):
    """Provider does not support the requested capability.  Code: AI-504."""
    CODE = "AI-504"

    def __init__(self, provider_id: str, capability: str) -> None:
        self.provider_id = provider_id
        self.capability  = capability
        super().__init__(
            f"Provider '{provider_id}' does not support capability '{capability}'."
        )


# ---------------------------------------------------------------------------
# AI-600 Execution
# ---------------------------------------------------------------------------

class AIExecutionException(AIException):
    """Execution pipeline error.  Code: AI-600."""
    CODE = "AI-600"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.CODE)


class AIPipelineError(AIExecutionException):
    """Execution pipeline encountered an unrecoverable error.  Code: AI-601."""
    CODE = "AI-601"

    def __init__(self, stage: str, reason: str) -> None:
        self.stage  = stage
        self.reason = reason
        super().__init__(f"Pipeline error at stage '{stage}': {reason}")


class AIPipelineStageError(AIExecutionException):
    """A specific pipeline stage failed.  Code: AI-602."""
    CODE = "AI-602"

    def __init__(self, stage: str, reason: str, *, recoverable: bool = False) -> None:
        self.stage       = stage
        self.reason      = reason
        self.recoverable = recoverable
        super().__init__(f"Stage '{stage}' failed: {reason}")


class AIExecutionTimeoutError(AIExecutionException):
    """Execution exceeded the pipeline timeout.  Code: AI-603."""
    CODE = "AI-603"

    def __init__(self, pipeline_id: str, timeout_s: float) -> None:
        self.pipeline_id = pipeline_id
        self.timeout_s   = timeout_s
        super().__init__(
            f"Pipeline '{pipeline_id}' timed out after {timeout_s:.1f}s."
        )


# ---------------------------------------------------------------------------
# AI-700 Validation
# ---------------------------------------------------------------------------

class AIValidationException(AIException):
    """Validation error.  Code: AI-700."""
    CODE = "AI-700"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.CODE)


class AIResponseValidationError(AIValidationException):
    """Provider response failed post-processing validation.  Code: AI-701."""
    CODE = "AI-701"

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Response validation failed: {reason}")


class AIPolicyViolationError(AIValidationException):
    """Request or response violated a configured policy.  Code: AI-702."""
    CODE = "AI-702"

    def __init__(self, policy: str, reason: str) -> None:
        self.policy = policy
        self.reason = reason
        super().__init__(f"Policy '{policy}' violated: {reason}")
