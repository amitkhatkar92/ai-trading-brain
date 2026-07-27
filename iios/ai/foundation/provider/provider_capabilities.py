"""
provider_capabilities.py -- iios.ai.foundation.provider
========================================================
Immutable capability models for AI providers.

Capability detection is entirely provider-independent -- no provider
SDK is imported here.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional

from .provider_constants import ProviderCapabilityType, ProviderTier, SCHEMA_VER


@dataclass(frozen=True)
class AIProviderCapabilities:
    """
    Immutable capability declaration for one AI provider/model.

    Fields
    ------
    provider_id :       Provider identifier.
    model_id :          Model identifier.
    capabilities :      Frozenset of supported :class:`ProviderCapabilityType`.
    context_window :    Maximum context window in tokens.
    max_output :        Maximum output tokens.
    supports_streaming: Whether the model supports token-by-token streaming.
    supports_functions: Whether the model supports function/tool calling.
    supports_vision :   Whether the model accepts image input.
    tier :              Cost/quality tier.
    max_requests_per_min : Rate limit (0 = unknown).
    max_tokens_per_min :   Token rate limit (0 = unknown).
    notes :             Optional human-readable notes.
    """
    provider_id:           str
    model_id:              str
    capabilities:          FrozenSet[ProviderCapabilityType]
    context_window:        int
    max_output:            int
    supports_streaming:    bool          = False
    supports_functions:    bool          = False
    supports_vision:       bool          = False
    tier:                  ProviderTier  = ProviderTier.STANDARD
    max_requests_per_min:  int           = 0
    max_tokens_per_min:    int           = 0
    notes:                 str           = ""
    schema:                str           = SCHEMA_VER

    def supports(self, capability: ProviderCapabilityType) -> bool:
        """Return True iff this provider supports ``capability``."""
        return capability in self.capabilities

    def supports_all(self, *capabilities: ProviderCapabilityType) -> bool:
        """Return True iff all listed capabilities are supported."""
        return all(c in self.capabilities for c in capabilities)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id":          self.provider_id,
            "model_id":             self.model_id,
            "capabilities":         [c.value for c in self.capabilities],
            "context_window":       self.context_window,
            "max_output":           self.max_output,
            "supports_streaming":   self.supports_streaming,
            "supports_functions":   self.supports_functions,
            "supports_vision":      self.supports_vision,
            "tier":                 self.tier.value,
            "max_requests_per_min": self.max_requests_per_min,
            "max_tokens_per_min":   self.max_tokens_per_min,
        }


@dataclass(frozen=True)
class ProviderProfile:
    """
    Immutable runtime profile combining identity, capabilities, and status.

    Created by :class:`ProviderRegistry` when a provider is registered.
    """
    provider_id:    str
    display_name:   str
    capabilities:   AIProviderCapabilities
    registered_at:  float
    metadata:       Dict[str, Any] = field(default_factory=dict)
    schema:         str            = SCHEMA_VER

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id":   self.provider_id,
            "display_name":  self.display_name,
            "capabilities":  self.capabilities.to_dict(),
            "registered_at": self.registered_at,
        }
