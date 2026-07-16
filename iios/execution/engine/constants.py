"""iios/execution/engine/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS Execution Engine.

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

ENGINE_SYSTEM_ID    = "iios:execution:engine"
MANAGER_SYSTEM_ID   = "iios:execution:engine:manager"
REGISTRY_SYSTEM_ID  = "iios:execution:engine:registry"
FACTORY_SYSTEM_ID   = "iios:execution:engine:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:engine:validator"

VERSION = "1.0.0"

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_ENGINE    = "iios:execution:engine"
ACTOR_VALIDATOR = "iios:execution:engine:validator"
ACTOR_FACTORY   = "iios:execution:engine:factory"
ACTOR_REGISTRY  = "iios:execution:engine:registry"
ACTOR_USER      = "iios:user"

# ── Capacity defaults ─────────────────────────────────────────────────────────

DEFAULT_MAX_EXECUTIONS = 100_000
DEFAULT_MAX_HISTORY    = 1_000
DEFAULT_QUEUE_SIZE     = 10_000

# ── Timing thresholds (seconds) ───────────────────────────────────────────────

MAX_EXECUTION_TIMEOUT_SEC  = 300.0   # 5 minutes hard limit
DEFAULT_EXECUTION_TIMEOUT  = 60.0
VALIDATION_TIMEOUT_SEC     = 10.0
PREPARATION_TIMEOUT_SEC    = 30.0

# ── Enumerations ──────────────────────────────────────────────────────────────


class ExecutionMode(str, Enum):
    """How the execution will be processed."""
    PAPER      = "PAPER"       # Simulated fills; no real money
    SIMULATION = "SIMULATION"  # Back-test or scenario replay
    LIVE       = "LIVE"        # Real broker routing (future phase)


class ExecutionPriority(str, Enum):
    """Relative urgency of an execution request."""
    CRITICAL   = "CRITICAL"
    HIGH       = "HIGH"
    NORMAL     = "NORMAL"
    LOW        = "LOW"
    BACKGROUND = "BACKGROUND"


class ExecutionValidationCode(str, Enum):
    """Machine-readable reason codes for validation failures."""
    MISSING_ORDER_ID     = "MISSING_ORDER_ID"
    MISSING_DECISION_ID  = "MISSING_DECISION_ID"
    MISSING_PORTFOLIO_ID = "MISSING_PORTFOLIO_ID"
    MISSING_STRATEGY_ID  = "MISSING_STRATEGY_ID"
    INVALID_MODE         = "INVALID_MODE"
    INVALID_PRIORITY     = "INVALID_PRIORITY"
    REQUEST_EXPIRED      = "REQUEST_EXPIRED"
    ORDER_NOT_FOUND      = "ORDER_NOT_FOUND"
    ORDER_TERMINAL       = "ORDER_TERMINAL"
    ORDER_INVALID_STATE  = "ORDER_INVALID_STATE"
    PORTFOLIO_MISSING    = "PORTFOLIO_MISSING"
    DECISION_MISSING     = "DECISION_MISSING"
    TRANSITION_INVALID   = "TRANSITION_INVALID"
