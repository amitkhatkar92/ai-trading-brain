"""iios/execution/risk/engine/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS
Execution Risk Engine coordination layer.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

ENGINE_SYSTEM_ID    = "iios:execution:risk:engine"
MANAGER_SYSTEM_ID   = "iios:execution:risk:engine:manager"
REGISTRY_SYSTEM_ID  = "iios:execution:risk:engine:registry"
FACTORY_SYSTEM_ID   = "iios:execution:risk:engine:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:risk:engine:validator"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_EVALUATIONS = 10_000
DEFAULT_MAX_HISTORY     = 5_000
DEFAULT_SEARCH_LIMIT    = 1_000
DEFAULT_MAX_RULES       = 200

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_ENGINE  = "iios:execution:risk:engine"
ACTOR_MANAGER = "iios:execution:risk:engine:manager"
ACTOR_SYSTEM  = "iios:system"


# ── Engine operation state ────────────────────────────────────────────────────

class EngineOpState(str, Enum):
    """
    Transient phase of the engine while processing a single evaluation.

    IDLE        — awaiting the next request
    VALIDATING  — running request validation
    EVALUATING  — invoking registered risk rules
    AGGREGATING — combining rule results into an overall outcome
    FINALIZING  — transitioning the lifecycle object and emitting events
    COMPLETED   — operation finished successfully
    FAILED      — operation finished with an error
    """
    IDLE        = "IDLE"
    VALIDATING  = "VALIDATING"
    EVALUATING  = "EVALUATING"
    AGGREGATING = "AGGREGATING"
    FINALIZING  = "FINALIZING"
    COMPLETED   = "COMPLETED"
    FAILED      = "FAILED"


TERMINAL_OP_STATES = frozenset({EngineOpState.COMPLETED, EngineOpState.FAILED})


# ── Operation types ───────────────────────────────────────────────────────────

class OperationType(str, Enum):
    """The seven execution risk engine operations."""
    CREATE_EVALUATION = "CREATE_EVALUATION"
    EVALUATE          = "EVALUATE"
    AGGREGATE         = "AGGREGATE"
    FINALIZE          = "FINALIZE"
    PUBLISH           = "PUBLISH"
    ARCHIVE           = "ARCHIVE"
    QUERY             = "QUERY"


# ── Engine event types ────────────────────────────────────────────────────────

class EngineEventType(str, Enum):
    """Domain events published by the Execution Risk Engine."""
    EVALUATION_STARTED       = "EVALUATION_STARTED"
    RULE_EXECUTION_STARTED   = "RULE_EXECUTION_STARTED"
    RULE_EXECUTION_COMPLETED = "RULE_EXECUTION_COMPLETED"
    EVALUATION_COMPLETED     = "EVALUATION_COMPLETED"
    EVALUATION_FAILED        = "EVALUATION_FAILED"
    SNAPSHOT_PUBLISHED       = "SNAPSHOT_PUBLISHED"
    ENGINE_STARTED           = "ENGINE_STARTED"
    ENGINE_STOPPED           = "ENGINE_STOPPED"


# ── Rule outcome ──────────────────────────────────────────────────────────────

class RuleOutcome(str, Enum):
    """
    The outcome produced by a single risk rule evaluation.

    PASSED  — rule check passed; execution may proceed
    WARNING — rule check passed with a warning
    BLOCKED — rule check blocked execution
    ERROR   — the rule itself encountered an error
    SKIPPED — rule was not applicable to this request
    """
    PASSED  = "PASSED"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"
    ERROR   = "ERROR"
    SKIPPED = "SKIPPED"


# ── Validation codes ──────────────────────────────────────────────────────────

class ValidationCode(str, Enum):
    """Short-code classification for validation failures."""
    IDENTIFIER_MISSING   = "IDENTIFIER_MISSING"
    CONTEXT_INVALID      = "CONTEXT_INVALID"
    SNAPSHOT_MISSING     = "SNAPSHOT_MISSING"
    EVALUATION_NOT_FOUND = "EVALUATION_NOT_FOUND"
    OPERATION_REJECTED   = "OPERATION_REJECTED"
