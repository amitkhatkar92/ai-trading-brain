"""
iios.ai.foundation.adapters
============================
A1 AI Foundation — M4 Adapters layer.

Provides the abstract ``AIProvider`` interface, configuration management,
token budgeting, rate limiting, retry handling, and the event bus that
prevents circular dependencies between AI modules.

Primary public exports
----------------------
:class:`AIProvider`              — abstract model provider interface
:class:`AIProviderInfo`          — static provider metadata
:class:`AIProviderRequest`       — immutable request DTO
:class:`AIProviderResponse`      — immutable response DTO
:class:`AIEmbeddingResponse`     — immutable embedding DTO
:class:`AIProviderRegistry`      — thread-safe provider registry
:class:`AIConfiguration`         — immutable platform configuration
:class:`AIConfigurationProvider` — abstract configuration source
:class:`EnvironmentAIConfigurationProvider` — env-var implementation
:class:`TokenManager`            — context window budget management
:class:`RateLimiter`             — sliding-window rate enforcement
:class:`RetryHandler`            — exponential back-off retry
:class:`AIEventBus`              — inter-module event bus interface
:class:`LocalAIEventBus`         — in-process synchronous bus
:class:`AIEvent`                 — immutable event DTO
:class:`AIMetadata`              — immutable operation metadata
:class:`AIExecutionResult`       — immutable execution result

A1 AI Foundation — Phase 3, Module 4
"""
from __future__ import annotations

# Provider interface + DTOs
from .ai_provider import (
    AIProvider,
    AIProviderInfo,
    AIProviderRequest,
    AIProviderResponse,
    AIEmbeddingResponse,
)

# Provider registry
from .ai_provider_registry import AIProviderRegistry

# Configuration
from .ai_configuration import (
    AIConfiguration,
    AIConfigurationProvider,
    AIProviderCredential,
    AIRateLimitConfig,
    EnvironmentAIConfigurationProvider,
)

# Budget / limits / retry
from .token_manager  import TokenManager, TokenBudgetSnapshot
from .rate_limiter   import RateLimiter, RateLimitSnapshot
from .retry_handler  import RetryHandler, RetrySnapshot

# Event bus
from .ai_event_bus import AIEventBus, LocalAIEventBus, AIEvent

# Metadata and results
from .ai_metadata import (
    AIMetadata,
    AIExecutionResult,
    AIProviderStatistics,
)

# Enumerations
from .constants import (
    AICapability,
    AIRequestPriority,
    AIExecutionStatus,
    AIProviderHealth,
    VERSION,
)

# Exceptions
from .exceptions import (
    AIAdapterError,
    AIProviderError,
    AIProviderNotFoundError,
    AITimeoutError,
    AITokenBudgetError,
    AIRateLimitError,
    AIConfigurationError,
    AICapabilityNotSupportedError,
)

__all__ = [
    # Provider
    "AIProvider",
    "AIProviderInfo",
    "AIProviderRequest",
    "AIProviderResponse",
    "AIEmbeddingResponse",
    "AIProviderRegistry",
    # Configuration
    "AIConfiguration",
    "AIConfigurationProvider",
    "AIProviderCredential",
    "AIRateLimitConfig",
    "EnvironmentAIConfigurationProvider",
    # Budget / limits / retry
    "TokenManager",
    "TokenBudgetSnapshot",
    "RateLimiter",
    "RateLimitSnapshot",
    "RetryHandler",
    "RetrySnapshot",
    # Event bus
    "AIEventBus",
    "LocalAIEventBus",
    "AIEvent",
    # Metadata
    "AIMetadata",
    "AIExecutionResult",
    "AIProviderStatistics",
    # Enums
    "AICapability",
    "AIRequestPriority",
    "AIExecutionStatus",
    "AIProviderHealth",
    "VERSION",
    # Exceptions
    "AIAdapterError",
    "AIProviderError",
    "AIProviderNotFoundError",
    "AITimeoutError",
    "AITokenBudgetError",
    "AIRateLimitError",
    "AIConfigurationError",
    "AICapabilityNotSupportedError",
]
