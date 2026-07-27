"""
ai_configuration.py — iios.ai.foundation.adapters
==================================================
:class:`AIConfiguration` and :class:`AIConfigurationProvider` — centralised
configuration management for the entire AI Platform.

All AI modules receive their configuration through this interface.  No AI
module reads environment variables, files, or secrets directly; all
configuration flows through ``AIConfigurationProvider``.

This addresses Review Observation O-004.

A1 AI Foundation — Phase 3, Module 4
"""
from __future__ import annotations

import abc
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence

from .constants import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RATE_LIMIT_RPM,
    DEFAULT_RATE_LIMIT_TPM,
    DEFAULT_TIMEOUT_S,
    DEFAULT_TOKEN_BUDGET,
    SCHEMA_VERSION,
    VERSION,
)


# ---------------------------------------------------------------------------
# Provider credential (never logged, never embedded in prompts)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIProviderCredential:
    """
    Immutable credential record for one AI provider.

    Fields
    ------
    provider_id :  Provider identifier matching ``AIProviderInfo.provider_id``.
    api_key :      API key (never logged).
    api_base :     Base URL for the provider API endpoint.
    organisation : Optional organisation identifier (OpenAI, etc.).
    extra :        Provider-specific additional parameters (e.g. ``api_version``).

    Security note
    -------------
    ``api_key`` is intentionally excluded from ``to_dict()`` and ``__repr__``
    to prevent accidental logging or prompt injection.
    """
    provider_id:   str
    api_key:       str
    api_base:      str              = ""
    organisation:  str              = ""
    extra:         Dict[str, str]   = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise WITHOUT the API key (safe for logging)."""
        return {
            "provider_id":  self.provider_id,
            "api_base":     self.api_base,
            "organisation": self.organisation,
            "has_api_key":  bool(self.api_key),
        }

    def __repr__(self) -> str:  # noqa: D401
        return (
            f"<AIProviderCredential provider={self.provider_id!r} "
            f"api_key=***REDACTED***>"
        )


# ---------------------------------------------------------------------------
# Rate-limit configuration per provider
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIRateLimitConfig:
    """
    Rate-limit parameters for one AI provider.

    Fields
    ------
    provider_id :    Provider identifier.
    tokens_per_min : Maximum tokens per minute.
    requests_per_min : Maximum requests per minute.
    """
    provider_id:      str
    tokens_per_min:   int = DEFAULT_RATE_LIMIT_TPM
    requests_per_min: int = DEFAULT_RATE_LIMIT_RPM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id":      self.provider_id,
            "tokens_per_min":   self.tokens_per_min,
            "requests_per_min": self.requests_per_min,
        }


# ---------------------------------------------------------------------------
# Platform-wide AI configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIConfiguration:
    """
    Immutable platform-wide AI configuration object.

    One instance is created at startup and injected into every AI module's
    M6 gateway at initialization time.  No module reads configuration
    outside of this object.

    Fields
    ------
    credentials :        Credentials indexed by ``provider_id``.
    rate_limits :        Rate-limit configs indexed by ``provider_id``.
    default_timeout_s :  Default per-request timeout.
    default_max_retries : Default maximum retry attempts.
    default_token_budget : Default context token budget.
    default_max_output :  Default maximum output tokens.
    governance_tier :    Default governance tier (``"fast"`` / ``"standard"`` / ``"full"``).
    environment :        Deployment environment label (``"production"`` / ``"staging"`` / ``"test"``).
    version :            Configuration schema version.
    """
    credentials:          Dict[str, AIProviderCredential] = field(default_factory=dict)
    rate_limits:          Dict[str, AIRateLimitConfig]    = field(default_factory=dict)
    default_timeout_s:    float = DEFAULT_TIMEOUT_S
    default_max_retries:  int   = DEFAULT_MAX_RETRIES
    default_token_budget: int   = DEFAULT_TOKEN_BUDGET
    default_max_output:   int   = DEFAULT_MAX_OUTPUT_TOKENS
    governance_tier:      str   = "standard"
    environment:          str   = "production"
    version:              str   = VERSION
    schema:               str   = SCHEMA_VERSION

    def credential(self, provider_id: str) -> Optional[AIProviderCredential]:
        """Return the credential for ``provider_id``, or ``None`` if not found."""
        return self.credentials.get(provider_id)

    def rate_limit(self, provider_id: str) -> AIRateLimitConfig:
        """Return the rate-limit config for ``provider_id`` (falls back to defaults)."""
        return self.rate_limits.get(
            provider_id,
            AIRateLimitConfig(provider_id=provider_id),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialise WITHOUT credentials (safe for logging)."""
        return {
            "provider_count":    len(self.credentials),
            "providers":         list(self.credentials.keys()),
            "default_timeout_s": self.default_timeout_s,
            "default_max_retries": self.default_max_retries,
            "default_token_budget": self.default_token_budget,
            "governance_tier":   self.governance_tier,
            "environment":       self.environment,
            "version":           self.version,
        }


# ---------------------------------------------------------------------------
# Abstract configuration provider
# ---------------------------------------------------------------------------

class AIConfigurationProvider(abc.ABC):
    """
    Abstract source of :class:`AIConfiguration`.

    Implementations may load from environment variables, a secrets manager,
    a config file, a Vault instance, or a test fixture.

    All AI modules receive configuration through this interface at
    initialization time — never by reading environment variables directly.
    """

    @abc.abstractmethod
    def load(self) -> AIConfiguration:
        """
        Load and return the current :class:`AIConfiguration`.

        Returns
        -------
        AIConfiguration
            Fully populated, immutable configuration object.

        Raises
        ------
        AIConfigurationError
            If required configuration is missing or invalid.
        """

    def reload(self) -> AIConfiguration:
        """
        Reload configuration (e.g., after a credential rotation).

        Default implementation delegates to :meth:`load`.
        Override in subclasses that support hot-reload.
        """
        return self.load()


# ---------------------------------------------------------------------------
# Environment-variable-based implementation (reference implementation)
# ---------------------------------------------------------------------------

class EnvironmentAIConfigurationProvider(AIConfigurationProvider):
    """
    Loads :class:`AIConfiguration` from environment variables.

    This is the default implementation for production deployments.
    Test fixtures should provide a mock implementation instead.

    Environment variables
    ----------------------
    ``IIOS_AI_{PROVIDER_ID}_API_KEY``    — API key for provider.
    ``IIOS_AI_{PROVIDER_ID}_API_BASE``   — Optional base URL.
    ``IIOS_AI_TIMEOUT_S``                — Default timeout.
    ``IIOS_AI_MAX_RETRIES``              — Default max retries.
    ``IIOS_AI_TOKEN_BUDGET``             — Default token budget.
    ``IIOS_AI_GOVERNANCE_TIER``          — Governance tier.
    ``IIOS_AI_ENVIRONMENT``              — Environment label.
    """

    _KNOWN_PROVIDERS = ("openai", "anthropic", "google", "azure_openai", "local")

    def load(self) -> AIConfiguration:
        credentials: Dict[str, AIProviderCredential] = {}
        rate_limits: Dict[str, AIRateLimitConfig]    = {}

        for pid in self._KNOWN_PROVIDERS:
            env_key = f"IIOS_AI_{pid.upper()}_API_KEY"
            api_key = os.environ.get(env_key, "")
            if api_key:
                credentials[pid] = AIProviderCredential(
                    provider_id = pid,
                    api_key     = api_key,
                    api_base    = os.environ.get(f"IIOS_AI_{pid.upper()}_API_BASE", ""),
                )

        return AIConfiguration(
            credentials          = credentials,
            rate_limits          = rate_limits,
            default_timeout_s    = float(os.environ.get("IIOS_AI_TIMEOUT_S",    DEFAULT_TIMEOUT_S)),
            default_max_retries  = int(  os.environ.get("IIOS_AI_MAX_RETRIES",  DEFAULT_MAX_RETRIES)),
            default_token_budget = int(  os.environ.get("IIOS_AI_TOKEN_BUDGET", DEFAULT_TOKEN_BUDGET)),
            governance_tier      = os.environ.get("IIOS_AI_GOVERNANCE_TIER", "standard"),
            environment          = os.environ.get("IIOS_AI_ENVIRONMENT",     "production"),
        )
