"""iios/execution/risk/integration/constants.py
==================================================
Constants, enumerations, and bounds for the
Execution Risk Integration subsystem (M6).

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

INTEGRATION_SYSTEM_ID = "iios:execution:risk:integration"
ENGINE_SYSTEM_ID      = "iios:execution:risk:integration:engine"
MANAGER_SYSTEM_ID     = "iios:execution:risk:integration:manager"
REGISTRY_SYSTEM_ID    = "iios:execution:risk:integration:registry"
FACTORY_SYSTEM_ID     = "iios:execution:risk:integration:factory"
VALIDATOR_SYSTEM_ID   = "iios:execution:risk:integration:validator"
HISTORY_SYSTEM_ID     = "iios:execution:risk:integration:history"
HEALTH_SYSTEM_ID      = "iios:execution:risk:integration:health"

VERSION = "1.0.0"

# ── Operational bounds ────────────────────────────────────────────────────────

DEFAULT_MAX_HISTORY        = 10_000
DEFAULT_MAX_REQUESTS       = 100_000
DEFAULT_TIMEOUT_MS         = 5_000.0
DEFAULT_SEARCH_LIMIT       = 1_000
DEFAULT_HEALTH_CHECK_LIMIT = 50

# ── Actors ────────────────────────────────────────────────────────────────────

ACTOR_ENGINE  = "iios:execution:risk:integration:engine"
ACTOR_MANAGER = "iios:execution:risk:integration:manager"
ACTOR_SYSTEM  = "iios:system"

# ── Component types ───────────────────────────────────────────────────────────

class ComponentType(str, Enum):
    """
    Logical types of components owned by the integration engine.

    Used to identify components in the ComponentRegistry and
    health checks.
    """
    LIFECYCLE   = "lifecycle"
    ENGINE      = "engine"
    RULES       = "rules"
    CONTROLS    = "controls"
    SNAPSHOT    = "snapshot"
    INTEGRATION = "integration"


# ── Integration event types ───────────────────────────────────────────────────

class IntegrationEventType(str, Enum):
    """Lifecycle events published by the integration subsystem."""
    SUBSYSTEM_INITIALIZED = "subsystem_initialized"
    SUBSYSTEM_STARTED     = "subsystem_started"
    EVALUATION_REQUESTED  = "evaluation_requested"
    EVALUATION_COMPLETED  = "evaluation_completed"
    SNAPSHOT_PUBLISHED    = "snapshot_published"
    VALIDATION_COMPLETED  = "validation_completed"
    HEALTH_UPDATED        = "health_updated"
    SUBSYSTEM_STOPPED     = "subsystem_stopped"


# ── Evaluation modes ──────────────────────────────────────────────────────────

class EvaluationMode(str, Enum):
    """
    Evaluation mode controls how the integration engine handles
    marginal or edge-case evaluations.

    STANDARD    — normal risk evaluation; all rules applied
    STRICT      — no warnings allowed; warnings treated as blocks
    PERMISSIVE  — warnings allowed; blocks require explicit override
    EMERGENCY   — emergency stop mode; all evaluations blocked
    """
    STANDARD   = "standard"
    STRICT     = "strict"
    PERMISSIVE = "permissive"
    EMERGENCY  = "emergency"


# ── M2 outcome → M5 lifecycle state mapping ───────────────────────────────────

_M2_OUTCOME_TO_RISK_STATE: dict[str, str] = {
    "PASSED":  "PASSED",
    "WARNING": "WARNING",
    "BLOCKED": "BLOCKED",
    "ERROR":   "BLOCKED",   # treat errors conservatively as blocking
    "SKIPPED": "PASSED",
}

# ── Control actions that constitute approval ──────────────────────────────────

APPROVED_ACTIONS = frozenset({"ALLOW", "ALLOW_WITH_WARNING"})

# ── Minimum required components (ComponentTypes that must be registered) ──────

REQUIRED_COMPONENT_TYPES = frozenset({
    ComponentType.ENGINE,
    ComponentType.CONTROLS,
    ComponentType.SNAPSHOT,
})
