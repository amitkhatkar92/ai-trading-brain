"""
provider_constants.py -- iios.ai.foundation.provider
=====================================================
Enumerations and constants for the provider runtime.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

from enum import Enum

VERSION    = "1.0.0"
SCHEMA_VER = "1.0"

PROVIDER_SYSTEM_ID = "iios:ai:foundation:provider"


class ProviderCapabilityType(str, Enum):
    """
    Provider capability types -- provider-independent capability model.

    A provider declares which capabilities it supports in its
    :class:`AIProviderCapabilities`.  Callers request capabilities;
    the registry routes to a matching provider.
    """
    CHAT             = "chat"
    COMPLETION       = "completion"
    EMBEDDING        = "embedding"
    VISION           = "vision"
    AUDIO            = "audio"
    STRUCTURED_OUTPUT= "structured_output"
    TOOL_CALLING     = "tool_calling"
    STREAMING        = "streaming"


class ProviderStatus(str, Enum):
    """Operational status of a registered provider."""
    REGISTERED   = "registered"   # registered but not yet activated
    ACTIVE       = "active"       # healthy and serving requests
    DEGRADED     = "degraded"     # serving but with reduced reliability
    UNAVAILABLE  = "unavailable"  # not serving requests
    DEREGISTERED = "deregistered" # removed from the registry


class ProviderSelectionStrategy(str, Enum):
    """Strategy used by :class:`ProviderSelector` to choose a provider."""
    FIRST_AVAILABLE     = "first_available"
    ROUND_ROBIN         = "round_robin"
    CAPABILITY_BEST_MATCH = "capability_best_match"
    LEAST_LOADED        = "least_loaded"


class ProviderTier(str, Enum):
    """Cost/quality tier for routing decisions."""
    PREMIUM   = "premium"    # highest quality, highest cost
    STANDARD  = "standard"   # balanced
    ECONOMY   = "economy"    # lowest cost, acceptable quality
    LOCAL     = "local"      # on-premise / no API cost
