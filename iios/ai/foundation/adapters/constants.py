"""
constants.py — iios.ai.foundation.adapters
============================================
Enumerations, identifiers, and defaults for the AI Foundation
provider adapter layer (M4).

A1 AI Foundation — Phase 3, Module 4
"""
from __future__ import annotations

from enum import Enum

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
ADAPTERS_SYSTEM_ID: str  = "iios:ai:foundation:adapters"
PROVIDER_REGISTRY_ID: str = "iios:ai:foundation:adapters:registry"
CONFIG_SYSTEM_ID: str    = "iios:ai:foundation:adapters:config"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Capability categories — used by A2 Model Management for routing
# ---------------------------------------------------------------------------
class AICapability(str, Enum):
    """
    Capability classes that an AI model provider can offer.

    AI modules declare required capabilities; A2 routes to an appropriate
    model based on these declarations.
    """
    COMPLETION         = "completion"          # text / chat completion
    EMBEDDING          = "embedding"           # vector embeddings
    SUMMARISATION      = "summarisation"       # text summarisation
    CODE               = "code"                # code generation / analysis
    STRUCTURED_OUTPUT  = "structured_output"   # JSON / schema-constrained output
    REASONING          = "reasoning"           # multi-step reasoning (CoT / o1-style)
    VISION             = "vision"              # image understanding
    TOOL_USE           = "tool_use"            # function calling / tool invocation


# ---------------------------------------------------------------------------
# AI request priority
# ---------------------------------------------------------------------------
class AIRequestPriority(str, Enum):
    """Request scheduling priority for the AI execution pipeline."""
    CRITICAL = "critical"   # time-sensitive trading signals
    HIGH     = "high"       # standard agent reasoning
    NORMAL   = "normal"     # background tasks
    LOW      = "low"        # evaluation / batch jobs


# ---------------------------------------------------------------------------
# AI execution status
# ---------------------------------------------------------------------------
class AIExecutionStatus(str, Enum):
    """Outcome status of an AI execution."""
    SUCCESS         = "success"
    FAILURE         = "failure"
    TIMEOUT         = "timeout"
    TOKEN_BUDGET    = "token_budget_exceeded"
    RATE_LIMITED    = "rate_limited"
    PROVIDER_ERROR  = "provider_error"
    POLICY_BLOCKED  = "policy_blocked"
    CANCELLED       = "cancelled"


# ---------------------------------------------------------------------------
# Provider health
# ---------------------------------------------------------------------------
class AIProviderHealth(str, Enum):
    """Health status of an AI model provider."""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"


# ---------------------------------------------------------------------------
# Numeric defaults
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT_S:             float = 30.0    # per-request timeout
DEFAULT_MAX_RETRIES:           int   = 3       # maximum retry attempts
DEFAULT_RETRY_BACKOFF_BASE_S:  float = 1.0     # base back-off interval
DEFAULT_RETRY_BACKOFF_MAX_S:   float = 30.0    # maximum back-off cap
DEFAULT_RATE_LIMIT_TPM:        int   = 100_000 # tokens per minute
DEFAULT_RATE_LIMIT_RPM:        int   = 500     # requests per minute
DEFAULT_TOKEN_BUDGET:          int   = 8_192   # default context budget
DEFAULT_MAX_OUTPUT_TOKENS:     int   = 2_048   # default max completion tokens
