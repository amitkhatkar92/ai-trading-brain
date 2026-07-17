"""iios/execution/risk/rules/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS Execution Risk
Rules Framework.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

RULES_SYSTEM_ID    = "iios:execution:risk:rules"
REGISTRY_SYSTEM_ID = "iios:execution:risk:rules:registry"
EXECUTOR_SYSTEM_ID = "iios:execution:risk:rules:executor"
MANAGER_SYSTEM_ID  = "iios:execution:risk:rules:manager"
FACTORY_SYSTEM_ID  = "iios:execution:risk:rules:factory"

VERSION = "1.0.0"

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_FRAMEWORK = "iios:execution:risk:rules:framework"
ACTOR_EXECUTOR  = "iios:execution:risk:rules:executor"
ACTOR_SYSTEM    = "iios:system"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_RULES           = 200
DEFAULT_MAX_HISTORY         = 2_000
DEFAULT_EXECUTION_TIMEOUT_MS = 100.0     # ms per rule
DEFAULT_SEARCH_LIMIT        = 500

# ── Rule outcome ──────────────────────────────────────────────────────────────

class RuleOutcome(str, Enum):
    """
    All valid outcomes for a single rule evaluation.

    Priority (highest first for aggregation):
      BLOCK > FAILED > OVERRIDE_REQUIRED > WARNING > SKIPPED > PASS
    """
    PASS              = "PASS"
    WARNING           = "WARNING"
    BLOCK             = "BLOCK"
    OVERRIDE_REQUIRED = "OVERRIDE_REQUIRED"
    SKIPPED           = "SKIPPED"
    FAILED            = "FAILED"


# ── Rule execution mode ───────────────────────────────────────────────────────

class ExecutionMode(str, Enum):
    """Order in which the executor applies rules."""
    SEQUENTIAL      = "SEQUENTIAL"       # registration order
    PRIORITY_ORDERED = "PRIORITY_ORDERED" # highest priority first
    CONDITIONAL     = "CONDITIONAL"      # stop on first BLOCK


# ── Rule event types ──────────────────────────────────────────────────────────

class RuleEventType(str, Enum):
    RULE_REGISTERED   = "RULE_REGISTERED"
    RULE_UNREGISTERED = "RULE_UNREGISTERED"
    RULE_STARTED      = "RULE_STARTED"
    RULE_COMPLETED    = "RULE_COMPLETED"
    RULE_PASSED       = "RULE_PASSED"
    RULE_WARNING      = "RULE_WARNING"
    RULE_BLOCKED      = "RULE_BLOCKED"
    RULE_FAILED       = "RULE_FAILED"


# ── Derived helpers ───────────────────────────────────────────────────────────

BLOCKING_OUTCOMES: frozenset[RuleOutcome] = frozenset({RuleOutcome.BLOCK})

PASSING_OUTCOMES: frozenset[RuleOutcome] = frozenset({
    RuleOutcome.PASS,
    RuleOutcome.SKIPPED,
})

WARNING_OUTCOMES: frozenset[RuleOutcome] = frozenset({
    RuleOutcome.WARNING,
    RuleOutcome.OVERRIDE_REQUIRED,
})

TERMINAL_OUTCOMES: frozenset[RuleOutcome] = frozenset({
    RuleOutcome.BLOCK,
    RuleOutcome.FAILED,
})
