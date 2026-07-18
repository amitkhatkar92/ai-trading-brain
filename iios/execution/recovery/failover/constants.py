"""
iios/execution/recovery/failover/constants.py
============================================
Constants, enumerations, and runtime limits for the Execution Failover
Framework.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, Tuple

# ── System identifiers ────────────────────────────────────────────────────────

SYSTEM_ID      = "iios:execution:recovery:failover"
ENGINE_ID      = "iios:execution:recovery:failover:engine"
MANAGER_ID     = "iios:execution:recovery:failover:manager"
CONTROLLER_ID  = "iios:execution:recovery:failover:controller"
EXECUTOR_ID    = "iios:execution:recovery:failover:executor"
VERIFIER_ID    = "iios:execution:recovery:failover:verifier"
REGISTRY_ID    = "iios:execution:recovery:failover:registry"
FACTORY_ID     = "iios:execution:recovery:failover:factory"

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Runtime limits ────────────────────────────────────────────────────────────

DEFAULT_MAX_SESSIONS       = 1_000
DEFAULT_MAX_HISTORY        = 2_000
DEFAULT_MAX_EVENTS         = 20_000
DEFAULT_MAX_ACTIVE_SESSIONS = 32    # concurrent failovers in flight
DEFAULT_EXECUTION_TIMEOUT_MS = 30_000

# ── Actors ────────────────────────────────────────────────────────────────────

ACTOR_ENGINE     = "failover_engine"
ACTOR_MANAGER    = "failover_manager"
ACTOR_CONTROLLER = "failover_controller"
ACTOR_EXECUTOR   = "failover_executor"
ACTOR_VERIFIER   = "failover_verifier"
ACTOR_SYSTEM     = "system"
ACTOR_OPERATOR   = "operator"

# ── Failover types ────────────────────────────────────────────────────────────

class FailoverType(str, Enum):
    """Type of failover to execute."""
    HOT       = "hot"           # Immediate switch to hot-standby
    WARM      = "warm"          # Switch to pre-warmed standby
    COLD      = "cold"          # Switch to cold standby
    COMPONENT = "component"     # Single component failover
    BROKER    = "broker"        # Broker connection failover
    GATEWAY   = "gateway"       # Gateway connection failover
    NODE      = "node"          # Node-level failover
    SERVICE   = "service"       # Service-level failover
    WORKFLOW  = "workflow"      # Full workflow failover
    MANUAL    = "manual"        # Human-initiated failover

# ── Failover actions ──────────────────────────────────────────────────────────

class FailoverAction(str, Enum):
    """Atomic action to execute during failover."""
    RETRY              = "retry"
    RESUME             = "resume"
    RESTART_COMPONENT  = "restart_component"
    RESTART_WORKFLOW   = "restart_workflow"
    SWITCH_GATEWAY     = "switch_gateway"
    SWITCH_BROKER      = "switch_broker"
    ACTIVATE_BACKUP    = "activate_backup"
    DEACTIVATE_PRIMARY = "deactivate_primary"
    ROLLBACK           = "rollback"
    GRACEFUL_SHUTDOWN  = "graceful_shutdown"
    MANUAL_ESCALATION  = "manual_escalation"

# ── Failover status ───────────────────────────────────────────────────────────

class FailoverStatus(str, Enum):
    PENDING    = "pending"
    PREPARING  = "preparing"
    EXECUTING  = "executing"
    VERIFYING  = "verifying"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"

# ── Failover phases ───────────────────────────────────────────────────────────

class FailoverPhase(str, Enum):
    VALIDATION    = "validation"
    RESOURCE_CHECK = "resource_check"
    PREPARATION   = "preparation"
    EXECUTION     = "execution"
    VERIFICATION  = "verification"
    RESTORATION   = "restoration"
    COMPLETION    = "completion"

# ── Verification status ───────────────────────────────────────────────────────

class VerificationStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    PASSED      = "passed"
    FAILED      = "failed"
    SKIPPED     = "skipped"

# ── Health status ─────────────────────────────────────────────────────────────

class HealthStatus(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN   = "unknown"

# ── Failover event types ──────────────────────────────────────────────────────

class FailoverEventType(str, Enum):
    FAILOVER_STARTED               = "failover_started"
    FAILOVER_PREPARED              = "failover_prepared"
    FAILOVER_EXECUTED              = "failover_executed"
    FAILOVER_VERIFIED              = "failover_verified"
    FAILOVER_COMPLETED             = "failover_completed"
    FAILOVER_FAILED                = "failover_failed"
    FALLBACK_ACTIVATED             = "fallback_activated"
    MANUAL_ESCALATION_REQUESTED    = "manual_escalation_requested"

# ── Strategy to failover mapping (M3 RecoveryStrategyType.value → (FailoverType, FailoverAction)) ─

STRATEGY_TO_FAILOVER_MAP: Dict[str, Tuple[FailoverType, FailoverAction]] = {
    "retry":               (FailoverType.COMPONENT, FailoverAction.RETRY),
    "resume":              (FailoverType.WORKFLOW,  FailoverAction.RESUME),
    "rollback":            (FailoverType.WORKFLOW,  FailoverAction.ROLLBACK),
    "restart":             (FailoverType.COMPONENT, FailoverAction.RESTART_COMPONENT),
    "failover":            (FailoverType.HOT,       FailoverAction.SWITCH_BROKER),
    "manual_intervention": (FailoverType.MANUAL,    FailoverAction.MANUAL_ESCALATION),
    "emergency_shutdown":  (FailoverType.SERVICE,   FailoverAction.GRACEFUL_SHUTDOWN),
    "composite":           (FailoverType.COMPONENT, FailoverAction.RESTART_COMPONENT),
}

# Default fallback mapping when strategy not recognised
DEFAULT_FAILOVER_TYPE   = FailoverType.MANUAL
DEFAULT_FAILOVER_ACTION = FailoverAction.MANUAL_ESCALATION

# Actions that always succeed (do not depend on external resources)
ALWAYS_SUCCEEDS: FrozenSet[FailoverAction] = frozenset({
    FailoverAction.DEACTIVATE_PRIMARY,
    FailoverAction.GRACEFUL_SHUTDOWN,
    FailoverAction.MANUAL_ESCALATION,
})

# Actions that render the system non-operational afterward
NON_OPERATIONAL_ACTIONS: FrozenSet[FailoverAction] = frozenset({
    FailoverAction.GRACEFUL_SHUTDOWN,
    FailoverAction.MANUAL_ESCALATION,
    FailoverAction.DEACTIVATE_PRIMARY,
})
