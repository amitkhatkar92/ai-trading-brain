"""
iios.ai.foundation.exceptions
==============================
Unified exception hierarchy for the AI Platform.

    from iios.ai.foundation.exceptions import AIException, AISessionNotFoundError

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

from .ai_exceptions import (
    AIException,
    # Configuration
    AIConfigurationException,
    AIMissingConfigurationException,
    AIInvalidConfigurationException,
    # Session
    AISessionException,
    AISessionNotFoundError,
    AISessionExpiredError,
    AISessionLimitError,
    AISessionStateError,
    # Context
    AIContextException,
    AIContextTooLargeError,
    AIContextValidationError,
    AIContextBuildError,
    # Request
    AIRequestException,
    AIRequestValidationError,
    AIRequestTimeoutError,
    AIRequestCancelledError,
    # Provider
    AIProviderException,
    AIProviderNotAvailableError,
    AIProviderAuthError,
    AIProviderRateLimitError,
    AIProviderCapabilityError,
    # Execution
    AIExecutionException,
    AIPipelineError,
    AIPipelineStageError,
    AIExecutionTimeoutError,
    # Validation
    AIValidationException,
    AIResponseValidationError,
    AIPolicyViolationError,
)

__all__ = [
    "AIException",
    "AIConfigurationException",
    "AIMissingConfigurationException",
    "AIInvalidConfigurationException",
    "AISessionException",
    "AISessionNotFoundError",
    "AISessionExpiredError",
    "AISessionLimitError",
    "AISessionStateError",
    "AIContextException",
    "AIContextTooLargeError",
    "AIContextValidationError",
    "AIContextBuildError",
    "AIRequestException",
    "AIRequestValidationError",
    "AIRequestTimeoutError",
    "AIRequestCancelledError",
    "AIProviderException",
    "AIProviderNotAvailableError",
    "AIProviderAuthError",
    "AIProviderRateLimitError",
    "AIProviderCapabilityError",
    "AIExecutionException",
    "AIPipelineError",
    "AIPipelineStageError",
    "AIExecutionTimeoutError",
    "AIValidationException",
    "AIResponseValidationError",
    "AIPolicyViolationError",
]
