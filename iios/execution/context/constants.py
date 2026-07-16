"""iios/execution/context/constants.py
==================================================
Constants, enumerations, and bounds for the
IIOS Execution Context package.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

CONTEXT_SYSTEM_ID    = "iios:execution:context"
BUILDER_SYSTEM_ID    = "iios:execution:context:builder"
FACTORY_SYSTEM_ID    = "iios:execution:context:factory"
REGISTRY_SYSTEM_ID   = "iios:execution:context:registry"
VALIDATOR_SYSTEM_ID  = "iios:execution:context:validator"

VERSION = "1.0.0"

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_BUILDER   = "iios:execution:context:builder"
ACTOR_FACTORY   = "iios:execution:context:factory"
ACTOR_REGISTRY  = "iios:execution:context:registry"
ACTOR_VALIDATOR = "iios:execution:context:validator"
ACTOR_USER      = "iios:user"

# ── Capacity defaults ─────────────────────────────────────────────────────────

DEFAULT_MAX_CONTEXTS       = 500_000
DEFAULT_MAX_HISTORY        = 100
DEFAULT_MAX_BUNDLE_SIZE    = 1_000

# ── Enumerations ──────────────────────────────────────────────────────────────


class ExecutionMode(str, Enum):
    """Operational mode for an execution context."""
    PAPER      = "PAPER"       # Simulated fills; no real money
    SIMULATION = "SIMULATION"  # Scenario replay
    BACKTEST   = "BACKTEST"    # Historical backtesting
    LIVE       = "LIVE"        # Real broker routing
    RECOVERY   = "RECOVERY"    # Recovering a failed / crashed execution
    REPLAY     = "REPLAY"      # Re-running a historical execution


class ExecutionEnvironment(str, Enum):
    """Deployment environment."""
    DEVELOPMENT = "DEVELOPMENT"
    TESTING     = "TESTING"
    STAGING     = "STAGING"
    PRODUCTION  = "PRODUCTION"


class MarketSession(str, Enum):
    """Market session classifier."""
    PRE_MARKET  = "PRE_MARKET"
    OPEN        = "OPEN"
    POST_MARKET = "POST_MARKET"
    CLOSED      = "CLOSED"
    HOLIDAY     = "HOLIDAY"
    UNKNOWN     = "UNKNOWN"


class ContextStatus(str, Enum):
    """Lifecycle status of an ExecutionContext in the registry."""
    BUILDING   = "BUILDING"
    VALIDATED  = "VALIDATED"
    PUBLISHED  = "PUBLISHED"
    REJECTED   = "REJECTED"
    ARCHIVED   = "ARCHIVED"


class ContextValidationCode(str, Enum):
    """Machine-readable codes for context validation failures."""
    MISSING_EXECUTION_ID   = "MISSING_EXECUTION_ID"
    MISSING_WORKFLOW_ID    = "MISSING_WORKFLOW_ID"
    MISSING_ORDER_ID       = "MISSING_ORDER_ID"
    MISSING_DECISION_ID    = "MISSING_DECISION_ID"
    MISSING_PORTFOLIO_ID   = "MISSING_PORTFOLIO_ID"
    MISSING_STRATEGY_ID    = "MISSING_STRATEGY_ID"
    MISSING_CORRELATION_ID = "MISSING_CORRELATION_ID"
    MISSING_REQUEST_ID     = "MISSING_REQUEST_ID"
    INVALID_MODE           = "INVALID_MODE"
    INVALID_ENVIRONMENT    = "INVALID_ENVIRONMENT"
    INCONSISTENT_IDS       = "INCONSISTENT_IDS"
    SNAPSHOT_MISMATCH      = "SNAPSHOT_MISMATCH"
    SESSION_INVALID        = "SESSION_INVALID"
    BROKER_CONTEXT_INVALID = "BROKER_CONTEXT_INVALID"
    DUPLICATE_CONTEXT      = "DUPLICATE_CONTEXT"
    REGISTRY_CAPACITY      = "REGISTRY_CAPACITY"
    INCOMPLETE_CONTEXT     = "INCOMPLETE_CONTEXT"
