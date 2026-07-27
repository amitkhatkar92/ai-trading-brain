"""
config_models.py -- iios.ai.foundation.config
==============================================
Configuration models and loaders for the AI Foundation.

Provides framework-level configuration (distinct from the provider-level
AIConfiguration in adapters/).  All components receive configuration
via dependency injection -- no global config singletons.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import abc
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..exceptions import AIMissingConfigurationException, AIInvalidConfigurationException

SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FeatureFlags:
    """
    Immutable feature flag set for the AI Platform.

    All flags default to safe values (features disabled).
    Enable flags explicitly in deployment configuration.
    """
    enable_streaming:       bool = False   # streaming responses
    enable_caching:         bool = False   # response caching
    enable_tracing:         bool = True    # distributed tracing
    enable_cost_tracking:   bool = True    # token cost tracking
    enable_policy_eval:     bool = True    # policy evaluation stage
    enable_result_validation: bool = True  # result validation stage
    enable_provider_fallback: bool = True  # automatic provider fallback
    enable_retry:           bool = True    # automatic retry on failure

    @classmethod
    def all_enabled(cls) -> "FeatureFlags":
        """Convenience -- all flags enabled (use in tests only)."""
        return cls(
            enable_streaming        = True,
            enable_caching          = True,
            enable_tracing          = True,
            enable_cost_tracking    = True,
            enable_policy_eval      = True,
            enable_result_validation = True,
            enable_provider_fallback = True,
            enable_retry            = True,
        )

    def to_dict(self) -> Dict[str, bool]:
        return {
            "enable_streaming":        self.enable_streaming,
            "enable_caching":          self.enable_caching,
            "enable_tracing":          self.enable_tracing,
            "enable_cost_tracking":    self.enable_cost_tracking,
            "enable_policy_eval":      self.enable_policy_eval,
            "enable_result_validation": self.enable_result_validation,
            "enable_provider_fallback": self.enable_provider_fallback,
            "enable_retry":            self.enable_retry,
        }


# ---------------------------------------------------------------------------
# AI Framework Configuration (immutable)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIFrameworkConfiguration:
    """
    Immutable framework-level AI Platform configuration.

    This is the top-level configuration object passed to
    :class:`AIContainer` at startup.

    Fields
    ------
    environment :      Deployment environment (``"production"`` | ``"staging"`` | ``"test"``).
    governance_tier :  Default governance tier (``"fast"`` | ``"standard"`` | ``"full"``).
    default_timeout_s : Default per-request timeout.
    default_max_retries : Default retry count.
    default_token_budget : Default context token budget.
    default_max_output :  Default max completion tokens.
    max_sessions :     Maximum concurrent sessions.
    session_ttl_s :    Default session TTL.
    feature_flags :    :class:`FeatureFlags`.
    """
    environment:          str          = "production"
    governance_tier:      str          = "standard"
    default_timeout_s:    float        = 30.0
    default_max_retries:  int          = 3
    default_token_budget: int          = 8_192
    default_max_output:   int          = 2_048
    max_sessions:         int          = 500
    session_ttl_s:        float        = 300.0
    feature_flags:        FeatureFlags = field(default_factory=FeatureFlags)
    schema:               str          = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "environment":          self.environment,
            "governance_tier":      self.governance_tier,
            "default_timeout_s":    self.default_timeout_s,
            "default_max_retries":  self.default_max_retries,
            "default_token_budget": self.default_token_budget,
            "default_max_output":   self.default_max_output,
            "max_sessions":         self.max_sessions,
            "session_ttl_s":        self.session_ttl_s,
            "feature_flags":        self.feature_flags.to_dict(),
        }


# ---------------------------------------------------------------------------
# Runtime Configuration (mutable, hot-reload capable)
# ---------------------------------------------------------------------------

class RuntimeConfiguration:
    """
    Mutable runtime configuration that can be updated without restart.

    Wraps an :class:`AIFrameworkConfiguration` and allows selective
    override of individual settings at runtime.

    Use :meth:`reload` to pick up a fresh configuration from the loader.
    """

    def __init__(self, config: AIFrameworkConfiguration) -> None:
        self._config = config
        self._overrides: Dict[str, Any] = {}

    @property
    def config(self) -> AIFrameworkConfiguration:
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Return an override value if set, otherwise the base config value."""
        if key in self._overrides:
            return self._overrides[key]
        return getattr(self._config, key, default)

    def override(self, key: str, value: Any) -> None:
        """Apply a runtime override for ``key``."""
        self._overrides[key] = value

    def clear_override(self, key: str) -> None:
        self._overrides.pop(key, None)

    def reload(self, new_config: AIFrameworkConfiguration) -> None:
        """Replace the base configuration (clears all overrides)."""
        self._config    = new_config
        self._overrides = {}

    def to_dict(self) -> Dict[str, Any]:
        d = self._config.to_dict()
        d["runtime_overrides"] = dict(self._overrides)
        return d


# ---------------------------------------------------------------------------
# Abstract ConfigurationLoader
# ---------------------------------------------------------------------------

class ConfigurationLoader(abc.ABC):
    """
    Abstract configuration loader.

    Implementations load :class:`AIFrameworkConfiguration` from
    environment variables, files, Vault, test fixtures, etc.
    """

    @abc.abstractmethod
    def load(self) -> AIFrameworkConfiguration:
        """Load and return a fully populated :class:`AIFrameworkConfiguration`."""

    def reload(self) -> AIFrameworkConfiguration:
        """Reload (default: delegates to :meth:`load`)."""
        return self.load()


# ---------------------------------------------------------------------------
# Environment-variable loader (reference implementation)
# ---------------------------------------------------------------------------

class EnvironmentConfigurationLoader(ConfigurationLoader):
    """
    Loads :class:`AIFrameworkConfiguration` from environment variables.

    Environment variables
    ----------------------
    ``IIOS_AI_ENVIRONMENT``         -- deployment environment
    ``IIOS_AI_GOVERNANCE_TIER``     -- governance tier
    ``IIOS_AI_TIMEOUT_S``           -- default timeout
    ``IIOS_AI_MAX_RETRIES``         -- default max retries
    ``IIOS_AI_TOKEN_BUDGET``        -- default token budget
    ``IIOS_AI_MAX_OUTPUT``          -- default max output tokens
    ``IIOS_AI_MAX_SESSIONS``        -- max concurrent sessions
    ``IIOS_AI_SESSION_TTL_S``       -- default session TTL
    """

    def load(self) -> AIFrameworkConfiguration:
        def _int(key: str, default: int) -> int:
            return int(os.environ.get(key, default))

        def _float(key: str, default: float) -> float:
            return float(os.environ.get(key, default))

        def _str(key: str, default: str) -> str:
            return os.environ.get(key, default)

        return AIFrameworkConfiguration(
            environment          = _str("IIOS_AI_ENVIRONMENT",     "production"),
            governance_tier      = _str("IIOS_AI_GOVERNANCE_TIER", "standard"),
            default_timeout_s    = _float("IIOS_AI_TIMEOUT_S",     30.0),
            default_max_retries  = _int("IIOS_AI_MAX_RETRIES",     3),
            default_token_budget = _int("IIOS_AI_TOKEN_BUDGET",    8_192),
            default_max_output   = _int("IIOS_AI_MAX_OUTPUT",      2_048),
            max_sessions         = _int("IIOS_AI_MAX_SESSIONS",    500),
            session_ttl_s        = _float("IIOS_AI_SESSION_TTL_S", 300.0),
        )
