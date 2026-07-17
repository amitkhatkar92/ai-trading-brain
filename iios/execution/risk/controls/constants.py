"""iios/execution/risk/controls/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS
Execution Risk Controls Framework.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

from enum import Enum
from typing import Dict

# ── System identifiers ────────────────────────────────────────────────────────

CONTROLS_SYSTEM_ID  = "iios:execution:risk:controls"
ENGINE_SYSTEM_ID    = "iios:execution:risk:controls:engine"
MANAGER_SYSTEM_ID   = "iios:execution:risk:controls:manager"
REGISTRY_SYSTEM_ID  = "iios:execution:risk:controls:registry"
FACTORY_SYSTEM_ID   = "iios:execution:risk:controls:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:risk:controls:validator"

VERSION = "1.0.0"

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_ENGINE   = "iios:execution:risk:controls:engine"
ACTOR_MANAGER  = "iios:execution:risk:controls:manager"
ACTOR_POLICY   = "iios:execution:risk:controls:policy"
ACTOR_SYSTEM   = "iios:system"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_HISTORY         = 5_000
DEFAULT_MAX_REQUESTS        = 10_000
DEFAULT_DECISION_TIMEOUT_MS = 200.0
DEFAULT_SEARCH_LIMIT        = 1_000
DEFAULT_PASS_THRESHOLD      = 0.50   # for MajorityPolicy


# ── Control actions ───────────────────────────────────────────────────────────

class ControlAction(str, Enum):
    """
    All control actions the framework can produce.

    Priority (highest first — determines winner when multiple rules fire):
      EMERGENCY_STOP > BLOCK > CANCEL > REQUIRE_OVERRIDE >
      PAUSE > RETRY > ALLOW_WITH_WARNING > ALLOW
    """
    ALLOW              = "ALLOW"
    ALLOW_WITH_WARNING = "ALLOW_WITH_WARNING"
    RETRY              = "RETRY"
    PAUSE              = "PAUSE"
    REQUIRE_OVERRIDE   = "REQUIRE_OVERRIDE"
    CANCEL             = "CANCEL"
    BLOCK              = "BLOCK"
    EMERGENCY_STOP     = "EMERGENCY_STOP"


# Priority map — higher int = higher priority
ACTION_PRIORITY: Dict[ControlAction, int] = {
    ControlAction.ALLOW:              1,
    ControlAction.ALLOW_WITH_WARNING: 2,
    ControlAction.RETRY:              3,
    ControlAction.PAUSE:              4,
    ControlAction.REQUIRE_OVERRIDE:   5,
    ControlAction.CANCEL:             6,
    ControlAction.BLOCK:              7,
    ControlAction.EMERGENCY_STOP:     8,
}


def highest_priority_action(*actions: ControlAction) -> ControlAction:
    """Return the highest-priority action from the given candidates."""
    if not actions:
        return ControlAction.ALLOW
    return max(actions, key=lambda a: ACTION_PRIORITY[a])


# Derived sets
BLOCKING_ACTIONS: frozenset = frozenset({
    ControlAction.BLOCK,
    ControlAction.CANCEL,
    ControlAction.EMERGENCY_STOP,
})

TERMINAL_ACTIONS: frozenset = frozenset({
    ControlAction.BLOCK,
    ControlAction.CANCEL,
    ControlAction.EMERGENCY_STOP,
})

PASSTHROUGH_ACTIONS: frozenset = frozenset({
    ControlAction.ALLOW,
    ControlAction.ALLOW_WITH_WARNING,
})

DEFERRAL_ACTIONS: frozenset = frozenset({
    ControlAction.PAUSE,
    ControlAction.RETRY,
    ControlAction.REQUIRE_OVERRIDE,
})


# ── Policy types ──────────────────────────────────────────────────────────────

class PolicyType(str, Enum):
    """Available control policy algorithms."""
    SINGLE_RULE       = "SINGLE_RULE"
    MAJORITY          = "MAJORITY"
    HIGHEST_SEVERITY  = "HIGHEST_SEVERITY"
    WEIGHTED_SEVERITY = "WEIGHTED_SEVERITY"
    EMERGENCY         = "EMERGENCY"
    CONFIGURABLE      = "CONFIGURABLE"


# ── Control event types ───────────────────────────────────────────────────────

class ControlEventType(str, Enum):
    CONTROL_EVALUATED  = "CONTROL_EVALUATED"
    CONTROL_APPROVED   = "CONTROL_APPROVED"
    CONTROL_PAUSED     = "CONTROL_PAUSED"
    CONTROL_RETRIED    = "CONTROL_RETRIED"
    OVERRIDE_REQUESTED = "OVERRIDE_REQUESTED"
    OVERRIDE_APPROVED  = "OVERRIDE_APPROVED"
    EXECUTION_BLOCKED  = "EXECUTION_BLOCKED"
    EMERGENCY_TRIGGERED = "EMERGENCY_TRIGGERED"


# ── Rule outcome → control action mapping ─────────────────────────────────────

# Canonical mapping used by HighestSeverityPolicy and SingleRulePolicy.
# Import from iios.execution.risk.rules.constants at runtime to avoid
# circular imports at module load time.
OUTCOME_TO_ACTION = {
    "PASS":              ControlAction.ALLOW,
    "SKIPPED":           ControlAction.ALLOW,
    "WARNING":           ControlAction.ALLOW_WITH_WARNING,
    "OVERRIDE_REQUIRED": ControlAction.REQUIRE_OVERRIDE,
    "BLOCK":             ControlAction.BLOCK,
    "FAILED":            ControlAction.BLOCK,   # failed rule = unsafe
}
