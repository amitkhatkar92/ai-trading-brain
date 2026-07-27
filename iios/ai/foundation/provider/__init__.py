"""
iios.ai.foundation.provider
============================
A1 AI Foundation -- Provider Runtime.

Primary exports
---------------
:class:`AIProviderRuntime`        -- lifecycle-aware provider runtime
:class:`ProviderManager`          -- provider lifecycle orchestrator
:class:`ProviderRegistry`         -- thread-safe provider registry
:class:`ProviderResolver`         -- capability-based discovery
:class:`ProviderSelector`         -- routing strategy
:class:`AIProviderCapabilities`   -- immutable capability model
:class:`AIProviderExtension`      -- abstract provider interface

Extension interfaces (no implementations -- A2 implements these)
-----------------------------------------------------------------
:class:`OpenAIProviderExtension`
:class:`AnthropicProviderExtension`
:class:`GoogleProviderExtension`
:class:`DeepSeekProviderExtension`
:class:`LocalModelProviderExtension`
:class:`EnterpriseProviderExtension`

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

from .provider_constants    import (
    ProviderCapabilityType, ProviderStatus,
    ProviderSelectionStrategy, ProviderTier, VERSION,
)
from .provider_capabilities import AIProviderCapabilities, ProviderProfile
from .provider_extensions   import (
    AIProviderExtension,
    OpenAIProviderExtension,
    AnthropicProviderExtension,
    GoogleProviderExtension,
    DeepSeekProviderExtension,
    LocalModelProviderExtension,
    EnterpriseProviderExtension,
)
from .provider_registry     import ProviderRegistry, ProviderEntry
from .provider_resolver     import ProviderResolver, ProviderSelector
from .provider_manager      import ProviderManager, AIProviderRuntime

__all__ = [
    # Constants
    "ProviderCapabilityType", "ProviderStatus",
    "ProviderSelectionStrategy", "ProviderTier", "VERSION",
    # Capability models
    "AIProviderCapabilities", "ProviderProfile",
    # Extension interfaces
    "AIProviderExtension",
    "OpenAIProviderExtension", "AnthropicProviderExtension",
    "GoogleProviderExtension", "DeepSeekProviderExtension",
    "LocalModelProviderExtension", "EnterpriseProviderExtension",
    # Runtime components
    "ProviderRegistry", "ProviderEntry",
    "ProviderResolver", "ProviderSelector",
    "ProviderManager", "AIProviderRuntime",
]
