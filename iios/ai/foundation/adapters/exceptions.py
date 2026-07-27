"""
exceptions.py — iios.ai.foundation.adapters
============================================
Exception hierarchy for the AI Foundation Adapters layer (M4).

All exceptions inherit from ``IIOSError`` to fit into the Core Platform
error handling chain.

Error code prefix: AFA (AI Foundation Adapters)

A1 AI Foundation — Phase 3, Module 4
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class AIAdapterError(IIOSError):
    """Base exception for all AI Foundation Adapter errors.  Code: AFA-000."""
    CODE = "AFA-000"


class AIProviderError(AIAdapterError):
    """AI model provider returned an error.  Code: AFA-001."""
    CODE = "AFA-001"

    def __init__(self, provider_id: str, message: str) -> None:
        self.provider_id = provider_id
        super().__init__(f"[{self.CODE}] Provider '{provider_id}': {message}")


class AIProviderNotFoundError(AIAdapterError):
    """Requested AI provider is not registered.  Code: AFA-002."""
    CODE = "AFA-002"

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        super().__init__(f"[{self.CODE}] AI provider not found: '{provider_id}'.")


class AITimeoutError(AIAdapterError):
    """AI provider request exceeded the configured timeout.  Code: AFA-003."""
    CODE = "AFA-003"

    def __init__(self, provider_id: str, timeout_s: float) -> None:
        self.provider_id = provider_id
        self.timeout_s   = timeout_s
        super().__init__(
            f"[{self.CODE}] Provider '{provider_id}' timed out after {timeout_s:.1f}s."
        )


class AITokenBudgetError(AIAdapterError):
    """Request exceeds the configured token budget.  Code: AFA-004."""
    CODE = "AFA-004"

    def __init__(self, used: int, budget: int) -> None:
        self.used   = used
        self.budget = budget
        super().__init__(
            f"[{self.CODE}] Token budget exceeded: used={used}, budget={budget}."
        )


class AIRateLimitError(AIAdapterError):
    """Provider rate limit exceeded.  Code: AFA-005."""
    CODE = "AFA-005"

    def __init__(self, provider_id: str, wait_s: float = 0.0) -> None:
        self.provider_id = provider_id
        self.wait_s      = wait_s
        super().__init__(
            f"[{self.CODE}] Rate limit exceeded for provider '{provider_id}' "
            f"(suggested wait: {wait_s:.1f}s)."
        )


class AIConfigurationError(AIAdapterError):
    """AI configuration is missing or invalid.  Code: AFA-006."""
    CODE = "AFA-006"

    def __init__(self, message: str) -> None:
        super().__init__(f"[{self.CODE}] AI configuration error: {message}")


class AICapabilityNotSupportedError(AIAdapterError):
    """Requested capability is not supported by the selected provider.  Code: AFA-007."""
    CODE = "AFA-007"

    def __init__(self, provider_id: str, capability: str) -> None:
        self.provider_id = provider_id
        self.capability  = capability
        super().__init__(
            f"[{self.CODE}] Provider '{provider_id}' does not support "
            f"capability '{capability}'."
        )
